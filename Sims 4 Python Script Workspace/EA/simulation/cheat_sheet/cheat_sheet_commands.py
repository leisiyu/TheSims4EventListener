import servicesimport sims4.commandsfrom distributor.ops import SendUIMessagefrom distributor.system import Distributor
@sims4.commands.Command('cheat_sheet.enabled')
def cheat_sheet_enabled(enabled:bool=True, _connection=None):
    if enabled:
        op = SendUIMessage('SetCheatSheetEnabled')
    else:
        op = SendUIMessage('SetCheatSheetDisabled')
    Distributor.instance().add_op_with_no_owner(op)
    services.misc_options_service().set_cheat_sheet_enabled(enabled)
