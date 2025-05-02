from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from typing import *
    from sims.household import Householdfrom date_and_time import TimeSpan, DateAndTimefrom drama_scheduler.drama_enums import MultiUnitEventOutcomefrom drama_scheduler.situation_drama_node import SituationDramaNodefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.results import TestResultfrom gsi_handlers.drama_handlers import GSIRejectedDramaNodeScoringDatafrom interactions import ParticipantTypefrom interactions.utils.tunable_icon import TunableIconfrom multi_unit.multi_unit_tuning import MultiUnitEventTypefrom sims.sim_info import SimInfofrom sims4.tuning.tunable import TunableList, Tunable, TunableReference, OptionalTunable, TunableEnumEntry, TunableTuplefrom sims4.utils import classpropertyfrom sims4.localization import TunableLocalizedStringimport randomimport servicesimport telemetry_helperimport sims4logger = sims4.log.Logger('MultiUnitEventDramaNode', default_owner='madang')UNIT_ZONE_ID_TOKEN = 'unit_zone_id'UNIT_EVENT_OUTCOME_TOKEN = 'unit_event_outcome'RECEIVER_HOUSEHOLD_ID_TOKEN = 'receiver_household_id'START_TIME_TOKEN = 'start_time'TELEMETRY_GROUP_MULTI_UNIT_EVENT = 'MULE'TELEMETRY_HOOK_MULTI_UNIT_EVENT_SET_OUTCOME = 'EVSO'TELEMETRY_FIELD_MULTI_UNIT_EVENT_TYPE = 'type'TELEMETRY_FIELD_MULTI_UNIT_EVENT_DURATION = 'sdur'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_MULTI_UNIT_EVENT)UNIT_ZONE_REQUIRES_MODIFIER_CLEANUP_MARKER = 0
