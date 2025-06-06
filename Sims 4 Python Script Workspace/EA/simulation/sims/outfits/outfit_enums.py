import itertoolsfrom sims4.tuning.dynamic_enum import DynamicEnumimport enum
class OutfitCategory(enum.Int):
    CURRENT_OUTFIT = -1
    EVERYDAY = 0
    FORMAL = 1
    ATHLETIC = 2
    SLEEP = 3
    PARTY = 4
    BATHING = 5
    CAREER = 6
    SITUATION = 7
    SPECIAL = 8
    SWIMWEAR = 9
    HOTWEATHER = 10
    COLDWEATHER = 11
    BATUU = 12
    SMALL_BUSINESS = 13

class WeatherOutfitCategory(enum.Int):
    HOTWEATHER = OutfitCategory.HOTWEATHER
    COLDWEATHER = OutfitCategory.COLDWEATHER

class SpecialOutfitIndex(enum.Int):
    DEFAULT = 0
    TOWEL = 1
    FASHION = 2

class OutfitChangeReason(DynamicEnum):
    Invalid = -1
    PreviousClothing = 0
    DefaultOutfit = 1
    RandomOutfit = 2
    ExitBedNPC = 3
    CurrentOutfit = 4
    FashionOutfit = 5

class DefaultOutfitPriority(DynamicEnum):
    NoPriority = 0
REGULAR_OUTFIT_CATEGORIES = (OutfitCategory.EVERYDAY, OutfitCategory.FORMAL, OutfitCategory.ATHLETIC, OutfitCategory.SLEEP, OutfitCategory.PARTY, OutfitCategory.SWIMWEAR, OutfitCategory.HOTWEATHER, OutfitCategory.COLDWEATHER)INFANT_PROHIBITED_OUTFIT_CATEGORIES = frozenset((OutfitCategory.ATHLETIC, OutfitCategory.SWIMWEAR))TODDLER_PROHIBITED_OUTFIT_CATEGORIES = frozenset((OutfitCategory.ATHLETIC,))HIDDEN_OUTFIT_CATEGORIES = (OutfitCategory.CAREER, OutfitCategory.SITUATION, OutfitCategory.SPECIAL, OutfitCategory.BATUU)NON_RANDOMIZABLE_OUTFIT_CATEGORIES = (OutfitCategory.BATHING,)
class BodyType(enum.Int):
    NONE = 0
    HAT = 1
    HAIR = 2
    HEAD = 3
    TEETH = 4
    FULL_BODY = 5
    UPPER_BODY = 6
    LOWER_BODY = 7
    SHOES = 8
    CUMMERBUND = 9
    EARRINGS = 10
    GLASSES = 11
    NECKLACE = 12
    GLOVES = 13
    WRIST_LEFT = 14
    WRIST_RIGHT = 15
    LIP_RING_LEFT = 16
    LIP_RING_RIGHT = 17
    NOSE_RING_LEFT = 18
    NOSE_RING_RIGHT = 19
    BROW_RING_LEFT = 20
    BROW_RING_RIGHT = 21
    INDEX_FINGER_LEFT = 22
    INDEX_FINGER_RIGHT = 23
    RING_FINGER_LEFT = 24
    RING_FINGER_RIGHT = 25
    MIDDLE_FINGER_LEFT = 26
    MIDDLE_FINGER_RIGHT = 27
    FACIAL_HAIR = 28
    LIPS_TICK = 29
    EYE_SHADOW = 30
    EYE_LINER = 31
    BLUSH = 32
    FACEPAINT = 33
    EYEBROWS = 34
    EYECOLOR = 35
    SOCKS = 36
    EYELASHES = 37
    SKINDETAIL_CREASE_FOREHEAD = 38
    SKINDETAIL_FRECKLES = 39
    SKINDETAIL_DIMPLE_LEFT = 40
    SKINDETAIL_DIMPLE_RIGHT = 41
    TIGHTS = 42
    SKINDETAIL_MOLE_LIP_LEFT = 43
    SKINDETAIL_MOLE_LIP_RIGHT = 44
    TATTOO_ARM_LOWER_LEFT = 45
    TATTOO_ARM_UPPER_LEFT = 46
    TATTOO_ARM_LOWER_RIGHT = 47
    TATTOO_ARM_UPPER_RIGHT = 48
    TATTOO_LEG_LEFT = 49
    TATTOO_LEG_RIGHT = 50
    TATTOO_TORSO_BACK_LOWER = 51
    TATTOO_TORSO_BACK_UPPER = 52
    TATTOO_TORSO_FRONT_LOWER = 53
    TATTOO_TORSO_FRONT_UPPER = 54
    SKINDETAIL_MOLE_CHEEK_LEFT = 55
    SKINDETAIL_MOLE_CHEEK_RIGHT = 56
    SKINDETAIL_CREASE_MOUTH = 57
    SKIN_OVERLAY = 58
    FUR_BODY = 59
    EARS = 60
    TAIL = 61
    SKINDETAIL_NOSE_COLOR = 62
    EYECOLOR_SECONDARY = 63
    OCCULT_BROW = 64
    OCCULT_EYE_SOCKET = 65
    OCCULT_EYE_LID = 66
    OCCULT_MOUTH = 67
    OCCULT_LEFT_CHEEK = 68
    OCCULT_RIGHT_CHEEK = 69
    OCCULT_NECK_SCAR = 70
    FOREARM_SCAR = 71
    ACNE = 72
    FINGERNAIL = 73
    TOENAIL = 74
    HAIRCOLOR_OVERRIDE = 75
    BITE = 76
    BODYFRECKLES = 77
    BODYHAIR_ARM = 78
    BODYHAIR_LEG = 79
    BODYHAIR_TORSOFRONT = 80
    BODYHAIR_TORSOBACK = 81
    BODYSCAR_ARMLEFT = 82
    BODYSCAR_ARMRIGHT = 83
    BODYSCAR_TORSOFRONT = 84
    BODYSCAR_TORSOBACK = 85
    BODYSCAR_LEGLEFT = 86
    BODYSCAR_LEGRIGHT = 87
    ATTACHMENT_BACK = 88
    SKINDETAIL_ACNE_PUBERTY = 89
    SCARFACE = 90
    BIRTHMARKFACE = 91
    BIRTHMARKTORSOBACK = 92
    BIRTHMARKTORSOFRONT = 93
    BIRTHMARKARMS = 94
    MOLEFACE = 95
    MOLECHESTUPPER = 96
    MOLEBACKUPPER = 97
    BIRTHMARKLEGS = 98
    STRETCHMARKS_FRONT = 99
    STRETCHMARKS_BACK = 100
    SADDLE = 101
    BRIDLE = 102
    REINS = 103
    BLANKET = 104
    SKINDETAIL_HOOF_COLOR = 105
    HAIR_MANE = 106
    HAIR_TAIL = 107
    HAIR_FORELOCK = 108
    HAIR_FEATHERS = 109
    HORN = 110
    TAIL_BASE = 111
    BIRTHMARKOCCULT = 112
    TATTOO_HEAD = 113

