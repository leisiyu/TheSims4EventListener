import itertoolsimport servicesimport sims4from distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import send_relationship_opfrom protocolbuffers import Commodities_pb2 as commodity_protocolfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom relationships.compatibility_tuning import CompatibilityTuningfrom relationships.data.relationship_label_data import RelationshipLabelDatafrom relationships.data.unidirectional_relationship_data import UnidirectionalRelationshipDatafrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.relationship_enums import RelationshipTrackTypefrom relationships.relationship_objects.relationship import Relationshipfrom relationships.sim_knowledge import SimKnowledgefrom sims.global_gender_preference_tuning import GenderPreferenceTypefrom sims.relationship_expectations_tuning import RelationshipExpectationsTuningfrom sims.sim_info import SimInfofrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.utils import classproperty
class SimRelationship(Relationship):
    __slots__ = ('_sim_id_a', '_sim_id_b', '_bi_directional_relationship_data', '_sim_a_relationship_data', '_sim_b_relationship_data', '_relationship_label_data')

    def __init__(self, sim_id_a:int, sim_id_b:int):
        if sim_id_a < sim_id_b:
            self._sim_id_a = sim_id_a
            self._sim_id_b = sim_id_b
        else:
            self._sim_id_a = sim_id_b
            self._sim_id_b = sim_id_a
        self._sim_a_relationship_data = UnidirectionalRelationshipData(self, self._sim_id_a)
        self._sim_b_relationship_data = UnidirectionalRelationshipData(self, self._sim_id_b)
        self._relationship_label_data = RelationshipLabelData()
        super().__init__()

    @classproperty
    def is_object_rel(cls):
        return False

    def apply_social_group_decay(self):
        self._sim_a_relationship_data.apply_social_group_decay()
        self._sim_b_relationship_data.apply_social_group_decay()
        super().apply_social_group_decay()

    def remove_social_group_decay(self):
        self._sim_a_relationship_data.remove_social_group_decay()
        self._sim_b_relationship_data.remove_social_group_decay()
        super().remove_social_group_decay()

    def _get_uni_directional_rel_data(self, sim_id):
        if sim_id == self._sim_id_a:
            return self._sim_a_relationship_data
        else:
            return self._sim_b_relationship_data

    def get_uni_directional_rel_data(self, sim_id):
        return self._get_uni_directional_rel_data(sim_id)

    def enable_player_sim_track_decay(self, to_enable=True):
        self._sim_a_relationship_data.enable_player_sim_track_decay(to_enable=to_enable)
        self._sim_b_relationship_data.enable_player_sim_track_decay(to_enable=to_enable)
        super().enable_player_sim_track_decay(to_enable)

    def get_highest_priority_track_bit(self, sim_id):
        return max(super().get_highest_priority_track_bit(sim_id), self._get_uni_directional_rel_data(sim_id).get_highest_priority_track_bit())

    def has_bit(self, sim_id, bit):
        return super().has_bit(sim_id, bit) or any(bit.matches_bit(bit_type) for bit_type in self._get_uni_directional_rel_data(sim_id).bit_types)

    def remove_bit(self, actor_sim_id, target_sim_id, bit, notify_client=True, send_rel_change_event=True):
        super().remove_bit(actor_sim_id, target_sim_id, bit, notify_client, send_rel_change_event)

    def on_sim_creation(self, sim):
        super().on_sim_creation(sim)
        self._get_uni_directional_rel_data(sim.sim_id).on_sim_creation(sim)

    def get_relationship_bit_lock(self, sim_id, lock_type):
        lock = super().get_relationship_bit_lock(sim_id, lock_type)
        if lock is None:
            lock = self._get_uni_directional_rel_data(sim_id).get_lock(lock_type)
        return lock

    def get_all_relationship_bit_locks(self, sim_id):
        return list(itertools.chain(super().get_all_relationship_bit_locks(sim_id), self._get_uni_directional_rel_data(sim_id).get_all_locks()))

    def get_relationship_label_data(self) -> RelationshipLabelData:
        return self._relationship_label_data

    def destroy(self, notify_client=True):
        super().destroy(notify_client)
        self._sim_a_relationship_data.destroy()
        self._sim_b_relationship_data.destroy()
        self._relationship_label_data.destroy()

    def notify_relationship_on_lod_change(self, old_lod, new_lod):
        super().notify_relationship_on_lod_change(old_lod, new_lod)
        self._sim_a_relationship_data.notify_relationship_on_lod_change(old_lod, new_lod)
        self._sim_b_relationship_data.notify_relationship_on_lod_change(old_lod, new_lod)

    def build_printable_string_of_tracks(self):
        ret = super().build_printable_string_of_tracks()
        for track in self._sim_a_relationship_data.all_tracks_gen():
            ret += '\t\t{} = {}; decaying? {}; decay rate: {}; track type: {}; from sim_id:{} to sim_id:{}\n'.format(track, track.get_value(), track.decay_enabled, track.get_decay_rate(), track.track_type, self.sim_id_a, self.sim_id_b)
        for track in self._sim_b_relationship_data.all_tracks_gen():
            ret += '\t\t{} = {}; decaying? {}; decay rate: {}; track type: {} from sim_id:{} to sim_id:{}\n'.format(track, track.get_value(), track.decay_enabled, track.get_decay_rate(), track.track_type, self.sim_id_b, self.sim_id_a)
        return ret

    def save_relationship(self, relationship_msg):
        super().save_relationship(relationship_msg)
        self._sim_a_relationship_data.save_relationship_data(relationship_msg.sim_a_relationship_data)
        self._sim_b_relationship_data.save_relationship_data(relationship_msg.sim_b_relationship_data)
        self._relationship_label_data.save_data(relationship_msg.relationship_label_data)

    def load_relationship(self, relationship_msg):
        super().load_relationship(relationship_msg)
        self._sim_a_relationship_data.load_relationship_data(relationship_msg.sim_a_relationship_data)
        self._sim_b_relationship_data.load_relationship_data(relationship_msg.sim_b_relationship_data)
        self._relationship_label_data.load_data(relationship_msg.relationship_label_data)

    def can_cull_relationship(self, consider_convergence=True):
        if not super().can_cull_relationship(consider_convergence):
            return False
        sim_info_a = self.find_sim_info_a()
        sim_info_b = self.find_sim_info_b()
        is_played_relationship = sim_info_a is not None and (sim_info_b is not None and (sim_info_a.is_player_sim or sim_info_b.is_player_sim))
        if not self._sim_a_relationship_data.can_cull_relationship(consider_convergence, is_played_relationship):
            return False
        elif not self._sim_b_relationship_data.can_cull_relationship(consider_convergence, is_played_relationship):
            return False
        return True

    def get_bits(self, sim_id):
        return tuple(itertools.chain(super().get_bits(sim_id), self._get_uni_directional_rel_data(sim_id).bit_types))

    def get_bit_instances(self, sim_id):
        return tuple(itertools.chain(super().get_bit_instances(sim_id), self._get_uni_directional_rel_data(sim_id).bit_instances))

    def get_track_tracker(self, sim_id, track):
        if track.track_type == RelationshipTrackType.SENTIMENT:
            return self._get_uni_directional_rel_data(sim_id).sentiment_track_tracker
        if track.track_type == RelationshipTrackType.UNIDIRECTIONAL:
            return self._get_uni_directional_rel_data(sim_id).track_tracker
        return super().get_track_tracker(sim_id, track)

    def get_track_relationship_data(self, sim_id, track):
        if track.track_type == RelationshipTrackType.SENTIMENT or track.track_type == RelationshipTrackType.UNIDIRECTIONAL:
            return self._get_uni_directional_rel_data(sim_id)
        return super().get_track_relationship_data(sim_id, track)

    def get_relationship_depth(self, sim_id):
        return super().get_relationship_depth(sim_id) + self._get_uni_directional_rel_data(sim_id).depth

    def refresh_knowledge(self):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self._sim_id_a)
        sim_info_b = sim_info_manager.get(self._sim_id_b)
        if sim_info_b.needs_preference_traits_fixup:
            sim_knowledge = self.get_knowledge(self._sim_id_a, self._sim_id_b)
            if sim_knowledge is not None:
                for known_trait in list(sim_knowledge.known_traits):
                    if not sim_info_b.has_trait(known_trait):
                        sim_knowledge.remove_known_trait(known_trait)
                self._fixup_gender_preference_knowledge(sim_knowledge, sim_info_b)
                self._fixup_relationship_expectations_knowledge(sim_knowledge, sim_info_b)
        if sim_info_a.needs_preference_traits_fixup:
            sim_knowledge = self.get_knowledge(self._sim_id_b, self._sim_id_a)
            if sim_knowledge is not None:
                for known_trait in list(sim_knowledge.known_traits):
                    if not sim_info_a.has_trait(known_trait):
                        sim_knowledge.remove_known_trait(known_trait)
                self._fixup_gender_preference_knowledge(sim_knowledge, sim_info_a)
                self._fixup_relationship_expectations_knowledge(sim_knowledge, sim_info_a)

    def get_knowledge(self, actor_sim_id, target_sim_id, initialize=False):
        rel_data = self._get_uni_directional_rel_data(actor_sim_id)
        if initialize and rel_data.knowledge is None:
            rel_data.initialize_knowledge()
        return rel_data.knowledge

    def apply_relationship_multipliers(self, sim_id, relationship_multipliers):
        super().apply_relationship_multipliers(sim_id, relationship_multipliers)
        uni_directional_data = self._get_uni_directional_rel_data(sim_id)
        for (track_type, multiplier) in relationship_multipliers.items():
            relationship_track = uni_directional_data.get_track(track_type, add=False)
            if relationship_track is not None:
                relationship_track.add_statistic_multiplier(multiplier)

    def remove_relationship_multipliers(self, sim_id, relationship_multipliers):
        super().remove_relationship_multipliers(sim_id, relationship_multipliers)
        uni_directional_data = self._get_uni_directional_rel_data(sim_id)
        for (track_type, multiplier) in relationship_multipliers.items():
            relationship_track = uni_directional_data.get_track(track_type, add=False)
            if relationship_track is not None:
                relationship_track.remove_statistic_multiplier(multiplier)

    def _fixup_gender_preference_knowledge(self, sim_knowledge, target_sim_info):
        if sim_knowledge.knows_romantic_preference and (sim_knowledge.get_known_exploring_sexuality != target_sim_info.is_exploring_sexuality or sim_knowledge.known_romantic_genders != target_sim_info.get_attracted_genders(GenderPreferenceType.ROMANTIC)):
            sim_knowledge.remove_knows_romantic_preference()
        if sim_knowledge.knows_woohoo_preference and sim_knowledge.known_woohoo_genders != target_sim_info.get_attracted_genders(GenderPreferenceType.WOOHOO):
            sim_knowledge.remove_knows_woohoo_preference()

    @staticmethod
    def _fixup_relationship_expectations_knowledge(sim_knowledge:SimKnowledge, target_sim_info:SimInfo):
        if not sim_knowledge.known_relationship_expectations:
            return
        for known_expectation in sim_knowledge.known_relationship_expectations:
            if known_expectation not in target_sim_info.get_relationship_expectations():
                sim_knowledge.remove_knows_relationship_expectations()
                return

    def _get_rel_data_for_bit(self, actor_sim_id, bit):
        rel_data = super()._get_rel_data_for_bit(actor_sim_id, bit)
        if rel_data is None:
            rel_data = self._get_uni_directional_rel_data(actor_sim_id)
        return rel_data

    def _invoke_bit_removed(self, actor_sim_id, bit):
        super()._invoke_bit_removed(actor_sim_id, bit)
        self.sentiment_track_tracker(actor_sim_id).on_relationship_bit_removed(bit, actor_sim_id)

    def _invoke_bit_added(self, actor_sim_id, bit_to_add):
        super()._invoke_bit_added(actor_sim_id, bit_to_add)
        self.sentiment_track_tracker(actor_sim_id).on_relationship_bit_added(bit_to_add, actor_sim_id)

    def _get_all_bits(self, actor_sim_id):
        return itertools.chain(super()._get_all_bits(actor_sim_id), self._get_uni_directional_rel_data(actor_sim_id).bit_types)

    def get_bit_added_buffs(self, sim_id):
        rel_data = self._get_uni_directional_rel_data(sim_id)
        if rel_data.bit_added_buffs is None:
            rel_data.bit_added_buffs = set()
        return rel_data.bit_added_buffs

    def add_bit_added_buffs(self, sim_id, buff):
        rel_data = self._get_uni_directional_rel_data(sim_id)
        if rel_data.bit_added_buffs is None:
            rel_data.bit_added_buff = set()
        rel_data.bit_added_buffs.add(buff.guid64)

    def sentiment_track_tracker(self, sim_id):
        return self._get_uni_directional_rel_data(sim_id).sentiment_track_tracker

    def relationship_tracks_gen(self, sim_id, track_type=None):
        if track_type is None or track_type == RelationshipTrackType.RELATIONSHIP:
            yield from super().relationship_tracks_gen(sim_id, track_type)
        if track_type is None or track_type == RelationshipTrackType.SENTIMENT:
            yield from self.sentiment_track_tracker(sim_id)
        if track_type is None or track_type == RelationshipTrackType.UNIDIRECTIONAL:
            yield from self._get_uni_directional_rel_data(sim_id).track_tracker

    def get_compatibility_level(self):
        return self._bi_directional_relationship_data.get_compatibility_level()

    def get_compatibility_score(self):
        return self._bi_directional_relationship_data.get_compatibility_score()

    def update_compatibility(self):
        self._bi_directional_relationship_data.update_compatibility()

    def set_npc_compatibility_preferences(self):
        self._bi_directional_relationship_data.set_npc_compatibility_preferences()

    def send_relationship_info(self, deltas=None, headline_icon_modifier=None, send_npc_relationship=False):
        if self.suppress_client_updates:
            return
        sim_info_a = self.find_sim_info_a()
        sim_info_b = self.find_sim_info_b()
        if sim_info_a is not None and (sim_info_b is not None and (sim_info_a.is_npc and sim_info_b.is_npc)) and not send_npc_relationship:
            return
        if sim_info_a is not None:
            send_relationship_op(sim_info_a, self._build_relationship_update_proto(sim_info_a, self._sim_id_b, deltas=deltas))
            if deltas is not None:
                self._send_headlines_for_sim(sim_info_a, deltas, headline_icon_modifier=headline_icon_modifier)
        if sim_info_b is not None:
            send_relationship_op(sim_info_b, self._build_relationship_update_proto(sim_info_b, self._sim_id_a, deltas=deltas))
            if deltas is not None:
                self._send_headlines_for_sim(sim_info_b, deltas, headline_icon_modifier=headline_icon_modifier)

    def _build_relationship_update_proto(self, actor_sim_info, target_sim_id, deltas=None):
        msg = commodity_protocol.RelationshipUpdate()
        actor_sim_id = actor_sim_info.sim_id
        msg.actor_sim_id = actor_sim_id
        msg.target_id.object_id = target_sim_id
        msg.target_id.manager_id = services.sim_info_manager().id
        msg.hidden = self.is_hidden
        msg.last_update_time = self._last_update_time
        msg.is_load = not services.current_zone().is_zone_running
        tracks = self._build_relationship_track_proto(actor_sim_id, msg)
        self._build_relationship_bit_proto(actor_sim_id, tracks, msg)
        sim_info_manager = services.sim_info_manager()
        target_sim_info = sim_info_manager.get(target_sim_id)
        owner = sim_info_manager.get(actor_sim_id)
        knowledge = self._get_uni_directional_rel_data(actor_sim_id).knowledge
        if owner.lod != SimInfoLODLevel.MINIMUM:
            if target_sim_info is not None:
                msg.num_traits = len(target_sim_info.trait_tracker.personality_traits)
            for trait in knowledge.known_traits:
                if not trait.is_personality_trait:
                    msg.known_trait_ids.append(trait.guid64)
            for trait in target_sim_info.trait_tracker.personality_traits:
                if trait in knowledge.known_traits:
                    msg.known_trait_ids.append(trait.guid64)
            if knowledge.knows_career:
                msg.known_careertrack_ids.extend(knowledge.get_known_careertrack_ids())
            if knowledge._known_stats is not None:
                for stat in knowledge._known_stats:
                    msg.known_stat_ids.append(stat.guid64)
            if knowledge._known_rel_tracks is not None:
                for track in knowledge._known_rel_tracks:
                    msg.known_rel_track_ids.append(track.guid64)
            if knowledge.get_known_major() is not None:
                msg.known_major_id = knowledge.get_known_major().guid64
            msg.knows_romantic_preference = knowledge.knows_romantic_preference
            if knowledge.knows_major and knowledge.knows_romantic_preference:
                for gender in knowledge.known_romantic_genders:
                    msg.known_romantic_genders.append(gender)
                if knowledge.get_known_exploring_sexuality is not None:
                    msg.known_exploring_sexuality = knowledge.get_known_exploring_sexuality
            msg.knows_woohoo_preference = knowledge.knows_woohoo_preference
            if knowledge.knows_woohoo_preference:
                for gender in knowledge.known_woohoo_genders:
                    msg.known_woohoo_genders.append(gender)
            if knowledge.knows_unconfronted_secret:
                msg.unconfronted_secret_id = knowledge.get_unconfronted_secret().guid64
            if knowledge.knows_confronted_secrets:
                for secret in knowledge.get_confronted_secrets():
                    secret_msg = protocols.ConfrontedSimSecret()
                    secret_msg.secret_id = secret.guid64
                    secret_msg.blackmailed = secret.blackmailed
                    msg.known_confronted_secrets.append(secret_msg)
            for expectation in knowledge.known_relationship_expectations:
                msg.known_relationship_expectations_ids.append(expectation.guid64)
        self._relationship_label_data.save_data(msg.relationship_label_data)
        if target_sim_info.spouse_sim_id is not None:
            msg.target_sim_significant_other_id = target_sim_info.spouse_sim_id
        actor_trait_tracker = actor_sim_info.trait_tracker
        target_trait_tracker = target_sim_info.trait_tracker if knowledge is not None and (target_sim_info is not None and (target_sim_info.lod != SimInfoLODLevel.MINIMUM and owner is not None)) and target_sim_info is not None and target_sim_info else None
        if actor_trait_tracker is not None and target_trait_tracker is not None and (actor_trait_tracker.has_characteristic_preferences() or target_trait_tracker.has_characteristic_preferences()):
            self._build_compatibility_proto(msg)
        return msg

    def _build_relationship_bit_proto(self, actor_sim_id, track_bits, msg):
        other_sim_id = self.get_other_sim_id(actor_sim_id)
        other_sim_track_bits = set()
        for track in self.relationship_tracks_gen(other_sim_id):
            active_bit = track.get_active_bit()
            if active_bit:
                other_sim_track_bits.add(active_bit.guid64)
        for bit in self.get_bit_instances(actor_sim_id):
            if bit.visible or not bit.invisible_filterable:
                pass
            elif not bit.guid64 in track_bits:
                if bit.guid64 in other_sim_track_bits:
                    pass
                else:
                    with ProtocolBufferRollback(msg.bit_updates) as bit_update:
                        bit_update.bit_id = bit.guid64
                        bit_timeout_data = self._get_uni_directional_rel_data(actor_sim_id)._find_timeout_data_by_bit_instance(bit)
                        if bit_timeout_data is not None:
                            bit_alarm = bit_timeout_data.alarm_handle
                            if bit_alarm is not None:
                                bit_update.end_time = bit_alarm.finishing_time

    def _build_compatibility_proto(self, msg):
        compatibility_level = self.get_compatibility_level()
        if compatibility_level in CompatibilityTuning.COMPATIBILITY_LEVEL_ICONS_MAP:
            icon_data = CompatibilityTuning.COMPATIBILITY_LEVEL_ICONS_MAP[compatibility_level]
            msg.compatibility.level = compatibility_level
            msg.compatibility.icon = sims4.resources.get_protobuff_for_key(icon_data.icon)
            msg.compatibility.small_icon = sims4.resources.get_protobuff_for_key(icon_data.small_icon)
            msg.compatibility.name = icon_data.level_name
            msg.compatibility.desc = icon_data.descriptive_text

    def _get_paired_sim_infos(self, actor_is_a):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self._sim_id_a)
        sim_info_b = sim_info_manager.get(self._sim_id_b)
        if actor_is_a:
            return (sim_info_a, sim_info_b)
        return (sim_info_b, sim_info_a)

    def add_track_score(self, sim_id, increment, track, apply_cross_age_multipliers=False, **kwargs):
        if track.cross_age_multipliers is None or not apply_cross_age_multipliers:
            super().add_track_score(sim_id, increment, track, **kwargs)
            return
        (actor_sim_info, target_sim_info) = self._get_paired_sim_infos(self._sim_id_b == sim_id)
        if actor_sim_info is None or target_sim_info is None or not (actor_sim_info.is_sim and target_sim_info.is_sim):
            super().add_track_score(sim_id, increment, track, **kwargs)
            return
        cross_age_multipliers = track.cross_age_multipliers
        multiplier_data = cross_age_multipliers.gain_multipliers if increment >= 0 else cross_age_multipliers.loss_multipliers
        multiplier = multiplier_data.get_value(actor_sim_info.age, target_sim_info.age)
        increment *= multiplier
        super().add_track_score(sim_id, increment, track, **kwargs)