class MultiUnitEventDramaNode(SituationDramaNode):
    INSTANCE_TUNABLES = {'success_loots': TunableList(description='\n            Loots that will be applied upon a successful event outcome, meaning the\n            the attempt to resolve it was successful.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), 'failure_loots': TunableList(description='\n            Loots that will be applied upon a failed event outcome, meaning the attempt \n            to resolve it was not successful.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), 'lapsed_loots': TunableList(description='\n            Loots that will be applied if the event times out, meaning there was no \n            attempt to resolve the issue.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), 'fallback_loots': TunableList(description='\n            If this event ends while the receiver household is inactive, these loots will\n            be applied by the MultiUnitEventService once the household is active again.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), 'loots_on_schedule': TunableList(description='\n            Loots that will be applied once this drama node is scheduled, meaning this\n            event is now active on a rental unit.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'unit_zone_modifiers': TunableList(description='\n            A list of lot traits that may be applied if a Property Owner or Tenant of a\n            rental unit loads into that zone, while the event for this unit is active.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), class_restrictions=('ZoneModifier',), pack_safe=True)), 'common_area_event': Tunable(description='\n            When this flag is set to True, this event applies to the common area of the\n            unit rather than the unit itself.\n            ', tunable_type=bool, default=False), 'event_type': OptionalTunable(description='\n            If enabled, this represents the Multi Unit event type, and will be used to \n            connect APM and MULE drama nodes.\n            ', tunable=TunableEnumEntry(description='\n                The MultiUnitEventType enum representing the event type.\n                ', tunable_type=MultiUnitEventType, default=MultiUnitEventType.INVALID)), 'contractor_picker_data': OptionalTunable(description="\n            The data for hire a contractor picker. You only need to tune it if it's a emergency type event.\n            ", tunable=TunableTuple(name=TunableLocalizedString(description='\n                    The event display name in hire contractor picker. \n                    '), icon=TunableIcon(description='\n                    The event icon in hire contractor picker. \n                    '), inexperienced_contractor_cost=Tunable(description='\n                    The cost of simoleons to hire a inexperienced contractor.\n                    ', tunable_type=int, default=200), experienced_contractor_cost=Tunable(description='\n                    The cost of simoleons to hire a experienced contractor.\n                    ', tunable_type=int, default=400))), 'send_initial_outcome_telemetry': Tunable(description='\n            Whether or not telemetry should be sent for this event drama node when the outcome is first set.\n            ', tunable_type=bool, default=False), 'property_owner_event': Tunable(description='\n            If this flag is set to True, this event is treated as an autonomous property management node.\n            If this flag is set to False, this event is treated as a multi unit living events node.\n            ', tunable_type=bool, default=True), 'start_mu_situation': Tunable(description='\n            If this flag is set to True, then the Multi Unit Event Service will start the situation when\n            a tenant sim or property owner sim visits the rental unit.\n            ', tunable_type=bool, default=True), 'start_in_any_relevant_unit': Tunable(description='\n            If this flag is set to True and if the drama node has common_area_event set, if APM starts the\n            event on any rental unit on the current lot it will start the event in the current zone regardless\n            if the event belongs to the current unit or not.\n            ', tunable_type=bool, default=True)}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.MULTI_UNIT_EVENT

    @classproperty
    def simless(cls):
        return True

    @classproperty
    def is_property_owner_event(cls) -> 'bool':
        return cls.property_owner_event

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unit_zone_id = None
        self._unit_event_outcome = None
        self._receiver_household = None
        self._start_time = None
        self._cleanup_started = False

    def get_unit_zone_id(self) -> 'int':
        return self._unit_zone_id

    def get_unit_event_outcome(self) -> 'int':
        return self._unit_event_outcome

    def get_receiver_household(self) -> 'Household':
        return self._receiver_household

    def get_start_time(self) -> 'DateAndTime':
        return self._start_time

    def get_duration(self) -> 'TimeSpan':
        return self.selected_time - self._start_time

    def is_emergency_type_event(self) -> 'bool':
        return self.contractor_picker_data is not None

    def is_receiver_valid(self, receiver:'Any') -> 'bool':
        if isinstance(receiver, SimInfo):
            receiver = receiver.household
        if self.get_receiver_household() is receiver or self.get_unit_zone_id() == receiver:
            return True
        elif self.common_area_event and (services.owning_household_of_active_lot() is receiver or services.current_zone_id() == receiver):
            event_service = services.multi_unit_event_service()
            if event_service is not None:
                drama_node_id = event_service.get_multi_unit_zone_best_active_event(services.current_zone_id())
                if drama_node_id is not None and drama_node_id == self.uid:
                    return True
        return False

    def get_event_name(self) -> 'TunableLocalizedString':
        if self.contractor_picker_data is not None:
            return self.contractor_picker_data.name

    def get_icon(self) -> 'TunableIcon':
        if self.contractor_picker_data is not None:
            return self.contractor_picker_data.icon

    def get_contractor_costs(self) -> 'Tuple(int, int)':
        if self.contractor_picker_data is not None:
            return (self.contractor_picker_data.experienced_contractor_cost, self.contractor_picker_data.inexperienced_contractor_cost)
        return (0, 0)

    def set_unit_event_outcome(self, event_outcome) -> 'None':
        if self.send_initial_outcome_telemetry:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_MULTI_UNIT_EVENT_SET_OUTCOME) as hook:
                hook.write_int(TELEMETRY_FIELD_MULTI_UNIT_EVENT_TYPE, self.guid64)
                hook.write_int(TELEMETRY_FIELD_MULTI_UNIT_EVENT_DURATION, (services.time_service().sim_now - self._start_time).in_ticks())
        self._unit_event_outcome = event_outcome

    def _run(self):
        services.drama_scheduler_service().cancel_scheduled_node(self._uid)

    def _setup(self, resolver, gsi_data=None, **kwargs):
        result = super()._setup(resolver, gsi_data, **kwargs)
        if not result:
            return result
        try:
            unit_zone_id = resolver.get_participant(ParticipantType.PickedZoneId)
            if unit_zone_id is not None:
                self._unit_zone_id = unit_zone_id
            else:
                target_zone = resolver.get_participant(ParticipantType.TargetSimZoneId)
                if target_zone:
                    self._unit_zone_id = target_zone
                else:
                    self._unit_zone_id = services.current_zone_id()
        except ValueError:
            if gsi_data is not None:
                gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), "Failed to setup drama node because it couldn't find _unit_zone_id from participant {}", self.receiver_sim))
            return False
        self._receiver_household = resolver.get_participant(self.receiver_sim)
        if self._receiver_household is None:
            if gsi_data is not None:
                gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), "Failed to setup drama node because it couldn't find _receiver household from participant {}", self.receiver_sim))
            return False
        if isinstance(self._receiver_household, int):
            self._receiver_household = services.household_manager().get(self._receiver_household)
        return True

    def on_scheduled(self):
        event_service = services.multi_unit_event_service()
        self._start_time = services.time_service().sim_now
        if self.is_property_owner_event:
            event_service.add_property_owner_active_event(self._unit_zone_id, self)
        else:
            event_service.add_multi_unit_active_event(self._unit_zone_id, self)

    def _test(self, resolver, skip_run_tests=False):
        if self._receiver_household is None:
            return TestResult(False, 'Cannot run because there is no receiver household.')
        if self._unit_zone_id is None:
            return TestResult(False, 'Cannot run because there is no rental unit zone id.')
        result = services.multi_unit_event_service().can_start_event(self._unit_zone_id, self)
        if not result:
            return result
        result = super()._test(resolver, skip_run_tests=skip_run_tests)
        if not result:
            return result
        return TestResult.TRUE

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO, **kwargs):
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier, **kwargs)
        if success:
            for loot in self.loots_on_schedule:
                loot.apply_to_resolver(resolver)
        return success

    def cleanup(self, from_service_stop=False):
        self._cleanup_started = True
        if not from_service_stop:
            event_service = services.multi_unit_event_service()
            if services.active_household_id() == self._receiver_household.id:
                resolver = self._get_resolver()
                loots_to_apply = self.lapsed_loots
                if self._unit_event_outcome == MultiUnitEventOutcome.SUCCESS:
                    loots_to_apply = self.success_loots
                elif self._unit_event_outcome == MultiUnitEventOutcome.FAILURE:
                    loots_to_apply = self.failure_loots
                for loot in loots_to_apply:
                    loot.apply_to_resolver(resolver)
            else:
                event_service.add_completed_inactive_event_data(self._receiver_household.id, self._unit_zone_id, self.guid64)
            if self.is_property_owner_event or services.current_zone_id() != self._unit_zone_id:
                event_service.add_completed_inactive_event_data(UNIT_ZONE_REQUIRES_MODIFIER_CLEANUP_MARKER, self._unit_zone_id, self.guid64)
            if self.is_property_owner_event:
                event_service.remove_property_owner_active_event(self._unit_zone_id)
            else:
                event_service.remove_multi_unit_active_event(self._unit_zone_id, self)
            drama_scheduler = services.drama_scheduler_service()
            for node in drama_scheduler.get_scheduled_nodes_by_drama_node_type(DramaNodeType.MULTI_UNIT_EVENT):
                if node.event_type == self.event_type and (node.get_unit_zone_id() == self._unit_zone_id and node.uid != self.uid) and not node._cleanup_started:
                    node.set_unit_event_outcome(self._unit_event_outcome)
                    drama_scheduler.cancel_scheduled_node(node.uid)
                    break
        self._unit_zone_id = None
        self._unit_event_outcome = None
        self._receiver_household = None
        super().cleanup(from_service_stop=from_service_stop)

    def _get_resolver(self) -> 'Resolver':
        resolver = services.multi_unit_event_service().get_resolver(self._unit_zone_id)
        random_zone_id = None
        neighbor_unit_zone_ids = set(services.get_plex_service().get_plex_zones_in_group(self._unit_zone_id))
        neighbor_unit_zone_ids.discard(self._unit_zone_id)
        if neighbor_unit_zone_ids:
            random_zone_id = random.choice(tuple(neighbor_unit_zone_ids))
        if random_zone_id:
            resolver.set_additional_participant(ParticipantType.RandomZoneId, (random_zone_id,))
        all_unit_zone_ids = set(services.get_plex_service().get_plex_zones_in_group(self._unit_zone_id))
        if all_unit_zone_ids:
            resolver.set_additional_participant(ParticipantType.AllUnitZoneIds, all_unit_zone_ids)
        return resolver

    def _save_custom_data(self, writer):
        if self._unit_zone_id is not None:
            writer.write_uint64(UNIT_ZONE_ID_TOKEN, self._unit_zone_id)
        if self._unit_event_outcome is not None:
            writer.write_uint32(UNIT_EVENT_OUTCOME_TOKEN, self._unit_event_outcome)
        if self._receiver_household is not None:
            writer.write_uint64(RECEIVER_HOUSEHOLD_ID_TOKEN, self._receiver_household.id)
        if self._start_time is not None:
            writer.write_uint64(START_TIME_TOKEN, int(self._start_time))

    def _load_custom_data(self, reader):
        self._unit_zone_id = reader.read_uint64(UNIT_ZONE_ID_TOKEN, None)
        self._unit_event_outcome = reader.read_uint32(UNIT_EVENT_OUTCOME_TOKEN, None)
        household_id = reader.read_uint64(RECEIVER_HOUSEHOLD_ID_TOKEN, None)
        if household_id is not None:
            self._receiver_household = services.household_manager().get(household_id)
        start_time = reader.read_uint64(START_TIME_TOKEN, None)
        if start_time is not None:
            self._start_time = DateAndTime(start_time)
        return True

    def _run_situation(self, run_from_external:'bool'=False, duration_override:'Optional[TimeSpan]'=None, **extra_kwargs) -> 'bool':
        if run_from_external:
            if duration_override is None:
                duration_override = self.get_time_remaining()
            result = super()._run_situation(duration_override=duration_override, start_time_override=self._start_time, drama_node_id=self.uid, **extra_kwargs)
            return result
        return False

    def run_situation(self):
        if self.start_mu_situation:
            return self._run_situation(run_from_external=True)
        return False

    def end_situation(self):
        if self.situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            situation = situation_manager.get(self.situation_id)
            if situation is not None:
                situation._self_destruct()
            self.situation_id = None