class BodyTypeGroups:
    NONE = 0
    BRACELETS = [BodyType.WRIST_LEFT, BodyType.WRIST_RIGHT]
    PIERCINGS = [BodyType.LIP_RING_LEFT, BodyType.LIP_RING_RIGHT, BodyType.NOSE_RING_LEFT, BodyType.NOSE_RING_RIGHT, BodyType.BROW_RING_LEFT, BodyType.BROW_RING_RIGHT]
    RINGS = [BodyType.INDEX_FINGER_LEFT, BodyType.INDEX_FINGER_RIGHT, BodyType.RING_FINGER_LEFT, BodyType.RING_FINGER_RIGHT, BodyType.MIDDLE_FINGER_LEFT, BodyType.MIDDLE_FINGER_RIGHT]
    ACCESSORY_ALL = list(itertools.chain(*[[BodyType.EARRINGS, BodyType.GLASSES, BodyType.NECKLACE, BodyType.GLOVES, BodyType.SOCKS, BodyType.TIGHTS], BRACELETS, PIERCINGS, RINGS]))
    CLOTHING = [BodyType.HAT, BodyType.FULL_BODY, BodyType.UPPER_BODY, BodyType.LOWER_BODY, BodyType.SHOES]
    CLOTHING_ALL = list(itertools.chain(*[ACCESSORY_ALL, CLOTHING]))
    CATS_DOGS_ALL = [BodyType.EARS, BodyType.FUR_BODY, BodyType.TAIL]

class BodyTypeFlag:

    def make_body_type_flag(*body_types):
        flags = 0
        for body_type in body_types:
            if body_type == BodyType.NONE:
                pass
            else:
                flags |= 1 << body_type
        return flags

    NONE = 0
    BRACELETS = make_body_type_flag(*BodyTypeGroups.BRACELETS)
    PIERCINGS = make_body_type_flag(*BodyTypeGroups.PIERCINGS)
    RINGS = make_body_type_flag(*BodyTypeGroups.RINGS)
    ACCESSORY_ALL = make_body_type_flag(*BodyTypeGroups.ACCESSORY_ALL)
    CLOTHING = make_body_type_flag(*BodyTypeGroups.CLOTHING)
    CLOTHING_ALL = CLOTHING | ACCESSORY_ALL
    CATS_DOGS_ALL = make_body_type_flag(*BodyTypeGroups.CATS_DOGS_ALL)

class MatchNotFoundPolicy(enum.Int):
    MATCH_NOT_FOUND_UNSPECIFIED = 0
    MATCH_NOT_FOUND_FAIL = ...
    MATCH_NOT_FOUND_KEEP_EXISTING = ...
    MATCH_NOT_FOUND_RANDOMIZE = ...

class OutfitFilterFlag(enum.IntFlags):
    NONE = 0
    USE_EXISTING_IF_APPROPRIATE = 1
    IGNORE_IF_NO_MATCH = 2
    OR_SAME_CATEGORY = 4
    EXCLUDE_FULLBODY = 8
    USE_VALID_FOR_LIVE_RANDOM = 16
    IGNORE_VALID_FOR_RANDOM = 32
    MATCH_ALL_TAGS = 64
    USE_DEFAULT_PARTS = 128
    KEEP_EXISTING_PARTS_NOT_BEING_UPDATED = 256
    INCLUDE_GHOST_PARTS = 512
CLOTHING_BODY_TYPES = (BodyType.CUMMERBUND, BodyType.BROW_RING_LEFT, BodyType.BROW_RING_RIGHT, BodyType.EARRINGS, BodyType.FULL_BODY, BodyType.GLASSES, BodyType.GLOVES, BodyType.HAT, BodyType.INDEX_FINGER_LEFT, BodyType.INDEX_FINGER_RIGHT, BodyType.LIP_RING_LEFT, BodyType.LOWER_BODY, BodyType.MIDDLE_FINGER_LEFT, BodyType.MIDDLE_FINGER_RIGHT, BodyType.NECKLACE, BodyType.NOSE_RING_LEFT, BodyType.NOSE_RING_RIGHT, BodyType.RING_FINGER_RIGHT, BodyType.SHOES, BodyType.SOCKS, BodyType.TIGHTS, BodyType.UPPER_BODY, BodyType.WRIST_LEFT, BodyType.WRIST_RIGHT)