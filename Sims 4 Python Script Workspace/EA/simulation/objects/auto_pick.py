from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.base.interaction import Interaction
    from objects.game_object import GameObjectimport operatorimport randomfrom interactions import ParticipantTypeSinglefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableVariant, TunableEnumEntryfrom sims4.utils import flexmethodimport servicesimport sims4.loglogger = sims4.log.Logger('AutoPick', default_owner='jdimailig')
class AutoPick(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(randomized_pick=AutoPickRandom.TunableFactory(), best_object_relationship=AutoPickBestObjectRelationship.TunableFactory(), pick_by_proximity=AutoPickProximity.TunableFactory(), locked_args={'disabled': False}, default='disabled', **kwargs)

class AutoPickProximity(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            We will pick the closest eligible object to this participant.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'use_parent_object_proximity': Tunable(description="\n            If checked, when calculating the proximity of child objects to the Participant, we will check proximity \n            of the object's parent instead. E.g. when looking at an item on a bookshelf, we will check the proximity\n            of the bookshelf.\n            ", tunable_type=bool, default=False)}

    def perform_auto_pick(self, choices:'List[GameObject]', interaction:'Interaction'=None) -> 'Optional[GameObject]':
        if interaction:
            proximity_participant = interaction.get_participant(self.participant)
            if proximity_participant is None:
                proximity_participant = interaction.sim
            return interaction.get_choice_by_proximity(choices, proximity_participant, self.use_parent_object_proximity)

class AutoPickRandom(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def perform_auto_pick(choices:'List[GameObject]', interaction:'Interaction'=None) -> 'Optional[GameObject]':
        return random.choice(choices)

class AutoPickBestObjectRelationship(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'exclude_no_relationships': Tunable(description="\n            If checked, objects that haven't had a relationship with the Sim are excluded.\n            ", tunable_type=bool, default=True)}

    def perform_auto_pick(self, choices:'List[GameObject]', interaction:'Interaction'=None) -> 'Optional[GameObject]':
        household = services.active_household()
        if household is None:
            return
        sim_ids = tuple(sim_info.id for sim_info in household.sim_info_gen())
        obj_rel_tuples_list = []
        for choice in choices:
            obj_rel_tuples_list.extend(self._get_obj_rel_tuples_for_sims(choice, sim_ids))
        if not obj_rel_tuples_list:
            return
        return max(obj_rel_tuples_list, key=operator.itemgetter(1))[0]

    def _get_obj_rel_tuples_for_sims(self, obj, sim_ids):
        tuple_list = []
        comp = obj.objectrelationship_component
        if comp is None:
            return tuple_list
        for sim_id in sim_ids:
            if self.exclude_no_relationships:
                if comp.has_relationship(sim_id):
                    tuple_list.append((obj, comp.get_relationship_value(sim_id)))
            tuple_list.append((obj, comp.get_relationship_value(sim_id)))
        return tuple_list
