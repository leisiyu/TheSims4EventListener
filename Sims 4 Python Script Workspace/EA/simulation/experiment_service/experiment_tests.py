from __future__ import annotationsfrom typing import TYPE_CHECKINGfrom experiment_service.experiment_service import ExperimentService, ExperimentNamefrom event_testing.results import TestResultfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableEnumEntryimport event_testing.test_baseimport servicesif TYPE_CHECKING:
    from typing import *
class ExperimentGroupTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'experiment_name': TunableEnumEntry(description='\n            The name of the experiment we are checking.\n            ', tunable_type=ExperimentName, default=ExperimentName.DEFAULT, invalid_enums=(ExperimentName.DEFAULT,)), 'group': Tunable(description='\n            The segmentation group to check.\n            ', tunable_type=int, default=0)}

    def get_expected_args(self):
        return {}

    def __call__(self, *args, **kwargs):
        experiment_service = services.get_experiment_service()
        if experiment_service is None:
            return TestResult(False, 'There is no active Experiment service.', tooltip=self.tooltip)
        group_id = experiment_service.get_group_for_experiment(self.experiment_name)
        if group_id is ExperimentService.EXPERIMENT_GROUP_NONE:
            return TestResult(False, 'The experiment {} is not currently active for the player.', self.experiment_name)
        if group_id == self.group:
            return TestResult.TRUE
        else:
            return TestResult(False, 'The player has not been assigned to this group.')
