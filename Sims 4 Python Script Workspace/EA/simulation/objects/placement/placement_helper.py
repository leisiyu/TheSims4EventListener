from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from objects.game_object import GameObject
    from typing import *from event_testing.resolver import SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeLotLevel, ParticipantTypeSinglefrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import ANYWHEREfrom interactions.utils.parent_object import parent_objectfrom native.animation import get_joint_transform_from_rigfrom objects import ALL_HIDDEN_REASONS, HiddenReasonFlagfrom objects.components.utils.inventory_helpers import TunableInventoryOwner, transfer_object_to_lot_or_object_inventoryfrom placement import FGLSearchFlag, create_starting_location, create_fgl_context_for_object_off_lot, create_fgl_context_for_object, PositionIncrementInfo, ScoringFunctionPolygon, FGLSearchFlagsDeprecated, RaytestInfo, WaterDepthInfofrom routing import SurfaceType, SurfaceIdentifierfrom sims4 import randomfrom sims4.geometry import Polygonfrom sims4.random import pop_weightedfrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableVariant, TunableTuple, OptionalTunable, TunableInterval, TunableAngle, Tunable, TunableReference, TunableList, TunableFactory, TunableEnumSet, TunableMapping, TunableEnumFlagsfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable_hash import TunableStringHash32from tag import TunableTagsfrom tunable_multiplier import TunableMultiplierfrom world.lot_enums import LotPositionStrategyfrom world.lot_geom_utils import get_random_points_on_floorfrom world.pool_size_test import PoolSizeTestfrom world.terrain_enums import TerrainTagimport build_buyimport servicesimport sims4.mathimport random as system_randomlogger = sims4.log.Logger('PlacementHelper', default_owner='miking')
class _ObjectsFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):

    @TunableFactory.factory_option
    def participant_type_default(participant_type_default=ParticipantType.Actor):
        return {'participant': TunableEnumEntry(description='\n                The participant that determines the object to be used for the\n                specified placement strategy.\n                ', tunable_type=ParticipantType, default=participant_type_default)}

    def get_objects_gen(self, resolver):
        yield resolver.get_participant(self.participant)

class _ObjectsFromTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tag_test_sets': TunableList(TunableTuple(description='\n            For each tag set, in order, gather all objects matching any tag in the set. \n            If placement fails, consider another object within the same tag set,\n            then consider objects for the next tag set.\n            If tests are set, for each tag set, gather all objects that match any tag \n            in the set and pass the tests set for the tag set. If placement fails, \n            consider another object that has also passed the tests, then consider objects\n            for the next tag set that also pass the tests set for that tag set.\n            If should_should is True, gather all objects matching any tag, then \n            pick a random one, if placement fails, pick another random one.\n            ', tags=TunableTags(description='\n                For each tag, in order, gather objects that match the tag. \n                If the placement fails, consider another object, then consider\n                objects for the next tag.\n                If should_shuffle is True, gather all objects matching any tag, then\n                pick a random one, if placement fails, pick another random one.\n                '), tests=TunableTestSet(description='\n                Tests for matched objects to pass to be considered to try for placement\n                '), shuffle_tags_in_test_set=Tunable(description='\n                If False, go through each tag within the tag set, in order, try placement\n                for each matched object (in the order of the tag indices in object manager).\n                If True, gather all objects matching any tag within the tag set,\n                then pick a random one, if placement fails, pick another random one.\n                ', tunable_type=bool, default=False))), 'shuffle_tag_test_sets': Tunable(description='\n            If False, go through each tag set, in order, and try placement for each \n            matched object (in the order of the tag set indices in object manager). \n            If True, gather all objects matching any tag in all the tag sets, \n            then pick a random one, if placement fails, pick another random one.\n            This supersedes the shuffle_tags_in_test_set.\n            ', tunable_type=bool, default=False)}

    def get_objects_gen(self, resolver):
        object_manager = services.object_manager()
        if self.shuffle_tag_test_sets:
            objs = []
            for tag_test_set in self.tag_test_sets:
                objects_with_tags = list(object_manager.get_objects_matching_tags(tag_test_set.tags, match_any=True))
                if tag_test_set.tests:
                    objs.extend(self._get_tested_tagged_objects(tag_test_set, objects_with_tags))
                else:
                    objs.extend(objects_with_tags)
            system_random.shuffle(objs)
            yield from objs
        else:
            for tag_test_set in self.tag_test_sets:
                if tag_test_set.shuffle_tags_in_test_set:
                    objects_with_tags = list(object_manager.get_objects_matching_tags(tag_test_set.tags, match_any=True))
                    if tag_test_set.tests:
                        yield from self._get_tested_tagged_objects(tag_test_set, objects_with_tags, should_shuffle=True)
                    else:
                        system_random.shuffle(objects_with_tags)
                        yield from objects_with_tags
                else:
                    for tag in tag_test_set.tags:
                        objects_with_tags = list(object_manager.get_objects_with_tag_gen(tag))
                        if tag_test_set.tests:
                            yield from self._get_tested_tagged_objects(tag_test_set, objects_with_tags)
                        else:
                            yield from objects_with_tags

    def _get_tested_tagged_objects(self, tag_test_set, objs, should_shuffle=False):
        tested_objects = []
        for obj in objs:
            resolver = SingleObjectResolver(obj)
            if tag_test_set.tests.run_tests(resolver):
                tested_objects.append(obj)
        if should_shuffle:
            system_random.shuffle(tested_objects)
        return tested_objects

