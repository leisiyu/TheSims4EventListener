from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims4.tuning.instances import HashedTunedInstanceMetaclass
    from objects.components.inventory import InventoryComponentfrom distributor.shared_messages import IconInfoDatafrom interactions.base.picker_interaction import ObjectPickerInteractionfrom objects.collection_manager import ObjectCollectionDatafrom objects.definition import Definitionfrom sims.sim_info import SimInfofrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, Tunablefrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import ObjectPickerRowimport randomfrom crafting.crafting_ingredients import IngredientRequirementByDeffrom crafting.crafting_interactions import StartCraftingMixinfrom crafting.recipe import Recipefrom interactions.base.super_interaction import SuperInteractionfrom jewelry_crafting.jewelry_crafting_tuning import JewelryCraftingTuning
class StartCraftingRandomJewelSuperInteraction(StartCraftingMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'use_inventory_materials': Tunable(description='\n            If checked, the sim will use materials from its/table inventory.\n            If not checked, the sim will purchase from the list of purchasable materials \n            ', tunable_type=bool, default=False)}

    def return_available_materials(self, purchasable:'List[HashedTunedInstanceMetaclass]', non_purchasable:'List[HashedTunedInstanceMetaclass]') -> 'Tuple[List[HashedTunedInstanceMetaclass], bool]':
        if not self.use_inventory_materials:
            return (purchasable, False)
        available_materials = []
        all_materials = purchasable + non_purchasable
        in_inventory = False
        for material in all_materials:
            sim_inventory = self.sim.inventory_component
            workbench_inventory = self.target.inventory_component
            count = sim_inventory.get_count(material)
            count += workbench_inventory.get_count(material) if workbench_inventory is not None else 0
            if count > 0:
                available_materials.append(material)
                in_inventory = True
        if not available_materials:
            available_materials = purchasable
        return (available_materials, in_inventory)

    def _run_interaction_gen(self, timeline):
        recipes = JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes
        available_recipes = []
        for recipe in recipes:
            if not recipe.skill_test is None:
                if recipe.skill_test(test_targets=(self.sim.sim_info,)):
                    available_recipes.append(recipe)
            available_recipes.append(recipe)
        (available_metals, metal_in_inventory) = self.return_available_materials(JewelryCraftingTuning.JEWELRY_DATA.purchasable_metals, JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_metals)
        (available_crystals, crystal_in_inventory) = self.return_available_materials(JewelryCraftingTuning.JEWELRY_DATA.purchasable_crystals, JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_crystals)
        recipe = random.choice(available_recipes)
        random_metal = random.choice(available_metals)
        metal_ingredient = IngredientRequirementByDef(ingredient_ref=random_metal)
        consumed_ingredients = []
        if metal_in_inventory:
            consumed_ingredients.append(metal_ingredient)
        if JewelryCraftingTuning.JEWELRY_NO_CRYSTAL_NEEDED_TAG in recipe.final_product_definition.build_buy_tags:
            defined_ingredients = [metal_ingredient]
        else:
            random_crystal = random.choice(available_crystals)
            crystal_ingredient = IngredientRequirementByDef(ingredient_ref=random_crystal)
            defined_ingredients = [metal_ingredient, crystal_ingredient]
            if crystal_in_inventory:
                consumed_ingredients.append(crystal_ingredient)
        return self._handle_begin_crafting(recipe, self.sim, defined_ingredients=defined_ingredients, ingredients=consumed_ingredients)

