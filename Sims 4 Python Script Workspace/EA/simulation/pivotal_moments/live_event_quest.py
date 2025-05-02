from __future__ import annotationsimport distributor.opsimport servicesimport sims4.logimport telemetry_helperfrom distributor.system import Distributorfrom sims4.tuning.tunable import Tunablefrom sims4.utils import classpropertyfrom pivotal_moments.pivotal_moment import PivotalMoment, PivotalMomentActivationStatusfrom ui.ui_dialog import ButtonType, UiDialogOkfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from interactions.utils.exit_condition_manager import ConditionGroup
    from protocolbuffers import GameplaySaveData_pb2
    from sims.sim_info import SimInfo
    from tutorials.tutorial_service import TutorialServiceTELEMETRY_GROUP_LIVE_EVENT = 'EVNT'TELEMETRY_GROUP_LIVE_EVENT_SITUATION_START = 'STRT'TELEMETRY_FIELD_EVENT_ID = 'evnt'TELEMETRY_FIELD_SITUATION_ID = 'goal'TELEMETRY_FIELD_SOURCE = 'srce'live_event_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_LIVE_EVENT)logger = sims4.log.Logger('Live Event Quest', default_owner='shipark')
class LiveEventQuest(PivotalMoment):
    QUEST_CLEARED_DIALOG = UiDialogOk.TunableFactory(description='\n        The dialog shown when live event quest situations are cleared during\n        gameplay. \n        \n        This is triggered via client when the server model of the event is \n        resolved against the local state of the event.\n        ')
    LIVE_EVENT_QUEST_END_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        Notification to show when the live event quest is ending.\n        ')
    INSTANCE_TUNABLES = {'persist_to_account_level_save_file': Tunable(description='\n            If True, persist the pivotal moment to the account level save file. Otherwise,\n            the pivotal moment progress is specific to the game.\n            ', tunable_type=bool, default=False)}

    @classproperty
    def persist_to_account(cls) -> 'bool':
        return cls.persist_to_account_level_save_file

    @classproperty
    def can_be_killed(cls) -> 'bool':
        return False

    @classproperty
    def enabled(self) -> 'bool':
        return True

    def _get_live_event_id(self) -> 'int':
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            logger.error('Tutorial service is not created and needs to be to get quest event information.')
            return 0
        live_event_ids = tutorial_service.get_live_event_id_for_quest(self.guid64)
        if not live_event_ids:
            logger.warn('No tracked quest event for quest with id: {}', self.guid64)
            return 0
        return live_event_ids[0]

    def reset(self, from_error_syncing=False) -> 'bool':
        if from_error_syncing:
            return super().reset()
        return False

    def should_load(self) -> 'bool':
        should_load = self._get_live_event_id() != 0
        return should_load

    def can_situation_start(self) -> 'bool':
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            return False
        return tutorial_service.can_new_live_event_quest_start()

    def on_pivotal_moment_complete(self, rewarded:'bool'=False) -> 'None':
        super().on_pivotal_moment_complete(rewarded)
        op = distributor.ops.QuestComplete(self.guid64, self._get_live_event_id())
        Distributor.instance().add_op_with_no_owner(op)
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None:
            tutorial_service.on_live_event_quest_complete(self._get_live_event_id(), self.guid64)

    def on_pivotal_moment_goal_complete(self, completed_goal_id:'int') -> 'None':
        super().on_pivotal_moment_goal_complete(completed_goal_id)
        op = distributor.ops.QuestGoalComplete(completed_goal_id, self.guid64, self._get_live_event_id())
        Distributor.instance().add_op_with_no_owner(op)

    def activation_callback(self, condition_group:'ConditionGroup'=None) -> 'None':
        self._activate_pivotal_moment(condition_group)

    def send_dialog_telemetry(self, sim_info:'SimInfo', dialog_response:'int') -> 'None':
        super().send_dialog_telemetry(sim_info, dialog_response)
        if dialog_response != ButtonType.DIALOG_RESPONSE_OK:
            return
        with telemetry_helper.begin_hook(live_event_telemetry_writer, TELEMETRY_GROUP_LIVE_EVENT_SITUATION_START, sim_info=sim_info) as hook:
            hook.write_int(TELEMETRY_FIELD_EVENT_ID, self._get_live_event_id())
            hook.write_guid(TELEMETRY_FIELD_SITUATION_ID, self.guid64)
            hook.write_string(TELEMETRY_FIELD_SOURCE, 'play')

    def load(self, pivotal_moment_data:'GameplaySaveData_pb2.PivotalMoment', tutorial_service:'TutorialService') -> 'None':
        super().load(pivotal_moment_data, tutorial_service)
        if self._activation_status == PivotalMomentActivationStatus.ACTIVE and self._situation_id == 0 and self.guid64 not in tutorial_service.completed_quest_ids():
            logger.warn('Loaded Live Event Quest ({}) with id {}, marked as active but not complete, and no tracked situation. Reschedule the drama node on load.', self, self.guid64)
            self.activation_callback()
