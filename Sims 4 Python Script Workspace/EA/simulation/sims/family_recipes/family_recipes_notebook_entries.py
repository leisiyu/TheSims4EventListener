from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from notebook.notebook_entry import NotebookEntryRecipe, EntryData, SubListDatafrom sims4.localization import LocalizationHelperTuning, ConcatenationStylefrom sims.family_recipes.family_recipes_tuning import FamilyRecipesTuningimport servicesfrom distributor.shared_messages import IconInfoDatafrom sims4.resources import Types
class NotebookEntryFamilyRecipe(NotebookEntryRecipe):

    def get_definition_notebook_data(self, ingredient_cache:'list'=[]) -> 'Optional[EntryData]':
        recipe_definition = self.get_recipe_definition()
        if recipe_definition is None or self.final_product is None:
            return
        selected_sim = services.active_sim_info()
        family_recipes_tracker = selected_sim.sim_info.family_recipes_tracker
        if family_recipes_tracker is None:
            return
        else:
            existing_family_recipe = family_recipes_tracker.get_family_recipe_by_buff(self.entry_object_definition_id)
            if existing_family_recipe:
                row_display = []
                buff_manager = services.get_instance_manager(Types.BUFF)
                buff = buff_manager.get(existing_family_recipe.buff_id)
                definition_manager = services.definition_manager()
                extra_ingredient = definition_manager.get(existing_family_recipe.ingredient_id)
                recipe_name = FamilyRecipesTuning.FAMILY_RECIPE_DATA.family_recipe_text.family_recipe_name_text(existing_family_recipe.recipe_name)
                recipe_owner = FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.original_creator_notebook_text(existing_family_recipe.recipe_owner)
                row_display.append(SubListData(None, 0, 0, True, False, LocalizationHelperTuning.NAME_VALUE_PAIR_STRUCTURE(FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.base_recipe_notebook_text(), LocalizationHelperTuning.get_object_name(self.final_product)), None, None))
                row_display.append(SubListData(None, 0, 0, True, False, recipe_owner, None, None))
                row_display.append(SubListData(None, 0, 0, True, False, LocalizationHelperTuning.NAME_VALUE_PAIR_STRUCTURE(FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.buff_notebook_text(), buff.buff_type.buff_name()), None, None))
                row_display.append(SubListData(None, 0, 0, True, False, LocalizationHelperTuning.NAME_VALUE_PAIR_STRUCTURE(FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.extra_ingredient_notebook_text(), LocalizationHelperTuning.get_object_name(extra_ingredient)), None, None))
                return EntryData(recipe_name, IconInfoData(obj_def_id=self.final_product.id), self._get_entry_tooltip(self.final_product), row_display, self.entry_sublist_is_sortable)
