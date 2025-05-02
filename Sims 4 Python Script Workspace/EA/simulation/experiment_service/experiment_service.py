from __future__ import annotationsimport distributor.opsimport sims4from distributor.system import Distributorfrom experiment_service.experiment_enums import ExperimentNamefrom experiment_service.experiment_types import SimExperiment, PivotalMomentsExperimentfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableVariant, TunableEnumEntry, TunableMappingfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from server.client import Client
    from typing import *logger = sims4.log.Logger('Experiments', default_owner='snunesdasilva')
class ExperimentService(Service):
    EXPERIMENT_GROUP_NONE = -1
    EXPERIMENT_GROUP_INVALID = -2
    EXPERIMENTS = TunableMapping(description='\n        Mapping of experiments and player segmentation.\n        ', key_type=TunableEnumEntry(description='\n            Experiment event key.\n            ', tunable_type=ExperimentName, default=ExperimentName.DEFAULT, invalid_enums=(ExperimentName.DEFAULT,)), value_type=TunableVariant(sim_experiment=SimExperiment.TunableFactory(), pivotal_moment_experiment=PivotalMomentsExperiment.TunableFactory()), tuple_name='TunableExperimentMap')

    def __init__(self):
        self._experiments_groups = {}

    def on_client_connect(self, client:'Client') -> 'None':
        experiments_op = distributor.ops.GetGroupsForExperiments()
        for experiment_name in ExperimentName:
            experiments_op.add_experiment(experiment_name.value_as_string())
        Distributor.instance().add_op_with_no_owner(experiments_op)

    def on_all_households_and_sim_infos_loaded(self, client:'Client') -> 'None':
        self.refresh_sims_experiments()

    def set_group_for_experiment(self, experiment_name_str:'str', group_id:'int') -> 'None':
        if experiment_name_str not in ExperimentName:
            logger.error('Tried to set group id {} for invalid experiment name {}', group_id, experiment_name_str)
            return
        experiment_name = ExperimentName[experiment_name_str]
        self._experiments_groups[experiment_name] = group_id
        if experiment_name not in ExperimentService.EXPERIMENTS:
            return
        ExperimentService.EXPERIMENTS[experiment_name].on_group_id_set(group_id)

    def set_no_group_for_experiment(self, experiment_name_str:'str') -> 'None':
        if experiment_name_str not in ExperimentName:
            logger.error('Tried to set control group for invalid experiment name {}', experiment_name_str)
            return
        experiment_name = ExperimentName[experiment_name_str]
        self._experiments_groups[experiment_name] = ExperimentService.EXPERIMENT_GROUP_NONE
        if experiment_name not in ExperimentService.EXPERIMENTS:
            return
        ExperimentService.EXPERIMENTS[experiment_name].on_no_group_id_set()

    def get_group_for_experiment(self, experiment_name:'ExperimentName') -> 'int':
        if experiment_name in self._experiments_groups:
            return self._experiments_groups[experiment_name]
        else:
            return ExperimentService.EXPERIMENT_GROUP_NONE

    def refresh_sims_experiments(self) -> 'None':
        for (experiment_name, experiment) in ExperimentService.EXPERIMENTS.items():
            if experiment_name in self._experiments_groups:
                if self._experiments_groups[experiment_name] != ExperimentService.EXPERIMENT_GROUP_NONE:
                    experiment.on_group_id_set(self._experiments_groups[experiment_name])
                else:
                    experiment.on_no_group_id_set()
