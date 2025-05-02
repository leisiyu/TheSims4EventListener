from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    import collections
    from sims.sim import Sim
    from sims4.tuning.instances import HashedTunedInstanceMetaclass
    from situations.situation import Situation
    from situations.situation_goal import SituationGoal
    from situations.situation_serialization import GoalTrackerSeedling, SituationSeed
    from typing import Listimport distributorimport itertoolsimport servicesimport sims4import sims4.logfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.test_events import TestEventfrom holidays.holiday_globals import HolidayTuningfrom protocolbuffers import Situations_pb2from situations.base_situation_goal_tracker import BaseSituationGoalTrackerfrom situations.situation_goal import UiSituationGoalStatusfrom situations.situation_serialization import GoalTrackerTypelogger = sims4.log.Logger('SituationGoals', default_owner='jjacobson')
class SimpleSituationGoalTracker(BaseSituationGoalTracker):

    def __init__(self, situation):
        super().__init__(situation)
        self._goals = []
        self._situation_goal_types = None

    def destroy(self):
        super().destroy()
        for goal in self._goals:
            goal.destroy()
        self._goals = None

    @property
    def goals(self):
        return self._goals

    @property
    def starting_goals(self):
        if self._situation.situation_goal_type_ids:
            situation_goal_manager = services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)
            self._situation_goal_types = [situation_goal_manager.get(goal_type_id) for goal_type_id in self._situation.situation_goal_type_ids]
        return self._situation_goal_types

    def save_to_seed(self, situation_seed):
        tracker_seedling = situation_seed.setup_for_goal_tracker_save(GoalTrackerType.DYNAMIC_GOAL_TRACKER, self._has_offered_goals, 0)
        for goal in self._goals:
            goal_seedling = goal.create_seedling()
            if goal.completed_time is not None:
                goal_seedling.set_completed()
            tracker_seedling.add_minor_goal(goal_seedling)

    def load_from_seedling(self, tracker_seedling):
        if self._has_offered_goals:
            raise AssertionError('Attempting to load goals for situation: {} but goals have already been offered.'.format(self))
        self._has_offered_goals = tracker_seedling.has_offered_goals
        for goal_seedling in tracker_seedling.minor_goals:
            sim_info = services.sim_info_manager().get(goal_seedling.actor_id)
            goal = goal_seedling.goal_type(sim_info=sim_info, situation=self._situation, goal_id=self._goal_id_generator(), count=goal_seedling.count, reader=goal_seedling.reader, locked=goal_seedling.locked, completed_time=goal_seedling.completed_time)
            if not goal_seedling.completed:
                goal.setup()
                goal.register_for_on_goal_completed_callback(self._on_goal_completed)
            self._goals.append(goal)
        for goal in self._goals:
            goal.validate_completion()

    def _on_goal_completed(self, goal, goal_completed):
        if goal_completed:
            goal.decommision()
            self._situation.on_goal_completed(goal)
            self.refresh_goals(completed_goal=goal)
        else:
            if goal.score_on_iteration_complete is not None:
                self.update_situation_score(goal)
            self.send_goal_update_to_client()

    def _offer_goals(self):
        if self._has_offered_goals:
            return False
        self._has_offered_goals = True
        if self.starting_goals is None:
            return False
        for goal in self.starting_goals:
            self.create_and_add_goal_inst(goal)
        return True

    def create_and_add_goal_inst(self, goal:'HashedTunedInstanceMetaclass') -> 'None':
        inst_goal = goal(sim_info=self._situation.get_situation_goal_actor(), situation=self._situation, goal_id=self._goal_id_generator())
        self._goals.append(inst_goal)
        inst_goal.setup()
        inst_goal.on_goal_offered()
        inst_goal.register_for_on_goal_completed_callback(self._on_goal_completed)

    def send_goal_update_to_client(self, completed_goal:'SituationGoal'=None, msg:'Situations_pb2.SituationGoalsUpdate'=None) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None or not situation_manager.sim_assignment_complete:
            return
        situation = self._situation
        if situation.is_running:
            if msg is None:
                msg = Situations_pb2.SituationGoalsUpdate()
            msg.goal_status = UiSituationGoalStatus.COMPLETED
            msg.situation_id = situation.id
            goal_sub_text = situation.get_goal_sub_text()
            if goal_sub_text is not None:
                msg.goal_sub_text = goal_sub_text
            goal_button_text = situation.get_goal_button_text()
            if goal_button_text is not None:
                msg.goal_button_data.button_text = goal_button_text
                msg.goal_button_data.is_enabled = situation.is_goal_button_enabled
            for goal in self.goals:
                self.build_goal_message(msg, goal)
            if completed_goal is not None:
                msg.completed_goal_id = completed_goal.id
            op = distributor.ops.SituationGoalUpdateOp(msg)
            Distributor.instance().add_op(situation, op)

    def get_goal_info(self):
        return list((goal, None) for goal in self._goals)

    def get_completed_goal_info(self):
        return []

    def all_goals_gen(self):
        if self._goals is not None:
            for goal in self._goals:
                yield goal

    def update_situation_score(self, goal):
        self._situation.score_update(goal.score_on_iteration_complete)

    def build_goal_message(self, msg, goal):
        with ProtocolBufferRollback(msg.goals) as goal_msg:
            goal.build_goal_message(goal_msg)

    def debug_force_complete_by_goal_id(self, goal_id:'int', target_sim:'Sim'=None) -> 'bool':
        goals = self._goals
        for goal in goals:
            if goal.id == goal_id:
                goal.force_complete(target_sim=target_sim)
                return True
        return False

