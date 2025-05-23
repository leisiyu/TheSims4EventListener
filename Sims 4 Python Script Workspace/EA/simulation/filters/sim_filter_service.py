from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from clubs.club import Club
    from date_and_time import DateAndTime
    from filters.tunable import BaseFilterTerm, TunableSimFilter, TunableAggregateFilter
    from sims.household import Household
    from sims.sim_info import SimInfo
    from story_progression.story_progression_arc import BaseStoryArc
    from typing import *import collectionsfrom filters import sim_filter_handlersfrom filters.tunable import FilterResult, FilterTermTagfrom interactions.liability import Liabilityfrom objects import ALL_HIDDEN_REASONSfrom random import shufflefrom sims4 import randomfrom sims4.service_manager import Servicefrom singletons import EMPTY_SETimport enumimport filtersimport gsi_handlers.sim_filter_service_handlersimport servicesimport sims4.loglogger = sims4.log.Logger('SimFilter')SIM_FILTER_GLOBAL_BLACKLIST_LIABILITY = 'SimFilterGlobalBlacklistLiability'
class SimFilterGlobalBlacklistReason(enum.Int, export=False):
    PHONE_CALL = 1
    SIM_INFO_BEING_REMOVED = 2
    MISSING_PET = 3
    RABBIT_HOLE = 4
SIM_FILTER_DIALOG_BLACKLIST_REASONS = [SimFilterGlobalBlacklistReason.SIM_INFO_BEING_REMOVED]
class SimFilterGlobalBlacklistLiability(Liability):

    def __init__(self, blacklist_sim_ids, reason, **kwargs):
        super().__init__(**kwargs)
        self._blacklist_sim_ids = blacklist_sim_ids
        self._reason = reason
        self._has_been_added = False

    def on_add(self, _):
        if self._has_been_added:
            return
        sim_filter_service = services.sim_filter_service()
        if sim_filter_service is not None:
            for sim_id in self._blacklist_sim_ids:
                services.sim_filter_service().add_sim_id_to_global_blacklist(sim_id, self._reason)
        self._has_been_added = True

    def release(self):
        sim_filter_service = services.sim_filter_service()
        if sim_filter_service is not None:
            for sim_id in self._blacklist_sim_ids:
                services.sim_filter_service().remove_sim_id_from_global_blacklist(sim_id, self._reason)

class SimFilterRequestState(enum.Int, export=False):
    SETUP = ...
    RAN_QUERY = ...
    SPAWNING_SIMS = ...
    FILLED_RESULTS = ...
    COMPLETE = ...

class _BaseSimFilterRequest:

    def __init__(self, callback=None, callback_event_data=None, blacklist_sim_ids=None, gsi_logging_data=None, sim_gsi_logging_data=None, required_story_progression_arc=None):
        self._state = SimFilterRequestState.SETUP
        self._callback = callback
        self._callback_event_data = callback_event_data
        self._blacklist_sim_ids = set(blacklist_sim_ids) if blacklist_sim_ids is not None else set()
        self._gsi_logging_data = gsi_logging_data
        self._sim_gsi_logging_data = sim_gsi_logging_data
        self._required_story_progression_arc = required_story_progression_arc

    @property
    def is_complete(self):
        return self._state == SimFilterRequestState.COMPLETE

    def run(self):
        raise NotImplementedError

    def run_without_yielding(self):
        raise NotImplementedError

    def gsi_start_logging(self, request_type, filter_type, yielding, gsi_source_fn):
        if gsi_handlers.sim_filter_service_handlers.archiver.enabled:
            self._gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData(request_type, str(filter_type), yielding, gsi_source_fn)
        if sim_filter_handlers.archiver.enabled:
            self._sim_gsi_logging_data = sim_filter_handlers.SimFilterGSILoggingData(request_type, str(filter_type), gsi_source_fn)

    def gsi_add_rejected_sim_info(self, sim_info, reason, filter_term=None):
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_rejected_sim_info(sim_info, reason, filter_term)

    def gsi_archive_logging(self, filter_results):
        if self._gsi_logging_data is not None:
            gsi_handlers.sim_filter_service_handlers.archive_filter_request(filter_results, self._gsi_logging_data)
            self._gsi_logging_data = None

    def get_filter_conflicts(self, filter_terms:'List[BaseFilterTerm]') -> 'Optional[List[BaseFilterTerm]]':
        approved_filters = []
        for filter_term in filter_terms:
            for approved_filter in approved_filters:
                if not filter_term.is_compatible(approved_filter):
                    return [approved_filter, filter_term]
            approved_filters.append(filter_term)

