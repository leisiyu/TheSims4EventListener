from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfo
    from sims4.localization import TunableLocalizedStringFactoryfrom aspirations.unfinished_business_aspiration_tuning import UnfinishedBusinessfrom event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEventfrom event_testing.objective_enums import ObjectiveCategoryTypefrom interactions import ParticipantTypeSingleSimfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableFactory, TunableEnumEntry, TunablePackSafeReference, Tunable, TunableList, TunableReference, TunableVariant, OptionalTunable, TunableRange, TunableOperatorfrom caches import cached_testimport servicesimport sims4.loglogger = sims4.log.Logger('AspirationTests', default_owner='nsavalani')
class SelectedAspirationTrackTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.AspirationTrackSelected,)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                    Who or what to apply this test to.\n                    ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'aspiration_track': TunablePackSafeReference(description='\n            The mood that must be active (or must not be active, if disallow is True).\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK))}

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call SelectedAspirationTrackTest with a None value in the sims iterable.')
            else:
                if self.aspiration_track is None:
                    return TestResult(False, '{} failed SelectedAspirationTrackTest check. Aspiration Track is None', target, tooltip=self.tooltip)
                if target._primary_aspiration is not self.aspiration_track:
                    return TestResult(False, '{} failed SelectedAspirationTrackTest check. Track guids: {} is not {}', target, target._primary_aspiration, self.aspiration_track.guid64, tooltip=self.tooltip)
        return TestResult.TRUE

class SelectedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                    Who or what to apply this test to', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'aspiration': TunablePackSafeReference(description='\n            The aspiration that must be active.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION))}

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call SelectedAspirationTest with a None value in the sims iterable.')
            else:
                if self.aspiration is None:
                    return TestResult(False, '{} failed SelectedAspirationTest check. Aspiration is None', target, tooltip=self.tooltip)
                if target.aspiration_tracker is None:
                    return TestResult(False, '{} failed SelectedAspirationTest check. Has no aspiration tracker', target, tooltip=self.tooltip)
                if target.aspiration_tracker._active_aspiration is not self.aspiration:
                    return TestResult(False, '{} failed SelectedAspirationTest check. Active Aspiration {} is not {}', target, target.aspiration_tracker._active_aspiration, self.aspiration, tooltip=self.tooltip)
        return TestResult.TRUE

class HasAnyTimedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'invert': Tunable(description='\n            If checked, the test will pass if a Sim has no timed aspirations.\n            ', tunable_type=bool, default=False)}

    def _run_test(self, target, tooltip=None):
        if target.aspiration_tracker._timed_aspirations:
            if self.invert:
                return TestResult(False, '{} has timed aspirations.'.format(target), tooltip=tooltip)
        elif not self.invert:
            return TestResult(False, '{} has no timed aspirations.'.format(target), tooltip=tooltip)
        return TestResult.TRUE

class HasSpecificTimedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'timed_aspirations': TunableList(description='\n            The specific timed aspirations to test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='TimedAspiration', pack_safe=True), minlength=1, unique_entries=True), 'invert': Tunable(description='\n            If checked, the test will pass if a Sim has none of the specific\n            timed aspirations.\n            ', tunable_type=bool, default=False)}

    def _run_test(self, target, tooltip=None):
        has_aspiration = any(aspiration for aspiration in self.timed_aspirations if aspiration in target.aspiration_tracker._timed_aspirations)
        if has_aspiration:
            if self.invert:
                return TestResult(False, '{} has one of the specified timed aspirations.'.format(target), tooltip=tooltip)
        elif not self.invert:
            return TestResult(False, '{} has none of the specified timed aspirations.'.format(target), tooltip=tooltip)
        return TestResult.TRUE

class TimedAspirationHasObjectiveTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'timed_aspiration': TunablePackSafeReference(description='\n            The timed aspiration whose objectives are being checked. \n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='TimedAspiration'), 'objective': TunablePackSafeReference(description='\n            The objective to test if it was added to the timed aspiration. \n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)), 'invert': Tunable(description='\n            If checked, the test will pass if the timed aspiration\n            does not have the objective.\n            ', tunable_type=bool, default=False)}

    def _run_test(self, target, tooltip=None):
        if self.timed_aspiration is None or self.objective is None:
            if not self.invert:
                return TestResult(False, 'Tuned timed aspiration or objective is none. Field is a PackSafeReference.', tooltip=tooltip)
            return TestResult.TRUE
        aspiration_tracker = target.aspiration_tracker
        if aspiration_tracker is None:
            if not self.invert:
                return TestResult(False, '{} has no aspiration tracker.', target, tooltip=tooltip)
            return TestResult.TRUE
        objectives = aspiration_tracker.get_objectives(self.timed_aspiration)
        if objectives is None:
            if not self.invert:
                return TestResult(False, 'The timed aspiration for {} has no objectives.', target, tooltip=tooltip)
            return TestResult.TRUE
        if self.objective in objectives:
            if self.invert:
                return TestResult(False, 'The timed aspiration for {} has the objective, but result was inverted.', target, tooltip=tooltip)
            return TestResult.TRUE
        if not self.invert:
            return TestResult(False, '{} does not have the timed aspiration {} with objective {}.', target, tooltip=tooltip)
        return TestResult.TRUE

class TimedAspirationHasNumberOfObjectivesTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'timed_aspiration': TunablePackSafeReference(description='\n            The timed aspiration whose objectives are being counted. \n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='TimedAspiration'), 'count': Tunable(description='\n            Number of objectives needed on the timed aspiration. \n            ', tunable_type=int, default=1), 'comparison_operator': TunableOperator(description='\n            The comparison to perform against the count and \n            the number of objectives.\n            ', default=sims4.math.Operator.GREATER_OR_EQUAL), 'include_completed': Tunable(description='\n            If enabled, include completed objectives, otherwise, only\n            uncompleted objectives will be counted. \n            ', tunable_type=bool, default=False)}

    def _run_test(self, target, tooltip=None):
        if self.timed_aspiration is None:
            return TestResult(False, 'Tuned timed aspiration is none. Field is a PackSafeReference.', tooltip=tooltip)
        aspiration_tracker = target.aspiration_tracker
        if aspiration_tracker is None:
            return TestResult(False, '{} has no aspiration tracker.', target, tooltip=tooltip)
        objectives = aspiration_tracker.get_objectives(self.timed_aspiration)
        if objectives is None:
            return TestResult(False, 'The timed aspiration for {} has no objectives.', target, tooltip=tooltip)
        objective_count = 0
        for objective in objectives:
            if aspiration_tracker.objective_completed(objective):
                if self.include_completed:
                    objective_count += 1
                    objective_count += 1
            else:
                objective_count += 1
        threshold = sims4.math.Threshold(self.count, self.comparison_operator)
        if not threshold.compare(objective_count):
            operator_symbol = sims4.math.Operator.from_function(self.comparison_operator).symbol
            return TestResult(False, 'Timed aspiration for {} failed comparison test for number of objectives: Present ({}) {} Required ({}).', target, objective_count, operator_symbol, self.count, tooltip=tooltip)
        return TestResult.TRUE

class HasTimedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'test_behavior': TunableVariant(description='\n            The type of test to run.\n            ', has_any_timed_aspiration=HasAnyTimedAspirationTest.TunableFactory(), has_specific_timed_aspiration=HasSpecificTimedAspirationTest.TunableFactory(), timed_aspiration_has_objective=TimedAspirationHasObjectiveTest.TunableFactory(), timed_aspiration_has_number_of_objectives=TimedAspirationHasNumberOfObjectivesTest.TunableFactory(), default='has_any_timed_aspiration')}

    def get_expected_args(self):
        return {'targets': self.target}

    @cached_test
    def __call__(self, targets):
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        return self.test_behavior._run_test(target_sim, tooltip=self.tooltip)

class CompletedAspirationTrackTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.MilestoneCompleted,)
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'aspiration_tracks': TunableList(description='\n            A list of AspirationTracks to consider. If left empty, the test\n            will consider all AspirationTracks.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK), pack_safe=True)), 'levels': OptionalTunable(description='\n            If enabled, the number of levels that should be completed in a single\n            aspiration track. If disabled, all levels in the aspiration track\n            must be completed.\n            ', tunable=TunableRange(description='\n                The number of levels that should be completed in a single\n                aspiration track.\n                ', tunable_type=int, default=1, minimum=1))}

    def get_expected_args(self):
        return {'targets': self.target}

    @cached_test
    def __call__(self, targets):
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        aspiration_tracker = target_sim.aspiration_tracker
        if aspiration_tracker is None:
            return TestResult(False, 'Target does not have an aspiration tracker.', tooltip=self.tooltip)
        if self.aspiration_tracks:
            aspiration_track_iterable = self.aspiration_tracks
        else:
            aspiration_track_iterable = services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK).types.values()
        for track in aspiration_track_iterable:
            track_completed = True
            levels_completed = 0
            for (_, aspiration_milestone) in track.get_aspirations():
                if aspiration_tracker.milestone_completed(aspiration_milestone):
                    levels_completed += 1
                else:
                    track_completed = False
                    break
            if self.levels is not None:
                if levels_completed >= self.levels:
                    return TestResult.TRUE
                    if track_completed:
                        return TestResult.TRUE
            elif track_completed:
                return TestResult.TRUE
        if self.levels is None:
            return TestResult(False, 'Target has not completed a relevant aspiration.', tooltip=self.tooltip)
        else:
            return TestResult(False, 'Target has not completed level {} in a relevant aspiration', self.levels, tooltip=self.tooltip)

class HasUnfinishedBusinessObjectiveTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'objective': TunablePackSafeReference(description='\n            The objective to test if it was added to the unfinished business aspiration. \n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)), 'invert': Tunable(description='\n            If checked, the test will pass if the timed aspiration\n            does not have the objective.\n            ', tunable_type=bool, default=False)}

    def _run_test(self, target:'SimInfo', tooltip:'TunableLocalizedStringFactory'=None) -> 'TestResult':
        if self.objective is None:
            if not self.invert:
                return TestResult(False, 'Objective is none. Field is a PackSafeReference.', tooltip=tooltip)
            return TestResult.TRUE
        aspiration_tracker = target.aspiration_tracker
        if aspiration_tracker is None:
            if not self.invert:
                return TestResult(False, '{} has no aspiration tracker.', target, tooltip=tooltip)
            return TestResult.TRUE
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return TestResult(False, "Global Unfinished Business Aspiration is None! This shouldn't be possible if EP17 is installed", tooltip=tooltip)
        objectives = aspiration_tracker.get_objectives(unfinished_business_aspiration)
        if objectives is None:
            if not self.invert:
                return TestResult(False, 'The unfinished business aspiration for {} has no objectives.', target, tooltip=tooltip)
            return TestResult.TRUE
        if self.objective in objectives:
            if self.invert:
                return TestResult(False, 'The unfinished business aspiration for {} has the objective, but result was inverted.', target, tooltip=tooltip)
            return TestResult.TRUE
        if not self.invert:
            return TestResult(False, '{} does not have the unfinished business with objective {}.', target, self.objective, tooltip=tooltip)
        return TestResult.TRUE

class HasNumberOfUnfinishedBusinessObjectivesTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'count': Tunable(description='\n            Number of objectives needed on the unfinished business aspiration. \n            ', tunable_type=int, default=1), 'comparison_operator': TunableOperator(description='\n            The comparison to perform against the count and \n            the number of objectives.\n            ', default=sims4.math.Operator.GREATER_OR_EQUAL)}

    def _run_test(self, target:'SimInfo', tooltip:'TunableLocalizedStringFactory'=None) -> 'TestResult':
        aspiration_tracker = target.aspiration_tracker
        if aspiration_tracker is None:
            return TestResult(False, '{} has no aspiration tracker.', target, tooltip=tooltip)
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return TestResult(False, "Global Unfinished Business Aspiration is None! This shouldn't be possible if EP17 is installed", tooltip=tooltip)
        objectives = aspiration_tracker.get_objectives(unfinished_business_aspiration)
        if objectives is None:
            return TestResult(False, 'The unfinished business aspiration for {} has no objectives.', target, tooltip=tooltip)
        objective_count = len(objectives)
        threshold = sims4.math.Threshold(self.count, self.comparison_operator)
        if not threshold.compare(objective_count):
            operator_symbol = sims4.math.Operator.from_function(self.comparison_operator).symbol
            return TestResult(False, 'Unfinished Business aspiration for {} failed comparison test for number of objectives: Present ({}) {} Required ({}).', target, objective_count, operator_symbol, self.count, tooltip=tooltip)
        return TestResult.TRUE

class UnfinishedBusinessObjectiveTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n           Who or what to apply this test to.\n           ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'test_behavior': TunableVariant(description='\n            The type of test to run.\n            ', has_unfinished_business_objective=HasUnfinishedBusinessObjectiveTest.TunableFactory(), has_number_of_unfinished_business_objectives=HasNumberOfUnfinishedBusinessObjectivesTest.TunableFactory(), default='has_unfinished_business_objective')}

    def get_expected_args(self):
        return {'targets': self.target}

    @cached_test
    def __call__(self, targets):
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        return self.test_behavior._run_test(target_sim, tooltip=self.tooltip)

class CurrentUnfinishedBusinessSource(HasTunableSingletonFactory):

    def get_objectives(self, target_sim):
        aspiration_tracker = target_sim.aspiration_tracker
        if aspiration_tracker is None:
            return []
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return []
        current_objectives = aspiration_tracker.get_objectives(unfinished_business_aspiration)
        return current_objectives

class ObjectiveAvailableByTypeTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'category_type': TunableEnumEntry(description='\n            What type of objective is this. Used for tests against types.\n            ', tunable_type=ObjectiveCategoryType, default=ObjectiveCategoryType.NO_CATEGORY_TYPE, invalid_enums=(ObjectiveCategoryType.NO_CATEGORY_TYPE,)), 'current_objectives_source': TunableVariant(description='\n            Where to source the Sim\'s current objectives to test.  \n            These objectives care considered "unavailable" since the Sim already has them in progress.\n            ', unfinished_business=CurrentUnfinishedBusinessSource.TunableFactory(), default='unfinished_business')}

    def get_expected_args(self):
        return {'target': self.target}

    def __call__(self, target):
        objectives = services.get_instance_manager(sims4.resources.Types.OBJECTIVE).types.values()
        target_sim = next(iter(target), None)
        current_objectives = self.current_objectives_source.get_objectives(target_sim)
        if target_sim.aspiration_tracker is None:
            return TestResult(False, '{} is missing an aspiration tracker.', target_sim, tooltip=self.tooltip)
        resolver = SingleSimResolver(target_sim)
        for objective in objectives:
            if objective.category_type != self.category_type:
                pass
            elif objective in current_objectives:
                pass
            elif objective in target_sim.aspiration_tracker.completed_objectives:
                pass
            elif objective.tests_for_picker_availability:
                if objective.tests_for_picker_availability.run_tests(resolver):
                    return TestResult.TRUE
                    return TestResult.TRUE
            else:
                return TestResult.TRUE
        return TestResult(False, 'No Valid Objectives of desired type found.', tooltip=self.tooltip)

class ObjectiveAvailableTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'objective': TunablePackSafeReference(description='\n            The objective to test for. \n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)), 'target': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'current_objectives_source': TunableVariant(description='\n            Where to source the Sim\'s current objectives to test.  \n            These objectives are considered "unavailable" since the Sim already has them in progress.\n            ', unfinished_business=CurrentUnfinishedBusinessSource.TunableFactory(), default='unfinished_business')}

    def get_expected_args(self):
        return {'target': self.target}

    def __call__(self, target):
        target_sim = next(iter(target), None)
        current_objectives = self.current_objectives_source.get_objectives(target_sim)
        if target_sim.aspiration_tracker is None:
            return TestResult(False, '{} is missing an aspiration tracker.', target_sim, tooltip=self.tooltip)
        resolver = SingleSimResolver(target_sim)
        if self.objective in current_objectives:
            return TestResult(False, '{} already has this objective in their list.', target_sim, tooltip=self.tooltip)
        if self.objective in target_sim.aspiration_tracker.completed_objectives:
            return TestResult(False, '{} has already completed this objective.', target_sim, tooltip=self.tooltip)
        if self.objective.tests_for_picker_availability:
            if self.objective.tests_for_picker_availability.run_tests(resolver):
                return TestResult.TRUE
            return TestResult(False, '{} failed the objectives tests.', target_sim, tooltip=self.tooltip)
        else:
            return TestResult.TRUE
