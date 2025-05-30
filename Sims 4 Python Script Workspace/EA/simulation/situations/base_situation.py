from __future__ import annotationsfrom cas.cas import get_tags_from_outfitfrom sims.outfits import outfit_utilsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from date_and_time import TimeSpan
    from typing import *
    from interactions.base import interaction as Interaction
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from situations.situation_job import SituationJobfrom builtins import propertyimport randomfrom protocolbuffers import Situations_pb2, Loot_pb2from bucks.bucks_utils import BucksUtilsfrom clock import interval_in_sim_minutesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom fame.fame_tuning import FameTunablesfrom interactions.context import QueueInsertStrategy, InteractionContextfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import PriorityExtendedfrom interactions.utils.tunable import SetGoodbyeNotificationElementfrom objects import ALL_HIDDEN_REASONSfrom objects.components import sim_visualizer_componentfrom objects.components.sim_visualizer_enum import SimVisualizerData, SimVisualizerFlagfrom sims.outfits.outfit_enums import OutfitCategory, BodyTypeFlag, OutfitFilterFlagfrom sims.outfits.outfit_generator import OutfitGeneratorfrom sims.sim_info_types import Speciesfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableList, TunableReferencefrom sims4.utils import classpropertyfrom singletons import DEFAULTfrom situations.bouncer.bouncer_client import IBouncerClientfrom situations.bouncer.bouncer_request import BouncerRequest, BouncerFallbackRequestFactory, BouncerHostRequestFactory, RequestSpawningOption, SimReservationRequestfrom situations.bouncer.bouncer_types import BouncerRequestPriorityfrom situations.situation_goal import SituationGoalfrom situations.situation_guest_list import SituationGuestList, SituationInvitationPurpose, SituationGuestInfofrom situations.situation_job_data import SituationJobDatafrom situations.situation_scoring_mixin import SituationScoringMixinfrom situations.situation_serialization import SituationSeed, SeedPurposefrom situations.situation_sim import SituationSimfrom situations.situation_types import JobHolderNoShowAction, JobHolderDiedOrLeftAction, SituationCategoryUid, SituationStage, SituationCallbackOption, ScoringCallbackData, SituationMedal, GreetedStatus, SituationSerializationOption, SituationCommonBlacklistCategory, SituationDisplayType, SituationUserFacingType, SituationDisplayPriority, SituationDisplayFlagsfrom tag import Tagimport build_buyimport distributor.opsimport enumimport gsi_handlersimport id_generatorimport interactions.contextimport servicesimport sims4.logimport stringimport telemetry_helperlogger = sims4.log.Logger('Situations')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_START_SITUATION = 'STOS'TELEMETRY_HOOK_STOP_SITUATION = 'STAS'TELEMETRY_HOOK_SCORE_CHANGE = 'CHSC'TELEMETRY_HOOK_GOAL = 'GOAL'TELEMETRY_HOOK_CANCEL = 'CNCL'TELEMETRY_FIELD_SITUATION_ID = 'stid'TELEMETRY_FIELD_SITUATION_TYPE = 'type'TELEMETRY_FIELD_SITUATION_SCORE = 'stsc'TELEMETRY_FIELD_SITUATION_DELTA_SCORE = 'scor'TELEMETRY_FIELD_SITUATION_GOAL = 'goal'TELEMETRY_FIELD_SITUATION_LOT_ID = 'hlid'TELEMETRY_FIELD_SITUATION_VENUE_TYPE = 'venu'TELEMETRY_FIELD_SITUATION_CANCELED = 'cncl'TELEMETRY_FIELD_SITUATION_ACTIVITY_KEY = 'atid'TELEMETRY_FIELD_SITUATION_PIVOTAL_MOMENT_ID = 'pmid'TELEMETRY_HOOK_START_DATE_HANGOUT_SITUATION = 'DATE'TELEMETRY_FIELD_SITUATION_ACTIVITY_IDS = 'datv'TELEMETRY_FIELD_SITUATION_INSTANCE_ID = 'situ'TELEMETRY_FIELD_SITUATION_LOT_DESCRIPTION_ID = 'dlid'TELEMETRY_FIELD_SITUATION_SCORING = 'gopt'TELEMETRY_FIELD_SITUATION_TARGET_SIM_IDS = 'tsim'TELEMETRY_FIELD_SITUATION_TUNING_ID = 'dtid'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)
class EnsembleOption(enum.Int):
    ONLY_WITHIN_SITUATION = 1
    ADD_TO_ACTIVE_HOUSEHOLD = 2
    ADD_TO_HOST = 3

class _RequestUserData:

    def __init__(self, role_state_type=None):
        self.role_state_type = role_state_type

