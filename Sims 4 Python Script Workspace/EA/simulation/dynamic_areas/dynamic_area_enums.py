import enum
class DynamicAreaType(enum.Int):
    INVALID = -1
    BUSINESS_RESIDENTIAL = 0
    BUSINESS_PUBLIC = 1
    BUSINESS_EMPLOYEES_ONLY = 2
    COUNT = 3
