from __future__ import annotationsimport enumimport telemetry_helperfrom business.unit_rating.unit_rating_enums import UnitRatingAlertStatefrom clock import interval_in_sim_weeksfrom sims4 import mathfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from Business_pb2 import BusinessSaveData, RentalUnitBusinessDataUpdate, SetBusinessData
    from event_testing.resolver import Resolver
    from sims.sim_info import SimInfofrom protocolbuffers import DistributorOps_pb2from business.business_rule import BusinessRulefrom business.business_rule_enums import BusinessRuleStatefrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import ZoneResolver, SingleSimAndHouseholdResolverfrom multi_unit.multi_unit_tuning import MultiUnitTuningfrom business.business_enums import BusinessType, FirstTimeMessageTypefrom business.business_manager import BusinessManager, TELEMETRY_GROUP_BUSINESSfrom business.business_rule_manager import BusinessRuleManagerMixinfrom business.unit_rating.unit_rating_tuning import UnitRatingTuningfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom protocolbuffers import Business_pb2, GameplaySaveData_pb2, Consts_pb2from sims.bills import Billsfrom singletons import DEFAULTimport alarmsimport date_and_timeimport sims4import build_buyimport servicesTELEMETRY_HOOK_RENTAL_UNIT_ACTION = 'RUAC'TELEMETRY_HOOK_CHANGE_UNIT_RATING_SCORE = 'CHSC'TELEMETRY_FIELD_PROPERTY_OWNER_ACTION_TYPE = 'poat'TELEMETRY_FIELD_PROPERTY_OWNER_ACTION_DESCRIPTION = 'poad'TELEMETRY_FIELD_IS_GRACE_PERIOD = 'grpd'TELEMETRY_FIELD_LOT_DESCRIPTION_ID = 'hlid'TELEMETRY_FIELD_NEW_SCORE_VALUE = 'scre'TELEMETRY_FIELD_UNIT_ID = 'unid'TELEMETRY_GROUP_RENT = 'RENT'TELEMETRY_HOOK_LATE = 'LATE'business_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)logger = sims4.log.Logger('Rental Unit Manager')MAX_BILLED_RENT_DAYS = 7
class PropertyOwnerAction(enum.Int):
    ChangeRent = 0
    EvictTenant = 1
    ChangeRule = 2

