from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from routing.walkstyle.walkstyle_tuning import Walkstyle
    from sims.sim import Sim
    from typing import *from _collections import defaultdictfrom animation import AnimationContext, get_throwaway_animation_contextfrom animation.animation_utils import create_run_animationfrom animation.arb import Arbfrom animation.asm import create_asmfrom contextlib import contextmanagerimport itertoolsimport operatorimport weakreffrom element_utils import build_critical_section, build_elementfrom event_testing.resolver import DoubleSimResolverfrom horse import horse_handlersfrom horse.horse_tuning import HorseTuningfrom interactions.utils.routing import FollowPathfrom animation.animation_interaction import AnimationInteractionfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContextfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom interactions.utils.interaction_liabilities import StandSlotReservationLiability, STAND_SLOT_LIABILITYfrom objects.components import Component, types, componentmethodfrom objects.helpers.user_footprint_helper import UserFootprintHelperfrom postures import DerailReasonfrom routing import has_walkstyle_info, PathNodeTransition, FOOTPRINT_KEY_ON_LOTfrom routing.formation.formation_type_base import FormationRoutingTypefrom routing.object_routing.object_routing_component import ObjectRoutingComponentfrom routing.path_planner.path_plan_context import PathPlanContextWrapperfrom routing.route_enums import RoutingStageEventfrom routing.route_events.route_event_context import RouteEventContextfrom routing.walkstyle.walkstyle_behavior import WalksStyleBehaviorfrom routing.walkstyle.walkstyle_carry_overrides import WalkstyleCarryOverridesfrom routing.walkstyle.walkstyle_enums import WalkStylePriorityfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom sims.sim_info_types import Age, SpeciesExtended, Genderfrom sims4.callback_utils import CallableListfrom sims4.tuning.tunable import HasTunableFactory, TunableTuple, AutoFactoryInit, TunableEnumEntry, OptionalTunable, TunableListfrom sims4.utils import RegistryHandlefrom singletons import DEFAULTimport gsi_handlersimport objectsimport placementimport servicesimport sims4.loglogger = sims4.log.Logger('RoutingComponent')ROUTE_EVENT_WINDOW_DURATION = 10
class RoutingComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.ROUTING_COMPONENT):
    _pathplan_context = None
    FACTORY_TUNABLES = {'plan_context_data': TunableTuple(description='\n            Data used to populate fields on the path plan context.\n            ', default_context=PathPlanContextWrapper.TunableFactory(description="\n                If no age override is specified, the default path plan data to\n                use for this agent's path planning.\n                "), context_age_species_overrides=TunableList(description='\n                List of age-species path plan context overrides for a specific\n                routing agent.\n                ', tunable=TunableTuple(description='\n                    Overrides to the path plan context of the agent defined by a\n                    combination of age and species.\n                    ', age=TunableEnumEntry(description='\n                        The age this override applies to.\n                        ', tunable_type=Age, default=Age.ADULT), species=TunableEnumEntry(description='\n                        The species this override applies to.\n                        ', tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,)), context_override=PathPlanContextWrapper.TunableFactory()))), 'walkstyle_behavior': WalksStyleBehavior.TunableFactory(description='\n            Define the walkstyle behavior for owners of this component.\n            '), 'object_routing_component': OptionalTunable(description='\n            If enabled, this object will have an Object Routing component, which\n            controls an object routing behavior based on triggered states.\n            ', tunable=ObjectRoutingComponent.TunableFactory())}

    def __init__(self, owner, **kwargs):
        super().__init__(owner, **kwargs)
        self.owner = owner
        walkstyle_behavior = self.get_walkstyle_behavior()
        self._walkstyle_requests = [WalkStyleRequest(self.owner, walkstyle=walkstyle_behavior.default_walkstyle, priority=-1)]
        self._walk_style_handles = {}
        self.wading_buff_handle = None
        self.last_route_has_wading_nodes = False
        self._routing_stage_event_callbacks = defaultdict(CallableList)
        if owner.is_sim:
            owner.remove_component(objects.components.types.FOOTPRINT_COMPONENT)
        self._path_plan_context_map = {}
        self.on_slot = None
        self.stand_slot_reservation_removed_callbacks = CallableList()
        self._active_follow_path_weakref = None
        self.on_follow_path = CallableList()
        self.on_plan_path = CallableList()
        self.on_set_routing_path = CallableList()
        self.on_intended_location_changed = CallableList()
        self._current_path = None
        self._routing_slave_data = []
        self._pending_clear_slaves = []
        self._routing_master_ref = None
        self._default_agent_radius = None
        self._route_event_context = RouteEventContext()
        self._route_interaction = None
        self._animation_context = None
        self._initial_carry_targets = None
        self._route_event_provider_requests = None
        self._routing_target = None
        self._routing_owner = None
        self._path_node_transitions = defaultdict(int)
        if self.object_routing_component is None:
            self._object_routing_component = None
        else:
            self._object_routing_component = self.object_routing_component(self.owner)

    def get_subcomponents_gen(self):
        yield from super().get_subcomponents_gen()
        if self._object_routing_component is not None:
            yield from self._object_routing_component.get_subcomponents_gen()

    def get_object_routing_component(self):
        return self._object_routing_component

    @componentmethod
    def set_routing_target(self, routing_target):
        self._routing_target = weakref.ref(routing_target) if routing_target is not None else None

    @componentmethod
    def get_routing_target(self):
        if self._routing_target is None:
            return
        return self._routing_target()

    @componentmethod
    def set_routing_owner(self, owner):
        self._routing_owner = weakref.ref(owner) if owner is not None else None

    @componentmethod
    def get_routing_owner(self):
        if self._routing_owner is None:
            return
        return self._routing_owner()

    @property
    def current_path(self):
        return self._current_path

    @property
    def object_radius(self):
        return self._pathplan_context.agent_radius

    @property
    def route_event_context(self):
        return self._route_event_context

    @componentmethod
    def register_routing_stage_event(self, routing_stage_event, callback):
        self._routing_stage_event_callbacks[routing_stage_event].register(callback)

    def _on_routing_stage_event(self, routing_stage_event, **kwargs):
        callbacks = self._routing_stage_event_callbacks.get(routing_stage_event)
        if callbacks is not None:
            callbacks(self.owner, routing_stage_event, **kwargs)

    @contextmanager
    def temporary_walkstyle_request(self, walkstyle_request_factory):
        try:
            request = walkstyle_request_factory(self.owner)
            request.start()
            yield None
        finally:
            request.stop()

    @componentmethod
    def unregister_routing_stage_event(self, routing_stage_event, callback):
        self._routing_stage_event_callbacks[routing_stage_event].unregister(callback)

    @componentmethod
    def get_walkstyle_behavior(self):
        return self.walkstyle_behavior

    @staticmethod
    def try_get_carry_compatible_walkstyle_override(walkstyle:'Walkstyle', actor:'Sim', carry_target:'Sim') -> 'Optional[Walkstyle]':
        walkstyle_overrides = WalkstyleCarryOverrides.CARRY_COMPATIBLE_WALKSTYLE_OVERRIDE_MAP.get(walkstyle, None)
        if walkstyle_overrides is not None:
            resolver = DoubleSimResolver(actor.sim_info, carry_target.sim_info)
            for walkstyle_override in walkstyle_overrides:
                if walkstyle_override.tests.run_tests(resolver):
                    return walkstyle_override.walkstyle

    @componentmethod
    def get_valid_walkstyle_and_request(self, cost_tuning):
        walkstyle_behavior = self.walkstyle_behavior
        carrying_anything = self.owner.is_sim and any(self.owner.posture_state.carry_targets)
        for walkstyle_request in self._walkstyle_requests:
            if walkstyle_request.priority != WalkStylePriority.COMBO:
                if carrying_anything and walkstyle_behavior.incompatible_with_carry(walkstyle_request):
                    pass
                else:
                    walkstyle_cost = cost_tuning.get(walkstyle_request.walkstyle, None)
                    if walkstyle_cost is None:
                        return (walkstyle_request.walkstyle, walkstyle_request)
                    current_value = self.owner.get_stat_value(walkstyle_cost.walkstyle_cost_statistic)
                    if current_value - walkstyle_cost.cost > walkstyle_cost.walkstyle_cost_statistic.min_value:
                        return (walkstyle_request.walkstyle, walkstyle_request)
        return (walkstyle_behavior.default_walkstyle, None)

    @componentmethod
    def get_default_walkstyle(self):
        (walkstyle, _) = self.walkstyle_behavior.get_default_walkstyle_and_request(self.owner)
        return walkstyle

    @componentmethod
    def get_walkstyle(self):
        for walkstyle in self._walkstyle_requests:
            if walkstyle.priority != WalkStylePriority.COMBO:
                return walkstyle.walkstyle
        walkstyle_behavior = self.get_walkstyle_behavior()
        return walkstyle_behavior.default_walkstyle

    @componentmethod
    def get_walkstyle_for_path(self, path) -> 'Walkstyle':
        return self.walkstyle_behavior.get_walkstyle_for_path(self.owner, path)

    @componentmethod
    def get_walkstyle_for_current_path(self) -> 'Walkstyle':
        return self.get_walkstyle_for_path(self.current_path)

    @componentmethod
    def get_walkstyle_list(self):
        return tuple(request.walkstyle for request in self._walkstyle_requests)

    @componentmethod
    def get_walkstyle_requests(self):
        return self._walkstyle_requests

    def _get_walkstyle_key(self):
        if self.owner.is_sim:
            return (self.owner.age, self.owner.gender, self.owner.extended_species)
        return (Age.ADULT, Gender.MALE, SpeciesExtended.HUMAN)

    @componentmethod
    def request_walkstyle(self, walkstyle_request, uid):
        if walkstyle_request.priority != WalkStylePriority.COMBO and not has_walkstyle_info(walkstyle_request.walkstyle, self._get_walkstyle_key()):
            return
        self._walkstyle_requests.append(walkstyle_request)
        self._walkstyle_requests.sort(reverse=True, key=operator.attrgetter('priority'))
        self._walk_style_handles[uid] = RegistryHandle(lambda : self._unrequest_walkstyle(walkstyle_request))
        self.pathplan_context.handle_update_walkstyle(walkstyle_request.walkstyle)
        self._update_walkstyle()

    @componentmethod
    def remove_walkstyle(self, uid):
        if uid in self._walk_style_handles:
            self._walk_style_handles[uid].release()
            del self._walk_style_handles[uid]

    def _unrequest_walkstyle(self, walkstyle_request):
        self._walkstyle_requests.remove(walkstyle_request)
        self.pathplan_context.handle_update_walkstyle(None)
        self._update_walkstyle()

    def _update_walkstyle(self):
        for primitive in self.owner.primitives:
            try:
                primitive.request_walkstyle_update()
            except AttributeError:
                pass

    @componentmethod
    def get_additional_scoring_for_surface(self, surface_type):
        return self._pathplan_context.surface_preference_scoring.get(surface_type, 0)

    @componentmethod
    def add_location_to_quadtree(self, *args, **kwargs):
        path_plan_context = self._pathplan_context
        return path_plan_context.add_location_to_quadtree(*args, **kwargs)

    @componentmethod
    def remove_location_from_quadtree(self, *args, **kwargs):
        path_plan_context = self._pathplan_context
        return path_plan_context.remove_location_from_quadtree(*args, **kwargs)

    @property
    def _pathplan_context(self):
        age_key = getattr(self.owner, 'age', DEFAULT)
        species_key = getattr(self.owner, 'extended_species', DEFAULT)
        combined_override_key = (age_key, species_key)
        if combined_override_key in self._path_plan_context_map:
            return self._path_plan_context_map[combined_override_key]
        for override in self.plan_context_data.context_age_species_overrides:
            if override.age == age_key and override.species == species_key:
                self._path_plan_context_map[combined_override_key] = override.context_override(self.owner)
                return self._path_plan_context_map[combined_override_key]
        self._path_plan_context_map.clear()
        self._path_plan_context_map[combined_override_key] = self.plan_context_data.default_context(self.owner)
        return self._path_plan_context_map[combined_override_key]

    @componentmethod
    def get_routing_context(self):
        return self.pathplan_context

    def on_sim_added(self):
        self._update_quadtree_location()

    def on_sim_removed(self):
        self.on_slot = None
        self._routing_master_ref = None
        self.clear_routing_slaves()

    def on_reset_internal_state(self, reset_reason):
        self.clear_routing_slaves()

    def add_callbacks(self):
        self.owner.register_on_location_changed(self._update_quadtree_location)
        self.owner.register_on_location_changed(self._check_violations)
        if self.get_walkstyle_behavior().supports_wading_walkstyle_buff(self.owner):
            self.owner.register_on_location_changed(self.get_walkstyle_behavior().check_for_wading)
        self.on_plan_path.append(self._on_update_goals)
        self.on_intended_location_changed.append(self.owner.refresh_los_constraint)
        self.on_intended_location_changed.append(self.owner._update_social_geometry_on_location_changed)
        self.on_intended_location_changed.append(lambda *_, **__: self.owner.two_person_social_transforms.clear())
        self.on_intended_location_changed.append(self.owner.update_intended_position_on_active_lot)

    def remove_callbacks(self):
        self.on_intended_location_changed.clear()
        if self._on_update_goals in self.on_plan_path:
            self.on_plan_path.remove(self._on_update_goals)
        if self.owner._on_location_changed_callbacks is not None and self._check_violations in self.owner._on_location_changed_callbacks:
            self.owner.unregister_on_location_changed(self._check_violations)
        if self.owner._on_location_changed_callbacks is not None and self._update_quadtree_location in self.owner._on_location_changed_callbacks:
            self.owner.unregister_on_location_changed(self._update_quadtree_location)

    @property
    def pathplan_context(self):
        return self._pathplan_context

    def get_or_create_routing_context(self):
        return self._pathplan_context

    @property
    def routing_context(self):
        return self._pathplan_context

    @property
    def connectivity_handles(self):
        return self._pathplan_context.connectivity_handles

    @property
    def is_moving(self):
        if self.owner.is_sim:
            return not self.owner.location.almost_equal(self.owner.intended_location)
        else:
            return self.current_path is not None and not self.current_path.finished

    @property
    def routing_master(self):
        if self._routing_master_ref is not None:
            return self._routing_master_ref()

    @routing_master.setter
    def routing_master(self, value):
        self._routing_master_ref = value.ref() if value is not None else None

    @property
    def required_formation_si(self):
        routing_master = self.routing_master
        if routing_master is None:
            return
        else:
            formation_data = routing_master.get_formation_data_for_slave(self.owner)
            if formation_data:
                return formation_data.required_interaction

    @property
    def route_interaction(self):
        return self._route_interaction

    @property
    def animation_context(self):
        if self._route_interaction is not None:
            return self._route_interaction.animation_context
        return self._animation_context

    SLAVE_RADIUS_MODIFIER = 0.5
    MAX_ALLOWED_AGENT_RADIUS = 0.25

    def _update_agent_radius(self):
        agent_radius_datas = [slave_data for slave_data in self._routing_slave_data if slave_data.should_increase_master_agent_radius]
        if not agent_radius_datas:
            return
        max_x = max(abs(slave_data.offset[0]) for slave_data in agent_radius_datas)
        max_x = max(max_x*self.SLAVE_RADIUS_MODIFIER, self._default_agent_radius)
        self._pathplan_context.agent_radius = min(self.MAX_ALLOWED_AGENT_RADIUS, max_x)

    @componentmethod
    def set_should_track_path_transition(self, transition_type, should_track):
        if should_track:
            self._path_node_transitions[transition_type] += 1
        else:
            if self._path_node_transitions[transition_type] <= 0:
                logger.error('Mismatch in requests to start and stop tracking {} path transition for agent {}.', transition_type, self.owner, owner='rrodgers')
            self._path_node_transitions[transition_type] -= 1

    @componentmethod
    def should_track_path_transition(self, transition_type):
        if self._path_node_transitions[transition_type] <= 0:
            return False
        if (transition_type == PathNodeTransition.PATH_NODE_TRANSITION_FIRST_INDOOR or transition_type == PathNodeTransition.PATH_NODE_TRANSITION_LAST_INDOOR) and not self.pathplan_context.get_key_mask() & FOOTPRINT_KEY_ON_LOT:
            return False
        return self._path_node_transitions[transition_type] > 0

    def add_routing_slave(self, slave_data):
        if len(self._routing_slave_data) == 0:
            self._default_agent_radius = self._pathplan_context.agent_radius
        slave_data.slave.routing_master = self.owner
        self._routing_slave_data.append(slave_data)
        slave_data.on_add()
        self._update_agent_radius()

    def clear_routing_slaves(self):
        for slave_data in self._routing_slave_data:
            slave_data.slave.routing_master = None
            slave_data.on_release()
        self._routing_slave_data.clear()
        self._restore_agent_radius()
        self._update_agent_radius()

    @componentmethod
    def get_routing_slave_data(self):
        return self._routing_slave_data

    @componentmethod
    def get_formation_data_for_slave(self, obj):
        for slave_data in self._routing_slave_data:
            if slave_data.slave is obj:
                return slave_data

    @componentmethod
    def get_all_routing_slave_data_gen(self):
        yield from self._routing_slave_data

    @componentmethod
    def get_routing_slave_data_count(self, formation_type):
        return sum(1 for slave_data in self._routing_slave_data if slave_data.formation_type is formation_type)

    def clear_slave(self, slave):
        if any(primitive for primitive in self.owner.primitives if isinstance(primitive, FollowPath)):
            self._pending_clear_slaves.append(slave)
        else:
            self._clear_slave(slave)

    def _clear_slave(self, slave):
        for slave_data in self._routing_slave_data:
            if slave_data.slave is slave:
                self._routing_slave_data.remove(slave_data)
                slave_data.on_release()
                break
        self._restore_agent_radius()
        slave.routing_master = None
        self._update_agent_radius()

    @componentmethod
    def process_pending_clear_slaves(self):
        for slave in self._pending_clear_slaves:
            self._clear_slave(slave)
        self._pending_clear_slaves = []

    @componentmethod
    def write_slave_data_msg(self, route_msg, path=None):
        transitioning_sims = ()
        actor = self.owner
        if actor.transition_controller is not None:
            transitioning_sims = actor.transition_controller.get_transitioning_sims()
        for slave_data in self.get_routing_slave_data():
            if actor is slave_data.slave:
                logger.error('Attempting to add slave_data to a routing pb when the slave and the master are the same ({}) in interaction ({}).', actor, slave_data.interaction)
            elif slave_data.should_slave_for_path(path) and not (slave_data.slave in transitioning_sims or slave_data.has_affordance_pause_slave_routing()):
                if slave_data.on_leader_using_specific_walkstyle():
                    pass
                else:
                    (slave_actor, slave_msg) = slave_data.add_routing_slave_to_pb(route_msg, path=path)
                    slave_actor.write_slave_data_msg(slave_msg, path=path)

    def _restore_agent_radius(self):
        if len(self._routing_slave_data) == 0:
            self._pathplan_context.agent_radius = self._default_agent_radius
            self._default_agent_radius = None

    def contains_slave(self, slave):
        return any(slave.id == slave_data.slave.id for slave_data in self._routing_slave_data)

    def _on_update_goals(self, goal_list, starting):
        NUM_GOALS_TO_RESERVE = 2
        for (index, goal) in enumerate(goal_list, start=1):
            if index > NUM_GOALS_TO_RESERVE:
                break
            if starting:
                self.add_location_to_quadtree(placement.ItemType.SIM_INTENDED_POSITION, position=goal.position, orientation=goal.orientation, routing_surface=goal.routing_surface_id, index=index)
            else:
                self.remove_location_from_quadtree(placement.ItemType.SIM_INTENDED_POSITION, index=index)

    def set_portal_mask_flag(self, flag):
        self._pathplan_context.set_portal_key_mask(self._pathplan_context.get_portal_key_mask() | flag)

    def clear_portal_mask_flag(self, flag):
        self._pathplan_context.set_portal_key_mask(self._pathplan_context.get_portal_key_mask() & ~flag)

    def set_portal_discouragement_mask_flag(self, flag):
        self._pathplan_context.set_portal_discourage_key_mask(self._pathplan_context.get_portal_discourage_key_mask() | flag)

    def clear_portal_discouragement_mask_flag(self, flag):
        self._pathplan_context.set_portal_discourage_key_mask(self._pathplan_context.get_portal_discourage_key_mask() & ~flag)

    def set_portal_exclusion_mask_flag(self, flag):
        self._pathplan_context.set_portal_exclusion_key_mask(self._pathplan_context.get_portal_exclusion_key_mask() | flag)

    def clear_portal_exclusion_mask_flag(self, flag):
        self._pathplan_context.set_portal_exclusion_key_mask(self._pathplan_context.get_portal_exclusion_key_mask() & ~flag)

    @componentmethod
    def update_portal_locks(self):
        agent = self.owner
        services.object_manager().add_portal_lock(agent, agent.portal_added_callback)

    def _update_quadtree_location(self, *_, **__):
        self.add_location_to_quadtree(placement.ItemType.SIM_POSITION)

    def add_stand_slot_reservation(self, interaction, position, routing_surface, excluded_sims, skip_move_away=False):
        interaction.add_liability(STAND_SLOT_LIABILITY, StandSlotReservationLiability(self.owner, interaction))
        excluded_sims.add(self.owner)
        self._stand_slot_reservation = position
        self.add_location_to_quadtree(placement.ItemType.ROUTE_GOAL_SUPPRESSOR, position=position, routing_surface=routing_surface)
        pathplan_context = self._pathplan_context
        reservation_radius = pathplan_context.agent_radius*2
        polygon = sims4.geometry.generate_circle_constraint(6, position, reservation_radius)
        self.on_slot = (position, polygon, routing_surface)
        if not skip_move_away:
            UserFootprintHelper.force_move_sims_in_polygon(polygon, routing_surface, exclude=excluded_sims)

    def remove_stand_slot_reservation(self, interaction):
        self.remove_location_from_quadtree(placement.ItemType.ROUTE_GOAL_SUPPRESSOR)
        self.on_slot = None
        self.stand_slot_reservation_removed_callbacks(sim=self.owner, interaction=interaction)

    def get_stand_slot_reservation_violators(self, excluded_sims=()):
        if not self.on_slot:
            return
        (_, polygon, routing_surface) = self.on_slot
        violators = []
        excluded_sims = {sim for sim in itertools.chain((self.owner,), excluded_sims)}
        for sim_nearby in placement.get_nearby_sims_gen(polygon.centroid(), routing_surface, radius=polygon.radius(), exclude=excluded_sims):
            if sims4.geometry.test_point_in_polygon(sim_nearby.position, polygon) and not sim_nearby.ignore_blocking_near_destination:
                violators.append(sim_nearby)
        return violators

    def _check_violations(self, *_, **__):
        if services.privacy_service().check_for_late_violators(self.owner):
            return
        for reaction_trigger in self.owner.reaction_triggers.values():
            reaction_trigger.intersect_and_execute(self.owner)

    def create_route_interaction(self):
        if self.owner.is_sim:
            aop = AffordanceObjectPair(AnimationInteraction, None, AnimationInteraction, None, hide_unrelated_held_props=False)
            context = InteractionContext(self.owner, InteractionContext.SOURCE_SCRIPT, Priority.High)
            self._route_interaction = aop.interaction_factory(context).interaction
        else:
            self._animation_context = AnimationContext()
            self._animation_context.add_ref(self._current_path)
        for slave_data in self.get_routing_slave_data():
            slave_data.slave.routing_component.create_route_interaction()

    def cancel_route_interaction(self):
        if self._route_interaction is not None:
            self._route_interaction.cancel(FinishingType.AUTO_EXIT, 'Route Ended.')
            self._route_interaction.on_removed_from_queue()
            self._route_interaction = None
        if self._animation_context is not None:
            self._animation_context.release_ref(self._current_path)
            self._animation_context = None
        for slave_data in self.get_routing_slave_data():
            slave_data.slave.routing_component.cancel_route_interaction()

    def set_follow_path(self, follow_path):
        self._active_follow_path_weakref = weakref.ref(follow_path)

    def clear_follow_path(self):
        self._active_follow_path_weakref = None

    def _get_active_follow_path(self):
        if self._active_follow_path_weakref is not None:
            return self._active_follow_path_weakref()

    def get_approximate_cancel_location(self):
        follow_path = self._get_active_follow_path()
        if follow_path is not None:
            ret = follow_path.get_approximate_cancel_location()
            if ret is not None:
                return ret
        return (self.owner.intended_transform, self.owner.intended_routing_surface)

    @componentmethod
    def set_routing_path(self, path):
        if path is None:
            self._current_path.finished = True
            if gsi_handlers.route_event_handlers.archiver.enabled:
                gsi_handlers.route_event_handlers.archive_route_events(self._current_path, self.owner, gsi_handlers.route_event_handlers.PATH_TYPE_FINISHED, clear=True)
            self._on_routing_stage_event(RoutingStageEvent.ROUTE_END, path=self._current_path)
            self.cancel_route_interaction()
            self._current_path = None
            if self.owner.is_sim and self.owner.transition_controller is not None and self._initial_carry_targets != self.owner.posture_state.carry_targets:
                self.owner.transition_controller.derail(DerailReason.CONSTRAINTS_CHANGED, self.owner)
            self._initial_carry_targets = None
            return
        if self.owner.is_sim:
            self._initial_carry_targets = self.owner.posture_state.carry_targets
        self._current_path = path
        if self.pathplan_context.disable_fake_portals:
            self._current_path.remove_fake_portals()
        self.create_route_interaction()
        self._on_routing_stage_event(RoutingStageEvent.ROUTE_START, path=path)
        walkstyle = self.walkstyle_behavior.apply_walkstyle_to_path(self.owner, self._current_path)
        origin_q = (float(self.owner.orientation.x), float(self.owner.orientation.y), float(self.owner.orientation.z), float(self.owner.orientation.w))
        origin_t = (float(self.owner.position.x), float(self.owner.position.y), float(self.owner.position.z))
        (age, gender, species) = self._get_walkstyle_key()
        self._current_path.nodes.apply_initial_timing(origin_q, origin_t, walkstyle, age, gender, species, int(services.time_service().sim_now), services.current_zone_id())
        self.on_set_routing_path(self._current_path)

    @componentmethod
    def update_routing_path(self, time_offset):
        if self._current_path is None:
            return
        walkstyle = self.walkstyle_behavior.apply_walkstyle_to_path(self.owner, self._current_path, time_offset=time_offset)
        (age, gender, species) = self._get_walkstyle_key()
        self._current_path.nodes.update_timing(walkstyle, age, gender, species, time_offset, services.current_zone_id())

    @componentmethod
    def update_slave_positions_for_path(self, path, transform, orientation, routing_surface, distribute=True, canceled=False):
        transitioning_sims = ()
        if self.owner.transition_controller is not None:
            transitioning_sims = self.owner.transition_controller.get_transitioning_sims()
        for slave_data in self.get_routing_slave_data():
            if slave_data.slave in transitioning_sims:
                pass
            else:
                slave_data.update_slave_position(transform, orientation, routing_surface, distribute=distribute, path=path, canceled=canceled)

    def add_route_event_provider(self, request):
        if self._route_event_provider_requests is None:
            self._route_event_provider_requests = []
        self._route_event_provider_requests.append(request)

    def remove_route_event_provider(self, request):
        if self._route_event_provider_requests is not None and request in self._route_event_provider_requests:
            self._route_event_provider_requests.remove(request)
        if not self._route_event_provider_requests:
            self._route_event_provider_requests = None

    def route_event_executed(self, event_id):
        for slave_data in self.get_routing_slave_data():
            if slave_data.slave.routing_component.route_event_executed(event_id):
                return True
        if self._route_event_context is None:
            return False
        return self._route_event_context.handle_route_event_executed(event_id, self.owner, path=self._current_path)

    def route_event_skipped(self, event_id):
        for slave_data in self.get_routing_slave_data():
            if slave_data.slave.routing_component.route_event_skipped(event_id):
                return True
        if self._route_event_context is None:
            return False
        return self._route_event_context.handle_route_event_skipped(event_id, self.owner, path=self._current_path)

    def remove_route_event_by_data(self, event_data):
        if self._route_event_context is None:
            return
        self._route_event_context.remove_route_event_by_data(event_data)

    @componentmethod
    def route_finished(self, path_id):
        for primitive in self.owner.primitives:
            if hasattr(primitive, 'route_finished'):
                primitive.route_finished(path_id)

    @componentmethod
    def route_time_update(self, path_id, current_time):
        for primitive in self.owner.primitives:
            if hasattr(primitive, 'route_time_update'):
                primitive.route_time_update(path_id, current_time)

    def _gather_route_events(self, path, **kwargs):
        owner = self.owner
        if owner.is_sim:
            interaction = owner.transition_controller.interaction if owner.transition_controller is not None else None
            if interaction is not None and interaction.is_super:
                interaction.provide_route_events(self._route_event_context, owner, path, **kwargs)
            owner.Buffs.provide_route_events_from_buffs(self._route_event_context, owner, path, **kwargs)
        broadcaster_service = services.current_zone().broadcaster_service
        broadcaster_service.provide_route_events(self._route_event_context, owner, path, **kwargs)
        if owner.weather_aware_component is not None:
            owner.weather_aware_component.provide_route_events(self._route_event_context, owner, path, **kwargs)
        if self._route_event_provider_requests is not None:
            for request in self._route_event_provider_requests:
                request.provide_route_events(self._route_event_context, owner, path, **kwargs)
        object_manager = services.object_manager(owner.zone_id)
        if object_manager is not None:
            for node in path.nodes:
                if node.portal_object_id != 0:
                    portal_object = object_manager.get(node.portal_object_id)
                    if portal_object is not None:
                        portal_object.provide_route_events(node.portal_id, self._route_event_context, owner, path, node=node, **kwargs)

    def clear_route_events(self, *args, **kwargs):
        if self._route_event_context is None:
            return
        self._route_event_context.clear_route_events()
        for slave_data in self.get_routing_slave_data():
            slave_data.slave.routing_component.clear_route_events()

    def schedule_and_process_route_events_for_new_path(self, path):
        if self._route_event_context is None:
            return
        if self.owner.is_sim and not self.owner.posture.mobile:
            return
        self.clear_route_events()
        start_time = RouteEventContext.ROUTE_TRIM_START
        end_time = min(start_time + ROUTE_EVENT_WINDOW_DURATION, path.duration())
        self._gather_route_events(path, start_time=start_time, end_time=end_time)
        self._route_event_context.schedule_route_events(self.owner, path)
        self._route_event_context.process_route_events(self.owner)
        for slave_data in self.get_routing_slave_data():
            slave_data.slave.routing_component.schedule_and_process_route_events_for_new_path(path)
        if gsi_handlers.route_event_handlers.archiver.enabled:
            gsi_handlers.route_event_handlers.archive_route_events(path, self.owner, gsi_handlers.route_event_handlers.PATH_TYPE_INITIAL)

    def append_route_events_to_route_msg(self, route_msg):
        if self._route_event_context is None:
            return
        self._route_event_context.append_route_events_to_route_msg(route_msg)
        for slave_data in self.get_routing_slave_data():
            slave_data.slave.routing_component.append_route_events_to_route_msg(route_msg)

    def update_route_events_for_current_path(self, path, current_time, time_offset):
        (failed_events, failed_types) = self._route_event_context.prune_stale_events_and_get_failed_types(self.owner, path, current_time)
        start_time = current_time
        window_duration = ROUTE_EVENT_WINDOW_DURATION
        if time_offset < 0:
            window_duration -= time_offset
        end_time = min(start_time + window_duration, path.duration())
        self._gather_route_events(path, failed_types=failed_types, start_time=start_time, end_time=end_time)
        self._route_event_context.schedule_route_events(self.owner, path, start_time=start_time)
        should_update = True if failed_events else False or self._route_event_context.has_pending_events_to_process()
        for slave_data in self.get_routing_slave_data():
            should_update |= slave_data.slave.routing_component.update_route_events_for_current_path(path, current_time, time_offset)
        if gsi_handlers.route_event_handlers.archiver.enabled and gsi_handlers.route_event_handlers.update_log_enabled:
            gsi_handlers.route_event_handlers.archive_route_events(path, self.owner, gsi_handlers.route_event_handlers.PATH_TYPE_UPDATE)
        return should_update

    def process_updated_route_events(self):
        self._route_event_context.process_route_events(self.owner)
        for slave_data in self.get_routing_slave_data():
            slave_data.slave.routing_component.process_updated_route_events()

    @componentmethod
    def should_route_instantly(self):
        zone = services.current_zone()
        if zone.force_route_instantly:
            return True
        if self.owner.is_sim:
            if not (zone.are_sims_hitting_their_marks and self.owner._allow_route_instantly_when_hitting_marks):
                return False
            else:
                return not services.sim_spawner_service().sim_is_leaving(self.owner)
        return False

    @componentmethod
    def maybe_append_reins_animation(self, interaction, sequence):

        def set_next_reins_state_if_valid(slave_data, next_state_override=None):
            if slave_data.routing_type.routing_type is not FormationRoutingType.PAIRED_HORSE:
                return
            current_reins_state = slave_data.routing_type.reins_state
            if current_reins_state is None:
                return
            else:
                next_reins_state = next_state_override
                if next_reins_state is None:
                    next_reins_state = interaction.get_require_reins_up(slave_data)
                if current_reins_state == next_reins_state:
                    return
            return next_reins_state

        def run_reins_animation(actor, target, formation, next_reins_state):

            def _set_reins_state():
                formation.reins_state = next_reins_state
                if next_reins_state:
                    target.remove_trait(HorseTuning.REINS_DOWN_TRAIT)
                else:
                    target.add_trait(HorseTuning.REINS_DOWN_TRAIT)
                if horse_handlers.archiver.enabled:
                    horse_handlers.log_horse_reins_animation_archive_data(actor, next_reins_state, interaction)

            reins_animation = None
            if next_reins_state:
                reins_animation = formation.reins_animation_tuning.pickup_animation(interaction)
            else:
                reins_animation = formation.reins_animation_tuning.putdown_animation(interaction)
            asm = create_asm(reins_animation.asm_key, context=get_throwaway_animation_context())
            if asm is None:
                return sequence
            asm.set_actor(reins_animation.actor_name, actor)
            asm.set_actor(reins_animation.target_name, target)
            reins_arb = Arb()
            reins_animation.append_to_arb(asm, reins_arb)
            element = build_critical_section(create_run_animation(reins_arb), lambda _: _set_reins_state())
            new_sequence = (build_element(element), sequence)
            return new_sequence

        owner = self.owner
        master = owner.routing_master
        interaction_sim = interaction.sim
        interaction_target = interaction.target
        routing_master = interaction_sim.routing_master
        if routing_master is not None and (interaction_target is not None and interaction_target.is_sim) and routing_master is not interaction_target:
            reins_down_target = True
        else:
            reins_down_target = False
        if master is not None:
            if interaction_sim is master:
                return sequence
            slave_data = master.get_formation_data_for_slave(owner)
            next_state_override = False if interaction_target is owner or reins_down_target else None
            next_reins_state = set_next_reins_state_if_valid(slave_data, next_state_override)
            if next_reins_state is not None:
                return run_reins_animation(master, owner, slave_data.routing_type, next_reins_state)
        for slave_data in self.get_routing_slave_data():
            if interaction_sim is slave_data.slave:
                pass
            else:
                next_state_override = False if reins_down_target else None
                next_reins_state = set_next_reins_state_if_valid(slave_data, next_state_override)
                if next_reins_state is not None:
                    return run_reins_animation(owner, slave_data.slave, slave_data.routing_type, next_reins_state)
        return sequence
