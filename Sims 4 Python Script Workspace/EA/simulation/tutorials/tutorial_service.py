from __future__ import annotationsimport distributor.opsimport itertoolsimport persistence_error_typesimport servicesimport sims4.localizationimport sims4.logimport telemetry_helperfrom alarms import add_alarmfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom protocolbuffers import DistributorOps_pb2from protocolbuffers import GameplaySaveData_pb2from pivotal_moments.live_event_quest import LiveEventQuestfrom pivotal_moments.pivotal_moment import PivotalMomentfrom google.protobuf import text_formatfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import OptionalTunable, TunableReference, TunableTuple, TunableListfrom sims4.utils import classpropertyfrom situations.situation_manager import MAX_SITUATION_INSTANCES_OF_SAME_TYPE, MAX_LIVE_EVENT_QUEST_SITUATION_INSTANCES_OF_SAME_TYPEfrom snippets import TunableAffordanceFilterSnippetfrom tutorials.tutorial_tip import TutorialModefrom typing import TYPE_CHECKINGfrom user_account_data.user_account_data_enums import UserAccountDataTypeEnumif TYPE_CHECKING:
    import GameplaySaveData_pb2
    from sims4.tuning.instances import HashedTunedInstanceMetaclass
    from pivotal_moments.pivotal_moment import PivotalMoment
    from server.client import Client
    from situations.situation_serialization import SituationSeed
    from typing import *TELEMETRY_GROUP_TUTORIAL_SERVICE = 'TTSE'TELEMETRY_FIELD_CANCELLED_QUEST_ID = 'cqid'tutorial_service_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_TUTORIAL_SERVICE)logger = sims4.log.Logger('tutorial', default_owner='nabaker')
