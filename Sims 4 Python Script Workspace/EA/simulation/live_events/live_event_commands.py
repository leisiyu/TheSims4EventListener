import servicesimport sims4.commandsfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom live_events.live_event_dialogs import LiveEventDialogsfrom live_events.live_event_service import LiveEventService, LiveEventState, LiveEventNamefrom live_events.live_event_telemetry import LiveEventSourcefrom ui.ui_dialog import UiMessageArgType, UiDialogResponselogger = sims4.log.Logger('Live Events')with sims4.reload.protected(globals()):
    LIVE_EVENT_WIDGET_ARG_EVENT_ID = 'eventId'
    LIVE_EVENT_WIDGET_ARG_FROM_CTA = 'bFromCTA'
    LIVE_EVENT_WIDGET_ARG_SOURCE = 'source'
@sims4.commands.Command('live_events.get_live_events', command_type=sims4.commands.CommandType.Live)
def get_live_events(*live_event_list, _connection=None):
    if live_event_list:
        live_event_service = services.get_live_event_service()
        if live_event_service is not None:
            live_event_service.process_incoming_live_events(live_event_list)

@sims4.commands.Command('live_events.open_event_dialog', command_type=sims4.commands.CommandType.DebugOnly)
def open_event_dialog(live_event_name:str, _connection=None):
    if str(live_event_name) not in LiveEventName:
        sims4.commands.output('The live event {} does not exist'.format(live_event_name), _connection)
        return
    live_event_service = services.get_live_event_service()
    live_event_data = live_event_service.LIVE_EVENTS.get(LiveEventName[str(live_event_name)], None)
    if live_event_data is not None and live_event_data.action.action_type == LiveEventService.ACTION_TYPE_DRAMA_NODE and hasattr(live_event_data.action.drama_node, 'dialog_and_loot'):
        resolver = SingleSimResolver(services.active_sim_info())
        if services.drama_scheduler_service().run_node(live_event_data.action.drama_node, resolver):
            sims4.commands.output('Successfully run dialog drama node: {} from live event.'.format(live_event_data.action.drama_node.__name__), _connection)
        else:
            sims4.commands.output('Failed to run dialog drama node: {} from live event'.format(live_event_data.action.drama_node.__name__), _connection)
        return
    sims4.commands.output('The live event does not have a dialog to show.', _connection)

@sims4.commands.Command('live_events.set_live_event_state', command_type=sims4.commands.CommandType.DebugOnly)
def set_live_event_state(live_event_name:str, live_event_state:int=1, _connection=None):
    if live_event_state not in LiveEventState:
        sims4.commands.output('{} is not a valid live event state'.format(live_event_state), _connection)
        return
    if str(live_event_name) not in LiveEventName:
        sims4.commands.output('The live event {} does not exist'.format(live_event_name), _connection)
        return
    live_event_service = services.get_live_event_service()
    event_manager = services.get_event_manager()
    live_event = LiveEventName[str(live_event_name)]
    if live_event in live_event_service.LIVE_EVENTS:
        if live_event_state == LiveEventState.ACTIVE and live_event_service.get_live_event_state(live_event) is not LiveEventState.ACTIVE:
            live_event_service.activate_live_event(live_event)
            event_manager.process_event(TestEvent.LiveEventStatesProcessed)
        elif live_event_state == LiveEventState.COMPLETED and live_event_service.get_live_event_state(live_event) is not LiveEventState.COMPLETED:
            live_event_service.set_live_event_state(live_event, LiveEventState.COMPLETED)
            event_manager.process_event(TestEvent.LiveEventStatesProcessed)
        else:
            sims4.commands.output('The live event {} was already in the {} state'.format(live_event_name, LiveEventState(live_event_state).name), _connection)
            return
        sims4.commands.output('Live event {} set to {}'.format(live_event_name, LiveEventState(live_event_state).name), _connection)
        return

@sims4.commands.Command('live_events.set_days_played', command_type=sims4.commands.CommandType.Live)
def set_days_played(player_experience_level:int, _connection=None) -> None:
    live_event_service = services.get_live_event_service()
    live_event_service.player_experience_level = player_experience_level

@sims4.commands.Command('live_events.show_reward_available_dialog', command_type=sims4.commands.CommandType.Live)
def show_reward_unlocked_dialog(event_id:str, _connection=None):
    client = services.client_manager().get(_connection)
    event_reward_notification = LiveEventDialogs.REWARD_NOTIFICATIONS.get(event_id, None)
    if event_reward_notification is None:
        sims4.commands.output('RewardAvailableNotification not found for LiveEventId: {}. Make sure tuning exists in OE live_event_dialogs for LiveEvent.'.format(event_id), _connection)
        return
    notification = event_reward_notification(client.active_sim)
    if notification.ui_responses is not None:
        for response in notification.ui_responses:
            if response.ui_request == UiDialogResponse.UiDialogUiRequest.SEND_UI_MESSAGE and response.ui_message_name == 'ShowLiveEvent':
                event_id_arg = (LIVE_EVENT_WIDGET_ARG_EVENT_ID, UiMessageArgType.TYPE_STRING, event_id)
                from_cta_arg = (LIVE_EVENT_WIDGET_ARG_FROM_CTA, UiMessageArgType.TYPE_BOOL, True)
                source_arg = (LIVE_EVENT_WIDGET_ARG_SOURCE, UiMessageArgType.TYPE_INT, LiveEventSource.TNS)
                ui_msg_args = [event_id_arg, from_cta_arg, source_arg]
                response.set_ui_message_args(ui_msg_args)
                break
    notification.show_dialog()
