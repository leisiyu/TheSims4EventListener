from interactions import ParticipantTypefrom server_commands.argument_helpers import SimInfoParam, OptionalSimInfoParam, get_optional_target, TunableInstanceParamfrom sims4.resources import Typesfrom story_progression.story_progression_enums import StoryTypefrom story_progression.story_progression_service import StoryProgressionServiceimport servicesimport sims4.commandsfrom story_progression.story_progression_log import start_story_progression_log, stop_story_progression_log, clear_story_progression_log, dump_story_progression_log
@sims4.commands.Command('story_progression.set_time_multiplier')
def story_progression_set_time_multiplier(time_multiplier:float=1, _connection=None):
    story_progression_service = services.get_story_progression_service()
    if story_progression_service is None:
        return False
    story_progression_service.set_time_multiplier(time_multiplier)
    return True

@sims4.commands.Command('story_progression.process_index', command_type=sims4.commands.CommandType.Cheat)
def process_index(index:int=0, _connection=None):
    current_zone = services.current_zone()
    if current_zone is None:
        return False
    story_progression_service = current_zone.story_progression_service
    if story_progression_service is None:
        return False
    story_progression_service.process_action_index(index)

@sims4.commands.Command('story_progression.list_action_indexes')
def list_action_indexes(_connection=None):
    sims4.commands.output('Index: Action Type', _connection)
    for (index, action) in enumerate(StoryProgressionService.ACTIONS):
        sims4.commands.output('{}: {}'.format(index, action), _connection)

@sims4.commands.Command('story_progression.process_all')
def process_all_story_progression(times_to_process:int=1, _connection=None):
    current_zone = services.current_zone()
    if current_zone is None:
        return False
    story_progression_service = current_zone.story_progression_service
    if story_progression_service is None:
        return False
    while times_to_process > 0:
        story_progression_service.process_all_actions()
        times_to_process -= 1
    sims4.commands.output('All story progression processed.', _connection)

@sims4.commands.Command('story_progression.add_story_arc_to_sim')
def add_story_arc_to_sim(story_arc:TunableInstanceParam(Types.STORY_ARC), sim_info_a:OptionalSimInfoParam=None, sim_info_b:SimInfoParam=None, sim_info_c:SimInfoParam=None, _connection=None):
    sim_info = get_optional_target(sim_info_a, _connection, OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to add story arc: No Sim.', _connection)
        return False
    if story_arc.arc_type == StoryType.SIM_BASED:
        result = sim_info.story_progression_tracker.add_arc(story_arc)
    elif story_arc.arc_type == StoryType.MULTI_SIM_BASED:
        if sim_info_b is None:
            sims4.commands.output('Failed to add story arc: Missing Additional Sim for Multi-Sim Arc.', _connection)
            return False
        result = sim_info.story_progression_tracker.add_arc(story_arc)
        arc = sim_info.story_progression_tracker._current_arcs[-1]
        arc.store_participant(participant=ParticipantType.SavedStoryProgressionSim1, obj=sim_info_b.id)
        if sim_info_c is not None:
            arc.store_participant(participant=ParticipantType.SavedStoryProgressionSim2, obj=sim_info_c.id)
    elif story_arc.arc_type == StoryType.HOUSEHOLD_BASED:
        result = sim_info.household.story_progression_tracker.add_arc(story_arc)
    else:
        sims4.commands.output('Failed to add story arc due to unsupported type: {}'.format(story_arc.arc_type), _connection)
        return False
    if not result:
        sims4.commands.output('Failed to add story arc: {}'.format(result), _connection)
        return False
    sims4.commands.output('Added story arc', _connection)
    services.get_story_progression_service().cache_active_arcs_sim_id(sim_info.id)
    return True

@sims4.commands.Command('story_progression.update_story_arcs_on_sim')
def update_story_arcs_on_sim(sim_id:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(sim_id, _connection, OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to progress story arcs: No Sim.', _connection)
        return False
    for _ in sim_info.story_progression_tracker.update_arcs_gen():
        pass
    sims4.commands.output('Updated story arcs on the Sim', _connection)
    return True

@sims4.commands.Command('story_progression.set_story_progression_effects_enabled', command_type=sims4.commands.CommandType.Live)
def set_story_progression_effects_enabled(enabled:bool=True, _connection=None):
    services.get_story_progression_service().set_story_progression_enabled_in_options(enabled)

@sims4.commands.Command('story_progression.update_story_progression_service')
def update_story_progression_service(seed_all_arcs:bool=False, _connection=None):
    story_progression_service = services.get_story_progression_service()
    for _ in story_progression_service.seed_new_story_arcs_gen(debug_seed_all_arcs=seed_all_arcs):
        pass
    sims4.commands.output('Seeded stories.', _connection)
    for _ in story_progression_service.update_story_progression_trackers_gen():
        pass
    sims4.commands.output('Updated stories.', _connection)
    return True

@sims4.commands.Command('story_progression.disable', command_type=sims4.commands.CommandType.Live)
def disable_story_progression(set_disabled:bool=False, _connection=None):
    if set_disabled:
        sims4.commands.output('Story Progression Disabled', _connection)
        services.get_story_progression_service().set_story_progression_enabled_via_killswitch(False)
    else:
        sims4.commands.output('Story Progression Enabled', _connection)
        services.get_story_progression_service().set_story_progression_enabled_via_killswitch(True)

@sims4.commands.Command('story_progression.story_progression_log.enable', command_type=sims4.commands.CommandType.Automation)
def enable_story_progression_logging(_connection=None):
    start_story_progression_log()
    output = sims4.commands.CheatOutput(_connection)
    output('Story Progression logging enabled. Dump the profile any time using story_progression.story_progression_log.dump')

@sims4.commands.Command('story_progression.story_progression_log.disable', command_type=sims4.commands.CommandType.Automation)
def disable_story_progression_logging(_connection=None):
    stop_story_progression_log()
    output = sims4.commands.CheatOutput(_connection)
    output('Story Progression logging disabled.')

@sims4.commands.Command('story_progression.story_progression_log.reset', command_type=sims4.commands.CommandType.Automation)
def reset_story_progression_logging(_connection=None):
    clear_story_progression_log()
    output = sims4.commands.CheatOutput(_connection)
    output('Autonomy profile metrics have been cleared.')

@sims4.commands.Command('story_progression.story_progression_log.dump', command_type=sims4.commands.CommandType.Automation)
def dump_story_progression_logging(_connection=None):
    dump_story_progression_log(connection=_connection)
