from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from filters.tunable import TunableAggregateFilter
    from sims4.tuning.tunable import TunableMapping, TunableSet
    from situations.situation_job import SituationJob
    from typing import *import itertoolsfrom situations.bouncer.bouncer_types import RequestSpawningOptionfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfoimport services
class AmbientSituationGuestListNoBouncerMixin:

    @staticmethod
    def create_guest_list(jobs:'List[SituationJob]', job_mapping:'TunableMapping', tags:'TunableSet', group_filter:'TunableAggregateFilter', gsi_name:'str') -> 'Optional[SituationGuestList]':
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_situation_blacklist = set()
        for job in jobs:
            auto_fill_situation_blacklist.update(situation_manager.get_auto_fill_blacklist(sim_job=job))
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_situation_blacklist))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=group_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=gsi_name)
        if not filter_results:
            return
        if len(filter_results) != group_filter.get_filter_count():
            return
        for result in filter_results:
            job = job_mapping.get(result.tag, None)
            if job is None:
                pass
            else:
                guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.DONT_CARE, job.sim_auto_invite_allow_priority))
        return guest_list
