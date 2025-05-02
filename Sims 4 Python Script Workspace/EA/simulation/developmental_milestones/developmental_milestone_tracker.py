import enumimport game_servicesimport servicesimport sims4import telemetry_helperimport uidfrom build_buy import get_object_catalog_namefrom collections import defaultdictfrom developmental_milestones.developmental_milestone import DevelopmentalMilestonefrom developmental_milestones.developmental_milestone_enums import DevelopmentalMilestoneStates, MilestoneDataClassfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom element_utils import build_elementfrom event_testing.resolver import SingleSimResolver, DataResolverfrom event_testing.test_events import TestEventfrom interactions.utils.death import DeathTrackerfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom protocolbuffers import GameplaySaveData_pb2, Localization_pb2, Sims_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.common import Packfrom sims4.utils import classpropertyfrom situations.situation_serialization import GoalSeedlingfrom zone_types import ZoneStateTELEMETRY_GROUP_MILESTONES = 'MILE'TELEMETRY_HOOK_MILESTONE_START = 'STRT'TELEMETRY_HOOK_MILESTONE_END = 'ENDD'TELEMETRY_FIELD_MILESTONE_ID = 'mile'TELEMETRY_FIELD_MILESTONE_CONTEXT = 'ctxt'milestones_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_MILESTONES)logger = sims4.log.Logger('DevelopmentalMilestones', default_owner='shipark')
class MilestoneTelemetryContext(enum.Int, export=False):
    NONE = 0
    NEW_SIM = 1
    GOAL = 2
    LOOT = 3
    AGE_UP = 4
    LOD_UP = 5
    CHEAT = 6
    REPEAT = 7

class PreviousGoalData:

    def __init__(self, goal, new_in_ui, age_completed):
        self.goal = goal
        self.age_completed = age_completed
        self.new_in_ui = new_in_ui

class DevelopmentalMilestoneData:

    def __init__(self):
        self.milestone = None
        self.state = DevelopmentalMilestoneStates.ACTIVE
        self.age_completed = None
        self.new_in_ui = False
        self.goal = None
        self._previous_goals = {}

    @property
    def previous_goals(self):
        return self._previous_goals

    def add_previous_goal_entry(self, goal_id, previous_goal_data):
        self._previous_goals[goal_id] = previous_goal_data

    def store_previous_data(self):
        if self.goal is None:
            logger.error('Attemping to store previous goal data from repeatable milestone {}, but no goal exists.', self.milestone)
            return
        previous_data = PreviousGoalData(self.goal, self.new_in_ui, self.age_completed)
        self.add_previous_goal_entry(self.goal.id, previous_data)

    def mark_as_viewed_in_ui(self, goal_id=None):
        if goal_id is None:
            self.new_in_ui = False
            return
        if goal_id == self.goal.id:
            self.new_in_ui = False
            return
        previous_goal_data = self._previous_goals.get(goal_id, None)
        if previous_goal_data is None:
            logger.error('Attempting to mark milestone {} as seen, but the goal id is not tracked in any iteration of the milestone.', self.milestone)
            return
        previous_goal_data.new_in_ui = False

    def get_unlock_function(self, sim_info):
        developmental_milestone_tracker = sim_info.developmental_milestone_tracker
        if developmental_milestone_tracker is None:
            logger.error('Attempting to unlock a milestone on a sim {} without a developmental milestone tracker.', sim_info)
            return
        return developmental_milestone_tracker.unlock_milestone

    def __repr__(self):
        return 'DevelopmentalMilestoneData(Milestone: {}, State: {}, Goal: {}'.format(self.milestone, self.state, self.goal)

