import sims4.commands
import services
import json

# from server_commands.zone_commands import register_zone_loaded_callback
from event_testing.test_events import TestEvent

@sims4.commands.Command('myfirstscript', command_type=sims4.commands.CommandType.Live)
def myfirstscript(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output("this is my first script")
    with open('D:\Qianwen\Mods\example.txt', 'a') as file:
        file.write('This is my first script mod')#

@sims4.commands.Command('simInfo', command_type=sims4.commands.CommandType.Live)
def simInfo(_connection=None):
    sim_info = services.active_sim_info()
    output = sims4.commands.CheatOutput(_connection)
    output(sim_info+ "\n")


@sims4.commands.Command('getname', command_type=sims4.commands.CommandType.Live)
def getSimName(_connection=None):
    client = services.client_manager().get_first_client()
    sim_info = client.active_sim.sim_info
    full_name = sim_info.first_name + " " + sim_info.last_name
    with open('D:\Qianwen\Mods\example.txt', 'a') as file:
        file.write('full name is ' + full_name + "\n")#
    output = sims4.commands.CheatOutput(_connection)
    output("name: " + full_name)

@sims4.commands.Command('getingametime', command_type=sims4.commands.CommandType.Live)
def getInGameTime(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    game_clock_now = services.game_clock_service().now()
    timeline_now = services.time_service().sim_now
    results = 'GameTime;'
    results += ' GameHour:{}, GameMinute:{}, GameSecond:{}, GameDay:{}, GameWeek:{},'.format(game_clock_now.hour(),
                                                                                             game_clock_now.minute(),
                                                                                             game_clock_now.second(),
                                                                                             game_clock_now.day(),
                                                                                             game_clock_now.week())
    results += ' SimHour:{}, SimMinute:{}, SimSecond:{}, SimDay:{}, SimWeek:{},'.format(timeline_now.hour(),
                                                                                        timeline_now.minute(),
                                                                                        timeline_now.second(),
                                                                                        timeline_now.day(),
                                                                                        timeline_now.week())
    output(results)
    with open('D:\Qianwen\Mods\example.txt', 'a') as file:
        file.write(results + "\n")


# def on_zone_loaded(zone_id):
#     output = sims4.commands.CheatOutput(_connection)
#     output("zone: " + zone_id)
#     with open('D:\Qianwen\Mods\example.txt', 'a') as file:
#         file.write('zone id is ' + zone_id + "\n")
#
# @sims4.commands.Command('zone', command_type=sims4.commands.CommandType.Live)
# def registerZone(zone_id=None, _connection=None):
#     sims4.callback_utils.register_zone_loaded_callback(on_zone_loaded)