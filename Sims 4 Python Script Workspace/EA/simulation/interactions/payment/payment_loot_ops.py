from interactions.payment.tunable_payment import TunablePaymentSnippetfrom interactions.utils.loot_basic_op import BaseLootOperation
class PaymentLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'payment': TunablePaymentSnippet()}

    def __init__(self, payment, **kwargs):
        super().__init__(**kwargs)
        self._payment = payment

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject.is_sim:
            self._payment.try_deduct_payment(resolver, subject)
