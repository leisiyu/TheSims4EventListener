from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfofrom _collections import dequefrom collections import namedtuplefrom date_and_time import TimeSpanfrom random import Randomimport mathimport randomfrom date_and_time import create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import GlobalResolverfrom protocolbuffers import GameplaySaveData_pb2from sims4.localization import LocalizationHelperTuningfrom sims4.math import MAX_UINT64from sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom ui.ui_dialog import ButtonTypefrom ui.ui_dialog_picker import SimPickerRowfrom world.region import get_region_instance_from_zone_idimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('Career Save Game Data')_PendingCareerEvent = namedtuple('_PendingCareerEvent', ('career', 'career_event', 'additional_careers'))
class CareerService(Service):

    def __init__(self):
        self._shuffled_career_list = None
        self._career_list_seed = None
        self._last_day_updated = None
        self._pending_career_events = deque()
        self._main_career_event_zone_id = None
        self._save_lock = None
        self.enabled = True
        self._career_event_subvenue_zone_ids = None
        self._career_lay_off_enabled = True
        self._gig_picker_disabled_gigs_map = {}
        self._gig_picker_associated_sims_map = {}
        self._gig_buckets = {}

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_CAREER_SERVICE

    def start(self):
        services.venue_service().on_venue_type_changed.register(self._remove_invalid_careers)
        return super().start()

    def stop(self):
        services.venue_service().on_venue_type_changed.unregister(self._remove_invalid_careers)
        return super().stop()

    def load(self, zone_data=None):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.gameplay_data.HasField('career_choices_seed'):
            self._career_list_seed = save_slot_data_msg.gameplay_data.career_choices_seed
        if not save_slot_data_msg.gameplay_data.HasField('career_service'):
            return
        career_service_data = save_slot_data_msg.gameplay_data.career_service
        if career_service_data.subvenue_zone_ids is not None:
            self._career_event_subvenue_zone_ids = {}
            for zone_id in career_service_data.subvenue_zone_ids:
                self._career_event_subvenue_zone_ids[zone_id] = set()
        if career_service_data.disabled_gig_data:
            for data in career_service_data.disabled_gig_data:
                if data.sim_ids:
                    self._gig_picker_disabled_gigs_map[data.gig_uid].extend(list(data.sim_ids))
                else:
                    self._gig_picker_disabled_gigs_map[data.gig_uid] = None
        if career_service_data.gig_associated_sim_data:
            for data in career_service_data.gig_associated_sim_data:
                self._gig_picker_associated_sims_map[data.gig_uid] = data.associated_sim_id

    def save(self, object_list=None, zone_data=None, open_street_data=None, save_slot_data=None):
        if self._career_list_seed is not None:
            save_slot_data.gameplay_data.career_choices_seed = self._career_list_seed
        career_service_data = GameplaySaveData_pb2.PersistableCareerService()
        if self._career_event_subvenue_zone_ids is not None:
            career_service_data.subvenue_zone_ids.extend(self._career_event_subvenue_zone_ids.keys())
        if self._gig_picker_disabled_gigs_map is not None:
            for (gig_uid, sim_ids) in self._gig_picker_disabled_gigs_map.items():
                with ProtocolBufferRollback(career_service_data.disabled_gig_data) as disabled_gig_msg:
                    disabled_gig_msg.gig_guid = gig_uid
                    if sim_ids:
                        disabled_gig_msg.sim_ids.extend(self._gig_picker_disabled_gigs_map[gig_uid])
        if self._gig_picker_associated_sims_map is not None:
            for (gig_uid, sim_id) in self._gig_picker_associated_sims_map.items():
                with ProtocolBufferRollback(career_service_data.gig_associated_sim_data) as associated_sim_msg:
                    associated_sim_msg.gig_uid = gig_uid
                    associated_sim_msg.associated_sim_id = sim_id
        save_slot_data.gameplay_data.career_service = career_service_data

    def _remove_invalid_careers(self):
        for sim_info in services.sim_info_manager().get_all():
            if sim_info.career_tracker is None:
                pass
            else:
                sim_info.career_tracker.remove_invalid_careers()

    def save_options(self, options_proto):
        options_proto.career_lay_off_enabled = self._career_lay_off_enabled

    def load_options(self, options_proto):
        self._career_lay_off_enabled = options_proto.career_lay_off_enabled

    @property
    def career_lay_off_enabled(self):
        return self._career_lay_off_enabled

    @career_lay_off_enabled.setter
    def career_lay_off_enabled(self, value):
        self._career_lay_off_enabled = value

    def get_days_from_time(self, time):
        return math.floor(time.absolute_days())

    def get_seed(self, days_now):
        if self._career_list_seed is None:
            self._career_list_seed = random.randint(0, MAX_UINT64)
        return self._career_list_seed + days_now

    def get_career_list(self):
        career_list = []
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in career_manager.types:
            career_tuning = career_manager.get(career_id)
            career_list.append(career_tuning)
        return career_list

    def get_shuffled_career_list(self):
        time_now = services.time_service().sim_now
        days_now = self.get_days_from_time(time_now)
        if self._shuffled_career_list is None or self._last_day_updated != days_now:
            career_seed = self.get_seed(days_now)
            career_rand = Random(career_seed)
            self._last_day_updated = days_now
            self._shuffled_career_list = self.get_career_list()
            career_rand.shuffle(self._shuffled_career_list)
        return self._shuffled_career_list

    def get_careers_by_category_gen(self, career_category):
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career in career_manager.types.values():
            if career.career_category == career_category:
                yield career

    def get_random_career_type_for_sim(self, sim_info):
        career_types = tuple(career_type for career_type in self.get_career_list() if career_type.is_valid_career(sim_info=sim_info))
        if career_types:
            return random.choice(career_types)

    def restore_career_state(self):
        try:
            manager = services.sim_info_manager()
            for sim_info in manager.get_all():
                if sim_info.is_npc:
                    pass
                else:
                    current_work_career = sim_info.career_tracker.get_currently_at_work_career()
                    for career in sim_info.careers.values():
                        if not career.currently_at_work:
                            pass
                        elif career is not current_work_career:
                            logger.error('Found a second at work career {} for a sim already at work at {}. This is invalid.', career, current_work_career)
                            if career.is_at_active_event:
                                career.end_career_event_without_payout()
                            else:
                                career.leave_work(left_early=True)
                                if career.is_at_active_event:
                                    if not career.career_event_manager.is_valid_zone_id(sim_info.zone_id):
                                        career.end_career_event_without_payout()
                                    else:
                                        for (career_event, subvenue_zone_id) in career.career_event_manager.get_subvenue_datas().items():
                                            career_event_set = self._career_event_subvenue_zone_ids.get(subvenue_zone_id)
                                            if career_event_set is None:
                                                logger.error('Subvenue for career event {} not found on load', career_event)
                                            else:
                                                career_event_set.add(career_event)
                                        if not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                            career.leave_work(left_early=True)
                                elif not career._rabbit_hole_id:
                                    career.put_sim_in_career_rabbit_hole()
                                    career.resend_career_data()
                                if not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                    career.leave_work(left_early=True)
                        else:
                            if career.is_at_active_event:
                                if not career.career_event_manager.is_valid_zone_id(sim_info.zone_id):
                                    career.end_career_event_without_payout()
                                else:
                                    for (career_event, subvenue_zone_id) in career.career_event_manager.get_subvenue_datas().items():
                                        career_event_set = self._career_event_subvenue_zone_ids.get(subvenue_zone_id)
                                        if career_event_set is None:
                                            logger.error('Subvenue for career event {} not found on load', career_event)
                                        else:
                                            career_event_set.add(career_event)
                                    if not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                        career.leave_work(left_early=True)
                            elif not career._rabbit_hole_id:
                                career.put_sim_in_career_rabbit_hole()
                                career.resend_career_data()
                            if not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                career.leave_work(left_early=True)
            if self._career_event_subvenue_zone_ids:
                venue_game_service = services.venue_game_service()
                if venue_game_service:
                    zone_ids_to_remove = [zone_id for (zone_id, current_zone_set) in self._career_event_subvenue_zone_ids.items() if not current_zone_set]
                    for zone_id in zone_ids_to_remove:
                        venue_game_service.restore_venue_type(zone_id, create_time_span(minutes=30))
                        del self._career_event_subvenue_zone_ids[zone_id]
        except:
            logger.exception('Exception raised while trying to restore career state.', owner='rrodgers')

    def create_career_event_situations_during_zone_spin_up(self):
        try:
            active_household = services.active_household()
            if active_household is None:
                return
            current_zone_id = services.current_zone_id()
            for sim_info in active_household:
                if sim_info.zone_id == current_zone_id:
                    career = sim_info.career_tracker.career_currently_within_hours
                    if career is not None:
                        career.create_career_event_situations_during_zone_spin_up()
        except:
            logger.exception('Exception raised while trying to restore career event.', owner='tingyul')

    def get_career_in_career_event(self):
        active_household = services.active_household()
        if active_household is not None:
            for sim_info in active_household:
                career = sim_info.career_tracker.get_at_work_career()
                if career is not None and career.is_at_active_event:
                    return career

    def try_add_pending_career_event_offer(self, career, career_event):
        additional_careers = []
        if career.is_multi_sim_active:
            for pending_event in self._pending_career_events:
                if pending_event.career_event == career_event and career in pending_event.additional_careers:
                    return
            household = career.sim_info.household
            region = get_region_instance_from_zone_id(household.home_zone_id)
            for sim_info in household.sim_info_gen():
                if sim_info is career.sim_info:
                    pass
                elif sim_info.career_tracker is None:
                    pass
                elif career.allow_active_offlot or not sim_info.is_instanced():
                    pass
                elif not region.is_sim_info_compatible(sim_info):
                    pass
                else:
                    additional_career = sim_info.career_tracker.careers.get(career.guid64)
                    if additional_career is not None and additional_career.follow_enabled and career_event in additional_career.career_events:
                        (best_work_time, _, _) = additional_career.get_next_work_time(check_if_can_go_now=True, ignore_pto=True)
                        if best_work_time == TimeSpan.ZERO:
                            additional_careers.append(additional_career)
        pending = _PendingCareerEvent(career=career, career_event=career_event, additional_careers=additional_careers)
        self._pending_career_events.append(pending)
        if len(self._pending_career_events) == 1:
            self._try_offer_next_career_event()

    def is_sim_info_in_pending_career_event(self, sim_info, ignorable_careers=None):
        for pending_career_event in self._pending_career_events:
            if pending_career_event.career.sim_info is sim_info:
                if ignorable_careers and pending_career_event.career in ignorable_careers:
                    pass
                else:
                    return True
                    for pending_career in pending_career_event.additional_careers:
                        if pending_career.sim_info is sim_info:
                            if ignorable_careers and pending_career in ignorable_careers:
                                pass
                            else:
                                return True
            for pending_career in pending_career_event.additional_careers:
                if pending_career.sim_info is sim_info:
                    if ignorable_careers and pending_career in ignorable_careers:
                        pass
                    else:
                        return True
        return False

    def _try_offer_next_career_event(self):
        if self._pending_career_events:
            pending = self._pending_career_events[0]
            if pending.additional_careers:
                dialog = pending.career.career_messages.career_event_multi_sim_confirmation_dialog
                response = self._on_career_event_multi_sim_response
            else:
                dialog = pending.career.career_messages.career_event_confirmation_dialog
                response = self._on_career_event_response
            pending.career.send_career_message(dialog, on_response=response, auto_response=ButtonType.DIALOG_RESPONSE_OK)

    def _on_career_event_response(self, dialog):
        pending = self._pending_career_events.popleft()
        career_event = pending.career_event
        if dialog.accepted:
            self._cancel_pending_career_events()
            pending.career.on_career_event_accepted(career_event)
        else:
            self._try_offer_next_career_event()
            pending.career.on_career_event_declined(career_event)

    def _on_career_event_multi_sim_response(self, dialog):
        if dialog.accepted:
            pending = self._pending_career_events[0]
            dialog = pending.career.career_messages.career_event_multi_sim_picker_dialog(None, resolver=GlobalResolver())
            sim_id = pending.career.sim_info.id
            dialog.add_row(SimPickerRow(sim_id=sim_id, tag=sim_id, select_default=not (pending.career.requested_day_off or pending.career.taking_day_off)))
            for career in pending.additional_careers:
                sim_id = career.sim_info.id
                dialog.add_row(SimPickerRow(sim_id=sim_id, tag=sim_id, select_default=not (career.requested_day_off or career.taking_day_off)))
            dialog.add_listener(self._on_career_event_sim_pick_response)
            dialog.show_dialog()
        else:
            pending = self._pending_career_events.popleft()
            career_event = pending.career_event
            self._try_offer_next_career_event()
            pending.career.on_career_event_declined(career_event)
            for career in pending.additional_careers:
                career.on_career_event_declined(career_event)

    def _on_career_event_sim_pick_response(self, dialog):
        pending = self._pending_career_events.popleft()
        career_event = pending.career_event
        results = set(dialog.get_result_tags())
        if dialog.accepted and results:
            self._cancel_pending_career_events()
            additional_sims = set()
            additional_careers = []
            primary_career = None
            rabbithole_careers = []
            if pending.career.sim_info.id in results:
                primary_career = pending.career
            else:
                rabbithole_careers.append(pending.career)
            for career in pending.additional_careers:
                if career.sim_info.id in results:
                    if primary_career is None:
                        primary_career = career
                    else:
                        additional_careers.append(career)
                        additional_sims.add(career.sim_info.id)
                        rabbithole_careers.append(career)
                else:
                    rabbithole_careers.append(career)
            primary_career.on_career_event_accepted(career_event, additional_sims=additional_sims)
            for career in additional_careers:
                career.on_career_event_accepted(career_event, is_additional_sim=True)
        else:
            rabbithole_careers = pending.additional_careers
            rabbithole_careers.append(pending.career)
            self._try_offer_next_career_event()
        for career in rabbithole_careers:
            career.on_career_event_declined(career_event)

    def _cancel_pending_career_events(self):
        for pending in self._pending_career_events:
            pending.career.on_career_event_declined(pending.career_event)
            for career in pending.additional_careers:
                career.on_career_event_declined(pending.career_event)
        self._pending_career_events.clear()

    def get_career_event_situation_is_running(self):
        career = self.get_career_in_career_event()
        if career is not None:
            manager = career.career_event_manager
            if manager is not None and manager.scorable_situation_id is not None:
                return True
        return False

    def set_main_career_event_zone_id_and_lock_save(self, main_zone_id):

        class _SaveLock:

            def get_lock_save_reason(self):
                return LocalizationHelperTuning.get_raw_text('')

        self._save_lock = _SaveLock()
        services.get_persistence_service().lock_save(self._save_lock)
        self._main_career_event_zone_id = main_zone_id

    def get_main_career_event_zone_id_and_unlock_save(self):
        if self._save_lock is not None:
            services.get_persistence_service().unlock_save(self._save_lock)
            self._save_lock = None
        zone_id = self._main_career_event_zone_id
        self._main_career_event_zone_id = None
        return zone_id

    def start_career_event_subvenue(self, career_event, zone_id, venue):
        if self._career_event_subvenue_zone_ids is None:
            self._career_event_subvenue_zone_ids = {}
        career_event_set = self._career_event_subvenue_zone_ids.get(zone_id)
        if career_event_set is None:
            career_event_set = set()
            self._career_event_subvenue_zone_ids[zone_id] = career_event_set
            venue_game_service = services.venue_game_service()
            if venue_game_service is not None:
                venue_game_service.change_venue_type(zone_id, venue)
            else:
                logger.error("Career event {} tuned with subvenue but VenueGameService isn't running.", career_event)
        career_event_set.add(career_event)

    def stop_career_event_subvenue(self, career_event, zone_id, delay):
        if self._career_event_subvenue_zone_ids is None:
            logger.error('Career event {} trying to stop subvenue when no subvenues are started', career_event)
            return
        career_event_set = self._career_event_subvenue_zone_ids.get(zone_id)
        if career_event_set is None:
            logger.error("Career event {} trying to stop subvenue that wasn't started", career_event)
            return
        if career_event not in career_event_set:
            return
        career_event_set.remove(career_event)
        if not career_event_set:
            del self._career_event_subvenue_zone_ids[zone_id]
            venue_game_service = services.venue_game_service()
            if venue_game_service is not None:
                venue_game_service.restore_venue_type(zone_id, delay())
            else:
                logger.error("Career event {} tuned with subvenue but VenueGameService isn't running.", career_event)

    def is_gig_available(self, gig_guid:'int', sim_id:'int') -> 'bool':
        if gig_guid in self._gig_picker_disabled_gigs_map.keys():
            sim_id_list = self._gig_picker_disabled_gigs_map[gig_guid]
            if sim_id_list is None or sim_id in sim_id_list:
                return False
        return True

    def disable_gig(self, gig_guid:'int', sim_id:'int'=None) -> 'None':
        if gig_guid in self._gig_picker_disabled_gigs_map:
            if self._gig_picker_disabled_gigs_map[gig_guid] is None:
                return
            if sim_id is not None:
                self._gig_picker_disabled_gigs_map[gig_guid].append(sim_id)
            else:
                logger.error('Requesting to disable a gig {} for all Sims, but is already disabled for individual Sims', gig_guid, owner='madang')
        else:
            sim_id_list = None
            if sim_id is not None:
                sim_id_list = [sim_id]
            self._gig_picker_disabled_gigs_map[gig_guid] = sim_id_list

    def enable_gig(self, gig_guid:'int', sim_id:'int'=None) -> 'None':
        if gig_guid in self._gig_picker_disabled_gigs_map:
            sim_id_list = self._gig_picker_disabled_gigs_map[gig_guid]
            if sim_id_list is None or sim_id is None:
                del self._gig_picker_disabled_gigs_map[gig_guid]
            elif sim_id in sim_id_list:
                sim_id_list.remove(sim_id)
                if not sim_id_list:
                    del self._gig_picker_disabled_gigs_map[gig_guid]

    def remove_gig_from_bucket(self, gig_guid:'int') -> 'None':
        gig_manager = services.get_instance_manager(sims4.resources.Types.CAREER_GIG)
        if gig_manager is None:
            return
        gig = gig_manager.get(gig_guid)
        if gig is not None and gig.picker_scoring is not None and gig.picker_scoring.bucket in self._gig_buckets.keys():
            gig_uid_list = self._gig_buckets[gig.picker_scoring.bucket]
            if gig_guid in gig_uid_list:
                gig_uid_list.remove(gig_guid)

    def get_gig_associated_sim_info(self, gig_guid:'int') -> 'SimInfo':
        associated_sim_id = self._gig_picker_associated_sims_map.get(gig_guid)
        if associated_sim_id is not None:
            sim_info_manager = services.sim_info_manager()
            return sim_info_manager.get(associated_sim_id)

    def set_gig_associated_sim_info(self, gig_guid:'int', sim_info:'SimInfo') -> 'None':
        self._gig_picker_associated_sims_map[gig_guid] = sim_info.id
