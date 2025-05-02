import servicesimport sims4.logimport sims4.resourcesfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom caches import cached_testfrom interactions import ParticipantType, ParticipantTypeObjectfrom objects.components import typesfrom objects.definition import Definitionfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableReference, TunableList, Tunablefrom traits.preference_enums import GameplayObjectPreferenceTypeslogger = sims4.log.Logger('GameplayObjectPreferenceTests', default_owner='micfisher')
class GameplayObjectPreferenceTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'sims': TunableEnumEntry(description='\n            The Sim(s) to test.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'targets': TunableEnumEntry(description='\n            The object(s) to test.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantType.PickedObject), 'gameplay_object_preference': TunableReference(description='\n            The Gameplay Object Preferences to be tested.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('GameplayObjectPreference',)), 'preference_type': TunableList(description='\n            The gameplay object preference types to check for the existence of on the Sim for the object.\n            ', tunable=TunableEnumEntry(tunable_type=GameplayObjectPreferenceTypes, default=GameplayObjectPreferenceTypes.UNSURE)), 'targetless': Tunable(description='\n            If True, we will ignore Targets tuning, and just check the preference type without\n            considering any specific target. \n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'sims': self.sims, 'targets': self.targets}

    @cached_test
    def __call__(self, sims, targets):
        for sim in sims:
            current_preference_type = sim.trait_tracker.get_gameplay_object_preference_type(self.gameplay_object_preference)
            if self.targetless:
                if current_preference_type in self.preference_type:
                    return TestResult.TRUE
                    for target in targets:
                        if not isinstance(target, Definition):
                            target = target.definition
                        if self.gameplay_object_preference.preference_item == target and current_preference_type in self.preference_type:
                            return TestResult.TRUE
            for target in targets:
                if not isinstance(target, Definition):
                    target = target.definition
                if self.gameplay_object_preference.preference_item == target and current_preference_type in self.preference_type:
                    return TestResult.TRUE
        if self.targetless:
            return TestResult(False, "Sim {}'s gameplay object preference {} does not match: {}", sims, self.gameplay_object_preference, self.preference_type)
        else:
            return TestResult(False, "The picked object {} does not match Sim {}'s gameplay object preference: {}", targets, sims, self.preference_type)

class GameplayObjectStoredSimTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'sims': TunableEnumEntry(description='\n            The Sim(s) to test.\n            ', tunable_type=ParticipantType, default=ParticipantType.PickedSim), 'targets': TunableEnumEntry(description='\n            The object(s) to test.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantType.PickedObject)}

    def get_expected_args(self):
        return {'sims': self.sims, 'targets': self.targets}

    @cached_test
    def __call__(self, sims, targets):
        for sim in sims:
            for target in targets:
                if target is None or sim is None:
                    logger.error('Trying to run Gameplay Object Stored Sim Test with a None Sim and/or Target. sim:{}, target:{}', sim, target)
                    return
                if not sim.is_sim:
                    logger.error('Trying to run Gameplay Object Stored Sim Test on Object {} with a Non Sim Sim {}', target, sim)
                    return
                if target.has_component(types.STORED_SIM_INFO_COMPONENT):
                    stored_sim_info = target.get_component(types.STORED_SIM_INFO_COMPONENT).get_stored_sim_info()
                    if stored_sim_info is not None and sim.id == stored_sim_info.id:
                        return TestResult.TRUE
        return TestResult(False, "The picked Sim(s) {} does not match any Gameplay Object(s) {}'s Stored Sim ID", sims, targets)