class _SimFilterRequest(_BaseSimFilterRequest):

    def __init__(self, sim_filter=None, requesting_sim_info=None, sim_constraints=None, household_id=None, start_time=None, end_time=None, club=None, tag=FilterTermTag.NO_TAG, optional=True, gsi_source_fn=None, additional_filter_terms=(), include_rabbithole_sims=False, include_missing_pets=False, **kwargs):
        super().__init__(**kwargs)
        if sim_filter is None:
            sim_filter = filters.tunable.TunableSimFilter.BLANK_FILTER
        self._sim_filter = sim_filter
        self._additional_filter_terms = additional_filter_terms
        self._requesting_sim_info = requesting_sim_info
        self._sim_constraints = sim_constraints
        if household_id is not None:
            self._household_id = household_id
        elif requesting_sim_info:
            self._household_id = requesting_sim_info.household_id
        else:
            self._household_id = 0
        if start_time is not None:
            self._start_time = start_time.time_since_beginning_of_week()
        else:
            self._start_time = None
        if end_time is not None:
            self._end_time = end_time.time_since_beginning_of_week()
        else:
            self._end_time = None
        self._club = club
        self.tag = tag
        self.optional = optional
        self._gsi_source_fn = gsi_source_fn
        self._include_rabbithole_sims = include_rabbithole_sims
        self._include_missing_pets = include_missing_pets

    def run(self):
        if self._state == SimFilterRequestState.SETUP:
            logger.assert_raise(self._sim_filter is not None, '[rez] Sim Filter is None in _SimFilterRequest.')
            self.gsi_start_logging('_SimFilterRequest', self._sim_filter, False, self._gsi_source_fn)
            results = self._run_filter_query()
            if self._callback is not None:
                self._callback(results, self._callback_event_data)
            self._state = SimFilterRequestState.COMPLETE
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_metadata(None, None, self._club, self._blacklist_sim_ids, self.optional, self._required_story_progression_arc)
            self.gsi_archive_logging(results)

    def run_without_yielding(self):
        self.gsi_start_logging('_SimFilterRequest ', self._sim_filter, True, self._gsi_source_fn)
        results = self._run_filter_query()
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_metadata(None, None, self._club, self._blacklist_sim_ids, self.optional, self._required_story_progression_arc)
        self.gsi_archive_logging(results)
        return results

    def _get_constrained_sims(self):
        return self._sim_constraints

    def _run_filter_query(self):
        constrained_sim_ids = self._get_constrained_sims()
        results = self._find_sims_matching_filter(constrained_sim_ids=constrained_sim_ids, start_time=self._start_time, end_time=self._end_time, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, club=self._club, tag=self.tag)
        sim_filter_service = services.sim_filter_service()
        global_blacklist = sim_filter_service.get_global_blacklist()
        for result in tuple(results):
            sim_info = result.sim_info
            if sim_info.id in self._blacklist_sim_ids or sim_info.id in global_blacklist:
                reasons = sim_filter_service.get_global_blacklist_reason(sim_info.id)
                if reasons:
                    num_reasons = len(reasons)
                    if SimFilterGlobalBlacklistReason.RABBIT_HOLE in reasons:
                        num_reasons -= 1
                    if SimFilterGlobalBlacklistReason.MISSING_PET in reasons:
                        num_reasons -= 1
                    if self._include_rabbithole_sims and self._include_missing_pets and num_reasons == 0:
                        pass
                    else:
                        results.remove(result)
                        self.gsi_add_rejected_sim_info(sim_info, 'Global Blacklisted' if sim_info.id in global_blacklist else 'Filter Request Blacklisted')
                        if self._sim_gsi_logging_data is not None:
                            sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Global Blacklisted' if sim_info.id in global_blacklist else 'Filter Request Blacklisted')
                            if self._required_story_progression_arc is not None:
                                rule_set = sim_info.household.story_progression_rule_set
                                if not rule_set.verify(self._required_story_progression_arc.required_rules):
                                    results.remove(result)
                                    self.gsi_add_rejected_sim_info(sim_info, 'Missing Required Story Progression Rules')
                                    if self._sim_gsi_logging_data is not None:
                                        sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Missing Required Story Progression Rules')
                                        if not sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc):
                                            results.remove(result)
                                            self.gsi_add_rejected_sim_info(sim_info, 'Cannot seed arc on Sim.')
                                            if self._sim_gsi_logging_data is not None:
                                                sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Cannot seed arc on Sim.')
                                elif not sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc):
                                    results.remove(result)
                                    self.gsi_add_rejected_sim_info(sim_info, 'Cannot seed arc on Sim.')
                                    if self._sim_gsi_logging_data is not None:
                                        sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Cannot seed arc on Sim.')
                else:
                    results.remove(result)
                    self.gsi_add_rejected_sim_info(sim_info, 'Global Blacklisted' if sim_info.id in global_blacklist else 'Filter Request Blacklisted')
                    if self._sim_gsi_logging_data is not None:
                        sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Global Blacklisted' if sim_info.id in global_blacklist else 'Filter Request Blacklisted')
                        if self._required_story_progression_arc is not None:
                            rule_set = sim_info.household.story_progression_rule_set
                            if not rule_set.verify(self._required_story_progression_arc.required_rules):
                                results.remove(result)
                                self.gsi_add_rejected_sim_info(sim_info, 'Missing Required Story Progression Rules')
                                if self._sim_gsi_logging_data is not None:
                                    sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Missing Required Story Progression Rules')
                                    if not sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc):
                                        results.remove(result)
                                        self.gsi_add_rejected_sim_info(sim_info, 'Cannot seed arc on Sim.')
                                        if self._sim_gsi_logging_data is not None:
                                            sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Cannot seed arc on Sim.')
                            elif not sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc):
                                results.remove(result)
                                self.gsi_add_rejected_sim_info(sim_info, 'Cannot seed arc on Sim.')
                                if self._sim_gsi_logging_data is not None:
                                    sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Cannot seed arc on Sim.')
            elif self._required_story_progression_arc is not None:
                rule_set = sim_info.household.story_progression_rule_set
                if not rule_set.verify(self._required_story_progression_arc.required_rules):
                    results.remove(result)
                    self.gsi_add_rejected_sim_info(sim_info, 'Missing Required Story Progression Rules')
                    if self._sim_gsi_logging_data is not None:
                        sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Missing Required Story Progression Rules')
                        if not sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc):
                            results.remove(result)
                            self.gsi_add_rejected_sim_info(sim_info, 'Cannot seed arc on Sim.')
                            if self._sim_gsi_logging_data is not None:
                                sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Cannot seed arc on Sim.')
                elif not sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc):
                    results.remove(result)
                    self.gsi_add_rejected_sim_info(sim_info, 'Cannot seed arc on Sim.')
                    if self._sim_gsi_logging_data is not None:
                        sim_filter_handlers.archive_filter_request(sim_info, self._sim_gsi_logging_data, rejected=True, reason='Cannot seed arc on Sim.')
        return results

    def _calculate_sim_filter_score(self, sim_info, filter_terms, start_time=None, end_time=None, tag=FilterTermTag.NO_TAG, **kwargs):
        total_result = FilterResult(sim_info=sim_info, tag=tag)
        start_time_ticks = start_time.absolute_ticks() if start_time is not None else None
        end_time_ticks = end_time.absolute_ticks() if end_time is not None else None
        for filter_term in filter_terms:
            result = filter_term.calculate_score(sim_info, start_time_ticks=start_time_ticks, end_time_ticks=end_time_ticks, **kwargs)
            result.score = max(result.score, filter_term.minimum_filter_score)
            if self._sim_gsi_logging_data is not None:
                self._sim_gsi_logging_data.add_filter(str(filter_term), result.score)
            total_result.combine_with_other_filter_result(result)
            if total_result.score == 0:
                self.gsi_add_rejected_sim_info(sim_info, '0 score', filter_term)
                if self._sim_gsi_logging_data is not None:
                    sim_filter_handlers.archive_filter_request(result.sim_info, self._sim_gsi_logging_data, rejected=True, reason='0 Score')
                break
        return total_result

    def _find_sims_matching_filter(self, constrained_sim_ids=None, **kwargs):
        filter_terms = self._sim_filter.get_filter_terms()
        if self._additional_filter_terms:
            filter_terms += self._additional_filter_terms
        sim_info_manager = services.sim_info_manager()
        results = []
        sim_ids = constrained_sim_ids if constrained_sim_ids is not None else sim_info_manager.keys()
        for sim_id in sim_ids:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            else:
                result = self._calculate_sim_filter_score(sim_info, filter_terms, **kwargs)
                if result.score > 0:
                    results.append(result)
        if self._sim_filter.use_weighted_random and len(results) > filters.tunable.TunableSimFilter.TOP_NUMBER_OF_SIMS_TO_LOOK_AT:
            shuffle(results)
        return results