class JewelryCraftingMaterialPickerInteraction(ObjectPickerInteraction):

    class _MaterialVariant:

        def create_rows_gen(self, purchasable:'Set[HashedTunedInstanceMetaclass]', non_purchasable:'Set[HashedTunedInstanceMetaclass]', get_description_from_buff:'bool', sim_info:'SimInfo', is_shape_design:'bool', prices:'Dict[Definition, int]'={}, **kwargs) -> 'List[HashedTunedInstanceMetaclass]':
            picked = kwargs['picked']
            picked_definition = self.get_picked_object_definition(picked.definition.id, purchasable, non_purchasable)
            if picked_definition is not None:
                for row in self.create_row_gen(picked_definition, True, get_description_from_buff, sim_info, prices, is_shape_design, **kwargs):
                    yield row
            else:
                all_rows = []
                for obj_def in purchasable + non_purchasable:
                    is_purchasable = obj_def in purchasable
                    rows = list(self.create_row_gen(obj_def, is_purchasable, get_description_from_buff, sim_info, prices, is_shape_design, **kwargs))
                    all_rows.extend(rows)
                sorted_rows = sorted(all_rows, key=lambda sorted_row: (sorted_row.count == 0, sorted_row.count, sorted_row.cost), reverse=False) if not is_shape_design else all_rows
                for row in sorted_rows:
                    yield row

        def get_description_string(self, definition:'Definition') -> 'LocalizedString':
            return LocalizationHelperTuning.get_object_description(definition)

        def get_tooltip(self, definition:'Definition', purchasable:'bool', rarity_text:'LocalizedString', cost:'int', count:'int', unlock_level:'int') -> 'List[LocalizedString]':
            if purchasable:
                tooltip_strings = [LocalizationHelperTuning.get_object_name(definition), LocalizationHelperTuning.get_colored_text(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.cost_color, LocalizationHelperTuning.get_money(cost)), LocalizationHelperTuning.get_object_description(definition)]
                if JewelryCraftingTuning.JEWELRY_NO_CRYSTAL_NEEDED_TAG in definition.build_buy_tags:
                    tooltip_strings.append(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.design_without_crystal_text)
            else:
                recipe = self.get_recipe(definition)
                tooltip_strings = [JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.not_purchasable_design_text(recipe.required_skill_level)]
            return tooltip_strings

        def create_row_gen(self, definition:'Definition', purchasable:'bool', get_description_from_buff:'bool', sim_info:'SimInfo', prices:'Dict[Definition, int]', is_shape_design:'bool', **kwargs) -> 'ObjectPickerRow':
            name = LocalizationHelperTuning.get_object_name(definition)
            (_, collectible_data, _) = ObjectCollectionData.get_collection_info_by_definition(definition.id)
            rarity_text = None
            rarity = collectible_data.rarity
            rarity_text = ObjectCollectionData.COLLECTION_RARITY_MAPPING[rarity].text_value
            sim_inventory = sim_info.inventory_component
            workbench = kwargs['target_object']
            workbench_inventory = workbench.inventory_component
            count = 0
            count = sim_inventory.get_count(definition)
            count += workbench_inventory.get_count(definition) if workbench_inventory is not None else 0
            cost = prices[definition] if collectible_data is not None and is_shape_design or definition in prices else int(definition.price*JewelryCraftingTuning.JEWELRY_DATA.purchase_multiplier)
            tags = list(definition.get_tags())
            tags += (JewelryCraftingTuning.MATERIAL_IN_INVENTORY_TAG,)
            tooltip_strings = self.get_tooltip(definition, purchasable, rarity_text, cost, count, 0)
            row = ObjectPickerRow(def_id=definition.id, name=name, icon_info=IconInfoData(obj_def_id=definition.id), cost=cost, rarity_text=rarity_text, count=count, is_enable=count > 0 and count > 0 or purchasable, tag_list=tags, discounted_cost=cost if count > 0 else 0, row_tooltip=lambda *_: LocalizationHelperTuning.get_new_line_separated_strings(*tooltip_strings), row_description=self.get_description_string(definition))
            yield row

        def get_picked_object_definition(self, definition_id:'int', purchasable:'Set[Definition]', non_purchasble:'Set[Definition]') -> 'Definition':
            for material in purchasable:
                if material.id == definition_id:
                    return material
            for material in non_purchasble:
                if material.id == definition_id:
                    return material

    class _ShapeMaterial(_MaterialVariant, HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def get_recipe(self, definition:'Definition') -> 'Recipe':
            for recipe in JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes:
                if recipe.final_product_definition == definition:
                    return recipe

        def get_shape_rows(self, sim_info:'SimInfo') -> 'List[ObjectPickerRow]':
            prices = {}
            unlocked_shape_definitions = []
            locked_shape_definitions = []
            for recipe in JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes:
                prices[recipe.final_product_definition] = recipe.crafting_price
                if recipe.skill_test is None or recipe.skill_test(test_targets=(sim_info,)):
                    unlocked_shape_definitions.append(recipe.final_product_definition)
                else:
                    locked_shape_definitions.append(recipe.final_product_definition)
            return (unlocked_shape_definitions, locked_shape_definitions, prices)

        def picker_rows_gen(self, inst, target, context, **kwargs):
            (unlocked_shape_definitions, locked_shape_definitions, prices) = self.get_shape_rows(inst.sim)
            for row in self.create_rows_gen(unlocked_shape_definitions, locked_shape_definitions, False, inst.sim, True, prices, **kwargs):
                yield row

    class _CrystalMaterial(_MaterialVariant, HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def get_description_string(self, definition:'Definition') -> 'LocalizedString':
            return self.get_effects_string(definition)

        def get_effects_string(self, definition:'Definition') -> 'LocalizedString':
            effects_list = None
            if definition in JewelryCraftingTuning.JEWELRY_DATA.crystal_definition_effects_strings_map:
                strings_effects = []
                for text in JewelryCraftingTuning.JEWELRY_DATA.crystal_definition_effects_strings_map[definition]:
                    strings_effects.append(text(definition))
                effects_list = LocalizationHelperTuning.get_new_line_separated_strings(*strings_effects)
            return effects_list

        def get_tooltip(self, definition:'Definition', purchasable:'bool', rarity_text:'LocalizedString', cost:'int', count:'int', unlock_level:'int') -> 'List[LocalizedString]':
            tooltip_strings = [LocalizationHelperTuning.get_object_name(definition), LocalizationHelperTuning.get_colored_text(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.rarity_color, rarity_text)]
            effects_string = self.get_effects_string(definition)
            if effects_string is not None:
                tooltip_strings.append(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.if_charged_text)
                tooltip_strings.append(LocalizationHelperTuning.get_colored_text(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.effects_color, effects_string))
            if purchasable or count == 0:
                tooltip_strings.append(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.not_purchasable_crystal_text)
            return tooltip_strings

        def picker_rows_gen(self, inst, target, context, **kwargs):
            for row in self.create_rows_gen(JewelryCraftingTuning.JEWELRY_DATA.purchasable_crystals, JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_crystals, True, inst.sim, False, **kwargs):
                yield row

    class _MetalMaterial(_MaterialVariant, HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def get_tooltip(self, definition:'Definition', purchasable:'bool', rarity_text:'LocalizedString', cost:'int', count:'int', unlock_level:'int') -> 'List[LocalizedString]':
            tooltip_strings = [LocalizationHelperTuning.get_object_name(definition), LocalizationHelperTuning.get_colored_text(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.rarity_color, rarity_text), LocalizationHelperTuning.get_object_description(definition)]
            if purchasable or count == 0:
                tooltip_strings.append(JewelryCraftingTuning.JEWELRY_DATA.material_picker_tooltip.not_purchasable_metal_text)
            return tooltip_strings

        def picker_rows_gen(self, inst, target, context, **kwargs):
            for row in self.create_rows_gen(JewelryCraftingTuning.JEWELRY_DATA.purchasable_metals, JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_metals, True, inst.sim, False, **kwargs):
                yield row

    class _GemstoneMaterial(_MaterialVariant, HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def get_recipe(self, definition:'Definition') -> 'Recipe':
            for recipe in JewelryCraftingTuning.JEWELRY_DATA.gemstone_cutting_recipes:
                if recipe.final_product_definition == definition:
                    return recipe

        def get_gemstone_rows(self, sim_info:'SimInfo') -> 'List[ObjectPickerRow]':
            prices = {}
            unlocked_gemstone_definitions = []
            locked_gemstone_definitions = []
            for recipe in JewelryCraftingTuning.JEWELRY_DATA.gemstone_cutting_recipes:
                prices[recipe.final_product_definition] = recipe.crafting_price
                if recipe.skill_test is None or recipe.skill_test(test_targets=(sim_info,)):
                    unlocked_gemstone_definitions.append(recipe.final_product_definition)
                else:
                    locked_gemstone_definitions.append(recipe.final_product_definition)
            return (unlocked_gemstone_definitions, locked_gemstone_definitions, prices)

        def picker_rows_gen(self, inst, target, context, **kwargs):
            (unlocked_gemstone_definitions, locked_gemstone_definitions, prices) = self.get_gemstone_rows(inst.sim)
            for row in self.create_rows_gen(unlocked_gemstone_definitions, locked_gemstone_definitions, False, inst.sim, True, prices, **kwargs):
                yield row

    INSTANCE_TUNABLES = {'material': TunableVariant(description='\n            Material to be used in the picker\n            ', shape=_ShapeMaterial.TunableFactory(), metal=_MetalMaterial.TunableFactory(), crystal=_CrystalMaterial.TunableFactory(), gemstone=_GemstoneMaterial.TunableFactory())}

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        for row in cls.material.picker_rows_gen(inst, target, context, **kwargs):
            yield row

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        return True
