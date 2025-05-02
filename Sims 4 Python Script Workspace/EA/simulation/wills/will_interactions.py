from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from scheduling import Timelinefrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom ui.ui_dialog_generic import UiDialogTextInputOkCancelimport element_utilsimport services
class SetWillNoteImmediateInteraction(ImmediateSuperInteraction):
    TEXT_INPUT_NOTE = 'text_input_note'
    INSTANCE_TUNABLES = {'note_dialog': UiDialogTextInputOkCancel.TunableFactory(description="\n            The dialog to enter a note for the Sim's will, to be read by the will\n            recipients upon delivery.\n            ", text_inputs=(TEXT_INPUT_NOTE,))}

    def process_result(self, dialog:'UiDialogTextInputOkCancel') -> 'None':
        note_string = dialog.text_input_responses.get(self.TEXT_INPUT_NOTE)
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(self.sim.sim_id)
            if sim_will is not None:
                note = will_service.SIM_WILL_NOTE_TEXT(note_string)
                sim_will.set_note(note)

    def _run_interaction_gen(self, timeline:'Timeline') -> 'None':

        def on_response(dialog):
            if not dialog.accepted:
                return
            self.process_result(dialog)
            sequence = self._build_outcome_sequence()
            services.time_service().sim_timeline.schedule(element_utils.build_element(sequence))

        dialog = self.note_dialog(self.sim, self.get_resolver())
        dialog.show_dialog(on_response=on_response)
