from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesplex_info_schema = GsiGridSchema(label='Plex Info', auto_refresh=False)plex_info_schema.add_field('neighborhood', label='Neighborhood', unique_field=True)plex_info_schema.add_field('master_zone_id', label='Master Zone ID')plex_info_schema.add_field('cur_lot', label='Current Lot', width=0.4)with plex_info_schema.add_has_many('plex_info', GsiGridSchema, label='Detailed Plex Info') as sub_schema:
    sub_schema.add_field('plex_id', label='Plex ID')
    sub_schema.add_field('zone_id', label='Zone ID')
    sub_schema.add_field('plex_type', label='Plex Type')
    sub_schema.add_field('current_active', label='Current Active')
@GsiHandler('plex_info', plex_info_schema)
def generate_plex_info_data(*args, zone_id:int=None, **kwargs):
    plex_infos = []
    plex_service = services.get_plex_service()
    persistence_service = services.get_persistence_service()
    current_zone_id = services.current_zone_id()
    current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
    master_zone_map = {}
    for (zone_id, (master_id, plex_id)) in plex_service.zone_to_master_map_gen():
        if master_id not in master_zone_map:
            neighborhood_name = persistence_service.get_neighborhood_proto_buf_from_zone_id(zone_id).name
            is_current_lot = master_id == current_master_zone_id
            cur_info = {'neighborhood': neighborhood_name, 'master_zone_id': hex(master_id) + ' | ' + str(master_id), 'cur_lot': 'X' if is_current_lot else '', 'plex_info': None}
        else:
            cur_info = master_zone_map[master_id]
        plex_info_entry = []
        if cur_info['plex_info'] is not None:
            plex_info_entry = cur_info['plex_info']
        is_current_active_zone = zone_id == current_zone_id
        plex_info_entry.append({'plex_id': plex_id, 'zone_id': hex(zone_id) + ' | ' + str(zone_id), 'plex_type': plex_service.get_plex_building_type(zone_id).name, 'current_active': 'X' if is_current_active_zone else ''})
        cur_info['plex_info'] = plex_info_entry
        master_zone_map[master_id] = cur_info
    for (_, info) in master_zone_map.items():
        plex_infos.append(info)
    return plex_infos
