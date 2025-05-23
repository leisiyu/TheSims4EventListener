from __future__ import annotationsfrom event_testing.test_events import TestEventfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from routing import Location, SurfaceIdentifier
    from routing.path_planner.path_plan_context import PathPlanContextWrapper
    from sims4.math import Vector3
    from typing import *
    from sims.household import Householdfrom contextlib import contextmanagerfrom indexed_manager import ObjectIDErrorfrom business.business_enums import BusinessTypefrom objects import ALL_HIDDEN_REASONSfrom objects.components.inventory_enums import InventoryTypefrom objects.object_enums import ItemLocationimport id_generatorimport objectsimport protocolbuffers.FileSerialization_pb2 as file_serializationfrom protocolbuffers import FileSerialization_pb2, SimObjectAttributes_pb2from sims4.callback_utils import CallableListfrom sims4.log import Loggerimport enumimport pythonutilsimport sims4.reloadimport sims4.utilsimport routingimport servicesimport venuesfrom objects.gallery_tuning import ContentSourcefrom event_testing import test_eventsfrom event_testing.event_data_const import SimoleonDatafrom dynamic_areas.dynamic_area_enums import DynamicAreaTypewith sims4.reload.protected(globals()):
    _build_buy_enter_callbacks = CallableList()
    _build_buy_exit_callbacks = CallableList()
class ObjectOriginLocation(enum.Int, export=False):
    UNKNOWN = 0
    ON_LOT = 1
    SIM_INVENTORY = 2
    HOUSEHOLD_INVENTORY = 3
    OBJECT_INVENTORY = 4
    LANDING_STRIP = 5

class FloorFeatureType(enum.Int):
    BURNT = 0
    LEAF = 1
    DUST = 2
try:
    import _buildbuy
except ImportError:

    class _buildbuy:

        @staticmethod
        def get_wall_contours(*_, **__):
            return []

        @staticmethod
        def update_object_attributes(*_, **__):
            pass

        @staticmethod
        def test_location_for_object(*_, **__):
            pass

        @staticmethod
        def get_object_slotset(*_, **__):
            pass

        @staticmethod
        def get_object_placement_flags(*_, **__):
            pass

        @staticmethod
        def get_object_buy_category_flags(*_, **__):
            pass

        @staticmethod
        def get_block_id(*_, **__):
            pass

        @staticmethod
        def get_room_id(*_, **__):
            pass

        @staticmethod
        def get_user_in_bb(*_, **__):
            pass

        @staticmethod
        def init_bb_force_exit(*_, **__):
            pass

        @staticmethod
        def bb_force_exit(*_, **__):
            pass

        @staticmethod
        def get_object_decosize(*_, **__):
            pass

        @staticmethod
        def get_object_catalog_name(*_, **__):
            pass

        @staticmethod
        def get_object_catalog_description(*_, **__):
            pass

        @staticmethod
        def get_object_is_deletable(*_, **__):
            pass

        @staticmethod
        def get_object_can_depreciate(*_, **__):
            pass

        @staticmethod
        def get_household_inventory_value(*_, **__):
            pass

        @staticmethod
        def get_object_has_tag(*_, **__):
            pass

        @staticmethod
        def get_object_all_tags(*_, **__):
            pass

        @staticmethod
        def get_current_venue(*_, **__):
            pass

        @staticmethod
        def get_current_venue_config(*_, **__):
            pass

        @staticmethod
        def get_current_venue_owner_id(*_, **__):
            pass

        @staticmethod
        def update_gameplay_unlocked_products(*_, **__):
            pass

        @staticmethod
        def has_floor_feature(*_, **__):
            pass

        @staticmethod
        def get_floor_feature(*_, **__):
            pass

        @staticmethod
        def set_floor_feature(*_, **__):
            pass

        @staticmethod
        def begin_update_floor_features(*_, **__):
            pass

        @staticmethod
        def end_update_floor_features(*_, **__):
            pass

        @staticmethod
        def find_floor_feature(*_, **__):
            pass

        @staticmethod
        def scan_floor_features(*_, **__):
            pass

        @staticmethod
        def get_variant_group_id(*_, **__):
            pass

        @staticmethod
        def get_replacement_object(*_, **__):
            pass

        @staticmethod
        def is_household_inventory_available(household_id):
            return True

        @staticmethod
        def get_lowest_level_allowed(*_, **__):
            return -2

        @staticmethod
        def get_highest_level_allowed(*_, **__):
            return 4

        @staticmethod
        def get_object_pack_by_key(*_, **__):
            return 0

        @staticmethod
        def load_conditional_objects(*_, **__):
            return (True, tuple())

        @staticmethod
        def mark_conditional_objects_loaded(*_, **__):
            pass

        @staticmethod
        def set_client_conditional_layer_active(*_, **__):
            pass

        @staticmethod
        def conditional_layer_destroyed(*_, **__):
            pass

        @staticmethod
        def request_season_weather_interpolation(*_, **__):
            pass

        @staticmethod
        def set_active_lot_decoration(*_, **__):
            pass

        @staticmethod
        def get_active_lot_decoration(*_, **__):
            pass

        @staticmethod
        def get_venue_tier(*_, **__):
            pass

        @staticmethod
        def get_gig_objects_added(zone_id):
            pass

        @staticmethod
        def get_gig_objects_deleted(zone_id):
            pass

        @staticmethod
        def get_gig_tags_added(*_, **__):
            pass

        @staticmethod
        def get_gig_tags_removed(*_, **__):
            pass

        @staticmethod
        def get_gig_tag_changes(*_, **__):
            pass

        @staticmethod
        def get_object_or_style_has_tag(object_def_guid, tag):
            pass

        @staticmethod
        def get_object_and_style_all_tags(object_def_guid):
            pass

        @staticmethod
        def set_venue_owner_id(zone_id, household_id):
            pass
