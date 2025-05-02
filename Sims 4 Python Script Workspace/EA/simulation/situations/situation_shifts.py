from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from situations.situation import Situation
    from protocolbuffers.GameplaySaveData_pb2 import AmbientSourceData, OpenStreetDirectorData, ZoneDirectorData
    ProtoData = Union[(ZoneDirectorData, OpenStreetDirectorData, AmbientSourceData)]from sims4.tuning.tunable import TunableSimMinute, TunableList, TunableTuple, TunableEnumEntry, TunableVariant, Tunable, HasTunableFactory, AutoFactoryInit, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.additional_situation_sources import HolidayWalkbys, ZoneModifierSituations, NarrativeSituationsfrom situations.situation_curve import SituationCurve, ShiftlessDesiredSituations, SituationShiftStrictnessfrom situations.situation_guest_list import SituationGuestListimport alarmsimport clockimport enumimport servicesimport sims4.logimport randomlogger = sims4.log.Logger('SituationShifts', default_owner='hbabaran')
class SituationChurnOperation(enum.Int, export=False):
    DO_NOTHING = 0
    START_SITUATION = 1
    REMOVE_SITUATION = 2

class SituationHost(enum.Int):
    ActiveSim = 0
    SimFromObject = 1

class SituationShifts(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situation_shifts': TunableList(description='\n            A list of situation distributions and their strictness rules.\n            ', tunable=TunableTuple(shift_curve=TunableVariant(description='\n                    A container for specifying the desired amount of certain situations at specific times of day/week. \n                    ', curve_based=SituationCurve.TunableFactory(get_create_params={'user_facing': True}), shiftless=ShiftlessDesiredSituations.TunableFactory(get_create_params={'user_facing': True}), default='curve_based'), shift_strictness=TunableEnumEntry(description='\n                    Determine how situations on shift will be handled on shift\n                    change.\n                    \n                    Example: I want 3 customers between 10-12.  then after 12 I\n                    want only 1.  Having this checked will allow 3 customers to\n                    stay and will let situation duration kick the sim out when\n                    appropriate.  This will not create new situations if over\n                    the cap.\n                    ', tunable_type=SituationShiftStrictness, default=SituationShiftStrictness.DESTROY), additional_sources=TunableList(description='\n                    Any additional sources of NPCs that we want to use to add\n                    into the possible situations of this shift curve.\n                    ', tunable=TunableVariant(description='\n                        The different additional situation sources that we\n                        want to use to get additional situation possibilities\n                        that can be chosen.\n                        ', holiday=HolidayWalkbys.TunableFactory(), zone_modifier=ZoneModifierSituations.TunableFactory(), narrative=NarrativeSituations.TunableFactory(), default='holiday')), count_based_on_expected_sims=Tunable(description='\n                    If checked then we will count based on the number of Sims\n                    that are expected to be in the Situation rather than the\n                    number of situations.\n                    NOTE if this is checked, your situation MUST have get_sims_expected_to_be_in_situation() implemented\n                    by a GPE. Otherwise the situation will not start. \n                    ', tunable_type=bool, default=False)), tuning_group=GroupNames.SITUATION), 'churn_alarm_interval': TunableSimMinute(description='\n            Number sim minutes to check to make sure shifts and churn are being accurate.\n            ', default=10, tuning_group=GroupNames.SITUATION), 'set_host_as_active_sim': Tunable(description='\n            DEPRECATED-- use Set Host As instead. If Set Host As is enabled, it will OVERRIDE this setting. \n            \n            If checked then the active Sim will be set as the host of\n            situations started from this director if we do not have a pre-made\n            guest list.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION, deprecated=True), 'set_host_as': OptionalTunable(description='\n            If enabled, we will set a host sim (aka Requesting Sim) for the situations being started. \n            The host sim can influence the default guest list for the situation, if we do not have a \n            premade guest list. Most of the time this should be the Active Sim. \n            \n            In the case of Object Situation Shifts only, select SimFromObject if you want to set the \n            host sim as the sim stored on the object (e.g. the ghost associated with an urnstone). \n            ', tunable=TunableEnumEntry(tunable_type=SituationHost, default=SituationHost.ActiveSim))}

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._shift_alarm_handles = {}
        self._situation_shifts_to_situation_ids = {}
        self._situation_shift_ideal_situations = {}
        self._object_parameters = []

    def __iter__(self) -> 'Iterable[Tuple[...]]':
        return iter(self.situation_shifts)

    def get_all_situations(self) -> 'None':
        situations = []
        situation_manager = services.get_zone_situation_manager()
        for shift_situations in self._situation_shifts_to_situation_ids.values():
            for situation_id in shift_situations:
                situation = situation_manager.get(situation_id)
                if situation is not None:
                    situations.append(situation)
        return situations

    @staticmethod
    def can_schedule_situation(situation:'Situation', limit_based_on_sims:'bool'=False, number_of_sims_desired:'int'=0, **kwargs) -> 'bool':
        if services.game_clock_service().clock_speed == clock.ClockSpeedMode.SUPER_SPEED3 and not situation.allowed_in_super_speed_3:
            return False
        if limit_based_on_sims and not situation.can_start_walkby(services.active_lot_id(), number_of_sims_desired):
            return False
        return situation.situation_meets_starting_requirements(**kwargs) and not services.get_zone_modifier_service().is_situation_prohibited(services.current_zone_id(), situation)

    def on_startup(self) -> 'None':
        for alarm_handle in self._shift_alarm_handles:
            alarms.cancel_alarm(alarm_handle)
        self._shift_alarm_handles.clear()
        time_of_day = services.time_service().sim_now
        churn_interval = clock.interval_in_sim_minutes(self.churn_alarm_interval)
        for situation_shift in self.situation_shifts:
            alarm_handle = alarms.add_alarm(self, churn_interval, self._shift_churn_alarm_callback, repeating=True)
            self._shift_alarm_handles[alarm_handle] = situation_shift
            time_span = situation_shift.shift_curve.get_timespan_to_next_shift_time(time_of_day)
            if time_span is not None:
                alarm_handle = alarms.add_alarm(self, time_span, self._shift_change_alarm_callback)
                self._shift_alarm_handles[alarm_handle] = situation_shift

    def on_shutdown(self) -> 'None':
        self.destroy_shifts()

    def destroy_shifts(self) -> 'None':
        for alarm_handle in self._shift_alarm_handles:
            alarms.cancel_alarm(alarm_handle)
        self._shift_alarm_handles.clear()
        situation_manager = services.get_zone_situation_manager()
        for situation_ids in self._situation_shifts_to_situation_ids.values():
            for situation_id in situation_ids:
                situation_manager.destroy_situation_by_id(situation_id)
        self._situation_shifts_to_situation_ids.clear()
        self._situation_shift_ideal_situations.clear()

    def create_situations_during_zone_spin_up(self) -> 'None':
        for situation_shift in self.situation_shifts:
            self.handle_situation_shift_churn(situation_shift, reserve_object_relationships=True)

    def start_missed_shifts(self) -> 'None':
        for situation_shift in self.situation_shifts:
            if not situation_shift.shift_curve.is_shift_churn_disabled:
                return
            missed_situations = situation_shift.shift_curve.get_missed_situations(situation_shift.shift_strictness)
            situation_manager = services.get_zone_situation_manager()
            situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
            situation_ids = situation_manager.get_validated_situation_ids(situation_ids)
            for (situation_to_start, params) in missed_situations:
                number_sims_desired_for_shift = params['desired_sim_count']
                num_sims_expected_per_situation = situation_to_start.get_sims_expected_to_be_in_situation()
                if num_sims_expected_per_situation is None:
                    num_sims_expected_per_situation = 1
                running_situations_of_this_type = situation_manager.get_situations_by_type(situation_to_start)
                number_sims_desired_for_shift -= len(running_situations_of_this_type)*num_sims_expected_per_situation
                object_param = random.choice(self._object_parameters) if len(self._object_parameters) > 0 else None
                if not self.can_schedule_situation(situation_to_start, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_sims_desired_for_shift, object_to_staff=object_param.get('obj') if object_param else None):
                    break
                situation_id = self._create_situation_with_params(situation_to_start, params, object_param)
                if situation_id is not None:
                    situation_ids.append(situation_id)
                    number_sims_desired_for_shift -= num_sims_expected_per_situation
                else:
                    break
            self._situation_shifts_to_situation_ids[situation_shift] = situation_ids

    def _create_situation_with_params(self, situation_to_start:'Situation', params:'Dict[str, int]', object_param:'dict') -> 'int or None':
        if situation_to_start is None or params is None:
            return
        if object_param is not None:
            params['object_to_staff'] = object_param.get('obj')
        situation_manager = services.get_zone_situation_manager()
        guest_list = situation_to_start.get_predefined_guest_list()
        if guest_list is None:
            guest_list = self._get_default_guest_list(self._get_host_id(object_param))
        try:
            creation_source = self.instance_name
        except:
            creation_source = str(self)
        return situation_manager.create_situation(situation_to_start, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, creation_source=creation_source, **params)

    def _get_default_guest_list(self, host_sim_id:'int'=0) -> 'SituationGuestList':
        if host_sim_id == 0:
            host_sim_id = self._get_host_id()
        return SituationGuestList(invite_only=True, host_sim_id=host_sim_id, filter_requesting_sim_id=host_sim_id)

    def _get_host_id(self, object_param:'dict'=None) -> 'int':
        host_sim_id = 0
        if self.set_host_as == SituationHost.SimFromObject and object_param is not None:
            sim_from_object = object_param.get('sim_from_object')
            if sim_from_object is not None:
                host_sim_id = sim_from_object.sim_id
        elif self.set_host_as == SituationHost.ActiveSim or self.set_host_as_active_sim:
            active_sim_info = services.active_sim_info()
            if active_sim_info is not None:
                host_sim_id = active_sim_info.sim_id
        return host_sim_id

    def _shift_change_alarm_callback(self, alarm_handle:'alarms.AlarmHandle'=None) -> 'None':
        situation_shift = self._shift_alarm_handles.pop(alarm_handle, None)
        if situation_shift is None:
            return
        situation_manager = services.get_zone_situation_manager()
        situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
        situation_ids = situation_manager.get_validated_situation_ids(situation_ids)
        number_sims_desired_for_shift = situation_shift.shift_curve.get_desired_sim_count().random_int()
        if not situation_shift.shift_curve.desired_sim_count_multipliers:
            self._situation_shift_ideal_situations[situation_shift] = number_sims_desired_for_shift
        if situation_shift.shift_strictness == SituationShiftStrictness.DESTROY:
            for situation_id in situation_ids:
                situation_manager.destroy_situation_by_id(situation_id)
            situation_ids.clear()
        elif situation_shift.shift_strictness == SituationShiftStrictness.OVERLAP:
            if situation_shift.count_based_on_expected_sims:
                for situation_id in situation_ids:
                    situation = situation_manager.get(situation_id)
                    sims_in_situation = situation.get_sims_expected_to_be_in_situation()
                    if sims_in_situation is None:
                        logger.error('Trying to get expected Sims for situation {} that does not provide that information.  Treating as a single Sim.  This situation does not support this behavior.  Contact your GPE partner to fix this.', situation, owner='jjacobson')
                        sims_in_situation = 1
                    number_sims_desired_for_shift -= sims_in_situation
            else:
                number_sims_desired_for_shift -= len(situation_ids)
        logger.debug('Situation Shift Change: Adding {}', number_sims_desired_for_shift)
        if number_sims_desired_for_shift > 0:
            object_param = random.choice(self._object_parameters) if len(self._object_parameters) > 0 else None
            additional_situations = []
            for situation_source in situation_shift.additional_sources:
                additional_situations.extend(situation_source.get_additional_situations(predicate=lambda potential_situation: self.can_schedule_situation(potential_situation, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_sims_desired_for_shift)))
            (situation_to_start, params) = situation_shift.shift_curve.get_situation_and_params(predicate=lambda potential_situation: self.can_schedule_situation(potential_situation, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_sims_desired_for_shift, object_to_staff=object_param.get('obj') if object_param else None), additional_situations=additional_situations)
            if situation_to_start is not None:
                situation_id = self._create_situation_with_params(situation_to_start, params, object_param)
                if situation_id is not None:
                    situation_ids.append(situation_id)
                    if situation_shift.count_based_on_expected_sims:
                        sims_in_situation = situation_to_start.get_sims_expected_to_be_in_situation()
                        if sims_in_situation is None:
                            logger.error('Trying to get expected Sims for situation {} that does not provide that information. Treating as a single Sim. This situation does not support this behavior. Contact your GPE partner to fix this.', situation, owner='jjacobson')
                            sims_in_situation = 1
                        number_sims_desired_for_shift -= sims_in_situation
                    else:
                        number_sims_desired_for_shift -= 1
                else:
                    number_sims_desired_for_shift -= 1
            else:
                number_sims_desired_for_shift -= 1
        self._situation_shifts_to_situation_ids[situation_shift] = situation_ids
        if alarm_handle is not None:
            time_of_day = services.time_service().sim_now
            time_span = situation_shift.shift_curve.get_timespan_to_next_shift_time(time_of_day)
            alarm_handle = alarms.add_alarm(self, time_span, self._shift_change_alarm_callback)
            self._shift_alarm_handles[alarm_handle] = situation_shift

    def _shift_churn_alarm_callback(self, alarm_handle:'alarms.AlarmHandle') -> 'None':
        situation_shift = self._shift_alarm_handles.get(alarm_handle, None)
        if situation_shift is None:
            return
        self.handle_situation_shift_churn(situation_shift)

    def handle_situation_shift_churn(self, situation_shift:'Tuple[...]', reserve_object_relationships:'bool'=False) -> 'None':
        if situation_shift.shift_curve.is_shift_churn_disabled:
            return
        number_situations_desire = self._situation_shift_ideal_situations.get(situation_shift, None)
        if number_situations_desire is None:
            number_situations_desire = situation_shift.shift_curve.get_desired_sim_count().random_int()
            if not situation_shift.shift_curve.desired_sim_count_multipliers:
                self._situation_shift_ideal_situations[situation_shift] = number_situations_desire
        situation_manager = services.get_zone_situation_manager()
        situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
        situation_ids = situation_manager.get_validated_situation_ids(situation_ids)
        current_count = 0
        if situation_shift.count_based_on_expected_sims:
            for situation_id in situation_ids:
                situation = situation_manager.get(situation_id)
                sims_in_situation = situation.get_sims_expected_to_be_in_situation()
                if sims_in_situation is None:
                    logger.error('Trying to get expected Sims for situation {} that does not provide that information. Treating as a single Sim. This situation does not support this behavior. Contact your GPE partner to fix this.', situation, owner='jjacobson')
                    sims_in_situation = 1
                current_count += sims_in_situation
        else:
            current_count = len(situation_ids)
        op = SituationChurnOperation.DO_NOTHING
        situation_to_start = None
        object_param = None
        params = None
        if number_situations_desire > current_count:
            reserved_object_relationships = 0
            if reserve_object_relationships:
                reserved_object_relationships = len(situation_ids)
            if len(self._object_parameters) > 0:
                object_param = random.choice(self._object_parameters)
            predicate = lambda situation: self.can_schedule_situation(situation, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_situations_desire - current_count, reserved_object_relationships=reserved_object_relationships, object_to_staff=object_param.get('obj') if object_param else None)
            additional_situations = []
            for situation_source in situation_shift.additional_sources:
                additional_situations.extend(situation_source.get_additional_situations(predicate=predicate))
            (situation_to_start, params) = situation_shift.shift_curve.get_situation_and_params(predicate=predicate, additional_situations=additional_situations)
            if situation_to_start is not None:
                op = SituationChurnOperation.START_SITUATION
        elif not situation_shift.shift_strictness == SituationShiftStrictness.OVERLAP:
            op = SituationChurnOperation.REMOVE_SITUATION
        if op == SituationChurnOperation.START_SITUATION:
            if situation_to_start is not None:
                situation_id = self._create_situation_with_params(situation_to_start, params, object_param)
                if situation_id is not None:
                    situation_ids.append(situation_id)
            self._situation_shifts_to_situation_ids[situation_shift] = situation_ids
        elif op == SituationChurnOperation.REMOVE_SITUATION:
            time_of_day = services.time_service().sim_now
            situations = [situation_manager.get(situation_id) for situation_id in situation_ids]
            situations.sort(key=lambda x: time_of_day - x.situation_start_time, reverse=True)
            situation_to_remove = next(iter(situations))
            if situation_to_remove is not None:
                logger.debug('Situation Churn Alarm Callback: Removing Situation: {}', situation_to_remove)
                situation_manager.destroy_situation_by_id(situation_to_remove.id)

    def save_object_situation_shifts(self, zone_director_proto:'ZoneDirectorData', object_tag:'int') -> 'None':
        situation_manager = services.get_zone_situation_manager()
        for (index, situation_shift) in enumerate(self.situation_shifts):
            situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
            situation_ids = situation_manager.get_validated_situation_ids(situation_ids)
            if situation_ids:
                situation_data_proto = zone_director_proto.object_situations.add()
                situation_data_proto.object_tag = object_tag
                situation_data_proto.situation_list_guid = index
                situation_data_proto.situation_ids.extend(situation_ids)

    def load_object_situation_shifts(self, zone_director_proto:'ZoneDirectorData', object_tag:'int') -> 'None':
        for situation_data_proto in zone_director_proto.object_situations:
            if situation_data_proto.object_tag != object_tag:
                pass
            else:
                situation_shift = self.situation_shifts[situation_data_proto.situation_list_guid]
                situation_ids = []
                situation_ids.extend(situation_data_proto.situation_ids)
                self._situation_shifts_to_situation_ids[situation_shift] = situation_ids

    def add_affected_object_count(self, num_affected_objects:'int') -> 'None':
        for situation_shift in self.situation_shifts:
            situation_shift.shift_curve.set_additional_count_multiplier(num_affected_objects)

    def add_object_parameters(self, object_parameters:'List') -> 'None':
        self._object_parameters = object_parameters

    def save_situation_shifts(self, zone_director_proto:'ProtoData', validate:'bool'=True) -> 'None':
        situation_manager = services.get_zone_situation_manager()
        for (index, situation_shift) in enumerate(self.situation_shifts):
            situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
            if validate:
                situation_ids = situation_manager.get_validated_situation_ids(situation_ids)
            if situation_ids:
                situation_data_proto = zone_director_proto.situations.add()
                situation_data_proto.situation_list_guid = index
                situation_data_proto.situation_ids.extend(situation_ids)

    def load_situation_shifts(self, zone_director_proto:'ProtoData') -> 'None':
        for situation_data_proto in zone_director_proto.situations:
            if situation_data_proto.situation_list_guid >= len(self.situation_shifts):
                pass
            else:
                situation_shift = self.situation_shifts[situation_data_proto.situation_list_guid]
                situation_ids = []
                situation_ids.extend(situation_data_proto.situation_ids)
                self._situation_shifts_to_situation_ids[situation_shift] = situation_ids
