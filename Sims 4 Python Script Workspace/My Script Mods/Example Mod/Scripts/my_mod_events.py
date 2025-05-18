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
        time_str = timeline_now
        interaction = resolver.interaction  # Access the completed interaction
        target = interaction.target  # Get the target of the interaction
        interaction_name = interaction.affordance.__name__  # Name of the interaction
        simName = sim_info.first_name + " " + sim_info.last_name

        eventJson = {
            "sim_name": simName,
            "interaction_name": interaction_name,
            "target": str(target),
            "time": str(time_str)
        }

        with open(logDir, 'a') as file:
            file.write(json.dumps(eventJson) + "\n")


    def registerEvent(self):
        event_manager = services.get_event_manager()
        if event_manager is not None:
            event_manager.register_single_event(self, TestEvent.InteractionStart)

