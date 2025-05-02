from __future__ import annotationsimport servicesimport sims4.logfrom interactions import ParticipantTypeSavedStoryProgressionSim, ParticipantTypeSavedStoryProgressionStringfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunableEnumEntry, TunableTuplefrom story_progression.story_progression_actions.story_progression_action_base import BaseSimStoryProgressionActionfrom story_progression.story_progression_enums import StoryTypefrom story_progression.story_progression_result import StoryProgressionResult, StoryProgressionResultTypefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *logger = sims4.log.Logger('Story Progression Actions')
class RelationshipModifiedStoryProgressionAction(BaseSimStoryProgressionAction):
    FACTORY_TUNABLES = {'store_relationship_bit_name': TunableTuple(description='\n            Store the bit name of the tuned relationship track between\n            the Sims in this Chapter.\n            ', track=TunableReference(description='\n                The relationship track to look for the bit name of.\n                ', manager=services.get_instance_manager(Types.STATISTIC), class_restrictions=('RelationshipTrack',)), participant_type=TunableEnumEntry(description='\n                Participant type to store the track bit name as.\n                ', tunable_type=ParticipantTypeSavedStoryProgressionString, default=ParticipantTypeSavedStoryProgressionString.SavedStoryProgressionString1)), 'store_partner_sim': OptionalTunable(description='\n            If tuned, stores the partner Sim as the tuned participant.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSavedStoryProgressionSim, default=ParticipantTypeSavedStoryProgressionSim.SavedStoryProgressionSim1))}

    def _run_story_progression_action(self) -> 'StoryProgressionResult':
        if self._owner_arc.arc_type != StoryType.MULTI_SIM_BASED:
            return StoryProgressionResult(StoryProgressionResultType.FAILED_ACTION, 'RelationshipModifiedStoryProgressionAction requires a Multi-Sim Arc.')
        sim_info_a = self._owner_arc.sim_info
        sim_id_b = self._owner_arc.retrieve_participant(ParticipantTypeSavedStoryProgressionSim.SavedStoryProgressionSim1)
        if sim_id_b is None:
            return StoryProgressionResult(StoryProgressionResultType.FAILED_ACTION, 'RelationshipModified Action does not have enough Sims to run.')
        sim_info_b = services.sim_info_manager().get(sim_id_b)
        if not services.relationship_service().has_relationship_track(sim_info_a.id, sim_info_b.id, self.store_relationship_bit_name.track):
            return StoryProgressionResult(StoryProgressionResultType.FAILED_ACTION, 'RelTrack {} not found between {} and {}.', self.store_relationship_bit_name.track, sim_info_a, sim_info_b)
        return StoryProgressionResult(StoryProgressionResultType.SUCCESS_MAKE_HISTORICAL)

    def _save_participants(self) -> 'None':
        super()._save_participants()
        sim_id_a = self._owner_arc.sim_info.id
        sim_id_b = self._owner_arc.retrieve_participant(ParticipantTypeSavedStoryProgressionSim.SavedStoryProgressionSim1)
        if sim_id_b is None:
            logger.error('RelationshipModified Action does not have enough Sims to run.')
        track = services.relationship_service().get_relationship_track(sim_id_a, sim_id_b, self.store_relationship_bit_name.track)
        self._owner_arc.store_participant(self.store_relationship_bit_name.participant_type, track.get_active_bit_by_value().display_name())
        if self.store_partner_sim and not self._owner_arc.has_participant(self.store_partner_sim, sim_id_b):
            self._owner_arc.store_participant(self.store_partner_sim, sim_id_b)
