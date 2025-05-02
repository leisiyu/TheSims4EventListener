from __future__ import annotationsfrom business.business_enums import BusinessTypefrom objects.game_object_properties import GameObjectPropertyfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.bills import UnpaidBillSourceInfo
    from interactions.payment.payment_dest import _PaymentDest
    from interactions.payment.payment_altering_service import PaymentAlteringService
    from event_testing.resolver import Resolverimport enumfrom protocolbuffers import Consts_pb2from crafting.crafting_tunable import CraftingTuningfrom event_testing.test_events import TestEventfrom objects.components.statistic_component import StatisticComponentfrom sims.bills import Billsfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableVariant, Tunable, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, OptionalTunable, TunableList, TunableFactory, TunableReference, TunableTuple, TunablePackSafeReferenceimport sims4.logfrom interactions import ParticipantType, ParticipantTypeActorTargetSim, ParticipantTypeSingle, ParticipantTypeObject, ParticipantTypeSingleSimfrom interactions.context import InteractionContextfrom interactions.payment.payment_dest import PaymentDestTuningFlags, PaymentDestNone, PaymentDestActiveHousehold, PaymentDestParticipantHousehold, PaymentDestBusiness, PaymentDestStatistic, PaymentDestRentalUnitPropertyOwners, PaymentDestOpenSmallBusinessfrom interactions.payment.payment_info import BusinessPaymentInfo, PaymentInfo, PaymentBusinessRevenueTypefrom interactions.payment_liability import PaymentLiabilityfrom interactions.priority import Priorityfrom restaurants.restaurant_tuning import get_restaurant_zone_directorfrom sims.household_utilities.utility_types import Utilitiesfrom ui.ui_dialog_generic import UiDialogTextInputOkCancelimport objects.components.typesimport serviceslogger = sims4.log.Logger('Payment', default_owner='rmccord')
class _Payment(HasTunableSingletonFactory, AutoFactoryInit):

    @TunableFactory.factory_option
    def payment_destination_option(available_dest_flags=PaymentDestTuningFlags.ALL):
        dest_kwargs = {'no_dest': PaymentDestNone.TunableFactory()}
        default = 'no_dest'
        if available_dest_flags & PaymentDestTuningFlags.ACTIVE_HOUSEHOLD:
            dest_kwargs['active_household'] = PaymentDestActiveHousehold.TunableFactory()
            default = 'active_household'
        if available_dest_flags & PaymentDestTuningFlags.PARTICIPANT_HOUSEHOLD:
            dest_kwargs['participant_household'] = PaymentDestParticipantHousehold.TunableFactory()
            default = 'participant_household'
        if available_dest_flags & PaymentDestTuningFlags.BUSINESS:
            dest_kwargs['business'] = PaymentDestBusiness.TunableFactory()
            default = 'business'
        if available_dest_flags & PaymentDestTuningFlags.STATISTIC:
            dest_kwargs['statistic'] = PaymentDestStatistic.TunableFactory()
            default = 'statistic'
        if available_dest_flags & PaymentDestTuningFlags.RENTAL_UNIT_PROPERY_OWNER:
            dest_kwargs['rental_unit_property_owner'] = PaymentDestRentalUnitPropertyOwners.TunableFactory()
            default = 'rental_unit_property_owner'
        if available_dest_flags & PaymentDestTuningFlags.OPEN_SMALL_BUSINESS:
            dest_kwargs['open_small_business'] = PaymentDestOpenSmallBusiness.TunableFactory()
            default = 'open_small_business'
        return {'payment_destinations': TunableList(description='\n                List of destinations for the payment cost to be given, which are\n                resolved in order until one successfully accepts the payment.\n                ', tunable=TunableVariant(description='\n                    Defines where the cost goes when it is paid for by the payment\n                    source.\n                    ', default=default, **dest_kwargs))}

    def get_amount(self, resolver):
        raise NotImplementedError

    def on_payment(self, amount, resolver, payment_info_override=None, display_zero_payment=False, reason=Consts_pb2.FUNDS_INTERACTION_REWARD):
        if payment_info_override is None:
            cost_info = self.get_payment_info(amount, resolver)
        else:
            cost_info = payment_info_override
        for dest in self.payment_destinations:
            if dest.give_payment(cost_info, reason=reason):
                if abs(amount) > 0 or display_zero_payment:
                    services.get_event_manager().process_event(event_type=TestEvent.PaymentDone, resolver=resolver, payment_info=cost_info, dest=dest)
                return True
        if self.payment_destinations == ():
            services.get_event_manager().process_event(event_type=TestEvent.PaymentDoneToVoid, resolver=resolver, payment_info=cost_info)
        if self.payment_destinations:
            logger.warn('Payment Destinations tuned on {}, but funds never made it there.', self)
        return True

    def try_deduct_payment(self, resolver, sim, fail_callback, source, cost_modifiers):
        return self.make_payment(resolver, sim, source, cost_modifiers)

    def make_payment(self, resolver, sim, source, cost_modifiers, override_amount=None, reason=None):
        (delta, _) = self.get_simoleon_delta(resolver, source, cost_modifiers, override_amount)
        if source.allow_credits:
            amount = -delta
        else:
            amount = max(-delta, 0)
        paid_amount = source.try_remove_funds(sim, amount, resolver, reason)
        if paid_amount is not None:
            return self.on_payment(paid_amount, resolver)
        return False

    def get_simoleon_delta(self, resolver, source, cost_modifiers, override_amount=None):
        if override_amount is None:
            payment_owed = self.get_amount(resolver)
            if payment_owed is None:
                logger.warn('Payment for {} has an invalid cost.', self)
                payment_owed = 0
        else:
            payment_owed = override_amount
        if payment_owed:
            payment_owed *= -cost_modifiers.get_multiplier(resolver)
        return (round(payment_owed), source.funds_source)

    def get_payment_info(self, amount, resolver):
        return PaymentInfo(amount, resolver)

    def get_payment_reason(self):
        return Consts_pb2.FUNDS_INTERACTION_REWARD

    def get_deduction_reason(self):
        pass