class _LocationFromLot(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'lot_location_strategy': TunableEnumEntry(description='\n            Strategy for how we will determine a location on the lot.\n            Default: Tries to retrieve the position of the front door, otherwise\n            uses an arbitrary corner (will always be the same corner)\n            \n            Random: Retrieves a random point on the first floor of the lot\n            \n            Random_any_floor: Retrieve a random point among all possible floors for current zone.\n            ', tunable_type=LotPositionStrategy, default=LotPositionStrategy.DEFAULT)}

    def get_objects_gen(self, resolver):
        lot = services.active_lot()
        from objects.terrain import TerrainPoint
        if self.lot_location_strategy == LotPositionStrategy.RANDOM_ANY_FLOOR:
            possible_start_positions = []
            for level in lot.lot_levels:
                points = get_random_points_on_floor(level)
                if points:
                    possible_start_positions.append((points[0], level))
            (position, level) = (lot.get_random_point(), 0) if len(possible_start_positions) == 0 else system_random.choice(possible_start_positions)
            yield TerrainPoint.create_for_position_and_orientation(position=position, routing_surface=SurfaceIdentifier(services.current_zone_id(), level, SurfaceType.SURFACETYPE_WORLD))
        else:
            pos = lot.get_lot_position(self.lot_location_strategy)
            yield TerrainPoint.create_for_position_and_orientation(position=pos, routing_surface=SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD))

class _LocationFromJoint(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that determines the object to be used for the\n            specified placement strategy.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'joint_name': TunableStringHash32(description='\n            The name of the joint to use for the position.\n            ', default='_FX_')}

    def get_objects_gen(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is None:
            logger.error('_LocationFromJoint: Failed to get participant.')
            return
        if participant.rig is None:
            logger.error('_LocationFromJoint: Participant does not a have a rig.')
            return
        joint_transform = get_joint_transform_from_rig(participant.rig, self.joint_name)
        obj_transform = sims4.math.Transform.concatenate(joint_transform, participant.location.transform)
        from objects.terrain import TerrainPoint
        point = TerrainPoint.create_for_position_and_orientation(position=obj_transform.translation, routing_surface=SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD))
        point.transform.orientation = obj_transform.orientation
        yield point

class _FrontDoorObject(HasTunableSingletonFactory, AutoFactoryInit):

    def get_objects_gen(self, resolver):
        front_door = services.get_door_service().get_front_door()
        if front_door is not None:
            yield front_door

