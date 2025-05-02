import servicesimport sims4import telemetry_helperTELEMETRY_GROUP_OBJECT = 'OBJC'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_OBJECT)TELEMETRY_HOOK_STATE_CHANGE = 'OBJC'TELEMETRY_FIELD_DEFINITION = 'objc'TELEMETRY_FIELD_INSTANCE = 'inst'TELEMETRY_FIELD_OLD_STATE = 'from'TELEMETRY_FIELD_NEW_STATE = 'news'TELEMETRY_FIELD_REASON = 'resn'TELEMETRY_FIELD_LUNAR_PHASE = 'moon'TELEMETRY_FIELD_QUALITY = 'qual'
def send_state_change_telemetry(obj, old_value, new_value, from_init, from_stat, from_sync):
    with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_STATE_CHANGE) as hook:
        definition_id = obj.definition.id if hasattr(obj, 'definition') else 0
        hook.write_int(TELEMETRY_FIELD_DEFINITION, definition_id)
        hook.write_int(TELEMETRY_FIELD_INSTANCE, obj.id)
        hook.write_enum(TELEMETRY_FIELD_OLD_STATE, old_value)
        hook.write_enum(TELEMETRY_FIELD_NEW_STATE, new_value)
        if from_init:
            reason = 'init'
        elif from_stat:
            reason = 'stat'
        elif from_sync:
            reason = 'sync'
        else:
            reason = 'other'
        hook.write_string(TELEMETRY_FIELD_REASON, reason)
        if obj.lunar_phase_aware_component is not None:
            lunar_cycle_service = services.lunar_cycle_service()
            hook.write_int(TELEMETRY_FIELD_LUNAR_PHASE, lunar_cycle_service.current_phase)
        if obj.gardening_component is not None:
            gardening_quality_value = obj.gardening_component.get_quality_value()
            if gardening_quality_value is not None:
                hook.write_int(TELEMETRY_FIELD_QUALITY, gardening_quality_value)
TELEMETRY_HOOK_OBJECT_CREATE_BSCEXTRA = 'CRBE'TELEMETRY_FIELD_OBJECT_INTERACTION = 'intr'TELEMETRY_FIELD_OBJECT_DEFINITION = 'objc'
def send_create_object_basic_extra_telemetry(interaction_id, definition_id):
    with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_OBJECT_CREATE_BSCEXTRA) as hook:
        hook.write_int(TELEMETRY_FIELD_OBJECT_INTERACTION, interaction_id)
        hook.write_guid(TELEMETRY_FIELD_OBJECT_DEFINITION, definition_id)
TELEMETRY_HOOK_OBJECT_SLOT = 'SLOT'TELEMETRY_FIELD_OBJECT_ID = 'obid'TELEMETRY_FIELD_PARENT_OBJECT_ID = 'paid'TELEMETRY_FIELD_SLOT_NAME = 'slna'
def send_object_slotted_telemetry(child, parent, slot_name):
    with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_OBJECT_SLOT) as hook:
        hook.write_guid(TELEMETRY_FIELD_OBJECT_ID, child.definition.id)
        hook.write_string(TELEMETRY_FIELD_SLOT_NAME, slot_name)
        hook.write_guid(TELEMETRY_FIELD_PARENT_OBJECT_ID, parent.definition.id)
