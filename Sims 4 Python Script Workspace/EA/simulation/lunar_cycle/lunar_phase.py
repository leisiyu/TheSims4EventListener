from __future__ import annotationsfrom scheduler_utils import TunableDayAvailabilityfrom tunable_time import TunableTimeSpanfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from date_and_time import TimeSpan
    from drama_scheduler.drama_node import BaseDramaNode
    from typing import List, Tuple
    from tunable_time import Daysimport servicesimport sims4.resourcesfrom date_and_time import create_time_spanfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableRange, TunableList, TunableReference, TunableTuplefrom lunar_cycle.lunar_cycle_enums import LunarCycleLengthOptionlogger = sims4.log.Logger('Lunar Phase', default_owner='cparrish')
class TunablePhaseEffectsByHour(TunableMapping):

    def __init__(self, **kwargs):
        super().__init__(key_type=TunableRange(description='\n                Hour offset into the current phase.\n                ', tunable_type=int, minimum=0, maximum=23, default=0), value_type=TunableList(description='\n                Effects to apply at the given hour offset.\n                ', tunable=TunableReference(description='\n                    Lunar Effect\n                    ', manager=services.get_instance_manager(sims4.resources.Types.LUNAR_CYCLE), class_restrictions=('LunarPhaseEffect',), pack_safe=True)), **kwargs)

    @property
    def export_class(self):
        return 'TunableMapping'

class LunarPhase(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.LUNAR_CYCLE)):
    base_game_only = True
    INSTANCE_TUNABLES = {'length_option_duration_map': TunableMapping(description='\n            A mapping of how long this phase is when a specific length option is set.\n            ', key_type=TunableEnumEntry(description='\n                The length option.\n                ', tunable_type=LunarCycleLengthOption, default=LunarCycleLengthOption.FULL_LENGTH), value_type=TunableRange(description='\n                The length of this phase (in Sim days) for the given option.\n                ', tunable_type=int, minimum=0, default=1), set_default_as_first_entry=True), 'phase_length_content': TunableMapping(description='\n            The list of festivals/events to trigger during this lunar phase. The values on the right\n            are a time offset from the Phase Change Time of Day.\n            ', key_type=TunableEnumEntry(tunable_type=LunarCycleLengthOption, default=LunarCycleLengthOption.FULL_LENGTH), value_type=TunableMapping(description='\n                Event content of a lunar phase.\n                ', key_type=TunableReference(description='\n                    The festivals/events to trigger during this lunar phase.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), pack_safe=True), value_type=TunableList(tunable=TunableTimeSpan(description='\n                        The length of time after the Phase Change Time of Day at which this node can be\n                        scheduled for.\n                        ', default_hours=12)))), 'locked_phase_content': TunableMapping(description='\n            The list of festivals/events to trigger during this LOCKED lunar phase. The values on the\n            right are a Time of Day to schedule the event.\n            ', key_type=TunableReference(description='\n                The festivals/events to trigger.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), pack_safe=True), value_type=TunableTuple(description='\n                The days, and start time that this node will be scheduled for.\n                ', days_available=TunableDayAvailability(), start_time=TunableTimeSpan(default_hours=19, locked_args={'days': 0}))), 'effects_by_hour_offset': TunablePhaseEffectsByHour(description="\n            A mapping of hour into the current phase to effects that will be applied at that hour of the phase.\n            \n            This is relative to the lunar cycle 'Phase Change Time of Day' tuning.\n            "), 'pre_phase_effects_by_hour_offset': TunablePhaseEffectsByHour(description="\n            A mapping of hour into the current phase to effects that will be applied at that hour of the phase.\n            \n            This is relative to the lunar cycle 'Phase Change Time of Day' tuning.\n            \n            This list of effects affect the phase IMMEDIATELY PRECEDING this tuned phase, if this content \n            is not the active phase yet but will be within the next 24 hours.\n            \n            e.g. these effects are tuned on FULL_MOON, they apply if today is WAXING_GIBBOUS, which is the phase \n            preceding the FULL_MOON phase.  This can be used for effects such as popping a TNS noting there is \n            an upcoming full moon coming tomorrow night.  \n            ")}

    @classmethod
    def _verify_tuning_callback(cls):
        for phase_length in cls.phase_length_content:
            for (event, phase_offsets) in cls.phase_length_content[phase_length].items():
                for offset in phase_offsets:
                    if offset().in_days() > cls.get_phase_length_in_days(phase_length):
                        logger.error("Event {} in {} has tuning for an event outside of it's phase length", event, cls)

    @classmethod
    def get_phase_length(cls, cycle_length_option:'LunarCycleLengthOption'):
        return create_time_span(days=cls.get_phase_length_in_days(cycle_length_option))

    @classmethod
    def get_phase_length_in_days(cls, cycle_length_option:'LunarCycleLengthOption'):
        return cls.length_option_duration_map[cycle_length_option]

    def get_cycle_event_data(self) -> 'List[Tuple[LunarCycleLengthOption, BaseDramaNode, TimeSpan]]':
        events_data = []
        if not self.phase_length_content:
            return events_data
        for phase_length in LunarCycleLengthOption:
            for (event, phase_offsets) in self.phase_length_content[phase_length].items():
                events_data.extend(iter((phase_length, event, offset()) for offset in phase_offsets))
        return events_data

    def get_locked_phase_event_data(self) -> 'List[Tuple[BaseDramaNode, Days, TimeSpan]]':
        locked_events_data = []
        if not self.locked_phase_content:
            return locked_events_data
        for (event, availability) in self.locked_phase_content.items():
            for (day, day_enabled) in availability.days_available.items():
                if day_enabled:
                    locked_events_data.append((event, day, availability.start_time()))
        return locked_events_data
