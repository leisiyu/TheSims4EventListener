from crafting.crafting_ingredients import IngredientRequirementByDef, IngredientRequirementByTagfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom interactions import ParticipantTypeObject, ParticipantType, ParticipantTypeSinglefrom objects.components.types import CRAFTING_COMPONENTfrom sims4.log import Loggerfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, TunableList, OptionalTunable, TunableEnumEntrylogger = Logger('Crafting_Ingredients_Tests')
class CraftingConsumedIngredientsTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'ingredient_list': TunableList(description='\n            List of ingredient requirements.\n            Test will succeed if all listed ingredient were used in the crafting process.\n            ', tunable=TunableVariant(description='\n            Possible ingredient mapping by object definition of by \n            catalog object Tag.\n            ', ingredient_by_definition=IngredientRequirementByDef.TunableFactory(ingredient_override=(True,)), ingredient_by_tag=IngredientRequirementByTag.TunableFactory())), 'subject': OptionalTunable(description='\n            Participant to look up the crafting process.  \n            Tuning this is not necessary if this loot run within a crafting interaction or during the crafting process.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object))}

    def get_expected_args(self):
        if self.subject is None:
            return {'crafting_process': ParticipantType.CraftingProcess}
        return {'subject': self.subject}

    def __call__(self, subject=(), crafting_process=None, **kwargs):
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
        ingredient_definitions = crafting_process.get_ingredients_object_definitions()
        for tuned_ingredient_factory in self.ingredient_list:
            ingredient_requirement = tuned_ingredient_factory()
            required_count = ingredient_requirement.count_required
            found_count = 0
            for ingredient_definition_tuple in ingredient_definitions:
                if ingredient_requirement.is_matching_ingredient(ingredient_definition_tuple.definition):
                    found_count += ingredient_definition_tuple.count
                    if found_count >= required_count:
                        break
            return TestResult(False, 'Ingredients are not matching!', tooltip=self.tooltip)
        return TestResult.TRUE
