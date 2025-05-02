from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from routing import Location
    from routing.portals.portal_tuning import PortalFlagsimport build_buyimport servicesimport terrainfrom routing.portals.portal_enums import PathSplitTypefrom routing import SurfaceTypefrom routing.portals.portal_event import TunablePortalEventVariantfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableListfrom sims4.utils import classproperty
class _PortalTypeDataBase(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'portal_events': TunableList(description='\n            A list of portal events to add when a Sim uses the portal.\n            ', tunable=TunablePortalEventVariant(description='\n                The tuning for a specific portal event.\n                '))}

    @property
    def portal_type(self):
        raise NotImplementedError

    @property
    def outfit_change(self):
        pass

    @property
    def requires_los_between_points(self):
        return True

    @property
    def lock_portal_on_use(self):
        return True

    @classproperty
    def discourage_portal_on_plan(cls):
        return True

    def get_additional_required_portal_flags(self, entry_location, exit_location):
        return 0

    def get_additional_exclusion_portal_flags(self, there_entry:'Location', there_exit:'Location') -> 'tuple[PortalFlags, PortalFlags]':
        block_id_entry = build_buy.get_block_id(services.current_zone_id(), there_entry.position, there_entry.routing_surface.secondary_id)
        block_id_exit = build_buy.get_block_id(services.current_zone_id(), there_exit.position, there_exit.routing_surface.secondary_id)
        entry_type = services.dynamic_area_service().get_area_type_for_block(block_id_entry)
        exit_type = services.dynamic_area_service().get_area_type_for_block(block_id_exit)
        (area_entry_exclusion_flag, area_exit_exclusion_flag) = services.dynamic_area_service().get_portal_flags_for_areas(entry_type, exit_type)
        return (area_entry_exclusion_flag, area_exit_exclusion_flag)

    def notify_in_use(self, user, portal_instance, portal_object):
        pass

    def add_portal_data(self, actor, portal_instance, is_mirrored, walkstyle):
        pass

    def add_portal_events(self, portal, actor, obj, time, route_pb):
        for portal_event in self.portal_events:
            op = portal_event.get_portal_op(actor, obj)
            event = route_pb.events.add()
            event.time = max(0, time + portal_event.time)
            event.type = portal_event.get_portal_event_type()
            event.data = op.SerializeToString()

    def get_portal_asm_params(self, portal_instance, portal_id, sim):
        return {}

    def get_destination_objects(self):
        return ()

    def get_portal_duration(self, portal_instance, is_mirrored, walkstyle, age, gender, species):
        raise NotImplementedError

    def get_portal_locations(self, obj):
        raise NotImplementedError

    def get_posture_change(self, portal_instance, is_mirrored, initial_posture):
        return (initial_posture, initial_posture)

    def is_ungreeted_sim_disallowed(self):
        return False

    def split_path_on_portal(self):
        return PathSplitType.PathSplitType_DontSplit

    def provide_route_events(self, *args, **kwargs):
        pass

    def is_offset_from_object(self, portal_position, obj, height_tolerance):
        if height_tolerance is None:
            return False
        if portal_position.routing_surface.type != SurfaceType.SURFACETYPE_WORLD:
            return False
        portal_height = terrain.get_lot_level_height(portal_position.position.x, portal_position.position.z, portal_position.routing_surface.secondary_id, portal_position.routing_surface.primary_id)
        portal_height_difference = abs(obj.position.y - portal_height)
        return portal_height_difference > height_tolerance
