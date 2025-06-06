from _math import Quaternion, Vector3, Transformfrom enum_lib import Enumimport weakrefimport enumimport sims4.reloadfrom objects.proxy import ProxyObjectimport build_buyimport placementimport serviceslogger = sims4.log.Logger('Routing')try:
    import _pathing
except ImportError:

    def get_actor_pitch_roll_at_location(*_, **__):
        return 0.0

    def get_default_traversal_cost(*_, **__):
        return 1.0

    def get_default_discouragement_cost(*_, **__):
        return 100.0

    def get_default_obstacle_cost(*_, **__):
        return 10000.0

    def get_min_agent_radius(*_, **__):
        return 0.123

    def get_default_agent_radius(*_, **__):
        return 0.123

    def get_default_agent_extra_clearance_multiplier(*_, **__):
        return 2.0

    def set_default_agent_extra_clearance_multiplier(*_, **__):
        pass

    def get_world_size(*_, **__):
        pass

    def get_world_bounds(*_, **__):
        pass

    def is_position_in_world_bounds(*_, **__):
        return False

    def is_position_in_surface_bounds(*_, **__):
        return False

    def get_world_center(*_, **__):
        pass

    def invalidate_navmesh(*_, **__):
        pass

    def add_footprint(*_, **__):
        pass

    def remove_footprint(*_, **__):
        pass

    def invalidate_footprint(*_, **__):
        pass

    def get_footprint_polys(*_, **__):
        pass

    def add_portal(*_, **__):
        pass

    def remove_portal(*_, **__):
        pass

    def get_stair_portals(*_, **__):
        pass

    def get_ladder_levels_and_height(*_, **__):
        pass

    def get_blocked_ladder_portals(*_, **__):
        pass

    def has_walkstyle_info(*_, **__):
        pass

    def test_connectivity_batch(*_, **__):
        pass

    def estimate_path_batch(*_, **__):
        pass

    def estimate_distance_between_multiple_points(*_, **__):
        pass

    def test_connectivity_math_locations(*_, **__):
        return False

    def test_connectivity_permissions_for_handle(*_, **__):
        return False

    def test_point_placement_in_navmesh(*_, **__):
        return False

    def test_polygon_placement_in_navmesh(*_, **__):
        return False

    def get_portals_in_connectivity_path(*_, **__):
        pass

    def estimate_path_portals(*_, **__):
        return (-1, 0)

    def estimate_path_distance(*_, **__):
        return (-1.0, 0)

    def ray_test(*_, **__):
        return False

    RAYCAST_HIT_TYPE_NONE = 0
    RAYCAST_HIT_TYPE_IMPASSABLE = 1
    RAYCAST_HIT_TYPE_LOS_IMPASSABLE = 2
    RAYCAST_HIT_TYPE_ERROR = 4294967295

    def ray_test_verbose(*_, **__):
        return RAYCAST_HIT_TYPE_NONE

    def is_location_in_building(*_, **__):
        return False

    def planner_build_id(*_, **__):
        return 0

    def get_walkstyle_hash_from_resource(*_, **__):
        return 0

    def get_walkstyle_name_from_resource(*_, **__):
        return ''

    def add_fence(*_, **__):
        pass

    def get_last_fence(*_, **__):
        return 0

    def update_portal_cost(*_, **__):
        pass

    def is_portal_valid(*_, **__):
        pass

    def flush_planner(*_, **__):
        pass

    class LocationBase:

        def __init__(self, position, orientation=None, routing_surface=None):
            pass

    class SurfaceIdentifier:

        def __init__(self, primary_id, secondary_id=None, surface_type=None):
            pass

        @property
        def primary_id(self):
            return 0

        @property
        def secondary_id(self):
            return 0

        @property
        def type(self):
            return 0

    class Destination:

        def __init__(self, loc, weight=1.0, tag=0):
            self._loc = loc
            self._weight = weight
            self._tag = tag

        @property
        def location(self):
            return self._loc

        @property
        def weight(self):
            return self._weight

        @property
        def tag(self):
            return self._tag

        @property
        def has_slot_params(self):
            return False

    class SurfaceType(enum.Int):
        SURFACETYPE_UNKNOWN = 0
        SURFACETYPE_WORLD = 1
        SURFACETYPE_OBJECT = 2
        SURFACETYPE_POOL = 3

    object_routing_surfaces = (SurfaceType.SURFACETYPE_OBJECT, SurfaceType.SURFACETYPE_POOL)

    class FootprintType(enum.Int, export=False):
        FOOTPRINT_TYPE_WORLD = 1
        FOOTPRINT_TYPE_LANDING_STRIP = 2
        FOOTPRINT_TYPE_LOT = 3
        FOOTPRINT_TYPE_BUILD = 4
        FOOTPRINT_TYPE_PATH = 5
        FOOTPRINT_TYPE_OBJECT = 6
        FOOTPRINT_TYPE_OVERRIDE = 7

    class RoutingContext:

        def __init__(self):
            pass

        @property
        def object_id(self):
            return 0

        @object_id.setter
        def object_id(self, value):
            pass

    class PathPlanContext:

        def __init__(self):
            pass

        @property
        def agent_id(self):
            return 0

        @agent_id.setter
        def agent_id(self, value):
            pass

    PATH_RESULT_UNKNOWN = 0
    PATH_RESULT_SUCCESS_TRIVIAL = 1
    PATH_RESULT_SUCCESS_LOCAL = 2
    PATH_RESULT_SUCCESS_GLOBAL = 3
    PATH_RESULT_FAIL_NO_GOALS = 4
    PATH_RESULT_FAIL_INVALID_START_SURFACE = 5
    PATH_RESULT_FAIL_INVALID_START_POINT = 6
    PATH_RESULT_FAIL_START_POINT_IN_IMPASSABLE_REGION = 7
    PATH_RESULT_FAIL_TOO_MANY_CYCLES = 8
    PATH_RESULT_FAIL_PARTIAL_PATH = 9
    PATH_RESULT_FAIL_NO_PATH = 10
    FAIL_PATH_TYPE_UNKNOWN = 0
    FAIL_PATH_TYPE_OBJECT_BLOCKING = 1
    FAIL_PATH_TYPE_BUILD_BLOCKING = 2
    FAIL_PATH_TYPE_UNKNOWN_BLOCKING = 3
    GOAL_STATUS_PENDING = 0
    GOAL_STATUS_INVALID_SURFACE = 1
    GOAL_STATUS_INVALID_POINT = 2
    GOAL_STATUS_DUPLICATE_GOAL = 4
    GOAL_STATUS_CONNECTIVITY_GROUP_UNREACHABLE = 8
    GOAL_STATUS_COMPONENT_DIFFERENT = 16
    GOAL_STATUS_NOTEVALUATED = 32
    GOAL_STATUS_LOWER_SCORE = 64
    GOAL_STATUS_IMPASSABLE = 128
    GOAL_STATUS_BLOCKED = 256
    GOAL_STATUS_REJECTED_UNKNOWN = 512
    GOAL_STATUS_SUCCESS = 1024
    GOAL_STATUS_SUCCESS_TRIVIAL = 2048
    GOAL_STATUS_SUCCESS_LOCAL = 4096
    FOOTPRINT_KEY_ON_LOT = 1
    FOOTPRINT_KEY_OFF_LOT = 2
    FOOTPRINT_KEY_REQUIRE_NO_CARRY = 4
    FOOTPRINT_KEY_REQUIRE_SMALL_HEIGHT = 16
    FOOTPRINT_KEY_REQUIRE_TINY_HEIGHT = 32
    FOOTPRINT_KEY_REQUIRE_LOW_HEIGHT = 512
    FOOTPRINT_KEY_REQUIRE_MEDIUM_HEIGHT = 1024
    FOOTPRINT_KEY_REQUIRE_FLOATING = 2048
    FOOTPRINT_KEY_REQUIRE_LARGE_HEIGHT = 64
    FOOTPRINT_KEY_REQUIRE_WADING_DEEP = 4096
    FOOTPRINT_KEY_REQUIRE_WADING_MEDIUM = 8192
    FOOTPRINT_KEY_REQUIRE_WADING_SHALLOW = 16384
    FOOTPRINT_KEY_REQUIRE_WADING_VERY_SHALLOW = 32768
    FOOTPRINT_KEY_DEFAULT = FOOTPRINT_KEY_ON_LOT | FOOTPRINT_KEY_OFF_LOT
    FOOTPRINT_DISCOURAGE_KEY_DEFAULT = 0
    FOOTPRINT_DISCOURAGE_KEY_LANDINGSTRIP = 1
    SPECIES_FLAG_RESERVE_INDEX = 16

    class EstimatePathFlag(enum.IntFlags, export=False):
        NONE = 0
        RETURN_DISTANCE_ON_FAIL = 1
        IGNORE_CONNECTIVITY_HANDLES = 2
        RETURN_DISTANCE_FROM_FIRST_CONNECTION_FOUND = 4
        ALWAYS_RETURN_MINIMUM_DISTANCE = 8
        ZERO_DISTANCE_IS_OPTIMAL = 16
        NO_NEAREST_VALID_POINT_SEARCH = 32

    class EstimatePathResults(enum.IntFlags, export=False):
        NONE = 0
        SUCCESS = 1
        PATHPLANNER_NOT_INITIALIZED = 2
        START_SURFACE_INVALID = 4
        START_LOCATION_INVALID = 8
        START_LOCATION_BLOCKED = 16
        ALL_START_HANDLES_BLOCKED = 32
        GOAL_SURFACE_INVALID = 64
        GOAL_LOCATION_INVALID = 128
        GOAL_LOCATION_BLOCKED = 256
        ALL_GOAL_HANDLES_BLOCKED = 512
        NO_CONNECTIVITY = 1024
        UNKNOWN_ERROR = 2048
