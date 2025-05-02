from __future__ import annotationsfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom sims.sim_info import SimInfofrom small_business.small_business_tuning import SmallBusinessTunablesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from Business_pb2 import BusinessTrackerData, BusinessManagerData, RetailBusinessDataUpdate
    from typing import *from _collections import defaultdictfrom protocolbuffers import Consts_pb2from business.business_enums import BusinessType, BusinessOriginTelemetryContextfrom business.business_manager import BusinessManagerfrom business.business_tuning import BusinessTuningfrom business.unit_rating.unit_rating_enums import UnitRatingAlertStatefrom business.unit_rating.unit_rating_tuning import DynamicUnitRatingTuningfrom collections import Counterfrom distributor.rollback import ProtocolBufferRollbackfrom protocolbuffers import Business_pb2from zone_types import ZoneStateimport alarmsimport date_and_timeimport game_servicesimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessTracker:

    def __init__(self, owner_household_id, business_type):
        self._owner_household_id = owner_household_id
        self._business_type = business_type
        self._business_managers = defaultdict(lambda : BusinessManager(business_type))
        self._zoneless_business_managers = defaultdict(lambda : BusinessManager(business_type))
        self._additional_employee_slots = Counter()
        self._business_type_tuning_data = services.business_service().get_business_tuning_data_for_business_type(business_type)
        current_zone = services.current_zone()
        if current_zone is not None:
            if current_zone.is_zone_running:
                self._register_perk_callbacks()
            else:
                current_zone.register_callback(ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, self._register_perk_callbacks)
        self._additional_markup_multiplier = 0
        self._additional_customer_count = 0
        self._rental_unit_clear_rating_alert_handler = None
        self._rental_unit_payout_cache = 0
        self._sim_id_open_business_on_load = 0

    @property
    def business_type(self):
        return self._business_type

    @property
    def business_managers(self):
        return self._business_managers

    @property
    def zoneless_business_managers(self):
        return self._zoneless_business_managers

    @property
    def is_on_lot_with_open_business(self):
        business_manager = self.get_business_manager_for_zone()
        return business_manager is not None and business_manager.is_open

    @property
    def business_type_tuning_data(self):
        return self._business_type_tuning_data

    @property
    def additional_markup_multiplier(self):
        return self._additional_markup_multiplier

    @property
    def addtitional_customer_count(self):
        return self._additional_customer_count

    @property
    def owner_household_id(self):
        return self._owner_household_id

    @property
    def sim_id_open_business_on_load(self) -> 'int':
        return self._sim_id_open_business_on_load

    def set_sim_id_open_business_on_load(self, owner_id:'int') -> 'None':
        self._sim_id_open_business_on_load = owner_id

    def _get_owner_household(self):
        return services.household_manager().get(self._owner_household_id)

    def save_data(self, business_tracker_msg):
        business_tracker_msg.additional_markup_multiplier = self._additional_markup_multiplier
        business_tracker_msg.additional_customer_count = self._additional_customer_count
        business_tracker_msg.rental_unit_payout_cache = self._rental_unit_payout_cache
        for (employee_type, additional_slot_count) in self._additional_employee_slots.items():
            with ProtocolBufferRollback(business_tracker_msg.additional_employee_slot_data) as additional_slot_data:
                additional_slot_data.employee_type = employee_type
                additional_slot_data.additional_slot_count = additional_slot_count
        for (zone_id, manager) in self._business_managers.items():
            with ProtocolBufferRollback(business_tracker_msg.business_manager_data) as business_manager_data:
                business_manager_data.zone_id = zone_id
                business_manager_data.make_unowned_on_load = manager.make_unowned_on_load
                manager.save_data(business_manager_data.business_data)
                if manager.owner_sim_id is not None:
                    business_manager_data.sim_id = manager.owner_sim_id
        for (sim_id, manager) in self._zoneless_business_managers.items():
            with ProtocolBufferRollback(business_tracker_msg.zoneless_business_manager_data) as zoneless_business_manager_data:
                zoneless_business_manager_data.sim_id = sim_id
                zoneless_business_manager_data.make_unowned_on_load = manager.make_unowned_on_load
                manager.save_data(zoneless_business_manager_data.business_data)
        if sims4.protocol_buffer_utils.has_field(business_tracker_msg, 'sim_id_open_business_on_load'):
            business_tracker_msg.sim_id_open_business_on_load = self._sim_id_open_business_on_load

    def load_data(self, business_tracker_msg:'BusinessTrackerData') -> 'None':
        self._additional_markup_multiplier = business_tracker_msg.additional_markup_multiplier
        self._additional_customer_count = business_tracker_msg.additional_customer_count
        self._rental_unit_payout_cache = business_tracker_msg.rental_unit_payout_cache
        self._additional_employee_slots.clear()
        for additional_slot_data in business_tracker_msg.additional_employee_slot_data:
            self._additional_employee_slots[additional_slot_data.employee_type] = additional_slot_data.additional_slot_count
        business_data = Business_pb2.SetBusinessData()
        for manager_save_data in business_tracker_msg.business_manager_data:
            if manager_save_data.HasField('make_unowned_on_load') and manager_save_data.make_unowned_on_load and self.business_type != BusinessType.SMALL_BUSINESS:
                self._create_unowned_manager(manager_save_data)
            else:
                business_data.sim_id = manager_save_data.sim_id
                loaded_manager = self.make_owner(self._owner_household_id, manager_save_data.zone_id, business_data=business_data, from_load=True)
                loaded_manager.load_data(manager_save_data.business_data)
        for zoneless_manager_save_data in business_tracker_msg.zoneless_business_manager_data:
            if zoneless_manager_save_data.HasField('make_unowned_on_load') and zoneless_manager_save_data.make_unowned_on_load:
                self._create_unowned_manager(manager_save_data)
            else:
                business_data.sim_id = zoneless_manager_save_data.sim_id
                loaded_manager = self.make_owner(self._owner_household_id, None, business_data=business_data, from_load=True)
                loaded_manager.load_data(zoneless_manager_save_data.business_data)
        if sims4.protocol_buffer_utils.has_field(business_tracker_msg, 'sim_id_open_business_on_load'):
            self._sim_id_open_business_on_load = business_tracker_msg.sim_id_open_business_on_load

    def _create_unowned_manager(self, manager_save_data:'BusinessManagerData') -> 'None':
        business_service = services.business_service()
        business_manager = business_service.add_unowned_business(self.business_type, manager_save_data.zone_id)
        business_manager.load_data(manager_save_data.business_data)

    def load_legacy_data(self, retail_store_data:'RetailBusinessDataUpdate') -> 'None':
        loaded_manager = self.make_owner(self._owner_household_id, retail_store_data.retail_zone_id, from_load=True)
        loaded_manager.load_data(retail_store_data, is_legacy=True)

    def set_legacy_additional_employee_slot(self, additional_slots):
        self._additional_employee_slots[BusinessTuning.LEGACY_RETAIL_ADDITIONAL_SLOT_EMPLOYEE_TYPE] = additional_slots

    def on_protocols_loaded(self):
        current_zone = services.current_zone()
        if current_zone is not None:
            business_manager = self.get_business_manager_for_zone(current_zone.id)
            if business_manager is not None:
                business_manager.on_protocols_loaded()
            current_zone.register_callback(ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, self._register_perk_callbacks)

    def on_zone_load(self):
        zoneless_business_managers_values = [business_manager for business_manager in self._zoneless_business_managers.values()]
        for zoneless_business_manager in zoneless_business_managers_values:
            zoneless_business_manager.on_zone_load()
        business_managers_values = [business_manager for business_manager in self._business_managers.values()]
        for business_manager in business_managers_values:
            business_manager.on_zone_load()
        if not self.is_on_lot_with_open_business:
            owner_household = self._get_owner_household()
            if owner_household is None:
                return
            owner_household.bucks_tracker.deactivate_all_temporary_perk_timers_of_type(self.business_type_tuning_data.bucks)
        if self.business_type == BusinessType.RENTAL_UNIT:
            timespan = date_and_time.create_time_span(hours=DynamicUnitRatingTuning.RATING_CHANGE_CLEAR_ALERT_TIME.hour(), minutes=DynamicUnitRatingTuning.RATING_CHANGE_CLEAR_ALERT_TIME.minute())
            self._rental_unit_clear_rating_alert_handler = alarms.add_alarm(self, timespan, lambda _: self._handle_rating_change_clear_alert_alarm(), repeating=True, use_sleep_time=False, cross_zone=True)
        if services.active_household() == self._get_owner_household() and self._rental_unit_payout_cache != 0:
            self._payout_rent_cache(True)

    def on_all_households_and_sim_infos_loaded(self) -> 'None':
        business_managers_to_close = []
        for business_manager in self._business_managers.values():
            if services.household_manager().get_by_sim_id(business_manager.owner_sim_id) is None:
                business_managers_to_close.append(business_manager)
            else:
                business_manager.on_all_households_and_sim_infos_loaded()
        for business_manager in business_managers_to_close:
            business_manager.close_business(play_sound=False, show_summary_dialog=False)
        business_managers_with_invalid_sim_owner = [business_manager for business_manager in self._zoneless_business_managers.values() if services.household_manager().get_by_sim_id(business_manager.owner_sim_id) is None]
        for zoneless_business_manager in business_managers_with_invalid_sim_owner:
            self.remove_owner_zoneless_business(zoneless_business_manager.owner_sim_id, sell=True)
        business_managers_with_changed_household = [business_manager for business_manager in self._zoneless_business_managers.values() if services.household_manager().get_by_sim_id(business_manager.owner_sim_id).id != business_manager.owner_household_id]
        for zoneless_business_manager in business_managers_with_changed_household:
            services.business_service().on_zoneless_owner_sim_changed_household(zoneless_business_manager, self)
        for zoneless_business_manager in self._zoneless_business_managers.values():
            zoneless_business_manager.on_all_households_and_sim_infos_loaded()

    def on_client_disconnect(self):
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_client_disconnect()
        owner_household = self._get_owner_household()
        if owner_household is None:
            return
        owner_household.bucks_tracker.remove_perk_unlocked_callback(self.business_type_tuning_data.bucks, self._business_perk_unlocked_callback)
        owner_household.bucks_tracker.deactivate_all_temporary_perk_timers_of_type(self.business_type_tuning_data.bucks)

    def _register_perk_callbacks(self):

        def add_perk_unlocked_callback_helper(businessManager) -> 'None':
            bucks_tracker = businessManager.get_bucks_tracker()
            if bucks_tracker is not None and not game_services.service_manager.is_traveling:
                bucks_tracker.add_perk_unlocked_callback(self._business_type_tuning_data.bucks, self._business_perk_unlocked_callback)

        if not game_services.service_manager.is_traveling:
            owner_household = self._get_owner_household()
            if owner_household is not None:
                owner_household.bucks_tracker.add_perk_unlocked_callback(self._business_type_tuning_data.bucks, self._business_perk_unlocked_callback)
        zone_business_manager = self.get_business_manager_for_zone()
        if zone_business_manager is not None:
            add_perk_unlocked_callback_helper(zone_business_manager)
            zone_business_manager.on_registered_perk_callback()
        household = services.active_household()
        if household is not None:
            for sim in household:
                small_business_manager = self.get_business_manager_for_sim(sim.id)
                if not small_business_manager is None:
                    if small_business_manager is zone_business_manager:
                        pass
                    else:
                        add_perk_unlocked_callback_helper(small_business_manager)
                        small_business_manager.on_registered_perk_callback()

    def run_off_lot_simulation(self):
        current_zone_id = services.current_zone_id()
        for business_manager in self._business_managers.values():
            if business_manager.business_zone_id != current_zone_id and business_manager.is_open:
                business_manager.run_off_lot_simulation()

    def get_business_manager_for_zone(self, zone_id=None):
        if zone_id is None:
            zone_id = services.current_zone_id()
        return self._business_managers.get(zone_id, None)

    def get_business_zones_in_tracker(self) -> 'Set[int]':
        return self._business_managers.keys()

    def get_business_manager_for_sim(self, sim_id:'int') -> 'Optional[BusinessManager]':
        if sim_id in self._zoneless_business_managers:
            return self._zoneless_business_managers[sim_id]
        for business_manager in self._business_managers.values():
            if business_manager.owner_sim_id == sim_id:
                return business_manager

    def _start_multi_unit_events(self):
        event_service = services.multi_unit_event_service()
        if event_service:
            if not event_service.is_property_owner_service_active():
                event_service.start_events_service()
            event_service.start_tenant_events()

    def _handle_rating_change_clear_alert_alarm(self) -> 'None':
        if self._rental_unit_clear_rating_alert_handler:
            for business_manager in self._business_managers.values():
                business_manager.set_unit_rating_alert_state(UnitRatingAlertState.CLEAR)

    def make_owner(self, owner_household_id:'int', business_zone_id:'int', telemetry_context:'BusinessOriginTelemetryContext'=BusinessOriginTelemetryContext.NONE, from_load:'bool'=False, business_data:'Business_pb2.SetBusinessData'=None) -> 'Union[BusinessManager, None]':
        sim_id = business_data.sim_id if business_data is not None else None
        if self.business_type == BusinessType.RETAIL:
            from retail.retail_manager import RetailManager
            business_manager = RetailManager()
            self._business_managers[business_zone_id] = business_manager
        elif self.business_type == BusinessType.RESTAURANT:
            from restaurants.restaurant_manager import RestaurantManager
            business_manager = RestaurantManager()
            self._business_managers[business_zone_id] = business_manager
        elif self.business_type == BusinessType.VET:
            from vet.vet_clinic_manager import VetClinicManager
            business_manager = VetClinicManager()
            self._business_managers[business_zone_id] = business_manager
        elif self.business_type == BusinessType.RENTAL_UNIT:
            from multi_unit.rental_unit_manager import RentalUnitManager
            business_manager = RentalUnitManager()
            self._business_managers[business_zone_id] = business_manager
            self._start_multi_unit_events()
        elif self.business_type == BusinessType.SMALL_BUSINESS:
            if not from_load:
                business_manager = self.get_business_manager_for_sim(sim_id=sim_id)
                if business_manager is not None:
                    return
                sim_info = services.sim_info_manager().get(sim_id)
                business_tuning_data = services.business_service().get_business_tuning_data_for_business_type(BusinessType.SMALL_BUSINESS)
                if sim_info is None:
                    return
                registration_fee_deducted = sim_info.household.funds.try_remove_amount(business_tuning_data.registration_fee, Consts_pb2.TELEMETRY_MONEY_CAREER, sim_info)
                if registration_fee_deducted is None:
                    return
            from small_business.small_business_manager import SmallBusinessManager
            business_manager = SmallBusinessManager(business_data, from_load)
            if business_zone_id is not None:
                self._business_managers[business_zone_id] = business_manager
            elif sim_id is not None:
                self._zoneless_business_managers[sim_id] = business_manager
            if not from_load:
                business_manager.send_data_to_client()
                if business_manager.is_zone_assigned_allowed(services.current_zone_id()):
                    business_manager.display_notification(SmallBusinessTunables.REGISTER_BUSINESS_NOTIFICATION_TNS)
                elif business_manager.has_allowed_zone():
                    business_manager.display_notification(SmallBusinessTunables.REGISTER_BUSINESS_NOTIFICATION_TNS_ON_INVALID_LOT)
                else:
                    business_manager.display_notification(SmallBusinessTunables.NO_VALID_LOT_TNS)
                sim_info = services.sim_info_manager().get(sim_id)
                business_manager.setup_business_for_sim_info(sim_info)
                bucks_tracker = business_manager.get_bucks_tracker()
                if bucks_tracker is not None:
                    bucks_tracker.reset_bucks(SmallBusinessTunables.SMALL_BUSINESS_PERKS_BUCKS_TYPE)
            connection = services.client_manager().get_first_client_id()
            if connection is not None:
                sims4.commands.automation_output('SmallBusinessRegisterResponse; Status:{0}'.format('Failed' if business_manager is None else 'Success'), connection)
        business_manager.set_owner_household_id(owner_household_id)
        business_manager.add_owner_career()
        if not from_load:
            business_manager.send_telemetry_origin_message(telemetry_context=telemetry_context)
            if business_manager.business_type == BusinessType.SMALL_BUSINESS:
                sim_info = services.sim_info_manager().get(sim_id)
                services.get_event_manager().process_event(TestEvent.BusinessRegistered, sim_info=sim_info, event_business_type=business_manager.business_type)
            else:
                household = services.household_manager().get(owner_household_id)
                services.get_event_manager().process_events_for_household(TestEvent.BusinessRegistered, household=household, event_business_type=business_manager.business_type)
        if business_zone_id is not None:
            business_manager.set_zone_id(business_zone_id)
            return self._business_managers[business_zone_id]
        elif sim_id is not None:
            return self._zoneless_business_managers[sim_id]

    def transfer_business_to_sim(self, owner_sim_info:'SimInfo', new_owner_sim_info:'SimInfo') -> 'BusinessManager':
        if self.business_type != BusinessType.SMALL_BUSINESS:
            return
        owner_sim_id = owner_sim_info.id
        new_owner_sim_id = new_owner_sim_info.id
        business_manager = self.get_business_manager_for_sim(sim_id=owner_sim_id)
        if owner_sim_info.is_dead or owner_sim_info.household.id != new_owner_sim_info.household.id:
            logger.warn('Trying to transfer business to a sim in different household. Owner sim:{}, target sim:{}', owner_sim_id, new_owner_sim_id)
            return
        second_business_manager = self.get_business_manager_for_sim(sim_id=new_owner_sim_id)
        if second_business_manager is not None:
            logger.error('Trying to transfer business to a sim that already owns a business. Target sim:{}', new_owner_sim_id)
        if business_manager is None or business_manager.is_open:
            return
        self.remove_owner_zoneless_business(owner_sim_id)
        self._zoneless_business_managers[new_owner_sim_id] = business_manager
        business_manager.transfer_business(new_owner_sim_info)
        return business_manager

    def remove_owner(self, business_zone_id):
        del self._business_managers[business_zone_id]

    def remove_owner_zoneless_business(self, sim_id:'int', sell:'bool'=False):
        business_manager = self._zoneless_business_managers[sim_id]
        if sell and business_manager is not None:
            business_manager.sell_business_finalize_funds(lot_sold=False)
            business_manager.display_notification(SmallBusinessTunables.SELL_BUSINESS_NOTIFICATION_TNS)
        del self._zoneless_business_managers[sim_id]
        return business_manager

    def on_zoneless_owner_sim_changed_household(self, owner_sim_id:'int', household_id:'int', business_manager:'BusinessManager'):
        self._zoneless_business_managers[owner_sim_id] = business_manager
        business_manager.set_owner_household_id(household_id)
        business_manager.reset_allowed_zones()
        business_manager.add_owner_career()
        business_manager.send_data_to_client()

    def on_zoneless_business_opened(self, business_manager:'BusinessManager'):
        owner_sim_id = business_manager.owner_sim_id
        if owner_sim_id in self._zoneless_business_managers:
            zone_id = services.current_zone().id
            self._business_managers[zone_id] = self._zoneless_business_managers[owner_sim_id]
            del self._zoneless_business_managers[owner_sim_id]
            business_manager.set_zone_id(zone_id)

    def on_zoneless_business_closed(self, zoneless_business_manager:'BusinessManager'):
        owner_sim_id = zoneless_business_manager.owner_sim_id
        for (zone_id, business_manager) in self._business_managers.items():
            if business_manager.owner_sim_id == owner_sim_id:
                self._zoneless_business_managers[owner_sim_id] = business_manager
                business_manager.set_zone_id(None)
                del self._business_managers[zone_id]
                break

    def increment_additional_employee_slots(self, employee_type):
        employee_type_tuning_data = self.business_type_tuning_data.employee_data_map.get(employee_type, None)
        if employee_type_tuning_data is None:
            logger.error("Trying to increment additional employee slots for business type: {} but employee type: {} doesn't exist.", self.business_type, employee_type)
            return
        if self._additional_employee_slots[employee_type] >= employee_type_tuning_data.employee_count_max - employee_type_tuning_data.employee_count_default:
            logger.error('Attempting to add additional slots beyond the max limit of {}', employee_type_tuning_data.employee_count_max)
            return
        self._additional_employee_slots[employee_type] += 1

    def get_additional_employee_slots(self, employee_type):
        employee_type_tuning_data = self.business_type_tuning_data.employee_data_map.get(employee_type, None)
        additional_slots_max_limit = employee_type_tuning_data.employee_count_max - employee_type_tuning_data.employee_count_default
        if self._additional_employee_slots[employee_type] > additional_slots_max_limit:
            logger.error('Attempting to retrieve additional slots data that is beyond the max limit of {}, resetting to default', additional_slots_max_limit)
            self._additional_employee_slots[employee_type] = additional_slots_max_limit
        return self._additional_employee_slots[employee_type]

    def add_additional_markup_multiplier(self, delta):
        self._additional_markup_multiplier = max(0, self._additional_markup_multiplier + delta)

    def add_additional_customer_count(self, delta):
        self._additional_customer_count = sims4.math.clamp(0, self._additional_customer_count + delta, 13)

    def _business_perk_unlocked_callback(self, perk):
        if perk.temporary_perk_information is None:
            return
        if self.is_on_lot_with_open_business:
            return
        owning_household = self._get_owner_household()
        if owning_household is not None:
            owning_household.bucks_tracker.deactivate_temporary_perk_timer(perk)

    def on_rental_unit_rent_due(self) -> 'None':
        for business_manager in self._business_managers.values():
            if business_manager.is_unit_occupied():
                business_manager.make_rent_due()

    def rental_units_payout_handler(self) -> 'None':
        weekly_cache = 0
        for business_manager in self._business_managers.values():
            weekly_cache += business_manager.get_rent_to_cache_for_payment()
        if self._rental_unit_payout_cache == 0:
            self._rental_unit_payout_cache = weekly_cache
        if self._owner_household_id == services.active_household_id():
            self._payout_rent_cache(False)

    def _payout_rent_cache(self, from_offline:'bool') -> 'None':
        if self._rental_unit_payout_cache == 0:
            return
        services.active_household().funds.add(self._rental_unit_payout_cache, Consts_pb2.FUNDS_RETAIL_PROFITS)
        owner_sim = next(self._get_owner_household().can_live_alone_info_gen())
        if from_offline:
            rent_paid_popup = services.business_service().PROPERTY_OWNER_RECEIVES_OFFLINE_PAYOUTS_NOTIFICATION(owner_sim)
        else:
            rent_paid_popup = services.business_service().PROPERTY_OWNER_RECEIVES_PAYOUTS_NOTIFICATION(owner_sim)
        rent_paid_popup.show_dialog(additional_tokens=(self._rental_unit_payout_cache,))
        self._rental_unit_payout_cache = 0

    def check_and_open_zoneless_npc_business(self) -> 'None':
        owning_household_id = services.owning_household_id_of_active_lot()
        active_household = services.active_household()
        if owning_household_id != active_household.id:
            if self._sim_id_open_business_on_load != 0:
                for (zone_id, business_manager) in self._business_managers.items():
                    if business_manager.owner_sim_id == self._sim_id_open_business_on_load:
                        business_manager.set_open(False)
                        break
                if self._sim_id_open_business_on_load in self._zoneless_business_managers:
                    self._zoneless_business_managers[self._sim_id_open_business_on_load].try_open_npc_store()
            elif len(self._zoneless_business_managers) > 0:
                current_zone_id = services.current_zone_id()
                for business_manager in self._zoneless_business_managers.values():
                    if business_manager.allowed_zone_ids and current_zone_id in business_manager.allowed_zone_ids:
                        business_manager.try_open_npc_store()
                        return
