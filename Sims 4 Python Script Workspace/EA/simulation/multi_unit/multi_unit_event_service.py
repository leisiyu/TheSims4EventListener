from __future__ import annotationsfrom typing import TYPE_CHECKINGfrom venues.venue_enums import VenueTypesif TYPE_CHECKING:
    from drama_scheduler.multi_unit_drama_node import MultiUnitEventDramaNode
    from event_testing.resolver import Resolver
    from sims4.tuning.instances import HashedTunedInstanceMetaclass
    from typing import *
    from zone_modifier.zone_modifier import ZoneModifierfrom protocolbuffers import GameplaySaveData_pb2from protocolbuffers.GameplaySaveData_pb2 import GameplayOptionsfrom business.business_enums import BusinessTypefrom date_and_time import TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom drama_scheduler.drama_node_types import DramaNodeTypefrom drama_scheduler.multi_unit_drama_node import UNIT_ZONE_REQUIRES_MODIFIER_CLEANUP_MARKERfrom event_testing.resolver import SingleSimAndHouseholdResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom sims4.common import Packfrom sims4.tuning.tunable import TunableInterval, TunableRange, TunableMapping, TunableEnumEntry, TunablePackSafeReference, TunableReferencefrom sims4.utils import classpropertyimport alarmsimport date_and_timeimport enumimport persistence_error_typesimport randomimport servicesimport sims4.loglogger = sims4.log.Logger('MultiUnitEventService', default_owner='madang')
class MultiUnitCommonAreaEventBehavior(enum.Int):
    UNIT_EVENT_BLOCKS_COMMON_AREA_EVENT = 1
    COMMON_AREA_EVENT_TERMINATES_UNIT_EVENT_IMMEDIATE = 2
    COMMON_AREA_EVENT_TERMINATES_UNIT_EVENT_DEFERRED = 3

