import servicesfrom event_testing.resolver import DoubleSimResolverfrom relationships.attraction_tuning import AttractionTuningfrom sims4.commands import Command, output, CommandType
@Command('relationship.attraction.refresh', command_type=CommandType.DebugOnly)
def _refresh_attraction(source_sim_id:int, target_sim_id:int, _connection=None):
    attraction_service = services.get_attraction_service()
    if attraction_service is None:
        output('Could not find attraction service.', _connection)
        return False
    if not attraction_service._attraction_refresh_enabled:
        output('Refresh will not do anything when refresh is not enabled.\nYou need to enable refresh first, or manually set the relationship\ntrack score(s) for the sims you are interested in.', _connection)
        return False
    attraction_service.refresh_attraction(source_sim_id, target_sim_id)

@Command('relationship.attraction.set_refresh_enabled', command_type=CommandType.DebugOnly)
def _toggle_attraction_refresh(enabled:bool, _connection=None):
    attraction_service = services.get_attraction_service()
    if attraction_service is None:
        output('Could not find attraction service.', _connection)
        return False
    attraction_service._set_attraction_refresh_enabled(enabled)

@Command('relationship.attraction.show_calculation', command_type=CommandType.DebugOnly)
def _show_attraction_calculation(source_sim_id:int, target_sim_id:int, _connection=None):
    attraction_service = services.get_attraction_service()
    if attraction_service is None:
        output('Could not find attraction service.', _connection)
        return False
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        output('Could not find sim info manager.', _connection)
        return False
    source_sim_info = sim_info_manager.get(source_sim_id)
    target_sim_info = sim_info_manager.get(target_sim_id)
    if source_sim_info is None:
        output(f'Unable to get actor sim info for id {source_sim_id} when updating attraction.', _connection)
        return
    if target_sim_info is None:
        output(f'Unable to get target sim info for id {target_sim_id} when updating attraction.', _connection)
        return
    resolver = DoubleSimResolver(source_sim_info, target_sim_info)
    attraction_value = AttractionTuning.BASE_ATTRACTION_VALUE
    output(f'Initial attraction total: {attraction_value}', _connection)
    actor_traits = set(filter(lambda trait: trait.is_attraction_trait, source_sim_info.trait_tracker))
    for trait in actor_traits:
        trait_total = trait.attraction_modifier.base_value
        output(f'Evaluating trait '{trait}'', _connection)
        passed_modifiers = []
        for (mod_index, mod) in enumerate(trait.attraction_modifier.modifiers):
            if mod.tests.run_tests(resolver):
                passed_modifiers.append((mod_index, mod))
        if trait_total == 0 and len(passed_modifiers) <= 0:
            pass
        else:
            output(f'	Initial modifier value: {trait_total}', _connection)
            output(f'	{len(passed_modifiers)} modifiers applied', _connection)
            for (index, mod) in passed_modifiers:
                output(f'		Modifier #{mod_index} passed tests: Adding {mod.modifier}', _connection)
                trait_total += mod.modifier
            output(f'	Final modifier: {trait_total}', _connection)
            attraction_value += trait_total
            output(f'	New attraction total: {attraction_value}', _connection)
    output(f'Total attraction value: {attraction_value}', _connection)
