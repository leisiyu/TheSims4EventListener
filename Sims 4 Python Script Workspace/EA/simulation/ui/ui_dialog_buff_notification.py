from interactions import ParticipantTypeSingleSimfrom sims4.tuning.tunable import TunableEnumEntryfrom ui.ui_dialog_notification import UiDialogNotificationimport sims4logger = sims4.log.Logger('UI Dialog Buff Notification', default_owner='kalucas')
class UiDialogBuffNotification(UiDialogNotification):
    FACTORY_TUNABLES = {'highest_priority_buff_subject': TunableEnumEntry(description='\n            What Sim to search for the highest priority buff on to use in the TNS.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim)}

    def show_dialog(self, **kwargs):
        participant = self._resolver.get_participant(self.highest_priority_buff_subject)
        if participant is None:
            logger.error('Got no participant which is required for a buff notification.')
            return
        if participant.Buffs.get_highest_priority_buff() is None:
            logger.error('Participant {} has no buffs with a tuned priority which is required for a buff notification.', participant)
            return
        super().show_dialog(**kwargs)

    def build_msg(self, **kwargs):
        participant = self._resolver.get_participant(self.highest_priority_buff_subject)
        highest_priority_buff = participant.Buffs.get_highest_priority_buff()
        msg = super().build_msg(text_override=highest_priority_buff.buff_notification_info.text, **kwargs)
        return msg
