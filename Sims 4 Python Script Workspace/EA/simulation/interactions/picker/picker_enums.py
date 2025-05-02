import enum
class PickerInteractionDeliveryMethod(enum.Int):
    INVENTORY = 0
    MAILMAN = 1
    SLOT_TO_PARENT = 2
    DELIVERY_SERVICE_NPC = 3

class SimPickerLinkContinuation(enum.Int):
    NEITHER = 0
    ACTOR = 1
    PICKED = 2
    ALL = 3
    TARGET = 4

class DuplicateObjectsSuppressionType(enum.Int):
    BY_DEFINITION_ID = 0
    BY_STACK_ID = 1
    BY_DEFINITION_ID_AND_STACK_ID = 2

class PriceOption(enum.Int):
    USE_CURRENT_VALUE = 0
    USE_RETAIL_VALUE = 1
