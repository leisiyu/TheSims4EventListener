from debugvis import Contextfrom objects.components.types import PROXIMITY_COMPONENTfrom sims4.color import pseudo_random_color
class ProximityVisualizer:

    def __init__(self, obj, layer):
        self._obj = obj
        self.layer = layer
        self.start()

    def start(self):
        self._obj.register_on_location_changed(self._on_position_changed)
        self.redraw(self._obj)

    def stop(self):
        if self._obj._on_location_changed_callbacks is not None and self._on_position_changed in self._obj._on_location_changed_callbacks:
            self._obj.unregister_on_location_changed(self._on_position_changed)

    def redraw(self, obj):
        with Context(self.layer) as layer:
            proximity_component = obj.get_component(PROXIMITY_COMPONENT)
            if proximity_component is not None:
                layer.add_circle(obj.position, proximity_component.update_distance, color=pseudo_random_color(obj.id))

    def _on_position_changed(self, *_, **__):
        self.redraw(self._obj)
