from __future__ import annotationsimport alarmsimport clockimport date_and_timeimport distributor.opsimport enumimport randomimport servicesimport sims4.logimport telemetry_helperfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.exit_condition_manager import ConditionalActionManagerfrom interactions.utils.tunable_icon import TunableIconfrom protocolbuffers import Situations_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Types, get_protobuff_for_keyfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import OptionalTunable, TunableInterval, TunableReference, HasTunableFactory, AutoFactoryInit, TunableVariant, TunableList, TunableTuple, TunableRange, TunableMappingfrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom sims4.utils import classpropertyfrom situations.situation_guest_list import SituationGuestListfrom situations.situation_serialization import SituationSeedfrom situations.situation_types import SituationSerializationOptionfrom statistics.statistic_conditions import TunableEventBasedCondition, TunableEventTestCondition, TunableTimedEventCondition, TunablePivotalMomentCondition, TunableTimeRangeCondition, TunableLiveEventQuestAvailabilityfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from interactions.utils.exit_condition_manager import ConditionGroup
    from protocolbuffers import GameplaySaveData_pb2, Localization_pb2
    from rewards.reward import Reward
    from sims.sim_info import SimInfo
    from tutorials.tutorial_service import TutorialService
    from typing import *TELEMETRY_GROUP_PIVOTAL_MOMENT = 'PIVM'TELEMETRY_GROUP_PIVOTAL_MOMENT_PHONE_CALL = 'FONE'TELEMETRY_FIELD_PIVOTAL_MOMENT_ID = 'pmid'TELEMETRY_FIELD_TRIGGERING_CONDITION = 'con'TELEMETRY_FIELD_CONDITION_INFO = 'inf'TELEMETRY_FIELD_DIALOG_RESPONSE = 'dres'pivotal_moment_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_PIVOTAL_MOMENT)logger = sims4.log.Logger('PivotalMoment')
class PivotalMomentActivationStatus(enum.Int):
    LISTENING = 0
    PENDING = 1
    SCHEDULED = 2
    ACTIVE = 3
    ON_COOLDOWN = 4
