from __future__ import annotationsimport servicesfrom interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from sims.sim_info import SimInfo
    from typing import *
class RefreshAttractionLootOp(BaseTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver') -> 'None':
        if subject is None:
            return
        if target is None:
            return
        attraction_service = services.get_attraction_service()
        if attraction_service is not None:
            attraction_service.refresh_attraction(subject.sim_id, target.sim_id)