logger = Logger('BuildBuy')
def remove_floor_feature(ff_type, pos, surface):
    zone_id = services.current_zone_id()
    set_floor_feature(zone_id, ff_type, pos, surface, 0)

def remove_object_from_buildbuy_system(obj_id, persist=True):
    _buildbuy.remove_object_from_buildbuy_system(obj_id, services.current_zone_id(), persist)
get_wall_contours = _buildbuy.get_wall_contoursupdate_object_attributes = _buildbuy.update_object_attributestest_location_for_object = _buildbuy.test_location_for_objectget_object_slotset = _buildbuy.get_object_slotsetget_block_id = _buildbuy.get_block_idget_room_id = _buildbuy.get_room_idget_user_in_build_buy = _buildbuy.get_user_in_bbinit_build_buy_force_exit = _buildbuy.init_bb_force_exitbuild_buy_force_exit = _buildbuy.bb_force_exitget_object_decosize = _buildbuy.get_object_decosizeget_object_catalog_name = _buildbuy.get_object_catalog_nameget_object_catalog_description = _buildbuy.get_object_catalog_descriptionget_object_is_deletable = _buildbuy.get_object_is_deletableget_object_can_depreciate = _buildbuy.get_object_can_depreciateget_household_inventory_value = _buildbuy.get_household_inventory_valueget_object_has_tag = _buildbuy.get_object_has_tagget_object_all_tags = _buildbuy.get_object_all_tagsget_current_venue_config = _buildbuy.get_current_venue_configget_current_venue_owner_id = _buildbuy.get_current_venue_owner_idupdate_gameplay_unlocked_products = _buildbuy.update_gameplay_unlocked_productshas_floor_feature = _buildbuy.has_floor_featureget_floor_feature = _buildbuy.get_floor_featureset_floor_feature = _buildbuy.set_floor_featurebegin_update_floor_features = _buildbuy.begin_update_floor_featuresend_update_floor_features = _buildbuy.end_update_floor_featuresfind_floor_feature = _buildbuy.find_floor_featurescan_floor_features = _buildbuy.scan_floor_featuresget_replacement_object = _buildbuy.get_replacement_objectget_lowest_level_allowed = _buildbuy.get_lowest_level_allowedget_highest_level_allowed = _buildbuy.get_highest_level_allowedget_object_pack_by_key = _buildbuy.get_object_pack_by_keyload_conditional_objects = _buildbuy.load_conditional_objectsmark_conditional_objects_loaded = _buildbuy.mark_conditional_objects_loadedset_client_conditional_layer_active = _buildbuy.set_client_conditional_layer_activeget_variant_group_id = _buildbuy.get_variant_group_idconditional_layer_destroyed = _buildbuy.conditional_layer_destroyedis_household_inventory_available = _buildbuy.is_household_inventory_availablerequest_season_weather_interpolation = _buildbuy.request_season_weather_interpolationset_active_lot_decoration = _buildbuy.set_active_lot_decorationget_active_lot_decoration = _buildbuy.get_active_lot_decorationget_venue_tier = _buildbuy.get_venue_tierget_gig_objects_added = _buildbuy.get_gig_objects_addedget_gig_objects_deleted = _buildbuy.get_gig_objects_deletedget_gig_tags_removed = _buildbuy.get_gig_tags_removedget_gig_tags_added = _buildbuy.get_gig_tags_addedget_gig_tag_changes = _buildbuy.get_gig_tag_changesget_object_or_style_has_tag = _buildbuy.get_object_or_style_has_tagget_object_and_style_all_tags = _buildbuy.get_object_and_style_all_tags
def get_current_venue(zone_id, allow_ineligible=False):
    return _buildbuy.get_current_venue(services.get_plex_service().get_master_zone_id(zone_id), allow_ineligible)

def register_build_buy_enter_callback(callback):
    _build_buy_enter_callbacks.register(callback)

def unregister_build_buy_enter_callback(callback):
    _build_buy_enter_callbacks.unregister(callback)

