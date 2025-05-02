from __future__ import annotationsimport enumfrom objects.base_object import BaseObjectfrom objects.components.types import PORTAL_COMPONENTfrom objects.game_object import GameObjectfrom objects.script_object import ScriptObjectfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from collections import namedtupleimport itertoolsimport operatorfrom native.routing.connectivity import Handlefrom objects.doors.door import Doorfrom objects.doors.door_enums import VenueFrontdoorRequirementfrom plex.plex_enums import PlexBuildingTypefrom routing.portals.portal_tuning import PortalFlagsfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableEnumFlagsfrom sims4.utils import classpropertyfrom singletons import EMPTY_SETimport persistence_error_typesimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('DoorService', default_owner='tingyul')ExteriorDoorInfo = namedtuple('ExteriorDoorInfo', ('door', 'distance', 'is_backwards'))PlexDoorInfo = namedtuple('PlexDoorInfo', ('door_id', 'zone_id', 'is_backwards'))
class PlexDoorSearchType(enum.Int, export=False):
    PLEX_EXTERIOR_DOORS = 1
    DOORS_TO_OTHER_UNITS = 2
    DOORS_OF_CURRENT_UNIT = 3
    SPECIAL_DOORS_TO_OTHER_UNITS = 4

class DoorConnectivityHandle(Handle):

    def __init__(self, location, routing_surface, *, door, is_front):
        super().__init__(location, routing_surface)
        self.door = door
        self.is_front = is_front

