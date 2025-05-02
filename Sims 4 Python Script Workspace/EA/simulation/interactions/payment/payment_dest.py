from __future__ import annotationsfrom business.business_tests import BusinessManagerFinderVariantfrom event_testing.resolver import DataResolverfrom protocolbuffers import Consts_pb2from business.business_enums import BusinessTypefrom interactions import ParticipantType, ParticipantTypeSingleSimfrom interactions.payment.payment_info import PaymentBusinessRevenueType, BusinessPaymentInfo, PaymentInfofrom sims.funds import get_funds_for_source, FundsSourcefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableReference, OptionalTunable, TunablePercent, Tunableimport enumimport servicesimport sims4.logfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from small_business.small_business_manager import SmallBusinessManagerlogger = sims4.log.Logger('Payment', default_owner='rmccord')
class PaymentDestTuningFlags(enum.IntFlags):
    NO_DEST = 0
    ACTIVE_HOUSEHOLD = 1
    PARTICIPANT_HOUSEHOLD = 2
    BUSINESS = 4
    STATISTIC = 8
    RENTAL_UNIT_PROPERY_OWNER = 16
    OPEN_SMALL_BUSINESS = 32
    ALL = NO_DEST | ACTIVE_HOUSEHOLD | PARTICIPANT_HOUSEHOLD | BUSINESS | STATISTIC | RENTAL_UNIT_PROPERY_OWNER | OPEN_SMALL_BUSINESS

class _PaymentDest(HasTunableSingletonFactory, AutoFactoryInit):

    def give_payment(self, cost_info, reason):
        raise NotImplementedError
        return False

    def get_funds_info(self, resolver):
        return (None, 0, None)

    def should_handle_interaction_sale_info(self, small_business:'SmallBusinessManager', resolver:'DataResolver') -> 'Tuple[bool, bool]':
        return (False, False)

class PaymentDestNone(_PaymentDest):

    def give_payment(self, cost_info, reason):
        return True

