from protocolbuffers import UI_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom date_and_time import create_time_span, TimeSpanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msg, IconInfoData, build_icon_info_msgfrom distributor.system import Distributorfrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeScoringBucket, CooldownOption, DramaNodeRunOutcome, DramaNodeUiDisplayTypefrom drama_scheduler.drama_node_types import DramaNodeTypefrom drama_scheduler.festival_contest_drama_node_mixin import FestivalContestDramaNodeMixinfrom event_testing.resolver import GlobalResolverfrom event_testing.test_events import TestEventfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.tunable_icon import TunableIconfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom open_street_director.open_street_director_request import OpenStreetDirectorRequestfrom organizations.organization_ops import OrgEventInfofrom server.pick_info import PickInfo, PickTypefrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunableTuple, TunableRange, TunableEnumEntry, TunableSimMinute, TunableList, TunableResourceKey, TunablePackSafeReference, TunableLotDescription, Tunable, HasTunableSingletonFactory, TunableVariant, AutoFactoryInitfrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom sims4.utils import classproperty, flexmethodfrom ui.tested_ui_dialog_notification import TunableTestedUiDialogNotificationSnippetfrom ui.ui_dialog import CommandArgTypeimport alarmsimport elementsimport enumimport interactions.contextimport servicesimport sims4.resourcesfrom world import get_lot_id_from_instance_idlogger = sims4.log.Logger('DramaNode', default_owner='jjacobson')
class FestivalDramaNode(BaseDramaNode):
    GO_TO_FESTIVAL_INTERACTION = TunablePackSafeReference(description='\n        Reference to the interaction used to travel the Sims to the festival.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    INSTANCE_TUNABLES = {'festival_open_street_director': TunableReference(description='\n            Reference to the open street director in question.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OPEN_STREET_DIRECTOR)), 'street': TunableReference(description='\n            The street that this festival is allowed to run on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STREET)), 'scoring': OptionalTunable(description='\n            If enabled this DramaNode will be scored and chosen by the drama\n            service.\n            ', tunable=TunableTuple(description='\n                Data related to scoring this DramaNode.\n                ', base_score=TunableRange(description='\n                    The base score of this drama node.  This score will be\n                    multiplied by the score of the different filter results\n                    used to find the Sims for this DramaNode to find the final\n                    result.\n                    ', tunable_type=int, default=1, minimum=1), bucket=TunableEnumEntry(description="\n                    Which scoring bucket should these drama nodes be scored as\n                    part of.  Only Nodes in the same bucket are scored against\n                    each other.\n                    \n                    Change different bucket settings within the Drama Node's\n                    module tuning.\n                    ", tunable_type=DramaNodeScoringBucket, default=DramaNodeScoringBucket.DEFAULT), locked_args={'receiving_sim_scoring_filter': None})), 'pre_festival_duration': TunableSimMinute(description='\n            The amount of time in Sim minutes that this festival will be in a\n            pre-running state.  Testing against this Drama Node will consider\n            the node to be running, but the festival will not actually be.\n            ', default=120, minimum=1), 'fake_duration': TunableSimMinute(description="\n            The amount of time in Sim minutes that we will have this drama node\n            run when the festival isn't actually up and running.  When the\n            festival actually runs we will trust in the open street director to\n            tell us when we should actually end.\n            ", default=60, minimum=1), 'festival_dynamic_sign_info': OptionalTunable(description='\n            If enabled then this festival drama node can be used to populate\n            a dynamic sign.\n            ', tunable=TunableTuple(description='\n                Data for populating the dynamic sign view for the festival.\n                ', festival_name=TunableLocalizedString(description='\n                    The name of this festival.\n                    '), festival_time=TunableLocalizedString(description='\n                    The time that this festival should run.\n                    '), travel_to_festival_text=TunableLocalizedString(description='\n                    The text that will display to get you to travel to the festival.\n                    '), festival_not_started_tooltip=TunableLocalizedString(description='\n                    The tooltip that will display on the travel to festival\n                    button when the festival has not started.\n                    '), on_street_tooltip=TunableLocalizedString(description='\n                    The tooltip that will display on the travel to festival\n                    button when the player is already at the festival.\n                    '), on_vacation_tooltip=TunableLocalizedString(description='\n                    The tooltip that will display on the travel to festival\n                    button when the player is on vacation.\n                    '), display_image=TunableResourceKey(description='\n                     The image for this festival display.\n                     ', resource_types=sims4.resources.CompoundTypes.IMAGE), background_image=TunableResourceKey(description='\n                     The background image for this festival display.\n                     ', default=None, resource_types=sims4.resources.CompoundTypes.IMAGE), activity_info=TunableList(description='\n                    The different activities that are advertised to be running at this\n                    festival.\n                    ', tunable=TunableTuple(description='\n                        A single activity that will be taking place at this festival.\n                        ', activity_name=TunableLocalizedString(description='\n                            The name of this activity.\n                            '), activity_description=TunableLocalizedString(description='\n                            The description of this activity.\n                            '), icon=TunableIcon(description='\n                            The Icon that represents this festival activity.\n                            '), calendar_icon=TunableIcon(description='\n                            The icon that represents this festival activity in the calendar.\n                            ', allow_none=True)))), tuning_group=GroupNames.UI), 'starting_notification': OptionalTunable(description='\n            If enabled then when this festival runs we will surface a\n            notification to the players.\n            ', tunable=TunableTestedUiDialogNotificationSnippet(description='\n                The notification that will appear when this drama node runs.\n                '), tuning_group=GroupNames.UI), 'additional_drama_nodes': TunableList(description='\n            A list of additional drama nodes that we will score and schedule\n            when this drama node is run.  Only 1 drama node is run.\n            ', tunable=TunableReference(description='\n                A drama node that we will score and schedule when this drama\n                node is run.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))), 'delay_timeout': TunableSimMinute(description='\n            The amount of time in Sim minutes that the open street director has\n            been delayed that we will no longer start the festival.\n            ', default=120, minimum=0), 'travel_lot_override': OptionalTunable(description='\n            If enabled, sims will spawn at this lot instead of the Travel Lot \n            tuned on the street.\n            ', tunable=TunableLotDescription(description='\n                The specific lot that we will travel to when asked to travel to\n                this street.\n                ')), 'reject_same_street_travel': Tunable(description='\n            If True, we will disallow the drama node travel interaction to run\n            if the Sim is on the same street as the destination zone. If False,\n            same street travel will be allowed.\n            ', tunable_type=bool, default=True), 'calendar_activity_info': OptionalTunable(description='\n            If enabled, explicitly define the festival activities displayed in the Calendar.\n            Otherwise, use the data provided in Festival Dynamic Sign Info\n            ', tunable=TunableList(description='\n                A list of activity entries displayed in the calendar schedule.\n                ', tunable=TunableTuple(description='\n                    Data for a single activity.\n                    ', activity_name=TunableLocalizedString(description='\n                        The name of the activity.\n                        '), activity_description=TunableLocalizedString(description='\n                        The description of the activity.\n                        '), icon=TunableIcon(description='\n                        The icon for this activity.\n                        '))), disabled_name='use_sign_info', tuning_group=GroupNames.UI)}
    REMOVE_INSTANCE_TUNABLES = ('receiver_sim', 'sender_sim_info', 'picked_sim_info')

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.FESTIVAL

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def simless(cls):
        return True

    @classmethod
    def get_travel_lot_id(cls, reject_same_street=False):
        if reject_same_street and cls.street is services.current_street():
            return
        if cls.travel_lot_override is not None:
            return get_lot_id_from_instance_id(cls.travel_lot_override)
        return get_lot_id_from_instance_id(cls.street.travel_lot)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._duration_alarm = None
        self._additional_nodes_processor = None

    def cleanup(self, from_service_stop=False):
        super().cleanup(from_service_stop=from_service_stop)
        if self._duration_alarm is not None:
            alarms.cancel_alarm(self._duration_alarm)
            self._duration_alarm = None
        if self._additional_nodes_processor is not None:
            self._additional_nodes_processor.trigger_hard_stop()
            self._additional_nodes_processor = None

    def _alarm_finished_callback(self, _):
        services.drama_scheduler_service().complete_node(self.uid)

    def _request_timed_out_callback(self):
        services.drama_scheduler_service().complete_node(self.uid)

    def _open_street_director_destroyed_early_callback(self):
        services.drama_scheduler_service().complete_node(self.uid)

    def _get_time_till_end(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        duration = create_time_span(minutes=self.fake_duration + self.pre_festival_duration)
        time_left_to_go = duration - time_since_started
        return time_left_to_go

    def _setup_end_alarm(self):
        time_left_to_go = self._get_time_till_end()
        self._duration_alarm = alarms.add_alarm(self, time_left_to_go, self._alarm_finished_callback)

    def _create_open_street_director_request(self):
        festival_open_street_director = self.festival_open_street_director(drama_node_uid=self._uid)
        preroll_time = self._selected_time + create_time_span(minutes=self.pre_festival_duration)
        request = OpenStreetDirectorRequest(festival_open_street_director, priority=festival_open_street_director.priority, preroll_start_time=preroll_time, timeout=create_time_span(minutes=self.delay_timeout), timeout_callback=self._request_timed_out_callback, premature_destruction_callback=self._open_street_director_destroyed_early_callback)
        services.venue_service().request_open_street_director(request)

    def _try_and_start_festival(self, from_resume=False):
        street = services.current_street()
        if street is not self.street:
            self._setup_end_alarm()
            return
        self._create_open_street_director_request()

    def _process_scoring_gen(self, timeline):
        try:
            yield from services.drama_scheduler_service().score_and_schedule_nodes_gen(self.additional_drama_nodes, 1, street_override=self.street, timeline=timeline)
        except GeneratorExit:
            raise
        except Exception as exception:
            logger.exception('Exception while scoring DramaNodes: ', exc=exception, level=sims4.log.LEVEL_ERROR)
        finally:
            self._additional_nodes_processor = None

    def _pre_festival_alarm_callback(self, _):
        self._try_and_start_festival()
        services.get_event_manager().process_events_for_household(TestEvent.FestivalStarted, services.active_household())
        if self.starting_notification is not None:
            resolver = GlobalResolver()
            starting_notification = self.starting_notification(services.active_sim_info(), resolver=resolver)
            starting_notification.show_dialog(response_command_tuple=tuple([CommandArgType.ARG_TYPE_INT, self.guid64]))
        if self.additional_drama_nodes:
            sim_timeline = services.time_service().sim_timeline
            self._additional_nodes_processor = sim_timeline.schedule(elements.GeneratorElement(self._process_scoring_gen))

    def _setup_pre_festival_alarm(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        duration = create_time_span(minutes=self.pre_festival_duration)
        time_left_to_go = duration - time_since_started
        self._duration_alarm = alarms.add_alarm(self, time_left_to_go, self._pre_festival_alarm_callback)

    def _run(self):
        self._setup_pre_festival_alarm()
        services.get_event_manager().process_events_for_household(TestEvent.FestivalStarted, services.active_household())
        return DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE

    def resume(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        if time_since_started < create_time_span(minutes=self.pre_festival_duration):
            self._setup_pre_festival_alarm()
        else:
            self._try_and_start_festival(from_resume=True)

    def is_on_festival_street(self):
        street = services.current_street()
        return street is self.street

    def is_during_pre_festival(self):
        now = services.time_service().sim_now
        time_since_started = now - self._selected_time
        if time_since_started < create_time_span(minutes=self.pre_festival_duration):
            return True
        return False

    def create_calendar_entry(self):
        calendar_entry = super().create_calendar_entry()
        activity_info = None
        if self.calendar_activity_info is None:
            info = self.festival_dynamic_sign_info
            if not info:
                logger.error('Calendar Ui Info set to use Dynamic Sign Info on {}, but no Dynamic Sign Info is present.', self)
                return calendar_entry
            activity_info = info.activity_info
        else:
            activity_info = self.calendar_activity_info
        for activity in activity_info:
            with ProtocolBufferRollback(calendar_entry.festival_activities) as activity_msg:
                activity_msg.name = activity.activity_name
                if hasattr(activity, 'calendar_icon'):
                    activity_msg.icon = create_icon_info_msg(IconInfoData(activity.calendar_icon))
                else:
                    activity_msg.icon = create_icon_info_msg(IconInfoData(activity.icon))
                activity_msg.description = activity.activity_description
        calendar_entry.scoring_enabled = False
        lot_id = self.get_travel_lot_id()
        persistence_service = services.get_persistence_service()
        zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        if zone_id:
            calendar_entry.zone_id = zone_id
        return calendar_entry

    def get_calendar_start_time(self):
        return self._selected_time + create_time_span(minutes=self.pre_festival_duration)

    def get_calendar_end_time(self):
        return self._selected_time + create_time_span(minutes=self.fake_duration + self.pre_festival_duration)

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO, **setup_kwargs):
        success = super().schedule(resolver, specific_time, time_modifier, **setup_kwargs)
        if success and self.ui_display_type != DramaNodeUiDisplayType.NO_UI:
            services.calendar_service().mark_on_calendar(self)
        return success

    def load(self, drama_node_proto, schedule_alarm=True):
        success = super().load(drama_node_proto, schedule_alarm)
        if success and self.ui_display_type != DramaNodeUiDisplayType.NO_UI:
            services.calendar_service().mark_on_calendar(self)
        return success

    @classmethod
    def show_festival_info(cls):
        if cls.festival_dynamic_sign_info is None:
            return
        ui_info = cls.festival_dynamic_sign_info
        festival_info = UI_pb2.DynamicSignView()
        festival_info.drama_node_guid = cls.guid64
        festival_info.name = ui_info.festival_name
        lot_id = cls.get_travel_lot_id()
        persistence_service = services.get_persistence_service()
        zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        zone_protobuff = persistence_service.get_zone_proto_buff(zone_id)
        if zone_protobuff is not None:
            festival_info.venue = LocalizationHelperTuning.get_raw_text(zone_protobuff.name)
        festival_info.time = ui_info.festival_time
        festival_info.image = sims4.resources.get_protobuff_for_key(ui_info.display_image)
        festival_info.background_image = sims4.resources.get_protobuff_for_key(ui_info.background_image)
        festival_info.action_label = ui_info.travel_to_festival_text
        running_nodes = services.drama_scheduler_service().get_running_nodes_by_class(cls)
        active_sim_info = services.active_sim_info()
        if all(active_node.is_during_pre_festival() for active_node in running_nodes):
            festival_info.disabled_tooltip = ui_info.festival_not_started_tooltip
        elif any(active_node.is_on_festival_street() for active_node in running_nodes):
            festival_info.disabled_tooltip = ui_info.on_street_tooltip
        elif active_sim_info.is_in_travel_group():
            festival_info.disabled_tooltip = ui_info.on_vacation_tooltip
        for activity in ui_info.activity_info:
            with ProtocolBufferRollback(festival_info.activities) as activity_msg:
                activity_msg.name = activity.activity_name
                activity_msg.description = activity.activity_description
                activity_msg.icon = create_icon_info_msg(IconInfoData(activity.icon))
        distributor = Distributor.instance()
        distributor.add_op(active_sim_info, GenericProtocolBufferOp(Operation.DYNAMIC_SIGN_VIEW, festival_info))

    @flexmethod
    def get_destination_lot_id(cls, inst):
        inst_or_cls = cls if inst is None else inst
        return cls.get_travel_lot_id(reject_same_street=inst_or_cls.reject_same_street_travel)

    @flexmethod
    def get_travel_interaction(cls, inst):
        return FestivalDramaNode.GO_TO_FESTIVAL_INTERACTION
lock_instance_tunables(FestivalDramaNode, allow_during_work_hours=False)MajorOrganizationEventDisplayMixin = get_display_mixin(has_description=True, has_icon=True, has_tooltip=True, use_string_tokens=True, has_secondary_icon=True, export_modes=ExportModes.All, enabled_by_default=True)
class MajorOrganizationEventDramaNode(FestivalContestDramaNodeMixin, MajorOrganizationEventDisplayMixin, FestivalDramaNode):
    INSTANCE_TUNABLES = {'organization': TunableReference(description='\n            The organization for which this drama node is scheduling venue events.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='Organization'), 'location_name': TunableLocalizedString(description="\n            The string used to populate UI's location field in the \n            organization events panel.\n            ")}

    def _return_submissions(self) -> None:
        pass

    @classmethod
    def _verify_tuning_callback(cls):
        if cls._display_data.instance_display_name is None:
            logger.error('Organization Event Drama Nodes require an instance display name to be tuned, but ({}) has a None value.', cls)
        if cls._display_data.instance_display_description is None:
            logger.error('Display data from Drama Node ({}) is sent to UI, but                            has a display description of None value, which cannot be True.', cls)
        if not hasattr(cls.time_option, 'valid_time'):
            logger.error('Drama Node ({}) need a single time tuned in order to schedule,                          but does not. It will not schedule.', cls)

    def load(self, *args, **kwargs):
        if not super().load(*args, **kwargs):
            return False
        lot_id = self.get_travel_lot_id()
        zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        if zone_id is None:
            zone_id = 0
        org_service = services.organization_service()
        icon_info = IconInfoData(icon_resource=self._display_data.instance_display_icon)
        org_event_info = OrgEventInfo(drama_node=self, schedule=self._selected_time, fake_duration=self.fake_duration, icon_info=icon_info, name=self._display_data.instance_display_name(), description=self._display_data.instance_display_description(), location=self.location_name, zone_id=zone_id)
        org_service.add_festival_event_update(self.organization.guid64, org_event_info, self.uid, str(type(self)))
        return True

    def schedule(self, *args, **kwargs):
        success = super().schedule(*args, **kwargs)
        if success:
            lot_id = self.get_travel_lot_id()
            zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
            if zone_id is None:
                zone_id = 0
            icon_info = IconInfoData(icon_resource=self._display_data.instance_display_icon)
            org_event_info = OrgEventInfo(drama_node=self, schedule=self._selected_time, fake_duration=self.fake_duration, icon_info=icon_info, name=self._display_data.instance_display_name(), description=self._display_data.instance_display_description(), location=self.location_name, zone_id=zone_id)
            services.organization_service().add_festival_event_update(self.organization.guid64, org_event_info, self.uid, str(type(self)))
        return success

class ShowFestivalInfoSuperInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'festival_drama_node': TunableReference(description='\n            The festival drama node whose info we will show.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions=('FestivalDramaNode',), tuning_group=GroupNames.CORE)}

    def _run_interaction_gen(self, timeline):
        self.festival_drama_node.show_festival_info()