get_actor_pitch_roll_at_location = _pathing.get_actor_pitch_roll_at_locationget_default_traversal_cost = _pathing.get_default_traversal_costget_default_discouragement_cost = _pathing.get_default_discouragement_costget_default_obstacle_cost = _pathing.get_default_obstacle_costget_min_agent_radius = _pathing.get_min_agent_radiusget_default_agent_radius = _pathing.get_default_agent_radiusget_default_agent_extra_clearance_multiplier = _pathing.get_default_agent_extra_clearance_multiplierset_default_agent_extra_clearance_multiplier = _pathing.set_default_agent_extra_clearance_multiplierget_world_size = _pathing.get_world_sizeget_world_bounds = _pathing.get_world_boundsis_position_in_world_bounds = _pathing.is_position_in_world_boundsis_position_in_surface_bounds = _pathing.is_position_in_surface_boundsget_world_center = _pathing.get_world_centerinvalidate_navmesh = _pathing.invalidate_navmeshadd_footprint = _pathing.add_footprintremove_footprint = _pathing.remove_footprintinvalidate_footprint = _pathing.invalidate_footprintget_footprint_polys = _pathing.get_footprint_polysadd_portal = _pathing.add_portalremove_portal = _pathing.remove_portalget_stair_portals = _pathing.get_stair_portalsget_stair_portal_key_mask = _pathing.get_stair_portal_key_maskget_ladder_levels_and_height = _pathing.get_ladder_levels_and_heightget_blocked_ladder_portals = _pathing.get_blocked_ladder_portalstest_connectivity_pt_pt = _pathing.test_connectivity_pt_pttest_point_placement_in_navmesh = _pathing.test_point_placement_in_navmeshtest_polygon_placement_in_navmesh = _pathing.test_polygon_placement_in_navmeshray_test = _pathing.ray_testget_portals_in_connectivity_path = _pathing.get_portals_in_connectivity_pathupdate_portal_cost = _pathing.update_portal_costis_portal_valid = _pathing.is_portal_validRAYCAST_HIT_TYPE_NONE = _pathing.RAYCAST_HIT_TYPE_NONERAYCAST_HIT_TYPE_IMPASSABLE = _pathing.RAYCAST_HIT_TYPE_IMPASSABLERAYCAST_HIT_TYPE_LOS_IMPASSABLE = _pathing.RAYCAST_HIT_TYPE_LOS_IMPASSABLEray_test_verbose = _pathing.ray_test_verbose
def is_location_in_building(location):
    pathing_location = location
    if not isinstance(pathing_location, Location):
        pathing_location = Location(location.world_transform.translation, location.world_transform.orientation, location.routing_surface)
    return _pathing.is_3d_point_indoors(pathing_location)
