import servicesimport sims4from objects.components.spawner_component_enums import SpawnerTypefrom objects.components.types import SPAWNER_COMPONENTfrom server_commands.argument_helpers import RequiredTargetParam
@sims4.commands.Command('spawners.force_spawn_objects')
def force_spawn_objects(_connection=None):
    for obj in services.object_manager().get_all_objects_with_component_gen(SPAWNER_COMPONENT):
        obj.force_spawn_object()

@sims4.commands.Command('spawners.slot_spawn')
def force_spawn_slot_objects(obj_id:RequiredTargetParam, _connection=None):
    obj = obj_id.get_target()
    if obj is None or obj.spawner_component is None:
        return
    empty_slot_count = sum(1 for runtime_slot in obj.get_runtime_slots_gen() if runtime_slot.empty)
    obj.force_spawn_object(spawn_type=SpawnerType.SLOT, ignore_firemeter=True, create_slot_obj_count=empty_slot_count)
