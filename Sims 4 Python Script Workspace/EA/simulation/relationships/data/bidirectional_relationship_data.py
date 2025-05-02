import servicesfrom relationships.compatibility import Compatibilityfrom relationships.data.relationship_data import RelationshipData, loggerfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.object_relationship_track_tracker import ObjectRelationshipTrackTrackerfrom relationships.relationship_track_tracker import RelationshipTrackTracker
class BidirectionalRelationshipData(RelationshipData):
    __slots__ = ('_level_change_watcher_id', '_compatibility')

    def __init__(self, relationship):
        super().__init__(relationship)
        if relationship.is_object_rel:
            self._track_tracker = ObjectRelationshipTrackTracker(self)
        else:
            self._track_tracker = RelationshipTrackTracker(self)
        self._level_change_watcher_id = self._track_tracker.add_watcher(self._value_changed)
        self._compatibility = Compatibility(relationship.sim_id_a, relationship.sim_id_b)

    def __repr__(self):
        return 'BidirectionalRelationshipData between: {} and {}'.format(self.sim_id_a, self.sim_id_b)

    @property
    def sim_id_a(self):
        return self.relationship.sim_id_a

    @property
    def sim_id_b(self):
        return self.relationship.sim_id_b

    def _sim_ids(self):
        return (self.sim_id_a, self.sim_id_b)

    def _value_changed(self, stat_type, old_value, new_value):
        if stat_type.causes_delayed_removal_on_convergence:
            self.relationship._destroy_culling_alarm()
        self.relationship._last_update_time = services.time_service().sim_now

    def get_prevailing_short_term_context_track(self):
        tracks = [track for track in self._track_tracker if track.is_short_term_context]
        if tracks:
            return max(tracks, key=lambda t: abs(t.get_value()))
        return self.get_track(RelationshipGlobalTuning.DEFAULT_SHORT_TERM_CONTEXT_TRACK, add=True)

    def _update_client_from_bit_add(self, bit_type, bit_instance, from_load):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        self._update_client_for_sim_info_for_bit_add(bit_type, bit_instance, sim_info_a, sim_info_b, from_load)
        if sim_info_b is not None:
            self._update_client_for_sim_info_for_bit_add(bit_type, bit_instance, sim_info_b, sim_info_a, from_load)

    def add_bit(self, bit_type, bit_instance, from_load=False):
        super().add_bit(bit_type, bit_instance, from_load=from_load)
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        if sim_info_a is not None:
            bit_instance.add_appropriateness_buffs(sim_info_a)
        if sim_info_b is not None:
            bit_instance.add_appropriateness_buffs(sim_info_b)

    def _update_client_from_bit_remove(self, bit_type, bit_instance):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        self._update_client_for_sim_info_for_bit_remove(bit_type, bit_instance, sim_info_a, sim_info_b)
        self._update_client_for_sim_info_for_bit_remove(bit_type, bit_instance, sim_info_b, sim_info_a)

    def remove_bit(self, bit):
        if bit not in self._bits:
            logger.debug("Attempting to remove bit for {} that doesn't exist: {}", self, bit)
            return
        bit_instance = self._bits[bit]
        super().remove_bit(bit)
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        if sim_info_a:
            bit_instance.remove_appropriateness_buffs(sim_info_a)
        if sim_info_b:
            bit_instance.remove_appropriateness_buffs(sim_info_b)

    def destroy(self):
        super().destroy()
        self._track_tracker.remove_watcher(self._level_change_watcher_id)
        self._level_change_watcher_id = None
        self._track_tracker.destroy()
        self._track_tracker = None

    def can_cull_relationship(self, consider_convergence, is_played_relationship):
        if consider_convergence and not self._track_tracker.are_all_tracks_that_cause_culling_at_convergence():
            return False
        return super().can_cull_relationship(consider_convergence, is_played_relationship)

    def show_bit_added_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_added_notification is None:
            return
        if sim.is_selectable and sim.is_human:
            relationship_bit.show_bit_added_dialog(sim, sim, target_sim_info)

    def show_bit_removed_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_removed_notification is None:
            return
        if sim.is_selectable and sim.is_human:
            relationship_bit.show_bit_removed_dialog(sim, target_sim_info)

    def update_compatibility(self):
        self._compatibility.calculate_score()

    def get_compatibility_level(self):
        return self._compatibility.get_level()

    def get_compatibility_score(self):
        return self._compatibility.get_score()

    def set_npc_compatibility_preferences(self):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        if sim_info_a is None or sim_info_b is None:
            return
        if sim_info_a.is_toddler_or_younger or sim_info_b.is_toddler_or_younger:
            return
        trait_tracker_a = sim_info_a.trait_tracker
        trait_tracker_b = sim_info_b.trait_tracker
        if trait_tracker_a is None or trait_tracker_b is None:
            return
        if sim_info_a.is_npc and not trait_tracker_a.has_characteristic_preferences():
            self._compatibility.assign_npc_preferences(sim_info_a)
        if sim_info_b.is_npc and not trait_tracker_b.has_characteristic_preferences():
            self._compatibility.assign_npc_preferences(sim_info_b)

    def save_relationship_data(self, relationship_data_msg):
        super().save_relationship_data(relationship_data_msg)
        self._compatibility.save_compatibility(relationship_data_msg)

    def load_relationship_data(self, relationship_data_msg):
        super().load_relationship_data(relationship_data_msg)
        self._compatibility.load_compatibility(relationship_data_msg)