class MultiUnitEventService(sims4.service_manager.Service):
    PROPERTY_OWNER_EVENT_TIME_INTERVAL = TunableInterval(description='\n        The min and max possible time (in hours) that the Property Owner event alarm will\n        trigger.  A random amount of time between them will be chosen each time alarm is \n        set up.\n        ', tunable_type=int, default_lower=3, default_upper=5, minimum=1)
    PROPERTY_OWNER_MAX_ACTIVE_EVENTS = TunableRange(description='\n        The maximum number of active events a Property Owner may have at any given time.\n        ', tunable_type=int, default=1, minimum=1)
    PROPERTY_OWNER_EVENT_TABLE = TunablePackSafeReference(description='\n        The Event Table, represented by this RandomWeightedLoot, will determine and  \n        launch the appropriate residential rental event (via drama node loot).\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('RandomWeightedLoot',))
    TESTED_UNIT_LOT_TRAITS = TunableMapping(description='\n        A mapping of ZoneModifiers => Tests, where the ZoneModifiers represent a \n        specific lot condition.  The ZoneModifiers will be tested against in the \n        PROPERTY_OWNER_EVENT_TABLE to determine whether an event type can be selected \n        for a unit.\n        ', key_type=TunableReference(description='\n            The ZoneModifier to test for.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), class_restrictions=('ZoneModifier',), pack_safe=True), value_type=TunableTestSet(description='\n            A series of tests that must pass in order for this ZoneModifier to be \n            applied to a zone.\n            '))
    TENANT_EVENT_TIME_INTERVAL = TunableInterval(description='\n        Interval in sim hours between attempts to trigger tenant events.\n        ', tunable_type=int, default_lower=23, default_upper=25, minimum=1)
    TENANT_EVENT_TABLE = TunablePackSafeReference(description="\n        A RandomWeightLoot event table that will determine and launch a tenant event\n        for the active household's home unit.\n        ", manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('RandomWeightedLoot',))
    MULTI_UNIT_EVENT_COMMON_AREA_EVENT_BEHAVIOR = TunableEnumEntry(description='\n        When scheduling a common area event, this is how it is affected by and affects\n        any existing unit events.\n        ', tunable_type=MultiUnitCommonAreaEventBehavior, default=MultiUnitCommonAreaEventBehavior.UNIT_EVENT_BLOCKS_COMMON_AREA_EVENT)

    def __init__(self):
        self._property_owner_event_alarm_handle = None
        self._tenant_event_alarm_handle = None
        self._current_property_owner_hh_id = 0
        self._events_enabled = True
        self._household_loaded = False
        self._enable_non_rental_unit_events = True
        self._property_owner_active_events = {}
        self._property_owners_event_data = {}
        self._property_owner_alarms = {}
        self._tenant_alarms = {}
        self._multi_unit_lot_active_events = {}
        self._multi_unit_zone_active_events = {}
        self._multi_unit_common_area_events = {}
        self._completed_inactive_events = []
        self._property_zone_modifiers = {}

    @classproperty
    def required_packs(cls):
        return (Pack.EP15,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_MULTI_UNIT_EVENT_SERVICE

    def get_current_property_owner_events(self) -> 'Dict[int, int]':
        return self._property_owner_active_events

    def get_all_property_owner_event_data(self) -> 'Dict[int, int]':
        return self._property_owners_event_data

    def get_multi_unit_lot_active_events(self) -> 'Dict[int, int]':
        return self._multi_unit_lot_active_events

    def get_multi_unit_zone_active_event_type(self, unit_zone_id:'int') -> 'Optional[HashedTunedInstanceMetaclass]':
        return self._multi_unit_zone_active_events.get(unit_zone_id, None)

    def get_multi_unit_zone_best_active_event(self, unit_zone_id:'int') -> 'Optional[int]':
        if unit_zone_id in self._multi_unit_lot_active_events:
            return self._multi_unit_lot_active_events[unit_zone_id]
        else:
            unit_master_zone_id = services.get_plex_service().get_master_zone_id(unit_zone_id)
            if unit_master_zone_id in self._multi_unit_common_area_events:
                controlling_zone_id = self._multi_unit_common_area_events[unit_master_zone_id]
                return self._multi_unit_lot_active_events.get(controlling_zone_id)

    def get_tenant_unit_alarm_times(self) -> 'Dict[int, TimeSpan]':
        alarms = {unit_zone_id: TimeSpan(remaining_time) for (unit_zone_id, remaining_time) in self._tenant_alarms.items()}
        if self._tenant_event_alarm_handle is not None:
            alarms.update({services.current_zone_id(): self._tenant_event_alarm_handle.get_remaining_time()})
        return alarms

    def on_zone_load(self):
        if self._household_loaded:
            self.start_tenant_events()
            self._apply_completed_inactive_event_loot()

    def on_zone_unload(self):
        if self._household_loaded:
            self._stop_tenant_event_alarm()

    def on_all_households_and_sim_infos_loaded(self, client):
        self._household_loaded = True
        self.start_events_service(client=client)

    @property
    def events_enabled(self) -> 'bool':
        return self._events_enabled

    def set_events_enabled(self, enable) -> 'None':
        self._events_enabled = enable
        if enable:
            self.start_events_service()
        else:
            self.stop_events_service()

    @property
    def enable_non_rental_unit_events(self) -> 'bool':
        return self._enable_non_rental_unit_events

    def set_enable_non_rental_unit_events(self, enable) -> 'None':
        self._enable_non_rental_unit_events = enable
        if enable:
            self.start_events_service()
        elif not self._enable_multi_unit_living_events(services.current_zone_id()):
            self.stop_events_service()

    def _is_zone_rental_unit(self, zone_id) -> 'bool':
        business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
        if business_manager is None:
            return False
        elif business_manager.business_type != BusinessType.RENTAL_UNIT:
            return False
        return True

    def _enable_multi_unit_living_events(self, zone_id, active_household=None) -> 'bool':
        if active_household is None:
            active_household = services.active_household()
        if active_household is None or active_household.home_zone_id != zone_id:
            return False
        if not self._events_enabled:
            return False
        return self._enable_non_rental_unit_events or self._is_zone_rental_unit(zone_id)

    def tenant_unit_has_active_mule_event(self, unit_zone_id:'int') -> 'bool':
        return unit_zone_id in self._multi_unit_zone_active_events

    def tenant_unit_has_active_apm_event(self, unit_zone_id:'int') -> 'bool':
        return unit_zone_id in self._property_owner_active_events

    def is_property_owner_service_active(self) -> 'bool':
        return self._property_owner_event_alarm_handle is not None

    def add_completed_inactive_event_data(self, household_id, unit_zone_id, drama_node_guid) -> 'None':
        if household_id == UNIT_ZONE_REQUIRES_MODIFIER_CLEANUP_MARKER:
            drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
            drama_node = drama_node_manager.get(drama_node_guid)
            if drama_node is not None and drama_node.common_area_event:
                plex_service = services.get_plex_service()
                unit_master_zone_id = plex_service.get_master_zone_id(unit_zone_id)
                current_master_zone_id = plex_service.get_master_zone_id(services.current_zone_id())
                if unit_master_zone_id == current_master_zone_id:
                    return
        self._completed_inactive_events.append((household_id, unit_zone_id, drama_node_guid))

    def _apply_completed_inactive_event_loot(self) -> 'None':
        plex_service = services.get_plex_service()
        drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
        current_zone_id = services.current_zone_id()
        current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
        for event_data in self._completed_inactive_events[:]:
            (household_id, unit_zone_id, drama_node_uid) = event_data
            if household_id == UNIT_ZONE_REQUIRES_MODIFIER_CLEANUP_MARKER:
                drama_node = drama_node_manager.get(drama_node_uid)
                if drama_node is not None:
                    can_cleanup_node = unit_zone_id == current_zone_id
                    if plex_service.get_master_zone_id(unit_zone_id) == current_master_zone_id:
                        can_cleanup_node = True
                    if drama_node.common_area_event and can_cleanup_node:
                        self._multi_unit_zone_active_events[unit_zone_id] = drama_node
                        self._completed_inactive_events.remove(event_data)
                        if household_id == services.active_household_id():
                            drama_node = drama_node_manager.get(drama_node_uid)
                            if drama_node is not None:
                                resolver = self.get_resolver(unit_zone_id)
                                for loot in drama_node.fallback_loots:
                                    loot.apply_to_resolver(resolver)
                                self._completed_inactive_events.remove(event_data)
            elif household_id == services.active_household_id():
                drama_node = drama_node_manager.get(drama_node_uid)
                if drama_node is not None:
                    resolver = self.get_resolver(unit_zone_id)
                    for loot in drama_node.fallback_loots:
                        loot.apply_to_resolver(resolver)
                    self._completed_inactive_events.remove(event_data)

    def _get_event_equivalent_node_type(self, event_drama_node:'MultiUnitEventDramaNode') -> 'MultiUnitEventDramaNode':
        drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
        for drama_node in drama_node_manager.types.values():
            if drama_node.drama_node_type == DramaNodeType.MULTI_UNIT_EVENT and drama_node.guid64 != event_drama_node.guid64 and drama_node.event_type == event_drama_node.event_type:
                return drama_node

    def _convert_mule_to_apm_events(self) -> 'None':
        drama_scheduler = services.drama_scheduler_service()
        for household_id in services.get_multi_unit_ownership_service().get_tenants_household_ids(self._current_property_owner_hh_id):
            if self._current_property_owner_hh_id == household_id:
                pass
            else:
                household = services.household_manager().get(household_id)
                if household is not None and (household.home_zone_id and household.home_zone_id in self._multi_unit_lot_active_events) and household.home_zone_id not in self._property_owner_active_events:
                    zone_id = household.home_zone_id
                    drama_node_id = self._multi_unit_lot_active_events[zone_id]
                    event_drama_node = drama_scheduler.get_scheduled_node_by_uid(drama_node_id)
                    if event_drama_node is not None:
                        apm_event_drama_node_type = self._get_event_equivalent_node_type(event_drama_node)
                        if apm_event_drama_node_type is not None:
                            resolver = self.get_resolver(zone_id)
                            specific_time = services.time_service().sim_now + event_drama_node.get_time_remaining()
                            drama_scheduler.schedule_node(apm_event_drama_node_type, resolver, specific_time=specific_time)

    def _start_property_owner_events(self, household) -> 'None':
        if not self._property_owner_active_events:
            self._current_property_owner_hh_id = household.id
            ownership_service = services.get_multi_unit_ownership_service()
            temp_event_data = self._property_owners_event_data.copy()
            for (unit_zone_id, drama_node_guid64) in temp_event_data.items():
                if ownership_service.get_property_owner_household_id(unit_zone_id) == self._current_property_owner_hh_id:
                    self._property_owner_active_events[unit_zone_id] = drama_node_guid64
                    del self._property_owners_event_data[unit_zone_id]
        self._convert_mule_to_apm_events()
        self._setup_property_owner_alarm()

    def start_events_service(self, client=None) -> 'None':
        if client is not None:
            active_household = client.household
        else:
            active_household = services.active_household()
        if active_household is not None:
            if services.business_service().get_business_tracker_for_household(active_household.id, BusinessType.RENTAL_UNIT) is not None:
                self._start_property_owner_events(active_household)
            self.start_tenant_events()
            self._apply_completed_inactive_event_loot()

    def stop_events_service(self) -> 'None':
        self._stop_property_owner_alarm()
        self._stop_tenant_event_alarm()

    def _setup_property_owner_alarm(self):
        if self._property_owner_event_alarm_handle is not None:
            alarms.cancel_alarm(self._property_owner_event_alarm_handle)
            self._property_owner_event_alarm_handle = None
        if self._current_property_owner_hh_id in self._property_owner_alarms:
            time_till_next_alarm = TimeSpan(self._property_owner_alarms[self._current_property_owner_hh_id])
            del self._property_owner_alarms[self._current_property_owner_hh_id]
        else:
            random_alarm_hours = self.PROPERTY_OWNER_EVENT_TIME_INTERVAL.random_int()
            time_till_next_alarm = date_and_time.create_time_span(hours=random_alarm_hours)
        self._property_owner_event_alarm_handle = alarms.add_alarm(self, time_till_next_alarm, self._property_owner_event_alarm_callback, cross_zone=True)

    def _stop_property_owner_alarm(self) -> 'None':
        if self._property_owner_event_alarm_handle is not None:
            self._property_owner_alarms[self._current_property_owner_hh_id] = self._property_owner_event_alarm_handle.get_remaining_time().in_ticks()
            alarms.cancel_alarm(self._property_owner_event_alarm_handle)
            self._property_owner_event_alarm_handle = None

    def _property_owner_event_alarm_callback(self, _):
        if len(self._property_owner_active_events) < self.PROPERTY_OWNER_MAX_ACTIVE_EVENTS:
            selected_unit_zone_id = self.select_unit_zone_id()
            if selected_unit_zone_id is not None:
                self._update_unit_zone_modifiers(selected_unit_zone_id)
                resolver = self.get_resolver(selected_unit_zone_id)
                self.PROPERTY_OWNER_EVENT_TABLE.apply_to_resolver(resolver)
        self._setup_property_owner_alarm()

    def start_tenant_events(self) -> 'None':
        if self._tenant_event_alarm_handle is not None:
            return
        active_household = services.active_household()
        if not active_household:
            return
        current_zone_id = services.current_zone_id()
        if self._enable_multi_unit_living_events(current_zone_id, active_household):
            self._setup_tenant_event_alarm()

    def _setup_tenant_event_alarm(self) -> 'None':
        if self._tenant_event_alarm_handle is not None:
            alarms.cancel_alarm(self._tenant_event_alarm_handle)
            self._tenant_event_alarm_handle = None
        current_zone_id = services.current_zone_id()
        if current_zone_id in self._tenant_alarms:
            next_alarm_time = TimeSpan(self._tenant_alarms[current_zone_id])
            del self._tenant_alarms[current_zone_id]
        else:
            random_alarm_hours = self.TENANT_EVENT_TIME_INTERVAL.random_int()
            next_alarm_time = date_and_time.create_time_span(hours=random_alarm_hours)
        self._tenant_event_alarm_handle = alarms.add_alarm(self, time_span=next_alarm_time, callback=self._tenant_event_alarm_callback, cross_zone=False)

    def _stop_tenant_event_alarm(self) -> 'None':
        if self._tenant_event_alarm_handle is not None:
            current_zone_id = services.current_zone_id()
            self._tenant_alarms[current_zone_id] = self._tenant_event_alarm_handle.get_remaining_time().in_ticks()
            alarms.cancel_alarm(self._tenant_event_alarm_handle)
            self._tenant_event_alarm_handle = None

    def _tenant_event_alarm_callback(self, _) -> 'None':
        current_zone_id = services.current_zone_id()
        current_master_zone_id = services.get_plex_service().get_master_zone_id(current_zone_id)
        if current_zone_id not in self._multi_unit_zone_active_events and current_master_zone_id not in self._multi_unit_common_area_events:
            resolver = self.get_resolver(current_zone_id)
            MultiUnitEventService.TENANT_EVENT_TABLE.apply_to_resolver(resolver)
        self._setup_tenant_event_alarm()

    def select_unit_zone_id(self) -> 'int':
        available_units = []
        for household_id in services.get_multi_unit_ownership_service().get_tenants_household_ids(self._current_property_owner_hh_id):
            if self._current_property_owner_hh_id == household_id:
                pass
            else:
                household = services.household_manager().get(household_id)
                if household is not None and household.home_zone_id and household.home_zone_id not in self._property_owner_active_events:
                    available_units.append(household.home_zone_id)
        if available_units:
            return random.choice(available_units)

    def _update_unit_zone_modifiers(self, unit_zone_id):
        if services.current_zone_id() == unit_zone_id:
            zone_modifier_service = services.get_zone_modifier_service()
            if zone_modifier_service is not None:
                zone_modifier_service.check_for_and_apply_new_zone_modifiers(unit_zone_id)

    def can_start_event(self, unit_zone_id, event_drama_node) -> 'TestResult':
        if MultiUnitEventService.MULTI_UNIT_EVENT_COMMON_AREA_EVENT_BEHAVIOR != MultiUnitCommonAreaEventBehavior.UNIT_EVENT_BLOCKS_COMMON_AREA_EVENT:
            return TestResult.TRUE
        plex_service = services.get_plex_service()
        unit_master_zone_id = plex_service.get_master_zone_id(unit_zone_id)
        if event_drama_node.common_area_event:
            if unit_master_zone_id in self._multi_unit_common_area_events:
                controlling_zone_id = self._multi_unit_common_area_events[unit_master_zone_id]
                existing_drama_node = services.drama_scheduler_service().get_scheduled_node_by_uid(self._multi_unit_lot_active_events[controlling_zone_id])
                if not (existing_drama_node is not None and existing_drama_node.event_type == event_drama_node.event_type and existing_drama_node.guid64 != event_drama_node.guid64):
                    return TestResult(False, 'Cannot run unit event because unit {} already has a shared event {} running in {}.', unit_zone_id, self._multi_unit_lot_active_events[controlling_zone_id], controlling_zone_id)
        else:
            for (zone_id, event_node_id) in self._multi_unit_lot_active_events.items():
                if plex_service.get_master_zone_id(zone_id) == unit_master_zone_id:
                    return TestResult(False, 'Cannot run shared event for {} in master {} because unit {} is running unit event {}.', unit_zone_id, unit_master_zone_id, zone_id, event_node_id)
        return TestResult.TRUE

    def add_property_owner_active_event(self, unit_zone_id, event_drama_node) -> 'None':
        if unit_zone_id not in self._property_owner_active_events:
            self._property_owner_active_events[unit_zone_id] = event_drama_node.uid
        check_common_area = False
        mule_event_drama_node_type = self._get_event_equivalent_node_type(event_drama_node)
        if mule_event_drama_node_type.start_in_any_relevant_unit:
            check_common_area = mule_event_drama_node_type.common_area_event
        if mule_event_drama_node_type is not None and check_common_area or unit_zone_id == services.current_zone_id():
            self._start_mule_event_from_current_apm_events()
        self._update_unit_zone_modifiers(unit_zone_id)

    def add_multi_unit_active_event(self, unit_zone_id, event_drama_node) -> 'None':
        if unit_zone_id not in self._multi_unit_lot_active_events:
            plex_service = services.get_plex_service()
            current_zone_id = services.current_zone_id()
            current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
            unit_master_zone_id = plex_service.get_master_zone_id(unit_zone_id)
            drama_scheduler = services.drama_scheduler_service()
            if not event_drama_node.common_area_event:
                if unit_master_zone_id in self._multi_unit_common_area_events:
                    controlling_zone_id = self._multi_unit_common_area_events[unit_master_zone_id]
                    drama_scheduler.cancel_scheduled_node(self._multi_unit_lot_active_events[controlling_zone_id])
                self._multi_unit_lot_active_events[unit_zone_id] = event_drama_node.uid
                affects_current_zone = unit_master_zone_id == current_master_zone_id
            else:
                if MultiUnitEventService.MULTI_UNIT_EVENT_COMMON_AREA_EVENT_BEHAVIOR == MultiUnitCommonAreaEventBehavior.COMMON_AREA_EVENT_TERMINATES_UNIT_EVENT_DEFERRED:
                    if unit_zone_id in self._multi_unit_lot_active_events:
                        drama_scheduler.cancel_scheduled_node(self._multi_unit_lot_active_events[unit_zone_id])
                    self._multi_unit_lot_active_events[unit_zone_id] = event_drama_node.uid
                    self._multi_unit_common_area_events[unit_master_zone_id] = unit_zone_id
                    affects_current_zone = unit_master_zone_id == current_master_zone_id
                for (zone_id, event_node_id) in list(self._multi_unit_lot_active_events.items()):
                    if plex_service.get_master_zone_id(zone_id) == unit_master_zone_id:
                        drama_scheduler.cancel_scheduled_node(event_node_id)
                self._multi_unit_lot_active_events[unit_zone_id] = event_drama_node.uid
                self._multi_unit_common_area_events[unit_master_zone_id] = unit_zone_id
                affects_current_zone = unit_master_zone_id == current_master_zone_id
            if affects_current_zone:
                self._multi_unit_zone_event_initialize_for_active_household(event_drama_node)
            else:
                logger.error('DramaNode {} attempting to start in inactive zone {}.', event_drama_node, event_drama_node.get_unit_zone_id(), owner='jmoline')
                drama_scheduler.cancel_scheduled_node(event_drama_node.uid)
                return
            self._update_unit_zone_modifiers(unit_zone_id)
            if affects_current_zone and unit_zone_id != current_zone_id:
                self._update_unit_zone_modifiers(current_zone_id)

    def remove_property_owner_active_event(self, unit_zone_id) -> 'None':
        if unit_zone_id in self._property_owner_active_events:
            del self._property_owner_active_events[unit_zone_id]
        if unit_zone_id in self._property_owners_event_data:
            del self._property_owners_event_data[unit_zone_id]
        self._update_unit_zone_modifiers(unit_zone_id)

    def remove_multi_unit_active_event(self, unit_zone_id, event_drama_node) -> 'None':
        if unit_zone_id in self._multi_unit_lot_active_events:
            plex_service = services.get_plex_service()
            current_zone_id = services.current_zone_id()
            current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
            unit_master_zone_id = plex_service.get_master_zone_id(unit_zone_id)
            del self._multi_unit_lot_active_events[unit_zone_id]
            if event_drama_node.common_area_event:
                del self._multi_unit_common_area_events[unit_master_zone_id]
                affects_current_zone = unit_master_zone_id == current_master_zone_id
            else:
                affects_current_zone = unit_zone_id == current_zone_id
            if affects_current_zone:
                self._multi_unit_zone_event_cleanup(event_drama_node=event_drama_node)
                self._start_mule_event_from_current_apm_events()
            self._update_unit_zone_modifiers(unit_zone_id)
            if affects_current_zone and unit_zone_id != current_zone_id:
                self._update_unit_zone_modifiers(current_zone_id)

    @staticmethod
    def _get_modifiers_from_drama_node_id(event_node_id) -> 'list[ZoneModifier]':
        event_node = services.drama_scheduler_service().get_scheduled_node_by_uid(event_node_id)
        if event_node is None or event_node.drama_node_type != DramaNodeType.MULTI_UNIT_EVENT:
            return list()
        if event_node.get_unit_event_outcome() is not None:
            return list()
        return event_node.unit_zone_modifiers

    def get_additional_zone_modifiers(self, unit_zone_id) -> 'set[ZoneModifier]':
        additional_zone_modifiers = set()
        if unit_zone_id in self._property_owner_active_events:
            additional_zone_modifiers.update(self._get_modifiers_from_drama_node_id(self._property_owner_active_events[unit_zone_id]))
        if unit_zone_id in self._multi_unit_lot_active_events:
            additional_zone_modifiers.update(self._get_modifiers_from_drama_node_id(self._multi_unit_lot_active_events[unit_zone_id]))
        unit_master_zone_id = services.get_plex_service().get_master_zone_id(unit_zone_id)
        if unit_master_zone_id in self._multi_unit_common_area_events:
            controlling_zone_id = self._multi_unit_common_area_events[unit_master_zone_id]
            additional_zone_modifiers.update(self._get_modifiers_from_drama_node_id(self._multi_unit_lot_active_events[controlling_zone_id]))
        if unit_zone_id in self._property_zone_modifiers:
            additional_zone_modifiers.update(self._property_zone_modifiers[unit_zone_id])
        return additional_zone_modifiers

    def evaluate_tested_zone_modifiers_for_current_zone(self) -> 'None':
        zone = services.current_zone()
        if zone is None:
            return
        unit_zone_id = services.current_zone_id()
        zone_modifiers = set()
        active_venue = services.venue_service().active_venue
        if active_venue.is_residential:
            resolver = self.get_resolver(unit_zone_id)
            for (zone_modifier, tests) in self.TESTED_UNIT_LOT_TRAITS.items():
                if tests.run_tests(resolver):
                    zone_modifiers.add(zone_modifier)
        if (VenueTypes.MULTI_UNIT == active_venue.venue_type or self._enable_non_rental_unit_events) and len(zone_modifiers) == 0:
            if unit_zone_id in self._property_zone_modifiers:
                del self._property_zone_modifiers[unit_zone_id]
                self._update_unit_zone_modifiers(unit_zone_id)
        elif unit_zone_id not in self._property_zone_modifiers or self._property_zone_modifiers[unit_zone_id] != zone_modifiers:
            self._property_zone_modifiers[unit_zone_id] = zone_modifiers
            self._update_unit_zone_modifiers(unit_zone_id)

    def get_resolver(self, unit_zone_id:'int', set_target_as_actor_hh=False) -> 'Resolver':
        target_household = services.household_manager().get_by_home_zone_id(unit_zone_id)
        actor_household = services.active_household()
        if set_target_as_actor_hh:
            actor_household = target_household
        additional_participants = {ParticipantType.PickedZoneId: (unit_zone_id,), ParticipantType.ActorHousehold: (actor_household,)}
        resolver = SingleSimAndHouseholdResolver(services.active_sim_info(), target_household, additional_participants=additional_participants)
        return resolver

    def save(self, save_slot_data=None, **__):
        multi_unit_event_proto = GameplaySaveData_pb2.PersistableMultiUnitEventService()
        current_zone_id = services.current_zone_id()
        temp_tenant_alarms = self._tenant_alarms.copy()
        if self._tenant_event_alarm_handle is not None:
            temp_tenant_alarms[current_zone_id] = self._tenant_event_alarm_handle.get_remaining_time().in_ticks()
        elif current_zone_id in temp_tenant_alarms:
            active_household = services.active_household()
            if current_zone_id == active_household.home_zone_id:
                del temp_tenant_alarms[current_zone_id]
        unit_zone_ids = set()
        unit_zone_ids.update(self._property_owners_event_data.keys())
        unit_zone_ids.update(self._property_owner_active_events.keys())
        unit_zone_ids.update(self._multi_unit_lot_active_events.keys())
        unit_zone_ids.update(self._property_zone_modifiers.keys())
        for unit_zone_id in unit_zone_ids:
            with ProtocolBufferRollback(multi_unit_event_proto.zone_event_data) as zone_event_data_msg:
                zone_event_data_msg.zone_id = unit_zone_id
                if unit_zone_id in self._property_owners_event_data:
                    zone_event_data_msg.property_owner_event_drama_node_guid64 = self._property_owners_event_data[unit_zone_id]
                if unit_zone_id in self._property_owner_active_events:
                    zone_event_data_msg.property_owner_event_drama_node_guid64 = self._property_owner_active_events[unit_zone_id]
                if unit_zone_id in self._multi_unit_lot_active_events:
                    zone_event_data_msg.active_event_drama_node_guid64 = self._multi_unit_lot_active_events[unit_zone_id]
                if unit_zone_id in temp_tenant_alarms:
                    zone_event_data_msg.tenant_alarm_time = temp_tenant_alarms[unit_zone_id]
                if unit_zone_id in self._property_zone_modifiers:
                    zone_event_data_msg.tested_zone_modifier_guid64s.extend([modifier.guid64 for modifier in self._property_zone_modifiers[unit_zone_id]])
        temp_property_owner_alarms = self._property_owner_alarms.copy()
        if self._property_owner_event_alarm_handle is not None:
            temp_property_owner_alarms[self._current_property_owner_hh_id] = self._property_owner_event_alarm_handle.get_remaining_time().in_ticks()
        for (property_owner_hh_id, event_alarm_time) in temp_property_owner_alarms.items():
            with ProtocolBufferRollback(multi_unit_event_proto.property_owner_event_data) as property_owner_event_data_msg:
                property_owner_event_data_msg.property_owner_hh_id = property_owner_hh_id
                property_owner_event_data_msg.event_alarm_time = event_alarm_time
        for (household_id, unit_zone_id, drama_node_guid) in self._completed_inactive_events:
            with ProtocolBufferRollback(multi_unit_event_proto.event_loot_data) as loot_event_data_msg:
                loot_event_data_msg.household_id = household_id
                loot_event_data_msg.zone_id = unit_zone_id
                loot_event_data_msg.drama_node_guid64 = drama_node_guid
        save_slot_data.gameplay_data.multi_unit_event_service = multi_unit_event_proto

    def load(self, **__):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.gameplay_data.HasField('multi_unit_event_service'):
            drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
            zone_modifier_manager = services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER)
            data = save_slot_data_msg.gameplay_data.multi_unit_event_service
            for zone_event_data in data.zone_event_data:
                zone_id = zone_event_data.zone_id
                po_drama_node_id = zone_event_data.property_owner_event_drama_node_guid64
                mule_drama_node_id = zone_event_data.active_event_drama_node_guid64
                if po_drama_node_id:
                    self._property_owners_event_data[zone_id] = po_drama_node_id
                if mule_drama_node_id:
                    self._multi_unit_lot_active_events[zone_id] = mule_drama_node_id
                if zone_event_data.tenant_alarm_time > 0:
                    self._tenant_alarms[zone_id] = zone_event_data.tenant_alarm_time
                if zone_event_data.tested_zone_modifier_guid64s:
                    zone_modifiers = set()
                    for zone_modifier_guid64 in zone_event_data.tested_zone_modifier_guid64s:
                        zone_modifier = zone_modifier_manager.get(zone_modifier_guid64)
                        if zone_modifier is not None:
                            zone_modifiers.add(zone_modifier)
                    self._property_zone_modifiers[zone_id] = zone_modifiers
            for property_owner_event_data in data.property_owner_event_data:
                self._property_owner_alarms[property_owner_event_data.property_owner_hh_id] = property_owner_event_data.event_alarm_time
            for event_loot_data in data.event_loot_data:
                self._completed_inactive_events.append((event_loot_data.household_id, event_loot_data.zone_id, event_loot_data.drama_node_guid64))

    def save_options(self, options_proto:'GameplayOptions') -> 'None':
        options_proto.multi_unit_events_enabled = self._events_enabled

    def load_options(self, options_proto:'GameplayOptions') -> 'None':
        self._events_enabled = options_proto.multi_unit_events_enabled

    def _multi_unit_zone_event_initialize_for_active_household(self, event_drama_node:'MultiUnitEventDramaNode', loading:'bool'=False) -> 'None':
        plex_service = services.get_plex_service()
        current_zone_id = services.current_zone_id()
        current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
        event_drama_node_type = event_drama_node.__class__
        if not loading:
            self._multi_unit_zone_event_cleanup()
        is_home_zone = False
        is_owned_zone = False
        is_home_common_area = False
        active_household = services.active_household()
        if active_household is not None:
            is_home_zone = active_household.home_zone_id == current_zone_id
            ownership_service = services.get_multi_unit_ownership_service()
            if ownership_service is not None:
                is_owned_zone = active_household.id == ownership_service.get_property_owner_household_id(current_zone_id)
            if event_drama_node.common_area_event:
                home_master_zone_id = plex_service.get_master_zone_id(active_household.home_zone_id)
                if home_master_zone_id == current_master_zone_id:
                    is_home_common_area = True
        if is_home_zone or is_owned_zone or is_home_common_area:
            event_drama_node.run_situation()
        if loading:
            new_event = current_zone_id not in self._multi_unit_zone_active_events
            if event_drama_node.common_area_event:
                for (zone_id, node_type) in self._multi_unit_zone_active_events.items():
                    if plex_service.get_master_zone_id(zone_id) == current_master_zone_id and node_type is event_drama_node_type:
                        new_event = False
            if new_event:
                for zone_modifier in event_drama_node.unit_zone_modifiers:
                    zone_modifier.on_add_actions(False)
        self._multi_unit_zone_active_events[current_zone_id] = event_drama_node_type

    def _multi_unit_zone_event_cleanup(self, event_drama_node:'MultiUnitEventDramaNode'=None, loading:'bool'=False) -> 'None':
        plex_service = services.get_plex_service()
        current_zone_id = services.current_zone_id()
        current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
        event_drama_node_type = self._multi_unit_zone_active_events.get(current_zone_id)
        if event_drama_node_type is None:
            if event_drama_node is None:
                return
            event_drama_node_type = event_drama_node.__class__
        if event_drama_node is not None:
            event_drama_node.end_situation()
        if loading:
            for zone_modifier in event_drama_node_type.unit_zone_modifiers:
                zone_modifier.on_remove_actions()
        if current_zone_id in self._multi_unit_zone_active_events:
            del self._multi_unit_zone_active_events[current_zone_id]
        if event_drama_node_type.common_area_event:
            for (zone_id, node_type) in tuple(self._multi_unit_zone_active_events.items()):
                if plex_service.get_master_zone_id(zone_id) == current_master_zone_id and node_type is event_drama_node_type:
                    del self._multi_unit_zone_active_events[zone_id]

    def sync_event_state_from_drama_scheduler(self):
        plex_service = services.get_plex_service()
        current_zone_id = services.current_zone_id()
        current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
        drama_scheduler = services.drama_scheduler_service()
        lot_zone_ids = tuple(self._multi_unit_lot_active_events.keys())
        for zone_id in lot_zone_ids:
            drama_node = drama_scheduler.get_scheduled_node_by_uid(self._multi_unit_lot_active_events[zone_id])
            if drama_node is None:
                del self._multi_unit_lot_active_events[zone_id]
            else:
                self._multi_unit_zone_active_events[zone_id] = drama_node.__class__
                if zone_id not in self._multi_unit_zone_active_events and drama_node.common_area_event:
                    master_zone_id = plex_service.get_master_zone_id(zone_id)
                    self._multi_unit_common_area_events[master_zone_id] = zone_id
        if current_zone_id in self._property_owners_event_data or (current_zone_id in self._property_owner_active_events or current_zone_id in self._multi_unit_lot_active_events) or current_master_zone_id in self._multi_unit_common_area_events:
            self._update_unit_zone_modifiers(current_zone_id)

    def prepare_multi_unit_event_state(self):
        plex_service = services.get_plex_service()
        current_zone_id = services.current_zone_id()
        current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
        controlling_zone_id = self._multi_unit_common_area_events.get(current_master_zone_id)
        drama_scheduler = services.drama_scheduler_service()
        self.evaluate_tested_zone_modifiers_for_current_zone()
        if current_zone_id in self._multi_unit_zone_active_events:
            expected_drama_node_uid = self._multi_unit_lot_active_events.get(current_zone_id, None)
            if controlling_zone_id in self._multi_unit_lot_active_events:
                expected_drama_node_uid = self._multi_unit_lot_active_events[controlling_zone_id]
            expected_drama_node = None
            if expected_drama_node_uid is None and controlling_zone_id is not None and expected_drama_node_uid is not None:
                expected_drama_node = drama_scheduler.get_scheduled_node_by_uid(expected_drama_node_uid)
            if expected_drama_node is None or self._multi_unit_zone_active_events[current_zone_id] is not expected_drama_node.__class__:
                self._multi_unit_zone_event_cleanup(loading=True)
        if controlling_zone_id is not None and controlling_zone_id != current_zone_id and current_zone_id in self._multi_unit_lot_active_events:
            drama_node_id = self._multi_unit_lot_active_events[current_zone_id]
            drama_scheduler.cancel_scheduled_node(drama_node_id)
        if self._is_zone_rental_unit(current_zone_id) or not self._enable_multi_unit_living_events(current_zone_id):
            return
        drama_node_id = None
        if current_zone_id in self._multi_unit_lot_active_events:
            drama_node_id = self._multi_unit_lot_active_events[current_zone_id]
        elif current_zone_id in self._property_owners_event_data or current_zone_id in self._property_owner_active_events:
            drama_node_id = self._start_mule_event_from_current_apm_events()
            if drama_node_id is not None:
                return
        if controlling_zone_id in self._multi_unit_lot_active_events:
            drama_node_id = self._multi_unit_lot_active_events[controlling_zone_id]
        if controlling_zone_id is not None and drama_node_id is not None:
            event_drama_node = drama_scheduler.get_scheduled_node_by_uid(drama_node_id)
            if event_drama_node is not None:
                self._multi_unit_zone_event_initialize_for_active_household(event_drama_node, loading=True)

    def _start_mule_event_from_current_apm_events(self) -> 'int':
        plex_service = services.get_plex_service()
        current_zone_id = services.current_zone_id()
        current_master_zone_id = plex_service.get_master_zone_id(current_zone_id)
        drama_scheduler = services.drama_scheduler_service()
        if current_zone_id in self._multi_unit_lot_active_events:
            return
        else:
            selected_event = None
            common_event = None
            zone_ids = list()
            zone_ids.extend(self._property_owners_event_data.keys())
            zone_ids.extend(self._property_owner_active_events.keys())
            for zone_id in zone_ids:
                if plex_service.get_master_zone_id(zone_id) == current_master_zone_id:
                    event_node = None
                    set_target_as_actor_hh = False
                    if zone_id in self._property_owners_event_data:
                        node_id = self._property_owners_event_data[zone_id]
                        event_node = drama_scheduler.get_scheduled_node_by_uid(node_id)
                    elif zone_id in self._property_owner_active_events:
                        node_id = self._property_owner_active_events[zone_id]
                        event_node = drama_scheduler.get_scheduled_node_by_uid(node_id)
                        set_target_as_actor_hh = True
                    if event_node is None:
                        pass
                    else:
                        mule_event_drama_node_type = self._get_event_equivalent_node_type(event_node)
                        if mule_event_drama_node_type is None:
                            pass
                        elif zone_id != current_zone_id and mule_event_drama_node_type.common_area_event:
                            if not mule_event_drama_node_type.start_in_any_relevant_unit:
                                pass
                            else:
                                running_nodes = drama_scheduler.get_scheduled_nodes_by_class(mule_event_drama_node_type)
                                running_nodes = [node for node in running_nodes if node.get_unit_zone_id() == zone_id]
                                if len(running_nodes) > 0:
                                    pass
                                elif zone_id == current_zone_id:
                                    selected_event = (zone_id, event_node, mule_event_drama_node_type, set_target_as_actor_hh)
                                elif common_event is None:
                                    common_event = (zone_id, event_node, mule_event_drama_node_type, set_target_as_actor_hh)
            if selected_event is None:
                selected_event = common_event
            if selected_event is not None:
                (zone_id, event_node, mule_event_drama_node_type, set_target_as_actor_hh) = selected_event
                resolver = self.get_resolver(zone_id, set_target_as_actor_hh=set_target_as_actor_hh)
                specific_time = services.time_service().sim_now + event_node.get_time_remaining()
                return drama_scheduler.schedule_node(mule_event_drama_node_type, resolver, specific_time=specific_time)

    def on_build_buy_exit(self) -> 'None':
        self.evaluate_tested_zone_modifiers_for_current_zone()

    def pre_save(self) -> 'None':
        self.evaluate_tested_zone_modifiers_for_current_zone()
