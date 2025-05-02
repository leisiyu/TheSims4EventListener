from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims4.localization import TunableLocalizedStringFactory
    from typing import *from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom interactions import ParticipantType, ParticipantTypeSingle, ParticipantTypeActorTargetSimfrom objects.components import typesfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, Tunable, TunableRange, TunableReference, TunablePackSafeReferencefrom wills.will import WillSectionTypeimport servicesimport sims4logger = sims4.log.Logger('WillTests', default_owner='madang')
class _SimWillExists(HasTunableSingletonFactory):

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            sim_will = will_service.get_sim_will(subject.id)
            if sim_will is not None:
                if negate:
                    return TestResult(False, 'Subject {} already has a SimWill', subject, tooltip=tooltip)
                return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "Subject's will is not yet finalized.", subject, tooltip=tooltip)

class _WillRecipientTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The target of this Will test.  This should be an object participant.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {'target': self.target}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=(), target:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            target = next(iter(target))
            if target is None or subject is None:
                return TestResult(False, 'The subject / target is None, fix in tuning.', tooltip=tooltip)
            if target.has_component(types.STORED_SIM_INFO_COMPONENT):
                will_owner_sim = target.get_stored_sim_info()
                if will_owner_sim is None:
                    return TestResult(False, 'Unable to get will owner from the target.', target, tooltip=tooltip)
                if will_owner_sim.id == subject.id:
                    return TestResult(False, 'Subject cannot be a recipient of their own will.', tooltip=tooltip)
                sim_will = will_service.get_sim_will(will_owner_sim.id)
                if sim_will is not None:
                    if subject.id in sim_will.get_sim_recipients():
                        if negate:
                            return TestResult(False, "Subject {} is a recipient of owner {}'s SimWill.", subject, will_owner_sim, tooltip=tooltip)
                        return TestResult.TRUE
                    household_id = sim_will.get_household_id()
                    household_will = will_service.get_household_will(household_id)
                    if household_will is not None and subject.household_id in household_will.get_household_recipients():
                        if negate:
                            return TestResult(False, "Household of subject {} is a recipient of owner {}'s HouseholdWill.", subject, will_owner_sim, tooltip=tooltip)
                        return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, 'Subject {} is not a recipient of target {} will.', subject, target, tooltip=tooltip)

class _ClaimInheritanceTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The target of this Will test.  This should be an object participant.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {'target': self.target}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=(), target:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            target = next(iter(target))
            if target is None or subject is None:
                return TestResult(False, 'The subject / target is None, fix in tuning.', tooltip=tooltip)
            will_owner_sim = None
            if target.has_component(types.STORED_SIM_INFO_COMPONENT):
                will_owner_sim = target.get_stored_sim_info()
            if will_owner_sim is None:
                return TestResult(False, 'Unable to get will owner from the target.', target, tooltip=tooltip)
            if will_owner_sim.id == subject.id:
                return TestResult(False, 'Invalid subject and target, {} cannot have a claim on their own will.', subject, tooltip=tooltip)
            sim_will = will_service.get_sim_will(will_owner_sim.id)
            if sim_will is not None:
                if sim_will.is_finalized():
                    if subject.id in sim_will.get_claimants():
                        if negate:
                            return TestResult(False, "Subject {} has not yet made their claim on {}'s SimWill.", subject, will_owner_sim, tooltip=tooltip)
                        return TestResult.TRUE
                    if subject.id in sim_will.get_sim_recipients():
                        if negate:
                            return TestResult.TRUE
                        return TestResult(False, "Subject {} has already claimed their inheritance from {}'s SimWill.", subject, will_owner_sim, tooltip=tooltip)
                household_id = sim_will.get_household_id()
                household_will = will_service.get_household_will(household_id)
                if household_will.is_finalized():
                    if subject.household_id in household_will.get_claimants():
                        if negate:
                            return TestResult(False, "Household of subject {} has not yet made their claim on {}'s HouseholdWill.", subject, will_owner_sim, tooltip=tooltip)
                        return TestResult.TRUE
                    if subject.household_id in household_will.get_household_recipients():
                        if negate:
                            return TestResult.TRUE
                        return TestResult(False, "Household of subject {} has already claimed their inheritance from {}'s HouseholdWill.", subject, will_owner_sim, tooltip=tooltip)
        if negate:
            return TestResult.TRUE
        return TestResult(False, 'Subject {} is not a recipient of target {} will.', subject, target, tooltip=tooltip)

class _WillFinalizedTest(HasTunableSingletonFactory):

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            sim_will = will_service.get_sim_will(subject.id)
            if sim_will is None:
                return TestResult(False, 'Subject {} does not have a will.', subject, tooltip=tooltip)
            if sim_will.is_finalized():
                if negate:
                    return TestResult(False, "Subject {}'s will is finalized.", subject, tooltip=tooltip)
                return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "Subject's will is not yet finalized.", subject, tooltip=tooltip)

