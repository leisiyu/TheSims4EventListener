from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import Optional
    from scheduling import Timelinefrom _collections import defaultdictimport itertoolsimport mathimport element_utilsfrom protocolbuffers import GameplaySaveData_pb2from date_and_time import DateAndTime, TimeSpan, DAYS_PER_WEEK, create_date_and_time, create_time_span, sim_ticks_per_weekfrom distributor.rollback import ProtocolBufferRollbackfrom drama_scheduler.drama_node import DramaNodeScoringBucket, CooldownOption, CooldownGroup, NODE_COOLDOWN, BaseDramaNode, DramaNodeRunOutcome, WeeklySchedulingGroupfrom event_testing.resolver import SingleSimResolver, DataResolverfrom gsi_handlers.drama_handlers import is_scoring_archive_enabled, GSIDramaScoringData, archive_drama_scheduler_scoring, GSIRejectedDramaNodeScoringData, GSIDramaNodeScoringData, is_drama_node_log_enabled, log_drama_node_scoring, DramaNodeLogActionsfrom scheduler_utils import TunableDayAvailabilityfrom sims4 import randomfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, TunableVariant, Tunable, TunableRange, TunableSetfrom sims4.utils import classpropertyfrom venues.venue_constants import ZoneDirectorRequestTypeimport build_buyimport date_and_timeimport elementsimport enumimport id_generatorimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('DramaScheduleService', default_owner='jjacobson')
class NodeSelectionOption(enum.Int):
    STATIC_AMOUNT = ...
    BASED_ON_HOUSEHOLD = ...