def register_build_buy_exit_callback(callback):
    _build_buy_exit_callbacks.register(callback)

def unregister_build_buy_exit_callback(callback):
    _build_buy_exit_callbacks.unregister(callback)

class HouseholdInventoryFlags(enum.IntFlags):
    FORCE_OWNERSHIP = 1
    DESTROY_OBJECT = 2

def copy_objectdata_to_household_inventory(obj_data:'FileSerialization_pb2.ObjectData', household:'Household') -> 'bool':
    def_id = get_vetted_object_defn_guid(obj_data.object_id, obj_data.guid or obj_data.type)
    if def_id is None:
        return False
    placement_flags = get_object_placement_flags(def_id)
    if PlacementFlags.NON_INVENTORYABLE in placement_flags:
        return False
    definition = services.definition_manager().get(def_id)
    if definition.cls._components.inventory_item is not None and definition.cls._components.inventory_item._tuned_values.always_destroy_on_inventory_transfer:
        return False
    if definition.cls._components.consumable is not None and definition.cls._component.consumable._tuned_values.allow_destruction_on_inventory_transfer:
        return False
    count = 1
    attribute_data = SimObjectAttributes_pb2.PersistenceMaster()
    attribute_data.ParseFromString(obj_data.attributes)
    from crafting.crafting_tunable import CraftingTuning
    for persistable_data in attribute_data.data:
        if persistable_data.type == persistable_data.InventoryItemComponent:
            data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableInventoryItemComponent.persistable_data]
            count = data.stack_count
            data.stack_count = 1
            data.inventory_type = InventoryType.UNDEFINED
            obj_data.attributes = attribute_data.SerializeToString()
        if persistable_data.type == persistable_data.StatisticComponent:
            statistics_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableStatisticsTracker.persistable_data].statistics
            statistic_guid = CraftingTuning.SERVINGS_STATISTIC.guid64
            for statistic in statistics_data:
                if statistic.name_hash == statistic_guid:
                    return False
    household_id = household.id
    if is_household_inventory_available(household_id):
        zone_id = services.current_zone_id()
        try:
            _buildbuy.copy_objectdata_to_household_inventory(obj_data, household_id, zone_id, household.account.id, count)
        except KeyError as e:
            logger.error('Failed to copy ObjectData {} to {} inventory. Exception: {}', obj_data.id, household, e, owner='nabaker')
            return False
        except:
            return False
    else:
        household_msg = services.get_persistence_service().get_household_proto_buff(household_id)
        if household_msg is not None:
            for i in range(count):
                new_object_data = FileSerialization_pb2.ObjectData()
                new_object_data.MergeFrom(obj_data)
                if i != 0:
                    new_object_data.object_id = id_generator.generate_object_id()
                household_msg.inventory.objects.append(new_object_data)
        else:
            return False
    return True

def move_object_to_household_inventory(obj, failure_flags=0, object_location_type=ObjectOriginLocation.ON_LOT):
    placement_flags = get_object_placement_flags(obj.definition.id)
    if PlacementFlags.NON_INVENTORYABLE in placement_flags:
        obj.destroy(cause="Can't add non inventoriable objects to household inventory.")
        return False
    else:
        household_id = obj.get_household_owner_id()
        active_household = services.active_household()
        household = services.household_manager().get(household_id)
        if household_id is None or household is None:
            if failure_flags & HouseholdInventoryFlags.FORCE_OWNERSHIP:
                household_id = active_household.id
                household = active_household
                obj.set_household_owner_id(household_id)
            else:
                if failure_flags & HouseholdInventoryFlags.DESTROY_OBJECT:
                    obj.destroy(cause="Can't add unowned objects to household inventory.")
                    return False
                return False
    return False
    obj.on_hovertip_requested()
    obj.new_in_inventory = True
    obj.remove_reference_from_parent()
    stack_count = obj.stack_count()
    obj.set_stack_count(1)
    if is_household_inventory_available(household_id):
        zone_id = services.current_zone_id()
        try:
            _buildbuy.add_object_to_household_inventory(obj.id, household_id, zone_id, household.account.id, object_location_type, stack_count)
        except KeyError as e:
            logger.error('Failed to add {} to {} inventory. Object Origin Location: {}. Exception: {}', obj, household, object_location_type, e, owner='manus')
            return False
    else:
        household_msg = services.get_persistence_service().get_household_proto_buff(household_id)
        if household_msg is not None:
            for i in range(stack_count):
                object_data = obj.save_object(household_msg.inventory.objects)
                if object_data is not None and i != 0:
                    object_data.object_id = id_generator.generate_object_id()
            obj.destroy(cause='Add to household inventory')
        else:
            return False
    return True

def has_any_objects_in_household_inventory(object_list, household_id):
    household = services.household_manager().get(household_id)
    zone_id = services.current_zone_id()
    _buildbuy.has_any_objects_in_household_inventory(object_list, household_id, zone_id, household.account.id)