class DynamicSituationGoalTracker(SimpleSituationGoalTracker):

    def __init__(self, situation):
        super().__init__(situation)
        self._goal_preferences = None

    @property
    def starting_goals(self):
        return self._situation._dynamic_goals

    def set_goal_preferences(self, goal_preferences):
        self._goal_preferences = goal_preferences

    def update_goals(self, goals_to_add, goals_to_remove, goal_type_order=None):
        for goal in tuple(self._goals):
            if goal.tuning_blueprint in goals_to_remove:
                goal.decommision()
                self._goals.remove(goal)
        for goal in goals_to_add:
            self.create_and_add_goal_inst(goal)
        if goal_type_order is None:
            return
        if len(goal_type_order) != len(self._goals):
            logger.error('Attempting to sort dynamic situation goals tracker with mismatching goals {} != {}', goal_type_order, self._goals)
            return
        type_to_goals = {goal.tuning_blueprint: goal for goal in self._goals}
        self._goals = [type_to_goals[goal_type] for goal_type in goal_type_order]

    def build_goal_message(self, msg, goal):
        with ProtocolBufferRollback(msg.goals) as goal_msg:
            goal.build_goal_message(goal_msg)
            if self._goal_preferences is not None:
                (preference, reason) = self._goal_preferences[goal.tuning_blueprint]
                goal_msg.goal_preference = preference
                if reason is not None:
                    goal_msg.goal_preference_tooltip = reason

    def refresh_goals(self, completed_goal=None):
        self._offer_goals()
        if completed_goal is not None:
            self.send_goal_update_to_client(completed_goal=completed_goal)

    def update_situation_score(self, goal):
        score = goal.score_on_iteration_complete
        (preference, _) = self._goal_preferences[goal.tuning_blueprint]
        if preference in HolidayTuning.TRADITION_PREFERENCE_SCORE_MULTIPLIER:
            score *= HolidayTuning.TRADITION_PREFERENCE_SCORE_MULTIPLIER[preference]
        self._situation.score_update(score)

