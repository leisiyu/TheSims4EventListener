import sims4from protocolbuffers import UI_pb2, DistributorOps_pb2from protocolbuffers.Localization_pb2 import LocalizedStringfrom singletons import EMPTY_SETfrom ui.ui_dialog import UiDialogBasefrom distributor.system import Distributorfrom distributor.ops import GenericProtocolBufferOp
class UiDialogObjectColorPicker(UiDialogBase):
    DIALOG_MSG_TYPE = DistributorOps_pb2.Operation.UI_LIGHT_COLOR_SHOW

    def __init__(self, obj, r:int, g:int, b:int, slider_value:int=0, checkbox_state:bool=False, on_update=None, palette:int=None, style:int=None, palette_label:LocalizedString=None, slider_label:LocalizedString=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obj = obj
        self._red = r
        self._green = g
        self._blue = b
        self._slider_value = slider_value
        self._checkbox_state = checkbox_state
        self._on_update = on_update
        self._palette = palette
        self._style = style
        self._grid_label = palette_label
        self._slider_label = slider_label
        self.ui_responses = EMPTY_SET

    def build_msg(self, **kwargs):
        msg = UI_pb2.LightColorAndIntensity()
        msg.response_id = self.dialog_id
        msg.target_id = self._obj.id
        msg.red = self._red
        msg.green = self._green
        msg.blue = self._blue
        msg.intensity = self._slider_value
        msg.checkbox_state = self._checkbox_state
        msg.palette = self._palette
        msg.style = self._style
        msg.grid_label = LocalizedString()
        if self._grid_label is not None and self._grid_label.hash != 0:
            msg.grid_label.MergeFrom(self._grid_label)
        else:
            msg.grid_label.hash = 0
        msg.slider_label = LocalizedString()
        if self._slider_label is not None and self._slider_label.hash != 0:
            msg.slider_label.MergeFrom(self._slider_label)
        else:
            msg.slider_label.hash = 0
        return msg

    def distribute_dialog(self, dialog_type, dialog_msg, **kwargs):
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(GenericProtocolBufferOp(dialog_type, dialog_msg))

    def update_dialog_data(self, color:int, slider_value:float=None, checkbox_state:bool=None):
        if self._on_update is not None:
            item = self._get_color_item(color)
            self._on_update(color=color, slider_value=slider_value, checkbox_state=checkbox_state, color_item=item)

    def has_responses(self):
        return True

    def _get_color_item(self, color:int):
        from objects.color.object_color_tuning import ObjectColorTuning
        if self._palette is not None:
            return ObjectColorTuning.get_color_item(self._palette, color)
