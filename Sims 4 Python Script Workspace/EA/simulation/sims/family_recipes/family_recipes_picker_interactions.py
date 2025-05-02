from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.script_object import ScriptObject
    from crafting.recipe import Recipe
    from sims.family_recipes.family_recipes_tracker import FamilyRecipesTracker, FamilyRecipe
    from sims.unlock_tracker import UnlockTracker
    from objects.components.inventory import InventoryComponent
    from sims.sim_info import SimInfofrom crafting.crafting_interactions import StartCraftingSuperInteractionfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom protocolbuffers.Localization_pb2 import LocalizedStringfrom interactions.base.picker_interaction import ObjectPickerInteractionfrom ui.ui_dialog_picker import ObjectPickerRowfrom distributor.shared_messages import IconInfoDatafrom sims.family_recipes.family_recipes_tuning import FamilyRecipesTuningfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInitfrom objects.definition import Definitionfrom sims4.localization import LocalizationHelperTuning, ConcatenationStylefrom sims4.utils import flexmethodfrom singletons import DEFAULTimport servicesfrom sims4.resources import Typesfrom crafting.crafting_ingredients import IngredientRequirementByDef
class StartCraftingFamilyRecipeSuperInteraction(StartCraftingSuperInteraction):

    class _ModeVariant:

        def on_multi_choice_selected(self, picked_choice, **kwargs):
            pass

    class _CreationVariant(_ModeVariant, HasTunableSingletonFactory, AutoFactoryInit):

        @staticmethod
        def use_parent_method():
            return True

    class _PreparationVariant(_ModeVariant, HasTunableSingletonFactory, AutoFactoryInit):

        @staticmethod
        def use_parent_method():
            return False

    INSTANCE_TUNABLES = {'mode': TunableVariant(description='\n            Mode to be used to filter the recipes\n            ', creation=_CreationVariant.TunableFactory(), preparation=_PreparationVariant.TunableFactory())}

    def _setup_dialog(self, dialog, crafter=DEFAULT, order_count=1, **kwargs):
        crafter = self.sim if crafter is DEFAULT else crafter
        dialog.set_target_sim(crafter)
        if self.mode.use_parent_method():
            target = kwargs['target_object']
            for row in self.picker_rows_gen(target=target, context=self.context, crafter=crafter, order_count=order_count, **kwargs):
                row.option_id = row.tag.guid64
                dialog.add_row(row)
        else:
            for row in self.picker_rows_gen(target=self.target, context=self.context, crafter=crafter, order_count=order_count, **kwargs):
                if crafter is not None:
                    family_recipes_tracker = crafter.sim_info.family_recipes_tracker
                if family_recipes_tracker is None:
                    return
                buff_manager = services.get_instance_manager(Types.BUFF)
                definition_manager = services.definition_manager()
                buff_id = row.buff_id
                family_recipe = family_recipes_tracker.get_family_recipe_by_buff(buff_id)
                if family_recipe is not None:
                    extra_ingredient = definition_manager.get(family_recipe.ingredient_id)
                    buff = buff_manager.get(family_recipe.buff_id)
                    buff_cost = 0
                    cost_modifier_size = family_recipes_tracker.get_family_recipe_cost_modifier(row.tag)
                    if buff is not None:
                        buff_cost = round(buff.buff_type.buff_cost*cost_modifier_size)
                    family_recipe_price = extra_ingredient.price + buff_cost
                    recipe_name = FamilyRecipesTuning.FAMILY_RECIPE_DATA.family_recipe_text.family_recipe_name_text(family_recipe.recipe_name)
                    row.name = recipe_name
                    row.price = row.price + family_recipe_price
                    row.price_with_ingredients = row.price_with_ingredients + family_recipe_price
                    row.price_with_only_prepped_ingredients = row.price_with_only_prepped_ingredients + family_recipe_price
                    row.price_with_both_fresh_prepped_ingredients = row.price_with_both_fresh_prepped_ingredients + family_recipe_price
                    row.discounted_price = row.discounted_price + family_recipe_price
                    dialog.add_row(row)
        dialog.set_picker_columns_override(self._get_valid_columns(dialog=dialog))

    def get_valid_recipe_list(self, candidate_ingredients:'Sequence[ScriptObject]'=(), ingredient_cost_only:'bool'=False, crafter=None) -> 'List[Recipe]':
        recipes = super(StartCraftingFamilyRecipeSuperInteraction, self).get_valid_recipe_list(crafter)
        if self.mode.use_parent_method():
            return recipes
        filtered_recipes = []
        if crafter is not None:
            family_recipes_tracker = crafter.sim_info.family_recipes_tracker
            if family_recipes_tracker is None:
                return
            family_recipes = family_recipes_tracker.get_family_recipes()
            for recipe_obj in recipes:
                for family_recipe in family_recipes:
                    (buff_id, recipe) = recipe_obj
                    if not family_recipe.recipe_id == recipe.guid64:
                        if recipe.base_recipe is not None and family_recipe.recipe_id == recipe.base_recipe.guid64:
                            filtered_recipes.append((family_recipe.buff_id, recipe))
                    filtered_recipes.append((family_recipe.buff_id, recipe))
        return filtered_recipes

    @classmethod
    def _try_build_ingredient_requirements_for_recipe(self, recipe, recipe_to_requirements_map, requirements_to_ingredients_map, crafter=None, buff_id=0, all_candidate_ingredients=None):
        requirements = []
        if self.mode.use_parent_method():
            return super(StartCraftingFamilyRecipeSuperInteraction, self)._try_build_ingredient_requirements_for_recipe(recipe, recipe_to_requirements_map, requirements_to_ingredients_map)
        if crafter is not None:
            family_recipes_tracker = crafter.sim_info.family_recipes_tracker
            if family_recipes_tracker is None:
                return
            definition_manager = services.definition_manager()
            ingredient_exist = False
            family_recipe = family_recipes_tracker.get_family_recipe_by_buff(buff_id)
            if recipe in recipe_to_requirements_map:
                requirements_factories = recipe_to_requirements_map[recipe]
            else:
                requirements_factories = []
            ingredients_used = {}
            if family_recipe is not None:
                extra_ingredient = definition_manager.get(family_recipe.ingredient_id)
                for tuned_ingredient_factory in requirements_factories:
                    candidate_ingredients = requirements_to_ingredients_map.get(tuned_ingredient_factory, [])
                    ingredient_requirement = tuned_ingredient_factory()
                    if len(ingredient_requirement._ingredients) == 0 and hasattr(ingredient_requirement, '_definition'):
                        if extra_ingredient.id == ingredient_requirement._definition.id:
                            ingredient_requirement._count_required += 1
                            ingredient_exist = True
                    else:
                        for ingredient in ingredient_requirement._ingredients:
                            if extra_ingredient.id == ingredient.ingredient_object.definition.id:
                                ingredient_requirement._count_required += 1
                                ingredient_exist = True
                                break
                    ingredient_requirement.attempt_satisfy_ingredients(candidate_ingredients, ingredients_used)
                    requirements.append(ingredient_requirement)
                if not ingredient_exist:
                    self.add_extra_ingredient_with_satisfaction_rule(requirements, extra_ingredient, all_candidate_ingredients, ingredients_used)
        return requirements

    @staticmethod
    def add_extra_ingredient_with_satisfaction_rule(requirements, extra_ingredient, all_candidate_ingredients, ingredients_used):
        ingredient_requirement_definition = IngredientRequirementByDef(ingredient_ref=extra_ingredient, count=1)
        for ingredient in FamilyRecipesTuning.FAMILY_RECIPE_DATA.ingredients:
            ingredient_factory = ingredient()
            if len(ingredient_factory._ingredients) == 0 and hasattr(ingredient_factory, '_definition'):
                if extra_ingredient.id == ingredient_factory._definition.id:
                    ingredient_requirement_definition.attempt_satisfy_ingredients(all_candidate_ingredients, ingredients_used)
                    requirements.append(ingredient_requirement_definition)
                    return
                    ingredients_by_tag = list(services.definition_manager().get_definitions_for_tags_gen((ingredient_factory._tag,)))
                    for definition_ingredient in ingredients_by_tag:
                        if extra_ingredient.id == definition_ingredient.id:
                            ingredient_requirement_definition.attempt_satisfy_ingredients(all_candidate_ingredients, ingredients_used)
                            requirements.append(ingredient_requirement_definition)
                            return
            else:
                ingredients_by_tag = list(services.definition_manager().get_definitions_for_tags_gen((ingredient_factory._tag,)))
                for definition_ingredient in ingredients_by_tag:
                    if extra_ingredient.id == definition_ingredient.id:
                        ingredient_requirement_definition.attempt_satisfy_ingredients(all_candidate_ingredients, ingredients_used)
                        requirements.append(ingredient_requirement_definition)
                        return

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            tag_obj = dialog.get_single_result_tag()
            family_recipes_tracker = dialog.owner.sim_info.family_recipes_tracker
            if family_recipes_tracker is None:
                return False
            family_recipe = family_recipes_tracker.get_family_recipe_by_buff(dialog.picker_rows[dialog.picked_results[0]].buff_id)
            tag_obj.resumable_by_different_sim = False
            if family_recipe is None:
                return False
            self.on_choice_selected(tag_obj, ingredient_check=dialog.ingredient_check, prepped_ingredient_check=dialog.prepped_ingredient_check, family_recipe=family_recipe)

