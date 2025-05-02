from protocolbuffers import Dialog_pb2from ui.ui_dialog import UiDialogimport sims4.loglogger = sims4.log.Logger('UI Dialog Death Options', default_owner='myakubek')
class UiDialogDeathOptions(UiDialog):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dialog_type = Dialog_pb2.UiDialogMessage.DEATH_OPTIONS

    def build_msg(self, **kwargs) -> None:
        msg = super().build_msg(**kwargs)
        msg.dialog_type = self._dialog_type
        return msg
