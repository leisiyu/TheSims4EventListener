import enumfrom sims4.tuning.dynamic_enum import DynamicEnum
class AdditionalBillSource(DynamicEnum):
    Miscellaneous = 0

class UtilityEndOfBillAction(enum.Int, export=False):
    SELL = 0
    STORE = 1

class BillTypes(enum.Int):
    ALL_BILLS = 0
    HOUSING_BILLS = 1
    NON_HOUSING_BILLS = 2

class BillDueType(enum.Int):
    IS_DUE = 0
    IS_NOT_DUE = 1
    HAS_POSITIVE_CREDITS = 2

class DebtSource(enum.Int):
    SCHOOL_LOAN = ...
    BILLS = ...
    HOUSING_BILLS = ...
