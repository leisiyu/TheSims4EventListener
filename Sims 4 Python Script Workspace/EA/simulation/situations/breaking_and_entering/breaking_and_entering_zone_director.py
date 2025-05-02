from __future__ import annotationsfrom clock import ClockSpeedModefrom distributor.system import Distributorfrom protocolbuffers.Consts_pb2 import MSG_TRAVEL_SIMS_TO_ZONEfrom protocolbuffers import InteractionOps_pb2from typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import Setimport servicesfrom sims.sim_info import SimInfofrom sims4.tuning.tunable import TunableReferencefrom situations.bouncer.bouncer_types import BouncerRequestPriority, RequestSpawningOptionfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCallbackOptionfrom venues.scheduling_zone_director import SchedulingZoneDirectorimport sims4.logfrom venues.venue_enums import VenueTypeslogger = sims4.log.Logger('Breaking&Entering ZoneDirector', default_owner='cparrish')
class BreakingAndEnteringZoneDirector(SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'resident_return_situation': TunableReference(description='\n            The situation we want resident sims to run when the time is right.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True), 'break_in_zone_buff': TunableReference(description='\n            The buff applied to all sims who are part of a group that initiated a\n            Break In Situation. Only active while the sim is on the Break In lot\n            after the PlayerGroup Break In situation has completed.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True)}
    HOST_SIM_INFO = '_host_sim_info'
    BREAK_IN_SIMS = '_break_in_sims'
    BREAKIN_FINISHED = 'break_in_finished'

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._should_load_sims = False
        self._host_sim_info = None
        self._break_in_sims = {}
        self.break_in_finished = False

    def _save_custom_zone_director(self, zone_director_proto, writer):
        writer.write_uint64s(self.BREAK_IN_SIMS, [sim_info.sim_id for sim_info in self._break_in_sims])
        writer.write_uint64(self.HOST_SIM_INFO, self._host_sim_info.sim_id)
        writer.write_bool(self.BREAKIN_FINISHED, self.break_in_finished)

    def _load_custom_zone_director(self, zone_director_proto, reader) -> 'None':
        self._should_load_sims = True
        if reader is not None:
            sim_info_manager = services.sim_info_manager()
            break_in_sim_ids = reader.read_uint64s(self.BREAK_IN_SIMS, {})
            self._break_in_sims = {sim_info_manager.get(sim_id) for sim_id in break_in_sim_ids}
            self._host_sim_info = sim_info_manager.get(reader.read_uint64(self.HOST_SIM_INFO, None))
            self.break_in_finished = reader.read_bool(self.BREAKIN_FINISHED, False)
        if self.break_in_finished:
            self.add_restrictive_buff()
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _process_zone_saved_sim(self, sim_info) -> 'None':
        user_controlled_sim_infos = self.get_user_controlled_sim_infos()
        if self._should_load_sims or sim_info in user_controlled_sim_infos:
            super()._on_maintain_zone_saved_sim(sim_info)
        else:
            logger.info('Discarding saved sim: {}', sim_info)

    def _process_open_street_saved_sim(self, sim_info) -> 'None':
        resident_sims = self._get_resident_sims()
        if self._should_load_sims or sim_info not in resident_sims:
            super()._process_open_street_saved_sim(sim_info)
        else:
            logger.info('Discarding open street saved sim: {}', sim_info)

    def _process_injected_sim(self, sim_info) -> 'None':
        logger.info('Discarding injected sim: {}', sim_info)

    def _get_resident_sims(self) -> 'Set[SimInfo]':
        current_zone = services.current_zone()
        venue_type = services.venue_service().active_venue.venue_type
        if venue_type == VenueTypes.RESIDENTIAL or venue_type == VenueTypes.MULTI_UNIT:
            active_household = current_zone.get_active_lot_owner_household()
            if active_household is not None:
                return set(active_household.sim_info_gen())
        elif venue_type == VenueTypes.RENTAL:
            travel_group_manager = services.travel_group_manager()
            travel_group = travel_group_manager.get_travel_group_by_zone_id(current_zone.id)
            if travel_group is not None:
                return set(travel_group.sim_info_gen())
        return set()

    def save_break_in_group(self, guest_list:'SituationGuestList') -> 'None':
        self._host_sim_info = guest_list.host_sim_info
        self._break_in_sims = {sim_info for sim_info in guest_list.invited_sim_infos_gen()}

    def ensure_group_is_instanced(self) -> 'None':
        for sim in self._break_in_sims:
            if sim.is_selectable or not sim.is_instanced():
                self.handle_sim_summon_request(sim, None)

    def return_all_resident_sims(self, *_, **kwargs) -> 'None':
        household = services.owning_household_of_active_lot()
        zone_shutting_down = services.current_zone().is_zone_shutting_down
        for household_member in household:
            if not household_member.is_instanced():
                if zone_shutting_down or kwargs.get('from_early_exit'):
                    household_member.set_zone_on_spawn()
                else:
                    self.handle_sim_summon_request(household_member, None)

    def send_player_group_home(self) -> 'None':
        host_sim_zone_id = self._host_sim_info.vacation_or_home_zone_id
        travel_info = InteractionOps_pb2.TravelSimsToZone()
        travel_info.zone_id = host_sim_zone_id
        for sim_info in self._break_in_sims:
            if sim_info.household.id == self._host_sim_info.household.id:
                travel_info.sim_ids.append(sim_info.sim_id)
            else:
                sim_info.inject_into_inactive_zone(sim_info.zone_id, skip_instanced_check=True)
        Distributor.instance().add_event(MSG_TRAVEL_SIMS_TO_ZONE, travel_info)
        services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)

    def add_restrictive_buff(self) -> 'None':
        for sim_info in self._break_in_sims:
            sim_info.add_buff(self.break_in_zone_buff)

    def request_resident_return_situation(self) -> 'None':
        active_sim_info = services.active_sim_info()
        situation_manager = services.get_zone_situation_manager()
        household = services.owning_household_of_active_lot()
        host_sim_info = next(household.can_live_alone_info_gen())
        guest_list = SituationGuestList(invite_only=True, host_sim_id=host_sim_info.sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(host_sim_info.sim_id, self.resident_return_situation.resident_job(), RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        return_situation_id = situation_manager.create_situation(self.resident_return_situation, guest_list=guest_list, user_facing=False)
        situation_manager.register_for_callback(return_situation_id, SituationCallbackOption.END_OF_SITUATION, self.return_all_resident_sims)
