from __future__ import annotationsimport servicesimport sims4from event_testing.resolver import SingleSimResolverfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableReference, TunableMapping, TunableList, HasTunableSingletonFactory, AutoFactoryInitfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
class BaseExperiment(HasTunableSingletonFactory, AutoFactoryInit):

    def on_group_id_set(self, group_id:'int') -> 'None':
        return NotImplementedError

    def on_no_group_id_set(self) -> 'None':
        pass

class SimExperiment(BaseExperiment):
    FACTORY_TUNABLES = {'loot_mapping': TunableMapping(description='\n            Mapping of experiments and player segmentation.\n            ', key_type=int, value_type=TunableList(description='\n                The loots that will be rewarded for the experiment.\n                ', tunable=TunableReference(description='\n                    A loot that will be rewarded.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), tuple_name='TunableSegmentationDataMap')}

    def on_group_id_set(self, group_id:'int') -> 'None':
        if group_id not in self.loot_mapping:
            return
        loots_to_apply = self.loot_mapping[group_id]
        household = services.active_household()
        for sim_info in household.sim_infos:
            resolver = SingleSimResolver(sim_info)
            for loot in loots_to_apply:
                loot.apply_to_resolver(resolver)

class PivotalMomentsExperiment(BaseExperiment):
    FACTORY_TUNABLES = {'pivotal_moment_mapping': TunableMapping(description='\n            Mapping of experiments and player segmentation.\n            Key is the group id.\n            Pivotal Moments that must be available to all players must be set in tutorial service instead.\n            ', key_type=int, value_type=TunableList(description='\n                The pivotal moments that will be available for the given group.\n                ', tunable=TunableReference(description='\n                    A pivotal moment available to player.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='PivotalMoment', pack_safe=True)), tuple_name='TunableSegmentationDataMap'), 'control_group_pivotal_moments': TunableList(description='\n            The pivotal moments that will be available for players that are not assigned to any group\n            ', tunable=TunableReference(description='\n                A pivotal moment available to player.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='PivotalMoment', pack_safe=True))}

    def on_group_id_set(self, group_id:'int') -> 'None':
        if group_id not in self.pivotal_moment_mapping:
            return
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None and self.pivotal_moment_mapping[group_id]:
            tutorial_service.set_dynamic_pivotal_moments(self.pivotal_moment_mapping[group_id])

    def on_no_group_id_set(self) -> 'None':
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None:
            tutorial_service.set_dynamic_pivotal_moments(self.control_group_pivotal_moments)
