from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from event_testing.test_events import TestEvent
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from situations.situation_guest_list import SituationGuestList
    from situations.situation_job import SituationJob
    from role.role_state import RoleState
    from typing import *
    from world.spawn_point import SpawnPointfrom filters.tunable import FilterTermTagfrom sims4.tuning.tunable import TunableTuple, TunableMapping, TunableEnumEntry, TunableReference, TunableList, TunableEnumWithFilterfrom sims4.utils import classpropertyfrom situations.ambient.guest_list_no_bouncer_mixin import AmbientSituationGuestListNoBouncerMixinfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, CommonSituationState, SituationComplexCommon, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_types import SituationSerializationOption, SituationCreationUIOptionfrom tag import Tag, SPAWN_PREFIXfrom world.spawn_point import SpawnPointfrom world.spawn_point_enums import SpawnPointRequestReasonimport servicesimport sims4.tuning.instances
class GetSimsState(SituationState):

    def _on_set_sim_role_state(self, sim:'Sim', *args, **kwargs) -> 'None':
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

class WalkbyWalkState(CommonSituationState):

    def timer_expired(self) -> 'None':
        self._change_state(self.owner.leave_state())

class LeaveState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self._end_situation()

    def _additional_tests(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'bool':
        return self.owner.is_sim_info_in_situation(sim_info)

    def timer_expired(self) -> 'None':
        self._end_situation()

    def _end_situation(self) -> 'None':
        for sim in self.owner.all_sims_in_situation_gen():
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

class WalkbyPetOwner(SituationComplexCommon, AmbientSituationGuestListNoBouncerMixin):
    INSTANCE_TUNABLES = {'group_filter': TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableAggregateFilter',)), 'walk_state': WalkbyWalkState.TunableFactory(description='\n            A state where the pet owner and pet will walk together.\n            ', locked_args={'allow_join_situation': False}), 'leave_state': LeaveState.TunableFactory(description='\n            The state for the pet and owner to leave the lot.\n            ', locked_args={'allow_join_situation': False}), 'pet_owner': TunableTuple(situation_job=TunableReference(description="\n                The Situation Job of the pet's owner.\n                ", manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), initial_role_state=TunableReference(description="\n                The initial Role State of the pet's owner.\n                ", manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',))), 'pet': TunableTuple(situation_job=TunableReference(description='\n                The Situation Job of the pet.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), initial_role_state=TunableReference(description='\n                The initial Role State of the pet.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',))), 'situation_job_mapping': TunableMapping(description='\n            A mapping of filter term tag to situation job.\n            \n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular situation.\n            \n            The situation job is the job that the Sim will be assigned to in\n            the background situation.\n            ', key_name='filter_tag', key_type=TunableEnumEntry(description='\n                The filter term tag returned with the filter results.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job', value_type=TunableReference(description='\n                The job the Sim will receive when added to the this situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), 'sim_spawner_tags': TunableList(description='\n            A list of tags that represent where to spawn Sims for this\n            Situation when they come onto the lot.  This tuning will be used\n            instead of the tuning on the jobs.\n            NOTE: Spawn location will be randomly selected based off valid tag locations.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=SPAWN_PREFIX))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, ...]':
        return (SituationStateData(1, GetSimsState), SituationStateData(2, WalkbyWalkState, factory=cls.walk_state), SituationStateData(3, LeaveState, factory=cls.leave_state))

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.pet_owner.situation_job, cls.pet_owner.initial_role_state), (cls.pet.situation_job, cls.pet.initial_role_state)]

    @classmethod
    def get_predefined_guest_list(cls) -> 'Optional[SituationGuestList]':
        return cls.create_guest_list([cls.pet_owner.situation_job, cls.pet.situation_job], cls.situation_job_mapping, cls.tags, cls.group_filter, cls.get_sim_filter_gsi_name)

    def start_situation(self) -> 'None':
        super().start_situation()
        if self._guest_list.guest_info_count != self.group_filter.get_filter_count():
            self._self_destruct()
        else:
            self._change_state(GetSimsState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls) -> 'int':
        return cls.group_filter.get_filter_count()

    @classmethod
    def _can_start_walkby(cls, lot_id:'int') -> 'bool':
        return True

    @classproperty
    def situation_serialization_option(cls) -> 'SituationSerializationOption':
        return SituationSerializationOption.OPEN_STREETS

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self) -> 'bool':
        return True

    def on_all_sims_spawned(self) -> 'None':
        self._change_state(self.walk_state())

    def _issue_requests(self, spawn_point_override:'SpawnPoint'=None) -> 'None':
        zone = services.current_zone()
        if SpawnPoint.ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags or SpawnPoint.VISITOR_ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags:
            lot_id = zone.lot.lot_id
        else:
            lot_id = None
        spawn_point = zone.get_spawn_point(lot_id=lot_id, sim_spawner_tags=self.sim_spawner_tags, spawn_point_request_reason=SpawnPointRequestReason.SPAWN)
        super()._issue_requests(spawn_point_override=spawn_point)
sims4.tuning.instances.lock_instance_tunables(WalkbyPetOwner, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)