class _MatchingFilterRequest(_SimFilterRequest):

    def __init__(self, number_of_sims_to_find:'int'=1, continue_if_constraints_fail:'bool'=False, conform_if_constraints_fail:'bool'=False, zone_id:'int'=None, allow_instanced_sims:'bool'=False, display_dialog_only:'bool'=False, optional:'bool'=True, gsi_source_fn:'Callable[None, str]'=None, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._continue_if_constraints_fail = continue_if_constraints_fail
        self._conform_if_constraints_fail = conform_if_constraints_fail
        self._number_of_sims_to_find = number_of_sims_to_find
        self._filter_results = []
        self._zone_id = zone_id
        self._allow_instanced_sims = allow_instanced_sims
        self._display_dialog_only = display_dialog_only
        self.optional = optional
        self._gsi_source_fn = gsi_source_fn

    def _select_sims_from_results(self, results, sims_to_spawn):
        self._filter_results = []
        self._filter_results_info = []
        if not self._display_dialog_only:
            blacklist = services.sim_filter_service().get_global_blacklist()
        else:
            blacklist = services.sim_filter_service().get_dialog_blacklist()
        for result in tuple(results):
            sim_info = result.sim_info
            if not sim_info.id in blacklist:
                if self._required_story_progression_arc is not None and not (sim_info.household.story_progression_rule_set.verify(self._required_story_progression_arc) or sim_info.story_progression_tracker.can_add_arc(self._required_story_progression_arc)):
                    results.remove(result)
            results.remove(result)
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        if self._sim_filter.use_weighted_random:
            index = filters.tunable.TunableSimFilter.TOP_NUMBER_OF_SIMS_TO_LOOK_AT
            randomization_group = [(result.score, result) for result in sorted_results[:index]]
            while index < len(sorted_results) and len(self._filter_results) < sims_to_spawn:
                random_choice = random.pop_weighted(randomization_group)
                randomization_group.append((sorted_results[index].score, sorted_results[index]))
                logger.info('Sim ID matching request {0}', random_choice)
                self._filter_results.append(random_choice)
                self._filter_results_info.append(random_choice.sim_info)
                index += 1
            if randomization_group:
                while True:
                    while randomization_group and len(self._filter_results) < self._number_of_sims_to_find:
                        random_choice = random.pop_weighted(randomization_group)
                        logger.info('Sim ID matching request {0}', random_choice)
                        self._filter_results.append(random_choice)
                        self._filter_results_info.append(random_choice.sim_info)
        else:
            for result in sorted_results:
                if len(self._filter_results) == sims_to_spawn:
                    break
                logger.info('Sim ID matching request {0}', result.sim_info)
                self._filter_results.append(result)
                self._filter_results_info.append(result.sim_info)
        if self._sim_gsi_logging_data is not None:
            for result in self._filter_results:
                sim_filter_handlers.archive_filter_request(result.sim_info, self._sim_gsi_logging_data, rejected=False, reason='Score > 0 and chosen for spawning')
        return self._filter_results

    def _run_filter_query(self):
        results = None
        constrained_sim_ids = self._get_constrained_sims()
        if constrained_sim_ids is not None:
            results = self._find_sims_matching_filter(constrained_sim_ids=constrained_sim_ids, start_time=self._start_time, end_time=self._end_time, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, club=self._club, tag=self.tag)
            if results or not self._continue_if_constraints_fail:
                return self._filter_results
            self._select_sims_from_results(results, self._number_of_sims_to_find)
            if len(self._filter_results) == self._number_of_sims_to_find or not self._continue_if_constraints_fail:
                return self._filter_results
        results = self._find_sims_matching_filter(start_time=self._start_time, end_time=self._end_time, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, club=self._club, tag=self.tag)
        if results:
            self._filter_results.extend(self._select_sims_from_results(results, self._number_of_sims_to_find - len(self._filter_results)))

    def _create_sim_info(self):
        filter_terms = self._sim_filter.get_filter_terms() + self._additional_filter_terms + self._sim_filter.get_additional_conform_terms()
        filter_conflicts = self.get_filter_conflicts(filter_terms)
        if filter_conflicts:
            logger.warn('Prevented sim_filter_service from spawning a new sim for SituationJob {}. Conflicting filter requirements detected: {} vs. {}', self._callback_event_data.job_type if self._callback_event_data else None, filter_conflicts[0], filter_conflicts[1], owner='hbabaran')
            return False
        blacklist_sim_ids = tuple(self._blacklist_sim_ids)
        blacklist_sim_ids += tuple(result.sim_info.sim_id for result in self._filter_results)
        if not self._sim_filter.repurpose_game_breaker:
            blacklist_sim_ids += tuple(sim.sim_info.sim_id for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS))
        create_result = self._sim_filter.create_sim_info(zone_id=self._zone_id, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, blacklist_sim_ids=blacklist_sim_ids, start_time=self._start_time, end_time=self._end_time, additional_filter_terms=self._additional_filter_terms, sim_constraints=self._sim_constraints)
        if create_result:
            fake_filter_result = FilterResult(sim_info=create_result.sim_info, tag=self.tag)
            self._filter_results.append(fake_filter_result)
            logger.info('Created Sim ID to match request {0}', create_result.sim_info.id)
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_created_household(create_result.sim_info.household, was_successful=True)
            if self._sim_gsi_logging_data is not None:
                sim_filter_handlers.archive_filter_request(create_result.sim_info, self._sim_gsi_logging_data, rejected=False, reason='Created to match the filter')
            return True
        else:
            if self._gsi_logging_data is not None and create_result.sim_info is not None:
                self._gsi_logging_data.add_created_household(create_result.sim_info.household, was_successful=False)
            return False

    def _create_sim_infos(self):
        while len(self._filter_results) < self._number_of_sims_to_find:
            if not self._create_sim_info():
                break

    def _should_try_conform(self):
        return not self._sim_constraints or (self._continue_if_constraints_fail or self._conform_if_constraints_fail)

    def run(self):
        if self._state == SimFilterRequestState.SETUP:
            self.gsi_start_logging('_MatchingFilterRequest', self._sim_filter, False, self._gsi_source_fn)
            self._run_filter_query()
            if len(self._filter_results) == self._number_of_sims_to_find or not self._should_try_conform():
                self._state = SimFilterRequestState.FILLED_RESULTS
            else:
                self._state = SimFilterRequestState.RAN_QUERY
        if self._state == SimFilterRequestState.RAN_QUERY:
            self._state = SimFilterRequestState.SPAWNING_SIMS
            return
        if self._state == SimFilterRequestState.SPAWNING_SIMS:
            result = self._create_sim_info()
            if result and len(self._filter_results) == self._number_of_sims_to_find:
                self._state = SimFilterRequestState.FILLED_RESULTS
        if self._state == SimFilterRequestState.FILLED_RESULTS:
            self._callback(self._filter_results, self._callback_event_data)
            self._state = SimFilterRequestState.COMPLETE
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_metadata(self._number_of_sims_to_find, self._allow_instanced_sims, self._club, self._blacklist_sim_ids, self.optional, self._required_story_progression_arc)
            self.gsi_archive_logging(self._filter_results)

    def run_without_yielding(self):
        self.gsi_start_logging('_MatchingFilterRequest', self._sim_filter, True, self._gsi_source_fn)
        self._run_filter_query()
        if self._should_try_conform():
            self._create_sim_infos()
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_metadata(self._number_of_sims_to_find, self._allow_instanced_sims, self._club, self._blacklist_sim_ids, self.optional, self._required_story_progression_arc)
        self.gsi_archive_logging(self._filter_results)
        return self._filter_results

