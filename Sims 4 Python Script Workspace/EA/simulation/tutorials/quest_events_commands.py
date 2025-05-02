from event_testing.resolver import SingleSimResolver, GlobalResolverfrom pivotal_moments.live_event_quest import LiveEventQuestfrom protocolbuffers import DistributorOps_pb2import servicesimport sims4.commandsimport sims4.resourcesfrom google.protobuf import text_formatlogger = sims4.log.Logger('Quest Event Commands')
@sims4.commands.Command('quest_events.get_quest_events', command_type=sims4.commands.CommandType.Live)
def get_quest_events(quest_events_string:str, _connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is None:
        logger.warn('Unable to process quest events before the tutorial service is instantiated.')
        return
    quest_event_proto = DistributorOps_pb2.LiveEventsQuestData()
    if quest_events_string:
        text_format.Merge(quest_events_string, quest_event_proto)
    tutorial_service.process_incoming_quest_events(quest_event_proto)

@sims4.commands.Command('quest_events.force_quest_activation', command_type=sims4.commands.CommandType.DebugOnly)
def force_quest_activation(pivotal_moment_id:int, _connection:int=None) -> None:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is None:
        sims4.commands.output('Tutorial Service not available', _connection)
        return False
    tutorial_service.debug_activate_quest(pivotal_moment_id)

@sims4.commands.Command('quest_events.grant_live_event_reward', command_type=sims4.commands.CommandType.Live)
def grant_live_event_reward(reward_loot_id:int, _connection:int=None) -> bool:
    action_manager = services.get_instance_manager(sims4.resources.Types.ACTION)
    if action_manager is None:
        return False
    reward_loot = action_manager.get(reward_loot_id)
    if reward_loot is None:
        return False
    resolver = SingleSimResolver(services.active_sim_info())
    reward_loot.apply_to_resolver(resolver)
    return True

@sims4.commands.Command('quest_events.trigger_end_event_notification', command_type=sims4.commands.CommandType.Live)
def trigger_end_event_notification(_connection:int=None) -> bool:
    notification = LiveEventQuest.LIVE_EVENT_QUEST_END_NOTIFICATION(None, resolver=GlobalResolver())
    notification.show_dialog()
    return True

@sims4.commands.Command('quest_events.reprocess_quest_events', command_type=sims4.commands.CommandType.Live)
def reprocess_quest_events(quest_events_string:str, _connection:int=None) -> bool:
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is None:
        sims4.commands.output('Tutorial Service not available', _connection)
        return False
    if not quest_events_string:
        sims4.commands.output('No quest events string provided to reset quests events.', _connection)
        return False
    quest_event_proto = DistributorOps_pb2.LiveEventsQuestData()
    text_format.Merge(quest_events_string, quest_event_proto)
    tutorial_service.reprocess_quest_events(quest_event_proto)
    return True
