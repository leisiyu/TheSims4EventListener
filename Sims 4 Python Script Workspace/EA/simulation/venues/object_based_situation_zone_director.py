from __future__ import annotationsimport sysfrom dataclasses import dataclassfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from protocolbuffers.GameplaySaveData_pb2 import ZoneDirectorData
    from sims4 import PropertyStreamWriter, PropertyStreamReader
    from objects.game_object import GameObjectfrom _weakrefset import WeakSetfrom date_and_time import TimeSpanfrom event_testing.resolver import SingleObjectResolverfrom objects.components import situation_scheduler_componentfrom objects.components.types import SITUATION_SCHEDULER_COMPONENT, STORED_SIM_INFO_COMPONENTfrom scheduler import SituationWeeklyScheduleVariant, WeightedSituationsWeeklySchedule, WeeklySchedule, AlarmDatafrom sims4.tuning.tunable import TunableMapping, TunableTuple, Tunable, OptionalTunable, TunableRange, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_shifts import SituationShiftsfrom tag import TunableTagimport servicesimport sims4.loglogger = sims4.log.Logger('ObjectBasedSituationZoneDirector', default_owner='hbabaran')
class ObjectBasedSituationData:
    __slots__ = ('situation_schedule', 'schedule_immediate', 'consider_off_lot_objects')

    def __init__(self, situation_schedule=None, schedule_immediate=False, consider_off_lot_objects=True):
        self.situation_schedule = situation_schedule
        self.schedule_immediate = schedule_immediate
        self.consider_off_lot_objects = consider_off_lot_objects