class BaseSituation(IBouncerClient, SituationScoringMixin):
    PLAYABLE_SIMS_SCORE_MULTIPLIER = TunableCurve(description='Score multiplier based on number of playable Sims in the Situation')
    AUTOMATIC_BRONZE_TRAITS = TunableList(description='\n        An optional collection of traits that, if possessed by the host, will automagically promote the situation to bronze on start.', tunable=TunableReference(description='\n            A trait that if possessed by the host will start a given situation at bronze.', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)))
    CHANGE_TO_SITUATION_OUTFIT = TunableReference(description='\n        The interaction used to cause Sims to spin into their situation outfit.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    SET_JOB_UNIFORM_TEST = TunableTestSet(description='\n        A set of tests that are run to determine whether or not a Sim is\n        allowed to set a job uniform. If these tests pass, Sims will try\n        and set a job uniform based on their situation job tuning.\n        ')

    @classproperty
    def distribution_override(cls):
        return False

    @classproperty
    def main_goal_visibility_test(cls):
        return cls._main_goal_visibility_test

    @classproperty
    def use_spawner_tags_on_travel(cls):
        return False

    constrained_emotional_loot = None

    def __init__(self, seed):
        self.id = seed.situation_id
        self._seed = seed
        self._guest_list = seed.guest_list
        self.initiating_sim_info = services.sim_info_manager().get(self._guest_list.host_sim_id)
        self.requesting_sim_info = self._guest_list.get_filter_requesting_sim_info()
        self.additional_requesting_sim_infos = self._guest_list.get_additional_filter_requesting_sim_infos()
        self._is_invite_only = self._guest_list.invite_only
        self.primitives = ()
        self.manager = services.get_zone_situation_manager()
        self.visible_to_client = False
        self._guid = id_generator.generate_object_id()
        self._stage = SituationStage.NEVER_RUN
        self._jobs = {}
        self._situation_sims = {}
        self._score = seed.score
        self.end_time_stamp = None
        self.scoring_enabled = seed.scoring_enabled
        self._start_time = seed.start_time
        self.save_to_situation_manager = True
        if self.scoring_enabled:
            for job in self.get_tuned_jobs():
                for score_list in job.interaction_scoring:
                    services.get_event_manager().register_tests(self, (score_list.affordance_list,))
            services.get_event_manager().register_single_event(self, TestEvent.ItemCrafted)
        self._main_goal_visibility = self._seed.main_goal_visibility

    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.id)

    def start_situation(self):
        logger.debug('Starting up situation: {}', self)
        host_sim_info = self._guest_list.host_sim_info
        if self.is_user_facing:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_START_SITUATION, sim_info=host_sim_info) as hook:
                hook.write_int(TELEMETRY_FIELD_SITUATION_ID, self.id)
                hook.write_guid(TELEMETRY_FIELD_SITUATION_TYPE, self.guid64)
                lot_description_id = self.lot_description_id
                if lot_description_id is not None:
                    hook.write_int(TELEMETRY_FIELD_SITUATION_LOT_ID, lot_description_id)
                venue_type = self.venue_type
                if venue_type is not None:
                    hook.write_int(TELEMETRY_FIELD_SITUATION_VENUE_TYPE, venue_type)
        if self.activity_selection:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_START_DATE_HANGOUT_SITUATION, sim_info=host_sim_info) as hook:
                hook.write_int(TELEMETRY_FIELD_SITUATION_TUNING_ID, self.guid64)
                hook.write_int(TELEMETRY_FIELD_SITUATION_SCORING, int(self.scoring_enabled))
                situation_activity_ids = self.situation_activity_ids
                if self.scoring_enabled and situation_activity_ids is None:
                    activity_ids_str = '0'
                else:
                    activity_ids_str = '_'.join(str(situation_activity_id) for situation_activity_id in situation_activity_ids)
                hook.write_string(TELEMETRY_FIELD_SITUATION_ACTIVITY_IDS, activity_ids_str)
                hook.write_int(TELEMETRY_FIELD_SITUATION_LOT_DESCRIPTION_ID, self.lot_description_id)
                host_sim_id = self._guest_list.host_sim_id
                target_sim_ids_str = '_'.join(str(target_sim_id) for target_sim_id in self.invited_sim_ids if target_sim_id != host_sim_id)
                hook.write_string(TELEMETRY_FIELD_SITUATION_TARGET_SIM_IDS, target_sim_ids_str)
                hook.write_int(TELEMETRY_FIELD_SITUATION_INSTANCE_ID, self.situation_id)
        self._stage = SituationStage.SETUP
        self._initialize_situation_jobs()
        self._expand_guest_list_based_on_tuning()
        if self.is_user_facing:
            self._verify_role_objects()
        self._issue_requests()
        self._notify_guests_of_request()
        if self._start_time is None:
            self._start_time = services.time_service().sim_now
        self._stage = SituationStage.RUNNING
        self._handle_automatic_bronze_promotion()
        services.get_event_manager().process_events_for_household(test_events.TestEvent.SituationStarted, services.active_household(), situation=self)

    def manage_vehicle(self, vehicle):
        logger.error('vehicle save/load persistence is not supported for this type of situation {}', self)

    def load_situation(self):
        logger.debug('Loading situation:{}', self)
        self._load_situation_issue_requests()
        self._load_situation_states_and_phases()
        self._stage = SituationStage.RUNNING
        return True

    @classmethod
    def should_seed_be_loaded(cls, seed, load_open_street_situation_with_selectable_sim=False):
        if cls.situation_serialization_option == SituationSerializationOption.DONT:
            return False
        if cls.situation_serialization_option == SituationSerializationOption.HOLIDAY or cls.situation_serialization_option == SituationSerializationOption.PIVOTAL_MOMENT or cls.situation_serialization_option == SituationSerializationOption.PIVOTAL_MOMENT_ACCT_LEVEL:
            return False
        zone = services.current_zone()
        if cls.situation_serialization_option == SituationSerializationOption.LOT:
            if not cls.time_jump.should_load(seed):
                logger.debug("Don't load lot situation:{} due to Sim Time passing", seed.situation_type, owner='sscholl')
                return False
            if cls.survives_active_household_change or zone.active_household_changed_between_save_and_load():
                logger.debug("Don't load lot situation:{} due to active_household_change", seed.situation_type, owner='sscholl')
                return False
            if zone.venue_changed_between_save_and_load():
                logger.debug("Don't load lot situation:{} due to venue change", seed.situation_type, owner='sscholl')
                return False
            elif zone.lot_owner_household_changed_between_save_and_load():
                logger.debug("Don't load lot situation:{} due to lot owner household change", seed.situation_type, owner='sscholl')
                return False
            return True
        if zone.time_has_passed_in_world_since_open_street_save():
            logger.debug("Don't load open street situation:{},{} due to open street time passed", seed.situation_type, seed.situation_id, owner='sscholl')
            return False
        active_lot_household = services.current_zone().get_active_lot_owner_household()
        if active_lot_household is not None:
            for sim_info in seed.invited_sim_infos_gen():
                if sim_info.household is active_lot_household:
                    logger.debug("Don't load open street situation:{},{} due to lot owner sim", seed.situation_type, seed.situation_id, owner='sscholl')
                    return False
        if load_open_street_situation_with_selectable_sim:
            return True
        active_household = services.active_household()
        if active_household is not None:
            for sim_info in seed.invited_sim_infos_gen():
                if sim_info.is_selectable:
                    logger.debug("Don't load open street situation:{},{} due to selectable sim", seed.situation_type, seed.situation_id, owner='sscholl')
                    return False
        return True

    @classmethod
    def should_load_after_time_jump(cls, seed):
        logger.error('Situation {} does not handle time jumps. A GPE must address this.', cls)
        return False

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        return True

    def should_time_jump(self):
        return self._seed.allow_time_jump

    def on_time_jump(self):
        pass

    def on_posture_graph_built_during_zone_spin_up(self) -> 'None':
        pass

    def on_hit_their_marks(self):
        for sim in tuple(self.all_sims_in_situation_gen()):
            current_role_state = self.get_current_role_state_instance_for_sim(sim)
            if current_role_state is not None:
                current_role_state.on_hit_their_marks()

    def _load_situation_issue_requests(self):
        self._load_situation_jobs()
        zone = services.current_zone()
        sim_info_manager = services.sim_info_manager()
        if zone.active_household_changed_between_save_and_load():
            still_here = set()
            removed_sim_job_data = None
            for sim_info in sim_info_manager.get_sim_infos_saved_in_zone():
                still_here.add(sim_info.sim_id)
            for guest_info in self._guest_list.get_persisted_sim_guest_infos():
                logger.debug('Sim:{} in guest list for situation:{}', sim_info_manager.get(guest_info.sim_id), self)
                if guest_info.sim_id not in still_here:
                    logger.debug('Sim: {} is not here. Removed from guest list for {}', sim_info_manager.get(guest_info.sim_id), self)
                    self._guest_list.remove_guest_info(guest_info)
                    if self.maintain_sims_consistency:
                        if removed_sim_job_data is None:
                            removed_sim_job_data = {}
                        removed_sim_job_data[guest_info.sim_id] = guest_info.job_type
            if removed_sim_job_data is not None:
                self._expand_guest_list_from_sim_job_data(removed_sim_job_data)
            self._expand_guest_list_based_on_tuning()
            self._seed._spawn_sims_during_zone_spin_up = True
        self._issue_requests()
        self._notify_guests_of_request()

    @classmethod
    def get_current_state_type(cls):
        raise NotImplementedError

    @classmethod
    def get_current_state_id(cls):
        raise NotImplementedError

    def _load_situation_states_and_phases(self):
        pass

    def on_arrived(self):
        pass

    def _destroy(self):
        logger.debug('Destroying situation: {}', self)
        if self.scoring_enabled:
            for job in self.get_tuned_jobs():
                for score_list in job.interaction_scoring:
                    services.get_event_manager().unregister_tests(self, (score_list.affordance_list,))
            services.get_event_manager().unregister_single_event(self, TestEvent.ItemCrafted)
        if self.main_goal_visibility_test is not None:
            services.get_event_manager().unregister(self, self.main_goal_visibility_test.test_events)
        self._stage = SituationStage.DEAD
        self.manager.bouncer.on_situation_destroy(self)
        for sim in tuple(self._situation_sims):
            self._on_remove_sim_from_situation(sim)
        for job_data in self._jobs.values():
            job_data.destroy()
        self._jobs.clear()
        self._situation_sims.clear()
        self._guest_list._destroy()

    def _self_destruct(self):
        if self._stage >= SituationStage.DYING:
            return
        if not self.manager._request_destruction(self):
            return
        self._stage = SituationStage.DYING
        self.manager.destroy_situation_by_id(self.id)

    def on_remove(self):
        logger.debug('on_remove situation: {}', self)
        self._stage = SituationStage.DYING
        if services.current_zone().is_zone_shutting_down == False:
            if self.should_give_rewards:
                level = self.get_level()
                for (sim, situation_sim) in self._situation_sims.items():
                    job_type = situation_sim.current_job_type
                    if not sim.is_selectable:
                        pass
                    if job_type.rewards:
                        rewards = job_type.rewards.get(level, None)
                        if rewards is not None:
                            rewards.apply(sim, self)
                if self.is_user_facing:
                    with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_STOP_SITUATION, sim=self._guest_list.host_sim) as hook:
                        hook.write_int(TELEMETRY_FIELD_SITUATION_ID, self.id)
                        hook.write_int(TELEMETRY_FIELD_SITUATION_SCORE, self._score)
                        hook.write_guid(TELEMETRY_FIELD_SITUATION_TYPE, self.guid64)
                        lot_description_id = self.lot_description_id
                        if lot_description_id is not None:
                            hook.write_int(TELEMETRY_FIELD_SITUATION_LOT_ID, lot_description_id)
                        venue_type = self.venue_type
                        if venue_type is not None:
                            hook.write_int(TELEMETRY_FIELD_SITUATION_VENUE_TYPE, venue_type)
                        hook.write_guid(TELEMETRY_FIELD_SITUATION_PIVOTAL_MOMENT_ID, self.get_pivotal_moment_id())
                if not self.visible_to_client:
                    level_reward = self._get_reward()
                    if level_reward is not None:
                        level_reward.give_reward(self.initiating_sim_info)
                self.run_situation_ended_events()
                data = ScoringCallbackData(self.id, self._score)
                for (sim, situation_sim) in self._situation_sims.items():
                    if sim.is_selectable:
                        data.add_sim_job_score(sim, situation_sim.current_job_type, situation_sim.get_int_total_score())
                self.manager._issue_callback(self.id, SituationCallbackOption.END_OF_SITUATION_SCORING, data)
                level = self.get_level()
                level_data = self.get_level_data(level)
                if level_data.medal == SituationMedal.BRONZE:
                    slam = self.screen_slam_bronze
                elif level_data.medal == SituationMedal.SILVER:
                    slam = self.screen_slam_silver
                elif level_data.medal == SituationMedal.GOLD:
                    slam = self.screen_slam_gold
                else:
                    slam = self.screen_slam_no_medal
                if slam is not None:
                    slam.send_screen_slam_message(services.active_sim_info(), self.display_name, level_data.level_description)
            elif self.always_run_situation_ended_events:
                self.run_situation_ended_events()
        if False and gsi_handlers.situation_handlers.situation_archiver.enabled:
            gsi_handlers.situation_handlers.situation_archiver.archive_event(self, 'DYING', final_event=True)
        self.manager._issue_callback(self.id, SituationCallbackOption.END_OF_SITUATION, None)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=services.active_sim_info())

    def run_situation_ended_events(self):
        for sim in self.all_sims_in_situation_gen():
            services.get_event_manager().process_event(test_events.TestEvent.SituationEnded, sim_info=sim.sim_info, situation=self, custom_keys=self.custom_event_keys)

    def on_added_to_distributor(self):
        for sim in self._situation_sims.keys():
            self.add_situation_sim_joined_message(sim)

    def on_removed_from_distributor(self):
        pass

    def post_remove(self):
        self._destroy()

    @property
    def guest_list(self):
        return self._guest_list

    @classproperty
    def always_elevated_importance(cls):
        return False

    @property
    def is_situation_of_elevated_importance(self):
        return self.always_elevated_importance or self.is_user_facing

    @classproperty
    def has_no_klout(cls):
        return False

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.LOT

    @classproperty
    def supports_multiple_sims(cls):
        return True

    @classproperty
    def survives_active_household_change(cls):
        return False

    @classproperty
    def implies_greeted_status(cls):
        return False

    @classmethod
    def _get_greeted_status(cls):
        if cls._implies_greeted_status == False:
            return GreetedStatus.NOT_APPLICABLE
        return GreetedStatus.GREETED

    @classmethod
    def get_player_greeted_status_from_seed(cls, situation_seed):
        active_household = services.active_household()
        sim_info_manager = services.sim_info_manager()
        if situation_seed.purpose != SeedPurpose.TRAVEL and situation_seed.purpose != SeedPurpose.PERSISTED_TRAVEL:
            sim_infos_of_interest = [sim_info for sim_info in active_household.sim_info_gen() if sim_info not in sim_info_manager.get_traveled_to_zone_sim_infos()]
        else:
            sim_infos_of_interest = list(active_household.sim_info_gen())
        if any(sim_info in situation_seed.invited_sim_infos_gen() for sim_info in sim_infos_of_interest):
            return cls._get_greeted_status()
        return GreetedStatus.NOT_APPLICABLE

    @classmethod
    def get_npc_greeted_status_during_zone_fixup(cls, situation_seed, sim_info):
        if situation_seed.contains_sim(sim_info):
            return cls._get_greeted_status()
        return GreetedStatus.NOT_APPLICABLE

    def _on_make_waiting_player_greeted(self, door_bell_ringing_sim):
        pass

    @classproperty
    def is_unique_situation(cls):
        return False

    @classproperty
    def allow_non_prestige_events(cls):
        return False

    @classproperty
    def sets_welcome_wagon_flag(cls):
        return False

    @classproperty
    def should_have_encouragement_buff(cls):
        return False

    def save_situation(self):
        if self.situation_serialization_option == SituationSerializationOption.DONT:
            return
        seed = self._create_standard_save_seed()
        if seed is None:
            return
        try:
            self._save_custom(seed)
        except Exception:
            logger.exception('Failed to save situation: {}', self)
            raise
        finally:
            seed.finalize_creation_for_save()
        return seed

    def _create_standard_save_seed(self):
        guest_list = SituationGuestList(self._guest_list.invite_only, self._guest_list.host_sim_id, filter_requesting_sim_id=self._guest_list.filter_requesting_sim_id)
        for request in self.manager.bouncer.situation_requests_gen(self):
            guest_info = self._create_guest_info_from_request(request)
            if guest_info is not None:
                guest_list.add_guest_info(guest_info)
        for request in self.manager.bouncer.situation_reservation_requests_gen(self):
            guest_list.add_guest_info(self._create_guest_info_from_reservation_request(request))
        seed = SituationSeed(type(self), SeedPurpose.PERSISTENCE, self.id, guest_list, self.is_user_facing, duration_override=self.get_remaining_time(), zone_id=services.current_zone().id, start_time=self._start_time, scoring_enabled=self.scoring_enabled, main_goal_visiblity=self._main_goal_visibility, linked_sim_id=self.linked_sim_id, guest_attire_color=self.guest_attire_color, guest_attire_style=self.guest_attire_style)
        for (job_type, situation_job_data) in self._jobs.items():
            seed.add_job_data(job_type, situation_job_data.default_role_state_type, situation_job_data.emotional_loot_actions)
        seed.score = self._score
        if self.special_object_definition_id is not None:
            seed.special_object_definition_id = self.special_object_definition_id
            if self.special_object_name is not None:
                seed.special_object_name = self.special_object_name
        return seed

    def _save_custom(self, seed):
        pass

    def handle_event(self, sim_info, event, resolver):
        if self.scoring_enabled:
            if self._main_goal_visibility or self.main_goal_visibility_test is not None and event in self.main_goal_visibility_test.test_events and resolver(self.main_goal_visibility_test):
                self._main_goal_visibility = True
                services.get_event_manager().unregister(self, self.main_goal_visibility_test.test_events)
                goal_tracker = self._get_goal_tracker()
                if goal_tracker is not None:
                    goal_tracker.send_goal_update_to_client()
            if sim_info is None:
                return
            sim = sim_info.get_sim_instance()
            if self._situation_sims.get(sim) is None:
                return
            score = self.get_sim_score_for_action(sim, event, resolver)
            if score != 0:
                self.score_update(score)

    @classmethod
    def get_zone_director_request(cls, host_sim_info=None, zone_id=None):
        return (None, None)

    def _should_apply_job_emotions_and_commodity_changes(self, sim):
        sim_in_no_other_situations = len(self.manager.get_situations_sim_is_in(sim)) == 1
        return sim_in_no_other_situations and (self.manager.sim_being_created is sim and sim.sim_info.is_npc)

    def _get_relationship_bits_to_add_to_sims(self, sim, job_type):
        result = []
        for relationship_data in self.relationship_between_job_members:
            target_job = None
            if job_type == relationship_data.job_x:
                target_job = relationship_data.job_y
            elif job_type == relationship_data.job_y:
                target_job = relationship_data.job_x
            if target_job is not None:
                for target_sim in self.all_sims_in_job_gen(target_job):
                    if target_sim is not sim:
                        for bit in relationship_data.relationship_bits_to_add:
                            result.append((target_sim, bit))
        return result

    def _add_relationship_amongst_job_members(self, sim, job_type):
        sim_id = sim.id
        sim_relationship_tracker = sim.relationship_tracker
        for (target_sim, bit) in self._get_relationship_bits_to_add_to_sims(sim, job_type):
            target_sim_id = target_sim.id
            if not sim_relationship_tracker.has_bit(target_sim_id, bit):
                sim_relationship_tracker.add_relationship_bit(target_sim_id, bit, force_add=True)

    def _remove_relationship_amongst_job_members(self, sim, job_type):
        sim_id = sim.id
        sim_relationship_tracker = sim.relationship_tracker
        for (target_sim, bit) in self._get_relationship_bits_to_add_to_sims(sim, job_type):
            sim_relationship_tracker.remove_relationship_bit(target_sim.id, bit)

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        logger.debug('adding sim {0} to situation: {1}', sim, self)
        if sim in self._situation_sims:
            logger.error('Adding sim {} with job {} to situation{} but the sims is already in the situation.', sim, job_type, self)
            return
        self._situation_sims[sim] = SituationSim(sim)
        self._set_job_for_sim(sim, job_type, role_state_type_override)
        if self._situation_sims.get(sim) is None:
            return
        self._add_situation_buff_to_sim(sim)
        if job_type.ignore_on_creation_restrictions and sim.is_npc or self._should_apply_job_emotions_and_commodity_changes(sim):
            job_data = self._jobs[job_type]
            resolver = sim.get_resolver()
            loot_actions = job_data.emotional_loot_actions
            if loot_actions:
                loot = loot_actions.pick_loot_op()
                if loot is not None:
                    (_, buff_type) = loot.apply_to_resolver(resolver)
                    self._situation_sims[sim].set_emotional_buff_for_gsi(buff_type)
            if job_type.commodities:
                for commodity in job_type.commodities:
                    commodity.apply_to_resolver(resolver)
        self._add_relationship_amongst_job_members(sim, job_type)
        self.add_situation_sim_joined_message(sim)
        ensemble_data = self._ensemble_data
        if ensemble_data is not None:
            ensemble_service = services.ensemble_service()
            if ensemble_data.remove_before_add:
                ensemble_service.remove_sim_from_ensemble(ensemble_data.ensemble_type, sim)
            if ensemble_data.ensemble_option == EnsembleOption.ONLY_WITHIN_SITUATION:
                ensemble_service.create_ensemble(ensemble_data.ensemble_type, list(self.all_sims_in_situation_gen()))
            elif ensemble_data.ensemble_option == EnsembleOption.ADD_TO_ACTIVE_HOUSEHOLD:
                ensemble_sims = services.client_manager().get_first_client().selectable_sims.get_instanced_sims(allow_hidden_flags=ALL_HIDDEN_REASONS)
                ensemble_sims.append(sim)
                ensemble_service.create_ensemble(ensemble_data.ensemble_type, ensemble_sims)
            elif ensemble_data.ensemble_option == EnsembleOption.ADD_TO_HOST:
                if self.initiating_sim_info is not None:
                    host_sim = self.initiating_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                    if host_sim is not None:
                        ensemble_service.create_ensemble(ensemble_data.ensemble_type, (sim, host_sim))
            else:
                logger.error('Trying to add to ensemble with invalid ensemble option {}', ensemble_data.ensemble_option)
        tracker = self._get_goal_tracker()
        if tracker is not None:
            tracker.on_add_sim_to_situation(sim, job_type)

    def _on_remove_sim_from_situation(self, sim):
        logger.debug('removing sim {0} from situation: {1}', sim, self)
        sim_job = self.get_current_job_for_sim(sim)
        if self.is_user_facing or sim_job is not None and sim_job.user_facing_sim_headline_display_override:
            sim.sim_info.sim_headline = None
            self.update_job_headline(sim, self)
        situation_sim = self._situation_sims.pop(sim, None)
        if False and sim_visualizer_component.is_enabled(SimVisualizerFlag.SITUATIONS):
            sim.update_visualizer_for_flag(SimVisualizerFlag.SITUATIONS)
        if situation_sim is not None and services.current_zone().is_zone_shutting_down == False:
            if situation_sim.outfit_priority_handle is not None:
                sim.sim_info.remove_default_outfit_priority(situation_sim.outfit_priority_handle)
            if self._stage != SituationStage.DEAD:
                self._on_sim_removed_from_situation_prematurely(sim, sim_job)
                self.add_situation_sim_left_message(sim)
            self._remove_situation_buff_from_sim(sim, situation_sim)
            self._remove_relationship_amongst_job_members(sim, situation_sim.current_job_type)
            situation_sim.destroy()
        ensemble_data = self._ensemble_data
        if ensemble_data is not None and not ensemble_data.ignore_situation_removal:
            services.ensemble_service().remove_sim_from_ensemble(ensemble_data.ensemble_type, sim)
        tracker = self._get_goal_tracker()
        if tracker is not None:
            tracker.on_remove_sim_from_situation(sim, sim_job)

    def _on_sim_removed_from_situation_prematurely(self, sim, sim_job):
        if self._should_cancel_leave_interaction_on_premature_removal:
            self._cancel_leave_interaction(sim)

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return False

    def _cancel_leave_interaction(self, sim):
        if sim.sim_info.get_sim_instance() is None:
            return
        interaction_set = sim.get_running_and_queued_interactions_by_tag(self.manager.LEAVE_INTERACTION_TAGS)
        for interaction in interaction_set:
            interaction.cancel(FinishingType.SITUATIONS, 'Keep Sim from leaving.')

    def on_sim_reset(self, sim):
        pass

    def _add_situation_buff_to_sim(self, sim):
        if self._buff.buff_type is not None:
            situation_sim = self._situation_sims[sim]
            situation_sim.buff_handle = sim.add_buff(self._buff.buff_type, buff_reason=self._buff.buff_reason)

    def _remove_situation_buff_from_sim(self, sim, situation_sim):
        if sim is not None and situation_sim.buff_handle is not None:
            sim.remove_buff(situation_sim.buff_handle)

    def remove_sim_from_situation(self, sim):
        self.manager.remove_sim_from_situation(sim, self.id)

    def is_sim_in_situation(self, sim):
        if self._situation_sims is None:
            return False
        return sim in self._situation_sims

    def sims_in_situation(self):
        return [sim for sim in self._situation_sims]

    def is_sim_info_in_situation(self, sim_info):
        sim = sim_info.get_sim_instance()
        if sim is None or not self.is_sim_in_situation(sim):
            return False
        return True

    def on_ask_sim_to_leave(self, sim):
        return True

    def on_add_interaction_liability(self, interaction:'Interaction') -> 'None':
        pass

    def on_first_assignment_pass_completed(self):
        self._offer_goals_first_time()

    def on_sim_assigned_to_request(self, sim, request):
        job_type = request.job_type
        role_state_type = request.callback_data.role_state_type
        self._on_add_sim_to_situation(sim, job_type, role_state_type)
        if sim.is_selectable and self.has_offered_goals():
            self.refresh_situation_goals()

    def on_sim_unassigned_from_request(self, sim, request):
        job_type = request.job_type
        if job_type.died_or_left_action == JobHolderDiedOrLeftAction.END_SITUATION:
            self._on_remove_sim_from_situation(sim)
            self._self_destruct()
        elif job_type.died_or_left_action == JobHolderDiedOrLeftAction.REPLACE_THEM:
            self.submit_replace_request(sim, request, job_type)
        else:
            self._on_remove_sim_from_situation(sim)

    def submit_replace_request(self, sim, request, job_type):
        self._on_remove_sim_from_situation(sim)
        new_request = request.clone_for_replace()
        if new_request is not None:
            self.manager.bouncer.submit_request(new_request)

    def on_sim_replaced_in_request(self, old_sim, new_sim, request):
        job_type = request.job_type
        role_state_type = request.callback_data.role_state_type
        self._on_remove_sim_from_situation(old_sim)
        self._on_add_sim_to_situation(new_sim, job_type, role_state_type)

    def on_failed_to_spawn_sim_for_request(self, request):
        job_type = request.job_type
        if job_type.no_show_action == JobHolderNoShowAction.END_SITUATION:
            self._self_destruct()
        elif job_type.no_show_action == JobHolderNoShowAction.REPLACE_THEM:
            new_request = request.clone_for_replace(only_if_explicit=True)
            if new_request is not None:
                self.manager.bouncer.submit_request(new_request)

    def on_tardy_request(self, request):
        job_type = request.job_type
        if job_type.no_show_action == JobHolderNoShowAction.END_SITUATION:
            self._self_destruct()

    def get_situation_goal_info(self):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return
        return tracker.get_goal_info()

    def get_situation_completed_goal_info(self):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return
        return tracker.get_completed_goal_info()

    def _offer_goals_first_time(self):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return
        if tracker.has_offered_goals():
            return
        if self._seed.goal_tracker_seedling is not None:
            if not self._main_goal_visibility:
                resolver = SingleSimResolver(self.initiating_sim_info)
                if resolver(self.main_goal_visibility_test):
                    self._main_goal_visibility = True
                else:
                    services.get_event_manager().register(self, self.main_goal_visibility_test.test_events)
            tracker.load_from_seedling(self._seed.goal_tracker_seedling)
            tracker.autocomplete_goals_on_load(self._seed.zone_id)
        else:
            if self.main_goal_visibility_test is not None:
                resolver = SingleSimResolver(self.initiating_sim_info)
                if not resolver(self.main_goal_visibility_test):
                    self._main_goal_visibility = False
                services.get_event_manager().register(self, self.main_goal_visibility_test.test_events)
            tracker.refresh_goals()

    def refresh_situation_goals(self):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return
        tracker.refresh_goals()

    def has_offered_goals(self):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return False
        return tracker.has_offered_goals()

    def debug_force_complete_by_goal_name(self, goal_name, target_sim=None):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return False
        return tracker.debug_force_complete_by_goal_name(goal_name, target_sim)

    def debug_force_complete_by_goal_id(self, goal_id, target_sim=None):
        tracker = self._get_goal_tracker()
        if tracker is None:
            return False
        return tracker.debug_force_complete_by_goal_id(goal_id, target_sim)

    def _get_goal_tracker(self):
        raise NotImplementedError

    def on_goal_completed(self, goal):
        score = goal.score
        score = self.score_update(score)
        self.send_goal_completed_telemetry(score, goal)

    def send_goal_completed_telemetry(self, score, goal):
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_GOAL) as hook:
            hook.write_int(TELEMETRY_FIELD_SITUATION_ID, self.id)
            hook.write_int(TELEMETRY_FIELD_SITUATION_DELTA_SCORE, score)
            hook.write_guid(TELEMETRY_FIELD_SITUATION_GOAL, goal.guid64)
            hook.write_guid(TELEMETRY_FIELD_SITUATION_TYPE, self.guid64)
            lot_description_id = self.lot_description_id
            if lot_description_id is not None:
                hook.write_int(TELEMETRY_FIELD_SITUATION_LOT_ID, lot_description_id)
            venue_type = self.venue_type
            if venue_type is not None:
                hook.write_int(TELEMETRY_FIELD_SITUATION_VENUE_TYPE, venue_type)
            current_activity_key = self.current_activity_key
            if current_activity_key is not None:
                hook.write_string(TELEMETRY_FIELD_SITUATION_ACTIVITY_KEY, current_activity_key)
            hook.write_guid(TELEMETRY_FIELD_SITUATION_PIVOTAL_MOMENT_ID, self.get_pivotal_moment_id())

    def send_situation_canceled_telemetry(self):
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CANCEL) as hook:
            hook.write_int(TELEMETRY_FIELD_SITUATION_ID, self.id)
            hook.write_guid(TELEMETRY_FIELD_SITUATION_TYPE, self.guid64)
            hook.write_int(TELEMETRY_FIELD_SITUATION_CANCELED, 1)
            hook.write_guid(TELEMETRY_FIELD_SITUATION_PIVOTAL_MOMENT_ID, self.get_pivotal_moment_id())

    def get_situation_goal_actor(self):
        pass

    @classmethod
    def default_job(cls):
        raise NotImplementedError

    @classmethod
    def resident_job(cls):
        raise NotImplementedError

    @classmethod
    def get_prepopulated_job_for_sims(cls, sim, target_sim_id=None):
        pass

    def churn_jobs(self):
        for job_data in self._jobs.values():
            job_data._churn()

    def shift_change_jobs(self):
        for job_data in self._jobs.values():
            job_data._shift_change()

    def _make_late_auto_fill_request(self, job_type):
        request_priority = BouncerRequestPriority.EVENT_AUTO_FILL
        request = BouncerRequest(self, callback_data=_RequestUserData(), job_type=job_type, request_priority=request_priority, user_facing=self.is_user_facing, exclusivity=self.exclusivity, common_blacklist_categories=job_type.get_common_blacklist_categories(), spawning_option=RequestSpawningOption.MUST_SPAWN, accept_looking_for_more_work=job_type.accept_looking_for_more_work)
        self.manager.bouncer.submit_request(request)

    def _initialize_situation_jobs(self):
        pass

    def _load_situation_jobs(self):
        for (job_type, job_data) in self._seed.get_job_data().items():
            self._add_job_type(job_type, job_data.role_state_type, job_data.emotional_loot_actions_type)

    def _add_job_type(self, job_type, default_role_state, emotional_loot_actions=None):
        self._jobs[job_type] = SituationJobData(job_type, default_role_state, self)
        if job_type.emotional_setup:
            job_data = self._jobs[job_type]
            if emotional_loot_actions is None:
                if self.constrained_emotional_loot is not None:
                    for loot in job_type.emotional_setup:
                        if loot.single_sim_loot_actions is self.constrained_emotional_loot:
                            emotional_loot_actions = self.constrained_emotional_loot
                if not emotional_loot_actions:
                    weighted_loots = [(loot.weight, loot.single_sim_loot_actions) for loot in job_type.emotional_setup]
                    emotional_loot_actions = sims4.random.weighted_random_item(weighted_loots)
            job_data.emotional_loot_actions = emotional_loot_actions

    def _set_job_role_state(self, job_type, role_state_type, role_affordance_target=None):
        if job_type in self._jobs:
            self._jobs[job_type].set_default_role_state_type(role_state_type)
        else:
            logger.error('In BaseSituation._set_job_role_state(), situation: {}, job type: {} was not found in self._jobs. If this is from an old/player save on load, this could be from a mod or changed tuning and thus not an error.', self, job_type)
        sim_key = list(self._situation_sims)
        for sim in sim_key:
            situation_sim = self._situation_sims.get(sim, None)
            if situation_sim is not None and situation_sim.current_job_type == job_type:
                self._set_sim_role_state(sim, role_state_type, role_affordance_target)

    def _set_sim_role_state(self, sim, role_state_type, role_affordance_target=None, **kwargs):
        situation_sim = self._situation_sims[sim]
        job_type = situation_sim.current_job_type
        (override_role_state_type, override_target) = self._get_role_state_overrides(sim, job_type, role_state_type, role_affordance_target)
        if override_role_state_type is not None:
            role_state_type = override_role_state_type
        if override_target is not None:
            role_affordance_target = override_target
        affordance_override_kwargs = self._get_role_state_affordance_override_kwargs()
        situation_sim.set_role_state_type(role_state_type, role_affordance_target, situation=self, **affordance_override_kwargs)
        if False and sim_visualizer_component.is_enabled(SimVisualizerFlag.SITUATIONS):
            sim.update_visualizer_for_flag(SimVisualizerFlag.SITUATIONS)
        self._on_set_sim_role_state(sim, job_type, role_state_type, role_affordance_target)

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (None, None)

    def _get_role_state_affordance_override_kwargs(self):
        return {}

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target=None):
        pass

    def _validate_guest_list(self):
        if self._guest_list is None:
            return
        for job in self._guest_list.get_set_of_jobs():
            if self._jobs.get(job) is None:
                logger.warn('guest list job {} is not available in situation: {}', job, self)

    def _expand_guest_list_from_sim_job_data(self, sim_job_dict):
        for (sim_id, job_type) in sim_job_dict.items():
            guest_info = SituationGuestInfo.construct_from_purpose(sim_id, job_type, SituationInvitationPurpose.PREFERRED)
            self._guest_list.add_guest_info(guest_info)

    def _expand_guest_list_based_on_tuning(self):
        host_sim_id = self._guest_list.host_sim_id
        if self.resident_job() is not None and host_sim_id != 0 and self._guest_list.get_guest_info_for_sim_id(host_sim_id) is None:
            guest_info = SituationGuestInfo.construct_from_purpose(host_sim_id, self.resident_job(), SituationInvitationPurpose.HOSTING)
            self._guest_list.add_guest_info(guest_info)
        for job_type in self._jobs:
            num_to_auto_fill = job_type.get_auto_invite() - len(self._guest_list.get_guest_infos_for_job(job_type))
            for _ in range(num_to_auto_fill):
                guest_info = SituationGuestInfo.construct_from_purpose(0, job_type, SituationInvitationPurpose.AUTO_FILL)
                self._guest_list.add_guest_info(guest_info)

    def _create_reservation_request_from_guest_info(self, guest_info):
        request = SimReservationRequest(self, guest_info.sim_id, self.exclusivity, job_type=guest_info.job_type, request_priority=guest_info.request_priority, spawning_option=guest_info.spawning_option, expectation_preference=guest_info.expectation_preference)
        return request

    def _create_guest_info_from_reservation_request(self, request):
        return SituationGuestInfo(request.sim_id, request.job_type, request.spawning_option, request.request_priority, request.expectation_preference, reservation=True)

    def _create_request_from_guest_info(self, guest_info, spawn_point_override=None, location_override=None, reassign_within_situation=False):
        request = BouncerRequest(self, callback_data=_RequestUserData(guest_info.persisted_role_state_type), job_type=guest_info.job_type, request_priority=guest_info.request_priority, user_facing=self.is_user_facing, exclusivity=self.exclusivity, requested_sim_id=guest_info.sim_id, accept_alternate_sim=guest_info.accept_alternate_sim, spawning_option=guest_info.spawning_option, requesting_sim_info=self.requesting_sim_info, expectation_preference=guest_info.expectation_preference, common_blacklist_categories=guest_info.common_blacklist_categories, for_persisted_sim=guest_info.for_persisted_sim, elevated_importance_override=guest_info.elevated_importance_override, accept_looking_for_more_work=guest_info.job_type.accept_looking_for_more_work, specific_spawn_point=spawn_point_override, specific_location=location_override, reassign_within_situation=reassign_within_situation)
        return request

    def _create_guest_info_from_request(self, request):
        guest_info = None
        sim = request.assigned_sim
        if sim is not None:
            guest_info = SituationGuestInfo(sim.id, request.job_type, request.spawning_option, request.request_priority, request.expectation_preference, request.accept_alternate_sim, request.common_blacklist_categories, elevated_importance_override=request.elevated_importance_override)
            guest_info._set_persisted_role_state_type(self.get_current_role_state_for_sim(sim))
        elif request.is_factory == False:
            guest_info = SituationGuestInfo(request.requested_sim_id, request.job_type, request.spawning_option, request.request_priority, request.expectation_preference, request.accept_alternate_sim, request.common_blacklist_categories, elevated_importance_override=request.elevated_importance_override)
        return guest_info

    def _notify_guests_of_request(self):
        if self._guest_list is None:
            return
        sim_info_manager = services.sim_info_manager()
        for guest_info in self._guest_list.guest_info_gen():
            sim_info = sim_info_manager.get(guest_info.sim_id)
            if sim_info is not None:
                sim_info.on_situation_request(self)

    def _issue_requests(self, spawn_point_override=None) -> 'None':
        for guest_info in self._guest_list.guest_info_gen():
            if guest_info.reservation:
                request = self._create_reservation_request_from_guest_info(guest_info)
                self.manager.bouncer.submit_reservation_request(request)
            elif not guest_info.job_type.do_not_spawn:
                request = self._create_request_from_guest_info(guest_info, spawn_point_override=spawn_point_override)
                self.manager.bouncer.submit_request(request)
        host_sim = self._guest_list.host_sim
        if self.resident_job() is not None and host_sim is not None and host_sim.sim_info.lives_here:
            request = BouncerHostRequestFactory(self, callback_data=_RequestUserData(), job_type=self.resident_job(), user_facing=self.is_user_facing, exclusivity=self.exclusivity, requesting_sim_info=self.requesting_sim_info)
            self.manager.bouncer.submit_request(request)
        self._create_uninvited_request()

    def _create_uninvited_request(self):
        if self._is_invite_only or self.default_job() is not None:
            request = BouncerFallbackRequestFactory(self, callback_data=_RequestUserData(), job_type=self.default_job(), user_facing=self.is_user_facing, exclusivity=self.exclusivity)
            self.manager.bouncer.submit_request(request)

    def _fulfill_reservation_guest_info(self, guest_info, location_override=None):
        if not guest_info.reservation:
            logger.error("Attempting to fulfill a reservation request for {} that isn't a reservation request.", self)
            return
        guest_info.reservation = False
        request = self._create_request_from_guest_info(guest_info, location_override=location_override)
        self.manager.bouncer.replace_reservation_request(request)

    def invite_sim_to_job(self, sim, job=DEFAULT, reassign_within_situation=False):
        if job is DEFAULT:
            job = self.default_job()
        if job is None:
            logger.error('Requesting invitation to a None job on a situation ({}).', self, owner='manus')
            return
        guest_info = SituationGuestInfo(sim.id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True)
        request = self._create_request_from_guest_info(guest_info, reassign_within_situation=reassign_within_situation)
        self.manager.bouncer.submit_request(request)

    def _set_job_for_sim(self, sim, job, role_state_type_override=None):
        logger.debug('set JOB[{}] for {} in [{}]', job, sim, self)
        job_data = self._jobs.get(job)
        if job_data is None:
            logger.error('No record of job {} in the situation {}.', job, self, owner='manus')
            return
        if job_data.test_add_sim(sim, self.requesting_sim_info) == False:
            logger.warn("Adding sim {} to job {} for which they don't match the filter {} in situation {}", sim, job, job.filter, self)
        self._situation_sims[sim].current_job_type = job
        self.set_job_uniform(sim, job)
        self._on_set_sim_job(sim, job)
        if role_state_type_override:
            role_state_type = role_state_type_override
        else:
            role_state_type = job_data.default_role_state_type
        self._set_sim_role_state(sim, role_state_type, None)

    def _get_weather_uniform(self, sim):
        if self.manager.sim_being_created is sim or not services.current_zone().is_zone_running:
            weather_service = services.weather_service()
            if weather_service is None:
                return
            else:
                return weather_service.get_weather_outfit_change(SingleSimResolver(sim.sim_info))

    def _check_outfit_validity(self, sim_info:'SimInfo', outfit_extra_tag_set:'Set', outfit_generators:'List', outfit_category:'OutfitCategory', outfit_index:'int') -> 'bool':
        try:
            for generator in outfit_generators:
                if generator.generator.filter_flag & OutfitFilterFlag.MATCH_ALL_TAGS:
                    sim_tags = outfit_utils.get_tags_present_on_all_given_body_types(generator.generator.get_tuned_required_body_types(), sim_info, outfit_category, outfit_index)
                else:
                    sim_tags = get_tags_from_outfit(sim_info._base, outfit_category, outfit_index, body_type_flags_filter=generator.generator.get_body_type_flags())
                combined_required_outfit_tags = outfit_extra_tag_set.union(generator.generator.tags)
                if combined_required_outfit_tags and combined_required_outfit_tags.issubset(sim_tags) and not generator.generator.blocked_tags.issubset(sim_tags):
                    return True
            return False
        except Exception:
            return False

    def _try_find_valid_existing_outfit(self, sim_info:'SimInfo', required_tags:'Set', outfit_generators:'List') -> 'Optional[Tuple[OutfitCategory, int]]':
        if self._seed.is_loadable:
            valid_outfit = self._check_outfit_validity(sim_info, required_tags, outfit_generators, OutfitCategory.SITUATION, 0)
            if valid_outfit:
                return (OutfitCategory.SITUATION, 0)
            return
        preferred_outfit_category = self.get_preferred_outfit_category()
        for (outfit_index, _) in enumerate(sim_info.get_outfits_in_category(preferred_outfit_category)):
            valid_outfit = self._check_outfit_validity(sim_info, required_tags, outfit_generators, preferred_outfit_category, outfit_index)
            if valid_outfit:
                return (preferred_outfit_category, 0)

    def set_job_uniform(self, sim_instance:'Sim', job:'SituationJob', outfit_for_clothing_change:'Optional[Tuple[OutfitCategory, int]]'=None) -> 'None':
        job_uniform = job.job_uniform
        sim_info = sim_instance.sim_info
        resolver = SingleSimResolver(sim_info)
        if not self.SET_JOB_UNIFORM_TEST.run_tests(resolver):
            return
        if job_uniform is None:
            weather_uniform = self._get_weather_uniform(sim_instance)
            if weather_uniform is not None and job.apply_weather_based_uniform:
                sim_info.set_current_outfit(weather_uniform)
                return
            if self.try_apply_trailblazer_outfit(sim_instance, resolver):
                return
            if self.manager.sim_being_created is sim_instance:
                services.get_style_service().try_set_style_outfit(sim_instance, resolver)
            return
        if sim_instance.is_selectable and not job_uniform.playable_sims_change_outfits:
            return
        if job_uniform.zone_custom_outfit:
            zone_director = services.venue_service().get_zone_director()
            if zone_director is not None:
                zone_director.apply_zone_outfit(sim_info, self)
                return
        if job_uniform.use_sold_fashion_outfit:
            fashion_trend_service = services.fashion_trend_service()
            if fashion_trend_service is not None:
                fashion_trend_service.apply_sold_fashion_outfit(target_sim=sim_instance)
                return
        outfit_generators = job_uniform.situation_outfit_generators
        outfit_extra_tag_set = set()
        if self._seed.has_user_defined_outfit:
            outfit_extra_tag_set = self.get_job_outfit_extra_tag_set(job)
        found_outfit = True
        existing_outfit = None
        if self._seed and outfit_generators:
            outfit_generation_allowed = self.permit_outfit_generation(job)
            existing_outfit = self._try_find_valid_existing_outfit(sim_info, outfit_extra_tag_set, outfit_generators)
            if existing_outfit:
                sim_info.generate_merged_outfit(sim_info, (OutfitCategory.SITUATION, 0), existing_outfit, existing_outfit)
            elif outfit_generation_allowed:
                found_outfit = False
                outfit_generators_test = list(outfit_generators)
                tested_outfit_generator = None
                while outfit_generators_test and not found_outfit:
                    tested_outfit_generator = random.choice(outfit_generators_test)
                    if not tested_outfit_generator.tests.run_tests(resolver):
                        outfit_generators_test.remove(tested_outfit_generator)
                    else:
                        found_outfit = True
                if found_outfit:
                    OutfitGenerator.generate_outfit(tested_outfit_generator, sim_info, OutfitCategory.SITUATION, outfit_extra_tag_set=outfit_extra_tag_set, outfit_index=0)
        if not found_outfit:
            return
        outfit_change_reason = self.get_job_outfit_change_reason(job)
        outfit_priority_handle = sim_info.add_default_outfit_priority(None, outfit_change_reason, job_uniform.outfit_change_priority)
        self._situation_sims[sim_instance].outfit_priority_handle = outfit_priority_handle
        if self.manager.sim_being_created is sim_instance or not services.current_zone().is_zone_running:
            if outfit_for_clothing_change is None and existing_outfit is None:
                new_outfit = sim_info.get_outfit_for_clothing_change(None, outfit_change_reason, resolver=resolver)
            else:
                new_outfit = outfit_for_clothing_change or existing_outfit
            sim_info.set_current_outfit(new_outfit)
        else:
            context = InteractionContext(sim_instance, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
            sim_instance.push_super_affordance(job.CHANGE_OUTFIT_INTERACTION, None, context)

    def _on_set_sim_job(self, sim, job):
        if job.goodbye_notification is DEFAULT:
            return
        sim.sim_info.try_to_set_goodbye_notification(job.goodbye_notification)

    def get_current_job_for_sim(self, sim):
        if sim is None:
            return
        situation_sim = self._situation_sims.get(sim)
        if situation_sim is None:
            return
        return situation_sim.current_job_type

    def get_current_role_state_for_sim(self, sim):
        if sim is None:
            return
        situation_sim = self._situation_sims.get(sim)
        if situation_sim is None:
            return
        return situation_sim.current_role_state_type

    def get_current_role_state_instance_for_sim(self, sim):
        if sim is None:
            return
        situation_sim = self._situation_sims.get(sim)
        if situation_sim is None:
            return
        return situation_sim.current_role_state_instance

    def get_role_tags_for_sim(self, sim):
        current_tag_set = set()
        current_job = self.get_current_job_for_sim(sim)
        if current_job is None:
            return current_tag_set
        current_tag_set.update(current_job.tags)
        current_role_state = self.get_current_role_state_for_sim(sim)
        if current_role_state is not None:
            current_tag_set.update(current_role_state.tags)
        return current_tag_set

    def sim_has_job(self, sim, job_type):
        return job_type == self.get_current_job_for_sim(sim)

    @classmethod
    def get_tuned_jobs(cls):
        pass

    def all_jobs_gen(self):
        for job_type in self._jobs.keys():
            yield job_type

    def gsi_all_jobs_data_gen(self):
        for job_data in self._jobs.values():
            yield job_data

    def all_sims_in_situation_gen(self):
        for sim in self._situation_sims:
            yield sim

    def all_sims_in_job_gen(self, job_type):
        for (sim, situation_sim) in self._situation_sims.items():
            if situation_sim.current_job_type is job_type:
                yield sim

    def get_num_sims_in_job(self, job_type=None):
        count = 0
        for (_, situation_sim) in self._situation_sims.items():
            if not job_type is None:
                if situation_sim.current_job_type is job_type:
                    count += 1
            count += 1
        return count

    def get_sims_in_job_for_churn(self, job_type):
        sims = []
        if not self._situation_sims:
            return sims
        for (sim, situation_sim) in tuple(self._situation_sims.items()):
            if situation_sim.current_job_type is job_type and self is self.manager._bouncer.get_most_important_situation_for_sim(sim):
                sims.append(sim)
        return sims

    def get_num_sims_in_job_for_churn(self, job_type):
        return len(self.get_sims_in_job_for_churn(job_type))

    def get_num_sims_in_role_state(self, role_state_type):
        count = 0
        for situation_sim in self._situation_sims.values():
            if situation_sim.current_role_state_type is role_state_type:
                count += 1
        return count

    def _verify_role_objects(self):
        if self._guest_list is None:
            return
        else:
            bullet_points = []
            for job in self._guest_list.get_set_of_jobs():
                for recommended_object_tuning in job.recommended_objects:
                    object_test = recommended_object_tuning.object
                    object_list = object_test()
                    num_objects = len(object_list)
                    if num_objects < recommended_object_tuning.number:
                        bullet_points.append(recommended_object_tuning.object_display_name)
            if bullet_points:
                sim_info = services.sim_info_manager().get(self._guest_list.host_sim_id)
                return self._display_role_objects_notification(sim_info, LocalizationHelperTuning.get_bulleted_list((None,), bullet_points))

    def _display_role_objects_notification(self, sim, bullets):
        raise NotImplementedError

    @classproperty
    def display_name(self):
        raise NotImplementedError

    @property
    def description(self):
        raise NotImplementedError

    @classproperty
    def icon(self):
        raise NotImplementedError

    @property
    def situation_start_time(self):
        return self._start_time

    @property
    def start_audio_sting(self):
        pass

    @property
    def audio_background(self):
        pass

    @property
    def end_audio_sting(self):
        pass

    @classproperty
    def relationship_between_job_members(cls):
        raise NotImplementedError

    @property
    def is_user_facing(self):
        return self._seed.user_facing

    @property
    def situation_id(self):
        return self.id or self._seed.situation_id

    @classproperty
    def supports_automatic_bronze(cls):
        return True

    @property
    def situation_display_priority(self):
        return SituationDisplayPriority.MEDIUM

    @property
    def spawn_sims_during_zone_spin_up(self):
        return self._seed.spawn_sims_during_zone_spin_up

    @property
    def sim(self):
        return self

    @property
    def num_invited_sims(self):
        return len(self._guest_list.get_invited_sim_ids())

    @property
    def invited_sim_ids(self):
        return self._guest_list.get_invited_sim_ids()

    @classproperty
    def _ensemble_data(cls):
        pass

    @property
    def is_traveling_situation(self):
        return self._seed.purpose == SeedPurpose.TRAVEL or self._seed.purpose == SeedPurpose.PERSISTED_TRAVEL

    @property
    def should_preroll_during_zone_spin_up(self):
        return not self.is_traveling_situation

    @property
    def linked_sim_id(self):
        return self._seed.linked_sim_id

    @property
    def special_object_name(self):
        return self._seed.special_object_name

    @property
    def special_object_definition_id(self):
        return self._seed.special_object_definition_id

    @property
    def guest_attire_color(self):
        return self._seed.guest_attire_color

    @property
    def guest_attire_style(self):
        return self._seed.guest_attire_style

    def set_end_time(self, end_time:'TimeSpan') -> 'None':
        time_now = services.time_service().sim_now
        self.end_time_stamp = time_now + end_time

    @property
    def is_running(self):
        return self._stage == SituationStage.RUNNING

    @property
    def zone_modifiers(self):
        return ()

    def permit_outfit_generation(self, job):
        return True

    def get_job_outfit_change_reason(self, job):
        return job.job_uniform.outfit_change_reason

    def get_preferred_outfit_category(self):
        return OutfitCategory.SITUATION

    def guest_attire_selection(self) -> 'Tuple[Optional[Tag], Optional[Tag]]':
        (style_tag, color_tag) = (None, None)
        if self.guest_attire_color != Tag.INVALID:
            color_tag = self.guest_attire_color
        if self.guest_attire_style != Tag.INVALID:
            style_tag = self.guest_attire_style
        return (style_tag, color_tag)

    def get_job_outfit_extra_tag_set(self, job) -> 'Set[Tag]':
        return set(tag for tag in self.guest_attire_selection() if tag is not None)

    def get_phase_state_name_for_gsi(self):
        return 'get_phase_state_name_for_gsi not overridden by a GPE'

    def _get_duration(self) -> 'TimeSpan':
        raise NotImplementedError

    def get_remaining_time(self):
        raise NotImplementedError

    def _get_remaining_time_for_gsi(self):
        raise NotImplementedError

    def _get_remaining_time_in_minutes(self):
        raise NotImplementedError

    def _get_sim_from_guest_list(self, job):
        return next(iter(services.object_manager().get(guest_info.sim_id) for guest_info in self._guest_list.get_guest_infos_for_job(job)), None)

    def _get_sim_info_from_guest_list(self, job):
        return next(iter(services.sim_info_manager().get(guest_info.sim_id) for guest_info in self._guest_list.get_guest_infos_for_job(job)), None)

    def gsi_additional_data(self, gsi_key_name, gsi_value_name):
        gsi_additional_data = []
        for (key, value) in self._gsi_additional_data_gen():
            gsi_additional_data.append({gsi_value_name: value, gsi_key_name: key})
        return gsi_additional_data

    def _gsi_additional_data_gen(self):
        pass

    @property
    def num_of_sims(self):
        return len(self._situation_sims)

    @property
    def creation_source(self):
        return self._seed.creation_source

    @property
    def custom_event_keys(self):
        return [type(self)]

    def get_situation_crafting_object(self):
        pass

    def get_pivotal_moment_id(self) -> 'int':
        return 0

    def on_refresh_completed_goals(self, goal:'SituationGoal') -> 'None':
        pass

    @classproperty
    def allow_user_facing_goals(cls):
        raise NotImplementedError

    @classmethod
    def get_level_data(cls, medal:'SituationMedal'=SituationMedal.TIN):
        raise NotImplementedError

    @classmethod
    def get_level_min_threshold(cls, medal:'SituationMedal'=SituationMedal.TIN):
        raise NotImplementedError

    @classmethod
    def get_level_icon(cls, medal:'SituationMedal'=SituationMedal.TIN):
        raise NotImplementedError

    @classmethod
    def get_possible_zone_ids_for_situation(cls, host_sim_info=None, guest_ids=None):
        raise NotImplementedError

    @classmethod
    def get_extended_guest_list(cls, guest_list=None):
        return guest_list

    def _get_effective_score_for_levels(self, score):
        return score

    @property
    def should_track_score(self):
        return self.scoring_enabled

    @property
    def should_give_rewards(self):
        return self.scoring_enabled

    @property
    def always_run_situation_ended_events(self):
        return False

    @property
    def should_display_score(self):
        return self.scoring_enabled

    @classproperty
    def situation_live_event_id(cls) -> 'int':
        return 0

    @property
    def situation_display_type(self) -> 'int':
        return SituationDisplayType.NORMAL

    @property
    def user_facing_type(self):
        return SituationUserFacingType.SOCIAL_EVENT

    @property
    def current_activity_key(self):
        pass

    @property
    def zone_id(self):
        return services.current_zone_id()

    @property
    def lot_description_id(self):
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(self.zone_id)
        lot_description_id = zone_data.lot_description_id if zone_data is not None else None
        return lot_description_id

    @property
    def venue_type(self):
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_tuning_id = build_buy.get_current_venue(self.zone_id)
        venue_tuning = venue_manager.get(venue_tuning_id)
        venue_type = venue_tuning.venue_type if venue_tuning is not None else None
        return venue_type

    def debug_set_overall_score(self, value):
        self._score = value

    def _get_reward(self):
        medal = self.get_level()
        level_data = self.get_level_data(medal)
        if level_data is not None:
            return level_data.reward
        else:
            return

    def _handle_automatic_bronze_promotion(self):
        if not self.supports_automatic_bronze:
            return
        host_sim_info = self._guest_list.host_sim_info
        if host_sim_info is None:
            return
        bronze_award = self.get_level_data(SituationMedal.BRONZE)
        if bronze_award is None:
            return
        if any(host_sim_info.trait_tracker.has_trait(trait) for trait in self.AUTOMATIC_BRONZE_TRAITS):
            self.score_update(bronze_award.score_delta)

    def on_situation_goal_completed(self, completed_goal:'SituationGoal') -> 'None':
        pass

    def score_update(self, score_delta, should_display_score=None):
        score_delta = self.score_update_internal(self, score_delta, should_display_score)
        if self.should_display_score:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_SCORE_CHANGE) as hook:
                hook.write_int(TELEMETRY_FIELD_SITUATION_ID, self.id)
                hook.write_int(TELEMETRY_FIELD_SITUATION_SCORE, self._score)
                hook.write_guid(TELEMETRY_FIELD_SITUATION_TYPE, self.guid64)
        return score_delta

    def get_sim_total_score(self, sim):
        situation_sim = self._situation_sims.get(sim)
        if situation_sim:
            return situation_sim.get_total_score()
        return 0

    def get_sim_score_for_action(self, sim, event, resolver, **kwargs):
        sim_job = self.get_current_job_for_sim(sim)
        if sim_job:
            return sim_job.get_score(event=event, resolver=resolver, **kwargs)
        return 0

    def get_num_playable_sims(self):
        playable_sims = 0
        for sim in self._situation_sims:
            if sim.is_selectable:
                playable_sims += 1
        return playable_sims

    def get_playable_sim_score_multiplier(self):
        if self.PLAYABLE_SIMS_SCORE_MULTIPLIER is not None:
            return self.PLAYABLE_SIMS_SCORE_MULTIPLIER.get(self.get_num_playable_sims())
        else:
            logger.warn('Invalid Tuning for Playable Sims Score Multiplier: {}', self.PLAYABLE_SIMS_SCORE_MULTIPLIER)
            return 1

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        pass

    @classmethod
    def _can_be_made_without_exceeding_sim_slots_available(cls, sim_slots_available):
        if sim_slots_available is None:
            return True
        expected_num_of_sims = cls.get_sims_expected_to_be_in_situation()
        if expected_num_of_sims is None:
            return False
        return expected_num_of_sims <= sim_slots_available

    @classmethod
    def _can_start_walkby(cls, lot_id:'int'):
        return False

    @classmethod
    def can_start_walkby(cls, lot_id:'int', sim_slots_available):
        return cls._can_be_made_without_exceeding_sim_slots_available(sim_slots_available) and cls._can_start_walkby(lot_id)

    def get_sim_available_for_walkby_flavor(self):
        pass

    def _get_score_for_ui(self):
        return int(round(self._score))

    def get_situation_display_description(self) -> 'Optional[LocalizedString]':
        pass

    def get_tutorial_id(self) -> 'int':
        pass

    def build_situation_start_message(self):
        start_msg = Situations_pb2.SituationStart()
        start_msg.score = self._get_score_for_ui()
        build_icon_info_msg(IconInfoData(icon_resource=self.icon), self.display_name, start_msg.icon_info)
        start_msg.icon_info.desc = self.description
        situation_display_description = self.get_situation_display_description()
        if situation_display_description is not None:
            start_msg.situation_display_description = situation_display_description
        tutorial_id = self.get_tutorial_id()
        if tutorial_id is not None:
            start_msg.tutorial_id = tutorial_id
        if self.end_time_stamp:
            start_msg.end_time = self.end_time_stamp.absolute_ticks()
        start_msg.current_level = self.build_situation_level_update_message()
        for sim in self._situation_sims.keys():
            if not sim.is_selectable:
                pass
            else:
                sim_job = self.get_current_job_for_sim(sim)
                if sim_job is not None:
                    with ProtocolBufferRollback(start_msg.sim_jobs) as job_msg:
                        job_msg.sim_id = sim.id
                        job_msg.name = sim_job.display_name
                        job_msg.desc = sim_job.job_description
        start_msg.start_time = self._start_time.absolute_ticks()
        start_audio_sting = self.start_audio_sting
        if start_audio_sting is not None:
            start_msg.start_audio_sting.type = start_audio_sting.type
            start_msg.start_audio_sting.group = start_audio_sting.group
            start_msg.start_audio_sting.instance = start_audio_sting.instance
        background_audio = self.audio_background
        if background_audio is not None:
            start_msg.background_audio.type = background_audio.type
            start_msg.background_audio.group = background_audio.group
            start_msg.background_audio.instance = background_audio.instance
        start_msg.display_type = self.situation_display_type.value
        start_msg.user_facing_type = self.user_facing_type.value
        start_msg.linked_sim_id = self.linked_sim_id
        start_msg.display_priority = self.situation_display_priority.value
        if not self.suppress_scoring_progress_bar:
            start_msg.situation_display_flags |= SituationDisplayFlags.SHOW_SCORE_BAR
        start_msg.situation_display_flags |= SituationDisplayFlags.SHOW_TIMER
        if self.scoring_enabled and self.scoring_enabled:
            start_msg.situation_display_flags |= SituationDisplayFlags.SHOW_GOALS
            if not self.show_timer_in_scored_situation:
                start_msg.situation_display_flags &= ~SituationDisplayFlags.SHOW_TIMER
            if self.user_facing_type == SituationUserFacingType.CAREER_EVENT or self.user_facing_type == SituationUserFacingType.ACTING_CAREER_EVENT:
                start_msg.situation_display_flags |= SituationDisplayFlags.SHOW_END_TIME
                start_msg.situation_end_time_string = self.situation_end_time_string()
        if self.cancel_tooltip_override is not None:
            start_msg.cancel_tooltip_override = self.cancel_tooltip_override()
        if self.cancelable:
            start_msg.situation_display_flags |= SituationDisplayFlags.SHOW_CANCEL
        start_msg.situation_display_style = self.display_style
        start_msg.allow_non_prestige_events = self.allow_non_prestige_events
        start_msg.from_load = self._seed.is_loadable
        start_msg.live_event_id = self.situation_live_event_id
        start_msg.situation_guid = self.guid64
        logger.debug('Sending SituationStart situation:{} ', self, owner='sscholl')
        return start_msg

    def give_level_rewards(self, end_msg, sim_info=None):
        level_reward = self._get_reward()
        if level_reward is not None:
            if sim_info is None:
                if self.initiating_sim_info is None:
                    logger.error('initiating_sim_info is None. Give level rewards unsuccessful in situation {}.', self)
                    return
                sim_info = self.initiating_sim_info
            if level_reward.reward_description is not None:
                end_msg.icon_info.desc = level_reward.reward_description
            level_reward.give_reward(sim_info)

    def build_situation_end_message(self):
        end_msg = Loot_pb2.SituationEnded()
        build_icon_info_msg(IconInfoData(icon_resource=self.icon), self.display_name, end_msg.icon_info)
        if services.current_zone().is_zone_shutting_down == False:
            household = services.active_household()
            if household is not None:
                household.set_highest_medal_for_situation(type(self).guid64, self.get_level())
            self.give_level_rewards(end_msg)
            for sim in self._situation_sims.keys():
                if not sim.is_selectable:
                    pass
                else:
                    end_msg.sim_ids.append(sim.id)
            end_msg.final_score = int(round(self._score))
            end_msg.final_level = self.build_situation_level_update_message()
            end_audio_sting = self.end_audio_sting
            if end_audio_sting is not None:
                end_msg.audio_sting.type = end_audio_sting.type
                end_msg.audio_sting.group = end_audio_sting.group
                end_msg.audio_sting.instance = end_audio_sting.instance
        return end_msg

    def build_situation_score_update_message(self, delta=0, sim=None):
        return self.build_situation_score_update_message_internal(delta, sim)

    def build_situation_level_update_message(self, delta=0):
        return self.build_situation_level_update_message_internal(delta)

    def get_create_op(self, *args, **kwargs):
        return distributor.ops.SituationStartOp(self, self.build_situation_start_message(), immediate=self.is_user_facing)

    def get_delete_op(self):
        return distributor.ops.SituationEndOp(self.build_situation_end_message())

    def get_create_after_objs(self):
        return ()

    def add_situation_score_update_message(self, msg):
        if self.manager.is_distributed(self):
            op = distributor.ops.SituationScoreUpdateOp(msg)
            Distributor.instance().add_op(self, op)

    def _resolve_sim_job_headline(self, sim, sim_job, removed_situation=None):
        resolver = SingleSimResolver(sim.sim_info)
        old_headline = sim.sim_info.sim_headline
        old_headline_hash = 0 if not old_headline else old_headline.hash
        tokens = sim_job.tooltip_name_text_tokens.get_tokens(resolver)
        new_headline = sim_job.tooltip_name(*tokens)
        highest_priority = PriorityExtended.SubLow
        selected_situation = None if removed_situation is self else self
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            sim_situations = situation_manager.get_situations_sim_is_in(sim)
            for situation in sim_situations:
                other_job = situation.get_current_job_for_sim(sim)
                if not situation is removed_situation:
                    if situation.is_user_facing or situation.manager.is_distributed(situation) or not other_job.user_facing_sim_headline_display_override:
                        pass
                    else:
                        other_tokens = other_job.tooltip_name_text_tokens.get_tokens(resolver)
                        other_headline = other_job.tooltip_name(*other_tokens)
                        if not other_job.tooltip_name_priority >= highest_priority:
                            if other_job.tooltip_name_priority > highest_priority:
                                new_headline = other_headline
                                highest_priority = other_job.tooltip_name_priority
                                tokens = other_tokens
                                selected_situation = situation
                        new_headline = other_headline
                        highest_priority = other_job.tooltip_name_priority
                        tokens = other_tokens
                        selected_situation = situation
        if selected_situation is not None:
            sim.sim_info.sim_headline = new_headline
        if sim.sim_info.species == Species.HORSE:
            sim.update_horse_tooltip_info()
        return tokens

    def update_job_headline(self, sim, removed_situation):
        sim_job = self.get_current_job_for_sim(sim)
        if sim_job is not None:
            self._resolve_sim_job_headline(sim, sim_job, removed_situation)

    def add_situation_sim_joined_message(self, sim):
        sim_job = self.get_current_job_for_sim(sim)
        if sim_job is not None:
            tokens = self._resolve_sim_job_headline(sim, sim_job)
        if self.is_user_facing and self.manager.is_distributed(self):
            msg = Situations_pb2.SituationSimJoined()
            msg.sim_id = sim.id
            if sim_job is not None:
                msg.job_assignment = Situations_pb2.SituationJobAssignment()
                msg.job_assignment.sim_id = sim.id
                msg.job_assignment.name = sim_job.display_name
                msg.job_assignment.desc = sim_job.job_description
                msg.job_assignment.tooltip = sim_job.tooltip_name(*tokens)
                logger.debug('Sending SituationSimJoinedOp situation:{} sim:{} job:{}', self, sim, sim_job, owner='sscholl')
            op = distributor.ops.SituationSimJoinedOp(msg)
            Distributor.instance().add_op(self, op)

    def add_situation_sim_left_message(self, sim):
        if self.is_user_facing:
            msg = Situations_pb2.SituationSimLeft()
            msg.sim_id = sim.id
            op = distributor.ops.SituationSimLeftOp(msg)
            Distributor.instance().add_op(self, op)

    def build_situation_duration_change_op(self):
        msg = Situations_pb2.SituationTimeUpdate()
        msg.end_time = self.end_time_stamp.absolute_ticks()
        return msg

    def add_situation_duration_change_op(self):
        if self.is_user_facing and self.is_running:
            msg = self.build_situation_duration_change_op()
            op = distributor.ops.SituationTimeUpdate(msg)
            Distributor.instance().add_op(self, op)

    def add_situation_callback_response_op(self, msg):
        if self.is_user_facing:
            op = distributor.ops.SituationCallbackResponse(msg)
            Distributor.instance().add_op(self, op)

    def get_active_goals(self):
        goal_tracker = self._get_goal_tracker()
        if goal_tracker is not None:
            goal_infos = goal_tracker.get_goal_info()
            goals = [goal for (goal, _) in goal_infos]
            return goals
        return ()

    def try_apply_trailblazer_outfit(self, sim, resolver):
        if FameTunables.TRAILBLAZER_PERK is None:
            return False
        if not FameTunables.TRAILBLAZER_EFFECT_AVAILABLE_TESTS.run_tests(resolver):
            return False
        sim_info = sim.sim_info
        if sim_info.is_child_or_younger:
            return False
        active_household = services.active_household()
        if active_household is None:
            return False
        for target_sim in active_household.instanced_sims_gen():
            target_sim_info = target_sim.sim_info
            if target_sim_info == sim_info:
                pass
            else:
                bucks_tracker = BucksUtils.get_tracker_for_bucks_type(FameTunables.TRAILBLAZER_PERK.associated_bucks_type, target_sim.id)
                if bucks_tracker is None:
                    pass
                elif target_sim_info.species == sim_info.species and (sim_info.clothing_preference_gender == target_sim_info.clothing_preference_gender and bucks_tracker.is_perk_unlocked(FameTunables.TRAILBLAZER_PERK)) and random.random() <= FameTunables.CHANCE_TO_WEAR_TRAILBLAZER_OUTFIT:
                    number_of_outfits = len(target_sim_info.get_outfits_in_category(OutfitCategory.EVERYDAY))
                    index = random.randrange(number_of_outfits - 1) if number_of_outfits > 1 else 0
                    with target_sim_info.set_temporary_outfit_flags(OutfitCategory.EVERYDAY, index, BodyTypeFlag.CLOTHING_ALL):
                        sim_info.generate_merged_outfit(target_sim_info, (OutfitCategory.SITUATION, 0), sim.sim_info.get_current_outfit(), (OutfitCategory.EVERYDAY, index), preserve_outfit_flags=True)
                    if self.manager.sim_being_created is sim or not services.current_zone().is_zone_running:
                        sim.set_current_outfit((OutfitCategory.SITUATION, 0))
                        return True
                    context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
                    sim.push_super_affordance(self.CHANGE_TO_SITUATION_OUTFIT, None, context)
                    return True
        return False

    def _on_proxy_situation_goal_setup(self, goal):
        logger.error('Situation {} does not support proxy goals.  Please check with your GPE partner why a proxy situation goal is being used and have this function implimented if it is intended.', self)

    def get_visualizer_data_string(self, visualizer_data:'SimVisualizerData') -> 'string':
        return ''
