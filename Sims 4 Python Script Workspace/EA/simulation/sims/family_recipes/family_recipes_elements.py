from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.family_recipes.family_recipes_tracker import FamilyRecipe, FamilyRecipesTrackerfrom interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableEnumEntry, Tunablefrom sims.family_recipes.family_recipes_tuning import FamilyRecipesTuning
class FamilyRecipeTeachTrackElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will teach the family recipe.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target_sim': TunableEnumEntry(description='\n            The target Sim that is going to learn the family recipe.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'family_recipe_participant': TunableEnumEntry(description='\n            Participant where the family recipe buff is stored.\n            ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId), 'show_warning_dialog': Tunable(description='\n            Show family recipe replace dialog if the target sim has a recipe already learned with that buff.\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        buff_id = self.interaction.get_participant(self.family_recipe_participant)
        target_sim = self.interaction.get_participant(self.target_sim)
        family_recipes_subject_tracker = subject.sim_info.family_recipes_tracker
        family_recipes_target_tracker = target_sim.sim_info.family_recipes_tracker
        if family_recipes_subject_tracker is None or family_recipes_target_tracker is None:
            return
        subject_family_recipe = family_recipes_subject_tracker.get_family_recipe_by_buff(buff_id)
        target_family_recipe = family_recipes_target_tracker.get_family_recipe_by_buff(buff_id)
        if target_family_recipe is None:
            family_recipes_target_tracker.add_family_recipe(subject_family_recipe)
        elif self.show_warning_dialog:

            def on_response(dialog):
                if not dialog.accepted:
                    return
                family_recipes_target_tracker.replace_family_recipe(target_family_recipe, subject_family_recipe)

            warning_dialog = FamilyRecipesTuning.FAMILY_RECIPE_REPLACE_DIALOG(target_sim)
            warning_dialog.show_dialog(on_response=on_response)
        else:
            family_recipes_target_tracker.replace_family_recipe(target_family_recipe, subject_family_recipe)
