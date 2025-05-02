import enumINVALID_PLEX_ID = 0
class PlexBuildingType(enum.Int):
    DEFAULT = 0
    FULLY_CONTAINED_PLEX = 1
    PENTHOUSE_PLEX = 2
    INVALID = 3
    EXPLORABLE = 4
    COASTAL = 5
    BT_MULTI_UNIT = 6
    BT_PENTHOUSE_RENTAL = 7
