from debugvis import Contextfrom sims4.color import Colorfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunableimport servicesimport sims4.loglogger = sims4.log.Logger('Debugvis')
class SpawnPointVisualizer:
    SPAWN_POINT_COLORS = TunableMapping(description="\n        Debug Spawn Point Color mapping. This way we can map spawn point types\n        to colors. When the user types the |debugvis.spawn_points.start\n        command, they will be able to see which spawn point belongs to it's\n        appropriate color, even if the catalog side changes.\n        ", key_type=Tunable(description='\n            The ID of the Spawn Point from the Catalog under Locators.\n            ', tunable_type=int, default=8890), value_type=TunableEnumEntry(description='\n            The debug Color this Spawn Point will appear in the world.\n            ', tunable_type=Color, default=Color.WHITE), key_name='Spawn Point ID', value_name='Spawn Point Color')

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        zone = services.current_zone()
        zone.register_spawn_points_changed_callback(self._draw_spawn_points)
        self._draw_spawn_points()

    def stop(self):
        zone = services.current_zone()
        zone.unregister_spawn_points_changed_callback(self._draw_spawn_points)

    def _draw_spawn_points(self):
        zone = services.current_zone()
        with Context(self.layer) as layer:
            for spawn_point in zone.spawn_points_gen():
                point_color = SpawnPointVisualizer.SPAWN_POINT_COLORS.get(spawn_point.obj_def_guid, Color.WHITE)
                footprint_polygon = spawn_point.get_footprint_polygon()
                routing_surface = spawn_point.routing_surface
                if footprint_polygon is not None:
                    layer.add_polygon(footprint_polygon, color=point_color, altitude=0.1, routing_surface=routing_surface)
                (valid_positions, invalid_positions) = spawn_point.get_valid_and_invalid_positions()
                layer.set_color(point_color)
                for slot_position in valid_positions:
                    layer.add_point(slot_position, altitude=0.1, routing_surface=routing_surface)
                layer.set_color(Color.RED)
                for slot_position in invalid_positions:
                    layer.add_point(slot_position, altitude=0.1, routing_surface=routing_surface)
                layer.set_color(Color.WHITE)
                layer.add_text_world(spawn_point.get_approximate_center(), spawn_point.get_name(), routing_surface=routing_surface)
            layer.set_color(Color.CYAN)
            for corner in services.current_zone().lot.corners:
                layer.add_point(corner, size=1.0)

    def get_spawn_point_string_gen(self):
        zone = services.current_zone()
        for spawn_point in zone.spawn_points_gen():
            spawn_point_string = 'Spawn Point {}:'.format(spawn_point.get_name())
            spawn_point_string += '\nPosition: {}'.format(spawn_point.get_approximate_center())
            spawn_point_string += '\nTags: {}'.format(spawn_point.get_tags())
            spawn_point_household_owner = spawn_point.get_household_owner()
            spawn_point_string += '\nHousehold: {}'.format(spawn_point_household_owner.name)
            yield spawn_point_string