class RentalUnitManager(BusinessRuleManagerMixin, BusinessManager):

    def __init__(self) -> 'None':
        super().__init__(BusinessType.RENTAL_UNIT)
        self.dynamic_unit_rating = UnitRatingTuning.MAINTENANCE_RATING_START_VALUE
        self._rent = 0
        self.lot_tile_count = 0
        self._signed_lease_length = 0
        self.due_rent = 0
        self.overdue_rent = 0
        self.max_rent = 0
        self.paid_rent_awaiting_transfer = 0
        self.tenant_alert_visible = False
        self._grace_period_alarm_handle = None
        self._has_tenant_ever_paid_rent = False
        self._has_tenant_ever_received_rent_bill = False
        self._unit_rating_alert_state = UnitRatingAlertState.CLEAR
        self._is_grace_period = None
        self._house_description_id = None

    @property
    def persisted_npc_owned(self) -> 'bool':
        return True

    @property
    def signed_lease_length(self) -> 'int':
        return self._signed_lease_length

    @signed_lease_length.setter
    def signed_lease_length(self, lease_length:'int') -> 'None':
        self._signed_lease_length = lease_length

    @property
    def rent(self) -> 'int':
        return self._rent

    @property
    def occupied(self) -> 'bool':
        return services.get_persistence_service().get_household_id_from_zone_id(self.business_zone_id) != 0

    @property
    def clear_lot_ownership_on_sell(self) -> 'bool':
        return False

    @property
    def clear_lot_ownership_on_death_of_owner(self) -> 'bool':
        return False

    @property
    def disown_household_objects_on_sell(self) -> 'bool':
        return False

    @property
    def include_furniture_price_on_sell(self) -> 'bool':
        return not self.occupied

    @property
    def house_description_id(self) -> 'int':
        if self.business_zone_id is not None:
            self._house_description_id = services.get_persistence_service().get_house_description_id(self.business_zone_id)
        return self._house_description_id

    @house_description_id.setter
    def house_description_id(self, value:'int') -> 'None':
        self._house_description_id = value

    @property
    def _grace_period_times(self) -> 'Tuple[date_and_time.DateAndTime, date_and_time.DateAndTime]':
        grace_start_time = MultiUnitTuning.GRACE_PERIOD.starting_time + date_and_time.create_time_span(days=1)
        return (grace_start_time, grace_start_time + MultiUnitTuning.GRACE_PERIOD.duration())

    @property
    def _elapsed_open_days(self) -> 'int':
        sim_now = services.time_service().sim_now
        return int(sim_now.absolute_days()) - int(self._open_time.absolute_days())

    @property
    def is_grace_period(self) -> 'bool':
        if self._is_grace_period is not None:
            return self._is_grace_period
        return self._update_grace_period(needs_return=True)

    @property
    def has_tenant_ever_paid_rent(self) -> 'bool':
        return self._has_tenant_ever_paid_rent

    def _open_pure_npc_store(self, is_premade:'bool') -> 'None':
        if is_premade and self.max_rent == 0:
            self.on_zone_load()
        self.set_open(True)
        services.get_multi_unit_ownership_service().refresh_relationships(self.business_zone_id)

    def prepare_for_off_lot_simulation(self) -> 'None':
        pass

    def on_zone_load(self) -> 'None':
        super().on_zone_load()
        if self.business_zone_id is None:
            return
        if self.house_description_id:
            tenant_hh = services.household_manager().get_by_home_zone_id(self._zone_id)
            self._rent = services.get_rent(self.house_description_id)
            if self._rent == sims4.math.MAX_UINT32:
                logger.error('Detected invalid rent value {} for house {}; adjusting to an initial rent value.', self._rent, self.house_description_id)
                self.set_initial_rent()
                business_unit_data = [(self.business_zone_id, self.house_description_id, self._rent)]
                services.set_initial_unit_rent_prices(services.current_zone_id(), business_unit_data)
                if tenant_hh is not None:
                    bills = tenant_hh.bills_manager
                    over_max_rent_threshold = MAX_BILLED_RENT_DAYS*self._rent*2
                    if bills.housing_costs_owed > over_max_rent_threshold:
                        bills.cap_housing_costs(over_max_rent_threshold)
            self._signed_lease_length = services.get_signed_lease_length(self.house_description_id)
            was_open = self._is_open
            self.set_open(tenant_hh is not None)
            if was_open and self._is_open:
                self._update_grace_period(from_load=True)
            if self.max_rent == 0:
                self.calculate_max_rent()

    def should_close_after_load(self) -> 'bool':
        return False

    def on_build_buy_enter(self) -> 'None':
        pass

    def on_build_buy_exit(self) -> 'None':
        if not self.meets_requirements_to_be_open():
            self.set_open(False)
        plex_service = services.get_plex_service()
        group_zone_ids = plex_service.get_plex_zones_in_group(self.business_zone_id)
        business_service = services.business_service()
        for zone_id in group_zone_ids:
            business_manager = business_service.get_business_manager_for_zone(zone_id)
            if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
                if business_manager.meets_tenant_requirement():
                    pass
                else:
                    business_manager.set_latest_tile_count()
                    business_manager.calculate_max_rent()

    def on_rating_change(self, previous_whole_star_rating:'int', current_whole_star_rating:'int', rating_delta:'Optional[int]'=None) -> 'None':
        target_household = services.household_manager().get_by_home_zone_id(self._zone_id)
        if target_household is None or target_household.id != self._owner_household_id:
            super().on_rating_change(previous_whole_star_rating, current_whole_star_rating)
            if self.is_owner_household_active or target_household is not None and target_household.is_active_household:
                services.business_service().show_first_time_dialog(self, FirstTimeMessageType.ANY_RATING_CHANGE_TENANT)
            self._star_rating_value = float(current_whole_star_rating)
            services.get_event_manager().process_event(TestEvent.RentalUnitStarRatingChanged, sim_info=services.active_sim_info())
            if rating_delta is not None and rating_delta != 0:
                new_alert_state = UnitRatingAlertState.INCREASE if rating_delta > 0 else UnitRatingAlertState.DECREASE
                self.set_unit_rating_alert_state(new_alert_state)
        if previous_whole_star_rating != current_whole_star_rating:
            persistence_service = services.get_persistence_service()
            with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_CHANGE_UNIT_RATING_SCORE) as hook:
                if persistence_service is not None:
                    zone_data = services.get_persistence_service().get_zone_proto_buff(self._zone_id)
                    lot_description_id = zone_data.lot_description_id if zone_data is not None else 0
                    hook.write_guid(TELEMETRY_FIELD_LOT_DESCRIPTION_ID, lot_description_id)
                hook.write_int(TELEMETRY_FIELD_NEW_SCORE_VALUE, current_whole_star_rating)
                hook.write_guid(TELEMETRY_FIELD_UNIT_ID, self._zone_id)

    def on_dynamic_rating_change(self) -> 'None':
        self.dynamic_unit_rating = math.clamp(UnitRatingTuning.MAINTENANCE_RATING_BOUNDS.lower_bound, self.dynamic_unit_rating, UnitRatingTuning.MAINTENANCE_RATING_BOUNDS.upper_bound)

    def set_unit_rating_alert_state(self, alert_state:'UnitRatingAlertState'):
        if self._unit_rating_alert_state == alert_state:
            return
        self._unit_rating_alert_state = alert_state
        self._distribute_business_manager_data_message()

    def set_rent(self, new_rent:'int') -> 'None':
        previous_rent = self._rent
        self._rent = new_rent
        if previous_rent < new_rent:
            resolver = self.get_resolver()
            for loot_action in MultiUnitTuning.ON_RENT_INCREASE_LOOT:
                loot_action.apply_to_resolver(resolver)
        self.send_property_owner_action_telemetry(PropertyOwnerAction.ChangeRent, 'Rent has been modified by Property Owner.')

    def update_overdue_rent_and_notify_client(self, overdue_rent:'int') -> 'None':
        previous_overdue_rent = self.overdue_rent
        self.overdue_rent = overdue_rent
        if overdue_rent != previous_overdue_rent:
            self.update_tenant_alert_visible(overdue_rent != 0)
            self._distribute_business_manager_data_message()
            services.get_event_manager().process_events_for_household(TestEvent.ActiveHouseholdRentBecameOverdue, services.household_manager().get_by_home_zone_id(self._zone_id))

    def handle_repo_event(self, repo_value:'int') -> 'None':
        if self.due_rent != 0:
            if repo_value > self.due_rent:
                repo_value -= self.due_rent
                self.due_rent = 0
            else:
                self.due_rent -= repo_value
                repo_value = 0
        if repo_value != 0 and self.overdue_rent != 0:
            new_overdue_rent = self.overdue_rent - repo_value
            if new_overdue_rent < 0:
                new_overdue_rent = 0
            self.update_overdue_rent_and_notify_client(new_overdue_rent)

    def update_max_rent_and_notify_client(self, max_rent:'int') -> 'None':
        previous_max_rent = self.max_rent
        self.max_rent = max_rent
        if max_rent != previous_max_rent:
            self._distribute_business_manager_data_message()

    def update_tenant_alert_visible(self, should_be_visible:'bool') -> 'bool':
        current_visibility = self.tenant_alert_visible
        all_errors_resolved = len(self.get_rules_by_states(BusinessRuleState.BROKEN)) == 0 and (self.overdue_rent == 0 and not self.is_grace_period)
        if should_be_visible and not current_visibility:
            self.tenant_alert_visible = should_be_visible
            return True
        elif should_be_visible or current_visibility and all_errors_resolved:
            self.tenant_alert_visible = should_be_visible
            return True
        return False

    def set_owner_household_id(self, owner_household_id:'int') -> 'None':
        super().set_owner_household_id(owner_household_id)
        self._grand_opening = False
        self._update_grace_period()

    def modify_funds(self, amount:'int', **kwargs) -> 'None':
        if amount == 0:
            return
        if amount < 0:
            logger.warn('Trying to deduct money from a rental property ownership.')
        if self.is_owner_household_active:
            household = services.household_manager().get(self._owner_household_id)
            household.funds.add(amount, Consts_pb2.FUNDS_RETAIL_PROFITS)

    def is_property_owner_a_tenant_in_plex_group(self) -> 'bool':
        persistence_service = services.get_persistence_service()
        plex_service = services.get_plex_service()

        def exclude_shared_zones(plex_id):
            return not plex_service.is_shared_plex(plex_id)

        group_zone_ids = plex_service.get_plex_zones_in_group(self.business_zone_id, exclude_shared_zones)
        for zone_id in group_zone_ids:
            if persistence_service.get_household_id_from_zone_id(zone_id) == self.owner_household_id:
                return True
        return False

    def add_unowned_business_on_sell(self) -> 'BusinessType':
        return BusinessType.RENTAL_UNIT

    def sell_business_finalize_funds(self, lot_value:'int'=0, lot_sold:'bool'=True) -> 'None':
        self.modify_funds(lot_value)

    def get_sell_store_dialog(self):
        if not self.is_property_owner_a_tenant_in_plex_group():
            return self.tuning_data.sell_store_dialog(services.get_zone(self.business_zone_id))
        return self.tuning_data.sell_store_dialog_property_owner_tenant(services.get_zone(self.business_zone_id))

    def get_early_move_out_rent(self) -> 'int':
        elapsed_days = self._elapsed_open_days
        if elapsed_days < MAX_BILLED_RENT_DAYS:
            return self._rent*elapsed_days
        return 0

    def handle_rule_state_change(self, rule:'BusinessRule', new_state:'BusinessRuleState') -> 'None':
        super().handle_rule_state_change(rule, new_state)
        if self.update_tenant_alert_visible(new_state == BusinessRuleState.BROKEN):
            self._distribute_business_manager_data_message()
        if new_state == BusinessRuleState.ENABLED:
            self.send_property_owner_action_telemetry(PropertyOwnerAction.ChangeRule, f'Rule {type(rule).__name__} is set to {new_state} by property owner.')

    def pay_rent_as_tenant(self) -> 'None':
        if self.due_rent == 0 and self.overdue_rent == 0:
            return
        self.paid_rent_awaiting_transfer = self.due_rent + self.overdue_rent
        self.due_rent = 0
        if self.overdue_rent != 0:
            self.update_overdue_rent_and_notify_client(0)
        self._has_tenant_ever_paid_rent = True

    def handle_tenant_paid_rent_event(self, should_modify_funds:'bool'=True) -> 'None':
        if self.due_rent is 0 and self.overdue_rent is 0:
            return
        renter_household = services.household_manager().get_by_home_zone_id(self._zone_id)
        renter_sim_info = next(renter_household.can_live_alone_info_gen())
        if renter_sim_info is None:
            return
        if should_modify_funds:
            rent_paid_popup = Bills.PROPERTY_OWNER_RENT_PAID_NOTIFICATION(renter_sim_info)
            rent_paid_popup.show_dialog(additional_tokens=(renter_sim_info.full_name, self.due_rent + self.overdue_rent))
            self.modify_funds(self.due_rent + self.overdue_rent)
        if self.overdue_rent is not 0:
            self.update_overdue_rent_and_notify_client(0)
        self.due_rent = 0
        self._has_tenant_ever_paid_rent = True

    def make_rent_due(self) -> 'None':
        if self._has_tenant_ever_received_rent_bill:
            self.due_rent = self.rent*MAX_BILLED_RENT_DAYS
        else:
            self._has_tenant_ever_received_rent_bill = True
            self.due_rent = self.rent*self._elapsed_open_days

    def make_rent_overdue(self) -> 'None':
        if self.due_rent != 0:
            self.update_overdue_rent_and_notify_client(self.overdue_rent + self.due_rent)
            active_household_id = services.active_household_id()
            tenant_household = services.household_manager().get_by_home_zone_id(self._zone_id)
            if active_household_id == tenant_household.id:
                with telemetry_helper.begin_hook(sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_RENT), TELEMETRY_HOOK_LATE, household=tenant_household):
                    pass
        self.due_rent = 0

    def clear_all_rent(self) -> 'None':
        self.due_rent = 0
        self.paid_rent_awaiting_transfer = 0
        self.update_overdue_rent_and_notify_client(0)

    def set_initial_rent(self) -> 'None':
        self.calculate_max_rent()
        self._rent = math.floor(self.max_rent*MultiUnitTuning.MAX_RENT.initial_rent_percentage)

    def get_resolver(self, actor:'Optional[SimInfo]'=DEFAULT) -> 'Resolver':
        if actor is DEFAULT:
            actor = services.active_sim_info()
        target_household = services.household_manager().get_by_home_zone_id(self._zone_id)
        actor_household = services.household_manager().get(self._owner_household_id)
        additional_participants = {ParticipantType.ActorZoneId: (self._zone_id,), ParticipantType.SavedActor1: (None,), ParticipantType.TargetSim: (None,), ParticipantType.PickedZoneId: (self._zone_id,), ParticipantType.ActorHousehold: (actor_household,)}
        if target_household is not None:
            for sim_info in target_household.get_humans_gen():
                if not sim_info.is_infant_or_younger:
                    additional_participants[ParticipantType.TargetSim] = (sim_info,)
                    break
        if actor_household is not None:
            for sim_info in actor_household.get_humans_gen():
                if not sim_info.is_infant_or_younger:
                    additional_participants[ParticipantType.SavedActor1] = (sim_info,)
                    break
        resolver = SingleSimAndHouseholdResolver(actor, target_household, additional_participants=additional_participants)
        return resolver

    def build_rental_unit_data_message(self) -> 'RentalUnitBusinessDataUpdate':
        msg = Business_pb2.RentalUnitBusinessDataUpdate()
        msg.zone_id = self.business_zone_id
        msg.max_rent = self.max_rent
        msg.overdue_rent = self.overdue_rent
        msg.tenant_alert_visible = self.tenant_alert_visible
        msg.unit_rating_alert_state = self._unit_rating_alert_state
        msg.is_grace_period = bool(self._is_grace_period)
        return msg

    def set_latest_tile_count(self) -> 'None':
        if self.business_zone_id is None or self.house_description_id is None:
            self.lot_tile_count = MultiUnitTuning.MAX_RENT.min_tile_count
            return
        tile_count = 0
        plex_id = services.get_plex_service().get_plex_id(self.business_zone_id)
        zone_id = self.business_zone_id
        business_zone_data = services.get_persistence_service().get_zone_proto_buff(self.business_zone_id)
        business_lot_id = business_zone_data.lot_id if business_zone_data is not None else 0
        active_lot_id = services.active_lot_id()
        if active_lot_id == business_lot_id:
            zone_id = services.current_zone_id()
        if active_lot_id is not None and plex_id is not None:
            tile_count = build_buy.get_plex_tile_count(zone_id, plex_id, self.house_description_id)
        self.lot_tile_count = max(tile_count, MultiUnitTuning.MAX_RENT.min_tile_count)

    def calculate_max_rent(self) -> 'None':
        if self.lot_tile_count == 0:
            self.set_latest_tile_count()
        temp_max_rent = self.lot_tile_count*MultiUnitTuning.MAX_RENT.simolean_cost_per_tile
        if self.business_zone_id is not None:
            resolver = ZoneResolver(self.business_zone_id)
            temp_max_rent *= MultiUnitTuning.MAX_RENT.cost_modifiers.get_multiplier(resolver)
            self.update_max_rent_and_notify_client(int(temp_max_rent))

    def get_remaining_lease_length(self) -> 'int':
        if self._is_open and self._signed_lease_length == 0:
            return self._signed_lease_length
        elapsed_open_days = int(services.time_service().sim_now.absolute_days()) - int(self._open_time.absolute_days())
        elapsed_lease_days = elapsed_open_days % self._signed_lease_length
        return self._signed_lease_length - elapsed_lease_days

    def get_currently_owed_rent(self) -> 'int':
        return self.due_rent + self.overdue_rent

    def get_rent_to_cache_for_payment(self) -> 'int':
        result = 0
        if self.due_rent != 0:
            result = self.due_rent + self.overdue_rent
            self.due_rent = 0
            self.update_overdue_rent_and_notify_client(0)
        if self.paid_rent_awaiting_transfer != 0:
            result += self.paid_rent_awaiting_transfer
            self.paid_rent_awaiting_transfer = 0
        self._has_tenant_ever_paid_rent = True
        return result

    def get_estimate_for_next_rent_due(self) -> 'int':
        if self._has_tenant_ever_received_rent_bill:
            return self.rent*MAX_BILLED_RENT_DAYS
        else:
            time = Bills.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY()
            time_until_bill_delivery = self._open_time.time_to_week_time(time)
            bill_delivery_time = self._open_time + time_until_bill_delivery
            end_of_first_week = date_and_time.DateAndTime(0) + interval_in_sim_weeks(1)
            if bill_delivery_time < end_of_first_week:
                time_until_bill_delivery += interval_in_sim_weeks(1)
            days_to_bill = math.ceil(time_until_bill_delivery.in_days())
            return self.rent*math.ceil(days_to_bill)

    def meets_tenant_requirement(self) -> 'bool':
        return services.get_persistence_service().get_household_id_from_zone_id(self._zone_id) != 0

    def meets_requirements_to_be_open(self) -> 'bool':
        return self.meets_zone_requirement() and self.meets_tenant_requirement()

    def is_unit_occupied(self, include_property_owner:'bool'=False) -> 'bool':
        if not self._is_open:
            return False
        if include_property_owner:
            return True
        else:
            property_owner_hh = None
            if self.is_owned_by_npc:
                multi_unit_ownership_service = services.get_multi_unit_ownership_service()
                npc_property_owner_info = multi_unit_ownership_service._get_npc_property_owner()
                if npc_property_owner_info is not None:
                    property_owner_hh = npc_property_owner_info.household
            else:
                property_owner_hh = services.household_manager().get(self._owner_household_id)
            if property_owner_hh is not None and property_owner_hh.home_zone_id == self._zone_id:
                return False
        return True

    def _open_business(self, is_npc_business=False) -> 'None':
        self._clear_state()
        self._is_open = True
        self._open_time = services.time_service().sim_now
        self._update_grace_period()
        self._distribute_business_open_status(is_open=True, open_time=self._open_time.absolute_ticks())
        owner_household = services.active_household()
        if owner_household is not None:
            services.get_event_manager().process_event(TestEvent.BusinessOpened, sim_info=owner_household.sim_infos[0])
        if self.house_description_id is not None:
            self._signed_lease_length = services.get_signed_lease_length(self.house_description_id)

    def _close_business(self, **kwargs) -> 'None':
        if not self._is_open:
            return
        self._send_business_closed_telemetry()
        if self._grace_period_alarm_handle:
            alarms.cancel_alarm(self._grace_period_alarm_handle)
            self._grace_period_alarm_handle = None
        self._has_tenant_ever_paid_rent = False
        self._has_tenant_ever_received_rent_bill = False
        self.on_store_closed()
        services.get_event_manager().process_event(TestEvent.BusinessClosed)
        self._distribute_business_open_status(False)
        self.calculate_max_rent()
        self._is_open = False
        self._open_time = None
        self.reset_rules()
        if self.overdue_rent is not 0 or self.tenant_alert_visible or self._is_grace_period:
            self.update_overdue_rent_and_notify_client(0)
            self.tenant_alert_visible = False
            self._is_grace_period = None
            self._distribute_business_manager_data_message()

    def _handle_grace_period_alarm(self) -> 'None':
        self._update_grace_period()

    def _set_grace_period(self, value:'bool', alarm_delay:'Optional[TimeSpan]'=None, from_load:'bool'=False) -> 'None':
        self._is_grace_period = value
        if not from_load:
            self.update_tenant_alert_visible(value)
            self._distribute_business_manager_data_message()
        if alarm_delay is not None:
            self._grace_period_alarm_handle = alarms.add_alarm(self, alarm_delay, lambda _: self._handle_grace_period_alarm())
        if not value:
            return
        additional_tokens = ()
        if alarm_delay is not None:
            additional_tokens = (services.time_service().sim_now + alarm_delay,)
        else:
            sim_now = services.time_service().sim_now
            additional_tokens = (sim_now + sim_now.time_till_next_day_time(MultiUnitTuning.GRACE_PERIOD.starting_time, True),)
        active_household_id = services.active_household_id()
        tenant_household = services.household_manager().get_by_home_zone_id(self._zone_id)
        if self._owner_household_id == active_household_id:
            services.business_service().show_first_time_dialog(self, FirstTimeMessageType.GRACE_PERIOD_OWNER, additional_tokens=additional_tokens)
        if tenant_household is not None and tenant_household.id == active_household_id:
            services.business_service().show_first_time_dialog(self, FirstTimeMessageType.GRACE_PERIOD_TENANT, additional_tokens=additional_tokens)

    def _update_one_day_lease_grace_period(self, is_pc:'bool', from_load:'bool'=False) -> 'bool':
        elapsed_open_days = self._elapsed_open_days
        sim_now = services.time_service().sim_now
        sim_now_time_of_day = sim_now.time_of_day()
        if elapsed_open_days == 0 or elapsed_open_days == 1 and sim_now_time_of_day < MultiUnitTuning.GRACE_PERIOD.starting_time:
            if is_pc:
                alarm_span = sim_now.time_till_next_day_time(MultiUnitTuning.GRACE_PERIOD.starting_time)
                if sim_now_time_of_day <= MultiUnitTuning.GRACE_PERIOD.starting_time:
                    alarm_span += date_and_time.create_time_span(days=1)
                self._set_grace_period(False, alarm_span, from_load=from_load)
            return False
        duration_span = MultiUnitTuning.GRACE_PERIOD.duration()
        if duration_span.in_days() >= 1:
            if is_pc:
                self._set_grace_period(True, from_load=from_load)
            return True
        end_time_of_day = (MultiUnitTuning.GRACE_PERIOD.starting_time + duration_span).time_of_day()
        if end_time_of_day < MultiUnitTuning.GRACE_PERIOD.starting_time:
            if end_time_of_day < sim_now_time_of_day and sim_now_time_of_day < MultiUnitTuning.GRACE_PERIOD.starting_time:
                if is_pc:
                    self._set_grace_period(False, sim_now.time_till_next_day_time(MultiUnitTuning.GRACE_PERIOD.starting_time, from_load=from_load))
                return False
            if is_pc:
                self._set_grace_period(True, sim_now.time_till_next_day_time(end_time_of_day), from_load=from_load)
            return True
        if MultiUnitTuning.GRACE_PERIOD.starting_time < sim_now_time_of_day and sim_now_time_of_day < end_time_of_day:
            if is_pc:
                self._set_grace_period(True, sim_now.time_till_next_day_time(end_time_of_day), from_load=from_load)
            return True
        if is_pc:
            self._set_grace_period(False, sim_now.time_till_next_day_time(MultiUnitTuning.GRACE_PERIOD.starting_time), from_load=from_load)
        return False

    def _update_grace_period(self, needs_return:'bool'=False, from_load:'bool'=False) -> 'bool':
        self._is_grace_period = None
        if self._grace_period_alarm_handle:
            alarms.cancel_alarm(self._grace_period_alarm_handle)
            self._grace_period_alarm_handle = None
        if self._is_open and self._signed_lease_length == 0:
            return False
        household_manager = services.household_manager()
        tenant_household = household_manager.get_by_home_zone_id(self._zone_id)
        owner_household = household_manager.get(self._owner_household_id)
        if tenant_household is owner_household:
            return False
        active_household = services.active_household()
        is_pc = tenant_household is active_household or owner_household is active_household
        if is_pc or not needs_return:
            return False
        if self._signed_lease_length == 1:
            return self._update_one_day_lease_grace_period(is_pc, from_load=from_load)
        elapsed_open_days = self._elapsed_open_days
        sim_now = services.time_service().sim_now
        (grace_start_time, grace_end_time) = self._grace_period_times
        end_grace_day = int(grace_end_time.absolute_days())
        if MultiUnitTuning.GRACE_PERIOD.starting_time == date_and_time.DATE_AND_TIME_ZERO:
            end_grace_day -= 1
        if end_grace_day > self._signed_lease_length:
            grace_end_time += -date_and_time.create_time_span(days=end_grace_day - self._signed_lease_length)
        if elapsed_open_days < self._signed_lease_length:
            grace_start_time += date_and_time.create_time_span(days=self._signed_lease_length)
        elapsed_lease_days = elapsed_open_days % self._signed_lease_length
        sim_now_time_of_day = sim_now.time_of_day()
        if elapsed_open_days != 0:
            elapsed_lease_days = self._signed_lease_length
        current_lease_relative_time = sim_now_time_of_day + date_and_time.create_time_span(days=elapsed_lease_days)
        if elapsed_lease_days == 0 and sim_now_time_of_day < MultiUnitTuning.GRACE_PERIOD.starting_time and current_lease_relative_time < grace_start_time:
            if is_pc:
                self._set_grace_period(False, grace_start_time - current_lease_relative_time, from_load=from_load)
            return False
        if current_lease_relative_time < grace_end_time:
            if is_pc:
                self._set_grace_period(True, grace_end_time - current_lease_relative_time, from_load=from_load)
            return True
        if is_pc:
            grace_start_time = grace_start_time + date_and_time.create_time_span(days=self._signed_lease_length)
            self._set_grace_period(False, grace_start_time - current_lease_relative_time, from_load=from_load)
        return False

    def _distribute_business_manager_data_message(self) -> 'None':
        msg = self.build_rental_unit_data_message()
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.RENTAL_UNIT_DATA_UPDATE, msg)
        Distributor.instance().add_op_with_no_owner(op)

    def save_data(self, business_save_data:'BusinessSaveData') -> 'None':
        super().save_data(business_save_data)
        rental_unit_save_data = Business_pb2.RentalUnitSaveData()
        rental_unit_save_data.max_rent = self.max_rent
        if self._is_open:
            rental_unit_save_data.tenant_alert_visible = self.tenant_alert_visible
            rental_unit_save_data.has_tenant_ever_paid_rent = self._has_tenant_ever_paid_rent
            rental_unit_save_data.has_tenant_ever_received_rent_bill = self._has_tenant_ever_received_rent_bill
            if self.overdue_rent is not 0:
                rental_unit_save_data.overdue_rent = self.overdue_rent
            if self.due_rent is not 0:
                rental_unit_save_data.due_rent = self.due_rent
            if self.paid_rent_awaiting_transfer != 0:
                rental_unit_save_data.paid_rent_awaiting_transfer = self.paid_rent_awaiting_transfer
        business_save_data.rental_unit_save_data = rental_unit_save_data

    def load_data(self, business_save_data:'BusinessSaveData', is_legacy:'bool'=False) -> 'None':
        super().load_data(business_save_data, is_legacy)
        rental_unit_save_data = business_save_data.rental_unit_save_data
        self.max_rent = rental_unit_save_data.max_rent
        if rental_unit_save_data.HasField('has_tenant_ever_paid_rent'):
            self._has_tenant_ever_paid_rent = rental_unit_save_data.has_tenant_ever_paid_rent
        if rental_unit_save_data.HasField('has_tenant_ever_received_rent_bill'):
            self._has_tenant_ever_received_rent_bill = rental_unit_save_data.has_tenant_ever_received_rent_bill
        if rental_unit_save_data.HasField('tenant_alert_visible'):
            self.tenant_alert_visible = rental_unit_save_data.tenant_alert_visible
        if rental_unit_save_data.HasField('overdue_rent'):
            self.overdue_rent = rental_unit_save_data.overdue_rent
        if rental_unit_save_data.HasField('due_rent'):
            self.due_rent = rental_unit_save_data.due_rent
        if rental_unit_save_data.HasField('paid_rent_awaiting_transfer'):
            self.paid_rent_awaiting_transfer = rental_unit_save_data.paid_rent_awaiting_transfer

    def construct_business_message(self, msg:'SetBusinessData') -> 'None':
        super().construct_business_message(msg)
        msg.rental_unit_data = self.build_rental_unit_data_message()

    def create_venue_business_data_proto(self) -> 'GameplaySaveData_pb2.VenueBusinessData':
        venue_business_data_proto = super().create_venue_business_data_proto()
        if venue_business_data_proto is None:
            venue_business_data_proto = GameplaySaveData_pb2.VenueBusinessData()
        venue_business_data_proto.plex_rating_offset = self.dynamic_unit_rating
        return venue_business_data_proto

    def load_venue_business_data_proto(self, venue_business_data_proto:'GameplaySaveData_pb2.VenueBusinessData') -> 'None':
        super().load_venue_business_data_proto(venue_business_data_proto)
        self.dynamic_unit_rating = venue_business_data_proto.plex_rating_offset

    def send_property_owner_action_telemetry(self, action_type:'PropertyOwnerAction', action_description:'str') -> 'None':
        household = services.household_manager().get(self._owner_household_id)
        if household is not None:
            sim_info = household.sim_infos[0]
            with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_RENTAL_UNIT_ACTION, sim_info=sim_info, valid_for_npc=True) as hook:
                hook.write_enum(TELEMETRY_FIELD_PROPERTY_OWNER_ACTION_TYPE, action_type)
                hook.write_string(TELEMETRY_FIELD_PROPERTY_OWNER_ACTION_DESCRIPTION, action_description)
                hook.write_bool(TELEMETRY_FIELD_IS_GRACE_PERIOD, self.is_grace_period)
