from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info_types import Gender
    from protocolbuffers import GameplaySaveData_pb2from _collections import defaultdictfrom date_and_time import DATE_AND_TIME_ZERO, DateAndTimefrom distributor.rollback import ProtocolBufferRollbackfrom matchmaking.matchmaking_enum import ProfileTypefrom protocolbuffers import ResourceKey_pb2from sims4.protocol_buffer_utils import has_fieldfrom sims.sim_info_types import Ageimport sims4.resources
class MatchmakingProfile:
    __slots__ = ('sim_id', 'region_name', 'real_sim_id', 'profile_bg_res_key', 'sim_info', 'profile_type', 'contacted', 'rel_is_hidden', 'first_name', 'age', 'gender', 'displayed_traits_map', 'exchange_data_creator_name', 'exchange_data_household_id', 'exchange_data_type', 'exchange_data_remote_id', 'trait_ids', 'reported', 'is_from_template', 'family_data', 'pose_index', 'thumbnail_url')

    def __init__(self, sim_id:'int', profile_type:'int', first_name:'str', age:'Age', gender:'Gender', displayed_trait_ids:'List[int]') -> 'None':
        self.sim_id = sim_id
        self.region_name = ''
        self.contacted = False
        self.rel_is_hidden = False
        self.sim_info = None
        self.profile_type = profile_type
        self.first_name = first_name
        self.age = age
        self.gender = gender
        self.displayed_traits_map = defaultdict(int)
        self.family_data = None
        self.pose_index = 0
        self.exchange_data_creator_name = ''
        self.exchange_data_household_id = 0
        self.exchange_data_type = 0
        self.exchange_data_remote_id = ''
        self.profile_bg_res_key = None
        self.real_sim_id = 0
        self.trait_ids = []
        self.reported = False
        self.is_from_template = False
        self.thumbnail_url = ''
        for trait_id in displayed_trait_ids:
            self.displayed_traits_map[trait_id] = 0

    @property
    def get_profile_type(self) -> 'int':
        return self.profile_type

    @property
    def is_gallery_profile(self) -> 'bool':
        return self.profile_type == ProfileType.GALLERY_NPC

    def report_gallery_profile(self) -> 'None':
        self.reported = True

    def save_profile(self, matchmaking_save_data:'GameplaySaveData_pb2.MatchmakingCandidateData()'):
        if self.profile_type == ProfileType.GENERATED_NPC or self.profile_type == ProfileType.GALLERY_NPC:
            self.sim_info.save_sim_info(matchmaking_save_data)
            matchmaking_save_data.trait_ids.extend(self.sim_info.trait_ids)
        matchmaking_save_data.sim_id = self.sim_id
        matchmaking_save_data.region_name = self.region_name
        matchmaking_save_data.displayed_trait_ids.extend(self.displayed_traits_map.keys())
        matchmaking_save_data.first_name = self.first_name
        matchmaking_save_data.profile_type = self.profile_type
        matchmaking_save_data.reported = self.reported
        matchmaking_save_data.is_from_template = self.is_from_template
        matchmaking_save_data.pose_index = self.pose_index
        matchmaking_save_data.contacted = self.contacted
        matchmaking_save_data.real_sim_id = self.real_sim_id
        if self.profile_bg_res_key is not None:
            proto_res_key = ResourceKey_pb2.ResourceKey()
            proto_res_key.type = self.profile_bg_res_key.type
            proto_res_key.group = self.profile_bg_res_key.group
            proto_res_key.instance = self.profile_bg_res_key.instance
            matchmaking_save_data.profile_bg_res_key = proto_res_key
        if self.is_gallery_profile:
            matchmaking_save_data.exchange_data_creator_name = self.exchange_data_creator_name
            matchmaking_save_data.exchange_data_household_id = self.exchange_data_household_id
            matchmaking_save_data.exchange_data_remote_id = self.exchange_data_remote_id
            matchmaking_save_data.exchange_data_type = self.exchange_data_type

