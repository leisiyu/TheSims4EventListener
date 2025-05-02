import enumfrom sims4.tuning.dynamic_enum import DynamicEnumLocked
class ObjectCollectionRarity(enum.Int):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3

class CollectionIdentifier(DynamicEnumLocked):
    Unindentified = 0
    Gardening = 1
    Frogs = 2
    MySims = 3
    Metals = 4
    Crystals = 5
    NatureElements = 6
    Postcards = 7
    Fossils = 8
    Microscope = 9
    Telescope = 10
    Aliens = 11
    SpaceRocks = 12
    Fish = 13
