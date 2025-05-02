from __future__ import annotationsfrom careers.career_enums import CareerCategoryfrom collections import defaultdictfrom distributor.rollback import ProtocolBufferRollbackfrom objects import HiddenReasonFlagfrom relationships.bit_timout import BitTimeoutDatafrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.relationship_enums import RelationshipBitCullingPrevention, RelationshipTrackTypeimport event_testingimport servicesimport sims4import telemetry_helperfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from relationships.relationship_bit import RelationshipBit
    from sims.sim_info import SimInfo
    from sims4.telemetry import _TelemetryHookWriter
    from traits.traits import Trait
    from relationships.relationship_track import RelationshipTrack
    from relationships.relationship_track_tracker import RelationshipTrackTrackerlogger = sims4.log.Logger('Relationship', default_owner='jjacobson')TELEMETRY_GROUP_RELATIONSHIPS = 'RSHP'TELEMETRY_HOOK_ADD_BIT = 'BADD'TELEMETRY_HOOK_REMOVE_BIT = 'BREM'TELEMETRY_HOOK_CHANGE_LEVEL = 'RLVL'TELEMETRY_FIELD_TARGET_ID = 'tsim'TELEMETRY_FIELD_BIT_ID = 'biid'TELEMETRY_FIELD_KEY_TRAIT_IDS = 'ktrt'TELEMETRY_FIELD_SENTIMENT_IDS = 'snta'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_RELATIONSHIPS)