class MatchmakingData:

    def __init__(self, sim_id:'int', num_contact_actions:'int') -> 'None':
        self._sim_id = sim_id
        self.selected_ages = {Age.YOUNGADULT, Age.ADULT, Age.ELDER}
        self.selected_trait_ids = set()
        self._time_last_refreshed = DATE_AND_TIME_ZERO
        self.num_contact_actions = num_contact_actions
        self._time_num_contact_action_reset = DATE_AND_TIME_ZERO
        self.candidate_ids = set()
        self.saved_candidate_ids = set()
        self.selfie_res_key = None
        self.bg_res_key = None
        self._is_first_refresh = True
        self.npcs_on_cooldown = {}
        self.gallery_sims_on_cooldown = {}

    def update_last_time_refreshed(self, time:'DateAndTime') -> 'None':
        self._time_last_refreshed = time

    def is_first_refresh(self) -> 'bool':
        return self._is_first_refresh

    def update_first_refresh(self) -> 'None':
        self._is_first_refresh = False

    def get_last_time_refreshed(self) -> 'DateAndTime':
        return self._time_last_refreshed

    def get_time_num_contact_action_reset(self) -> 'DateAndTime':
        return self._time_num_contact_action_reset

    def reset_num_contact_actions(self, num_contact_actions:'int', time:'DateAndTime') -> 'None':
        self.num_contact_actions = num_contact_actions
        self._time_num_contact_action_reset = time

    def contact_action_used(self) -> 'None':
        self.num_contact_actions -= 1

    def has_contact_actions_left(self) -> 'bool':
        return self.num_contact_actions > 0

    def update_selected_ages(self, ages:'Set[Age]') -> 'None':
        self.selected_ages = ages

    def select_traits(self, traits:'Set[int]') -> 'None':
        self.selected_trait_ids = traits

    def clear_candidates(self) -> 'None':
        self.candidate_ids.clear()

    def add_candidate(self, sim_id:'int') -> 'None':
        self.candidate_ids.add(sim_id)

    def remove_candidate(self, sim_id:'int') -> 'None':
        if sim_id in self.candidate_ids:
            self.candidate_ids.remove(sim_id)

    def save_candidate(self, sim_id:'int') -> 'None':
        self.saved_candidate_ids.add(sim_id)

    def remove_saved_candidate(self, sim_id:'int') -> 'None':
        if sim_id in self.saved_candidate_ids:
            self.saved_candidate_ids.remove(sim_id)

    def save_actor_data(self, matchmaking_save_data:'GameplaySaveData_pb2.MatchmakingActorData()'):
        matchmaking_save_data.sim_id = self._sim_id
        matchmaking_save_data.candidate_ids.extend(self.candidate_ids)
        matchmaking_save_data.selected_ages.extend(self.selected_ages)
        matchmaking_save_data.displayed_trait_ids.extend(self.selected_trait_ids)
        matchmaking_save_data.time_last_refreshed = self._time_last_refreshed.absolute_ticks()
        matchmaking_save_data.num_contact_actions = self.num_contact_actions
        matchmaking_save_data.time_num_contact_action_reset = self._time_num_contact_action_reset.absolute_ticks()
        matchmaking_save_data.saved_ids.extend(self.saved_candidate_ids)
        matchmaking_save_data.is_first_refresh = self._is_first_refresh
        for (candidate_id, time) in self.npcs_on_cooldown.items():
            if hasattr(matchmaking_save_data, 'npcs_on_cooldown'):
                with ProtocolBufferRollback(matchmaking_save_data.npcs_on_cooldown) as npcs_on_cooldown:
                    npcs_on_cooldown.sim_id = candidate_id
                    npcs_on_cooldown.absolute_ticks = time.absolute_ticks()
        for (remote_id, time) in self.gallery_sims_on_cooldown.items():
            if hasattr(matchmaking_save_data, 'gallery_sims_on_cooldown'):
                with ProtocolBufferRollback(matchmaking_save_data.gallery_sims_on_cooldown) as gallery_sim_on_cooldown:
                    gallery_sim_on_cooldown.remote_id = remote_id
                    gallery_sim_on_cooldown.absolute_ticks = time.absolute_ticks()
        if self.selfie_res_key is not None:
            proto_res_key = ResourceKey_pb2.ResourceKey()
            proto_res_key.type = self.selfie_res_key.type
            proto_res_key.group = self.selfie_res_key.group
            proto_res_key.instance = self.selfie_res_key.instance
            matchmaking_save_data.selfie_res_key = proto_res_key
        if self.bg_res_key is not None:
            proto_res_key = ResourceKey_pb2.ResourceKey()
            proto_res_key.type = self.bg_res_key.type
            proto_res_key.group = self.bg_res_key.group
            proto_res_key.instance = self.bg_res_key.instance
            matchmaking_save_data.bg_res_key = proto_res_key

    def load_actor_data(self, actor_save_data:'GameplaySaveData_pb2.MatchmakingActorData()'):
        self._sim_id = actor_save_data.sim_id
        self._time_last_refreshed = DateAndTime(actor_save_data.time_last_refreshed)
        self.num_contact_actions = actor_save_data.num_contact_actions
        self._time_num_contact_action_reset = DateAndTime(actor_save_data.time_num_contact_action_reset)
        self._is_first_refresh = actor_save_data.is_first_refresh
        if has_field(actor_save_data, 'selfie_res_key'):
            self.selfie_res_key = sims4.resources.Key()
            self.selfie_res_key.type = actor_save_data.selfie_res_key.type
            self.selfie_res_key.group = actor_save_data.selfie_res_key.group
            self.selfie_res_key.instance = actor_save_data.selfie_res_key.instance
        if has_field(actor_save_data, 'bg_res_key'):
            self.bg_res_key = sims4.resources.Key()
            self.bg_res_key.type = actor_save_data.bg_res_key.type
            self.bg_res_key.group = actor_save_data.bg_res_key.group
            self.bg_res_key.instance = actor_save_data.bg_res_key.instance
        for sim_id in actor_save_data.candidate_ids:
            self.add_candidate(sim_id)
        for sim_id in actor_save_data.saved_ids:
            self.saved_candidate_ids.add(sim_id)
        self.selected_ages.clear()
        for age in actor_save_data.selected_ages:
            if age == Age.YOUNGADULT:
                self.selected_ages.add(Age.YOUNGADULT)
            elif age == Age.ADULT:
                self.selected_ages.add(Age.ADULT)
            elif age == Age.ELDER:
                self.selected_ages.add(Age.ELDER)
        for trait_id in actor_save_data.displayed_trait_ids:
            self.selected_trait_ids.add(trait_id)
        if hasattr(actor_save_data, 'npcs_on_cooldown'):
            for npc_cooldowns in actor_save_data.npcs_on_cooldown:
                self.npcs_on_cooldown[npc_cooldowns.sim_id] = DateAndTime(npc_cooldowns.absolute_ticks)
        if hasattr(actor_save_data, 'gallery_sims_on_cooldown'):
            for gallery_sim_cooldowns in actor_save_data.gallery_sims_on_cooldown:
                self.gallery_sims_on_cooldown[gallery_sim_cooldowns.remote_id] = DateAndTime(gallery_sim_cooldowns.absolute_ticks)