def find_objects_in_household_inventory(definition_ids, household_id):
    return _buildbuy.find_objects_in_household_inventory(definition_ids, household_id)

def remove_object_from_household_inventory(object_id, household, update_funds=True):
    zone_id = services.current_zone_id()
    return _buildbuy.remove_object_from_household_inventory(object_id, household.id, zone_id, household.account.id, update_funds)

def object_exists_in_household_inventory(object_id, household_id):
    return _buildbuy.object_exists_in_household_inventory(object_id, household_id)

def get_object_ids_in_household_inventory(household_id):
    if is_household_inventory_available(household_id):
        return _buildbuy.get_object_ids_in_household_inventory(household_id)
    else:
        household_msg = services.get_persistence_service().get_household_proto_buff(household_id)
        if household_msg is not None and household_msg.inventory:
            return [object_data.object_id for object_data in household_msg.inventory.objects]

def get_object_data_from_household_inventory(object_id, household_id):
    if is_household_inventory_available(household_id):
        object_data_raw = _buildbuy.get_object_data_in_household_inventory(object_id, household_id)
        if object_data_raw is None:
            return
        object_data = FileSerialization_pb2.ObjectData()
        object_data.ParseFromString(object_data_raw)
        if object_data is not None:
            return object_data
    else:
        household_msg = services.get_persistence_service().get_household_proto_buff(household_id)
        if household_msg.inventory:
            for object_data in household_msg.inventory.objects:
                if object_data.object_id == object_id:
                    return object_data

def get_definition_id_in_household_inventory(object_id, household_id):
    object_data = get_object_data_from_household_inventory(object_id, household_id)
    if object_data is not None:
        return (get_vetted_object_defn_guid(object_id, object_data.guid), object_data)
    return (None, None)

def get_object_in_household_inventory(object_id, household_id):

    def make_object(object_data):
        def_id = get_vetted_object_defn_guid(object_id, object_data.guid)
        definition = services.definition_manager().get(def_id, obj_state=object_data.state_index)

        class HouseholdInventoryObject(definition.cls):

            @property
            def persistence_group(self):
                return objects.persistence_groups.PersistenceGroups.NONE

            @persistence_group.setter
            def persistence_group(self, value):
                pass

            def save_object(self, object_list, *args, item_location=objects.object_enums.ItemLocation.ON_LOT, container_id=0, **kwargs):
                pass

            @property
            def is_valid_posture_graph_object(self):
                return False

        try:
            obj = objects.system.create_object(object_data.guid, cls_override=HouseholdInventoryObject, obj_id=object_id, obj_state=object_data.state_index, loc_type=ItemLocation.HOUSEHOLD_INVENTORY, content_source=ContentSource.HOUSEHOLD_INVENTORY_PROXY)
            obj.append_tags(objects.object_manager.ObjectManager.HOUSEHOLD_INVENTORY_OBJECT_TAGS)
            obj.attributes = object_data.SerializeToString()
            obj.set_household_owner_id(household_id)
        except ObjectIDError as exc:
            obj = services.object_manager().get(object_id)
            if obj is None:
                logger.error('Failed to create or find proxy object for Household Inventory object {}\n{}', object_id, exc)
        return obj

    object_data = get_object_data_from_household_inventory(object_id, household_id)
    if object_data is not None:
        return make_object(object_data)

def is_location_outside(position, level):
    return _buildbuy.is_location_outside(services.current_zone_id(), position, level)

def is_location_natural_ground(position, level):
    return _buildbuy.is_location_natural_ground(services.current_zone_id(), position, level)

def has_floor_at_location(position, level):
    return _buildbuy.has_floor_at_location(services.current_zone_id(), position, level)

def is_location_pool(position, level):
    return _buildbuy.is_location_pool(services.current_zone_id(), position, level)

def generate_lot_waypoints(zone_id:'int', plex_id:'int', num_waypoints:'int', sim_location:'Location', routing_surface:'SurfaceIdentifier', outside_only:'bool', routing_context:'PathPlanContextWrapper', ignore_objects:'Optional[bool]'=None) -> 'Optional[Dict[int, List[Vector3]]]':
    return _buildbuy.generate_lot_waypoints(zone_id, plex_id, num_waypoints, sim_location, routing_surface, outside_only, routing_context, ignore_objects)

def get_pool_size_at_location(position, level):
    return _buildbuy.get_pool_size_at_location(services.current_zone_id(), position, level)

def get_pool_edges():
    return _buildbuy.get_pool_edges(services.current_zone_id())

def get_all_block_polygons(plex_id):
    return _buildbuy.get_all_block_polygons(services.current_zone_id(), plex_id)

def get_pool_polys(pool_block_id, level):
    return _buildbuy.get_pool_polys(pool_block_id, services.current_zone_id(), level)

def get_pond_id(position):
    return _buildbuy.get_pond_id(services.current_zone_id(), position)

