from _math import Vector3import timefrom autonomy.autonomy_modes import AutonomyMode, FullAutonomyfrom autonomy.autonomy_modifier import AutonomyModifierfrom autonomy.settings import AutonomyState, AutonomySettingsGroup, AutonomyRandomization, NPCAutonomyTypefrom objects.object_enums import ResetReasonfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParamimport alarmsimport autonomy.autonomy_utilimport date_and_timeimport objects.components.typesimport servicesimport sims.simimport sims4.commandsimport sims4.logimport sims4.resourcesimport singletonslogger = sims4.log.Logger('Autonomy')automation_logger = sims4.log.Logger('AutonomyAutomation')with sims4.reload.protected(globals()):
    g_distance_estimate_alarm_handle = None
@sims4.commands.Command('autonomy.show')
def show_autonomy_settings(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Couldn't find Sim.", _connection)
        return
    autonomy_state = _convert_state_to_string(sim.get_autonomy_state_setting())
    autonomy_randomization = _convert_randomization_to_string(sim.get_autonomy_randomization_setting())
    selected_sim_autonomy_enabled = services.autonomy_service()._selected_sim_autonomy_enabled
    sims4.commands.output('Autonomy State: {}\nAutonomyRandomization: {}\nSelected Sim Autonomy: {}'.format(autonomy_state, autonomy_randomization, selected_sim_autonomy_enabled), _connection)

@sims4.commands.Command('autonomy.sim')
def sim_autonomy_state(state, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    true_state = _parse_state(state, _connection=_connection)
    if true_state is None:
        return
    sim.autonomy_settings.set_setting(true_state, sim.get_autonomy_settings_group())

@sims4.commands.Command('autonomy.sim_randomization', command_type=sims4.commands.CommandType.Automation)
def sim_autonomy_randomization(randomization, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    true_randomization = _parse_randomization(randomization)
    sim.autonomy_settings.set_setting(true_randomization, sim.get_autonomy_settings_group())

@sims4.commands.Command('autonomy.household', command_type=sims4.commands.CommandType.Live)
def household_autonomy_state(state, opt_sim:OptionalTargetParam=None, settings_group:AutonomySettingsGroup=AutonomySettingsGroup.DEFAULT, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('Failed to find Sim', _connection)
        return
    household = sim.household
    if household is None:
        sims4.commands.output('No household for sim {}'.format(sim), _connection)
        return
    true_state = _parse_state(state, _connection=_connection)
    if true_state is None:
        return
    household.autonomy_settings.set_setting(true_state, settings_group)

@sims4.commands.Command('autonomy.household_randomization', command_type=sims4.commands.CommandType.Automation)
def household_autonomy_randomization(randonmization, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('Failed to find Sim', _connection)
        return
    household = sim.household
    if household is None:
        sims4.commands.output('No household for sim {}'.format(sim), _connection)
        return
    true_randomization = _parse_randomization(randonmization)
    household.autonomy_settings.set_setting(true_randomization, AutonomySettingsGroup.DEFAULT)

@sims4.commands.Command('autonomy.global', command_type=sims4.commands.CommandType.Automation)
def global_autonomy_state(state, settings_group:AutonomySettingsGroup=AutonomySettingsGroup.DEFAULT, _connection=None):
    autonomy_service = services.autonomy_service()
    true_state = _parse_state(state, _connection=_connection)
    if true_state is None:
        return
    autonomy_service.global_autonomy_settings.set_setting(true_state, settings_group)
    sims4.commands.output('Setting Global autonomy state to {} '.format(true_state), _connection)

@sims4.commands.Command('autonomy.global_randomization', command_type=sims4.commands.CommandType.Automation)
def global_autonomy_randomization(randomization, settings_group:AutonomySettingsGroup=AutonomySettingsGroup.DEFAULT, _connection=None):
    autonomy_service = services.autonomy_service()
    true_randomization = _parse_randomization(randomization)
    if true_randomization is not None:
        autonomy_service.global_autonomy_settings.set_setting(true_randomization, settings_group)

@sims4.commands.Command('autonomy.global_all', command_type=sims4.commands.CommandType.Automation)
def all_autonomy_state(state, _connection=None):
    autonomy_service = services.autonomy_service()
    true_state = _parse_state(state, _connection=_connection)
    if true_state is None:
        return
    for settings_group in AutonomySettingsGroup:
        autonomy_service.global_autonomy_settings.set_setting(true_state, settings_group)

@sims4.commands.Command('autonomy.set_autonomy_for_active_sim_option', command_type=sims4.commands.CommandType.Live)
def set_autonomy_for_active_sim_option(enabled:bool, _connection=None):
    services.autonomy_service().set_autonomy_for_active_sim(enabled)

@sims4.commands.Command('autonomy.ambient', 'walkby.toggle', command_type=sims4.commands.CommandType.Automation)
def set_ambient_autonomy(enabled:bool=None, _connection=None):
    tgt_client = services.client_manager().get(_connection)
    if enabled is None:
        enabled = not tgt_client.account.debug_ambient_npcs_enabled
    tgt_client.account.debug_ambient_npcs_enabled = enabled
    sims4.commands.output('Ambient NPCs ' + ('enabled' if enabled else 'disabled'), _connection)

def _parse_state(state, _connection=None):
    state_lower = state.lower()
    if state_lower == 'on' or (state_lower == 'true' or state_lower == 'full') or state_lower == '3':
        return AutonomyState.FULL
    if state_lower == 'medium':
        return AutonomyState.MEDIUM
    if state_lower == 'limitedonly' or (state_lower == 'la' or (state_lower == 'off' or state_lower == 'false')) or state_lower == '1':
        return AutonomyState.LIMITED_ONLY
    if state_lower == 'undefined' or state_lower == 'default':
        return AutonomyState.UNDEFINED
    else:
        sims4.commands.output('Invalid Autonomy State: {}. Valid values are on, full, true, medium, false, off, default, undefined, limitedonly'.format(state_lower), _connection)
        logger.error('Unknown state: {}', state_lower, owner='rmccord')
        return

def _convert_state_to_string(autonomy_state):
    if autonomy_state == AutonomyState.UNDEFINED:
        return 'Undefined'
    if autonomy_state == AutonomyState.DISABLED:
        return 'Disabled'
    if autonomy_state == AutonomyState.LIMITED_ONLY:
        return 'Limited Only'
    if autonomy_state == AutonomyState.MEDIUM:
        return 'Medium'
    if autonomy_state == AutonomyState.FULL:
        return 'Full'
    else:
        return '<Unknown State: {}>'.format(autonomy_state)

def _parse_randomization(randomization):
    randomization_lower = randomization.lower()
    if randomization_lower == 'on' or randomization_lower == 'true' or randomization_lower == 'enabled':
        return AutonomyRandomization.ENABLED
    if randomization_lower == 'off' or randomization_lower == 'false' or randomization_lower == 'disabled':
        return AutonomyRandomization.DISABLED
    if randomization_lower == 'undefined' or randomization_lower == 'default':
        return AutonomyRandomization.UNDEFINED
    else:
        logger.error('Unknown randomization: {}', randomization_lower, owner='rez')
        return

def _convert_randomization_to_string(autonomy_randomization):
    if autonomy_randomization == AutonomyRandomization.UNDEFINED:
        return 'Undefined'
    if autonomy_randomization == AutonomyRandomization.DISABLED:
        return 'Disabled'
    if autonomy_randomization == AutonomyRandomization.ENABLED:
        return 'Enabled'
    else:
        return '<Unknown Randomization: {}>'.format(autonomy_randomization)

@sims4.commands.Command('autonomy.show_timers')
def show_autonomy_timers(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sim.debug_output_autonomy_timers(_connection)
    else:
        sims4.commands.output('No target for autonomy.show_timers.', _connection)

@sims4.commands.Command('autonomy.clear_skipped_autonomy')
def clear_skipped_autonomy(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sim.clear_all_autonomy_skip_sis()
    else:
        sims4.commands.output('No target for autonomy.clear_skipped_autonomy.', _connection)

def _reset_autonomy_timers_for_all_objects():
    for obj in services.object_manager().valid_objects():
        if obj.has_component(objects.components.types.AUTONOMY_COMPONENT):
            obj.debug_update_autonomy_timer(FullAutonomy)

@sims4.commands.Command('autonomy.toggle_user_directed_interaction_full_autonomy_ping')
def override_disable_autonomous_multitasking_if_user_directed(enabled=None, _connection=None):
    if enabled is None:
        to_enabled = None
    else:
        enabled_lower = enabled.lower()
        if enabled_lower == 'on' or enabled_lower == 'true' or enabled_lower == 'enabled':
            to_enabled = True
        elif enabled_lower == 'off' or enabled_lower == 'false' or enabled_lower == 'disabled':
            to_enabled = False
        elif enabled_lower == 'undefined' or enabled_lower == 'default':
            to_enabled = singletons.DEFAULT
    status = AutonomyMode.toggle_disable_autonomous_multitasking_if_user_directed(to_enabled)
    sims4.commands.output('Current disable autonomous multitasking: {}'.format(status), _connection)

@sims4.commands.Command('autonomy.override_full_autonomy_delay', command_type=sims4.commands.CommandType.Automation)
def override_full_autonomy_delay(lower_bound:float, upper_bound:float, _connection=None):
    AutonomyMode.override_full_autonomy_delay(lower_bound, upper_bound)
    _reset_autonomy_timers_for_all_objects()

@sims4.commands.Command('autonomy.clear_full_autonomy_override', command_type=sims4.commands.CommandType.Automation)
def clear_full_autonomy_override(_connection=None):
    AutonomyMode.clear_full_autonomy_delay_override()
    _reset_autonomy_timers_for_all_objects()

@sims4.commands.Command('autonomy.override_full_autonomy_delay_after_user_action', command_type=sims4.commands.CommandType.Automation)
def override_full_autonomy_delay_after_user_action(delay:float, _connection=None):
    AutonomyMode.override_full_autonomy_delay_after_user_action(delay)
    _reset_autonomy_timers_for_all_objects()

@sims4.commands.Command('autonomy.clear_full_autonomy_delay_after_user_action', command_type=sims4.commands.CommandType.Automation)
def clear_full_autonomy_delay_after_user_action(_connection=None):
    AutonomyMode.clear_full_autonomy_delay_after_user_action()
    _reset_autonomy_timers_for_all_objects()

@sims4.commands.Command('autonomy.reset_autonomy_alarm')
def reset_autonomy_alarm(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sim.debug_reset_autonomy_alarm()
    else:
        sims4.commands.output('No target for autonomy.reset_autonomy_alarm.', _connection)

@sims4.commands.Command('autonomy.run')
def run_autonomy(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target for autonomy.run', _connection)
        return
    sim.run_full_autonomy_next_ping()

@sims4.commands.Command('autonomy.test_ping', command_type=sims4.commands.CommandType.Automation)
def test_ping_autonomy(opt_sim:OptionalTargetParam=None, affordance:TunableInstanceParam(sims4.resources.Types.INTERACTION)=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        output('No target for autonomy.run')
        return
    if affordance is not None:
        affordance_list = (affordance,)
        commodity_list = affordance.commodity_flags
    else:
        affordance_list = None
        commodity_list = None
    selected_interaction = sim.run_test_autonomy_ping(affordance_list=affordance_list, commodity_list=commodity_list)
    output('Autonomy Test Ping: {}'.format(selected_interaction))

@sims4.commands.Command('autonomy.add_modifier')
def add_modifier(stat_multiplier_list_string, locked_stat_list_string='', decay_multiplier_list_string='', opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target for autonomy.add_modifier', _connection)
        return
    multipliers = _read_multiplier_dictionary_from_string(stat_multiplier_list_string, _connection)
    if multipliers == None:
        sims4.commands.output('Unable to parse stat multiplier list.', _connection)
        return
    decay_multipliers = _read_multiplier_dictionary_from_string(decay_multiplier_list_string, _connection)
    if multipliers == None:
        sims4.commands.output('Unable to parse decay multiplier list.', _connection)
        return
    locked_stat_list = locked_stat_list_string.split()
    locked_stats = []
    for stat_str in locked_stat_list:
        stat = _get_stat_from_string(stat_str, _connection)
        if stat is None:
            return
        locked_stats.append(stat)
    modifier = AutonomyModifier(multipliers, locked_stats, decay_multipliers)
    handle = sim.add_statistic_modifier(modifier)
    sims4.commands.output('Successfully added autonomy modifier: {}.'.format(handle), _connection)

@sims4.commands.Command('autonomy.remove_modifier')
def remove_modifier(handle:int, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target for autonomy.add_modifier', _connection)
        return
    if sim.remove_statistic_modifier(handle):
        sims4.commands.output('Successfully removed autonomy modifier', _connection)
    else:
        sims4.commands.output('Unable to find autonomy handle: {}'.format(handle), _connection)

@sims4.commands.Command('autonomy.update_sleep_schedule')
def force_update_sleep_schedule(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target for autonomy.update_sleep_schedule', _connection)
        return
    sim.update_sleep_schedule()

@sims4.commands.Command('autonomy.reset_multitasking_roll')
def reset_multitasking_roll(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target for autonomy.reset_multitasking_roll', _connection)
        return
    sim.reset_multitasking_roll()

@sims4.commands.Command('qa.automation.start_autonomy_load_test', command_type=sims4.commands.CommandType.Automation)
def start_autonomy_load_test(motive_value:float=-40, _connection=None):
    sim_list = [sim for sim in services.sim_info_manager().instanced_sims_gen()]
    global_autonomy_randomization('disabled', _connection=_connection)
    for sim in sim_list:
        sim.run_full_autonomy_next_ping()
    _randomize_all_motives_deterministically(sim_list, motive_value)
    services.autonomy_service().start_automated_load_test(_connection, len(sim_list))

@sims4.commands.Command('qa.automation.start_single_sim_performance_test', command_type=sims4.commands.CommandType.Automation)
def start_single_sim_performance_test(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target for qa.automation.start_single_sim_performance_test', _connection)
        return
    sim.reset(ResetReason.RESET_EXPECTED, None, 'start_single_sim_performance_test')
    services.autonomy_service().start_single_sim_load_test(_connection, sim)
    sim.run_full_autonomy_next_ping()

@sims4.commands.Command('autonomy.show_queue', command_type=sims4.commands.CommandType.Automation)
def show_queue(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('Autonomy Queue:')
    if services.autonomy_service()._active_sim is not None:
        output('    0) {}'.format(services.autonomy_service()._active_sim))
    else:
        output('    0) None')
    for (index, request) in enumerate(services.autonomy_service().queue, start=1):
        output('    {}) {}'.format(index, request.sim))
    queue_size = len(services.autonomy_service().queue)
    output('Queue size: {}'.format(queue_size))

@sims4.commands.Command('qa.automation.show_queue', command_type=sims4.commands.CommandType.Automation)
def show_queue_automation(_connection=None):
    sims4.commands.automation_output('Autonomy; Queue:Begin', _connection)
    automation_logger.debug('Autonomy; Queue:Begin')
    for request in services.autonomy_service().queue:
        sims4.commands.automation_output('Autonomy; Queue:Data, Id:{}'.format(request.sim.id), _connection)
        automation_logger.debug('Autonomy; Queue:Data, Id:{}'.format(request.sim.id))
    sims4.commands.automation_output('Autonomy; Queue:End', _connection)
    automation_logger.debug('Autonomy; Queue:End')

@sims4.commands.Command('autonomy.show_update_times', command_type=sims4.commands.CommandType.Automation)
def show_update_times(_connection=None):
    sim_info_manager = services.sim_info_manager()
    sim_times = []
    for sim in sim_info_manager.instanced_sims_gen():
        autonomy_component = sim.autonomy_component
        if autonomy_component is not None:
            sim_times.append((sim.full_name, autonomy_component.get_time_until_ping()))
    sim_times.sort(key=lambda x: x[1])
    output = sims4.commands.CheatOutput(_connection)
    output('Update Times:')
    for (name, time) in sim_times:
        output('    {}: {}'.format(time, name))

def _read_multiplier_dictionary_from_string(stat_list_string, _connection=None):
    string_list = stat_list_string.split()
    if len(string_list) % 2 != 0:
        sims4.commands.output("multiplier_list_string didn't have an even number of elements", _connection)
        return
    multiplier_dict = {}
    index = 0
    while index < len(string_list):
        stat = _get_stat_from_string(string_list[index], _connection)
        if stat is None:
            return
        try:
            multiplier = float(string_list[index + 1])
        except ValueError:
            sims4.commands.output('Multiplier value is not a valid float: {}.'.format(string_list[index + 1]), _connection)
            return
        multiplier_dict[stat] = multiplier
        index += 2
    return multiplier_dict

def _get_stat_from_string(stat_str, _connection):
    stat_name = stat_str.lower()
    stat = services.get_instance_manager(sims4.resources.Types.STATISTIC).get(stat_name)
    if stat is None:
        sims4.commands.output("Unable to get stat '{}'.".format(stat_name), _connection)
        return
    return stat

def _randomize_all_motives_deterministically(sim_list, motive_value:float):
    sim_list_length = len(sim_list)
    sim_list_index = 0
    while sim_list_index < sim_list_length:
        for (commodity_type, count) in autonomy.autonomy_modes.AutonomyMode.AUTOMATED_RANDOMIZATION_LIST.items():
            for _ in range(count):
                sim_list[sim_list_index].set_stat_value(commodity_type, motive_value)
                sim_list_index += 1
                if sim_list_index >= sim_list_length:
                    return
    logger.error('Weird exit in randomize_all_motives_deterministically()', owner='rez')

@sims4.commands.Command('autonomy.trigger_walkby', command_type=sims4.commands.CommandType.DebugOnly)
def trigger_walkby(_connection=None):
    situation_id = services.current_zone().ambient_service.debug_update()
    if situation_id is not None:
        situation = services.get_zone_situation_manager().get(situation_id)
        sims4.commands.output('Created ambient situation: {}.{}'.format(situation, situation_id), _connection)
    else:
        sims4.commands.output('Did not create ambient situation. There are no types of walkbys that are available at this time.', _connection)
    return True

@sims4.commands.Command('autonomy.set_anchor', command_type=sims4.commands.CommandType.DebugOnly)
def set_anchor(x:float, y:float, z:float, level:int, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Couldn't find Sim.", _connection)
        return
    vec = Vector3(x, y, z)
    sim.set_anchor((vec, level))

@sims4.commands.Command('autonomy.clear_anchor', command_type=sims4.commands.CommandType.DebugOnly)
def clear_anchor(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Couldn't find Sim.", _connection)
        return
    sim.clear_anchor()

@sims4.commands.Command('autonomy.log_sim')
def sim_autonomy_log_on(status:bool, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('Invalid Sim ID specified.', _connection)
        return False
    _set_sim_autonomy_log(sim, state=status)

def _set_sim_autonomy_log(sim:sims.sim.Sim, state=None):
    if state:
        services.autonomy_service().logging_sims.add(sim)
    else:
        services.autonomy_service().logging_sims.discard(sim)
    logger.debug('Autonomy log toggled to {0} on {1}', state, sim)
    return True

@sims4.commands.Command('autonomy.distance_estimates.enable', command_type=sims4.commands.CommandType.Automation)
def autonomy_distance_estimates_enable(_connection=None):
    autonomy.autonomy_util.AutonomyAffordanceTimes.start()

@sims4.commands.Command('autonomy.distance_estimates.disable', command_type=sims4.commands.CommandType.Automation)
def autonomy_distance_estimates_disable(_connection=None):
    autonomy.autonomy_util.AutonomyAffordanceTimes.stop()

@sims4.commands.Command('autonomy.distance_estimates.reset', command_type=sims4.commands.CommandType.Automation)
def autonomy_reset_aggregate_times(_connection=None):
    autonomy.autonomy_util.AutonomyAffordanceTimes.reset()

@sims4.commands.Command('autonomy.distance_estimates.dump', command_type=sims4.commands.CommandType.Automation)
def autonomy_distance_estimates_dump(_connection=None):
    autonomy.autonomy_util.AutonomyAffordanceTimes.dump(connection=_connection)

@sims4.commands.Command('autonomy.distance_estimates.perform_timed_run', command_type=sims4.commands.CommandType.Automation)
def autonomy_distance_estimates_perform_timed_run(time_to_run_in_seconds:int=180, _connection=None):
    global g_distance_estimate_alarm_handle
    if g_distance_estimate_alarm_handle is not None:
        autonomy_distance_estimates_disable(_connection=_connection)
        alarms.cancel_alarm(g_distance_estimate_alarm_handle)
        g_distance_estimate_alarm_handle = None
    autonomy_distance_estimates_enable(_connection=_connection)

    def _finish_test_and_write_file(_):
        global g_distance_estimate_alarm_handle
        autonomy_distance_estimates_dump(_connection=_connection)
        autonomy_distance_estimates_disable(_connection=_connection)
        g_distance_estimate_alarm_handle = None

    time_span = date_and_time.create_time_span(minutes=time_to_run_in_seconds)
    g_distance_estimate_alarm_handle = alarms.add_alarm_real_time(services.autonomy_service(), time_span, _finish_test_and_write_file)

@sims4.commands.Command('autonomy.npc_autonomy', command_type=sims4.commands.CommandType.Automation)
def set_npc_autonomy(npc_autonomy_type:NPCAutonomyType, new_setting:bool, _connection=None) -> bool:
    if services.autonomy_service().global_autonomy_settings.get_npc_setting(npc_autonomy_type) != new_setting:
        services.autonomy_service().global_autonomy_settings.set_npc_setting(npc_autonomy_type, new_setting)
        return True
    return False