class FamilyCreationItemPickerInteraction(ObjectPickerInteraction):

    class _ItemVariant:

        def create_rows_gen(self, items:'Set[HashedTunedInstanceMetaclass]', family_recipes_tracker:'FamilyRecipesTracker'=None, unlock_tracker:'UnlockTracker'=None, sim_info:'SimInfo'=None, **kwargs) -> 'List[HashedTunedInstanceMetaclass]':
            for obj_def in items:
                rows = list(self.create_row_gen(obj_def, family_recipes_tracker, unlock_tracker, sim_info, **kwargs))
                yield from rows

        def get_description_string(self, definition:'Definition') -> 'LocalizedString':
            return LocalizationHelperTuning.get_object_description(definition)

        def get_tooltip(self, definition:'Definition') -> 'List[LocalizedString]':
            tooltip_strings = [LocalizationHelperTuning.get_object_name(definition), LocalizationHelperTuning.get_object_description(definition)]
            return tooltip_strings

        def create_row_gen(self, definition:'Definition', family_recipes_tracker:'FamilyRecipesTracker'=None, unlock_tracker:'UnlockTracker'=None, sim_info:'SimInfo'=None, **kwargs) -> 'ObjectPickerRow':
            name = LocalizationHelperTuning.get_object_name(definition)
            item_id = definition.id
            icon = IconInfoData(obj_def_id=definition.id)
            rarity_text = None
            cost = definition.price
            tooltip_strings = self.get_tooltip(definition)
            tags = list(definition.get_tags())
            sim_inventory = sim_info.get_sim_instance().inventory_component
            count = sim_inventory.get_count(definition)
            row = ObjectPickerRow(def_id=item_id, name=name, icon_info=icon, cost=cost, rarity_text=rarity_text, is_enable=True, count=count, discounted_cost=cost if count > 0 else 0, tag_list=tags, row_tooltip=lambda *_: LocalizationHelperTuning.get_new_line_separated_strings(*tooltip_strings), row_description=self.get_description_string(definition))
            yield row

        def get_picked_object_definition(self, definition_id:'int', items:'Set[Definition]') -> 'Definition':
            for item in items:
                if item.id == definition_id:
                    return item

    class _BuffItem(_ItemVariant, HasTunableSingletonFactory, AutoFactoryInit):

        def get_tooltip(self, existing_family_recipe:'FamilyRecipe', is_enabled:'bool', locked_tooltip:'LocalizedString') -> 'List[LocalizedString]':
            tooltip_strings = []
            if existing_family_recipe is not None:
                tooltip_strings.append(FamilyRecipesTuning.FAMILY_RECIPE_DATA.family_recipe_text.buff_already_in_use_text(existing_family_recipe.recipe_name))
            if not is_enabled:
                tooltip_strings.append(locked_tooltip if locked_tooltip is not None else FamilyRecipesTuning.FAMILY_RECIPE_DATA.family_recipe_text.locked_buff)
            return tooltip_strings

        def get_buff_description_row(self, buff_description:'LocalizedString') -> 'LocalizedString':
            strings_description = [buff_description]
            description_row = LocalizationHelperTuning.get_new_line_separated_strings(*strings_description)
            return description_row

        def create_row_gen(self, buff, family_recipes_tracker:'FamilyRecipesTracker'=None, unlock_tracker:'UnlockTracker'=None, sim_info:'SimInfo'=None, **kwargs) -> 'ObjectPickerRow':
            buff_reference = buff.buff_reference
            name = buff_reference.buff_type.buff_name
            buff_cost = buff_reference.buff_type.buff_cost
            icon = IconInfoData(buff.icon)
            buff_id = buff_reference.buff_type.guid64
            existing_family_recipe = family_recipes_tracker.get_family_recipe_by_buff(buff_id)
            is_enabled = True
            is_enabled = unlock_tracker.is_unlocked(buff_reference.buff_type)
            buff_count = 0 if buff.locked and existing_family_recipe is None else 1
            tooltip_strings = self.get_tooltip(existing_family_recipe, is_enabled, buff.locked_tooltip)
            row_tooltip = None if not tooltip_strings else lambda *_: LocalizationHelperTuning.get_new_line_separated_strings(*tooltip_strings)
            row_description = self.get_buff_description_row(buff.buff_description)
            row = ObjectPickerRow(object_id=buff_id, name=name(), cost=buff_cost, count=buff_count, icon_info=icon, is_enable=is_enabled, row_description=row_description, row_tooltip=row_tooltip)
            yield row

        def picker_rows_gen(self, family_recipes_tracker:'FamilyRecipesTracker', unlock_tracker:'UnlockTracker', sim_info:'SimInfo', **kwargs):

            def _key_func(buff) -> 'int':
                if buff.locked and unlock_tracker.is_unlocked(buff.buff_reference.buff_type):
                    return 0
                return 1

            items = sorted(FamilyRecipesTuning.FAMILY_RECIPE_DATA.buffs, key=_key_func)
            for row in self.create_rows_gen(items, family_recipes_tracker, unlock_tracker, sim_info, **kwargs):
                yield row

    class _IngredientItem(_ItemVariant, HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def get_tooltip(self, definition:'Definition') -> 'List[LocalizedString]':
            tooltip_strings = [LocalizationHelperTuning.get_object_name(definition)]
            return tooltip_strings

        def picker_rows_gen(self, family_recipes_tracker:'FamilyRecipesTracker'=None, unlock_tracker:'UnlockTracker'=None, sim_info:'SimInfo'=None, **kwargs):
            filtered_defs = []
            ingredient_list = [ingredient_requirement_factory() for ingredient_requirement_factory in FamilyRecipesTuning.FAMILY_RECIPE_DATA.ingredients]
            for ingredient_definition in ingredient_list:
                definition = ingredient_definition.get_definition()
                if definition is None:
                    filtered_defs.extend(list(services.definition_manager().get_definitions_for_tags_gen((ingredient_definition._tag,))))
                else:
                    filtered_defs.append(definition)
            for row in self.create_rows_gen(filtered_defs, None, None, sim_info, **kwargs):
                yield row

    class _FamilyRecipeItem(_ItemVariant, HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def get_tooltip(self, definition:'Definition', buff, extra_ingredient:'Definition') -> 'List[LocalizedString]':
            tooltip_strings = [LocalizationHelperTuning.NAME_VALUE_PAIR_STRUCTURE(FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.base_recipe_notebook_text(), LocalizationHelperTuning.get_object_name(definition)), LocalizationHelperTuning.NAME_VALUE_PAIR_STRUCTURE(FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.buff_notebook_text(), buff.buff_type.buff_name()), LocalizationHelperTuning.NAME_VALUE_PAIR_STRUCTURE(FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.extra_ingredient_notebook_text(), LocalizationHelperTuning.get_object_name(extra_ingredient))]
            return tooltip_strings

        def create_row_gen(self, family_recipe:'FamilyRecipe', family_recipes_tracker:'FamilyRecipesTracker'=None, unlock_tracker:'UnlockTracker'=None, sim_info:'SimInfo'=None, **kwargs) -> 'ObjectPickerRow':
            recipe_manager = services.get_instance_manager(Types.RECIPE)
            buff_manager = services.get_instance_manager(Types.BUFF)
            buff = buff_manager.get(family_recipe.buff_id)
            recipe = recipe_manager.get(family_recipe.recipe_id)
            definition_manager = services.definition_manager()
            extra_ingredient = definition_manager.get(family_recipe.ingredient_id)
            recipe_owner = FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.original_creator_notebook_text(family_recipe.recipe_owner)
            recipe_name = FamilyRecipesTuning.FAMILY_RECIPE_DATA.family_recipe_text.family_recipe_name_text(family_recipe.recipe_name)
            recipe_icon = IconInfoData(icon_resource=recipe.icon_override, obj_def_id=recipe.final_product_definition_id, obj_geo_hash=recipe.final_product_geo_hash, obj_material_hash=recipe.final_product_material_hash)
            tooltip_strings = self.get_tooltip(recipe.final_product_definition, buff, extra_ingredient)
            row = ObjectPickerRow(option_id=family_recipe.buff_id, name=recipe_name, icon_info=recipe_icon, is_enable=True, tag=family_recipe.buff_id, row_description=recipe_owner, row_tooltip=lambda *_: LocalizationHelperTuning.get_new_line_separated_strings(*tooltip_strings))
            yield row

        def picker_rows_gen(self, family_recipes_tracker:'FamilyRecipesTracker'=None, unlock_tracker:'UnlockTracker'=None, sim_info:'SimInfo'=None, **kwargs):
            family_recipes = family_recipes_tracker.get_family_recipes()
            for row in self.create_rows_gen(family_recipes, None, None, None, **kwargs):
                yield row

    INSTANCE_TUNABLES = {'item': TunableVariant(description='\n            Item to be used in the picker\n            ', ingredient=_IngredientItem.TunableFactory(), buff=_BuffItem.TunableFactory(), family_recipe=_FamilyRecipeItem.TunableFactory())}

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        sim_info = context.sim.sim_info
        family_recipes_tracker = sim_info.sim_info.family_recipes_tracker
        unlock_tracker = sim_info.unlock_tracker
        if family_recipes_tracker is None or unlock_tracker is None:
            return
        for row in cls.item.picker_rows_gen(family_recipes_tracker, unlock_tracker, sim_info, **kwargs):
            yield row

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        return True