class PaymentAmount(_Payment):
    FACTORY_TUNABLES = {'amount': Tunable(description='\n            The amount to pay.\n            ', tunable_type=int, default=0)}

    def get_amount(self, resolver):
        payment_multiplier = 1.0
        payment_altering_service = services.payment_altering_service()
        payer_sim = resolver.get_participant(ParticipantType.Actor)
        if payment_altering_service is not None:
            payment_multiplier = payment_altering_service.get_payment_extra_modifier(payer_sim.sim_id, self.payment_destinations, resolver, self.amount)
        return self.amount*payment_multiplier

class PaymentAmountUpTo(PaymentAmount):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description="\n            The participant Sim from whom we'll collect the amount.\n            ", tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)}

    def get_amount(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is not None and participant is not None:
            return min(self.amount, participant.household.funds.money)
        return self.amount

class PaymentBills(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for whom we need to pay bills.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'locked_args': {'payment_destinations': None}}

    def __init__(self, *args, payment_destinations=None, **kwargs):
        super().__init__(*args, payment_destinations=[], **kwargs)

    def _get_bills_manager(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is not None:
            household = participant.household
            if household is not None:
                return household.bills_manager

    def get_amount(self, resolver):
        bills_manager = self._get_bills_manager(resolver)
        if bills_manager is not None:
            return bills_manager.current_payment_owed

    def on_payment(self, amount, resolver, payment_info_override=None):
        bills_manager = self._get_bills_manager(resolver)
        if bills_manager is not None:
            if bills_manager.current_payment_owed != amount:
                return False
            else:
                bills_manager.pay_bill()
                return True
        return False

class PaymentHousingCosts(PaymentBills):

    def __init__(self, *args, payment_destinations:'_PaymentDest'=None, **kwargs) -> 'None':
        super().__init__(*args, payment_destinations=[], **kwargs)

    def _get_housing_bill_info(self, bills_manager:'Bills') -> 'int':
        return bills_manager.housing_costs_owed

    def get_amount(self, resolver:'Resolver') -> 'Optional[int]':
        bills_manager = self._get_bills_manager(resolver)
        if bills_manager is None:
            return
        return bills_manager.housing_costs_owed

    def on_payment(self, amount:'int', resolver:'Resolver', payment_info_override:'PaymentInfo'=None) -> 'bool':
        bills_manager = self._get_bills_manager(resolver)
        bills_manager.pay_housing_bill()
        return True

class PaymentNonHousingCosts(PaymentBills):
    FACTORY_TUNABLES = {'override_keep_excess_production': OptionalTunable(description='\n            If enabled then ignore the results of the Keep Excess Production test\n            that would normally be used to compute the amount of the utility available\n            for payout.\n            ', tunable=Tunable(description='\n                Use this value and ignore the results of the Keep Excess Production test\n                that would normally be used to compute the amount of the utility available\n                for payout.\n                ', tunable_type=bool, default=True))}

    def __init__(self, *args, payment_destinations:'_PaymentDest'=None, **kwargs) -> 'None':
        super().__init__(*args, payment_destinations=[], **kwargs)
        self._utility_infos = None

    def _get_non_housing_bill_info(self, bills_manager:'Bills') -> 'List[Tuple[UnpaidBillSourceInfo, Utilities]]':
        utility_infos = []
        for utility in Bills.UTILITY_INFO.keys():
            utility_info = bills_manager.get_utility_bill_info(utility)
            if utility_info.is_zero():
                pass
            else:
                utility_infos.append([utility_info, utility])
        return utility_infos

    def get_amount(self, resolver:'Resolver') -> 'Optional[int]':
        bills_manager = self._get_bills_manager(resolver)
        if bills_manager is None:
            return
        self._utility_infos = self._get_non_housing_bill_info(bills_manager)
        if not len(self._utility_infos):
            return
        billable = 0
        for (utility_info, _) in self._utility_infos:
            billable += utility_info.billable_amount
        (total_bill_amount, _) = bills_manager.get_additional_bill_costs()
        return bills_manager.non_housing_costs_owed

    def on_payment(self, amount:'int', resolver:'Resolver', payment_info_override:'PaymentInfo'=None) -> 'bool':
        if self._utility_infos is None:
            return False
        bills_manager = self._get_bills_manager(resolver)
        bills_manager.pay_non_housing_bill()
        return True

class PaymentUtility(PaymentBills):
    FACTORY_TUNABLES = {'utility': TunableEnumEntry(description='\n            The household utility we want to modify.\n            ', tunable_type=Utilities, default=Utilities.POWER), 'override_keep_excess_production': OptionalTunable(description='\n            If enabled then ignore the results of the Keep Excess Production test\n            that would normally be used to compute the amount of the utility available\n            for payout.\n            ', tunable=Tunable(description='\n                Use this value and ignore the results of the Keep Excess Production test\n                that would normally be used to compute the amount of the utility available\n                for payout.\n                ', tunable_type=bool, default=True))}

    def __init__(self, *args, payment_destinations=None, **kwargs):
        super().__init__(*args, payment_destinations=[], **kwargs)
        self._utility_info = None

    def _get_utility_bill_info(self, bills_manager):
        utility_info = bills_manager.get_utility_bill_info(self.utility)
        if utility_info is None:
            return
        unpaid_info = bills_manager.current_source_owed(self.utility)
        if unpaid_info is not None:
            utility_info -= unpaid_info
        return utility_info

    def get_amount(self, resolver):
        bills_manager = self._get_bills_manager(resolver)
        if bills_manager is None:
            return
        self._utility_info = self._get_utility_bill_info(bills_manager)
        if self._utility_info is None:
            return
        return self._utility_info.billable_amount

    def on_payment(self, amount, resolver, payment_info_override=None):
        if self._utility_info is None:
            return False
        bills_manager = self._get_bills_manager(resolver)
        if bills_manager is not None:
            utility_info = self._get_utility_bill_info(bills_manager)
            if utility_info.billable_amount != self._utility_info.billable_amount or self._utility_info.billable_amount != amount:
                return False
            else:
                bills_manager.pay_source_bill(self.utility, self._utility_info)
                return True
        return False

class PaymentCatalogValue(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for which we want to pay an amount equal to its\n            catalog value.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_amount(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is not None:
            return participant.definition.price

class PaymentCurrentValue(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for which we want to pay an amount equal to its\n            current value.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_amount(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is not None:
            return participant.current_value

class PaymentBaseRetailValue(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for which we want to pay an amount equal to its\n            retail value.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_amount(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is not None:
            retail_component = participant.get_component(objects.components.types.RETAIL_COMPONENT)
            if retail_component is not None:
                return retail_component.get_retail_value()
            else:
                return participant.current_value

class PaymentBaseDiningBill(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for Sim is paying the bill so we can use that Sim\n            to determine the correct dining group and meal cost.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'locked_args': {'payment_destinations': ()}}

    def get_amount(self, resolver):
        group = self._get_group(resolver)
        if group is not None:
            return group.meal_cost
        return 0

    def on_payment(self, amount, resolver, payment_info_override=None):
        super().on_payment(amount, resolver)
        group = self._get_group(resolver)
        if group is not None:
            group.pay_for_group(amount)
            return True
        return False

    def _get_group(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is None:
            return
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        sim_instance = participant.get_sim_instance()
        if sim_instance is None:
            return
        groups = zone_director.get_dining_groups_by_sim(sim_instance)
        return next(iter(groups), None)

class PaymentSmallBusinessEntryFee(_Payment):
    FACTORY_TUNABLES = {'business_owner': TunableEnumEntry(description='\n            The reference to the sim that owns the business we want to look the fees for.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.CurrentlyOpenSmallBusinessOwner), 'locked_args': {'payment_destinations': ()}}

    def get_amount(self, resolver) -> 'int':
        business_manager = None
        if self.business_owner is None:
            business_manager = services.business_service().get_business_manager_for_zone()
        else:
            sim_info = resolver.get_participant(self.business_owner)
            if sim_info is not None:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        entry_fee = 0
        if business_manager.business_type == BusinessType.SMALL_BUSINESS:
            entry_fee = business_manager.small_business_income_data.get_entry_fee()
        return entry_fee

    def get_payment_info(self, amount, resolver) -> 'BusinessPaymentInfo':
        return BusinessPaymentInfo(amount, resolver, revenue_type=PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_ENTRY_FEE)

class PaymentSmallBusinessHourlyFee(_Payment):
    FACTORY_TUNABLES = {'business_owner': TunableEnumEntry(description="\n            The reference to the sim that owns the business we want to look the fees for. If empty, it'll use\n            the currently opened business' info.\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.CurrentlyOpenSmallBusinessOwner), 'locked_args': {'payment_destinations': ()}}

    def get_amount(self, resolver) -> 'int':
        business_manager = None
        if self.business_owner is None:
            business_manager = services.business_service().get_business_manager_for_zone()
        else:
            sim_info = resolver.get_participant(self.business_owner)
            if sim_info is not None:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        hourly_fee = 0
        if business_manager.business_type == BusinessType.SMALL_BUSINESS:
            hourly_fee = business_manager.small_business_income_data.get_hourly_fee()
        return hourly_fee

    def get_payment_info(self, amount, resolver) -> 'BusinessPaymentInfo':
        return BusinessPaymentInfo(amount, resolver, revenue_type=PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_HOURLY_FEE)

class PaymentSmallBusinessLightRetailFee(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for which we want to pay an amount equal to its\n            retail value.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'locked_args': {'payment_destinations': ()}}

    def get_amount(self, resolver) -> 'int':
        participant = resolver.get_participant(self.participant)
        light_retail_fee = 0
        if participant is not None:
            business_manager = services.business_service().get_business_manager_for_zone()
            simoleon_value = participant.get_object_property(GameObjectProperty.MODIFIED_PRICE)
            mark_up_value = 0
            if business_manager.business_type == BusinessType.SMALL_BUSINESS:
                mark_up_value = business_manager.small_business_income_data.get_markup_multiplier()
            servings = participant.get_stat_instance(CraftingTuning.SERVINGS_STATISTIC)
            num_servings = servings.tracker.get_value(CraftingTuning.SERVINGS_STATISTIC) if servings is not None else 0
            if num_servings > 0:
                simoleon_value = num_servings*simoleon_value
            light_retail_fee = int(simoleon_value*mark_up_value)
        return light_retail_fee

    def get_payment_info(self, amount, resolver) -> 'BusinessPaymentInfo':
        return BusinessPaymentInfo(amount, resolver, revenue_type=PaymentBusinessRevenueType.SMALL_BUSINESS_LIGHT_RETAIL_FEE)

class PaymentSmallBusinessEmployeePayment(PaymentAmount):

    def get_payment_reason(self):
        return Consts_pb2.FUNDS_SMALL_BUSINESS_EMPLOYEE

    def get_deduction_reason(self):
        return Consts_pb2.FUNDS_SMALL_BUSINESS_EMPLOYEE

class PaymentSmallBusinessFee(_Payment):
    FACTORY_TUNABLES = {'payment_type': TunableVariant(description='\n            Type of Small Business payment to use.\n            ', small_business_entry_fee_payment=PaymentSmallBusinessEntryFee.TunableFactory(), small_business_hourly_fee_payment=PaymentSmallBusinessHourlyFee.TunableFactory(), small_business_light_retail_fee_payment=PaymentSmallBusinessLightRetailFee.TunableFactory(), small_business_employee_payment=PaymentSmallBusinessEmployeePayment.TunableFactory())}

    def try_deduct_payment(self, resolver, sim, fail_callback, source, cost_modifiers):
        reason = self.payment_type.get_deduction_reason()
        return self.make_payment(resolver, sim, source, cost_modifiers, reason=reason)

    def on_payment(self, amount, resolver, payment_info_override=None):
        payment_done = super().on_payment(amount, resolver, payment_info_override, True, self.get_payment_reason())
        if payment_done and amount == 0:
            business_manager = services.business_service().get_business_manager_for_zone()
            active_household = services.active_household()
            if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS and active_household is not None:
                active_household.funds.send_money_update(vfx_amount=0, reason=business_manager.get_customer_appreciation_day_reason())

    def get_amount(self, resolver) -> 'int':
        return self.payment_type.get_amount(resolver)

    def get_payment_info(self, amount, resolver) -> 'BusinessPaymentInfo':
        return self.payment_type.get_payment_info(amount, resolver)

    def get_payment_reason(self):
        return self.payment_type.get_payment_reason()

class _PaymentWrapper(_Payment):
    FACTORY_TUNABLES = {'wrapped_cost': TunableVariant(description='\n            The amount to pay, affected by wrapped payment type. If this is 0,\n            then this operation costs nothing.\n            ', amount=PaymentAmount.TunableFactory(), amount_up_to=PaymentAmountUpTo.TunableFactory(), catalog_value=PaymentCatalogValue.TunableFactory(), current_value=PaymentCurrentValue.TunableFactory(), base_retail_value=PaymentBaseRetailValue.TunableFactory(), default='amount'), 'locked_args': {'payment_destinations': ()}}

    def on_payment(self, amount, resolver, payment_info_override=None):
        return self.wrapped_cost.on_payment(amount, resolver, payment_info_override=self.get_payment_info(amount, resolver))

class PaymentBusinessAmount(_PaymentWrapper):

    @staticmethod
    def _verify_tunable_callback(cls, tunable_name, source, value):
        if value.generate_revenue is not None and not value.wrapped_cost.payment_destinations:
            logger.error('Business Payment from {} is expected to generate revenue, but does not pay to any destinations.', source)

    FACTORY_TUNABLES = {'generate_revenue': OptionalTunable(description='\n            If this is enabled, then the business provider will gain the spent\n            amount as revenue. If this is not enabled, then the expense is\n            incurred and no revenue is generated.\n            \n            NOTE: You still need to set the payment destination under the\n            payment cost to actually pay the business.\n            ', tunable=TunableEnumEntry(description='\n                The type of revenue generated by this interaction. If the type\n                is Item Sold, the items old count for the store will increment.\n                If the type is Seed Money, the money is added to the store\n                without the sold item count being touched.\n                ', tunable_type=PaymentBusinessRevenueType, default=PaymentBusinessRevenueType.ITEM_SOLD), enabled_by_default=True), 'verify_tunable_callback': _verify_tunable_callback}

    def get_amount(self, resolver):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            amount = self.wrapped_cost.get_amount(resolver)
            if self.generate_revenue == PaymentBusinessRevenueType.ITEM_SOLD:
                return business_manager.get_value_with_markup(amount)
            return amount
        return self.wrapped_cost.get_amount(resolver)

    def get_payment_info(self, amount, resolver):
        return BusinessPaymentInfo(amount, resolver, revenue_type=self.generate_revenue)

class PaymentMarketplaceListing(_Payment):
    FACTORY_TUNABLES = {'seller_sim': TunableEnumEntry(description="\n            The sim doing the selling. Might affect price, but doesn't \n            determine the actual payment source.\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'object_being_listed': TunableEnumEntry(description='\n            The object being listed. This will be used to calculate the cost.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object)}

    def get_amount(self, resolver):
        seller_sim_info = resolver.get_participant(self.seller_sim)
        object_being_listed = resolver.get_participant(self.object_being_listed)
        from objects.components.object_marketplace_component import ObjectMarketplaceComponent
        return ObjectMarketplaceComponent.get_listing_cost(seller_sim_info, object_being_listed)

class PaymentFashionMarketplaceListing(_Payment):
    FACTORY_TUNABLES = {'seller_sim': TunableEnumEntry(description="\n            The sim doing the selling. Might affect price, but doesn't \n            determine the actual payment source.\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'object_being_listed': TunableEnumEntry(description='\n            The object being listed. This will be used to calculate the cost.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object)}

    def get_amount(self, resolver):
        seller_sim_info = resolver.get_participant(self.seller_sim)
        object_being_listed = resolver.get_participant(self.object_being_listed)
        from objects.components.object_fashion_marketplace_component import ObjectFashionMarketplaceComponent
        return ObjectFashionMarketplaceComponent.get_listing_cost(seller_sim_info, object_being_listed)

class PaymentFromLiability(_Payment):
    FACTORY_TUNABLES = {'locked_args': {'payment_destinations': ()}}

    def on_payment(self, amount, resolver, payment_info_override=None):
        interaction = resolver.interaction
        payment_liability = interaction.get_liability(PaymentLiability.LIABILITY_TOKEN)
        if payment_liability is not None:
            self.payment_destinations = payment_liability.payment_destinations
        super().on_payment(amount, resolver, payment_info_override)

    def get_amount(self, resolver):
        interaction = resolver.interaction
        if interaction is not None:
            payment_liability = interaction.get_liability(PaymentLiability.LIABILITY_TOKEN)
            if payment_liability is not None:
                return payment_liability.amount
            logger.error('Interaction {} has a payment element with liability payment cost but no liability', interaction)
            return 0
        else:
            return 0

class PaymentStatisticOnSim(_Payment):
    FACTORY_TUNABLES = {'sim': TunableEnumEntry(description='\n            The Sim who we will check for the tuned statistic.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'statistic': TunablePackSafeReference(description='\n            The statistic that we will check the Sim for and whose value will determine the payment amount.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))}

    def get_amount(self, resolver) -> 'float':
        sim_info = resolver.get_participant(self.sim)
        statistic = sim_info.statistic_tracker.get_statistic(self.statistic)
        if statistic is None:
            return self.statistic.default_value
        return statistic.get_value()

    def get_simoleon_delta(self, resolver, source, cost_modifiers, override_amount=None):
        (payment_owed, funds_source) = super().get_simoleon_delta(resolver, source, cost_modifiers, override_amount)
        payment_multiplier = 1.0
        payment_altering_service = services.payment_altering_service()
        payer_sim = resolver.get_participant(self.sim)
        if payment_altering_service is not None:
            payment_multiplier = payment_altering_service.get_payment_extra_modifier(payer_sim.sim_id, self.payment_destinations, resolver, payment_owed)
        return (payment_owed*payment_multiplier, funds_source)

class PaymentMultiServingType(enum.Int):
    AllServings = 1
    OneServing = 2
    RemainingServings = 3
    RemainingServingsMinusOne = 4

class PaymentMultiServing(_Payment):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for which we want to pay and check its servings\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'payment_multi_serving_type': TunableEnumEntry(description='\n            How many servings should be paid\n            ', tunable_type=PaymentMultiServingType, default=PaymentMultiServingType.RemainingServings)}

    def get_amount(self, resolver):
        participant = resolver.get_participant(self.participant)
        if participant is None:
            return 0
        servings = participant.get_stat_instance(CraftingTuning.SERVINGS_STATISTIC)
        if servings is None:
            return participant.current_value
        current_servings = servings.tracker.get_value(CraftingTuning.SERVINGS_STATISTIC)
        if current_servings == 0:
            return 0
        if participant.crafting_component is not None:
            serving_value = participant.crafting_component.get_simoleon_value()
            if self.payment_multi_serving_type == PaymentMultiServingType.AllServings:
                return participant.current_value
            if self.payment_multi_serving_type == PaymentMultiServingType.RemainingServings:
                quantity = current_servings
            elif self.payment_multi_serving_type == PaymentMultiServingType.RemainingServingsMinusOne:
                quantity = current_servings - 1
            elif self.payment_multi_serving_type == PaymentMultiServingType.OneServing:
                quantity = 1
            return quantity*serving_value
        return participant.current_value
TEXT_INPUT_PAYMENT_VALUE = 'payment_value'
class PaymentDialog(_Payment):
    FACTORY_TUNABLES = {'input_dialog': UiDialogTextInputOkCancel.TunableFactory(description='\n            The dialog that is displayed. The amount the user enters into the\n            input is used as the payment amount.\n            ', text_inputs=(TEXT_INPUT_PAYMENT_VALUE,)), 'dest_exceed_tooltip': OptionalTunable(description='\n             If enabled, allows specification of a tooltip to display if\n             the user has entered a value that exceeds what the destination\n             can hold.\n             \n             Additional tokens are source max, dest value, minimum\n             ', tunable=TunableLocalizedStringFactory()), 'source_exceed_tooltip': OptionalTunable(description='\n             If enabled, allows specification of a tooltip to display if\n             the user has entered a value that exceeds the amount in the source.\n             \n             Additional tokens are source max, dest value, minimum\n             ', tunable=TunableLocalizedStringFactory()), 'below_min_tooltip': OptionalTunable(description='\n             If enabled, allows specification of a tooltip to display if\n             the user has entered a value that is below minimum amount allowed.\n             \n             Additional tokens are source max, dest value, minimum\n             ', tunable=TunableLocalizedStringFactory()), 'success_continuation': OptionalTunable(description=' \n            If tuned to an interaction, we will push that interaction as a\n            continuation if we receive a valid dialog response. Additionally, we\n            will attach a payment liability to that interaction so that the\n            payment can be resolved on the sequence of that interaction or on a\n            later continuation. The payment liability will store the entered\n            value and tuned destination, but will not respect all other tuned\n            options.To trigger that payment, add a payment basic extra to that\n            interaction and select the "Liability" payment cost.\n            ', tunable=TunableTuple(interaction=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), target_participant=TunableEnumEntry(description='\n                    The participant that is to be used as the target of the\n                    continuation interaction.\n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Object)))}

    def get_amount(self, resolver):
        return 0

    def try_deduct_payment(self, resolver, sim, fail_callback, source, cost_modifiers):
        max_value = None
        min_value = None
        dest_funds = 0
        invalid_max_tooltip = None
        invalid_min_tooltip = None
        for dest in self.payment_destinations:
            (max_value, dest_funds, min_value) = dest.get_funds_info(resolver)
            if max_value is not None:
                break
        source_max = source.max_funds(sim, resolver)
        if max_value is None or source_max < max_value:
            max_value = source_max
            if self.source_exceed_tooltip is not None:
                invalid_max_tooltip = self.source_exceed_tooltip
        elif self.dest_exceed_tooltip is not None:
            invalid_max_tooltip = self.dest_exceed_tooltip
        if min_value is not None:
            invalid_min_tooltip = self.below_min_tooltip
        dialog = self.input_dialog(sim, resolver, max_value=max_value, invalid_max_tooltip=invalid_max_tooltip, min_value=min_value, invalid_min_tooltip=invalid_min_tooltip)

        def on_response(value_dialog):
            if not value_dialog.accepted:
                return
            new_value = value_dialog.text_input_responses.get(TEXT_INPUT_PAYMENT_VALUE)
            try:
                new_value = int(new_value)
            except:
                if fail_callback:
                    fail_callback()
                return
            if self.success_continuation is not None:
                context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
                target = resolver.get_participant(self.success_continuation.target_participant)
                if target.is_sim:
                    target = target.get_sim_instance()
                    if target is None:
                        return
                liability = PaymentLiability(new_value, self.payment_destinations)
                liabilities = ((PaymentLiability.LIABILITY_TOKEN, liability),)
                sim.push_super_affordance(self.success_continuation.interaction, target, context, liabilities=liabilities)
            else:
                self.make_payment(resolver, sim, source, cost_modifiers, new_value)

        if min_value is None:
            min_value = 0
        dialog.show_dialog(on_response=on_response, additional_tokens=(source_max, dest_funds, min_value))
        return True
