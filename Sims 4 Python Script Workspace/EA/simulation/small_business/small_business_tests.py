import sims4from business.business_enums import SmallBusinessAttendanceSaleMode, BusinessTypefrom business.business_tests import ActiveZone, PickedZoneIdsfrom event_testing import test_basefrom event_testing.results import TestResultfrom interactions import ParticipantTypeSingleSim, ParticipantType, ParticipantTypeSimfrom sims4.math import almost_equalfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableVariant, TunableEnumEntry, TunableOperator, TunableInterval, TunableEnumWithFilter, TunableThreshold, TunableRange, TunableReferenceimport servicesimport taglogger = sims4.log.Logger('SmallBusinessTests', default_owner='sersanchez')
class SmallBusinessAttendanceModeTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The sim that is currently in the Small Business we want to check the Attendance Mode against.', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'attendance_sale_mode': TunableEnumEntry(description='\n                Attendance Sale Mode to check against.', tunable_type=SmallBusinessAttendanceSaleMode, default=SmallBusinessAttendanceSaleMode.DISABLED), 'negate': Tunable(description="\n                If true, negates the result of the test. Won't affect a false result if it has happened due to\n                a small business not being found.\n                ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'participant': self.participant}

    def __call__(self, participant=None) -> TestResult:
        if participant is None or participant == () or participant[0] is None:
            return TestResult(False, 'Unable to find participant', tooltip=self.tooltip)
        sim_info = participant[0]
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return TestResult(False, 'No Small business is registered to sim, {}.', sim_info.id, tooltip=self.tooltip)
        current_mode = business_manager.small_business_income_data.attendance_sale_mode
        if current_mode != self.attendance_sale_mode:
            if not self.negate:
                return TestResult(False, "The passed-in attendance sale mode [{}] doesn't match the current mode [{}] for the small business owned by sim {}", self.attendance_sale_mode, current_mode, sim_info.id, tooltip=self.tooltip)
        elif self.negate:
            return TestResult(False, 'The passed-in attendance sale mode [{}] matches the current mode [{}] for the small business owned by sim {}, but the result of the test is inverted.', self.attendance_sale_mode, current_mode, sim_info.id, tooltip=self.tooltip)
        return TestResult.TRUE

class SmallBusinessLightRetailSalesActiveTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The sim that is currently in the Small Business we want to check against.', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'is_enabled': Tunable(description='\n                Small Business Light Retail Mode to check against.', tunable_type=bool, default=False), 'negate': Tunable(description="\n                If true, negates the result of the test. Won't affect a false result if it has happened due to\n                a small business not being found.\n                ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'participant': self.participant}

    def __call__(self, participant=None) -> TestResult:
        if participant is None or participant == () or participant[0] is None:
            return TestResult(False, 'Unable to find participant', tooltip=self.tooltip)
        sim_info = participant[0]
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return TestResult(False, 'No Small business is registered to sim, {}.', sim_info.id, tooltip=self.tooltip)
        current_mode = business_manager.small_business_income_data.is_light_retail_enabled
        if current_mode != self.is_enabled:
            if not self.negate:
                return TestResult(False, "The passed-in light retail sale mode [{}] doesn't match the current mode [{}] for the small business owned by sim {}", self.is_enabled, current_mode, sim_info.id, tooltip=self.tooltip)
        elif self.negate:
            return TestResult(False, 'The passed-in light retail sale mode [{}] matches the current mode [{}] for the small business owned by sim {}, but the result is negated', self.is_enabled, current_mode, sim_info.id, tooltip=self.tooltip)
        return TestResult.TRUE

class _BaseSmallBusinessMarkupTestVariant(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, current_markup:float=None, tooltip=None) -> TestResult:
        if current_markup is not None:
            return self._run_test(current_markup, tooltip=tooltip)
        else:
            return TestResult(False, 'No Small Business markup found.')

    def _run_test(self, current_markup:float, tooltip=None) -> TestResult:
        raise NotImplementedError