class _AggregateFilterRequest(_BaseSimFilterRequest):

    def __init__(self, aggregate_filter=None, filter_sims_with_matching_filter_request=True, gsi_source_fn=None, additional_filter_terms=(), **kwargs):
        super().__init__(**kwargs)
        self._aggregate_filter = aggregate_filter
        self._additional_filter_terms = additional_filter_terms
        self._filter_sims_with_matching_filter_request = filter_sims_with_matching_filter_request
        logger.assert_raise(aggregate_filter is not None, 'Filter is None in _AggregateFilterRequest.')
        self._leader_filter_request = None
        self._non_leader_filter_requests = []
        self._leader_sim_info = None
        self._filter_results = []
        self._gsi_source_fn = gsi_source_fn

    def run(self):
        if self._state == SimFilterRequestState.SETUP:
            self.gsi_start_logging('_AggregateFilterRequest', self._aggregate_filter, False, self._gsi_source_fn)
            self._create_leader()
            if self._leader_sim_info is None:
                self._state = SimFilterRequestState.COMPLETE
                self._callback([], self._callback_event_data)
                if self._gsi_logging_data is not None:
                    self._gsi_logging_data.add_metadata(None, None, None, self._blacklist_sim_ids, None, self._required_story_progression_arc)
                self.gsi_archive_logging(self._filter_results)
                return
            self._create_non_leader_filter_requests()
            self._state = SimFilterRequestState.SPAWNING_SIMS
            return
        if self._state == SimFilterRequestState.SPAWNING_SIMS:
            if self._non_leader_filter_requests:
                filter_to_run = self._non_leader_filter_requests.pop()
                result = self._run_sim_filter(filter_to_run)
                if result or filter_to_run.optional:
                    return
                self._filter_results.clear()
                self._state = SimFilterRequestState.FILLED_RESULTS
                return
            self._state = SimFilterRequestState.FILLED_RESULTS
        if self._state == SimFilterRequestState.FILLED_RESULTS:
            self._callback(self._filter_results, self._callback_event_data)
            self._state = SimFilterRequestState.COMPLETE
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_metadata(None, None, None, self._blacklist_sim_ids, None, self._required_story_progression_arc)
            self.gsi_archive_logging(self._filter_results)

    def run_without_yielding(self):
        self.gsi_start_logging('_AggregateFilterRequest', self._aggregate_filter, True, self._gsi_source_fn)
        self._create_leader()
        if self._leader_sim_info is None:
            return []
        self._create_non_leader_filter_requests()
        for filter_to_run in self._non_leader_filter_requests:
            result = self._run_sim_filter(filter_to_run)
            if not result:
                if filter_to_run.optional:
                    pass
                else:
                    self._filter_results.clear()
                    return self._filter_results
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_metadata(None, None, None, self._blacklist_sim_ids, None, self._required_story_progression_arc)
        self.gsi_archive_logging(self._filter_results)
        return self._filter_results

    def _create_leader(self):
        self._create_leader_filter_request()
        filter_results = self._leader_filter_request.run_without_yielding()
        if not filter_results:
            return
        self._leader_sim_info = filter_results[0].sim_info
        self._filter_results.append(filter_results[0])
        self._blacklist_sim_ids.add(self._leader_sim_info.sim_id)

    def _create_leader_filter_request(self):
        if self._gsi_logging_data is not None:
            request_type = '_AggregateFilterRequest:_MatchingFilterRequest' if self._filter_sims_with_matching_filter_request else '_AggregateFilterRequest:_SimFilterRequest'
            sub_gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData(request_type, 'LeaderFilter:{}'.format(self._aggregate_filter.leader_filter), self._gsi_logging_data.yielding, self._gsi_logging_data.gsi_source_fn)
        else:
            sub_gsi_logging_data = None
        if self._filter_sims_with_matching_filter_request:
            self._leader_filter_request = _MatchingFilterRequest(sim_filter=self._aggregate_filter.leader_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, required_story_progression_arc=self._required_story_progression_arc, gsi_logging_data=sub_gsi_logging_data, tag=self._aggregate_filter.leader_filter.tag, additional_filter_terms=self._additional_filter_terms)
        else:
            self._leader_filter_request = _SimFilterRequest(sim_filter=self._aggregate_filter.leader_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, required_story_progression_arc=self._required_story_progression_arc, gsi_logging_data=sub_gsi_logging_data, tag=self._aggregate_filter.leader_filter.tag, additional_filter_terms=self._additional_filter_terms)

    def _create_non_leader_filter_requests(self):
        if self._filter_sims_with_matching_filter_request:
            for sim_filter in self._aggregate_filter.filters:
                sub_gsi_logging_data = None
                if self._gsi_logging_data is not None:
                    sub_gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData('_AggregateFilterRequest:_MatchingFilterRequest', 'NonLeaderFilter:{}'.format(sim_filter.filter), self._gsi_logging_data.yielding, self._gsi_logging_data.gsi_source_fn)
                self._non_leader_filter_requests.append(_MatchingFilterRequest(sim_filter=sim_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, required_story_progression_arc=self._required_story_progression_arc, requesting_sim_info=self._leader_sim_info, gsi_logging_data=sub_gsi_logging_data, tag=sim_filter.tag, optional=sim_filter.optional))
        else:
            for sim_filter in self._aggregate_filter.filters:
                sub_gsi_logging_data = None
                if self._gsi_logging_data is not None:
                    sub_gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData('_AggregateFilterRequest:_SimFilterRequest', 'NonLeaderFilter:{}'.format(sim_filter.filter), self._gsi_logging_data.yielding)
                self._non_leader_filter_requests.append(_SimFilterRequest(sim_filter=sim_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, required_story_progression_arc=self._required_story_progression_arc, requesting_sim_info=self._leader_sim_info, gsi_logging_data=sub_gsi_logging_data, tag=sim_filter.tag, optional=sim_filter.optional))

    def _run_sim_filter(self, filter_to_run):
        filter_results = filter_to_run.run_without_yielding()
        if filter_results:
            for result in filter_results:
                self._filter_results.append(result)
                self._blacklist_sim_ids.add(result.sim_info.sim_id)
        return bool(filter_results)

