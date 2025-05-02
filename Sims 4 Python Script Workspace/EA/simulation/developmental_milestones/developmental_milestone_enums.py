import enum
class DevelopmentalMilestoneStates(enum.Int):
    LOCKED = -1
    ACTIVE = 0
    UNLOCKED = 1

class MilestoneDataClass(enum.Int):
    DEFAULT = 0
    HAD_CHILD = 1
