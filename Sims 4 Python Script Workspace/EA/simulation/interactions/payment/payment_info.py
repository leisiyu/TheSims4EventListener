import enum
class PaymentInfo:

    def __init__(self, amount, resolver):
        self.amount = amount
        self.resolver = resolver
        self.revenue_type = PaymentBusinessRevenueType.INVALID

class BusinessPaymentInfo(PaymentInfo):

    def __init__(self, *args, revenue_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.revenue_type = revenue_type

class PaymentBusinessRevenueType(enum.Int):
    INVALID = -1
    ITEM_SOLD = 0
    SEED_MONEY = 1
    SMALL_BUSINESS_ATTENDANCE_HOURLY_FEE = 2
    SMALL_BUSINESS_ATTENDANCE_ENTRY_FEE = 3
    SMALL_BUSINESS_LIGHT_RETAIL_FEE = 4
    SMALL_BUSINESS_INTERACTION_FEE = 5
    SMALL_BUSINESS_OPENING_FEE = 6
    EMPLOYEE_WAGES = 7
    SMALL_BUSINESS_TIP_JAR_FEE = 8
