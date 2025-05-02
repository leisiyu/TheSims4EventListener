from sims4.tuning.dynamic_enum import DynamicEnumFlagsfrom sims4.tuning.tunable import TunableRangeimport enum
class PortalTuning:
    SURFACE_PORTAL_HEIGH_OFFSET = TunableRange(description='\n        A height offset on meters increase the height of the raycast test\n        to consider two connecting portals valid over an objects footprint.\n        For example this height is high enough so two portals on counters pass\n        a raycast test over a stove or a sink (low objects), but is not high\n        enough to pass over a microwave (which would cause our sims to clip\n        through the object when transitioning through the portal.\n        ', tunable_type=float, default=0.2, minimum=0)

class PortalFlags(DynamicEnumFlags):
    DEFAULT = 0
    REQUIRE_NO_CARRY = 1
    REQUIRE_NO_CARRY_BACK = 2
    STAIRS_PORTAL_LONG = 4
    STAIRS_PORTAL_SHORT = 8
    SPECIES_HUMAN = 16
    SPECIES_DOG = 32
    SPECIES_CAT = 64
    SPECIES_SMALLDOG = 128
    SPECIES_FOX = 256
    SPECIES_HORSE = 512
    AGE_INFANT = 1024
    AGE_TODDLER = 2048
    AGE_CHILD = 4096
    AGE_TYAE = 8192
    CLEARANCE_HIGH = 16384
    CLEARANCE_MEDIUM = 32768
    CLEARANCE_LOW = 65536
    BUSINESS_EMPLOYEE_AREA = 131072
    BUSINESS_PRIVATE_AREA = 262144

class PortalType(enum.Int, export=False):
    PortalType_Wormhole = 0
    PortalType_Walk = 1
    PortalType_Animate = 2
