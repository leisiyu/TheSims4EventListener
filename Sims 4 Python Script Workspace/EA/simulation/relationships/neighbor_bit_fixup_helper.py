from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from relationships.relationship_bit import RelationshipBit
    from sims.household import Household
    from sims.sim_info import SimInfo
    from typing import *import itertoolsfrom _collections import defaultdictfrom relationships.global_relationship_tuning import RelationshipGlobalTuningimport servicesimport sims4logger = sims4.log.Logger('Neighbor Bit Fixup Helper', default_owner='shipark')
class NeighborBitFixupHelper:

    def __init__(self):
        self._world_to_households = defaultdict(set)
        self._master_plex_to_households = defaultdict(set)
        self._create_household_dictionaries()

    @staticmethod
    def _validate_multi_unit_neighbor_bit(zone_id:'int', master_plex_id:'int') -> 'None':
        if zone_id == 0:
            return False
        sim_master_plex_id = services.get_plex_service().get_master_zone_id(zone_id)
        return sim_master_plex_id == master_plex_id

    @staticmethod
    def _validate_neighbor_bit(zone_id:'int', world_id:'int') -> 'bool':
        if zone_id == 0:
            return False
        sim_world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
        return sim_world_id == world_id

    def _update_neighbor_rel_between_sims(self, sim_id_a:'int', sim_id_b:'int', relbit:'RelationshipBit', add:'bool'=True) -> 'bool':
        relationship = services.relationship_service()._find_relationship(sim_id_a, sim_id_b)
        if relationship is None:
            return
        household_manager = services.household_manager()
        if household_manager.get_by_sim_id(sim_id_a) is not None and household_manager.get_by_sim_id(sim_id_b) == household_manager.get_by_sim_id(sim_id_a):
            relationship.remove_bit(sim_id_a, sim_id_b, relbit, notify_client=True, send_rel_change_event=True)
            return
        if add:
            relationship.add_relationship_bit(sim_id_a, sim_id_b, relbit, notify_client=True, send_rel_change_event=True)
        else:
            relationship.remove_bit(sim_id_a, sim_id_b, relbit, notify_client=True, send_rel_change_event=True)

    def _update_sim_neighbors(self, sim_info:'SimInfo', neighbor_household:'Household', relbit:'RelationshipBit', add:'bool'=True) -> 'None':
        sim_id = sim_info.id
        for neighbor_sim_info in neighbor_household:
            neighbor_id = neighbor_sim_info.id
            self._update_neighbor_rel_between_sims(sim_id, neighbor_id, relbit, add=add)

    def _apply_neighborhood_bits_between_households(self, household_a:'Household', household_b:'Household', relbit:'RelationshipBit', add:'bool'=True) -> 'None':
        for (sim_info_a, sim_info_b) in itertools.product(household_a, household_b):
            sim_info_id_a = sim_info_a.id
            sim_info_id_b = sim_info_b.id
            self._update_neighbor_rel_between_sims(sim_info_id_a, sim_info_id_b, relbit, add=add)

    def _create_household_dictionaries(self):
        plex_service = services.get_plex_service()
        persistence_service = services.get_persistence_service()
        household_manager = services.household_manager()
        for household in household_manager.values():
            home_zone_id = household.home_zone_id
            if home_zone_id != 0:
                sim_home_zone_proto_buffer = persistence_service.get_zone_proto_buff(home_zone_id)
                if sim_home_zone_proto_buffer is None:
                    logger.error('Invalid zone protocol buffer in RelationshipService._add_neighbor_bits() for {}', household)
                else:
                    self._world_to_households[sim_home_zone_proto_buffer.world_id].add(household.id)
                    if plex_service.is_zone_a_multi_unit(home_zone_id):
                        master_zone_id = plex_service.get_master_zone_id(home_zone_id)
                        self._master_plex_to_households[master_zone_id].add(household.id)

    def _update_neighborhood_relationships(self, sim_info:'SimInfo', old_zone_id:'int', new_zone_id:'int', household_mapping:'Dict[int, Set[int]]', validation_func:'Callable[[int, int], bool]', relbit:'RelationshipBit') -> 'None':
        old_zone_key = None
        new_zone_key = None
        household_manager = services.household_manager()
        for (key_value, hh_ids) in household_mapping.items():
            households = [household_manager.get(hh_id) for hh_id in hh_ids]
            if old_zone_key:
                break
            if new_zone_key and validation_func(new_zone_id, key_value):
                new_zone_key = key_value
                for neighbor_household in households:
                    self._update_sim_neighbors(sim_info, neighbor_household, relbit)
            elif validation_func(old_zone_id, key_value):
                old_zone_key = key_value
                for neighbor_household in households:
                    self._update_sim_neighbors(sim_info, neighbor_household, relbit, add=False)

    def add_neighbor_bits(self) -> 'None':
        household_manager = services.household_manager()
        for household_ids in self._world_to_households.values():
            households = [household_manager.get(hh_id) for hh_id in household_ids]
            for (household_a, household_b) in itertools.combinations(households, 2):
                self._apply_neighborhood_bits_between_households(household_a, household_b, RelationshipGlobalTuning.NEIGHBOR_RELATIONSHIP_BIT)
        for household_ids in self._master_plex_to_households.values():
            households = [household_manager.get(hh_id) for hh_id in household_ids]
            for (household_a, household_b) in itertools.combinations(households, 2):
                self._apply_neighborhood_bits_between_households(household_a, household_b, RelationshipGlobalTuning.MULTI_UNIT_NEIGHBOR_RELATIONSHIP_BIT)

    def handle_sim_home_zone_changed(self, sim_info:'SimInfo', old_zone_id:'int', new_zone_id:'int') -> 'None':
        self._update_neighborhood_relationships(sim_info, old_zone_id, new_zone_id, self._world_to_households, self._validate_neighbor_bit, RelationshipGlobalTuning.NEIGHBOR_RELATIONSHIP_BIT)
        self._update_neighborhood_relationships(sim_info, old_zone_id, new_zone_id, self._master_plex_to_households, self._validate_multi_unit_neighbor_bit, RelationshipGlobalTuning.MULTI_UNIT_NEIGHBOR_RELATIONSHIP_BIT)
