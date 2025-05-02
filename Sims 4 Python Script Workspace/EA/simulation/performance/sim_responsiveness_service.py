from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.base.interaction import Interactionfrom sims4.service_manager import Serviceimport servicesimport sims4import timeINVALID_RESPONSIVENESS_VALUE = -1.0
class SimResponsivenessService(Service):

    def __init__(self):
        self._rsp_player_directed = INVALID_RESPONSIVENESS_VALUE
        self._rsp_non_player_directed = INVALID_RESPONSIVENESS_VALUE
        self._pending_interaction_dict = dict()
        self.callback_player_directed = None
        self.enabled = False

    def on_zone_load(self) -> 'None':
        self.enabled = True

    def on_zone_unload(self) -> 'None':
        self.enabled = False
        self.reset()

    def on_game_paused(self) -> 'None':
        self._pending_interaction_dict.clear()
        self.enabled = False

    def on_game_unpaused(self) -> 'None':
        self.enabled = True

    def start_metrics(self, interaction:'Interaction', context_responsiveness:'float'=0) -> 'None':
        if not self.enabled:
            return
        if not interaction.is_super:
            return
        if interaction.id in self._pending_interaction_dict:
            return
        is_player_directed = interaction.sim is not None and (interaction.sim.is_selectable and interaction.is_user_directed)
        guid64 = interaction.guid64 if is_player_directed and hasattr(interaction, 'guid64') else None
        self._pending_interaction_dict[interaction.id] = (self.get_time() - context_responsiveness, is_player_directed, guid64)

    def stop_metrics(self, interaction:'Interaction', should_report:'bool'=False) -> 'None':
        if not self.enabled:
            return
        if interaction.id not in self._pending_interaction_dict:
            return
        (start_time, is_player_directed, guid64) = self._pending_interaction_dict.pop(interaction.id)
        if not should_report:
            return
        end_time = self.get_time()
        responsiveness = end_time - start_time
        if responsiveness <= 0:
            return
        if is_player_directed:
            self.add_entry_player_directed(responsiveness)
            if self.callback_player_directed is not None and guid64 is not None:
                interaction_type = services.get_instance_manager(sims4.resources.Types.INTERACTION).get(guid64)
                msg = 'Responsiveness (Player Directed): {:.3f} s. Interaction: {}'.format(responsiveness, interaction_type)
                self.callback_player_directed(msg)
        else:
            self.add_entry_non_player_directed(responsiveness)

    def add_entry_player_directed(self, delta:'float') -> 'None':
        self._rsp_player_directed = max(delta, self._rsp_player_directed)

    def add_entry_non_player_directed(self, delta:'float') -> 'None':
        self._rsp_non_player_directed = max(delta, self._rsp_non_player_directed)

    def reset(self) -> 'None':
        self.reset_records()
        self._pending_interaction_dict.clear()
        self.callback_player_directed = None

    def reset_records(self) -> 'None':
        self._rsp_player_directed = INVALID_RESPONSIVENESS_VALUE
        self._rsp_non_player_directed = INVALID_RESPONSIVENESS_VALUE

    @staticmethod
    def get_time() -> 'float':
        return time.perf_counter()

    def get_responsiveness(self) -> 'Tuple(float, float)':
        result = (self._rsp_player_directed, self._rsp_non_player_directed)
        self.reset_records()
        return result
