from __future__ import annotationsfrom protocolbuffers import GameplaySaveData_pb2import alarmsimport event_testingimport servicesimport sims4from business.business_rule_enums import BusinessRuleStatefrom date_and_time import create_time_spanfrom event_testing.resolver import SingleSimResolver, Resolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions.utils.tunable_icon import TunableIconfrom objects.object_tests import ObjectCriteriaTestfrom sims.sim_info import SimInfofrom sims.sim_info_tests import TraitTestfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableList, TunableSimMinute, TunableVariant, TunableRange, TunablePackSafeReferencefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom singletons import DEFAULTfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *logger = sims4.log.Logger('BusinessRule', default_owner='bzhu')
class BusinessRuleTestVariant(TunableVariant):

    def __init__(self, description:'str'='A single tunable test for rule compliance.', **kwargs):
        super().__init__(description=description, day_and_time=event_testing.test_variants.TunableDayTimeTest(), object_criteria=ObjectCriteriaTest.TunableFactory(), trait=TraitTest.TunableFactory(), household_size=event_testing.test_variants.HouseholdSizeTest.TunableFactory(), event_ran=event_testing.test_variants.EventRanSuccessfullyTest.TunableFactory(), situation_running_test=event_testing.test_variants.TunableSituationRunningTest(), **kwargs)

