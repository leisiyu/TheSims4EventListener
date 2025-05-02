from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from _sims4_collections import frozendict
    from _math import Vector3Immutable
    from constraints import Constraint
    from objects.game_object import GameObject
    from interactions.base.interaction import Interaction
    from sims.sim import Simfrom _collections import defaultdictimport build_buyimport interactions.constraintsimport routingimport servicesimport sims4.logimport sims4.resourcesimport socials.groupfrom interactions import ParticipantTypefrom interactions.constraints import Anywhere, create_constraint_set, Nowhere, WaterDepthIntervalsfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.routing import get_two_person_transforms_for_jigfrom objects.components.types import PORTAL_COMPONENTfrom objects.pools import pool_utilsfrom routing import SurfaceType, SurfaceIdentifierfrom sims.sim_info_types import Speciesfrom sims4.geometry import PolygonFootprintfrom sims4.math import transform_almost_equal_2dfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunable, TunableSimMinutefrom sims4.utils import classpropertyfrom socials.jigs.jig_utils import JigPositioningfrom socials.jigs.jig_variant import TunableJigVariantfrom socials.side_group import SideGroupfrom world.ocean_tuning import OceanTuninglogger = sims4.log.Logger('Social Group')
class JigGroup(SideGroup):
    HORSE_RIDER_CANCEL_DELAY_ADDITION = TunableSimMinute(description='\n        Amount of extra time a jig group can be inactive before it will shut\n        down if either the target or intiaiting sim is riding a horse. This\n        accounts for the extra time it will take for them to get off the horse.\n        ', default=120)
    INSTANCE_TUNABLES = {'jig': TunableJigVariant(), 'participant_slot_map': TunableMapping(description='\n            The slot index mapping on the jig keyed by participant type.\n            ', key_type=TunableEnumEntry(description='\n                The participant associated with this jig position.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), value_type=Tunable(description='\n                The slot index for this participant.\n                ', tunable_type=int, default=0)), 'cancel_delay': TunableSimMinute(description='\n            Amount of time a jig group must be inactive before it will shut\n            down.\n            ', default=15), 'stay_outside': Tunable(description='\n            Whether the FGL should require the jig to be outside.\n            ', tunable_type=bool, default=False), 'stay_in_enclosed_room': Tunable(description='\n            If checked, the fgl will look within the enclosed room only.\n            ', tunable_type=bool, default=False)}
    DEFAULT_SLOT_INDEX_ACTOR = 1
    DEFAULT_SLOT_INDEX_TARGET = 0

    def __init__(self, *args, si=None, target_sim=None, participant_slot_overrides=None, **kwargs):
        super().__init__(*args, si=si, target_sim=target_sim, **kwargs)
        initiating_sim = si.sim
        if initiating_sim is None or target_sim is None:
            logger.error('JigGroup {} cannot init with initial sim {} or target sim {}', self.__class__.__name__, initiating_sim, target_sim)
            return
        if initiating_sim.is_riding_horse or target_sim.is_riding_horse:
            self.inactivity_time_before_shutdown = self.cancel_delay + self.HORSE_RIDER_CANCEL_DELAY_ADDITION
        else:
            self.inactivity_time_before_shutdown = self.cancel_delay
        self._initating_sim_ref = initiating_sim.ref()
        self._target_sim_ref = target_sim.ref() if target_sim is not None else None
        self._picked_object_ref = si.picked_object.ref() if si.picked_object is not None else None
        self.participant_slot_overrides = participant_slot_overrides
        self._sim_routing_slot_map = {}
        self._jig_polygon = None
        self._jig_positioning_participant = self.get_jig_positioning_participant(si)
        self._create_social_geometry()

    @classproperty
    def is_jig_group(cls):
        return True

    @classmethod
    def _can_picked_object_be_jig(cls, picked_object):
        if picked_object is None:
            return False
        if picked_object.slot is None or picked_object.slot == sims4.resources.INVALID_KEY:
            return False
        if picked_object.is_sim:
            return False
        elif picked_object.carryable_component is not None:
            return False
        return True

    @classmethod
    def get_jig_positioning_participant(cls, inst:'Interaction') -> 'GameObject or None':
        pass

    @classmethod
    def _get_routing_surface_and_kwargs(cls, initiating_sim:'Sim', target_sim:'Sim') -> 'List':
        fallback_routing_surface = None
        if target_sim is None:
            fallback_routing_surface = initiating_sim.routing_surface
        elif initiating_sim.routing_surface != target_sim.routing_surface:
            if initiating_sim.routing_surface.type == routing.SurfaceType.SURFACETYPE_WORLD:
                fallback_routing_surface = initiating_sim.routing_surface
            else:
                fallback_routing_surface = target_sim.routing_surface
        fallback_starting_position = None
        stay_in_connectivity_group = True
        ignore_restrictions = False
        if target_sim.routing_surface.type == SurfaceType.SURFACETYPE_POOL:
            fallback_routing_surface = SurfaceIdentifier(target_sim.routing_surface.primary_id, target_sim.routing_surface.secondary_id, SurfaceType.SURFACETYPE_WORLD)
            ocean = services.terrain_service.ocean_object()
            if ocean is None or target_sim.in_pool or not services.active_lot().is_position_on_lot(target_sim.position):
                extended_species = target_sim.extended_species
                age = target_sim.age
                start_location = ocean.get_nearest_constraint_start_location(extended_species, age, target_sim.position, WaterDepthIntervals.WET)
                if start_location is not None:
                    fallback_starting_position = start_location.transform.translation
            elif target_sim.in_pool:
                pool_block_id = build_buy.get_block_id(target_sim.zone_id, target_sim.position, target_sim.location.level - 1)
                if pool_block_id:
                    pool = pool_utils.get_pool_by_block_id(pool_block_id)
                    if pool is not None:
                        closest = sims4.math.MAX_FLOAT
                        fallback_position = None
                        for part in pool.parts:
                            if not part.has_component(PORTAL_COMPONENT):
                                pass
                            else:
                                (portal_entry, portal_exit) = part.portal_component.get_single_portal_locations()
                                if not portal_entry is None:
                                    if portal_exit is None:
                                        pass
                                    else:
                                        pool_position = portal_exit.position if portal_exit.routing_surface.type == SurfaceType.SURFACETYPE_POOL else portal_entry.position
                                        distance = (pool_position - target_sim.position).magnitude_squared()
                                        if distance < closest:
                                            closest = distance
                                            fallback_position = portal_entry.position if portal_entry.routing_surface.type == SurfaceType.SURFACETYPE_WORLD else portal_exit.position
                        if fallback_position is not None:
                            fallback_starting_position = fallback_position
            stay_in_connectivity_group = False
            ignore_restrictions = True
        reference_routing_surface = initiating_sim.routing_surface if target_sim is not None and target_sim is None else target_sim.routing_surface
        (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(reference_routing_surface, initiating_sim)
        if target_sim is not None:
            (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(reference_routing_surface, target_sim, min_water_depth, max_water_depth)
        initiating_sim_routing_context = initiating_sim.routing_context
        target_sim_routing_context = target_sim.routing_context if target_sim else None
        max_pond_water_depth = None
        if initiating_sim_routing_context is not None:
            if target_sim_routing_context is not None:
                max_pond_water_depth = min(target_sim_routing_context.max_allowed_wading_depth, initiating_sim_routing_context.max_allowed_wading_depth)
            else:
                max_pond_water_depth = initiating_sim_routing_context.max_allowed_wading_depth
        if max_water_depth is not None:
            max_pond_water_depth = min(max_water_depth, max_pond_water_depth)
        if max_pond_water_depth is not None and fallback_routing_surface is not None:
            (fallback_min_water_depth, fallback_max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(fallback_routing_surface, initiating_sim)
            if target_sim is not None:
                (fallback_min_water_depth, fallback_max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(fallback_routing_surface, target_sim, fallback_min_water_depth, fallback_max_water_depth)
        else:
            fallback_min_water_depth = None
            fallback_max_water_depth = None
        fgl_routing_context = initiating_sim.routing_context
        if target_sim.species == Species.HORSE:
            fgl_routing_context = target_sim.routing_context
        fgl_kwargs = {'stay_outside': cls.stay_outside, 'stay_in_enclosed_room': cls.stay_in_enclosed_room, 'fallback_min_water_depth': fallback_min_water_depth, 'fallback_max_water_depth': fallback_max_water_depth, 'fallback_starting_position': fallback_starting_position, 'stay_in_connectivity_group': stay_in_connectivity_group, 'ignore_restrictions': ignore_restrictions, 'min_water_depth': min_water_depth, 'max_water_depth': max_water_depth, 'max_pond_water_depth': max_pond_water_depth, 'routing_context': fgl_routing_context}
        return (fallback_routing_surface, fgl_kwargs)

    @classmethod
    def _get_jig_transforms_gen(cls, initiating_sim:'Sim', target_sim:'Sim', picked_object:'GameObject'=None, participant_slot_overrides:'frozendict'=None, jig_positioning_participant=None) -> 'List':
        slot_map = cls.participant_slot_map if participant_slot_overrides is None else participant_slot_overrides
        actor_slot_index = slot_map.get(ParticipantType.Actor, cls.DEFAULT_SLOT_INDEX_ACTOR)
        target_slot_index = slot_map.get(ParticipantType.TargetSim, cls.DEFAULT_SLOT_INDEX_TARGET)
        if cls._can_picked_object_be_jig(picked_object):
            try:
                (actor_transform, target_transform, routing_surface) = get_two_person_transforms_for_jig(picked_object.definition, picked_object.transform, picked_object.routing_surface, actor_slot_index, target_slot_index)
                yield (actor_transform, target_transform, routing_surface, ())
                return
            except RuntimeError:
                pass
        (fallback_routing_surface, fgl_kwargs) = cls._get_routing_surface_and_kwargs(initiating_sim, target_sim)
        yield from cls.jig.get_transforms_gen(initiating_sim, target_sim, actor_slot_index=actor_slot_index, target_slot_index=target_slot_index, fallback_routing_surface=fallback_routing_surface, fgl_kwargs=fgl_kwargs)

    @classmethod
    def make_constraint_default(cls, actor:'Sim', target_sim:'Sim', position:'Vector3Immutable', routing_surface:'SurfaceIdentifier', participant_type:'ParticipantType'=ParticipantType.Actor, picked_object:'GameObject'=None, participant_slot_overrides:'frozendict'=None, si:'Interaction'=None, **kwargs) -> 'Constraint':
        if participant_type not in (ParticipantType.Actor, ParticipantType.TargetSim):
            return Anywhere()
        jig_positioning_participant = cls.get_jig_positioning_participant(si)
        all_transforms = []
        for (actor_transform, target_transform, routing_surface, _) in cls._get_jig_transforms_gen(actor, target_sim, picked_object=picked_object, participant_slot_overrides=participant_slot_overrides, jig_positioning_participant=jig_positioning_participant):
            if participant_type == ParticipantType.Actor:
                transform = actor_transform
            else:
                transform = target_transform
            if transform is None:
                pass
            else:
                all_transforms.append(interactions.constraints.Transform(transform, routing_surface=routing_surface, debug_name='JigGroupConstraint'))
        if not all_transforms:
            return Nowhere('Unable to get constraints from jig.')
        return create_constraint_set(all_transforms)

    @property
    def initiating_sim(self):
        if self._initating_sim_ref is not None:
            return self._initating_sim_ref()

    @property
    def target_sim(self):
        if self._target_sim_ref is not None:
            return self._target_sim_ref()

    @property
    def picked_object(self):
        if self._picked_object_ref is not None:
            return self._picked_object_ref()

    @property
    def jig_positioning_participant(self) -> 'GameObject or None':
        return self._jig_positioning_participant

    @property
    def group_radius(self):
        if self._jig_polygon is not None:
            return self._jig_polygon.radius()
        return 0

    @property
    def jig_polygon(self):
        return self._jig_polygon

    def _create_social_geometry(self, *args, **kwargs):
        self._sim_transform_map = defaultdict(list)
        self.geometry = None
        for (sim_transform, target_transform, routing_surface, locked_params) in self._get_jig_transforms_gen(self.initiating_sim, self.target_sim, picked_object=self.picked_object, participant_slot_overrides=self.participant_slot_overrides, jig_positioning_participant=self.jig_positioning_participant):
            if not sim_transform is None:
                if target_transform is None:
                    pass
                else:
                    self._sim_transform_map[self.initiating_sim].append((sim_transform, locked_params))
                    self._sim_transform_map[self.target_sim].append((target_transform, ()))
        if not (self._sim_transform_map[self.initiating_sim] and self._sim_transform_map[self.target_sim]):
            self._constraint = Nowhere('JigGroup, failed to FGL and place the jig. Sim: {}, Target Sim: {}, Picked Object: {}', self.initiating_sim, self.target_sim, self.picked_object)
            return
        target_forward = target_transform.transform_vector(sims4.math.FORWARD_AXIS)
        self._set_focus(target_transform.translation, target_forward, routing_surface, refresh_geometry=False)
        self._initialize_constraint(notify=True)

    def _clear_social_geometry(self, *args, **kwargs):
        self._clear_social_polygon_footprint()
        return super()._clear_social_geometry(*args, **kwargs)

    def refresh_position(self):
        self._clear_social_polygon_footprint()
        self._create_social_geometry()

    def _create_social_polygon_footprint(self):
        if self.initiating_sim not in self._sim_routing_slot_map:
            return
        if self.target_sim not in self._sim_routing_slot_map:
            return
        self._clear_social_polygon_footprint()
        self._jig_polygon = self.jig.get_footprint_polygon(self.initiating_sim, self.target_sim, self._sim_routing_slot_map[self.initiating_sim][0], self._sim_routing_slot_map[self.target_sim][0], self.routing_surface)
        if isinstance(self._jig_polygon, PolygonFootprint):
            self.initiating_sim.routing_context.ignore_footprint_contour(self._jig_polygon.footprint_id)
            self.target_sim.routing_context.ignore_footprint_contour(self._jig_polygon.footprint_id)
        self.initiating_sim.on_social_geometry_changed()
        self.target_sim.on_social_geometry_changed()

    def _clear_social_polygon_footprint(self):
        if self._jig_polygon is not None:
            if isinstance(self._jig_polygon, PolygonFootprint):
                self.initiating_sim.routing_context.remove_footprint_contour_override(self._jig_polygon.footprint_id)
                self.target_sim.routing_context.remove_footprint_contour_override(self._jig_polygon.footprint_id)
            self._jig_polygon = None

    def _relocate_group_around_focus(self, *args, **kwargs):
        pass

    def setup_asm_default(self, asm, *args, **kwargs):
        (_, locked_params) = self._sim_routing_slot_map.get(self.initiating_sim, ((), ()))
        if locked_params:
            asm.update_locked_params(locked_params)
        return super().setup_asm_default(asm, *args, **kwargs)

    def _set_sim_intended_location(self, sim, *, intended_location):
        for (transform, locked_params) in self._sim_transform_map.get(sim, ()):
            if transform_almost_equal_2d(transform, intended_location.transform):
                self._sim_routing_slot_map[sim] = (transform, locked_params)
                self._create_social_polygon_footprint()
                break

    def get_constraint(self, sim):
        transforms = self._sim_transform_map.get(sim, None)
        if transforms is not None:
            all_transforms = [interactions.constraints.Transform(transform, routing_surface=self.routing_surface, create_jig_fn=self._set_sim_intended_location) for (transform, _) in transforms]
            return create_constraint_set(all_transforms)
        if sim in self._sim_transform_map:
            return Nowhere("JigGroup, Sim is expected to have a transform but we didn't find a good spot for them. Sim: {}", sim)
        return Anywhere()

    def _make_constraint(self, *args, **kwargs):
        all_constraints = [self.get_constraint(sim) for sim in self._sim_transform_map]
        if all_constraints:
            self._constraint = create_constraint_set(all_constraints)
        else:
            self._constraint = Anywhere()
        return self._constraint

    _create_adjustment_alarm = socials.group.SocialGroup._create_adjustment_alarm

    def _consider_adjusting_sim(self, sim=None, initial=False):
        if not initial:
            for sim in self:
                sis = self._si_registry.get(sim)
                if sis is not None and any(not si.staging for si in sis):
                    return
                for _ in self.queued_mixers_gen(sim):
                    return
            if self.time_since_interaction().in_minutes() < self.inactivity_time_before_shutdown:
                return
            self.shutdown(FinishingType.NATURAL)
lock_instance_tunables(JigGroup, social_anchor_object=None, include_default_facing_constraint=False)
class MultiSimPostureJigGroup(JigGroup):

    @classmethod
    def get_jig_positioning_participant(cls, inst:'Interaction') -> 'GameObject or None':
        if not inst:
            return
        jp_participant = None
        jp_type = getattr(cls.jig, 'jig_positioning_type', None)
        jp_single_participant = getattr(cls.jig, 'jig_positioning_single_participant', None)
        if jp_single_participant is not None:
            jp_participant = inst.get_participant(jp_single_participant)
        return jp_participant

    @classmethod
    def _get_jig_transforms_gen(cls, initiating_sim:'Sim', target_sim:'Sim', picked_object:'GameObject'=None, participant_slot_overrides:'frozendict'=None, jig_positioning_participant:'GameObject'=None) -> 'List':
        if jig_positioning_participant is None:
            yield from super()._get_jig_transforms_gen(initiating_sim, target_sim, picked_object, participant_slot_overrides)
        else:
            slot_map = cls.participant_slot_map if participant_slot_overrides is None else participant_slot_overrides
            actor_slot_index = slot_map.get(ParticipantType.Actor, cls.DEFAULT_SLOT_INDEX_ACTOR)
            target_slot_index = slot_map.get(ParticipantType.TargetSim, cls.DEFAULT_SLOT_INDEX_TARGET)
            (fallback_routing_surface, fgl_kwargs) = cls._get_routing_surface_and_kwargs(initiating_sim, target_sim)
            yield from cls.jig.get_transforms_gen(initiating_sim, target_sim, actor_slot_index=actor_slot_index, target_slot_index=target_slot_index, fallback_routing_surface=fallback_routing_surface, jig_positioning_participant=jig_positioning_participant, fgl_kwargs=fgl_kwargs)
