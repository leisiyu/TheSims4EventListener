from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims4.tuning.instance_manager import InstanceManagerimport sims4.tuning.instance_manager_types
def get_definition_manager_type() -> 'InstanceManager':
    from objects.definition_manager import DefinitionManager
    return DefinitionManager

def get_module_tuning_manager_type() -> 'InstanceManager':
    from sims4.tuning.module_tuning import ModuleTuningManager
    return ModuleTuningManager

def get_aspiration_instance_manager_type() -> 'InstanceManager':
    from aspirations.aspiration_instance_manager import AspirationInstanceManager
    return AspirationInstanceManager

def get_interaction_instance_manager_type() -> 'InstanceManager':
    from interactions.interaction_instance_manager import InteractionInstanceManager
    return InteractionInstanceManager

def get_statistics_instance_manager_type() -> 'InstanceManager':
    from statistics.statistic_instance_manager import StatisticInstanceManager
    return StatisticInstanceManager

def get_instanced_class_manager_type() -> 'InstanceManager':
    from sims4.tuning.instanced_class_manager import InstancedClassManager
    return InstancedClassManager
MANAGER_TYPES = {sims4.tuning.instance_manager_types.INSTANCED_CLASS_MANAGER: get_instanced_class_manager_type(), sims4.tuning.instance_manager_types.STATISTIC_INSTANCE_MANAGER: get_statistics_instance_manager_type(), sims4.tuning.instance_manager_types.INTERACTION_INSTANCE_MANAGER: get_interaction_instance_manager_type(), sims4.tuning.instance_manager_types.ASPIRATION_INSTANCE_MANAGER: get_aspiration_instance_manager_type(), sims4.tuning.instance_manager_types.MODULE_TUNING_MANAGER: get_module_tuning_manager_type(), sims4.tuning.instance_manager_types.DEFINITION_MANAGER: get_definition_manager_type()}