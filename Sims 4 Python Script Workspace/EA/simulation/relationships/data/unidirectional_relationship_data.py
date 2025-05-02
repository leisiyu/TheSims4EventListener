from __future__ import annotationsimport servicesimport itertoolsfrom date_and_time import DateAndTimefrom relationships.data.relationship_data import RelationshipData, loggerfrom relationships.relationship_enums import SentimentDurationType, RelationshipTrackTypefrom relationships.relationship_track_tracker import RelationshipTrackTrackerfrom relationships.sentiment_track_tracker import SentimentTrackTrackerfrom relationships.sim_knowledge import SimKnowledgefrom sims.sim_info_lod import SimInfoLODLevelfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from relationships.relationship_bit import RelationshipBit
    from relationships.relationship_track import RelationshipTrack
    from sims.sim_info import SimInfo
    from sims.sim_info_mixin import HasSimInfoMixin
    from sims4.telemetry import _TelemetryHookWriterTELEMETRY_FIELD_SENTIMENT_IDS = 'snta'
class UnidirectionalRelationshipData(RelationshipData):
    __slots__ = ('_knowledge', '_actor_sim_id', 'bit_added_buffs', '_sentiment_tracker')

    def __init__(self, relationship, actor_sim_id):
        super().__init__(relationship)
        self._knowledge = None
        self._actor_sim_id = actor_sim_id
        self.bit_added_buffs = None
        self._track_tracker = RelationshipTrackTracker(self)
        self._sentiment_tracker = SentimentTrackTracker(self)

    def __repr__(self):
        return 'UnidirectionalRelationshipData between: {} and {}'.format(self._actor_sim_id, self._target_sim_id)

    @property
    def sim_id_a(self):
        return self._actor_sim_id

    @property
    def sim_id_b(self):
        return self._target_sim_id

    @property
    def _target_sim_id(self):
        return self.relationship.get_other_sim_id(self._actor_sim_id)

    @property
    def knowledge(self):
        return self._knowledge

    def initialize_knowledge(self):
        self._knowledge = SimKnowledge(self)

    def find_target_sim_info(self):
        return services.sim_info_manager().get(self._target_sim_id)

    def _sim_ids(self):
        return (self._actor_sim_id, self._target_sim_id)

    def _update_client_from_bit_add(self, bit_type, bit_instance, from_load):
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(self._actor_sim_id)
        target_sim_info = sim_info_manager.get(self._target_sim_id)
        self._update_client_for_sim_info_for_bit_add(bit_type, bit_instance, actor_sim_info, target_sim_info, from_load)

    def add_bit(self, bit_type, bit_instance, from_load=False):
        super().add_bit(bit_type, bit_instance, from_load=from_load)
        sim_info = services.sim_info_manager().get(self._actor_sim_id)
        if sim_info:
            bit_instance.add_appropriateness_buffs(sim_info)

    def _update_client_from_bit_remove(self, bit_type, bit_instance):
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(self._actor_sim_id)
        target_sim_info = sim_info_manager.get(self._target_sim_id)
        self._update_client_for_sim_info_for_bit_remove(bit_type, bit_instance, actor_sim_info, target_sim_info)

    def remove_bit(self, bit):
        if bit not in self._bits:
            logger.debug("Attempting to remove bit for {} that doesn't exist: {}", self, bit)
            return
        bit_instance = self._bits[bit]
        super().remove_bit(bit)
        sim_info = services.sim_info_manager().get(self._actor_sim_id)
        if sim_info is not None:
            bit_instance.remove_appropriateness_buffs(sim_info)

    def remove_track(self, track, on_destroy=False):
        if not self.has_track(track):
            return
        if self.relationship is not None:
            active_bit = self.relationship.get_track(self._actor_sim_id, track).get_active_bit()
            self.relationship.get_track_relationship_data(self._target_sim_id, track).remove_bit(active_bit)
        return super().remove_track(track, on_destroy=on_destroy)

    def save_relationship_data(self, relationship_data_msg):
        super().save_relationship_data(relationship_data_msg)
        if self.bit_added_buffs is not None:
            for buff_id in self.bit_added_buffs:
                relationship_data_msg.bit_added_buffs.append(buff_id)
        if self._knowledge is not None:
            relationship_data_msg.knowledge = self._knowledge.get_save_data()
        sentiment_proximity_cooldown_end = self._sentiment_tracker.proximity_cooldown_end_time
        if sentiment_proximity_cooldown_end is not None:
            relationship_data_msg.sentiment_proximity_cooldown_end = sentiment_proximity_cooldown_end.absolute_ticks()

    def load_relationship_data(self, relationship_data_msg):
        if relationship_data_msg.bit_added_buffs:
            if self.bit_added_buffs is None:
                self.bit_added_buffs = set()
            for bit_added_buff in relationship_data_msg.bit_added_buffs:
                self.bit_added_buffs.add(bit_added_buff)
        super().load_relationship_data(relationship_data_msg)
        if relationship_data_msg.HasField('knowledge'):
            self._knowledge = SimKnowledge(self)
            self._knowledge.load_knowledge(relationship_data_msg.knowledge)
        if relationship_data_msg.HasField('sentiment_proximity_cooldown_end'):
            self._sentiment_tracker.proximity_cooldown_end_time = DateAndTime(relationship_data_msg.sentiment_proximity_cooldown_end)

    def remove_sentiments_by_duration(self, duration_type=None, preserve_active_household_infos=False):
        if preserve_active_household_infos:
            active_household = services.active_household()
            sim_info_manager = services.sim_info_manager()
            actor_sim_info = sim_info_manager.get(self._actor_sim_id)
            target_sim_info = sim_info_manager.get(self._target_sim_id)
            if actor_sim_info in active_household or target_sim_info in active_household:
                return
        tracks_to_remove = []
        for sentiment_track in self._sentiment_tracker:
            if not duration_type is None:
                if sentiment_track.duration == duration_type:
                    tracks_to_remove.append(sentiment_track)
            tracks_to_remove.append(sentiment_track)
        for sentiment_track in tracks_to_remove:
            self.remove_track(sentiment_track.stat_type)

    def notify_relationship_on_lod_change(self, old_lod, new_lod):
        if new_lod < SimInfoLODLevel.INTERACTED:
            self.remove_sentiments_by_duration()
            return
        elif new_lod == SimInfoLODLevel.INTERACTED:
            self.remove_sentiments_by_duration(duration_type=SentimentDurationType.SHORT, preserve_active_household_infos=True)
            return

    def destroy(self):
        self._track_tracker.destroy()
        self._track_tracker = None
        self._sentiment_tracker.destroy()
        self._sentiment_tracker = None
        super().destroy()
        self.bit_added_buffs = None
        self._knowledge = None
        self._actor_sim_id = 0

    def show_bit_added_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_added_notification is None:
            return
        target_sim = target_sim_info.get_sim_instance()
        if sim.is_selectable and sim.is_human:
            if target_sim is None or target_sim.is_selectable and target_sim.is_pet:
                relationship_bit.show_bit_added_dialog(sim, sim, target_sim_info)
            elif not target_sim_info.relationship_tracker.has_bit(sim.id, type(relationship_bit)):
                relationship_bit.show_bit_added_dialog(sim, sim, target_sim_info)
        elif relationship_bit.bit_added_notification.show_if_unselectable and target_sim_info.is_selectable and target_sim_info.is_human:
            relationship_bit.show_bit_added_dialog(target_sim_info, sim, target_sim_info)

    def show_bit_removed_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_removed_notification is None:
            return
        if sim.is_selectable and sim.is_pet:
            return
        target_sim = target_sim_info.get_sim_instance()
        if target_sim is not None or target_sim.is_selectable and target_sim.is_pet:
            relationship_bit.show_bit_removed_dialog(sim, target_sim_info)
        elif not target_sim_info.relationship_tracker.has_bit(sim.id, type(self)):
            relationship_bit.show_bit_removed_dialog(sim, target_sim_info)

    @property
    def sentiment_track_tracker(self) -> 'SentimentTrackTracker':
        return self._sentiment_tracker

    def _write_to_hook(self, bit:'RelationshipBit', sim_info:'SimInfo', target_sim_info:'SimInfo', hook:'_TelemetryHookWriter') -> 'None':
        sentiments_str = '_'.join(str(int(sentiment_track.get_bit_for_client().guid64)) for sentiment_track in self._track_tracker)
        if len(sentiments_str) > 0:
            hook.write_string(TELEMETRY_FIELD_SENTIMENT_IDS, sentiments_str)

    def all_tracks_gen(self) -> 'Generator[RelationshipTrack]':
        chain = itertools.chain(super().all_tracks_gen(), self._sentiment_tracker)
        for track in chain:
            yield track

    def _set_load_in_progress(self, load_in_progress:'bool') -> 'None':
        super()._set_load_in_progress(load_in_progress)
        self._sentiment_tracker.suppress_callback_setup_during_load = load_in_progress
        self._sentiment_tracker.load_in_progress = load_in_progress

    def on_sim_creation(self, sim:'HasSimInfoMixin') -> 'None':
        super().on_sim_creation(sim)
        self._sentiment_tracker.on_sim_creation(sim)

    def enable_player_sim_track_decay(self, to_enable:'bool'=True) -> 'None':
        super().enable_player_sim_track_decay(to_enable)
        self._sentiment_tracker.enable_player_sim_track_decay(to_enable)

    def get_tracker_for_track_type(self, track_type:'RelationshipTrackType') -> 'RelationshipTrackTracker':
        if track_type == RelationshipTrackType.SENTIMENT:
            return self._sentiment_tracker
        return super().get_tracker_for_track_type(track_type)
