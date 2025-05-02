from __future__ import annotationsimport build_buyimport functoolsimport operatorimport servicesimport sims4import sims4.mathimport telemetry_helperfrom business.business_enums import BusinessType, SmallBusinessAttendanceSaleModefrom business.business_manager import BusinessManager, TELEMETRY_HOOK_BUSINESS_ID, TELEMETRY_GROUP_BUSINESS, TELEMETRY_HOOK_BUSINESS_INHERIT, TELEMETRY_HOOK_TARGET_SIMfrom bucks.small_business_bucks_tracker import SmallBusinessBucksTrackerfrom distributor.ops import GenericProtocolBufferOp, SetBusinessNameDescriptionKeyfrom distributor.system import Distributorfrom dynamic_areas.dynamic_area_enums import DynamicAreaTypefrom interactions import ParticipantTypefrom interactions.payment.payment_info import PaymentBusinessRevenueTypefrom protocolbuffers import Business_pb2, Consts_pb2, DistributorOps_pb2, Localization_pb2from autonomy.autonomy_modifier import OffLotAutonomyRulesfrom sims4.commands import automation_outputfrom small_business.small_business_income_data import SmallBusinessIncomeDatafrom sims.sim_info_types import Age, Speciesfrom sims4.resources import get_protobuff_for_keyfrom clubs import club_tuning, UnavailableClubCriteriaErrorfrom clubs.club_tuning import ClubRule, ClubRuleEncouragementStatus, TunableClubRuleSnippet, ClubCriteriaCategory, FameRank, HouseholdValueCategory, MaritalStatus, CareSimTypefrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom singletons import DEFAULTfrom sims.outfits.outfit_enums import OutfitCategoryfrom small_business.small_business_summary_dialog import SmallBusinessSummaryDialogfrom small_business.small_business_employee_manager import SmallBusinessEmployeeManagerfrom statistics.static_commodity import StaticCommodity, SituationStaticCommodityDatafrom small_business.small_business_tuning import SmallBusinessTunablesfrom server_commands.argument_helpers import TunableInstanceParamfrom event_testing.test_events import TestEventfrom distributor.rollback import ProtocolBufferRollbackfrom sims.household_utilities.utility_types import Utilitiesimport routingimport date_and_timefrom typing import TYPE_CHECKINGfrom zone_types import ZoneStateif TYPE_CHECKING:
    from business.business_employee import BusinessEmployeeData
    from business.business_enums import BusinessEmployeeType, SmallBusinessSalary
    from sims.sim_info import SimInfo
    from ui.ui_dialog_notification import TunableUiDialogNotificationSnippet
    from typing import *TELEMETRY_HOOK_BUSINESS_ADD_RULE = 'RULE'TELEMETRY_HOOK_BUSINESS_HIRE_EMPLOYEE = 'NEMP'TELEMETRY_HOOK_BUSINESS_FIRE_EMPLOYEE = 'REMP'TELEMETRY_HOOK_BUSINESS_RULE_CATEGORY = 'catg'TELEMETRY_HOOK_BUSINESS_RULE_ACTIVITY = 'acti'logger = sims4.log.Logger('SmallBusinessManager', default_owner='bshefket')EMPLOYEE_NUM_SKILLS_TO_SHOW = 3REASON_CUSTOMER_APPRECIATION_DAY = 100
