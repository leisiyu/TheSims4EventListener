from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from protocolbuffers.FileSerialization_pb2 import ObjectDatafrom _math import Transformfrom _sims4_collections import frozendictfrom _weakrefset import WeakSetfrom native.animation import get_joint_transform_from_rigfrom protocolbuffers.FileSerialization_pb2 import LotCoordfrom sims4.callback_utils import CallableListConsumingExceptionsfrom sims4.collections import enumdictfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuple, TunableResourceKey, OptionalTunable, TunableReference, TunableSet, TunableMapping, TunableEnumEntry, TunableRangefrom sims4.tuning.tunable_base import FilterTag, GroupNamesfrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import constproperty, classpropertyfrom singletons import DEFAULT, UNSET, EMPTY_SETimport sims4.logimport sims4.protocol_buffer_utilsfrom animation.posture_manifest_constants import STAND_AT_NONE_POSTURE_STATE_SPECfrom autonomy.autonomy_modifier import TunableAutonomyModifierfrom bucks.bucks_enums import BucksTypefrom build_buy import remove_object_from_buildbuy_system, add_object_to_buildbuy_system, invalidate_object_location, get_object_catalog_name, get_object_catalog_description, is_location_outside, is_location_natural_groundfrom crafting.genre import Genrefrom distributor.shared_messages import IconInfoDatafrom event_testing import test_eventsfrom event_testing.tests import TunableTestSetfrom fire.flammability import TunableFlammableAreaVariantfrom interactions.aop import AffordanceObjectPairfrom interactions.constraint_variants import TunableConstraintVariantfrom interactions.constraints import Constraintfrom interactions.utils.routing import RouteTargetTypefrom objects import VisibilityStatefrom objects.client_object_mixin import ClientObjectMixinfrom objects.components import forward_to_components, ored_forward_to_components, forward_to_components_genfrom objects.components.types import FOOTPRINT_COMPONENTfrom objects.game_object_properties import GameObjectPropertyfrom objects.object_enums import ResetReason, ItemLocationfrom objects.persistence_groups import PersistenceGroupsfrom objects.script_object import ScriptObjectfrom postures import posture_graphfrom postures.posture import TunablePostureTypeListSnippetfrom postures.posture_graph import PostureGraphServicefrom postures.posture_specs import PostureOperationfrom reservation.reservation_mixin import ReservationMixinfrom routing import SurfaceType, SurfaceIdentifierfrom sims.household_utilities.utility_types import Utilitiesfrom sims.sim_info_types import Speciesfrom snippets import TunableAffordanceFilterSnippetfrom terrain import get_water_depth_at_locationimport alarmsimport autonomyimport build_buyimport clockimport distributor.fieldsimport objectsimport placementimport resetimport routingimport serviceslogger = sims4.log.Logger('Objects')
class GameObject(ClientObjectMixin, ReservationMixin, ScriptObject, reset.ResettableObjectMixin):
    INSTANCE_TUNABLES = {'_transient_tuning': Tunable(description='\n            If transient the object will always be destroyed and never put down.\n            ', tunable_type=bool, default=False, tuning_filter=FilterTag.EXPERT_MODE, display_name='Transient'), 'additional_interaction_constraints': TunableList(description="\n            A list of constraints that must be fulfilled in order to run the \n            linked affordances. This should only be used when the same \n            affordance uses different constraints based on the object.\n            \n            WARNING: this constraints will override the linked affordances' constraints.\n            ", tunable=TunableTuple(constraint=TunableConstraintVariant(description='\n                    A constraint that must be fulfilled in order to interact with this object.\n                    '), affordance_links=TunableAffordanceFilterSnippet()), tuning_filter=FilterTag.EXPERT_MODE), 'autonomy_modifiers': TunableList(description='\n            List of autonomy modifiers that will be applied to the tuned\n            participant type.  These can be used to tune object variations.\n            ', tunable=TunableAutonomyModifier(locked_args={'commodities_to_add': (), 'score_multipliers': frozendict(), 'provided_affordance_compatibility': None, 'super_affordance_suppression_mode': autonomy.autonomy_modifier_enums.SuperAffordanceSuppression.AUTONOMOUS_ONLY, 'suppress_self_affordances': False, 'only_scored_static_commodities': None, 'only_scored_stats': None, 'relationship_multipliers': None})), 'set_ico_as_carry_target': Tunable(description="\n            Whether or not the crafting process should set the carry target\n            to be the ICO.  Example Usage: Sheet Music has this set to false\n            because the sheet music is in the Sim's inventory and the Sim needs\n            to carry the guitar/violin.  This is a tunable on game object\n            because the ICO in the crafting process can be any game object.\n            ", tunable_type=bool, default=True), 'supported_posture_types': TunablePostureTypeListSnippet(description='\n            The postures supported by this part. If empty, assumes all postures \n            are supported.\n            '), 'allow_preroll_multiple_targets': Tunable(description='\n            When checked allows multiple sims to target this object during \n            preroll autonomy. If not checked then the default preroll behavior\n            will happen.\n            \n            The default setting is to only allow each target to be targeted\n            once during preroll. However it makes sense in certain cases where\n            multiple sims can use the same object at the same time to allow\n            multiple targets.\n            ', tunable_type=bool, default=False), 'add_parent_to_crafting_request': Tunable(description='\n        When checked parents of this objects are also considered as targets to crafting interactions\n        available during the whole crafting process. If not checked then only object itself will be considered\n        as target.\n        ', tunable_type=bool, default=True), 'icon_override': OptionalTunable(description='\n            If enabled, the icon that will be displayed in the UI for this object.\n            This does not override the build/buy icon, which can be overriden\n            through the catalog.\n            ', tunable=TunableResourceKey(tuning_group=GroupNames.UI, resource_types=sims4.resources.CompoundTypes.IMAGE)), 'flammable_area': TunableFlammableAreaVariant(description='\n            How the object defines its area of flammability. This is used \n            by the fire service to build the quadtree of flammable objects.\n            '), '_provided_mobile_posture': OptionalTunable(description="\n            If enabled, this object will add these postures to the posture\n            graph. We need to do this for mobile postures that have no body\n            target and we don't intend on them ever being included in searches\n            for getting from one place to another without this object somewhere\n            on the lot.\n            ", tunable=TunableTuple(affordances=TunableSet(description='\n                    The set of mobile posture providing interactions we want this\n                    object to provide.\n                    ', tunable=TunableReference(description='\n                        The posture providing interaction we want to add to the\n                        posture graph when this object is instanced.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True, class_restrictions='SuperInteraction'), minlength=1), placement_footprint_name_set=TunableSet(description="\n                    The set of object's placement footprint names.\n                    ", tunable=TunableStringHash32(description='\n                        Name of the placement footprint.\n                        '), minlength=1))), '_remap_child_parenting': Tunable(description='\n            DEPRECATED. Used only for banquette booth.\n            ', tunable_type=bool, default=False), 'recycling_data': TunableTuple(description='\n            Recycling information for this object.\n            ', recycling_values=TunableMapping(description='\n                Maps a buck type to the recycled value for this object.\n                ', key_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=BucksType.INVALID, pack_safe=True), key_name='Bucks Type', value_type=TunableRange(description='\n                    Object multiplier for this buck type.\n                    ', tunable_type=float, default=1.0, minimum=0.0), value_name='Value'), recycling_loot=TunableList(description='\n                Loot Actions that will be given when the object is recycled.\n                SingleActorAndObjectResolver will be used where actor is specified\n                by subject, and object is the object being recycled.\n                ', tunable=TunableReference(description='\n                    A loot action applied.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True))), 'tests_to_bypass_utility_requirement': TunableMapping(description='\n            A mapping of utility types to tunable test sets. \n            ', key_type=TunableEnumEntry(tunable_type=Utilities, default=Utilities.POWER), value_type=TunableTestSet(description='\n                A test set to run when the object is the target of a\n                recipe or interaction and the utility required for that recipe or \n                interaction is absent. If at least one test group passes, \n                then any interaction or recipe that requires the utility\n                will be allowed to run despite the absence of the utility. \n                \n                ORs of ANDs.\n                '))}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls._provided_mobile_posture is not None:
            for affordance in cls._provided_mobile_posture.affordances:
                if affordance.provided_posture_type is None:
                    logger.error("{} provides posture affordance {} but it doesn't provide a posture.", cls, affordance, owner='rmccord')
                elif not affordance.provided_posture_type.unconstrained:
                    logger.error('{} provides posture affordance {} but the provided posture is not unconstrained and therefore requires a body target.', cls, affordance, owner='rmccord')
                elif affordance in PostureGraphService.POSTURE_PROVIDING_AFFORDANCES:
                    logger.error('{} provides posture affordance {} but this is already provided by the posture graph in Posture Providing Affordances.', cls, affordance, owner='rmccord')

    def __init__(self, definition, **kwargs):
        super().__init__(definition, **kwargs)
        self._on_location_changed_callbacks = None
        self._transient = None
        self._created_constraints = None
        self._created_constraints_dirty = True
        self._household_owner_id = None
        self.new_in_inventory = True
        self.is_new_object = False
        self._provided_surface = UNSET
        zone = services.current_zone()
        account_id = build_buy.get_user_in_build_buy(zone.id)
        if account_id is not None:
            self.set_household_owner_id(zone.lot.zone_owner_household_id)
            self.set_post_bb_fixup_needed()
            zone.set_to_fixup_on_build_buy_exit(self)
        self._hidden_flags = 0
        self._local_tags = None
        self._persisted_tags = None
        self._is_routable_terrain = None
        self._is_surface = None
        self._build_buy_use_flags = 0
        self._scheduled_elements = None
        self._work_locks = WeakSet()
        self._on_hidden_or_shown_callbacks = None
        self._provided_mobile_posture_operations = None

    def add_work_lock(self, handle):
        self._work_locks.add(handle)

    def remove_work_lock(self, handle):
        self._work_locks.discard(handle)

    @property
    def has_work_locks(self):
        if self._work_locks:
            return True
        return False

    @property
    def is_fire_related_object(self):
        if self.is_sim:
            return False
        return self.fire_retardant or self.flammable

    @constproperty
    def is_valid_for_height_checks():
        return True

    def is_game_object(self, *args, **kwargs) -> 'bool':
        return True

    def has_tag(self, tag):
        if self._local_tags and tag in self._local_tags:
            return True
        if self._persisted_tags and tag in self._persisted_tags:
            return True
        return self.definition.has_build_buy_tag(tag)

    def has_any_tag(self, tags):
        return any(self.has_tag(tag) for tag in tags)

    def get_tags(self):
        tags = frozenset(self.definition.build_buy_tags)
        if self._local_tags:
            tags |= self._local_tags
        return tags

    def get_style_tags(self):
        return self.definition.get_style_tags()

    def get_dynamic_tags(self):
        if self._local_tags:
            return frozenset(self._local_tags)
        return frozenset()

    def append_tags(self, tag_set, persist=False):
        if self.manager is not None:
            self.manager.add_tags_and_object_to_cache(tag_set, self)
        if self._local_tags:
            self._local_tags = self._local_tags | tag_set
        else:
            self._local_tags = tag_set
        if persist:
            if self._persisted_tags:
                self._persisted_tags = self._persisted_tags | tag_set
            else:
                self._persisted_tags = tag_set
        current_inventory = self.get_inventory()
        if current_inventory is not None:
            current_inventory.push_inventory_item_tag_update_msg(self, tag_set)

    def remove_dynamic_tags(self, tag_set):
        if self.manager is not None:
            self.manager.remove_tags_on_object_from_cache(tag_set, self)
        if self._local_tags:
            self._local_tags = self._local_tags - tag_set
        if self._persisted_tags:
            self._persisted_tags = self._persisted_tags - tag_set
        current_inventory = self.get_inventory()
        if current_inventory is not None:
            current_inventory.push_inventory_item_tag_update_msg(self, tag_set)

    def get_icon_info_data(self):
        return IconInfoData(obj_instance=self, obj_def_id=self.definition.id, obj_geo_hash=self.geometry_state, obj_material_hash=self.material_hash, obj_name=LocalizationHelperTuning.get_object_name(self), multicolor=self.multicolor)

    @property
    def catalog_name(self):
        return get_object_catalog_name(self.definition.id)

    @property
    def catalog_description(self):
        return get_object_catalog_description(self.definition.id)

    def is_routing_surface_overlapped_at_position(self, position):
        routing_surface = self.provided_routing_surface
        if routing_surface is not None:
            (_, object_id) = services.terrain_service.terrain_object().get_routing_surface_height_and_surface_object_at(position.x, position.z, routing_surface)
            if object_id == self.id:
                return False
        return True

    @property
    def provided_routing_surface(self):
        if self._provided_surface is UNSET:
            self._provided_surface = None
            if placement.has_object_surface_footprint(self.get_footprint()):
                self._provided_surface = routing.SurfaceIdentifier(services.current_zone_id(), self.routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_OBJECT)
        return self._provided_surface

    @property
    def provided_mobile_posture_operations(self):
        if self._provided_mobile_posture_operations is None:
            self._provided_mobile_posture_operations = set()
            for affordance in self.provided_mobile_posture_affordances:
                posture_type = affordance.provided_posture_type
                if posture_type is not None:
                    aop = AffordanceObjectPair(affordance, None, affordance, None, force_inertial=True)
                    sim_aops = enumdict(Species, {affordance.provided_posture_type_species: aop})
                    self._provided_mobile_posture_operations.add(PostureOperation.BodyTransition(posture_type, sim_aops))
        return self._provided_mobile_posture_operations

    def get_icon_override(self):
        for icon_override in self._icon_override_gen():
            if icon_override is not None:
                return icon_override

    @forward_to_components_gen
    def _icon_override_gen(self):
        if self.icon_override is not None:
            yield self.icon_override

    @forward_to_components
    def populate_localization_token(self, token):
        self.definition.populate_localization_token(token)

    def is_hidden(self, allow_hidden_flags=0):
        if int(self._hidden_flags) & ~int(allow_hidden_flags):
            return True
        return False

    def has_hidden_flags(self, hidden_flags):
        if int(self._hidden_flags) & int(hidden_flags):
            return True
        return False

    def hide(self, hidden_reasons_to_add):
        self._hidden_flags = self._hidden_flags | hidden_reasons_to_add
        if self._on_hidden_or_shown_callbacks is not None:
            self._on_hidden_or_shown_callbacks(self, hidden_reasons_to_add, added=True)

    def show(self, hidden_reasons_to_remove):
        self._hidden_flags = self._hidden_flags & ~hidden_reasons_to_remove
        if self._on_hidden_or_shown_callbacks is not None:
            self._on_hidden_or_shown_callbacks(self, hidden_reasons_to_remove, added=False)

    @property
    def transient(self):
        if self._transient is not None:
            return self._transient
        return self._transient_tuning

    @transient.setter
    def transient(self, value):
        self._transient = value

    @distributor.fields.Field(op=distributor.ops.SetBuildBuyUseFlags, default=0)
    def build_buy_use_flags(self):
        return self._build_buy_use_flags

    @build_buy_use_flags.setter
    def build_buy_use_flags(self, value):
        self._build_buy_use_flags = value

    @distributor.fields.Field(op=distributor.ops.SetOwnerId, default=None)
    def household_owner_id(self):
        return self._household_owner_id

    _resend_household_owner_id = household_owner_id.get_resend()

    def get_edges(self):
        (lower_bound, upper_bound) = self.get_fooptrint_polygon_bounds()
        if lower_bound is None or upper_bound is None:
            return ()
        y = self.position.y
        transform = self.transform
        p0 = transform.transform_point(sims4.math.Vector3(lower_bound.x, y, lower_bound.z))
        p1 = transform.transform_point(sims4.math.Vector3(lower_bound.x, y, upper_bound.z))
        p2 = transform.transform_point(sims4.math.Vector3(upper_bound.x, y, upper_bound.z))
        p3 = transform.transform_point(sims4.math.Vector3(upper_bound.x, y, lower_bound.z))
        return ((p0, p1), (p1, p2), (p2, p3), (p3, p0))

    def get_edge_constraint(self, constraint_width=1.0, inward_dir=False, return_constraint_list=False, los_reference_point=DEFAULT, sim=None):
        edges = self.get_edges()
        polygons = []
        for (start, stop) in edges:
            along = sims4.math.vector_normalize(stop - start)
            inward = sims4.math.vector3_rotate_axis_angle(along, sims4.math.PI/2, sims4.math.Vector3.Y_AXIS())
            if inward_dir:
                polygon = sims4.geometry.Polygon([start, start + constraint_width*inward, stop + constraint_width*inward, stop])
            else:
                polygon = sims4.geometry.Polygon([start, stop, stop - constraint_width*inward, start - constraint_width*inward])
            polygons.append(polygon)
        routing_surface = self.routing_surface
        if return_constraint_list:
            constraint_list = []
            for polygon in polygons:
                restricted_polygon = sims4.geometry.RestrictedPolygon(polygon, ())
                constraint = Constraint(routing_surface=routing_surface, geometry=restricted_polygon, los_reference_point=los_reference_point, posture_state_spec=STAND_AT_NONE_POSTURE_STATE_SPEC)
                constraint_list.append(constraint)
            return constraint_list
        else:
            geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(polygons), ())
            constraint = Constraint(routing_surface=routing_surface, geometry=geometry, posture_state_spec=STAND_AT_NONE_POSTURE_STATE_SPEC)
            return constraint

    def get_created_constraint(self, tuned_constraint):
        if not self.additional_interaction_constraints:
            return
        if not self._created_constraints:
            self._created_constraints = {}
        if self._created_constraints_dirty:
            self._created_constraints.clear()
            for tuned_additional_constraint in self.additional_interaction_constraints:
                constraint = tuned_additional_constraint.constraint
                if constraint is not None:
                    self._created_constraints[constraint] = constraint.create_constraint(None, self)
            self._created_constraints_dirty = False
        return self._created_constraints.get(tuned_constraint)

    @classmethod
    def _get_tuning_suggestions(cls, print_suggestion):
        if cls.additional_interaction_constraints:
            print_suggestion("This Constraint will override linked affordances' constraints.Make sure you compare it with the constraints used on theseaffordances and test if they work as expected.")

    @forward_to_components
    def register_rebate_tests(self, test_set):
        pass

    @forward_to_components
    def validate_definition(self):
        pass

    def _should_invalidate_location(self):
        parent = self.parent
        if parent is None:
            return True
        return parent._should_invalidate_location()

    def _notify_buildbuy_of_location_change(self, old_location):
        if self.persistence_group == PersistenceGroups.OBJECT and self._should_invalidate_location():
            invalidate_object_location(self.id)

    def set_build_buy_lockout_state(self, lockout_state, lockout_timer=None):
        if self._build_buy_lockout_alarm_handler is not None:
            alarms.cancel_alarm(self._build_buy_lockout_alarm_handler)
            self._build_buy_lockout_alarm_handler = None
        elif self._build_buy_lockout and lockout_state:
            return
        if lockout_timer is not None:
            time_span_real_time = clock.interval_in_real_seconds(lockout_timer)
            self._build_buy_lockout_alarm_handler = alarms.add_alarm_real_time(self, time_span_real_time, lambda *_: self.set_build_buy_lockout_state(False))
        if lockout_state and lockout_state and not self.build_buy_lockout:
            self.reset(ResetReason.RESET_EXPECTED)
        self._build_buy_lockout = lockout_state
        self.resend_interactable()
        self.resend_tint()

    def on_location_changed(self, old_location):
        super().on_location_changed(old_location)
        self.mark_get_locations_for_posture_needs_update()
        self.clear_check_line_of_sight_cache()
        self._provided_surface = UNSET
        if self.id:
            self._update_persistence_group()
            self._notify_buildbuy_of_location_change(old_location)
            self.manager.on_location_changed(self)
            if self._on_location_changed_callbacks is not None:
                self._on_location_changed_callbacks(self, old_location, self.location)
            self._created_constraints_dirty = True

    def set_object_def_state_index(self, state_index):
        if type(self) != self.get_class_for_obj_state(state_index):
            logger.error("Attempting to change object {}'s state to one that would require a different runtime class.  This is not supported.", self, owner='tastle')
        self.apply_definition(self.definition, state_index)
        self.model = self._model
        self.rig = self._rig
        self.resend_state_index()
        self.resend_slot()

    def register_on_location_changed(self, callback):
        if self._on_location_changed_callbacks is None:
            self._on_location_changed_callbacks = CallableListConsumingExceptions()
        self._on_location_changed_callbacks.append(callback)

    def unregister_on_location_changed(self, callback):
        if self._on_location_changed_callbacks is None:
            logger.error('Unregistering location changed callback on {} when there are none registered.', self)
            return
        if callback not in self._on_location_changed_callbacks:
            logger.error('Unregistering location changed callback on {} that is not registered. Callback: {}.', self, callback)
            return
        self._on_location_changed_callbacks.remove(callback)
        if not self._on_location_changed_callbacks:
            self._on_location_changed_callbacks = None

    def is_on_location_changed_callback_registered(self, callback):
        if self._on_location_changed_callbacks is None:
            return False
        return callback in self._on_location_changed_callbacks

    def register_on_hidden_or_shown(self, callback):
        if self._on_hidden_or_shown_callbacks is None:
            self._on_hidden_or_shown_callbacks = CallableListConsumingExceptions()
        self._on_hidden_or_shown_callbacks.append(callback)

    def unregister_on_hidden_or_shown(self, callback):
        if self._on_hidden_or_shown_callbacks is None:
            logger.error('Unregistering hidden or shown callback on {} when there are none registered.', self)
            return
        if callback not in self._on_hidden_or_shown_callbacks:
            logger.error('Unregistering hidden or shown callback on {} that is not registered. Callback: {}.', self, callback)
            return
        self._on_hidden_or_shown_callbacks.remove(callback)
        if not self._on_hidden_or_shown_callbacks:
            self._on_hidden_or_shown_callbacks = None

    def is_on_hidden_or_shown_callback_registered(self, callback):
        if self._on_hidden_or_shown_callbacks is None:
            return False
        return callback in self._on_hidden_or_shown_callbacks

    def is_on_active_lot(self, tolerance=0):
        return self.persistence_group == PersistenceGroups.OBJECT

    @property
    def is_in_navmesh(self):
        if self._routing_context is not None and self._routing_context.object_footprint_id is not None:
            return True
        else:
            return False

    @property
    def may_move(self):
        return self.vehicle_component is not None or self.routing_component is not None and self.routing_component.object_routing_component is not None

    def get_surface_override_for_posture(self, source_posture_name):
        pass

    @classproperty
    def provided_mobile_posture_affordances(cls):
        if cls._provided_mobile_posture:
            return cls._provided_mobile_posture.affordances
        return EMPTY_SET

    @classproperty
    def placement_footprint_hash_set(cls):
        if cls._provided_mobile_posture:
            return frozenset(cls._provided_mobile_posture.placement_footprint_name_set)
        return EMPTY_SET

    def get_joint_transform_for_joint(self, joint_name):
        transform = get_joint_transform_from_rig(self.rig, joint_name)
        transform = Transform.concatenate(transform, self.transform)
        return transform

    @property
    def object_radius(self):
        if self._routing_context is None:
            return routing.get_default_agent_radius()
        return self._routing_context.object_radius

    @property
    def persistence_group(self):
        return self._persistence_group

    @persistence_group.setter
    def persistence_group(self, value):
        self._persistence_group = value

    def _update_persistence_group(self):
        if self.is_in_inventory():
            self.persistence_group = objects.persistence_groups.PersistenceGroups.OBJECT
            return
        if self.persistence_group == objects.persistence_groups.PersistenceGroups.OBJECT:
            if not services.current_zone().lot.is_position_on_lot(self.position, 0):
                remove_object_from_buildbuy_system(self.id)
                self.persistence_group = objects.persistence_groups.PersistenceGroups.IN_OPEN_STREET
        elif self.persistence_group == objects.persistence_groups.PersistenceGroups.IN_OPEN_STREET and services.current_zone().lot.is_position_on_lot(self.position, 0):
            self.persistence_group = objects.persistence_groups.PersistenceGroups.OBJECT
            add_object_to_buildbuy_system(self.id)

    def _fixup_pool_surface(self):
        if (self.item_location == ItemLocation.FROM_WORLD_FILE or self.item_location == ItemLocation.FROM_CONDITIONAL_LAYER) and (self.routing_surface.type != SurfaceType.SURFACETYPE_POOL and build_buy.PlacementFlags.REQUIRES_WATER_SURFACE & build_buy.get_object_placement_flags(self.definition.id)) and get_water_depth_at_location(self.location) > 0:
            routing_surface = self.routing_surface
            self.set_location(self.location.clone(routing_surface=SurfaceIdentifier(routing_surface.primary_id, routing_surface.secondary_id, SurfaceType.SURFACETYPE_POOL)))

    def _add_to_world(self):
        if self.persistence_group == PersistenceGroups.OBJECT:
            add_object_to_buildbuy_system(self.id)

    def _remove_from_world(self):
        if self.persistence_group == PersistenceGroups.OBJECT:
            remove_object_from_buildbuy_system(self.id)

    @property
    def remap_child_parenting(self):
        return self._remap_child_parenting

    def on_add(self):
        super().on_add()
        self._add_to_world()
        self.register_on_location_changed(self._location_changed)
        if self.is_fire_related_object:
            fire_service = services.get_fire_service()
            self.register_on_location_changed(fire_service.flammable_object_location_changed)
        posture_graph_service = services.posture_graph_service()
        if posture_graph.is_object_mobile_posture_compatible(self):
            self.register_on_location_changed(posture_graph_service.mobile_posture_object_location_changed)
        if self.provided_mobile_posture_affordances:
            posture_graph_service.add_mobile_posture_provider(self)
        services.call_to_action_service().object_created(self)
        self.try_mark_as_new_object()

    def on_remove(self):
        zone = services.current_zone()
        if zone is not None and not zone.is_zone_shutting_down:
            services.get_event_manager().process_event(test_events.TestEvent.ObjectDestroyed, obj=self)
        super().on_remove()
        if not zone.is_zone_shutting_down:
            self._remove_from_world()
            self.unregister_on_location_changed(self._location_changed)
            if self.is_fire_related_object:
                fire_service = services.get_fire_service()
                if fire_service is not None:
                    self.unregister_on_location_changed(fire_service.flammable_object_location_changed)
            posture_graph_service = services.posture_graph_service()
            if self.provided_mobile_posture_affordances:
                posture_graph_service.remove_mobile_posture_provider(self)
            if posture_graph.is_object_mobile_posture_compatible(self):
                posture_graph_service.remove_object_from_mobile_posture_quadtree(self)
                self.unregister_on_location_changed(posture_graph_service.mobile_posture_object_location_changed)
        else:
            self._on_location_changed_callbacks = None
        services.call_to_action_service().object_removed(self)

    def on_added_to_inventory(self):
        super().on_added_to_inventory()
        self._remove_from_world()
        self.visibility = VisibilityState(False)

    def on_removed_from_inventory(self):
        super().on_removed_from_inventory()
        self._add_to_world()
        self.visibility = VisibilityState(True)

    @forward_to_components
    def on_buildbuy_exit(self):
        self._update_location_callbacks(update_surface=True)

    def _update_location_callbacks(self, update_surface=False):
        self._inside_status_change()
        self._natural_ground_status_change()
        if update_surface:
            self._surface_type_changed()

    @staticmethod
    def _location_changed(obj, old_loc, new_loc):
        if obj.zone_id:
            obj._update_location_callbacks(update_surface=old_loc.routing_surface != new_loc.routing_surface)
        obj._fixup_pool_surface()

    def _inside_status_change(self, *_, **__):
        if self.is_outside:
            self._set_placed_outside()
        else:
            self._set_placed_inside()

    def _natural_ground_status_change(self, *_, **__):
        if self.routing_surface is not None and self.routing_surface.type == SurfaceType.SURFACETYPE_POOL:
            return
        if self.is_on_natural_ground():
            self._set_placed_on_natural_ground()
        else:
            self._set_placed_off_natural_ground()

    @ored_forward_to_components
    def on_hovertip_requested(self):
        return False

    @ored_forward_to_components
    def has_ui_metadata_handles(self) -> 'bool':
        return False

    @property
    def is_outside(self):
        routing_surface = self.routing_surface
        level = 0 if routing_surface is None else routing_surface.secondary_id
        try:
            return is_location_outside(self.position, level)
        except RuntimeError:
            pass

    @property
    def is_inside_building(self):
        try:
            return routing.is_location_in_building(self.location)
        except RuntimeError:
            pass

    def is_on_natural_ground(self):
        if self.parent is not None:
            return False
        routing_surface = self.routing_surface
        level = 0 if routing_surface is None else routing_surface.secondary_id
        try:
            return is_location_natural_ground(self.position, level)
        except RuntimeError:
            pass

    def try_mark_as_new_object(self):
        if not (self.should_mark_as_new and services.current_zone().is_in_build_buy):
            return
        self.add_dynamic_component(objects.components.types.NEW_OBJECT_COMPONENT)

    def on_child_added(self, child, location):
        super().on_child_added(child, location)
        self.get_raycast_root().on_leaf_child_changed()

    def on_child_removed(self, child, new_location:'routing.Location', new_parent=None):
        super().on_child_removed(child, new_location, new_parent=new_parent)
        self.get_raycast_root().on_leaf_child_changed()

    def on_leaf_child_changed(self):
        if self._raycast_context is not None:
            self._create_raycast_context()

    @property
    def forward_direction_for_picking(self):
        return sims4.math.Vector3.Z_AXIS()

    @property
    def route_target(self):
        parts = self.parts
        if parts is None:
            return (RouteTargetType.OBJECT, self)
        else:
            return (RouteTargetType.PARTS, parts)

    @property
    def should_mark_as_new(self):
        return True

    def is_routable_terrain(self, include_parts=False, ignore_deco_slots=False):
        if self._is_routable_terrain is None:
            self._is_routable_terrain = {}
        key = (include_parts, ignore_deco_slots)
        is_routable_terrain = self._is_routable_terrain.get(key)
        if is_routable_terrain is not None:
            return is_routable_terrain

        def is_valid_terrain_slot(slot_type):
            if slot_type.implies_owner_object_is_routable_terrain:
                return True

        for runtime_slot in self.get_runtime_slots_gen():
            if not any(is_valid_terrain_slot(slot_type) for slot_type in runtime_slot.slot_types):
                pass
            else:
                self._is_routable_terrain[key] = True
                return True

    def is_surface(self, include_parts=False, ignore_deco_slots=None):
        if self._is_surface is None:
            self._is_surface = {}
        if ignore_deco_slots is None:
            ignore_deco_slots = self.ignore_deco_slots_for_surfaces
        key = (include_parts, ignore_deco_slots)
        is_surface = self._is_surface.get(key)
        if is_surface is not None:
            return is_surface
        inventory_component = self.inventory_component
        if inventory_component is not None and inventory_component.has_get_put:
            self._is_surface[key] = True
            return True

        def is_valid_surface_slot(slot_type):
            if ignore_deco_slots and slot_type.is_deco_slot or slot_type.implies_owner_object_is_surface:
                return True
            return False

        for runtime_slot in self.get_runtime_slots_gen():
            if include_parts or runtime_slot.owner is not self:
                pass
            elif not any(is_valid_surface_slot(slot_type) for slot_type in runtime_slot.slot_types):
                pass
            elif not runtime_slot.owner.is_same_object_or_part(self):
                pass
            else:
                self._is_surface[key] = True
                return True
        self._is_surface[key] = False
        return False

    def get_save_lot_coords_and_level(self):
        lot_coord_msg = LotCoord()
        parent = self.parent
        if parent is not None and parent.is_sim:
            parent.force_update_routing_location()
            starting_position = parent.position + parent.forward
            starting_location = placement.create_starting_location(position=starting_position, orientation=parent.orientation, routing_surface=self.location.world_routing_surface)
            fgl_context = placement.create_fgl_context_for_object(starting_location, self)
            (trans, orient, _) = fgl_context.find_good_location()
            if trans is None:
                logger.warn('Unable to find good location to save object{}, which is parented to sim {} and cannot go into an inventory. Defaulting to location of sim.', self, parent)
                transform = parent.transform
            else:
                transform = sims4.math.Transform(trans, orient)
            if self.persistence_group == PersistenceGroups.OBJECT:
                transform = services.current_zone().lot.convert_to_lot_coordinates(transform)
        elif self.persistence_group == PersistenceGroups.OBJECT:
            transform = services.current_zone().lot.convert_to_lot_coordinates(self.transform)
        else:
            transform = self.transform
        lot_coord_msg.x = transform.translation.x
        lot_coord_msg.y = transform.translation.y
        lot_coord_msg.z = transform.translation.z
        lot_coord_msg.rot_x = transform.orientation.x
        lot_coord_msg.rot_y = transform.orientation.y
        lot_coord_msg.rot_z = transform.orientation.z
        lot_coord_msg.rot_w = transform.orientation.w
        if self.location.world_routing_surface is not None:
            level = self.location.level
        else:
            level = 0
        return (lot_coord_msg, level)

    def save_object(self, object_list, *args, **kwargs):
        save_data = super().save_object(object_list, *args, **kwargs)
        if save_data is None:
            return
        save_data.slot_id = self.bone_name_hash
        (save_data.position, save_data.level) = self.get_save_lot_coords_and_level()
        inventory_plex_id = self.get_inventory_plex_id()
        if inventory_plex_id is not None:
            save_data.inventory_plex_id = inventory_plex_id
        save_data.scale = self.scale
        save_data.state_index = self.state_index
        if hasattr(save_data, 'buildbuy_use_flags'):
            save_data.buildbuy_use_flags = self._build_buy_use_flags
        save_data.cost = self.base_value
        save_data.ui_metadata = self.ui_metadata._value
        self.post_tooltip_save_data_stored()
        save_data.is_new = self.new_in_inventory
        save_data.is_new_object = self.is_new_object
        self.populate_icon_canvas_texture_info(save_data)
        if self._household_owner_id is not None:
            save_data.owner_id = self._household_owner_id
        save_data.needs_depreciation = self._needs_depreciation
        save_data.needs_post_bb_fixup = self._needs_post_bb_fixup
        if self._persisted_tags:
            save_data.persisted_tags.extend(self._persisted_tags)
        if self._multicolor is not None:
            for color in self._multicolor:
                color = getattr(color, 'value', color)
                multicolor_info_msg = save_data.multicolor.add()
                (multicolor_info_msg.x, multicolor_info_msg.y, multicolor_info_msg.z, _) = sims4.color.to_rgba(color)
        save_data.created_from_lot_template = False
        save_data.stack_sort_order = self.get_stack_sort_order()
        if self.material_state:
            save_data.material_state = self.material_state.state_name_hash
        if self.geometry_state:
            save_data.geometry_state = self.geometry_state
        if self.model:
            model_key = sims4.resources.get_protobuff_for_key(self.model)
            save_data.model_override_resource_key = model_key
        parent = self.get_parent()
        if not parent.is_sim:
            save_data.parent_id = parent.id
        if not (parent is not None and parent is None or parent.is_sim):
            save_data.object_parent_type = self._parent_type
            save_data.encoded_parent_location = self._parent_location
        inventory = self.inventory_component
        if not inventory.is_shared_inventory:
            save_data.unique_inventory = inventory.save_items()
        return save_data

    def load_object(self, object_data:'ObjectData', **kwargs) -> 'None':
        if object_data.HasField('owner_id'):
            self._household_owner_id = object_data.owner_id
        if self._household_owner_id is None and self.is_downloaded:
            self.base_value = self.catalog_value
        else:
            self.base_value = object_data.cost
        self.new_in_inventory = object_data.is_new
        super().load_object(object_data, **kwargs)
        if object_data.HasField('texture_id') and self.canvas_component is not None:
            self.canvas_component.set_painting_texture_id(object_data.texture_id)
        if object_data.HasField('needs_depreciation'):
            self._needs_depreciation = object_data.needs_depreciation
        if object_data.HasField('needs_post_bb_fixup'):
            self._needs_post_bb_fixup = object_data.needs_post_bb_fixup
        else:
            self._needs_post_bb_fixup = self._needs_depreciation
        inventory = self.inventory_component
        if inventory is not None:
            inventory.load_items(object_data.unique_inventory)
        if sims4.protocol_buffer_utils.has_field(object_data, 'buildbuy_use_flags'):
            self._build_buy_use_flags = object_data.buildbuy_use_flags
        self.is_new_object = object_data.is_new_object
        if self.is_new_object:
            self.add_dynamic_component(objects.components.types.NEW_OBJECT_COMPONENT)
        if object_data.persisted_tags is not None:
            self.append_tags(set(object_data.persisted_tags))

    def finalize(self, **kwargs):
        super().finalize(**kwargs)
        self.try_post_bb_fixup(**kwargs)
        if self.is_fire_related_object:
            fire_service = services.get_fire_service()
            if fire_service is not None:
                fire_service.flammable_object_location_changed(self)
        if posture_graph.is_object_mobile_posture_compatible(self):
            posture_graph_service = services.current_zone().posture_graph_service
            posture_graph_service.mobile_posture_object_location_changed(self)

    def set_household_owner_id(self, new_owner_id):
        self._household_owner_id = new_owner_id
        self._resend_household_owner_id()
        if self.live_drag_component is not None:
            self.live_drag_component.resolve_live_drag_household_permission()

    def get_household_owner_id(self):
        return self._household_owner_id

    def get_object_property(self, property_type):
        if property_type == GameObjectProperty.CATALOG_PRICE:
            return self.definition.price
        if property_type == GameObjectProperty.MODIFIED_PRICE:
            if self.crafting_component is not None:
                return self.crafting_component.get_simoleon_value()
            return self.current_value
        if property_type == GameObjectProperty.RARITY:
            return self.get_object_rarity_string()
        if property_type == GameObjectProperty.GENRE:
            return Genre.get_genre_localized_string(self)
        if property_type == GameObjectProperty.RECIPE_NAME or property_type == GameObjectProperty.RECIPE_DESCRIPTION:
            return self.get_craftable_property(self, property_type)
        if property_type == GameObjectProperty.OBJ_TYPE_REL_ID:
            return services.relationship_service().get_object_type_rel_id(self)
        logger.error('Requested property_type {} not found on game_object'.format(property_type), owner='camilogarcia')

    def update_ownership(self, sim, make_sim_owner=True, make_sim_inventory_owner=None):
        if make_sim_inventory_owner is None:
            make_sim_inventory_owner = make_sim_owner
        household_id = sim.household_id
        if self._household_owner_id != household_id:
            if self.ownable_component is not None:
                self.ownable_component.update_sim_ownership(None)
            self.set_household_owner_id(household_id)
        if make_sim_owner and self.ownable_component is not None:
            self.ownable_component.update_sim_ownership(sim.sim_id)
        if self.manager is not None:
            inventory_component = self.inventory_component
            if not inventory_component.is_shared_inventory:
                for inv_obj in inventory_component:
                    inv_obj.update_ownership(sim, make_sim_owner=make_sim_inventory_owner)

    @property
    def flammable(self):
        fire_service = services.get_fire_service()
        if fire_service is not None:
            return fire_service.is_object_flammable(self)
        return False

    def object_bounds_for_flammable_object(self, fire_retardant_bonus):
        return self.flammable_area.get_bounds_for_flammable_object(self, fire_retardant_bonus)

    @property
    def is_set_as_head(self):
        parent = self.parent
        if parent is None:
            return False
        if not parent.is_sim:
            return False
        if parent.current_object_set_as_head is None:
            return False
        else:
            parent_head = parent.current_object_set_as_head()
            if not self.is_same_object_or_part(parent_head):
                return False
        return True

    @classmethod
    def register_tuned_animation(cls, *_, **__):
        pass

    @classmethod
    def add_auto_constraint(cls, *_, **__):
        pass

    def may_reserve(self, sim, *args, **kwargs):
        for child in self.children:
            child_targets = child.parts if child.parts else (child,)
            for child_target in child_targets:
                if child_target.is_sim:
                    pass
                else:
                    reserve_result = child_target.may_reserve(sim, *args, **kwargs)
                    if not reserve_result:
                        return reserve_result
        return super().may_reserve(sim, *args, **kwargs)

    def make_transient(self):
        self.transient = True
        self._destroy_if_not_in_use()

    def _destroy_if_not_in_use(self):
        if self.is_part and self.part_owner is not None:
            self.part_owner._destroy_if_not_in_use()
            return
        if self.self_or_part_in_use:
            return
        if not self.transient:
            return
        self.schedule_destroy_asap(source=self, cause='Destroying unused transient object.')

    def remove_reservation_handler(self, *args, **kwargs):
        super().remove_reservation_handler(*args, **kwargs)
        self._destroy_if_not_in_use()

    def schedule_element(self, timeline, element):
        resettable_element = reset.ResettableElement(element, self)
        resettable_element.on_scheduled(timeline)
        timeline.schedule(resettable_element)
        return resettable_element

    def register_reset_element(self, element):
        if self._scheduled_elements is None:
            self._scheduled_elements = set()
        self._scheduled_elements.add(element)

    def unregister_reset_element(self, element):
        if self._scheduled_elements is not None:
            self._scheduled_elements.discard(element)
            if not self._scheduled_elements:
                self._scheduled_elements = None

    def on_reset_element_hard_stop(self):
        self.reset(reset_reason=ResetReason.RESET_EXPECTED)

    def on_reset_get_elements_to_hard_stop(self, reset_reason):
        elements_to_reset = super().on_reset_get_elements_to_hard_stop(reset_reason)
        if self._scheduled_elements is not None:
            scheduled_elements = list(self._scheduled_elements)
            self._scheduled_elements = None
            for element in scheduled_elements:
                elements_to_reset.append(element)
                element.unregister()
        return elements_to_reset

    def get_gsi_portal_items(self, key_name, value_name):
        household_owner_id = self.household_owner_id
        household_owner = services.household_manager().get(household_owner_id)
        name = household_owner.name if household_owner is not None else 'Not Owned'
        return [{value_name: name, key_name: 'Household Owner'}]

    def portal_added_callback(self, portal):
        portal.lock_object(self)

    @property
    def allow_different_multi_sim_idles(self):
        return True
