import sims4from business.business_enums import BusinessTypefrom event_testing.test_events import TestEventfrom interactions.payment.payment_info import PaymentBusinessRevenueTypefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableListimport servicesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_goal import SituationGoallogger = sims4.log.Logger('SmallBusinessSituationGoals', default_owner='sersanchez')
class SituationGoalSmallBusinessIncome(SituationGoal):
    SIMOLEONS_EARNED = 'simoleons_earned'
    REMOVE_INSTANCE_TUNABLES = ('_post_tests',)
    INSTANCE_TUNABLES = {'revenue_types': TunableList(description='\n            The types of the payment we want to track.\n            ', tunable=TunableEnumEntry(description='\n                The type of the payment we want to track.\n                ', tunable_type=PaymentBusinessRevenueType, default=PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE), tuning_group=GroupNames.GOALS), 'amount_to_earn': Tunable(description='\n            Amount to earn in order to consider this goal as completed.\n            ', tunable_type=int, default=0, tuning_group=GroupNames.GOALS)}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._goal_test = None
        if reader is not None:
            self._total_simoleons_earned = reader.read_uint64(self.SIMOLEONS_EARNED, 0)
        else:
            self._total_simoleons_earned = 0
        self._iterations = self.amount_to_earn

    def setup(self):
        super().setup()
        services.get_event_manager().register(self, (TestEvent.SmallBusinessPaymentRegistered,))

    def _decommision(self):
        services.get_event_manager().unregister(self, (TestEvent.SmallBusinessPaymentRegistered,))
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if not self._valid_event_sim_of_interest(sim_info):
            return
        if 'revenue_type' not in resolver.event_kwargs or 'amount' not in resolver.event_kwargs:
            return
        revenue_type = resolver.event_kwargs['revenue_type']
        if revenue_type not in self.revenue_types:
            return
        amount = resolver.event_kwargs['amount']
        self._total_simoleons_earned += amount
        self._count = self._total_simoleons_earned
        if self._total_simoleons_earned >= self.amount_to_earn:
            super()._on_goal_completed()
        else:
            self._on_iteration_completed()

    def create_seedling(self):
        seedling = super().create_seedling()
        seedling.writer.write_uint64(self.SIMOLEONS_EARNED, self._total_simoleons_earned)
        return seedling
lock_instance_tunables(SituationGoalSmallBusinessIncome, _iterations=1)
class SituationGoalSmallBusinessCustomerActivitiesPerformed(SituationGoal):
    PERFORMED_ACTIVITIES_COUNT = 'performed_activities_count'
    REMOVE_INSTANCE_TUNABLES = ('_post_tests',)
    INSTANCE_TUNABLES = {'number_of_activities_to_complete': Tunable(description='\n            Amount of customers activities that should be done to consider the goal as completed.\n            ', tunable_type=int, default=1, tuning_group=GroupNames.GOALS)}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        if reader is not None:
            self._performed_activities_count = reader.read_uint64(self.PERFORMED_ACTIVITIES_COUNT, 0)
        else:
            self._performed_activities_count = 0
        self._iterations = self.number_of_activities_to_complete

    def setup(self):
        super().setup()
        services.get_event_manager().register(self, (TestEvent.SmallBusinessCustomerActivityDone,))

    def _decommision(self):
        services.get_event_manager().unregister(self, (TestEvent.SmallBusinessCustomerActivityDone,))
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return
        owner_sim_info = services.sim_info_manager().get(business_manager.owner_sim_id)
        if not self._valid_event_sim_of_interest(owner_sim_info):
            return
        self._performed_activities_count += 1
        self._count = self._performed_activities_count
        if self._performed_activities_count >= self.number_of_activities_to_complete:
            super()._on_goal_completed()
        else:
            self._on_iteration_completed()

    def create_seedling(self):
        seedling = super().create_seedling()
        seedling.writer.write_uint64(self.PERFORMED_ACTIVITIES_COUNT, self._performed_activities_count)
        return seedling
lock_instance_tunables(SituationGoalSmallBusinessCustomerActivitiesPerformed, _iterations=1)