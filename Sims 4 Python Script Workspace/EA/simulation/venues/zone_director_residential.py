from business.business_enums import BusinessTypefrom business.small_business_zone_director_mixin import SmallBusinessZoneDirectorMixinfrom date_and_time import DateAndTimefrom objects import ALL_HIDDEN_REASONSfrom plex.plex_enums import PlexBuildingTypefrom sims.sim_info_types import Age, Speciesfrom sims4.tuning.tunable import OptionalTunable, TunableReference, TunablePackSafeReferencefrom situations.situation_types import GreetedStatusfrom venues.scheduling_zone_director import SchedulingZoneDirectorfrom venues.venue_enums import VenueTypesfrom world import regionfrom zone_director import _ZoneSavedSimOp, _OpenStreetSavedSimOpimport alarmsimport servicesimport simsimport sims4SUPPORTED_BUSINESS_TYPES = (BusinessType.RENTAL_UNIT, BusinessType.SMALL_BUSINESS)logger = sims4.log.Logger('ZoneDirector')
class ZoneDirectorResidentialSwitch(SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'player': TunableReference(description='\n            The residential ZoneDirector type for lots owned by the active household.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',)), 'npc': TunableReference(description='\n            The residential ZoneDirector type for lots owned by an NPC household.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',)), 'apartment_player': OptionalTunable(description='\n            If enabled and the zone is an apartment, this zone director will be\n            invoked if the active zone is owned by the active household.\n            ', tunable=TunablePackSafeReference(description='\n                The residential ZoneDirector type for apartments owned by the active household.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',))), 'apartment_npc': OptionalTunable(description='\n            If enabled and the zone is an apartment, this zone director will be\n            invoked if the active zone is owned by an NPC household.\n            ', tunable=TunablePackSafeReference(description='\n                The residential ZoneDirector type for apartments owned by an NPC household.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',))), 'penthouse_player': OptionalTunable(description='\n            If enabled and the zone is a penthouse, this zone director will be\n            invoked if the active zone is owned by the active household.\n            ', tunable=TunablePackSafeReference(description='\n                The residential ZoneDirector type for penthouses owned by the active household.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',))), 'penthouse_npc': OptionalTunable(description='\n            If enabled and the zone is a penthouse, this zone director will be\n            invoked if the active zone is owned by an NPC household.\n            ', tunable=TunablePackSafeReference(description='\n                The residential ZoneDirector type for penthouses owned by an NPC household.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',)))}

    @staticmethod
    def get_residential_zone_director_type(zone_id, residence_zone_director, apartment_zone_director, penthouse_zone_director, *args, **kwargs):
        plex_service = services.get_plex_service()
        if penthouse_zone_director is not None and plex_service.get_plex_building_type(zone_id) == PlexBuildingType.PENTHOUSE_PLEX:
            return penthouse_zone_director(*args, **kwargs)
        if apartment_zone_director is not None and plex_service.is_zone_a_plex(zone_id):
            return apartment_zone_director(*args, **kwargs)
        return residence_zone_director(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        active_household = services.active_household()
        logger.assert_log(active_household is not None, 'Cannot determine zone director if active household is None.')
        zone_id = services.current_zone_id()
        if ZoneDirectorResidentialSwitch.player_in_unoccupied_owned_rental_residential_zone(zone_id, active_household.id) or active_household.considers_current_zone_its_residence():
            return ZoneDirectorResidentialSwitch.get_residential_zone_director_type(zone_id, cls.player, cls.apartment_player, cls.penthouse_player)
        else:
            return ZoneDirectorResidentialSwitch.get_residential_zone_director_type(zone_id, cls.npc, cls.apartment_npc, cls.penthouse_npc)

    @staticmethod
    def player_in_unoccupied_owned_rental_residential_zone(zone_id:int, active_household_id:int) -> bool:
        business_tracker = services.business_service().get_business_tracker_for_household(active_household_id, BusinessType.RENTAL_UNIT)
        if not business_tracker:
            return False
        else:
            current_business_manager = business_tracker.get_business_manager_for_zone(zone_id)
            if current_business_manager and (current_business_manager.owner_household_id != active_household_id or current_business_manager.is_open):
                return False
        return True

class ZoneDirectorResidentialBase(SmallBusinessZoneDirectorMixin, SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'front_door_call_to_action': OptionalTunable(description='\n            Optional Call to action to use to highlight the front door of the residential.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION)))}

    def __init__(self):
        super().__init__()
        self._return_sim_to_home_lot_alarm_handles = set()
        self._has_cta_been_seen = False
        self._cta_disabled = False

    @property
    def supported_business_types(self):
        return SUPPORTED_BUSINESS_TYPES

    def on_shutdown(self):
        self._clear_return_sim_to_home_lot_alarm_handles()
        self._turn_off_front_door_call_to_action()
        return super().on_shutdown()

    def _clear_return_sim_to_home_lot_alarm_handles(self):
        for alarm_handle in self._return_sim_to_home_lot_alarm_handles:
            alarms.cancel_alarm(alarm_handle)
        self._return_sim_to_home_lot_alarm_handles.clear()

    def _process_resident_sim(self, sim_info):
        current_zone = services.current_zone()
        if current_zone.lot_owner_household_changed_between_save_and_load():
            if sim_info.is_selectable:
                spin_up_action = sims.sim_info_types.SimZoneSpinUpAction.NONE
            else:
                spin_up_action = sims.sim_info_types.SimZoneSpinUpAction.PREROLL
            self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=spin_up_action)
            return
        if sim_info in self._injected_into_zone_sim_infos:
            self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.PREROLL)
            return
        if sim_info in self._zone_saved_sim_infos:
            zone_op = self._zone_saved_sim_op
            if zone_op == _ZoneSavedSimOp.MAINTAIN:
                self._on_maintain_zone_saved_resident_sim(sim_info)
            elif zone_op == _ZoneSavedSimOp.REINITIATE:
                if sim_info.career_tracker is not None:
                    career = sim_info.career_tracker.get_at_work_career()
                    if career is not None and (career.is_at_active_event or sim_info.sim_info.zone_id == current_zone.id):
                        self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER)
                        return
                self._on_reinitiate_zone_saved_resident_sim(sim_info)
            elif zone_op == _ZoneSavedSimOp.CLEAR:
                self._on_clear_zone_saved_residential_sim(sim_info)
            return
        if sim_info in self._open_street_saved_sim_infos:
            if self._open_street_saved_sim_op == _OpenStreetSavedSimOp.CLEAR:
                self._on_clear_open_street_saved_resident_sim(sim_info)
            elif self._open_street_saved_sim_op == _OpenStreetSavedSimOp.MAINTAIN:
                self._on_maintain_open_street_saved_resident_sim(sim_info)
            return
        self._bring_home_resident_if_overdue(sim_info)

    def _bring_home_resident_if_overdue(self, sim_info):
        current_zone = services.current_zone()
        if sim_info.zone_id == current_zone.id:
            return
        if sim_info.is_pet and not any(household_sim_info.is_human and (household_sim_info.is_child_or_older and sim_info.zone_id == household_sim_info.zone_id) for household_sim_info in sim_info.household.sim_info_gen()):
            self._bring_sim_home(sim_info)
            return
        if sim_info.species != Species.HUMAN or sim_info.age < Age.CHILD:
            business_manager = services.business_service().get_business_manager_for_zone(zone_id=sim_info.zone_id)
            if business_manager and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                for household_sim_info in sim_info.household.sim_info_gen():
                    if household_sim_info.zone_id == sim_info.zone_id and household_sim_info.species == Species.HUMAN and household_sim_info.age > Age.CHILD:
                        break
                self._bring_sim_home(sim_info)
                return
        current_region = current_zone.region
        sim_region = region.get_region_instance_from_zone_id(sim_info.zone_id)
        if sim_region is not None and not sim_region.is_region_compatible(current_region):
            return
        travel_group = sim_info.travel_group
        if travel_group is not None and travel_group.zone_id != current_zone.id:
            return
        if sim_info.career_tracker is None:
            logger.error('Career Tracker for resident Sim {} is unexpectedly None.'.format(sim_info))
        else:
            career = sim_info.career_tracker.get_at_work_career()
            if career is not None and career.is_at_active_event:
                return
        if services.hidden_sim_service().is_hidden(sim_info.id):
            return
        if sim_info.zone_id == 0 or sim_info.game_time_bring_home is None:
            self._bring_sim_home(sim_info)
            return
        bring_home_time = DateAndTime(sim_info.game_time_bring_home)
        current_time = services.time_service().sim_now
        if current_time >= bring_home_time:
            self._bring_sim_home(sim_info)
        else:
            time_till_spawn = bring_home_time - current_time
            self._return_sim_to_home_lot_alarm_handles.add(alarms.add_alarm(sim_info, time_till_spawn, self._return_sim_to_current_lot))

    def _bring_sim_home(self, sim_info):
        self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.PREROLL)

    def _return_sim_to_current_lot(self, alarm_handle):
        self._return_sim_to_home_lot_alarm_handles.discard(alarm_handle)
        sim_info = alarm_handle.owner
        if sim_info is None or sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            return
        self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER)

    def _on_maintain_zone_saved_resident_sim(self, sim_info):
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.RESTORE_SI)

    def _on_reinitiate_zone_saved_resident_sim(self, sim_info):
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.PREROLL)

    def _on_clear_zone_saved_residential_sim(self, sim_info):
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.PREROLL)

    def _on_maintain_open_street_saved_resident_sim(self, sim_info):
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.RESTORE_SI)

    def _on_clear_open_street_saved_resident_sim(self, sim_info):
        self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.PREROLL)

    def on_loading_screen_animation_finished(self):
        super().on_loading_screen_animation_finished()
        if self.front_door_call_to_action is not None:
            self._trigger_front_door_call_to_action()

    def _trigger_front_door_call_to_action(self):
        if services.current_zone().active_household_changed_between_save_and_load() or services.current_zone().time_has_passed_in_world_since_zone_save():
            self._cta_disabled = False
        if self._cta_disabled:
            return
        if self._has_cta_been_seen:
            return
        if services.get_zone_situation_manager().is_player_greeted():
            return
        target_household_id = services.get_persistence_service().get_household_id_from_zone_id(services.current_zone().id)
        if target_household_id is None or target_household_id == 0:
            return
        services.call_to_action_service().begin(self.front_door_call_to_action, self)
        self._has_cta_been_seen = True

    def _turn_off_front_door_call_to_action(self) -> None:
        if self.front_door_call_to_action is None:
            return
        call_to_action_service = services.call_to_action_service()
        if call_to_action_service is not None and call_to_action_service.is_call_to_action_active(self.front_door_call_to_action):
            call_to_action_service.end(self.front_door_call_to_action)

    def on_cta_ended(self, value):
        self._cta_disabled = True

    def _get_lot_owner_household_sims(self):
        active_household = services.current_zone().get_active_lot_owner_household()
        if active_household is None:
            return set()
        return set(active_household.sim_info_gen())

    def _get_travel_group_sims(self):
        current_zone = services.current_zone()
        travel_group_manager = services.travel_group_manager()
        travel_group = travel_group_manager.get_travel_group_by_zone_id(current_zone.id)
        if travel_group is None:
            return set()
        return {sim_info for sim_info in travel_group.sim_info_gen()}

    def _create_player_greeting_related_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        situation_manager = services.get_zone_situation_manager()
        cur_status = GreetedStatus.WAITING_TO_BE_GREETED
        lot_seeds = situation_manager.get_zone_persisted_seeds_during_zone_spin_up()
        arriving_seed = situation_manager.get_arriving_seed_during_zone_spin()
        if arriving_seed is not None:
            lot_seeds.append(arriving_seed)
        for seed in lot_seeds:
            status = seed.get_player_greeted_status()
            logger.debug('Player:{} :{}', status, seed.situation_type, owner='sscholl')
            if status == GreetedStatus.GREETED:
                cur_status = status
                break
        if self._is_any_sim_always_greeted() or self.should_auto_greeted():
            cur_status = GreetedStatus.GREETED
        if cur_status == GreetedStatus.WAITING_TO_BE_GREETED:
            situation_manager.make_player_waiting_to_be_greeted_during_zone_spin_up()
        elif cur_status == GreetedStatus.GREETED:
            situation_manager.make_player_greeted_during_zone_spin_up()

    def _is_any_sim_always_greeted(self):
        active_household = services.current_zone().get_active_lot_owner_household()
        if active_household is not None:
            for sim_info in self._traveled_sim_infos:
                if sim_info.id in active_household.always_welcomed_sims:
                    return True
        return False

    def should_auto_greeted(self):
        current_zone_plex_type = services.get_plex_service().get_plex_building_type(services.current_zone_id())
        front_door = services.get_door_service().get_front_door()
        if front_door is None and current_zone_plex_type == PlexBuildingType.BT_MULTI_UNIT:
            return True
        business_manager = services.business_service().get_business_manager_for_zone()
        return business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS

    def _should_create_npc_business_manager(self):
        plex_service = services.get_plex_service()
        if plex_service is None:
            return False
        return plex_service.is_zone_a_multi_unit(services.current_zone_id())

    def _get_new_npc_business_manager(self):
        return services.business_service().add_unowned_business(BusinessType.RENTAL_UNIT, services.current_zone_id())

