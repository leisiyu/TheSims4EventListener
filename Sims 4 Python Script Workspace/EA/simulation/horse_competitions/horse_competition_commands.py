import servicesimport sims4.commandsfrom server_commands.argument_helpers import RequiredTargetParam, OptionalTargetParam, get_optional_targetfrom sims4.commands import output
@sims4.commands.Command('horse_competition.show_ui', command_type=sims4.commands.CommandType.Live)
def show_horse_competition_ui(_connection=None):
    services.get_horse_competition_service().show_competition_selector_ui()

@sims4.commands.Command('horse_competition.pick_new_assignee', command_type=sims4.commands.CommandType.Live)
def pick_new_assignee(current_competition_id:int, current_sim:OptionalTargetParam, current_horse:OptionalTargetParam, for_horse:bool=False, _connection=None):
    sim = get_optional_target(current_sim, _connection)
    horse = get_optional_target(current_horse, _connection)
    services.get_horse_competition_service().pick_new_assignee(current_competition_id, sim, horse, for_horse)

@sims4.commands.Command('horse_competition.start_competition', command_type=sims4.commands.CommandType.Live)
def start_competition(competition_id:int, selected_sim:RequiredTargetParam, selected_horse:RequiredTargetParam, _connection=None):
    output('Running start command!', _connection)
    sim = selected_sim.get_target(manager=services.sim_info_manager())
    if sim is None:
        output('No sim given when trying to start a competition.', _connection)
        return False
    horse = selected_horse.get_target(manager=services.sim_info_manager())
    if horse is None:
        output('No horse given when trying to start a competition.', _connection)
        return False
    services.get_horse_competition_service().start_competition(competition_id, sim, horse)

@sims4.commands.Command('horse_competition.print_highest_placement_index')
def print_highest_placement_index(selected_horse:RequiredTargetParam, skip_not_participated=False, _connection=None):
    horse = selected_horse.get_target(manager=services.sim_info_manager())
    if horse is None:
        output('No horse given.', _connection)
        return False
    output(f'All placement indexes for horse {horse.full_name}:', _connection)
    hc_service = services.get_horse_competition_service()
    all_competitions = hc_service.get_all_competition_ids()
    for competition_id in all_competitions:
        competition = hc_service.try_get_competition_by_id(competition_id)
        highest_placement = hc_service.try_get_highest_placement(horse.sim_id, competition_id)
        if skip_not_participated and highest_placement is None:
            pass
        else:
            output(f'	{competition}({competition_id}): {highest_placement}', _connection)
    return True

@sims4.commands.Command('horse_competition.print_available_competitions')
def print_unlocked_competitions(selected_sim:RequiredTargetParam, selected_horse:RequiredTargetParam, _connection=None):
    sim = selected_sim.get_target(manager=services.sim_info_manager())
    if sim is None:
        output('No sim given when trying to start a competition.', _connection)
        return False
    horse = selected_horse.get_target(manager=services.sim_info_manager())
    if horse is None:
        output('No horse given when trying to start a competition.', _connection)
        return False
    output('Unlocked competitions (name, guid):', _connection)
    competitions = services.get_horse_competition_service()._get_unlocked_competitions(sim, horse)
    for competition in competitions:
        output(f'	{competition}, {competition.guid64}', _connection)
    return True

@sims4.commands.Command('horse_competition.print_placement_weights')
def print_placement_weights(competition_id:int, selected_sim:RequiredTargetParam, selected_horse:RequiredTargetParam, _connection=None):
    sim = selected_sim.get_target(manager=services.sim_info_manager())
    if sim is None:
        output('No sim given when trying to start a competition.', _connection)
        return False
    horse = selected_horse.get_target(manager=services.sim_info_manager())
    if horse is None:
        output('No horse given when trying to start a competition.', _connection)
        return False
    hcs = services.get_horse_competition_service()
    selected_competition = hcs.try_get_competition_by_id(competition_id)
    if selected_competition is None:
        output('Could not find competition.', _connection)
        return False
    output('Printing weights for placements in tuned order:', _connection)
    weighted_placements = hcs._get_weighted_placements(selected_competition, sim, horse)
    for (index, (weight, placement)) in enumerate(weighted_placements):
        output(f'	Placement {index} weight: {weight}', _connection)
