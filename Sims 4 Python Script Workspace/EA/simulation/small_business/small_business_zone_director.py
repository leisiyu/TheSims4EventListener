import servicesfrom business.business_enums import BusinessTypefrom business.small_business_zone_director_mixin import SmallBusinessZoneDirectorMixinfrom event_testing.resolver import SingleSimResolverfrom sims.sim_info import SimInfofrom small_business.small_business_tuning import SmallBusinessTunablesfrom venues.scheduling_zone_director import SchedulingZoneDirectorSUPPORTED_BUSINESS_TYPES = (BusinessType.SMALL_BUSINESS,)
class SmallBusinessZoneDirector(SmallBusinessZoneDirectorMixin, SchedulingZoneDirector):

    @property
    def supported_business_types(self):
        return SUPPORTED_BUSINESS_TYPES

    def notify_buy_small_business_venue(self, active_sim_info:SimInfo) -> None:
        dialog = SmallBusinessTunables.BUY_SMALL_BUSINESS_VENUE_TNS(active_sim_info, SingleSimResolver(active_sim_info))
        dialog.show_dialog()

    def on_loading_screen_animation_finished(self) -> None:
        super().on_loading_screen_animation_finished()
        active_sim_info = services.active_sim_info()
        if active_sim_info is None:
            return
        owner_household = services.owning_household_of_active_lot()
        if owner_household is None:
            self.notify_buy_small_business_venue(active_sim_info)
            return
        if all(sim_info.is_dead for sim_info in owner_household.sim_info_gen()):
            self.notify_buy_small_business_venue(active_sim_info)
            return
        if owner_household.id != active_sim_info.household_id:
            return
        is_household_business_assigned = False
        current_zone_id = services.current_zone_id()
        business_tracker = services.business_service().get_business_tracker_for_household(owner_household.id, BusinessType.SMALL_BUSINESS)
        if business_tracker.zoneless_business_managers:
            for (sim_id, business_manager) in business_tracker.zoneless_business_managers.items():
                if business_manager.is_zone_assigned_allowed(current_zone_id):
                    is_household_business_assigned = True
        if business_tracker and owner_household.id == active_sim_info.household_id and not is_household_business_assigned:
            small_business_manager = services.business_service().get_business_manager_for_sim(active_sim_info.id)
            if small_business_manager:
                dialog = SmallBusinessTunables.ASSIGN_VENUE_TO_SMALL_BUSINESS_TNS(active_sim_info, SingleSimResolver(active_sim_info))
            else:
                dialog = SmallBusinessTunables.ASSIGN_VENUE_TO_NEW_SMALL_BUSINESS_TNS(active_sim_info, SingleSimResolver(active_sim_info))
            dialog.show_dialog()