class DramaScheduleService(Service):
    VENUE_BUCKET_DAYS = TunableDayAvailability()
    STARTUP_BUCKETS = TunableSet(description="\n        PLEASE CHECK WITH YOUR GPE PARTNER BEFORE ADDING TO THIS SET!\n        \n        A set of buckets that we want to schedule on initial startup.  We will\n        run an initial scoring of nodes within these buckets the first time\n        a game is loaded.  This should mainly be used if there is a need to\n        have nodes schedule immediately when the player begins playing and they\n        cannot wait until the next scheduling ping.\n        \n        Ex. Auditions for the acting career are represented as Drama Nodes that\n        the player can sign up for.  When the player begins playing the game\n        they shouldn't have to wait until the next day for auditions to be\n        available for them to sign up for.\n        ", tunable=TunableEnumEntry(description='\n            The bucket that we are going to score this node in.\n            ', tunable_type=DramaNodeScoringBucket, default=DramaNodeScoringBucket.DEFAULT))
    BUCKET_SCORING_RULES = TunableMapping(description='\n        A mapping between the different possible scoring buckets, and rules\n        about scheduling nodes in that bucket.\n        ', key_type=TunableEnumEntry(description='\n            The bucket that we are going to score on startup.\n            ', tunable_type=DramaNodeScoringBucket, default=DramaNodeScoringBucket.DEFAULT), value_type=TunableTuple(description='\n            Rules about scheduling this drama node.\n            ', days=TunableDayAvailability(), score_if_no_nodes_are_scheduled=Tunable(description='\n                If checked then if no drama nodes are scheduled from this\n                bucket then we will try and score and schedule this bucket\n                even if we are not expected to score nodes on this day.\n                ', tunable_type=bool, default=False), number_to_schedule=TunableVariant(description='\n                How many actual nodes should we schedule from this bucket.\n                ', based_on_household=TunableTuple(description='\n                    Select the number of nodes based on the number of Sims in\n                    the active household.\n                    ', locked_args={'option': NodeSelectionOption.BASED_ON_HOUSEHOLD}), fixed_amount=TunableTuple(description='\n                    Select the number of nodes based on a static number.\n                    ', number_of_nodes=TunableRange(description='\n                        The number of nodes that we will always try and\n                        schedule from this bucket.\n                        ', tunable_type=int, default=1, minimum=0), locked_args={'option': NodeSelectionOption.STATIC_AMOUNT})), refresh_nodes_on_scheduling=Tunable(description='\n                If checked, any existing scheduled nodes for this \n                particular scoring bucket will be canceled before scheduling\n                new nodes.\n                ', tunable_type=bool, default=False)))
    WEEKLY_SCHEDULING_RULES = TunableMapping(description='\n        A mapping between the different possible weekly scheduling groups, and rules\n        about scheduling nodes in that group.\n        ', key_type=TunableEnumEntry(description='\n            The group that we are going to put the weekly scheduled nodes in.\n            ', tunable_type=WeeklySchedulingGroup, default=WeeklySchedulingGroup.DEFAULT), value_type=TunableTuple(description='\n            Rules about scheduling this drama node weekly.\n            ', weeks_to_schedule_in_advance=TunableRange(description='\n                Number of weeks we want to be scheduled in advance.\n                For example, if weeks_to_schedule_in_advance is 4, this week is week 7, latest scheduled week is week X,\n                weeks_gap is 1. Then when we run the scheduling code, we will need to make sure:\n                weeks_to_schedule_in_advance <= latest scheduled week number - this week number + weeks_gap\n                (4 <= X - 7 + 1)\n                Otherwise we will keep scheduling until X is large enough to satisfy the inequation.\n                ', tunable_type=int, default=1, minimum=1), weeks_gap=TunableRange(description='\n                Week gaps for scheduling.\n                For example if this is set to 1, we will schedule one node per 1 week; \n                if this is 2, we will schedule one node per 2 weeks... and so on. \n                ', tunable_type=int, default=1, minimum=1)))
    SCORING_TIME = 3
    WEEKLY_SCHEDULING_TIME = 3

    def __init__(self):
        self._active_nodes = {}
        self._scheduled_nodes = {}
        self._cooldown_nodes = {}
        self._cooldown_groups = {}
        self._drama_nodes_on_permanent_cooldown = set()
        self._drama_node_groups_on_permanent_cooldown = set()
        self._has_started_up = False
        self._processor = None
        self._processor_weekly_schedule = None
        self._enabled = True
        self._startup_buckets_used = set()
        self._grouped_weekly_nodes = None
        self._processing_node = None
        self._process_cooldown_handle = None

    def __iter__(self):
        return iter(self._scheduled_nodes.values())

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_DRAMA_SCHEDULE_SERVICE

    def set_enabled_state(self, enabled):
        self._enabled = enabled

    def start(self):
        self._setup_scoring_alarm()
        self._setup_weekly_schedule_alarm()

    def stop(self):
        if self._processor is not None:
            self._processor.trigger_hard_stop()
            self._processor = None
        if self._processor_weekly_schedule is not None:
            self._processor_weekly_schedule.trigger_hard_stop()
            self._processor_weekly_schedule = None
        for node in self._active_nodes.values():
            node.cleanup(from_service_stop=True)
        self._active_nodes.clear()
        for node in self._scheduled_nodes.values():
            node.cleanup(from_service_stop=True)
        self._scheduled_nodes.clear()
        self._processing_node = None
        if self._process_cooldown_handle is not None:
            self._process_cooldown_handle.trigger_hard_stop()
            self._process_cooldown_handle = None

    def all_nodes_gen(self):
        for node in itertools.chain(self.active_nodes_gen(), self.scheduled_nodes_gen()):
            yield node
        if self._processing_node is not None:
            yield self._processing_node

    def active_nodes_gen(self):
        for node in self._active_nodes.values():
            yield node

    def scheduled_nodes_gen(self):
        yield from self._scheduled_nodes.values()

    @property
    def processing_node(self):
        return self._processing_node

    def start_cooldown(self, drama_node):
        if drama_node.cooldown_data is None:
            return
        if drama_node.cooldown.duration is None:
            if drama_node.cooldown_data.cooldown_type == NODE_COOLDOWN:
                self._drama_nodes_on_permanent_cooldown.add(drama_node.guid64)
            else:
                self._drama_node_groups_on_permanent_cooldown.add(drama_node.cooldown_data.group)
            return
        now = services.time_service().sim_now
        if drama_node.cooldown_data.cooldown_type == NODE_COOLDOWN:
            self._cooldown_nodes[drama_node] = now
        else:
            self._cooldown_groups[drama_node.cooldown_data.group] = now
        self._setup_update_cooldowns_alarm()

    def get_active_node_by_uid(self, drama_node_uid):
        return self._active_nodes.get(drama_node_uid)

    def get_scheduled_node_by_uid(self, drama_node_uid):
        return self._scheduled_nodes.get(drama_node_uid)

    def get_running_nodes_by_class(self, drama_node_class):
        return [node for node in self._active_nodes.values() if type(node) is drama_node_class]

    def get_running_nodes_by_drama_node_type(self, drama_node_type):
        return [node for node in self._active_nodes.values() if node.drama_node_type is drama_node_type]

    def get_scheduled_nodes_by_class(self, drama_node_class):
        return [node for node in self._scheduled_nodes.values() if type(node) is drama_node_class]

    def get_scheduled_nodes_by_drama_node_type(self, drama_node_type):
        return [node for node in self._scheduled_nodes.values() if node.drama_node_type is drama_node_type]

    def _update_cooldowns(self, timeline:'Timeline'):
        now = services.time_service().sim_now
        for (drama_node, time) in tuple(self._cooldown_nodes.items()):
            cooldown = drama_node.cooldown
            if not cooldown is None:
                if cooldown.duration is None:
                    pass
                else:
                    cooldown_length = date_and_time.create_time_span(hours=cooldown.duration)
                    time += cooldown_length
                    if time <= now:
                        del self._cooldown_nodes[drama_node]
        for (cooldown_group, time) in tuple(self._cooldown_groups.items()):
            cooldown_length = date_and_time.create_time_span(hours=BaseDramaNode.COOLDOWN_GROUPS[cooldown_group].duration)
            time += cooldown_length
            if time <= now:
                del self._cooldown_groups[cooldown_group]
        self._setup_update_cooldowns_alarm()

    def _calculate_shortest_cooldown_span(self) -> 'Optional[TimeSpan]':
        now = services.time_service().sim_now
        shortest_cooldown_span = None
        for (drama_node, time) in tuple(self._cooldown_nodes.items()):
            cooldown = drama_node.cooldown
            if not cooldown is None:
                if cooldown.duration is None:
                    pass
                else:
                    cooldown_length = date_and_time.create_time_span(hours=cooldown.duration)
                    time += cooldown_length
                    cooldown_span = time - now
                    if not shortest_cooldown_span is None:
                        if cooldown_span < shortest_cooldown_span:
                            shortest_cooldown_span = cooldown_span
                    shortest_cooldown_span = cooldown_span
        for (cooldown_group, time) in tuple(self._cooldown_groups.items()):
            cooldown_length = date_and_time.create_time_span(hours=BaseDramaNode.COOLDOWN_GROUPS[cooldown_group].duration)
            time += cooldown_length
            cooldown_span = time - now
            if not shortest_cooldown_span is None:
                if cooldown_span < shortest_cooldown_span:
                    shortest_cooldown_span = cooldown_span
            shortest_cooldown_span = cooldown_span
        return shortest_cooldown_span

    def _setup_update_cooldowns_alarm(self) -> 'None':
        timeline = services.time_service().sim_timeline
        shortest_cooldown_span = self._calculate_shortest_cooldown_span()
        if self._process_cooldown_handle is not None:
            self._process_cooldown_handle.trigger_hard_stop()
            self._process_cooldown_handle = None
        if shortest_cooldown_span is None:
            return
        update_cooldown_span = services.time_service().sim_now + shortest_cooldown_span
        element = element_utils.build_element(self._update_cooldowns)
        self._process_cooldown_handle = timeline.schedule(element, when=update_cooldown_span)

    def on_situation_creation_during_zone_spin_up(self) -> 'None':
        for node in tuple(self._active_nodes.values()):
            node.on_situation_creation_during_zone_spin_up()

    def schedule_weekly_nodes_on_startup(self):
        self._grouped_weekly_nodes = defaultdict(list)
        drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
        for drama_node in drama_node_manager.types.values():
            if drama_node.weekly_scheduling_rules is None:
                pass
            else:
                self._grouped_weekly_nodes[drama_node.weekly_scheduling_rules.scheduling_group].append(drama_node)
        for nodes_list in self._grouped_weekly_nodes.values():
            nodes_list.sort(key=lambda node: node.weekly_scheduling_rules.weight, reverse=True)
        for _ in self._schedule_weekly_nodes_gen():
            pass

    def _schedule_weekly_nodes_gen(self, timeline=None):
        drama_scheduler = services.drama_scheduler_service()
        now = services.time_service().sim_now
        for (scheduling_group, nodes) in self._grouped_weekly_nodes.items():
            if not nodes:
                pass
            else:
                rules = self.WEEKLY_SCHEDULING_RULES[scheduling_group]
                nodes_scheduled = [node_inst for node_inst in self._scheduled_nodes.values() if node_inst.weekly_scheduling_rules is not None and node_inst.weekly_scheduling_rules.scheduling_group == scheduling_group]
                latest_selected_time = max(node.selected_time for node in nodes_scheduled) if nodes_scheduled else None
                while True:
                    while latest_selected_time is None or rules.weeks_to_schedule_in_advance > latest_selected_time.week() - now.week() + rules.weeks_gap:
                        resolver = DataResolver(None)
                        latest_selected_time = latest_selected_time.start_of_week() + TimeSpan(sim_ticks_per_week()*rules.weeks_gap) if latest_selected_time is not None else now.start_of_week()
                        index_of_nodes = int(latest_selected_time.week()/rules.weeks_gap)
                        actual_index_of_nodes = index_of_nodes % len(nodes)
                        drama_node = nodes[actual_index_of_nodes]
                        week_time = drama_node.get_week_time_for_weekly_schedule()
                        if week_time is None:
                            pass
                        else:
                            selected_time = latest_selected_time + TimeSpan(week_time.absolute_ticks())
                            if selected_time < now:
                                pass
                            else:
                                drama_scheduler.schedule_node(drama_node, resolver, specific_time=selected_time)
                                if timeline is not None:
                                    yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))

    def schedule_node(self, drama_node, resolver, specific_time=None, drama_inst=None, setup_kwargs={}, **constructor_kwargs):
        if drama_inst is not None:
            drama_node_inst = drama_inst
        else:
            uid = id_generator.generate_object_id()
            drama_node_inst = drama_node(uid, **constructor_kwargs)
        if self._is_node_on_cooldown(drama_node):
            return
        if not drama_node_inst.schedule(resolver, specific_time=specific_time, **setup_kwargs):
            return
        if is_drama_node_log_enabled():
            log_drama_node_scoring(drama_node_inst, DramaNodeLogActions.SCHEDULED)
        self._scheduled_nodes[drama_node_inst.uid] = drama_node_inst
        drama_node_inst.on_scheduled()
        if drama_node.cooldown is not None and drama_node.cooldown.cooldown_option == CooldownOption.ON_SCHEDULE:
            self.start_cooldown(drama_node)
        return drama_node_inst.uid

    def cancel_scheduled_nodes_with_types(self, drama_nodes):
        node_guids_to_cancel = set(drama_node_type.guid64 for drama_node_type in drama_nodes)
        for drama_node in list(self._scheduled_nodes.values()):
            if drama_node.guid64 not in node_guids_to_cancel:
                pass
            else:
                if is_drama_node_log_enabled():
                    log_drama_node_scoring(drama_node, DramaNodeLogActions.CANCELED, '{} canceled manually.', drama_node)
                drama_node.cleanup()
                del self._scheduled_nodes[drama_node.uid]

    def cancel_scheduled_node(self, drama_node_uid):
        if drama_node_uid not in self._scheduled_nodes:
            logger.error('Trying to cancel a drama node that is not scheduled. Node id: {}', drama_node_uid)
            return False
        drama_node = self._scheduled_nodes[drama_node_uid]
        if is_drama_node_log_enabled():
            log_drama_node_scoring(drama_node, DramaNodeLogActions.CANCELED, '{} canceled manually.', drama_node)
        drama_node.cleanup()
        del self._scheduled_nodes[drama_node.uid]
        return True

    def run_node(self, drama_node, resolver, **kwargs):
        uid = id_generator.generate_object_id()
        drama_node_inst = drama_node(uid)
        if not drama_node_inst.setup(resolver, **kwargs):
            return
        drama_node_inst.debug_set_selected_time(services.time_service().sim_now)
        self._processing_node = drama_node_inst
        result = drama_node_inst.run()
        self._processing_node = None
        if result == DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE:
            self._active_nodes[uid] = drama_node_inst
        elif result == DramaNodeRunOutcome.RESCHEDULED:
            self._scheduled_nodes[uid] = drama_node_inst
        elif is_drama_node_log_enabled():
            log_drama_node_scoring(drama_node_inst, DramaNodeLogActions.COMPLETED)
        return drama_node_inst.uid

    def complete_node(self, uid, from_shutdown=False):
        if uid not in self._active_nodes:
            return
        node_inst = self._active_nodes[uid]
        if is_drama_node_log_enabled():
            log_drama_node_scoring(node_inst, DramaNodeLogActions.COMPLETED)
        node_inst.complete(from_shutdown=from_shutdown)
        node_inst.cleanup()
        del self._active_nodes[uid]

    def _run_node(self, uid):
        if uid not in self._scheduled_nodes:
            logger.error('Trying to run a drama node with uid {} that is not scheduled.', uid)
            return
        drama_node_inst = self._scheduled_nodes[uid]
        del self._scheduled_nodes[uid]
        if not self._enabled:
            drama_node_inst.cleanup()
            if is_drama_node_log_enabled():
                log_drama_node_scoring(drama_node_inst, DramaNodeLogActions.CANCELED, 'Drama Scheduler is disabled')
            return
        if drama_node_inst.cooldown is not None and drama_node_inst.cooldown.cooldown_option != CooldownOption.ON_SCHEDULE and self._is_node_on_cooldown(type(drama_node_inst)):
            drama_node_inst.cleanup()
            if is_drama_node_log_enabled():
                log_drama_node_scoring(drama_node_inst, DramaNodeLogActions.CANCELED, '{} is currently on cooldown', drama_node_inst)
            return
        self._processing_node = drama_node_inst
        result = drama_node_inst.run()
        self._processing_node = None
        if result == DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE:
            self._active_nodes[uid] = drama_node_inst
        elif result == DramaNodeRunOutcome.RESCHEDULED:
            self._scheduled_nodes[uid] = drama_node_inst
        else:
            if is_drama_node_log_enabled():
                log_drama_node_scoring(drama_node_inst, DramaNodeLogActions.COMPLETED)
            drama_node_inst.cleanup()

    def save(self, save_slot_data=None, **kwargs):
        if not self._has_started_up:
            return
        drama_schedule_proto = GameplaySaveData_pb2.PersistableDramaScheduleService()
        for drama_node_inst in self._scheduled_nodes.values():
            with ProtocolBufferRollback(drama_schedule_proto.drama_nodes) as drama_node_msg:
                drama_node_inst.save(drama_node_msg)
        for drama_node_inst in self._active_nodes.values():
            if drama_node_inst.persist_when_active:
                with ProtocolBufferRollback(drama_schedule_proto.running_nodes) as drama_node_msg:
                    drama_node_inst.save(drama_node_msg)
        for (drama_node, time) in self._cooldown_nodes.items():
            with ProtocolBufferRollback(drama_schedule_proto.cooldown_nodes) as cooldown_node:
                cooldown_node.node_type = drama_node.guid64
                cooldown_node.completed_time = time.absolute_ticks()
        for (group, time) in self._cooldown_groups.items():
            with ProtocolBufferRollback(drama_schedule_proto.cooldown_groups) as cooldown_group:
                cooldown_group.group = group
                cooldown_group.completed_time = time.absolute_ticks()
        drama_schedule_proto.drama_nodes_on_permanent_cooldown.extend(self._drama_nodes_on_permanent_cooldown)
        drama_schedule_proto.cooldown_groups_on_permanent_cooldown.extend(self._drama_node_groups_on_permanent_cooldown)
        drama_schedule_proto.startup_drama_node_buckets_used.extend(self._startup_buckets_used)
        save_slot_data.gameplay_data.drama_schedule_service = drama_schedule_proto

    def on_all_households_and_sim_infos_loaded(self, client):
        self._has_started_up = True
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
        for drama_proto in save_slot_data.gameplay_data.drama_schedule_service.drama_nodes:
            node_type = drama_node_manager.get(drama_proto.node_type)
            if node_type is None:
                pass
            else:
                drama_node_inst = node_type()
                if drama_node_inst.load(drama_proto):
                    self._scheduled_nodes[drama_node_inst.uid] = drama_node_inst
                else:
                    drama_node_inst.cleanup()
        for drama_proto in save_slot_data.gameplay_data.drama_schedule_service.running_nodes:
            node_type = drama_node_manager.get(drama_proto.node_type)
            if node_type is None:
                pass
            else:
                drama_node_inst = node_type()
                if drama_node_inst.load(drama_proto, schedule_alarm=False):
                    self._active_nodes[drama_node_inst.uid] = drama_node_inst
                    drama_node_inst.resume()
                else:
                    drama_node_inst.cleanup()
        for cooldown_proto in save_slot_data.gameplay_data.drama_schedule_service.cooldown_nodes:
            node_type = drama_node_manager.get(cooldown_proto.node_type)
            if node_type is None:
                pass
            else:
                time = DateAndTime(cooldown_proto.completed_time)
                self._cooldown_nodes[node_type] = time
        for cooldown_group_proto in save_slot_data.gameplay_data.drama_schedule_service.cooldown_groups:
            time = DateAndTime(cooldown_proto.completed_time)
            self._cooldown_groups[CooldownGroup(cooldown_group_proto.group)] = time
        self._drama_nodes_on_permanent_cooldown.update(save_slot_data.gameplay_data.drama_schedule_service.drama_nodes_on_permanent_cooldown)
        self._drama_node_groups_on_permanent_cooldown.update(CooldownGroup(cooldown_group) for cooldown_group in save_slot_data.gameplay_data.drama_schedule_service.cooldown_groups_on_permanent_cooldown)
        self._startup_buckets_used = {DramaNodeScoringBucket(bucket) for bucket in save_slot_data.gameplay_data.drama_schedule_service.startup_drama_node_buckets_used}

    def _process_weekly_schedule_gen(self, timeline):
        try:
            teardown = False
            yield from self._schedule_weekly_nodes_gen(timeline)
        except GeneratorExit:
            teardown = True
            raise
        except Exception as exception:
            logger.exception('Exception while scheduling weekly DramaNodes: ', exc=exception, level=sims4.log.LEVEL_ERROR)
        finally:
            if not teardown:
                self._setup_weekly_schedule_alarm()

    def _setup_weekly_schedule_alarm(self):
        day_time = date_and_time.create_date_and_time(hours=self.WEEKLY_SCHEDULING_TIME)
        now = services.time_service().sim_now
        time_delay = now.time_to_week_time(day_time)
        if time_delay.in_ticks() == 0:
            time_delay = date_and_time.create_time_span(days=DAYS_PER_WEEK)
        schedule_time = now + time_delay
        sim_timeline = services.time_service().sim_timeline
        self._processor_weekly_schedule = sim_timeline.schedule(elements.GeneratorElement(self._process_weekly_schedule_gen), when=schedule_time)

    def _setup_scoring_alarm(self):
        day_time = date_and_time.create_date_and_time(hours=self.SCORING_TIME)
        now = services.time_service().sim_now
        time_delay = now.time_till_next_day_time(day_time)
        if time_delay.in_ticks() == 0:
            time_delay = date_and_time.create_time_span(days=1)
        schedule_time = now + time_delay
        sim_timeline = services.time_service().sim_timeline
        self._processor = sim_timeline.schedule(elements.GeneratorElement(self._process_scoring_gen), when=schedule_time)

    def _is_node_on_cooldown(self, drama_node):
        if drama_node.cooldown_data is None:
            return False
        if drama_node.cooldown_data.cooldown_type == NODE_COOLDOWN:
            return drama_node in self._cooldown_nodes or drama_node.guid64 in self._drama_nodes_on_permanent_cooldown
        else:
            return drama_node.cooldown_data.group in self._cooldown_groups or drama_node.cooldown_data.group in self._drama_node_groups_on_permanent_cooldown

    def score_and_schedule_nodes_gen(self, nodes_to_score, nodes_to_schedule, specific_time=None, time_modifier=TimeSpan.ZERO, timeline=None, gsi_data=None, resolver_resolver=None, **additional_drama_node_kwargs):
        active_household = services.active_household()
        if active_household is None:
            return
        self._update_cooldowns(timeline)
        resolver_resolver = SingleSimResolver
        sim_resolvers = tuple(resolver_resolver(sim_info) for sim_info in active_household.sim_info_gen())
        possible_nodes = []
        chosen_node_types = set()
        for drama_node in nodes_to_score:
            if not self._is_node_on_cooldown(drama_node) or gsi_data is not None:
                gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(drama_node, '{} is on cooldown.', drama_node))
                for resolver in sim_resolvers:
                    uid = id_generator.generate_object_id()
                    drama_node_inst = drama_node(uid)
                    result = drama_node_inst.setup(resolver, gsi_data=gsi_data, for_scoring=True, **additional_drama_node_kwargs)
                    if timeline is not None:
                        yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))
                    if not result:
                        drama_node_inst.cleanup()
                    else:
                        score = drama_node_inst.score()
                        if score == 0:
                            if gsi_data is not None:
                                gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(drama_node, 'Scoring generated a score of 0.', score=score, receiver=drama_node_inst.get_receiver_sim_info(), sender=drama_node_inst.get_sender_sim_info()))
                            drama_node_inst.cleanup()
                        else:
                            if gsi_data is not None:
                                gsi_data.potential_nodes.append(GSIDramaNodeScoringData(drama_node, score, drama_node_inst.get_score_details(), drama_node_inst.get_receiver_sim_info(), drama_node_inst.get_sender_sim_info()))
                            possible_nodes.append((score, drama_node_inst))
        if not (resolver_resolver is None and possible_nodes):
            return
        while nodes_to_schedule > 0 and possible_nodes:
            chosen_node = random.pop_weighted(possible_nodes)
            if type(chosen_node) in chosen_node_types:
                if gsi_data is not None:
                    gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(drama_node_inst), 'Could not schedule drama node because a drama node of this type was already scheduled.', score=chosen_node.score(), score_details=chosen_node.get_score_details(), receiver=chosen_node.get_receiver_sim_info(), sender=chosen_node.get_sender_sim_info()))
                chosen_node.cleanup()
            else:
                chosen_node.finish_deferred_setup()
                result = chosen_node.schedule(None, specific_time=specific_time, time_modifier=time_modifier)
                if timeline is not None:
                    yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))
                if not result:
                    if gsi_data is not None:
                        error_message = 'Could not schedule drama node: '
                        if result.reason is not None:
                            error_message += result.reason
                        else:
                            error_message += 'Unknown reason.'
                        error_message = error_message.replace('{', '').replace('}', '')
                        gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(chosen_node), error_message, score=chosen_node.score(), score_details=chosen_node.get_score_details(), receiver=chosen_node.get_receiver_sim_info(), sender=chosen_node.get_sender_sim_info()))
                    chosen_node.cleanup()
                else:
                    if gsi_data is not None:
                        gsi_data.chosen_nodes.append(GSIDramaNodeScoringData(type(chosen_node), chosen_node.score(), chosen_node.get_score_details(), chosen_node.get_receiver_sim_info(), chosen_node.get_sender_sim_info()))
                    self._scheduled_nodes[chosen_node.uid] = chosen_node
                    if chosen_node.cooldown is not None and chosen_node.cooldown.cooldown_option == CooldownOption.ON_SCHEDULE:
                        self.start_cooldown(type(chosen_node))
                    if is_drama_node_log_enabled():
                        log_drama_node_scoring(chosen_node, DramaNodeLogActions.SCHEDULED)
                    nodes_to_schedule -= 1
                    chosen_node_types.add(type(chosen_node))
        for (score, drama_node_inst) in possible_nodes:
            drama_node_inst.cleanup()

    def _check_day(self, current_day, days):
        for (day, day_enabled) in days.items():
            if current_day == day:
                return day_enabled
        logger.error('Day {} not found within day structure {} when trying to check of the day was valid.', current_day, days)
        return False

    def _score_and_schedule_drama_nodes_gen(self, timeline, from_zone_spin_up=False):
        active_household = services.active_household()
        if active_household is None:
            return
        current_time = services.time_service().sim_now
        current_day = current_time.day()
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        for neighborhood_proto in services.get_persistence_service().get_neighborhoods_proto_buf_gen():
            for lot_owner_info in neighborhood_proto.lots:
                zone_id = lot_owner_info.zone_instance_id
                if not zone_id:
                    pass
                else:
                    venue_tuning = venue_manager.get(build_buy.get_current_venue(zone_id))
                    if venue_tuning is None:
                        pass
                    elif not venue_tuning.drama_node_events:
                        pass
                    else:
                        if is_scoring_archive_enabled():
                            gsi_data = GSIDramaScoringData()
                            gsi_data.bucket = 'Venue'
                        else:
                            gsi_data = None
                        yield from self.score_and_schedule_nodes_gen(venue_tuning.drama_node_events, venue_tuning.drama_node_events_to_schedule, timeline=timeline, gsi_data=gsi_data, zone_id=zone_id)
                        if gsi_data is not None:
                            archive_drama_scheduler_scoring(gsi_data)
                        if timeline is not None:
                            yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))
        bucketted_nodes = defaultdict(list)
        drama_node_manager = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
        for drama_node in drama_node_manager.types.values():
            if drama_node.scoring is None:
                pass
            else:
                bucketted_nodes[drama_node.scoring.bucket].append(drama_node)
        buckets_to_score = []
        if from_zone_spin_up or self._check_day(current_day, self.VENUE_BUCKET_DAYS) and from_zone_spin_up:
            buckets = self.STARTUP_BUCKETS - self._startup_buckets_used
            if current_time < create_date_and_time(days=int(current_time.absolute_days()), hours=self.SCORING_TIME):
                day_modifier = -1
            else:
                day_modifier = 0
            for bucket in buckets:
                if not bucketted_nodes[bucket]:
                    pass
                else:
                    self._startup_buckets_used.add(bucket)
                    rules = self.BUCKET_SCORING_RULES[bucket]
                    smallest_day_modification = None
                    for (day, day_enabled) in rules.days.items():
                        if not day_enabled:
                            pass
                        else:
                            potential_modification = current_day + day_modifier - day
                            potential_modification += DAYS_PER_WEEK
                            if potential_modification < 0 and (smallest_day_modification is None or potential_modification < smallest_day_modification):
                                smallest_day_modification = potential_modification
                    if smallest_day_modification is None:
                        time_modification = TimeSpan.ZERO
                    else:
                        time_modification = TimeSpan(current_time.absolute_ticks()) - create_time_span(days=int(current_time.absolute_days()) - smallest_day_modification + day_modifier, hours=self.SCORING_TIME)
                    buckets_to_score.append((bucket, rules, time_modification))
        else:
            for (bucket_type, rules) in self.BUCKET_SCORING_RULES.items():
                valid_day = self._check_day(current_day, rules.days)
                for drama_node in self._scheduled_nodes.values():
                    if drama_node.scoring is None:
                        pass
                    elif drama_node.scoring.bucket == bucket_type:
                        break
                valid_day = True
                if valid_day or rules.score_if_no_nodes_are_scheduled and valid_day:
                    buckets_to_score.append((bucket_type, rules, TimeSpan.ZERO))
        for (bucket_type, rules, time_modifier) in buckets_to_score:
            if is_scoring_archive_enabled():
                gsi_data = GSIDramaScoringData()
                gsi_data.bucket = bucket_type
            else:
                gsi_data = None
            if rules.number_to_schedule.option == NodeSelectionOption.BASED_ON_HOUSEHOLD:
                nodes_to_schedule = 1 + math.floor(len(active_household)/2)
            elif rules.number_to_schedule.option == NodeSelectionOption.STATIC_AMOUNT:
                nodes_to_schedule = rules.number_to_schedule.number_of_nodes
            else:
                logger.error('Trying to determine how many nodes to run with invalid option {}', rules.number_to_schedule.option)
                if gsi_data is not None:
                    archive_drama_scheduler_scoring(gsi_data)
                    if nodes_to_schedule == 0:
                        if gsi_data is not None:
                            archive_drama_scheduler_scoring(gsi_data)
                            for node in list(self._scheduled_nodes.values()):
                                if not node.scoring is not None or node.scoring.bucket == bucket_type:
                                    self.cancel_scheduled_node(node.uid)
                            yield from self.score_and_schedule_nodes_gen(bucketted_nodes[bucket_type], nodes_to_schedule, time_modifier=time_modifier, timeline=timeline, gsi_data=gsi_data)
                            if not rules.refresh_nodes_on_scheduling or gsi_data is not None:
                                archive_drama_scheduler_scoring(gsi_data)
                            if timeline is not None:
                                yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))
                    else:
                        gsi_data.nodes_to_schedule = nodes_to_schedule
                    for node in list(self._scheduled_nodes.values()):
                        if not node.scoring is not None or node.scoring.bucket == bucket_type:
                            self.cancel_scheduled_node(node.uid)
                    yield from self.score_and_schedule_nodes_gen(bucketted_nodes[bucket_type], nodes_to_schedule, time_modifier=time_modifier, timeline=timeline, gsi_data=gsi_data)
                    if not rules.refresh_nodes_on_scheduling or gsi_data is not None:
                        archive_drama_scheduler_scoring(gsi_data)
                    if timeline is not None:
                        yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))
            if nodes_to_schedule == 0:
                if gsi_data is not None:
                    archive_drama_scheduler_scoring(gsi_data)
                    for node in list(self._scheduled_nodes.values()):
                        if not node.scoring is not None or node.scoring.bucket == bucket_type:
                            self.cancel_scheduled_node(node.uid)
                    yield from self.score_and_schedule_nodes_gen(bucketted_nodes[bucket_type], nodes_to_schedule, time_modifier=time_modifier, timeline=timeline, gsi_data=gsi_data)
                    if not rules.refresh_nodes_on_scheduling or gsi_data is not None:
                        archive_drama_scheduler_scoring(gsi_data)
                    if timeline is not None:
                        yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))
            else:
                gsi_data.nodes_to_schedule = nodes_to_schedule
            for node in list(self._scheduled_nodes.values()):
                if not node.scoring is not None or node.scoring.bucket == bucket_type:
                    self.cancel_scheduled_node(node.uid)
            yield from self.score_and_schedule_nodes_gen(bucketted_nodes[bucket_type], nodes_to_schedule, time_modifier=time_modifier, timeline=timeline, gsi_data=gsi_data)
            if not rules.refresh_nodes_on_scheduling or gsi_data is not None:
                archive_drama_scheduler_scoring(gsi_data)
            if timeline is not None:
                yield timeline.run_child(elements.SleepElement(date_and_time.TimeSpan(0)))

    def _process_scoring_gen(self, timeline):
        try:
            teardown = False
            yield from self._score_and_schedule_drama_nodes_gen(timeline)
        except GeneratorExit:
            teardown = True
            raise
        except Exception as exception:
            logger.exception('Exception while scoring DramaNodes: ', exc=exception, level=sims4.log.LEVEL_ERROR)
        finally:
            if not teardown:
                self._setup_scoring_alarm()

    def make_zone_director_requests(self):
        for drama_node in self._active_nodes.values():
            if drama_node.zone_director_override is None:
                pass
            else:
                services.venue_service().request_zone_director(drama_node.zone_director_override(), ZoneDirectorRequestType.DRAMA_SCHEDULER)

    def schedule_scorable_nodes_on_startup(self):
        for _ in self._score_and_schedule_drama_nodes_gen(None, from_zone_spin_up=True):
            pass

    def add_cleanup_callback(self, uid, func_callback):
        node_inst = self.get_scheduled_node_by_uid(uid)
        if node_inst is None:
            node_inst = self.get_active_node_by_uid(uid)
        if node_inst is None:
            return
        node_inst.add_callback_on_cleanup_func(func_callback)

    def add_complete_callback(self, uid, func_callback):
        node_inst = self.get_scheduled_node_by_uid(uid)
        if node_inst is None:
            node_inst = self.get_active_node_by_uid(uid)
        if node_inst is None:
            return
        node_inst.add_callback_on_complete_func(func_callback)
