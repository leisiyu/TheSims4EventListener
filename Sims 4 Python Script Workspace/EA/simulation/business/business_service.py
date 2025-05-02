from __future__ import annotationsfrom build_buy import get_current_venue_owner_idfrom sims.sim_info import SimInfofrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from business.business_manager import BusinessManager
    import protocolbuffers.Clubs_pb2 as Clubs_pb2
    from protocolbuffers.FileSerialization_pb2 import SaveSlotData
    from server.client import Client
    from typing import *from _collections import defaultdictfrom ui.ui_dialog_notification import UiDialogNotificationfrom business.business_enums import BusinessType, BusinessOriginTelemetryContextfrom business.business_tracker import BusinessTrackerfrom business.business_tuning import BusinessTuningfrom distributor.ops import GenericProtocolBufferOp, SendUIMessagefrom date_and_time import create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom protocolbuffers import Business_pb2, DistributorOps_pb2from sims4.math import MAX_UINT32from sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableRangefrom sims4.utils import classpropertyimport alarmsimport clockimport game_servicesimport itertoolsimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessService(Service):
    HOURS_BETWEEN_OFF_LOT_SIMULATIONS = TunableRange(description='\n        The number of hours between off lot simulations for business.\n        ', tunable_type=int, default=4, minimum=4, maximum=24)
    PROPERTY_OWNER_PAYOUT_TIMER = TunableRange(description='\n        The amount of time, in hours, that pass after the delinquency timer (in sims.bills) that payouts for property\n        Owners will be done. If they are the active household they  will get paid at this time for all non arrears \n        properties with renters. If they are not active, we will cache the first week of rent to be paid for their \n        next time active. Additional triggers will not actually add to the payout value, \n        but will clear rent for the tenants. \n        \n        Any change to this should be run by automated property management to ensure rent arrears calculations are \n        handled within the correct time frame.\n        ', tunable_type=int, default=24, minimum=12)
    PROPERTY_OWNER_RECEIVES_PAYOUTS_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A notification that shows up for property owners when they receive payment each week.\n        ')
    PROPERTY_OWNER_RECEIVES_OFFLINE_PAYOUTS_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A notification that shows up for property owners when they receive payment upon signing in \n        after payments processed\n        ')
    EMPLOYEE_ADDITIONAL_IMMUNITY = TunableRange(description="\n        This unit less number will be a boost the employee's importance when\n        the culling system scores this Sim. Higher the number, lower the\n        probability this Sim being culled.\n        \n        Performance WARNING: Remember that employees can be hired by many\n        households via rotational gameplay. This number has to balance the\n        desire to keep this Sim around as well as supporting multiple player\n        families with businesses.\n        ", tunable_type=int, default=10, minimum=0)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_BUSINESS_SERVICE

    def __init__(self) -> 'None':
        self._business_trackers = defaultdict(list)
        self._unowned_business_trackers = defaultdict(BusinessTracker)
        self._off_lot_churn_alarm_handle = None
        self._rental_unit_payout_alarm_handle = None
        self._first_time_messages = {}
        self.rules_presets = defaultdict(list)

    def business_trackers_gen(self) -> 'Iterable[BusinessTracker]':
        yield from itertools.chain(self._business_trackers.values(), self._unowned_business_trackers.values())

    def _stop_off_lot_churn_alarm(self):
        if self._off_lot_churn_alarm_handle is not None:
            alarms.cancel_alarm(self._off_lot_churn_alarm_handle)
            self._off_lot_churn_alarm_handle = None

    def _start_off_lot_churn_alarm(self):
        self._off_lot_churn_alarm_handle = alarms.add_alarm(self, create_time_span(hours=BusinessService.HOURS_BETWEEN_OFF_LOT_SIMULATIONS), self._off_lot_churn_callback, repeating=True, use_sleep_time=False)

    def _off_lot_churn_callback(self, alarm_handle):
        trackers = self.get_business_trackers_for_household(services.active_household_id())
        if not trackers:
            return
        for tracker in trackers:
            tracker.run_off_lot_simulation()

    def start_rental_unit_payout_alarm(self, delinquency_timer:'int') -> 'None':
        if self._rental_unit_payout_alarm_handle is None:
            self._rental_unit_payout_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_hours(delinquency_timer + self.PROPERTY_OWNER_PAYOUT_TIMER), lambda _: self._rental_unit_payout_alarm_callback(), cross_zone=True)

    def _stop_rental_unit_payout_alarm(self) -> 'None':
        if self._rental_unit_payout_alarm_handle is not None:
            alarms.cancel_alarm(self._rental_unit_payout_alarm_handle)
            self._rental_unit_payout_alarm_handle = None

    def _rental_unit_payout_alarm_callback(self) -> 'None':
        rental_unit_trackers = self.get_business_trackers_for_business_type(BusinessType.RENTAL_UNIT)
        if rental_unit_trackers:
            for tracker in rental_unit_trackers:
                tracker.rental_units_payout_handler()
        self._stop_rental_unit_payout_alarm()

    def on_client_disconnect(self, client:'Client') -> 'None':
        self._stop_off_lot_churn_alarm()
        for business_tracker in self.business_trackers_gen():
            business_tracker.on_client_disconnect()

    def on_enter_main_menu(self):
        self._business_trackers.clear()
        self._unowned_business_trackers.clear()

    def _manage_current_lot_on_zone_change(self, added_zones:'Set[int]', deleted_zones:'Set[int]') -> 'Tuple[Set[int], Set[int]]':
        current_zone_id = services.current_zone_id()
        if current_zone_id is None:
            return (added_zones, deleted_zones)

        def _active_venue_is_multi_unit():
            persistence_service = services.get_persistence_service()
            if persistence_service is None:
                return False
            zone_data = persistence_service.get_zone_proto_buff(current_zone_id)
            if zone_data is None:
                return False
            lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
            if lot_data is None:
                return False
            venue_tuning = services.get_instance_manager(sims4.resources.Types.VENUE).get(lot_data.venue_key)
            if venue_tuning is None:
                return False
            return venue_tuning.is_multi_unit

        lot_is_multi_unit_venue = _active_venue_is_multi_unit()
        active_business_manager = self.get_business_manager_for_zone(current_zone_id)
        if lot_is_multi_unit_venue:
            added_zones.add(current_zone_id)
        if lot_is_multi_unit_venue or active_business_manager and active_business_manager.business_type == BusinessType.RENTAL_UNIT:
            deleted_zones.add(current_zone_id)
        return (added_zones, deleted_zones)

    def on_multi_unit_zone_change(self, owning_household_id:'int', added_zones:'Set[int]', deleted_zones:'Set[int]') -> 'None':
        plex_service = services.get_plex_service()
        owning_household_id = owning_household_id if owning_household_id != 0 else None
        added_business_zone_ids = added_zones.copy()
        removed_business_zone_ids = deleted_zones.copy()
        update_units = []
        send_ui_message = False
        active_household_id = services.active_household_id()
        (added_business_zone_ids, removed_business_zone_ids) = self._manage_current_lot_on_zone_change(added_business_zone_ids, removed_business_zone_ids)
        for zone_id in added_business_zone_ids:
            if owning_household_id is not None:
                business_manager = self._make_owner(owning_household_id, BusinessType.RENTAL_UNIT, zone_id, telemetry_context=BusinessOriginTelemetryContext.BB)
            else:
                business_manager = self.add_unowned_business(BusinessType.RENTAL_UNIT, zone_id)
            if plex_service.is_zone_a_plex(zone_id) and business_manager is not None:
                if business_manager.owner_household_id == active_household_id:
                    business_manager.send_data_to_client()
                    send_ui_message = True
                if business_manager.business_zone_id:
                    business_manager.set_initial_rent()
                    update_units.append((zone_id, business_manager.house_description_id, business_manager.rent))
        persistence_service = services.get_persistence_service()
        households = services.household_manager()
        for zone_id in removed_business_zone_ids:
            self.remove_owner(zone_id, owning_household_id)
            tenant_hh_id = persistence_service.get_household_id_from_zone_id(zone_id)
            if tenant_hh_id is not None and tenant_hh_id != 0 and tenant_hh_id != owning_household_id:
                tenant_hh = households.get(tenant_hh_id)
                logger.error('{} currently lives in deleted zone id {}, this will make them homeless now', tenant_hh.name, zone_id)
                multi_unit_ownership_service = services.get_multi_unit_ownership_service()
                if multi_unit_ownership_service is not None:
                    multi_unit_ownership_service.evict_tenant(tenant_hh_id)
        current_zone_id = services.current_zone_id()
        zone_ids_in_group = plex_service.get_plex_zones_in_group(current_zone_id)
        if not zone_ids_in_group:
            zone_data = persistence_service.get_zone_proto_buff(current_zone_id)
            if zone_data is not None:
                zone_ids_in_group = plex_service.get_plex_zones_in_group(zone_data.master_zone_object_data_id)
        for zone_id in zone_ids_in_group:
            if not zone_id in added_business_zone_ids:
                if zone_id in removed_business_zone_ids:
                    pass
                else:
                    business_manager = self.get_business_manager_for_zone(zone_id)
                    if not business_manager is None:
                        if business_manager.business_type != BusinessType.RENTAL_UNIT:
                            pass
                        else:
                            house_description_id = persistence_service.get_house_description_id(zone_id)
                            business_manager.house_description_id = house_description_id
                            if business_manager.house_description_id is None:
                                pass
                            else:
                                client_rent = services.get_rent(business_manager.house_description_id)
                                if client_rent != MAX_UINT32:
                                    pass
                                else:
                                    if business_manager.owner_household_id == active_household_id:
                                        business_manager.send_data_to_client()
                                        send_ui_message = True
                                    business_manager.set_latest_tile_count()
                                    business_manager.set_initial_rent()
                                    update_units.append((zone_id, business_manager.house_description_id, business_manager.rent))
        if send_ui_message or any(removed_business_zone_ids):
            op = SendUIMessage('MultiUnitZoneUpdate')
            Distributor.instance().add_op_with_no_owner(op)
        if update_units:
            services.set_initial_unit_rent_prices(current_zone_id, update_units)

    def add_unowned_business(self, business_type:'BusinessType', business_zone_id:'int') -> 'BusinessManager':
        unowned_business_tracker = self._unowned_business_trackers.get(business_type)
        if unowned_business_tracker is None:
            unowned_business_tracker = BusinessTracker(None, business_type)
            self._unowned_business_trackers[business_type] = unowned_business_tracker
        return unowned_business_tracker.make_owner(None, business_zone_id)

    def make_owner(self, owner_household_id:'int', business_type:'BusinessType', zone_id:'int', telemetry_context:'BusinessOriginTelemetryContext'=BusinessOriginTelemetryContext.NONE, from_load:'bool'=False, business_data:'Business_pb2.SetBusinessData'=None) -> 'Set[int]':
        zone_ids = {zone_id}
        if business_type == BusinessType.RENTAL_UNIT:
            plex_service = services.get_plex_service()

            def _exclude_shared_zones(plex_id):
                return not plex_service.is_shared_plex(plex_id)

            zone_ids.update(plex_service.get_plex_zones_in_group(zone_id, _exclude_shared_zones))
        for business_zone_id in zone_ids:
            self._make_owner(owner_household_id, business_type, business_zone_id, telemetry_context=telemetry_context, from_load=from_load, business_data=business_data)
        return zone_ids

    def _make_owner(self, owner_household_id:'int', business_type:'BusinessType', business_zone_id:'int', telemetry_context:'BusinessOriginTelemetryContext'=BusinessOriginTelemetryContext.NONE, from_load:'bool'=False, business_data:'Business_pb2.SetBusinessData'=None) -> 'BusinessManager':
        unowned_businesses_tracker = self._unowned_business_trackers.get(business_type)
        if unowned_businesses_tracker is not None:
            unowned_business = unowned_businesses_tracker.get_business_manager_for_zone(business_zone_id)
            if unowned_business is not None:
                unowned_businesses_tracker.remove_owner(business_zone_id)
        business_tracker = self._get_or_create_tracker_for_household(owner_household_id, business_type)
        return business_tracker.make_owner(owner_household_id, business_zone_id, telemetry_context=telemetry_context, from_load=from_load, business_data=business_data)

    def remove_owner(self, zone_id, household_id=None, unowned_business_type:'int'=BusinessType.INVALID):
        business_tracker = self._get_tracker_for_business_in_zone(zone_id, household_id=household_id)
        if business_tracker is None:
            return
        business_tracker.remove_owner(zone_id)
        if unowned_business_type != BusinessType.INVALID:
            self.add_unowned_business(unowned_business_type, zone_id)
            services.get_multi_unit_ownership_service().refresh_relationships(zone_id)

    def remove_owner_zoneless_business(self, sim_info:'SimInfo', business_type:'BusinessType', sell:'bool'=False):
        business_tracker = self._get_business_tracker_for_sim(sim_info, business_type)
        if business_tracker is None:
            return
        business_tracker.remove_owner_zoneless_business(sim_info.id, sell)

    def transfer_business_to_sim(self, owner_sim_info:'SimInfo', new_owner_sim_info:'SimInfo', business_type:'BusinessType'):
        owner_sim_business_tracker = self._get_business_tracker_for_sim(owner_sim_info, business_type)
        if owner_sim_business_tracker is None:
            return
        owner_sim_business_tracker.transfer_business_to_sim(owner_sim_info, new_owner_sim_info)

    def on_zoneless_owner_sim_changed_household(self, business_manager:'BusinessManager', old_business_tracker=None, household_id:'int'=None):
        owner_sim_id = business_manager.owner_sim_id
        owner_sim_info = services.sim_info_manager().get(owner_sim_id)
        if old_business_tracker is None:
            old_business_tracker = self._get_or_create_tracker_for_household(business_manager.owner_household_id, business_manager.business_type)
        old_business_tracker.remove_owner_zoneless_business(owner_sim_id)
        if household_id is None:
            household = services.household_manager().get_by_sim_id(owner_sim_id)
            household_id = household.id
        new_business_tracker = self._get_or_create_tracker_for_household(household_id, business_manager.business_type)
        new_business_tracker.on_zoneless_owner_sim_changed_household(owner_sim_id, household_id, business_manager)

    def get_business_trackers_for_household(self, household_id):
        return self._business_trackers.get(household_id, None)

    def _get_business_tracker_for_sim(self, sim_info:'SimInfo', business_type:'BusinessType'):
        sim_business_tracker = None
        if sim_info.is_dead:
            for business_tracker in self.business_trackers_gen():
                business_manager = business_tracker.get_business_manager_for_sim(sim_id=sim_info.id)
                if business_manager:
                    sim_business_tracker = business_tracker
                    break
        else:
            sim_business_tracker = self.get_business_tracker_for_household(sim_info.household.id, business_type)
        return sim_business_tracker

    def get_retail_manager_for_zone(self, zone_id=None):
        business_manager = self.get_business_manager_for_zone(zone_id=zone_id)
        if business_manager is not None and business_manager.business_type == BusinessType.RETAIL:
            return business_manager

    def get_business_manager_for_zone(self, zone_id:'int'=None) -> 'Optional[BusinessManager]':
        check_active_zone = False
        current_zone_id = services.current_zone_id()
        if zone_id is None:
            zone_id = current_zone_id
            check_active_zone = True
        elif zone_id == current_zone_id:
            check_active_zone = True
        for business_tracker in self.business_trackers_gen():
            business_manager = business_tracker.get_business_manager_for_zone(zone_id=zone_id)
            if business_manager:
                return business_manager
        if check_active_zone:
            zone_director = services.venue_service().get_zone_director()
            return getattr(zone_director, 'business_manager', None)

    def get_business_manager_for_sim(self, sim_id:'int') -> 'Optional[BusinessManager]':
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is None:
            return
        if sim_info.is_dead:
            for business_tracker in self.business_trackers_gen():
                business_manager = business_tracker.get_business_manager_for_sim(sim_id=sim_info.id)
                if business_manager:
                    return business_manager
        household_id = sim_info.household_id
        for business_tracker in self._business_trackers[household_id]:
            business_manager = business_tracker.get_business_manager_for_sim(sim_id=sim_id)
            if business_manager:
                return business_manager

    def get_business_tracker_for_household(self, household_id, business_type):
        for business_tracker in self._business_trackers[household_id]:
            if business_tracker.business_type == business_type:
                return business_tracker

    def get_business_trackers_for_business_type(self, business_type:'BusinessType') -> 'list[BusinessTracker]':
        business_tracker_list = []
        for tracker in self.business_trackers_gen():
            if tracker.business_type == business_type:
                business_tracker_list.append(tracker)
        return business_tracker_list

    def increment_additional_employee_slots(self, household_id, business_type, employee_type):
        business_tracker = self.get_business_tracker_for_household(household_id, business_type)
        if business_tracker is None:
            logger.error('Trying to increment additional employee slots for business_type: {} owned by household id: {} but no tracker exists.', business_type, household_id)
            return
        business_tracker.increment_additional_employee_slots(employee_type)

    def increment_additional_markup(self, household_id, business_type, markup_increment):
        business_tracker = self.get_business_tracker_for_household(household_id, business_type)
        if business_tracker is None:
            logger.error('Trying to increment additional markup for business type: {} owned by household id: {} but no tracker exists.', business_type, household_id)
            return
        business_tracker.add_additional_markup_multiplier(markup_increment)

    def increment_additional_customer_count(self, household_id, business_type, count_increment):
        business_tracker = self.get_business_tracker_for_household(household_id, business_type)
        if business_tracker is None:
            logger.error('Trying to increment additional markup for business type: {} owned by household id: {} but no tracker exists.', business_type, household_id)
            return
        business_tracker.add_additional_customer_count(count_increment)

    def _get_or_create_tracker_for_household(self, owner_household_id, business_type):
        business_tracker = self.get_business_tracker_for_household(owner_household_id, business_type)
        if business_tracker is not None:
            return business_tracker
        household = services.household_manager().get(owner_household_id)
        business_tracker = BusinessTracker(household.id, business_type)
        self._business_trackers[owner_household_id].append(business_tracker)
        return business_tracker

    def _get_tracker_for_business_in_zone(self, zone_id:'int', household_id:'int'=None) -> 'Optional[BusinessTracker]':
        if household_id is None:
            business_trackers = self.business_trackers_gen()
        else:
            business_trackers = self.get_business_trackers_for_household(household_id)
            if business_trackers is None:
                return
        for tracker in business_trackers:
            if tracker.get_business_manager_for_zone(zone_id) is not None:
                return tracker

    def get_business_managers_for_household(self, household_id=None):
        if household_id is None:
            active_household = services.active_household()
            if active_household is None:
                return
            household_id = active_household.id
        business_trackers = self.get_business_trackers_for_household(household_id)
        if business_trackers is None:
            return
        household_business_managers = {zone_id: manager for tracker in business_trackers for (zone_id, manager) in tracker.business_managers.items()}
        household_business_managers.update({sim_id: manager for tracker in business_trackers for (sim_id, manager) in tracker.zoneless_business_managers.items()})
        return household_business_managers

    @classmethod
    def get_business_tuning_data_for_business_type(cls, business_type):
        return BusinessTuning.BUSINESS_TYPE_TO_BUSINESS_DATA_MAP.get(business_type, None)

    def on_zone_load(self) -> 'None':
        for tracker in self.business_trackers_gen():
            tracker.on_zone_load()
        self._start_off_lot_churn_alarm()
        self.send_business_data_to_client()

    def on_build_buy_enter(self):
        self.send_business_data_to_client()
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_build_buy_enter()

    def on_build_buy_exit(self):
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_build_buy_exit()
            return
        sim_info = services.active_sim_info()
        if sim_info is not None:
            business_manager = self.get_business_manager_for_sim(sim_info.id)
            if business_manager is not None:
                business_manager.on_build_buy_exit()

    def clear_owned_business(self, household_id):
        if household_id not in self._business_trackers:
            return
        zone_manager = services.get_zone_manager()
        business_trackers = self._business_trackers[household_id]
        business_managers_to_replace = []
        business_managers_to_move = []
        for business_tracker in business_trackers:
            for zone_id in business_tracker.business_managers:
                business_manager = self.get_business_manager_for_zone(zone_id)
                if business_manager is None:
                    logger.error('Business manager of zone id {} is None, and is expected not to be.', zone_id)
                elif business_manager.clear_lot_ownership_on_death_of_owner:
                    zone_manager.clear_lot_ownership(zone_id)
                elif business_manager.owner_sim_id is not None:
                    business_managers_to_move.append(business_manager)
                else:
                    business_managers_to_replace.append(business_manager)
            for business_manager in business_managers_to_move:
                business_manager.set_open(False)
            zoneless_business_managers = [business_manager for business_manager in business_tracker.zoneless_business_managers.values()]
            for business_manager in zoneless_business_managers:
                sim_id = business_manager.owner_sim_id
                new_household = services.household_manager().get_by_sim_id(sim_id)
                if new_household is not None:
                    if new_household.id != business_manager.owner_household_id:
                        new_business_tracker = self._get_or_create_tracker_for_household(new_household.id, business_tracker.business_type)
                        new_business_tracker.on_zoneless_owner_sim_changed_household(sim_id, new_household.id, business_manager)
                        business_tracker.remove_owner_zoneless_business(sim_id)
                        business_tracker.remove_owner_zoneless_business(sim_id, sell=True)
                else:
                    business_tracker.remove_owner_zoneless_business(sim_id, sell=True)
        for business_manager in business_managers_to_replace:
            self.remove_owner(business_manager.business_zone_id, household_id=household_id, unowned_business_type=business_manager.business_type)
        if household_id in self._business_trackers:
            for business_tracker in self._business_trackers[household_id]:
                if not business_tracker.zoneless_business_managers.keys():
                    if business_tracker.business_managers.keys():
                        return
                return
        del self._business_trackers[household_id]

    def handle_lot_owner_changed(self, zone_id, previous_owner_household_id):
        if previous_owner_household_id is not None:
            business_managers_dict = self.get_business_managers_for_household(previous_owner_household_id)
            if not business_managers_dict:
                return
            for business_manager in business_managers_dict.values():
                business_manager.handle_on_lot_not_owned_anymore(zone_id)

    def add_rule_preset(self, name:'str', rules:'List[Clubs_pb2.ClubConductRule]') -> 'None':
        self.rules_presets[name] = rules
        self.send_rule_presets_to_client()

    def remove_rule_preset(self, name:'str') -> 'None':
        self.rules_presets.pop(name)
        self.send_rule_presets_to_client()

    def send_rule_presets_to_client(self) -> 'None':
        preset_data_msg = Business_pb2.UpdateBusinessRulePresets()
        for (name, rules) in self.rules_presets.items():
            with ProtocolBufferRollback(preset_data_msg.presets) as presets_message:
                presets_message.name = name
                for rule in rules:
                    with ProtocolBufferRollback(presets_message.rules) as preset_rule:
                        preset_rule.encouraged = True
                        preset_rule.interaction_group = rule.interaction_group
                        if sims4.protocol_buffer_utils.has_field(rule, 'with_whom'):
                            preset_rule.with_whom = rule.with_whom
        preset_data_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.UPDATE_BUSINESS_PRESETS, preset_data_msg)
        Distributor.instance().add_op_with_no_owner(preset_data_op)

    def save(self, save_slot_data:'SaveSlotData'=None, **kwargs) -> 'None':
        business_service_data = save_slot_data.gameplay_data.business_service_data
        business_service_data.Clear()
        current_time = services.time_service().sim_now
        if self._rental_unit_payout_alarm_handle is not None:
            time = max((self._rental_unit_payout_alarm_handle.finishing_time - current_time).in_ticks(), 0)
            business_service_data.rental_unit_payout_timer = time
        for (household_id, business_trackers) in self._business_trackers.items():
            for tracker in business_trackers:
                with ProtocolBufferRollback(business_service_data.business_tracker_data) as business_tracker_data:
                    business_tracker_data.household_id = household_id
                    business_tracker_data.business_type = tracker.business_type
                    tracker.save_data(business_tracker_data)
        for tracker in self._unowned_business_trackers.values():
            with ProtocolBufferRollback(business_service_data.unowned_business_tracker_data) as business_tracker_data:
                business_tracker_data.business_type = tracker.business_type
                tracker.save_data(business_tracker_data)
        for (business_type, message_set) in self._first_time_messages.items():
            with ProtocolBufferRollback(business_service_data.first_time_messages) as first_time_messages:
                first_time_messages.business_type = business_type
                first_time_messages.messages.extend(message_set)
        if sims4.protocol_buffer_utils.has_field(business_service_data, 'rule_presets_data'):
            for (name, rules) in self.rules_presets.items():
                with ProtocolBufferRollback(business_service_data.rule_presets_data) as rule_presets_data:
                    rule_presets_data.name = name
                    for rule in rules:
                        with ProtocolBufferRollback(rule_presets_data.rules) as preset_rule:
                            preset_rule.encouraged = True
                            preset_rule.interaction_group = rule.interaction_group
                            if sims4.protocol_buffer_utils.has_field(rule, 'with_whom'):
                                preset_rule.with_whom = rule.with_whom

    def on_all_households_and_sim_infos_loaded(self, client):
        if services.get_plex_service().is_zone_a_multi_unit(services.current_zone_id()):
            self.fix_business_tracker_for_multi_unit()
        business_owning_household_ids = set(self._business_trackers.keys())
        all_households_ids = set(services.household_manager())
        invalid_household_ids = business_owning_household_ids - all_households_ids
        for household_id in invalid_household_ids:
            self.clear_owned_business(household_id)
        for tracker in self.business_trackers_gen():
            tracker.on_all_households_and_sim_infos_loaded()

    def are_business_trackers_valid(self, business_tracker_save_datas):
        for business_tracker in itertools.chain(*self._business_trackers.values()):
            business_tracker_data = None
            for business_tracker_data in business_tracker_save_datas:
                if business_tracker.owner_household_id == business_tracker_data.household_id and business_tracker.business_type == business_tracker_data.business_type:
                    if len(business_tracker.business_managers) != len(business_tracker_data.business_manager_data):
                        return False
                    break
            return False
        return True

    def show_first_time_dialog(self, business_manager:'BusinessManager', message_type:'int', **kwargs) -> 'None':
        dialog_factory = business_manager.tuning_data.first_time_notifications.get(message_type)
        if dialog_factory is None:
            return
        business_type = business_manager.business_type
        sent_messages = self._first_time_messages.get(business_type)
        if sent_messages is None:
            sent_messages = set()
            self._first_time_messages[business_type] = sent_messages
        elif message_type in sent_messages:
            return
        dialog = dialog_factory(services.active_sim_info(), resolver=business_manager.get_resolver())
        dialog.show_dialog(**kwargs)
        sent_messages.add(message_type)

    def process_zone_loaded(self) -> 'None':
        if game_services.service_manager.is_traveling:
            for business_tracker in self.business_trackers_gen():
                business_tracker.on_protocols_loaded()
            return
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if not save_slot_data_msg.gameplay_data.HasField('business_service_data'):
            self._business_trackers.clear()
            self._unowned_business_trackers.clear()
            self._first_time_messages.clear()
            return
        business_service_data = save_slot_data_msg.gameplay_data.business_service_data
        if business_service_data.rental_unit_payout_timer != 0:
            self._rental_unit_payout_alarm_handle = alarms.add_alarm(self, clock.TimeSpan(business_service_data.rental_unit_payout_timer), lambda _: self._rental_unit_payout_alarm_callback(), cross_zone=True)
        if not (business_service_data.HasField('rental_unit_payout_timer') and self._first_time_messages):
            for first_time_messages in business_service_data.first_time_messages:
                if first_time_messages.messages:
                    self._first_time_messages[first_time_messages.business_type] = set(message_type for message_type in first_time_messages.messages)
        if self._business_trackers and self.are_business_trackers_valid(business_service_data.business_tracker_data):
            for business_tracker in self.business_trackers_gen():
                business_tracker.on_protocols_loaded()
            return
        self._business_trackers.clear()
        self._unowned_business_trackers.clear()
        for business_tracker_data in save_slot_data_msg.gameplay_data.business_service_data.unowned_business_tracker_data:
            business_tuning_data = self.get_business_tuning_data_for_business_type(business_tracker_data.business_type)
            if business_tuning_data is None:
                pass
            else:
                business_tracker = BusinessTracker(None, business_tracker_data.business_type)
                business_tracker.load_data(business_tracker_data)
                self._unowned_business_trackers[business_tracker_data.business_type] = business_tracker
        for business_tracker_data in save_slot_data_msg.gameplay_data.business_service_data.business_tracker_data:
            business_tuning_data = self.get_business_tuning_data_for_business_type(business_tracker_data.business_type)
            if business_tuning_data is None:
                pass
            else:
                business_tracker = BusinessTracker(business_tracker_data.household_id, business_tracker_data.business_type)
                business_tracker.load_data(business_tracker_data)
                self._business_trackers[business_tracker_data.household_id].append(business_tracker)
        if sims4.protocol_buffer_utils.has_field(save_slot_data_msg.gameplay_data.business_service_data, 'rule_presets_data'):
            rule_preset_data = save_slot_data_msg.gameplay_data.business_service_data.rule_presets_data
            for preset in rule_preset_data:
                self.add_rule_preset(preset.name, preset.rules)

    def fix_business_tracker_for_multi_unit(self):
        plex_service = services.get_plex_service()
        persistence_service = services.get_persistence_service()
        business_service = services.business_service()
        lot_decoration_service = services.lot_decoration_service()
        current_zone_id = services.current_zone_id()
        current_lot_id = persistence_service.get_lot_id_from_zone_id(current_zone_id)
        plex_zones_in_current_lot = plex_service.get_plex_zones_in_group(current_zone_id)
        owner_household = get_current_venue_owner_id(current_zone_id)
        business_tracker = services.business_service().get_business_tracker_for_household(owner_household, BusinessType.RENTAL_UNIT)
        need_fix = False
        business_zones_in_current_lot = set()
        if business_tracker:
            for zone_id in business_tracker.get_business_zones_in_tracker():
                lot_id = persistence_service.get_lot_id_from_zone_id(zone_id)
                if lot_id == current_lot_id:
                    business_zones_in_current_lot.add(zone_id)
            if business_zones_in_current_lot != plex_zones_in_current_lot:
                need_fix = True
        elif len(plex_zones_in_current_lot) > 0:
            need_fix = True
        if need_fix:
            business_service.on_multi_unit_zone_change(owner_household, set(plex_zones_in_current_lot), business_zones_in_current_lot)
            if lot_decoration_service is not None:
                lot_decoration_service.on_multi_unit_zone_change(set(plex_zones_in_current_lot), business_zones_in_current_lot)

    def load_legacy_data(self, household, household_proto):
        legacy_save_data = None
        if hasattr(household_proto.gameplay_data, 'retail_data'):
            legacy_save_data = household_proto.gameplay_data.retail_data
        if not legacy_save_data:
            return
        business_tuning_data = self.get_business_tuning_data_for_business_type(BusinessType.RETAIL)
        if business_tuning_data is None:
            return
        retail_business_tracker = self.get_business_tracker_for_household(household.id, BusinessType.RETAIL)
        if retail_business_tracker is None:
            retail_business_tracker = BusinessTracker(household.id, BusinessType.RETAIL)
            self._business_trackers[household.id].append(retail_business_tracker)
        for retail_store_data in legacy_save_data:
            retail_business_tracker.load_legacy_data(retail_store_data)
            retail_store_data.Clear()
        additional_employee_slot = household_proto.gameplay_data.additional_employee_slots
        retail_business_tracker.set_legacy_additional_employee_slot(additional_employee_slot)

    def send_business_data_to_client(self):
        business_managers_dict = self.get_business_managers_for_household()
        if not business_managers_dict:
            return
        for business_manager in business_managers_dict.values():
            business_manager.send_data_to_client()
        self.send_rule_presets_to_client()

    def get_culling_npc_score(self, sim_info):
        if self.is_employee_of_any_business(sim_info):
            return self.EMPLOYEE_ADDITIONAL_IMMUNITY
        return 0

    def is_employee_of_any_business(self, sim_info):
        for business_trackers in self._business_trackers.values():
            for tracker in business_trackers:
                for business_manager in tracker.business_managers.values():
                    if business_manager.is_employee(sim_info):
                        return True
        return False

    def notify_fire_ended(self):
        for business_trackers in self._business_trackers.values():
            for tracker in business_trackers:
                for business_manager in tracker.business_managers.values():
                    business_manager.on_fire_ended()
