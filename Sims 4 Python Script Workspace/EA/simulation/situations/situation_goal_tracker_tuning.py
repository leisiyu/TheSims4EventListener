from situations.dynamic_situation_goal_tracker import DynamicSituationGoalTracker, SimpleSituationGoalTracker, ActivitySituationGoalTrackerfrom situations.situation_goal_tracker import SituationGoalTrackerfrom situations.situation_serialization import GoalTrackerTypefrom sims4.tuning.tunable import TunableFactory, TunableVariantFORCE_USER_FACING_GOAL_TRACKERS = [GoalTrackerType.SIMPLE_GOAL_TRACKER]
class TunableSituationGoalTracker(TunableFactory):

    @staticmethod
    def _get_situation_goal_tracker(situation=None):
        return (GoalTrackerType.STANDARD_GOAL_TRACKER, None if situation is None else SituationGoalTracker(situation))

    FACTORY_TYPE = _get_situation_goal_tracker

class TunableDynamicSituationGoalTracker(TunableFactory):

    @staticmethod
    def _get_dynamic_goal_tracker(situation=None):
        return (GoalTrackerType.DYNAMIC_GOAL_TRACKER, None if situation is None else DynamicSituationGoalTracker(situation))

    FACTORY_TYPE = _get_dynamic_goal_tracker

class TunableSimpleSituationGoalTracker(TunableFactory):

    @staticmethod
    def _get_simple_goal_tracker(situation=None):
        return (GoalTrackerType.SIMPLE_GOAL_TRACKER, None if situation is None else SimpleSituationGoalTracker(situation))

    FACTORY_TYPE = _get_simple_goal_tracker

class TunableActivitySituationGoalTracker(TunableFactory):

    @staticmethod
    def _get_activity_goal_tracker(situation=None):
        return (GoalTrackerType.ACTIVITY_GOAL_TRACKER, None if situation is None else ActivitySituationGoalTracker(situation))

    FACTORY_TYPE = _get_activity_goal_tracker

class TunableSituationGoalTrackerVariant(TunableVariant):

    def __init__(self, *args, default='situation_goal_tracker', **kwargs):
        super().__init__(*args, situation_goal_tracker=TunableSituationGoalTracker(description='\n                Standard goal tracker used by situations with chained major and minor goals.\n                '), dynamic_situation_goal_tracker=TunableDynamicSituationGoalTracker(description='\n                Goal tracker that tracks a list of goals and associated preferences. Goals are\n                unchained, without major/minor structure.\n                \n                Primary use is for Holidays.\n                '), simple_situation_goal_tracker=TunableSimpleSituationGoalTracker(description='\n                Goal tracker that tracks a list of goals. Goals are unchained, without major/minor\n                structure.\n                '), activity_situation_goal_tracker=TunableActivitySituationGoalTracker(description='\n                Goal tracker that uses activities selected by the user to determine a list of goals.\n                Goals are unchained, but maintain a major/minor structure.\n                '), default=default, **kwargs)
