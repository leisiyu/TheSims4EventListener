import servicesimport sims4.commandsfrom experiment_service.experiment_service import ExperimentService, ExperimentNamelogger = sims4.log.Logger('Experiments')
@sims4.commands.Command('experiments.set_group_for_experiment', command_type=sims4.commands.CommandType.Live)
def set_groups_for_experiments(experiment_name:str, group_id:int, _connection=None) -> None:
    experiment_service = services.get_experiment_service()
    experiment_service.set_group_for_experiment(experiment_name, group_id)

@sims4.commands.Command('experiments.set_no_group_for_experiment', command_type=sims4.commands.CommandType.Live)
def set_no_group_for_experiments(experiment_name:str, _connection=None) -> None:
    experiment_service = services.get_experiment_service()
    experiment_service.set_no_group_for_experiment(experiment_name)

@sims4.commands.Command('experiments.get_group_for_experiment', command_type=sims4.commands.CommandType.DebugOnly)
def get_group_for_experiment(experiment_name:ExperimentName, _connection=None) -> None:
    experiment_service = services.get_experiment_service()
    group_id = experiment_service.get_group_for_experiment(experiment_name)
    if group_id == ExperimentService.EXPERIMENT_GROUP_INVALID:
        sims4.commands.output('{} is not a valid ExperimentName'.format(experiment_name), _connection)
    elif group_id == ExperimentService.EXPERIMENT_GROUP_NONE:
        sims4.commands.output('No group set for experiment {}'.format(experiment_name), _connection)
    else:
        sims4.commands.output('Group for experiment {} is {}'.format(experiment_name, group_id), _connection)
