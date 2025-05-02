from __future__ import annotationsimport alarmsimport servicesimport sims4from date_and_time import DAYS_PER_WEEK, DateAndTime, create_date_and_time, create_time_span, TimeSpanfrom drama_scheduler.drama_scheduler import DramaScheduleServicefrom event_testing.resolver import DataResolverfrom lunar_cycle.lunar_cycle_service import phase_change_time_for_dayfrom lunar_cycle.lunar_cycle_tuning import LunarCycleTuningfrom math import ceilfrom persistence_error_types import ErrorCodesfrom sims4.service_manager import Servicefrom lunar_cycle.lunar_cycle_enums import LunarCycleLengthOption, LunarPhaseLockedOptionfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from lunar_cycle.lunar_cycle_enums import LunarPhaseType
    from typing import Generator, List, Optional, Tuplefrom _collections import defaultdictlogger = sims4.log.Logger('Lunar Events Service', default_owner='cparrish')
class LunarCycleEvents:

    def __init__(self, phase_length:'int'):
        self._phase_length = phase_length
        self._events = defaultdict(dict)

    def events_to_schedule_gen(self) -> 'Generator[LunarPhaseType, TimeSpan, int]':
        for (phase, phase_data) in self._events.items():
            for (phase_offset, event_guid) in phase_data.items():
                yield (phase, phase_offset, event_guid)

    def get_event_data(self, event_guid_for_data:'int') -> 'Tuple[Optional[LunarPhaseType], Optional[TimeSpan]]':
        for (phase, phase_offset, event_guid) in self.events_to_schedule_gen():
            if event_guid == event_guid_for_data:
                return (phase, phase_offset)
        return (None, None)

    def add_event(self, phase:'LunarPhaseType', phase_offset:'TimeSpan', event_guid:'int'):
        self._events[phase][phase_offset] = event_guid

class LunarEventsService(Service):

    def __init__(self):
        self._event_times = {}
        self._locked_phase_scheduling_alarm = None

    def start(self) -> 'None':
        scheduling_day_time = create_date_and_time(hours=DramaScheduleService.WEEKLY_SCHEDULING_TIME)
        sim_now = services.time_service().sim_now
        time_delay = sim_now.time_to_week_time(scheduling_day_time)
        if time_delay.in_ticks() == 0:
            time_delay = sim_now.time_till_timespan_of_week(scheduling_day_time)
        self._locked_phase_scheduling_alarm = alarms.add_alarm(self, time_delay, self.schedule_locked_phase_events, repeating=True, repeating_time_span=create_time_span(days=7), use_sleep_time=False, cross_zone=True)

    def on_lunar_cycle_started(self) -> 'None':
        self._schedule_cycle_events()

    def on_calendar_settings_changed(self) -> 'None':
        self._cancel_all_scheduled_events()
        self._schedule_lunar_events()

    def on_all_households_and_sim_infos_loaded(self, _) -> 'None':
        if self._find_scheduled_events():
            return
        self._schedule_lunar_events()

    def _schedule_lunar_events(self) -> 'None':
        if services.lunar_cycle_service().locked_phase != LunarPhaseLockedOption.NO_LUNAR_PHASE_LOCK:
            self.schedule_locked_phase_events()
        else:
            self._schedule_cycle_events()

    def _find_scheduled_events(self) -> 'List':
        lunar_event_tuning_instances = set()
        for (phase_type, phase_tuning) in LunarCycleTuning.LUNAR_PHASE_MAP.items():
            for (_, event, _) in phase_tuning().get_cycle_event_data():
                lunar_event_tuning_instances.add(event)
        scheduled_events = []
        drama_scheduler = services.drama_scheduler_service()
        for tuning_class in lunar_event_tuning_instances:
            scheduled_events.extend(drama_scheduler.get_scheduled_nodes_by_class(tuning_class))
        return scheduled_events

    def _cancel_all_scheduled_events(self) -> 'None':
        scheduled_events = self._find_scheduled_events()
        drama_scheduler = services.drama_scheduler_service()
        calendar_service = services.calendar_service()
        for event in scheduled_events:
            calendar_service.remove_on_calendar(event.uid)
            drama_scheduler.cancel_scheduled_node(event.uid)

    def _schedule_cycle_events(self) -> 'None':
        for phase_length in LunarCycleLengthOption:
            self._event_times[phase_length] = LunarCycleEvents(phase_length)
        for (phase_type, phase_tuning) in services.lunar_cycle_service().get_phases_for_scheduling():
            for (phase_length, event, phase_offset) in phase_tuning().get_cycle_event_data():
                self._event_times[phase_length].add_event(phase_type, phase_offset, event.guid64)
        resolver = DataResolver(None)
        drama_scheduler = services.drama_scheduler_service()
        lunar_cycle_service = services.lunar_cycle_service()
        phase_length = lunar_cycle_service.cycle_length_selected
        phase_data = defaultdict(list)
        for (phase_type, phase_instance) in lunar_cycle_service.get_phases_for_scheduling():
            phase_data[phase_type].append(phase_instance)
        sim_now = services.time_service().sim_now
        for (phase_type, phase_offset, event_guid) in self._event_times[phase_length].events_to_schedule_gen():
            for phase_instance in phase_data[phase_type]:
                for phase_event in phase_instance.phase_length_content[phase_length]:
                    event_start_time = lunar_cycle_service.get_projected_phase_start_time(phase_type, phase_offset)
                    if event_start_time > sim_now and not drama_scheduler.schedule_node(phase_event, resolver=resolver, specific_time=event_start_time):
                        logger.warn('The phase event {} failed to be scheduled.', phase_event)

    def schedule_locked_phase_events(self, handle=None) -> 'None':
        locked_phase = services.lunar_cycle_service().locked_phase
        if locked_phase is LunarPhaseLockedOption.NO_LUNAR_PHASE_LOCK or self._find_scheduled_events():
            return
        resolver = DataResolver(None)
        drama_scheduler = services.drama_scheduler_service()
        phase_instance = LunarCycleTuning.LUNAR_PHASE_MAP[locked_phase]
        events_data = phase_instance().get_locked_phase_event_data()
        sim_now = services.time_service().sim_now
        for (phase_event, valid_day, start_time) in events_data:
            day_of_week = sim_now.start_of_week() + create_time_span(days=valid_day)
            event_start_time = day_of_week + start_time
            if event_start_time > sim_now and not drama_scheduler.schedule_node(phase_event, resolver=resolver, specific_time=event_start_time):
                logger.warn('The phase event {} failed to be scheduled.', phase_event)