class _WillSectionSetTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'section': TunableEnumEntry(description="\n            The section of the subject Sim's will to check.\n            ", tunable_type=WillSectionType, default=WillSectionType.BURIAL, pack_safe=True)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            sim_will = will_service.get_sim_will(subject.id)
            if sim_will is not None:
                if self.section == WillSectionType.BURIAL and sim_will.get_burial_preference() is not None:
                    if negate:
                        return TestResult(False, "Subject {}'s SimWill has a burial preference set", subject, tooltip=tooltip)
                    return TestResult.TRUE
                if self.section == WillSectionType.FUNERAL and len(sim_will.get_funeral_activity_preferences()) == will_service.SIM_WILL_FUNERAL_ACTIVITY_PREFERENCE_MAX:
                    if negate:
                        return TestResult(False, "Subject {}'s SimWill is maxed out their funeral activity preference selections.", subject, tooltip=tooltip)
                    return TestResult.TRUE
                if self.section == WillSectionType.EMOTION and sim_will.get_emotion() is not None:
                    if negate:
                        return TestResult(False, "Subject {}'s SimWill has an emotion set.", subject, tooltip=tooltip)
                    return TestResult.TRUE
                if self.section == WillSectionType.NOTE and sim_will.get_note() is not None:
                    if negate:
                        return TestResult(False, "Subject {}'s SimWill has a note set.", subject, tooltip=tooltip)
                    return TestResult.TRUE
                if self.section == WillSectionType.HEIRLOOM and sim_will.get_heirloom_distributions():
                    if negate:
                        return TestResult(False, "Subject {}'s SimWill has heirlooms set.", subject, tooltip=tooltip)
                    return TestResult.TRUE
            household_will = will_service.get_household_will(subject.household_id)
            if household_will is not None:
                if self.section == WillSectionType.DEPENDENT and household_will.get_dependent_distributions():
                    if negate:
                        return TestResult(False, "Subject {}'s Householdwill has dependents set.", subject, tooltip=tooltip)
                    return TestResult.TRUE
                if self.section == WillSectionType.SIMOLEON and household_will.remaining_simoleon_allocation_percentage() == 0.0:
                    if negate:
                        return TestResult(False, "Subject {}'s HouseholdWill has maxed out its simoleon allocation.", subject, tooltip=tooltip)
                    return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "Subject {}'s does not have the tuned section fully set", subject, tooltip=tooltip)

class _WillSimoleonPercentageAllowedTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'percentage': TunableRange(description='\n            Simoleon percentage to check.\n            ', tunable_type=float, default=0.2, minimum=0.0, maximum=1.0)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            household_will = will_service.get_household_will(subject.household_id)
            if household_will is not None and self.percentage <= household_will.remaining_simoleon_allocation_percentage():
                if negate:
                    return TestResult(False, "{} is a permitted percentage for subject {}'s HouseholdWill", self.percentage, subject, tooltip=tooltip)
                return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "{} is not a permitted percentage for subject {}'s HouseholdWill", self.percentage, subject, tooltip=tooltip)

class _SimWillBurialTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'object_definition': TunablePackSafeReference(description="\n            The object definition of the burial preference to check for in the subject's\n            SimWill.\n            ", manager=services.definition_manager())}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            sim_will = will_service.get_sim_will(subject.id)
            if sim_will is not None and sim_will.get_burial_preference() == self.object_definition.id:
                if negate:
                    return TestResult(False, "{} is the burial preference in Subject {}'s SimWill", self.object_definition, subject, tooltip=tooltip)
                return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "{} is not the burial preference for subject {}'s SimWill", self.object_definition, subject, tooltip=tooltip)

class _SimWillFuneralActivityTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'funeral_activity': TunablePackSafeReference(description="\n            The funeral activity to check for in the subject's SimWill.\n            ", manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION), class_restrictions=('SituationActivity',))}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            sim_will = will_service.get_sim_will(subject.id)
            if sim_will is not None and self.funeral_activity.guid64 in sim_will.get_funeral_activity_preferences():
                if negate:
                    return TestResult(False, "{} is one of the Funeral Activities set in Subject {}'s SimWill", self.funeral_activity, subject, tooltip=tooltip)
                return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "{} is not one of the Funeral Activity preferences in subject {}'s SimWill", self.funeral_activity, subject, tooltip=tooltip)

class _SimWillMoodTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'mood': TunablePackSafeReference(description="\n            The mood to check for in the subject's SimWill.\n            ", manager=services.get_instance_manager(sims4.resources.Types.MOOD))}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=()) -> 'TestResult':
        will_service = services.get_will_service()
        if will_service is not None:
            subject = next(iter(subject))
            if subject is None:
                return TestResult(False, 'The subject is None, fix in tuning.', tooltip=tooltip)
            sim_will = will_service.get_sim_will(subject.id)
            if sim_will is not None and self.mood == sim_will.get_emotion():
                if negate:
                    return TestResult(False, "{} is the will emotion in Subject {}'s SimWill", self.mood, subject, tooltip=tooltip)
                return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, "{} is not the will emotion in subject {}'s SimWill", self.mood, subject, tooltip=tooltip)

