from sims4.tuning.tunable import TunableSetfrom sims4.utils import classpropertyfrom situations.ambient.walkby_limiting_tags_mixin import WalkbyLimitingTagsMixinfrom situations.situation_complex import SituationState, SituationStateDataimport servicesimport sims4.tuning.tunableimport situations.bouncerimport situations.situation_complexlogger = sims4.log.Logger('Walkby')DO_STUFF_TIMEOUT = 'do_stuff_timeout'
class OpenStreetsAutonomySituation(WalkbyLimitingTagsMixin, situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'role': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                The situation job for the sim.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), do_stuff_role_state=sims4.tuning.tunable.TunableReference(description='\n                The role state for the sim doing stuff.  This is the initial state.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), leave_role_state=sims4.tuning.tunable.TunableReference(description='\n                The role state for the sim leaving.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',))), 'do_stuff_timeout': sims4.tuning.tunable.TunableSimMinute(description='\n            The amount of time the sim does stuff before leaving.\n            ', default=180)}
    REMOVE_INSTANCE_TUNABLES = situations.situation.Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _DoStuffState), SituationStateData(2, _LeaveState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.role.situation_job, cls.role.do_stuff_role_state)]

    @classmethod
    def default_job(cls):
        return cls.role.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(_DoStuffState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.OPEN_STREETS

    def _get_remaining_time_for_gsi(self):
        if self._cur_state is not None:
            return self._cur_state._get_remaining_time_for_gsi()
        return super()._get_remaining_time_for_gsi()
sims4.tuning.instances.lock_instance_tunables(OpenStreetsAutonomySituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.WALKBY, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=0)
class _DoStuffState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.role.situation_job, self.owner.role.do_stuff_role_state)
        self._create_or_load_alarm(DO_STUFF_TIMEOUT, self.owner.do_stuff_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        self._change_state(_LeaveState())

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(DO_STUFF_TIMEOUT)

class _LeaveState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.role.situation_job, self.owner.role.leave_role_state)

    def _get_remaining_time_for_gsi(self):
        return self.owner.get_remaining_time()