get_walkstyle_info = _pathing.get_walkstyle_infoget_walkstyle_info_full = _pathing.get_walkstyle_info_fullhas_walkstyle_info = _pathing.has_walkstyle_infoget_walkstyle_property = _pathing.get_walkstyle_propertyplanner_build_id = _pathing.planner_build_idget_walkstyle_hash_from_resource = _pathing.get_walkstyle_hash_from_resourceget_walkstyle_name_from_resource = _pathing.get_walkstyle_name_from_resourceplanner_build_record = _pathing.planner_build_recordflush_planner = _pathing.flush_planneradd_fence = _pathing.add_fenceget_last_fence = _pathing.get_last_fenceLocationBase = _pathing.LocationSurfaceIdentifier = _pathing.SurfaceIdentifierpath_wrapper = _pathing.PathNodeListDestination = _pathing.DestinationRoutingContext = _pathing.RoutingContextPathPlanContext = _pathing.PathPlanContext
class SurfaceType(enum.Int):
    SURFACETYPE_UNKNOWN = _pathing.SURFACETYPE_UNKNOWN
    SURFACETYPE_WORLD = _pathing.SURFACETYPE_WORLD
    SURFACETYPE_OBJECT = _pathing.SURFACETYPE_OBJECT
    SURFACETYPE_POOL = _pathing.SURFACETYPE_POOL

class FootprintType(enum.Int, export=False):
    FOOTPRINT_TYPE_WORLD = _pathing.FOOTPRINT_TYPE_WORLD
    FOOTPRINT_TYPE_LANDING_STRIP = _pathing.FOOTPRINT_TYPE_LANDING_STRIP
    FOOTPRINT_TYPE_LOT = _pathing.FOOTPRINT_TYPE_LOT
    FOOTPRINT_TYPE_BUILD = _pathing.FOOTPRINT_TYPE_BUILD
    FOOTPRINT_TYPE_PATH = _pathing.FOOTPRINT_TYPE_PATH
    FOOTPRINT_TYPE_OBJECT = _pathing.FOOTPRINT_TYPE_OBJECT
    FOOTPRINT_TYPE_OVERRIDE = _pathing.FOOTPRINT_TYPE_OVERRIDE
