import servicesimport sims4from game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableReference, TunableList
class AdventureMomentSuccessModifier(HasTunableSingletonFactory, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'description': '\n            The modifier makes it so that the option a player selects on an adventure moment (i.e. chance cards) \n            will give a good/successful outcome.\n            \n            Currently, this modifier is hard coded to look for the outcome with positive career performance.\n            ', 'success_modifiers': TunableList(description='\n            "The statistic(s) we are aiming to increase with the adventure moment outcomes', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True))}

    def __init__(self, success_modifiers):
        super().__init__(GameEffectType.ADVENTURE_MOMENTS_SUCCESS_MODIFIER)
        self._success_modifiers = success_modifiers

    def apply_modifier(self, sim_info):
        if self._success_modifiers is None:
            return
        if sim_info.adventure_tracker is None:
            return
        sim_info.adventure_tracker.apply_success_override(self._success_modifiers)

    def remove_modifier(self, sim_info, handle):
        if self._success_modifiers is None:
            return
        if sim_info.adventure_tracker is None:
            return
        sim_info.adventure_tracker.remove_success_override()