class TutorialService(Service):
    INTERACTION_DISABLED_TOOLTIP = sims4.localization.TunableLocalizedStringFactory(description='\n        Default Tooltip for disabled interactions.\n        ')
    TUTORIAL_DRAMA_NODE = TunableReference(description='\n        The drama node that controls the tutorial.\n        ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions=('TutorialDramaNode',))
    FALLBACK_RESTRICTED_AFFORDANCES = OptionalTunable(description='\n        If enabled, use this affordance restriction if we are in the tutorial \n        mode and somehow no restriction has currently been specified by a \n        tutorial tip.  (There should always be a restriction.)\n        ', tunable=TunableTuple(visible_affordances=TunableAffordanceFilterSnippet(description='\n                The filter of affordances that are visible.\n                '), tooltip=OptionalTunable(description='\n                Tooltip when interaction is disabled by tutorial restrictions\n                If not specified, will use the default in the tutorial service\n                tuning.\n                ', tunable=sims4.localization.TunableLocalizedStringFactory()), enabled_affordances=TunableAffordanceFilterSnippet(description='\n                The filter of visible affordances that are enabled.\n                ')))
    PIVOTAL_MOMENT_LIST = TunableList(description='\n        List of all Pivotal Moments that should be available to all players.\n        For A/B Testable Pivotal Moments, they must be set in experiment_service\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='PivotalMoment', pack_safe=True))
    FEATURE_KEY = 146753015717498385

    def __init__(self):
        self._visible_affordance_filter = None
        self._enabled_affordance_filter = None
        self._tooltip = None
        self._tutorial_alarms = {}
        self._unselectable_sim_id = None
        self._unselectable_sim_count = 0
        self._tutorial_mode = TutorialMode.STANDARD
        self._completed_pivotal_moments = set()
        self._rewarded_pivotal_moments = set()
        self._pivotal_moments = {}
        self._active_pivotal_ids = set()
        self._received_completed_pivotal_moments = False
        self._pivotal_moments_enabled = True
        self._pivotal_moment_situation_seeds = []
        self._pivotal_moments_activation_overrides = {}
        self._received_live_event_quests = False
        self._active_quests = {}
        self._cancelable_quests = {}
        self._completed_quest_ids = {}
        self._received_account_level_data = False
        self._account_level_situation_seeds = []
        self._dynamic_pivotal_moments = []

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_TUTORIAL_SERVICE

    def add_tutorial_alarm(self, tip, callback, time_of_day):
        now = services.game_clock_service().now()
        time_till_satisfy = now.time_till_next_day_time(time_of_day)
        self._tutorial_alarms[tip] = add_alarm(self, time_till_satisfy, callback, cross_zone=True)

    def remove_tutorial_alarm(self, tip):
        del self._tutorial_alarms[tip]

    def is_affordance_visible(self, affordance):
        visible_filter = self._visible_affordance_filter
        if self.FALLBACK_RESTRICTED_AFFORDANCES:
            visible_filter = self.FALLBACK_RESTRICTED_AFFORDANCES.visible_affordances
        return visible_filter is None and self._tutorial_mode == TutorialMode.FTUE and visible_filter is None or visible_filter(affordance)

    def get_disabled_affordance_tooltip(self, affordance):
        enabled_filter = self._enabled_affordance_filter
        disabled_text = self._tooltip
        if enabled_filter is None and self._tutorial_mode == TutorialMode.FTUE:
            enabled_filter = self.FALLBACK_RESTRICTED_AFFORDANCES.enabled_affordances
            disabled_text = self.FALLBACK_RESTRICTED_AFFORDANCES.tooltip
            return
        if enabled_filter is None or enabled_filter(affordance):
            return
        if disabled_text is not None:
            return disabled_text
        return self.INTERACTION_DISABLED_TOOLTIP

    def clear_restricted_affordances(self):
        self._visible_affordance_filter = None
        self._enabled_affordance_filter = None
        self._tooltip = None

    def set_restricted_affordances(self, visible_filter, tooltip, enabled_filter):
        self._visible_affordance_filter = visible_filter
        self._enabled_affordance_filter = enabled_filter
        self._tooltip = tooltip

    def on_all_households_and_sim_infos_loaded(self, client):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.trigger_tutorial_drama_node:
            save_slot_data_msg.trigger_tutorial_drama_node = False
            drama_scheduler = services.drama_scheduler_service()
            if drama_scheduler is not None:
                resolver = SingleSimResolver(services.active_sim_info())
                drama_scheduler.run_node(self.TUTORIAL_DRAMA_NODE, resolver)
        self._tutorial_mode = save_slot_data_msg.tutorial_mode

    def set_tutorial_mode(self, mode):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        save_slot_data_msg.tutorial_mode = mode
        self._tutorial_mode = mode
        if mode != TutorialMode.FTUE:
            drama_scheduler = services.drama_scheduler_service()
            if drama_scheduler is not None:
                drama_nodes = drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL)
                if drama_nodes:
                    drama_nodes[0].end()

    def is_sim_unselectable(self, sim_info):
        return sim_info.sim_id == self._unselectable_sim_id

    def set_unselectable_sim(self, sim_info):
        if sim_info is None:
            sim_id = None
        else:
            sim_id = sim_info.sim_id
        if sim_id != self._unselectable_sim_id:
            if sim_id is None:
                self._unselectable_sim_count -= 1
                if self._unselectable_sim_count > 0:
                    return
            elif self._unselectable_sim_id is None:
                self._unselectable_sim_count = 1
            else:
                logger.error('Tutorial only supports one unselectable sim at a time.  Attempting to add:{}', sim_info)
                return
            self._unselectable_sim_id = sim_id
            client = services.client_manager().get_first_client()
            if client is not None:
                client.selectable_sims.notify_dirty()
                if sim_id is not None:
                    client.validate_selectable_sim()
        elif sim_id is not None:
            self._unselectable_sim_count += 1

    def is_tutorial_running(self):
        drama_scheduler = services.drama_scheduler_service()
        if drama_scheduler is None or not drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL):
            return False
        return True

    def on_client_connect(self, client:'Client') -> 'None':
        opCompletedPivMos = distributor.ops.RequestCompletedPivotalMoments()
        Distributor.instance().add_op_with_no_owner(opCompletedPivMos)
        current_zone = services.current_zone()
        current_zone.refresh_feature_params(feature_key=self.FEATURE_KEY)
        opRequestQuestEvents = distributor.ops.RequestQuestEvents()
        Distributor.instance().add_op_with_no_owner(opRequestQuestEvents)
        opGetPivotalMomentsData = distributor.ops.GetAccountDataForCurrentUser(UserAccountDataTypeEnum.PIVOTAL_MOMENTS)
        Distributor.instance().add_op_with_no_owner(opGetPivotalMomentsData)

    def on_account_data_loaded(self, user_account_data):
        if self._received_account_level_data:
            return
        if user_account_data.data_type != UserAccountDataTypeEnum.PIVOTAL_MOMENTS:
            return
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        if snippet_manager is None:
            logger.warn('Unable to process pivotal moments before the snippet_manager is instantiated.')
            return
        pivotal_moments_data = GameplaySaveData_pb2.PivotalMomentsData()
        pivotal_moments_data.ParseFromString(user_account_data.data)
        for pivotal_moment_save_data in pivotal_moments_data.pivotal_moments:
            piv_moment = snippet_manager.get(pivotal_moment_save_data.pivotal_moment_id)
            piv_moment_inst = piv_moment()
            if not piv_moment_inst.should_load():
                pass
            else:
                piv_moment_inst.load(pivotal_moment_save_data, self)
                self._pivotal_moments[piv_moment.guid64] = piv_moment_inst
        self.process_account_level_data()
        self._received_account_level_data = True

    def _retrigger_test_events(self) -> 'None':
        active_quest_ids = [quest_id for quest_id in itertools.chain(*self._active_quests.values())]
        services.get_event_manager().process_event(test_events.TestEvent.LiveEventQuestsActive, active_quest_ids=active_quest_ids)
        for completed_pivotal_moment in self._completed_pivotal_moments:
            services.get_event_manager().process_event(test_events.TestEvent.PivotalMomentCompleted, pivotal_moment=completed_pivotal_moment)

    def process_account_level_data(self) -> 'None':
        self.determine_valid_pivotal_moments()
        self._retrigger_test_events()
        self.load_account_level_situations()

    def process_completed_pivotal_moments(self, completed_ids:'Tuple[str, str]') -> 'None':
        if self._received_completed_pivotal_moments:
            return
        self._received_completed_pivotal_moments = True
        if completed_ids is not None:
            if completed_ids[0] != '':
                completed_list = []
                completed_list.extend(completed_ids[0].split(','))
                self._completed_pivotal_moments.update([int(pivotal_moment_id) for pivotal_moment_id in completed_list])
            if completed_ids[1] != '':
                completed_list = []
                completed_list.extend(completed_ids[1].split(','))
                self._rewarded_pivotal_moments.update([int(pivotal_moment_id) for pivotal_moment_id in completed_list])
        self.determine_valid_pivotal_moments()

    def is_pivotal_moment_completed(self, pivotal_moment_id:'int') -> 'bool':
        if self._completed_pivotal_moments:
            return pivotal_moment_id in self._completed_pivotal_moments
        return False

    def process_pivotal_moment_data(self, pivotal_moment_data:'DistributorOps_pb2.PivotalMomentsList') -> 'None':
        if self._received_completed_pivotal_moments:
            return
        self._received_completed_pivotal_moments = True
        self._completed_pivotal_moments.update([pivotal_moment_id for pivotal_moment_id in pivotal_moment_data.completed_ids])
        self._rewarded_pivotal_moments.update([pivotal_moment_id for pivotal_moment_id in pivotal_moment_data.rewarded_ids])
        for pivotal_moment_item in pivotal_moment_data.items:
            self._pivotal_moments_activation_overrides[pivotal_moment_item.pivotal_moment_id] = pivotal_moment_item.activation_trigger_id
        self.determine_valid_pivotal_moments()

    def on_pivotal_moment_complete(self, pivotal_moment_id:'int', rewarded:'bool') -> 'None':
        self._completed_pivotal_moments.add(pivotal_moment_id)
        self._active_pivotal_ids.discard(pivotal_moment_id)
        if rewarded:
            self._rewarded_pivotal_moments.add(pivotal_moment_id)

    def on_live_event_quest_complete(self, live_event_id:'int', pivotal_moment_id:'int') -> 'None':
        completed_quests = self._completed_quest_ids.get(live_event_id, [])
        completed_quests.append(pivotal_moment_id)
        self._completed_quest_ids[live_event_id] = completed_quests

    def on_pivotal_moment_active(self, pivotal_moment_id:'int') -> 'None':
        self._active_pivotal_ids.add(pivotal_moment_id)

    def can_new_pivotal_moment_start(self) -> 'bool':
        return len(self._active_pivotal_ids) < MAX_SITUATION_INSTANCES_OF_SAME_TYPE

    def can_new_live_event_quest_start(self) -> 'bool':
        active_event_quest_ids = [quest_id for quest_id in itertools.chain(*self._active_quests.values())]
        active_live_event_quests = set(quest_id for quest_id in self._active_pivotal_ids if quest_id in active_event_quest_ids)
        return len(active_live_event_quests) < MAX_LIVE_EVENT_QUEST_SITUATION_INSTANCES_OF_SAME_TYPE

    def is_pivotal_moment_rewarded(self, pivotal_moment_id:'int') -> 'bool':
        return pivotal_moment_id in self._rewarded_pivotal_moments

    def determine_valid_pivotal_moments(self) -> 'None':
        if not self._received_completed_pivotal_moments:
            return
        if len(self._pivotal_moments) > 0:
            for piv_moment_inst in self._pivotal_moments.values():
                piv_moment_inst.update_activation_triggers()
        pivotal_moments = set(itertools.chain(self.PIVOTAL_MOMENT_LIST, self.get_active_quests(), self._dynamic_pivotal_moments))
        for piv_moment in pivotal_moments:
            if not piv_moment.guid64 in self._completed_pivotal_moments:
                if piv_moment.guid64 in self._pivotal_moments:
                    pass
                else:
                    activation_trigger_id = self._pivotal_moments_activation_overrides.get(piv_moment.guid64, 1)
                    piv_moment_inst = piv_moment(activation_trigger_id=activation_trigger_id)
                    piv_moment_inst.register_activation_trigger()
                    self._pivotal_moments[piv_moment.guid64] = piv_moment_inst

    def set_dynamic_pivotal_moments(self, pivotal_moments:'List[PivotalMoment]') -> 'None':
        if pivotal_moments:
            self._dynamic_pivotal_moments = pivotal_moments
            self.load_dynamic_moments()
            self.determine_valid_pivotal_moments()
            self.load_pivotal_moment_situations()

    def get_pivotal_moment_inst(self, piv_moment_id:'int') -> 'PivotalMoment':
        return self._pivotal_moments.get(piv_moment_id)

    def get_tuned_pivotal_moments(self, pivotal_moment_ids:'Set[int]') -> 'List[PivotalMoment]':
        pivotal_moments = []
        pivotal_moment_instance_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for pivotal_moment_id in pivotal_moment_ids:
            pivotal_moment = pivotal_moment_instance_manager.get(pivotal_moment_id)
            if pivotal_moment is None:
                pass
            else:
                pivotal_moments.append(pivotal_moment)
        return pivotal_moments

    def update_activation_trigger(self, pivotal_moment_id:'int', activation_trigger_id:'int') -> 'Tuple(bool, str)':
        if not any(pivotal_moment_id == pivotal_moment.guid64 for pivotal_moment in self.PIVOTAL_MOMENT_LIST):
            return (False, f'{pivotal_moment_id} does not exist')
        self._pivotal_moments_activation_overrides[pivotal_moment_id] = activation_trigger_id
        pivotal_moment = self.get_pivotal_moment_inst(pivotal_moment_id)
        if pivotal_moment is None:
            return (False, 'Pivotal Moment is not active')
        return pivotal_moment.switch_activation_triggers(activation_trigger_id)

    def reset_pivotal_moments(self, should_reset_rewards:'bool'=False) -> 'None':
        pivotal_moment_ids_to_reset = []
        for pivotal_moment_inst in self._pivotal_moments.values():
            if not pivotal_moment_inst.reset():
                pass
            else:
                pivotal_moment_ids_to_reset.append(pivotal_moment_inst.guid64)
        for pivotal_moment_id in pivotal_moment_ids_to_reset:
            self._active_pivotal_ids.discard(pivotal_moment_id)
            self._pivotal_moments.pop(pivotal_moment_id, None)
            self._completed_pivotal_moments.discard(pivotal_moment_id)
            if should_reset_rewards:
                self._rewarded_pivotal_moments.discard(pivotal_moment_id)
        self.determine_valid_pivotal_moments()

    def toggle_pivotal_moments(self, value:'bool', killswitch:'bool'=False) -> 'None':
        if killswitch or self._pivotal_moments_enabled == value:
            return
        self._pivotal_moments_enabled = value
        if killswitch:
            pivotal_moment_ids_to_kill = []
            for piv_moment_id in self._active_pivotal_ids:
                piv_moment_inst = self.get_pivotal_moment_inst(piv_moment_id)
                if not piv_moment_inst.can_be_killed:
                    pass
                else:
                    piv_moment_inst.destroy_situation()
                    pivotal_moment_ids_to_kill.append(piv_moment_inst.guid64)
            for pivotal_moment_id in pivotal_moment_ids_to_kill:
                self._pivotal_moments.pop(pivotal_moment_id, None)
                self._active_pivotal_ids.discard(pivotal_moment_id)
        else:
            for pivotal_moment_inst in self._pivotal_moments.values():
                if pivotal_moment_inst.guid64 in self._active_pivotal_ids:
                    pass
                else:
                    pivotal_moment_inst.toggle_enable(value)

    @property
    def pivotal_moments_enabled(self) -> 'bool':
        return self._pivotal_moments_enabled

    def save_options(self, options_proto:'GameplaySaveData_pb2.GameplayOptions') -> 'None':
        options_proto.pivotal_moments_enabled = self._pivotal_moments_enabled

    def load_options(self, options_proto:'GameplaySaveData_pb2.GameplayOptions') -> 'None':
        self.toggle_pivotal_moments(options_proto.pivotal_moments_enabled)

    def set_pivotal_moment_situation_seeds(self, situation_seeds:'List[SituationSeed]') -> 'None':
        self._pivotal_moment_situation_seeds = [seed.get_deserializable_seed_from_serializable_seed() for seed in situation_seeds]

    def add_pivotal_moment_situation_seed(self, seed:'SituationSeed') -> 'None':
        self._pivotal_moment_situation_seeds.append(seed)

    def load_pivotal_moment_situations(self) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        for seed in self._pivotal_moment_situation_seeds:
            if seed.guest_list is None or seed.guest_list.guest_info_count == 0:
                seed._guest_list = seed.situation_type.get_predefined_guest_list()
            situation_manager.create_situation_from_seed(seed)
        for seed in self._account_level_situation_seeds:
            seed._guest_list = seed.situation_type.get_predefined_guest_list()
            situation_manager.create_situation_from_seed(seed)
        self._pivotal_moment_situation_seeds.clear()
        self._account_level_situation_seeds.clear()

    def load_account_level_situations(self) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        is_build_buy_edit_mode = services.current_zone().venue_service.build_buy_edit_mode
        for seed in self._account_level_situation_seeds:
            if not is_build_buy_edit_mode:
                seed._guest_list = seed.situation_type.get_predefined_guest_list()
            situation_id = situation_manager.create_situation_from_seed(seed)
            if situation_id is not None:
                situation = situation_manager.get(situation_id)
                if situation:
                    situation.offer_initial_situation_goals()
        self._account_level_situation_seeds.clear()

    def set_account_level_pivotal_moment_situation_seeds(self, situation_seeds:'List[SituationSeed]') -> 'None':
        self._account_level_situation_seeds = [seed.get_deserializable_seed_from_serializable_seed() for seed in situation_seeds]

    def add_account_level_pivotal_moment_situation_seed(self, seed:'SituationSeed') -> 'None':
        self._account_level_situation_seeds.append(seed)

    def completed_quest_ids(self) -> 'Set[int]':
        return set(itertools.chain(*self._completed_quest_ids.values()))

    def process_incoming_quest_events(self, quests_data:'DistributorOps_pb2.QuestEvent') -> 'None':
        if self._received_live_event_quests:
            return
        self._received_live_event_quests = True
        for quest_instance_data in quests_data.quest_event:
            self._process_quest_data(quest_instance_data.live_event_id, [quest_id for quest_id in quest_instance_data.active_pivmos], [quest_id for quest_id in quest_instance_data.cancelable_ids], [quest_id for quest_id in quest_instance_data.completed_ids])

    def reset_quest_events(self, quests_data:'DistributorOps_pb2.QuestEvent') -> 'None':
        completed_quest_ids = set(itertools.chain(*self._completed_quest_ids.values()))
        self._received_live_event_quests = False
        self._active_quests.clear()
        self._cancelable_quests.clear()
        self._completed_pivotal_moments.difference_update(completed_quest_ids)
        self._completed_quest_ids.clear()
        self._account_level_situation_seeds.clear()
        self.process_incoming_quest_events(quests_data)

    def _get_quest_event_status(self, quests_data:'DistributorOps_pb2.QuestEvent') -> 'Dict[int, bool]':
        quest_event_status = {}
        for quest_instance_data in quests_data.quest_event:
            quest_event_status[quest_instance_data.live_event_id] = quest_instance_data.event_ending
        return quest_event_status

    def _get_next_two_available_quests(self, event_id:'int') -> 'List[int]':
        available_quests = self._active_quests.get(event_id, [])
        return available_quests[:2]

    def reprocess_quest_events(self, quests_data:'DistributorOps_pb2.QuestEvent') -> 'None':
        old_active_event_quest_ids = self._active_quests.copy()
        old_active_event_quests = {}
        for (old_event_id, old_active_quest_ids) in old_active_event_quest_ids.items():
            old_active_event_quests[old_event_id] = set(self.get_pivotal_moment_inst(active_quest_id) for active_quest_id in old_active_quest_ids)
        self.reset_quest_events(quests_data)
        quest_event_status = self._get_quest_event_status(quests_data)
        invalid_quests = {}
        for (old_event_id, old_active_quest_ids_list) in old_active_event_quest_ids.items():
            old_active_quests = old_active_event_quests.get(old_event_id)
            old_active_quest_ids = set(old_active_quest_ids_list)
            next_two_available_quests_ids = set(self._get_next_two_available_quests(old_event_id))
            invalid_quest_ids = old_active_quest_ids.difference(next_two_available_quests_ids)
            invalid_quests[old_event_id] = [old_active_quest for old_active_quest in old_active_quests if old_active_quest.guid64 in invalid_quest_ids]
        self._clear_invalid_quests(invalid_quests, quest_event_status)
        self.process_account_level_data()

    def _process_quest_data(self, event_id:'int', active_quests:'List[int]', cancelable_quests:'List[int]', completed_quests:'List[int]') -> 'None':

        def _add_item_to_quest_dictionary(service_dict, items):
            array = service_dict.get(event_id)
            if array is None:
                array = []
            array.extend(items)
            service_dict[event_id] = array

        self._completed_pivotal_moments |= set(completed_quests)
        _add_item_to_quest_dictionary(self._active_quests, active_quests)
        _add_item_to_quest_dictionary(self._completed_quest_ids, completed_quests)
        _add_item_to_quest_dictionary(self._cancelable_quests, cancelable_quests)

    def debug_activate_quest(self, debug_quest_id:'int') -> 'None':
        return
        quests.append(debug_quest_id)
        self._active_quests.update({event_id: quests})
        self.determine_valid_pivotal_moments()

    def is_pivotal_moment_active_quest(self, pivotal_moment_guid:'int') -> 'bool':
        return pivotal_moment_guid in set(itertools.chain(*self._active_quests.values()))

    def is_quest_situation_cancelable(self, situation_guid:'int') -> 'bool':
        cancelable_quests = self.get_cancelable_quests()
        for quest in cancelable_quests:
            if quest.situation_to_start.guid64 == situation_guid:
                return True
        return False

    def get_cancelable_quests(self) -> 'List[PivotalMoment]':
        cancelable_quest_ids = set(itertools.chain(*self._cancelable_quests.values()))
        return self.get_tuned_pivotal_moments(cancelable_quest_ids)

    def get_active_quests(self) -> 'List[PivotalMoment]':
        active_quest_ids = set(itertools.chain(*self._active_quests.values()))
        return self.get_tuned_pivotal_moments(active_quest_ids)

    def get_live_event_id_for_quest(self, quest_id:'int') -> 'List[int]':
        return [live_event_id for (live_event_id, active_quests) in self._active_quests.items() if quest_id in active_quests]

    def _clear_invalid_quests(self, invalid_quests:'Dict[int, PivotalMoment]', event_ending:'Dict[int, bool]') -> 'None':
        show_error_dialog = False
        for (invalid_quest_event_id, invalid_quests) in invalid_quests.items():
            for invalid_quest in invalid_quests:
                self._active_pivotal_ids.discard(invalid_quest.guid64)
                self._pivotal_moments.pop(invalid_quest.guid64, None)
                if invalid_quest.has_active_situation():
                    show_error_dialog = show_error_dialog or not event_ending.get(invalid_quest_event_id, False)
                    with telemetry_helper.begin_hook(tutorial_service_telemetry_writer, TELEMETRY_GROUP_TUTORIAL_SERVICE) as hook:
                        hook.write_guid(TELEMETRY_FIELD_CANCELLED_QUEST_ID, invalid_quest.guid64)
                invalid_quest.reset(from_error_syncing=True)
        if show_error_dialog:
            resolver = SingleSimResolver(services.active_sim_info())
            dialog = LiveEventQuest.QUEST_CLEARED_DIALOG(None, resolver)
            dialog.show_dialog()

    def save(self, save_slot_data=None, **kwargs) -> 'None':
        if save_slot_data is None:
            return
        tutorial_service_data = save_slot_data.gameplay_data.tutorial_service
        tutorial_service_data.Clear()
        pivotal_moments_data_account = GameplaySaveData_pb2.PivotalMomentsData()
        is_build_buy_edit_mode = services.current_zone().venue_service.build_buy_edit_mode
        for pivotal_moment_inst in self._pivotal_moments.values():
            if pivotal_moment_inst.persist_to_account:
                with ProtocolBufferRollback(pivotal_moments_data_account.pivotal_moments) as pivotal_moment_data:
                    pivotal_moment_inst.save(pivotal_moment_data, is_build_buy_edit_mode=is_build_buy_edit_mode)
            else:
                with ProtocolBufferRollback(tutorial_service_data.pivotal_moments) as pivotal_moment_data:
                    pivotal_moment_inst.save(pivotal_moment_data)
        save_slot_data.gameplay_data.tutorial_service = tutorial_service_data
        user_account_data = DistributorOps_pb2.UserAccountData()
        user_account_data.data_type = UserAccountDataTypeEnum.PIVOTAL_MOMENTS
        user_account_data.data = pivotal_moments_data_account.SerializeToString()
        opSetPivotalMomentsData = distributor.ops.SetAccountDataForCurrentUser(user_account_data)
        Distributor.instance().add_op_with_no_owner(opSetPivotalMomentsData)

    def load(self, **_) -> 'None':
        self._load(self.PIVOTAL_MOMENT_LIST)

    def load_dynamic_moments(self, **_) -> 'None':
        self._load(self._dynamic_pivotal_moments)

    def _load(self, pivotal_moments_list, **_) -> 'None':
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if not save_slot_data_msg.gameplay_data.HasField('tutorial_service'):
            return
        if not save_slot_data_msg.gameplay_data.tutorial_service.pivotal_moments:
            return
        for pivotal_moment_save_data in save_slot_data_msg.gameplay_data.tutorial_service.pivotal_moments:
            for piv_moment in pivotal_moments_list:
                if piv_moment.guid64 == pivotal_moment_save_data.pivotal_moment_id:
                    piv_moment_inst = piv_moment()
                    piv_moment_inst.load(pivotal_moment_save_data, self)
                    self._pivotal_moments[piv_moment.guid64] = piv_moment_inst
                    break
