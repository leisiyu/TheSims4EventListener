from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from protocolbuffers import FileSerialization_pb2 as serializationfrom plex.plex_enums import PlexBuildingTypefrom sims4.geometry import Polygonfrom sims4.service_manager import Serviceimport build_buyimport servicesimport sims4.loglogger = sims4.log.Logger('PlexService', default_owner='tingyul')
class PlexService(Service):

    def __init__(self):
        self._zone_to_master_map = {}

    def setup(self, gameplay_zone_data:'serialization.GameplayZoneData'=None, save_slot_data:'serialization.SaveSlotData'=None) -> 'None':
        persistence_service = services.get_persistence_service()
        for zone_data in persistence_service.zone_proto_buffs_gen():
            self.refresh_zone_to_master_map(zone_data)

    def clear_zone_to_master_map(self:'PlexService') -> 'None':
        self._zone_to_master_map.clear()

    def refresh_zone_to_master_map(self:'PlexService', zone_data:'serialization.ZoneData') -> 'None':
        master_id = zone_data.master_zone_object_data_id
        if master_id != 0:
            zone_id = zone_data.zone_id
            plex_id = zone_data.active_plex
            if not self.is_shared_plex(plex_id):
                self._zone_to_master_map[zone_id] = (master_id, plex_id)

    def is_shared_plex(self:'PlexService', plex_id:'int') -> 'bool':
        return plex_id == 300

    def is_active_zone_a_plex(self):
        return self.is_zone_a_plex(services.current_zone_id())

    def is_zone_a_plex(self, zone_id):
        return zone_id in self._zone_to_master_map

    def is_zone_matching_plex_type(self, zone_id:'int', *accepted_plex_building_types):
        return self.is_zone_a_plex(zone_id) and self.get_plex_building_type(zone_id) in accepted_plex_building_types

    def is_zone_an_apartment(self, zone_id, consider_penthouse_an_apartment=True, consider_multi_unit_an_apartment=True):
        accepted_plex_types = [PlexBuildingType.FULLY_CONTAINED_PLEX]
        if consider_penthouse_an_apartment:
            accepted_plex_types.append(PlexBuildingType.PENTHOUSE_PLEX)
            accepted_plex_types.append(PlexBuildingType.BT_PENTHOUSE_RENTAL)
        if consider_multi_unit_an_apartment:
            accepted_plex_types.append(PlexBuildingType.BT_MULTI_UNIT)
            accepted_plex_types.append(PlexBuildingType.BT_PENTHOUSE_RENTAL)
        return self.is_zone_matching_plex_type(zone_id, accepted_plex_types)

    def is_zone_a_multi_unit(self, zone_id:'int') -> 'bool':
        return self.is_zone_matching_plex_type(zone_id, PlexBuildingType.BT_MULTI_UNIT) or self.is_zone_matching_plex_type(zone_id, PlexBuildingType.BT_PENTHOUSE_RENTAL)

    def unit_count_in_lot(self, zone_id:'int') -> 'int':
        return len(self.get_plex_zones_in_group(zone_id))

    def get_active_zone_plex_id(self):
        zone_id = services.current_zone_id()
        return self.get_plex_id(zone_id)

    def get_plex_id(self, zone_id):
        if zone_id in self._zone_to_master_map:
            (_, plex_id) = self._zone_to_master_map[zone_id]
            return plex_id

    def get_master_zone_id(self, child_zone_id):
        if child_zone_id in self._zone_to_master_map:
            (master_id, _) = self._zone_to_master_map[child_zone_id]
            return master_id
        return child_zone_id

    def get_plex_building_type(self, zone_id):
        persistence_service = services.get_persistence_service()
        house_description_id = persistence_service.get_house_description_id(zone_id)
        return PlexBuildingType(services.get_building_type(house_description_id))

    def get_plex_zones_in_group(self, zone_id:'int', condition_func:'function'=lambda plex_id: True) -> 'Set[int]':
        if zone_id in self._zone_to_master_map:
            (master_id, _) = self._zone_to_master_map[zone_id]
            return frozenset(z for (z, (m, plex_id)) in self._zone_to_master_map.items() if m == master_id and condition_func(plex_id))
        return set()

    def get_shared_plex_zones_in_group(self, zone_id:'int') -> 'Set[int]':
        return self.get_plex_zones_in_group(zone_id, condition_func=self.is_shared_plex)

    def zone_to_master_map_gen(self):
        yield from self._zone_to_master_map.items()

    def get_plex_zone_at_position(self, world_position, level):
        active_zone_id = services.current_zone_id()
        if active_zone_id not in self._zone_to_master_map:
            return
        (master_id, _) = self._zone_to_master_map[active_zone_id]
        plex_id = build_buy.get_location_plex_id(world_position, level)
        for (zone_id, (other_master_id, other_plex_id)) in self._zone_to_master_map.items():
            if master_id == other_master_id and plex_id == other_plex_id:
                return zone_id

    def is_position_in_common_area_or_active_plex(self, world_position, level):
        if not services.current_zone().lot.is_position_on_lot(world_position, level):
            return False
        else:
            plex_zone_id = self.get_plex_zone_at_position(world_position, level)
            if plex_zone_id is None or plex_zone_id == services.current_zone_id():
                return True
        return False

    def get_plex_polygons(self, level):
        zone_id = services.current_zone_id()
        if zone_id not in self._zone_to_master_map:
            logger.error("Can't get polygons for a non-plex: {}", zone_id)
            return []
        (_, plex_id) = self._zone_to_master_map[zone_id]
        blocks = build_buy.get_plex_outline(plex_id, level)
        polygons = []
        for block in blocks:
            logger.assert_log(len(block) == 1, 'Plex has cutouts. get_plex_polygons needs to be updated. Zone: {}, Level: {}', zone_id, level)
            vertices = list(reversed(block[0]))
            polygon = Polygon(vertices)
            polygons.append(polygon)
        return polygons
