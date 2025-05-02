from __future__ import annotationsfrom sims.occult.occult_enums import OccultTypefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from collections import Iterable
    from sims.sim import Sim
    from sims.sim_info import SimInfofrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims.occult.occult_tracker import OccultTrackerfrom tag import TunableTagsfrom protocolbuffers import GameplaySaveData_pb2import randomimport servicesimport sims4from server_commands.household_commands import trigger_move_out_for_reincarnationfrom sims.household_enums import HouseholdChangeOriginfrom sims4.localization import TunableLocalizedStringFactoryfrom sims.sim_info_types import Agefrom sims.sim_spawner import SimSpawner, SimCreatorfrom sims4.math import MAX_UINT32from sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePackSafeReference, TunableList, TunableTuple, TunableReferencelogger = sims4.log.Logger('Tuning', default_owner='ycao')
class ReincarnationData:

    def __init__(self, previous_sim_id:'int', trait_ids:'int', has_shown_reincarnation_animation:'bool') -> 'None':
        self.previous_sim_id = previous_sim_id
        self.trait_ids = trait_ids
        self.has_shown_reincarnation_animation = has_shown_reincarnation_animation

    @staticmethod
    def generate_reincarnation_data_msg(sim_info:'SimInfo') -> 'GameplaySaveData_pb2.ReincarnationData':
        reincarnation_data_msg = GameplaySaveData_pb2.ReincarnationData()
        reincarnation_data_msg.previous_sim_id = sim_info.reincarnation_data.previous_sim_id
        reincarnation_data_msg.trait_ids.extend(sim_info.reincarnation_data.trait_ids)
        reincarnation_data_msg.has_shown_reincarnation_animation = sim_info.reincarnation_data.has_shown_reincarnation_animation
        return reincarnation_data_msg

