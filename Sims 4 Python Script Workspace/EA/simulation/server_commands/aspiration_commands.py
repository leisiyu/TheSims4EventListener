from aspirations.aspiration_types import AspriationTypefrom event_testing.resolver import DataResolverfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParam, get_tunable_instanceimport servicesimport sims4.commandslogger = sims4.log.Logger('AspirationCommand')
@sims4.commands.Command('ui.aspirations.set_primary', command_type=sims4.commands.CommandType.Live)
def set_primary_track(aspiration_track:TunableInstanceParam(sims4.resources.Types.ASPIRATION_TRACK), sim_id:int=0, _connection=None):
    sim_info = services.sim_info_manager().get(sim_id)
    if sim_info is None:
        logger.error('Sim Info not found')
        return False
    sim_info.primary_aspiration = aspiration_track

@sims4.commands.Command('aspirations.reset_data')
def reset_aspirations(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sim.sim_info.aspiration_tracker.reset_data()
        sims4.commands.output('Aspirations reset complete', _connection)
    else:
        sims4.commands.output('Sim not found, please check: |aspirations.reset_data <sim id from desired account>', _connection)

@sims4.commands.Command('aspirations.list_all_aspirations')
def list_all_aspirations(_connection=None):
    aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
    for aspiration_id in aspiration_manager.types:
        aspiration = aspiration_manager.get(aspiration_id)
        sims4.commands.output('{}: {}'.format(aspiration, int(aspiration.guid64)), _connection)

@sims4.commands.Command('aspirations.complete_aspiration', command_type=sims4.commands.CommandType.Cheat)
def complete_aspiration(aspiration_type:TunableInstanceParam(sims4.resources.Types.ASPIRATION), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        objectives_just_completed = []
        for objective_type in aspiration_type.objectives:
            if not sim.sim_info.aspiration_tracker.objective_completed(objective_type):
                sim.sim_info.aspiration_tracker.complete_objective(objective_type, aspiration_type)
                objectives_just_completed.append(objective_type)
        sim.sim_info.aspiration_tracker.complete_milestone(aspiration_type, sim.sim_info)
        sims4.commands.output('Complete {} on {}'.format(aspiration_type, sim), _connection)
        sim.sim_info.aspiration_tracker.send_if_dirty()
        sim.sim_info.aspiration_tracker.update_objectives_after_ui_change(objectives_just_completed)

@sims4.commands.Command('aspirations.complete_current_milestone', command_type=sims4.commands.CommandType.Cheat)
def complete_current_milestone(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        track_id = sim.sim_info.primary_aspiration.guid64 if sim.sim_info.primary_aspiration is not None else 0
        if track_id == 0:
            sims4.commands.output("{} doesn't have a primary aspiration.".format(sim), _connection)
            return
        track = get_tunable_instance(sims4.resources.Types.ASPIRATION_TRACK, track_id)
        for (_, track_aspriation) in track.get_aspirations():
            if not sim.sim_info.aspiration_tracker.milestone_completed(track_aspriation):
                objectives_just_completed = []
                for objective_type in track_aspriation.objectives:
                    if not sim.sim_info.aspiration_tracker.objective_completed(objective_type):
                        sim.sim_info.aspiration_tracker.complete_objective(objective_type, track_aspriation)
                        objectives_just_completed.append(objective_type)
                sim.sim_info.aspiration_tracker.complete_milestone(track_aspriation, sim.sim_info)
                sims4.commands.output('Complete {} on {}'.format(track_aspriation, sim), _connection)
                sim.sim_info.aspiration_tracker.send_if_dirty()
                sim.sim_info.aspiration_tracker.update_objectives_after_ui_change(objectives_just_completed)
                return
        sims4.commands.output('{} has completed all milestones in {}.'.format(sim, track), _connection)

@sims4.commands.Command('aspirations.complete_objective', command_type=sims4.commands.CommandType.Cheat)
def complete_objective(objective:TunableInstanceParam(sims4.resources.Types.OBJECTIVE), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and objective is not None:
        aspiration_tracker = sim.sim_info.aspiration_tracker
        for aspiration in services.get_instance_manager(sims4.resources.Types.ASPIRATION).types.values():
            if aspiration.aspiration_type == AspriationType.FULL_ASPIRATION and aspiration.do_not_register_events_on_load and not aspiration_tracker.aspiration_in_sequence(aspiration):
                pass
            else:
                for asp_objective in aspiration_tracker.get_objectives(aspiration):
                    if asp_objective == objective:
                        aspiration_tracker.handle_event(aspiration, None, DataResolver(sim.sim_info), debug_objectives_to_force_complete=[objective])
        sims4.commands.output('Complete {} on {}'.format(objective, sim), _connection)

@sims4.commands.Command('aspirations.activate_timed_aspiration')
def activate_timed_aspiration(aspiration_type:TunableInstanceParam(sims4.resources.Types.ASPIRATION), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        return
    sim.sim_info.aspiration_tracker.activate_timed_aspiration(aspiration_type)

@sims4.commands.Command('aspirations.print_unfinished_business_objective_info')
def print_unfinished_business_objective_info(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        return
    aspiration_tracker = sim.sim_info.aspiration_tracker
    unfinished_business_aspiration = None
    for aspiration in sim.sim_info.unfinished_business_aspiration.aspirations.values():
        unfinished_business_aspiration = aspiration
    objectives = [aspiration_tracker.get_additional_objectives(unfinished_business_aspiration)]
    sims4.commands.output('Sim {} Unfinished Aspiration Objectives'.format(sim), _connection)
    for objective in objectives:
        sims4.commands.output('--Objective {}'.format(objective), _connection)

@sims4.commands.Command('aspirations.get_active_aspiration', command_type=sims4.commands.CommandType.Automation)
def get_active_aspiration(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sims4.commands.automation_output('GetActiveAspiration; Status:Begin', _connection)
        aspiration_tracker = sim.sim_info.aspiration_tracker
        if aspiration_tracker.active_track is None:
            sims4.commands.output('GetActiveAspiration; Target does not have an active aspiration.', _connection)
            return
        for aspiration in aspiration_tracker.active_track.aspirations.values():
            for objective in aspiration.objectives:
                message = 'Aspiration:{}, Objective:{}, Progress:{}, Goal:{}, Complete:{}'.format(aspiration.__name__, objective.__name__, aspiration_tracker.get_last_updated_value_for_objective(objective), objective.goal_value(), aspiration_tracker.objective_completed(objective))
                sims4.commands.output(message, _connection)
                sims4.commands.automation_output('GetActiveAspiration; Status:Data, {}'.format(message), _connection)
        sims4.commands.automation_output('GetActiveAspiration; Status:End', _connection)
    else:
        sims4.commands.output('GetActiveAspiration; No target for aspirations.get_active_aspiration.', _connection)
