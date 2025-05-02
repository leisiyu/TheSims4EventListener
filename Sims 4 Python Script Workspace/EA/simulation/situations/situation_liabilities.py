from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.base import interaction as Interactionfrom interactions import ParticipantTypefrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liability, ReplaceableLiabilityfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunable, TunableReferencefrom situations.situation_sim_providers import SituationSimParticipantProviderMixinfrom situations.situation_types import SituationCallbackOptionfrom situations.tunable import TunableSituationStartimport servicesAUTO_INVITE_LIABILTIY = 'AutoInviteLiability'
class AutoInviteLiability(Liability):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._target_sim = None
        self._situation_id = None
        self._interaction = None

    def on_add(self, interaction):
        self._interaction = interaction
        self._target_sim = interaction.get_participant(ParticipantType.TargetSim)
        situation_manager = services.get_zone_situation_manager()
        self._situation_id = situation_manager.create_visit_situation(self._target_sim)
        situation_manager.bouncer._assign_instanced_sims_to_unfulfilled_requests()

    def release(self):
        if not self._target_sim.is_on_active_lot():
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(self._situation_id)

    def should_transfer(self, continuation):
        return False

class SituationLiabilityBase(Liability, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'cancel_interaction_on_situation_end': Tunable(description='\n            If enabled, we will cancel the interaction with this liability\n            whenever the created situation ends. Note: this will not merge well\n            with another liability that has the opposite setting.\n            ', tunable_type=bool, default=True)}

    def __init__(self, interaction:'Interaction', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._situation_ids = set()
        self._interaction = interaction

    def on_add(self, interaction:'Interaction') -> 'None':
        self._interaction = interaction

    def release(self) -> 'None':
        self._interaction = None
        self.destroy_situations()

    def transfer(self, interaction:'Interaction') -> 'None':
        self._interaction = interaction

    def merge(self, interaction:'Interaction', key:'str', new_liability:'SituationLiabilityBase') -> 'SituationLiabilityBase':
        new_liability._situation_ids.update(self._situation_ids)
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.unregister_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
            situation_manager.register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, new_liability._situation_end_callback)
            self._notify_situation_of_liability(situation_id)
        return new_liability

    def should_transfer(self, continuation:'Interaction') -> 'bool':
        self.validate_situations()
        if not self._situation_ids:
            return False
        return True

    def validate_situations(self) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        invalid_ids = set()
        for situation_id in self._situation_ids:
            if situation_manager.get(situation_id) is None:
                invalid_ids.add(situation_id)
        self._situation_ids.difference_update(invalid_ids)

    def destroy_situations(self) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.unregister_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
            situation_manager.destroy_situation_by_id(situation_id)

    def register_situation_with_liability(self, situation_id:'int') -> 'None':
        self._situation_ids.add(situation_id)
        situation_manager = services.get_zone_situation_manager()
        situation_manager.register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
        self._notify_situation_of_liability(situation_id)

    def _situation_end_callback(self, situation_id:'int', callback_option:'SituationCallbackOption', _) -> 'None':
        if callback_option == SituationCallbackOption.END_OF_SITUATION:
            if self.cancel_interaction_on_situation_end and self._interaction is not None:
                self._interaction.cancel(FinishingType.SITUATIONS, 'Situation owned by liability was destroyed.')
            self._situation_ids.discard(situation_id)

    def _notify_situation_of_liability(self, situation_id:'int') -> 'None':
        situation = services.get_zone_situation_manager().try_get_situation_by_id(situation_id)
        if situation is not None:
            situation.on_add_interaction_liability(self._interaction)

class CreateSituationLiability(SituationLiabilityBase):
    LIABILITY_TOKEN = 'CreateSituationLiability'
    FACTORY_TUNABLES = {'create_situation': TunableSituationStart()}

    def __init__(self, interaction:'Interaction', **kwargs) -> 'None':
        super().__init__(interaction, **kwargs)
        self._situation_created = False

    def on_run(self) -> 'None':
        if not self._situation_created:
            self.create_situation(self._interaction.get_resolver(), situation_created_callback=self.register_situation_with_liability)()

    def register_situation_with_liability(self, situation_id:'int') -> 'None':
        self._situation_created = True
        super().register_situation_with_liability(situation_id)

class RunningSituationLiability(SituationLiabilityBase):
    LIABILITY_TOKEN = 'RunningSituationLiability'
    FACTORY_TUNABLES = {'situation': TunableReference(description='\n            The Situation to check for when this Interaction runs.\n            ', manager=services.get_instance_manager(Types.SITUATION))}

    def on_run(self) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_by_type(self.situation):
            for sim in situation.sims_in_situation():
                if self._interaction.sim == sim:
                    self.register_situation_with_liability(situation.situation_id)

class SituationSimParticipantProviderLiability(ReplaceableLiability, SituationSimParticipantProviderMixin):
    LIABILITY_TOKEN = 'SituationSimParticipantProviderLiability'

    def __init__(self, interaction=None, **__):
        super().__init__(**__)

class RemoveFromSituationLiability(Liability):
    LIABILITY_TOKEN = 'RemoveFromSituationLiability'

    def __init__(self, sim, situation, **kwargs):
        super().__init__(**kwargs)
        self._sim = sim
        self._situation = situation

    def release(self):
        self._situation.remove_sim_from_situation(self._sim)

    def should_transfer(self, continuation):
        return True
