from __future__ import annotationsfrom sims4.tuning.tunable import TunableReferencefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from role.role_state import RoleState
    from situations.situation_job import SituationJob
    from typing import Optional
    from typing import Tuple
    from typing import Listimport distributor.opsimport servicesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import SituationState, TunableSituationJobAndRoleState, SituationStateData, SituationComplexCommonfrom situations.situation_zone_director_mixin import SituationZoneDirectorMixinfrom venues.venue_constants import ZoneDirectorRequestTypeimport sims4.loglogger = sims4.log.Logger('Breaking&Entering Situation', default_owner='cparrish')
class _PreBreakingAndEnteringState(SituationState):

    def on_pre_activate(self, reader=None) -> 'None':
        super().on_pre_activate(reader=reader)
        zone_director = services.venue_service().get_zone_director()
        if zone_director.guid64 != self.owner._zone_director.guid64:
            self.owner.guest_list.host_sim_info.send_travel_switch_to_zone_op()
        else:
            op = distributor.ops.SetWallsUpOrDown(True)
            distributor.system.Distributor.instance().add_op_with_no_owner(op)
            zone_director.save_break_in_group(self.owner.guest_list)
            zone_director.ensure_group_is_instanced()

class _ActiveBreakingAndEnteringState(SituationState):

    def on_activate(self, reader=None):
        op = distributor.ops.SetWallsUpOrDown(False)
        distributor.system.Distributor.instance().add_op_with_no_owner(op)

class BreakingAndEnteringPlayerGroupSituation(SituationZoneDirectorMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_breakin_player_group_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of the Sims who travelled here to B&E.\n            '), 'post_breakin_role': TunableReference(description='\n            The role state the player Sims who travelled here have once the door is open.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE))}
    REMOVE_INSTANCE_TUNABLES = ('_resident_job',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resident_return_triggered = False

    @classproperty
    def allow_user_facing_goals(cls) -> 'bool':
        return True

    @classmethod
    def get_possible_zone_ids_for_situation(cls, **kwargs) -> 'List[int]':
        return [services.current_zone_id()]

    @classmethod
    def _get_zone_director_request_type(cls) -> 'ZoneDirectorRequestType':
        return ZoneDirectorRequestType.SOCIAL_EVENT

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, SituationStateData]':
        return (SituationStateData(1, _PreBreakingAndEnteringState), SituationStateData(2, _ActiveBreakingAndEnteringState))

    @classmethod
    def resident_job(cls) -> 'Optional[SituationJob]':
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.pre_breakin_player_group_job_and_role_state.job, cls.pre_breakin_player_group_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        pass

    def start_situation(self) -> 'None':
        super().start_situation()
        self._change_state(_PreBreakingAndEnteringState())

    def _on_make_waiting_player_greeted(self, _) -> 'None':
        for sim in self.sims_in_situation():
            self._set_sim_role_state(sim, self.post_breakin_role, None)
        self._change_state(_ActiveBreakingAndEnteringState())

    def _situation_timed_out(self, _) -> 'None':
        zone_director = services.venue_service().get_zone_director()
        zone_director.request_resident_return_situation()
        self.resident_return_triggered = True
        super()._situation_timed_out(_)

    def on_remove(self):
        super().on_remove()
        zone_director = services.venue_service().get_zone_director()
        if zone_director.guid64 == self._zone_director.guid64:
            if not self.resident_return_triggered:
                zone_director.return_all_resident_sims(from_early_exit=True)
                zone_director.send_player_group_home()
            else:
                zone_director.break_in_finished = True
                zone_director.add_restrictive_buff()
lock_instance_tunables(BreakingAndEnteringPlayerGroupSituation, exclusivity=BouncerExclusivityCategory.VISIT, _implies_greeted_status=True)
class _ReturnBreakingAndEnteringState(SituationState):
    pass

class BreakingAndEnteringResidentsReturnSituation(SituationZoneDirectorMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'resident_sims_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of the resident Sims who live on the lot.\n            ')}
    REMOVE_INSTANCE_TUNABLES = ('_resident_job',)

    @classmethod
    def get_possible_zone_ids_for_situation(cls, **kwargs) -> 'List[int]':
        return [services.current_zone_id()]

    @classmethod
    def _get_zone_director_request_type(cls) -> 'ZoneDirectorRequestType':
        return ZoneDirectorRequestType.SOCIAL_EVENT

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData]':
        return (SituationStateData(1, _ReturnBreakingAndEnteringState),)

    @classmethod
    def resident_job(cls) -> 'SituationJob':
        return cls.resident_sims_job_and_role_state.job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.resident_sims_job_and_role_state.job, cls.resident_sims_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        pass

    def start_situation(self) -> 'None':
        super().start_situation()
        self._change_state(_ReturnBreakingAndEnteringState())
lock_instance_tunables(BreakingAndEnteringResidentsReturnSituation, exclusivity=BouncerExclusivityCategory.NORMAL, _implies_greeted_status=True)