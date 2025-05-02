import enum
class SuperAffordanceSuppression(enum.Int):
    AUTONOMOUS_ONLY = 0
    USER_DIRECTED = 1
    USE_AFFORDANCE_COMPATIBILITY_AND_WHITELIST = 2

class SuppressionCheckOption(enum.Int, export=False):
    AFFORDANCE_ONLY = 0
    PROVIDED_AFFORDANCE_ONLY = 1
    AFFORDANCE_AND_PROVIDED_AFFORDANCE = 2
