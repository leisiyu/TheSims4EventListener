from interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom sims4.tuning.tunable import TunableEnumEntry, TunableReferencefrom traits.preference_enums import GameplayObjectPreferenceTypesimport sims4.resourcesimport services
class AddGameplayObjectPreferenceLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'description': '\n            This loot will add the specified Gameplay Object Preference.\n            ', 'gameplay_object_preference': TunableReference(description='\n            The Gameplay Object Preference to be added.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('GameplayObjectPreference',)), 'preference_type': TunableEnumEntry(description='\n            The type (unsure, dislike, like, love) associated with this Gameplay Object Preference.\n            ', tunable_type=GameplayObjectPreferenceTypes, default=GameplayObjectPreferenceTypes.UNSURE)}

    def __init__(self, gameplay_object_preference, preference_type, **kwargs):
        super().__init__(**kwargs)
        self._gameplay_object_preference = gameplay_object_preference
        self._preference_type = preference_type

    def _apply_to_subject_and_target(self, subject, target, resolver):
        target.trait_tracker.add_gameplay_object_preference(self._gameplay_object_preference, self._preference_type)
