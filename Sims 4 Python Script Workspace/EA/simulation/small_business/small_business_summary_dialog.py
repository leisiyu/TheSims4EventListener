from __future__ import annotationsimport servicesfrom sims4.localization import LocalizationHelperTuningfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from small_business.small_business_income_data import SmallBusinessIncomeRecord, SingleRevenueSourceRecordfrom business.business_enums import SmallBusinessAttendanceSaleModefrom business.business_summary_dialog import BusinessSummaryDialog, BusinessSummaryLineItemTypefrom interactions.payment.payment_info import PaymentBusinessRevenueTypeimport sims4from small_business.small_business_tuning import SmallBusinessTunableslogger = sims4.log.Logger('Business', default_owner='sersanchez')DEFAULT_FRAME = 'default'VIRAL_SOCIAL_MEDIA_ACTIVE_FRAME = 'viral_social_media_active'ULTRASONIC_WHISTLE_ACTIVE_FRAME = 'ultrasonic_whistle_active'VIRAL_SOCIAL_MEDIA_AND_ULTRASONIC_ACTIVE_FRAME = 'viral_social_media_and_ultrasonic_whistle_active'
class SmallBusinessSummaryDialog(BusinessSummaryDialog):

    def __init__(self, *args, is_from_close:'bool'=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_EOD = is_from_close
        self._report_msg.is_global_overview = not self._is_EOD
        self._report_msg.hide_review_stars = True
        self._report_msg.show_sim_bubble = True
        self._report_msg.show_staff_report = False
        if hasattr(self._report_msg, 'default_highlight_finances_help'):
            self._report_msg.default_highlight_finances_help = True
        self._init_custom_stats_container()
        if self._is_EOD:
            self._income_data = self._business_manager.small_business_income_data.current_day_business_income_record
        else:
            self._income_data = self._business_manager.small_business_income_data.total_business_income_record
        self.opening_fee_data = self._income_data.revenue_source_records[PaymentBusinessRevenueType.SMALL_BUSINESS_OPENING_FEE]
        self.hourly_fee_data = self._income_data.revenue_source_records[PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_HOURLY_FEE]
        self.entry_fee_data = self._income_data.revenue_source_records[PaymentBusinessRevenueType.SMALL_BUSINESS_ATTENDANCE_ENTRY_FEE]
        self.interaction_fee_data = self._income_data.revenue_source_records[PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE]
        self.light_retail_fee_data = self._income_data.revenue_source_records[PaymentBusinessRevenueType.SMALL_BUSINESS_LIGHT_RETAIL_FEE]
        self.employee_wages_data = self._income_data.revenue_source_records[PaymentBusinessRevenueType.EMPLOYEE_WAGES]
        self.tip_jar = self._income_data.revenue_source_records[PaymentBusinessRevenueType.SMALL_BUSINESS_TIP_JAR_FEE]

    def _calculated_profit(self):
        business_open_fee = self.opening_fee_data.profit
        hourly_fee_profit = self.hourly_fee_data.profit
        entry_fee_profit = self.entry_fee_data.profit
        interaction_fee_profit = self.interaction_fee_data.profit
        light_retail_fee_profit = self.light_retail_fee_data.profit
        employee_wages = self.employee_wages_data.profit
        tip_jar = self.tip_jar.profit
        return hourly_fee_profit + entry_fee_profit + interaction_fee_profit + light_retail_fee_profit + tip_jar - (business_open_fee + employee_wages)

    def _add_line_entries(self):
        if self._is_EOD:
            self._add_end_of_day_line_entries()
        else:
            self._add_global_record_line_entries()

    def _add_global_record_line_entries(self):
        self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_BUSINESS_OPENING_FEE_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(-self.opening_fee_data.profit))
        had_or_has_ticket_machine = self._business_manager.had_ticket_machine_once or self._business_manager.is_ticket_machine_on_lot()
        no_ticket_machine_tooltip = (SmallBusinessTunables.SUMMARY_DIALOG_NO_TICKET_MACHINE_TOOLTIP, None)[had_or_has_ticket_machine]
        self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_ATTENDANCE_FEES_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.entry_fee_data.profit + self.hourly_fee_data.profit), is_locked=not had_or_has_ticket_machine, tooltip=no_ticket_machine_tooltip)
        had_light_retail_surfaces = self._business_manager.had_light_retail_surface_once()
        no_light_retail_surfaces_tooltip = (SmallBusinessTunables.SUMMARY_DIALOG_NO_LIGHT_RETAIL_TOOLTIP, None)[had_light_retail_surfaces]
        self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_LIGHT_RETAIL_SALES_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.light_retail_fee_data.profit), is_locked=not had_light_retail_surfaces, tooltip=no_light_retail_surfaces_tooltip)
        self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_INTERACTION_SALES_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.interaction_fee_data.profit))
        if self.tip_jar.profit > 0:
            self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_TIP_JAR_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.tip_jar.profit))
        self._add_employee_wages_line_entry()

    def _add_end_of_day_line_entries(self):
        self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_BUSINESS_OPENING_FEE_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(-self.opening_fee_data.profit))
        attendance_sale_mode = self._business_manager.small_business_income_data.attendance_sale_mode
        has_ticket_machine = self._business_manager.is_ticket_machine_on_lot()
        no_ticket_machine_tooltip = (SmallBusinessTunables.SUMMARY_DIALOG_NO_TICKET_MACHINE_TOOLTIP, None)[has_ticket_machine]
        if attendance_sale_mode == SmallBusinessAttendanceSaleMode.HOURLY_FEE:
            if self._business_manager.get_session_customers_served() == 0:
                average_hours = 0
            else:
                average_hours = int(self.hourly_fee_data.count/self._business_manager.get_session_customers_served())
            self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_ATTENDANCE_FEES_HEADER, BusinessSummaryLineItemType.WITH_SUBTITLE_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.hourly_fee_data.profit), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_HOURLY_FEES_TEXT(average_hours), is_locked=not has_ticket_machine, tooltip=no_ticket_machine_tooltip)
        elif attendance_sale_mode == SmallBusinessAttendanceSaleMode.ENTRY_FEE:
            sim_info = services.sim_info_manager().get(self._business_manager.owner_sim_id)
            bucks_tracker = self._business_manager.get_bucks_tracker()
            if self.entry_fee_data.count > 0 and (sim_info is not None and bucks_tracker is not None) and (bucks_tracker.is_perk_unlocked(SmallBusinessTunables.PERK_SETTINGS.viral_on_social_media.perk) or sim_info.has_trait(SmallBusinessTunables.PERK_SETTINGS.ultrasonic_whistle.trait)):
                self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_ATTENDANCE_FEES_HEADER, BusinessSummaryLineItemType.CUSTOM_BACKGROUND_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_WITH_PERK_BOOST_TEXT(self.entry_fee_data.profit), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_ENTRY_FEES_TEXT(self.entry_fee_data.count), is_locked=not has_ticket_machine, tooltip=no_ticket_machine_tooltip)
            else:
                self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_ATTENDANCE_FEES_HEADER, BusinessSummaryLineItemType.WITH_SUBTITLE_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.entry_fee_data.profit), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_ENTRY_FEES_TEXT(self.entry_fee_data.count), is_locked=not has_ticket_machine, tooltip=no_ticket_machine_tooltip)
        else:
            self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_ATTENDANCE_FEES_HEADER, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.entry_fee_data.profit + self.hourly_fee_data.profit), is_locked=True, tooltip=SmallBusinessTunables.SUMMARY_DIALOG_ATTENDANCE_SALES_DISABLED_TOOLTIP)
        light_retail_enabled = self._business_manager.small_business_income_data.is_light_retail_enabled
        has_light_retail_surfaces = self._business_manager.is_light_retail_surface_on_lot()
        no_light_retail_surfaces_tooltip = (SmallBusinessTunables.SUMMARY_DIALOG_NO_LIGHT_RETAIL_TOOLTIP, None)[has_light_retail_surfaces]
        if light_retail_enabled:
            self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_LIGHT_RETAIL_SALES_HEADER, BusinessSummaryLineItemType.WITH_SUBTITLE_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.light_retail_fee_data.profit), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_AMOUNT_TEXT(self.light_retail_fee_data.count), is_locked=not has_light_retail_surfaces, tooltip=no_light_retail_surfaces_tooltip)
        else:
            self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_LIGHT_RETAIL_SALES_HEADER, BusinessSummaryLineItemType.WITH_SUBTITLE_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(0), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_AMOUNT_TEXT(0), is_locked=True, tooltip=SmallBusinessTunables.SUMMARY_DIALOG_LIGHT_RETAIL_SALES_DISABLED_TOOLTIP)
        self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_INTERACTION_SALES_HEADER, BusinessSummaryLineItemType.WITH_SUBTITLE_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.interaction_fee_data.profit), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_AMOUNT_TEXT(self.interaction_fee_data.count))
        tip_jar_settings = SmallBusinessTunables.PERK_SETTINGS.tip_jar
        bucks_tracker = self._business_manager.get_bucks_tracker()
        if bucks_tracker is not None:
            for tip_type in tip_jar_settings.tip_types:
                if bucks_tracker.is_perk_unlocked_and_unfrozen(tip_type.perk):
                    self._add_line_entry(SmallBusinessTunables.SUMMARY_DIALOG_TIP_JAR_HEADER, BusinessSummaryLineItemType.WITH_SUBTITLE_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(self.tip_jar.profit), subtitle=SmallBusinessTunables.SUMMARY_DIALOG_AMOUNT_TEXT(self.tip_jar.count))
                    break
        self._add_employee_wages_line_entry()

    def _add_net_profit(self, calculated_profit):
        if self._is_EOD:
            xp_gained = self._business_manager.get_xp_gained_on_business_day()
            self._add_line_entry(self._business_tuning.summary_dialog_wages_net_profit_header, BusinessSummaryLineItemType.TOTAL_WITH_BUCKS_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(int(calculated_profit)), entry_bucks=SmallBusinessTunables.SUMMARY_DIALOG_BUCKS_GAINED_TEXT(xp_gained))
        else:
            self._add_line_entry(self._business_tuning.summary_dialog_wages_net_profit_header, BusinessSummaryLineItemType.TOTAL_WITH_BUCKS_LINE_ITEM, SmallBusinessTunables.SUMMARY_DIALOG_CURRENCY_TEXT(int(calculated_profit)))

    def _add_employee_wages_line_entry(self):
        if self._is_EOD:
            has_employees = self._business_manager.employee_count > 0
            employee_tooltip = (SmallBusinessTunables.SUMMARY_DIALOG_NO_EMPLOYEES_TOOLTIP, None)[has_employees]
            self._add_line_entry(self._business_tuning.summary_dialog_wages_owed_header, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, self._business_tuning.summary_dialog_wages_owed_text(-self.employee_wages_data.profit), is_locked=not has_employees, tooltip=employee_tooltip)
        else:
            had_employees = self._business_manager.had_employee_once
            employee_tooltip = (SmallBusinessTunables.SUMMARY_DIALOG_NO_EMPLOYEES_TOOLTIP, None)[had_employees]
            self._add_line_entry(self._business_tuning.summary_dialog_wages_owed_header, BusinessSummaryLineItemType.BEVELED_ENTRY_LINE_ITEM, self._business_tuning.summary_dialog_wages_owed_text(-self.employee_wages_data.profit), is_locked=not had_employees, tooltip=employee_tooltip)

    def _add_employee_data(self):
        pass

    def _init_custom_stats_container(self):
        show_custom_stats_container = False
        sim_info = services.sim_info_manager().get(self._business_manager.owner_sim_id)
        bucks_tracker = self._business_manager.get_bucks_tracker()
        if bucks_tracker is not None:
            is_viral_social_media_unlocked = bucks_tracker.is_perk_unlocked(SmallBusinessTunables.PERK_SETTINGS.viral_on_social_media.perk)
            is_ultrasonic_whistle_unlocked = sim_info.has_trait(SmallBusinessTunables.PERK_SETTINGS.ultrasonic_whistle.trait)
            background_type = DEFAULT_FRAME
            tooltip_text = None
            if is_ultrasonic_whistle_unlocked and is_viral_social_media_unlocked:
                show_custom_stats_container = True
                background_type = VIRAL_SOCIAL_MEDIA_ACTIVE_FRAME
                perk_names = [SmallBusinessTunables.PERK_SETTINGS.ultrasonic_whistle.perk_name, SmallBusinessTunables.PERK_SETTINGS.viral_on_social_media.perk_name]
                tooltip_text = LocalizationHelperTuning.get_comma_separated_list(*perk_names)
            elif is_ultrasonic_whistle_unlocked:
                show_custom_stats_container = True
                background_type = ULTRASONIC_WHISTLE_ACTIVE_FRAME
                tooltip_text = SmallBusinessTunables.PERK_SETTINGS.ultrasonic_whistle.perk_name
            elif is_viral_social_media_unlocked:
                show_custom_stats_container = True
                background_type = VIRAL_SOCIAL_MEDIA_ACTIVE_FRAME
                tooltip_text = SmallBusinessTunables.PERK_SETTINGS.viral_on_social_media.perk_name
            if hasattr(self._report_msg, 'stats_custom_tooltip'):
                self._report_msg.show_custom_stats_container = show_custom_stats_container
            if hasattr(self._report_msg, 'stats_custom_background'):
                self._report_msg.stats_custom_background = background_type
            if tooltip_text:
                self._report_msg.stats_custom_tooltip = SmallBusinessTunables.SUMMARY_DIALOG_PERK_BOOST_TOOLIP_TEXT(tooltip_text)