object_routing_surfaces = (SurfaceType.SURFACETYPE_OBJECT, SurfaceType.SURFACETYPE_POOL)
def test_connectivity_math_locations(loc1:sims4.math.Location, loc2:sims4.math.Location, routing_context):
    return test_connectivity_pt_pt(Location(loc1.transform.translation, orientation=loc1.transform.orientation, routing_surface=loc1.routing_surface), Location(loc2.transform.translation, orientation=loc2.transform.orientation, routing_surface=loc2.routing_surface), routing_context)

def test_connectivity_batch(src, dst, routing_context=None, compute_cost=False, flush_planner=False, allow_permissive_connections=False, ignore_objects=False):
    return _pathing.test_connectivity_batch(src, dst, routing_context, compute_cost, flush_planner, allow_permissive_connections, ignore_objects)

def estimate_path_batch(src, dst, routing_context=None, flush_planner=False, allow_permissive_connections=False, ignore_objects=False):
    return _pathing.estimate_path_batch(src, dst, routing_context, flush_planner, allow_permissive_connections, ignore_objects)

def estimate_distance_between_multiple_points(sources, dests, routing_context=None, allow_permissive_connections=False):
    return _pathing.estimate_distance_between_multiple_points(sources, dests, routing_context, allow_permissive_connections)

def test_connectivity_permissions_for_handle(handle, routing_context=None, flush_planner=False):
    return _pathing.test_connectivity_permissions_for_handle(handle, routing_context, flush_planner)
PATH_RESULT_UNKNOWN = _pathing.PATH_RESULT_UNKNOWNPATH_RESULT_SUCCESS_TRIVIAL = _pathing.PATH_RESULT_SUCCESS_TRIVIALPATH_RESULT_SUCCESS_LOCAL = _pathing.PATH_RESULT_SUCCESS_LOCALPATH_RESULT_SUCCESS_GLOBAL = _pathing.PATH_RESULT_SUCCESS_GLOBALPATH_RESULT_FAIL_NO_GOALS = _pathing.PATH_RESULT_FAIL_NO_GOALSPATH_RESULT_FAIL_INVALID_START_SURFACE = _pathing.PATH_RESULT_FAIL_INVALID_START_SURFACEPATH_RESULT_FAIL_INVALID_START_POINT = _pathing.PATH_RESULT_FAIL_INVALID_START_POINTPATH_RESULT_FAIL_START_POINT_IN_IMPASSABLE_REGION = _pathing.PATH_RESULT_FAIL_START_POINT_IN_IMPASSABLE_REGIONPATH_RESULT_FAIL_TOO_MANY_CYCLES = _pathing.PATH_RESULT_FAIL_TOO_MANY_CYCLESPATH_RESULT_FAIL_PARTIAL_PATH = _pathing.PATH_RESULT_FAIL_PARTIAL_PATHPATH_RESULT_FAIL_NO_PATH = _pathing.PATH_RESULT_FAIL_NO_PATHFAIL_PATH_TYPE_UNKNOWN = _pathing.FAIL_PATH_TYPE_UNKNOWNFAIL_PATH_TYPE_OBJECT_BLOCKING = _pathing.FAIL_PATH_TYPE_OBJECT_BLOCKINGFAIL_PATH_TYPE_BUILD_BLOCKING = _pathing.FAIL_PATH_TYPE_BUILD_BLOCKINGFAIL_PATH_TYPE_UNKNOWN_BLOCKING = _pathing.FAIL_PATH_TYPE_UNKNOWN_BLOCKINGGOAL_STATUS_PENDING = _pathing.GOAL_STATUS_PENDINGGOAL_STATUS_INVALID_SURFACE = _pathing.GOAL_STATUS_INVALID_SURFACEGOAL_STATUS_INVALID_POINT = _pathing.GOAL_STATUS_INVALID_POINTGOAL_STATUS_DUPLICATE_GOAL = _pathing.GOAL_STATUS_DUPLICATE_GOALGOAL_STATUS_CONNECTIVITY_GROUP_UNREACHABLE = _pathing.GOAL_STATUS_CONNECTIVITY_GROUP_UNREACHABLEGOAL_STATUS_COMPONENT_DIFFERENT = _pathing.GOAL_STATUS_COMPONENT_DIFFERENTGOAL_STATUS_NOTEVALUATED = _pathing.GOAL_STATUS_NOTEVALUATEDGOAL_STATUS_LOWER_SCORE = _pathing.GOAL_STATUS_LOWER_SCOREGOAL_STATUS_IMPASSABLE = _pathing.GOAL_STATUS_IMPASSABLEGOAL_STATUS_BLOCKED = _pathing.GOAL_STATUS_BLOCKEDGOAL_STATUS_REJECTED_UNKNOWN = _pathing.GOAL_STATUS_REJECTED_UNKNOWNGOAL_STATUS_SUCCESS = _pathing.GOAL_STATUS_SUCCESSGOAL_STATUS_SUCCESS_TRIVIAL = _pathing.GOAL_STATUS_SUCCESS_TRIVIALGOAL_STATUS_SUCCESS_LOCAL = _pathing.GOAL_STATUS_SUCCESS_LOCALFOOTPRINT_KEY_ON_LOT = _pathing.FOOTPRINT_KEY_ON_LOTFOOTPRINT_KEY_OFF_LOT = _pathing.FOOTPRINT_KEY_OFF_LOTFOOTPRINT_KEY_REQUIRE_NO_CARRY = _pathing.FOOTPRINT_KEY_REQUIRE_NO_CARRYFOOTPRINT_KEY_REQUIRE_SMALL_HEIGHT = _pathing.FOOTPRINT_KEY_REQUIRE_SMALL_HEIGHTFOOTPRINT_KEY_REQUIRE_TINY_HEIGHT = _pathing.FOOTPRINT_KEY_REQUIRE_TINY_HEIGHTFOOTPRINT_KEY_REQUIRE_LOW_HEIGHT = _pathing.FOOTPRINT_KEY_REQUIRE_LOW_HEIGHTFOOTPRINT_KEY_REQUIRE_MEDIUM_HEIGHT = _pathing.FOOTPRINT_KEY_REQUIRE_MEDIUM_HEIGHTFOOTPRINT_KEY_REQUIRE_FLOATING = _pathing.FOOTPRINT_KEY_REQUIRE_FLOATINGFOOTPRINT_KEY_REQUIRE_LARGE_HEIGHT = _pathing.FOOTPRINT_KEY_REQUIRE_LARGE_HEIGHTFOOTPRINT_KEY_REQUIRE_WADING_DEEP = _pathing.FOOTPRINT_KEY_REQUIRE_WADING_DEEPFOOTPRINT_KEY_REQUIRE_WADING_MEDIUM = _pathing.FOOTPRINT_KEY_REQUIRE_WADING_MEDIUMFOOTPRINT_KEY_REQUIRE_WADING_SHALLOW = _pathing.FOOTPRINT_KEY_REQUIRE_WADING_SHALLOWFOOTPRINT_KEY_REQUIRE_WADING_VERY_SHALLOW = _pathing.FOOTPRINT_KEY_REQUIRE_WADING_VERY_SHALLOWFOOTPRINT_KEY_DEFAULT = _pathing.FOOTPRINT_KEY_DEFAULTFOOTPRINT_DISCOURAGE_KEY_LANDINGSTRIP = _pathing.FOOTPRINT_DISCOURAGE_KEY_LANDINGSTRIPFOOTPRINT_DISCOURAGE_KEY_DEFAULT = _pathing.FOOTPRINT_DISCOURAGE_KEY_DEFAULTSPECIES_FLAG_RESERVE_INDEX = _pathing.SPECIES_FLAG_RESERVE_INDEX
class EstimatePathFlag(enum.IntFlags, export=False):
    NONE = 0
    RETURN_DISTANCE_ON_FAIL = _pathing.ESTIMATE_PATH_OPTION_RETURN_DISTANCE_ON_FAIL
    IGNORE_CONNECTIVITY_HANDLES = _pathing.ESTIMATE_PATH_OPTION_IGNORE_CONNECTIVITY_HANDLES
    RETURN_DISTANCE_FROM_FIRST_CONNECTION_FOUND = _pathing.ESTIMATE_PATH_OPTION_RETURN_DISTANCE_FROM_FIRST_CONNECTION_FOUND
    ALWAYS_RETURN_MINIMUM_DISTANCE = _pathing.ESTIMATE_PATH_OPTION_ALWAYS_RETURN_MINIMUM_DISTANCE
    ZERO_DISTANCE_IS_OPTIMAL = _pathing.ESTIMATE_PATH_OPTION_ZERO_DISTANCE_IS_OPTIMAL
    NO_NEAREST_VALID_POINT_SEARCH = _pathing.ESTIMATE_PATH_OPTION_NO_NEAREST_VALID_POINT_SEARCH

