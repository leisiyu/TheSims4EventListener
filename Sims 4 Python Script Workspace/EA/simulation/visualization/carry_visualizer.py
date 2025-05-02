from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from carry.put_down_interactions import PutDown
    from sims.sim import Simfrom debugvis import Contextfrom sims4.color import pseudo_random_color
class PutDownVisualizer:

    def __init__(self, sim:'Sim', layer:'str') -> 'None':
        self.sim = sim
        self.layer = layer
        self.start()

    def start(self) -> 'None':
        if self._on_putdown not in self.sim.on_putdown_event:
            self.sim.on_putdown_event.append(self._on_putdown)

    def stop(self) -> 'None':
        if self._on_putdown in self.sim.on_putdown_event:
            self.sim.on_putdown_event.remove(self._on_putdown)

    def _on_putdown(self, putdown_interaction:'PutDown', *args, **kwargs) -> 'None':
        if True or putdown_interaction is None:
            return
        with Context(self.layer, altitude=0.1) as layer:
            color = pseudo_random_color(putdown_interaction.id)
            putdown_transform = putdown_interaction._terrain_transform if hasattr(putdown_interaction, '_terrain_transform') else None
            if putdown_transform is not None:
                layer.add_arrow_for_transform(putdown_transform, color=color, altitude=0.05)
            putdown_jig_polygon = putdown_interaction.putdown_jig_polygon if hasattr(putdown_interaction, 'putdown_jig_polygon') else None
            if putdown_jig_polygon is not None:
                layer.add_polygon(putdown_jig_polygon, color=color)
            layer.routing_surface = self.sim.routing_surface
