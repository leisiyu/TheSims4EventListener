from __future__ import annotationsfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom relationships.compatibility_tuning import CompatibilityTuningfrom sims4.common import Pack, is_available_packfrom sims4.utils import staticpropertyfrom traits.preference_enums import PreferenceSubject, PreferenceTypesimport servicesimport sims4import telemetry_helperfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from cas.cas_preference_item import CasPreferenceItem
    from relationships.sim_knowledge import SimKnowledge
    from traits.preference import Preference
    from traits.trait_tracker import TraitTracker
    from typing import *TELEMETRY_GROUP_RELATIONSHIPS = 'RSHP'TELEMETRY_HOOK_COMPATIBILITY = 'COMP'TELEMETRY_FIELD_SIM_1_ID = 'sim1'TELEMETRY_FIELD_SIM_2_ID = 'sim2'TELEMETRY_FIELD_COMP_LVL = 'comp'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_RELATIONSHIPS)
class Compatibility:
    __slots__ = ('_score', '_level', '_sim_id_a', '_sim_id_b')

    def __init__(self, sim_id_a:'int', sim_id_b:'int'):
        self._sim_id_a = min(sim_id_a, sim_id_b)
        self._sim_id_b = max(sim_id_a, sim_id_b)
        self._score = CompatibilityTuning.COMPATIBILITY_SCORE_DEFAULT
        self._level = None

    @staticproperty
    def required_packs() -> 'Tuple[Pack, ...]':
        return (Pack.EP13,)

    @property
    def sim_id_a(self):
        return self._sim_id_a

    @property
    def sim_id_b(self):
        return self._sim_id_b

    def find_sim_info_a(self):
        return services.sim_info_manager().get(self._sim_id_a)

    def find_sim_info_b(self):
        return services.sim_info_manager().get(self._sim_id_b)

    def get_score(self):
        return self._score

    def get_level(self):
        return self._level

    def _set_level(self):
        for (level, range) in CompatibilityTuning.COMPATIBILITY_LEVEL_THRESHOLDS.items():
            if self._score < range.upper_bound and self._score >= range.lower_bound:
                self._level = level

    def assign_npc_preferences(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot_action in CompatibilityTuning.NPC_PREFERENCE_LOOT:
            loot_action.apply_to_resolver(resolver)

    def _calculate_score_sim(self, trait_tracker_one:'TraitTracker', trait_tracker_two:'TraitTracker') -> 'int':
        score = 0
        for preference in trait_tracker_one.preferences:
            score += self._calculate_score_for_preference(preference, trait_tracker_two)
        return score

    @staticmethod
    def _calculate_score_for_preference(sim_preference:'Preference', target_trait_tracker:'TraitTracker', use_knowledge:'bool'=False, sim_knowledge:'SimKnowledge'=None) -> 'int':
        score = 0
        if use_knowledge and sim_knowledge is None:
            return score
        if sim_preference.is_preference_subject(PreferenceSubject.CHARACTERISTIC):
            preference_item = sim_preference.preference_item
            for (trait, trait_score) in preference_item.trait_map.items():
                if use_knowledge and trait not in sim_knowledge.known_traits:
                    pass
                elif target_trait_tracker.has_trait(trait):
                    if sim_preference.trait_type == PreferenceTypes.LIKE:
                        if trait.trait_type == PreferenceTypes.DISLIKE:
                            score -= trait_score
                        else:
                            score += trait_score
                            if sim_preference.trait_type == PreferenceTypes.DISLIKE:
                                if trait.trait_type == PreferenceTypes.DISLIKE:
                                    score += trait_score
                                else:
                                    score -= trait_score
                    elif sim_preference.trait_type == PreferenceTypes.DISLIKE:
                        if trait.trait_type == PreferenceTypes.DISLIKE:
                            score += trait_score
                        else:
                            score -= trait_score
        return score

    def calculate_score(self):
        if not any(is_available_pack(pack) for pack in self.required_packs):
            return
        sim_info_a = self.find_sim_info_a()
        sim_info_b = self.find_sim_info_b()
        if sim_info_a is None or sim_info_b is None:
            return
        if sim_info_a.is_toddler_or_younger or sim_info_b.is_toddler_or_younger:
            return
        trait_tracker_a = sim_info_a.trait_tracker
        trait_tracker_b = sim_info_b.trait_tracker
        if trait_tracker_a is None or trait_tracker_b is None:
            return
        previous_level = self._level
        overall_score = CompatibilityTuning.COMPATIBILITY_SCORE_DEFAULT
        overall_score += self._calculate_score_sim(trait_tracker_a, trait_tracker_b)
        overall_score += self._calculate_score_sim(trait_tracker_b, trait_tracker_a)
        self._score = sims4.math.clamp(CompatibilityTuning.COMPATIBILITY_SCORE_RANGE.lower_bound, overall_score, CompatibilityTuning.COMPATIBILITY_SCORE_RANGE.upper_bound)
        self._set_level()
        if self._level != previous_level:
            resolver_a = DoubleSimResolver(sim_info_a, sim_info_b)
            resolver_b = DoubleSimResolver(sim_info_b, sim_info_a)
            if self._level in CompatibilityTuning.COMPATIBILITY_LEVEL_LOOT_MAP:
                loot = CompatibilityTuning.COMPATIBILITY_LEVEL_LOOT_MAP[self._level]
                loot.apply_to_resolver(resolver_a)
                loot.apply_to_resolver(resolver_b)
            if previous_level is not None:
                if sim_info_a.is_player_sim:
                    self._send_telemetry_for_level_change(sim_info_a, sim_info_b)
                elif sim_info_b.is_player_sim:
                    self._send_telemetry_for_level_change(sim_info_b, sim_info_a)

    @staticmethod
    def calculate_score_for_preference(sim_id_a:'int', sim_id_b:'int', scored_preference:'CasPreferenceItem', use_knowledge=False) -> 'int':
        sim_info_a = services.sim_info_manager().get(sim_id_a)
        sim_info_b = services.sim_info_manager().get(sim_id_b)
        if sim_info_a is None or sim_info_b is None:
            return CompatibilityTuning.COMPATIBILITY_SCORE_DEFAULT
        if sim_info_a.is_toddler_or_younger or sim_info_b.is_toddler_or_younger:
            return CompatibilityTuning.COMPATIBILITY_SCORE_DEFAULT
        trait_tracker_a = sim_info_a.trait_tracker
        trait_tracker_b = sim_info_b.trait_tracker
        if trait_tracker_a is None or trait_tracker_b is None:
            return CompatibilityTuning.COMPATIBILITY_SCORE_DEFAULT
        preference = None
        if scored_preference.like in trait_tracker_a.preferences:
            preference = scored_preference.like
        elif scored_preference.dislike in trait_tracker_a.preferences:
            preference = scored_preference.dislike
        else:
            return CompatibilityTuning.COMPATIBILITY_SCORE_DEFAULT
        sim_knowledge = sim_info_a.relationship_tracker.get_knowledge(sim_id_b) if use_knowledge else None
        return sims4.math.clamp(CompatibilityTuning.COMPATIBILITY_SCORE_RANGE.lower_bound, Compatibility._calculate_score_for_preference(preference, trait_tracker_b, use_knowledge, sim_knowledge), CompatibilityTuning.COMPATIBILITY_SCORE_RANGE.upper_bound)

    def save_compatibility(self, relationship_data_msg):
        if self._score is not None:
            relationship_data_msg.compatibility_score = self._score
        if self._level is not None:
            relationship_data_msg.compatibility_level = self._level

    def load_compatibility(self, relationship_data_msg):
        if relationship_data_msg.HasField('compatibility_score'):
            self._score = relationship_data_msg.compatibility_score
        if relationship_data_msg.HasField('compatibility_level'):
            self._level = relationship_data_msg.compatibility_level

    def _send_telemetry_for_level_change(self, sim_info_1, sim_info_2):
        household = services.active_household()
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_COMPATIBILITY, household=household) as hook:
            hook.write_guid(TELEMETRY_FIELD_SIM_1_ID, sim_info_1.id)
            hook.write_guid(TELEMETRY_FIELD_SIM_2_ID, sim_info_2.id)
            hook.write_int(TELEMETRY_FIELD_COMP_LVL, self.get_level())
