from gsi_handlers.gameplay_archiver import GameplayArchiverfrom objects.object_enums import ObjectRoutingBehaviorTrackingCategoryfrom routing.object_routing.object_routing_priority import ObjectRoutingPriorityfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport gsi_handlersimport servicesobject_routing_schema = GsiGridSchema(label='Object Routing')object_routing_schema.add_field('tracking_category', label='Tracking Category')with object_routing_schema.add_has_many('active_objects', GsiGridSchema) as active_objects_schema:
    active_objects_schema.add_field('objId', label='Object Id', width=3, unique_field=True)
    active_objects_schema.add_field('classStr', label='Class', width=3)
    active_objects_schema.add_field('definitionStr', label='Definition', width=3)
@GsiHandler('object_routing_view', object_routing_schema)
def generate_object_routing_view():
    categories = []
    routing_service = services.get_object_routing_service()
    if routing_service:
        for tracking_category in ObjectRoutingBehaviorTrackingCategory:
            if tracking_category is not ObjectRoutingBehaviorTrackingCategory.NONE:
                objects = []
                object_refs = routing_service.get_active_routing_object_set(tracking_category)
                for obj in object_refs:
                    class_str = gsi_handlers.gsi_utils.format_object_name(obj)
                    definition_str = str(obj.definition.name)
                    object_dict = {'objId': hex(obj.id), 'classStr': class_str, 'definitionStr': definition_str}
                    objects.append(object_dict)
                category_dict = {'tracking_category': tracking_category.name, 'active_objects': objects}
                categories.append(category_dict)
    return categories
object_routing_queue_log_schema = GsiGridSchema(label='Object Routing Queue Log')object_routing_queue_log_schema.add_field('obj_id', label='Object Id', width=0.25)object_routing_queue_log_schema.add_field('obj_name', label='Object Name', width=0.5)object_routing_queue_log_schema.add_field('class_str', label='Class', width=0.5)object_routing_queue_log_schema.add_field('priority_str', label='Priority', width=0.5)object_routing_queue_log_schema.add_field('last_route_timestamp', label='Last Route', type=GsiFieldVisualizers.TIME, width=0.25)object_routing_queue_log_schema.add_field('sleep_duration_str', label='Sleep Duration', width=0.25)object_routing_queue_log_schema.add_field('routing_behavior_str', label='Routing Behavior', width=0.5)object_routing_queue_log_schema.add_field('sim_time', label='Sim Time', type=GsiFieldVisualizers.STRING)object_routing_queue_log_archiver = GameplayArchiver('object_routing_queue_log_archiver', object_routing_queue_log_schema, enable_archive_by_default=True, max_records=100)
def generate_object_routing_queue_log(data=None):
    if data is not None:
        entry = {'obj_id': data['obj_id'], 'obj_name': data['obj_name'], 'class_str': data['class_str'], 'priority_str': data['priority_str'], 'last_route_timestamp': data['last_route_timestamp'], 'sleep_duration_str': data['sleep_duration_str'], 'routing_behavior_str': data['routing_behavior_str'], 'sim_time': str(services.time_service().sim_now)}
        object_routing_queue_log_archiver.archive(data=entry)
object_routing_queue_schema = GsiGridSchema(label='Object Routing Queue')object_routing_queue_schema.add_field('index', label='Sort Position', width=0.15)object_routing_queue_schema.add_field('obj_id', label='Object Id', width=0.25)object_routing_queue_schema.add_field('obj_name', label='Object Name', width=0.5)object_routing_queue_schema.add_field('class_str', label='Class', width=0.5)object_routing_queue_schema.add_field('priority_str', label='Priority', width=0.5)object_routing_queue_schema.add_field('last_route_timestamp', label='Last Route', type=GsiFieldVisualizers.TIME, width=0.25)object_routing_queue_schema.add_field('sleep_duration_str', label='Sleep Duration', width=0.25)object_routing_queue_schema.add_field('is_routing', label='Is Routing', width=0.15)object_routing_queue_schema.add_field('routing_behavior_str', label='Routing Behavior', width=0.5)with object_routing_queue_schema.add_view_cheat('objects.focus_camera_on_object', label='Focus On Selected Object') as cheat:
    cheat.add_token_param('obj_id')
def _get_object_routing_priority_string(priority, promoted):
    priority_str = '{} ({})'.format(priority, ObjectRoutingPriority.get_priority_value_string(priority))
    if promoted:
        priority_str += ' (Promoted)'
    return priority_str

@GsiHandler('object_routing_queue_view', object_routing_queue_schema)
def generate_object_routing_view():
    entries = []
    object_routing_service = services.get_object_routing_service()
    if not object_routing_service:
        return entries
    objects = object_routing_service.get_sorted_objects()
    index = 0
    for obj in objects:
        behavior = obj.get_object_routing_behavior()
        routing_behavior_str = None if behavior is None else type(behavior).__name__
        promoted_priority = object_routing_service.get_object_promoted_routing_priority(obj)
        if promoted_priority is not None:
            priority_str = _get_object_routing_priority_string(promoted_priority, True)
        else:
            base_priority = obj.get_object_routing_priority()
            priority_str = _get_object_routing_priority_string(base_priority, False)
        sleep_duration_str = None
        last_sleep_timestamp = object_routing_service.get_object_last_sleep_timestamp(obj)
        if last_sleep_timestamp is not None:
            time_delta = services.time_service().sim_now - last_sleep_timestamp
            sleep_duration_str = '{:.2f} minutes'.format(time_delta.in_minutes())
        is_routing = object_routing_service.has_routing_reservation(obj)
        queue_entry_dict = {'index': index, 'obj_id': hex(obj.id), 'obj_name': obj.custom_name if obj.has_custom_name() else obj.catalog_name, 'class_str': gsi_handlers.gsi_utils.format_object_name(obj), 'priority_str': priority_str, 'last_route_timestamp': str(object_routing_service.get_object_last_route_timestamp(obj)), 'sleep_duration_str': sleep_duration_str, 'is_routing': is_routing, 'routing_behavior_str': routing_behavior_str}
        entries.append(queue_entry_dict)
        if is_routing:
            generate_object_routing_queue_log(data=queue_entry_dict)
        index += 1
    return entries