class SmallBusinessManager(BusinessManager):

    def __init__(self, business_data:'Business_pb2.SetBusinessData', from_load:'bool'=False):
        self._name = ''
        self._description = ''
        self._icon = None
        self._name_description_key = None
        self._affordance_dirty_cache = set()
        self.customer_rules = []
        self.dependents_supervised = True
        self.attendance_criteria = []
        self._encouragement_name = 'SmallBusinessEncouragement'
        self._value_stat_listener = None
        self._summary_dialog_class = SmallBusinessSummaryDialog
        self.encouragement_commodity = type(self._encouragement_name, (StaticCommodity, object), {'ad_data': SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_AD_DATA})
        self._business_xp_on_open = 0
        self.had_ticket_machine_once = False
        self._had_light_retail_surface_once = False
        self._next_no_customers_tns_allowed_time = 0
        self.business_has_been_autocreated = False
        self._has_ticket_machine = True
        self._amount_of_ticket_machines_in_current_lot = 0
        super().__init__(BusinessType.SMALL_BUSINESS, business_data.sim_id)
        self._bucks_tracker = SmallBusinessBucksTracker(self.owner_sim_id)
        self._employee_manager.add_employee_assignment(self.owner_sim_id)
        self._allowed_zone_ids = []
        self._business_visitor_ids = []
        self._small_business_income_data = SmallBusinessIncomeData(self)
        self._transferred_sim_id = 0
        if not from_load:
            self.update_small_business_from_ui(business_data)
            self._set_listeners()

    @property
    def name(self) -> 'str':
        return self._name

    @property
    def icon(self) -> 'sims4.resources.Key':
        return self._icon

    @property
    def small_business_income_data(self) -> 'SmallBusinessIncomeData':
        return self._small_business_income_data

    @property
    def had_employee_once(self) -> 'bool':
        return self._employee_manager.had_employee_once

    @property
    def employee_encouragement_name(self):
        return self._employee_manager.employee_encouragement_name

    @property
    def has_employee_assignments(self) -> 'bool':
        return self._employee_manager.has_employee_assignments

    @property
    def allowed_zone_ids(self) -> 'List[int]':
        return self._allowed_zone_ids

    def employee_assignments_gen(self):
        return self._employee_manager.get_employee_assignments_gen()

    def get_employee_assignment(self, employee_sim_id:'int'):
        return self._employee_manager.get_employee_assignment(employee_sim_id)

    def _create_employee_manager(self):
        self._employee_manager = SmallBusinessEmployeeManager(self)

    def set_name_and_description_key(self, name_key, description_key, send_localize_request:'bool') -> 'None':
        self._name_description_key = (name_key.hash, description_key.hash)
        if send_localize_request:
            self._set_business_name_description_key()

    def _set_business_name_description_key(self) -> 'None':
        try:
            op = SetBusinessNameDescriptionKey(self._name_description_key[0], self._name_description_key[1], self.owner_sim_id)
            Distributor.instance().add_op_with_no_owner(op)
        except:
            pass

    def set_name_and_description(self, name:'str', description:'str') -> 'None':
        self._name = name
        self._description = description
        self._name_description_key = None
        sim_info = services.sim_info_manager().get(self._owner_sim_id)
        active_household = services.active_household()
        if active_household is not None and active_household == sim_info.household:
            self.send_data_to_client()
            if self.business_has_been_autocreated:
                self.notify_lot_purchase(self._allowed_zone_ids[0])
                self.display_notification(SmallBusinessTunables.SMALL_BUSINESS_LOT_PURCHASE_DIALOG)
                self.business_has_been_autocreated = False
        else:
            business_data_msg = Business_pb2.SetBusinessData()
            self.construct_business_message(business_data_msg)
            business_data_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SET_NPC_BUSINESS_DATA, business_data_msg)
            Distributor.instance().add_op_with_no_owner(business_data_op)

    def on_client_disconnect(self) -> 'None':
        super().on_client_disconnect()
        if self._name_description_key is not None:
            services.current_zone().unregister_callback(ZoneState.CLIENT_CONNECTED, self._set_business_name_description_key)

    def can_open(self):
        active_business_manager = services.business_service().get_business_manager_for_zone()
        zone_director = services.venue_service().get_zone_director()
        business_type_supported = zone_director is not None and zone_director.supports_business_type(self._business_type)
        return not self._is_open and (active_business_manager is None and business_type_supported)

    def _open_business(self, is_npc_business=False):
        if not self.can_open():
            return False
        sim_info = services.sim_info_manager().get(self.owner_sim_id)
        opening_fee_deducted = sim_info.household.funds.try_remove_amount(self.tuning_data.opening_fee, Consts_pb2.FUNDS_SMALL_BUSINESS_OPEN_BUSINESS, sim_info)
        if opening_fee_deducted or not is_npc_business:
            return False
        tracker = services.business_service().get_business_tracker_for_household(self.owner_household_id, self.business_type)
        tracker.on_zoneless_business_opened(self)
        zone_director = services.venue_service().get_zone_director()
        if hasattr(zone_director, 'set_business_manager'):
            zone_director.set_business_manager(self)
        self._compute_has_had_ticket_machine_once()
        if self._small_business_income_data.attendance_sale_mode != SmallBusinessAttendanceSaleMode.DISABLED:
            self._verify_ticket_machine()
            services.get_event_manager().register_single_event(self, TestEvent.UtilityStatusChanged)
            services.get_event_manager().register_single_event(self, TestEvent.ObjectReplaced)
        self.had_light_retail_surface_once()
        super()._open_business()
        self.small_business_income_data.clear_current_day_income()
        self.small_business_income_data.register_payment(opening_fee_deducted, PaymentBusinessRevenueType.SMALL_BUSINESS_OPENING_FEE)
        self._small_business_income_data.start_payment_handling()
        zone_director.start_owner_employee_situation(self._owner_sim_id, is_npc=is_npc_business)
        if is_npc_business:
            zone_director.start_traveled_sims_customer_situations()
        sim_info_manager = services.sim_info_manager()
        for sim_id in self._business_visitor_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is not None and sim_info in sim_info_manager._sim_infos_saved_in_zone:
                sim_info_manager._sim_infos_saved_in_zone.remove(sim_info)
        self._business_visitor_ids.clear()
        self._business_xp_on_open = self._bucks_tracker.get_current_business_xp()
        self.send_small_business_open_close_info_to_automation_output(True)
        sim_info = services.sim_info_manager().get(self._owner_sim_id)
        if sim_info.aspiration_tracker is not None:
            sim_info.aspiration_tracker.set_tooltip_disabled_for_special_case(True)
        return True

    def is_ticket_machine_on_lot(self) -> 'bool':
        ticket_machines = list(services.object_manager().get_objects_with_tag_gen(SmallBusinessTunables.TICKET_MACHINE_TAG))
        if not ticket_machines:
            return False
        return True

    def is_light_retail_surface_on_lot(self) -> 'bool':
        light_retail_surfaces = list(services.object_manager().get_objects_with_tag_gen(SmallBusinessTunables.LIGHT_RETAIL_SURFACE_TAG))
        if not light_retail_surfaces:
            return False
        return True

    def had_light_retail_surface_once(self) -> 'bool':
        if not self._had_light_retail_surface_once:
            self._had_light_retail_surface_once = self.is_light_retail_surface_on_lot()
        return self._had_light_retail_surface_once

    def get_xp_gained_on_business_day(self) -> 'int':
        return int(self._bucks_tracker.get_current_business_xp() - self._business_xp_on_open)

    def _compute_has_had_ticket_machine_once(self) -> 'bool':
        if not self.had_ticket_machine_once:
            ticket_machines = list(services.object_manager().get_objects_with_tag_gen(SmallBusinessTunables.TICKET_MACHINE_TAG))
            if ticket_machines:
                self.had_ticket_machine_once = True
        return self.had_ticket_machine_once

    def _verify_ticket_machine(self) -> 'None':
        current_zone = services.current_zone()
        if current_zone is not None and not self.is_zone_assigned_allowed(current_zone.id):
            return
        if self._small_business_income_data.attendance_sale_mode != SmallBusinessAttendanceSaleMode.DISABLED:
            (available, tns) = self._is_ticket_machine_available()
            if self._has_ticket_machine and (available or tns):
                self.display_notification(tns)
            self._has_ticket_machine = available

    def _is_ticket_machine_available(self) -> 'Tuple[bool, Optional[TunableUiDialogNotificationSnippet]]':
        sim_info = services.sim_info_manager().get(self._owner_sim_id)
        if services.active_household() != sim_info.household:
            return (True, None)
        if self._small_business_income_data.attendance_sale_mode == SmallBusinessAttendanceSaleMode.DISABLED:
            return (True, None)
        ticket_machines = list(services.object_manager().get_objects_with_tag_gen(SmallBusinessTunables.TICKET_MACHINE_TAG))
        if not ticket_machines:
            return (False, SmallBusinessTunables.INACCESSIBLE_TICKET_MACHINE_TNS)
        if not services.utilities_manager().is_utility_active(Utilities.POWER):
            return (False, SmallBusinessTunables.INOPERABLE_TICKET_MACHINE_TNS)
        accessible_machines = []
        zone = services.current_zone()
        if zone is not None:
            spawn_point = zone.get_spawn_point()
            spawn_location = routing.Location(spawn_point.get_approximate_center(), sims4.math.Quaternion.ZERO(), spawn_point.routing_surface)
            area_service = services.dynamic_area_service()
            for machine in ticket_machines:
                if area_service.can_object_be_used_by_autonomy(machine, OffLotAutonomyRules.BUSINESS_CUSTOMER) and routing.test_connectivity_pt_pt(machine.routing_location, spawn_location, machine.routing_context):
                    accessible_machines.append(machine)
            if len(accessible_machines) == 0:
                return (False, SmallBusinessTunables.INACCESSIBLE_TICKET_MACHINE_TNS)
            fire_service = services.get_fire_service()
            flammable_commodity = fire_service.FLAMMABLE_COMMODITY
            burnt_commodity = fire_service.FLAMMABLE_COMMODITY_BURNT_VALUE
            for machine in accessible_machines:
                tracker = machine.get_tracker(flammable_commodity)
                stat = tracker.get_statistic(flammable_commodity)
                if stat.get_value() > burnt_commodity:
                    return (True, None)
            return (False, SmallBusinessTunables.INOPERABLE_TICKET_MACHINE_TNS)

    def _set_listeners(self):
        sim_info = services.sim_info_manager().get(self.owner_sim_id)
        tracker = sim_info.get_tracker(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC)
        threshold = sims4.math.Threshold(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC.min_value, operator.ge)
        self._value_stat_listener = tracker.create_and_add_listener(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC, threshold, self._on_business_value_changed)

    def display_notification(self, notification:'TunableUiDialogNotificationSnippet', target_sim_info:'SimInfo'=None, resolver=None) -> 'None':
        sim_info = services.sim_info_manager().get(self.owner_sim_id)
        if sim_info is None or services.active_household() != sim_info.household:
            return
        if resolver is None:
            resolver = DoubleSimResolver(sim_info, target_sim_info)
        dialog = notification(sim_info, resolver)
        dialog.show_dialog()

    def send_no_customers_notification(self, tns_type:'TunableUiDialogNotificationSnippet') -> 'None':
        now = services.time_service().sim_now
        if now > self._next_no_customers_tns_allowed_time:
            self._next_no_customers_tns_allowed_time = now + date_and_time.create_time_span(minutes=SmallBusinessTunables.NO_CUSTOMER_TNS_COOLDOWN)
            self.display_notification(tns_type)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if self._small_business_income_data.attendance_sale_mode != SmallBusinessAttendanceSaleMode.DISABLED:
            if event == TestEvent.UtilityStatusChanged:
                self._verify_ticket_machine()
            if event == TestEvent.ObjectReplaced:
                obj = resolver.interaction.target
                if obj is not None and obj.has_tag(SmallBusinessTunables.TICKET_MACHINE_TAG):
                    self._verify_ticket_machine()

    def get_ticket_machine_count(self) -> 'int':
        ticket_machines = list(services.object_manager().get_objects_with_tag_gen(SmallBusinessTunables.TICKET_MACHINE_TAG))
        if not ticket_machines:
            return 0
        return len(ticket_machines)

    def on_build_buy_enter(self):
        super().on_build_buy_enter()
        self._amount_of_ticket_machines_in_current_lot = self.get_ticket_machine_count()

    def on_build_buy_exit(self):
        self.on_build_buy_exit_money_update()
        zone_director = services.venue_service().get_zone_director()
        if zone_director is not None and not zone_director.supports_business_type(self._business_type):
            self.set_open(False)
        self._change_attendance_sales_based_on_ticket_machine_count_change()
        self._compute_has_had_ticket_machine_once()
        self._verify_ticket_machine()
        self.had_light_retail_surface_once()

    def _change_attendance_sales_based_on_ticket_machine_count_change(self) -> 'None':
        if self.is_zone_assigned_allowed(services.current_zone_id()):
            new_amount_of_ticket_machines = self.get_ticket_machine_count()
            old_amount_of_ticket_machines = self._amount_of_ticket_machines_in_current_lot
            if old_amount_of_ticket_machines != new_amount_of_ticket_machines:
                self._amount_of_ticket_machines_in_current_lot = new_amount_of_ticket_machines
                if old_amount_of_ticket_machines > 0 and new_amount_of_ticket_machines == 0:
                    if self._small_business_income_data.attendance_sale_mode != SmallBusinessAttendanceSaleMode.DISABLED:
                        self._small_business_income_data.set_attendance_sales_mode(SmallBusinessAttendanceSaleMode.DISABLED)
                        services.get_event_manager().process_event(TestEvent.BusinessDataUpdated)
                        if self.is_open:
                            services.get_event_manager().unregister_single_event(self, TestEvent.UtilityStatusChanged)
                            services.get_event_manager().unregister_single_event(self, TestEvent.ObjectReplaced)
                elif 0 <= old_amount_of_ticket_machines and old_amount_of_ticket_machines < new_amount_of_ticket_machines:
                    if self._small_business_income_data.attendance_sale_mode == SmallBusinessAttendanceSaleMode.DISABLED:
                        self._small_business_income_data.set_attendance_sales_mode(SmallBusinessAttendanceSaleMode.ENTRY_FEE)
                        services.get_event_manager().process_event(TestEvent.BusinessDataUpdated)
                        if self.is_open:
                            services.get_event_manager().register_single_event(self, TestEvent.UtilityStatusChanged)
                            services.get_event_manager().register_single_event(self, TestEvent.ObjectReplaced)

    def _close_business(self, **kwargs):
        if not self._is_open:
            return
        self.small_business_income_data.register_payment(self.get_total_employee_wages(), PaymentBusinessRevenueType.EMPLOYEE_WAGES)
        self._small_business_income_data.apply_all_pending_interaction_payments()
        super()._close_business(**kwargs)
        tracker = services.business_service().get_business_tracker_for_household(self.owner_household_id, self.business_type)
        tracker.on_zoneless_business_closed(self)
        zone_director = services.venue_service().get_zone_director()
        if hasattr(zone_director, 'set_business_manager'):
            zone_director.set_business_manager(None)
        self._small_business_income_data.stop_payment_handling()
        if self._small_business_income_data.attendance_sale_mode != SmallBusinessAttendanceSaleMode.DISABLED:
            services.get_event_manager().unregister_single_event(self, TestEvent.UtilityStatusChanged)
            services.get_event_manager().unregister_single_event(self, TestEvent.ObjectReplaced)
        self.send_small_business_open_close_info_to_automation_output(False)
        sim_info = services.sim_info_manager().get(self._owner_sim_id)
        if sim_info is not None and sim_info.aspiration_tracker is not None:
            sim_info.aspiration_tracker.set_tooltip_disabled_for_special_case(False)

    def add_owner_career(self):
        owner_info = services.sim_info_manager().get(self.owner_sim_id)
        if owner_info:
            employee_tuning_data = self._employee_manager.get_employee_tuning_data_for_employee_type(SmallBusinessTunables.EMPLOYEE_TYPE)
            employee_career_type = employee_tuning_data.career
            employee_career = employee_career_type(owner_info)
            owner_info.career_tracker.add_career(employee_career, user_level_override=1, owner_id=self.owner_sim_id)

    def set_owner_household_id(self, owner_household_id:'int') -> 'None':
        super().set_owner_household_id(owner_household_id)
        self._grand_opening = False

    @property
    def daily_revenue(self) -> 'int':
        revenue_records = self.small_business_income_data.current_day_business_income_record.revenue_source_records
        attendance_sale_count = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_HOURLY_FEE].profit + revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_ENTRY_FEE].profit
        interaction_sale_count = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE].profit
        light_retail_sale_count = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_LIGHT_RETAIL_FEE].profit
        tip_jar = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_TIP_JAR_FEE].profit
        return attendance_sale_count + interaction_sale_count + light_retail_sale_count + tip_jar

    def get_daily_outgoing_costs(self, include_employee_wages:'bool'=True) -> 'int':
        revenue_records = self.small_business_income_data.current_day_business_income_record.revenue_source_records
        opening_fee_data = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_OPENING_FEE].profit
        employee_wages_data = revenue_records[PaymentBusinessRevenueType.EMPLOYEE_WAGES].profit
        return opening_fee_data + (employee_wages_data if include_employee_wages else 0)

    def show_summary_dialog(self, is_from_close=False):
        SmallBusinessSummaryDialog(self, is_from_close=is_from_close).show_business_summary_dialog()

    def setup_business_for_sim_info(self, sim_info:'SimInfo') -> 'None':
        sim_info.add_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC, SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC.initial_value)
        sim_info.add_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC, SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC.initial_value)
        sim_info.add_statistic(SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC, SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC.initial_value, from_load=True)
        if SmallBusinessTunables.LOOT_ON_REGISTER_BUSINESS is not None:
            register_loot_resolver = SingleSimResolver(sim_info)
            SmallBusinessTunables.LOOT_ON_REGISTER_BUSINESS.apply_to_resolver(register_loot_resolver)

    def sell_business_finalize_funds(self, lot_value:'int'=0, lot_sold:'bool'=True) -> 'None':
        if lot_sold:
            self.modify_funds(lot_value)
        sim_info = services.sim_info_manager().get(self._owner_sim_id)
        if sim_info is None:
            return
        if SmallBusinessTunables.LOOT_ON_UNREGISTER_BUSINESS is not None:
            loot_resolver = SingleSimResolver(sim_info)
            SmallBusinessTunables.LOOT_ON_UNREGISTER_BUSINESS.apply_to_resolver(loot_resolver)
        business_value_amount = self.get_business_value(sim_info)
        business_owner_household = services.household_manager().get(self.owner_household_id)
        business_owner_household.funds.add(business_value_amount, Consts_pb2.FUNDS_SMALL_BUSINESS_SELL_BUSINESS_VALUE)
        sim_info.remove_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC)
        for bucks_type in SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC.associated_bucks_types:
            self._bucks_tracker.reset_bucks(bucks_type)
        self.clean_up_after_unregistering(sim_info, None)

    def get_bucks_tracker(self):
        return self._bucks_tracker

    def get_business_value(self, sim_info:'SimInfo'=None) -> 'int':
        sim_info = services.sim_info_manager().get(self.owner_sim_id) if sim_info is None else sim_info
        if sim_info is None:
            return 0
        business_value_stat = sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC)
        return business_value_stat.get_value()

    def _load_specific_criteria(self, criteria_data):
        criteria = club_tuning.CATEGORY_TO_CRITERIA_MAPPING[criteria_data.category]
        criteria_infos = list(criteria_data.criteria_infos)
        if not criteria.is_multi_select:
            if not criteria_infos:
                return
            criteria_info = criteria_infos[0]
            if criteria_info.resource_value or criteria_info.enum_value or not criteria_info.resource_id:
                return
        try:
            new_criteria = criteria(criteria_infos=criteria_infos, criteria_id=criteria_data.criteria_id)
            new_criteria.required = criteria_data.required
            new_criteria.supervised = criteria_data.supervised
            if criteria_data.category == ClubCriteriaCategory.CARE_SIM_TYPE_SUPERVISED:
                self.dependents_supervised = criteria_data.supervised
        except UnavailableClubCriteriaError:
            new_criteria = None
        return new_criteria

    def _load_attendance_criteria(self, saved_criterias):
        self.dependents_supervised = True
        new_criteria = []
        for criteria_data in saved_criterias:
            criteria = self._load_specific_criteria(criteria_data)
            if criteria is not None:
                new_criteria.append(criteria)
        return new_criteria

    def _load_rules(self, saved_rules:'[TunableClubRuleSnippet]') -> '[ClubRule]':
        action_manager = services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP)
        rules = []
        for rule in saved_rules:
            action_category = action_manager.get(rule.interaction_group.instance)
            with_whom = None
            if rule.HasField('with_whom'):
                with_whom = lambda : self._load_specific_criteria(rule.with_whom)
            new_rule = ClubRule(action=action_category, with_whom=with_whom, restriction=ClubRuleEncouragementStatus.ENCOURAGED)
            rules.append(new_rule)
        return rules

    def add_rule(self, rule:'TunableClubRuleSnippet', is_load:'bool') -> 'None':
        if rule.action is None:
            return
        static_commodity_data = SituationStaticCommodityData(self.encouragement_commodity, 1)
        for affordance in rule.action():
            affordance.add_additional_static_commodity_data(static_commodity_data)
            self.dirty_affordance(affordance)
        if not is_load:
            business_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)
            with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_ADD_RULE) as hook:
                hook.write_int(TELEMETRY_HOOK_BUSINESS_ID, self._owner_sim_id)
                hook.write_enum(TELEMETRY_HOOK_BUSINESS_RULE_CATEGORY, rule.action.category)
                hook.write_int(TELEMETRY_HOOK_BUSINESS_RULE_ACTIVITY, rule.action.guid64)
        self.customer_rules.append(rule)

    def add_employee(self, sim_info, employee_type, is_npc_employee=False, show_notification=True) -> 'None':
        super().add_employee(sim_info, employee_type, is_npc_employee)
        if show_notification:
            self.display_notification(SmallBusinessTunables.HIRE_EMPLOYEE_NOTIFICATION, sim_info)

    def get_employee_uniform_data(self, employee_type, gender, sim_id=0):
        return self._employee_manager.get_employee_uniform_data(employee_type, gender, OutfitCategory.SMALL_BUSINESS, sim_id)

    def get_employees_sim_info(self):
        return self._employee_manager.get_employee_sim_infos()

    def update_employee_rules(self, employees_data_proto:'Business_pb2.ManageSmallBusinessEmployeesData') -> 'None':
        for employee_data in employees_data_proto.employees:
            if not hasattr(employee_data, 'rules'):
                pass
            else:
                employee_rules = self._load_rules(employee_data.rules)
                self._employee_manager.update_employee_rules(employee_data.sim_id, employee_rules)
        self.update_affordance_cache()

    def update_employee_club_rules(self, sim_id:'int', employee_rules:'List[ClubRule]') -> 'None':
        self._employee_manager.update_employee_rules(sim_id, employee_rules)

    def set_employee_pay_level(self, employee_info:'SimInfo', pay_level:'SmallBusinessSalary') -> 'None':
        self._employee_manager.set_pay_level(employee_info, pay_level)

    def remove_rule(self, rule:'TunableClubRuleSnippet'):
        static_commodity_data = SituationStaticCommodityData(self.encouragement_commodity, 1)
        for affordance in rule.action():
            affordance.remove_additional_static_commodity_data(static_commodity_data)
            self.dirty_affordance(affordance)
        self.customer_rules.remove(rule)

    def set_default_rule(self):
        for rule in SmallBusinessTunables.ALWAYS_ACTIVE_RULES:
            self.add_rule(rule, False)

    def is_sim_a_customer(self, sim_info:'SimInfo') -> 'bool':
        return self._customer_manager.is_sim_a_customer(sim_info)

    def update_small_business_from_ui(self, business_data:'Business_pb2.SetBusinessData') -> 'None':
        icon_from_ui = sims4.resources.get_key_from_protobuff(business_data.icon)
        do_update_career = self.name != business_data.name or self.icon != icon_from_ui
        self._name = business_data.name
        self._description = business_data.small_business_data.description
        self._icon = icon_from_ui
        self._small_business_income_data.set_attendance_sales_mode(business_data.small_business_data.attendance_sale_mode, False)
        self._small_business_income_data.set_markup_multiplier(round(business_data.markup_chosen, 3))
        self.attendance_criteria = self._load_attendance_criteria(business_data.small_business_data.attendance_criteria)
        if len(business_data.small_business_data.customer_rules) > 0 or len(self.customer_rules) == 0:
            self._next_no_customers_tns_allowed_time = 0
            new_customer_rules = self._load_rules(business_data.small_business_data.customer_rules)
            for existing_rule in tuple(self.customer_rules):
                self.remove_rule(existing_rule)
            for new_rule in new_customer_rules:
                self.add_rule(new_rule, False)
            self.set_default_rule()
            self.update_affordance_cache()
        if sims4.protocol_buffer_utils.has_field(business_data, 'allowed_zone_ids'):
            self._allowed_zone_ids = [zone_id for zone_id in business_data.allowed_zone_ids]
        if do_update_career:
            self.update_career_data()

    def update_career_data(self):
        owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
        if owner_sim_info and owner_sim_info.career_tracker:
            owner_sim_info.career_tracker.resend_career_data()
        for employee_sim_info in self.get_employees_sim_info():
            if employee_sim_info and employee_sim_info.career_tracker:
                employee_sim_info.career_tracker.resend_career_data()

    def dirty_affordance(self, affordance):
        self._affordance_dirty_cache.add(affordance)

    def update_affordance_cache(self):
        with services.object_manager().batch_commodity_flags_update():
            for affordance in self._affordance_dirty_cache:
                affordance.trigger_refresh_static_commodity_cache()
        self._affordance_dirty_cache.clear()

    def construct_business_message(self, msg:'Business_pb2.SetBusinessData') -> 'None':
        msg.sim_id = self.owner_sim_id
        if self.business_zone_id is not None:
            msg.zone_id = self.business_zone_id
        msg.name = self._name
        msg.is_open = self.is_open
        if self.is_open and self._open_time is not None:
            msg.time_opened = self._open_time.absolute_ticks()
        msg.daily_items_sold = self._daily_items_sold
        msg.daily_outgoing_costs = self.get_daily_outgoing_costs(include_employee_wages=False)
        msg.daily_customers_served = self._customer_manager.session_customers_served
        msg.net_profit = int(self.get_business_value())
        msg.markup_chosen = self.markup_multiplier
        msg.daily_revenue = int(self.daily_revenue)
        msg.icon = sims4.resources.get_protobuff_for_key(self._icon)
        msg.dynamic_area_types.extend([DynamicAreaType.BUSINESS_RESIDENTIAL, DynamicAreaType.BUSINESS_PUBLIC, DynamicAreaType.BUSINESS_EMPLOYEES_ONLY])
        msg.default_dynamic_area_type = DynamicAreaType.BUSINESS_PUBLIC
        msg.total_open_hours = self._total_open_hours
        msg.total_customers_served = self._customer_manager.lifetime_customers_served
        msg.small_business_data = self._build_small_business_data_message()
        msg.allowed_zone_ids.extend(self._allowed_zone_ids)
        if self.is_open:
            msg.review_data = Business_pb2.ReviewDataUpdate()
            self._populate_review_update_message(msg.review_data)

    def _build_small_business_data_message(self) -> 'Business_pb2.SmallBusinessDataUpdate':
        msg = Business_pb2.SmallBusinessDataUpdate()
        msg.sim_id = self.owner_sim_id
        msg.description = self._description
        msg.attendance_sale_mode = self._small_business_income_data.attendance_sale_mode
        for rule in self.customer_rules:
            with ProtocolBufferRollback(msg.customer_rules) as customer_rule:
                action_proto = sims4.resources.get_protobuff_for_key(rule.action.resource_key)
                customer_rule.encouraged = True
                customer_rule.interaction_group = action_proto
                if rule.with_whom is not None:
                    rule.with_whom.save(customer_rule.with_whom)
        for criteria in self.attendance_criteria:
            with ProtocolBufferRollback(msg.attendance_criteria) as attendance_criteria:
                criteria.save(attendance_criteria)
        if sims4.protocol_buffer_utils.has_field(msg, 'allowed_zone_ids'):
            msg.allowed_zone_ids.extend(self._allowed_zone_ids)
        return msg

    def populate_employee_msg(self, sim_info:'SimInfo', employee_msg:'Business_pb2.ManageSmallBusinessEmployeeRowData', business_employee_type:'BusinessEmployeeType'=None, business_employee_data:'BusinessEmployeeData'=None):
        employee_msg.sim_id = sim_info.sim_id
        employee_is_training = sim_info.has_buff_with_tag(self.tuning_data.employee_training_buff_tag)
        employee_data = self._employee_manager.get_employee_data(sim_info)
        top_skills = sim_info.top_skills(EMPLOYEE_NUM_SKILLS_TO_SHOW)
        for skill in top_skills:
            with ProtocolBufferRollback(employee_msg.skill_data) as employee_skill_msg:
                employee_skill_msg.skill_id = skill.guid64
                employee_skill_msg.curr_points = int(skill.get_value())
                employee_skill_msg.is_training = employee_is_training
                employee_skill_msg.has_skilled_up = employee_data.has_leveled_up_skill(skill) if employee_data is not None else False
                employee_skill_msg.skill_tooltip = skill.skill_description(sim_info)
        for employee_assignment in self._employee_manager.get_employee_assignments_gen():
            employee_sim_id = employee_assignment.sim_id
            if sim_info.sim_id != employee_sim_id:
                pass
            else:
                for rule in self._employee_manager.get_employee_rules_gen(employee_sim_id):
                    with ProtocolBufferRollback(employee_msg.rules) as employee_rule:
                        action_proto = sims4.resources.get_protobuff_for_key(rule.action.resource_key)
                        employee_rule.encouraged = True
                        employee_rule.interaction_group = action_proto
                        if rule.with_whom is not None:
                            rule.with_whom.save(employee_rule.with_whom)
                break
        career_level = None
        if self.is_employee(sim_info):
            career_level = self.get_employee_career_level(sim_info)
            employee_msg.pay = career_level.simoleons_per_hour
        elif business_employee_data:
            desired_level = self.get_desired_career_level(sim_info, business_employee_type)
            career_level = business_employee_data.career.start_track.career_levels[desired_level]
            employee_msg.pay = career_level.simoleons_per_hour
        fake_salary_payment_relbit = SmallBusinessTunables.PERK_SETTINGS.fake_employee_payment
        employee_owner_rel_bits = services.relationship_service().get_all_bits(sim_info.id, self.owner_sim_id)
        is_fake_salary_payment_enabled = fake_salary_payment_relbit is not None and fake_salary_payment_relbit in employee_owner_rel_bits
        employee_msg.is_fake_payment_enabled = is_fake_salary_payment_enabled
        if career_level is not None:
            employee_salary_icon = SmallBusinessTunables.EMPLOYEE_SALARY_DATA[career_level.level]
            salary_icon = employee_salary_icon.fake_salary_icon if is_fake_salary_payment_enabled else employee_salary_icon.normal_salary_icon
            employee_msg.salary_icon = sims4.resources.get_protobuff_for_key(salary_icon)

    def get_business_rank_level(self) -> 'int':
        owner_id = self.owner_sim_id
        owner_sim_info = services.sim_info_manager().get(owner_id)
        rank_stat = owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC, add=True)
        rank_level = None
        if rank_stat is not None:
            rank_level = rank_stat.rank_level
        return rank_level

    def get_interaction_score_multiplier(self, interaction, sim=DEFAULT):
        sim = interaction.sim if sim is DEFAULT else sim
        base_multiplier = 1
        sim_info = sim.sim_info
        if not self.is_open:
            return base_multiplier
        if self._customer_manager is not None and self._customer_manager.is_sim_a_customer(sim_info):
            return self.get_customer_interaction_score_multiplier(interaction)
        elif sim_info.sim_id == self._owner_sim_id or self._employee_manager is not None and self._employee_manager.is_employee(sim_info):
            return self.get_employee_interaction_score_multiplier(interaction, sim_info)
        return base_multiplier

    def get_customer_interaction_score_multiplier(self, interaction):
        base_multiplier = 1
        customer_rules = self.customer_rules
        if not customer_rules:
            return base_multiplier
        interaction_type = interaction.affordance.get_interaction_type()
        if not any(interaction_type in rule.action() for rule in self.customer_rules):
            return base_multiplier
        if interaction.affordance.is_super:
            return SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_MULTIPLIER
        return SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_SUBACTION_MULTIPLIER

    def get_employee_interaction_score_multiplier(self, interaction, sim_info):
        base_multiplier = 1
        if any(tag in SmallBusinessTunables.BUSINESS_AREA_TAGS for tag in interaction.target.get_tags()):
            base_multiplier *= SmallBusinessTunables.BUSINESS_AREA_MULTIPLIER
        interaction_type = interaction.affordance.get_interaction_type()
        if not (interaction.target is not None and (interaction.target.is_sim or any(interaction_type in rule.action() for rule in self._employee_manager.get_employee_rules_gen(sim_info)))):
            return base_multiplier
        if interaction.affordance.is_super:
            return SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_MULTIPLIER*base_multiplier
        return SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_SUBACTION_MULTIPLIER*base_multiplier

    def on_fire_ended(self):
        self._verify_ticket_machine()

    def debug_add_attendance_criteria(self, criteria_category:'ClubCriteriaCategory', criteria_param:'Union[int, TunableInstanceParam(sims4.resources.Types.TRAIT), TunableInstanceParam(sims4.resources.Types.STATISTIC), TunableInstanceParam(sims4.resources.Types.CAREER)]', required:'bool'=False, supervised:'bool'=True):
        criteria = club_tuning.CATEGORY_TO_CRITERIA_MAPPING[criteria_category]
        current_criteria = next((ac for ac in self.attendance_criteria if isinstance(ac, criteria)), None)
        if current_criteria is None:
            current_criteria = criteria(criteria_infos=None)
            self.attendance_criteria.append(current_criteria)
        current_criteria.required = required
        current_criteria.supervised = supervised
        if criteria_category == ClubCriteriaCategory.SKILL:
            if not current_criteria.skills:
                current_criteria.skills = []
            if criteria_param not in current_criteria.skills:
                current_criteria.skills.append(criteria_param)
        elif criteria_category == ClubCriteriaCategory.TRAIT:
            if not current_criteria.traits:
                current_criteria.traits = []
            if criteria_param not in current_criteria.traits:
                current_criteria.traits.append(criteria_param)
        elif criteria_category == ClubCriteriaCategory.CAREER:
            if not current_criteria.careers:
                current_criteria.careers = []
            if criteria_param not in current_criteria.careers:
                current_criteria.careers.append(criteria_param)
        elif criteria_category == ClubCriteriaCategory.FAME_RANK:
            if current_criteria.fame_rank_requirements is None:
                current_criteria.fame_rank_requirements = []
            if FameRank(criteria_param) not in current_criteria.fame_rank_requirements:
                current_criteria.fame_rank_requirements.append(FameRank(criteria_param))
        elif criteria_category == ClubCriteriaCategory.AGE:
            if current_criteria.ages is None:
                current_criteria.ages = []
            if Age(criteria_param) not in current_criteria.ages:
                current_criteria.ages.append(Age(criteria_param))
        elif criteria_category == ClubCriteriaCategory.HOUSEHOLD_VALUE:
            current_criteria.household_value = HouseholdValueCategory(criteria_param)
        elif criteria_category == ClubCriteriaCategory.RELATIONSHIP:
            current_criteria.marital_status = MaritalStatus(criteria_param)
        elif criteria_category == ClubCriteriaCategory.CARE_SIM_TYPE_SUPERVISED:
            if not current_criteria.care_sim_type_requirements:
                current_criteria.care_sim_type_requirements = []
            if CareSimType(criteria_param) not in current_criteria.care_sim_type_requirements:
                current_criteria.care_sim_type_requirements.append(CareSimType(criteria_param))

    def debug_clear_attendance_criteria(self):
        self.attendance_criteria.clear()

    def get_session_customers_served(self) -> 'int':
        return self._customer_manager.session_customers_served

    def save_data(self, business_save_data):
        super().save_data(business_save_data)
        business_save_data.small_business_save_data = Business_pb2.SmallBusinessSaveData()
        self._bucks_tracker.save_data(business_save_data.small_business_save_data)
        business_save_data.small_business_save_data.name = self._name
        business_save_data.small_business_save_data.description = self._description
        business_save_data.small_business_save_data.icon = sims4.resources.get_protobuff_for_key(self._icon)
        business_save_data.small_business_save_data.business_xp_on_open = int(self._business_xp_on_open)
        business_save_data.small_business_save_data.allowed_zone_ids.extend(self._allowed_zone_ids)
        if sims4.protocol_buffer_utils.has_field(business_save_data.small_business_save_data, 'transferred_sim_id'):
            business_save_data.small_business_save_data.transferred_sim_id = self._transferred_sim_id
        business_save_data.small_business_save_data.had_ticket_machine_once = self.had_ticket_machine_once
        business_save_data.small_business_save_data.had_employee_once = self._employee_manager.had_employee_once
        business_save_data.small_business_save_data.had_light_retail_surface_once = self._had_light_retail_surface_once
        business_save_data.small_business_save_data.business_has_been_autocreated = self.business_has_been_autocreated
        try:
            if self._name_description_key is not None:
                localized_string = Localization_pb2.LocalizedString()
                localized_string.hash = self._name_description_key[0]
                business_save_data.small_business_save_data.name_key = localized_string
                localized_string = Localization_pb2.LocalizedString()
                localized_string.hash = self._name_description_key[1]
                business_save_data.small_business_save_data.description_key = localized_string
        except:
            pass
        self._small_business_income_data.save_data(business_save_data.small_business_save_data.small_business_income_data)
        for rule in self.customer_rules:
            with ProtocolBufferRollback(business_save_data.small_business_save_data.customer_rules) as customer_rule:
                action_proto = sims4.resources.get_protobuff_for_key(rule.action.resource_key)
                customer_rule.encouraged = True
                customer_rule.interaction_group = action_proto
                if rule.with_whom is not None:
                    rule.with_whom.save(customer_rule.with_whom)
        for criteria in self.attendance_criteria:
            with ProtocolBufferRollback(business_save_data.small_business_save_data.attendance_criteria) as attendance_criteria:
                criteria.save(attendance_criteria)
        if sims4.protocol_buffer_utils.has_field(business_save_data.small_business_save_data, 'employee_data'):
            for employee_assignment in self._employee_manager.get_employee_assignments_gen():
                with ProtocolBufferRollback(business_save_data.small_business_save_data.employee_data) as employee_data:
                    employee_data.employee_id = employee_assignment.sim_id
                    for rule in self._employee_manager.get_employee_rules_gen(employee_data.employee_id):
                        with ProtocolBufferRollback(employee_data.employee_rules) as employee_rule:
                            action_proto = sims4.resources.get_protobuff_for_key(rule.action.resource_key)
                            employee_rule.encouraged = True
                            employee_rule.interaction_group = action_proto
                            if rule.with_whom is not None:
                                rule.with_whom.save(employee_rule.with_whom)
        if sims4.protocol_buffer_utils.has_field(business_save_data.small_business_save_data, 'business_visitors_ids'):
            if self.is_open:
                zone_director = services.venue_service().get_zone_director()
                if self.business_zone_id == services.current_zone_id():
                    (customer_situation, params) = zone_director.customer_situation_type_curve.get_situation_and_params()
                    situations = services.get_zone_situation_manager().get_situations_by_type(customer_situation)
                    self._business_visitor_ids = [sim.sim_id for situation in situations for sim in situation.sims_in_situation()]
            business_save_data.small_business_save_data.business_visitors_ids.extend(self._business_visitor_ids)

    def start_already_opened_business(self):
        super().start_already_opened_business()
        self._small_business_income_data.start_payment_handling()

    def should_close_after_load(self):
        if not super().should_close_after_load():
            current_zone = services.current_zone()
            if current_zone.id == self._zone_id and (current_zone.lot.get_household() is None or current_zone.lot.get_household().id != self.owner_household_id):
                return True
            else:
                return False
        return True

    def should_automatically_close(self):
        if self.is_open and not self.is_owner_household_active:
            return True
        return self.is_owner_household_active and (self._zone_id is not None and self._zone_id != services.current_zone_id())

    def load_data(self, business_save_data, is_legacy=False):
        super().load_data(business_save_data, is_legacy)
        self._bucks_tracker.load_data(business_save_data.small_business_save_data)
        self._name = business_save_data.small_business_save_data.name
        self._description = business_save_data.small_business_save_data.description
        self._icon = sims4.resources.get_key_from_protobuff(business_save_data.small_business_save_data.icon)
        self._business_xp_on_open = business_save_data.small_business_save_data.business_xp_on_open
        self.business_has_been_autocreated = business_save_data.small_business_save_data.business_has_been_autocreated
        if sims4.protocol_buffer_utils.has_field(business_save_data.small_business_save_data, 'name_key'):
            self._name_description_key = (business_save_data.small_business_save_data.name_key.hash, business_save_data.small_business_save_data.description_key.hash)
        self.had_ticket_machine_once = business_save_data.small_business_save_data.had_ticket_machine_once
        self._employee_manager.force_had_employee_once(business_save_data.small_business_save_data.had_employee_once)
        self._had_light_retail_surface_once = business_save_data.small_business_save_data.had_light_retail_surface_once
        self._small_business_income_data.load_data(business_save_data.small_business_save_data.small_business_income_data)
        new_customer_rules = self._load_rules(business_save_data.small_business_save_data.customer_rules)
        for new_rule in new_customer_rules:
            self.add_rule(new_rule, True)
        for employee in business_save_data.small_business_save_data.employee_data:
            self._employee_manager.add_employee_assignment(employee.employee_id)
            employee_rules = self._load_rules(employee.employee_rules)
            for rule in employee_rules:
                self._employee_manager.add_employee_rule(employee.employee_id, rule)
        self.update_affordance_cache()
        self.attendance_criteria = self._load_attendance_criteria(business_save_data.small_business_save_data.attendance_criteria)
        if self._name_description_key is not None:
            services.current_zone().register_callback(ZoneState.CLIENT_CONNECTED, self._set_business_name_description_key)
        self._allowed_zone_ids = [zone_id for zone_id in business_save_data.small_business_save_data.allowed_zone_ids]
        if sims4.protocol_buffer_utils.has_field(business_save_data.small_business_save_data, 'transferred_sim_id'):
            self._transferred_sim_id = business_save_data.small_business_save_data.transferred_sim_id
        if sims4.protocol_buffer_utils.has_field(business_save_data.small_business_save_data, 'business_visitors_ids'):
            self._business_visitor_ids = [id for id in business_save_data.small_business_save_data.business_visitors_ids]
        if self._is_open:
            services.get_event_manager().register_single_event(self, TestEvent.UtilityStatusChanged)
            services.get_event_manager().register_single_event(self, TestEvent.ObjectReplaced)

    def on_all_households_and_sim_infos_loaded(self) -> 'None':
        super().on_all_households_and_sim_infos_loaded()
        sim_info = services.sim_info_manager().get(self._owner_sim_id)
        self._bucks_tracker.set_owner(sim_info)
        self._bucks_tracker.on_all_households_and_sim_infos_loaded()
        self._set_listeners()
        if sim_info.aspiration_tracker is not None:
            sim_info.aspiration_tracker.set_tooltip_disabled_for_special_case(self._is_open)
        self.validate_allowed_zone_ids()
        if self.has_allowed_zone() or sim_info.household.home_zone_id == services.current_zone_id():
            self.display_notification(SmallBusinessTunables.NO_VALID_LOT_TNS)

    def validate_allowed_zone_ids(self):
        persistence_service = services.get_persistence_service()
        zone_ids_to_remove = []
        for zone_id in self._allowed_zone_ids:
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            if zone_data is not None:
                lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
                for lot_owner in lot_data.lot_owner:
                    if lot_owner.household_id == self._owner_household_id:
                        break
                zone_ids_to_remove.append(zone_id)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        residental_lot_removed = False
        for zone_id in zone_ids_to_remove:
            venue_tuning_id = build_buy.get_current_venue(zone_id)
            venue_tuning = venue_manager.get(venue_tuning_id)
            if venue_tuning.is_residential:
                residental_lot_removed = True
            self._allowed_zone_ids.remove(zone_id)
        if residental_lot_removed:
            household = services.household_manager().get(self._owner_household_id)
            if household is not None and household.home_zone_id != 0 and SmallBusinessManager.is_zone_allowed_for_small_business(household.home_zone_id, household.id):
                self._allowed_zone_ids.append(household.home_zone_id)
                self.send_data_to_client()

    def clean_up_after_unregistering(self, old_owner_sim_info:'SimInfo', new_owner_sim_info:'SimInfo') -> 'None':
        old_rank_stat = old_owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC, add=False)
        if old_rank_stat:
            old_rank_stat.set_value(old_rank_stat.initial_value)
            old_owner_sim_info.remove_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC)
        old_rep_stat = old_owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC, add=False)
        if old_rep_stat:
            old_rep_stat.set_value(old_rep_stat.initial_value)
            old_owner_sim_info.remove_statistic(SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC)
        old_owner_sim_info.remove_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC)
        self._total_open_hours = 0
        old_owner_sim_info.remove_buff_by_type(SmallBusinessTunables.BUSINESS_EVENTS_COOLDOWN_BUFF)
        services.get_event_manager().process_event(TestEvent.BusinessDataUpdated)
        if new_owner_sim_info is not None:
            new_owner_sim_info.remove_trait(SmallBusinessTunables.TRAIT_ON_TRANSFER_BUSINESS)
        business_tag = SmallBusinessTunables.BUSINESS_TAG
        for trait in tuple(old_owner_sim_info.trait_tracker):
            if business_tag in trait.tags:
                old_owner_sim_info.remove_trait(trait)
        if self._value_stat_listener is not None:
            tracker = old_owner_sim_info.get_tracker(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC)
            tracker.remove_listener(self._value_stat_listener)
            self._value_stat_listener = None
        employee_tuning_data = self._employee_manager.get_employee_tuning_data_for_employee_type(SmallBusinessTunables.EMPLOYEE_TYPE)
        old_owner_sim_info.career_tracker.remove_career(employee_tuning_data.career.guid64, owner_id=old_owner_sim_info.sim_id, post_quit_msg=False)
        for employee_info in self.get_employees_sim_info():
            self.remove_employee(employee_info, is_quitting=False)

    def modify_funds(self, amount, employee_wages:'bool'=False, **kwargs) -> 'None':
        reason = Consts_pb2.FUNDS_SMALL_BUSINESS_EMPLOYEE if employee_wages else Consts_pb2.FUNDS_RETAIL_PROFITS
        if amount == 0:
            return
        sim_info = services.sim_info_manager().get(self.owner_sim_id)
        if sim_info:
            if amount < 0:
                sim_info.household.funds.try_remove(-amount, reason)
            else:
                sim_info.household.funds.add(amount, reason)

    def _check_if_in_process_of_another_transfer(self, sim_id):
        if self.owner_household_id is not None:
            tracker = services.business_service().get_business_tracker_for_household(self.owner_household_id, self.business_type)
            for manager in tracker._business_managers.values():
                if manager._transferred_sim_id == sim_id:
                    return True
            for manager in tracker._zoneless_business_managers.values():
                if manager._transferred_sim_id == sim_id:
                    return True
        return False

    def transfer_business(self, new_owner_sim_info:'SimInfo') -> 'None':
        old_owner_id = self.owner_sim_id
        new_owner_id = new_owner_sim_info.id
        self._transferred_sim_id = 0
        old_owner_sim_info = services.sim_info_manager().get(old_owner_id)
        if SmallBusinessTunables.LOOT_ON_UNREGISTER_BUSINESS is not None:
            unregister_loot_resolver = SingleSimResolver(old_owner_sim_info)
            SmallBusinessTunables.LOOT_ON_UNREGISTER_BUSINESS.apply_to_resolver(unregister_loot_resolver)
        business_rank_stat = old_owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC, add=False)
        business_rank = None
        if business_rank_stat is not None:
            previous_owner_highest_level = business_rank_stat.get_user_value()
            business_rank = business_rank_stat.get_value()
            new_owner_sim_info.add_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC, business_rank, from_transfer=True)
            new_owner_ranked_stat = new_owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC, add=False)
            new_owner_ranked_stat.highest_level = previous_owner_highest_level
        business_reputation_stat = old_owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC, add=False)
        if business_reputation_stat is not None:
            business_reputation = business_reputation_stat.get_value()
            from_load = business_reputation == business_reputation_stat.default_value
            new_owner_sim_info.add_statistic(SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC, business_reputation, from_load=from_load)
        business_value_stat = old_owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC, add=False)
        if business_value_stat is not None:
            business_value = business_value_stat.get_value()
            new_owner_sim_info.add_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC, business_value)
        self.set_owner_household_id(new_owner_sim_info.household.id)
        self._bucks_tracker.transfer_owner(new_owner_sim_info, business_rank)
        self.clean_up_after_unregistering(old_owner_sim_info, new_owner_sim_info)
        self._owner_sim_id = new_owner_id
        self.add_owner_career()
        self._employee_manager.transfer(new_owner_id)
        self.send_data_to_client()
        if SmallBusinessTunables.LOOT_ON_REGISTER_BUSINESS is not None:
            register_loot_resolver = SingleSimResolver(new_owner_sim_info)
            SmallBusinessTunables.LOOT_ON_REGISTER_BUSINESS.apply_to_resolver(register_loot_resolver)
        delete_message = Business_pb2.DeleteSimBusiness()
        delete_message.sim_id = old_owner_id
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SIM_BUSINESS_DELETE, delete_message)
        Distributor.instance().add_op_with_no_owner(op)

    def on_zoneless_owner_sim_changed_household(self, new_owner_id:'int', household_id:'int') -> 'None':
        self.set_owner_household_id(household_id)
        self.reset_allowed_zones()
        self.add_owner_career()
        self._transferred_sim_id = 0
        self.send_data_to_client()

    def on_death(self, sim_info:'SimInfo', show_transfer_dialog=True) -> 'None':
        self.set_open(False)
        household_sim_infos = [household_sim_info for household_sim_info in sim_info.household if household_sim_info.id != sim_info.id]
        relationship_service = services.relationship_service()

        def compare_func(item1, item2):
            relationship_value_1 = relationship_service.get_relationship_score(item1.id, sim_info.id)
            relationship_value_2 = relationship_service.get_relationship_score(item2.id, sim_info.id)
            return relationship_value_2 - relationship_value_1

        household_sim_infos.sort(key=functools.cmp_to_key(compare_func))
        business_service = services.business_service()
        business_manager_of_dead_sim = business_service.get_business_manager_for_sim(sim_id=sim_info.id)
        active_household_id = services.active_household_id()

        def send_inheritance_telemetry(dead_owner_sim_id, target_sim_info):
            business_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)
            with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_INHERIT, household=services.household_manager().get(target_sim_info.household_id)) as hook:
                hook.write_enum(TELEMETRY_HOOK_BUSINESS_ID, dead_owner_sim_id)
                hook.write_enum(TELEMETRY_HOOK_TARGET_SIM, target_sim_info.id)

        is_dependent_household = not any(sim_info.can_live_alone for sim_info in household_sim_infos)
        for household_sim_info in household_sim_infos:
            if not household_sim_info.is_toddler_or_younger:
                if household_sim_info.species != Species.HUMAN:
                    pass
                else:
                    business_manager = business_service.get_business_manager_for_sim(sim_id=household_sim_info.id)
                    if business_manager is not None:
                        pass
                    elif self._check_if_in_process_of_another_transfer(household_sim_info.id):
                        pass
                    else:
                        if sim_info.household_id != active_household_id or show_transfer_dialog and is_dependent_household:
                            business_service.transfer_business_to_sim(sim_info, household_sim_info, BusinessType.SMALL_BUSINESS)
                            send_inheritance_telemetry(business_manager_of_dead_sim.owner_sim_id, household_sim_info)
                            break
                        if SmallBusinessTunables.SMALL_BUSINESS_OWNER_ON_DEATH_LOOT is not None:
                            double_sim_resolver = DoubleSimResolver(sim_info, household_sim_info)
                            SmallBusinessTunables.SMALL_BUSINESS_OWNER_ON_DEATH_LOOT.apply_to_resolver(double_sim_resolver)
                            self._transferred_sim_id = household_sim_info.id
                            send_inheritance_telemetry(business_manager_of_dead_sim.owner_sim_id, household_sim_info)
                            break
        business_service.remove_owner_zoneless_business(sim_info, business_manager_of_dead_sim.business_type, sell=True)
        services.get_event_manager().process_event(TestEvent.BusinessDataUpdated)

    def _on_business_value_changed(self, stat):
        profit_msg = Business_pb2.BusinessProfitUpdate()
        profit_msg.sim_id = self.owner_sim_id
        profit_msg.net_profit = int(self.get_business_value())
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.BUSINESS_PROFIT_UPDATE, profit_msg)
        Distributor.instance().add_op_with_no_owner(op)

    def show_hobby_class_cancel_dialog(self, sim_info, situation, _connection=None) -> 'None':

        def on_response(dialog, situation):
            if not dialog.accepted:
                return
            situation._self_destruct()
            self._close_business()

        notification = SmallBusinessTunables.HOBBY_CLASS_CLOSE_BUSINESS_WARNING_DIALOG(sim_info)
        notification.show_dialog(on_response=lambda dialog: on_response(dialog, situation))

    def get_customer_appreciation_day_reason(self):
        return REASON_CUSTOMER_APPRECIATION_DAY

    def is_customer_appreciation_day_perk_active(self) -> 'bool':
        owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
        if owner_sim_info is not None and not owner_sim_info.household.is_active_household:
            return False
        else:
            customer_appreciation_day_perk = SmallBusinessTunables.PERK_SETTINGS.customer_appreciation_day
            if customer_appreciation_day_perk is not None:
                owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
                if owner_sim_info.has_buff(customer_appreciation_day_perk.buff.buff_type):
                    return True
        return False

    def show_customer_appreciation_day_cancel_dialog(self, sim_info:'SimInfo') -> 'None':
        customer_appreciation_day_perk = SmallBusinessTunables.PERK_SETTINGS.customer_appreciation_day

        def on_response(dialog):
            if not dialog.accepted:
                return
            if customer_appreciation_day_perk is not None:
                owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
                owner_sim_info.remove_buff_by_type(customer_appreciation_day_perk.buff.buff_type)
            self._close_business()

        notification = customer_appreciation_day_perk.confirmation_dialog(sim_info)
        notification.show_dialog(on_response=on_response)

    def send_small_business_open_close_info_to_automation_output(self, is_open:'bool'):
        connection = services.client_manager().get_first_client_id()
        if connection is None:
            return
        automation_output('BusinessOpenResponse; Status:Open'.format('Open' if is_open else 'Closed'), connection)
        if not is_open:
            business_reputation = None
            owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
            if owner_sim_info is None:
                return
            business_reputation_stat = owner_sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC, add=False)
            if business_reputation_stat is not None:
                business_reputation = business_reputation_stat.get_value()
            revenue_records = self.small_business_income_data._current_day_business_income_record.revenue_source_records
            attendance_sale_count = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_HOURLY_FEE].count + revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_ENTRY_FEE].count
            interaction_sale_count = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE].count
            light_retail_sale_count = revenue_records[PaymentBusinessRevenueType.SMALL_BUSINESS_LIGHT_RETAIL_FEE].count
            number_of_successful_sales = attendance_sale_count + interaction_sale_count + light_retail_sale_count
            automation_output('BusinessCloseResponse; Rank:{}, Reputation:{}, Customers:{}, AttendanceSales:{}, InteractionSales:{}, LightRetailSales:{}, TotalSales:{}'.format(self.get_business_rank_level(), business_reputation, self.get_session_customers_served(), attendance_sale_count, interaction_sale_count, light_retail_sale_count, number_of_successful_sales), connection)

    def add_allowed_zone_id(self, zone_id:'int') -> 'None':
        if zone_id not in self._allowed_zone_ids:
            self._allowed_zone_ids.append(zone_id)
            if self._name is not None and self._name:
                self.notify_lot_purchase(zone_id)

    def notify_lot_purchase(self, zone_id) -> 'None':
        sim_info = services.sim_info_manager().get(self.owner_sim_id)
        resolver = DoubleSimResolver(sim_info, None)
        resolver.set_additional_participant(ParticipantType.RandomZoneId, (zone_id,))
        self.display_notification(SmallBusinessTunables.PURCHASED_LOT_AUTO_ASSIGNED_TO_SMALL_BUSINESS_TNS, resolver=resolver)

    def is_zone_assigned_allowed(self, zone_id) -> 'bool':
        return zone_id in self._allowed_zone_ids

    def has_allowed_zone(self) -> 'bool':
        return len(self._allowed_zone_ids) > 0

    def get_allowed_zone_ids(self):
        return self._allowed_zone_ids

    def handle_on_lot_not_owned_anymore(self, zone_id):
        if zone_id in self._allowed_zone_ids:
            self._allowed_zone_ids.remove(zone_id)
        owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
        home_zone_id = owner_sim_info.household.home_zone_id
        if self.has_allowed_zone() or home_zone_id != zone_id:
            is_home_zone_allowed_for_small_business = SmallBusinessManager.is_zone_allowed_for_small_business(home_zone_id, owner_sim_info.household.id)
            if is_home_zone_allowed_for_small_business:
                self._allowed_zone_ids.append(home_zone_id)
        self.send_data_to_client()
        if not self.has_allowed_zone():
            self.display_notification(SmallBusinessTunables.NO_VALID_LOT_TNS)

    def reset_allowed_zones(self):
        self._allowed_zone_ids.clear()
        owner_household = services.household_manager().get(self.owner_household_id)
        if SmallBusinessManager.is_zone_allowed_for_small_business(owner_household.home_zone_id, self.owner_household_id):
            self._allowed_zone_ids.append(owner_household.home_zone_id)

    @staticmethod
    def is_zone_allowed_for_small_business(zone_id:'int', household_id:'int'):
        business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        if business_manager is not None and business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return False
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_key = build_buy.get_current_venue(zone_id, allow_ineligible=True)
        venue_tuning = venue_manager.get(venue_key)
        if venue_tuning is not None and not (venue_tuning.is_residential or venue_tuning.is_small_business):
            return False
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is not None:
            lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
            for lot_owner in lot_data.lot_owner:
                if lot_owner is not None and lot_owner.household_id == household_id:
                    return True
        return False

    @property
    def clear_lot_ownership_on_death_of_owner(self) -> 'bool':
        return False

    def on_zone_load(self):
        super().on_zone_load()
        self._amount_of_ticket_machines_in_current_lot = self.get_ticket_machine_count()
        owner_sim_info = services.sim_info_manager().get(self.owner_sim_id)
        if self._bucks_tracker is not None and owner_sim_info is not None and owner_sim_info.household.is_active_household:
            self._bucks_tracker.distribute_bucks(SmallBusinessTunables.SMALL_BUSINESS_PERKS_BUCKS_TYPE.value)
