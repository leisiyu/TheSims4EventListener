from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from interactions.base.interaction import Interaction
    from typing import *from event_testing.test_events import TestEventfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims.sim import SimulationStatefrom sims.sim_info_types import Speciesfrom sims4.log import Loggerfrom sims4.tuning.tunable import TunableTuple, TunableReferencefrom situations.ambient.walkby_pet_owner import GetSimsState, LeaveState, WalkbyPetOwner, WalkbyWalkStatefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import CommonInteractionStartingSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionimport servicesimport sims4.tuning.instanceslogger = Logger('WalkbyHorseback', default_owner='cseraphim')
class GetHorsebackSimsState(GetSimsState):

    def __init__(self) -> 'None':
        super().__init__()
        self._sims_ready = 0

    def _on_set_sim_role_state(self, sim:'Sim', *args, **kwargs) -> 'None':
        super(GetSimsState, self)._on_set_sim_role_state(sim, *args, **kwargs)

        def sim_is_ready(start_up_sim:'Sim') -> 'None':
            self._sims_ready += 1
            if self._sims_ready >= self.owner.num_invited_sims:
                self.owner.on_all_sims_spawned()

        if sim.simulation_state is SimulationState.SIMULATING:
            self._sims_ready += 1
        else:
            sim.on_start_up.append(sim_is_ready)
        if self.owner.num_of_sims >= self.owner.num_invited_sims and self._sims_ready >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

class HorsebackMountState(CommonInteractionStartingSituationState):
    FACTORY_TUNABLES = {'mount_interaction': TunableReference(description='\n            The interaction that makes the sim mount the horse.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))}

    def __init__(self, mount_interaction:'Interaction', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._mount_interaction = mount_interaction

    def on_activate(self, reader=None) -> 'None':
        super().on_activate(reader)
        context = InteractionContext(self.owner.rider, InteractionContext.SOURCE_SCRIPT, Priority.High, run_priority=Priority.High, insert_strategy=QueueInsertStrategy.FIRST)
        self.owner.rider.push_super_affordance(super_affordance=self._mount_interaction, target=self.owner.horse, context=context)

    def timer_expired(self) -> 'None':
        self.owner.end_situation()

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self._change_state(self.owner.walk_state())

    def _additional_tests(self, sim_info:'Type[SimInfo]', event:'TestEvent', resolver:'Resolver') -> 'bool':
        return self.owner.is_sim_info_in_situation(sim_info)

class HorsebackLeaveState(LeaveState):

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self.owner.end_situation()

    def _additional_tests(self, sim_info:'Type[SimInfo]', event:'TestEvent', resolver:'Resolver') -> 'bool':
        return self.owner.is_sim_info_in_situation(sim_info)

    def timer_expired(self) -> 'None':
        self.owner.end_situation()

class WalkbyHorseback(WalkbyPetOwner):
    INSTANCE_TUNABLES = {'mount_state': HorsebackMountState.TunableFactory(description='\n            A state which gets the sim to mount the horse.\n            ', locked_args={'allow_join_situation': False}), 'leave_state': HorsebackLeaveState.TunableFactory(description='\n            The state for the pet and owner to leave the lot.\n            ', locked_args={'allow_join_situation': False})}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._horse = None
        self._rider = None

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, ...]':
        return (SituationStateData(1, GetHorsebackSimsState), SituationStateData(2, HorsebackMountState, factory=cls.mount_state), SituationStateData(3, WalkbyWalkState, factory=cls.walk_state), SituationStateData(4, HorsebackLeaveState, factory=cls.leave_state))

    def _get_horse_and_rider(self) -> 'None':
        situation_sims = self.sims_in_situation()
        if len(situation_sims) < 2:
            self.end_situation(missing_required_sims=True)
        for sim in self.sims_in_situation():
            if sim.species == Species.HORSE:
                self._horse = sim
            else:
                self._rider = sim

    @property
    def horse(self) -> 'Sim':
        if not self._horse:
            self._get_horse_and_rider()
        return self._horse

    @property
    def rider(self) -> 'Sim':
        if not self._rider:
            self._get_horse_and_rider()
        return self._rider

    def _save_custom_state(self, writer) -> 'None':
        writer.write_uint32(SituationComplexCommon.STATE_ID_KEY, self._states()[0].uid)
        self._cur_state.save_state(writer)

    def start_situation(self) -> 'None':
        super(WalkbyPetOwner, self).start_situation()
        if self._guest_list.guest_info_count != self.group_filter.get_filter_count():
            self._self_destruct()
        else:
            self._change_state(GetHorsebackSimsState())

    def end_situation(self, missing_required_sims:'bool'=False) -> 'None':
        zone_situation_manager = services.get_zone_situation_manager()
        if missing_required_sims or self.horse is not None and self.rider is not None:
            zone_situation_manager.make_sim_leave_now_must_run(self.horse)
            if not self.rider.is_riding_horse:
                zone_situation_manager.make_sim_leave_now_must_run(self.rider)
        else:
            for sim in self.sims_in_situation():
                zone_situation_manager.make_sim_leave_now_must_run(sim)
        self._self_destruct()

    def on_all_sims_spawned(self) -> 'None':
        self._change_state(self.mount_state())
sims4.tuning.instances.lock_instance_tunables(WalkbyHorseback, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)