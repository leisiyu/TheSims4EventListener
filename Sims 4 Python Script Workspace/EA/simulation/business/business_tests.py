from __future__ import annotationsimport sims4from business.business_enums import BusinessQualityType, BusinessTypefrom business.business_rule_enums import BusinessRuleStatefrom event_testing import test_basefrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom interactions import ParticipantType, ParticipantTypeHousehold, ParticipantTypeSingleSim, ParticipantTypeZoneIdfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, OptionalTunable, TunableInterval, TunableThreshold, TunableSet, TunablePackSafeReference, TunableVariantfrom sims4.tuning.tunable import Tunablefrom sims4.utils import classpropertyfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport servicesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from business.business_manager import BusinessManager
    from sims.household import Household
    from sims.sim_info import SimInfologger = sims4.log.Logger('BusinessTests', default_owner='jsampson')
class BusinessAllowsNewCustomersTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'customers_allowed': Tunable(description='\n            If checked this will test if new customers are currently allowed\n            to show up on a business lot. \n            \n            If unchecked this will test if new customers are not allowed to \n            show up currently. \n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {}

    def __call__(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return TestResult(False, 'Not currently on a business lot.')
        zone_director = services.venue_service().get_zone_director()
        if zone_director is None:
            return TestResult(False, 'There is no zone_director for this zone.')
        from business.business_zone_director_mixin import CustomerAndEmployeeZoneDirectorMixin
        if not isinstance(zone_director, CustomerAndEmployeeZoneDirectorMixin):
            return TestResult(False, 'The current zone director does not implement the CustomerAndEmployeeZoneDirectorMixin interface.')
        if zone_director.allows_new_customers():
            if not self.customers_allowed:
                return TestResult(False, 'Business does allow new customers but the test is for not allowing them.')
        elif self.customers_allowed:
            return TestResult(False, 'Business does not allow new customers and the test is for allowing them.')
        return TestResult.TRUE

class ActiveZone(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def get_zone_id(self, **kwargs) -> 'Optional[int]':
        return services.current_zone_id()

class PickedZoneIds(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {'picked_zone_ids': ParticipantType.PickedZoneId}

    def get_zone_id(self, *, picked_zone_ids, **kwargs) -> 'int':
        if not picked_zone_ids:
            logger.error('Zone Test could not find a picked zone id.')
            return
        return picked_zone_ids[0]

class BusinessSettingTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'quality_setting': OptionalTunable(description='\n            A test to see if the current business has certain settings set by the owner.\n            ', tunable=TunableWhiteBlackList(description='\n                Use of this white/black list will check whether or not the \n                current on-lot business is set to certain quality settings.\n                ', tunable=TunableEnumEntry(description='\n                    Business Quality Type from business settings.\n                    ', tunable_type=BusinessQualityType, default=BusinessQualityType.INVALID, invalid_enums=(BusinessQualityType.INVALID,))), disabled_name='ignore', enabled_name='test'), 'star_rating': OptionalTunable(description='\n            A test to see if the current business is within a star rating range.\n            ', tunable=TunableInterval(description="\n                If the business's star rating is within this range, this test passes.\n                ", tunable_type=float, default_lower=0, default_upper=5, minimum=0), disabled_name='ignore', enabled_name='test'), 'zone': TunableVariant(description="\n            The zone to check if it's a business and has the tuned criteria.\n            ", use_current_zone=ActiveZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), default='use_current_zone')}

    def get_expected_args(self):
        return self.zone.get_expected_args()

    def __call__(self, *args, **kwargs):
        zone_id = self.zone.get_zone_id(**kwargs)
        if not zone_id:
            return TestResult(False, "BusinessSettingTest couldn't find a zone to test.", tooltip=self.tooltip)
        business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        if business_manager is None:
            return TestResult(False, 'Not currently on a business lot.')
        if self.quality_setting is not None and not self.quality_setting.test_item(business_manager.quality_setting):
            return TestResult(False, 'Business is set to {}'.format(business_manager.quality_setting))
        if self.star_rating is not None:
            business_star_rating = business_manager.get_star_rating()
            if business_star_rating not in self.star_rating:
                return TestResult(False, 'Business star rating is {}'.format(business_star_rating))
        return TestResult.TRUE

class RentalUnitStarRatingTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    test_events = (TestEvent.RentalUnitStarRatingChanged,)
    USES_EVENT_DATA = False
    PROPERTY_OWNER = 0
    TENANT = 1
    FACTORY_TUNABLES = {'star_rating': TunableInterval(description='\n            A test to see if an owned rental unit is within a star rating range.\n            ', tunable_type=float, default_lower=0, default_upper=5, minimum=0), 'subject': TunableEnumEntry(description='\n            The sim whose household is the object of this unit star rating test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'target': TunableVariant(description='\n            The role the subject has in relation to the household being tested. \n            ', locked_args={'property_owner': PROPERTY_OWNER, 'tenant': TENANT}, default='property_owner')}

    def get_expected_args(self):
        return {'test_targets': self.subject}

    def __call__(self, test_targets:'Set[Any]') -> 'TestResult':
        target_sim = next(iter(test_targets), None)
        if target_sim is None:
            return TestResult(False, 'No sim was passed in.', tooltip=self.tooltip)
        sim_household = target_sim.household
        if sim_household is None:
            return TestResult(False, 'No sim household Found', tooltip=self.tooltip)
        if self.target == RentalUnitStarRatingTest.PROPERTY_OWNER:
            business_tracker = services.business_service().get_business_tracker_for_household(sim_household.id, BusinessType.RENTAL_UNIT)
            if business_tracker is None:
                return TestResult(False, 'No Business Tracker Found for household id {}'.format(sim_household.id), tooltip=self.tooltip)
            if business_tracker.business_managers is None:
                return TestResult(False, 'Business Tracker contains no Rental Unit Managers', tooltip=self.tooltip)
            for rental_unit_manager in business_tracker.business_managers.values():
                if rental_unit_manager.get_star_rating() in self.star_rating:
                    return TestResult.TRUE
        elif self.target == RentalUnitStarRatingTest.TENANT:
            rental_unit_manager = services.business_service().get_business_manager_for_zone(sim_household.home_zone_id)
            if rental_unit_manager is None or rental_unit_manager.business_type != BusinessType.RENTAL_UNIT:
                return TestResult(False, "No rental unit business found for tenant's home zone", tooltip=self.tooltip)
            if rental_unit_manager.get_star_rating() in self.star_rating:
                return TestResult.TRUE
        return TestResult(False, 'No rental unit had a star rating between {} and {}'.format(self.star_rating.lower_bound, self.star_rating.upper_bound), tooltip=self.tooltip)

class BusinessManagerFinderVariant(TunableVariant):

    class _FromSimParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                Participant that resolves to a tenant sim of a multi unit business.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor, invalid_enums=(ParticipantTypeSingleSim.Invalid,))}

        @classmethod
        def get_business_manager(cls, sim_info:'SimInfo') -> 'BusinessManager':
            return services.business_service().get_business_manager_for_zone(zone_id=sim_info.household.home_zone_id)

        @classmethod
        def get_business_managers(cls, sim_infos:'List[SimInfo]') -> 'List[BusinessManager]':
            business_managers = []
            for sim_info in sim_infos:
                business_manager = services.business_service().get_business_manager_for_zone(zone_id=sim_info.household.home_zone_id)
                if business_manager is not None:
                    business_managers.append(business_manager)
            return business_managers

    class _FromHouseholdParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                Participant that resolves to a tenant household of a multi unit business.\n                ', tunable_type=ParticipantTypeHousehold, default=ParticipantTypeHousehold.TargetHousehold)}

        @classmethod
        def get_business_manager(cls, household:'Household') -> 'BusinessManager':
            return services.business_service().get_business_manager_for_zone(zone_id=household.home_zone_id)

        @classmethod
        def get_business_managers(cls, households:'List[Household]') -> 'List[BusinessManager]':
            business_managers = []
            for household in households:
                business_manager = services.business_service().get_business_manager_for_zone(zone_id=household.home_zone_id)
                if business_manager is not None:
                    business_managers.append(business_manager)
            return business_managers

    class _FromTenantHouseholds(HasTunableSingletonFactory, AutoFactoryInit):

        @classproperty
        def participant(cls) -> 'ParticipantType':
            return ParticipantType.ActorTenantHouseholds

        @classmethod
        def get_business_managers(cls, household_ids:'List[int]') -> 'List[BusinessManager]':
            business_managers = []
            for household_id in household_ids:
                household = services.household_manager().get(household_id)
                if household is not None:
                    manager = services.business_service().get_business_manager_for_zone(zone_id=household.home_zone_id)
                    if manager is not None:
                        business_managers.append(manager)
            return business_managers

    class _FromZone(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                Participant that resolves to zone id of a multi unit business.\n                ', tunable_type=ParticipantTypeZoneId, default=ParticipantTypeZoneId.PickedZoneId)}

        @classmethod
        def get_business_manager(cls, zone_id:'int') -> 'BusinessManager':
            return services.business_service().get_business_manager_for_zone(zone_id=zone_id)

        @classmethod
        def get_business_managers(cls, zone_ids:'List[int]') -> 'List[BusinessManager]':
            business_managers = []
            for zone_id in zone_ids:
                business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
                if business_manager is not None:
                    business_managers.append(business_manager)
            return business_managers

    __slots__ = ()

    def __init__(self, allow_multiples:'bool'=False, default:'str'='zone', **kwargs):
        if allow_multiples:
            kwargs['tenant_households'] = BusinessManagerFinderVariant._FromTenantHouseholds.TunableFactory()
        super().__init__(zone=BusinessManagerFinderVariant._FromZone.TunableFactory(), household=BusinessManagerFinderVariant._FromHouseholdParticipant.TunableFactory(), sim=BusinessManagerFinderVariant._FromSimParticipant.TunableFactory(), default=default, **kwargs)

class RentalBusinessIsGracePeriodTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'target_business': BusinessManagerFinderVariant(description='\n            Method by which to find the business of interest.\n            '), 'negate': Tunable(description='\n            If checked then the result of the test will be negated.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.target_business.participant}

    def __call__(self, test_targets:'Set[Any]') -> 'TestResult':
        target = next(iter(test_targets), None)
        if target is None:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, "There isn't a valid target for participant {}", self.target_business.participant, tooltip=self.tooltip)
        business_manager = self.target_business.get_business_manager(target)
        if business_manager is None:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Unable to find target business for participant {}', self.target_business.participant, tooltip=self.tooltip)
        if business_manager.business_type != BusinessType.RENTAL_UNIT:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Business not a rental unit for target participant {}.', self.target_business.participant, tooltip=self.tooltip)
        if business_manager.is_grace_period == self.negate:
            return TestResult(False, "Grace period isn't as requested for target participant {}", self.target_business.participant, tooltip=self.tooltip)
        return TestResult.TRUE

class HasTenantEverPaidRentTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'target_business': BusinessManagerFinderVariant(description='\n            Method by which to find the business of interest.\n            '), 'negate': Tunable(description='\n            If checked then the result of the test will be negated.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.target_business.participant}

    def __call__(self, test_targets:'Set[Any]') -> 'TestResult':
        target = next(iter(test_targets), None)
        if target is None:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, "There isn't a valid target for participant {}", self.target_business.participant, tooltip=self.tooltip)
        rental_unit_manager = self.target_business.get_business_manager(target)
        if rental_unit_manager is None:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Unable to find target business for participant {}', self.target_business.participant, tooltip=self.tooltip)
        if rental_unit_manager.business_type != BusinessType.RENTAL_UNIT:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Business not a rental unit for target participant {}.', self.target_business.participant, tooltip=self.tooltip)
        if rental_unit_manager.has_tenant_ever_paid_rent:
            if self.negate:
                return TestResult(False, 'Rental Unit Tenant {} has never paid rent.', self.target_business.participant, tooltip=self.tooltip)
            return TestResult.TRUE
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'Rental Unit Tenant {} has never paid rent before', self.target_business.participant, tooltip=self.tooltip)

class RentalUnitHasOverdueStatusTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'tenant': TunableEnumEntry(description='\n            The sim whose household is the object of this overdue rent test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'negate': Tunable(description='\n            If True, test will return true if the rental unit does not have overdue rent.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'tenant_to_test': self.tenant}

    def __call__(self, tenant_to_test=None):
        target = next(iter(tenant_to_test), None)
        if target is None:
            return TestResult(False, 'No tenant was passed in.', tooltip=self.tooltip)
        rental_unit_manager = services.business_service().get_business_manager_for_zone(target.household.home_zone_id)
        if rental_unit_manager is None or rental_unit_manager.business_type != BusinessType.RENTAL_UNIT:
            return TestResult(False, '{} has no Rental Unit Manager On their home lot id {}', target, target.household.home_zone_id, tooltip=self.tooltip)
        if self.negate == rental_unit_manager.overdue_rent != 0:
            return TestResult(False, 'RentalUnit overdue rent does not match the desired test value. Rental Unit Shows {} Overdue and Negate is set to {}', rental_unit_manager.overdue_rent, self.negate, tooltip=self.tooltip)
        return TestResult.TRUE

class BusinessRuleStateTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'target_business': BusinessManagerFinderVariant(description='\n            Method by which to find the business of interest.\n            ', default='sim'), 'rules': TunableSet(description='\n            Set of rules that will be tested against. If empty, then all active rules\n            in rental unit will be tested.\n            ', tunable=TunablePackSafeReference(manager=services.get_instance_manager(sims4.resources.Types.BUSINESS_RULE))), 'state': TunableEnumEntry(description='\n            The state that all the rules in rule set need to be in order to pass the test.\n            ', tunable_type=BusinessRuleState, default=BusinessRuleState.DISABLED), 'threshold': TunableThreshold(description='\n            Number of rules that must match the tuned state to pass the test.\n            ')}

    def __init__(self, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._rule_set = set()
        for tuning_rule in self.rules:
            self._rule_set.add(tuning_rule.guid64)

    def get_expected_args(self):
        return {'test_targets': self.target_business.participant}

    def __call__(self, test_targets:'Set[Any]') -> 'TestResult':
        target = next(iter(test_targets), None)
        if target is None:
            return TestResult(False, "There isn't a valid target for participant {}", self.target_business.participant, tooltip=self.tooltip)
        business_manager = self.target_business.get_business_manager(target)
        if business_manager is None:
            return TestResult(False, 'Cannot find business manager for target sim {}.', target, tooltip=self.tooltip)
        if business_manager.has_rules:
            check_all_rules = len(self._rule_set) == 0
            pass_count = 0
            for rule in business_manager.active_rules.values():
                if not check_all_rules:
                    pass
                if rule.rule_state == self.state:
                    pass_count += 1
            if self.threshold.compare(pass_count):
                return TestResult.TRUE
            return TestResult(False, "Rental unit for {} doesn't meet rule state threshold requirement.", target, tooltip=self.tooltip)
        else:
            return TestResult(False, "Business unit for target sim {} doesn't support rules.", target, tooltip=self.tooltip)
