import enumfrom carry.put_down_strategy import TunablePutDownStrategySpeciesMappingfrom game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry
class OwnershipMode(enum.Int):
    ANY = 0
    OWNED = 1
    UNOWNED = 2

class SimOverridePutDownStrategyModifierPriority(DynamicEnum):
    DEFAULT = 0

class TunableSimOverridePutDownStrategyModifier(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'put_down_strategy_override': TunablePutDownStrategySpeciesMapping(description='\n            Put down strategy override to add to the sim\n            '), 'ownership_mode': TunableEnumEntry(description='\n            The ownership mode of the object.\n            ', tunable_type=OwnershipMode, default=OwnershipMode.ANY), 'priority': TunableEnumEntry(description='\n            The priority of the SimOverridePutDownStrategyModifier.\n            ', tunable_type=SimOverridePutDownStrategyModifierPriority, default=SimOverridePutDownStrategyModifierPriority.DEFAULT)}

class SimOverridePutDownStrategyModifier(HasTunableSingletonFactory, AutoFactoryInit, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'put_down_strategy_override': TunableSimOverridePutDownStrategyModifier.TunableFactory()}

    def __init__(self, **kwargs):
        super().__init__(GameEffectType.SIM_OVERRIDE_PUT_DOWN_STRATEGY_MODIFIER, **kwargs)

    def apply_modifier(self, sim_info):
        sim_info.add_override_put_down_strategy(self, self.put_down_strategy_override)

    def remove_modifier(self, sim_info, handle):
        sim_info.remove_override_put_down_strategy(self)
