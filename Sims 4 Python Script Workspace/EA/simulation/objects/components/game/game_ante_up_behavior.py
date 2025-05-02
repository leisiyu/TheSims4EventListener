from __future__ import annotationsimport servicesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.components.game_component import GameTeam
    from objects.game_object import GameObject
    from sims.sim import Simfrom objects.components.game.game_behavior_base import GameBehaviorBasefrom sims4.tuning.tunable import Tunable, TunableReferencefrom tag import TunableTagimport sims4import objects.components.typeslogger = sims4.log.Logger('GameAnteUp', default_owner='rpang')
class AnteUpBehavior(GameBehaviorBase):
    FACTORY_TUNABLES = {'default_state_value': TunableReference(description='\n            Default state value of ante object at the start of the game\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)), 'ante_up_state_value': TunableReference(description='\n            State value to apply to object to indicate that it is to be used as an ante for the game\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)), 'item_tag': TunableTag(description='\n            Tag to look for when iterating through objects to know if they are of the correct type to ante up\n            '), 'destroy_ante_on_removing_player': Tunable(description='\n            If checked, ante object is destroyed when player leaves game before game ends.\n            Note that this does not affect the ante object at end of game,\n            the ante object is automatically destroyed if the player loses or returned if the player wins\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._ante_obj = None
        self._ante_owner = None
        self._game_component = None

    def on_player_added(self, sim:'Sim', target:'GameObject') -> 'None':
        if sim is None or sim.is_npc:
            return
        if self._ante_obj is not None:
            return
        self._game_component = target.get_component(objects.components.types.GAME_COMPONENT)
        self._add_ante(sim)

    def on_player_removed(self, sim:'Sim', from_game_ended:'bool'=False) -> 'None':
        if sim is None:
            logger.error('AnteUpBehavior::on_player_removed() Unable to remove ante, sim being removed is invalid')
            return
        if from_game_ended:
            return
        if sim.is_npc or sim is not self._ante_owner:
            return
        if self._game_component is not None:
            player_team = self._game_component.get_team(sim)
            if player_team is not None and player_team.rounds_taken > 0:
                self._remove_ante(self.destroy_ante_on_removing_player)
                return
        self._remove_ante(False)

    def on_game_ended(self, winning_team:'GameTeam', game_object:'GameObject') -> 'None':
        if winning_team is None:
            self._remove_ante(False)

    def on_winner_picked(self, winning_team:'GameTeam') -> 'None':
        if winning_team is None:
            logger.error('AnteUpBehavior::on_winner_picked() Winning team is invalid')
            return
        if self._ante_owner in winning_team.players:
            self._remove_ante(False)
        else:
            self._remove_ante(True)

    def _add_ante(self, sim:'Sim') -> 'None':
        if sim is None:
            logger.error('AnteUpBehavior::_add_ante() Unable to add ante, ante owner sim is invalid')
            return
        sim_inventory = sim.inventory_component
        if sim_inventory is None:
            logger.error('AnteUpBehavior::_add_ante() Unable to get sim inventory to add ante')
            return
        self._ante_obj = None
        self._ante_owner = None
        for obj in sim_inventory:
            if obj.definition.has_build_buy_tag(self.item_tag) and obj.state_value_active(self.ante_up_state_value):
                self._ante_owner = sim
                self._ante_obj = obj
                self._ante_obj.set_state(self.default_state_value.state, self.default_state_value)
                break
        if self._ante_obj is None:
            logger.info('AnteUpBehavior::_add_ante() Unable to find the ante object on player {}', sim.sim_info)
            return
        if self._ante_obj.inventoryitem_component is not None and not self._ante_obj.inventoryitem_component.is_hidden:
            sim_inventory.try_move_object_to_hidden_inventory(self._ante_obj)

    def _remove_ante(self, destroy_ante:'bool') -> 'None':
        if self._ante_obj is None or self._ante_owner is None:
            logger.info('AnteUpBehavior::_remove_ante() Unable to get remove ante, ante object or owner may already have been removed')
            return
        sim_inventory = self._ante_owner.inventory_component
        if sim_inventory is None:
            logger.error('AnteUpBehavior::_remove_ante() Unable to get sim inventory to remove ante')
            return
        if destroy_ante:
            logger.info('AnteUpBehavior::_remove_ante() Destroying ante object {} anted by owner {}', self._ante_obj, self._ante_owner)
            sim_inventory.try_destroy_object(self._ante_obj, count=1, source=self, cause='Destroy ante object due to losing game')
        else:
            logger.info('AnteUpBehavior::_remove_ante() Moving ante object {} back to owner {}', self._ante_obj, self._ante_owner)
            sim_inventory.try_move_hidden_object_to_inventory(self._ante_obj)
        self._ante_obj = None
        self._ante_owner = None