class EstimatePathResults(enum.IntFlags, export=False):
    NONE = 0
    SUCCESS = _pathing.ESTIMATE_PATH_RESULT_SUCCESS
    PATHPLANNER_NOT_INITIALIZED = _pathing.ESTIMATE_PATH_RESULT_PATHPLANNER_NOT_INITIALIZED
    START_SURFACE_INVALID = _pathing.ESTIMATE_PATH_RESULT_START_SURFACE_INVALID
    START_LOCATION_INVALID = _pathing.ESTIMATE_PATH_RESULT_START_LOCATION_INVALID
    START_LOCATION_BLOCKED = _pathing.ESTIMATE_PATH_RESULT_START_LOCATION_BLOCKED
    ALL_START_HANDLES_BLOCKED = _pathing.ESTIMATE_PATH_RESULT_ALL_START_HANDLES_BLOCKED
    GOAL_SURFACE_INVALID = _pathing.ESTIMATE_PATH_RESULT_GOAL_SURFACE_INVALID
    GOAL_LOCATION_INVALID = _pathing.ESTIMATE_PATH_RESULT_GOAL_LOCATION_INVALID
    GOAL_LOCATION_BLOCKED = _pathing.ESTIMATE_PATH_RESULT_GOAL_LOCATION_BLOCKED
    ALL_GOAL_HANDLES_BLOCKED = _pathing.ESTIMATE_PATH_RESULT_ALL_GOAL_HANDLES_BLOCKED
    NO_CONNECTIVITY = _pathing.ESTIMATE_PATH_RESULT_NO_CONNECTIVITY
    UNKNOWN_ERROR = _pathing.ESTIMATE_PATH_RESULT_UNKNOWN_ERROR