class SmallBusinessMarkupComparisonTest(_BaseSmallBusinessMarkupTestVariant):
    FACTORY_TUNABLES = {'markup_multiplier': Tunable(description='\n                The markup multiplier value.\n                ', tunable_type=float, default=1.0), 'comparison_operator': TunableOperator(description='\n                Operator used for the comparison.\n                ', default=sims4.math.Operator.EQUAL), 'negate': Tunable(description="\n                If true, negates the result of the test. Won't affect a false result if it has happened due to\n                a small business not being found.\n                ", tunable_type=bool, default=False)}

    def _run_test(self, current_markup:float, tooltip=None) -> TestResult:
        threshold = sims4.math.Threshold(self.markup_multiplier, self.comparison_operator)
        operator_symbol = sims4.math.Operator.from_function(self.comparison_operator).symbol
        if not threshold.compare(current_markup):
            if not self.negate:
                return TestResult(False, 'The current markup {} failed comparison test for: {} ({}) {}.', current_markup, current_markup, operator_symbol, self.markup_multiplier, tooltip=tooltip)
        elif self.negate:
            return TestResult(False, 'The current markup {} passed comparison test for: {} ({}) {}, but the result is negated.', current_markup, current_markup, operator_symbol, self.markup_multiplier, tooltip=tooltip)
        return TestResult.TRUE

class SmallBusinessMarkupBetweenTest(_BaseSmallBusinessMarkupTestVariant):
    FACTORY_TUNABLES = {'markup_multiplier_interval': TunableInterval(description='\n                The range in which the current markup should be for the test to be true.\n                Includes the limits if the include_thresholds field is set to true.\n                ', tunable_type=float, default_lower=1.0, default_upper=2.0), 'negate': Tunable(description="\n                If true, negates the result of the test. Won't affect a false result if it has happened due to\n                a small business not being found.\n                ", tunable_type=bool, default=False), 'include_thresholds': Tunable(description='\n                If true, converts the "low < markup < high" into "low <= markup <= high".\n                ', tunable_type=bool, default=True)}

    def _run_test(self, current_markup:float, tooltip=None) -> TestResult:
        if self.include_thresholds:
            if self.markup_multiplier_interval.lower_bound <= current_markup and current_markup <= self.markup_multiplier_interval.upper_bound:
                if self.negate:
                    return TestResult(False, 'Current retail markup [{}] is between (thresholds INcluded) the markups passed in [{},{}], but the operation is negated.', current_markup, self.markup_multiplier_interval.lower_bound, self.markup_multiplier_interval.upper_bound, tooltip=tooltip)
                    if not self.negate:
                        return TestResult(False, 'Current retail markup [{}] is NOT between (thresholds INcluded) the markups passed in [{},{}].', current_markup, self.markup_multiplier_interval.lower_bound, self.markup_multiplier_interval.upper_bound, tooltip=tooltip)
            elif not self.negate:
                return TestResult(False, 'Current retail markup [{}] is NOT between (thresholds INcluded) the markups passed in [{},{}].', current_markup, self.markup_multiplier_interval.lower_bound, self.markup_multiplier_interval.upper_bound, tooltip=tooltip)
        elif self.markup_multiplier_interval.lower_bound < current_markup and current_markup < self.markup_multiplier_interval.upper_bound:
            if self.negate:
                return TestResult(False, 'Current retail markup [{}] is between (thresholds EXcluded) the markups passed in [{},{}], but the operation is negated.', current_markup, self.markup_multiplier_interval.lower_bound, self.markup_multiplier_interval.upper_bound, tooltip=tooltip)
        elif not self.negate:
            return TestResult(False, 'Current retail markup [{}] is NOT between (thresholds EXcluded) the markups passed in [{},{}].', current_markup, self.markup_multiplier_interval.lower_bound, self.markup_multiplier_interval.upper_bound, tooltip=tooltip)
        return TestResult.TRUE

class SmallBusinessMarkupTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'markup_test': TunableVariant(description='\n                Tests to check various things about the current small business markup value\n                ', compare=SmallBusinessMarkupComparisonTest.TunableFactory(), between=SmallBusinessMarkupBetweenTest.TunableFactory()), 'participant': TunableEnumEntry(description='\n                The sim that is currently in the Small Business we want to check against.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

    def get_expected_args(self):
        return {'participant': self.participant}

    def __call__(self, participant=None) -> TestResult:
        if participant is None or participant == () or participant[0] is None:
            return TestResult(False, 'Unable to find participant', tooltip=self.tooltip)
        sim_info = participant[0]
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return TestResult(False, 'No Small business is registered to sim, {}.', sim_info.id, tooltip=self.tooltip)
        return self.markup_test(current_markup=business_manager.markup_multiplier, tooltip=self.tooltip)

class SmallBusinessIsAffordanceEncouragedTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'small_business_customer_situation_tag': TunableEnumWithFilter(description='\n            The tag that will be tested against currently running situations on the target sim. Needs to match a\n            tag on the situation for which affordances are tested.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=['situation'], pack_safe=True)}

    def get_expected_args(self):
        return {'subjects': ParticipantType.Actor, 'affordance': ParticipantType.Affordance}

    def _test_small_business(self, subject, affordance_data=None):
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        if business_manager is None:
            return TestResult(False, 'No small business is active')
        employee_data = business_manager.get_employee_assignment(subject.sim_id)
        rules = employee_data.rules if employee_data else business_manager.customer_rules
        for rule in rules:
            if any(affordance == affordance_data for affordance in rule.action()):
                return TestResult.TRUE
        return TestResult(False, 'Affordance is not encouraged by the small business')

    def __call__(self, subjects=(), affordance=None) -> TestResult:
        subject = next(iter(subjects), None)
        if subject is None:
            return TestResult(False, 'Subject not found for small business encouragement test', tooltip=self.tooltip)
        if affordance is None:
            return TestResult(False, 'No affordance to test', tooltip=self.tooltip)
        situation_manager = services.get_zone_situation_manager()
        sim = subject.get_sim_instance()
        customer_situations = situation_manager.get_situations_sim_is_in_by_tag(sim, self.small_business_customer_situation_tag)
        if not customer_situations:
            return TestResult(False, 'Sim is not a customer', tooltip=self.tooltip)
        if not self._test_small_business(subject, affordance_data=affordance):
            return TestResult(False, 'Affordance is not encouraged by the small business')
        return TestResult.TRUE

class SmallBusinessOwnershipTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The sim on which ownership of small business is checked\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'negate': Tunable(description='\n            Boolean to invert the test to check the participant does not own a small business\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'participant': self.participant}

    def __call__(self, participant=None) -> TestResult:
        if participant is None or len(participant) == 0:
            return TestResult(False, 'Unable to find participant', tooltip=self.tooltip)
        sim_id = None
        is_owner = False
        for participant_sim_info in participant:
            sim_id = participant_sim_info.id
            business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_id)
            is_owner = business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS
            if is_owner:
                break
        if self.negate or not is_owner:
            return TestResult(False, 'No Small business is registered to sim, {}.', sim_id, tooltip=self.tooltip)
        if self.negate and is_owner:
            return TestResult(False, 'A small business is registered to sim, {}.', sim_id, tooltip=self.tooltip)
        return TestResult.TRUE

class SmallBusinessOpenHoursTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The sim on which small business open status is checked\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'open_hours_to_verify': TunableThreshold(description='\n            Time in hours to check with small business total open hours\n            Default value is 40 i.e a work week (5 days * 8 hours)\n            Default comparison is Greater than or equal to\n            ', value=TunableRange(description='\n                The value of a threshold.\n                ', tunable_type=int, default=40, minimum=0), default=sims4.math.Threshold(40, sims4.math.Operator.GREATER_OR_EQUAL.function))}

    def get_expected_args(self):
        return {'participant': self.participant}

    def __call__(self, participant=None) -> TestResult:
        if participant is None or len(participant) == 0:
            return TestResult(False, 'Unable to find participant', tooltip=self.tooltip)
        business_manager = None
        for participant_sim_info in participant:
            business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
            if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                break
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return TestResult(False, 'Unable to find small business owned by a selected participant', tooltip=self.tooltip)
        if not self.open_hours_to_verify.compare(business_manager.total_open_hours):
            return TestResult(False, 'Small business is open for {} hours, failed threshold {}:{}.', business_manager.total_open_hours, self.open_hours_to_verify.comparison, self.open_hours_to_verify.value, tooltip=self.tooltip)
        return TestResult.TRUE

class IsSmallBusinessOpenTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The sim on which small business open status is checked\n            ', tunable_type=ParticipantTypeSingleSim, default=None), 'negate': Tunable(description='\n            Boolean to invert the test to check if the small business is closed\n            ', tunable_type=bool, default=False), 'zone': TunableVariant(description='\n            The zone to check if it has a small business\n            ', use_current_zone=ActiveZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), default='use_current_zone')}

    def get_expected_args(self):
        expected_args = {}
        if self.participant is not None:
            expected_args['participant'] = self.participant
        return expected_args

    def __call__(self, participant=None, *args, **kwargs) -> TestResult:
        if participant is not None and len(participant) > 0:
            business_manager = None
            for participant_sim_info in participant:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
                if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                    sb_owned_by_participant = True
                    break
            if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
                return TestResult(False, 'Unable to find small business owned by a selected participant', tooltip=self.tooltip)
            if business_manager.is_open or not self.negate:
                return TestResult(False, 'A small business owned by {} is closed.', business_manager.owner_sim_id, tooltip=self.tooltip)
            if business_manager.is_open and self.negate:
                return TestResult(False, 'A small business owned by {}, is available on the lot {} and is open.', business_manager.owner_sim_id, business_manager.business_zone_id, tooltip=self.tooltip)
            return TestResult.TRUE
        zone_id = self.zone.get_zone_id(**kwargs)
        if not zone_id:
            return TestResult(False, "IsSmallBusinessOpenTest couldn't find a zone to test.")
        business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Unable to find small business which is open in the lot {}', zone_id, tooltip=self.tooltip)
        if business_manager.is_open or not self.negate:
            return TestResult(False, 'A small business owned by {}, is available on the lot {} but is closed.', business_manager.owner_sim_id, business_manager.business_zone_id, tooltip=self.tooltip)
        if business_manager.is_open and self.negate:
            return TestResult(False, 'A small business owned by {}, is available on the lot {} and is open.', business_manager.owner_sim_id, business_manager.business_zone_id, tooltip=self.tooltip)
        else:
            return TestResult.TRUE

class SmallBusinessDoesHouseholdHaveOtherBusinessTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The sim on which the household is in\n            ', tunable_type=ParticipantTypeSingleSim, default=None), 'negate': Tunable(description='\n            Boolean to invert the test (if household Sim has a business return false)\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        expected_args = {}
        if self.participant is not None:
            expected_args['participant'] = self.participant
        return expected_args

    def __call__(self, participant=None, *args, **kwargs) -> TestResult:
        if len(participant) > 0:
            business_service = services.business_service()
            for participant_sim_info in participant:
                for household_sim in participant_sim_info.household.sim_info_gen():
                    if household_sim not in participant and business_service.get_business_manager_for_sim(household_sim.id) is not None:
                        if not self.negate:
                            return TestResult.TRUE
                        return TestResult(False, f'{participant_sim_info} has a business.')
        if not (participant is not None and self.negate):
            return TestResult(False, 'No other household Sims own a small business')
        return TestResult.TRUE

class SmallBusinessIsZoneAssignedAllowed(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The owner of small business being checked\n            ', tunable_type=ParticipantTypeSingleSim, default=None), 'zone': TunableVariant(description='\n            The zone to check if this small business can be opened.\n            ', use_current_zone=ActiveZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), default='use_current_zone')}

    def get_expected_args(self):
        expected_args = {}
        if self.participant is not None:
            expected_args['participant'] = self.participant
        return expected_args

    def __call__(self, participant=None, *args, **kwargs) -> TestResult:
        if len(participant) > 0:
            business_manager = None
            for participant_sim_info in participant:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
                if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                    zone_id = self.zone.get_zone_id(**kwargs)
                    if not zone_id:
                        return TestResult(False, "CanOpenSmallBusinessOpenInZoneTest couldn't find a zone to test.")
                    if business_manager.is_zone_assigned_allowed(zone_id):
                        return TestResult.TRUE
        return TestResult(False, 'A small business owned by {}, is not allowed to be open on the lot {}.', business_manager.owner_sim_id, business_manager.business_zone_id, tooltip=self.tooltip)

class SmallBusinessIsOnlyHomeLotAllowed(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The owner of small business being checked\n            ', tunable_type=ParticipantTypeSingleSim, default=None), 'negate': Tunable(description='\n            Boolean to invert the test\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        expected_args = {}
        if self.participant is not None:
            expected_args['participant'] = self.participant
        return expected_args

    def __call__(self, participant=None, *args, **kwargs) -> TestResult:
        if len(participant) > 0:
            for participant_sim_info in participant:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
                if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                    if participant_sim_info.household and business_manager.is_zone_assigned_allowed(participant_sim_info.household.home_zone_id) and len(business_manager.get_allowed_zone_ids()) == 1:
                        if self.negate:
                            return TestResult(False, 'Home zone is not the only allowed zone for small business of sim {}', participant_sim_info.id, tooltip=self.tooltip)
                        return TestResult.TRUE
                        if self.negate:
                            return TestResult.TRUE
                        return TestResult(False, 'Sim {} does not own any small business.', participant_sim_info.id, tooltip=self.tooltip)
                else:
                    if self.negate:
                        return TestResult.TRUE
                    return TestResult(False, 'Sim {} does not own any small business.', participant_sim_info.id, tooltip=self.tooltip)
        if participant is not None and self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, 'No sim participant found.', tooltip=self.tooltip)

class IsSimAnEmployeeOfBusinessOwnerTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject who potentially owns the business.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target_sim': TunableEnumEntry(description='\n            The target sim to test if they are an employee.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim), 'business_type': TunableEnumEntry(description='\n            The business type being checked.\n            ', tunable_type=BusinessType, default=BusinessType.SMALL_BUSINESS), 'negate': Tunable(description='\n            Boolean to invert the test\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'source_participants': self.subject, 'target_participants': self.target_sim}

    def __call__(self, source_participants=None, target_participants=None, *args, **kwargs) -> TestResult:
        if source_participants is not None and target_participants is not None:
            business_manager = None
            for participant_sim_info in source_participants:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
                if business_manager is not None and business_manager.business_type == self.business_type:
                    break
            if business_manager is None:
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'Unable to find a business owned by a selected participant', tooltip=self.tooltip)
            if any(business_manager.is_employee(employee) for employee in target_participants):
                if self.negate:
                    return TestResult(False, 'Found a business owned by a selected participant', tooltip=self.tooltip)
                return TestResult.TRUE
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'No target sims are employees of the specified business', tooltip=self.tooltip)

class EmployeeCountTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject who potentially owns the business.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'business_type': TunableEnumEntry(description='\n            The business type being checked.\n            ', tunable_type=BusinessType, default=BusinessType.SMALL_BUSINESS), 'employee_count': Tunable(description='\n            Tested employee count \n            ', tunable_type=int, default=3), 'negate': Tunable(description='\n            Boolean to invert the test\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'source_participants': self.subject}

    def __call__(self, source_participants=None, *args, **kwargs) -> TestResult:
        if source_participants is not None:
            business_manager = None
            for participant_sim_info in source_participants:
                business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
                if business_manager is not None and business_manager.business_type == self.business_type:
                    break
            if business_manager is None:
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'Unable to find small business owned by a selected participant', tooltip=self.tooltip)
            if business_manager.employee_count != self.employee_count:
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, "Employee count doesn't match", tooltip=self.tooltip)
            elif business_manager.employee_count == self.employee_count:
                if self.negate:
                    return TestResult(False, 'Employee count matches but the result is negated', tooltip=self.tooltip)
                return TestResult.TRUE
        return TestResult(False, 'No participants', tooltip=self.tooltip)

class SmallBusinessCareerLevelTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The optional subject who potentially owns the business. If the test has no subject, the test will run \n            against any business currently open in the zone.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target_sim': TunableEnumEntry(description='\n            The target sim to test their pay level in the business.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim), 'career_level': TunableReference(description='\n            A reference to career level tuning that each subject must have in \n            small business career in subject small business to pass.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_LEVEL), needs_tuning=True), 'negate': Tunable(description='\n            Boolean to invert the test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'source_participants': self.subject, 'target_participants': self.target_sim}

    def __call__(self, source_participants=None, target_participants=None, *args, **kwargs) -> TestResult:
        if target_participants is not None:
            business_manager = None
            if source_participants is not None:
                for participant_sim_info in source_participants:
                    business_manager = services.business_service().get_business_manager_for_sim(sim_id=participant_sim_info.id)
                    if business_manager is not None:
                        break
            if business_manager is None:
                business_manager = services.business_service().get_business_manager_for_zone()
                if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
                    return TestResult(False, 'No small business found', tooltip=self.tooltip)
            for target_participant_info in target_participants:
                if self.career_level == business_manager.get_employee_career_level(target_participant_info):
                    if self.negate:
                        return TestResult(False, 'Employee pay level matches the requested pay level', tooltip=self.tooltip)
                    return TestResult.TRUE
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, "They pay level doesn't match for any participants", tooltip=self.tooltip)
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'No target sims are employees of the small business', tooltip=self.tooltip)

class CanBeHiredByAnotherSmallBusinessTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'target_sim': TunableEnumEntry(description='\n            The target sim to test amount of small businesses that hire them.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim), 'small_business_career': TunableReference(description='\n            A reference to small business career to check how many businesses sim is hired in.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), needs_tuning=True), 'negate': Tunable(description='\n            Boolean to invert the test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'target_participants': self.target_sim}

    def __call__(self, target_participants=None, *args, **kwargs) -> TestResult:
        if target_participants is not None:
            for participant_sim_info in target_participants:
                career = participant_sim_info.career_tracker.get_career_by_uid(self.small_business_career.guid64)
                if not career:
                    if self.negate:
                        return TestResult(False, 'Not employed by a small business', tooltip=self.tooltip)
                    return TestResult.TRUE
                if career.get_employers_count() < 5:
                    if self.negate:
                        return TestResult(False, 'Employed by less than 5 employers', tooltip=self.tooltip)
                    return TestResult.TRUE
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'Employed by more than 5 employers', tooltip=self.tooltip)
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'No target sims', tooltip=self.tooltip)

class SmallBusinessDependentsSupervisedTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'negate': Tunable(description='\n            Boolean to invert the test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {}

    def __call__(self, *args, **kwargs):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
            if business_manager.dependents_supervised:
                if self.negate:
                    return TestResult(False, 'Dependents are supervised', tooltip=self.tooltip)
                return TestResult.TRUE
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Dependents are not supervised or no dependent rule is set', tooltip=self.tooltip)
        return TestResult(False, 'No small business open', tooltip=self.tooltip)
