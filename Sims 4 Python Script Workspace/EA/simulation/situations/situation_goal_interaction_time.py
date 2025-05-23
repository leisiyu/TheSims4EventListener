import alarmsfrom clock import interval_in_sim_hoursfrom date_and_time import TimeSpanimport event_testingfrom event_testing.results import TestResultimport servicesimport sims4.resourcesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import AutoFactoryInit, TunableReference, TunableSingletonFactory, TunableRange, TunableSet, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexproperty, blueprintpropertyfrom situations.situation_goal import SituationGoalfrom tag import Tag
class InteractionOfInterest(AutoFactoryInit):
    FACTORY_TUNABLES = {'affordance': TunableReference(description='\n                The affordance that we are are timing for length of runtime.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True, class_restrictions='SuperInteraction'), 'tags': TunableSet(description='\n                A set of tags that will match an affordance instead of looking\n                for a specific one.\n                ', tunable=TunableEnumEntry(Tag, Tag.INVALID)), 'duration': TunableRange(description='\n                The amount of time in sim hours that this interaction has to\n                run for this test to be considered passed.\n                ', tunable_type=int, default=10, minimum=1)}
    expected_kwargs = (('interaction', event_testing.test_constants.FROM_EVENT_DATA),)

    def get_expected_args(self):
        return dict(self.expected_kwargs)

    def __call__(self, interaction=None):
        if interaction.affordance is self.affordance:
            return TestResult.TRUE
        if self.tags & interaction.get_category_tags():
            return TestResult.TRUE
        return TestResult(False, 'Failed affordance check: {} is not {} and does not have any matching tags in {}.', interaction.affordance, self.affordance, self.tags)

    def custom_keys_gen(self):
        if self.affordance:
            yield self.affordance
        for tag in self.tags:
            yield tag
TunableInteractionOfInterest = TunableSingletonFactory.create_auto_factory(InteractionOfInterest)
class SituationGoalInteractionTime(SituationGoal):
    DURATION_RUN = 'duration_run'
    REMOVE_INSTANCE_TUNABLES = ('_post_tests',)
    INSTANCE_TUNABLES = {'_goal_test': TunableInteractionOfInterest(description='\n                Interaction and duration that this situation goal will use.\n                Example: Bartend for 10 sim minutes.\n                ', tuning_group=GroupNames.TESTS)}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._total_time_ran = TimeSpan.ZERO
        self._last_started_time = None
        self._alarm_handle = None
        self._total_duration = interval_in_sim_hours(self._goal_test.duration)
        for custom_key in self._goal_test.custom_keys_gen():
            services.get_event_manager().register_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, custom_key)
            services.get_event_manager().register_with_custom_key(self, event_testing.test_events.TestEvent.InteractionComplete, custom_key)
        if reader is not None:
            duration_run = reader.read_uint64(self.DURATION_RUN, 0)
            self._total_time_ran = TimeSpan(duration_run)
        self._sims_running_interaction = set()

    def setup(self):
        super().setup()
        for sim in self.all_sims_interested_in_goal_gen():
            if sim.si_state.is_running_affordance(self._goal_test.affordance):
                self._sims_running_interaction.add(sim.id)
        if self._sims_running_interaction:
            self._start_alarm()

    def create_seedling(self):
        if self._alarm_handle is not None:
            self._start_alarm()
        seedling = super().create_seedling()
        writer = seedling.writer
        writer.write_uint64(self.DURATION_RUN, self._total_time_ran.in_ticks())
        return seedling

    def _decommision(self):
        for custom_key in self._goal_test.custom_keys_gen():
            services.get_event_manager().unregister_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, custom_key)
            services.get_event_manager().unregister_with_custom_key(self, event_testing.test_events.TestEvent.InteractionComplete, custom_key)
        self._stop_alarm()
        super()._decommision()

    def _on_hour_reached(self, alarm_handle=None):
        self._stop_alarm()
        if self._total_time_ran >= self._total_duration:
            super()._on_goal_completed()
        else:
            self._on_iteration_completed()
            self._start_alarm()

    def _start_alarm(self):
        self._stop_alarm()
        if not self._sims_running_interaction:
            return
        next_hour = interval_in_sim_hours(int(self._total_time_ran.in_hours()) + 1)
        time_till_completion = (next_hour - self._total_time_ran)/len(self._sims_running_interaction)
        self._alarm_handle = alarms.add_alarm(self, time_till_completion, self._on_hour_reached)
        self._last_started_time = services.time_service().sim_now

    def _stop_alarm(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None
            self._total_time_ran += (services.time_service().sim_now - self._last_started_time)*len(self._sims_running_interaction)
            self._last_started_time = None

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if not resolver(self._goal_test):
            return False
        self._stop_alarm()
        if event == event_testing.test_events.TestEvent.InteractionStart:
            self._sims_running_interaction.add(sim_info.id)
        else:
            self._sims_running_interaction.discard(sim_info.id)
        self._start_alarm()
        return False

    @property
    def completed_iterations(self):
        return int(self._total_time_ran.in_hours())

    @blueprintproperty
    def max_iterations(self):
        return self._goal_test.duration
lock_instance_tunables(SituationGoalInteractionTime, _iterations=1, should_reevaluate_on_load=False)