class PaymentDestActiveHousehold(_PaymentDest):

    def give_payment(self, cost_info, reason):
        household = services.active_household()
        if household is not None:
            amount = abs(cost_info.amount)
            if amount > 0:
                household.funds.add(amount, reason)
            return True
        return False

    def get_funds_info(self, resolver):
        household = services.active_household()
        if household is not None:
            money = household.funds.money
            return (household.funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

    def should_handle_interaction_sale_info(self, small_business:'SmallBusinessManager', resolver:'DataResolver') -> 'Tuple[bool, bool]':
        return (True, True)

class PaymentDestParticipantHousehold(_PaymentDest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description="\n            The participant whose household will accept the payment. If the\n            participant is not a Sim, we will use the participant's owning\n            household.\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def give_payment(self, cost_info, reason):
        household = self._get_household(cost_info.resolver)
        tags = self._get_interaction_tags(cost_info)
        if household is not None:
            amount = abs(cost_info.amount)
            if amount > 0:
                household.funds.add(amount, reason, tags=tags)
            return True
        return False

    def get_funds_info(self, resolver):
        household = self._get_household(resolver)
        if household is not None:
            money = household.funds.money
            return (household.funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

    def _get_household(self, resolver):
        participant = resolver.get_participant(self.participant)
        household = None
        if participant is not None:
            if participant.is_sim:
                household = participant.household
            else:
                household_owner_id = participant.get_household_owner_id()
                household = services.household_manager().get(household_owner_id)
        return household

    def _get_interaction_tags(self, cost_info:'PaymentInfo'):
        if cost_info.resolver is None:
            return
        return cost_info.resolver.interaction.interaction_category_tags

    def should_handle_interaction_sale_info(self, small_business:'SmallBusinessManager', resolver:'DataResolver') -> 'Tuple[bool, bool]':
        should_handle_interaction_sale = True
        already_paid_to_owner = False
        is_destination_an_employee = False
        participant = resolver.get_participant(self.participant)
        if participant is not None:
            if participant.is_sim:
                dest_household = participant.household
                dest_sim_info = participant.sim_info
                dest_household_id = dest_household.id
                is_destination_an_employee = small_business.is_employee(dest_sim_info)
            else:
                dest_household_owner_id = participant.get_household_owner_id()
                dest_household = services.household_manager().get(dest_household_owner_id)
                dest_household_id = dest_household.id
            already_paid_to_owner = small_business.owner_household_id == dest_household_id
        if not is_destination_an_employee:
            should_handle_interaction_sale = False
        return (should_handle_interaction_sale, already_paid_to_owner)

class PaymentDestBusiness(_PaymentDest):

    def give_payment(self, cost_info, reason):
        if not isinstance(cost_info, BusinessPaymentInfo):
            revenue_type = None
        else:
            revenue_type = cost_info.revenue_type
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.modify_funds(cost_info.amount, from_item_sold=revenue_type == PaymentBusinessRevenueType.ITEM_SOLD)
            return True
        return False

    def get_funds_info(self, resolver):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            money = business_manager.funds.money
            return (business_manager.funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

class PaymentDestOpenSmallBusiness(_PaymentDest):

    def give_payment(self, cost_info, reason):
        small_business_funds = self._get_small_business_funds()
        if small_business_funds is not None:
            reason = PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE
            if cost_info.revenue_type == PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_HOURLY_FEE:
                reason = Consts_pb2.FUNDS_SMALL_BUSINESS_HOURLY_FEE_REWARD
            elif cost_info.revenue_type == PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_ENTRY_FEE:
                reason = Consts_pb2.FUNDS_SMALL_BUSINESS_ENTRY_FEE_REWARD
            elif cost_info.revenue_type == PaymentBusinessRevenueType.SMALL_BUSINESS_LIGHT_RETAIL_FEE:
                reason = Consts_pb2.FUNDS_SMALL_BUSINESS_LIGHT_RETAIL_REWARD
            elif cost_info.revenue_type == PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE:
                reason = Consts_pb2.FUNDS_SMALL_BUSINESS_INTERACTION_REWARD
            elif cost_info.revenue_type == PaymentBusinessRevenueType.SMALL_BUSINESS_OPENING_FEE:
                reason = Consts_pb2.FUNDS_SMALL_BUSINESS_OPEN_BUSINESS
            small_business_funds.add(cost_info.amount, reason=reason)
            return True
        return False

    def get_funds_info(self, resolver):
        small_business_funds = self._get_small_business_funds()
        if small_business_funds is not None:
            money = small_business_funds.money
            return (small_business_funds.MAX_FUNDS - money, money, None)
        return (None, 0, None)

    def _get_small_business_funds(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
            owner_sim_info = services.sim_info_manager().get(business_manager.owner_sim_id)
            owner_funds = get_funds_for_source(FundsSource.HOUSEHOLD, sim=owner_sim_info)
            return owner_funds

    def should_handle_interaction_sale_info(self, small_business:'SmallBusinessManager', resolver:'DataResolver') -> 'Tuple[bool, bool]':
        return (True, True)

class PaymentDestRentalUnitPropertyOwners(_PaymentDest):
    FACTORY_TUNABLES = {'target_business': BusinessManagerFinderVariant(description='\n            The target business unit which will be used to generate payment. \n            '), 'should_modify_funds': Tunable(description='\n            If set, household funds for property owner will be modified.\n            ', tunable_type=bool, default=True)}

    def give_payment(self, cost_info:'BusinessPaymentInfo', reason) -> 'bool':
        participant = self.target_business.participant
        participant_targets = cost_info.resolver.get_participants(participant_type=participant)
        rental_unit_managers = self.target_business.get_business_managers(list(participant_targets))
        rental_unit_manager = next(iter(rental_unit_managers), None)
        if rental_unit_manager is None or rental_unit_manager.business_type != BusinessType.RENTAL_UNIT:
            return False
        rental_unit_manager.handle_tenant_paid_rent_event(should_modify_funds=self.should_modify_funds)
        return True

class PaymentDestStatistic(_PaymentDest):
    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            The statistic that should accept the payment.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'participant': TunableEnumEntry(description='\n            The participant whose statistic will accept the payment.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'is_debt': OptionalTunable(description='\n            True if the statistics is a debt, otherwise False.\n            ', tunable=TunablePercent(description='\n                Percent of debt that is minimum payment.\n                ', default=5), disabled_name='False', enabled_name='True')}

    def give_payment(self, cost_info, reason):
        participant = cost_info.resolver.get_participant(self.participant)
        stat = None
        if participant is not None:
            tracker = participant.get_tracker(self.statistic)
            if tracker is not None:
                stat = tracker.get_statistic(self.statistic)
        if stat is not None:
            amount = cost_info.amount
            if self.is_debt:
                amount = -amount
            stat.add_value(amount)
            return True
        return False

    def get_funds_info(self, resolver):
        participant = resolver.get_participant(self.participant)
        stat = None
        if participant is not None:
            tracker = participant.get_tracker(self.statistic)
            if tracker is not None:
                stat = tracker.get_statistic(self.statistic)
        if stat is not None:
            value = stat.get_value()
            if self.is_debt is not None:
                return (value, value, int(self.is_debt*value))
            else:
                return (stat.max_value - value, value, None)
        return (None, 0, None)
