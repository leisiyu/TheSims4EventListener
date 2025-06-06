from __future__ import annotationsimport itertoolsfrom _collections import defaultdictfrom contextlib import contextmanagerfrom protocolbuffers import GameplaySaveData_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom protocolbuffers.ResourceKey_pb2 import ResourceKeyfrom protocolbuffers.UI_pb2 import HovertipCreatedfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom relationships.data.relationship_label_data import RelationshipLabelDatafrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.neighbor_bit_fixup_helper import NeighborBitFixupHelperfrom relationships.relationship_objects.object_relationship import ObjectRelationshipfrom relationships.relationship_objects.relationship import Relationshipfrom relationships.relationship_objects.sim_relationship import SimRelationshipfrom relationships.relationship_enums import RelationshipDirectionfrom relationships.relationship_track import ObjectRelationshipTrack, RelationshipTrackfrom relationships.relationship_tracker_tuning import DefaultRelationshipInHousehold, DefaultGenealogyLinkfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.callback_utils import CallableListfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom singletons import DEFAULTimport cachesimport persistence_error_typesimport servicesimport sims4.logimport stringfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from event_testing.test_events import TestEvent
    from sims.sim_info import SimInfo
    from typing import *logger = sims4.log.Logger('Relationship', default_owner='mjuskelis')
class RelationshipTimeoutSeed:

    def __init__(self):
        self.timeout_bit_id_hash = 0
        self.elapsed_time = 0

class RelationshipTrackSeed:

    def __init__(self):
        self.track_id = 0
        self.value = 0
        self.visible = False
        self.ticks_until_decay_begins = -1

class RelationshipKnowledgeSeed:

    def __init__(self):
        self.trait_ids = []
        self.knows_career = False
        self.stats = []

class UnidirectionalRelationshipSeed:

    def __init__(self):
        self.bits = []
        self.timeouts = []
        self.knowledge = None
        self.bit_added_buffs = []
        self.tracks = []

    @property
    def relationship_bit_locks(self):
        return ()

    def HasField(self, field_name):
        if field_name == 'knowledge':
            return self.knowledge is not None
        return False

class BidirectionalRelationshipSeed:

    def __init__(self):
        self.bits = []
        self.timeouts = []
        self.tracks = []

    @property
    def relationship_bit_locks(self):
        return ()

    def HasField(self, field_name):
        return False

class RelationshipSeed:

    def __init__(self):
        self.sim_id_a = 0
        self.sim_id_b = 0
        self.bidirectional_relationship_data = BidirectionalRelationshipSeed()
        self.sim_a_relationship_data = UnidirectionalRelationshipSeed()
        self.sim_b_relationship_data = UnidirectionalRelationshipSeed()
        self.last_update_time = 0

class LegacyRelationshipData:

    def __init__(self):
        self.target_id = 0
        self.bits = []
        self.bit_added_buffs = []
        self.bit_timeout_data = {}
        self.last_update_time = None
        self.relationship_track_data = {}
        self.knowledge = None
        self.processed = False

    def load_legacy_data(self, relationship_msg):
        self.target_id = relationship_msg.target_id
        for bit_guid in relationship_msg.bits:
            self.bits.append(bit_guid)
        for timeout_data in relationship_msg.timeouts:
            relationship_timeout_data = RelationshipTimeoutSeed()
            relationship_timeout_data.timeout_bit_id_hash = timeout_data.timeout_bit_id_hash
            relationship_timeout_data.elapsed_time = timeout_data.elapsed_time
            self.bit_timeout_data[timeout_data.timeout_bit_id_hash] = relationship_timeout_data
        for bit_added_buff in relationship_msg.bit_added_buffs:
            self.bit_added_buffs.append(bit_added_buff.bit_id)
        self.last_update_time = relationship_msg.last_update_time
        if relationship_msg.HasField('knowledge'):
            self.knowledge = RelationshipKnowledgeSeed()
            for trait_guid in relationship_msg.knowledge.trait_ids:
                self.knowledge.trait_ids.append(trait_guid)
            self.knowledge.knows_career = relationship_msg.knowledge.knows_career
            for stat_guid in relationship_msg.knowledge.stats:
                self.knowledge.stats.append(stat_guid)
        for track_data in relationship_msg.tracks:
            rel_track_data = RelationshipTrackSeed()
            rel_track_data.track_id = track_data.track_id
            rel_track_data.value = track_data.value
            rel_track_data.visible = track_data.visible
            rel_track_data.ticks_until_decay_begins = track_data.ticks_until_decay_begins
            self.relationship_track_data[track_data.track_id] = rel_track_data

