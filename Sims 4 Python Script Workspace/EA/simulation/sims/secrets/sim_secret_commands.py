import servicesimport sims4from server_commands.argument_helpers import TunableInstanceParam, OptionalTargetParam, get_optional_targetfrom sims.secrets.sim_secrets_service import SimSecretsServicefrom sims.secrets.tunable_sim_secret import SimSecretfrom sims.sim_info import SimInfo
def _get_sim_and_knowledge(opt_sim:OptionalTargetParam, target_sim_id, _connection):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        return (sim, sim.relationship_tracker.get_knowledge(target_sim_id, initialize=True))

@sims4.commands.Command('sim_secrets.list', command_type=sims4.commands.CommandType.DebugOnly)
def list_secrets(target_sim_id:int, opt_sim:OptionalTargetParam=None, _connection=None):
    (sim, knowledge) = _get_sim_and_knowledge(opt_sim, target_sim_id, _connection)
    output = sims4.commands.Output(_connection)
    confronted_secrets_string = ''
    for secret in knowledge.get_confronted_secrets():
        confronted_secrets_string += '    {}:{}\n'.format(secret, secret.blackmailed)
    output('Sim Secrets:\n  - Unconfronted Secret:\n    {}\n  - Confronted secrets:\n{}'.format(knowledge.get_unconfronted_secret() or '', confronted_secrets_string))

@sims4.commands.Command('sim_secrets.add', command_type=sims4.commands.CommandType.DebugOnly)
def add_secret(simsecret:TunableInstanceParam(sims4.resources.Types.SNIPPET), target_sim_id:int, opt_sim:OptionalTargetParam=None, _connection=None):
    (sim, knowledge) = _get_sim_and_knowledge(opt_sim, target_sim_id, _connection)
    secret_instance = simsecret()
    knowledge.set_unconfronted_secret(secret_instance)

@sims4.commands.Command('sim_secrets.confront', command_type=sims4.commands.CommandType.DebugOnly)
def confront_secret(target_sim_id:int, opt_sim:OptionalTargetParam=None, blackmailed:bool=True, _connection=None):
    (sim, knowledge) = _get_sim_and_knowledge(opt_sim, target_sim_id, _connection)
    knowledge.make_secret_known(blackmailed, notify_client=True)

@sims4.commands.Command('sim_secrets.determine_target', command_type=sims4.commands.CommandType.DebugOnly)
def determine_target(opt_sim:OptionalTargetParam=None, _connection=None):
    sim_secrets_service = services.sim_secrets_service()
    if sim_secrets_service is None:
        return False
    source_sim = get_optional_target(opt_sim, _connection)
    target_household_id = services.get_persistence_service().get_household_id_from_zone_id(services.current_zone_id())
    target = sim_secrets_service.determine_snooping_target(source_sim, target_household_id)
    output = sims4.commands.Output(_connection)
    output('{} [{}]'.format(target.full_name, target.id))

@sims4.commands.Command('sim_secrets.generate', command_type=sims4.commands.CommandType.DebugOnly)
def generate_secret(target_sim_id:int, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    sim_secrets_service = services.sim_secrets_service()
    if sim_secrets_service is None:
        return False
    secret = sim_secrets_service.generate_secret_for_target_sim(sim, target_sim_id)
    output = sims4.commands.Output(_connection)
    output('{}'.format(secret))
