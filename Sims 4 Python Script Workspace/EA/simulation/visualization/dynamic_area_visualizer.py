import build_buyimport servicesimport sims4.mathfrom debugvis import Contextfrom indexed_manager import CallbackTypesfrom sims4.color import Colorfrom dynamic_areas.dynamic_area_enums import DynamicAreaTypelogger = sims4.log.Logger('Dynamic Area Visualizer', default_owner='pgoujet')
class DynamicAreaVisualizer:

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        self._draw_all_areas()
        build_buy.register_build_buy_exit_callback(self._draw_all_areas)
        services.object_manager().register_callback(CallbackTypes.ON_OBJECT_ADD, self._draw_all_areas)
        services.object_manager().register_callback(CallbackTypes.ON_OBJECT_REMOVE, self._draw_all_areas)
        services.dynamic_area_service().register_update_object_callback(self._draw_all_areas)

    def stop(self):
        build_buy.unregister_build_buy_exit_callback(self._draw_all_areas)
        services.object_manager().unregister_callback(CallbackTypes.ON_OBJECT_ADD, self._draw_all_areas)
        services.object_manager().unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self._draw_all_areas)
        services.dynamic_area_service().unregister_update_object_callback(self._draw_all_areas)

    def _draw_all_areas(self, *_, **__):
        with Context(self.layer, preserve=True) as context:
            context.layer.clear()
            debug_colors = [Color.RED, Color.GREEN, Color.ORANGE]
            if len(debug_colors) != int(DynamicAreaType.COUNT):
                logger.error('Debug colors count is different from the number of possible DynamicAreaType.')
                return
            for i in range(DynamicAreaType.COUNT):
                area_type = DynamicAreaType(i)
                self._draw_area(context.layer, area_type, debug_colors[i])

    def _draw_area(self, layer, area_type:DynamicAreaType, debug_color:Color):
        area = services.dynamic_area_service().get_dynamic_area(area_type)
        if area is not None:
            for obj_id in area.objects:
                obj = services.object_manager().get(obj_id)
                if obj is not None:
                    layer.add_segment(obj.position, obj.position + sims4.math.Vector3(0.0, 2.5, 0.0), debug_color)