class ZoneDirectorResidentialPlayer(ZoneDirectorResidentialBase):

    def _get_resident_sims(self):
        return self._get_lot_owner_household_sims()

    def _process_resident_sim(self, sim_info):
        current_zone = services.current_zone()
        travel_group = sim_info.travel_group
        sim_info_in_played_travel_group = travel_group.played if travel_group is not None else False
        if current_zone.is_first_visit_to_zone or not (sim_info.household.is_first_time_playing() and sim_info_in_played_travel_group):
            self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER)
            return
        super()._process_resident_sim(sim_info)

class ZoneDirectorResidentialNPC(ZoneDirectorResidentialBase):

    def on_shutdown(self):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            situation_manager.destroy_player_waiting_to_be_greeted_situation()
        super().on_shutdown()

    def _get_resident_sims(self):
        return self._get_lot_owner_household_sims()

    def create_greeted_related_situations_during_zone_spin_up(self):
        super().create_greeted_related_situations_during_zone_spin_up()
        self._create_player_greeting_related_situations_during_zone_spin_up()

class ZoneDirectorRentablePlayer(ZoneDirectorResidentialBase):
    INSTANCE_TUNABLES = {'situation_to_create_on_travel_group_changed': OptionalTunable(description='\n                If enabled then when the zone loads, if the travel group\n                changed then we will create this situation as a non-user facing\n                situation.\n                ', tunable=TunableReference(description='\n                    The situation that will be created as a non-user facing\n                    situation when the zone loads and the situation\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)))}

    def _get_resident_sims(self):
        return self._get_travel_group_sims()

    def _process_resident_sim(self, sim_info):
        current_zone = services.current_zone()
        if current_zone.is_first_visit_to_zone or current_zone.travel_group_changed_between_save_and_load():
            self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.LOT_OWNER)
            return
        super()._process_resident_sim(sim_info)

    def _on_reinitiate_zone_saved_sim(self, sim_info):
        if services.current_zone().travel_group_changed_between_save_and_load():
            return
        super()._on_reinitiate_zone_saved_sim(sim_info)

    def _on_maintain_zone_saved_sim(self, sim_info):
        if services.current_zone().travel_group_changed_between_save_and_load():
            return
        super()._on_maintain_zone_saved_sim(sim_info)

    def _on_maintain_open_street_saved_sim(self, sim_info):
        if services.current_zone().travel_group_changed_between_save_and_load():
            return
        super()._on_maintain_open_street_saved_sim(sim_info)

    def _create_travel_group_changed_situation_if_nessesary(self):
        if self.situation_to_create_on_travel_group_changed is None:
            return
        current_zone = services.current_zone()
        if current_zone.is_first_visit_to_zone or not current_zone.travel_group_changed_between_save_and_load():
            return
        services.get_zone_situation_manager().create_situation(self.situation_to_create_on_travel_group_changed, user_facing=False, creation_source=self.instance_name)

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        self._create_travel_group_changed_situation_if_nessesary()

class ZoneDirectorRentableNPC(ZoneDirectorResidentialBase):

    def _get_resident_sims(self):
        return self._get_travel_group_sims()

    def create_greeted_related_situations_during_zone_spin_up(self):
        super().create_greeted_related_situations_during_zone_spin_up()
        self._create_player_greeting_related_situations_during_zone_spin_up()