class SimFilterService(Service):

    def __init__(self):
        self._filter_requests = []
        self._global_blacklist = {}

    def update(self):
        try:
            if self._filter_requests:
                current_request = self._filter_requests[0]
                current_request.run()
                if current_request.is_complete:
                    del self._filter_requests[0]
        except Exception:
            logger.exception('Exception while updating the sim filter service..')

    @property
    def is_processing_request(self):
        if not self._filter_requests:
            return False
        else:
            current_request = self._filter_requests[0]
            if current_request is not None:
                return not current_request.is_complete
        return False

    def add_sim_id_to_global_blacklist(self, sim_id, reason):
        if sim_id not in self._global_blacklist:
            self._global_blacklist[sim_id] = []
        self._global_blacklist[sim_id].append(reason)

    def remove_sim_id_from_global_blacklist(self, sim_id, reason):
        reasons = self._global_blacklist.get(sim_id)
        if reasons is None:
            logger.error('Trying to remove sim id {} to global blacklist without adding it first.', sim_id, owner='jjacobson')
            return
        if reason not in reasons:
            logger.error('Trying to remove reason {} from global blacklist with sim id {} without adding it first.', reason, sim_id, owner='jjacobson')
            return
        self._global_blacklist[sim_id].remove(reason)
        if not self._global_blacklist[sim_id]:
            del self._global_blacklist[sim_id]

    def get_dialog_blacklist(self) -> 'Set[int]':
        return set([sim_id for (sim_id, reasons) in self._global_blacklist.items() if any(reason in reasons for reason in SIM_FILTER_DIALOG_BLACKLIST_REASONS)])

    def get_global_blacklist(self):
        return set(self._global_blacklist.keys())

    def get_global_blacklist_reason(self, sim_id):
        return self._global_blacklist.get(sim_id, [])

    def submit_matching_filter(self, number_of_sims_to_find:'int'=1, sim_filter:'Union[TunableSimFilter, TunableAggregateFilter]'=None, callback:'Callable[List[FilterResult], object]'=None, callback_event_data:'object'=None, sim_constraints:'List[int]'=None, requesting_sim_info:'SimInfo'=None, blacklist_sim_ids:'set[int]'=EMPTY_SET, required_story_progression_arc:'BaseStoryArc'=None, continue_if_constraints_fail:'bool'=False, conform_if_constraints_fail:'bool'=False, allow_yielding:'bool'=True, start_time:'DateAndTime'=None, end_time:'DateAndTime'=None, household_id:'int'=None, zone_id:'int'=None, club:'Club'=None, allow_instanced_sims:'bool'=False, display_dialog_only:'bool'=False, additional_filter_terms:'Tuple[BaseFilterTerm]'=(), gsi_source_fn:'Callable[None, str]'=None) -> 'Optional[FilterResult]':
        request = None
        if sim_filter is not None and sim_filter.is_aggregate_filter():
            request = _AggregateFilterRequest(aggregate_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, blacklist_sim_ids=blacklist_sim_ids, required_story_progression_arc=required_story_progression_arc, filter_sims_with_matching_filter_request=True, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        else:
            request = _MatchingFilterRequest(number_of_sims_to_find=number_of_sims_to_find, continue_if_constraints_fail=continue_if_constraints_fail, conform_if_constraints_fail=conform_if_constraints_fail, sim_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, requesting_sim_info=requesting_sim_info, sim_constraints=sim_constraints, blacklist_sim_ids=blacklist_sim_ids, required_story_progression_arc=required_story_progression_arc, start_time=start_time, end_time=end_time, household_id=household_id, zone_id=zone_id, club=club, allow_instanced_sims=allow_instanced_sims, display_dialog_only=display_dialog_only, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        if allow_yielding:
            self._add_filter_request(request)
        else:
            return request.run_without_yielding()

    def submit_filter(self, sim_filter, callback, callback_event_data=None, sim_constraints=None, requesting_sim_info=None, blacklist_sim_ids=EMPTY_SET, required_story_progression_arc=None, allow_yielding=True, start_time=None, end_time=None, household_id=None, club=None, additional_filter_terms=(), gsi_source_fn=None, include_rabbithole_sims=False, include_missing_pets=False):
        request = None
        if sim_filter is not None and sim_filter.is_aggregate_filter():
            request = _AggregateFilterRequest(aggregate_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, blacklist_sim_ids=blacklist_sim_ids, required_story_progression_arc=required_story_progression_arc, filter_sims_with_matching_filter_request=False, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        else:
            request = _SimFilterRequest(sim_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, requesting_sim_info=requesting_sim_info, sim_constraints=sim_constraints, blacklist_sim_ids=blacklist_sim_ids, required_story_progression_arc=required_story_progression_arc, start_time=start_time, end_time=end_time, household_id=household_id, club=club, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn, include_rabbithole_sims=include_rabbithole_sims, include_missing_pets=include_missing_pets)
        if allow_yielding:
            self._add_filter_request(request)
        else:
            return request.run_without_yielding()

    def _add_filter_request(self, filter_request):
        self._filter_requests.append(filter_request)

    def does_sim_match_filter(self, sim_id, sim_filter=None, requesting_sim_info=None, start_time=None, end_time=None, household_id=None, additional_filter_terms=(), gsi_source_fn=None, include_rabbithole_sims=False, include_missing_pets=False):
        result = self.submit_filter(sim_filter, None, allow_yielding=False, sim_constraints=[sim_id], requesting_sim_info=requesting_sim_info, start_time=start_time, end_time=end_time, household_id=household_id, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn, include_rabbithole_sims=include_rabbithole_sims, include_missing_pets=include_missing_pets)
        if result:
            return True
        return False

    def submit_household_filter(self, sim_filter:'Union[TunableSimFilter, TunableAggregateFilter]', callback:'Callable[[List[Tuple[Household, float]], object], None]', callback_event_data:'object'=None, blacklist_filter:'TunableSimFilter'=None, household_constraints:'List[int]'=None, requesting_sim_info:'SimInfo'=None, blacklist_household_ids:'set[int]'=EMPTY_SET, required_story_progression_arc:'BaseStoryArc'=None, allow_yielding:'bool'=True, start_time:'DateAndTime'=None, end_time:'DateAndTime'=None, household_id:'int'=None, club:'Club'=None, additional_filter_terms:'Tuple[BaseFilterTerm]'=(), gsi_source_fn:'Callable[None, str]'=None, include_rabbithole_sims:'bool'=False, include_missing_pets:'bool'=False) -> 'Optional[List[Tuple[Household, int]]]':

        def helpercallback(filter_results:'List[FilterResult]', _:'object') -> 'Optional[List[Tuple[Household, int]]]':
            return_list = []
            if not filter_results:
                if allow_yielding:
                    callback(return_list, callback_event_data)
                    return
                return return_list
            result_map = {}
            for result in filter_results:
                existing_score = result_map.get(result.sim_info.household, 0)
                if result.score > existing_score:
                    result_map[result.sim_info.household] = result.score

            def blacklist_helper(blacklist_helper_results:'List[FilterResult]', blacklist_helper_household:'Household') -> 'None':
                blacklist_max_score = 0
                for blacklist_helper_result in blacklist_helper_results:
                    if blacklist_helper_result.score == 1:
                        blacklist_max_score = 1
                        break
                    if blacklist_helper_result.score > blacklist_max_score:
                        blacklist_max_score = blacklist_helper_result.score
                if blacklist_max_score < 1:
                    return_list.append((blacklist_helper_household, result_map[blacklist_helper_household]*(1 - blacklist_max_score)))
                del result_map[blacklist_helper_household]
                if not result_map:
                    callback(return_list, callback_event_data)

            if blacklist_filter:
                if blacklist_filter.is_aggregate_filter():
                    logger.error('Blacklist filter for submit household filter does not support aggregate filters')
                    return_list = [(result_household, score) for (result_household, score) in result_map.items() if score > 0]
                    if allow_yielding:
                        callback(return_list, callback_event_data)
                        return
                    else:
                        for (blacklist_household, score) in result_map.items():
                            blacklist_sim_constraints = list(sim_info.sim_id for sim_info in blacklist_household)
                            blacklist_request = _SimFilterRequest(sim_filter=blacklist_filter, callback=blacklist_helper, callback_event_data=blacklist_household, requesting_sim_info=requesting_sim_info, sim_constraints=blacklist_sim_constraints, required_story_progression_arc=required_story_progression_arc, start_time=start_time, end_time=end_time, household_id=household_id, club=club, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn, include_rabbithole_sims=include_rabbithole_sims, include_missing_pets=include_missing_pets)
                            if allow_yielding:
                                self._add_filter_request(blacklist_request)
                            else:
                                blacklist_results = blacklist_request.run_without_yielding()
                                max_score = 0
                                for blacklist_result in blacklist_results:
                                    if blacklist_result.score == 1:
                                        max_score = 1
                                        break
                                    if blacklist_result.score > max_score:
                                        max_score = blacklist_result.score
                                if max_score < 1:
                                    return_list.append((blacklist_household, score*(1 - max_score)))
                else:
                    for (blacklist_household, score) in result_map.items():
                        blacklist_sim_constraints = list(sim_info.sim_id for sim_info in blacklist_household)
                        blacklist_request = _SimFilterRequest(sim_filter=blacklist_filter, callback=blacklist_helper, callback_event_data=blacklist_household, requesting_sim_info=requesting_sim_info, sim_constraints=blacklist_sim_constraints, required_story_progression_arc=required_story_progression_arc, start_time=start_time, end_time=end_time, household_id=household_id, club=club, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn, include_rabbithole_sims=include_rabbithole_sims, include_missing_pets=include_missing_pets)
                        if allow_yielding:
                            self._add_filter_request(blacklist_request)
                        else:
                            blacklist_results = blacklist_request.run_without_yielding()
                            max_score = 0
                            for blacklist_result in blacklist_results:
                                if blacklist_result.score == 1:
                                    max_score = 1
                                    break
                                if blacklist_result.score > max_score:
                                    max_score = blacklist_result.score
                            if max_score < 1:
                                return_list.append((blacklist_household, score*(1 - max_score)))
            else:
                return_list = [(result_household, score) for (result_household, score) in result_map.items() if score > 0]
                if allow_yielding:
                    callback(return_list, callback_event_data)
                    return
            return return_list

        sim_constraints = None
        household_manager = services.household_manager()
        if household_constraints is not None:
            sim_constraints = []
            for household_id in household_constraints:
                household = household_manager.get(household_id)
                if household:
                    sim_constraints.extend(household_sim_info.id for household_sim_info in household.sim_infos)
        blacklist_sim_ids = set()
        for household_id in blacklist_household_ids:
            household = household_manager.get(household_id)
            if household:
                blacklist_sim_ids.update(household.sim_infos)
        if sim_filter is not None and sim_filter.is_aggregate_filter():
            request = _AggregateFilterRequest(aggregate_filter=sim_filter, callback=helpercallback, callback_event_data=callback_event_data, blacklist_sim_ids=blacklist_sim_ids, required_story_progression_arc=required_story_progression_arc, filter_sims_with_matching_filter_request=False, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        else:
            request = _SimFilterRequest(sim_filter=sim_filter, callback=helpercallback, callback_event_data=callback_event_data, requesting_sim_info=requesting_sim_info, sim_constraints=sim_constraints, blacklist_sim_ids=blacklist_sim_ids, required_story_progression_arc=required_story_progression_arc, start_time=start_time, end_time=end_time, household_id=household_id, club=club, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn, include_rabbithole_sims=include_rabbithole_sims, include_missing_pets=include_missing_pets)
        if allow_yielding:
            self._add_filter_request(request)
        else:
            return helpercallback(request.run_without_yielding(), callback_event_data)
