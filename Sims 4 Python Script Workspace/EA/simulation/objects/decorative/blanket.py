from objects.game_object import GameObjectfrom sims4.tuning.tunable import Tunable
class Blanket(GameObject):
    INSTANCE_TUNABLES = {'_allow_different_multi_sim_idles': Tunable(description='\n            If True, multi-Sim postures that target this object will allow the Sim and the linked Sim to use different\n            idle animations. If False, then block idles if the Sims in the multi-Sim posture are trying to do different\n            idles.\n            ', tunable_type=bool, default=True)}

    @property
    def allow_different_multi_sim_idles(self):
        return self._allow_different_multi_sim_idles
