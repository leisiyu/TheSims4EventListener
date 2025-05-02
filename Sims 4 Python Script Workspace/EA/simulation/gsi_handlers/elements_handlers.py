from __future__ import annotationsfrom TimelineHandleArchiver import timeline_archiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from TimelineHandleArchiver import TimelineHandleSnapshot, TimelineHandleArchive
    from elements import Element
    from scheduling import ElementHandle
    from scheduling import Timeline
    from typing import *
def build_schema(schema:'GsiGridSchema') -> 'None':
    schema.add_field('handle_id', label='Handle ID')
    schema.add_field('is_scheduled', label='Is Scheduled?')
    schema.add_field('scheduled_time', label='Scheduled Time')
    schema.add_field('element_type', label='Element Type')
    schema.add_field('num_changes', label='Change Count')
    with schema.add_has_many('element_data', GsiGridSchema, label='Current Element Data') as sub_schema:
        sub_schema.add_field('name', label='Name')
        sub_schema.add_field('value', label='Value')
    with schema.add_has_many('changes', GsiGridSchema, label='Changes') as sub_schema:
        sub_schema.add_field('change_index', label='Change Index')
        sub_schema.add_field('old', label='Old Value')
        sub_schema.add_field('new', label='New Value')
        sub_schema.add_field('call_stack', label='Call Stack')
    with schema.add_has_many('element_call_stack', GsiGridSchema, label='Element Stack') as sub_schema:
        sub_schema.add_field('sort_order', label='Sort Order')
        sub_schema.add_field('stack_handle_id', label='Handle ID')
        sub_schema.add_field('repr', label='Data')
timeline_active_handles_schema = GsiGridSchema(label='Sim Timeline/Active Handles', auto_refresh=False)build_schema(timeline_active_handles_schema)timeline_active_handles_schema.add_field('sorted_index', label='Sorted Index')timeline_all_handles_schema = GsiGridSchema(label='Sim Timeline/All Handles', auto_refresh=False)build_schema(timeline_all_handles_schema)
@GsiHandler('timeline_handles', timeline_all_handles_schema)
def generate_all_handles() -> 'Optional[List[Dict[str, Any]]]':
    if not timeline_archiver.enabled:
        return
    time_service = services.time_service()
    if time_service is None:
        return
    sim_timeline = time_service.sim_timeline
    if sim_timeline is None:
        return
    handles_data = []
    snapshot_archive = sim_timeline.handle_archiver.id_to_snapshot_archive
    for current_id in snapshot_archive.keys():
        handles_data.append(build_handle_data(sim_timeline, current_id))
    return handles_data

@GsiHandler('timeline_active_handles', timeline_active_handles_schema)
def generate_active_handles() -> 'Optional[List[Dict[str, Any]]]':
    if not timeline_archiver.enabled:
        return
    time_service = services.time_service()
    if time_service is None:
        return
    sim_timeline = time_service.sim_timeline
    if sim_timeline is None:
        return
    handles_data = []
    for (idx, handle) in enumerate(sorted(list(sim_timeline.heap))):
        handle_data = build_handle_data(sim_timeline, handle.ix)
        handle_data['sorted_index'] = idx
        handles_data.append(handle_data)
    return handles_data

def build_handle_data(timeline:'Timeline', handle_id:'int') -> 'Dict[str, Any]':
    handle_archives = timeline.handle_archiver
    current_archive = handle_archives.id_to_snapshot_archive.get(handle_id, None)
    if current_archive is None:
        current_handle_id = handle_archives.get_current_id(handle_id)
        handle_data = build_handle_data(timeline, current_handle_id)
        handle_data['handle_id'] = f'{handle_id} -> {current_handle_id}'
        return handle_data
    delta_data = []
    for (idx, entry) in enumerate(current_archive):
        old_value = current_archive[idx - 1] if idx > 0 else ''
        delta_data.append({'change_index': str(idx), 'old': str(old_value), 'new': str(entry), 'call_stack': entry.call_stack})
    most_recent_snapshot = current_archive[-1]
    handle_data = {'handle_id': handle_id, 'is_scheduled': str(most_recent_snapshot.is_scheduled), 'scheduled_time': str(most_recent_snapshot.when), 'changes': delta_data, 'num_changes': len(delta_data), 'element_call_stack': build_stack(handle_id, handle_archives)}
    active_handle = next((i for i in timeline.heap if most_recent_snapshot.id == i.ix), None)
    if active_handle is not None and active_handle.element is not None:
        element = active_handle.element
        handle_data['element_type'] = type(element).__name__
        handle_data['element_data'] = build_element_data(element)
    else:
        handle_data['element_type'] = 'None'
        handle_data['element_data'] = []
    return handle_data

def build_element_data(element:'Element') -> 'List[Dict[str, str]]':
    if element is None:
        return []
    data = []
    element_dir = dir(element)
    for attribute_name in element_dir:
        if callable(getattr(element, attribute_name)):
            pass
        else:
            data.append({'name': attribute_name, 'value': str(getattr(element, attribute_name))})
    return data

def build_stack(target_id:'int', handle_archive:'TimelineHandleArchive') -> 'List[Dict[str, str]]':
    output = []
    current_handle = handle_archive.id_to_snapshot_archive[target_id][-1]
    while current_handle is not None:
        output.append({'sort_order': len(output), 'stack_handle_id': current_handle.id, 'repr': repr(current_handle)})
        current_handle = current_handle.parent_snapshot
    return output
