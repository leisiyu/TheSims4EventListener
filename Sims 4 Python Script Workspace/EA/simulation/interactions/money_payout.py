from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from interactions.payment.payment_altering_service import PaymentAlteringServiceimport servicesfrom event_testing.test_events import TestEventfrom protocolbuffers import Consts_pb2import collectionsimport interactions.utilsimport sims4from interactions.liability import Liabilityfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims.funds import FundsSourcefrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import Tunable, TunableList, TunableLiteralOrRandomValue, OptionalTunablefrom tag import TunableTagsfrom singletons import DEFAULTfrom tunable_multiplier import TunableStatisticModifierCurvefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetlogger = sims4.log.Logger('MoneyPayout')
class MoneyLiability(Liability):
    LIABILITY_TOKEN = 'MoneyLiability'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.amounts = collections.defaultdict(lambda : 0)

class MoneyChange(BaseLootOperation):
    FACTORY_TUNABLES = {'amount': TunableLiteralOrRandomValue(description='\n            The amount of Simoleons awarded. The value will be rounded to the\n            closest integer. When two integers are equally close, rounding is done\n            towards the even one (e.g. 0.5 -> 0, 1.5 -> 2).  Negative amounts allowed\n            and allow partial deductions (will only take balance to zero, not negative).\n            ', tunable_type=float, default=0, minimum=None), 'statistic_multipliers': TunableList(description='\n            Tunables for adding statistic based multipliers to the payout in the\n            format:\n            \n            amount *= statistic.value\n            ', tunable=TunableStatisticModifierCurve.TunableFactory()), 'display_to_user': Tunable(description='\n            If true, the amount will be displayed in the interaction name.\n            ', tunable_type=bool, default=False), 'notification': OptionalTunable(description='\n            If set and an amount is awarded, displays a dialog to the user.\n            \n            The notification will have access to the amount awarded as a localization token. e.g. {0.Money} \n            ', tunable=TunableUiDialogNotificationSnippet()), 'tags': OptionalTunable(description='\n            If enabled, the simoleons earned will be associated with the listed\n            tags which can be tested against using ObjectiveTests tuning.\n            ', tunable=TunableTags(description='\n                The tag associated with this payment\n                '))}

    def __init__(self, amount, statistic_multipliers, display_to_user, notification, tags, **kwargs):
        super().__init__(**kwargs)
        self._amount = amount
        self._statistic_multipliers = statistic_multipliers
        self._display_to_user = display_to_user
        self._random_amount = None
        self._notification = notification
        self._tags = tags

    @property
    def loot_type(self):
        return interactions.utils.LootType.SIMOLEONS

    def get_simoleon_delta(self, interaction, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        if not self._display_to_user:
            return (0, FundsSource.HOUSEHOLD)
        if not self._tests.run_tests(interaction.get_resolver(target=target, context=context, **interaction_parameters)):
            return (0, FundsSource.HOUSEHOLD)
        sim = context.sim if context is not DEFAULT else DEFAULT
        recipients = interaction.get_participants(participant_type=self.subject, sim=sim, target=target, **interaction_parameters)
        skill_multiplier = 1 if context is DEFAULT else interaction.get_skill_multiplier(interaction.monetary_payout_multipliers, context.sim)
        payment_multiplier = 1.0
        payment_altering_service = services.payment_altering_service()
        if sim is not None:
            payment_multiplier = payment_altering_service.get_money_loot_modifier(sim.id, sim, self.amount, interaction, self._tags)
        return (self.amount*len(recipients)*skill_multiplier*payment_multiplier, FundsSource.HOUSEHOLD)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        interaction = resolver.interaction
        if interaction is not None:
            money_liability = interaction.get_liability(MoneyLiability.LIABILITY_TOKEN)
            if money_liability is None:
                money_liability = MoneyLiability()
                interaction.add_liability(MoneyLiability.LIABILITY_TOKEN, money_liability)
            skill_multiplier = interaction.get_skill_multiplier(interaction.monetary_payout_multipliers, interaction.sim)
        else:
            money_liability = None
            skill_multiplier = 1
        subject_obj = self._get_object_from_recipient(subject)
        payment_multiplier = 1.0
        if subject_obj is not None:
            payment_altering_service = services.payment_altering_service()
            if subject_obj.is_sim is not None:
                payment_multiplier = payment_altering_service.get_money_loot_modifier(subject_obj.id, subject_obj, self.amount, interaction, self._tags)
        amount_multiplier = self._get_multiplier(resolver, subject_obj)*skill_multiplier*payment_multiplier
        amount = round(self.amount*amount_multiplier)
        if amount:
            if money_liability is not None:
                money_liability.amounts[self.subject] += amount
            if interaction is not None:
                interaction_category_tags = interaction.interaction_category_tags
            else:
                interaction_category_tags = frozenset()
            if self._tags is not None:
                interaction_category_tags = interaction_category_tags.union(self._tags)
            if amount < 0:
                subject.household.funds.try_remove_amount(-amount, Consts_pb2.TELEMETRY_INTERACTION_REWARD, subject_obj, require_full_amount=False)
            else:
                subject.household.funds.add(amount, Consts_pb2.TELEMETRY_INTERACTION_REWARD, subject_obj, tags=interaction_category_tags)
            services.get_event_manager().process_event(event_type=TestEvent.MoneyLoot, sim_info=interaction.sim if interaction is not None else None, resolver=resolver, subject=subject, interaction=interaction, amount=amount, tags=interaction_category_tags)
            if self._notification is not None:
                dialog = self._notification(subject, resolver=resolver)
                dialog.show_dialog(additional_tokens=(amount,))

    def _on_apply_completed(self):
        self._random_amount = None

    def _get_display_text(self, resolver=None):
        return LocalizationHelperTuning.MONEY(*self._get_display_text_tokens())

    def _get_display_text_tokens(self, resolver=None):
        return (self.amount,)

    def _get_multiplier(self, resolver, sim):
        amount_multiplier = 1
        if self._statistic_multipliers:
            for statistic_multiplier in self._statistic_multipliers:
                amount_multiplier *= statistic_multiplier.get_multiplier(resolver, sim)
        return amount_multiplier

    @property
    def amount(self):
        if self._random_amount is None:
            self._random_amount = self._amount.random_float()
        return self._random_amount
