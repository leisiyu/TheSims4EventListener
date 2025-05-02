from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfofrom interactions.utils.loot_basic_op import BaseTargetedLootOperationimport servicesimport sims4logger = sims4.log.Logger('AddAdoptedSimToFamilyLoot', default_owner='micfisher')
class AddAdoptedSimToFamilyLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'description': "\n            This loot will add the specified Sim to the Parent's household.\n            "}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'None') -> 'None':
        adopted_sim_info = target
        parent_a = subject
        parent_b = services.sim_info_manager().get(parent_a.spouse_sim_id)
        pregnancy_tracker = parent_a.pregnancy_tracker
        if pregnancy_tracker is not None:
            pregnancy_tracker.initialize_sim_info(adopted_sim_info, parent_a, parent_b)
        else:
            logger.warn('Attempted to add a Sim to a family, but the parent Sim has no pregnancy tracker. Parent: {}', parent_a.full_name)
