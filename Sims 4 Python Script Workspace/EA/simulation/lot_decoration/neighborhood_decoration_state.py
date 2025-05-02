from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from lot_decoration.decoratable_lot import DecoratableLot
    from protocolbuffers import FileSerialization_pb2 as serialization
    from typing import *from lot_decoration.decoratable_lot import DecoratableLotimport servicesimport sims4.loglogger = sims4.log.Logger('Neighborhood Decoration State', default_owner='shipark')
class NeighborhoodDecorationState:

    def __init__(self, world_id, zone_datas):
        self._zone_to_lot_decoration_data = {}
        self._world_id = world_id
        for lot_info in zone_datas:
            self._zone_to_lot_decoration_data[lot_info.zone_id] = DecoratableLot(lot_info)

    @property
    def lots(self) -> 'List[DecoratableLot]':
        return self._zone_to_lot_decoration_data.values()

    @property
    def world_id(self) -> 'int':
        return self._world_id

    def add_new_zone(self, zone_id:'int') -> 'None':
        if zone_id in self._zone_to_lot_decoration_data:
            return
        lot_info = services.get_persistence_service().get_zone_proto_buff(zone_id)
        if lot_info is None:
            logger.error('Attempting to add non-existent zone with zone id {} to neighborhood decoration state.', zone_id)
            return
        self._zone_to_lot_decoration_data[lot_info.zone_id] = DecoratableLot(lot_info)

    def remove_zone(self, zone_id:'int') -> 'None':
        if zone_id not in self._zone_to_lot_decoration_data:
            return
        del self._zone_to_lot_decoration_data[zone_id]

    def get_deco_lot_by_zone_id(self, zone_id:'int') -> 'DecoratableLot':
        return self._zone_to_lot_decoration_data[zone_id]