class _LocationFromFloor(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that determines the lot level to be used to find\n            an initial location.\n            ', tunable_type=ParticipantTypeLotLevel, default=ParticipantTypeLotLevel.ActorLotLevel)}

    def get_objects_gen(self, resolver):
        lot_level = resolver.get_participant(self.participant)
        if lot_level is None:
            logger.error('_LocationFromFloor: Cannot resolve LotLevel from {}', self.participant)
            return
        points = get_random_points_on_floor(lot_level.level_index)
        if not points:
            return
        from objects.terrain import TerrainPoint
        yield TerrainPoint.create_for_position_and_orientation(position=points[0], routing_surface=SurfaceIdentifier(services.current_zone_id(), lot_level.level_index, SurfaceType.SURFACETYPE_WORLD))

class _LocationFromSwimmingPool(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'pool_size_test': OptionalTunable(description='\n            Filter pools to pools within the size range.\n            ', tunable=PoolSizeTest.TunableFactory())}
    SWIMMING_POOL_OBJECT_DEF = TunableReference(description='\n        Reference to basic_pool, used for filtering objects to swimming pools, not the pool_part objects.\n        ', manager=services.definition_manager())

    def get_objects_gen(self, resolver):
        if self.SWIMMING_POOL_OBJECT_DEF is None:
            return
        object_manager = services.object_manager()
        for swimming_pool in object_manager.get_objects_of_type_gen(self.SWIMMING_POOL_OBJECT_DEF):
            if self.pool_size_test is None or self.pool_size_test((swimming_pool,)):
                yield swimming_pool

class _PlacementStrategy(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'reference_obj_hidden_flags': TunableEnumFlags(description='\n            Hidden reasons we allow when retrieving the reference object.\n            ', enum_type=HiddenReasonFlag, default=HiddenReasonFlag.RABBIT_HOLE, allow_no_flags=True)}

    def _get_reference_objects_gen(self, obj, resolver, **kwargs):
        raise NotImplementedError

    def try_place_object(self, obj:'GameObject', resolver:'Resolver', location:'Optional[Any]'=None, **kwargs) -> 'bool':
        for target_obj in self._get_reference_objects_gen(obj, resolver, location=location, **kwargs):
            if target_obj.is_sim:
                target_obj = target_obj.sim_info.get_sim_instance(allow_hidden_flags=self.reference_obj_hidden_flags)
            if target_obj is not None and target_obj is None:
                pass
            elif self._try_place_object_internal(obj, target_obj, resolver, **kwargs):
                return True
        return False

class _PlacementStrategyInventory(_PlacementStrategy):
    FACTORY_TUNABLES = {'recipient': TunableInventoryOwner.TunableFactory(description='\n            The inventory into which the object is placed.\n            ')}

    def try_place_object(self, obj, resolver, **kwargs):
        recipient = self.recipient()
        recipient_inventory = recipient.get_owner_inventory(resolver=resolver)
        recipient_object = None
        if recipient_inventory is not None:
            recipient_object = recipient_inventory.owner
        transfer_object_to_lot_or_object_inventory(obj, recipient_inventory, recipient_object=recipient_object)
        return True

class _PlacementStrategyLocation(_PlacementStrategy):
    POSITION_INCREMENT = 0.5
    FACTORY_TUNABLES = {'search_flag_set': TunableEnumSet(description="\n            Set of flags for FGL Search that will be enabled if present in list.\n            If you're unsure how these flags work, consult your GPE partner.\n            ", enum_type=FGLSearchFlag, default_enum_list=[FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP, FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS, FGLSearchFlag.DONE_ON_MAX_RESULTS], invalid_enums=FGLSearchFlagsDeprecated), 'initial_location': TunableVariant(description='\n            The FGL search initial position is determined by this. If more than\n            one initial position is available, all are considered up to the\n            specified upper bound.\n            ', from_participant=_ObjectsFromParticipant.TunableFactory(), from_tags=_ObjectsFromTags.TunableFactory(), from_lot=_LocationFromLot.TunableFactory(), from_joint=_LocationFromJoint.TunableFactory(), front_door_object=_FrontDoorObject.TunableFactory(), from_floor=_LocationFromFloor.TunableFactory(), from_swimming_pool=_LocationFromSwimmingPool.TunableFactory(), default='from_participant'), 'initial_location_offset': TunableTuple(default_offset=TunableVector3(description="\n                The default Vector3 offset from the location target's\n                position.\n                ", default=sims4.math.Vector3.ZERO()), x_randomization_range=OptionalTunable(tunable=TunableInterval(description='\n                    A random number in this range will be applied to the\n                    default offset along the x axis.\n                    ', tunable_type=float, default_lower=0, default_upper=0)), z_randomization_range=OptionalTunable(tunable=TunableInterval(description='\n                    A random number in this range will be applied to the\n                    default offset along the z axis.\n                    ', tunable_type=float, default_lower=0, default_upper=0))), 'initial_location_fallback': OptionalTunable(tunable=TunableList(description='\n            A list of position(s) that will be considered should the original \n            initial location fail. It will iterate through the list from the\n            top down until the target has been placed successfully. \n            ', tunable=TunableVariant(from_participant=_ObjectsFromParticipant.TunableFactory(), from_tags=_ObjectsFromTags.TunableFactory(), from_lot=_LocationFromLot.TunableFactory(), from_joint=_LocationFromJoint.TunableFactory(), front_door_object=_FrontDoorObject.TunableFactory(), from_floor=_LocationFromFloor.TunableFactory(), from_swimming_pool=_LocationFromSwimmingPool.TunableFactory(), default='from_participant'), maxlength=5)), 'facing': OptionalTunable(description='\n            If enabled, the final location will ensure that the placed object\n            faces a specific location.\n            ', tunable=TunableTuple(target=OptionalTunable(description='\n                    The location to face.\n                    ', tunable=TunableEnumEntry(description='\n                        Specify a participant that needs to be faced.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Actor), disabled_name='face_initial_location'), angle=TunableAngle(description='\n                    The angle that facing will trying to keep inside while test\n                    FGL. The larger the number is, the more offset the facing\n                    could be, but the chance will be higher to succeed in FGL.\n                    ', default=0.5*sims4.math.PI, minimum=0, maximum=sims4.math.PI))), 'placement_constraints': TunableMapping(description='\n            When tuned, this generates geometric scoring functions for FGL to determine valid placement locations.\n            \n            For example, yoga uses this to ensure that yoga mats are placed within a cone constraint in front of the\n            instructor and that the placement is within line of sight.\n            \n            A mapping of participant type to constraint relative to that participant type that we will attempt\n            to restrict placement of the object to.\n            ', key_type=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), value_type=TunableList(description='\n                A list of geometric constraints relative to the participant type that must be met.\n                ', tunable=TunableGeometricConstraintVariant())), 'perform_fgl_check': Tunable(description='\n            If checked (default), FGL will be used to find an unblocked location \n            for the object to be placed after it is created.\n            \n            If unchecked, FGL will not be performed, and the object will be \n            placed at the location + orientation specified, even if it overlaps\n            other footprints.\n            \n            Ideally this should be used in conjunction with another system that\n            assures objects will not overlap.  This is useful for placing an\n            object on top of a jig, but probably should not be used for placing\n            a build buy object that intersects with another build buy object.\n            \n            It should also be noted that object collisions will not play nice\n            with save/load, and objects that overlap may be deleted when \n            loading a save.  This should be used with objects that are temporary.\n            ', tunable_type=bool, default=True), 'ignore_bb_footprints': Tunable(description='\n            Ignores the build buy object footprints when trying to find a\n            position for creating this object. This will allow objects to appear\n            on top of each other.\n            \n            e.g. Trash cans when tipped over want to place the trash right under\n            them so it looks like the pile came out from the object while it was\n            tipped.\n            ', tunable_type=bool, default=True), 'allow_off_lot_placement': Tunable(description='\n            If checked, objects will be allowed to be placed off-lot. If\n            unchecked, we will always attempt to place created objects on the\n            active lot.\n            ', tunable_type=bool, default=False), 'stay_outside_placement': Tunable(description='\n            If checked, objects will run their placement search only for\n            positions that are considered outside.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.DEPRECATED), 'in_same_room': Tunable(description='\n            If checked, objects will be placed in the same block/room of the\n            initial location. If there is not enough space to put down the\n            object in the same block, the placement will fail.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.DEPRECATED), 'skip_plex_starting_position_validation': Tunable(description='\n            If checked, placement of the object will not restrict the starting point of the placement search to inside \n            of the active plex when doing an on-lot placement. \n            \n            For example, if your reference starting point is an object in a common area outside of an apartment unit \n            like a trash chute, and you want to spawn trash next to that trash chute, you would want to check this.\n            ', tunable_type=bool, default=False), 'terrain_tags': OptionalTunable(description='\n            If enabled, a set of allowed terrain tags. At least one tag must\n            match the terrain under each vertex of the footprint of the supplied\n            object.\n            ', tunable=TunableEnumSet(enum_type=TerrainTag, enum_default=TerrainTag.INVALID)), 'stay_in_connected_connectivity_group': Tunable(description='\n            If unchecked then the object will be allowed to be placed in\n            a connectivity group that is currently disconnected from\n            the starting location.\n            \n            If checked then the placement will fail if there is not a\n            position inside a connected connectivity group from the\n            starting position that can be used for placement.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.DEPRECATED), 'surface_type_override': OptionalTunable(description='\n            If enabled, we will override the routing surface type of the\n            location to whatever is tuned here. Otherwise, we use the routing\n            surface of the initial location.\n            \n            Example: The initial location may be in a pool but you want the\n            created object to be placed on the ground.\n            ', tunable=TunableEnumEntry(description='\n                The routing surface we want to force the object to be placed on.\n                ', tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_WORLD)), 'min_water_depth': OptionalTunable(description='\n            (float) If provided, each vertex of the test polygon along with its centroid will\n            be tested to determine whether the ocean water at the test location is at least this deep.\n            Values <= 0 indicate placement on land is valid.\n            ', tunable=Tunable(description='\n                Value of the min water depth allowed.\n                ', tunable_type=float, default=-1.0)), 'max_water_depth': OptionalTunable(description='\n            (float) If provided, each vertex of the test polygon along with its centroid will\n            be tested to determine whether the ocean water at the test location is at most this deep.\n            Values <= 0 indicate placement in ocean is invalid.\n            ', tunable=Tunable(description='\n                Value of the max water depth allowed.\n                ', tunable_type=float, default=1000.0)), 'ignore_sim_positions': Tunable(description='\n            If checked, the FGL search will ignore current Sim positions and \n            any positions Sims are intending to go.  If unchecked, these Sim\n            positions will be taken into account when placing the object.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.DEPRECATED), 'raytest': OptionalTunable(description='\n            If enabled then we will run a raytest to make sure that the object remains within LOS.\n            ', tunable=TunableTuple(description='\n                Data related to running a raytest to a position.\n                ', starting_position=OptionalTunable(description='\n                    Use either the previously calculated starting point or perform a raytest in regards to a specific\n                    participant.\n                    ', tunable=TunableEnumEntry(description="\n                        A partcipant's location that we will perform the raytest to.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Actor), enabled_name='use_participants_location', disabled_name='use_initial_location'), raytest_radius=Tunable(description='\n                    The radius of the ray.  0.1 is acceptable for a line of sight check.\n                    ', tunable_type=float, default=0.1), raytest_start_height_offset=Tunable(description='\n                    The height offset of the start height.  1.5 is the height of a Sim.\n                    ', tunable_type=float, default=1.5), raytest_end_height_offset=Tunable(description='\n                    The height offset of end point of the ray.  1.5 is the height of a Sim.\n                    ', tunable_type=float, default=1.5))), 'randomize_orientation': Tunable(description='\n            If checked, object will be spawned using a random orientation.\n            Otherwise, it will use the orientation of the target object.\n            ', tunable_type=bool, default=True), 'enclosed_room_only': Tunable(description='\n            If checked, objects will run their placement search only for\n            positions that are considered in an enclosed room.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.DEPRECATED), 'lot_terrain_only': Tunable(description='\n            If checked, objects will run their placement search only for\n            positions that are within the lot and on terrain.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.DEPRECATED)}

    def _get_reference_objects_gen(self, obj, resolver, location=None, **kwargs):
        reference_location = location or self.initial_location
        yield from reference_location.get_objects_gen(resolver)

    def try_place_object(self, obj:'GameObject', resolver:'Resolver', location:'Optional[Any]'=None, **kwargs) -> 'bool':
        return super().try_place_object(obj, resolver, location=location or self.initial_location)

    def _try_place_object_internal(self, obj, target_obj, resolver, ignored_object_ids=None, **kwargs):
        offset_tuning = self.initial_location_offset
        default_offset = sims4.math.Vector3(offset_tuning.default_offset.x, offset_tuning.default_offset.y, offset_tuning.default_offset.z)
        x_range = offset_tuning.x_randomization_range
        z_range = offset_tuning.z_randomization_range
        if self.randomize_orientation:
            start_orientation = sims4.random.random_orientation()
        else:
            start_orientation = target_obj.orientation
        if x_range is not None:
            x_axis = start_orientation.transform_vector(sims4.math.Vector3.X_AXIS())
            default_offset += x_axis*random.uniform(x_range.lower_bound, x_range.upper_bound)
        if z_range is not None:
            z_axis = start_orientation.transform_vector(sims4.math.Vector3.Z_AXIS())
            default_offset += z_axis*random.uniform(z_range.lower_bound, z_range.upper_bound)
        offset = sims4.math.Transform(default_offset, sims4.math.Quaternion.IDENTITY())
        start_position = sims4.math.Transform.concatenate(offset, target_obj.transform).translation
        routing_surface = target_obj.routing_surface
        active_lot = services.active_lot()
        start_position_is_off_lot = not active_lot.is_position_on_lot(start_position)
        if self.allow_off_lot_placement or start_position_is_off_lot:
            return False
        if not self.perform_fgl_check:
            starting_location = create_starting_location(position=start_position, orientation=start_orientation, routing_surface=routing_surface)
            obj.move_to(routing_surface=routing_surface, translation=starting_location.position, orientation=starting_location.orientation)
            return True
        search_flags = 0
        for flag in self.search_flag_set:
            search_flags |= flag
        if self.surface_type_override is not None:
            routing_surface = SurfaceIdentifier(routing_surface.primary_id, routing_surface.secondary_id, self.surface_type_override)
        else:
            search_flags |= FGLSearchFlag.SHOULD_TEST_ROUTING
        if self.ignore_sim_positions:
            search_flags |= FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS | FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS
        if self.in_same_room:
            search_flags |= FGLSearchFlag.STAY_IN_CURRENT_BLOCK
        if self.stay_in_connected_connectivity_group:
            search_flags |= FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
        if self.stay_outside_placement:
            search_flags |= FGLSearchFlag.STAY_OUTSIDE
        if self.enclosed_room_only:
            search_flags |= FGLSearchFlag.ENCLOSED_ROOM_ONLY
        if self.lot_terrain_only:
            search_flags |= FGLSearchFlag.LOT_TERRAIN_ONLY
        raytest_info = None
        if self.raytest:
            start_point_override = None
            if self.raytest.starting_position is not None:
                raytest_target = resolver.get_participant(self.raytest.starting_position)
                if raytest_target is not None:
                    if raytest_target.is_sim:
                        raytest_target = raytest_target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                    start_point_override = raytest_target.transform.translation
            raytest_info = RaytestInfo(raytest_radius=self.raytest.raytest_radius, raytest_start_offset=self.raytest.raytest_start_height_offset, raytest_end_offset=self.raytest.raytest_end_height_offset, raytest_start_point_override=start_point_override)
        restrictions = None
        if self.facing is not None:
            if self.facing.target is None:
                facing_target = target_obj
            else:
                facing_target = resolver.get_participant(self.facing.target)
            if facing_target is not None:
                restriction = sims4.geometry.RelativeFacingRange(facing_target.position, self.facing.angle)
                restrictions = (restriction,)
        scoring_functions = None
        if self.placement_constraints:
            scoring_functions = self._generate_scoring_functions(resolver)
        terrain_tags = list(self.terrain_tags) if self.terrain_tags else []
        routing_context = None
        routing_component = obj.routing_component
        if routing_component is not None:
            routing_context = routing_component.routing_context
        if self.allow_off_lot_placement and start_position_is_off_lot:
            obj.location = sims4.math.Location(sims4.math.Transform(start_position, start_orientation), routing_surface)
            starting_location = create_starting_location(position=start_position, orientation=start_orientation, routing_surface=routing_surface)
            try:
                context = create_fgl_context_for_object_off_lot(starting_location, obj, terrain_tags=terrain_tags, search_flags=search_flags, ignored_object_ids=(obj.id,), restrictions=restrictions, min_water_depth=self.min_water_depth, max_water_depth=self.max_water_depth, routing_context=routing_context, scoring_functions=scoring_functions, raytest_info=raytest_info)
            except Exception:
                logger.exception('Exception occurred when creating FGL context for placing {}', obj)
                return False
        else:
            if not self.ignore_bb_footprints:
                if routing_surface.type != SurfaceType.SURFACETYPE_WORLD:
                    search_flags |= FGLSearchFlag.SHOULD_TEST_BUILDBUY
                else:
                    search_flags |= FGLSearchFlag.SHOULD_TEST_BUILDBUY | FGLSearchFlag.STAY_IN_CURRENT_BLOCK
                if start_position_is_off_lot:
                    start_position = active_lot.get_default_position(position=start_position)
                elif not self.skip_plex_starting_position_validation:
                    position_inside_plex = self._get_plex_postion_for_object_creation(start_position, routing_surface.secondary_id)
                    if position_inside_plex is not None:
                        start_position = position_inside_plex
            starting_location = create_starting_location(position=start_position, orientation=start_orientation, routing_surface=routing_surface)
            pos_increment_info = PositionIncrementInfo(position_increment=self.POSITION_INCREMENT, from_exception=False)
            water_depth_info = WaterDepthInfo(min_water_depth=self.min_water_depth, max_water_depth=self.max_water_depth)
            try:
                context = create_fgl_context_for_object(starting_location, obj, terrain_tags=terrain_tags, search_flags=search_flags, ignored_object_ids=ignored_object_ids, position_increment_info=pos_increment_info, restrictions=restrictions, water_depth_info=water_depth_info, routing_context=routing_context, scoring_functions=scoring_functions, raytest_info=raytest_info)
            except Exception:
                logger.exception('Exception occurred when creating FGL context for placing {}', obj)
                return False
        (translation, orientation, _) = context.find_good_location()
        if translation is not None:
            obj.move_to(routing_surface=routing_surface, translation=translation, orientation=orientation)
            return True
        if self.initial_location_fallback:
            for location in self.initial_location_fallback:
                if self.try_place_object(obj, resolver, location=location, **kwargs):
                    return True
        return False

    def _generate_scoring_functions(self, resolver):
        actor = resolver.get_participant(ParticipantType.Actor)
        object_manager = services.object_manager()
        if actor is None:
            logger.error('_generate_scoring_functions: Could not find actor in {}', resolver)
            return
        sim = object_manager.get(actor.id)
        if sim is None:
            logger.error('_generate_scoring_functions: Could not find instance for {} in object manager! {}', sim, resolver)
            return
        else:
            polygon_constraint = ANYWHERE
            scoring_functions = []
            for (participant_type, relative_placement_constraints) in self.placement_constraints.items():
                participant = resolver.get_participant(participant_type)
                if participant is None:
                    logger.error('_generate_scoring_functions: Could not resolve participant for {} in {}', participant_type, resolver)
                    break
                participant_obj = object_manager.get(participant.id)
                if participant_obj is None:
                    logger.error('_generate_scoring_functions: Could not find instance for {} in object manager! {}', participant, resolver)
                    break
                for tuned_relative_constraint in relative_placement_constraints:
                    relative_constraint = tuned_relative_constraint.create_constraint(sim, participant_obj)
                    polygon_constraint = polygon_constraint.intersect(relative_constraint)
            for polygon in tuple(*polygon_constraint.polygons):
                scoring_functions.append(ScoringFunctionPolygon(polygon))
            if not scoring_functions:
                logger.error('_generate_scoring_functions: No scoring functions generated, check tuning and resolver for missing participants or constraints {}', resolver)
                return
        return scoring_functions

    def _get_plex_postion_for_object_creation(self, start_position, level):
        plex_service = services.get_plex_service()
        is_active_zone_a_plex = plex_service.is_active_zone_a_plex()
        if not is_active_zone_a_plex:
            return
        if plex_service.get_plex_zone_at_position(start_position, level) is not None:
            return
        front_door = services.get_door_service().get_front_door()
        if front_door is not None:
            (front_position, back_position) = front_door.get_door_positions()
            front_zone_id = plex_service.get_plex_zone_at_position(front_position, front_door.level)
            if front_zone_id is not None:
                return front_position
            else:
                back_zone_id = plex_service.get_plex_zone_at_position(back_position, front_door.level)
                if back_zone_id is not None:
                    return back_position

class _PlacementStrategySlot(_PlacementStrategy):
    FACTORY_TUNABLES = {'parent': TunableVariant(description='\n            The object this object is going to be slotted into.\n            ', from_participant=_ObjectsFromParticipant.TunableFactory(participant_type_default=(ParticipantType.Object,)), from_tags=_ObjectsFromTags.TunableFactory(), default='from_participant'), 'parent_slot': TunableVariant(description='\n            The slot on location_target where the object should go. This may be\n            either the exact name of a bone on the location_target or a slot\n            type, in which case the first empty slot of the specified type in\n            which the child object fits will be used.\n            ', by_name=Tunable(description='\n                The exact name of a slot on the location_target in which the\n                target object should go.\n                ', tunable_type=str, default='_ctnm_'), by_reference=TunableReference(description='\n                A particular slot type in which the target object should go.\n                The first empty slot of this type found on the location_target\n                will be used.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))), 'use_part_owner': Tunable(description='\n            If enabled and target is a part, placement will use the part owner\n            instead of the part.\n            ', tunable_type=bool, default=False)}

    def _get_reference_objects_gen(self, obj, resolver, **kwargs):
        yield from self.parent.get_objects_gen(resolver)

    def _try_place_object_internal(self, obj, target_obj, resolver, **kwargs):
        if target_obj.is_part:
            target_obj = target_obj.part_owner
        parent_slot = self.parent_slot
        result = False
        if self.use_part_owner and isinstance(parent_slot, str):
            bone_name_hash = sims4.hash_util.hash32(parent_slot)
            result = parent_object(obj, target_obj, bone_name_hash=bone_name_hash)
        else:
            result = target_obj.slot_object(parent_slot=parent_slot, slotting_object=obj)
        return result

class _PlacementStrategyHouseholdInventory(_PlacementStrategy):

    def try_place_object(self, obj, resolver, **kwargs):
        return build_buy.move_object_to_household_inventory(obj)

class TunablePlacementStrategyVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, inventory=_PlacementStrategyInventory.TunableFactory(), location=_PlacementStrategyLocation.TunableFactory(), slot=_PlacementStrategySlot.TunableFactory(), household_inventory=_PlacementStrategyHouseholdInventory.TunableFactory(), default='location', **kwargs)

class PlacementHelper(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'placement_strategy_groups': TunableList(description='\n            A list of ordered strategy groups. These are executed in order. If\n            any placement from the group succeeds, the placement is considered\n            terminated.\n            ', tunable=TunableList(description='\n                A list of weighted strategies. Each placement strategy is\n                randomly weighted against the rest. Attempts are made until all\n                strategies are exhausted. If none succeeds, the next group is\n                considered.\n                ', tunable=TunableTuple(weight=TunableMultiplier.TunableFactory(description='\n                        The weight of this strategy relative to other strategies\n                        in its group.\n                        '), placement_strategy=TunablePlacementStrategyVariant(description='\n                        The placement strategy for the object in question.\n                        ')), minlength=1), minlength=1)}

    def try_place_object(self, obj, resolver, **kwargs):
        for strategy_group in self.placement_strategy_groups:
            strategies = [(entry.weight.get_multiplier(resolver), entry.placement_strategy) for entry in strategy_group]
            while strategies:
                strategy = pop_weighted(strategies)
                if strategy is None:
                    break
                if strategy.try_place_object(obj, resolver, **kwargs):
                    return True
        return False
