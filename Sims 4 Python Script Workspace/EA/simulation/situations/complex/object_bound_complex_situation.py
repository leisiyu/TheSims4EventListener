from __future__ import annotationsfrom sims4.tuning.tunable import TunableReferencefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.game_object import GameObject
    from situations.situation_job import SituationJob
    from role.role_state import RoleStatefrom _functools import partialimport servicesimport sims4.tuning.instancesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SingleJobComplexSituationState, SituationStateData, SituationComplexCommonfrom situations.complex.object_bound_situation_mixin import ObjectBoundSituationMixinfrom situations.situation_types import SituationCreationUIOptionlogger = sims4.log.Logger('ObjectBoundComplexSituation', default_owner='myakubek')
class _DoStuffState(SingleJobComplexSituationState):

    def get_time_remaining(self) -> 'Optional[int]':
        if self._time_out_string in self._alarms:
            return self._alarms[self._time_out_string].alarm_handle.get_remaining_time()

    def timer_expired(self) -> 'None':
        self.owner.go_to_leave_state()
        self._change_state(_LeaveState())

class _LeaveState(SingleJobComplexSituationState):
    pass

class ObjectBoundComplexSituation(ObjectBoundSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'_situation_job': TunableReference(description='\n            The situation job for the Sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',), tuning_group=GroupNames.SITUATION), '_do_stuff_state': _DoStuffState.TunableFactory(description='\n            The state for the Sim doing stuff.\n            ', display_name='1. Do Stuff', tuning_group=GroupNames.STATE), '_leave_state': _LeaveState.TunableFactory(description='\n            The state for the Sim leaving.\n            ', display_name='2. Leave', tuning_group=GroupNames.STATE)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, SituationStateData]':
        return (SituationStateData(1, _DoStuffState, partial(cls._do_stuff_state, situation_job=cls._situation_job)), SituationStateData(2, _LeaveState, partial(cls._leave_state, situation_job=cls._situation_job)))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls._situation_job, None)]

    @classmethod
    def default_job(cls) -> 'SituationJob':
        return cls._situation_job

    @classmethod
    def get_sims_expected_to_be_in_situation(cls) -> 'int':
        return 1

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        target_object_id = self._seed.extra_kwargs.get('default_target_id', None)
        self._target_object = services.object_manager().get(target_object_id)
        self.bind_object_id(target_object_id)

    def start_situation(self) -> 'None':
        super().start_situation()
        self._change_state(self._do_stuff_state(situation_job=self._situation_job))

    def get_target_object(self) -> 'Optional[GameObject]':
        return self._target_object

    def go_to_leave_state(self) -> 'None':
        self._change_state(self._leave_state(situation_job=self._situation_job))

    def _gsi_additional_data_gen(self) -> 'Generator[Tuple[str, str]]':
        if isinstance(self._cur_state, _DoStuffState):
            yield ('Time till Leave State', str(self._cur_state.get_time_remaining()))
sims4.tuning.instances.lock_instance_tunables(ObjectBoundComplexSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)