def get_pond_edges(pond_id):
    edges = _buildbuy.get_pond_edges(services.current_zone_id())
    return edges.get((pond_id,))

def get_pond_contours_for_wading_depth(pond_id, min_depth, max_depth, routing_surface):
    contours = _buildbuy.get_pond_contours_for_wading_depth(pond_id, min_depth, max_depth, routing_surface)
    return contours

def get_location_plex_id(position, level):
    return _buildbuy.get_location_plex_id(services.current_zone_id(), position, level)

def get_plex_outline(plex_id, level):
    return _buildbuy.get_plex_outline(services.current_zone_id(), plex_id, level)

def get_plex_tile_count(zone_id:'int', plex_id:'int', house_description_id:'int') -> 'int':
    return _buildbuy.get_plex_tile_count(zone_id, plex_id, house_description_id)

def set_plex_visibility(plex_id, is_visible):
    return _buildbuy.set_plex_visibility(services.current_zone_id(), plex_id, is_visible)

def get_vetted_object_defn_guid(obj_id, definition_id):
    return _buildbuy.get_vetted_object_defn_guid(services.current_zone_id(), obj_id, definition_id)

def add_object_to_buildbuy_system(obj_id):
    return _buildbuy.add_object_to_buildbuy_system(obj_id, services.current_zone_id())

def invalidate_object_location(obj_id):
    return _buildbuy.invalidate_object_location(obj_id, services.current_zone_id())

def get_stair_count(obj_id):
    return _buildbuy.get_stair_count(obj_id, services.current_zone_id())

def get_portal_height_offset_threshold():
    return _buildbuy.get_portal_height_offset_threshold()

def list_floor_features(terrain_feature):
    return _buildbuy.list_floor_features(services.current_zone_id(), terrain_feature)

def get_lot_value(zone_id:'int', is_furnished:'bool') -> 'Tuple(int)':
    return _buildbuy.get_furnished_lot_value(zone_id, is_furnished)

def disown_household_objects(zone_id:'int', house_desc_id:'int') -> 'None':
    return _buildbuy.disown_household_objects(zone_id, house_desc_id)

def clear_venue_owner(current_zone_id:'int', household_id:'int') -> 'bool':
    return _buildbuy.clear_venue_owner(current_zone_id, household_id)

def set_venue_owner_id(zone_id:'int', household_id:'int') -> 'bool':
    return _buildbuy.set_venue_owner_id(zone_id, household_id)

def __reload__(old_module_vars):
    pass

class BuyCategory(enum.IntFlags):
    UNUSED = 1
    APPLIANCES = 2
    ELECTRONICS = 4
    ENTERTAINMENT = 8
    UNUSED_2 = 16
    LIGHTING = 32
    PLUMBING = 64
    DECOR = 128
    KIDS = 256
    STORAGE = 512
    COMFORT = 2048
    SURFACE = 4096
    VEHICLE = 8192
    DEFAULT = 2147483648

class PlacementFlags(enum.IntFlags, export=False):
    CENTER_ON_WALL = 1
    EDGE_AGAINST_WALL = 2
    ADJUST_HEIGHT_ON_WALL = 4
    CEILING = 8
    IMMOVABLE_BY_USER = 16
    DIAGONAL = 32
    ROOF = 64
    REQUIRES_FENCE = 128
    SHOW_OBJ_IF_WALL_DOWN = 256
    SLOTTED_TO_FENCE = 512
    REQUIRES_SLOT = 1024
    ALLOWED_ON_SLOPE = 2048
    REPEAT_PLACEMENT = 4096
    NON_DELETEABLE = 8192
    NON_INVENTORYABLE = 16384
    NON_ABANDONABLE = 32768
    REQUIRES_TERRAIN = 65536
    ENCOURAGE_INDOOR = 131072
    ENCOURAGE_OUTDOOR = 262144
    NON_DELETABLE_BY_USER = 524288
    NON_INVENTORYABLE_BY_USER = 1048576
    REQUIRES_WATER_SURFACE = 2097152
    ALLOWED_IN_FOUNTAIN = 4194304
    GROUNDED_AGAINST_WALL = 8388608
    NOT_BLUEPRINTABLE = 16777216
    IS_HUMAN = 33554432
    ALLOWED_ON_WATER_SURFACE = 67108864
    ALLOWED_IN_POOL = 134217728
    ON_WALL_TOP = 268435456
    FORCE_DESIGNABLE = 536870912
    ALWAYS_BLUEPRINTABLE = 1073741824
    WALL_OPTIONAL = 2147483648
    REQUIRES_WALL = CENTER_ON_WALL | EDGE_AGAINST_WALL
    WALL_GRAPH_PLACEMENT = REQUIRES_WALL | REQUIRES_FENCE
    SNAP_TO_WALL = REQUIRES_WALL | ADJUST_HEIGHT_ON_WALL
