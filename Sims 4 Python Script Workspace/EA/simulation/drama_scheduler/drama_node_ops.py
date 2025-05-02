from drama_scheduler.drama_node_types import DramaNodeTypefrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableReference, TunableSet, TunableEnumEntry, OptionalTunable, Tunablefrom tunable_time import TunableTimeSpanimport servicesimport sims4.resources
class ScheduleDramaNodeLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'drama_node': TunableReference(description='\n            The drama node to schedule.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)), 'time_delay': OptionalTunable(description='\n            If enabled, this drama node will be scheduled to run later.\n            ', tunable=TunableTimeSpan(description='\n                The amount of time the node will be delayed by.\n                '))}

    def __init__(self, drama_node, time_delay, **kwargs):
        super().__init__(**kwargs)
        self._drama_node = drama_node
        self._time_delay = time_delay

    def _apply_to_subject_and_target(self, subject, target, resolver):
        specific_time = None
        if self._time_delay is not None:
            specific_time = services.time_service().sim_now + self._time_delay()
        services.drama_scheduler_service().schedule_node(self._drama_node, resolver, specific_time=specific_time)

class CancelScheduledDramaNodeLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'drama_nodes': TunableSet(description='\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))), 'receiver': TunableEnumEntry(description='\n            The recipient of the drama node.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'sender': OptionalTunable(description='\n            The sender of the drama node. Can be left unspecified if there is\n            no sender.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.TargetSim)), 'is_simless': Tunable(description='\n            If checked, no receiver or sender will be considered, and all \n            specified drama nodes will be canceled.\n            ', tunable_type=bool, default=False), 'locked_args': {'subject': None}}

    def __init__(self, drama_nodes, receiver, sender, is_simless, **kwargs):
        super().__init__(**kwargs)
        self._drama_nodes = drama_nodes
        self._receiver_type = receiver
        self._sender_type = sender
        self._is_simless = is_simless

    def _apply_to_subject_and_target(self, subject, target, resolver):
        receiver = resolver.get_participant(self._receiver_type)
        sender = resolver.get_participant(self._sender_type) if self._sender_type is not None else None
        dss = services.drama_scheduler_service()
        for node in tuple(dss.scheduled_nodes_gen()):
            recipient_passed = self._recipient_passed(node, receiver)
            sender_passed = self._sender_passed(node, sender)
            if type(node) in self._drama_nodes and recipient_passed and sender_passed:
                dss.cancel_scheduled_node(node.uid)

    def _recipient_passed(self, node, receiver):
        if node.drama_node_type == DramaNodeType.MULTI_UNIT_EVENT and node.is_receiver_valid(receiver):
            return True
        elif self._is_simless or node.get_receiver_sim_info() is receiver:
            return True
        return False

    def _sender_passed(self, node, sender):
        if node.drama_node_type == DramaNodeType.MULTI_UNIT_EVENT:
            return True
        elif self._is_simless or node.get_sender_sim_info() is sender:
            return True
        return False