class HadChildDevelopmentalMilestoneData(DevelopmentalMilestoneData):

    def __init__(self):
        super().__init__()
        self._sim_info = None
        self._offspring_infos = []
        self._evaluation_counter = 0
        self._pregnancy_unlock_queued = False
        self.milestone = None

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.OffspringCreated:
            offspring_infos = resolver.event_kwargs.get('offspring_infos')
            if not offspring_infos:
                logger.error('Attempting to unlock a birth milestone for sim {} but the offspring kwarg is not                              provided.', self._sim_info)
                return
            self._offspring_infos = offspring_infos
            self._evaluation_counter = len(offspring_infos)
            self._run_pregnancy_evaluations()

    def _run_pregnancy_evaluations(self):
        self.pregnancy_unlock_queued = True
        developmental_milestone_tracker = self._sim_info.developmental_milestone_tracker
        if developmental_milestone_tracker is None:
            logger.error('Attempting to unlock a milestone on a sim {} without a developmental milestone tracker.', self._sim_info)
            return
        for offspring_info in self._offspring_infos:
            developmental_milestone_tracker.add_milestone_evaluation(self.milestone, self._sim_info, offspring_info.id)
        developmental_milestone_tracker.process_evaluation(self.milestone)

    def _setup_unlock(self, milestone, telemetry_context, **kwargs):
        if self._pregnancy_unlock_queued:
            return
        self.milestone = milestone
        self._pregnancy_unlock_queued = True
        services.get_event_manager().register_single_event(self, TestEvent.OffspringCreated)

    def get_unlock_function(self, sim_info):
        if not services.current_zone().have_households_and_sim_infos_loaded:
            return super().get_unlock_function(sim_info)
        self._sim_info = sim_info
        if self._evaluation_counter == 0:
            return self._setup_unlock
        self._evaluation_counter -= 1
        return super().get_unlock_function(sim_info)

class _ReevaluationAction:

    def __init__(self, milestone, subject_sim, target_sim_id):
        self.milestone = milestone
        self.subject_sim = subject_sim
        self.target_sim_id = target_sim_id

class DevelopmentalMilestoneTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._goal_id_generator = uid.UniqueIdGenerator(1)
        self._active_milestones_data = {}
        self._archived_milestones_data = {}
        self._active_goal_map = {}
        self._developmental_milestone_proto = None
        self._initial_loot_applied = False
        self._milestone_evaluations = defaultdict(list)
        self._setup_delayed_goals = False

    @classproperty
    def required_packs(cls):
        return (Pack.EP13,)

    def start_milestone_tracker(self):
        if self._sim_info.is_npc:
            return
        is_instanced = self._sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        zone_is_running = services.current_zone().is_zone_running
        if self._setup_delayed_goals:
            self.setup_goals()
        self._activate_available_milestones(telemetry_context=MilestoneTelemetryContext.NEW_SIM, activate_goals=is_instanced)
        if self._initial_loot_applied or is_instanced:
            if zone_is_running:
                self._apply_retroactive_milestones_from_gameplay()
            else:
                self._apply_initial_loot()
                services.current_zone().register_callback(ZoneState.RUNNING, self._shutdown_retroactive_only_milestones)
        if not zone_is_running:
            services.current_zone().register_callback(ZoneState.RUNNING, self.send_all_milestones_update_to_client)

    def clean_up(self):
        self._active_milestones_data.clear()
        self._archived_milestones_data.clear()
        self._active_goal_map.clear()
        self._milestone_evaluations.clear()

    def add_milestone_evaluation(self, milestone, subject_sim, target_sim_id):
        reevaluation_action = _ReevaluationAction(milestone, subject_sim, target_sim_id)
        if milestone in self._milestone_evaluations:
            self._milestone_evaluations[milestone].append(reevaluation_action)
        else:
            self._milestone_evaluations[milestone] = [reevaluation_action]

    def process_evaluation(self, milestone):
        if len(self._milestone_evaluations) == 0 or milestone not in self._milestone_evaluations:
            if self._initial_loot_applied:
                self.send_all_milestones_update_to_client()
            return
        action = self._milestone_evaluations[milestone].pop(0)
        goal = self.get_active_milestone_goal(action.milestone)
        if goal is None:
            self._milestone_evaluations[milestone].append(action)
            logger.info('{} for {} is not in the ACTIVE state.', action.milestone, action.subject_sim)
            return
        resolver = DataResolver(sim_info=action.subject_sim, event_kwargs={'target_sim_id': action.target_sim_id, 'bypass_pretest': True})
        goal.reevaluate_goal_completion(resolver=resolver)
        if len(self._milestone_evaluations[milestone]) == 0:
            del self._milestone_evaluations[milestone]

    @property
    def active_milestones(self):
        return self._active_milestones_data.values()

    def is_milestone_valid_for_sim(self, milestone):
        if self._sim_info.age not in milestone.ages:
            return False
        return True

    def is_milestone_available(self, milestone, allow_retroactive_only=False):
        if self.is_milestone_valid_for_sim(milestone) and milestone.retroactive_only and self._initial_loot_applied:
            return False
        if milestone.retroactive_only and not allow_retroactive_only:
            return False
        if milestone.prerequisite_milestones:
            for prerequisite_milestone in milestone.prerequisite_milestones:
                if not self.is_milestone_unlocked(prerequisite_milestone):
                    return False
        return True

    def get_milestone_state(self, milestone):
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is None:
            milestone_data = self._archived_milestones_data.get(milestone)
        if milestone_data is None:
            return DevelopmentalMilestoneStates.LOCKED
        return milestone_data.state

    def is_milestone_locked(self, milestone):
        return self.get_milestone_state(milestone) == DevelopmentalMilestoneStates.LOCKED

    def is_milestone_active(self, milestone):
        return self.get_milestone_state(milestone) == DevelopmentalMilestoneStates.ACTIVE

    def is_milestone_unlocked(self, milestone):
        return self.get_milestone_state(milestone) == DevelopmentalMilestoneStates.UNLOCKED

    def is_milestone_tracked(self, milestone):
        milestone_data = self._active_milestones_data.get(milestone)
        return milestone_data is not None

    def get_active_milestone_goal(self, milestone):
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is not None and milestone_data.state == DevelopmentalMilestoneStates.ACTIVE:
            return milestone_data.goal

    def get_milestone_goals(self, milestone, milestone_state=DevelopmentalMilestoneStates.UNLOCKED):
        milestone_data = self._active_milestones_data.get(milestone)
        goals = []
        if milestone_data is None:
            return goals
        if milestone.repeatable:
            for (_, previous_data) in milestone_data.previous_goals.items():
                goals.append(previous_data.goal)
        if milestone_data.state == milestone_state:
            goals.append(milestone_data.goal)
        return goals

    def any_previous_goal_completed(self, milestone):
        if not milestone.repeatable:
            return False
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is None:
            return False
        return len(milestone_data.previous_goals) > 0

    def is_milestone_visible(self, milestone, resolver):
        if self.is_milestone_unlocked(milestone):
            return True
        if milestone.is_primary_milestone is not None and milestone.is_primary_milestone.tests.run_tests(resolver):
            return True
        elif self.any_previous_goal_completed(milestone):
            return True
        return False

    def is_milestone_completed(self, milestone_data):
        if milestone_data.milestone.repeatable:
            return len(milestone_data.previous_goals) > 0
        return milestone_data.state == DevelopmentalMilestoneStates.UNLOCKED

    def get_all_completed_milestones(self):
        completed_milestones = [milestone for (milestone, milestone_data) in self._active_milestones_data.items() if self.is_milestone_completed(milestone_data)]
        completed_milestones.extend(self._archived_milestones_data)
        return completed_milestones

    def create_milestone(self, milestone, send_ui_update=False):
        milestone_data = self._get_data_class(milestone)()
        milestone_data.milestone = milestone
        milestone_data.state = DevelopmentalMilestoneStates.LOCKED
        milestone_data.new_in_ui = True
        milestone_data.goal = None
        if self.is_milestone_valid_for_sim(milestone):
            self._active_milestones_data[milestone] = milestone_data
        else:
            self._archived_milestones_data[milestone] = milestone_data
        if send_ui_update:
            self.try_send_milestone_update_to_client(milestone_data)
        return milestone_data

    def activate_milestone(self, milestone, telemetry_context, from_repeat=False, send_ui_update=True, activate_goals=True):
        if not self.is_milestone_valid_for_sim(milestone):
            logger.error('activate_milestone() called for milestone {}, which is not valid for sim {}.', milestone, self._sim_info)
            return
        if self._sim_info.lod == SimInfoLODLevel.MINIMUM:
            logger.info('Can not activate milestone {} for MIN LOD sim {}.', milestone, self._sim_info)
            return
        if milestone.retroactive_only and self._initial_loot_applied and milestone not in self._milestone_evaluations:
            return
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is None:
            milestone_data = self.create_milestone(milestone)
        milestone_data.state = DevelopmentalMilestoneStates.ACTIVE
        if from_repeat:
            milestone_data.store_previous_data()
            milestone_data.age_completed = None
            milestone_data.new_in_ui = True
        commodity_to_add = milestone.commodity
        if commodity_to_add is not None:
            self._sim_info.commodity_tracker.add_statistic(commodity_to_add)
        if milestone.goal is not None:
            goal = milestone.goal(sim_info=self._sim_info, goal_id=self._goal_id_generator())
            milestone_data.goal = goal
            self._active_goal_map[goal] = milestone
            if activate_goals:
                goal.setup()
                goal.on_goal_offered()
                goal.register_for_on_goal_completed_callback(self.on_goal_completed)
        if send_ui_update:
            self.try_send_milestone_update_to_client(milestone_data)
            for previous_goal_data in milestone_data.previous_goals.values():
                self.try_send_milestone_update_to_client(milestone_data, previous_goal_data.goal.id)
        if telemetry_context is not MilestoneTelemetryContext.NONE:
            with telemetry_helper.begin_hook(milestones_telemetry_writer, TELEMETRY_HOOK_MILESTONE_START, sim_info=self._sim_info) as hook:
                hook.write_guid(TELEMETRY_FIELD_MILESTONE_ID, milestone.guid64)
                hook.write_int(TELEMETRY_FIELD_MILESTONE_CONTEXT, telemetry_context)
        logger.info('activate_milestone(): milestone {} activated.', milestone)
        if milestone.repeatable:
            self.process_evaluation(milestone)

    def unlock_milestone(self, milestone, telemetry_context, send_ui_update=True):
        if not self.is_milestone_valid_for_sim(milestone):
            logger.error('unlock_milestone() called for milestone {}, which is not valid for sim {}.', milestone, self._sim_info)
            return
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is None:
            logger.error('unlock_milestone() called for milestone {}, which does not have milestone_data.', milestone)
            return
        if milestone_data == DevelopmentalMilestoneStates.UNLOCKED:
            logger.error('Trying to unlock milestone {}, but it is already unlocked.', milestone)
            return
        milestone_data.state = DevelopmentalMilestoneStates.UNLOCKED
        milestone_data.age_completed = self._sim_info.age
        milestone_data.new_in_ui = True
        self._shutdown_milestone(milestone_data)
        resolver = SingleSimResolver(self._sim_info)
        for loot in milestone.loot:
            loot.apply_to_resolver(resolver)
        if send_ui_update:
            self.try_send_milestone_update_to_client(milestone_data)
        if telemetry_context is not MilestoneTelemetryContext.NONE:
            with telemetry_helper.begin_hook(milestones_telemetry_writer, TELEMETRY_HOOK_MILESTONE_END, sim_info=self._sim_info) as hook:
                hook.write_guid(TELEMETRY_FIELD_MILESTONE_ID, milestone.guid64)
                hook.write_int(TELEMETRY_FIELD_MILESTONE_CONTEXT, telemetry_context)
        logger.info('unlock_milestone(): milestone {} unlocked.', milestone)
        self._activate_available_milestones(telemetry_context=telemetry_context, send_ui_update=send_ui_update)
        if milestone.repeatable:
            activate_fn = lambda _: self.activate_milestone(milestone, telemetry_context=MilestoneTelemetryContext.REPEAT, from_repeat=True, send_ui_update=False)
            element = build_element([activate_fn])
            services.time_service().sim_timeline.schedule(element)

    def remove_milestone(self, milestone):
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is None:
            logger.error('remove_milestone() called for milestone {}, which does not have milestone_data.', milestone)
            return
        self._shutdown_milestone(milestone_data)
        if self.is_milestone_completed(milestone_data):
            self._archived_milestones_data[milestone] = milestone_data
        del self._active_milestones_data[milestone]
        if milestone_data.goal is not None:
            if milestone_data.goal not in self._active_goal_map:
                logger.error('Milestone {} is being removed from active data without having registered a goal with the active goal map. This is unexpected.', milestone)
                return
            del self._active_goal_map[milestone_data.goal]

    def mark_milestone_as_viewed(self, milestone, goal_id=None):
        milestone_data = self._active_milestones_data.get(milestone)
        if milestone_data is None:
            logger.error('mark_milestone_as_viewed() called for milestone {}, which does not have milestone_data.', milestone)
            return
        milestone_data.mark_as_viewed_in_ui(goal_id)
        self.try_send_milestone_update_to_client(milestone_data, goal_id)

    def recursively_unlock_prerequisites(self, milestone, telemetry_context):
        for prerequisite_milestone in milestone.prerequisite_milestones:
            if not self.is_milestone_unlocked(prerequisite_milestone):
                self.recursively_unlock_prerequisites(prerequisite_milestone, telemetry_context=telemetry_context)
                if not self.is_milestone_active(prerequisite_milestone):
                    self.activate_milestone(prerequisite_milestone, telemetry_context=telemetry_context)
                self.unlock_milestone(prerequisite_milestone, telemetry_context=telemetry_context)

    def setup_goals(self):
        for (milestone, milestone_data) in self._active_milestones_data.items():
            if milestone_data.state == DevelopmentalMilestoneStates.ACTIVE:
                goal = milestone_data.goal
                if goal is not None and goal.guid == milestone.goal.guid:
                    goal.setup()
                else:
                    if goal is not None:
                        goal.decommision()
                    if self._active_goal_map.get(goal):
                        del self._active_goal_map[goal]
                    goal = milestone.goal(sim_info=self._sim_info, goal_id=self._goal_id_generator())
                    milestone_data.goal = goal
                    self._active_goal_map[goal] = milestone
                    goal.setup()
                    goal.on_goal_offered()
                goal.register_for_on_goal_completed_callback(self.on_goal_completed)
        self._setup_delayed_goals = False

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def _apply_initial_loot(self, from_gameplay=False):
        resolver = SingleSimResolver(self._sim_info)
        for loot_entry in DevelopmentalMilestone.RETROACTIVE_MILESTONES:
            loot_entry.apply_to_resolver(resolver)
        if not from_gameplay:
            self._initial_loot_applied = True

    def _activate_available_milestones(self, telemetry_context, send_ui_update=False, activate_goals=True):
        if self._sim_info.lod < self._tracker_lod_threshold:
            return
        allow_retroactive_only = not self._initial_loot_applied
        for milestone in DevelopmentalMilestone.age_milestones_gen(self._sim_info.age):
            if self.is_milestone_locked(milestone):
                if self.is_milestone_available(milestone, allow_retroactive_only=allow_retroactive_only):
                    self.activate_milestone(milestone, telemetry_context=telemetry_context, send_ui_update=send_ui_update, activate_goals=activate_goals)
                elif self.is_milestone_tracked(milestone) or self.is_milestone_valid_for_sim(milestone) and milestone.is_primary_milestone is not None:
                    self.create_milestone(milestone, send_ui_update=send_ui_update)

    def _remove_all_milestones(self):
        to_remove = [milestone for milestone in self._active_milestones_data.keys()]
        for milestone in to_remove:
            self.remove_milestone(milestone)
        self.send_all_milestones_update_to_client()

    def _remove_inappropriate_milestones(self):
        to_remove = []
        for (milestone, milestone_data) in self._active_milestones_data.items():
            if not self.is_milestone_valid_for_sim(milestone):
                to_remove.append(milestone_data)
        if to_remove:
            for milestone_data in to_remove:
                self.remove_milestone(milestone_data.milestone)
            self.send_all_milestones_update_to_client()

    def _grant_retroactive_fake_milestones(self, telemetry_context):
        milestones_unlocked = False
        current_age_percentage = self._sim_info.age_progress_percentage
        for milestone in DevelopmentalMilestone.age_milestones_gen(self._sim_info.age):
            if self.is_milestone_unlocked(milestone) or milestone.treat_unlocked_at_age_percentage is not None and current_age_percentage >= milestone.treat_unlocked_at_age_percentage:
                if not self.is_milestone_active(milestone):
                    self.activate_milestone(milestone, telemetry_context=telemetry_context, send_ui_update=False)
                self.unlock_milestone(milestone, telemetry_context=telemetry_context, send_ui_update=False)
                milestones_unlocked = True
        if milestones_unlocked:
            self.send_all_milestones_update_to_client()

    def _shutdown_milestone(self, milestone_data):
        if milestone_data.goal is not None:
            milestone_data.goal.decommision()
        commodity_to_remove = milestone_data.milestone.commodity
        if commodity_to_remove is not None:
            self._sim_info.commodity_tracker.remove_statistic(commodity_to_remove)

    def _shutdown_retroactive_only_milestones(self):
        retroactive_only_milestones_data = [milestone_data for milestone_data in self._active_milestones_data.values() if milestone_data.milestone.retroactive_only and milestone_data.milestone not in self._milestone_evaluations]
        for milestone_data in retroactive_only_milestones_data:
            if milestone_data.state == DevelopmentalMilestoneStates.UNLOCKED:
                self._shutdown_milestone(milestone_data)
            else:
                self.remove_milestone(milestone_data.milestone)

    @staticmethod
    def _get_data_class(milestone):
        data_class_enum = DevelopmentalMilestone.DEVELOPMENTAL_MILESTONE_UNLOCK_OVERRIDES.get(milestone)
        if data_class_enum == MilestoneDataClass.HAD_CHILD:
            return HadChildDevelopmentalMilestoneData
        return DevelopmentalMilestoneData

    def on_age_stage_change(self):
        self._remove_inappropriate_milestones()
        self._activate_available_milestones(telemetry_context=MilestoneTelemetryContext.AGE_UP)
        self.send_all_milestones_update_to_client()

    def on_goal_completed(self, goal, is_completed):
        if not is_completed:
            return
        milestone = self._active_goal_map.get(goal)
        if milestone is None:
            logger.error('on_goal_completed() called for goal {}, which is not in the goal_map.', goal)
            return
        unlock_function = self._active_milestones_data.get(milestone).get_unlock_function(self._sim_info)
        if unlock_function is None:
            logger.error("No unlock function for this milestone {}'s data class was provided.", milestone)
            return
        unlock_function(milestone, telemetry_context=MilestoneTelemetryContext.GOAL)

    def _apply_retroactive_milestones_from_gameplay(self):
        self._apply_initial_loot(from_gameplay=True)

        def _post_retroactive_actions(*_):
            self._initial_loot_applied = True
            self._shutdown_retroactive_only_milestones()
            self.send_all_milestones_update_to_client()

        element = build_element([_post_retroactive_actions])
        services.time_service().sim_timeline.schedule(element)

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self._remove_all_milestones()
        elif old_lod < self._tracker_lod_threshold:
            self._grant_retroactive_fake_milestones(telemetry_context=MilestoneTelemetryContext.LOD_UP)
            self._activate_available_milestones(telemetry_context=MilestoneTelemetryContext.LOD_UP)
            if services.current_zone().have_households_and_sim_infos_loaded:
                self._apply_retroactive_milestones_from_gameplay()
        elif new_lod > old_lod and not self._sim_info.is_npc:
            self.load_milestones_info_from_proto()
            self.send_all_milestones_update_to_client()

    def on_zone_load(self):
        if self._sim_info.is_npc:
            return
        self.load_milestones_info_from_proto()
        services.current_zone().register_callback(ZoneState.ALL_SIMS_SPAWNED, self.start_milestone_tracker)

    def on_zone_unload(self):
        if self._sim_info.is_npc or not self._sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED):
            return
        if not game_services.service_manager.is_traveling:
            return
        self._developmental_milestone_proto = GameplaySaveData_pb2.DevelopmentalMilestoneTrackerData()
        self.save_milestones_info_to_proto(self._developmental_milestone_proto, copy_existing=False)
        self.clean_up()

    def cache_milestones_proto(self, milestone_tracker_proto, skip_load=False):
        if skip_load:
            return
        if self._sim_info.developmental_milestone_tracker is None:
            return
        self._developmental_milestone_proto = GameplaySaveData_pb2.DevelopmentalMilestoneTrackerData()
        self._developmental_milestone_proto.CopyFrom(milestone_tracker_proto)

    def _load_milestone_data_from_proto(self, msg, milestone_data, reassociate_goal=True):
        milestone = milestone_data.milestone
        milestone_data.state = DevelopmentalMilestoneStates(msg.state)
        milestone_data.new_in_ui = msg.new_in_ui
        if msg.HasField('age_completed'):
            milestone_data.age_completed = msg.age_completed
        if msg.HasField('goal_data'):
            goal_seed = GoalSeedling.deserialize_from_proto(msg.goal_data)
            if goal_seed is not None:
                goal = goal_seed.goal_type(sim_info=self._sim_info, goal_id=self._goal_id_generator(), count=goal_seed.count, reader=goal_seed.reader, locked=goal_seed.locked, completed_time=goal_seed.completed_time)
                milestone_data.goal = goal
                if reassociate_goal:
                    self._active_goal_map[goal] = milestone
        for previous_goal_msg in msg.previous_goals:
            if not previous_goal_msg.HasField('age_completed'):
                logger.info('Trying to load previous milestone data with no completed age value for DEVELOPMENTAL_MILESTONE : {}', milestone)
            else:
                goal_seed = GoalSeedling.deserialize_from_proto(previous_goal_msg.goal_data)
                if goal_seed is not None:
                    goal = goal_seed.goal_type(sim_info=self._sim_info, goal_id=self._goal_id_generator(), count=goal_seed.count, reader=goal_seed.reader, locked=goal_seed.locked, completed_time=goal_seed.completed_time)
                    previous_goal_data = PreviousGoalData(goal, previous_goal_msg.new_in_ui, previous_goal_msg.age_completed)
                    milestone_data.add_previous_goal_entry(goal.id, previous_goal_data)
        logger.info('Milestone {} loaded for Sim {}. State = {}', milestone, self._sim_info, milestone_data.state)

    def load_milestones_info_from_proto(self):
        if self._developmental_milestone_proto is None:
            return
        self._setup_delayed_goals = True
        self._initial_loot_applied = self._developmental_milestone_proto.initial_loot_applied
        milestone_manager = services.get_instance_manager(sims4.resources.Types.DEVELOPMENTAL_MILESTONE)
        for active_milestone_msg in self._developmental_milestone_proto.active_milestones:
            milestone_id = active_milestone_msg.milestone_id
            milestone = milestone_manager.get(milestone_id)
            if milestone is None:
                logger.info('Trying to load unavailable DEVELOPMENTAL_MILESTONE resource: {}', milestone_id)
            elif not self.is_milestone_valid_for_sim(milestone):
                pass
            else:
                milestone_data = self.create_milestone(milestone)
                self._load_milestone_data_from_proto(active_milestone_msg, milestone_data)
        for archived_milestone_msg in self._developmental_milestone_proto.archived_milestones:
            milestone_id = archived_milestone_msg.milestone_id
            milestone = milestone_manager.get(milestone_id)
            if milestone is None:
                logger.info('Trying to load unavailable DEVELOPMENTAL_MILESTONE resource: {}', milestone_id)
            else:
                milestone_data = self.create_milestone(milestone)
                self._load_milestone_data_from_proto(archived_milestone_msg, milestone_data, reassociate_goal=False)
        self._developmental_milestone_proto = None

    def _save_milestone_data_to_message(self, msg, milestone_data):
        msg.milestone_id = milestone_data.milestone.guid64
        msg.state = milestone_data.state
        msg.new_in_ui = milestone_data.new_in_ui
        if milestone_data.age_completed is not None:
            msg.age_completed = milestone_data.age_completed
        if milestone_data.goal is not None:
            goal_seed = milestone_data.goal.create_seedling()
            goal_seed.finalize_creation_for_save()
            goal_seed.serialize_to_proto(msg.goal_data)
        for previous_goal_data in milestone_data.previous_goals.values():
            with ProtocolBufferRollback(msg.previous_goals) as previous_goal_msg:
                previous_goal_msg.new_in_ui = previous_goal_data.new_in_ui
                if previous_goal_data.age_completed:
                    previous_goal_msg.age_completed = previous_goal_data.age_completed
                if previous_goal_data.goal is not None:
                    previous_goal_seed = previous_goal_data.goal.create_seedling()
                    previous_goal_seed.finalize_creation_for_save()
                    previous_goal_seed.serialize_to_proto(previous_goal_msg.goal_data)

    def save_milestones_info_to_proto(self, developmental_milestone_tracker_proto, copy_existing=True):
        if copy_existing and self._developmental_milestone_proto is not None:
            developmental_milestone_tracker_proto.CopyFrom(self._developmental_milestone_proto)
            return
        developmental_milestone_tracker_proto.initial_loot_applied = self._initial_loot_applied
        for milestone_data in self._active_milestones_data.values():
            with ProtocolBufferRollback(developmental_milestone_tracker_proto.active_milestones) as active_milestone_msg:
                self._save_milestone_data_to_message(active_milestone_msg, milestone_data)
        for milestone_data in self._archived_milestones_data.values():
            with ProtocolBufferRollback(developmental_milestone_tracker_proto.archived_milestones) as archived_milestone_msg:
                self._save_milestone_data_to_message(archived_milestone_msg, milestone_data)

    def _should_include_goal_message(self, milestone_data, previous_goal_id):
        return milestone_data.state == DevelopmentalMilestoneStates.UNLOCKED or previous_goal_id is not None

    def _get_milestone_update_msg(self, milestone_data, previous_goal_id=None):
        msg = Sims_pb2.DevelopmentalMilestoneUpdate()
        msg.sim_id = self._sim_info.sim_id
        msg.developmental_milestone_id = milestone_data.milestone.guid64
        msg.state = milestone_data.state if previous_goal_id is None else DevelopmentalMilestoneStates.UNLOCKED
        milestone_state_data = milestone_data.previous_goals.get(previous_goal_id, milestone_data)
        msg.new_in_ui = milestone_state_data.new_in_ui
        if milestone_state_data.age_completed is not None:
            msg.age_completed = milestone_state_data.age_completed
        goal = milestone_state_data.goal
        if goal:
            msg.goal_id = goal.id
            target_sim_info = goal.get_actual_target_sim_info()
            if target_sim_info is not None:
                msg.unlocked_with_sim_id = target_sim_info.id
            target_object_id = goal.get_actual_target_object_definition_id()
            if target_object_id is not None:
                catalog_name_key = get_object_catalog_name(target_object_id)
                if catalog_name_key is not None:
                    msg.unlocked_with_object_name = Localization_pb2.LocalizedString()
                    msg.unlocked_with_object_name.hash = catalog_name_key
            unlocked_zone_id = goal.get_actual_zone_id()
            if unlocked_zone_id is not None:
                persistence_service = services.get_persistence_service()
                zone_data = persistence_service.get_zone_proto_buff(unlocked_zone_id)
                if zone_data is not None:
                    msg.unlocked_in_lot_name = zone_data.name
                world_id = persistence_service.get_world_id_from_zone(unlocked_zone_id)
                if world_id:
                    msg.unlocked_in_region_id = persistence_service.get_region_id_from_world_id(world_id)
            unlocked_career_track = goal.get_career_track()
            if unlocked_career_track is not None:
                career_track = services.get_instance_manager(sims4.resources.Types.CAREER_TRACK).get(unlocked_career_track)
                if career_track is not None:
                    msg.unlocked_career_name = career_track.get_career_name(self._sim_info)
                    unlocked_career_level = goal.get_career_level()
                    if unlocked_career_level < len(career_track.career_levels):
                        career_level = career_track.career_levels[unlocked_career_level]
                        if career_level is not None:
                            msg.unlocked_career_level = career_level.get_title(self._sim_info)
            unlocked_death_type = goal.get_death_type_info()
            if unlocked_death_type is not None:
                death_trait = DeathTracker.DEATH_TYPE_GHOST_TRAIT_MAP.get(unlocked_death_type)
                if death_trait is not None:
                    msg.unlocked_death_type = death_trait.display_name(self._sim_info)
            unlocked_trait_guid = goal.get_trait_guid()
            if unlocked_trait_guid is not None:
                trait = services.get_instance_manager(sims4.resources.Types.TRAIT).get(unlocked_trait_guid)
                if trait is not None:
                    msg.unlocked_trait_name = trait.display_name(self._sim_info)
            unlocked_business_name = goal.get_small_business_name()
            if unlocked_business_name is not None:
                msg.unlocked_small_business_name = unlocked_business_name
            if goal.completed_time is not None:
                msg.completed_time = goal.completed_time
        return msg

    def try_send_milestone_update_to_client(self, milestone_data, previous_goal_id=None):
        if services.current_zone().is_zone_shutting_down:
            return
        resolver = SingleSimResolver(self._sim_info)
        if not self.is_milestone_visible(milestone_data.milestone, resolver):
            return
        msg = self._get_milestone_update_msg(milestone_data, previous_goal_id=previous_goal_id)
        owner = self._sim_info
        distributor = Distributor.instance()
        distributor.add_op(owner, GenericProtocolBufferOp(Operation.DEVELOPMENTAL_MILESTONE_UPDATE, msg))

    def send_all_milestones_update_to_client(self):
        zone = services.current_zone()
        if not zone.have_households_and_sim_infos_loaded:
            return
        if zone.is_zone_shutting_down:
            return
        msg = Sims_pb2.AllDevelopmentalMilestonesUpdate()
        msg.sim_id = self._sim_info.sim_id
        resolver = SingleSimResolver(self._sim_info)
        for (milestone, milestone_data) in self._active_milestones_data.items():
            if self.is_milestone_visible(milestone, resolver) and milestone.repeatable and (milestone.repeatable and milestone.is_primary_milestone and len(milestone_data.previous_goals) < 1 or milestone.repeatable and milestone.retroactive_only):
                milestone_msg = self._get_milestone_update_msg(milestone_data)
                msg.milestones.append(milestone_msg)
            for previous_goal_id in milestone_data.previous_goals.keys():
                prev_milestone_msg = self._get_milestone_update_msg(milestone_data, previous_goal_id)
                msg.milestones.append(prev_milestone_msg)
        for (milestone, milestone_data) in self._archived_milestones_data.items():
            if not milestone.repeatable:
                archived_milestone_msg = self._get_milestone_update_msg(milestone_data)
                msg.milestones.append(archived_milestone_msg)
            for previous_goal_id in milestone_data.previous_goals.keys():
                prev_milestone_msg = self._get_milestone_update_msg(milestone_data, previous_goal_id)
                msg.milestones.append(prev_milestone_msg)
        owner = self._sim_info
        distributor = Distributor.instance()
        distributor.add_op(owner, GenericProtocolBufferOp(Operation.ALL_DEVELOPMENTAL_MILESTONES_UPDATE, msg))
