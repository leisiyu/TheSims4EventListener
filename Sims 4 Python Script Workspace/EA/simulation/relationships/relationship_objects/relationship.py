from __future__ import annotationsimport itertoolsimport alarmsimport date_and_timeimport event_testingimport servicesimport sims4.logfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom protocolbuffers import DistributorOps_pb2, Commodities_pb2 as commodity_protocolfrom relationships.data.bidirectional_relationship_data import BidirectionalRelationshipDatafrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.relationship_bit import RelationshipBitTypefrom relationships.relationship_bit_lock import RelationshipBitLockfrom relationships.relationship_enums import RelationshipDirection, RelationshipTrackTypefrom relationships.relationship_track import RelationshipTrackfrom sims4.utils import classpropertyfrom singletons import EMPTY_SET, DEFAULTfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.sim_info import SimInfo
    from relationships.relationship_track_tracker import RelationshipTrackTracker
    from typing import *logger = sims4.log.Logger('Relationship', default_owner='jjacobson')
class Relationship:
    __slots__ = ('_sim_id_a', '_sim_id_b', '_bi_directional_relationship_data', '_level_change_watcher_id', '_culling_alarm_handle', '_last_update_time', '_relationship_multipliers', '_counts_as_incest', '__weakref__', '_hidden')

    def __init__(self):
        self._bi_directional_relationship_data = BidirectionalRelationshipData(self)
        self._culling_alarm_handle = None
        self._last_update_time = 0
        self._counts_as_incest = False
        self._hidden = False

    @property
    def suppress_client_updates(self):
        return services.relationship_service().suppress_client_updates

    @property
    def sim_id_a(self):
        return self._sim_id_a

    @property
    def sim_id_b(self):
        return self._sim_id_b

    @property
    def considered_incest(self):
        if self._counts_as_incest is not None:
            return self._counts_as_incest
        for rel_bit in self._get_all_bits(self._sim_id_a):
            if rel_bit.counts_as_incest:
                self._counts_as_incest = True
                return True
        self._counts_as_incest = False
        return False

    @property
    def is_hidden(self) -> 'bool':
        return self._hidden

    def hide_relationship(self, value:'bool', notify_client:'bool'=True) -> 'None':
        self._hidden = value
        if notify_client is True:
            self.send_relationship_info()

    def get_relationship_key(self):
        return (self._sim_id_a, self._sim_id_b)

    def find_sim_info_a(self):
        return services.sim_info_manager().get(self._sim_id_a)

    def find_sim_info_b(self):
        return services.sim_info_manager().get(self._sim_id_b)

    def find_member_obj_b(self):
        return services.definition_manager().get(self._sim_id_b)

    def find_sim_a(self):
        sim_info = self.find_sim_info_a()
        if sim_info is not None:
            return sim_info.get_sim_instance()

    def find_sim_b(self):
        sim_info = self.find_sim_info_b()
        if sim_info is not None:
            return sim_info.get_sim_instance()

    def get_bi_directional_rel_data(self):
        return self._bi_directional_relationship_data

    def get_other_sim_id(self, sim_id):
        if self._sim_id_a == sim_id:
            return self._sim_id_b
        else:
            return self._sim_id_a

    def get_other_sim_info(self, sim_id):
        if self._sim_id_a == sim_id:
            return self.find_sim_info_b()
        else:
            return self.find_sim_info_a()

    def get_other_sim(self, sim_id):
        if self._sim_id_a == sim_id:
            return self.find_sim_b()
        else:
            return self.find_sim_a()

    @property
    def bidirectional_track_tracker(self) -> 'RelationshipTrackTracker':
        return self._bi_directional_relationship_data.track_tracker

    def get_track_relationship_data(self, sim_id, track):
        return self._bi_directional_relationship_data

    def get_relationship_depth(self, sim_id):
        return self._bi_directional_relationship_data.depth

    def _build_relationship_track_proto(self, actor_sim_id, msg):
        client_tracks = []
        for track in self.relationship_tracks_gen(actor_sim_id):
            if not track.display_priority is not None:
                if track.display_in_sim_profile:
                    client_tracks.append(track)
            client_tracks.append(track)
        client_tracks.sort(key=lambda rel_track: (rel_track.display_priority is None, rel_track.display_priority))
        track_bits = set()
        for track in client_tracks:
            if track.visible_to_client:
                with ProtocolBufferRollback(msg.tracks) as relationship_track_update:
                    track.build_single_relationship_track_proto(relationship_track_update)
            track_bits.add(track.get_bit_for_client().guid64)
        return track_bits

    def _send_headlines_for_sim(self, sim_info, deltas, headline_icon_modifier=None):
        for (track, delta) in deltas.items():
            if track.headline is None:
                pass
            elif track.track_type == RelationshipTrackType.UNIDIRECTIONAL and track.tracker.rel_data.sim_id_a != sim_info.sim_id:
                pass
            else:
                track.headline.send_headline_message(sim_info, delta, icon_modifier=headline_icon_modifier)

    def send_relationship_info(self, deltas=None, headline_icon_modifier=None):
        raise NotImplementedError()

    def relationship_tracks_gen(self, sim_id, track_type=None):
        if track_type is None or track_type == RelationshipTrackType.RELATIONSHIP:
            yield from self._bi_directional_relationship_data.track_tracker

    def get_track_score(self, sim_id, track):
        return self.get_track_relationship_data(sim_id, track).get_track_score(track)

    def set_track_score(self, sim_id, value, track, **kwargs):
        self.get_track_relationship_data(sim_id, track).set_track_score(value, track, **kwargs)

    def add_track_score(self, sim_id, increment, track, **kwargs):
        self.get_track_relationship_data(sim_id, track).add_track_score(increment, track, **kwargs)

    def set_track_to_max(self, sim_id, track):
        self.get_track_relationship_data(sim_id, track).set_track_to_max(track)

    def enable_player_sim_track_decay(self, to_enable=True):
        self._bi_directional_relationship_data.enable_player_sim_track_decay(to_enable=to_enable)
        if self._culling_alarm_handle is None and self.can_cull_relationship():
            self._create_culling_alarm()

    def get_track_utility_score(self, sim_id, track):
        return self.get_track_relationship_data(sim_id, track).get_track_utility_score(track)

    def get_track_tracker(self, sim_id, track):
        return self._bi_directional_relationship_data.track_tracker

    def get_track(self, sim_id, track, add=False):
        should_add = add and track.track_type != RelationshipTrackType.SENTIMENT
        return self.get_track_relationship_data(sim_id, track).get_track(track, add=should_add)

    def get_highest_priority_track_bit(self, sim_id):
        return self._bi_directional_relationship_data.get_highest_priority_track_bit()

    def get_prevailing_short_term_context_track(self, sim_id):
        return self._bi_directional_relationship_data.get_prevailing_short_term_context_track()

    def apply_social_group_decay(self):
        self._bi_directional_relationship_data.apply_social_group_decay()

    def remove_social_group_decay(self):
        self._bi_directional_relationship_data.remove_social_group_decay()

    def set_relationship_score(self, sim_id, value, track=DEFAULT, threshold=None, **kwargs):
        if track is DEFAULT:
            track = RelationshipGlobalTuning.REL_INSPECTOR_TRACK
        if threshold is None or threshold.compare(self.get_track_score(sim_id, track)):
            self.set_track_score(sim_id, value, track, **kwargs)
            logger.debug('Setting score on track {} for {}: = {}; new score = {}', track, self, value, self.get_track_score(sim_id, track))
        else:
            logger.debug('Attempting to set score on track {} for {} but {} not within threshold {}', track, self, self.get_track_score(sim_id, track), threshold)

    def add_relationship_bit(self, actor_sim_id, target_sim_id, bit_to_add, notify_client=True, pending_bits=EMPTY_SET, force_add=False, from_load=False, send_rel_change_event=True):
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        if self.is_object_rel:
            target_sim_info = None
            send_rel_change_event = False
        else:
            target_sim_info = sim_info_manager.get(target_sim_id)
        if send_rel_change_event:
            self._send_relationship_prechange_event(actor_sim_info, target_sim_info, bidirectional=bit_to_add.directionality == RelationshipDirection.BIDIRECTIONAL, bits_of_interest=(bit_to_add,))
        if bit_to_add is None:
            logger.error('Error: Sim Id: {} trying to add a None relationship bit to Sim_Id: {}.', actor_sim_id, target_sim_id)
            return False
        if force_add:
            if bit_to_add.triggered_track is not None:
                track = bit_to_add.triggered_track
                mean_list = track.bit_data.get_track_mean_list_for_bit(bit_to_add)
                for mean_tuple in mean_list:
                    self.set_relationship_score(actor_sim_id, mean_tuple.mean, track=mean_tuple.track)
            for required_bit in bit_to_add.required_bits:
                self.add_relationship_bit(actor_sim_id, target_sim_id, required_bit, force_add=True)
        required_bit_count = len(bit_to_add.required_bits)
        bit_to_remove = None
        for curr_bit in itertools.chain(self._get_all_bits(actor_sim_id), pending_bits):
            if curr_bit is bit_to_add:
                logger.debug('Attempting to add duplicate bit {} on {}', bit_to_add, actor_sim_info)
                if curr_bit.is_trope_bit and curr_bit.directionality == RelationshipDirection.BIDIRECTIONAL:
                    target_sim_info.genealogy.set_relationship_trope(actor_sim_id, curr_bit.guid64)
                return False
            if curr_bit in bit_to_add.required_bits:
                required_bit_count -= 1
            if required_bit_count and bit_to_add.group_id != RelationshipBitType.NoGroup and bit_to_add.group_id == curr_bit.group_id:
                if bit_to_add.priority >= curr_bit.priority:
                    if bit_to_remove is not None:
                        logger.error('Multiple relationship bits of the same type are set on a single relationship: {}', self)
                        return False
                    bit_to_remove = curr_bit
                else:
                    logger.debug('Failed to add bit {}; existing bit {} has higher priority for {}', bit_to_add, curr_bit, self)
                    return False
        if bit_to_add.remove_on_threshold:
            track_val = self._bi_directional_relationship_data.track_tracker.get_value(bit_to_add.remove_on_threshold.track)
            if bit_to_add.remove_on_threshold.threshold.compare(track_val):
                logger.debug('Failed to add bit {}; track {} meets the removal threshold {} for {}', bit_to_add, bit_to_add.remove_on_threshold.track, bit_to_add.remove_on_threshold.threshold, self)
                return False
        if from_load or required_bit_count > 0:
            logger.debug('Failed to add bit {}; required bit count is {}', bit_to_add, required_bit_count)
            return False
        rel_data = self._get_rel_data_for_bit(actor_sim_id, bit_to_add)
        if rel_data is None:
            logger.debug('Failed to get relationship data for bit {}', bit_to_add)
            return False
        if force_add or from_load or bit_to_add.group_id != RelationshipBitType.NoGroup:
            lock_type = RelationshipBitLock.get_lock_type_for_group_id(bit_to_add.group_id)
            if lock_type is not None:
                lock = rel_data.get_lock(lock_type)
                if lock is not None:
                    if not lock.try_and_aquire_lock_permission():
                        logger.debug('Failed to add bit {} because of Relationship Bit Lock {}', bit_to_add, lock_type)
                        return False
                else:
                    lock = rel_data.add_lock(lock_type)
                lock.lock()
        if bit_to_remove is not None:
            self.remove_bit(actor_sim_id, target_sim_id, bit_to_remove, notify_client=False)
        if bit_to_add.exclusive:
            services.relationship_service().remove_exclusive_relationship_bit(actor_sim_id, bit_to_add)
            if bit_to_add.directionality == RelationshipDirection.BIDIRECTIONAL:
                services.relationship_service().remove_exclusive_relationship_bit(target_sim_id, bit_to_add)
        if bit_to_add.is_trope_bit and actor_sim_info is not None:
            actor_sim_info.genealogy.set_relationship_trope(target_sim_id, bit_to_add.guid64)
        bit_instance = bit_to_add()
        rel_data.add_bit(bit_to_add, bit_instance, from_load=from_load)
        logger.debug('Added bit {} for {}', bit_to_add, self)
        if bit_to_add.counts_as_incest:
            self._counts_as_incest = True
        self._invoke_bit_added(actor_sim_id, bit_to_add)
        if notify_client is True:
            self.send_relationship_info()
        if send_rel_change_event:
            self._send_relationship_changed_event(actor_sim_info, target_sim_info, bidirectional=bit_to_add.directionality == RelationshipDirection.BIDIRECTIONAL)
        return True

    def add_reincarnation_bits(self, previous_sim_id:'int', new_sim_info:'SimInfo') -> 'None':
        reincarnation_bits_to_add = set()
        for bit in self.get_bits(previous_sim_id):
            if bit.reincarnation_bits is not None:
                reincarnation_bits_to_add.update(bit.reincarnation_bits)
        target_sim_id = self.get_other_sim_id(previous_sim_id)
        for new_bit in reincarnation_bits_to_add:
            new_sim_info.relationship_tracker.add_relationship_bit(target_sim_id, new_bit)

    def _get_all_bits(self, actor_sim_id):
        return itertools.chain(self._bi_directional_relationship_data.bit_types)

    def _invoke_bit_added(self, actor_sim_id, bit_to_add):
        self._bi_directional_relationship_data.track_tracker.on_relationship_bit_added(bit_to_add, actor_sim_id)

    @staticmethod
    def _validate_sim_home_zones(sim_info_a:'SimInfo', sim_info_b:'SimInfo') -> 'Optional[Tuple[int]]':
        household_a = sim_info_a.household
        household_b = sim_info_b.household
        if household_a is None or household_b is None:
            return
        home_zone_id_a = household_a.home_zone_id
        home_zone_id_b = household_b.home_zone_id
        if home_zone_id_a == home_zone_id_b:
            return
        if home_zone_id_a == 0 or home_zone_id_b == 0:
            return
        return (home_zone_id_a, home_zone_id_b)

    def add_neighbor_bit(self, sim_info_a:'SimInfo', sim_info_b:'SimInfo') -> 'None':
        home_zones = self._validate_sim_home_zones(sim_info_a, sim_info_b)
        if home_zones is None:
            return
        (home_zone_id_a, home_zone_id_b) = home_zones
        persistence_service = services.get_persistence_service()
        sim_a_home_zone_proto_buffer = persistence_service.get_zone_proto_buff(home_zone_id_a)
        sim_b_home_zone_proto_buffer = persistence_service.get_zone_proto_buff(home_zone_id_b)
        if sim_a_home_zone_proto_buffer is None or sim_b_home_zone_proto_buffer is None:
            logger.error('Invalid zone protocol buffer in Relationship.add_neighbor_bit_if_necessary() between {} and {}', sim_info_a, sim_info_b)
            return
        if sim_a_home_zone_proto_buffer.world_id != sim_b_home_zone_proto_buffer.world_id:
            return
        self.add_relationship_bit(sim_info_a.id, sim_info_b.id, RelationshipGlobalTuning.NEIGHBOR_RELATIONSHIP_BIT, notify_client=False)

    def add_multi_unit_neighbor_bit(self, sim_info_a:'SimInfo', sim_info_b:'SimInfo') -> 'None':
        home_zones = self._validate_sim_home_zones(sim_info_a, sim_info_b)
        if home_zones is None:
            return
        (home_zone_id_a, home_zone_id_b) = home_zones
        plex_service = services.get_plex_service()
        master_zone_id_a = plex_service.get_master_zone_id(home_zone_id_a)
        master_zone_id_b = plex_service.get_master_zone_id(home_zone_id_b)
        if master_zone_id_a != master_zone_id_b:
            return
        self.add_relationship_bit(sim_info_a.id, sim_info_b.id, RelationshipGlobalTuning.MULTI_UNIT_NEIGHBOR_RELATIONSHIP_BIT, notify_client=False)

    def add_neighbor_bit_if_necessary(self) -> 'None':
        sim_info_a = self.find_sim_info_a()
        if sim_info_a is None:
            return
        sim_info_b = self.find_sim_info_b()
        if sim_info_b is None:
            return
        self.add_neighbor_bit(sim_info_a, sim_info_b)
        self.add_multi_unit_neighbor_bit(sim_info_a, sim_info_b)

    def _remove_bit(self, actor_sim_id, bit):
        rel_data = self._get_rel_data_for_bit(actor_sim_id, bit)
        rel_data.remove_bit(bit)
        if bit.counts_as_incest:
            self._counts_as_incest = None
        self._invoke_bit_removed(actor_sim_id, bit)

    def remove_bit_by_collection_id(self, actor_sim_id, target_sim_id, collection_id, notify_client=True, send_rel_change_event=True):
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        has_bidirectional_update = False
        bits_to_remove = []
        for bit_type in self.get_bits(target_sim_id):
            if collection_id in bit_type.collection_ids:
                if bit_type.directionality == RelationshipDirection.BIDIRECTIONAL:
                    has_bidirectional_update = True
                bits_to_remove.append(bit_type)
        if send_rel_change_event:
            self._send_relationship_prechange_event(actor_sim_info, target_sim_info, bidirectional=has_bidirectional_update, bits_of_interest=bits_to_remove)
        for bit in bits_to_remove:
            self._remove_bit(actor_sim_id, bit)
        if notify_client:
            self.send_relationship_info()
        if send_rel_change_event:
            self._send_relationship_changed_event(actor_sim_info, target_sim_info, bidirectional=has_bidirectional_update)

    def remove_bit(self, actor_sim_id, target_sim_id, bit, notify_client=True, send_rel_change_event=True):
        if bit is None:
            logger.error('Error: Sim Id: {} trying to remove a None relationship bit to Sim_Id: {}.', actor_sim_id, target_sim_id)
            return
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        if bit.is_trope_bit and actor_sim_info is not None:
            actor_sim_info.genealogy.remove_relationship_trope(target_sim_info.sim_id, bit)
            if bit.directionality == RelationshipDirection.BIDIRECTIONAL:
                target_sim_info.genealogy.remove_relationship_trope(actor_sim_info.sim_id, bit)
        if send_rel_change_event:
            self._send_relationship_prechange_event(actor_sim_info, target_sim_info, bidirectional=bit.directionality == RelationshipDirection.BIDIRECTIONAL, bits_of_interest=(bit,))
        self._remove_bit(actor_sim_id, bit)
        if notify_client is True:
            self.send_relationship_info()
        if self.is_object_rel or send_rel_change_event:
            self._send_relationship_changed_event(actor_sim_info, target_sim_info, bidirectional=bit.directionality == RelationshipDirection.BIDIRECTIONAL)

    def _invoke_bit_removed(self, actor_sim_id, bit):
        self.bidirectional_track_tracker.on_relationship_bit_removed(bit, actor_sim_id)

    def _get_rel_data_for_bit(self, actor_sim_id, bit):
        if bit.directionality == RelationshipDirection.BIDIRECTIONAL:
            return self._bi_directional_relationship_data

    def has_bit(self, sim_id, bit):
        return any(bit.matches_bit(bit_type) for bit_type in self._bi_directional_relationship_data.bit_types)

    def remove_track(self, actor_sim_id, target_sim_id, track, notify_client=True, send_rel_change_event=True):
        if track is None:
            logger.error('Error: Sim Id: {} trying to remove a None relationship track to Sim_Id: {}.', actor_sim_id, target_sim_id)
            return
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        if send_rel_change_event:
            self._send_relationship_prechange_event(actor_sim_info, target_sim_info, bidirectional=track.track_type == RelationshipTrackType.RELATIONSHIP)
        self.get_track_relationship_data(actor_sim_id, track).remove_track(track)
        if notify_client is True:
            self.send_relationship_info()
        if self.is_object_rel or send_rel_change_event:
            self._send_relationship_changed_event(actor_sim_info, target_sim_info, bidirectional=track.track_type == RelationshipTrackType.RELATIONSHIP)

    def has_track(self, sim_id, relationship_track):
        return self.get_track_relationship_data(sim_id, relationship_track).has_track(relationship_track)

    def get_bits(self, sim_id):
        return tuple(self._bi_directional_relationship_data.bit_types)

    def get_bit_instances(self, sim_id):
        return tuple(self._bi_directional_relationship_data.bit_instances)

    def get_highest_priority_bit(self, sim_id):
        highest_priority_bit = None
        for bit in self.get_bits(sim_id):
            if not highest_priority_bit is None:
                if bit.priority > highest_priority_bit.priority:
                    highest_priority_bit = bit
            highest_priority_bit = bit
        return highest_priority_bit

    def add_relationship_appropriateness_buffs(self, sim_id):
        sim_info = services.sim_info_manager().get(sim_id)
        for bit in self.get_bit_instances(sim_id):
            bit.add_appropriateness_buffs(sim_info)

    def _create_culling_alarm(self):
        self._destroy_culling_alarm()
        time_range = date_and_time.create_time_span(minutes=RelationshipGlobalTuning.DELAY_UNTIL_RELATIONSHIP_IS_CULLED)
        self._culling_alarm_handle = alarms.add_alarm(self, time_range, self._cull_relationship_callback, cross_zone=True)

    def _destroy_culling_alarm(self):
        if self._culling_alarm_handle is not None:
            alarms.cancel_alarm(self._culling_alarm_handle)
            self._culling_alarm_handle = None

    def _cull_relationship_callback(self, _):
        self._destroy_culling_alarm()
        if self.can_cull_relationship():
            logger.debug('Culling {}', self)
            services.relationship_service().destroy_relationship(self._sim_id_a, self._sim_id_b)
        else:
            logger.warn("Attempting to cull {} but it's no longer allowed.", self)

    def can_cull_relationship(self, consider_convergence=True):
        sim_info_a = self.find_sim_info_a()
        sim_info_b = self.find_sim_info_b()
        if sim_info_a is not None and sim_info_b is not None and sim_info_a.household_id == sim_info_b.household_id:
            return False
        is_played_relationship = sim_info_a is not None and (sim_info_b is not None and (sim_info_a.is_player_sim or sim_info_b.is_player_sim))
        return self._bi_directional_relationship_data.can_cull_relationship(consider_convergence, is_played_relationship)

    def apply_relationship_multipliers(self, sim_id, relationship_multipliers):
        for (track_type, multiplier) in relationship_multipliers.items():
            relationship_track = self._bi_directional_relationship_data.get_track(track_type, add=False)
            if relationship_track is not None:
                relationship_track.add_statistic_multiplier(multiplier)

    def remove_relationship_multipliers(self, sim_id, relationship_multipliers):
        for (track_type, multiplier) in relationship_multipliers.items():
            relationship_track = self._bi_directional_relationship_data.get_track(track_type, add=False)
            if relationship_track is not None:
                relationship_track.remove_statistic_multiplier(multiplier)

    def _send_relationship_prechange_event(self, sim_info_a, sim_info_b, bidirectional=True, bits_of_interest=None):
        if sim_info_a is None or sim_info_b is None:
            return
        if bits_of_interest is not None:
            custom_keys = bits_of_interest
        else:
            custom_keys = ()
        services.get_event_manager().process_event(event_testing.test_events.TestEvent.PrerelationshipChanged, sim_info_a, sim_id=sim_info_a.id, target_sim_id=sim_info_b.id, custom_keys=custom_keys)
        if bidirectional:
            services.get_event_manager().process_event(event_testing.test_events.TestEvent.PrerelationshipChanged, sim_info_b, sim_id=sim_info_b.id, target_sim_id=sim_info_a.id, custom_keys=custom_keys)

    def _send_relationship_changed_event(self, sim_info_a, sim_info_b, bidirectional=True):
        if sim_info_a is None or sim_info_b is None:
            return
        services.get_event_manager().process_event(event_testing.test_events.TestEvent.RelationshipChanged, sim_info_a, sim_id=sim_info_a.id, target_sim_id=sim_info_b.id)
        if bidirectional:
            services.get_event_manager().process_event(event_testing.test_events.TestEvent.RelationshipChanged, sim_info_b, sim_id=sim_info_b.id, target_sim_id=sim_info_a.id)

    def save_relationship(self, relationship_msg):
        relationship_msg.sim_id_a = self._sim_id_a
        relationship_msg.sim_id_b = self._sim_id_b
        self._bi_directional_relationship_data.save_relationship_data(relationship_msg.bidirectional_relationship_data)
        relationship_msg.last_update_time = self._last_update_time
        relationship_msg.hidden = self._hidden

    def load_relationship(self, relationship_msg):
        self._bi_directional_relationship_data.load_relationship_data(relationship_msg.bidirectional_relationship_data)
        self._last_update_time = relationship_msg.last_update_time
        self._hidden = relationship_msg.hidden

    def build_printable_string_of_bits(self, sim_id):
        return '\t\t{}'.format('\n\t\t'.join(map(str, self.get_bit_instances(sim_id))))

    def build_printable_string_of_tracks(self):
        ret = ''
        for track in self._bi_directional_relationship_data.track_tracker:
            ret += '\t\t{} = {}; decaying? {}; decay rate: {}; track type: {}\n'.format(track, track.get_value(), track.decay_enabled, track.get_decay_rate(), track.track_type)
        return ret

    def _send_destroy_message_to_client(self):
        msg_a = commodity_protocol.RelationshipDelete()
        msg_a.actor_sim_id = self._sim_id_a
        msg_a.target_id = self._sim_id_b
        op_a = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SIM_RELATIONSHIP_DELETE, msg_a)
        distributor = Distributor.instance()
        distributor.add_op(self.find_sim_info_a(), op_a)
        if not self.is_object_rel:
            msg_b = commodity_protocol.RelationshipDelete()
            msg_b.actor_sim_id = self._sim_id_b
            msg_b.target_id = self._sim_id_a
            op_b = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SIM_RELATIONSHIP_DELETE, msg_b)
            distributor.add_op(self.find_sim_info_b(), op_b)

    def notify_relationship_on_lod_change(self, old_lod, new_lod):
        pass

    def destroy(self, notify_client=True):
        if notify_client:
            self._send_destroy_message_to_client()
        self._bi_directional_relationship_data.destroy()
        self._destroy_culling_alarm()

    def get_all_relationship_bit_locks(self, sim_id):
        return list(self._bi_directional_relationship_data.get_all_locks())

    def get_relationship_bit_lock(self, sim_id, lock_type):
        return self._bi_directional_relationship_data.get_lock(lock_type)

    def on_sim_creation(self, sim):
        self._bi_directional_relationship_data.on_sim_creation(sim)

    @classproperty
    def is_object_rel(cls):
        raise NotImplementedError()