BUILD_BUY_OBJECT_LEAK_DISABLED = 'in build buy'WALL_OBJECT_POSITION_PADDING = 0.25
def get_object_placement_flags(*args, **kwargs):
    return PlacementFlags(_buildbuy.get_object_placement_flags(*args, **kwargs))

def get_object_buy_category_flags(*args, **kwargs):
    return BuyCategory(_buildbuy.get_object_buy_category_flags(*args, **kwargs))

def get_all_objects_with_flags_gen(objs, buy_category_flags):
    for obj in objs:
        if not get_object_buy_category_flags(obj.definition.id) & buy_category_flags:
            pass
        else:
            yield obj

@sims4.utils.exception_protected
def c_api_wall_contour_update(zone_id, wall_type):
    if wall_type == 0 or wall_type == 2:
        services.get_zone(zone_id).wall_contour_update_callbacks()

@sims4.utils.exception_protected
def c_api_foundation_and_level_height_update(zone_id):
    services.get_zone(zone_id).foundation_and_level_height_update_callbacks()

@sims4.utils.exception_protected
def c_api_navmesh_update(zone_id):
    pass

@sims4.utils.exception_protected
def c_api_modify_household_funds(amount:'int', household_id:'int', reason, zone_id:'int'):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is not None and business_manager.business_type != BusinessType.RENTAL_UNIT and business_manager.business_type != BusinessType.SMALL_BUSINESS:
        business_manager.modify_funds(amount, from_item_sold=False)
        return True
    household_manager = services.household_manager()
    household = household_manager.get(household_id)
    if household is None:
        if household_manager.try_add_pending_household_funds(household_id, amount, reason):
            return True
        logger.error('Invalid Household id {} when attempting to modify household funds.', household_id)
        return False
    if household.is_active_household:
        for sim in household.instanced_sims_gen():
            career_tracker = sim.career_tracker
            if not career_tracker is None:
                if not career_tracker.careers:
                    pass
                else:
                    for career in career_tracker:
                        gig = career.get_current_gig()
                        if gig is None:
                            pass
                        else:
                            customer_zone_id = gig.get_customer_lot_id()
                            if not customer_zone_id is None:
                                if customer_zone_id != zone_id:
                                    pass
                                elif not hasattr(gig, 'update_budget_spent'):
                                    pass
                                else:
                                    gig.update_budget_spent(amount)
                                    return True
                            elif amount > 0:
                                household.funds.add(amount, reason, count_as_earnings=False)
                                services.get_event_manager().process_events_for_household(test_events.TestEvent.SimoleonsEarnedBB, household, simoleon_data_type=SimoleonData.TotalMoneyEarned, amount=amount)
                            elif amount < 0:
                                return household.funds.try_remove(-amount, reason)
    if amount > 0:
        household.funds.add(amount, reason, count_as_earnings=False)
        services.get_event_manager().process_events_for_household(test_events.TestEvent.SimoleonsEarnedBB, household, simoleon_data_type=SimoleonData.TotalMoneyEarned, amount=amount)
    elif amount < 0:
        return household.funds.try_remove(-amount, reason)
    return True

@sims4.utils.exception_protected
def c_api_buildbuy_session_begin(zone_id:'int', account_id:'int'):
    current_zone = services.current_zone()
    posture_graph_service = current_zone.posture_graph_service
    posture_graph_service.on_enter_buildbuy()
    current_zone.on_build_buy_enter()
    object_leak_tracker = services.get_object_leak_tracker()
    if object_leak_tracker is not None:
        object_leak_tracker.add_disable_reason(BUILD_BUY_OBJECT_LEAK_DISABLED)
    resource_keys = []
    if services.get_career_service().get_career_event_situation_is_running():
        household = services.active_household()
    else:
        household = current_zone.get_active_lot_owner_household()
    if household is not None:
        for unlock in household.build_buy_unlocks:
            resource_keys.append(unlock)
    update_gameplay_unlocked_products(resource_keys, zone_id, account_id)
    services.business_service().on_build_buy_enter()
    services.get_reset_and_delete_service().on_build_buy_enter()
    services.utilities_manager().on_build_buy_enter()
    services.unique_object_service().on_build_buy_enter()
    services.object_manager(zone_id).cleanup_build_buy_transient_objects()
    _build_buy_enter_callbacks()
    return True

def _sync_venue_service_to_zone_venue_type(zone_id, from_bb_venue_changed=False):
    active_venue_tuning_id = get_current_venue(zone_id)
    logger.assert_raise(active_venue_tuning_id is not None, ' Venue is None in buildbuy for zone id:{}', zone_id, owner='shouse')
    raw_active_venue_tuning_id = get_current_venue(zone_id, allow_ineligible=True)
    logger.assert_raise(raw_active_venue_tuning_id is not None, ' Raw Venue is None in buildbuy for zone id:{}', zone_id, owner='shouse')
    if active_venue_tuning_id is None or not raw_active_venue_tuning_id is None:
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        active_venue_tuning = venue_manager.get(active_venue_tuning_id)
        raw_active_venue_tuning = venue_manager.get(raw_active_venue_tuning_id)
        source_venue_tuning = venues.venue_service.VenueService.get_variable_venue_source_venue(raw_active_venue_tuning)
        services.current_zone().venue_service.on_change_venue_type_at_runtime(active_venue_tuning, source_venue_tuning, force_start_situations=from_bb_venue_changed)
        return True
    return False