class BusinessRuleTestSet(event_testing.tests.CompoundTestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.CompoundTestList()

    def __init__(self, description:'str'=None, **kwargs):
        super().__init__(description=description, tunable=TunableList(BusinessRuleTestVariant(), description='A list of tests.  All of these must pass for the group to pass.'), **kwargs)

class BusinessRule(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.BUSINESS_RULE)):
    INSTANCE_TUNABLES = {'rule_name': TunableLocalizedString(description='\n            Name of rule.\n            ', export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'rule_description': TunableLocalizedString(description='\n            Description of rule.\n            ', export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'icon': TunableIcon(description='\n            Rule icon.\n            ', export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'fine': TunableRange(description='\n            The Simolean amount for breaking a rule. \n            ', tunable_type=int, default=500, minimum=0, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'cooldown_time': TunableSimMinute(description='\n            The minutes until a rule can be broken (compliance checks ran) again after it gets resolved.\n            ', default=360, minimum=0), 'auto_resolve_time': TunableSimMinute(description='\n            The amount of time a broken rule, if not addressed, will resolve itself.\n            ', minimum=0, default=360), 'test_events': BusinessRuleTestSet(description="\n            At least one sub test group (AKA one list item) must pass\n            within this list before the action associated with this\n            tuning will be run.\n            All tests in sub test group must pass for the sub test group\n            to pass.\n            \n            Uses relevant business manager's resolver.\n            "), 'loot_on_rule_broken': TunablePackSafeReference(description="\n            A loot applied to the unit when the rule breaks.\n            \n            Uses relevant business manager's resolver.\n            ", manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), 'loot_on_auto_resolved': TunablePackSafeReference(description="\n            A loot applied to the unit if the broken rule is not resolved within auto resolve time.\n            \n            Uses relevant business manager's resolver.\n            ", manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))}

    def __init__(self, zone_id:'int'=None, state_change_callback:'Callable[[BusinessRule, BusinessRuleState], None]'=None) -> 'None':
        self._auto_resolve_alarm_handle = None
        self._cooldown_alarm_handle = None
        self.zone_id = zone_id
        self._household_id = None
        self._state = BusinessRuleState.DISABLED
        self._cooldown_time = 0
        self._state_change_callback = state_change_callback

    @property
    def rule_state(self) -> 'BusinessRuleState':
        return self._state

    @property
    def household_id(self) -> 'int':
        if self.zone_id is not None:
            self._household_id = services.get_persistence_service().get_household_id_from_zone_id(self.zone_id)
        return self._household_id

    @property
    def household_sim(self) -> 'SimInfo':
        if self.zone_id is not None:
            self._household_id = services.get_persistence_service().get_household_id_from_zone_id(self.zone_id)
        household = services.household_manager().get(self._household_id)
        if household is not None and household.sim_infos:
            return household.sim_infos[0]

    def get_resolver(self, household_sim:'SimInfo') -> 'Resolver':
        if household_sim is None:
            return
        business_manager = None if self.zone_id is None else services.business_service().get_business_manager_for_zone(zone_id=self.zone_id)
        if business_manager is None:
            return SingleSimResolver(household_sim)
        return business_manager.get_resolver(actor=household_sim)

    def set_state(self, state:'BusinessRuleState', override_rule_cooldown_time:'int'=DEFAULT) -> 'None':
        self._disable_alarms()
        if state == BusinessRuleState.BROKEN:
            if override_rule_cooldown_time is DEFAULT:
                self._break_rule(self.auto_resolve_time)
            elif override_rule_cooldown_time <= 0:
                self._break_rule()
            else:
                self._break_rule(override_rule_cooldown_time)
        elif state == BusinessRuleState.ENABLED:
            if override_rule_cooldown_time is DEFAULT:
                self._enable_rule(self.cooldown_time)
            elif override_rule_cooldown_time <= 0:
                self._enable_rule()
            else:
                self._enable_rule(override_rule_cooldown_time)
        elif state == BusinessRuleState.DISABLED:
            self._disable_rule()

    def _notify_rule_state_change(self, rule_state:'BusinessRuleState') -> 'None':
        if self._state_change_callback:
            self._state_change_callback(self, rule_state)

    def _enable_rule(self, remaining_cooldown_time:'int'=None, is_auto_resolved:'bool'=False) -> 'None':
        if self._state != BusinessRuleState.ENABLED:
            self._state = BusinessRuleState.ENABLED
            self._notify_rule_state_change(BusinessRuleState.ENABLED)
        if is_auto_resolved and self.loot_on_auto_resolved is not None:
            resolver = self.get_resolver(self.household_sim)
            if resolver is not None:
                self.loot_on_auto_resolved.apply_to_resolver(resolver)
        self._disable_alarms()
        if remaining_cooldown_time is not None and remaining_cooldown_time > 0:
            self._cooldown_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=remaining_cooldown_time), lambda _: self._register_and_run_tests())
        else:
            self._register_and_run_tests()
        logger.debug('Rule {} has been resolved, rule state {}', self.rule_name, self._state)

    def _break_rule(self, remaining_auto_resolve_time:'int'=None) -> 'None':
        if self._state != BusinessRuleState.BROKEN:
            self._state = BusinessRuleState.BROKEN
            self._notify_rule_state_change(BusinessRuleState.BROKEN)
        if self.loot_on_rule_broken is not None:
            resolver = self.get_resolver(self.household_sim)
            if resolver is not None:
                self.loot_on_rule_broken.apply_to_resolver(resolver)
        self.unregister_compliance_check()
        self._disable_alarms()
        if remaining_auto_resolve_time > 0:
            self._auto_resolve_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=remaining_auto_resolve_time), lambda _: self._enable_rule(remaining_cooldown_time=self.cooldown_time, is_auto_resolved=True))
        logger.debug('Rule {} has been broken, rule state {}', self.rule_name, self._state)

    def get_remaining_cooldown_time(self) -> 'int':
        if self._cooldown_alarm_handle is not None:
            time_span = self._cooldown_alarm_handle.get_remaining_time()
            return int(time_span.in_minutes())
        return 0

    def get_remaining_auto_resolve_time(self) -> 'int':
        if self._auto_resolve_alarm_handle is not None:
            time_span = self._auto_resolve_alarm_handle.get_remaining_time()
            return int(time_span.in_minutes())
        return 0

    def _disable_alarms(self) -> 'None':
        if self._cooldown_alarm_handle:
            alarms.cancel_alarm(self._cooldown_alarm_handle)
        if self._auto_resolve_alarm_handle:
            alarms.cancel_alarm(self._auto_resolve_alarm_handle)

    def _disable_rule(self) -> 'None':
        if self._state != BusinessRuleState.DISABLED:
            self._state = BusinessRuleState.DISABLED
            self._notify_rule_state_change(BusinessRuleState.DISABLED)
        self._disable_alarms()
        self.unregister_compliance_check()
        logger.debug('Rule {} has been disabled, rule state {}', self.rule_name, self._state)

    def _register_and_run_tests(self) -> 'None':
        if self.zone_id != services.current_zone_id():
            return
        business_manager = services.business_service().get_business_manager_for_zone(self.zone_id)
        if business_manager is None or not business_manager.is_open:
            return
        active_hh_id = services.active_household_id()
        if active_hh_id != self.household_id and active_hh_id != business_manager.owner_household_id:
            return
        self.register_compliance_check()
        self._run_rule_compliance_tests()

    def register_compliance_check(self) -> 'None':
        for test_lists in self.test_events:
            services.get_event_manager().register_tests(self, test_lists)

    def unregister_compliance_check(self) -> 'None':
        for test_lists in self.test_events:
            services.get_event_manager().unregister_tests(self, test_lists)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        self._run_rule_compliance_tests()

    def update_business_rule_proto(self, business_rule_proto:'GameplaySaveData_pb2.BusinessRule()') -> 'None':
        business_rule_proto.rule_id = self.guid64
        business_rule_proto.state = self._state
        if self._state == BusinessRuleState.BROKEN:
            business_rule_proto.state_change_cooldown_time = max(0, self.get_remaining_auto_resolve_time())
        elif self._state == BusinessRuleState.ENABLED:
            business_rule_proto.state_change_cooldown_time = max(0, self.get_remaining_cooldown_time())

    def load_business_rule_proto(self, business_rule_proto:'GameplaySaveData_pb2.BusinessRule') -> 'None':
        self._state = BusinessRuleState(business_rule_proto.state)
        self._cooldown_time = business_rule_proto.state_change_cooldown_time

    def on_loading_screen_finished(self) -> 'None':
        self.set_state(self._state, self._cooldown_time)

    def _run_rule_compliance_tests(self, resolver:'Resolver'=None) -> 'None':
        if resolver is None:
            resolver = self.get_resolver(self.household_sim)
        if resolver is not None and self.test_events.run_tests(resolver):
            self.set_state(BusinessRuleState.BROKEN)
