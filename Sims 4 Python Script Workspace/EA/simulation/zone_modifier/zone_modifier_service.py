import randomfrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom event_testing.test_events import TestEventfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom zone_modifier.zone_modifier import ZoneModifierWeeklySchedulefrom zone_modifier.zone_modifier_display_info import ZoneModifierDisplayInfoimport alarmsimport servicesimport sims4.telemetryimport telemetry_helperTELEMETRY_GROUP_LOT_TRAITS = 'LTRT'TELEMETRY_HOOK_ADD_TRAIT = 'TADD'TELEMETRY_HOOK_REMOVE_TRAIT = 'TRMV'TELEMETRY_FIELD_TRAIT_ID = 'idtr'TELEMETRY_FIELD_LOT_DESCRIPTION_ID = 'hlid'TELEMETRY_FIELD_TRAIT_LIST = 'tlst'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_LOT_TRAITS)
class ZoneModifierService(Service):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_id_to_modifier_cache = dict()
        self._scheduler = None
        self._action_alarm_handles = set()
        self._zone_mod_spin_up_state_complete = False
        self._is_build_eco_effects_enabled = True

    @property
    def is_build_eco_effects_enabled(self):
        return self._is_build_eco_effects_enabled

    def on_client_connect(self, client):
        services.get_event_manager().register_single_event(self, TestEvent.SimActiveLotStatusChanged)
        self._run_start_actions()
        self._setup_zone_modifier_schedules()

    def spin_up(self):
        self._run_spin_up_actions()
        self._zone_mod_spin_up_state_complete = True

    def start(self):
        services.venue_service().on_venue_type_changed.register(self._handle_venue_type_changed)
        return super().start()

    def stop(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.SimActiveLotStatusChanged)
        services.venue_service().on_venue_type_changed.unregister(self._handle_venue_type_changed)
        self._run_stop_actions()
        self._clear_action_alarms()
        if self._scheduler is not None:
            self._scheduler.destroy()

    def on_all_households_and_sim_infos_loaded(self, *args):
        zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
        for zone_modifier in zone_modifiers:
            zone_modifier.start_household_actions()

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SimActiveLotStatusChanged:
            loot_resolver = SingleSimResolver(sim_info)
            sim_on_lot = resolver.get_resolved_arg('on_active_lot')
            zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
            for zone_modifier in zone_modifiers:
                if self._zone_mod_spin_up_state_complete or zone_modifier.ignore_route_events_during_zone_spin_up:
                    pass
                else:
                    loot_list = zone_modifier.enter_lot_loot if sim_on_lot else zone_modifier.exit_lot_loot
                    for loot in loot_list:
                        loot.apply_to_resolver(loot_resolver)

    def _handle_venue_type_changed(self):
        persistence_service = services.get_persistence_service()
        zone_id = services.current_zone_id()
        active_venue = services.venue_service().active_venue
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        neighborhood_data = persistence_service.get_neighborhood_proto_buf_from_zone_id(zone_id)
        for lot_data in neighborhood_data.lots:
            if zone_id != lot_data.zone_instance_id:
                pass
            else:
                lot_data.venue_key = active_venue.guid64
                if lot_data.sub_venue_infos:
                    for sub_venue_info in lot_data.sub_venue_infos:
                        if sub_venue_info.sub_venue_key == lot_data.venue_key:
                            lot_data.venue_eligible = sub_venue_info.sub_venue_eligible
                            zone_data.ClearField('lot_traits')
                            for trait in sub_venue_info.sub_venue_lot_traits:
                                zone_data.lot_traits.append(trait)
        self.check_for_and_apply_new_zone_modifiers(zone_id)

    def check_for_and_apply_new_zone_modifiers(self, zone_id):
        cached_zone_modifiers = self.get_zone_modifiers(zone_id, force_cache=True)
        zone_modifiers_update = self.get_zone_modifiers(zone_id, force_refresh=True)
        if zone_id != services.current_zone_id():
            return
        for modifier in zone_modifiers_update:
            modifier.apply_object_actions(self._is_build_eco_effects_enabled)
        removed_modifiers = cached_zone_modifiers - zone_modifiers_update
        added_modifiers = zone_modifiers_update - cached_zone_modifiers
        if removed_modifiers or not added_modifiers:
            return
        if self._scheduler is not None:
            for schedule_entry in self._scheduler:
                data = schedule_entry.entry
                if data.execute_on_removal and data.zone_modifier in removed_modifiers:
                    self._on_scheduled_alarm(None, schedule_entry, None)
        instanced_sims = frozenset(services.sim_info_manager().instanced_sims_on_active_lot_gen(include_spawn_point=True))
        for sim in instanced_sims:
            loot_resolver = SingleSimResolver(sim.sim_info)
            loots_to_apply = set()
            for removed_modifier in removed_modifiers:
                loots_to_apply.update(removed_modifier.exit_lot_loot)
            for added_modifier in added_modifiers:
                loots_to_apply.update(added_modifier.enter_lot_loot)
            for loot in loots_to_apply:
                loot.apply_to_resolver(loot_resolver)
        for removed_modifier in removed_modifiers:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_REMOVE_TRAIT) as hook:
                hook.write_int(TELEMETRY_FIELD_TRAIT_ID, removed_modifier.guid64)
                hook.write_guid(TELEMETRY_FIELD_LOT_DESCRIPTION_ID, services.get_persistence_service().get_lot_id_from_zone_id(zone_id))
            removed_modifier.on_remove_actions()
        for added_modifier in added_modifiers:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ADD_TRAIT) as hook:
                hook.write_int(TELEMETRY_FIELD_TRAIT_ID, added_modifier.guid64)
                hook.write_guid(TELEMETRY_FIELD_LOT_DESCRIPTION_ID, services.get_persistence_service().get_lot_id_from_zone_id(zone_id))
                unlocked_trait_ids = [trait.guid64 for trait in zone_modifiers_update if trait.zone_modifier_locked or not trait.guid64 == added_modifier.guid64]
                unlocked_trait_ids.sort()
                hook.write_string(TELEMETRY_FIELD_TRAIT_LIST, '_'.join([str(id) for id in unlocked_trait_ids]))
            added_modifier.on_add_actions(self._is_build_eco_effects_enabled)
        self._setup_zone_modifier_schedules()

    def set_build_eco_effects_enabled(self, enabled):
        if self._is_build_eco_effects_enabled == enabled:
            return
        self._is_build_eco_effects_enabled = enabled
        zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
        for zone_modifier in zone_modifiers:
            if self._is_build_eco_effects_enabled:
                zone_modifier.apply_object_actions(self._is_build_eco_effects_enabled)
            else:
                zone_modifier.revert_object_actions()

    def get_zone_modifiers(self, zone_id, force_refresh=False, force_cache=False):
        zone_modifiers = None if force_refresh else self._zone_id_to_modifier_cache.get(zone_id, None)
        if zone_modifiers is not None:
            return zone_modifiers
        if force_cache:
            return frozenset()
        zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
        zone_modifiers = self._get_zone_modifiers_from_zone_data(zone_data)
        venue_zone_modifiers = services.venue_service().get_additional_zone_modifiers(zone_id)
        zone_modifiers.update(venue_zone_modifiers)
        situation_manager = services.get_zone_situation_manager()
        situation_zone_modifiers = situation_manager.get_additional_zone_modifiers()
        zone_modifiers.update(situation_zone_modifiers)
        dust_service = services.dust_service()
        if dust_service is not None:
            zone_modifiers.update(dust_service.get_zone_modifiers())
        obj_manager = services.object_manager()
        zone_modifiers.update(obj_manager.get_object_provided_zone_modifiers())
        event_service = services.multi_unit_event_service()
        if event_service is not None:
            zone_modifiers.update(event_service.get_additional_zone_modifiers(zone_id))
        self._zone_id_to_modifier_cache[zone_id] = zone_modifiers
        return zone_modifiers

    def is_situation_prohibited(self, zone_id, situation_type):
        return any(zone_modifier.is_situation_prohibited(situation_type) for zone_modifier in self.get_zone_modifiers(zone_id))

    def _get_zone_modifiers_from_zone_data(self, zone_data=None):
        if zone_data is None:
            return set()
        return self._get_zone_modifiers_from_lot_traits_msg(zone_data.lot_traits)

    def _get_zone_modifiers_from_lot_traits_msg(self, lot_traits_msg):
        zone_modifiers = set()
        mgr = services.get_instance_manager(Types.ZONE_MODIFIER)
        for trait_guid in lot_traits_msg:
            trait = mgr.get(trait_guid)
            if trait is not None:
                zone_modifiers.add(trait)
        return zone_modifiers

    def get_zone_modifier_display_infos(self, zone_id):
        display_infos = set()
        zone_modifiers = self.get_zone_modifiers(zone_id)
        for modifier in zone_modifiers:
            if not modifier.hide_screen_slam:
                display_infos.add(self._get_display_info_for_zone_modifier(modifier))
        return display_infos

    def _get_display_info_for_zone_modifier(self, zone_modifier):
        ui_info_manager = services.get_instance_manager(Types.USER_INTERFACE_INFO)
        for display_info in ui_info_manager.get_ordered_types(only_subclasses_of=ZoneModifierDisplayInfo):
            if display_info.zone_modifier_reference is zone_modifier:
                return display_info

    def _on_scheduled_alarm(self, scheduler, alarm_data, extra_data):
        if random.random() >= alarm_data.entry.chance:
            return
        resolver = GlobalResolver()
        if not alarm_data.entry.tests.run_tests(resolver):
            return
        for action in alarm_data.entry.actions:
            action.perform()
        continuation_actions = alarm_data.entry.continuation_actions
        for continuation in continuation_actions:
            continuation.perform_action()

    def _run_start_actions(self):
        zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
        for zone_modifier in zone_modifiers:
            zone_modifier.on_start_actions()

    def _run_spin_up_actions(self):
        zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
        for zone_modifier in zone_modifiers:
            zone_modifier.on_spin_up_actions(self._is_build_eco_effects_enabled)

    def _run_stop_actions(self):
        zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
        for zone_modifier in zone_modifiers:
            zone_modifier.on_stop_actions()

    def run_zone_modifier_schedule_entry(self, schedule_entry):
        for action in schedule_entry.actions:
            action.perform()
        continuation_actions = schedule_entry.continuation_actions
        for continuation in continuation_actions:
            continuation.perform_action()

    def _setup_zone_modifier_schedules(self):
        if self._scheduler is not None:
            self._scheduler.destroy()
        self._scheduler = ZoneModifierWeeklySchedule([], init_only=True, start_callback=self._on_scheduled_alarm)
        zone_modifiers = self.get_zone_modifiers(services.current_zone_id())
        for zone_modifier in zone_modifiers:
            self._scheduler.merge_schedule(zone_modifier.schedule(init_only=True))
        self._scheduler.schedule_next_alarm()

    def create_action_alarm(self, alarm_time, callback):

        def callback_wrapper(handle):
            self._action_alarm_handles.discard(handle)
            callback()

        handle = alarms.add_alarm(self, alarm_time, callback_wrapper)
        self._action_alarm_handles.add(handle)

    def cancel_action_alarm(self, handle):
        self._action_alarm_handles.discard(handle)
        handle.cancel()

    def _clear_action_alarms(self):
        for handle in self._action_alarm_handles:
            handle.cancel()
        self._action_alarm_handles.clear()

    def save_options(self, options_proto):
        options_proto.build_eco_effects_enabled = self._is_build_eco_effects_enabled

    def load_options(self, options_proto):
        self._is_build_eco_effects_enabled = options_proto.build_eco_effects_enabled
