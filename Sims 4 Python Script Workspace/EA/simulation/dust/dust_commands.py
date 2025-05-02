import servicesimport sims4from event_testing.game_option_tests import TestableGameOptionsfrom event_testing.test_events import TestEventfrom sims4.common import Pack
@sims4.commands.Command('dust.set_dust_enabled', pack=Pack.SP22, command_type=sims4.commands.CommandType.Live)
def set_dust_enabled(enabled:bool=True, _connection=None):
    dust_service = services.dust_service()
    if dust_service is None:
        sims4.commands.automation_output('Pack not loaded', _connection)
        sims4.commands.cheat_output('Pack not loaded', _connection)
        return False
    dust_service.set_enabled(enabled)
    services.get_event_manager().process_event(TestEvent.TestedGameOptionChanged, custom_keys=(TestableGameOptions.DUST_SYSTEM_ENABLED,))
    return True
