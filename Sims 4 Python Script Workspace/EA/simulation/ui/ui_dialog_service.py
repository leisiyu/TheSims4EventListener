from __future__ import annotationsfrom clock import ClockSpeedModefrom date_and_time import TimeSpanfrom distributor.ops import SetPhoneSilencefrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom protocolbuffers import Consts_pb2, Dialog_pb2, GameplaySaveData_pb2from sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom singletons import DEFAULTfrom ui.notification_suppression import NotificationSuppressionTuningfrom ui.ui_dialog import PhoneRingTypeimport alarmsimport clockimport persistence_error_typesimport servicesimport sims4.logfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from FileSerialization_pb2 import ZoneData
    from ui.notification_suppression import TNSSuppressionGroup, TNSSuppression
    from ui.ui_dialog_notification import UiDialogNotificationlogger = sims4.log.Logger('UI Dialog Service', default_owner='shipark')
class UiDialogService(Service):

    def __init__(self):
        self._active_dialogs = {}
        self._auto_respond = False
        self._auto_respond_alarm_handles = {}
        self._is_phone_silenced = False
        self._enabled = True
        self._tns_configs = {}
        for (group, config) in NotificationSuppressionTuning.SUPPRESSION_GROUP_CONFIG_MAPPING.items():
            self._tns_configs[group] = config()

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_UI_DIALOG_SERVICE

    def disable_on_teardown(self):
        for alarm_handle in self._auto_respond_alarm_handles.values():
            alarm_handle.cancel()
        self._auto_respond_alarm_handles.clear()
        self._enabled = False

    def has_active_modal_dialogs(self) -> 'bool':
        for dialog in self._active_dialogs.values():
            if dialog.DIALOG_MSG_TYPE != Consts_pb2.MSG_UI_NOTIFICATION_SHOW and dialog.get_phone_ring_type() == PhoneRingType.NO_RING:
                return True
        return False

    @property
    def is_phone_silenced(self):
        return self._is_phone_silenced

    def _set_is_phone_silenced(self, value):
        self._is_phone_silenced = value
        op = SetPhoneSilence(self._is_phone_silenced)
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(op)

    def toggle_is_phone_silenced(self):
        self._set_is_phone_silenced(not self._is_phone_silenced)

    def try_get_suppression_config(self, tns:'UiDialogNotification') -> 'Optional[TNSSuppression]':
        if tns.tns_suppression_group:
            return self._tns_configs.get(tns.tns_suppression_group, None)

    def dialog_show(self, dialog, phone_ring_type, auto_response=DEFAULT, caller_id=None, immediate=False, **kwargs):
        if not self._enabled:
            return
        self._active_dialogs[dialog.dialog_id] = dialog
        if dialog.has_responses() and self.auto_respond:

            def auto_respond_callback(_):
                dialog.do_auto_respond(auto_response=auto_response)
                del self._auto_respond_alarm_handles[dialog.dialog_id]

            self._auto_respond_alarm_handles[dialog.dialog_id] = alarms.add_alarm(self, TimeSpan.ZERO, auto_respond_callback)
            return
        dialog_msg = dialog.build_msg(**kwargs)
        if phone_ring_type != PhoneRingType.NO_RING:
            if not self._is_phone_silenced:
                game_clock_services = services.game_clock_service()
                if game_clock_services.clock_speed != ClockSpeedMode.PAUSED and not clock.GameClock.ignore_game_speed_requests:
                    game_clock_services.set_clock_speed(ClockSpeedMode.NORMAL)
            msg_type = Consts_pb2.MSG_UI_PHONE_RING
            msg_data = Dialog_pb2.UiPhoneRing()
            msg_data.phone_ring_type = phone_ring_type
            msg_data.dialog = dialog_msg
            if caller_id is not None:
                msg_data.caller_id = caller_id
            distributor = Distributor.instance()
            distributor.add_event(msg_type, msg_data)
        else:
            msg_type = dialog.DIALOG_MSG_TYPE
            msg_data = dialog_msg
            dialog.distribute_dialog(msg_type, msg_data, immediate=immediate)

    def _dialog_cancel_internal(self, dialog):
        msg = Dialog_pb2.UiDialogCloseRequest()
        msg.dialog_id = dialog.dialog_id
        distributor = Distributor.instance()
        distributor.add_event(Consts_pb2.MSG_UI_DIALOG_CLOSE, msg)
        del self._active_dialogs[dialog.dialog_id]

    def dialog_cancel(self, dialog_id:'int'):
        dialog = self._active_dialogs.get(dialog_id, None)
        if dialog is not None:
            self._dialog_cancel_internal(dialog)

    def dialog_respond(self, dialog_id:'int', response:'int', client=None) -> 'bool':
        dialog = self._active_dialogs.get(dialog_id, None)
        if dialog is not None:
            try:
                if dialog.respond(response):
                    self._dialog_cancel_internal(dialog)
                    return True
            except:
                self._dialog_cancel_internal(dialog)
                raise
        return False

    def dialog_pick_result(self, dialog_id:'int', picked_results=[], ingredient_check=None, prepped_ingredient_check=None, recipe_id=None) -> 'bool':
        dialog = self._active_dialogs.get(dialog_id, None)
        if dialog is not None and dialog.pick_results(picked_results=picked_results, ingredient_check=ingredient_check, prepped_ingredient_check=prepped_ingredient_check, recipe_id=recipe_id):
            return True
        return False

    def dialog_pick_result_family_recipe(self, dialog_id:'int', picked_results=[], recipe_name:'str'=None, recipe_owner_name:'str'=None) -> 'bool':
        dialog = self._active_dialogs.get(dialog_id, None)
        if dialog is not None and dialog.pick_results_family_recipe(picked_results=picked_results, recipe_name=recipe_name, recipe_owner_name=recipe_owner_name):
            return True
        return False

    def dialog_pick_result_def_ids_and_counts(self, dialog_id:'int', picked_def_ids=[], obj_ids=[], picked_counts=[], ingredient_check=None) -> 'bool':
        dialog = self._active_dialogs.get(dialog_id, None)
        if dialog is not None and dialog.pick_definitions_ids_and_counts(picked_def_ids, obj_ids, picked_counts, ingredient_check):
            return True
        return False

    def dialog_text_input(self, dialog_id:'int', text_input_name, text_input_value) -> 'bool':
        dialog = self._active_dialogs.get(dialog_id, None)
        if dialog is not None and dialog.on_text_input(text_input_name, text_input_value):
            return True
        return False

    def get_dialog(self, dialog_id):
        return self._active_dialogs.get(dialog_id, None)

    def send_dialog_options_to_client(self):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        self._set_is_phone_silenced(save_slot_data_msg.gameplay_data.is_phone_silenced)

    def load(self, zone_data:'ZoneData'=None) -> 'None':
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        for entry in save_slot_data.gameplay_data.ui_dialog_service.suppression_entries:
            if entry.group_id in self._tns_configs:
                self._tns_configs[entry.group_id].load(entry)

    def save(self, save_slot_data=None, **kwargs) -> 'None':
        save_slot_data.gameplay_data.is_phone_silenced = self._is_phone_silenced
        save_data = GameplaySaveData_pb2.PersistableUiDialogService()
        for (group, config) in self._tns_configs.items():
            with ProtocolBufferRollback(save_data.suppression_entries) as entry:
                config.save(entry)
                entry.group_id = group
        save_slot_data.gameplay_data.ui_dialog_service = save_data

    @property
    def auto_respond(self):
        return self._auto_respond

    def set_auto_respond(self, auto_respond):
        if self._auto_respond == auto_respond:
            return
        self._auto_respond = auto_respond
        if auto_respond:
            for dialog in list(self._active_dialogs.values()):
                dialog.do_auto_respond()
