# from sims4 import services
import services
from event_testing.test_events import TestEvent
from interactions import ParticipantType
import Util
import json


class MyModEvents():
    def __init__(self, data):
        self.data = data

    def handle_event(self, sim_info, event, resolver):
        logDir = Util.getPath()
        if sim_info is None:
            with open(logDir, 'a') as file:
                file.write("Sim info is None\n")
            return
        # participant = resolver.get_participant(ParticipantType.Actor)

        timeline_now = services.time_service().sim_now
        time_str = Util.timeToTimeStamp(timeline_now)
        interaction = resolver.interaction  # Access the completed interaction
        # target = interaction.target  # Get the target of the interaction
        interaction_name = interaction.affordance.__name__  # Name of the interaction
        simName = sim_info.first_name + " " + sim_info.last_name


        actor = resolver.get_participant(ParticipantType.Actor)
        target = resolver.get_participant(ParticipantType.TargetSim)

        if actor and target:
            actor_name = actor.first_name + " " + actor.last_name
            target_name = target.first_name + " " + target.last_name

        current_zone = services.current_zone()
        if current_zone is not None:
            zone_id = current_zone.id  # Get the current zone ID
            building_name = current_zone.lot.get_lot_name()


        # position = sim_info.get_sim_instance().transform.translation
        # position_str = f"X: {position.x} Y: {position.y} Z: {position.z}"


        eventJson = {
            "sim_name": simName,
            "target_name": target_name,
            "interaction_name": interaction_name,
            "building_name": building_name,
            "time": str(time_str)
        }

        with open(logDir, 'a') as file:
            file.write(json.dumps(eventJson) + "\n")


    def registerEvent(self):
        event_manager = services.get_event_manager()
        if event_manager is not None:
            event_manager.register_single_event(self, TestEvent.InteractionComplete)