PORTAL_PLAN_LOCK = 5000PORTAL_USE_LOCK = 25000PORTAL_LOCKED_COST = 100000EstimatePathDistance_DefaultOptions = EstimatePathFlag.NONEFAKE_AGENT_RADIUS_FOR_OBJECT_ROUTING_SURFACE_VALIDATION = 0.01
class GoalType(Enum):
    Good = 0
    Bad = 1
    Failure = 2

class GoalFailureType(Enum):
    NoError = 0
    LOSBlocked = 1
    OutsideRouteableArea = 2
    IsSuppressed = 3
    OutOfWaterDepth = 4
    TerrainTagViolations = 5
    ClipsWithEdge = 6

class GoalFailureInfo:
    __slots__ = ('info', 'location', 'cost', 'validation', 'failure', 'height_clearance')

    def __init__(self, info, location=None, cost=None, validation=None, failure=None, height_clearance=None):
        self.info = info
        self.location = location
        self.cost = cost
        self.validation = GoalType.Good if validation is None else GoalType(validation)
        self.failure = GoalFailureType.NoError if failure is None else GoalFailureType(failure)
        self.height_clearance = height_clearance

    def __repr__(self):
        return '({}{}{}{}{}{})'.format(self.info, '' if self.location is None else ', {}'.format(str(self.location)), '' if self.cost is None else ', {}'.format(str(self.cost)), '' if self.validation is GoalType.Good else ', {}'.format(str(self.validation.name)), '' if self.failure is GoalFailureType.NoError else ', {}'.format(self.failure.name), '' if self.height_clearance is None else ', {}'.format(str(self.height_clearance)))

class PathNodeAction(enum.Int, export=False):
    PATH_NODE_WALK_ACTION = 0
    PATH_NODE_PORTAL_WARP_ACTION = 1
    PATH_NODE_PORTAL_WALK_ACTION = 2
    PATH_NODE_PORTAL_ANIMATE_ACTION = 3
    PATH_NODE_UNDEFINED_ACTION = 4294967295

class PathNodeTransition(enum.IntFlags, export=False):
    PATH_NODE_TRANSITION_FIRST_INDOOR = 1
    PATH_NODE_TRANSITION_LAST_INDOOR = 2

class PathNodeTerrainTransition(enum.IntFlags, export=False):
    PATH_NODE_TRANSITION_FIRST_TERRAIN = 1
    PATH_NODE_TRANSITION_LAST_TERRAIN = 2

def get_sim_extra_clearance_distance():
    extra_clearance_mult = get_default_agent_extra_clearance_multiplier()
    if extra_clearance_mult > 0.0:
        agent_radius = get_default_agent_radius()
        return agent_radius*extra_clearance_mult
    return 0.0

def get_routing_surface_at_or_below_position(position):
    for level in range(build_buy.get_highest_level_allowed(), build_buy.get_lowest_level_allowed() - 1, -1):
        if build_buy.has_floor_at_location(position, level):
            break
    return SurfaceIdentifier(services.current_zone_id(), level, SurfaceType.SURFACETYPE_WORLD)

def get_animation_routing_surface_type_param(value):
    if value == SurfaceType.SURFACETYPE_WORLD:
        return 'world'
    if value == SurfaceType.SURFACETYPE_OBJECT:
        return 'object'
    if value == SurfaceType.SURFACETYPE_POOL:
        return 'pool'
    logger.error('Failed to get ASM parameter for routing surface {}.', value)
    return ''

def get_routing_surface_asm_params(initial_routing_surface, target_routing_surface):
    return {('routingSurfaceTypeFrom', 'x'): get_animation_routing_surface_type_param(initial_routing_surface.type), ('routingSurfaceTypeTo', 'x'): get_animation_routing_surface_type_param(target_routing_surface.type)}

class Location(LocationBase):

    def __init__(self, position, orientation=None, routing_surface=None):
        if orientation is None:
            orientation = Quaternion.ZERO()
        if routing_surface is None:
            import sims4.log
            sims4.log.callstack('Routing', 'Attempting to create a location without a routing_surface.')
            routing_surface = SurfaceIdentifier(0, 0)
        super().__init__(position, orientation, routing_surface)

    def get_world_surface_location(self):
        routing_surface = SurfaceIdentifier(self.routing_surface.primary_id, self.routing_surface.secondary_id, SurfaceType.SURFACETYPE_WORLD)
        return Location(self.position, orientation=self.orientation, routing_surface=routing_surface)

