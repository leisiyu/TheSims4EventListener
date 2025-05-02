from __future__ import annotationsimport sims4from typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from role.role_state import RoleState
    from situations.situation_job import SituationJob
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from event_testing.resolver import Resolver
    from default_property_stream_reader import DefaultPropertyStreamReader
    from situations.situation_complex import InteractionOfInterest
    from interactions.base.interaction import Interactionimport servicesimport situations.situation_typesfrom crafting.crafting_tunable import CraftingTuningfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom objects.base_object import BaseObjectfrom sims4.log import Loggerfrom sims4.tuning.tunable import TunableRange, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationState, SituationStateData, TunableSituationJobAndRoleState, TunableInteractionOfInterestlogger = Logger('Situations')
class _GetSimsState(SituationState):

    def _on_set_sim_role_state(self, sim:'Type[Sim]', *args, **kwargs) -> 'None':
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        self.owner.on_all_sims_spawned()

class _SituationRecoveryState(CommonSituationState):
    FACTORY_TUNABLES = {'add_to_world_interaction': TunableReference(description='\n            The interaction used to get the serving from the inventory and\n            place it in the world.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'retrieve_serving_interaction': TunableInteractionOfInterest(description='\n            The interaction that puts down the serving. The interactions\n            tuned here will cause the situation to proceed to the next state.\n            ')}

    def __init__(self, add_to_world_interaction:'Interaction', retrieve_serving_interaction:'InteractionOfInterest', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._add_to_world_interaction = add_to_world_interaction
        self._retrieve_serving_interaction = retrieve_serving_interaction

    def on_activate(self, reader:'DefaultPropertyStreamReader'=None) -> 'None':
        super().on_activate(reader)
        for custom_key in self._retrieve_serving_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)
        if self.owner._last_served_object_id is not None:
            serve_object = services.inventory_manager().get(self.owner._last_served_object_id)
            if serve_object is not None:
                self.owner.get_actor_sim().push_super_affordance(self._add_to_world_interaction, serve_object, self.owner.get_context())

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        if event == TestEvent.InteractionExitedPipeline and (self.owner.is_sim_info_in_situation(sim_info) and resolver(self._retrieve_serving_interaction)) and resolver.interaction.is_finishing_naturally:
            if self.owner.has_servings_remaining():
                self._change_state(self.owner.get_single_serving_state())
            else:
                self.owner._self_destruct()

class _GetSingleServingState(CommonSituationState):
    FACTORY_TUNABLES = {'grab_serving_interaction': TunableReference(description='\n            The interaction that actually grabs an individual serving.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'put_down_interactions': TunableInteractionOfInterest(description='\n            A set of possible_interactions that indicate when we are done\n            putting down the single serving, and can move on to get the\n            next serving.\n            \n            Note: if your multi-serve flow is stalling after putting down\n            the single serving, verify that the actual put down interaction\n            that is being run on the single serving is included in this list.\n            ')}

    def __init__(self, grab_serving_interaction:'Type', put_down_interactions:'InteractionOfInterest', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._grab_serving_interaction = grab_serving_interaction
        self._put_down_interactions = put_down_interactions

    def on_activate(self, reader:'DefaultPropertyStreamReader'=None) -> 'None':
        super().on_activate(reader)
        for custom_key in self._put_down_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)
        sim = self.owner.get_actor_sim()
        if sim is None:
            return
        interaction = self._grab_serving_interaction
        context = self.owner.get_context()
        result = sim.push_super_affordance(interaction, self.owner.try_get_multi_serve_object(), context)
        if not result:
            logger.error('GetSingleServingState unable to begin grab serving interaction.')
            self.owner._self_destruct()
            return
        self.owner.decrement_servings_remaining()

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        if event == TestEvent.InteractionExitedPipeline and self.owner.is_sim_info_in_situation(sim_info) and resolver(self._put_down_interactions):
            if resolver.interaction.is_finishing_naturally:
                self._on_put_down_serving_complete()
            else:
                self.owner._self_destruct()

    def _on_put_down_serving_complete(self) -> 'None':
        if not self.owner.is_running:
            return
        if self.owner.has_servings_remaining():
            self._change_state(self.owner.get_single_serving_state())
        else:
            self.owner._self_destruct()

class MultiServeSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_total_servings': TunableRange(description='\n            The number of servings that the sim will serve.\n            ', tunable_type=int, default=1, minimum=1), 'serving_sim_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the sim that is serving the dish. This prepopulates\n            to the actor of the situation.\n            '), 'get_single_serving_state': _GetSingleServingState.TunableFactory(description='\n            A situation state that will make the sim grab a serving from the main dish in one hand,\n            and hold the serving in the other hand.\n            ', tuning_group=GroupNames.STATE, display_name='Get Single Serving State'), 'recover_from_load_state': _SituationRecoveryState.TunableFactory(description='\n            A situation state that recovers the situation from load by placing servings that\n            ended up in the inventory onto a surface before proceeding.\n            ', tuning_group=GroupNames.STATE, display_name='Recover From Load State')}

    def __init__(self, *arg, **kwargs) -> 'None':
        super().__init__(*arg, **kwargs)
        self._group_id = None
        self._object_stat_tracker = None
        self._interaction = None
        self._sims_spawned = False
        self._last_served_object_id = None
        self._serving_object = None
        reader = self._seed.custom_init_params_reader
        self._serving_object_id = self._seed.extra_kwargs.get('default_target_id', None)
        self._servings_remaining = self._total_servings
        if reader is not None:
            self._servings_remaining = reader.read_uint64('servings_remaining', self._total_servings)
            self._last_served_object_id = reader.read_uint64('serving_id', None)
            if self._serving_object_id is None:
                self._serving_object_id = reader.read_uint64('serving_object_id', None)

    @classproperty
    def situation_serialization_option(cls) -> 'situations.situation_types.SituationSerializationOption':
        return situations.situation_types.SituationSerializationOption.LOT

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, ...]':
        return (SituationStateData(0, _GetSimsState), SituationStateData(1, _SituationRecoveryState, factory=cls.recover_from_load_state), SituationStateData(2, _GetSingleServingState, factory=cls.get_single_serving_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.serving_sim_job_and_role.job, cls.serving_sim_job_and_role.role_state)]

    def start_situation(self) -> 'None':
        super().start_situation()
        self._change_state(_GetSimsState())

    def _save_custom_situation(self, writer) -> 'None':
        super()._save_custom_situation(writer)
        writer.write_uint64('serving_object_id', self._serving_object_id)
        writer.write_uint64('servings_remaining', self._servings_remaining)
        serving_id = None
        for child_object in self.get_actor_sim().children:
            if child_object.is_sim or child_object.id != self._serving_object_id:
                serving_id = child_object.id
        if serving_id is not None:
            writer.write_uint64('serving_id', serving_id)

    def _save_custom_state(self, writer):
        writer.write_uint32(SituationComplexCommon.STATE_ID_KEY, self._states()[0].uid)
        self._cur_state.save_state(writer)

    def _try_change_state(self) -> 'None':
        if self._interaction is not None and self._sims_spawned:
            if self._serving_object is None and self._last_served_object_id is not None:
                self.try_get_multi_serve_object()
                self.populate_statistic_tracker()
                self._change_state(self.recover_from_load_state())
            elif self._servings_remaining > 0:
                self._change_state(self.get_single_serving_state())
            else:
                self._self_destruct()

    def on_all_sims_spawned(self) -> 'None':
        self._sims_spawned = True
        self._try_change_state()

    def on_add_interaction_liability(self, interaction:'Interaction') -> 'None':
        self._interaction = interaction
        self._group_id = self._interaction.group_id
        self._try_change_state()

    def populate_statistic_tracker(self) -> 'None':
        self._object_stat_tracker = self._serving_object.get_tracker(CraftingTuning.SERVINGS_STATISTIC)

    @classmethod
    def default_job(cls) -> 'SituationJob':
        return cls.serving_sim_job_and_role.job

    @classmethod
    def get_sims_expected_to_be_in_situation(cls) -> 'int':
        return 1

    def try_get_multi_serve_object(self) -> 'Optional[BaseObject]':
        if self._serving_object_id is not None:
            target_sources = set()
            if self._interaction is not None:
                target_sources.add(self._interaction.target)
            target_sources.update((services.inventory_manager().get(self._serving_object_id), services.object_manager().get(self._serving_object_id)))
            self._serving_object = next(filter(lambda obj: obj is not None and obj.id == self._serving_object_id, target_sources), None)
        return self._serving_object

    def get_actor_sim(self) -> 'Sim':
        return self.initiating_sim_info.get_sim_instance()

    def get_context(self) -> 'InteractionContext':
        return InteractionContext(self.get_actor_sim(), InteractionContext.SOURCE_SCRIPT, Priority.High, run_priority=Priority.Low, insert_strategy=QueueInsertStrategy.NEXT, group_id=self._group_id)

    def decrement_servings_remaining(self) -> 'None':
        self._servings_remaining = self._servings_remaining - 1

    def has_servings_remaining(self) -> 'bool':
        if self._object_stat_tracker is None:
            self.populate_statistic_tracker()
        return self._servings_remaining > 0 and self._object_stat_tracker.get_value(CraftingTuning.SERVINGS_STATISTIC) > 0
