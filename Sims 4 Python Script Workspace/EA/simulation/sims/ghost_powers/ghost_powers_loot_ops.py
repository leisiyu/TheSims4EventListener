from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from protocolbuffers import Commodities_pb2from protocolbuffers.Consts_pb2 import MSG_SIM_GHOST_BURNOUT_TOGGLEfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableRangeimport distributor
class GhostBurnoutCooldownShaderLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'edge_color_multiplier': TunableRange(description='\n            The visual intensity that this effect will have on the ghost sim.\n            ', tunable_type=float, minimum=0.0, maximum=1.0, default=1.0)}

    def __init__(self, *args, edge_color_multiplier, **kwargs):
        super().__init__(*args, **kwargs)
        self._edge_color_multiplier = edge_color_multiplier

    def _apply_to_subject_and_target(self, subject, target, resolver) -> 'None':
        ghost_burnout_cooldown_shader_msg = Commodities_pb2.CooldownVisualEffectToggle()
        ghost_burnout_cooldown_shader_msg.sim_id = subject.sim_id
        ghost_burnout_cooldown_shader_msg.edge_color_multiplier = self._edge_color_multiplier
        distributor.shared_messages.add_object_message(subject, MSG_SIM_GHOST_BURNOUT_TOGGLE, ghost_burnout_cooldown_shader_msg, False)
