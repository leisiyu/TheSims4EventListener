from event_testing.resolver import SingleSimResolver, GlobalResolverfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableReference, TunableVariantimport servicesimport sims4.resourcesimport sims4.tuningimport situations.situation_goalfrom sims4.utils import flexproperty, classproperty, blueprintmethod, blueprintpropertylogger = sims4.log.Logger('SituationGoalCompound', default_owner='bosee')
class _EvalModeBase(AutoFactoryInit, HasTunableSingletonFactory):

    def get_completed_iterations(self, compound_goal):
        raise NotImplementedError

    def get_max_iterations(self, goals, compound_goal_name=None):
        raise NotImplementedError

    def is_completed(self, compound_goal, sub_goal_completed):
        raise NotImplementedError

    def run_goal_completion_tests(self, compound_goal, *args):
        raise NotImplementedError

class _EvalModeAny(_EvalModeBase):

    def get_completed_iterations(self, compound_goal):
        goal_to_find = compound_goal._most_completed_sub_goal()
        return goal_to_find.completed_iterations

    def get_max_iterations(self, goals, compound_goal_name='name_missing'):
        iterations = next((goal.max_iterations for goal in goals), 1)
        if any(goal.max_iterations != iterations for goal in goals):
            logger.warn("Compound any-goal {} has sub goals with different iterations. Listing the compound goal's iterations as the first sub goal's iterations.", compound_goal_name)
        return iterations

    def run_goal_completion_tests(self, compound_goal, *args):
        current_return = False
        for situation_goal in compound_goal._situation_goal_instances:
            current_return = current_return or situation_goal._run_goal_completion_tests(*args)
        return current_return

    def is_completed(self, compound_goal, sub_goal_completed):
        return sub_goal_completed

class _EvalModeAll(_EvalModeBase):

    def get_completed_iterations(self, compound_goal):
        return sum(1 for sub_goal in compound_goal._situation_goal_instances if sub_goal.is_completed)

    def get_max_iterations(self, goals, compound_goal_name=None):
        return len(goals)

    def run_goal_completion_tests(self, compound_goal, *args):
        current_return = True
        for sub_goal in compound_goal._situation_goal_instances:
            sub_goal_is_complete = sub_goal._run_goal_completion_tests(*args) or sub_goal.is_completed
            current_return = current_return and sub_goal_is_complete
        return current_return

    def is_completed(self, compound_goal, sub_goal_completed):
        for sub_goal in compound_goal._situation_goal_instances:
            if not sub_goal.is_completed:
                return False
        return True

class SituationGoalCompound(situations.situation_goal.SituationGoal, AutoFactoryInit, HasTunableSingletonFactory):
    INSTANCE_TUNABLES = {'situation_goals': TunableList(description='\n            If any of the situation goal passes this situation goal will pass too.\n            ', tunable=TunableReference(description='\n                If this situation goal passes, pass this compound one.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)), unique_entries=True, minlength=2), 'evaluation_mode': TunableVariant(description='\n            Determines how progress of the compound goal is tracked.\n            \n            Any - Compound goal completes when any sub-goals complete.\n            All - Compound goal completes when all sub-goals complete.\n            ', any=_EvalModeAny.TunableFactory(), all=_EvalModeAll.TunableFactory(), default='any')}

    @blueprintmethod
    def _verify_tuning_callback(self):
        for situation_goal in self.situation_goals:
            if isinstance(situation_goal, SituationGoalCompound):
                logger.error('Compound goal {} contains other compound goals. This might cause performance problems.', self)

    def __init__(self, *args, reader=None, sub_goals=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._situation_goal_instances = []
        kwargs.pop('init_blueprint_func', None)
        if sub_goals:
            self._situation_goal_instances = sub_goals
        else:
            for situation_goal in self.situation_goals:
                self._situation_goal_instances.append(situation_goal(*args, reader=reader, **kwargs))

    @property
    def sub_goal_instances(self):
        return self._situation_goal_instances

    @blueprintproperty
    def sub_goals(self):
        if not self.is_blueprint:
            return self.sub_goal_instances
        return self.situation_goals

    def setup(self):
        super().setup()
        for situation_goal in self._situation_goal_instances:
            if situation_goal.is_completed:
                pass
            else:
                situation_goal.setup()
                situation_goal.register_for_on_goal_completed_callback(self._sub_goal_completed_callback)

    def _decommision(self):
        super()._decommision()
        for situation_goal in self._situation_goal_instances:
            situation_goal._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if not self.evaluation_mode.run_goal_completion_tests(self, sim_info, event, resolver):
            return False
        elif not super()._run_goal_completion_tests(sim_info, event, resolver):
            return False
        return True

    @property
    def completed_iterations(self):
        return self.evaluation_mode.get_completed_iterations(self)

    @blueprintproperty
    def max_iterations(self):
        if not self.is_blueprint:
            return self.evaluation_mode.get_max_iterations(self._situation_goal_instances, self.__class__)
        else:
            return self.evaluation_mode.get_max_iterations(self.situation_goals)

    def _sub_goal_completed_callback(self, sub_goal, sub_goal_completed):
        if self.evaluation_mode.is_completed(self, sub_goal_completed):
            resolver = self.get_resolver()
            if self._post_tests.run_tests(resolver):
                self._on_goal_completed(start_cooldown=True)
        else:
            self._on_iteration_completed()
            if sub_goal_completed:
                sub_goal._decommision()

    def _most_completed_sub_goal(self):
        return max(self._situation_goal_instances, key=lambda x: x.completed_iterations/x.max_iterations)

    def get_resolver(self):
        sim_info = next(self.all_sim_infos_interested_in_goal_gen(), None)
        if sim_info is None:
            return GlobalResolver()
        return SingleSimResolver(sim_info)
sims4.tuning.instances.lock_instance_tunables(SituationGoalCompound, score_on_iteration_complete=None, _iterations=1)