@sims4.utils.exception_protected
def buildbuy_session_end(zone_id):
    services.object_manager(zone_id).rebuild_objects_to_ignore_portal_validation_cache()
    for obj in services.object_manager(zone_id).get_all():
        obj.on_buildbuy_exit()
    posture_graph_service = services.current_zone().posture_graph_service
    posture_graph_service.on_exit_buildbuy()
    _build_buy_exit_callbacks()
    pythonutils.try_highwater_gc()
    services.get_zone_modifier_service().check_for_and_apply_new_zone_modifiers(zone_id)
    if _sync_venue_service_to_zone_venue_type(zone_id):
        zone_director = services.venue_service().get_zone_director()
        if zone_director is not None:
            zone_director.on_exit_buildbuy()
    object_preference_tracker = services.object_preference_tracker(disable_overrides=True)
    if object_preference_tracker is not None:
        object_preference_tracker.validate_objects(zone_id)
    services.business_service().on_build_buy_exit()
    services.current_zone().on_build_buy_exit()
    services.utilities_manager().on_build_buy_exit()
    services.get_reset_and_delete_service().on_build_buy_exit()
    street_service = services.street_service()
    if street_service is not None:
        street = services.current_street()
        if street is not None:
            provider = street_service.get_provider(street)
            if provider is not None:
                provider.on_build_buy_exit()
    event_service = services.multi_unit_event_service()
    if event_service is not None:
        event_service.on_build_buy_exit()
    services.object_manager().clear_objects_to_ignore_portal_validation_cache()

@sims4.utils.exception_protected
def c_api_buildbuy_venue_type_changed(zone_id):
    _sync_venue_service_to_zone_venue_type(zone_id, from_bb_venue_changed=True)
    services.venue_game_service().on_sub_venue_finished_loading()

@sims4.utils.exception_protected
def c_api_buildbuy_session_end(zone_id:'int', account_id:'int', zone_data_change:'int') -> 'bool':
    if zone_data_change:
        on_zone_data_change()
    zone = services.get_zone(zone_id)
    fence_id = zone.get_current_fence_id_and_increment()
    routing.flush_planner(False)
    routing.add_fence(fence_id)
    object_leak_tracker = services.get_object_leak_tracker()
    if object_leak_tracker is not None:
        object_leak_tracker.remove_disable_reason(BUILD_BUY_OBJECT_LEAK_DISABLED)
    return True

def on_zone_data_change() -> 'None':
    persistence_service = services.get_persistence_service()
    plex_service = services.get_plex_service()
    business_service = services.business_service()
    lot_decoration_service = services.lot_decoration_service()
    updated_zones = persistence_service.get_save_game_data_proto().zones
    existing_zone_ids = persistence_service.get_zone_ids()
    new_zone_ids = set()
    persistence_service.clear_zone_data_pb_cache()
    plex_service.clear_zone_to_master_map()
    for zone in updated_zones:
        if zone.zone_id in existing_zone_ids:
            existing_zone_ids.remove(zone.zone_id)
        else:
            new_zone_ids.add(zone.zone_id)
        persistence_service.refresh_zone_data_pb_cache(zone)
        plex_service.refresh_zone_to_master_map(zone)
    current_zone_id = services.current_zone_id()
    business_service.on_multi_unit_zone_change(get_current_venue_owner_id(current_zone_id), new_zone_ids, existing_zone_ids)
    if lot_decoration_service is not None:
        lot_decoration_service.on_multi_unit_zone_change(new_zone_ids, existing_zone_ids)
    zone_manager = services.get_zone_manager()
    for zone_id in existing_zone_ids:
        if zone_id in zone_manager:
            zone_manager.remove_id(zone_id)
    zone_manager.build_buy_zones_changed = False

@sims4.utils.exception_protected
def c_api_buildbuy_zones_changed(added_or_modified_zone_ids, removed_zoneids={}, pendingZoneToDelete=0):
    if not services.current_zone().is_in_build_buy:
        on_zone_data_change()
    else:
        zone_manager = services.get_zone_manager()
        zone_manager.build_buy_zones_changed = True
    return True

@sims4.utils.exception_protected
def c_api_buildbuy_dynamic_areas_changed(dynamic_areas:'List[Tuple[int, List[int], List[int]]]'):
    services.dynamic_area_service().clear_all_areas()
    changed_by_player = False
    for (area_type, blocks, area_objects) in dynamic_areas:
        if area_type != DynamicAreaType.BUSINESS_PUBLIC:
            changed_by_player = True
        services.dynamic_area_service().create_area(DynamicAreaType(area_type), blocks)
    services.dynamic_area_service().update_all_objects()
    if changed_by_player:
        services.get_event_manager().process_event(TestEvent.DynamicAreaChanged)
    return True

