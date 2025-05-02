from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from animation.animation_utils import AnimationOverrides
    from objects.components.game_component import GameTeam
    from objects.game_object import GameObject
    from sims.sim import Simfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactoryimport sims4logger = sims4.log.Logger('GameBehavior', default_owner='rpang')
class GameBehaviorBase(HasTunableFactory, AutoFactoryInit):

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)

    def on_setup_game(self, game_object:'GameObject') -> 'None':
        pass

    def on_player_added(self, sim:'Sim', target:'GameObject') -> 'None':
        pass

    def on_player_removed(self, sim:'Sim', from_game_ended:'bool'=False) -> 'None':
        pass

    def on_winner_picked(self, winning_team:'GameTeam') -> 'None':
        pass

    def on_game_ended(self, winning_team:'GameTeam', game_object:'GameObject') -> 'None':
        pass

    def additional_anim_overrides_gen(self) -> 'Iterator[AnimationOverrides]':
        pass
