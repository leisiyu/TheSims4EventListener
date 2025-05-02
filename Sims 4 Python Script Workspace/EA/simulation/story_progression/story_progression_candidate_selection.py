from __future__ import annotationsimport randomimport servicesimport sims4from event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom filters.tunable import TunableAggregateFilterfrom sims4.math import EPSILONfrom sims4.random import weighted_random_item, weighted_random_indexfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, Tunablefrom story_progression.story_progression_lot_selection import StoryProgressionLotSelectionfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.household import Household
    from sims.sim_info import SimInfo
    from zone import Zone
    from story_progression.story_progression_arc import BaseStoryArc
    from typing import *
class BaseCandidateSelectionFunction(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'None':
        if demographic_sim_infos is not None:
            for sim in tuple(demographic_sim_infos):
                household = sim.household
                rule_set = household.story_progression_rule_set
                if not household.scenario_tracker.active_scenario is not None:
                    if not sim.story_progression_tracker.can_add_arc(arc):
                        demographic_sim_infos.remove(sim)
                demographic_sim_infos.remove(sim)
        if demographic_households is not None:
            household_manager = services.household_manager()
            for household_id in tuple(demographic_households):
                household = household_manager.get(household_id)
                rule_set = household.story_progression_rule_set
                if not household.scenario_tracker.active_scenario is not None:
                    if not household.story_progression_tracker.can_add_arc(arc):
                        demographic_households.remove(household_id)
                demographic_households.remove(household_id)

class BaseMultiSimCandidateSelectionFunction(BaseCandidateSelectionFunction):
    FACTORY_TUNABLES = {'count': Tunable(description='\n            The number of Sims to return. Candidate selection will fail if this many Sims are not found.\n            ', tunable_type=int, default=2)}

class SelectSimCandidateFromDemographicListFunction(BaseCandidateSelectionFunction):

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[SimInfo], Optional[Household], Optional[Zone]]':
        super().__call__(demographic_sim_infos, demographic_households, demographic_zones, arc)
        if not demographic_sim_infos:
            return (None, None, None)
        return (random.choice(demographic_sim_infos), None, None)

class SelectSimCandidateFromFilterFunction(BaseCandidateSelectionFunction):
    FACTORY_TUNABLES = {'sim_filter': TunableReference(description='\n            The Sim Filter that we will use in order to determine the candidate Sim.\n            ', manager=services.get_instance_manager(Types.SIM_FILTER))}

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[SimInfo], Optional[Household], Optional[Zone]]':
        results = services.sim_filter_service().submit_filter(self.sim_filter, callback=None, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, required_story_progression_arc=arc, allow_yielding=False, gsi_source_fn=lambda : 'Sim candidate for Story Progression arc')
        if not results:
            return (None, None, None)
        return (weighted_random_item([(result.score, result.sim_info) for result in results]), None, None)

class SelectMultipleSimCandidatesFromDemographicListFunction(BaseMultiSimCandidateSelectionFunction):

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[List[SimInfo]], Optional[Household], Optional[Zone]]':
        super().__call__(demographic_sim_infos, demographic_households, demographic_zones, arc)
        if demographic_sim_infos and len(demographic_sim_infos) < self.count:
            return (None, None, None)
        return (random.sample(demographic_sim_infos, self.count), None, None)

class SelectMultipleSimCandidatesFromFilterFunction(BaseMultiSimCandidateSelectionFunction):
    FACTORY_TUNABLES = {'sim_filter': TunableReference(description='\n            The Sim Filter that we will use in order to determine the candidate Sims.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',))}

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[List[SimInfo]], Optional[Household], Optional[Zone]]':
        results = services.sim_filter_service().submit_filter(self.sim_filter, callback=None, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, required_story_progression_arc=arc, allow_yielding=False, gsi_source_fn=lambda : 'Sim candidates for Story Progression arc')
        if results and len(results) < self.count:
            return (None, None, None)
        selected_sims = list()
        pairs = list((result.score, result.sim_info) for result in results)
        for i in range(self.count):
            chosen_index = weighted_random_index(pairs)
            selected_sims.append(pairs[chosen_index][1])
            pairs.pop(chosen_index)
        return (selected_sims, None, None)

