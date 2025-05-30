from build_buy import get_room_idfrom objects.components.lighting_component import LightingComponentfrom objects.components.types import LIGHTING_COMPONENTfrom objects.color.object_color_dialog import UiDialogObjectColorPickerfrom objects.color.object_color_enums import ObjectColorPickerPalette, ObjectColorPickerStylefrom objects.lighting.lighting_utils import all_lights_gen, lights_in_target_room_genimport servicesimport sims4.colorimport sims4.commands
@sims4.commands.Command('lighting.set_color_and_intensity', command_type=sims4.commands.CommandType.Live)
def set_color_and_intensity(response_id:int, r:int=None, g:int=None, b:int=None, intensity:float=1.0, _connection=None):
    ui_dialog_service = services.ui_dialog_service()
    if ui_dialog_service is not None:
        dialog = ui_dialog_service.get_dialog(response_id)
        if dialog is not None:
            color = sims4.color.from_rgba_as_int(r, g, b)
            dialog.update_dialog_data(color=color, slider_value=intensity)
    return True

def single_light_gen(target):
    yield target

@sims4.commands.Command('lighting.showlighteditor', command_type=sims4.commands.CommandType.Live)
def show_light_editor(light_object_id:int, light_target_type:int=0, _connection=None):
    light_object = services.object_manager().get(light_object_id)
    if light_object is None:
        sims4.commands.output('Invalid object ID specified. Please try again with a valid object ID.', _connection)
        return
    if not light_object.has_component(LIGHTING_COMPONENT):
        sims4.commands.output('Specified object {} does not have a lighting component'.foramt(light_object), _connection)
        return
    light_gen = None
    if light_target_type == 0:
        light_gen = single_light_gen
    elif light_target_type == 1:
        light_gen = lights_in_target_room_gen
    elif light_target_type == 2:
        light_gen = all_lights_gen
    else:
        sims4.commands.output('Invalid value for light_target_type specified: {}. Expecting a 0 (Current Light), 1 (All Lights in Room of target), or 2 (all lights).'.format(light_target_type), _connection)
        return

    def _on_update(*, color, slider_value, **kwargs):
        if light_gen is not None:
            for light in light_gen(light_object):
                light.set_user_intensity_override(slider_value)
                light.set_light_color(color)

    color = light_object.get_light_color()
    if color is not None:
        (r, g, b, _) = sims4.color.to_rgba_as_int(color)
    else:
        r = g = b = sims4.color.MAX_INT_COLOR_VALUE
    intensity = light_object.get_user_intensity_overrides()
    dialog = UiDialogObjectColorPicker(light_object, r, g, b, slider_value=intensity, on_update=_on_update, palette=ObjectColorPickerPalette.LIGHTING, style=ObjectColorPickerStyle.SLIDER)
    dialog.show_dialog()

@sims4.commands.Command('lighting.auto_room_light_status', command_type=sims4.commands.CommandType.Live)
def auto_room_light_status(room_id:int, on:bool, _connection=None):
    zone_id = services.current_zone_id()
    for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT):
        if obj.get_light_dimmer_value() != LightingComponent.LIGHT_AUTOMATION_DIMMER_VALUE:
            pass
        else:
            obj_room_id = get_room_id(zone_id, obj.position, obj.level)
            if obj_room_id != room_id:
                pass
            else:
                obj.on_light_changed(on)
