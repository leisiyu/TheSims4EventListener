import servicesfrom google.protobuf import text_formatfrom sims4.resources import Typesfrom distributor.system import Distributorfrom protocolbuffers import UI_pb2, Consts_pb2, Dialog_pb2from distributor import shared_messagesfrom sims4.commands import CommandType, Command, outputfrom sims.family_recipes.family_recipes_tuning import FamilyRecipesTuningfrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_picker import UiSimPicker
@Command('family_recipes.get_recipes_cost_modifiers', command_type=CommandType.Live)
def get_recipes_cost_modifiers(recipe_id=int, _connection=None):
    sim = services.get_active_sim()
    if sim is None:
        output("Can't find provided Sim.", _connection)
        return
    family_recipes_tracker = sim.sim_info.family_recipes_tracker
    if family_recipes_tracker is None:
        return
    recipe_manager = services.get_instance_manager(Types.RECIPE)
    recipe = recipe_manager.get(recipe_id)
    if recipe is None:
        return
    msg = UI_pb2.FamilyRecipeCostModifier()
    msg.cost_modifier_size = family_recipes_tracker.get_family_recipe_cost_modifier(recipe)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_FAMILY_RECIPE_COST_MODIFIER)
    Distributor.instance().add_op_with_no_owner(op)

@Command('ui.dialog.validate_teach_family_recipes_multi_picker_result', command_type=CommandType.Live)
def ui_dialog_validate_multi_picker_result(dialog_id:int, multi_picker_proto:str, _connection=None):

    def send_response(is_valid:bool) -> None:
        msg = Dialog_pb2.PickerValidationResponse()
        msg.is_valid = is_valid
        shared_messages.add_message_if_selectable(dialog.owner, Consts_pb2.MSG_PICKER_VALIDATION_RESPONSE, msg, is_valid)

    ui_dialog_service = services.ui_dialog_service()
    if ui_dialog_service is None:
        send_response(False)
        return
    dialog = ui_dialog_service.get_dialog(dialog_id)
    if dialog is None:
        send_response(False)
        return
    response_proto = Dialog_pb2.MultiPickerResponse()
    text_format.Merge(multi_picker_proto, response_proto)
    for picker_result in response_proto.picker_responses:
        if picker_result.picker_id in dialog._picker_dialogs:
            dialog_picker = dialog._picker_dialogs[picker_result.picker_id]
            dialog_picker.pick_results(picked_results=picker_result.choices, control_ids=picker_result.control_ids)
            if isinstance(dialog_picker, UiSimPicker):
                target_sim_id = dialog_picker.get_single_result_tag()
                sim_info = services.sim_info_manager().get(target_sim_id)
            else:
                object_picked = dialog_picker.get_single_result_tag()
    family_recipes_tracker = sim_info.family_recipes_tracker
    if family_recipes_tracker is None or sim_info is None or object_picked is None:
        send_response(False)
        return
    recipe = family_recipes_tracker.get_family_recipe_by_buff(object_picked)
    if recipe is None:
        send_response(True)
        return

    def on_response(confirm_dialog:UiDialogOkCancel):
        send_response(confirm_dialog.accepted)

    warning_dialog = FamilyRecipesTuning.FAMILY_RECIPE_REPLACE_DIALOG(sim_info)
    warning_dialog.show_dialog(on_response=on_response)