class ReincarnationService(Service):
    REINCARNATION_TRAIT = TunablePackSafeReference(description='\n        Trait that gets added to the new sim, when the current sim reincarnated.\n        ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT))
    REINCARNATION_COUNT_STATISTIC = TunablePackSafeReference(description='\n        The statistic on a reincarnated Sim that represents the number of times they reincarnated.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
    REINCARNATION_START_AFFORDANCE = TunablePackSafeReference(description="\n        Affordance that will be applied to reincarnated sim when reincarnated sim enter's live mode the first time.\n        This is the interaction that will be used to show animation when reincarnated sim arrives lot the first time.\n        ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',))
    SAVE_LOCK_TOOLTIP = TunableLocalizedStringFactory(description='\n        The tooltip/message to show when the player tries to save the game while reincarnation is happening\n        ')
    REINCARNATION_TRAIT_TO_PASS_TAGS = TunableTags(description="\n        traits with these tags will be passed onto sims' next incarnation of life and will be available to \n        apply to the new sim through peer into soul interaction.\n        ")

    def __init__(self, *args, **kwargs):
        self._current_new_household_id = None
        super().__init__(*args, **kwargs)

    def reincarnation(self, reincarnated_sim_info:'SimInfo', reincarnate_immediately:'bool'=False) -> 'bool':
        sim_creator = SimCreator(age=Age.INFANT, gender=reincarnated_sim_info.gender, first_name=reincarnated_sim_info.first_name, last_name=reincarnated_sim_info.last_name)
        source_sim_household = reincarnated_sim_info.household
        new_sim_household = services.household_manager().create_household(reincarnated_sim_info.account)
        self._current_new_household_id = new_sim_household.id
        zone_id = source_sim_household.home_zone_id
        (sim_info_list, _) = SimSpawner.create_sim_infos((sim_creator,), household=new_sim_household, account=reincarnated_sim_info.account, zone_id=zone_id, generate_deterministic_sim=True, creation_source='reincarnation', household_change_origin=HouseholdChangeOrigin.REINCARNATION)
        new_sim_info = sim_info_list[0]
        new_sim_info.world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
        for trait in tuple(new_sim_info.trait_tracker.personality_traits):
            new_sim_info.remove_trait(trait)
        for trait_data in OccultTracker.OCCULT_DATA.values():
            if reincarnated_sim_info.has_trait(trait_data.occult_trait):
                new_sim_info.add_trait(trait_data.occult_trait)
        new_sim_info.apply_genetics(reincarnated_sim_info, reincarnated_sim_info, seed=random.randint(1, MAX_UINT32))
        new_sim_info.resend_extended_species()
        new_sim_info.resend_physical_attributes()
        trait_ids_to_pass = [trait.guid64 for trait in reincarnated_sim_info.trait_tracker.get_traits_with_tags(self.REINCARNATION_TRAIT_TO_PASS_TAGS)]
        previous_personality_traits = reincarnated_sim_info.trait_tracker.personality_traits
        previous_personality_trait_ids = [trait.guid64 for trait in previous_personality_traits if trait.persistable]
        new_sim_info.set_reincarnation_data(reincarnated_sim_info.id, trait_ids_to_pass + previous_personality_trait_ids, False)
        relationship_service = services.relationship_service()
        for relationship in relationship_service._get_relationships_for_sim(reincarnated_sim_info.id):
            relationship.add_reincarnation_bits(reincarnated_sim_info.id, new_sim_info)
        if self.REINCARNATION_TRAIT:
            new_sim_info.add_trait(self.REINCARNATION_TRAIT)
        reincarnated_sim_info.apply_reincarnation_carry_over_traits(new_sim_info)
        new_statistic_tracker = new_sim_info.statistic_tracker
        if new_statistic_tracker is not None and self.REINCARNATION_COUNT_STATISTIC is not None:
            new_statistic_tracker.add_statistic(self.REINCARNATION_COUNT_STATISTIC)
        previous_count_stat = reincarnated_sim_info.get_statistic(self.REINCARNATION_COUNT_STATISTIC)
        if previous_count_stat:
            new_sim_info.add_statistic(self.REINCARNATION_COUNT_STATISTIC, previous_count_stat.get_value())
        client = services.client_manager().get_client_by_household_id(new_sim_info.household_id)
        if client is not None:
            client.add_selectable_sim_info(new_sim_info)
        reincarnated_sim_occult_tracker = reincarnated_sim_info.occult_tracker
        if reincarnated_sim_occult_tracker and reincarnated_sim_occult_tracker.get_current_occult_types() == OccultType.MERMAID:
            reincarnated_sim_occult_tracker.switch_to_occult_type(OccultType.HUMAN)
        if reincarnate_immediately:
            trigger_move_out_for_reincarnation(new_sim_household.id, services.current_zone_id())
        return True

    def trigger_move_out_for_reincarnation(self) -> 'None':
        trigger_move_out_for_reincarnation(self._current_new_household_id, services.current_zone_id())

    def get_sim_reincarnation_times(self, sim_id:'int') -> 'int':
        sim_info_manager = services.sim_info_manager()
        sim_info = sim_info_manager.get(sim_id)
        stat_type = self.REINCARNATION_COUNT_STATISTIC
        if sim_info.statistic_tracker is not None:
            reincarnation_stat = sim_info.statistic_tracker.get_statistic(stat_type)
            if reincarnation_stat is not None:
                return int(reincarnation_stat.get_value())
        return 0

    def on_all_sims_spawned(self) -> 'None':
        if self.REINCARNATION_START_AFFORDANCE is None:
            return
        for sim in self._newly_reincarnated_sim_gen():
            sim.opacity = 0

    def on_loading_screen_animation_finished(self) -> 'None':
        for sim in self._newly_reincarnated_sim_gen():
            sim.sim_info.reincarnation_data.has_shown_reincarnation_animation = True
            if self.REINCARNATION_START_AFFORDANCE is None:
                return
            context = InteractionContext(sim=sim, source=InteractionContext.SOURCE_SCRIPT, priority=Priority.High, run_priority=Priority.High, insert_strategy=QueueInsertStrategy.FIRST)
            result = sim.push_super_affordance(self.REINCARNATION_START_AFFORDANCE, sim, context)
            if not result:
                sim.opacity = 1
                logger.error('Failed to push reincarnation start affordance on sim {}. Result: {}', sim, result, owner='yecao')
            return

    def get_lock_save_reason(self):
        return self.SAVE_LOCK_TOOLTIP()

    def _newly_reincarnated_sim_gen(self) -> 'Iterable[Sim]':
        household = services.active_household()
        if household is not None:
            for sim_info in household:
                sim_reincarnation_data = sim_info.reincarnation_data
                if sim_reincarnation_data is not None and not sim_reincarnation_data.has_shown_reincarnation_animation:
                    sim = sim_info.get_sim_instance()
                    if sim is None:
                        pass
                    else:
                        yield sim