TunablePivotalMomentDisplayMixin = get_display_mixin(has_description=True, use_string_tokens=True, export_modes=ExportModes.All)
class PivotalMoment(TunablePivotalMomentDisplayMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SNIPPET)):

    class _Cooldown(HasTunableFactory, AutoFactoryInit):

        def cancel_situation(self, pivotal_moment_inst:'PivotalMoment') -> 'None':
            pivotal_moment_inst.start_cooldown()

    class _MarkAsComplete(HasTunableFactory, AutoFactoryInit):

        def cancel_situation(self, pivotal_moment_inst:'PivotalMoment') -> 'None':
            pivotal_moment_inst.on_pivotal_moment_complete()

    @classmethod
    def _verify_tuning_callback(cls):
        for (activation_trigger_id, activation_triggers) in cls.activation_triggers.items():
            for condition_group in activation_triggers:
                save_ids_in_use = set()
                for condition in condition_group.conditions:
                    if condition.save_id == 0:
                        logger.error('{} key {} has activation trigger {} with Save Id 0. Every Save Id should be non 0.', cls, activation_trigger_id, condition)
                    elif condition.save_id in save_ids_in_use:
                        logger.error('{} key:{} has activation trigger {} with the same Save Id as another trigger in the same group. All Save Ids within a group should be different', cls, activation_trigger_id, condition)
                    save_ids_in_use.add(condition.save_id)
        if cls.drama_node.pivotal_moment.guid64 != cls.guid64:
            logger.error('The pivotal moment tuned for the drama node in {} should be the same.', cls)
        if cls.situation_to_start.pivotal_moment.guid64 != cls.guid64:
            logger.error('The pivotal moment tuned for the situation in {} should be the same.', cls)
        if cls.situation_to_start.situation_serialization_option not in (SituationSerializationOption.PIVOTAL_MOMENT_ACCT_LEVEL, SituationSerializationOption.PIVOTAL_MOMENT):
            logger.error('{} has a tuned situation ({}) with a serialization option outside of the valid range.', cls, cls.situation_to_start)
        if cls.situation_to_start.situation_serialization_option != SituationSerializationOption.PIVOTAL_MOMENT_ACCT_LEVEL and cls.persist_to_account:
            logger.error('The pivotal moment {} is tuned to be persistable to the account, but its situation {} serialization does not match.', cls, cls.situation_to_start)
        if cls.situation_to_start.situation_serialization_option != SituationSerializationOption.PIVOTAL_MOMENT and not cls.persist_to_account:
            logger.error('The pivotal moment {} is tuned to be persistable to the game, but its situation {} serialization does not match.', cls, cls.situation_to_start)

    INSTANCE_TUNABLES = {'cooldown': OptionalTunable(description='\n            Cool down in seconds before this pivotal moment can be shown again\n            ', tunable=TunableInterval(description='\n                Cooldown amount\n                ', tunable_type=int, default_lower=600, default_upper=600, minimum=0)), 'activation_triggers': TunableMapping(description='\n            Trigger condition that must be satisfied for pivotal moment to be triggered. Key is the id to determine which set of\n            conditions will be used. REQUIRED FOR SAVING/LOADING.\n            ', key_type=TunableRange(description='\n                Unique identifier to determine which sets of conditions to use.\n                ', tunable_type=int, minimum=0, maximum=5, default=1), value_type=TunableList(description='\n            Lists of trigger sets. If any of these groups of conditions is satisfied, then the pivotal moment is triggered.\n            ', tunable=TunableTuple(conditions=TunableList(description='\n                        A list of conditions that all must be satisfied for the\n                        group to be considered satisfied.\n                        ', tunable=TunableVariant(description='\n                            The type of trigger to listen for\n                            ', event_based=TunableEventBasedCondition(description='Event trigger for the pivotal moment', add_save_id=True), event_test_based=TunableEventTestCondition(description='Event with test trigger for the pivotal moment', add_save_id=True, use_test_variant_frag=True), time_based=TunableTimeRangeCondition(description='Time trigger for the pivotal moment', add_save_id=True), timed_event_based=TunableTimedEventCondition(description='Time trigger for the pivotal moment, with an event to reset the timer', add_save_id=True), pivotal_moment=TunablePivotalMomentCondition(description='Trigger when a pivotal moment is completed.', add_save_id=True), live_event_quest=TunableLiveEventQuestAvailability(description='Trigger when a live quest event provides a quest.', add_save_id=True), default='event_based'))))), 'drama_node': TunableReference(description='\n            The drama node to schedule when the conditions for this pivotal moment have been met.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions='PivotalMomentDialogDramaNode'), 'situation_to_start': TunableReference(description='\n            A situation that is available for situation replacement.\n            ', manager=services.get_instance_manager(Types.SITUATION)), 'on_situation_cancel': TunableVariant(description='\n            What should happen if a user cancels the pivotal moment situation\n            ', cooldown=_Cooldown.TunableFactory(), mark_as_complete=_MarkAsComplete.TunableFactory(), default='mark_as_complete'), 'outcome_title_text': TunableLocalizedString(description='\n            The title for the reward screen when the pivotal moment is completed.\n            ', tuning_group=GroupNames.UI), 'outcome_description_text': TunableLocalizedString(description='\n            The description for the reward screen when the pivotal moment is completed.\n            ', tuning_group=GroupNames.UI), 'outcome_next_steps_text': TunableLocalizedString(description='\n            Text in the rewards screen, explaining what they can do after the pivotal moment is completed.\n            ', tuning_group=GroupNames.UI), 'outcome_already_rewarded_text': TunableLocalizedString(description="\n            Text in the rewards screen that replaces 'Outcome Next Steps Text' when the reward has already been given\n            a previous time this pivotal moment was completed.\n            ", tuning_group=GroupNames.UI), 'reward_icons': TunableList(description='\n            List of reward icons associated with the pivotal moment. \n            ', tunable=TunableIcon(description='\n                Resource key for the icon. \n                ', allow_none=True), export_modes=ExportModes.All, tuning_group=GroupNames.UI)}

    def __init__(self, *args, activation_trigger_id:'int'=1, **kwargs):
        super().__init__(*args, **kwargs)
        self._household_id = 0
        self._situation_id = 0
        self._activation_trigger_id = activation_trigger_id
        self._cooldown_alarm_handle = None
        self._activation_status = PivotalMomentActivationStatus.LISTENING
        self._condition_manager = ConditionalActionManager()
        self._drama_node_id = 0
        self._triggering_condition_group = None

    @classproperty
    def persist_to_account(cls) -> 'bool':
        return False

    @classproperty
    def can_be_killed(cls) -> 'bool':
        return True

    @classproperty
    def enabled(cls) -> 'bool':
        tutorial_service = services.get_tutorial_service()
        return tutorial_service.pivotal_moments_enabled

    def has_active_situation(self) -> 'bool':
        if self._situation_id == 0:
            return False
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return False
        return bool(situation_manager.get(self._situation_id))

    def register_activation_trigger(self, saved_trigger_data:'GameplaySaveData_pb2.ActivationTriggerStatus'=None) -> 'None':
        if not self.enabled:
            return
        activation_triggers = self.activation_triggers.get(self._activation_trigger_id, None)
        if activation_triggers is None:
            logger.error('Valid Activation Trigger required for pivotal moment with id: {}', self.guid64)
            return
        self._condition_manager.attach_conditions(self, activation_triggers, self.activation_callback)
        if saved_trigger_data is not None:
            for condition_group in self._condition_manager:
                for condition in condition_group:
                    for saved_trigger in saved_trigger_data:
                        if saved_trigger.trigger_id == condition.save_id and saved_trigger.satisfied:
                            condition._satisfy()
                            break

    def switch_activation_triggers(self, activation_trigger_id) -> 'Tuple[bool, str]':
        if self._activation_status != PivotalMomentActivationStatus.LISTENING:
            return (False, 'Pivotal Moment not listening to events anymore')
        activation_triggers = self.activation_triggers.get(activation_trigger_id, None)
        if activation_triggers is None:
            return (False, 'Activation Trigger does not exist in tuning.')
        self._condition_manager.detach_conditions(self)
        self._activation_trigger_id = activation_trigger_id
        self.register_activation_trigger()
        return (True, None)

    def update_activation_triggers(self) -> 'None':
        for condition_group in self._condition_manager:
            for condition in condition_group:
                if not condition.satisfied:
                    condition.attach_to_owner(self, condition_group._on_condition_satisfied_callback)

    def _activate_pivotal_moment(self, condition_group:'ConditionGroup'=None) -> 'None':
        self._activation_status = PivotalMomentActivationStatus.PENDING
        self._cooldown_alarm_handle = None
        resolver = SingleSimResolver(services.active_sim_info())
        drama_scheduler = services.drama_scheduler_service()
        scheduled_drama_nodes = drama_scheduler.get_scheduled_nodes_by_class(self.drama_node)
        for scheduled_drama_node in scheduled_drama_nodes:
            drama_scheduler.cancel_scheduled_node(scheduled_drama_node.uid)
        self._drama_node_id = drama_scheduler.schedule_node(self.drama_node, resolver)
        if self._drama_node_id is None:
            self.start_cooldown()
        else:
            self._activation_status = PivotalMomentActivationStatus.SCHEDULED
            if condition_group is not None:
                self._triggering_condition_group = condition_group
        self._condition_manager.detach_conditions(self)

    def activation_callback(self, condition_group:'ConditionGroup'=None) -> 'None':
        self._cooldown_alarm_handle = None
        if not self.enabled:
            return
        self._activate_pivotal_moment(condition_group)

    def can_situation_start(self) -> 'bool':
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            return False
        if services.get_active_sim() is None:
            return False
        return tutorial_service.can_new_pivotal_moment_start()

    def start_situation(self) -> 'None':
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            return
        if not self.can_situation_start():
            self.start_cooldown()
            return
        self._activation_status = PivotalMomentActivationStatus.ACTIVE
        self._household_id = services.active_household_id()
        situation_manager = services.get_zone_situation_manager()
        guest_list = self.situation_to_start.get_predefined_guest_list()
        if guest_list.guest_info_count == 0:
            sim = services.get_active_sim()
            guest_list = SituationGuestList(invite_only=False, host_sim_id=sim.id)
        self._situation_id = situation_manager.create_situation(self.situation_to_start, guest_list)
        tutorial_service.on_pivotal_moment_active(self.guid64)

    def destroy_situation(self):
        situation_manager = services.get_zone_situation_manager()
        situation_manager.destroy_situation_by_id(self._situation_id)

    def on_situation_canceled(self) -> 'None':
        self.on_situation_cancel().cancel_situation(self)

    def start_cooldown(self, remaining_ticks:'int'=0) -> 'None':
        if self.cooldown is None:
            return
        self._activation_status = PivotalMomentActivationStatus.ON_COOLDOWN
        if self._cooldown_alarm_handle:
            alarms.cancel_alarm(self._cooldown_alarm_handle)
        if remaining_ticks > 0:
            time_span = date_and_time.TimeSpan(remaining_ticks)
        else:
            interval = random.uniform(self.cooldown.lower_bound, self.cooldown.upper_bound)
            time_span = clock.interval_in_sim_seconds(interval)
        self._cooldown_alarm_handle = alarms.add_alarm(self, time_span, lambda _: self.activation_callback(), cross_zone=True)

    def on_pivotal_moment_complete(self, rewarded:'bool'=False) -> 'None':
        if self._cooldown_alarm_handle:
            alarms.cancel_alarm(self._cooldown_alarm_handle)
            self._cooldown_alarm_handle = None
        services.get_event_manager().process_event(TestEvent.PivotalMomentCompleted, pivotal_moment=self.guid64)
        if not self.persist_to_account:
            op = distributor.ops.PivotalMomentCompleted(self.guid64, rewarded)
            Distributor.instance().add_op_with_no_owner(op)
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None:
            tutorial_service.on_pivotal_moment_complete(self.guid64, rewarded)

    def on_pivotal_moment_goal_complete(self, completed_goal_id:'int') -> 'None':
        pass

    def show_outcome_dialog(self, situation_name:'Localization_pb2.LocalizedString', reward:'Reward', rewarded:'bool', situation_display_style:'int') -> 'None':
        outcome_info = Situations_pb2.SituationOutcomeData()
        outcome_info.situation_name = situation_name
        outcome_info.outcome_title = self.outcome_title_text
        outcome_info.outcome_description = self.outcome_description_text
        outcome_info.next_steps_description = self.outcome_already_rewarded_text if rewarded else self.outcome_next_steps_text
        outcome_info.reward_1_icon = get_protobuff_for_key(reward.icon)
        outcome_info.reward_1_name = reward.name
        outcome_info.reward_1_tooltip = reward.reward_description
        outcome_info.situation_display_style = situation_display_style
        outcome_distributor_op = GenericProtocolBufferOp(Operation.SITUATION_SHOW_OUTCOME, outcome_info)
        Distributor.instance().add_op(services.active_sim_info(), outcome_distributor_op)

    def reset(self, from_error_syncing=False) -> 'bool':
        self._condition_manager.detach_conditions(self)
        if self._situation_id != 0:
            self.destroy_situation()
        if self._drama_node_id != 0:
            services.drama_scheduler_service().cancel_scheduled_node(self._drama_node_id)
        if self._cooldown_alarm_handle:
            alarms.cancel_alarm(self._cooldown_alarm_handle)
            self._cooldown_alarm_handle = None
        return True

    def toggle_enable(self, enable:'bool') -> 'None':
        if enable:
            if self._activation_status == PivotalMomentActivationStatus.LISTENING:
                self.register_activation_trigger()
            elif self._activation_status == PivotalMomentActivationStatus.SCHEDULED:
                self.activation_callback()
            elif self._activation_status == PivotalMomentActivationStatus.ON_COOLDOWN:
                self.start_cooldown()
        elif self._activation_status == PivotalMomentActivationStatus.LISTENING:
            self._condition_manager.detach_conditions(self)
        elif self._activation_status == PivotalMomentActivationStatus.SCHEDULED:
            services.drama_scheduler_service().cancel_scheduled_node(self._drama_node_id)
        elif self._cooldown_alarm_handle:
            alarms.cancel_alarm(self._cooldown_alarm_handle)
            self._cooldown_alarm_handle = None

    def send_dialog_telemetry(self, sim_info:'SimInfo', dialog_response:'int') -> 'None':
        if self._triggering_condition_group is None:
            return
        with telemetry_helper.begin_hook(pivotal_moment_telemetry_writer, TELEMETRY_GROUP_PIVOTAL_MOMENT_PHONE_CALL, sim_info=sim_info) as hook:
            hook.write_guid(TELEMETRY_FIELD_PIVOTAL_MOMENT_ID, self.guid64)
            condition_index = 0
            for condition in self._triggering_condition_group:
                hook.write_int(TELEMETRY_FIELD_TRIGGERING_CONDITION + str(condition_index), condition.telemetry_triggering_condition)
                condition.write_telemetry_data(hook, TELEMETRY_FIELD_CONDITION_INFO + str(condition_index))
                condition_index += 1
            hook.write_int(TELEMETRY_FIELD_DIALOG_RESPONSE, dialog_response)
        self._triggering_condition_group = None

    def save(self, pivotal_moment_data:'GameplaySaveData_pb2.PivotalMoment', is_build_buy_edit_mode:'bool'=False) -> 'None':
        pivotal_moment_data.pivotal_moment_id = self.guid64
        if self._household_id != 0:
            pivotal_moment_data.household_id = self._household_id
        if self._cooldown_alarm_handle is not None:
            now_ticks = services.game_clock_service().now().absolute_ticks()
            alarm_ticks = self._cooldown_alarm_handle.finishing_time.absolute_ticks()
            pivotal_moment_data.remaining_ticks = alarm_ticks - now_ticks
        if self._situation_id != 0:
            situation_manager = services.get_zone_situation_manager()
            if situation_manager is not None:
                situation = situation_manager.get(self._situation_id)
                if situation is not None:
                    if is_build_buy_edit_mode:
                        situation._seed.serialize_to_proto(pivotal_moment_data.situation_seed)
                    else:
                        seed = situation.save_situation()
                        seed.serialize_to_proto(pivotal_moment_data.situation_seed)
        pivotal_moment_data.activation_status = self._activation_status
        try:
            pivotal_moment_data.activation_trigger_id = self._activation_trigger_id
        except:
            pass
        for condition_group in self._condition_manager:
            for condition in condition_group:
                with ProtocolBufferRollback(pivotal_moment_data.triggers) as trigger_data:
                    trigger_data.trigger_id = condition.save_id
                    trigger_data.satisfied = condition.satisfied

    def should_load(self) -> 'bool':
        return True

    def load(self, pivotal_moment_data:'GameplaySaveData_pb2.PivotalMoment', tutorial_service:'TutorialService') -> 'None':
        self._household_id = pivotal_moment_data.household_id
        self._activation_status = PivotalMomentActivationStatus(pivotal_moment_data.activation_status)
        if pivotal_moment_data.remaining_ticks > 0:
            self.start_cooldown(pivotal_moment_data.remaining_ticks)
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        if snippet_manager is None:
            logger.error('Unable to load pivotal moments before the snippet_manager is instantiated.')
            return
        force_activation_trigger_registration = False
        deserialized_seed = SituationSeed.deserialize_from_proto(pivotal_moment_data.situation_seed)
        if tutorial_service is not None:
            if deserialized_seed is not None:
                self._situation_id = deserialized_seed.situation_id
                if self.persist_to_account:
                    tutorial_service.add_account_level_pivotal_moment_situation_seed(deserialized_seed)
                else:
                    tutorial_service.add_pivotal_moment_situation_seed(deserialized_seed)
                tutorial_service.on_pivotal_moment_active(self.guid64)
            elif not tutorial_service.is_pivotal_moment_completed(self.guid64):
                force_activation_trigger_registration = True
        try:
            if pivotal_moment_data.HasField('activation_trigger_id'):
                self._activation_trigger_id = pivotal_moment_data.activation_trigger_id
        except:
            self._activation_trigger_id = 1
        if pivotal_moment_data.activation_status == PivotalMomentActivationStatus.LISTENING or force_activation_trigger_registration:
            self.register_activation_trigger(pivotal_moment_data.triggers)
        elif pivotal_moment_data.activation_status == PivotalMomentActivationStatus.PENDING or pivotal_moment_data.activation_status == PivotalMomentActivationStatus.SCHEDULED:
            self.activation_callback()
