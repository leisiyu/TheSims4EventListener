import servicesfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom sims4.tuning.tunable import TunableSimMinutefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationComplexCommon, TunableInteractionOfInterest, SituationState, SituationStateDataimport alarmsimport clockimport sims4.tuning.tunable
class BirthdayPartySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'celebrant': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                    The SituationJob for the celebrant.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), celebrant_gather_role_state=sims4.tuning.tunable.TunableReference(description="\n                    Celebrant's role state before the celebration (gather phase).\n                    ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), celebrant_reception_role_state=sims4.tuning.tunable.TunableReference(description="\n                    Celebrant's role state after the celebration (eat, drink, socialize, dance).\n                    ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES), 'bartender': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                        The SituationJob for the Bartender.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), bartender_pre_reception_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Bartender's role state to prepare drinks and socialize with guests.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), bartender_reception_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Bartender's role state to prepare drinks, socialize, etc. during the reception.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES), 'caterer': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                        The SituationJob for the caterer.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), caterer_prep_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Caterer's role state for preparing cake and meal for guests.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), caterer_serve_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Caterer's role state for serving the guests.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES), 'entertainer': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                        The SituationJob for the entertainer.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), entertainer_prep_reception_state=sims4.tuning.tunable.TunableReference(description="\n                        Entertainer's role state before reception.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), entertainer_reception_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Entertainer's role state during reception.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES), 'guest': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                        The SituationJob for the Guests.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), guest_gather_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Guest's role state before the celebration (gather phase).\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), guest_gather_impatient_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Guest's role state if it is taking too long for the celebration to start.\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), guest_reception_role_state=sims4.tuning.tunable.TunableReference(description="\n                        Guest's role state after the celebration (now they can eat the cake).\n                        ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES), 'start_reception': TunableInteractionOfInterest(description='\n                        This is a birthday cake interaction where starting this interaction starts \n                        the cake reception phase.', tuning_group=GroupNames.TRIGGERS), 'guests_become_impatient_timeout': TunableSimMinute(description='\n                        If the celebration is not started in this amount of time the guests will grow impatient.', default=120, tuning_group=GroupNames.TRIGGERS)}
    REMOVE_INSTANCE_TUNABLES = ('venue_invitation_message', 'venue_situation_player_job')

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GatherState), SituationStateData(2, ImpatientGatherState), SituationStateData(3, ReceptionState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.celebrant.situation_job, cls.celebrant.celebrant_gather_role_state), (cls.bartender.situation_job, cls.bartender.bartender_pre_reception_role_state), (cls.caterer.situation_job, cls.caterer.caterer_prep_role_state), (cls.entertainer.situation_job, cls.entertainer.entertainer_prep_reception_state), (cls.guest.situation_job, cls.guest.guest_gather_role_state)]

    @classmethod
    def default_job(cls):
        return cls.guest.situation_job

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._celebrant_id = None

    def start_situation(self):
        super().start_situation()
        self._change_state(GatherState())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.celebrant.situation_job:
            self._celebrant_id = sim.sim_id

    def _is_birthday_starting(self, event, resolver):
        if resolver(self.start_reception):
            participants = resolver.get_participants(ParticipantType.Actor)
            for sim_info in participants:
                if sim_info.id == self._celebrant_id:
                    return True
        return False

class GatherState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        time_out = self.owner.guests_become_impatient_timeout
        if reader is not None:
            time_out = reader.read_float('impatient_timer', time_out)
        self._impatient_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(time_out), lambda _: self.timer_expired())
        for custom_key in self.owner.start_reception.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)

    def save_state(self, writer):
        super().save_state(writer)
        if self._impatient_alarm_handle is not None:
            writer.write_float('impatient_timer', self._impatient_alarm_handle.get_remaining_time().in_minutes())

    def on_deactivate(self):
        if self._impatient_alarm_handle is not None:
            alarms.cancel_alarm(self._impatient_alarm_handle)
            self._impatient_alarm_handle = None
        super().on_deactivate()

    def timer_expired(self):
        self._change_state(ImpatientGatherState())

    def handle_event(self, sim_info, event, resolver):
        if self.owner._is_birthday_starting(event, resolver):
            self._change_state(ReceptionState())

class ImpatientGatherState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self.owner.start_reception.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)
        self.owner._set_job_role_state(self.owner.guest.situation_job, self.owner.guest.guest_gather_impatient_role_state)

    def handle_event(self, sim_info, event, resolver):
        if self.owner._is_birthday_starting(event, resolver):
            self._change_state(ReceptionState())

class ReceptionState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.celebrant.situation_job, self.owner.celebrant.celebrant_reception_role_state)
        self.owner._set_job_role_state(self.owner.bartender.situation_job, self.owner.bartender.bartender_reception_role_state)
        self.owner._set_job_role_state(self.owner.caterer.situation_job, self.owner.caterer.caterer_serve_role_state)
        self.owner._set_job_role_state(self.owner.entertainer.situation_job, self.owner.entertainer.entertainer_reception_role_state)
        self.owner._set_job_role_state(self.owner.guest.situation_job, self.owner.guest.guest_reception_role_state)
