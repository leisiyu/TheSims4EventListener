from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from crafting.crafting_process import CraftingProcess
    from crafting.recipe import Recipeimport servicesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableEnumEntry, TunableReferencefrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom interactions import ParticipantType, ParticipantTypeSinglefrom objects.components.types import CRAFTING_COMPONENT
class CraftingDefinedIngredientsTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'ingredient_ref': TunableReference(description='\n            Reference to ingredient object definition.\n            Example: gardenFruitGENOnion_01\n            ', manager=services.definition_manager(), pack_safe=True), 'subject': OptionalTunable(description='\n            Participant to look up the crafting process.  \n            Tuning this is not necessary if this loot run within a crafting interaction or during the crafting process.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object))}

    def get_expected_args(self):
        if self.subject is None:
            return {'crafting_process': ParticipantType.CraftingProcess}
        return {'subject': self.subject}

    def __call__(self, subject:'Set[Any]'=(), crafting_process:'CraftingProcess'=None, **kwargs) -> 'TestResult':
        if self.subject is not None:
            subject = next(iter(subject), None)
            if subject is None:
                return TestResult(False, 'No subject passed to CraftingTest', tooltip=self.tooltip)
            if not subject.has_component(CRAFTING_COMPONENT):
                return TestResult(False, 'Crafting process not found when testing {}', self, tooltip=self.tooltip)
            crafting_process = subject.get_crafting_process()
        if crafting_process is None:
            return TestResult(False, 'Crafting process not found when testing {}', self, tooltip=self.tooltip)
        recipe = crafting_process.get_order_or_recipe()
        if recipe is None:
            return TestResult(False, 'No recipe on crafting process!', tooltip=self.tooltip)
        for ingredient in crafting_process.defined_ingredients:
            if ingredient.get_definition().id == self.ingredient_ref.id:
                return TestResult.TRUE
        return TestResult(False, 'Ingredients are not matching!', tooltip=self.tooltip)