class ActivitySituationGoalTracker(SimpleSituationGoalTracker):
    DEFAULT_WEIGHT = 1
    MAX_MINOR_GOALS = 3

    def __init__(self, situation:'Situation') -> 'None':
        super().__init__(situation)
        self._main_goal = None
        self._main_goal_completed = False
        self._completed_goals = []
        self._offered_goal_ids = []
        self._debug_force_show_goal_id = 0

    def destroy(self) -> 'None':
        super().destroy()
        if self._main_goal is not None:
            self._main_goal.destroy()
            self._main_goal = None
        for goal in self._completed_goals:
            goal.destroy()
        self._completed_goals = None
        self._offered_goal_ids = None

    @property
    def main_goal(self) -> 'SituationGoal':
        return self._main_goal

    @property
    def main_goal_completed(self) -> 'bool':
        return self._main_goal_completed

    @property
    def completed_goals(self) -> 'List[SituationGoal]':
        return self._completed_goals

    @property
    def starting_goals(self) -> 'List[float, HashedTunedInstanceMetaclass]':
        if self._situation.situation_activity_ids:
            situation_goal_manager = services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)
            if self._situation.activity_goals is None:
                self._situation_goal_types = [(self.DEFAULT_WEIGHT, situation_goal_manager.get(goal_type_id)) for goal_type_id in self._situation.situation_goal_type_ids]
            else:
                self._situation_goal_types = []
                situation_activity_ids = self._situation.situation_activity_ids
                for (activity, activity_goals) in self._situation.activity_goals.items():
                    if activity.guid64 not in situation_activity_ids:
                        pass
                    else:
                        for activity_goal in activity_goals:
                            self._situation_goal_types.append((activity_goal.weight, activity_goal.goal))
        return self._situation_goal_types

    def save_to_seed(self, situation_seed:'SituationSeed') -> 'None':
        situation_seed._situation_activity_ids = self._situation.situation_activity_ids
        tracker_seedling = situation_seed.setup_for_goal_tracker_save(GoalTrackerType.ACTIVITY_GOAL_TRACKER, self._has_offered_goals, 0)
        for goal in itertools.chain((self._main_goal,), self._goals, self._completed_goals):
            if goal is None:
                pass
            else:
                goal_seedling = goal.create_seedling()
                if goal.completed_time is not None:
                    goal_seedling.set_completed()
                if goal is self._main_goal:
                    tracker_seedling.set_main_goal(goal_seedling)
                else:
                    tracker_seedling.add_minor_goal(goal_seedling)

    def load_from_seedling(self, tracker_seedling:'GoalTrackerSeedling') -> 'None':
        if self._has_offered_goals:
            raise AssertionError('Attempting to load goals for situation: {} but goals have already been offered.'.format(self))
        self._has_offered_goals = tracker_seedling.has_offered_goals
        sim_info_manager = services.sim_info_manager()
        minor_goals = tracker_seedling.minor_goals
        for goal_seedling in minor_goals:
            sim_info = sim_info_manager.get(goal_seedling.actor_id)
            goal = goal_seedling.goal_type(sim_info=sim_info, situation=self._situation, goal_id=self._goal_id_generator(), count=goal_seedling.count, reader=goal_seedling.reader, locked=goal_seedling.locked, completed_time=goal_seedling.completed_time)
            if not goal_seedling.completed:
                goal.setup()
                goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                self._goals.append(goal)
            else:
                self._completed_goals.append(goal)
            self._offered_goal_ids.append(goal.guid64)
        for goal in self._goals:
            goal.validate_completion()
        if tracker_seedling.main_goal:
            goal_seedling = tracker_seedling.main_goal
            sim_info = sim_info_manager.get(goal_seedling.actor_id)
            self._main_goal = goal_seedling.goal_type(sim_info=sim_info, situation=self._situation, goal_id=self._goal_id_generator(), count=goal_seedling.count, reader=goal_seedling.reader, locked=goal_seedling.locked, completed_time=goal_seedling.completed_time)
            if goal_seedling.completed:
                self._main_goal_completed = True
            else:
                self._main_goal.setup()
                self._main_goal.register_for_on_goal_completed_callback(self._on_goal_completed)
            self._main_goal.validate_completion()
        if self._goals or self._main_goal is None:
            self._offer_goals()

    def check_completed_goal_cooldowns(self) -> 'None':
        goal_index = 0
        if len(self._goals) < self.MAX_MINOR_GOALS:
            if self._completed_goals[goal_index].is_on_cooldown() and False and self._debug_force_show_goal_id == self._completed_goals[goal_index].guid64:
                completed_goal = self._completed_goals.pop(goal_index)
                self._offered_goal_ids.remove(completed_goal.guid64)
            else:
                goal_index += 1

    def _on_goal_completed(self, goal:'SituationGoal', goal_completed:'bool') -> 'None':
        if goal_completed:
            if goal is self._main_goal:
                self._main_goal_completed = True
                services.get_event_manager().process_event(TestEvent.MainSituationGoalComplete, sim_info=goal.sim_info, custom_keys=self._situation.custom_event_keys)
            else:
                goal_index = self._goals.index(goal)
                self._completed_goals.append(self._goals.pop(goal_index))
            goal.decommision()
            self._situation.on_goal_completed(goal)
            self.check_completed_goal_cooldowns()
            self.refresh_goals(completed_goal=goal)
        else:
            if goal.score_on_iteration_complete is not None:
                self.update_situation_score(goal)
            self.send_goal_update_to_client()

    def _offer_goals(self) -> 'bool':
        situation = self._situation
        goal_actor = services.sim_info_manager().get(situation.guest_list.host_sim_id)
        goal_actor_sim = goal_actor.get_sim_instance() if goal_actor is not None else None
        if self._main_goal is None:
            main_goal = situation.get_main_goal(sim_info=goal_actor, situation=situation, goal_id=self._goal_id_generator())
            if main_goal is None:
                return False
            self._main_goal = main_goal
            self._main_goal.setup()
            self._main_goal.on_goal_offered()
            self._main_goal.register_for_on_goal_completed_callback(self._on_goal_completed)
        starting_goals = self.starting_goals
        if starting_goals is None:
            return False
        if self._debug_force_show_goal_id != 0:
            for weighted_goal in starting_goals:
                goal = weighted_goal[1]
                if goal.guid64 == self._debug_force_show_goal_id:
                    self.create_and_add_goal_inst(goal)
                    self._offered_goal_ids.append(goal.guid64)
                    self._has_offered_goals = True
                    self._debug_force_show_goal_id = 0
                    return True
        available_goals = starting_goals.copy()
        while False and len(available_goals) > 0 and len(self._goals) < self.MAX_MINOR_GOALS:
            choice_index = sims4.random.weighted_random_index(available_goals)
            goal = available_goals[choice_index][1]
            del available_goals[choice_index]
            if goal.can_be_given_as_goal(goal_actor_sim, situation) and goal.guid64 not in self._offered_goal_ids:
                self.create_and_add_goal_inst(goal)
                self._offered_goal_ids.append(goal.guid64)
        self._has_offered_goals = True
        return True

    def send_goal_update_to_client(self, completed_goal:'SituationGoal'=None, msg:'Situations_pb2.SituationGoalsUpdate'=None) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None or not situation_manager.sim_assignment_complete:
            return
        situation = self._situation
        if situation.is_running:
            msg = Situations_pb2.SituationGoalsUpdate()
            main_goal = self._main_goal
            if main_goal is not None and situation._main_goal_visibility:
                main_goal.build_goal_message(msg.major_goal)
            super().send_goal_update_to_client(completed_goal, msg)

    def get_goal_info(self) -> 'List[SituationGoal, None]':
        return list((goal, None) for goal in self.all_goals_gen())

    def all_goals_gen(self) -> 'collections.Iterable':
        if self._main_goal is not None:
            yield self._main_goal
        yield from super().all_goals_gen()

    def debug_force_complete_by_goal_id(self, goal_id:'int', target_sim:'Sim'=None) -> 'bool':
        if self._main_goal.id == goal_id:
            self._main_goal.force_complete(target_sim=target_sim)
            return True
        return super().debug_force_complete_by_goal_id(goal_id, target_sim)

    def debug_force_show_by_goal_id(self, goal_id:'int', target_sim:'Sim'=None) -> 'bool':
        starting_goals = self.starting_goals
        if starting_goals is None:
            return False
        valid_goal = False
        for goal in starting_goals:
            if goal[1].guid64 == goal_id:
                valid_goal = True
                break
        if not valid_goal:
            return False
        for goal in self.goals:
            if goal.guid64 == goal_id:
                return False
        self._debug_force_show_goal_id = goal_id
        if len(self.goals) >= self.MAX_MINOR_GOALS:
            self.debug_force_complete_by_goal_id(self.goals[0].id, target_sim)
        else:
            self.check_completed_goal_cooldowns()
            self.refresh_goals(completed_goal=None)
        return True
