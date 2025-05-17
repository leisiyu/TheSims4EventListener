# from sims4 import services
import services
from event_testing.test_events import TestEvent
from interactions import ParticipantType


class MyModEvents():
    def __init__(self, data):
        self.data = data

    def handle_event(self, sim_info, event, resolver):
        if sim_info is None:
            with open('D:\\Qianwen\\Mods\\example.txt', 'a') as file:
                file.write("Sim info is None\n")
            return
        # participant = resolver.get_participant(ParticipantType.Actor)

        # timeline_now = services.time_service().sim_now
        # time_str = timeline_now
        interaction = resolver.interaction  # Access the completed interaction
        target = interaction.target  # Get the target of the interaction
        interaction_name = interaction.affordance.__name__  # Name of the interaction
        with open('D:\\Qianwen\\Mods\\example.txt', 'a') as file:
            file.write(f"Sim: {sim_info.full_name}, Interaction: {interaction_name}, Target: {target}\n")


    def registerEvent(self):
        event_manager = services.get_event_manager()
        if event_manager is not None:
            event_manager.register_single_event(self, TestEvent.InteractionStart)

