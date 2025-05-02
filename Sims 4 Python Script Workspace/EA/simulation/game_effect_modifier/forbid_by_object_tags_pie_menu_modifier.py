import servicesfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import OptionalTunable, HasTunableSingletonFactory, AutoFactoryInit, Tunablefrom tag import TunableTags
class ForbidByObjectTagsPieMenuModifier(HasTunableSingletonFactory, AutoFactoryInit, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'suppression_tooltip': OptionalTunable(description='\n            If supplied, interactions are disabled with this tooltip.\n            ', tunable=TunableLocalizedStringFactory(description='Reason of failure.')), 'forbidden_object_tags': TunableTags(description='\n            List of tags to look for in the game objects we want to forbid player interaction with.\n            '), 'whitelisted_object_tags': TunableTags(description='\n            List of tags that will let the game object be allowed even if the game object has a tag from the\n            list of forbidden tags.\n        '), 'tests': TunableTestSet(description="\n            Tests are run first. \n            If there are no tests or it fails we then check the whitelisted_objects_tags to see if the object being \n            tested has any of the tags.\n            If the object does not have any then we check that the object doesn't have any of the tags in the \n            forbidden_object_tags list.\n            "), 'off_lot_objects_always_allowed': Tunable(description='\n            If True, every objects that are not part of the active lot will be allowed by default.\n            ', tunable_type=bool, default=True)}

    def __init__(self, **kwargs):
        super().__init__(GameEffectType.FORBID_BY_OBJECT_TAGS_PIE_MENU_MODIFIER, **kwargs)

    def is_game_object_allowed(self, game_object) -> bool:
        if game_object.is_game_object():
            if self.off_lot_objects_always_allowed and not game_object.is_on_active_lot(tolerance=0):
                return True
            if self.tests is not None and len(self.tests) > 0:
                active_sim = services.get_active_sim()
                resolver = SingleSimResolver(active_sim)
                if self.tests.run_tests(resolver):
                    return True
            if any(game_object.has_tag(whitelisted_tag) for whitelisted_tag in self.whitelisted_object_tags):
                return True
            elif any(game_object.has_tag(forbidden_tag) for forbidden_tag in self.forbidden_object_tags):
                return False
        return True