class Goal(Destination):
    __slots__ = ('requires_los_check', 'path_id', 'connectivity_handle', 'path_cost', 'failure_reason', 'height_clearance')

    def __init__(self, location, cost=1.0, tag=0, group=0, requires_los_check=True, path_id=0, connectivity_handle=None, failure_reason=GoalFailureType.NoError, height_clearance=0.0):
        super().__init__(location, cost, tag, group)
        self.requires_los_check = requires_los_check
        self.path_id = path_id
        self.connectivity_handle = connectivity_handle
        self.path_cost = None
        self.failure_reason = failure_reason
        self.height_clearance = height_clearance

    def __repr__(self):
        if self.failure_reason == GoalFailureType.NoError:
            return '{}, Cost: {}'.format(self.location, self.cost)
        return '{}, Cost: {}, {}'.format(self.location, self.cost, self.failure_reason)

    def clone(self):
        new_goal = type(self)(self.location)
        self._copy_data(new_goal)
        return new_goal

    def _copy_data(self, new_goal):
        new_goal.location = self.location
        new_goal.connectivity_handle = self.connectivity_handle
        new_goal.cost = self.cost
        new_goal.tag = self.tag
        new_goal.group = self.group
        new_goal.requires_los_check = self.requires_los_check
        new_goal.failure_reason = self.failure_reason
        new_goal.height_clearance = self.height_clearance