class DoorService(Service):
    FRONT_DOOR_ALLOWED_PORTAL_FLAGS = TunableEnumFlags(description="\n        Door Service does a routability check to all doors from the lot's\n        arrival spawn point to find doors that are reachable without crossing\n        other doors.\n        \n        These flags are supplied to the routability check's PathPlanContext, to\n        tell it what portals are usable. For example, stair portals should be\n        allowed (e.g. for front doors off the ground level, or house is on a\n        foundation).\n        ", enum_type=PortalFlags)
    FRONT_DOOR_ALLOWED_APARTMENT_PORTAL_FLAGS = TunableEnumFlags(description='\n        Additional portal flags to be used if needing to choose between\n        multiple external doors in an apartment.\n        \n        e.g. Elevator.\n        ', enum_type=PortalFlags)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._front_door_id = None
        self._plex_door_infos = {}

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_DOOR_SERVICE

    def has_front_door(self):
        return self._front_door_id is not None

    def get_front_door(self):
        return services.object_manager().get(self._front_door_id)

    def object_is_door(self, obj:'GameObject', include_special_doors:'bool'=False) -> 'bool':
        if not isinstance(obj, Door):
            return False
        elif include_special_doors or not obj.is_door_portal:
            return False
        return True

    def on_door_removed(self, door):
        if door.id == self._front_door_id:
            self._front_door_id = None

    def fix_up_doors(self, force_refresh:'bool'=False) -> 'None':
        building_type = services.get_plex_service().get_plex_building_type(services.current_zone_id())
        if building_type == PlexBuildingType.DEFAULT or building_type == PlexBuildingType.PENTHOUSE_PLEX or building_type == PlexBuildingType.COASTAL:
            has_other_unit_doors = False
            if self._plex_door_infos:
                other_unit_regular_doors = self._plex_door_infos[PlexDoorSearchType.DOORS_TO_OTHER_UNITS]
                other_unit_special_doors = self._plex_door_infos[PlexDoorSearchType.SPECIAL_DOORS_TO_OTHER_UNITS]
                has_other_unit_doors = len(other_unit_regular_doors) > 0 or len(other_unit_special_doors) > 0
            self._fix_up(force_refresh=force_refresh, reset_door_ownership=has_other_unit_doors)
        elif building_type == PlexBuildingType.FULLY_CONTAINED_PLEX:
            self._fix_up_for_apartments()
        elif building_type == PlexBuildingType.BT_MULTI_UNIT or building_type == PlexBuildingType.BT_PENTHOUSE_RENTAL:
            self._fix_up_for_multi_unit(force_refresh=force_refresh, is_apartment_or_penthouse_rental=building_type == PlexBuildingType.BT_PENTHOUSE_RENTAL)
        services.object_manager().on_front_door_candidates_changed()

    def _fix_up(self, force_refresh:'bool', reset_door_ownership:'bool'=False) -> 'None':
        (exterior_door_infos, interior_doors) = self._get_exterior_and_interior_doors(self._get_doors())
        backward_doors = set(info.door for info in exterior_door_infos if info.is_backwards)
        self._flip_backward_doors(backward_doors)
        if reset_door_ownership:
            persistence_service = services.get_persistence_service()
            hh_id = persistence_service.get_household_id_from_zone_id(services.current_zone_id())
            for obj in itertools.chain(exterior_door_infos, interior_doors):
                door = obj.door if isinstance(obj, ExteriorDoorInfo) else obj
                door.set_household_owner_id(hh_id)
                door.set_inactive_apartment_door_status(False)
        self._set_front_door_availabilities(exterior_door_infos, interior_doors)
        preferred_door_id = self._front_door_id if not force_refresh else None
        new_front_door = self._choose_front_door(exterior_door_infos, preferred_door_id=preferred_door_id)
        self.set_as_front_door(new_front_door)

    def set_as_front_door(self, door):
        if door is None and self._front_door_id is None:
            return
        if door is not None and self._front_door_id == door.id:
            return
        old_door = services.object_manager().get(self._front_door_id)
        if old_door is not None:
            old_door.set_front_door_status(False)
        self._front_door_id = None
        if door is not None:
            door.set_front_door_status(True)
            self._front_door_id = door.id

    def _flip_backward_doors(self, doors):
        for door in doors:
            door.swap_there_and_back()

    def _set_front_door_availabilities(self, exterior_door_infos, interior_doors):
        zone_requires_front_door = self._zone_requires_front_door()
        for info in exterior_door_infos:
            info.door.set_front_door_availability(zone_requires_front_door)
        for door in interior_doors:
            door.set_front_door_availability(False)

    def _zone_requires_front_door(self):
        zone = services.current_zone()
        venue = zone.venue_service.active_venue
        requires_front_door = venue.venue_requires_front_door
        if requires_front_door == VenueFrontdoorRequirement.NEVER:
            return False
        if requires_front_door == VenueFrontdoorRequirement.ALWAYS:
            return True
        if requires_front_door == VenueFrontdoorRequirement.OWNED_OR_RENTED:
            if services.travel_group_manager().is_current_zone_rented():
                return True
            return zone.lot.zone_owner_household_id != 0
        logger.error('Current venue {} at Zone {} has front door requirement set to invalid value: {}', venue, zone, requires_front_door, owner='trevor')
        return False

    def _choose_front_door(self, exterior_door_infos, preferred_door_id=None):
        if not self._zone_requires_front_door():
            return
        if preferred_door_id is not None:
            for info in exterior_door_infos:
                if info.door.id == preferred_door_id:
                    return info.door
        if not exterior_door_infos:
            return
        info = min(exterior_door_infos, key=operator.attrgetter('distance'))
        return info.door

    def _get_doors(self, include_special_doors:'bool'=False) -> 'bool':
        doors = frozenset(obj for obj in services.object_manager().values() if self.object_is_door(obj, include_special_doors=include_special_doors))
        return doors

    def _get_arrival_point(self):
        zone = services.current_zone()
        spawn_point = zone.active_lot_arrival_spawn_point
        if spawn_point is not None:
            return spawn_point.get_approximate_center()
        logger.error('Active lot missing lot arrival spawn points. This will cause incorrect front door behavior.', zone.lot.lot_id)
        return zone.lot.corners[1]

    def _get_exterior_and_interior_doors(self, doors_to_test:'set[ScriptObject]', is_apartment_or_penthouse_rental:'bool'=False, doors_to_unlock:'set[ScriptObject]'=None, doors_to_lock:'set[ScriptObject]'=None) -> '(frozenset[ExteriorDoorInfo], frozenset[ScriptObject])':
        connections = self._get_door_connections_from_arrival(doors_to_test, is_apartment_or_penthouse_rental=is_apartment_or_penthouse_rental, specify_doors_to_unlock=doors_to_unlock, specify_doors_to_lock=doors_to_lock)
        exterior_door_to_infos = {}
        for (_, handle, distance) in connections:
            old_info = exterior_door_to_infos.get(handle.door)
            if old_info is not None and not handle.is_front:
                pass
            else:
                is_backwards = not handle.is_front
                info = ExteriorDoorInfo(door=handle.door, distance=distance, is_backwards=is_backwards)
                exterior_door_to_infos[handle.door] = info
        interior_doors = frozenset(door for door in doors_to_test if door not in exterior_door_to_infos)
        return (frozenset(exterior_door_to_infos.values()), interior_doors)

    def _get_door_connections_from_arrival(self, doors:'set[BaseObject]', is_apartment_or_penthouse_rental:'bool'=False, specify_doors_to_unlock:'set[BaseObject]'=None, specify_doors_to_lock:'set[BaseObject]'=None):
        zone = services.current_zone()
        source_point = self._get_arrival_point()
        source_handles = set()
        source_handle = Handle(source_point, routing.SurfaceIdentifier(zone.id, 0, routing.SurfaceType.SURFACETYPE_WORLD))
        source_handles.add(source_handle)
        routing_context = routing.PathPlanContext()
        if specify_doors_to_unlock is not None:
            for door in specify_doors_to_unlock:
                for portal_handle in door.get_portal_pairs():
                    routing_context.unlock_portal(portal_handle.there)
                    routing_context.unlock_portal(portal_handle.back)
        doors_to_lock = doors if specify_doors_to_lock is None else specify_doors_to_lock
        for door in doors_to_lock:
            for portal_handle in door.get_portal_pairs():
                routing_context.lock_portal(portal_handle.there)
                routing_context.lock_portal(portal_handle.back)
        routing_context.set_key_mask(routing.FOOTPRINT_KEY_ON_LOT | routing.FOOTPRINT_KEY_OFF_LOT)
        if is_apartment_or_penthouse_rental:
            routing_context.set_portal_key_mask(DoorService.FRONT_DOOR_ALLOWED_PORTAL_FLAGS | DoorService.FRONT_DOOR_ALLOWED_APARTMENT_PORTAL_FLAGS)
        else:
            routing_context.set_portal_key_mask(DoorService.FRONT_DOOR_ALLOWED_PORTAL_FLAGS)
        dest_handles = set()
        for door in doors:
            (front_position, back_position) = door.get_door_positions()
            if not front_position is None:
                if back_position is None:
                    pass
                else:
                    dest_handles.add(DoorConnectivityHandle(front_position, door.routing_surface, door=door, is_front=True))
                    dest_handles.add(DoorConnectivityHandle(back_position, door.routing_surface, door=door, is_front=False))
        connections = ()
        if dest_handles:
            connections = routing.estimate_path_batch(source_handles, dest_handles, routing_context=routing_context)
            if connections is None:
                connections = ()
        return connections

    def _fix_up_for_apartments(self):
        plex_door_infos = self.get_plex_door_infos(force_refresh=True)
        backward_doors = set()
        active_zone_id = services.current_zone_id()
        object_manager = services.object_manager()
        plex_doors = []
        for info in plex_door_infos:
            household_id = services.get_persistence_service().get_household_id_from_zone_id(info.zone_id)
            door = object_manager.get(info.door_id)
            if door is None:
                logger.error('Plex Door {} does not exist.', info.door_id, owner='rmccord')
            else:
                if info.is_backwards:
                    backward_doors.add(door)
                    current_zone = services.current_zone()
                    lot = current_zone.lot
                    world_description_id = services.get_world_description_id(current_zone.world_id)
                    lot_description_id = services.get_lot_description_id(lot.lot_id, world_description_id)
                    neighborhood_id = current_zone.neighborhood_id
                    neighborhood_data = services.get_persistence_service().get_neighborhood_proto_buff(neighborhood_id)
                    logger.error('For WB: An apartment door facing the common area needs to be flipped. Lot desc id: {}, World desc id: {}. Neighborhood id: {}, Neighborhood Name: {}', lot_description_id, world_description_id, neighborhood_id, neighborhood_data.name)
                door.set_household_owner_id(household_id)
                if info.zone_id == active_zone_id:
                    plex_doors.append(door)
                else:
                    door.set_inactive_apartment_door_status(True)
        self._flip_backward_doors(backward_doors)
        if not plex_doors:
            return
        if len(plex_doors) == 1:
            self.set_as_front_door(plex_doors[0])
            return
        logger.warn("plex zone_id: {} has multiple potential front doors: {}, can lead to sims able to access areas they shouldn't", active_zone_id, plex_doors)
        best_door = None
        best_distance = None
        connections = self._get_door_connections_from_arrival(plex_doors, is_apartment_or_penthouse_rental=True)
        for (_, handle, distance) in connections:
            if not best_distance is None:
                if best_distance < distance:
                    best_door = handle.door
                    best_distance = distance
            best_door = handle.door
            best_distance = distance
        if best_door is None:
            logger.error('Unable to route to plex doors in zone_id: {} potential doors: {}', active_zone_id, plex_doors)
            self.set_as_front_door(plex_doors[0])
            return
        self.set_as_front_door(best_door)

    def _fix_up_for_multi_unit(self, force_refresh:'bool', is_apartment_or_penthouse_rental:'bool'=False) -> 'None':
        door_infos_for_other_units = self.get_plex_door_infos(force_refresh=True, plex_door_search_type=PlexDoorSearchType.DOORS_TO_OTHER_UNITS)
        door_infos_for_current_unit = self.get_plex_door_infos(plex_door_search_type=PlexDoorSearchType.DOORS_OF_CURRENT_UNIT)
        special_door_infos_for_other_units = self.get_plex_door_infos(plex_door_search_type=PlexDoorSearchType.SPECIAL_DOORS_TO_OTHER_UNITS)
        if door_infos_for_current_unit or services.get_plex_service().unit_count_in_lot(services.current_zone_id()) == 1:
            self._fix_up(force_refresh=True, reset_door_ownership=True)
            return
        object_manager = services.object_manager()
        persistence_service = services.get_persistence_service()
        doors_for_current_zone = set(self._get_doors(include_special_doors=True))
        normal_doors_for_current_zone = set()
        normal_doors_for_current_unit = set()

        def _fixup_inactive_unit_door(door_info:'PlexDoorInfo', need_back_spawn_point:'bool') -> 'None':
            door = object_manager.get(door_info.door_id)
            if door is None:
                logger.error('Plex Door {} does not exist.', door_info.door_id, owner='rmccord')
                return
            if door_info.is_backwards:
                door.swap_there_and_back()
            doors_for_current_zone.remove(door)
            household_id = persistence_service.get_household_id_from_zone_id(door_info.zone_id)
            door.set_household_owner_id(household_id)
            door.set_inactive_apartment_door_status(True, need_back_spawn_point=need_back_spawn_point)
            if door.is_door_portal:
                door.set_front_door_availability(False)

        inactive_units_exterior_doors = self._get_inactive_units_exterior_doors(door_infos_for_other_units)
        for info in itertools.chain(door_infos_for_other_units, special_door_infos_for_other_units):
            door = object_manager.get(info.door_id)
            is_door_connect_to_outside = door in inactive_units_exterior_doors
            _fixup_inactive_unit_door(info, is_door_connect_to_outside)
        current_zone_id = services.current_zone_id()
        hh_id = persistence_service.get_household_id_from_zone_id(current_zone_id)
        for door in doors_for_current_zone:
            door.set_household_owner_id(hh_id)
            door.set_inactive_apartment_door_status(False)
            if door.is_door_portal:
                normal_doors_for_current_zone.add(door)
        backward_doors = set()
        for info in door_infos_for_current_unit:
            door = object_manager.get(info.door_id)
            if door is None:
                logger.error('Plex Door {} does not exist.', info.door_id, owner='rmccord')
            else:
                if info.is_backwards:
                    backward_doors.add(door)
                normal_doors_for_current_unit.add(door)
        self._flip_backward_doors(backward_doors)
        self._set_multiunit_front_door(force_refresh, normal_doors_for_current_zone, normal_doors_for_current_unit, is_apartment_or_penthouse_rental)

    def _set_multiunit_front_door(self, force_refresh:'bool', doors_for_current_zone:'set[Door]', doors_for_current_unit:'set[Door]', is_apartment_or_penthouse_rental:'bool'=False) -> 'None':
        (building_exterior_door_infos, building_interior_doors) = self._get_exterior_and_interior_doors(doors_for_current_zone)
        (unit_exterior_door_infos, _) = self._get_exterior_and_interior_doors(doors_for_current_unit, is_apartment_or_penthouse_rental=is_apartment_or_penthouse_rental, doors_to_unlock=doors_for_current_zone, doors_to_lock=doors_for_current_unit)
        doors_available_for_front_door = [info.door.id for info in unit_exterior_door_infos]
        doors_not_available_for_front_door = set()
        for door in doors_for_current_zone:
            if door.id not in doors_available_for_front_door:
                doors_not_available_for_front_door.add(door)
        self._set_front_door_availabilities(unit_exterior_door_infos, doors_not_available_for_front_door)
        preferred_door_id = self._front_door_id if not force_refresh else None
        building_and_unit_exterior_door = set(building_exterior_door_infos).intersection(unit_exterior_door_infos)
        if len(building_and_unit_exterior_door) > 0:
            front_door_candidates = building_and_unit_exterior_door
        else:
            front_door_candidates = unit_exterior_door_infos
        new_front_door = self._choose_front_door(front_door_candidates, preferred_door_id=preferred_door_id)
        self.set_as_front_door(new_front_door)

    def _get_inactive_units_exterior_doors(self, door_infos_for_other_units:'set[PlexDoorInfo]') -> 'set[ScriptObject]':
        object_manager = services.object_manager()
        door_for_other_unit = set()
        for info in door_infos_for_other_units:
            door = object_manager.get(info.door_id)
            if door is None:
                logger.error('Plex Door {} does not exist.', info.door_id, owner='yecao')
            else:
                door_for_other_unit.add(door)
        (other_unit_exterior_doors_info, _) = self._get_exterior_and_interior_doors(door_for_other_unit)
        other_unit_exterior_doors = set()
        for info in other_unit_exterior_doors_info:
            other_unit_exterior_doors.add(info.door)
        return other_unit_exterior_doors

    def unlock_all_doors(self):
        doors = self._get_doors()
        for door in doors:
            door.remove_locks()

    def get_plex_door_search_type(self, zone_id:'int') -> 'int':
        plex_building_type = services.get_plex_service().get_plex_building_type(zone_id)
        if plex_building_type == PlexBuildingType.BT_MULTI_UNIT:
            return PlexDoorSearchType.DOORS_TO_OTHER_UNITS
        else:
            return PlexDoorSearchType.PLEX_EXTERIOR_DOORS

    def get_plex_door_infos(self, force_refresh:'bool'=False, plex_door_search_type:'int'=PlexDoorSearchType.PLEX_EXTERIOR_DOORS) -> 'Set[PlexDoorInfo]':
        if self._plex_door_infos and not force_refresh:
            return self._plex_door_infos[plex_door_search_type]
        current_zone_id = services.current_zone_id()
        plex_service = services.get_plex_service()
        doors = self._get_doors(include_special_doors=True)
        plex_exterior_doors = set()
        doors_to_other_units = set()
        special_doors_to_other_unit = set()
        doors_in_current_unit = set()
        for door in doors:
            (front_position, back_position) = door.get_door_positions()
            if front_position is None or back_position is None:
                logger.error("Door '{}' has broken portals.", door)
            else:
                front_zone_id = plex_service.get_plex_zone_at_position(front_position, door.level)
                back_zone_id = plex_service.get_plex_zone_at_position(back_position, door.level)
                plex_exterior_door_info = self._get_plex_exterior_door(front_zone_id, back_zone_id, door.id)
                if plex_exterior_door_info and door.is_door_portal:
                    plex_exterior_doors.add(plex_exterior_door_info)
                other_units_door_info = self._get_other_units_door(front_zone_id, back_zone_id, current_zone_id, door.id)
                if other_units_door_info:
                    if door.is_door_portal:
                        doors_to_other_units.add(other_units_door_info)
                    else:
                        special_doors_to_other_unit.add(other_units_door_info)
                current_unit_door_info = self._get_doors_in_current_unit(front_zone_id, back_zone_id, current_zone_id, door.id)
                if current_unit_door_info and door.is_door_portal:
                    doors_in_current_unit.add(current_unit_door_info)
        plex_door_infos = {PlexDoorSearchType.SPECIAL_DOORS_TO_OTHER_UNITS: frozenset(special_doors_to_other_unit), PlexDoorSearchType.DOORS_OF_CURRENT_UNIT: frozenset(doors_in_current_unit), PlexDoorSearchType.DOORS_TO_OTHER_UNITS: frozenset(doors_to_other_units), PlexDoorSearchType.PLEX_EXTERIOR_DOORS: frozenset(plex_exterior_doors)}
        self._plex_door_infos = plex_door_infos
        return self._plex_door_infos[plex_door_search_type]

    def get_plex_info_for_door_id(self, door_id:'int') -> 'Optional[PlexDoorInfo]':
        for search_type in PlexDoorSearchType:
            infos = self.get_plex_door_infos(plex_door_search_type=search_type)
            for info in infos:
                if info.door_id == door_id:
                    return info

    def _get_plex_exterior_door(self, front_zone_id:'int', back_zone_id:'int', door_id:'int') -> 'PlexDoorInfo':
        if front_zone_id == back_zone_id:
            return
        zone_id = front_zone_id or back_zone_id
        is_backwards = front_zone_id is not None
        plex_exterior_door_info = PlexDoorInfo(door_id=door_id, zone_id=zone_id, is_backwards=is_backwards)
        return plex_exterior_door_info

    def _get_other_units_door(self, front_zone_id:'int', back_zone_id:'int', current_zone_id:'int', door_id:'int'):
        if front_zone_id and front_zone_id != current_zone_id:
            zone_id = front_zone_id
        elif back_zone_id and back_zone_id != current_zone_id:
            zone_id = back_zone_id
        else:
            return
        is_backwards = front_zone_id is not None and back_zone_id is None
        info = PlexDoorInfo(door_id=door_id, zone_id=zone_id, is_backwards=is_backwards)
        return info

    def _get_doors_in_current_unit(self, front_zone_id:'int', back_zone_id:'int', current_zone_id:'int', door_id:'int') -> 'PlexDoorInfo':
        if front_zone_id != current_zone_id and back_zone_id != current_zone_id:
            return
        info = PlexDoorInfo(door_id=door_id, zone_id=front_zone_id, is_backwards=back_zone_id != current_zone_id)
        return info

    def save(self, zone_data=None, **kwargs):
        if self._front_door_id is not None:
            zone_data.front_door_id = self._front_door_id

    def load(self, zone_data=None):
        for door in self._get_doors():
            door.set_front_door_status(False)
            door.set_front_door_availability(False)
            door.set_inactive_apartment_door_status(False)
        if zone_data is not None and zone_data.HasField('front_door_id'):
            door = services.object_manager().get(zone_data.front_door_id)
            if door is not None:
                self.set_as_front_door(door)