class RelationshipService(Service):
    NEIGHBORHOOD_BIT_VALIDATION_EVENTS = (TestEvent.SimHomeZoneChanged,)
    ALL_EVENTS = NEIGHBORHOOD_BIT_VALIDATION_EVENTS

    def __init__(self):
        self._relationships = {}
        self._object_relationships = {}
        self._sim_relationships = defaultdict(list)
        self._sim_object_relationships = defaultdict(list)
        self._object_sim_relationships = defaultdict(list)
        self._tag_set_to_ids_map = {}
        self._def_id_to_tag_set_map = {}
        self._relationship_multipliers = defaultdict(dict)
        self._create_relationship_callbacks = defaultdict(CallableList)
        self._suppress_client_updates = False
        self._legacy_relationship_data_storage = defaultdict(dict)
        self._pre_on_all_households_and_sim_infos_loaded = True

    def __iter__(self):
        yield from self._relationships.values()

    def __len__(self):
        return len(self._relationships.values())

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_RELATIONSHIP_SERVICE

    @contextmanager
    def suppress_client_updates_context_manager(self):
        self._suppress_client_updates = True
        try:
            yield None
        finally:
            self._suppress_client_updates = False

    @property
    def suppress_client_updates(self):
        return self._suppress_client_updates

    def save(self, save_slot_data=None, **kwargs):
        rel_service_msg = GameplaySaveData_pb2.PersistableRelationshipService()
        for relationship in self._relationships.values():
            with ProtocolBufferRollback(rel_service_msg.relationships) as relationship_msg:
                relationship.save_relationship(relationship_msg)
        for object_relationship in self._object_relationships.values():
            with ProtocolBufferRollback(rel_service_msg.object_relationships) as relationship_msg:
                object_relationship.save_relationship(relationship_msg)
        save_slot_data.gameplay_data.relationship_service = rel_service_msg

    def load(self, zone_data=None):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        with self.suppress_client_updates_context_manager():
            for relationship_msg in save_slot_data_msg.gameplay_data.relationship_service.relationships:
                try:
                    relationship = self._find_relationship(relationship_msg.sim_id_a, relationship_msg.sim_id_b, create=True)
                    relationship.load_relationship(relationship_msg)
                except:
                    logger.exception('Exception encountered when trying to load relationship between {} and {}', relationship_msg.sim_id_a, relationship_msg.sim_id_b)
                    self.destroy_relationship(relationship_msg.sim_id_a, relationship_msg.sim_id_b)
            for relationship_msg in save_slot_data_msg.gameplay_data.relationship_service.object_relationships:
                try:
                    relationship = self._find_object_relationship(relationship_msg.sim_id_a, None, target_def_id=relationship_msg.sim_id_b, from_load=True, create=True)
                    if relationship is not None:
                        relationship.load_relationship(relationship_msg)
                except:
                    logger.exception('Exception encountered when trying to load relationship between {} and {}', relationship_msg.sim_id_a, relationship_msg.sim_id_b)
                    self.destroy_object_relationship(relationship_msg.sim_id_a, relationship_msg.sim_id_b)

    def start(self) -> 'None':
        services.get_event_manager().register(self, self.ALL_EVENTS)

    def shutdown(self) -> 'None':
        services.get_event_manager().unregister(self, self.ALL_EVENTS)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        if event == TestEvent.SimHomeZoneChanged:
            old_zone_id = resolver.get_resolved_arg('old_zone_id')
            new_zone_id = resolver.get_resolved_arg('new_zone_id')
            if old_zone_id == new_zone_id:
                return
            neighbor_bit_fixup_helper = NeighborBitFixupHelper()
            neighbor_bit_fixup_helper.handle_sim_home_zone_changed(sim_info, old_zone_id, new_zone_id)

    def add_create_relationship_listener(self, sim_id, callback):
        if callback not in self._create_relationship_callbacks[sim_id]:
            self._create_relationship_callbacks[sim_id].append(callback)

    def remove_create_relationship_listener(self, sim_id, callback):
        if callback in self._create_relationship_callbacks[sim_id]:
            self._create_relationship_callbacks[sim_id].remove(callback)
        else:
            logger.info('callback {} not in create_relationship_callbacks for sim_id {}. This might caused by updating MIN LOD on relationship tracker execute before trait tracker', callback, sim_id)
        if not self._create_relationship_callbacks[sim_id]:
            del self._create_relationship_callbacks[sim_id]

    def create_relationship(self, sim_id_a:'int', sim_id_b:'int'):
        return self._find_relationship(sim_id_a, sim_id_b, create=True)

    def destroy_relationship(self, sim_id_a:'int', sim_id_b:'int', notify_client=True):
        key = self._get_key_tuple(sim_id_a, sim_id_b)
        relationship = self._relationships.pop(key, None)
        if relationship is None:
            return
        relationship.destroy(notify_client=notify_client)
        self._sim_relationships[sim_id_a].remove(relationship)
        self._sim_relationships[sim_id_b].remove(relationship)

    def _clear_relationships(self):
        for relationship in self._relationships.values():
            relationship.destroy(notify_client=False)
        self._relationships.clear()
        self._sim_relationships.clear()

    def notify_all_relationships_on_lod_change(self, sim_id, old_lod, new_lod):
        for relationship in self._get_relationships_for_sim(sim_id):
            relationship.notify_relationship_on_lod_change(old_lod, new_lod)

    def destroy_all_relationships(self, sim_id:'int'):
        for relationship in self._get_relationships_for_sim(sim_id):
            self.destroy_relationship(relationship.sim_id_a, relationship.sim_id_b)

    def _can_create_relationship(self, sim_id_a, sim_id_b):
        sim_info_manager = services.sim_info_manager()
        if sim_info_manager is None:
            return True
        sim_info_a = sim_info_manager.get(sim_id_a)
        if sim_info_a is not None and sim_info_a.lod == SimInfoLODLevel.MINIMUM:
            return False
        else:
            sim_info_b = sim_info_manager.get(sim_id_b)
            if sim_info_b is not None and sim_info_b.lod == SimInfoLODLevel.MINIMUM:
                return False
        return True

    def send_all_relationship_info(self):
        for relationship in self._relationships.values():
            relationship.send_relationship_info()

    def send_relationship_info(self, sim_id, target_sim_id=None, allow_sending_npc_info=False):
        if target_sim_id is None:
            for relationship in self._get_relationships_for_sim(sim_id):
                relationship.send_relationship_info(send_npc_relationship=allow_sending_npc_info)
        else:
            relationship = self._find_relationship(sim_id, target_sim_id)
            if relationship is not None:
                relationship.send_relationship_info(send_npc_relationship=allow_sending_npc_info)

    def create_relationships_msg_info(self, sim_id):
        override_owner_relationships = []
        for relationship in self._get_relationships_for_sim(sim_id):
            sim_info_a = relationship.find_sim_info_a()
            sim_info_b = relationship.find_sim_info_b()
            if sim_info_a is not None:
                msg_relationship = relationship._build_relationship_update_proto(sim_info_a, relationship._sim_id_b)
                override_owner_relationships.append(msg_relationship)
            if sim_info_b is not None:
                msg_relationship = relationship._build_relationship_update_proto(sim_info_b, relationship._sim_id_a)
                override_owner_relationships.append(msg_relationship)
        return override_owner_relationships

    def clean_and_send_remaining_relationship_info(self, sim_id):
        sim_info_manager = services.sim_info_manager()
        for relationship in self._get_relationships_for_sim(sim_id):
            other_sim_id = relationship.get_other_sim_id(sim_id)
            if other_sim_id in sim_info_manager:
                relationship.send_relationship_info()
            else:
                self.destroy_relationship(sim_id, other_sim_id, notify_client=False)

    def on_all_households_and_sim_infos_loaded(self, client):
        self._process_legacy_relationship_data()
        sim_info_manager = services.sim_info_manager()
        self._pre_on_all_households_and_sim_infos_loaded = False
        for (sim_ids, relationship) in tuple(self._relationships.items()):
            sim_id_a = sim_ids[0]
            sim_id_b = sim_ids[1]
            sim_info_a = sim_info_manager.get(sim_id_a)
            sim_info_b = sim_info_manager.get(sim_id_b)
            if sim_info_a.is_player_sim or sim_info_b.is_player_sim:
                relationship.enable_player_sim_track_decay()
            relationship.bidirectional_track_tracker.set_callback_alarm_calculation_supression(False)
            rel_bits = relationship.get_bits(sim_id_a)
            for rel_bit in rel_bits:
                if rel_bit.is_trope_bit and sim_info_a is not None:
                    sim_info_a.genealogy.set_relationship_trope(sim_id_b, rel_bit.guid64)
            if not sim_info_a.needs_preference_traits_fixup:
                if sim_info_b.needs_preference_traits_fixup:
                    relationship.refresh_knowledge()
                    relationship.update_compatibility()
            relationship.refresh_knowledge()
            relationship.update_compatibility()
        neighbor_bit_fixup_helper = NeighborBitFixupHelper()
        neighbor_bit_fixup_helper.add_neighbor_bits()

    def purge_invalid_relationships(self):
        sim_info_manager = services.sim_info_manager()
        for (sim_ids, relationship) in tuple(self._relationships.items()):
            sim_id_a = sim_ids[0]
            sim_id_b = sim_ids[1]
            sim_info_a = sim_info_manager.get(sim_id_a)
            sim_info_b = sim_info_manager.get(sim_id_b)
            if sim_info_a is None or sim_info_b is None:
                self.destroy_relationship(sim_id_a, sim_id_b, notify_client=False)
            else:
                if not sim_info_a.lod == SimInfoLODLevel.MINIMUM:
                    if sim_info_b.lod == SimInfoLODLevel.MINIMUM:
                        logger.error('Rel Tracker found/deleted a rel with a Min LOD between Sim A: {} Sim B: {}', sim_info_a, sim_info_b)
                        self.destroy_relationship(sim_id_a, sim_id_b, notify_client=False)
                logger.error('Rel Tracker found/deleted a rel with a Min LOD between Sim A: {} Sim B: {}', sim_info_a, sim_info_b)
                self.destroy_relationship(sim_id_a, sim_id_b, notify_client=False)

    def on_sim_creation(self, sim):
        for relationship in self._sim_relationships[sim.sim_id]:
            relationship.on_sim_creation(sim)

    @caches.cached
    def get_relationship_score(self, sim_id_a:'int', sim_id_b:'int', track=DEFAULT):
        if track is DEFAULT:
            track = RelationshipGlobalTuning.REL_INSPECTOR_TRACK
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is not None:
            return relationship.get_track_score(sim_id_a, track)
        else:
            return RelationshipGlobalTuning.DEFAULT_RELATIONSHIP_VALUE

    def add_relationship_score(self, sim_id_a:'int', sim_id_b:'int', increment, track=DEFAULT, threshold=None, **kwargs):
        if track is DEFAULT:
            track = RelationshipGlobalTuning.REL_INSPECTOR_TRACK
        if sim_id_a == sim_id_b:
            return
        relationship = self._find_relationship(sim_id_a, sim_id_b, True)
        if relationship is not None:
            if threshold is None or threshold.compare(relationship.get_track_score(sim_id_a, track)):
                relationship.add_track_score(sim_id_a, increment, track, apply_cross_age_multipliers=True, **kwargs)
                logger.debug('Adding to score to track {} for {}: += {}; new score = {}', track, relationship, increment, relationship.get_track_score(sim_id_a, track))
            else:
                logger.debug('Attempting to add to track {} for {} but {} not within threshold {}', track, relationship, relationship.get_track_score(sim_id_a, track), threshold)
        else:
            logger.error('relationship_tracker.add_relationship_score() could not find/create a relationship between: Sim = {} TargetSimId = {}', sim_id_a, sim_id_b)

    def set_can_add_reltrack(self, sim_id_a:'int', sim_id_b:'int', can_add:'bool'):
        relationship = self._find_relationship(sim_id_a, sim_id_b, True)
        if relationship is not None:
            relationship.bidirectional_track_tracker.can_add_reltrack = can_add
            relationship.sentiment_track_tracker(sim_id_a).can_add_reltrack = can_add
            logger.debug('Setting can_add_reltrack to {} for Sim = {} TargetSimId = {}', can_add, sim_id_a, sim_id_b)
        else:
            logger.error('relationship_tracker.set_can_add_reltrack() could not find/create a relationship between: Sim = {} TargetSimId = {}', sim_id_a, sim_id_b)

    def set_track_to_max(self, sim_id_a:'int', sim_id_b:'int', track):
        if sim_id_a == sim_id_b:
            logger.debug('Error, attempting to set a track {} for sim {} on itself', track, sim_id_a)
            return
        relationship = self._find_relationship(sim_id_a, sim_id_b, True)
        if relationship is not None:
            relationship.set_track_to_max(sim_id_a, track)
            logger.debug('Adding track {} for {}: new score = {}', track, relationship, relationship.get_track_score(sim_id_a, track))
        else:
            logger.error('relationship_tracker.set_track_to_max() could not find/create a relationship between: Sim = {} TargetSimId = {}', sim_id_a, sim_id_b)

    def set_relationship_score(self, sim_id_a:'int', sim_id_b:'int', value, track=DEFAULT, threshold=None, **kwargs):
        if sim_id_a == sim_id_b:
            return
        relationship = self._find_relationship(sim_id_a, sim_id_b, True)
        if relationship is not None:
            relationship.set_relationship_score(sim_id_a, value, track=track, threshold=threshold, **kwargs)
        else:
            logger.error('relationship_tracker.set_relationship_score() could not find/create a relationship between: Sim = {} TargetSimId = {}', sim_id_a, sim_id_b)

    def enable_player_sim_track_decay(self, sim_id, to_enable=True):
        logger.debug('Enabling ({}) decay for player sim: {}'.format(to_enable, sim_id))
        for relationship in self._get_relationships_for_sim(sim_id):
            relationship.enable_player_sim_track_decay(to_enable)
        for obj_relationship in self._get_object_relationships_for_sim(sim_id):
            obj_relationship.enable_player_sim_track_decay(to_enable)

    def get_relationship_prevailing_short_term_context_track(self, sim_id_a:'int', sim_id_b:'int'):
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is not None:
            return relationship.get_prevailing_short_term_context_track(sim_id_a)

    def has_relationship_track(self, sim_id_a, sim_id_b, relationship_track):
        relationship = self._find_relationship(sim_id_a, sim_id_b, False)
        if relationship is None:
            return False
        return relationship.has_track(sim_id_a, relationship_track)

    def get_relationship_track(self, sim_id_a:'int', sim_id_b:'int', track=DEFAULT, add=False):
        with self.suppress_client_updates_context_manager():
            if track is DEFAULT:
                track = RelationshipGlobalTuning.REL_INSPECTOR_TRACK
            relationship = self._find_relationship(sim_id_a, sim_id_b, add)
            if relationship is not None:
                return relationship.get_track(sim_id_a, track, add)
            if add:
                logger.error('relationship_tracker.get_relationship_track() failed to create a relationship between Sim: {} TargetId: {}', sim_id_a, sim_id_b)
            return

    def relationship_tracks_gen(self, sim_id_a:'int', sim_id_b:'int', track_type=None):
        with self.suppress_client_updates_context_manager():
            relationship = self._find_relationship(sim_id_a, sim_id_b)
            if relationship is not None:
                yield from relationship.relationship_tracks_gen(sim_id_a, track_type=track_type)

    def add_relationship_multipliers(self, sim_id:'int', handle, relationship_multipliers):
        if not relationship_multipliers:
            return
        tested_multipliers = dict()
        sim_info_manager = services.sim_info_manager()
        sim_info = sim_info_manager.get(sim_id)
        if sim_info is not None:
            resolver = SingleSimResolver(sim_info)
            for (track, multiplier) in relationship_multipliers.items():
                if multiplier.tests is not None:
                    if multiplier.tests.run_tests(resolver):
                        tested_multipliers[track] = multiplier
                        tested_multipliers[track] = multiplier
                else:
                    tested_multipliers[track] = multiplier
        for relationship in self._get_relationships_for_sim(sim_id):
            relationship.apply_relationship_multipliers(sim_id, tested_multipliers)
        self._relationship_multipliers[sim_id][handle] = tested_multipliers

    def remove_relationship_multipliers(self, sim_id:'int', handle):
        relationship_multipliers = self._relationship_multipliers[sim_id].pop(handle, None)
        if not self._relationship_multipliers[sim_id]:
            del self._relationship_multipliers[sim_id]
        if relationship_multipliers is None:
            return
        for relationship in self._get_relationships_for_sim(sim_id):
            relationship.remove_relationship_multipliers(sim_id, relationship_multipliers)

    def get_relationship_multipliers_for_sim(self, sim_id):
        if sim_id in self._relationship_multipliers:
            return tuple(self._relationship_multipliers[sim_id].values())
        return tuple()

    def on_added_to_social_group(self, sim_id_a:'int', sim_id_b:'int'):
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is not None:
            relationship.apply_social_group_decay()

    def on_removed_from_social_group(self, sim_id_a:'int', sim_id_b:'int'):
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is not None:
            relationship.remove_social_group_decay()

    def set_default_tracks(self, sim_id_a, sim_id_b, update_romance=True, family_member=False, default_track_overrides=None, bits_only=False):
        if sim_id_a == sim_id_b:
            return
        with self.suppress_client_updates_context_manager():
            sim_info_manager = services.sim_info_manager()
            sim_info_a = sim_info_manager.get(sim_id_a)
            sim_info_b = sim_info_manager.get(sim_id_b)
            relationship = self._find_relationship(sim_id_a, sim_id_b, create=True)
            if relationship is None:
                return
            for roomate_entry in DefaultRelationshipInHousehold.SPECIES_TO_ROOMATE_LINK:
                if sim_info_a.species == roomate_entry.species_actor and sim_info_b.species == roomate_entry.species_target:
                    key = roomate_entry.genealogy_link
                    break
            key = DefaultGenealogyLink.Roommate
            if family_member:
                for entry in DefaultRelationshipInHousehold.SPECIES_TO_FAMILY_MEMBER_LINK:
                    if sim_info_a.species == entry.species:
                        key = entry.genealogy_link
                        break
                key = DefaultGenealogyLink.FamilyMember
            if default_track_overrides is not None:
                key = default_track_overrides.get(sim_info_b, key)
            resolver = DoubleSimResolver(sim_info_a, sim_info_b)
            default_relationships = DefaultRelationshipInHousehold.RelationshipSetupMap.get(key)
            for default_relationship in default_relationships(resolver=resolver):
                default_relationship.apply(relationship, sim_id_a, sim_id_b, bits_only=bits_only)
            is_significant_other = False
            if sim_info_a.relationship_tracker.fiance_sim_id == sim_id_b:
                is_significant_other = True
                key = DefaultGenealogyLink.Fiance
            for b in sim_info_a.relationship_tracker.steady_sim_ids:
                if b == sim_id_b:
                    is_significant_other = True
                    key = DefaultGenealogyLink.Steady
                    break
            if sim_info_a.relationship_tracker.spouse_sim_id == sim_id_b:
                is_significant_other = True
                key = DefaultGenealogyLink.Spouse
            if update_romance and is_significant_other:
                default_relationships = DefaultRelationshipInHousehold.RelationshipSetupMap.get(key)
                for default_relationship in default_relationships(resolver=resolver):
                    default_relationship.apply(relationship, sim_id_a, sim_id_b, bits_only=bits_only)
                for (gender, gender_preference_statistic) in sim_info_a.get_gender_preferences_gen():
                    if gender_preference_statistic is None:
                        pass
                    elif gender == sim_info_b.gender:
                        gender_preference_statistic.set_value(gender_preference_statistic.max_value)
            logger.info('Set default tracks {:25} -> {:25} as {}', sim_info_a.full_name, sim_info_b.full_name, key)

    def add_relationship_bit(self, actor_sim_id:'int', target_sim_id:'int', bit_to_add, force_add=False, from_load=False, send_rel_change_event=True, allow_readdition=True):
        if not self._validate_bit(bit_to_add, actor_sim_id, target_sim_id):
            return
        relationship = self._find_relationship(actor_sim_id, target_sim_id, True)
        if not relationship:
            return
        if allow_readdition or relationship.has_bit(actor_sim_id, bit_to_add):
            return
        relationship.add_relationship_bit(actor_sim_id, target_sim_id, bit_to_add, force_add=force_add, from_load=from_load, send_rel_change_event=send_rel_change_event)

    def remove_relationship_bit(self, actor_sim_id, target_sim_id:'int', bit_to_remove, send_rel_change_event=True):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is None:
            return
        relationship.remove_bit(actor_sim_id, target_sim_id, bit_to_remove, send_rel_change_event=send_rel_change_event)

    def remove_relationship_bits(self, actor_sim_id, target_sim_id:'int', bits_to_remove, send_rel_change_event=True):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is None:
            return
        for bit_to_remove in bits_to_remove:
            relationship.remove_bit(actor_sim_id, target_sim_id, bit_to_remove, send_rel_change_event=send_rel_change_event)

    def remove_relationship_track(self, actor_sim_id, target_sim_id:'int', track_to_remove, send_rel_change_event=True):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is None:
            return
        relationship.remove_track(actor_sim_id, target_sim_id, track_to_remove, send_rel_change_event=send_rel_change_event)

    def remove_relationship_bit_by_collection_id(self, actor_sim_id, target_sim_id:'int', collection_id, notify_client=True, send_rel_change_event=True):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is None:
            return
        relationship.remove_bit_by_collection_id(actor_sim_id, target_sim_id, collection_id, notify_client=notify_client, send_rel_change_event=send_rel_change_event)

    def remove_exclusive_relationship_bit(self, actor_sim_id, bit):
        for relationship in self._get_relationships_for_sim(actor_sim_id):
            if relationship.has_bit(actor_sim_id, bit):
                relationship.remove_bit(actor_sim_id, relationship.get_other_sim_id(actor_sim_id), bit)
                return

    def get_all_bits(self, actor_sim_id, target_sim_id:'int'=None):
        bits = []
        if target_sim_id is None:
            for relationship in self._get_relationships_for_sim(actor_sim_id):
                bits.extend(relationship.get_bits(actor_sim_id))
        else:
            relationship = self._find_relationship(actor_sim_id, target_sim_id)
            if relationship is not None:
                bits.extend(relationship.get_bits(actor_sim_id))
        return bits

    def get_relationship_depth(self, actor_sim_id, target_sim_id:'int'):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.get_relationship_depth(actor_sim_id)
        else:
            return 0

    def has_bit(self, actor_sim_id, target_sim_id:'int', bit):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.has_bit(actor_sim_id, bit)
        else:
            return False

    def get_highest_priority_track_bit(self, actor_sim_id, target_sim_id):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.get_highest_priority_track_bit(actor_sim_id)
        else:
            return

    def get_highest_priority_bit(self, actor_sim_id, target_sim_id):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.get_highest_priority_bit()
        else:
            return

    def get_all_sim_relationships(self, sim_id):
        if sim_id in self._sim_relationships:
            return list(self._sim_relationships[sim_id])
        return []

    def target_sim_gen(self, sim_id):
        for relationship in self._get_relationships_for_sim(sim_id):
            yield relationship.get_other_sim_id(sim_id)

    def get_target_sim_infos(self, sim_id):
        return tuple(relationship.get_other_sim_info(sim_id) for relationship in self._get_relationships_for_sim(sim_id))

    def has_relationship(self, actor_sim_id, target_sim_id):
        return self._find_relationship(actor_sim_id, target_sim_id) is not None

    def get_is_considered_incest(self, actor_sim_id, target_sim_id):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.considered_incest
        return False

    def is_hidden(self, actor_sim_id:'int', target_sim_id:'int') -> 'bool':
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.is_hidden
        return False

    def hide_relationship(self, actor_sim_id:'int', target_sim_id:'int', value:'bool', notify_client:'bool'=True) -> 'None':
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            relationship.hide_relationship(value, notify_client)

    def get_hidden_relationships(self, actor_sim_id:'int') -> 'Optional[List[Relationship]]':
        hidden_relationships = [relationship for relationship in self._get_relationships_for_sim(actor_sim_id) if relationship is not None and relationship.is_hidden]
        return hidden_relationships

    def add_relationship_appropriateness_buffs(self, actor_sim_id, target_sim_id:'int'):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            relationship.add_relationship_appropriateness_buffs(actor_sim_id)

    def get_relationship_label_data(self, actor_sim_id:'int', target_sim_id:'int') -> 'Optional[RelationshipLabelData]':
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.get_relationship_label_data()

    def set_relationship_label_data(self, actor_sim_id:'int', target_sim_id:'int', label:'string', icon:'ResourceKey') -> 'None':
        relationship_label_data = self.get_relationship_label_data(actor_sim_id, target_sim_id)
        relationship_label_data.set_data(label, icon)
        self.send_relationship_info(actor_sim_id, target_sim_id)

    def get_knowledge(self, actor_sim_id, target_sim_id:'int', initialize=False):
        relationship = self._find_relationship(actor_sim_id, target_sim_id, create=initialize)
        if relationship is not None:
            return relationship.get_knowledge(actor_sim_id, target_sim_id, initialize=initialize)

    def update_all_known_npcs_commodities(self):
        sim_info_manager = services.sim_info_manager()
        active_household = services.active_household()
        active_sim_ids = [sim_info.id for sim_info in active_household.sim_infos]
        known_sim_ids = set()
        for active_sim_id in active_sim_ids:
            for target_sim_id in tuple(self.target_sim_gen(active_sim_id)):
                known_sim_ids.add(target_sim_id)
        for known_sim_id in known_sim_ids:
            known_sim_info = sim_info_manager.get(known_sim_id)
            if known_sim_info.is_player_sim is False:
                known_sim_info.commodity_tracker.send_commodity_progress_update()

    def add_known_trait(self, trait, actor_sim_id, target_sim_id:'int', notify_client=True):
        relationship = self._find_relationship(actor_sim_id, target_sim_id, True)
        if relationship is not None:
            knowledge = relationship.get_knowledge(actor_sim_id, target_sim_id, initialize=True)
            return knowledge.add_known_trait(trait, notify_client=notify_client)
        return False

    def remove_known_trait(self, trait, actor_sim_id, target_sim_id:'int', notify_client=True):
        relationship = self._find_relationship(actor_sim_id, target_sim_id, True)
        if relationship is not None:
            knowledge = relationship.get_knowledge(actor_sim_id, target_sim_id, initialize=True)
            knowledge.remove_known_trait(trait, notify_client=notify_client)

    def add_knows_romantic_preference(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id, initialize=True)
        if knowledge is not None:
            return knowledge.add_knows_romantic_preference(notify_client=notify_client)
        return False

    def remove_knows_romantic_preference(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            knowledge.remove_knows_romantic_preference(notify_client=notify_client)

    def add_knows_woohoo_preference(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id, initialize=True)
        if knowledge is not None:
            return knowledge.add_knows_woohoo_preference(notify_client=notify_client)
        return False

    def remove_knows_woohoo_preference(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            knowledge.remove_knows_woohoo_preference(notify_client=notify_client)

    def add_knows_relationship_expectations(self, actor_sim_id:'int', target_sim_id:'int', notify_client:'bool'=True) -> 'bool':
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            return knowledge.add_knows_relationship_expectations(notify_client)
        return False

    def remove_knows_relationship_expectations(self, actor_sim_id:'int', target_sim_id:'int', notify_client:'bool'=True) -> 'None':
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            knowledge.remove_knows_relationship_expectations(notify_client)

    def add_knows_career(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id, initialize=True)
        if knowledge is not None:
            return knowledge.add_knows_career(notify_client=notify_client)
        return False

    def remove_knows_career(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            knowledge.remove_knows_career(notify_client=notify_client)

    def add_knows_major(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            return knowledge.add_knows_major(notify_client=notify_client)
        return False

    def remove_knows_major(self, actor_sim_id, target_sim_id:'int', notify_client=True):
        knowledge = self.get_knowledge(actor_sim_id, target_sim_id)
        if knowledge is not None:
            knowledge.remove_knows_major(notify_client=notify_client)

    def print_relationship_info(self, actor_sim_id, target_sim_id:'int', _connection):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            sims4.commands.output('{}:\n\tTotal Depth: {}\n\tBits:\n{}\n\tTracks:\n{}'.format(relationship, relationship.get_relationship_depth(actor_sim_id), relationship.build_printable_string_of_bits(), relationship.build_printable_string_of_tracks()), _connection)
        else:
            sims4.commands.output('Relationship not found between {} and {}:\n\tTotal Depth: {}\n\tBits:\n{}\n\tTracks:\n{}'.format(actor_sim_id, target_sim_id, self.get_relationship_depth(actor_sim_id, target_sim_id), self._build_printable_string_of_bits(actor_sim_id, target_sim_id), self._build_printable_string_of_tracks(actor_sim_id, target_sim_id)), _connection)

    def relationship_decay_metrics(self, target_sim_id):
        relationship = self._find_relationship(target_sim_id)
        if relationship is None:
            return
        return relationship.get_decay_metrics()

    def _validate_bit(self, bit_to_add, actor_sim_id, target_id):
        if bit_to_add is None:
            logger.error('Attempting to add None bit to relationship for {} and {}', actor_sim_id, target_id)
            return False
        return True

    def _get_key_tuple(self, sim_id_a:'int', sim_id_b:'int'):
        if sim_id_a < sim_id_b:
            return (sim_id_a, sim_id_b)
        return (sim_id_b, sim_id_a)

    def _get_relationships_for_sim(self, sim_id):
        relationships = self._sim_relationships.get(sim_id, None)
        if relationships is None:
            return tuple()
        return tuple(relationships)

    def _find_relationship(self, sim_id_a:'int', sim_id_b:'int', create=False):
        if sim_id_a == sim_id_b:
            return
        key = self._get_key_tuple(sim_id_a, sim_id_b)
        relationship = self._relationships.get(key, None)
        if relationship is not None:
            return relationship
        if create:
            if not self._can_create_relationship(sim_id_a, sim_id_b):
                return
            else:
                logger.debug('Creating relationship for {0} and {1}', sim_id_a, sim_id_b)
                relationship = SimRelationship(sim_id_a, sim_id_b)
                if self._pre_on_all_households_and_sim_infos_loaded:
                    relationship.bidirectional_track_tracker.set_callback_alarm_calculation_supression(True)
                self._relationships[key] = relationship
                self._sim_relationships[sim_id_a].append(relationship)
                self._sim_relationships[sim_id_b].append(relationship)
                relationship.add_neighbor_bit_if_necessary()
                if sim_id_a in self._create_relationship_callbacks:
                    self._create_relationship_callbacks[sim_id_a](sim_id_a, relationship)
                if sim_id_b in self._create_relationship_callbacks:
                    self._create_relationship_callbacks[sim_id_b](sim_id_b, relationship)
                relationship.set_npc_compatibility_preferences()
                relationship.update_compatibility()
                attraction_service = services.get_attraction_service()
                if attraction_service is not None:
                    attraction_service.refresh_attraction(sim_id_a, sim_id_b)
                    attraction_service.refresh_attraction(sim_id_b, sim_id_a)
                return relationship

    def get_depth_sorted_rel_bit_list(self, actor_sim_id, target_sim_id):
        sorted_bits = []
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            sorted_bits = sorted(relationship.get_bits(actor_sim_id), key=lambda bit: bit.depth, reverse=True)
        return sorted_bits

    def _build_printable_string_of_bits(self, actor_sim_id, target_sim_id:'int'):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.build_printable_string_of_bits(actor_sim_id)
        else:
            return ''

    def _build_printable_string_of_tracks(self, actor_sim_id, target_sim_id:'int'):
        relationship = self._find_relationship(actor_sim_id, target_sim_id)
        if relationship is not None:
            return relationship.build_printable_string_of_tracks()
        else:
            return ''

    def on_lod_update(self, sim_id, old_lod, new_lod):
        if new_lod > SimInfoLODLevel.INTERACTED:
            return
        if new_lod > SimInfoLODLevel.MINIMUM:
            self.notify_all_relationships_on_lod_change(sim_id, old_lod, new_lod)
        else:
            if RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT is not None:
                self.remove_exclusive_relationship_bit(sim_id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT)
            self.destroy_all_relationships(sim_id)
            if sim_id in self._relationship_multipliers:
                del self._relationship_multipliers[sim_id]
            if sim_id in self._create_relationship_callbacks:
                del self._create_relationship_callbacks[sim_id]
            self.destroy_all_object_relationships(sim_id)

    def _process_legacy_relationship_data(self):
        bit_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)
        sim_info_manager = services.sim_info_manager()
        try:
            with self.suppress_client_updates_context_manager():
                for (sim_id, legacy_relationships) in self._legacy_relationship_data_storage.items():
                    for (target_id, legacy_relationship) in legacy_relationships.items():
                        if legacy_relationship.processed:
                            pass
                        else:
                            self.destroy_relationship(sim_id, target_id, notify_client=False)
                            relationship = self._find_relationship(sim_id, target_id, create=True)
                            if relationship is None:
                                legacy_relationship.processed = True
                                logger.warn('Could not create relationship to build legacy relationship.')
                            else:
                                target_relationships = self._legacy_relationship_data_storage.get(target_id, None)
                                if target_relationships is not None:
                                    target_sim_relationship = target_relationships.get(sim_id, None)
                                else:
                                    target_sim_relationship = None
                                if target_sim_relationship is not None and target_sim_relationship.processed:
                                    legacy_relationship.processed = True
                                    logger.error('Attempting to merge relationship that was already processed.')
                                else:
                                    relationship_seed = RelationshipSeed()
                                    if sim_id < target_id:
                                        sim_info_a = sim_info_manager.get(sim_id)
                                        sim_info_b = sim_info_manager.get(target_id)
                                        rel_data_a = legacy_relationship
                                        rel_data_b = target_sim_relationship
                                    else:
                                        sim_info_a = sim_info_manager.get(target_id)
                                        sim_info_b = sim_info_manager.get(sim_id)
                                        rel_data_a = target_sim_relationship
                                        rel_data_b = legacy_relationship
                                    if sim_info_a is None or sim_info_b is None:
                                        legacy_relationship.processed = True
                                        logger.warn('Attempting to load legacy relationship for Sim who no longer exists.')
                                    else:
                                        if rel_data_a is not None:
                                            for bit_id in rel_data_a.bits:
                                                relationship_bit = bit_manager.get(bit_id)
                                                if relationship_bit is None:
                                                    pass
                                                elif relationship_bit.directionality == RelationshipDirection.UNIDIRECTIONAL:
                                                    relationship_seed.sim_a_relationship_data.bits.append(bit_id)
                                                    bit_timeout = rel_data_a.bit_timeout_data.get(bit_id, None)
                                                    if bit_timeout is not None:
                                                        relationship_seed.sim_a_relationship_data.timeouts.append(bit_timeout)
                                                else:
                                                    relationship_seed.bidirectional_relationship_data.bits.append(bit_id)
                                                    bit_timeout_a = rel_data_a.bit_timeout_data.get(bit_id, None)
                                                    if rel_data_b is not None:
                                                        bit_timeout_b = rel_data_b.bit_timeout_data.get(bit_id, None)
                                                    else:
                                                        bit_timeout_b = None
                                                    if bit_timeout_a is not None and bit_timeout_b is None:
                                                        relationship_seed.bidirectional_relationship_data.timeouts.append(bit_timeout_a)
                                                    elif bit_timeout_a is None and bit_timeout_b is not None:
                                                        relationship_seed.bidirectional_relationship_data.timeouts.append(bit_timeout_b)
                                                    elif bit_timeout_a is not None and bit_timeout_b is not None:
                                                        if bit_timeout_a.elapsed_time < bit_timeout_b.elapsed_time:
                                                            relationship_seed.bidirectional_relationship_data.timeouts.append(bit_timeout_a)
                                                        else:
                                                            relationship_seed.bidirectional_relationship_data.timeouts.append(bit_timeout_b)
                                        if rel_data_b is not None:
                                            for bit_id in rel_data_b.bits:
                                                relationship_bit = bit_manager.get(bit_id)
                                                if relationship_bit is None:
                                                    pass
                                                elif relationship_bit.directionality == RelationshipDirection.UNIDIRECTIONAL:
                                                    relationship_seed.sim_b_relationship_data.bits.append(bit_id)
                                                elif bit_id not in relationship_seed.bidirectional_relationship_data.bits:
                                                    relationship_seed.bidirectional_relationship_data.bits.append(bit_id)
                                        if rel_data_a is not None:
                                            for buff_guid64 in rel_data_a.bit_added_buffs:
                                                relationship_seed.sim_a_relationship_data.bit_added_buffs.append(buff_guid64)
                                        if rel_data_b is not None:
                                            for buff_guid64 in rel_data_b.bit_added_buffs:
                                                relationship_seed.sim_b_relationship_data.bit_added_buffs.append(buff_guid64)
                                        if rel_data_a is not None:
                                            relationship_seed.sim_a_relationship_data.knowledge = rel_data_a.knowledge
                                        if rel_data_b is not None:
                                            relationship_seed.sim_b_relationship_data.knowledge = rel_data_b.knowledge
                                        use_sim_a = sim_info_a.is_player_sim and not sim_info_b.is_player_sim
                                        use_sim_b = not sim_info_a.is_player_sim and sim_info_b.is_player_sim
                                        added_tracks = set()
                                        if rel_data_a is not None:
                                            for (track_id, track_data_a) in rel_data_a.relationship_track_data.items():
                                                added_tracks.add(track_id)
                                                if rel_data_b is not None:
                                                    track_data_b = rel_data_b.relationship_track_data.get(track_id, None)
                                                else:
                                                    track_data_b = None
                                                if track_data_b is None or use_sim_a:
                                                    relationship_seed.bidirectional_relationship_data.tracks.append(track_data_a)
                                                elif use_sim_b:
                                                    relationship_seed.bidirectional_relationship_data.tracks.append(track_data_b)
                                                else:
                                                    new_seed = RelationshipTrackSeed()
                                                    new_seed.track_id = track_id
                                                    new_seed.value = (track_data_a.value + track_data_b.value)/2.0
                                                    new_seed.visible = track_data_a.visible or track_data_b.visible
                                                    new_seed.ticks_until_decay_begins = (track_data_a.ticks_until_decay_begins + track_data_b.ticks_until_decay_begins)/2.0
                                                    relationship_seed.bidirectional_relationship_data.tracks.append(new_seed)
                                        if rel_data_b is not None:
                                            for (track_id, track_data_b) in rel_data_b.relationship_track_data.items():
                                                if track_id in added_tracks:
                                                    pass
                                                else:
                                                    relationship_seed.bidirectional_relationship_data.tracks.append(track_data_b)
                                        if rel_data_a is not None and rel_data_b is None:
                                            relationship_seed.last_update_time = rel_data_a.last_update_time
                                        elif rel_data_a is None and rel_data_b is not None:
                                            relationship_seed.last_update_time = rel_data_b.last_update_time
                                        elif rel_data_a.last_update_time < rel_data_b.last_update_time:
                                            relationship_seed.last_update_time = rel_data_a.last_update_time
                                        else:
                                            relationship_seed.last_update_time = rel_data_b.last_update_time
                                        if rel_data_a is not None:
                                            rel_data_a.processed = True
                                        if rel_data_b is not None:
                                            rel_data_b.processed = True
                                        relationship.load_relationship(relationship_seed)
        finally:
            self._legacy_relationship_data_storage = None

    def load_legacy_data(self, sim_id, relationships_msg):
        if self._legacy_relationship_data_storage is None:
            logger.warn('Attempting to load legacy relationship data for Sim Id {} after legacy data has been processed.  No action has been taken.', sim_id)
            return
        legacy_data_container = LegacyRelationshipData()
        legacy_data_container.load_legacy_data(relationships_msg)
        self._legacy_relationship_data_storage[sim_id][relationships_msg.target_id] = legacy_data_container

    def get_relationship_lock(self, sim_id_a, sim_id_b, relationship_bit_lock):
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is None:
            return
        return relationship.get_relationship_bit_lock(sim_id_a, relationship_bit_lock)

    def get_all_object_sim_relationships(self, obj_tag_set):
        if obj_tag_set in self._object_sim_relationships:
            return list(self._object_sim_relationships[obj_tag_set])
        return []

    def update_object_type_name(self, name, sim_id_a, object_id_b, name_override_obj):
        name_override_obj.add_ui_metadata('custom_name', name)
        if not name_override_obj.on_hovertip_requested():
            name_override_obj.update_ui_metadata()
        hovertip_created_msg = HovertipCreated()
        Distributor.instance().add_op(name_override_obj, GenericProtocolBufferOp(Operation.HOVERTIP_CREATED, hovertip_created_msg))
        obj_tag_set = self.get_mapped_tag_set_of_id(object_id_b)
        object_relationship = self._find_object_relationship(sim_id_a, obj_tag_set)
        if object_relationship is None:
            return
        object_relationship.set_object_rel_name(name)
        object_relationship.send_relationship_info()

    def has_object_relationship_track(self, sim_id_a, obj_tag_set, relationship_track):
        obj_relationship = self._find_object_relationship(sim_id_a, obj_tag_set)
        if obj_relationship is None:
            return False
        return obj_relationship.has_track(sim_id_a, relationship_track)

    def destroy_object_relationship(self, sim_id_a, obj_tag_set, notify_client=True):
        key = (sim_id_a, obj_tag_set)
        obj_relationship = self._object_relationships.pop(key, None)
        if obj_relationship is None:
            return
        obj_defs = self._tag_set_to_ids_map.get(obj_tag_set)
        for obj_def in obj_defs:
            self._def_id_to_tag_set_map.pop(obj_def, None)
        self._tag_set_to_ids_map.pop(obj_tag_set, None)
        self._sim_object_relationships[sim_id_a].remove(obj_relationship)
        self._object_sim_relationships[obj_tag_set].remove(obj_relationship)
        obj_relationship.destroy(notify_client=notify_client)

    def destroy_all_object_relationships(self, sim_id:'int'):
        for obj_relationship in self._get_object_relationships_for_sim(sim_id):
            obj_tag_set = self.get_mapped_tag_set_of_id(obj_relationship.sim_id_b)
            self.destroy_object_relationship(obj_relationship.sim_id_a, obj_tag_set)

    def send_all_object_relationship_info(self):
        for obj_relationship in self._object_relationships.values():
            obj_relationship.send_relationship_info()

    def send_object_relationship_info(self, sim_id, obj_tag_set=None):
        if obj_tag_set is None:
            for obj_relationship in self._get_object_relationships_for_sim(sim_id):
                obj_relationship.send_relationship_info()
        else:
            obj_relationship = self._find_object_relationship(sim_id, obj_tag_set)
            if obj_relationship is not None:
                obj_relationship.send_relationship_info()

    def get_object_relationship_score(self, sim_id_a:'int', obj_tag_set, track=DEFAULT, target_def_id=None, create=False):
        relationship = self._find_object_relationship(sim_id_a, obj_tag_set, target_def_id=target_def_id, create=create)
        if relationship is not None:
            return relationship.get_track_score(sim_id_a, track)
        else:
            return

    def add_object_relationship_score(self, sim_id_a:'int', obj_tag_set, increment, track=DEFAULT, threshold=None, **kwargs):
        obj_relationship = self._find_object_relationship(sim_id_a, obj_tag_set)
        if obj_relationship is not None:
            if threshold is None or threshold.compare(obj_relationship.get_track_score(sim_id_a, track)):
                obj_relationship.add_track_score(sim_id_a, increment, track, **kwargs)
                logger.debug('Adding to score to track {} for {}: += {}; new score = {}', track, obj_relationship, increment, obj_relationship.get_track_score(sim_id_a, track))
            else:
                logger.debug('Attempting to add to track {} for {} but {} not within threshold {}', track, obj_relationship, obj_relationship.get_track_score(sim_id_a, track), threshold)
        else:
            logger.error('relationship_tracker.add_relationship_score() could not find/create a relationship between: Sim = {} Object Tag Set = {}', sim_id_a, obj_tag_set)

    def set_object_relationship_score(self, sim_id_a:'int', obj_tag_set, value, track=DEFAULT, threshold=None):
        obj_relationship = self._find_object_relationship(sim_id_a, obj_tag_set)
        if obj_relationship is not None:
            obj_relationship.set_relationship_score(sim_id_a, value, track=track, threshold=threshold)
        else:
            logger.error('relationship_tracker.set_relationship_score() could not find/create an object relationship between: Sim = {} ObjectTagSet = {}', sim_id_a, obj_tag_set)

    def get_object_relationship_track(self, sim_id_a:'int', obj_tag_set, target_def_id=None, track=DEFAULT, add=False):
        with self.suppress_client_updates_context_manager():
            relationship = self._find_object_relationship(sim_id_a, obj_tag_set, target_def_id=target_def_id, create=add)
            if relationship is not None:
                return relationship.get_track(sim_id_a, track, add=add)
            if add:
                logger.error('relationship_tracker.get_object_relationship_track() failed to create a relationship between Sim: {} ObjectTagSet: {}', sim_id_a, obj_tag_set)
            return

    def add_object_relationship_bit(self, actor_sim_id:'int', obj_tag_set, bit_to_add, force_add=False, from_load=False, send_rel_change_event=True):
        if not self._validate_bit(bit_to_add, actor_sim_id, obj_tag_set):
            return
        relationship = self._find_object_relationship(actor_sim_id, obj_tag_set, create=False)
        if relationship is None:
            return
        member_obj_def_id = relationship.get_sim_id_b
        relationship.add_relationship_bit(actor_sim_id, member_obj_def_id, bit_to_add, force_add=force_add, from_load=from_load, send_rel_change_event=send_rel_change_event)

    def remove_object_relationship_bit(self, actor_sim_id, obj_tag_set, bit_to_remove, send_rel_change_event=True):
        relationship = self._find_object_relationship(actor_sim_id, obj_tag_set)
        if relationship is None:
            return
        member_obj_def_id = relationship.sim_id_b
        relationship.remove_bit(actor_sim_id, member_obj_def_id, bit_to_remove, send_rel_change_event=send_rel_change_event)

    def clean_and_send_remaining_object_relationships(self, sim_id):
        for object_relationship in self.get_all_sim_object_relationships(sim_id):
            object_relationship.send_relationship_info()

    def get_all_object_bits(self, actor_sim_id, obj_tag_set=None):
        bits = []
        if obj_tag_set is None:
            for relationship in self._get_object_relationships_for_sim(actor_sim_id):
                bits.extend(relationship.get_bits(actor_sim_id))
        else:
            relationship = self._find_object_relationship(actor_sim_id, obj_tag_set)
            if relationship is not None:
                bits.extend(relationship.get_bits(actor_sim_id))
        return bits

    def has_object_bit(self, actor_sim_id, obj_tag_set, bit):
        obj_relationship = self._find_object_relationship(actor_sim_id, obj_tag_set)
        if obj_relationship is None:
            return False
        elif obj_relationship.has_bit(actor_sim_id, bit):
            return obj_relationship
        return False

    def get_all_sim_object_relationships(self, sim_id):
        if sim_id in self._sim_object_relationships:
            return list(self._sim_object_relationships[sim_id])
        return []

    def target_object_gen(self, sim_id):
        for obj_relationship in self._get_object_relationships_for_sim(sim_id):
            yield self._get_tag_set_of - id(obj_relationship.get_other_sim_id(sim_id))

    def has_object_relationship(self, actor_sim_id, obj_tag_set):
        return self._find_object_relationship(actor_sim_id, obj_tag_set) is not None

    def get_mapped_tag_set_of_id(self, obj_def_id):
        tag_set = self._def_id_to_tag_set_map.get(obj_def_id)
        if tag_set is None:
            if obj_def_id is None:
                logger.error('Failed to find a tag set, no definition id was specified')
                return
            target_definition = services.definition_manager().get(obj_def_id)
            if target_definition is None:
                logger.warn('Failed to find an object definition {}', obj_def_id)
                return
            for (_, mapped_tag_set) in ObjectRelationshipTrack.OBJECT_BASED_FRIENDSHIP_TRACKS.items():
                if set(target_definition.get_tags()) & mapped_tag_set.tags:
                    tag_set = mapped_tag_set
                    break
        return tag_set

    def map_tag_set_of_id(self, obj_def_id, tag_set):
        if tag_set not in self._tag_set_to_ids_map:
            self._tag_set_to_ids_map[tag_set] = set()
        self._tag_set_to_ids_map[tag_set].add(obj_def_id)
        self._def_id_to_tag_set_map[obj_def_id] = tag_set

    def get_mapped_track_of_tag_set(self, obj_tag_set):
        track = None
        for (mapped_track, mapped_tag_set) in ObjectRelationshipTrack.OBJECT_BASED_FRIENDSHIP_TRACKS.items():
            if obj_tag_set == mapped_tag_set:
                track = mapped_track
        return track

    def get_ids_of_tag_set(self, tag_set):
        return self._tag_set_to_ids_map.get(tag_set)

    def get_object_type_rel_id(self, obj):
        object_rel_override_id = 0
        if len(self._object_relationships) == 0:
            return object_rel_override_id
        obj_tag_set = self.get_mapped_tag_set_of_id(obj.definition.id)
        if obj_tag_set is None:
            return object_rel_override_id
        active_sim = services.get_active_sim()
        if active_sim is None:
            return object_rel_override_id
        key = (services.get_active_sim().id, obj_tag_set)
        object_relationship = self._object_relationships.get(key, None)
        if object_relationship is not None:
            object_rel_override_id = object_relationship._target_object_instance_id
        return object_rel_override_id

    def get_object_relationship(self, sim_id, obj_tag_set):
        key = (sim_id, obj_tag_set)
        return self._object_relationships.get(key)

    def _create_object_relationship(self, sim_id_a, obj_tag_set, target_def_id:'int'):
        self.map_tag_set_of_id(target_def_id, obj_tag_set)
        return ObjectRelationship(sim_id_a, target_def_id)

    def _find_object_relationship(self, sim_id_a:'int', obj_tag_set, target_def_id:'int'=None, create=False, from_load=False):
        if from_load:
            obj_tag_set = self.get_mapped_tag_set_of_id(target_def_id)
            if obj_tag_set is None:
                logger.warn('Failed to find object relationship, no tag set found for definition id {}', target_def_id)
                return
        key = (sim_id_a, obj_tag_set)
        relationship = self._object_relationships.get(key)
        if relationship is not None:
            return relationship
        if create:
            if target_def_id is None:
                logger.error('Failed to create an object relationship, no target was specified')
                return
            relationship = self._create_object_relationship(sim_id_a, obj_tag_set, target_def_id)
            if relationship is None:
                return
            else:
                self._object_relationships[key] = relationship
                self._sim_object_relationships[sim_id_a].append(relationship)
                self._object_sim_relationships[obj_tag_set].append(relationship)
                if sim_id_a in self._create_relationship_callbacks:
                    self._create_relationship_callbacks[sim_id_a](sim_id_a, relationship)
                if obj_tag_set in self._create_relationship_callbacks:
                    self._create_relationship_callbacks[obj_tag_set](obj_tag_set, relationship)
                return relationship

    def _get_object_relationships_for_sim(self, sim_id):
        obj_relationships = self._sim_object_relationships.get(sim_id, None)
        if obj_relationships is None:
            return tuple()
        return tuple(obj_relationships)

    def update_compatibilities(self, sim_id):
        for relationship in self._sim_relationships[sim_id]:
            relationship.update_compatibility()

    def get_compatibility_level(self, sim_id_a:'int', sim_id_b:'int'):
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is None:
            return
        return relationship.get_compatibility_level()

    def get_compatibility_score(self, sim_id_a:'int', sim_id_b:'int'):
        relationship = self._find_relationship(sim_id_a, sim_id_b)
        if relationship is None:
            return
        return relationship.get_compatibility_score()