class _SimRecipientObjectTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The target of this Will test.  This should be an object participant.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {'target': self.target}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=(), target:'Tuple'=()) -> 'TestResult':
        subject = next(iter(subject))
        target = next(iter(target))
        if subject is None or target is None:
            return TestResult(False, 'The subject/target is None, fix in tuning.', tooltip=tooltip)
        will_service = services.get_will_service()
        if will_service is not None and target.has_component(types.STORED_SIM_INFO_COMPONENT):
            will_owner_sim = target.get_stored_sim_info()
            if will_owner_sim is not None:
                sim_will = will_service.get_sim_will(will_owner_sim.id)
                if sim_will is not None and subject.id in sim_will.get_heirloom_distributions().values():
                    if negate:
                        return TestResult(False, '{} is receiving heirloom objects in SimWill', subject, tooltip=tooltip)
                    return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, '{} is not receiving heirloom objects in SimWill OR SimWill does not exist', subject, tooltip=tooltip)

class _SimRecipientSimoleonThresholdTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'threshold': TunableRange(description='\n            The simoleon threshold percentage to test.\n            ', tunable_type=float, default=0.5, minimum=0.0, maximum=1.0), 'is_inclusive': Tunable(description='\n            If checked, operation is inclusive.\n            ', tunable_type=bool, default=True), 'target': TunableEnumEntry(description='\n            The target of this Will test.  This should be an object participant.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {'target': self.target}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=(), target:'Tuple'=()) -> 'TestResult':
        subject = next(iter(subject))
        target = next(iter(target))
        if subject is None or target is None:
            return TestResult(False, 'The subject/target is None, fix in tuning.', tooltip=tooltip)
        will_service = services.get_will_service()
        test_result = True
        if target.has_component(types.STORED_SIM_INFO_COMPONENT):
            will_owner_sim = target.get_stored_sim_info()
            if will_owner_sim is not None:
                household_will = will_service.get_household_will(will_owner_sim.id)
                if household_will is not None:
                    simoleon_distributions = household_will.get_simoleon_distributions()
                    if subject.household_id in simoleon_distributions:
                        test_result = simoleon_distributions[subject.household_id] > self.threshold
                    if self.is_inclusive:
                        test_result = test_result or simoleon_distributions[subject.household_id] == self.threshold
        if will_service is not None and negate:
            test_result = not test_result
        if test_result:
            return TestResult.TRUE
        return TestResult(False, 'The simoleon distribution for {} does not meet the threshold.', subject, tooltip=tooltip)

class _SimRecipientChildrenTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The target of this Will test.  This should be an object participant.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def _get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {'target': self.target}

    def _evaluate(self, negate:'bool', tooltip:'TunableLocalizedStringFactory', subject:'Tuple'=(), target:'Tuple'=()) -> 'TestResult':
        subject = next(iter(subject))
        target = next(iter(target))
        if subject is None or target is None:
            return TestResult(False, 'The subject/target is None, fix in tuning.', tooltip=tooltip)
        will_service = services.get_will_service()
        if will_service is not None and target.has_component(types.STORED_SIM_INFO_COMPONENT):
            will_owner_sim = target.get_stored_sim_info()
            if will_owner_sim is not None:
                household_will = will_service.get_household_will(will_owner_sim.id)
                if household_will is not None and subject.household_id in household_will.get_dependent_distributions():
                    if negate:
                        return TestResult(False, 'The household belonging to {} is receiving dependents.', subject, tooltip=tooltip)
                    return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, 'The household belonging to {} is not receiving dependents.', subject, tooltip=tooltip)

class WillTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'test_type': TunableVariant(description='\n            The type of will test to run.\n            ', sim_will_exists=_SimWillExists.TunableFactory(), will_recipient=_WillRecipientTest.TunableFactory(), claim_inheritance=_ClaimInheritanceTest.TunableFactory(), will_finalized=_WillFinalizedTest.TunableFactory(), will_section_set=_WillSectionSetTest.TunableFactory(), will_simoleon_percentage_allowed=_WillSimoleonPercentageAllowedTest.TunableFactory(), sim_will_burial=_SimWillBurialTest.TunableFactory(), sim_will_funeral_activity=_SimWillFuneralActivityTest.TunableFactory(), sim_will_mood=_SimWillMoodTest.TunableFactory(), sim_object_recipient=_SimRecipientObjectTest.TunableFactory(), sim_simoleon_recipient=_SimRecipientSimoleonThresholdTest.TunableFactory(), sim_dependent_recipient=_SimRecipientChildrenTest.TunableFactory()), 'subject': TunableEnumEntry(description='\n            The sim on whom the will test will apply to.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'negate': Tunable(description='\n            Returns the opposite of the test results.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self) -> 'Dict[str, ParticipantType]':
        args = self.test_type._get_expected_args()
        args['subject'] = self.subject
        return args

    def __call__(self, *args, **kwargs) -> 'TestResult':
        return self.test_type._evaluate(self.negate, self.tooltip, *args, **kwargs)
