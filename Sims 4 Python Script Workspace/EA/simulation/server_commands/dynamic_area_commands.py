import build_buyimport sims4.commandsimport servicesfrom dynamic_areas.dynamic_area_enums import DynamicAreaType
@sims4.commands.Command('debug.force_block_dynamic_area', command_type=sims4.commands.CommandType.DebugOnly)
def force_block_area_type(block_id:int=0, area_type:int=0, _connection=None):
    services.dynamic_area_service().cheat_force_type_for_block(block_id, DynamicAreaType(area_type))
    for obj in list(services.object_manager(services.current_zone_id()).objects):
        obj_block_id = build_buy.get_block_id(services.current_zone_id(), obj.position, obj.level)
        if obj_block_id == block_id:
            services.dynamic_area_service().add_object(obj)
