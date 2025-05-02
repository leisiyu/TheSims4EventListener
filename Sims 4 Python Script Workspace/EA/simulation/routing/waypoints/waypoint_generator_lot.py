from _collections import defaultdictimport itertoolsimport mathfrom build_buy import get_all_block_polygons, get_block_idfrom interactions.constraints import Anywhere, Circlefrom plex import plex_enumsfrom routing.waypoints.waypoint_generator import _WaypointGeneratorBase, WaypointContextfrom routing.waypoints.waypoint_generator_tags import _WaypointGeneratorMultipleObjectByTagfrom sims4.geometry import CompoundPolygon, random_uniform_points_in_compound_polygon, Polygonfrom sims4.math import MAX_INT32from sims4.tuning.tunable import TunableRange, OptionalTunable, TunableTuple, Tunableimport build_buyimport routingimport services
class _WaypointGeneratorLotPoints(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'constraint_radius': TunableRange(description='\n            The radius, in meters, for each of the generated waypoint\n            constraints.\n            ', tunable_type=float, default=2, minimum=0), 'object_tag_generator': OptionalTunable(description='\n            If enabled, in addition to generating random points on the lot, this\n            generator also ensures that all constraints that would be generated\n            by the Tag generator are also hit.\n            \n            This gets you a very specific behavior: apparent randomness but the\n            guarantee that all objects with specific tags are route to.\n            ', tunable=_WaypointGeneratorMultipleObjectByTag.TunableFactory()), 'constraint_parameters': TunableTuple(description='\n            Parameters used to generate the constraints that will be used to generate waypoints.\n            ', min_water_depth=OptionalTunable(description='\n                If enabled, generate waypoints at locations that are at least this deep.\n                ', tunable=TunableRange(description='\n                    The minimum water depth allowed for each waypoint.\n                    ', tunable_type=float, default=0, minimum=0)), max_water_depth=OptionalTunable(description='\n                If enabled, generate waypoints at locations that are at most this deep.\n                ', tunable=TunableRange(description='\n                    The maximum water depth allowed for each waypoint.\n                    ', tunable_type=float, default=1000.0, minimum=0, maximum=1000.0))), 'waypoints_outside_only': Tunable(description='\n            If enabled, only waypoints outside of a block will be generated.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = self._context.sim

    def get_start_constraint(self):
        return self.get_water_constraint(self.constraint_parameters.min_water_depth, self.constraint_parameters.max_water_depth)

    def _get_polygons_for_lot(self):
        lot = services.active_lot()
        return [(CompoundPolygon(Polygon(list(reversed(lot.corners)))), self._routing_surface)]

    def _get_waypoint_constraints_from_polygons(self, object_constraints, waypoints_dict):
        object_constraints = dict(object_constraints)
        restriction = None
        if self.object_tag_generator is not None:
            restriction = self.object_tag_generator.placement_restriction
        final_constraints = []
        for (block_id, waypoints) in waypoints_dict.items():
            block_object_constraints = object_constraints.pop(block_id, ())
            if restriction is not None:
                if restriction and block_id == 0:
                    pass
                elif restriction or block_id != 0:
                    pass
                else:
                    for position in waypoints:
                        position_constraint = Circle(position, self.constraint_radius, routing_surface=self._routing_surface)
                        for block_object_constraint in tuple(block_object_constraints):
                            intersection = block_object_constraint.intersect(position_constraint)
                            if intersection.valid:
                                block_object_constraints.remove(block_object_constraint)
                        final_constraints.append(position_constraint)
                    final_constraints.extend(block_object_constraints)
            else:
                for position in waypoints:
                    position_constraint = Circle(position, self.constraint_radius, routing_surface=self._routing_surface)
                    for block_object_constraint in tuple(block_object_constraints):
                        intersection = block_object_constraint.intersect(position_constraint)
                        if intersection.valid:
                            block_object_constraints.remove(block_object_constraint)
                    final_constraints.append(position_constraint)
                final_constraints.extend(block_object_constraints)
        final_constraints.extend(itertools.chain.from_iterable(object_constraints.values()))
        return final_constraints

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        zone_id = services.current_zone_id()
        object_constraints = defaultdict(list)
        if self.object_tag_generator is not None:
            object_tag_generator = self.object_tag_generator(WaypointContext(self._sim), None)
            for constraint in itertools.chain((object_tag_generator.get_start_constraint(),), object_tag_generator.get_waypoint_constraints_gen(routing_agent, MAX_INT32)):
                level = constraint.routing_surface.secondary_id
                block_id = get_block_id(zone_id, constraint.average_position, level)
                object_constraints[block_id].append(constraint)
        plex_id = services.get_plex_service().get_active_zone_plex_id() or plex_enums.INVALID_PLEX_ID
        waypoints_dict = build_buy.generate_lot_waypoints(zone_id, plex_id, waypoint_count, self._sim.routing_location, self._routing_surface, self.waypoints_outside_only, self._sim.get_routing_context())
        if not waypoints_dict:
            return False
        final_constraints = self._get_waypoint_constraints_from_polygons(object_constraints, waypoints_dict)
        final_constraints = self.apply_water_constraint(final_constraints)
        yield from final_constraints
