from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from tag import Tag
    from typing import Setimport servicesimport sims4from interactions.context import InteractionContextfrom interactions.priority import Priorityfrom sims.outfits.outfit_enums import OutfitCategory, OutfitChangeReasonfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableReference, TunableEnumEntryfrom situations.custom_states.custom_states_situation import CustomStatesSituationfrom situations.situation_job import SituationJobfrom situations.situation_types import SituationDisplayTypefrom tag import Taglogger = sims4.log.Logger('Wedding Situation Update', default_owner='shipark')
class CustomStateWeddingSituation(CustomStatesSituation):
    INSTANCE_TUNABLES = {'betrothed_job': TunableReference(description='\n            The Situation Job used by the betrothed couple.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), 'move_in_together_interaction': TunableReference(description='\n            The affordance to push on the betrothed sims when the wedding event ends.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'player_outfit_tags_jobs': TunableList(description='\n            The jobs that will use the player defined outfit tags.\n            ', tunable=TunableReference(description='\n                The Situation Job that will include player defined outfit tags in its uniform.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',))), 'outfit_change_reason_default': TunableEnumEntry(description='\n            An override applied to wedding jobs if the player has not selected customized outfit.\n            \n            An enum that represents a reason for outfit change for\n            the outfit system, which determines the category of an outfit.\n            ', tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid, invalid_enums=(OutfitChangeReason.Invalid,)), 'preferred_outfit_category': TunableEnumEntry(description="\n            If a sim's outfit in the tuned category complies with one of the tags in the \n            outfit extra tag set, then use that existing outfit instead of \n            generating a new one for wedding jobs. \n            ", tunable_type=OutfitCategory, default=OutfitCategory.SITUATION)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._betrothed_sims = []

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.betrothed_job:
            self._betrothed_sims.append(sim)

    def on_remove(self):
        super().on_remove()
        if len(self._betrothed_sims) < 2:
            logger.warn('List of betrothed sims is less than two. Failed to push move-in-together interaction.')
            return
        sim = self._betrothed_sims.pop()
        target = self._betrothed_sims.pop()
        if sim is not None and target is not None:
            priority = Priority.High
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, priority)
            sim.push_super_affordance(self.move_in_together_interaction, target, context)

    def has_player_customized_outfit(self, job):
        if job not in self.player_outfit_tags_jobs:
            return False
        if not self._seed.has_user_defined_outfit:
            return False
        return self._seed.guest_attire_style != Tag.INVALID or self._seed.guest_attire_color != Tag.INVALID

    def permit_outfit_generation(self, job):
        return self.has_player_customized_outfit(job)

    def get_preferred_outfit_category(self):
        return self.preferred_outfit_category

    def get_job_outfit_extra_tag_set(self, job:'SituationJob') -> 'Set[Tag]':
        if job not in self.player_outfit_tags_jobs:
            return set()
        return super().get_job_outfit_extra_tag_set(job)
lock_instance_tunables(CustomStateWeddingSituation, situation_display_type_override=SituationDisplayType.ACTIVITY)