import sims4.commands
import services
import json

from my_mod_events import MyModEvents

# from server_commands.zone_commands import register_zone_loaded_callback


@sims4.commands.Command('myfirstscript', command_type=sims4.commands.CommandType.Live)
def myfirstscript(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output("this is my first script")
    with open('D:\Qianwen\Mods\example.txt', 'a') as file:
        file.write('This is my first script mod \n')#

@sims4.commands.Command('siminfo', command_type=sims4.commands.CommandType.Live)
def simInfo(_connection=None):
    # sim_info = services.active_sim_info()
    client = services.client_manager().get_first_client()
    sim_info = client.active_sim.sim_info

    output = sims4.commands.CheatOutput(_connection)
    output(sim_info + "\n")



@sims4.commands.Command('getname', command_type=sims4.commands.CommandType.Live)
def getSimName(_connection=None):
    client = services.client_manager().get_first_client()
    sim_info = client.active_sim.sim_info
    full_name = sim_info.first_name + " " + sim_info.last_name
    with open('D:\Qianwen\Mods\example.txt', 'a') as file:
        file.write('full name is ' + full_name + "\n")#
    output = sims4.commands.CheatOutput(_connection)

    output("name: " + full_name)

@sims4.commands.Command('getlocation', command_type=sims4.commands.CommandType.Live)
def getSimLocation(_connection=None):
    client = services.client_manager().get_first_client()
    sim_info = client.active_sim.sim_info
    position = sim_info.get_sim_instance().transform.translation
    position_str = f"X: {position.x}, Y: {position.y}, Z: {position.z}"
    output = sims4.commands.CheatOutput(_connection)
    output("location:" + position_str)
    with open('D:\Qianwen\Mods\example.txt', 'a') as file:
        file.write('location is: ' + position_str + "\n")  #


@sims4.commands.Command('getzone', command_type=sims4.commands.CommandType.Live)
def getSimZone(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    current_zone = services.current_zone()
    if current_zone is not None:
        zone_id = current_zone.id  # Get the current zone ID
        zone_name = current_zone.lot.get_lot_name()
        output(f"Sim is in zone: {zone_id}" + zone_name)
        with open('D:\\Qianwen\\Mods\\example.txt', 'a') as file:
            file.write(f"Sim is in zone: {zone_id} {zone_name}\n")
    else:
        output("Unable to retrieve the current zone.")

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


@sims4.commands.Command('regevent', command_type=sims4.commands.CommandType.Live)
def regEvent(_connection=None):
    myModEvents = MyModEvents("test")
    myModEvents.registerEvent()