@sims4.utils.exception_protected
def c_api_buildbuy_get_save_object_data(zone_id:'int', obj_id:'int'):
    obj = services.get_zone(zone_id).find_object(obj_id)
    if obj is None:
        return
    object_list = file_serialization.ObjectList()
    save_data = obj.save_object(object_list.objects, from_bb=True)
    return save_data

@sims4.utils.exception_protected
def c_api_buildbuy_lot_traits_changed(zone_id:'int'):
    pass

@sims4.utils.exception_protected
def c_api_house_inv_obj_added(zone_id, household_id, obj_id, obj_def_id):
    household = services.household_manager().get(household_id)
    if household is None:
        current_zone = services.current_zone()
        logger.error('Invalid Household with id: {} when being notified object (id: {} def id: {}) has been added to household inventory. IsZoneLoading:{} ', household_id, obj_id, obj_def_id, current_zone.is_zone_loading)
        return
    collection_tracker = household.collection_tracker
    collection_tracker.check_add_collection_item(household, obj_id, obj_def_id)
    animal_service = services.animal_service()
    if animal_service is not None:
        if animal_service.is_registered_home(obj_id):
            animal_service.on_home_added(obj_id)
        elif obj_id in animal_service.animal_assignment_map:
            animal_service.on_animal_added(obj_id)

@sims4.utils.exception_protected
def c_api_house_inv_obj_removed(zone_id, household_id, obj_id, obj_def_id):
    animal_service = services.animal_service()
    if animal_service is not None:
        if animal_service.is_registered_home(obj_id):
            animal_service.on_home_destroyed(obj_id)
        elif obj_id in animal_service.animal_assignment_map:
            animal_service.on_animal_destroyed(obj_id)

@sims4.utils.exception_protected
def c_api_set_object_location(zone_id, obj_id, routing_surface, transform):
    obj = services.object_manager().get(obj_id)
    if obj is None:
        logger.error('Trying to place an invalid object id: {}', obj_id, owner='camilogarcia')
        return
    obj.move_to(routing_surface=routing_surface, transform=transform)

@sims4.utils.exception_protected
def c_api_set_object_location_ex(zone_id, obj_id, routing_surface, transform, parent_id, parent_type_info, slot_hash):
    obj = services.get_zone(zone_id).find_object(obj_id)
    if obj is None:
        return
    parent = services.object_manager().get(parent_id) if parent_id else None
    obj.parent_type_info = parent_type_info
    obj.set_parent(parent, transform=transform, slot_hash=slot_hash, routing_surface=routing_surface)

@sims4.utils.exception_protected
def c_api_reset_sims_to_landing_strip(zone_id):
    for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
        sim.fgl_reset_to_landing_strip()

@sims4.utils.exception_protected
def c_api_on_apply_blueprint_lot_begin(zone_id):
    for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
        sim.fgl_reset_to_landing_strip()
    from objects.components.mannequin_component import set_mannequin_group_sharing_mode, MannequinGroupSharingMode
    set_mannequin_group_sharing_mode(MannequinGroupSharingMode.ACCEPT_THEIRS)

@sims4.utils.exception_protected
def c_api_on_apply_blueprint_lot_end(zone_id):
    from objects.components.mannequin_component import set_mannequin_group_sharing_mode, MannequinGroupSharingMode
    set_mannequin_group_sharing_mode(MannequinGroupSharingMode.ACCEPT_MERGED)

@sims4.utils.exception_protected
def c_api_on_lot_clearing_begin(zone_id):
    zone = services.get_zone(zone_id)
    zone.on_active_lot_clearing_begin()

@sims4.utils.exception_protected
def c_api_on_lot_clearing_end(zone_id):
    zone = services.get_zone(zone_id)
    zone.on_active_lot_clearing_end()

@contextmanager
def floor_feature_update_context(*args, **kwargs):
    try:
        begin_update_floor_features(*args, **kwargs)
        yield None
    finally:
        end_update_floor_features(*args, **kwargs)

@sims4.utils.exception_protected
def c_api_buildbuy_get_mannequin(mannequin_id):
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        mannequin_data = persistence_service.get_mannequin_proto_buff(mannequin_id)
        if mannequin_data is not None:
            return mannequin_data.SerializeToString()

@sims4.utils.exception_protected
def c_api_buildbuy_delete_mannequin(mannequin_id):
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        persistence_service.del_mannequin_proto_buff(mannequin_id)

@sims4.utils.exception_protected
def c_api_buildbuy_update_mannequin(mannequin_id, mannequin_data):
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        persistence_service.del_mannequin_proto_buff(mannequin_id)
        sim_info_data_proto = persistence_service.add_mannequin_proto_buff()
        sim_info_data_proto.ParseFromString(mannequin_data)