class RelationshipData:
    __slots__ = ('relationship', '_bits', '_bit_timeouts', '_cached_depth', 'cached_depth_dirty', '_relationship_bit_locks', '__weakref__', '_track_tracker')

    def __init__(self, relationship):
        self.relationship = relationship
        self._bits = {}
        self._bit_timeouts = None
        self._cached_depth = 0
        self.cached_depth_dirty = True
        self._relationship_bit_locks = None
        self._track_tracker = None

    @property
    def bit_types(self):
        return self._bits.keys()

    @property
    def bit_instances(self):
        return self._bits.values()

    @property
    def depth(self):
        if self.cached_depth_dirty:
            self._refresh_depth_cache()
        return self._cached_depth

    @property
    def track_tracker(self):
        return self._track_tracker

    def _refresh_depth_cache(self):
        self._cached_depth = 0
        for bit in self._bits.keys():
            self._cached_depth += bit.depth
        self.cached_depth_dirty = False

    def _sim_ids(self):
        raise NotImplementedError

    def track_reached_convergence(self, track_instance):
        if track_instance.track_type == RelationshipTrackType.SENTIMENT:
            self.remove_track(track_instance.stat_type)
        if track_instance.causes_delayed_removal_on_convergence and self.relationship is not None and self.relationship.can_cull_relationship():
            logger.debug('{} has been marked for culling.', self)
            self.relationship._create_culling_alarm()
        if track_instance.is_visible:
            logger.debug('Notifying client that {} has reached convergence.', self)
            if self.relationship is not None:
                self.relationship.send_relationship_info()

    def can_cull_relationship(self, consider_convergence, is_played_relationship):
        for bit in self._bits.values():
            if bit.relationship_culling_prevention == RelationshipBitCullingPrevention.ALLOW_ALL:
                pass
            else:
                if bit.relationship_culling_prevention == RelationshipBitCullingPrevention.PLAYED_AND_UNPLAYED:
                    return False
                if is_played_relationship and bit.relationship_culling_prevention == RelationshipBitCullingPrevention.PLAYED_ONLY:
                    return False
        return True

    def _find_timeout_data_by_bit(self, bit):
        if self._bit_timeouts:
            return self._bit_timeouts.get(bit, None)

    def find_timeout_data_by_bit(self, bit):
        return self._find_timeout_data_by_bit(bit)

    def _find_timeout_data_by_bit_instance(self, bit_instance):
        bit_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)
        bit = bit_manager.get(bit_instance.guid64)
        return self._find_timeout_data_by_bit(bit)

    def _find_timeout_data_by_handle(self, alarm_handle):
        if self._bit_timeouts:
            for data in self._bit_timeouts.values():
                if alarm_handle is data.alarm_handle:
                    return data

    def _timeout_alarm_callback(self, alarm_handle):
        timeout_data = self._find_timeout_data_by_handle(alarm_handle)
        if timeout_data is not None:
            self.remove_bit(timeout_data.bit)
        else:
            logger.error('Failed to find alarm handle in _bit_timeouts list')

    def _send_telemetry_event_for_bit_change(self, telemetry_hook:'str', bit:'RelationshipBit', sim_info:'SimInfo', target_sim_info:'SimInfo') -> 'None':
        if sim_info is None or target_sim_info is None:
            return
        relevant_traits = set()
        for trait_of_interest in RelationshipGlobalTuning.TRAITS_OF_INTEREST:
            if not sim_info.has_trait(trait_of_interest):
                if target_sim_info.has_trait(trait_of_interest):
                    relevant_traits.add(trait_of_interest)
            relevant_traits.add(trait_of_interest)
        relevant_traits_str = '_'.join(str(relevant_trait.guid64) for relevant_trait in relevant_traits)
        with telemetry_helper.begin_hook(writer, telemetry_hook, sim_info=sim_info) as hook:
            hook.write_int(TELEMETRY_FIELD_TARGET_ID, target_sim_info.sim_id)
            hook.write_int(TELEMETRY_FIELD_BIT_ID, bit.guid64)
            hook.write_string(TELEMETRY_FIELD_KEY_TRAIT_IDS, relevant_traits_str)
            self._write_to_hook(bit, sim_info, target_sim_info, hook)

    def _write_to_hook(self, bit:'RelationshipBit', sim_info:'SimInfo', target_sim_info:'SimInfo', hook:'_TelemetryHookWriter') -> 'None':
        pass

    def _update_client_for_sim_info_for_bit_add(self, bit_to_add, bit_instance, sim_info, target_sim_info, from_load):
        if sim_info is None or self.relationship is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is not None:
            bit_instance.on_add_to_relationship(sim, target_sim_info, self.relationship, from_load)
            self.show_bit_added_dialog(bit_instance, sim, target_sim_info)
        if not self.relationship.is_object_rel:
            self._send_telemetry_event_for_bit_change(TELEMETRY_HOOK_ADD_BIT, bit_to_add, sim_info, target_sim_info)
            services.get_event_manager().process_event(event_testing.test_events.TestEvent.AddRelationshipBit, sim_info=sim_info, relationship_bit=bit_to_add, sim_id=sim_info.sim_id, target_sim_id=target_sim_info.sim_id, custom_keys=(bit_to_add,))
        if bit_to_add is RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT:
            sim_info.update_spouse_sim_id(target_sim_info.sim_id)
        if bit_to_add is RelationshipGlobalTuning.ENGAGEMENT_RELATIONSHIP_BIT:
            sim_info.update_fiance_sim_id(target_sim_info.sim_id)
        if bit_to_add is RelationshipGlobalTuning.STEADY_RELATIONSHIP_BIT:
            sim_info.update_steady_sim_ids(target_sim_info.id, True)
        if bit_to_add is RelationshipGlobalTuning.WORKPLACE_RIVAL_RELATIONSHIP_BIT:
            self._update_workplace_rival_career_data(sim_info, target_sim_info.id)

    def _update_workplace_rival_career_data(self, sim_info, rival_id):
        if sim_info is None or sim_info.career_tracker is None:
            return
        careers_gen = sim_info.career_tracker.get_careers_by_category_gen(CareerCategory.Work)
        careers = list(careers_gen)
        if len(careers) == 0:
            return
        work_career = careers[0]
        work_career.workplace_rival_id = rival_id
        work_career.resend_career_data()

    def _update_client_from_bit_add(self, bit_type, bit_instance, from_load):
        raise NotImplementedError

    def _update_client_for_sim_info_for_bit_remove(self, bit_to_remove, bit_instance, sim_info, target_sim_info):
        if sim_info is None:
            return
        if target_sim_info is not None:
            self._send_telemetry_event_for_bit_change(TELEMETRY_HOOK_REMOVE_BIT, bit_to_remove, sim_info, target_sim_info)
            services.get_event_manager().process_event(event_testing.test_events.TestEvent.RemoveRelationshipBit, sim_info=sim_info, relationship_bit=bit_to_remove, sim_id=sim_info.sim_id, target_sim_id=target_sim_info.sim_id, custom_keys=(bit_to_remove,))
            sim = sim_info.get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE)
            if sim is not None:
                bit_instance.on_remove_from_relationship(sim, target_sim_info)
                self.show_bit_removed_dialog(bit_instance, sim, target_sim_info)
        if bit_to_remove is RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT:
            sim_info.update_spouse_sim_id(None)
        if bit_to_remove is RelationshipGlobalTuning.ENGAGEMENT_RELATIONSHIP_BIT:
            sim_info.update_fiance_sim_id(None)
        if bit_to_remove is RelationshipGlobalTuning.WORKPLACE_RIVAL_RELATIONSHIP_BIT:
            self._update_workplace_rival_career_data(sim_info, None)

    def _update_client_from_bit_remove(self, bit_type, bit_instance):
        raise NotImplementedError

    def add_bit(self, bit_type, bit_instance, from_load=False):
        self.cached_depth_dirty = True
        self._bits[bit_type] = bit_instance
        if self.relationship is None:
            return
        if not self.relationship.suppress_client_updates:
            self._update_client_from_bit_add(bit_type, bit_instance, from_load)
        if bit_type.timeout > 0:
            timeout_data = self._find_timeout_data_by_bit(bit_type)
            if timeout_data is None:
                timeout_data = BitTimeoutData(bit_type, self._timeout_alarm_callback)
                if self._bit_timeouts is None:
                    self._bit_timeouts = {}
                self._bit_timeouts[bit_type] = timeout_data
            timeout_data.reset_alarm()
        remove_on_threshold = bit_type.remove_on_threshold
        if remove_on_threshold is None:
            return
        track_def = remove_on_threshold.track
        if track_def is None:
            return
        track_type = track_def.track_type
        if track_type == RelationshipTrackType.SENTIMENT:
            logger.error('remove_on_threshold should not be set for bits of sentiments. Sentiment bits are not added/removed based on sentiment track valuesbit:{} should be updated'.format(bit_type))
            return
        actor_sim_id = self._sim_ids()[0]
        tracker = self.relationship.get_track_tracker(actor_sim_id, track_def)
        listener = tracker.create_and_add_listener(track_def, remove_on_threshold.threshold, self._on_remove_bit_threshold_satisfied)
        bit_instance.add_conditional_removal_listener(listener)

    def _on_remove_bit_threshold_satisfied(self, track):
        for bit in self._bits.keys():
            if bit.remove_on_threshold is None:
                pass
            elif bit.remove_on_threshold.track is type(track):
                self.remove_bit(bit)
                return
        logger.error("Got a callback to remove a bit for track {}, but one doesn't exist.", track)

    def remove_bit(self, bit):
        bit_instance = self._bits.get(bit)
        if bit_instance is None:
            logger.warn("Attempting to remove bit of type {} that doesn't exist.", bit)
        if self.relationship is None:
            logger.warn('Attempting to remove bit on a relationship that has been deleted')
            return
        self.cached_depth_dirty = True
        del self._bits[bit]
        logger.debug('Removed bit {} for {}', bit, self)
        if not self.relationship.suppress_client_updates:
            self._update_client_from_bit_remove(bit, bit_instance)
        timeout_data = self._find_timeout_data_by_bit(bit)
        if timeout_data is not None:
            timeout_data.cancel_alarm()
            del self._bit_timeouts[bit]
            if not self._bit_timeouts:
                self._bit_timeouts = None
        remove_on_threshold = bit.remove_on_threshold
        if remove_on_threshold is None:
            return
        listener = bit_instance.remove_conditional_removal_listener()
        if listener is None:
            logger.error(f'Bit {bit} is meant to have a listener on track {remove_on_threshold.track} but it doesn't for {self}.')
            return
        track_def = remove_on_threshold.track
        if track_def is None:
            return
        track_type = track_def.track_type
        if track_type == RelationshipTrackType.SENTIMENT:
            logger.error('remove_on_threshold should not be set for bits of sentiments. Sentiment bits are not added/removed based on sentiment track valuesbit:{} should be updated'.format(bit))
            return
        actor_sim_id = self._sim_ids()[0]
        self.relationship.get_track_tracker(actor_sim_id, track_def).remove_listener(listener)

    def save_relationship_data(self, relationship_data_msg):
        for bit in self._bits:
            if bit.persisted:
                relationship_data_msg.bits.append(bit.guid64)
        if self._bit_timeouts is not None:
            for timeout in self._bit_timeouts.values():
                with ProtocolBufferRollback(relationship_data_msg.timeouts) as timeout_proto_buffer:
                    timeout_proto_buffer.timeout_bit_id_hash = timeout.bit.guid64
                    timeout_proto_buffer.elapsed_time = timeout.get_elapsed_time()
        if self._relationship_bit_locks is not None:
            for relationship_bit_lock in self._relationship_bit_locks.values():
                with ProtocolBufferRollback(relationship_data_msg.relationship_bit_locks) as relationship_bit_lock_proto_buffer:
                    relationship_bit_lock.save(relationship_bit_lock_proto_buffer)
        for track in self.all_tracks_gen():
            if not track.persisted:
                pass
            elif track.persist_at_convergence or track.is_at_convergence():
                pass
            else:
                with ProtocolBufferRollback(relationship_data_msg.tracks) as track_proto_buffer:
                    track_proto_buffer.track_id = track.type_id()
                    track_proto_buffer.value = track.get_value()
                    track_proto_buffer.visible = track.visible_to_client
                    track_proto_buffer.ticks_until_decay_begins = track.get_saved_ticks_until_decay_begins()

    def load_relationship_data(self, relationship_data_msg):
        track_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        track_to_bit_list_map = defaultdict(list)
        try:
            self._set_load_in_progress(True)
            for track_data in relationship_data_msg.tracks:
                track_def = track_manager.get(track_data.track_id)
                if track_def is None:
                    pass
                elif track_def.persist_at_convergence or track_data.value == track_def.default_value:
                    pass
                else:
                    track_tracker = self.get_tracker_for_track_type(track_def.track_type)
                    track_inst = track_tracker.add_statistic(track_def)
                    if track_inst is not None:
                        track_inst.set_value(track_data.value)
                        track_inst.visible_to_client = track_data.visible
                        track_inst.set_time_until_decay_begins(track_data.ticks_until_decay_begins)
                        track_inst.fixup_callbacks_during_load()
                        track_to_bit_list_map[track_inst] = []
                    else:
                        logger.warn('Failed to load track {}.  This is valid if the tuning has changed.', track_def)
        finally:
            self._set_load_in_progress(False)
        bit_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)
        logger.assert_raise(bit_manager, 'Unable to retrieve relationship bit manager.')
        if track_to_bit_list_map is None:
            track_to_bit_list_map = defaultdict(list)
        bit_list = []
        for bit_guid in relationship_data_msg.bits:
            bit = bit_manager.get(bit_guid)
            if bit is None:
                logger.info('Trying to load unavailable RELATIONSHIP_BIT resource: {}', bit_guid)
            elif bit.triggered_track is not None:
                track_tracker = self.get_tracker_for_track_type(bit.triggered_track.track_type)
                track_inst = track_tracker.get_statistic(bit.triggered_track)
                if track_inst is not None:
                    bit_data_set = track_inst.get_bit_data_set()
                    if bit_data_set and bit in bit_data_set:
                        track_to_bit_list_map[track_inst].append(bit)
                    else:
                        bit_list.append(bit)
                else:
                    bit_list.append(bit)
            else:
                bit_list.append(bit)
        for (track_inst, track_bit_list) in track_to_bit_list_map.items():
            if len(track_bit_list) > 1:
                active_bit = track_inst.get_active_bit_by_value()
                logger.warn('{} has bad persisted Rel Bit value on Rel Track {}.  Fix it by adding bit {} and removing bits {}.', self, track_inst, active_bit, track_bit_list, owner='mkartika')
                bit_list.append(active_bit)
            else:
                bit_list.extend(track_bit_list)
        (sim_id_a, sim_id_b) = self._sim_ids()
        while bit_list:
            bit = bit_list.pop()
            if bit in self._bits:
                pass
            elif not self.relationship.add_relationship_bit(sim_id_a, sim_id_b, bit, notify_client=False, pending_bits=bit_list, from_load=True, send_rel_change_event=False):
                logger.warn('Failed to load relationship bit {}.  This is valid if tuning has changed.', bit)
        if relationship_data_msg.timeouts is not None:
            for timeout_save in relationship_data_msg.timeouts:
                bit = bit_manager.get(timeout_save.timeout_bit_id_hash)
                timeout_data = self._find_timeout_data_by_bit(bit)
                if timeout_data is not None:
                    if not timeout_data.load_bit_timeout(timeout_save.elapsed_time):
                        self.remove_bit(bit)
                else:
                    logger.warn('Attempting to load timeout value on bit {} with no timeout.  This is valid if tuning has changed.', bit)
        relationship_bit_lock_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_LOCK)
        for relationship_bit_lock_data in relationship_data_msg.relationship_bit_locks:
            lock_type = relationship_bit_lock_manager.get(relationship_bit_lock_data.relationship_bit_lock_type)
            if lock_type is None:
                pass
            else:
                new_lock = self.add_lock(lock_type)
                new_lock.load(relationship_bit_lock_data)
        for track in self.all_tracks_gen():
            track.update_track_index(self.relationship)

    def notify_relationship_on_lod_change(self, old_lod, new_lod):
        pass

    def destroy(self):
        self.relationship = None
        self._bits.clear()
        self._bit_timeouts = None
        self._cached_depth = 0
        self.cached_depth_dirty = False
        self._relationship_bit_locks = None

    def show_bit_added_dialog(self, relationship_bit, sim, target_sim_info):
        raise NotImplementedError

    def show_bit_removed_dialog(self, relationship_bit, sim, target_sim_info):
        raise NotImplementedError

    def add_lock(self, lock_type):
        if self._relationship_bit_locks is None:
            self._relationship_bit_locks = {}
        current_lock = self._relationship_bit_locks.get(lock_type, None)
        if current_lock is not None:
            return current_lock
        new_lock = lock_type()
        self._relationship_bit_locks[lock_type] = new_lock
        return new_lock

    def get_lock(self, lock_type):
        if self._relationship_bit_locks is None:
            return
        return self._relationship_bit_locks.get(lock_type, None)

    def get_all_locks(self):
        locks = []
        if self._relationship_bit_locks is None:
            return locks
        locks.extend(self._relationship_bit_locks.values())
        return locks

    def on_sim_creation(self, sim):
        for bit_instance in self._bits.values():
            bit_instance.add_buffs_for_bit_add(sim, self.relationship, True)
        self._track_tracker.on_sim_creation(sim)

    def set_track_to_max(self, track):
        self.get_tracker_for_track_type(track.track_type).set_max(track)

    def get_track(self, track, add=False):
        return self.get_tracker_for_track_type(track.track_type).get_statistic(track, add)

    def has_track(self, track):
        return self.get_tracker_for_track_type(track.track_type).has_statistic(track)

    def remove_track(self, track, on_destroy=False):
        return self.get_tracker_for_track_type(track.track_type).remove_statistic(track, on_destroy)

    def get_highest_priority_track_bit(self):
        highest_priority_bit = None
        for track in self.all_tracks_gen():
            bit = track.get_active_bit()
            if not bit:
                pass
            else:
                if not highest_priority_bit is None:
                    if bit.priority > highest_priority_bit.priority:
                        highest_priority_bit = bit
                highest_priority_bit = bit
        return highest_priority_bit

    def apply_social_group_decay(self):
        for track in self.all_tracks_gen():
            track.apply_social_group_decay()

    def get_track_score(self, track):
        return self.get_tracker_for_track_type(track.track_type).get_user_value(track)

    def set_track_score(self, value, track, **kwargs):
        self.get_tracker_for_track_type(track.track_type).set_value(track, value, **kwargs)

    def add_track_score(self, increment, track, **kwargs):
        self.get_tracker_for_track_type(track.track_type).add_value(track, increment, **kwargs)

    def enable_player_sim_track_decay(self, to_enable=True):
        self._track_tracker.enable_player_sim_track_decay(to_enable)

    def get_track_utility_score(self, track):
        track_inst = self.get_tracker_for_track_type(track.track_type).get_statistic(track)
        if track_inst is not None:
            return track_inst.autonomous_desire
        else:
            return track.autonomous_desire

    def remove_social_group_decay(self):
        for track in self.all_tracks_gen():
            track.remove_social_group_decay()

    def is_object_rel(self):
        return self.relationship and self.relationship.is_object_rel

    def all_tracks_gen(self) -> 'Generator[RelationshipTrack]':
        for track in self._track_tracker:
            yield track

    def _set_load_in_progress(self, load_in_progress:'bool') -> 'None':
        self._track_tracker.suppress_callback_setup_during_load = load_in_progress
        self._track_tracker.load_in_progress = load_in_progress

    def get_tracker_for_track_type(self, track_type:'RelationshipTrackType') -> 'RelationshipTrackTracker':
        return self._track_tracker