class Path:
    PLANSTATUS_NONE = 0
    PLANSTATUS_PLANNING = 1
    PLANSTATUS_READY = 2
    PLANSTATUS_FAILED = 3

    def __init__(self, sim, route):
        if route is None:
            raise ValueError('Path has no route object')
        self.status = Path.PLANSTATUS_NONE
        self.route = route
        self.nodes = route.path
        self.start_ids = {}
        self.goal_ids = {}
        self._sim_ref = weakref.ref(sim)
        self.blended_orientation = False
        self.finished = False
        self.next_path = None
        self._portal_object_ref = None
        self.portal_id = 0
        self.force_ghost_route = False
        self.final_orientation_override = None

    def __len__(self):
        return len(self.nodes)

    def __getitem__(self, key):
        return self.nodes[key]

    def __setitem__(self, value):
        raise RuntimeError('Only route generation should be trying to modify the nodes of a path.')

    def __delitem__(self, key):
        raise RuntimeError('Only route generation should be trying to modify the nodes of a path.')

    def __iter__(self):
        return iter(self.nodes)

    def __contains__(self, item):
        return item in self.nodes

    @property
    def sim(self):
        if self._sim_ref is not None:
            return self._sim_ref()

    @property
    def selected_start(self):
        (start_id, _) = self.nodes.selected_start_tag_tuple
        return self.start_ids[start_id]

    @property
    def selected_goal(self):
        (goal_id, _) = self.nodes.selected_tag_tuple
        return self.goal_ids[goal_id]

    @property
    def start_location(self):
        if not self.nodes:
            return
        initial_node = self.nodes[0]
        location = Location(sims4.math.Vector3(*initial_node.position), sims4.math.Quaternion(*initial_node.orientation), initial_node.routing_surface_id)
        return location

    @property
    def final_location(self):
        if not self.nodes:
            return
        final_path_node = self.nodes[-1]
        location = Location(sims4.math.Vector3(*final_path_node.position), sims4.math.Quaternion(*final_path_node.orientation), final_path_node.routing_surface_id)
        return location

    @property
    def portal_obj(self):
        if self._portal_object_ref is not None:
            return self._portal_object_ref()

    @portal_obj.setter
    def portal_obj(self, value):
        if value is None:
            self._portal_object_ref = None
        elif issubclass(value.__class__, ProxyObject):
            self._portal_object_ref = value.ref()
        else:
            self._portal_object_ref = weakref.ref(value)

    def set_status(self, status):
        cur_path = self
        while cur_path is not None:
            cur_path.status = status
            cur_path = cur_path.next_path

    def add_start(self, start):
        self.start_ids[id(start)] = start
        self.nodes.add_start(start.location, start.cost, (id(start), 0))

    def add_goal(self, goal):
        self.goal_ids[id(goal)] = goal
        self.nodes.add_goal(goal.location, goal.cost, (id(goal), 0), goal.group)

    def add_waypoint(self, waypoint):
        self.nodes.add_waypoint(waypoint.location, waypoint.cost, (id(waypoint), 0), waypoint.group)

    def duration(self):
        if self.status == self.PLANSTATUS_READY:
            return self.nodes.duration
        return -1

    def length(self):
        if self.status == self.PLANSTATUS_READY:
            return self.nodes.length
        return -1

    def length_squared(self):
        if self.status == self.PLANSTATUS_READY:
            return self.nodes.length*self.nodes.length
        return -1

    def get_location_data_at_time(self, time):
        if self.nodes is None:
            return
        routing_surface = self.node_at_time(time).routing_surface_id
        translation = Vector3(*self.nodes.position_at_time(time))
        translation.y = services.terrain_service.terrain_object().get_routing_surface_height_at(translation.x, translation.z, routing_surface)
        orientation = Quaternion(*self.nodes.orientation_at_time(time, self.blended_orientation))
        return (Transform(translation, orientation), routing_surface)

    def get_location_data_along_path_gen(self, time_step=0.3, start_time=0, end_time=None):
        time = start_time
        end_time = self.duration() if end_time is None else end_time
        while time < end_time:
            (transform, routing_surface) = self.get_location_data_at_time(time)
            yield (transform, routing_surface, time)
            time += time_step

    def get_location_data_along_segment_gen(self, first_node_index, last_node_index, time_step=0.3, start_time=0, stop_time=1):
        if self.nodes is None:
            return
        first_node = self.nodes[first_node_index]
        last_node = self.nodes[last_node_index]
        first_time = first_node.time
        last_time = last_node.time
        time = sims4.math.vector_interpolate(first_time, last_time, start_time)
        end_time = sims4.math.vector_interpolate(first_time, last_time, stop_time)
        if time == end_time and end_time == 0.0:
            routing_surface = first_node.routing_surface_id
            dist = 0.0
            while True:
                while dist < 1.0:
                    pos = sims4.math.vector_interpolate(Vector3(*first_node.position), Vector3(*last_node.position), dist)
                    dist += time_step
                    yield (Transform(pos, Quaternion(*first_node.orientation)), first_node.routing_surface_id, 0.0)
        else:
            while time < end_time:
                (transform, routing_surface) = self.get_location_data_at_time(time)
                yield (transform, routing_surface, time)
                time += time_step

    def get_transition_tagged_nodes_gen(self, transition):
        for node in self:
            transitions = node.tracked_transitions
            if transitions is not None and transition in transitions:
                yield node

    def get_final_indoor_level_change_node(self):
        prev_level_index = None
        last_recorded_level_change_node = None
        for node in self:
            curr_level_index = node.routing_surface_id.secondary_id
            if prev_level_index is not None and prev_level_index is not curr_level_index:
                location = Location(Vector3(*node.position), Quaternion(*node.orientation), node.routing_surface_id)
                if is_location_in_building(location):
                    last_recorded_level_change_node = node
            else:
                transitions = node.tracked_transitions
                if PathNodeTransition.PATH_NODE_TRANSITION_FIRST_INDOOR in transitions:
                    last_recorded_level_change_node = node
            prev_level_index = curr_level_index
        return last_recorded_level_change_node

    def node_at_time(self, time):
        if self.nodes:
            return self.nodes.node_at_time(time)

    def is_route_fail(self):
        if not self.nodes:
            return True
        elif not self.nodes.plan_success:
            return True
        return False

    def add_destination_to_quad_tree(self):
        if not self.nodes:
            return
        final_location = self.final_location
        if final_location is not None:
            self.add_intended_location_to_quadtree(final_location)

    def add_intended_location_to_quadtree(self, location):
        if location is None:
            return
        self.intended_location = location
        if self.sim.location.almost_equal(location):
            return
        self.sim.add_location_to_quadtree(placement.ItemType.SIM_INTENDED_POSITION, position=location.transform.translation, orientation=location.transform.orientation, routing_surface=location.routing_surface)

    def remove_intended_location_from_quadtree(self):
        self.sim.remove_location_from_quadtree(placement.ItemType.SIM_INTENDED_POSITION)

    def remove_fake_portals(self):
        for node in self:
            if node.action == PathNodeAction.PATH_NODE_PORTAL_ANIMATE_ACTION and not (node.portal_id or node.portal_object_id):
                node.action = PathNodeAction.PATH_NODE_PORTAL_WALK_ACTION

    def get_contents_as_string(self, nodes):
        nodes_str = ''
        for node in nodes:
            node_str = 'Node{{Vector3{}, {}}} '.format(str(node.position), str(node.portal_object_id))
            nodes_str += node_str
        path_str = 'Path[{}]'.format(nodes_str)
        return path_str

class Route:
    __slots__ = ('goals', 'options', 'path', 'origins', 'waypoints')

    def __init__(self, origin, goals, waypoints=(), additional_origins=(), routing_context=None, options=None):
        if routing_context is not None:
            self.path = path_wrapper(routing_context)
        else:
            self.path = path_wrapper()
        self.origin = origin
        self.origins = additional_origins
        self.goals = goals
        self.waypoints = waypoints
        self.options = options

    @property
    def context(self):
        return self.path.context

    @context.setter
    def context(self, value):
        self.path.context = value

    @property
    def origin(self):
        return self.path.origin

    @origin.setter
    def origin(self, value):
        self.path.origin = value

def c_api_navmesh_updated_callback(navmesh_build_id):
    zone = services.current_zone()
    if zone is not None and zone.is_zone_running:
        zone.check_perform_deferred_front_door_check()

def c_api_navmesh_fence_callback(fence_id):
    zone = services.current_zone()
    if zone.is_zone_running:
        build_buy.buildbuy_session_end(zone.id)
    from objects.components.spawner_component import SpawnerInitializerSingleton
    if SpawnerInitializerSingleton is not None:
        SpawnerInitializerSingleton.spawner_spawn_objects_post_nav_mesh_load(zone.id)
