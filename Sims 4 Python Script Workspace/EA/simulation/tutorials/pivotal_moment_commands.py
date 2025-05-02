from protocolbuffers import DistributorOps_pb2import servicesimport sims4.commandsfrom google.protobuf import text_formatimport protocolbuffers.GameplaySaveData_pb2 as gameplay_save_datafrom protocolbuffers.Consts_pb2 import MSG_GAMEPLAY_OPTIONS
@sims4.commands.Command('pivotal_moments.completed_ids', command_type=sims4.commands.CommandType.Live)
def completed_ids(*completed_ids, _connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is not None:
        tutorial_service.process_completed_pivotal_moments(completed_ids)

@sims4.commands.Command('pivotal_moments.reset', command_type=sims4.commands.CommandType.Live)
def reset_pivotal_moments(_connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is not None:
        tutorial_service.reset_pivotal_moments()

@sims4.commands.Command('pivotal_moments.reset_with_rewards', command_type=sims4.commands.CommandType.Live)
def reset_pivotal_moments_and_rewards(_connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is not None:
        tutorial_service.reset_pivotal_moments(should_reset_rewards=True)

@sims4.commands.Command('pivotal_moments.toggle_enable', command_type=sims4.commands.CommandType.Live)
def toggle_pivotal_moments(enabled:bool, send_save_to_client:bool=False, _connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is not None:
        tutorial_service.toggle_pivotal_moments(enabled)
    if send_save_to_client:
        options = gameplay_save_data.GameplayOptions()
        client = services.client_manager().get(_connection)
        tutorial_service.save_options(options)
        client.send_message(MSG_GAMEPLAY_OPTIONS, options)

@sims4.commands.Command('pivotal_moments.disable', command_type=sims4.commands.CommandType.Live)
def disable_pivotal_moments(disabled:bool, _connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if disabled and tutorial_service is not None:
        enabled = not disabled
        tutorial_service.toggle_pivotal_moments(enabled, killswitch=True)

@sims4.commands.Command('pivotal_moments.process_stored_data', command_type=sims4.commands.CommandType.Live)
def process_pivotal_moment_data(pivotal_moment_data:str, _connection:int=None) -> bool:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is None:
        sims4.commands.output('Tutorial Service not available', _connection)
        return False
    pivotal_moment_proto = DistributorOps_pb2.PivotalMomentsList()
    text_format.Merge(pivotal_moment_data, pivotal_moment_proto)
    tutorial_service.process_pivotal_moment_data(pivotal_moment_proto)
    return True

@sims4.commands.Command('pivotal_moments.switch_activation_triggers')
def switch_activation_triggers(pivotal_moment_id:int, activation_trigger_id:int, _connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is None:
        sims4.commands.output('Tutorial Service not available', _connection)
        return False
    (result, reason) = tutorial_service.update_activation_trigger(pivotal_moment_id, activation_trigger_id)
    if not result:
        sims4.commands.output(reason, _connection)
    sims4.commands.output('Pivotal Moment trigger updated.', _connection)
    return True
