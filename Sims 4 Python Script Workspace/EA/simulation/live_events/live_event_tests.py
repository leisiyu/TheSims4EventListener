from __future__ import annotationsfrom typing import TYPE_CHECKINGimport sims4from live_events.live_event_service import LiveEventState, LiveEventNamefrom event_testing.results import TestResultfrom sims4.math import Operatorfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableEnumEntry, TunableRange, TunableOperatorimport event_testing.test_baseimport servicesif TYPE_CHECKING:
    from typing import *
class LiveEventStateTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'live_event_name': TunableEnumEntry(description='\n            The name of the live event we are checking.\n            ', tunable_type=LiveEventName, default=LiveEventName.DEFAULT, invalid_enums=(LiveEventName.DEFAULT,)), 'state': TunableEnumEntry(description='\n            If the live event is in this state, this test passes.\n            ', tunable_type=LiveEventState, default=LiveEventState.ACTIVE), 'negate': Tunable(description='\n            If checked then the result of the test will be negated.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {}

    def __call__(self, *args, **kwargs):
        live_event_service = services.get_live_event_service()
        if live_event_service is None:
            return TestResult(False, 'There is no active Live Event service.', tooltip=self.tooltip)
        live_event_state = live_event_service.get_live_event_state(self.live_event_name)
        if live_event_state != self.state:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'The live event {} is in {} state, not {}.', self.live_event_name.name, live_event_state, self.state, tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'The live event {} is in {} state, but this test is negated.', self.live_event_name.name, live_event_state, tooltip=self.tooltip)
        return TestResult.TRUE

class PlayerDayTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'number_of_days': TunableRange(description='\n            The number of days the player has played. This is capped at 100, as that is considered\n            the max experience level for a player.\n            ', tunable_type=int, default=1, minimum=0, maximum=100), 'comparison_operator': TunableOperator(description='\n            The comparison to perform against the number of days played.\n            ', default=sims4.math.Operator.GREATER_OR_EQUAL)}

    def get_expected_args(self) -> 'Dict':
        return {}

    def __call__(self, *args, **kwargs) -> 'TestResult':
        live_event_service = services.get_live_event_service()
        if live_event_service is None:
            return TestResult(False, 'There is no active Live Event service.', tooltip=self.tooltip)
        threshold = sims4.math.Threshold(self.number_of_days, self.comparison_operator)
        days_played = live_event_service.player_experience_level
        if not threshold.compare(days_played):
            operator_symbol = sims4.math.Operator.from_function(self.comparison_operator).symbol
            return TestResult(False, 'Player Day failed comparison test for number of days: Played ({}) {} Required ({}).', days_played, operator_symbol, self.number_of_days, tooltip=self.tooltip)
        return TestResult.TRUE
