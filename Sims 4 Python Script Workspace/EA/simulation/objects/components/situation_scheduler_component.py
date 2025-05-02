from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from scheduler import WeeklySchedule
    from situations.situation import Situationfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable, TunableTuple, TunableRange, Tunable, TunableListimport sims4.logfrom event_testing.tests import TunableTestSetfrom objects.components import Component, componentmethodfrom objects.components.types import SITUATION_SCHEDULER_COMPONENTfrom scheduler import SituationWeeklyScheduleVariant, WeeklySchedulefrom situations.situation_guest_list import SituationGuestListfrom situations.situation_manager import SituationManagerfrom situations.situation_shifts import SituationShiftsfrom tag import TunableTag, Tagimport serviceslogger = sims4.log.Logger('SituationSchedulerComponent', default_owner='mkartika')
class SituationSchedulerComponent(Component, HasTunableFactory, AutoFactoryInit, allow_dynamic=True, component_name=SITUATION_SCHEDULER_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.SituationSchedulerComponent):
    FACTORY_TUNABLES = {'object_situation_shifts': OptionalTunable(description='\n            Enables modern Object Situation Shifts, and ignores deprecated Object Based Situation Schedule.\n            \n            This is a schedule for situations associated with this object. The situations specified in this schedule \n            will override the Zone Director\'s Object Situation Shifts IF:\n                - this object exists on a lot or in the open street, AND\n                - Tests is either empty or returns True, AND\n                - the lot\'s Zone Director allows object-based schedules by enabling "Use Object Situation Scheduler\n                  Component".\n            ', tunable=TunableTuple(description='\n                ', object_tag=TunableTag(description='\n                        This tag must match one of the tags associated with this object.\n                        ', filter_prefixes=('func',)), consider_off_lot_objects=Tunable(description='\n                    If checked, these situations are scheduled for all instances of the object in both the active lot \n                    and the open street. If unchecked, these situations are only scheduled for objects within the active \n                    lot.\n                    ', tunable_type=bool, default=True), include_objects_within_object_inventories=OptionalTunable(description="\n                    If enabled, provide one or more Container Object Tags (e.g. func_Crypt). \n                    Objects with any of the Container Object Tags will allow the zone director to include the \n                    container object's inventory in its search for objects that can start situations.\n            \n                    Staffed Object Situations based on inventoried objects will have the spawned sims \n                    walk up to the container object instead. \n                    ", tunable=TunableList(description='\n                        A list of Container Object Tags. \n                        ', tunable=TunableTag(description="\n                            An object tag. If an object has this tag, and it has an inventory, the zone director\n                            can schedule object situations based on objects INSIDE this object's inventory.\n            \n                            Staffed Object Situations based on inventoried objects will have the spawned sims \n                            walk up to the container object instead.  \n                            ", filter_prefixes=('func',)))), schedule_immediate=Tunable(description='\n                    This controls the behavior of the scheduler if the current time\n                    happens to fall within a scheduled entry. If this is True, \n                    start_missed_situations will trigger immediately for that entry.\n                    If False, the shift will start at its next scheduled entry.\n                    ', tunable_type=bool, default=True), tests=TunableTestSet(description='\n                    Tests to determine if this schedule should override the Object Situation Shifts in the Zone \n                    Director, if the ZD is configured to allow it (Use Object Situation Scheduler Component is checked).\n                    Test is performed when the schedule is rebuilt (which currently occurs on Zone Spin Up and \n                    Build Buy Exit). If Tests is not defined, it defaults to True.\n                    '), affected_object_cap=TunableRange(description='\n                    Specify the maximum number of objects on the zone lot that \n                    can schedule the situations.\n                    ', tunable_type=int, minimum=1, default=1), **SituationShifts.FACTORY_TUNABLES)), 'object_based_situations_schedule': OptionalTunable(description='\n            DEPRECATED - use Situation Shifts instead! \n            If enabled, the object provides its own situation schedule.\n            ', deprecated=True, tunable=TunableTuple(description='\n                Data associated with situations schedule.\n                ', tag=TunableTag(description='\n                    An object tag. If the object exist on the zone lot, situations\n                    will be scheduled. The basic assumption is that this tag matches\n                    one of the tags associated with this object, but this is not \n                    enforced.\n                    ', filter_prefixes=('func',)), situation_schedule=SituationWeeklyScheduleVariant(description='\n                    The schedule to trigger the different situations.\n                    ', pack_safe=True, affected_object_cap=True), schedule_immediate=Tunable(description='\n                    This controls the behavior of scheduler if the current time\n                    happens to fall within a schedule entry. If this is True, \n                    a start_callback will trigger immediately for that entry.\n                    If False, the next start_callback will occur on the next entry.\n                    ', tunable_type=bool, default=False), consider_off_lot_objects=Tunable(description='\n                    If True, consider all objects in lot and the open street for\n                    this object situation. If False, only consider objects on\n                    the active lot.\n                    ', tunable_type=bool, default=True), tests=TunableTestSet(description="\n                    Tests to determine if this Tag should be added to the active\n                    Zone Director's Situations Schedule.  Test is performed\n                    when the schedule is rebuilt.  This is currently on Zone\n                    Spin Up and Build Buy Exit.\n                    \n                    NOTE: Object Based Situation Schedule is DEPRECATED, and if the zone director enables Object \n                    Situation Shifts, this schedule will be ignored, as though Tests are FALSE. \n                    ")))}

    def __init__(self, *args, scheduler=None, **kwargs):
        if 'object_based_situations_schedule' not in kwargs:
            kwargs['object_based_situations_schedule'] = None
        super().__init__(*args, **kwargs)
        self._situation_scheduler = scheduler
        self._generated_situation_ids = set()
        self._has_shift_schedule = self.object_situation_shifts is not None and (self.object_situation_shifts.object_tag != Tag.INVALID and self.object_situation_shifts.situation_shifts is not None)
        self._has_weekly_schedule = self.object_based_situations_schedule is not None and (self.object_based_situations_schedule.tag != Tag.INVALID and self.object_based_situations_schedule.situation_schedule is not None)

    @componentmethod
    def set_weekly_situation_scheduler(self, scheduler:'WeeklySchedule') -> 'None':
        self._destroy_weekly_situation_scheduler()
        self._situation_scheduler = scheduler

    @componentmethod
    def create_weekly_situation(self, situation_type:'Situation', **params) -> 'None':
        if not situation_type.situation_meets_starting_requirements():
            return
        situation_manager = services.get_zone_situation_manager()
        self._cleanup_generated_weekly_situations(situation_manager)
        running_situation = self._get_same_weekly_situation_running(situation_manager, situation_type)
        if running_situation is not None:
            situation_manager.destroy_situation_by_id(running_situation.id)
        guest_list = situation_type.get_predefined_guest_list() or SituationGuestList(invite_only=True)
        merged_params = dict(params, guest_list=guest_list, user_facing=False, scoring_enabled=False, spawn_sims_during_zone_spin_up=True, creation_source=str(self), default_target_id=self.owner.id)
        situation_id = situation_manager.create_situation(situation_type, **merged_params)
        if situation_id is None:
            return
        self._generated_situation_ids.add(situation_id)

    def on_remove(self, *_, **__):
        self.destroy_weekly_scheduler_and_situations()

    def destroy_weekly_scheduler_and_situations(self):
        self._destroy_weekly_situation_scheduler()
        self._destroy_generated_weekly_situations()

    def _cleanup_generated_weekly_situations(self, situation_manager:'SituationManager') -> 'None':
        for situation_id in list(self._generated_situation_ids):
            running_situation = situation_manager.get(situation_id)
            if running_situation is None:
                self._generated_situation_ids.remove(situation_id)

    def _get_same_weekly_situation_running(self, situation_manager:'SituationManager', situation_type:'Situation') -> 'Optional[Situation]':
        for situation_id in self._generated_situation_ids:
            running_situation = situation_manager.get(situation_id)
            if situation_type is type(running_situation):
                return running_situation

    def _destroy_weekly_situation_scheduler(self):
        if self._situation_scheduler is not None:
            self._situation_scheduler.destroy()
            self._situation_scheduler = None

    def _destroy_generated_weekly_situations(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._generated_situation_ids:
            situation_manager.destroy_situation_by_id(situation_id)
        self._generated_situation_ids.clear()

    @property
    def can_remove_weekly_component(self):
        return not self._has_weekly_schedule

    def save(self, persistence_master_message):
        if not self._has_shift_schedule:
            persistable_data = protocols.PersistenceMaster.PersistableData()
            persistable_data.type = protocols.PersistenceMaster.PersistableData.SituationSchedulerComponent
            component_data = persistable_data.Extensions[protocols.PersistableSituationSchedulerComponent.persistable_data]
            if self._generated_situation_ids:
                component_data.situation_ids.extend(self._generated_situation_ids)
            persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        if not self._has_shift_schedule:
            component_data = persistable_data.Extensions[protocols.PersistableSituationSchedulerComponent.persistable_data]
            for situation_id in component_data.situation_ids:
                self._generated_situation_ids.add(situation_id)
