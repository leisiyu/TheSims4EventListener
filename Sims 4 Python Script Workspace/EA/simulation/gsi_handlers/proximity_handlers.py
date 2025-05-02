import servicesfrom objects.components.types import PROXIMITY_COMPONENTfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaproximity_schema = GsiGridSchema(label='Proximity')proximity_schema.add_field('buff_name', label='Buff Name', width=2)proximity_schema.add_field('object_id', label='Object Id', width=1)proximity_schema.add_field('object_name', label='Object Name', width=2)proximity_schema.add_view_cheat('debugvis.proximity.start', label='Start Visualization')proximity_schema.add_view_cheat('debugvis.proximity.stop', label='Stop Visualization')with proximity_schema.add_has_many('affected_sims', GsiGridSchema, label='Affected Sims') as sub_schema:
    sub_schema.add_field('sim_id', label='Sim Id', width=1)
    sub_schema.add_field('sim_name', label='Sim Name', width=2)
@GsiHandler('proximity_view', proximity_schema)
def generate_proximity_view_data():
    proximity_data = []
    all_objects = list(services.object_manager().objects)
    for obj in all_objects:
        obj_proximity_component = obj.get_component(PROXIMITY_COMPONENT)
        if obj_proximity_component is None:
            pass
        else:
            obj_buff_data = {}
            for (sim_id, buff_handles) in obj_proximity_component.active_buff_handles.items():
                sim_info = services.sim_info_manager().get(sim_id)
                if not sim_info is None:
                    if sim_info.Buffs is None:
                        pass
                    else:
                        sim_data = {'sim_id': str(hex(sim_id)), 'sim_name': sim_info.full_name}
                        for handle in buff_handles:
                            buff_type = sim_info.Buffs.get_buff_type(handle)
                            buff_name = buff_type.__name__
                            if buff_name in obj_buff_data:
                                obj_buff_data[buff_name]['affected_sims'].append(sim_data)
                            else:
                                buff_data = {'buff_name': buff_name, 'object_id': str(hex(obj.id)), 'object_name': str(obj), 'affected_sims': [sim_data]}
                                obj_buff_data[buff_name] = buff_data
            for (_, buff_data) in obj_buff_data.items():
                proximity_data.append(buff_data)
    return proximity_data
