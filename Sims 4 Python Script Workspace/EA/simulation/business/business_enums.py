from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class BusinessType(enum.Int):
    INVALID = 0
    RETAIL = 1
    RESTAURANT = 2
    VET = 3
    RENTAL_UNIT = 4
    SMALL_BUSINESS = 5

class BusinessEmployeeType(DynamicEnum):
    INVALID = 0

class BusinessCustomerStarRatingBuffBuckets(DynamicEnum):
    INVALID = 0

class BusinessAdvertisingType(DynamicEnum):
    INVALID = 0

class BusinessQualityType(DynamicEnum):
    INVALID = 0

class FirstTimeMessageType(enum.Int):
    INVALID = 0
    STAR_RATING_CHANGE = 1
    GRACE_PERIOD_TENANT = 2
    GRACE_PERIOD_OWNER = 3
    ANY_RATING_CHANGE = 4
    ANY_RATING_CHANGE_TENANT = 5

class BusinessOriginTelemetryContext(enum.Int):
    NONE = 0
    XEVT = 1
    BB = 2
    PREMADE = 3

class SmallBusinessAttendanceSaleMode(enum.Int):
    DISABLED = 0
    HOURLY_FEE = 1
    ENTRY_FEE = 2

class SmallBusinessSalary(enum.Int):
    LOW = 0
    AVERAGE = 1
    HIGH = 2
