from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *import enum
class ModifyDynamicUnitRating(enum.Int):
    SMALL_LOSS = 0
    LARGE_LOSS = 1
    SMALL_GAIN = 2
    LARGE_GAIN = 3
    BONUS_SMALL = 4
    BONUS_LARGE = 5

class RatingSubScore(enum.Int):
    LOW = 0
    MEDIUM = 1
    HIGH = 2

class RatingContributionObject(enum.Int):
    RCO_TOILET = 0
    RCO_BED = 1
    RCO_BATH = 2
    RCO_STOVE = 3
    RCO_FRIDGE = 4
    RCO_AMENITY = 5
    RCO_COUNT = 6
    RCO_INVALID = 255

class UnitRatingCategoryType(enum.Int):
    SIZE = 0
    AMENITY = 1
    ENVIRONMENT = 2
    MAINTENANCE = 3

class UnitRatingAlertState(enum.Int, export=False):
    CLEAR = 0
    INCREASE = 1
    DECREASE = 2
