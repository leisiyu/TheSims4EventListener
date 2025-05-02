from interactions.base.multi_picker_interaction import MultiPickerInteractionfrom sims4.tuning.tunable_base import GroupNamesfrom tattoo.sentimental_tattoo_multi_picker import UiStoredSelectedOptionsMultiPickerimport sims4.loglogger = sims4.log.Logger('FamilyRecipeMultiPickerInteraction', default_owner='rahissamiyordi')
class FamilyRecipeMultiPickerInteraction(MultiPickerInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiStoredSelectedOptionsMultiPicker.TunableFactory(description='\n            This multipicker allows players to choose a family recipe and a Sim and \n            store them as Target and PickedItemId.\n            ', tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, **kwargs):
        super(MultiPickerInteraction, self).__init__(*args, **kwargs)
        self.picked_item_ids = set()

    def _on_picker_selected(self, dialog):
        self.set_target(dialog.target)
        self.picked_item_ids = dialog.picked_item_ids
        if self.picked_item_ids and self.target is not None:
            self._handle_successful_editing()
        else:
            self._handle_unsuccessful_editing()
