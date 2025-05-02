from routing.portals.portal_data_build_ladders import _PortalTypeDataBuildLadders
class _PortalTypeDataObjectLadders(_PortalTypeDataBuildLadders):

    def _get_num_rungs(self, ladder):
        rung_start = self.climb_up_locations.location_start(ladder).position.y
        rung_end = self.climb_up_locations.location_end(ladder).position.y - self.ladder_rung_distance
        return (rung_end - rung_start)//self.ladder_rung_distance + 1

    def _get_top_and_bottom_levels(self, obj):
        obj_level = obj.location.level
        return (obj_level, obj_level)

    def _get_blocked_alignment_flags(self, obj):
        return 0