class SelectMultipleSimCandidatesFromAggregateFunction(BaseCandidateSelectionFunction):
    FACTORY_TUNABLES = {'aggregate_filter': TunableReference(description='\n            The Aggregate Filter that we will use in order to determine the candidate Sims.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableAggregateFilter',))}

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[List[SimInfo]], Optional[Household], Optional[Zone]]':
        results = services.sim_filter_service().submit_filter(self.aggregate_filter, callback=None, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, required_story_progression_arc=arc, allow_yielding=False, gsi_source_fn=lambda : 'Sim candidates for Story Progression arc')
        num_results = len(results)
        filter_count = self.aggregate_filter.get_filter_count()
        if num_results < filter_count:
            return (None, None, None)
        if num_results > filter_count:
            selected_sims = [results[0].sim_info]
            pairs = list((result.score, result.sim_info) for result in results)
            pairs.pop(0)
            for i in range(filter_count - 1):
                chosen_index = weighted_random_index(pairs)
                selected_sims.append(pairs[chosen_index][1])
                pairs.pop(chosen_index)
            return (selected_sims, None, None)
        return ([result.sim_info for result in results], None, None)

class SelectHouseholdCandidateMatchingLotFromDemographicListFunction(BaseCandidateSelectionFunction):

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[SimInfo], Optional[Household], Optional[Zone]]':
        possible_households = list(services.household_manager().values())
        for household in tuple(possible_households):
            if household.is_active_household:
                possible_households.remove(household)
            else:
                rule_set = household.story_progression_rule_set
                if not rule_set.verify(arc.required_rules):
                    possible_households.remove(household)
                elif not household.story_progression_tracker.can_add_arc(arc):
                    possible_households.remove(household)
        if demographic_zones:
            possible_zones = demographic_zones.copy()
            if possible_zones:
                zone_id = possible_zones.pop(random.randint(0, len(possible_zones) - 1))
                templates_and_bed_data = StoryProgressionLotSelection.get_household_templates_and_bed_data(zone_id)
                (total_beds, lot_has_double_bed, lot_has_kid_bed) = templates_and_bed_data
                if total_beds <= 0:
                    pass
                else:
                    weighted_households = StoryProgressionLotSelection.get_available_households(possible_households, total_beds, lot_has_double_bed, lot_has_kid_bed)
                    if not weighted_households:
                        pass
                    else:
                        return (None, weighted_random_item(weighted_households), zone_id)
        return (None, None, None)

class SelectHouseholdWithHomeCandidateFromDemographicListBasedOnCullingScoreFunction(BaseCandidateSelectionFunction):
    FACTORY_TUNABLES = {'invalid_household_test': TunableTestSet(description='\n                Ideally, you should not use this and Engineer should work on a way to set and saves the rules on a premade household. \n                A set of tests that every sims of the household will do. If one fail, the household will not be a valid candidate.\n                ')}

    def __call__(self, demographic_sim_infos:'Set[SimInfo]', demographic_households:'Set[Household]', demographic_zones:'Set[Zone]', arc:'BaseStoryArc') -> 'Tuple[Optional[SimInfo], Optional[Household], Optional[Zone]]':
        super().__call__(demographic_sim_infos, demographic_households, demographic_zones, arc)
        culling_service = services.get_culling_service()
        household_manager = services.household_manager()
        weighted_households = []
        for household_id in demographic_households:
            household = household_manager.get(household_id)
            if household is None:
                pass
            elif household.home_zone_id == 0:
                pass
            else:
                household_sims_valid = True
                if len(self.invalid_household_test) > 0:
                    for household_sim in household.sim_info_gen():
                        resolver = SingleSimResolver(household_sim)
                        if self.invalid_household_test.run_tests(resolver):
                            household_sims_valid = False
                            break
                if not household_sims_valid:
                    pass
                else:
                    weight = max(culling_service.get_culling_score_for_sim_info(sim_info).score for sim_info in household)
                    if weight <= 0:
                        weight = EPSILON
                    weighted_households.append((1/weight, household_id))
        if not weighted_households:
            return (None, None, None)
        return (None, weighted_random_item(weighted_households), None)
