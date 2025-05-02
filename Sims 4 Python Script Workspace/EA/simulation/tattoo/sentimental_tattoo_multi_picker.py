import servicesfrom interactions.base.multi_picker_interaction import MultiPickerInteractionfrom sims4.tuning.tunable_base import GroupNamesfrom ui.ui_dialog_multi_picker import UiMultiPickerfrom ui.ui_dialog_picker import UiSimPickerimport sims4.loglogger = sims4.log.Logger('SentimentalTattooMultiPickerInteraction', default_owner='rahissamiyordi')
class UiStoredSelectedOptionsMultiPicker(UiMultiPicker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picked_item_ids = set()

    def multi_picker_result(self, response_proto):
        for picker_result in response_proto.picker_responses:
            if picker_result.picker_id in self._picker_dialogs:
                dialog = self._picker_dialogs[picker_result.picker_id]
                dialog.pick_results(picked_results=picker_result.choices, control_ids=picker_result.control_ids)
                if isinstance(dialog, UiSimPicker):
                    target_sim_id = dialog.get_single_result_tag()
                    if target_sim_id is None:
                        logger.error('Failed to get sim in UiStoredSelectedOptionsMultiPicker')
                        return
                    sim_info = services.sim_info_manager().get(target_sim_id)
                    self.target = sim_info
                else:
                    object_picked = dialog.get_single_result_tag()
                    if object_picked is None:
                        logger.error('Failed to get object in UiStoredSelectedOptionsMultiPicker')
                        return
                    self.picked_item_ids = {object_picked}

class SentimentalTattooMultiPickerInteraction(MultiPickerInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiStoredSelectedOptionsMultiPicker.TunableFactory(description='\n            This multipicker allows you to choose a sentimental target and a tattoo design and \n            store them as SavedActor1 and PickedItemId.\n            ', tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, **kwargs):
        super(MultiPickerInteraction, self).__init__(*args, **kwargs)
        self.picked_item_ids = set()

    def _on_picker_selected(self, dialog):
        self.set_saved_participant(0, dialog.target)
        self.picked_item_ids = dialog.picked_item_ids
        if self.picked_item_ids and dialog.target is not None:
            self._handle_successful_editing()
        else:
            self._handle_unsuccessful_editing()
