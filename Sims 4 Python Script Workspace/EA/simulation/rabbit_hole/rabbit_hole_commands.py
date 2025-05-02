import servicesimport sims4.commandsimport sims4.resourcesfrom rabbit_hole.multi_sim_rabbit_hole import MultiSimRabbitHoleBasefrom server_commands.argument_helpers import TunableInstanceParam, OptionalTargetParam, get_optional_targetoutput = sims4.commands.output
@sims4.commands.Command('rabbit_hole.complete_current_rabbit_hole')
def complete_current_rabbit_hole(target_sim:OptionalTargetParam=None, _connection=None) -> bool:
    sim = get_optional_target(target_sim, _connection)
    if sim is None:
        output('No sim found when trying to complete rabbit hole.', _connection)
        return False
    sim_id = sim.sim_id
    rabbit_hole_service = services.get_rabbit_hole_service()
    rabbit_hole_id = rabbit_hole_service.get_head_rabbit_hole_id(sim_id)
    if rabbit_hole_id is None:
        output('Sim is not in a rabbit hole.', _connection)
        return True
    rabbit_hole_service.remove_sim_from_rabbit_hole(sim_id, rabbit_hole_id)
    return True

@sims4.commands.Command('rabbit_hole.send_sim_to_rabbit_hole')
def send_sim_to_rabbit_hole(rabbit_hole:TunableInstanceParam(sims4.resources.Types.RABBIT_HOLE), sim_id:OptionalTargetParam=None, _connection=None) -> bool:
    if rabbit_hole is None:
        output('Cannot put sim in undefined rabbit hole.', _connection)
        return False
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        output('No sim given when trying to put sim in rabbit hole.', _connection)
        return False
    services.get_rabbit_hole_service().put_sim_in_managed_rabbithole(sim, rabbit_hole)
    return True

@sims4.commands.Command('rabbit_hole.send_household_to_rabbit_hole')
def send_household_to_rabbit_hole(rabbit_hole:TunableInstanceParam(sims4.resources.Types.RABBIT_HOLE), _connection=None) -> bool:
    if rabbit_hole is None:
        output('Cannot put sims in undefined rabbit hole.', _connection)
        return False
    if not issubclass(rabbit_hole, MultiSimRabbitHoleBase):
        output('Cannot put multiple sims into a rabbit hole that is not Multi Sim.', _connection)
        return False
    household = services.active_household()
    if household is None:
        output('Could not find active household.', _connection)
        return False
    sim_infos = [sim_info for sim_info in household.sim_info_gen()]
    services.get_rabbit_hole_service().put_sims_in_shared_rabbithole(sim_infos, rabbit_hole)
    return True
