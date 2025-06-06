from __future__ import annotationsfrom business.business_enums import BusinessTypefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from _collections import defaultdictfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom statistics.base_statistic import StatisticChangeDirectionfrom weakref import WeakKeyDictionaryimport itertoolsimport mathimport operatorimport randomimport weakreffrom protocolbuffers import Consts_pb2, DistributorOps_pb2, SimObjectAttributes_pb2, FileSerialization_pb2from protocolbuffers.Dialog_pb2 import UiCareerNotificationArgsfrom protocolbuffers.DistributorOps_pb2 import Operationfrom audio.primitive import play_tunable_audiofrom bucks.bucks_utils import BucksUtilsfrom buffs.buff_display_type import BuffDisplayTypefrom careers import career_opsfrom careers.career_enums import CareerOutfitGenerationType, CareerShiftType, ReceiveDailyHomeworkHelp, CareerCategory, CareerPanelType, GigResult, CareerEventDeclineOptions, TestEventCareersOrigin, WORK_PART_TIME_CAREER_CATEGORIESfrom careers.career_event_manager import CareerEventManagerfrom careers.career_mixins import CareerKnowledgeMixinfrom careers.career_ops import CareerTimeOffReasonfrom careers.career_scheduler import get_career_schedule_for_levelfrom careers.coworker import CoworkerMixinfrom careers.retirement import Retirementfrom clock import interval_in_sim_minutesfrom date_and_time import create_time_span, DateAndTime, TimeSpan, DATE_AND_TIME_ZERO, MINUTES_PER_HOUR, date_and_time_from_week_timefrom distributor.ops import GenericProtocolBufferOp, EndOfWorkdayfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.results import EnqueueResultfrom event_testing.test_events import TestEventfrom fame.fame_tuning import FameTunablesfrom interactions.aop import AffordanceObjectPairfrom interactions.context import QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom objects import ALL_HIDDEN_REASONS, HiddenReasonFlagfrom objects.client_object_mixin import ClientObjectMixinfrom sims.outfits.outfit_enums import OutfitChangeReason, OutfitCategoryfrom sims.sickness_tuning import SicknessTuningfrom sims.sim_info_types import Agefrom sims.sim_spawner_service import SimSpawnRequest, SimSpawnPointStrategy, SimSpawnReasonfrom sims4.callback_utils import CallableList, RemovableCallableListfrom sims4.localization import LocalizationHelperTuningfrom sims4.math import Threshold, clamp, EPSILONfrom sims4.protocol_buffer_utils import has_fieldfrom sims4.utils import flexmethod, constpropertyfrom singletons import DEFAULTfrom ui.ui_dialog import UiDialogResponse, ButtonTypefrom ui.ui_utils import UIUtilsfrom world.region import Regionfrom world.spawn_point import SpawnPointimport alarmsimport clockimport date_and_timeimport distributor.systemimport enumimport game_servicesimport interactions.contextimport servicesimport simsimport sims4.logimport sims4.mathimport telemetry_helperTELEMETRY_GROUP_CAREERS = 'CARE'TELEMETRY_HOOK_CAREER_START = 'CAST'TELEMETRY_HOOK_CAREER_END = 'CAEN'TELEMETRY_HOOK_CAREER_PROMOTION = 'CAUP'TELEMETRY_HOOK_CAREER_DEMOTION = 'CADW'TELEMETRY_HOOK_CAREER_DAILY_END = 'CADA'TELEMETRY_HOOK_CAREER_OVERMAX = 'CAOM'TELEMETRY_HOOK_CAREER_LEAVE_EARLY = 'CALE'TELEMETRY_HOOK_CAREER_EVENT_END = 'CEND'TELEMETRY_HOOK_CAREER_INITIAL_ASSIGNMENT_OFFER = 'ASSI'TELEMETRY_HOOK_CAREER_ASSIGNMENT_END = 'ASEV'TELEMETRY_HOOK_CAREER_WORKDAY_START = 'BOTD'TELEMETRY_CAREER_ID = 'caid'TELEMETRY_CAREER_LEVEL = 'leve'TELEMETRY_CAREER_DAILY_PERFORMANCE = 'poin'TELEMETRY_TRACK_ID = 'trid'TELEMETRY_TRACK_LEVEL = 'trlv'TELEMETRY_TRACK_OVERMAX = 'trom'TELEMETRY_CAREER_EVENT_MEDAL = 'ceme'TELEMETRY_CAREER_EVENT_GOALS = 'cego'TELEMETRY_ASSIGNMENT_ID = 'asid'TELEMETRY_ASSIGNMENT_ACCEPTANCE = 'asar'TELEMETRY_ASSIGNMENT_COMPLETED = 'ascf'TELEMETRY_FIELD_WORKDAY_TYPE = 'wktp'TELEMETRY_WORKDAY_TYPE_RABBIT_HOLE = 1TELEMETRY_WORKDAY_TYPE_ACTIVE = 2TELEMETRY_WORKDAY_TYPE_WORK_FROM_HOME = 3TELEMETRY_WORKDAY_TYPE_DAY_OFF = 4career_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CAREERS)logger = sims4.log.Logger('Careers', default_owner='tingyul')NO_TIME_DIFFERENCE = date_and_time.TimeSpan.ZEROPERCENT_FLOAT_CONVERSION = 0.01RESPONSE_ID_GO_TO_WORK = 0RESPONSE_ID_WORK_FROM_HOME = 1RESPONSE_ID_TAKE_PTO = 2RESPONSE_ID_CALL_IN_SICK = 3with sims4.reload.protected(globals()):
    _career_event_overrides = WeakKeyDictionary()
def set_career_event_override(sim_info, career_event):
    _career_event_overrides[sim_info] = career_event

class Evaluation(enum.Int, export=False):
    ON_TARGET = ...
    PROMOTED = ...
    DEMOTED = ...
    FIRED = ...

class EvaluationResult:

    def __init__(self, evaluation, dialog_factory, *args, **kwargs):
        self.evaluation = evaluation
        self.dialog_factory = dialog_factory
        self.dialog_args = args
        self.dialog_kwargs = kwargs

    def display_dialog(self, career):
        if self.dialog_factory is not None:
            career.send_career_message(self.dialog_factory, self.dialog_args, **self.dialog_kwargs)

class CareerBase(CoworkerMixin, CareerKnowledgeMixin, sims.sim_spawner_service.ISimSpawnerServiceCustomer):
    TONE_STAT_MOD = 1

    def __init__(self, sim_info, init_track=False):
        super().__init__()
        self._sim_info = sim_info
        self.on_promoted = CallableList()
        self.on_demoted = CallableList()
        self.on_career_removed = RemovableCallableList()
        self._level = 0
        self._user_level = 1
        self._overmax_level = 0
        self._join_time = None
        self._career_location = self.career_location(self)
        self._current_work_start = None
        self._current_work_end = None
        self._current_work_duration = None
        self._at_work = False
        self._requested_day_off_reason = career_ops.CareerTimeOffReason.NO_TIME_OFF
        self._taking_day_off_reason = career_ops.CareerTimeOffReason.NO_TIME_OFF
        self._pto_taken = 0
        self._current_track = None
        if init_track:
            self._current_track = self.start_track
        self._auto_work = False
        self._pending_promotion = False
        self._work_scheduler = None
        self._end_work_handle = None
        self._late_for_work_handle = None
        self._assignment_offering_handle = None
        self._rabbit_hole_id = None
        self._statistic_down_listeners = {}
        self._statistic_up_listeners = {}
        self._trait_listener = None
        self._career_event_manager = None
        self._career_session_extended = False
        self._has_attended_first_day = False
        self._career_event_cooldown_map = {}
        self._active_assignments = []
        self._offered_assignment_ids = set()
        self._assignment_late = False
        self.assignment_handler_gsi_cache = []
        self._player_rewards_deferred = False
        self.fame_moment_completed = False
        self._current_gigs = []
        self._work_scheduler_override = None
        self._current_shift_type = CareerShiftType.ALL_DAY
        self._first_gig_completed = False
        self._seen_scholarship_info = False
        self._guid_to_claimed_object_ids = None
        self._follow_enabled = True
        self._icon_override = None
        self.workplace_rival_id = None
        self._outfit_index = None

    def __repr__(self):
        return '{} on {}'.format(type(self).__name__, self._get_sim())

    def _get_sim(self):
        return self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)

    @property
    def sim_info(self):
        return self._sim_info

    @property
    def seen_scholarship_info(self):
        return self._seen_scholarship_info

    @property
    def follow_enabled(self):
        return self._follow_enabled

    @follow_enabled.setter
    def follow_enabled(self, value):
        self._follow_enabled = value

    @property
    def career_event_manager(self):
        return self._career_event_manager

    @property
    def current_level_tuning(self):
        return self._current_track.career_levels[self._level]

    @property
    def next_level_tuning(self):
        next_level = self._level + 1
        if next_level < len(self._current_track.career_levels):
            return self._current_track.career_levels[next_level]

    @property
    def previous_level_tuning(self):
        previous_level = self._level - 1
        if previous_level >= 0:
            return self._current_track.career_levels[previous_level]

    @property
    def current_track_tuning(self):
        return self._current_track

    @property
    def level(self):
        return self._level

    @property
    def user_level(self):
        return self._user_level

    @property
    def overmax_level(self):
        return self._overmax_level

    @property
    def has_attended_first_day(self):
        return self._has_attended_first_day

    @property
    def days_worked_statistic(self):
        return self._sim_info.get_statistic(self._days_worked_statistic_type)

    @property
    def active_days_worked_statistic(self):
        return self._sim_info.get_statistic(self._active_days_worked_statistic_type)

    @property
    def join_time(self):
        return self._join_time

    def add_work_performance(self, amount, interaction=None):
        stat_tracker = self._sim_info.statistic_tracker
        if stat_tracker is not None:
            stat_type = self.current_level_tuning.performance_stat
            performance_stat = stat_tracker.get_statistic(stat_type)
            if performance_stat is None:
                performance_stat = self._sim_info.statistic_tracker.add_statistic(stat_type)
            if performance_stat is not None:
                performance_stat.add_value(amount, interaction)

    @property
    def work_performance(self):
        stat_type = self.current_level_tuning.performance_stat
        if self._sim_info.statistic_tracker is not None:
            performance_stat = self._sim_info.statistic_tracker.get_statistic(stat_type)
            if performance_stat is not None:
                return performance_stat.get_value()
        return stat_type.default_value

    @property
    def pto(self):
        pto_commodity_instance = self._sim_info.get_statistic(self.pto_commodity, add=False)
        if pto_commodity_instance is not None:
            return int(pto_commodity_instance.get_value())
        return int(self.initial_pto)

    @property
    def requested_day_off_reason(self):
        return self._requested_day_off_reason

    @property
    def requested_day_off(self):
        return self._requested_day_off_reason is not career_ops.CareerTimeOffReason.NO_TIME_OFF

    @property
    def taking_day_off_reason(self):
        return self._taking_day_off_reason

    @property
    def taking_day_off(self):
        return self._taking_day_off_reason is not career_ops.CareerTimeOffReason.NO_TIME_OFF

    @property
    def currently_at_work(self):
        return self._at_work

    @property
    def is_at_active_event(self):
        return self._career_event_manager is not None

    @property
    def is_late(self):
        if self.is_work_time and (self.currently_at_work or self.on_assignment):
            return False
        late_time = self.get_late_time()
        if late_time is None:
            return False
        else:
            now = services.time_service().sim_now
            if now < late_time:
                return False
        return True

    @property
    def is_work_time(self):
        if self._current_work_start is None:
            return False
        else:
            current_time = services.time_service().sim_now
            if current_time.time_between_week_times(self._current_work_start, self._current_work_end):
                return True
        return False

    @property
    def icon_override(self):
        return self._icon_override

    @icon_override.setter
    def icon_override(self, value):
        if self._icon_override != value:
            self._icon_override = value

    @property
    def outfit_index(self) -> 'Optional[int]':
        return self._outfit_index

    def get_customer_lot_id(self):
        gig = self.get_current_gig()
        if gig is not None:
            return gig.get_customer_lot_id()

    def on_scholarship_info_shown(self):
        self._seen_scholarship_info = True

    def get_is_quittable_shift(self, schedule_shift_type=CareerShiftType.ALL_DAY, career_category=None):
        if career_category == CareerCategory.TeenSideHustle or self.career_category == CareerCategory.TeenPartTime:
            return True
        elif schedule_shift_type == self._current_shift_type or schedule_shift_type == CareerShiftType.ALL_DAY or self._current_shift_type == CareerShiftType.ALL_DAY:
            return True
        return False

    def is_time_during_shift(self, time=DEFAULT):
        if self._work_scheduler is None and self._work_scheduler_override is None:
            return True
        if self.on_assignment:
            return True
        time = services.time_service().sim_now if time is DEFAULT else time
        all_busy_times_iter = self._get_work_scheduler().get_schedule_entries()
        for (start_time, end_time) in all_busy_times_iter:
            if time.time_between_week_times(start_time, end_time):
                return True
        return False

    def get_current_agent(self):
        sim = self._sim_info
        for agent_trait in self.current_level_tuning.agents_available:
            if sim.has_trait(agent_trait):
                return agent_trait

    def clear_current_agent(self):
        agent_trait = self.get_current_agent()
        if agent_trait is not None:
            self._sim_info.remove_trait(agent_trait)

    def _get_work_scheduler(self):
        if self._work_scheduler_override is not None:
            return self._work_scheduler_override
        return self._work_scheduler

    @property
    def start_time(self):
        return self._current_work_start

    @property
    def current_work_duration(self):
        return self._current_work_duration

    @property
    def on_assignment(self):
        if self._active_assignments:
            return True
        return False

    @property
    def active_assignments(self):
        return self._active_assignments

    @property
    def player_rewards_deferred(self):
        return self._player_rewards_deferred

    @property
    def schedule_shift_type(self):
        return self._current_shift_type

    def defer_player_rewards(self):
        self._player_rewards_deferred = True

    def get_late_time(self):
        if not self.is_work_time:
            return
        time_before_late = self._current_work_duration*(1 - self.current_level_tuning.performance_metrics.full_work_day_percent*PERCENT_FLOAT_CONVERSION)
        late_time = self._current_work_start + time_before_late
        return late_time

    @flexmethod
    def is_career_available(cls, inst, sim_info=DEFAULT, from_join=False):
        if inst is not None and not inst._career_location.is_valid_career_location():
            return False
        inst_or_cls = inst if inst is not None else cls
        sim_info = inst_or_cls.sim_info if sim_info is DEFAULT else sim_info
        if from_join or inst_or_cls.career_category != CareerCategory.TeenSideHustle and (inst_or_cls.allow_multiple_careers or any(career.guid64 != inst_or_cls.guid64 and (career.career_category != CareerCategory.AdultPartTime and (career.career_category != CareerCategory.Invalid and (career.career_category != CareerCategory.TeenSideHustle and career.career_category == inst_or_cls.career_category))) for career in sim_info.career_tracker)):
            return False
        resolver = SingleSimResolver(sim_info)
        return inst_or_cls.career_availablity_tests.run_tests(resolver)

    @flexmethod
    def is_career_selectable(cls, inst, sim_info=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        sim_info = inst_or_cls.sim_info if sim_info is DEFAULT else sim_info
        resolver = SingleSimResolver(sim_info)
        return inst_or_cls.career_selectable_tests.run_tests(resolver, search_for_tooltip=True)

    @flexmethod
    def is_valid_career(cls, inst, sim_info=DEFAULT, from_join=False):
        inst_or_cls = inst if inst is not None else cls
        if not inst_or_cls.is_career_available(sim_info=sim_info, from_join=from_join):
            return False
        return inst_or_cls.is_career_selectable(sim_info=sim_info)

    def get_all_aspirations(self):
        aspirations = set()
        promotion_milestone = self.current_level_tuning.aspiration
        if promotion_milestone is not None:
            aspirations.add(promotion_milestone)
        aspirations.update(self.aspirations_to_activate)
        return aspirations

    def _populate_work_state_time_off_msg(self, msg, reason, enable_go_to_work=False):
        reason_text = self.career_messages.career_time_off_messages[reason]
        if reason_text is not None:
            panel_string = reason_text.text
            tooltip_string = reason_text.tooltip
            pto = self.pto
            if panel_string is not None:
                msg.panel_string = panel_string(self._sim_info, pto)
            if tooltip_string is not None:
                msg.tooltip_string = tooltip_string(self._sim_info, pto)
        msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_TIME_OFF
        msg.enable_go_to_work = enable_go_to_work

    def create_work_state_msg(self):
        msg = DistributorOps_pb2.SetAtWorkInfo()
        msg.career_uid = self.guid64
        if self.is_work_time:
            if self.taking_day_off:
                self._populate_work_state_time_off_msg(msg, self.taking_day_off_reason, enable_go_to_work=not self._sim_info.is_in_travel_group(group_type=FileSerialization_pb2.TravelGroupData.GROUPTYPE_VACATION))
            elif self.currently_at_work or self.on_assignment:
                if self._career_session_extended:
                    msg.end_time_override = self._current_work_end.absolute_ticks()
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_ATTENDING
            elif self.is_late:
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_LATE
                msg.enable_go_to_work = True
            else:
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_AVAILABLE
                msg.enable_go_to_work = True
        elif self.career_panel_type == CareerPanelType.UNIVERSITY_COURSE and not self._sim_info.is_in_travel_group(group_type=FileSerialization_pb2.TravelGroupData.GROUPTYPE_VACATION):
            degree_tracker = self._sim_info.degree_tracker
            if not degree_tracker.course_infos:
                msg.enable_go_to_work = True
        elif self.career_panel_type == CareerPanelType.FREELANCE_CAREER:
            msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_OVER
        elif self.requested_day_off and self.requested_day_off_reason != career_ops.CareerTimeOffReason.WORK_FROM_HOME:
            self._populate_work_state_time_off_msg(msg, self.requested_day_off_reason)
        elif self._sim_info.is_in_travel_group(group_type=FileSerialization_pb2.TravelGroupData.GROUPTYPE_VACATION):
            if self.pto > 0:
                self._populate_work_state_time_off_msg(msg, career_ops.CareerTimeOffReason.PTO)
            else:
                self._populate_work_state_time_off_msg(msg, career_ops.CareerTimeOffReason.MISSING_WORK)
        else:
            msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_OVER
        msg.enable_go_to_work_early = self.can_work_early()
        if self.on_assignment:
            if self._assignment_late:
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_ASSIGNMENT_LATE
            elif self.has_completed_active_assignments:
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_OVER
            elif not self.has_attended_first_day:
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_OVER
            else:
                msg.work_state = DistributorOps_pb2.SetAtWorkInfo.WORKDAY_ASSIGNMENT
        return msg

    @property
    def career_session_extended(self):
        return self._career_session_extended

    @property
    def auto_work(self):
        return self._auto_work

    def request_day_off(self, reason):
        if self.is_work_time and not self.is_late:
            if reason == CareerTimeOffReason.WORK_FROM_HOME:
                assignments_to_offer = self.get_assignments_to_offer(just_accepted=False)
                self._offered_assignment_ids = set(assignment.guid64 for assignment in assignments_to_offer)
                self._start_work_from_home()
                return
            self._taking_day_off_reason = reason
            self.resend_at_work_info()
            self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_DAY_OFF)
            return
        self._requested_day_off_reason = reason
        self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_DAY_OFF)
        self.resend_career_data()
        self.resend_at_work_info()

    def add_pto(self, days):
        initial_pto_value = self.pto
        pto_commodity = self._sim_info.get_statistic(self.pto_commodity, add=True)
        pto_commodity.add_value(days)
        final_pto_value = self.pto
        if days < 0:
            self._pto_taken += days
        delta = final_pto_value - initial_pto_value
        return delta

    def resend_career_data(self):
        career_tracker = self._sim_info.career_tracker
        if career_tracker is None:
            return
        career_tracker.resend_career_data()

    def resend_at_work_info(self):
        career_tracker = self._sim_info.career_tracker
        if career_tracker is None:
            return
        career_tracker.resend_at_work_infos()
        client = services.client_manager().get_client_by_household_id(self._sim_info._household_id)
        if client is not None:
            client.selectable_sims.notify_dirty()

    def send_assignment_update(self, gig_id=None, objective_id=None):
        op = distributor.ops.DisplayCareerTooltip(self.guid64, self._sim_info.id, gig_id, objective_id)
        distributor.system.Distributor.instance().add_op(self._sim_info, op)

    def get_career_entry_data(self, career_history=None, career_track=None, user_level_override=None, career_level_override=None):
        if user_level_override is not None:
            return self.get_career_entry_level_from_user_level(user_level_override)
        if career_level_override is not None:
            if not isinstance(self, career_level_override.career):
                logger.error("Can't get entry data for career level not in career. Level: {}, career: {}", career_level_override, self)
            else:
                return (career_level_override.level, career_level_override.user_level, career_level_override.track)
        resolver = SingleSimResolver(self._sim_info)
        return next(self.get_career_entry_level(career_track=career_track, career_history=career_history, resolver=resolver))

    def get_career_entry_level_from_user_level(self, desired_user_level):
        track = self.start_track
        track_start_level = 1
        while True:
            track_length = len(track.career_levels)
            level = desired_user_level - track_start_level
            if level < track_length:
                user_level = track_start_level + level
                return (level, user_level, track)
            if not track.branches:
                level = track_length - 1
                user_level = track_start_level + level
                return (level, user_level, track)
            track_start_level += track_length
            track = random.choice(track.branches)
            track_length = len(track.career_levels)

    @classmethod
    def get_career_entry_level(cls, career_history=None, career_track=None, resolver=None):
        use_start_track = False
        histories = []
        if career_history is None:
            use_start_track = True
        else:
            histories = [value for ((career_id_key, _), value) in career_history.items() if career_id_key == cls.guid64]
        if histories and use_start_track:
            career_track = cls.start_track
            level = max(int(cls.start_level_modifiers.get_max_modifier(resolver)), 0)
            max_level = len(career_track.career_levels)
            level = sims4.math.clamp(0, level, max_level - 1)
            yield (level, level + 1, career_track)
        else:
            for history in histories:
                if not history.career_track is cls.start_track or len(histories) > 1:
                    pass
                else:
                    new_level = history.level
                    new_user_level = history.user_level
                    time_of_leave = history.time_of_leave
                    current_track = history.career_track
                    new_level -= cls.levels_lost_on_leave
                    new_user_level -= cls.levels_lost_on_leave
                    current_time = services.time_service().sim_now
                    time_gone_from_career = current_time - time_of_leave
                    days_gone_from_career = time_gone_from_career.in_days()
                    levels_to_lose = int(days_gone_from_career/cls.days_to_level_loss)
                    new_level -= levels_to_lose
                    new_user_level -= levels_to_lose
                    new_level = 0
                    minimum_user_level = current_track.career_levels[0].user_level
                    new_user_level = max(new_user_level, minimum_user_level)
                    yield (new_level, new_user_level, current_track)

    @classmethod
    def _loses_level_on_rejoin(cls, resolver=None):
        if resolver is not None and FameTunables.CAREER_HOPPER_PERK is not None:
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(FameTunables.CAREER_HOPPER_PERK.associated_bucks_type, resolver.sim_info_to_test.id)
            if bucks_tracker is not None and bucks_tracker.is_perk_unlocked(FameTunables.CAREER_HOPPER_PERK):
                return False
        return True

    def get_next_wakeup_time(self) -> 'date_and_time.DateAndTime':
        return self.current_level_tuning.wakeup_time

    def get_time_since_last_work_period_ended(self):
        now = services.time_service().sim_now
        work_scheduler = self._get_work_scheduler()
        if work_scheduler is not None:
            return work_scheduler.time_since_last_scheduled_event(now)
        else:
            return

    def get_next_work_time(self, offset_time=None, check_if_can_go_now=False, consider_skipped_shifts=True, ignore_pto=False):
        work_scheduler = self._get_work_scheduler()
        if work_scheduler is None:
            return (None, None, None)
        now = services.time_service().sim_now
        if offset_time:
            now += offset_time
        (best_time, work_data_list) = work_scheduler.time_until_next_scheduled_event(now, schedule_immediate=check_if_can_go_now)
        work_data = work_data_list[0]
        start_time = now + best_time
        if consider_skipped_shifts:
            if self.requested_day_off and not ignore_pto:
                valid_start_time = start_time + TimeSpan.ONE
            else:
                valid_start_time = self.get_valid_first_work_day_time()
            if start_time < valid_start_time:
                (best_time, work_data_list) = work_scheduler.time_until_next_scheduled_event(valid_start_time, schedule_immediate=False)
                best_time += valid_start_time - now
                work_data = work_data_list[0]
                start_time = now + best_time
        end_time = now.time_of_next_week_time(work_data.end_time)
        return (best_time, start_time, end_time)

    def get_valid_first_work_day_time(self):
        if self._join_time is None:
            return DATE_AND_TIME_ZERO
        delay = clock.interval_in_sim_minutes(self.initial_delay)
        if self.is_course_slot:
            degree_tracker = self._sim_info.degree_tracker
            if degree_tracker is not None:
                term_start_time = degree_tracker.get_pending_start_of_term_time()
                if term_start_time is not None:
                    return term_start_time
        return self._join_time + delay

    def should_skip_next_shift(self, check_if_can_go_now=False):
        if self.requested_day_off and self.requested_day_off_reason != CareerTimeOffReason.WORK_FROM_HOME:
            return True
        (_, start, _) = self.get_next_work_time(check_if_can_go_now=check_if_can_go_now, consider_skipped_shifts=False)
        if start is None:
            return False
        elif start > self.get_valid_first_work_day_time():
            return False
        return True

    def get_career_location(self):
        return self._career_location

    def get_company_name(self):
        return self._career_location.get_company_name()

    def award_deferred_promotion_rewards(self):
        self._give_rewards_for_skipped_levels(starting_level=0)
        self._player_rewards_deferred = False
        self._sim_info.career_tracker.update_history(self)

    def _give_rewards_for_skipped_levels(self, starting_level=None, disallowed_reward_types=(), force_rewards_to_sim_info_inventory=False):
        if starting_level is None:
            level_of_last_reward = self._sim_info.career_tracker.get_highest_level_reached_for_track(self.guid64, self._current_track.guid64)
        else:
            level_of_last_reward = starting_level
        track = self.current_track_tuning
        level = self.level
        user_level = self.user_level
        while user_level > level_of_last_reward:
            reward = track.career_levels[level].promotion_reward
            if reward is not None:
                logger.info('Giving {} reward {} to {}', 'deferred' if self.player_rewards_deferred else 'skipped', reward, self.sim_info, owner='jdimailig')
                reward.give_reward(self._sim_info, disallowed_reward_types=disallowed_reward_types, force_rewards_to_sim_info_inventory=force_rewards_to_sim_info_inventory)
            user_level -= 1
            level -= 1
            if level < 0:
                if track.parent_track is None:
                    break
                track = track.parent_track
                level = len(track.career_levels) - 1

    def generate_outfit(self, force_generate:'bool'=False) -> 'Optional[int]':
        if self.has_outfit():
            if self._outfit_index is not None:
                if not force_generate:
                    return self._outfit_index
            else:
                self._outfit_index = self._sim_info.career_tracker.get_first_available_outfit_index()
            work_outfit = self.current_level_tuning.get_work_outfit(self.sim_info)
            work_outfit.outfit_generator(self.sim_info, OutfitCategory.CAREER, outfit_index=self._outfit_index)
            return self._outfit_index

    def join_career(self, career_history=None, career_track=None, user_level_override=None, career_level_override=None, give_skipped_rewards=True, defer_rewards=False, schedule_shift_override=CareerShiftType.ALL_DAY, show_join_msg=True, disallowed_reward_types=(), force_rewards_to_sim_info_inventory=False, defer_first_assignment=False, schedule_init_only=False, allow_outfit_generation=True, show_icon_override_picker=True, owner_id=None):
        (new_level, new_user_level, current_track) = self.get_career_entry_data(career_history=career_history, user_level_override=user_level_override, career_level_override=career_level_override)
        if career_track is None:
            career_track = current_track
        if defer_rewards:
            self.defer_player_rewards()
        self._current_track = career_track
        self._join_time = services.time_service().sim_now
        self._level = new_level
        self._user_level = new_user_level
        self._current_shift_type = schedule_shift_override
        self._load_days_worked_commodities(career_history, career_track)
        self._reset_career_objectives(self._current_track, new_level)
        starting_level = self._sim_info.career_tracker.get_highest_level_reached_for_track(self.guid64, self._current_track.guid64)
        self._sim_info.career_tracker.update_history(self)
        self.career_start(schedule_init_only=schedule_init_only, allow_outfit_generation=allow_outfit_generation, test_event_origin=TestEventCareersOrigin.JOIN_CAREER)
        if self.icon_override_picker_interaction is None:
            show_icon_override_picker = False
        if not show_icon_override_picker:
            self._setup_assignments_for_career_joined(defer_assignment=defer_first_assignment)
        resolver = SingleSimResolver(self._sim_info)
        for loot in self.current_level_tuning.loot_on_join:
            loot.apply_to_resolver(resolver)
        if give_skipped_rewards:
            self._give_rewards_for_skipped_levels(starting_level=starting_level, disallowed_reward_types=disallowed_reward_types, force_rewards_to_sim_info_inventory=force_rewards_to_sim_info_inventory)
        self._send_telemetry(TELEMETRY_HOOK_CAREER_START)
        join_career_notification = self.career_messages.join_career_notification
        if show_icon_override_picker or UIUtils.get_hide_selected_notification_status() or show_join_msg and self.display_career_info and join_career_notification is not None:
            (_, first_work_time, _) = self.get_next_work_time()
            if first_work_time is not None:
                self.send_career_message(join_career_notification, first_work_time)
        self.add_coworker_relationship_bit()
        self._add_career_knowledge()
        if show_icon_override_picker:
            sim = self._sim_info.get_sim_instance()
            if sim is None:
                return
            context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            enqueue_result = sim.push_super_affordance(self.icon_override_picker_interaction, sim, context, target_career=self, defer_assignment=defer_first_assignment)
            if not enqueue_result:
                logger.error('Push icon override picker failed.')

    def career_start(self, is_load=False, is_level_change=False, schedule_init_only=False, allow_outfit_generation=True, test_event_origin=TestEventCareersOrigin.UNSPECIFIED):
        if self.career_messages.career_early_warning_time is not None:
            early_warning_time_span = date_and_time.create_time_span(hours=self.career_messages.career_early_warning_time)
        else:
            early_warning_time_span = None
        schedule_immediate = False if self.initial_delay else True
        self._work_scheduler = self.current_level_tuning.schedule(self, start_callback=self._start_work_callback, schedule_immediate=schedule_immediate, early_warning_callback=self.early_warning_callback, early_warning_time_span=early_warning_time_span, schedule_shift_type=self._current_shift_type, init_only=schedule_init_only)
        self._add_performance_statistics()
        self._add_reputation_statistics()
        if is_load:
            self.restore_career_session()
            self.restore_tones()
        else:
            sim = self._get_sim()
            if self.has_outfit():
                sim_info = None if sim is None else sim.sim_info
                work_outfit = self.current_level_tuning.get_work_outfit(sim_info)
                if work_outfit.generate_on_level_change or not is_level_change:
                    self.generate_outfit(force_generate=True)
            if allow_outfit_generation and sim is not None:
                sim.update_sleep_schedule()
            services.get_event_manager().process_event(test_events.TestEvent.CareerEvent, sim_info=self._sim_info, career=self, track=self.current_track_tuning, level=self.level, test_event_origin=test_event_origin)
            aspiration_tracker = self._sim_info.aspiration_tracker
            if not is_level_change:
                for aspiration in self.aspirations_to_activate:
                    aspiration_tracker.reset_milestone(aspiration)
                    aspiration.register_callbacks()
                    aspiration_tracker.process_test_events_for_aspiration(aspiration)
            sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if aspiration_tracker is not None and sim is not None:
                self.create_objects()
        self._remove_statistic_metric_listeners()
        self._add_statistic_metric_listeners()
        self._add_trait_listener()

    def create_objects(self):
        object_creation_datas = self.current_level_tuning.object_create_on_join
        if not object_creation_datas:
            return
        if self._sim_info.is_npc:
            return
        guid = self.current_level_tuning.guid
        if self._guid_to_claimed_object_ids:
            if guid in self._guid_to_claimed_object_ids:
                return
        else:
            self._guid_to_claimed_object_ids = {}
        self._guid_to_claimed_object_ids[guid] = set()
        resolver = SingleSimResolver(self._sim_info)
        for creation_data in object_creation_datas:
            if creation_data.require_claim:
                creation_data.initialize_helper(resolver)
                created_object = creation_data.create_object(resolver)
                if created_object:
                    self._guid_to_claimed_object_ids[guid].add(created_object.id)

    def _destroy_claimed_objects(self, guid):
        if self._guid_to_claimed_object_ids:
            object_manager = services.object_manager()
            inventory_manager = services.inventory_manager()
            if guid in self._guid_to_claimed_object_ids:
                for object_id in self._guid_to_claimed_object_ids[guid]:
                    object_manager.set_unclaimed_item(object_id)
                    target = object_manager.get(object_id)
                    if target is None:
                        target = inventory_manager.get(object_id)
                        if target is None:
                            pass
                        elif target.in_use:
                            target.transient = True
                        else:
                            target.destroy(source=self, cause='destroying claimed objects for guid {}'.format(guid), fade_duration=ClientObjectMixin.FADE_DURATION)
                    elif target.in_use:
                        target.transient = True
                    else:
                        target.destroy(source=self, cause='destroying claimed objects for guid {}'.format(guid), fade_duration=ClientObjectMixin.FADE_DURATION)
                del self._guid_to_claimed_object_ids[guid]
                if not self._guid_to_claimed_object_ids:
                    self._guid_to_claimed_object_ids = None

    def career_stop(self, for_travel=False, is_level_change=False):
        if self._work_scheduler is not None:
            self._work_scheduler.destroy()
            if not for_travel:
                self._work_scheduler = None
        if self._current_gigs and not (for_travel or is_level_change):
            self.clear_all_gigs()
        if self._work_scheduler_override is not None:
            self._work_scheduler_override.destroy()
            if not for_travel:
                self._work_scheduler_override = None
        self._clear_career_alarms()
        self._remove_statistic_metric_listeners()
        self._remove_trait_listener()
        if not for_travel:
            self._remove_performance_statistics()
            self._destroy_claimed_objects(self.current_level_tuning.guid)

    def _clear_career_alarms(self):
        if self._end_work_handle is not None:
            alarms.cancel_alarm(self._end_work_handle)
            self._end_work_handle = None
        if self._late_for_work_handle is not None:
            alarms.cancel_alarm(self._late_for_work_handle)
            self._late_for_work_handle = None
        if self._assignment_offering_handle is not None:
            alarms.cancel_alarm(self._assignment_offering_handle)
            self._assignment_offering_handle = None

    def _add_performance_statistics(self):
        tuning = self.current_level_tuning
        sim_info = self._sim_info
        tracker = sim_info.get_tracker(tuning.performance_stat)
        tracker.add_statistic(tuning.performance_stat)
        for metric in tuning.performance_metrics.statistic_metrics:
            tracker = sim_info.get_tracker(metric.statistic)
            tracker.add_statistic(metric.statistic)

    def _remove_performance_statistics(self):
        tuning = self.current_level_tuning
        sim_info = self._sim_info
        sim_info.remove_statistic(tuning.performance_stat)
        for metric in tuning.performance_metrics.statistic_metrics:
            sim_info.remove_statistic(metric.statistic)

    def _add_reputation_statistics(self):
        if self.reputation_stat is None:
            return
        tracker = self._sim_info.get_tracker(self.reputation_stat)
        tracker.add_statistic(self.reputation_stat)

    def _remove_pto_commodity(self):
        sim_info = self._sim_info
        sim_info.remove_statistic(self.pto_commodity)

    def _remove_days_worked_commodities(self):
        sim_info = self._sim_info
        sim_info.remove_statistic(self._days_worked_statistic_type)
        sim_info.remove_statistic(self._active_days_worked_statistic_type)

    def _load_days_worked_commodities(self, career_history, career_track):
        if self.guid64 in career_history:
            history = career_history[self.guid64]
            if history is not None and career_track.guid64 in history:
                track_history = history[career_track.guid64]
                self.days_worked_statistic.set_value(track_history.days_worked)
                self.active_days_worked_statistic.set_value(track_history.active_days_worked)

    def _reset_performance_statistics(self):
        tuning = self.current_level_tuning
        sim_info = self._sim_info
        sim_info.remove_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE)
        homework_percentage = self.get_homework_help_percentage()
        for metric in tuning.performance_metrics.statistic_metrics:
            if metric.reset_at_end_of_work:
                tracker = sim_info.get_tracker(metric.statistic)
                if tracker is None:
                    logger.error('Could not find statistic tracker for statistic {} when trying to reset performance statistic. Career: {} SimInfo:{}', metric.statistic, self, sim_info, owner='nsavalani')
                    return
                new_value = metric.statistic.initial_value
                if homework_percentage:
                    new_value = metric.statistic.min_value + (metric.statistic.max_value + abs(metric.statistic.min_value))*homework_percentage
                tracker.set_value(metric.statistic, new_value)

    def _on_statistic_metric_changed(self, stat_type):
        self.resend_career_data()
        self._refresh_statistic_metric_listeners()
        services.get_event_manager().process_event(test_events.TestEvent.WorkDailyTaskProgress, self._sim_info)

    def _add_statistic_metric_listeners(self):
        metrics = self.current_level_tuning.performance_metrics
        for metric in metrics.statistic_metrics:
            tracker = self._sim_info.get_tracker(metric.statistic)
            value = tracker.get_value(metric.statistic)
            (lower_threshold, upper_threshold) = self._get_statistic_progress_thresholds(metric.statistic, value)
            if lower_threshold:
                threshold = Threshold(lower_threshold.threshold, operator.lt)
                handle = tracker.create_and_add_listener(metric.statistic, threshold, self._on_statistic_metric_changed)
                self._statistic_down_listeners[metric.statistic] = handle
            if upper_threshold:
                threshold = Threshold(upper_threshold.threshold, operator.ge)
                handle = tracker.create_and_add_listener(metric.statistic, threshold, self._on_statistic_metric_changed)
                self._statistic_up_listeners[metric.statistic] = handle

    def _remove_statistic_metric_listeners(self):
        for (stat_type, handle) in itertools.chain(self._statistic_down_listeners.items(), self._statistic_up_listeners.items()):
            tracker = self._sim_info.get_tracker(stat_type)
            tracker.remove_listener(handle)
        self._statistic_down_listeners = {}
        self._statistic_up_listeners = {}

    def _refresh_statistic_metric_listeners(self):
        self._remove_statistic_metric_listeners()
        self._add_statistic_metric_listeners()

    def _add_trait_listener(self):
        services.get_event_manager().register(self, (TestEvent.TraitAddEvent, TestEvent.TraitRemoveEvent))

    def _remove_trait_listener(self):
        services.get_event_manager().unregister(self, (TestEvent.TraitAddEvent, TestEvent.TraitRemoveEvent))

    def handle_event(self, sim_info, event, resolver):
        if sim_info is self._sim_info:
            self.resend_career_data()

    def _get_performance_tooltip(self):
        loc_strings = []
        metrics = self.current_level_tuning.performance_metrics
        if metrics.performance_tooltip is not None:
            loc_strings.append(metrics.performance_tooltip)
        for metric in metrics.statistic_metrics:
            text = metric.tooltip_text
            if text is not None and text.general_description:
                stat = self._sim_info.get_statistic(metric.statistic, add=False)
                (lower_threshold, _) = self._get_statistic_progress_thresholds(metric.statistic, stat.get_value() if stat is not None else metric.statistic.default_value)
                if lower_threshold:
                    description = text.general_description(lower_threshold.text)
                else:
                    description = text.general_description()
                loc_strings.append(description)
        if loc_strings:
            return LocalizationHelperTuning.get_new_line_separated_strings(*loc_strings)

    def _get_statistic_progress_thresholds(self, stat_type, value):
        metrics = self.current_level_tuning.performance_metrics
        for metric in metrics.statistic_metrics:
            if metric.statistic is stat_type:
                text = metric.tooltip_text
                if text is not None:
                    lower_threshold = None
                    upper_threshold = None
                    for threshold in text.thresholded_descriptions:
                        if lower_threshold is None or threshold.threshold > lower_threshold.threshold:
                            lower_threshold = threshold
                        if not upper_threshold is None:
                            if threshold.threshold < upper_threshold.threshold:
                                upper_threshold = threshold
                        upper_threshold = threshold
                    return (lower_threshold, upper_threshold)
                break
        return (None, None)

    def _get_common_performance_change(self):
        metrics = self.current_level_tuning.performance_metrics
        gain = 0
        loss = 0

        def add_metric(value):
            nonlocal gain, loss
            if value >= 0:
                gain += value
            else:
                loss -= value

        def multiple_metric(value):
            nonlocal gain
            gain *= value

        for commodity_metric in metrics.commodity_metrics:
            tracker = self._sim_info.get_tracker(commodity_metric.commodity)
            curr_value = tracker.get_user_value(commodity_metric.commodity)
            if curr_value is not None and commodity_metric.threshold.compare(curr_value):
                add_metric(commodity_metric.performance_mod)
        for metric in metrics.statistic_metrics:
            if metric.performance_curve is not None:
                stat = self._sim_info.get_statistic(metric.statistic, add=False)
                if stat is not None:
                    stat_value = stat.get_value()
                    performance_mod = metric.performance_curve.get(stat_value)
                    add_metric(performance_mod)
        tested_performance_multipliers = []
        if metrics.tested_metrics:
            resolver = SingleSimResolver(self._sim_info)
            for metric in metrics.tested_metrics:
                if metric.tests.run_tests(resolver):
                    add_metric(metric.performance_mod)
                    if metric.performance_stat_multiplier:
                        tested_performance_multipliers.append(metric.performance_stat_multiplier)
        completed_objectives = 0
        promotion_milestone = self.current_level_tuning.aspiration
        if promotion_milestone is not None:
            aspiration_tracker = self._sim_info.aspiration_tracker
            for objective in promotion_milestone.objectives:
                if aspiration_tracker.objective_completed(objective):
                    completed_objectives += 1
        objective_mod = completed_objectives*metrics.performance_per_completed_goal
        add_metric(objective_mod)
        return (gain, loss, tested_performance_multipliers)

    def _handle_post_reset_loot(self):
        end_of_day_loot = self.current_level_tuning.end_of_day_loot
        resolver = SingleSimResolver(self._sim_info)
        for loot in end_of_day_loot:
            loot.apply_to_resolver(resolver)

    def apply_performance_change(self, time_elapsed, tone_multiplier):
        if self.current_work_duration is None:
            logger.error('Career {} attempted to apply performance with no work duration set', self)
            return
        metrics = self.current_level_tuning.performance_metrics
        (gain, loss, tested_performance_multipliers) = self._get_common_performance_change()

        def add_metric(value):
            nonlocal gain, loss
            if value >= 0:
                gain += value
            else:
                loss -= value

        add_metric(metrics.base_performance)
        active_mood = self._sim_info.get_mood()
        for mood_metric in metrics.mood_metrics:
            if active_mood is mood_metric.mood:
                add_metric(mood_metric.performance_mod)
                break
        statistic_tracker = self._sim_info.statistic_tracker
        if statistic_tracker is not None:
            total = gain*tone_multiplier - loss
            delta = total*time_elapsed.in_ticks()/self._current_work_duration.in_ticks()
            if tested_performance_multipliers:
                delta = self._apply_tested_performance_multipliers(tested_performance_multipliers, delta)
            self.add_work_performance(delta)
            session_stat = statistic_tracker.get_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE, add=True)
            if session_stat is not None:
                session_stat.add_value(delta)

    def _apply_tested_performance_multipliers(self, performance_multipliers, delta):
        for performance_multiplier in performance_multipliers:
            if not performance_multiplier.apply_direction == StatisticChangeDirection.DECREASE:
                if performance_multiplier.apply_direction == StatisticChangeDirection.BOTH:
                    delta *= performance_multiplier.multiplier
            delta *= performance_multiplier.multiplier
        return delta

    def apply_assignment_performance_change(self, total_assignments):
        metrics = self.current_level_tuning.performance_metrics
        (gain, loss, _) = self._get_common_performance_change()

        def add_metric(value):
            nonlocal gain, loss
            if value >= 0:
                gain += value
            else:
                loss -= value

        add_metric(metrics.daily_assignment_performance)
        total = gain - loss
        delta = total/total_assignments
        self.add_work_performance(delta)
        statistic_tracker = self._sim_info.statistic_tracker
        if statistic_tracker is not None:
            session_stat = statistic_tracker.get_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE, add=True)
            if session_stat is not None:
                session_stat.add_value(delta)

    def get_busy_time_periods(self):
        busy_times = []
        if self._work_scheduler is not None:
            busy_times.extend(self._work_scheduler.get_schedule_times())
            for time_period in self.current_level_tuning.additional_unavailable_times:
                start_time = time_period.start_time()
                end_time = start_time + clock.interval_in_sim_hours(time_period.period_duration)
                busy_times.append((start_time.absolute_ticks(), end_time.absolute_ticks()))
        if self._work_scheduler_override is not None:
            busy_times.extend(self._work_scheduler_override.get_schedule_times())
        return busy_times

    def _should_automatically_use_pto(self):
        return self._sim_info.is_in_travel_group(group_type=FileSerialization_pb2.TravelGroupData.GROUPTYPE_VACATION) and self.pto > 0

    def _start_work_from_home(self):
        if not self._offered_assignment_ids:
            logger.error('Career {} at level {} has no available assignments', self, self.current_level_tuning.__name__)
            return
        aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
        for assignment_guid in self._offered_assignment_ids:
            assignment = aspiration_manager.get(assignment_guid)
            if assignment is not None:
                self._active_assignments.append(assignment)
        if not self._has_attended_first_day:
            self._has_attended_first_day = True
        self._initialize_assignments(from_load=False, just_accepted=True)
        self._offered_assignment_ids.clear()
        self.resend_at_work_info()
        self.send_assignment_update()
        self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_WORK_FROM_HOME)

    def _on_early_warning_alarm_response(self, dialog):
        response = dialog.response
        if response == RESPONSE_ID_WORK_FROM_HOME:
            self._start_work_from_home()
            self._taking_day_off_reason = CareerTimeOffReason.WORK_FROM_HOME
        elif response == RESPONSE_ID_TAKE_PTO:
            self.request_day_off(CareerTimeOffReason.PTO)
            self.add_pto(-1)
            self.resend_career_data()
        elif response == RESPONSE_ID_CALL_IN_SICK:
            self.request_day_off(CareerTimeOffReason.FAKE_SICK)
        else:
            if self.can_work_early():
                self.go_to_work_early()
                self.resend_at_work_info()
            return

    def _get_early_warning_alarm_responses(self):
        message_tuning = self.career_messages.career_early_warning_alarm
        if message_tuning is None:
            return []
        responses = []
        responses.append(UiDialogResponse(dialog_response_id=RESPONSE_ID_GO_TO_WORK, text=message_tuning.go_to_work_text, ui_request=UiDialogResponse.UiDialogUiRequest.CAREER_GO_TO_WORK))
        if self._offered_assignment_ids:
            responses.append(UiDialogResponse(dialog_response_id=RESPONSE_ID_WORK_FROM_HOME, text=message_tuning.work_from_home_text, ui_request=UiDialogResponse.UiDialogUiRequest.CAREER_WORK_FROM_HOME))
        if self.pto > 0:
            responses.append(UiDialogResponse(dialog_response_id=RESPONSE_ID_TAKE_PTO, text=message_tuning.take_pto_text, ui_request=UiDialogResponse.UiDialogUiRequest.CAREER_TAKE_PTO))
        else:
            responses.append(UiDialogResponse(dialog_response_id=RESPONSE_ID_CALL_IN_SICK, text=message_tuning.call_in_sick_text, ui_request=UiDialogResponse.UiDialogUiRequest.CAREER_CALL_IN_SICK))
        return responses

    def early_warning_callback(self):
        if not services.get_career_service().enabled:
            return
        if self.should_skip_next_shift() or self._should_automatically_use_pto():
            return
        if self._requested_day_off_reason == CareerTimeOffReason.NO_TIME_OFF and not self._current_gigs:
            reason = self._get_drama_node_time_off_reason()
            if reason is None:
                return
            if reason != CareerTimeOffReason.NO_TIME_OFF:
                self._requested_day_off_reason = reason
                self.resend_at_work_info()
                return
        if SicknessTuning.is_child_sim_sick(self._sim_info):
            resolver = SingleSimResolver(self.sim_info)
            for sick_loot in SicknessTuning.LOOT_ACTIONS_ON_CHILD_CAREER_AUTO_SICK:
                sick_loot.apply_to_resolver(resolver)
            return
        if self.early_work_loot is not None:
            resolver = SingleSimResolver(self.sim_info)
            self.early_work_loot.apply_to_resolver(resolver)
        if self.on_assignment:
            evaluation = self._handle_assignment_results()
            self.clear_career_assignments()
            if evaluation is not None and evaluation != Evaluation.ON_TARGET:
                self._requested_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
                self._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
                if evaluation == Evaluation.FIRED:
                    return
                self.resend_career_data()
                (time_till_work, _, _) = self.get_next_work_time()
                time_for_early_warning = date_and_time.create_time_span(hours=self.career_messages.career_early_warning_time)
                if time_till_work > time_for_early_warning:
                    return
        if not self._sim_info.is_selectable:
            self._requested_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
            return
        assignments_to_offer = self.get_assignments_to_offer(just_accepted=False)
        self._offered_assignment_ids = set(assignment.guid64 for assignment in assignments_to_offer)
        if not self._offered_assignment_ids:
            self.send_career_message(self.career_messages.career_early_warning_notification)
            if self.can_work_early():
                self.go_to_work_early()
                self.resend_at_work_info()
        elif self.requested_day_off_reason == CareerTimeOffReason.WORK_FROM_HOME:
            self._start_work_from_home()
        else:
            self._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
            message_tuning = self.career_messages.career_early_warning_alarm
            if message_tuning is not None:
                self.send_career_message(message_tuning.dialog, additional_responses=self._get_early_warning_alarm_responses(), on_response=self._on_early_warning_alarm_response)

    def _get_drama_node_time_off_reason(self):
        (_, _, end_time) = self.get_next_work_time()
        if end_time is None:
            logger.error('Could not get an end time for career {} on sim: {}', self, self._sim_info, owner='madang')
            return
        for drama_node in services.drama_scheduler_service().all_nodes_gen():
            reason = drama_node.get_time_off_reason(self.sim_info, self.career_category, end_time)
            if reason != CareerTimeOffReason.NO_TIME_OFF:
                return reason
        return CareerTimeOffReason.NO_TIME_OFF

    def _career_missing_work_response(self, dialog):
        if dialog.accepted or not dialog.response == ButtonType.DIALOG_RESPONSE_NO_RESPONSE:
            return
        sim = self._sim_info.get_sim_instance()
        if sim is None:
            return
        missing_work = self.career_messages.career_missing_work
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, interactions.priority.Priority.High, insert_strategy=interactions.context.QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
        sim.push_super_affordance(missing_work.affordance, sim, context)
        resolver = sim.get_resolver()
        if len(missing_work.loot) > 0:
            for loot_action in missing_work.loot:
                loot_action.apply_to_resolver(resolver)

    def _late_for_work_callback(self, _):
        self.resend_at_work_info()
        if self.taking_day_off:
            return
        if self.on_assignment:
            return
        if self._rabbit_hole_id and services.get_rabbit_hole_service().is_in_rabbit_hole(self.sim_info.id, self._rabbit_hole_id):
            return
        if self.career_messages.career_missing_work is None:
            return
        self.send_career_message(self.career_messages.career_missing_work.dialog, on_response=self._career_missing_work_response)

    def _start_work_callback(self, scheduler, alarm_data, extra_data):
        if self._at_work:
            return
        if not services.get_career_service().enabled:
            return
        current_time = services.time_service().sim_now
        logger.debug('My Work Time just triggered!, Current Time: {}', current_time)
        current_gig = self.get_current_gig()
        if current_gig and current_gig.treat_work_time_as_due_date():
            self._end_work_at_home_gig(current_gig)
            return
        if self.requested_day_off_reason == CareerTimeOffReason.WORK_FROM_HOME:
            self._requested_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
            if not self.on_assignment:
                assignments_to_offer = self.get_assignments_to_offer(just_accepted=False)
                self._offered_assignment_ids = set(assignment.guid64 for assignment in assignments_to_offer)
                self._start_work_from_home()
        if self.should_skip_next_shift(check_if_can_go_now=True):
            if self.requested_day_off:
                self._taking_day_off_reason = self._requested_day_off_reason
                self._requested_day_off_reason = career_ops.CareerTimeOffReason.NO_TIME_OFF
                self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_DAY_OFF)
            else:
                self._requested_day_off_reason = career_ops.CareerTimeOffReason.NO_TIME_OFF
                self.resend_career_data()
                return
        elif self._sim_info.is_in_travel_group(group_type=FileSerialization_pb2.TravelGroupData.GROUPTYPE_VACATION):
            if self.pto > 0:
                self._taking_day_off_reason = career_ops.CareerTimeOffReason.PTO
                self.add_pto(-1)
            else:
                self._taking_day_off_reason = career_ops.CareerTimeOffReason.MISSING_WORK
            self.resend_career_data()
            self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_DAY_OFF)
        if not self.on_assignment:
            end_time = date_and_time_from_week_time(current_time.week(), alarm_data.end_time)
        else:
            (_, next_work_time, _) = self.get_next_work_time()
            end_time = next_work_time
        if current_time > end_time:
            logger.error("\n                The career {} for {} is about to start a shift with an end time\n                of {}, but it's already {}! Please provide a save and GSI dump\n                and file a DT.\n                ", self, self._sim_info, end_time, current_time, owner='epanero')
            return
        self.start_new_career_session(current_time, end_time)

        def get_situation_jobs(sim):
            situation_manager = services.get_zone_situation_manager()
            return {situation.get_current_job_for_sim(sim) for situation in situation_manager.get_situations_sim_is_in(sim)}

        if not self._sim_info.career_tracker.available_for_work(self):
            return
        if self.taking_day_off or not self._sim_info.is_in_travel_group(group_type=FileSerialization_pb2.TravelGroupData.GROUPTYPE_VACATION):
            sim = self._get_sim()
            situation_jobs = None
            if self._sim_info.is_npc:
                if sim is not None:
                    situation_jobs = get_situation_jobs(sim)
                    for situation_job in situation_jobs:
                        if situation_job is not None and situation_job.participating_npcs_should_ignore_work:
                            return
                self._career_location.on_npc_start_work()
                return
            if sim is not None:
                if situation_jobs is None:
                    situation_jobs = get_situation_jobs(sim)
                for job in situation_jobs:
                    if job is not None and job.confirm_leave_situation_for_work:
                        responses = None
                        if self.pto > 0:
                            pto_response = UiDialogResponse(dialog_response_id=RESPONSE_ID_TAKE_PTO, text=self.career_messages.situation_leave_confirmation.take_pto_button_text)
                            responses = (pto_response,)

                        def on_response(dialog):
                            if dialog.accepted:
                                if self._try_offer_career_event():
                                    return
                                self.put_sim_in_career_rabbit_hole()
                            elif dialog.response == RESPONSE_ID_TAKE_PTO:
                                self.request_day_off(CareerTimeOffReason.PTO)
                                self.add_pto(-1)
                                self.resend_career_data()

                        self.send_career_message(self.career_messages.situation_leave_confirmation.dialog, on_response=on_response, additional_responses=responses)
                        return
            if self._try_offer_career_event():
                return
            if self.on_assignment:
                return
            self.put_sim_in_career_rabbit_hole()

    def _try_offer_career_event(self):
        if services.get_persistence_service().is_save_locked():
            return False
        if self._sim_info.is_npc:
            return False
        if self.allow_active_offlot or not self._sim_info.is_instanced():
            return False
        if not self._follow_enabled:
            return False
        current_gig = self.get_current_gig()
        if self._sim_info in _career_event_overrides:
            career_event = _career_event_overrides.pop(self._sim_info)
        elif current_gig is not None and current_gig.career_events:
            career_event = current_gig.get_random_gig_event()
        else:
            self._prune_stale_career_event_cooldowns()
            resolver = SingleSimResolver(self._sim_info)
            available_events = tuple(event for event in self.career_events if self.is_career_event_on_cooldown(event) or event.tests.run_tests(resolver))
            if not available_events:
                return False
            household = self._sim_info.household
            for sim_info in household.sim_info_gen():
                if any(career.is_at_active_event for career in sim_info.careers.values()):
                    return False
            career_event = random.choice(available_events)
        services.get_career_service().try_add_pending_career_event_offer(self, career_event)
        return True

    def on_career_event_accepted(self, career_event, additional_sims=None, is_additional_sim=False):
        self._start_career_event(career_event, additional_sims, is_additional_sim)
        self._add_career_event_cooldown(career_event)
        self.attend_work(start_tones=False)
        self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_ACTIVE)

    def on_career_event_declined(self, career_event):
        if self.requested_day_off or self.taking_day_off:
            return
        if self.career_event_decline_option == CareerEventDeclineOptions.CAREER_RABBITHOLE:
            self.put_sim_in_career_rabbit_hole()
        elif self.career_event_decline_option == CareerEventDeclineOptions.CANCEL_CURRENT_GIG:
            self.cancel_gig()
        elif self.career_event_decline_option == CareerEventDeclineOptions.DO_NOTHING:
            pass

    def _start_career_event(self, career_event, additional_sims, is_additional_sim):
        self.active_days_worked_statistic.add_value(1)
        self._career_event_manager = CareerEventManager(self)
        self._career_event_manager.start()
        self._career_event_manager.request_career_event(career_event)
        self._career_event_manager.start_top_career_event(additional_sims=additional_sims, is_additional_sim=is_additional_sim)
        self.resend_at_work_info()

    def _end_career_event(self, left_early=False):
        if self._career_event_manager is None:
            logger.error('Trying to end a career event when career {} does not have a career event manager', self)
            return
        current_gig = self.get_current_gig()
        if current_gig is not None and current_gig.extend_current_gig():
            return
        payout = self._career_event_manager.get_career_event_payout_info()
        if payout is None:
            logger.error('Failed to get career event payout info for {}', self)
            return
        if current_gig is not None and current_gig.end_of_gig_dialog is not None:
            self._end_gig_career_event(payout, current_gig)
        else:
            self._end_regular_career_event(payout, left_early)

    def gig_aspiration_completed(self, aspiration):
        for gig in self._current_gigs:
            if aspiration is gig.get_aspiration():
                if self.is_active:
                    if self.is_at_active_event:
                        self._end_career_event()
                else:
                    self._end_work_at_home_gig(gig)
                return

    def score_work_at_home_gig_early(self, gig=None):
        self._end_work_at_home_gig(gig)

    def _end_work_at_home_gig(self, gig):
        if self._has_single_gig():
            gig = self.get_current_gig()
        if gig is None and gig is None:
            logger.error('No gig was specified and there is no single gig on career {}', self)
            return
        money_earned = gig.get_pay(overmax_level=self._overmax_level)
        money_earned = self._get_simolean_trait_bonus_pay(pay=money_earned)
        gig.pay_out_gig(money_earned)
        pto_earned = 0
        self.apply_gig_statistic_changes(gig)
        gig.collect_additional_rewards()
        result = self.evaluate_career_performance(money_earned, pto_earned, gig=gig)
        if result:
            result.display_dialog(self)
        if gig.save_history:
            self._sim_info.career_tracker.add_gig_history(gig)
        self._clear_gig(gig)
        self._first_gig_completed = True

    def _end_gig_career_event(self, payout, gig):
        if self._has_single_gig():
            gig = self.get_current_gig()
        if gig is None and gig is None:
            logger.error('No gig was specified and there is no single gig on career {}', self)
            return
        performance = self.current_level_tuning.performance_metrics.base_performance*payout.performance_multiplier
        self.add_work_performance(performance)
        money_earned = gig.get_pay(payout_multiplier=payout.money_multiplier)
        money_earned = self._get_simolean_trait_bonus_pay(pay=money_earned)
        gig.collect_additional_rewards()
        gig.pay_out_gig(money_earned)
        self.apply_gig_statistic_changes(gig)
        result = self.evaluate_career_performance(money_earned, 0)
        if result is not None:
            if result.evaluation == Evaluation.PROMOTED and not gig.uses_gig_notifications_for_promotions:
                end_of_gig_result = gig.get_end_of_gig_evaluation_result()
                if end_of_gig_result is not None:
                    end_of_gig_result.display_dialog(self)
            result.display_dialog(self)

        def response(dialog):
            if dialog.accepted:
                CareerEventManager.post_career_event_travel(self._sim_info, outfit_change_reason=OutfitChangeReason.DefaultOutfit)

        reputation_change = gig.get_professional_reputation()
        if self._career_event_manager.get_main_zone_id() == services.current_zone_id():
            (end_of_day_dialog, additional_icons) = gig.build_end_gig_dialog(payout)
            end_of_day_dialog.show_dialog(additional_tokens=(money_earned, reputation_change), on_response=response, additional_icons=additional_icons)
        else:
            main_zone_id = self._career_event_manager.get_main_zone_id()
            CareerEventManager.post_career_event_travel(self._sim_info, zone_id_override=main_zone_id, outfit_change_reason=OutfitChangeReason.DefaultOutfit)
        if gig.save_history:
            self._sim_info.career_tracker.add_gig_history(gig)
        self.end_career_event_without_payout()
        self._send_end_of_career_event_telemetry(payout.medal, payout.num_goals_completed)

    def _build_regular_end_of_workday(self, payout, money_earned, pto_earned):
        result = self.evaluate_career_performance(money_earned, pto_earned)
        if result is not None:
            result.display_dialog(self)
        text = payout.text_factory(self._sim_info)
        op = EndOfWorkday(career_uid=self.guid64, score_text=text, level_icon=self._current_track.icon, money_earned=money_earned, paid_time_off_earned=pto_earned)
        if result is not None and result.evaluation == Evaluation.PROMOTED and result.dialog_factory is not None:
            dialog = result.dialog_factory(self._sim_info, resolver=SingleSimResolver(self._sim_info))
            dialog_msg = dialog.build_msg(additional_tokens=self.get_career_text_tokens() + result.dialog_args)
            op.add_promotion_info(self, dialog_msg.text)
        return op

    def _end_regular_career_event(self, payout, left_early):
        work_duration = self._current_work_duration.in_hours()
        now = services.time_service().sim_now
        span_worked = now - self._current_work_start
        hours_worked = min(span_worked.in_hours(), work_duration)
        performance = self.current_level_tuning.performance_metrics.base_performance*payout.performance_multiplier
        if performance > 0:
            performance *= hours_worked/work_duration
        self.add_work_performance(performance)
        (money_earned, pto_earned) = self._collect_rewards(hours_worked, payout.money_multiplier)
        if self.is_multi_sim_active:
            result = self.evaluate_career_performance(money_earned, pto_earned)
            if result is not None:
                result.display_dialog(self)
        else:
            op = self._build_regular_end_of_workday(payout, money_earned, pto_earned)
            main_zone_id = self._career_event_manager.get_main_zone_id()
            if services.current_zone().ui_dialog_service.auto_respond:
                CareerEventManager.post_career_event_travel(self._sim_info, zone_id_override=main_zone_id)
            else:
                services.get_career_service().set_main_career_event_zone_id_and_lock_save(main_zone_id)
                distributor.system.Distributor.instance().add_op(self._sim_info, op)
        self._send_end_of_career_event_telemetry(payout.medal, payout.num_goals_completed)
        for buff in self.BUFFS_LEAVE_WORK:
            self._sim_info.add_buff_from_op(buff_type=buff.buff_type, buff_reason=buff.buff_reason)
        services.get_event_manager().process_event(test_events.TestEvent.WorkdayComplete, sim_info=self._sim_info, career=self, time_worked=span_worked.in_ticks(), money_made=money_earned)
        self._display_end_of_day_reports(left_early, payout)
        self.end_career_event_without_payout()

    def _display_end_of_day_reports(self, left_early, payout):
        report_strings = []
        career_sim_info = self.sim_info
        career_event = self.career_event_manager.get_top_career_event()
        if career_event is None or career_event.end_of_day_reports is None or career_event.end_of_day_results_reported:
            return
        career_event.end_of_day_results_reported = True
        sim_info_performance = career_event.get_end_of_day_result_string_for_active_career(career_sim_info)
        if sim_info_performance is not None:
            report_strings.append(sim_info_performance(career_sim_info))
        else:
            report_strings.append(payout.text_factory(career_sim_info))
        if not left_early:
            household = self.sim_info.household
            for sim_info in household:
                if sim_info is career_sim_info:
                    pass
                else:
                    career_tracker = sim_info.career_tracker
                    current_career = career_tracker.get_currently_at_work_career()
                    if current_career is not None and self.career_event_manager.is_same_current_event(current_career):
                        if current_career.time_until_end_of_work().in_minutes() > 1:
                            pass
                        else:
                            alternate_career_event_manager = current_career.career_event_manager
                            current_career_event = alternate_career_event_manager.get_top_career_event()
                            if current_career_event is not None and not current_career_event.end_of_day_results_reported:
                                current_career_event.end_of_day_results_reported = True
                                performance_string = current_career_event.get_end_of_day_result_string_for_active_career(sim_info)
                                if performance_string is not None:
                                    report_strings.append(performance_string(sim_info))
                                else:
                                    alternate_payout = alternate_career_event_manager.get_career_event_payout_info()
                                    if alternate_payout is not None:
                                        report_strings.append(alternate_payout.text_factory(sim_info))
        career_event.build_end_of_day_notification(self.sim_info, report_strings, left_early)

    def end_career_event_without_payout(self):
        loots = self._career_event_manager.stop()
        self._career_event_manager = None
        self.end_career_session()
        resolver = SingleSimResolver(self._sim_info)
        for loot in loots:
            if loot is not None:
                loot.apply_to_resolver(resolver)
        if self.is_multi_sim_active and (self._sim_info.is_npc or self._sim_info.away_action_tracker is not None):
            self._sim_info.away_action_tracker.reset_to_default_away_action()

    def create_career_event_situations_during_zone_spin_up(self):
        if self._career_event_manager is not None:
            self._career_event_manager.create_career_event_situations_during_zone_spin_up()

    def _add_career_event_cooldown(self, career_event):
        if career_event.cooldown > 0:
            current_day = self.days_worked_statistic.get_value()
            self._career_event_cooldown_map[career_event.guid64] = int(current_day + career_event.cooldown)

    def is_career_event_on_cooldown(self, career_event):
        return career_event.guid64 in self._career_event_cooldown_map

    def _prune_stale_career_event_cooldowns(self):
        current_day = self.days_worked_statistic.get_value()
        self._career_event_cooldown_map = {event_id: day for (event_id, day) in self._career_event_cooldown_map.items() if current_day < day}

    def _end_work_callback(self, _):
        if self.currently_at_work:
            self.leave_work()
        else:
            if self.taking_day_off_reason == CareerTimeOffReason.MISSING_WORK or self.taking_day_off_reason == CareerTimeOffReason.NO_TIME_OFF:
                time_at_work = 0
            else:
                time_at_work = self._current_work_duration.in_hours()
            if not self._sim_info.is_npc:
                self.handle_career_loot(time_at_work)
            self.end_career_session()

    def _create_work_session_alarms(self):
        self._create_end_of_work_day_alarm()
        if self.on_assignment:
            return
        if not self.currently_at_work:
            now = services.time_service().sim_now
            late_time = self.get_late_time()
            if now < late_time:
                if self._late_for_work_handle is not None:
                    self._late_for_work_handle.cancel()
                self._late_for_work_handle = alarms.add_alarm(self, late_time - now + TimeSpan.ONE, self._late_for_work_callback)

    def _create_end_of_work_day_alarm(self):
        if self._end_work_handle is not None:
            self._end_work_handle.cancel()
        self._end_work_handle = alarms.add_alarm(self, self.time_until_end_of_work(), self._end_work_callback)

    def start_new_career_session(self, start_time, end_time):
        self._at_work = False
        self._career_session_extended = False
        gig = self.get_current_gig()
        if gig is not None:
            gig.prep_time_end()
        if not self.on_assignment:
            self._current_work_start = start_time
            self._current_work_end = end_time
            self._current_work_duration = self._current_work_end - self._current_work_start
            self._create_work_session_alarms()
            self.resend_at_work_info()
            if gig is None or gig.odd_job_tuning is None:
                tracker = self._sim_info.get_tracker(self.WORK_SESSION_PERFORMANCE_CHANGE)
                if tracker is None:
                    logger.error('Could not find statistic tracker for statistic {} on starting a new career session. Career: {} SimInfo:{}', self.WORK_SESSION_PERFORMANCE_CHANGE, self, self._sim_info, owner='nsavalani')
                else:
                    self._sim_info.add_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE, self.WORK_SESSION_PERFORMANCE_CHANGE.initial_value)
            if self.is_school_career and not self._sim_info.is_npc:
                self.reset_homework_help()

    def restore_career_session(self):
        for gig in self.get_current_gigs():
            self._set_up_gig_timers(gig)
        if self.is_work_time and not self.on_assignment:
            self._create_work_session_alarms()
        if self._career_event_manager is not None:
            self._career_event_manager.start()
        if self.on_assignment:
            self._initialize_assignments(from_load=True)

    def should_get_homework_help(self, homework_help_enum):
        homework_help_data = self.get_homework_help_data()
        if homework_help_data is None:
            self.set_homework_help_data(ReceiveDailyHomeworkHelp.CHECKED_NO_HELP)
            return False
        valid_region = False
        if homework_help_data.eligible_regions:
            for region_id in homework_help_data.eligible_regions:
                if services.current_region() is Region.REGION_DESCRIPTION_TUNING_MAP.get(region_id):
                    valid_region = True
                    break
        if not valid_region:
            self.set_homework_help_data(ReceiveDailyHomeworkHelp.CHECKED_NO_HELP)
            return False
        should_help = random.random() < homework_help_data.base_chance
        if not should_help:
            self.set_homework_help_data(ReceiveDailyHomeworkHelp.CHECKED_NO_HELP)
            return False
        resolver = SingleSimResolver(self.sim_info)
        dialog = homework_help_data.homework_help_notification(self.sim_info, resolver=resolver)
        dialog.show_dialog()
        self.set_homework_help_data(ReceiveDailyHomeworkHelp.CHECKED_RECEIVE_HELP)
        return True

    def get_homework_help_data(self):
        return self.HOMEWORK_HELP_MAPPING.get(self.sim_info.age)

    def reset_homework_help(self):
        active_household = services.active_household()
        active_household.set_homework_help(Age.CHILD, ReceiveDailyHomeworkHelp.UNCHECKED)
        active_household.set_homework_help(Age.TEEN, ReceiveDailyHomeworkHelp.UNCHECKED)

    def set_homework_help_data(self, status):
        active_household = services.active_household()
        active_household.set_homework_help(self.sim_info.age, status)

    def get_tuned_homework_progress(self):
        return self.get_homework_help_data().progress_percentage

    def get_homework_help_percentage_helper(self, homework_help_enum):
        if homework_help_enum == ReceiveDailyHomeworkHelp.UNCHECKED:
            if not self.should_get_homework_help(homework_help_enum):
                return
            return self.get_tuned_homework_progress()
        if homework_help_enum == ReceiveDailyHomeworkHelp.CHECKED_RECEIVE_HELP:
            return self.get_tuned_homework_progress()
        elif homework_help_enum == ReceiveDailyHomeworkHelp.CHECKED_NO_HELP:
            return

    def get_homework_help_percentage(self):
        if self._sim_info.is_npc:
            return
        if not self.is_school_career:
            return
        current_homework_help_status = services.active_household().get_homework_help(self.sim_info.age)
        if current_homework_help_status == ReceiveDailyHomeworkHelp.UNCHECKED:
            if not self.should_get_homework_help(current_homework_help_status):
                return
            return self.get_tuned_homework_progress()
        elif current_homework_help_status == ReceiveDailyHomeworkHelp.CHECKED_RECEIVE_HELP:
            return self.get_tuned_homework_progress()

    def end_career_session(self):
        self._clear_career_alarms()
        current_gig = self.get_current_gig()
        if self.taking_day_off or current_gig is None or current_gig.odd_job_tuning is None:
            self._reset_performance_statistics()
            if not self._sim_info.is_npc:
                self._handle_post_reset_loot()
        self._clear_work_status()
        self._clear_gig()
        self.resend_at_work_info()

    def _clear_work_status(self):
        self._current_work_start = None
        self._current_work_end = None
        self._current_work_duration = None
        self._at_work = False
        self._rabbit_hole_id = None
        self._career_session_extended = False
        self._taking_day_off_reason = career_ops.CareerTimeOffReason.NO_TIME_OFF
        self._pto_taken = 0

    def extend_career_session(self, stay_late_extension_override=None):
        if self._career_session_extended:
            logger.error('Trying to extend work hours twice for career {}', self)
            return
        if self._current_work_end is None:
            logger.error('Trying to extend work hours when not during work hours for career {}', self)
            return
        self._career_session_extended = True
        if stay_late_extension_override is None:
            stay_late_extension = self.current_level_tuning.stay_late_extension
        else:
            stay_late_extension = stay_late_extension_override
        self.set_career_end_time(self._current_work_end + interval_in_sim_minutes(minutes=stay_late_extension))
        services.get_event_manager().process_event(test_events.TestEvent.CareerStayLate, sim_info=self._sim_info)

    def set_career_end_time(self, end_time, reset_warning_alarm=True):
        self._current_work_end = max(end_time, services.time_service().sim_now)
        if self._career_event_manager is not None:
            self._career_event_manager.on_career_session_extended(reset_warning_alarm=reset_warning_alarm)
        self._create_end_of_work_day_alarm()
        self.resend_at_work_info()

    def put_sim_in_career_rabbit_hole(self):
        if not self._sim_info.career_tracker.available_for_work(self):
            return False
        elif self._rabbit_hole_id is None:
            self._rabbit_hole_id = services.get_rabbit_hole_service().put_sim_in_managed_rabbithole(self._sim_info, self.career_rabbit_hole, career_uid=self.guid64)
            if self._rabbit_hole_id is not None:
                self._send_workday_info_telemetry(TELEMETRY_WORKDAY_TYPE_RABBIT_HOLE)
                business_service = services.business_service()
                business_manager = business_service.get_business_manager_for_sim(sim_id=self._sim_info.sim_id)
                if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                    business_manager.set_open(False)
                return True
            else:
                return False
        return False
        return False

    def on_inactive_rabbit_hole_canceled(self):
        self._rabbit_hole_id = None

    def remove_sim_from_career_rabbit_hole(self, suppress_error=False):
        if not self._rabbit_hole_id:
            if not suppress_error:
                logger.error('Tried to remove {} from career rabbit hole but no rabbit hole exists.', self._sim_info)
            return
        services.get_rabbit_hole_service().remove_sim_from_rabbit_hole(self.sim_info.id, self._rabbit_hole_id)

    def leave_work_early(self):
        self._send_telemetry(TELEMETRY_HOOK_CAREER_LEAVE_EARLY)
        if self._rabbit_hole_id:
            if self.sim_info.is_selectable:
                services.get_rabbit_hole_service().try_remove_sim_from_rabbit_hole(self.sim_info.id, self._rabbit_hole_id)
            else:
                self.remove_sim_from_career_rabbit_hole()
        else:
            self.leave_work(left_early=True)

    def attend_work(self, interaction=None, start_tones=True):
        if not self._has_attended_first_day:
            self._has_attended_first_day = True
        if self._at_work:
            return
        self.days_worked_statistic.add_value(1)
        self._at_work = True
        gig = self.get_current_gig()
        if gig is not None:
            gig.notify_gig_attended()
        self._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
        self.add_pto(self._pto_taken*-1)
        self._pto_taken = 0
        if self._late_for_work_handle is not None:
            alarms.cancel_alarm(self._late_for_work_handle)
            self._late_for_work_handle = None
        if not self.on_assignment:
            self.send_career_message(self.career_messages.career_daily_start_notification)
            self.resend_career_data()
            self.resend_at_work_info()
        if start_tones:
            self.start_tones()
        services.get_event_manager().process_event(test_events.TestEvent.WorkdayStart, sim_info=self._sim_info, career=self)

    def leave_work(self, left_early=False):
        if self._career_event_manager is not None:
            self._end_career_event(left_early=left_early)
            return
        gig = self.get_current_gig()
        if left_early and gig is not None:
            gig.notify_canceled()
        if self._rabbit_hole_id:
            self.remove_sim_from_career_rabbit_hole()
        hours_worked = self.end_tones_and_get_hours_worked()
        if self._sim_info.is_npc or not self.on_assignment:
            self.handle_career_loot(hours_worked, left_early=left_early)
        self.end_career_session()
        if self._sim_info.is_npc or self._sim_info.away_action_tracker is not None:
            self._sim_info.away_action_tracker.reset_to_default_away_action()
        if not left_early:
            self._try_invite_over()

    def time_until_end_of_work(self) -> 'TimeSpan':
        current_time = services.time_service().sim_now
        time_to_work_end = current_time.time_to_week_time(self._current_work_end)
        return time_to_work_end

    def _try_invite_over(self):
        if self.invite_over is None:
            return
        if self.sim_info.is_npc or not self.sim_info.is_at_home:
            return
        if not self.sim_info.is_instanced(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE):
            return
        resolver = SingleSimResolver(self.sim_info)
        if random.random() > self.invite_over.chance.get_chance(resolver):
            return
        services.sim_filter_service().submit_filter(self.invite_over.sim_filter, self._on_try_invite_over_sim_filter_response, requesting_sim_info=self.sim_info, gsi_source_fn=self.get_sim_filter_gsi_name)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def _on_try_invite_over_sim_filter_response(self, filter_results, callback_event_data):
        if not filter_results:
            return
        result = random.choice(filter_results)

        def response(dialog):
            if dialog.accepted:
                services.get_current_venue().summon_npcs((result.sim_info,), self.invite_over.purpose, self.sim_info)

        resolver = DoubleSimResolver(self.sim_info, result.sim_info)
        dialog = self.invite_over.confirmation_dialog(self.sim_info, resolver=resolver)
        dialog.show_dialog(additional_tokens=(result.sim_info,), on_response=response)

    def _send_telemetry(self, hook_tag, level=None):
        with telemetry_helper.begin_hook(career_telemetry_writer, hook_tag, sim_info=self._sim_info) as hook:
            self._populate_telemetry_hook_with_career_data(hook, level=level)

    def _send_end_of_career_event_telemetry(self, medal, num_goals_completed):
        with telemetry_helper.begin_hook(career_telemetry_writer, TELEMETRY_HOOK_CAREER_EVENT_END, sim_info=self._sim_info) as hook:
            self._populate_telemetry_hook_with_career_data(hook)
            hook.write_enum(TELEMETRY_CAREER_EVENT_MEDAL, medal)
            hook.write_int(TELEMETRY_CAREER_EVENT_GOALS, num_goals_completed)

    def _populate_telemetry_hook_with_career_data(self, hook, level=None):
        level = self._level if level is None else level
        hook.write_int(TELEMETRY_CAREER_ID, self.guid64)
        hook.write_int(TELEMETRY_CAREER_LEVEL, self._user_level)
        hook.write_guid(TELEMETRY_TRACK_ID, self._current_track.guid64)
        hook.write_int(TELEMETRY_TRACK_LEVEL, level)
        hook.write_int(TELEMETRY_TRACK_OVERMAX, self._overmax_level)

    def _send_assignment_telemetry(self, hook_tag, assignment, telemetry_type, result):
        with telemetry_helper.begin_hook(career_telemetry_writer, hook_tag, sim_info=self._sim_info) as hook:
            self._populate_telemetry_hook_with_career_data(hook)
            hook.write_int(TELEMETRY_ASSIGNMENT_ID, assignment.guid64)
            hook.write_bool(telemetry_type, result)

    def _send_workday_info_telemetry(self, work_type):
        with telemetry_helper.begin_hook(career_telemetry_writer, TELEMETRY_HOOK_CAREER_WORKDAY_START, sim_info=self._sim_info) as hook:
            self._populate_telemetry_hook_with_career_data(hook)
            hook.write_int(TELEMETRY_FIELD_WORKDAY_TYPE, work_type)

    def promote(self, levels_to_promote=1):
        result = self._promote(levels_to_promote=levels_to_promote)
        if result is not None:
            result.display_dialog(self)

    def is_promotion_blocked(self):
        if self.sim_info.is_npc:
            return False
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None and tutorial_service.is_tutorial_running():
            return False
        elif self.block_promotion_tests is not None and len(self.block_promotion_tests) != 0:
            resolver = SingleSimResolver(self.sim_info)
            if self.block_promotion_tests.run_tests(resolver):
                return True
        return False

    def demote(self, levels_to_demote=1):
        result = self._demote(levels_to_demote=levels_to_demote)
        if result is not None:
            result.display_dialog(self)

    def fire(self, show_notification=True):
        self.leave_work()
        result = self._fire()
        if result is not None and show_notification:
            result.display_dialog(self)

    def lay_off(self, post_lay_off_msg=False):
        career_service = services.get_career_service()
        if career_service is None or not career_service.career_lay_off_enabled:
            return
        resolver = SingleSimResolver(self._sim_info)
        if self.current_level_tuning.loot_on_lay_off is not None:
            for loot in self.current_level_tuning.loot_on_lay_off:
                loot.apply_to_resolver(resolver)
        if post_lay_off_msg:
            self.send_career_message(self.career_messages.lay_off_career_notification)
        self._sim_info.career_tracker.remove_career(self.guid64, post_quit_msg=False, test_event_origin=TestEventCareersOrigin.LAY_OFF)

    def quit_career(self, post_quit_msg:'bool'=True, update_ui:'bool'=True, test_event_origin:'TestEventCareersOrigin'=TestEventCareersOrigin.QUIT_CAREER) -> 'None':
        self._send_telemetry(TELEMETRY_HOOK_CAREER_END)
        resolver = SingleSimResolver(self._sim_info)
        for loot in self.current_level_tuning.loot_on_quit:
            loot.apply_to_resolver(resolver)
        self._sim_info.career_tracker.career_leave(self)
        if post_quit_msg:
            self.send_career_message(self.career_messages.quit_career_notification)
        self._remove_pto_commodity()
        self._remove_days_worked_commodities()
        self._clear_auditions()
        self.clear_all_gigs()
        self._clear_career_alarms()
        if self._work_scheduler is not None:
            self._work_scheduler.destroy()
        self.resend_career_data()
        self.resend_at_work_info()
        self._remove_career_knowledge(update_ui)
        self.remove_coworker_relationship_bit()
        self.clear_current_agent()
        self.icon_override = None
        object_manager = services.object_manager()
        inventory_manager = services.inventory_manager()
        if self._guid_to_claimed_object_ids:
            for object_id_list in self._guid_to_claimed_object_ids.values():
                for object_id in object_id_list:
                    object_manager.set_unclaimed_item(object_id)
                    target = object_manager.get(object_id)
                    if target is None:
                        target = inventory_manager.get(object_id)
                        if target is None:
                            pass
                        elif target.in_use:
                            target.transient = True
                        else:
                            target.destroy(source=self, cause='Quitting career claiming object', fade_duration=ClientObjectMixin.FADE_DURATION)
                    elif target.in_use:
                        target.transient = True
                    else:
                        target.destroy(source=self, cause='Quitting career claiming object', fade_duration=ClientObjectMixin.FADE_DURATION)
            self._guid_to_claimed_object_ids.clear()
        services.get_event_manager().process_event(test_events.TestEvent.CareerEvent, sim_info=self._sim_info, career=self, track=self.current_track_tuning, test_event_origin=test_event_origin)

    def can_change_level(self, demote=False):
        if demote or self.is_promotion_blocked():
            return False
        delta = 1 if not demote else -1
        new_level = self._level + delta
        num_career_levels = len(self._current_track.career_levels)
        if new_level < 0:
            return False
        elif new_level >= num_career_levels and (self.current_track_tuning.branches or self.current_track_tuning.overmax is None):
            return False
        return True

    def can_work_early(self):
        return False

    def _change_level_within_track(self, delta):
        self.career_stop(is_level_change=True)
        self._level += delta
        self._user_level += delta
        self._overmax_level = 0
        self._sim_info.career_tracker.update_history(self)
        self._reset_career_objectives(self._current_track, self.level)
        self.career_start(is_level_change=True, test_event_origin=TestEventCareersOrigin.CHANGE_CAREER_LEVEL_IN_TRACK)
        self.resend_career_data()
        self.resend_at_work_info()

    def _handle_promotion(self, previous_salary, previous_highest_level):
        reward_text = self._handle_promotion_reward(levels_delta=self.user_level - previous_highest_level) if self.user_level > previous_highest_level else None
        (_, next_work_time, _) = self.get_next_work_time()
        salary = self.get_hourly_pay()
        salary_increase = salary - previous_salary
        promotion_sting = self.current_level_tuning.promotion_audio_sting
        if promotion_sting is not None:
            play_tunable_audio(promotion_sting)
        if self.current_level_tuning.screen_slam is not None:
            self.current_level_tuning.screen_slam.send_screen_slam_message(self._sim_info, self._sim_info, self.current_level_tuning.get_title(self._sim_info), self.user_level, self.current_track_tuning.get_career_name(self._sim_info))
        if self.promotion_buff is not None:
            self._sim_info.add_buff_from_op(self.promotion_buff.buff_type, buff_reason=self.promotion_buff.buff_reason)
        if self.current_track_tuning.outfit_generation_type == CareerOutfitGenerationType.CAREER_TUNING:
            if self.has_outfit():
                self._sim_info.resend_current_outfit()
            else:
                new_outfit = self._sim_info.get_outfit_for_clothing_change(None, OutfitChangeReason.DefaultOutfit, resolver=SingleSimResolver(self._sim_info))
                self._sim_info.set_current_outfit(new_outfit)
        self._send_telemetry(TELEMETRY_HOOK_CAREER_PROMOTION)
        self.on_promoted(self._sim_info)
        services.get_event_manager().process_event(test_events.TestEvent.CareerPromoted, sim_info=self._sim_info, career=self, level=self.level, track=self.current_track_tuning, test_event_origin=TestEventCareersOrigin.PROMOTION)
        current_gig = self.get_current_gig()
        if current_gig is not None:
            result = current_gig.get_promotion_evaluation_result(reward_text, first_gig=not self._first_gig_completed)
            if result:
                return result
        if reward_text is None:
            return EvaluationResult(Evaluation.PROMOTED, self.career_messages.promote_career_rewardless_notification, next_work_time, salary, salary_increase, None, display_career_info=self.display_career_info)
        return EvaluationResult(Evaluation.PROMOTED, self.career_messages.promote_career_notification, next_work_time, salary, salary_increase, None, reward_text, display_career_info=self.display_career_info)

    def _promote(self, levels_to_promote=1):
        if self._level + levels_to_promote < len(self._current_track.career_levels):
            return self._promote_within_track(levels_to_promote=levels_to_promote)
        if self.current_track_tuning.branches:
            return self._promote_to_new_branch()
        elif self.current_track_tuning.overmax is not None:
            return self._increase_overmax_level(levels_to_overmax=levels_to_promote)

    def _handle_promotion_reward(self, levels_delta=1):
        promotion_rewards = []
        reward_payout = []
        for career_level in range(max(0, self._level - levels_delta + 1), self._level + 1):
            level_tuning = self._current_track.career_levels[career_level]
            if level_tuning is not None:
                promotion_rewards.append(level_tuning.promotion_reward)
        if self._player_rewards_deferred:
            logger.info('Defering rewards {} to {}', promotion_rewards, self.sim_info, owner='jdimailig')
            return
        else:
            for promotion_reward in promotion_rewards:
                if promotion_reward is None:
                    pass
                else:
                    logger.info('Giving reward {} to {}', promotion_reward, self.sim_info, owner='jdimailig')
                    reward_payout.extend(promotion_reward.give_reward(self._sim_info))
            if reward_payout:
                return LocalizationHelperTuning.get_bulleted_list((None,), (reward.get_display_text(SingleSimResolver(self._sim_info)) for reward in reward_payout))

    def _demote(self, levels_to_demote=1):
        current_level_tuning = self.current_level_tuning
        current_performance = self.work_performance
        if self.can_be_fired and (current_performance <= current_level_tuning.fired_performance_level or self._level < levels_to_demote):
            return self._fire()
        if self._level >= levels_to_demote:
            return self._demote_within_track(levels_to_demote=levels_to_demote)
        elif self._level > 0:
            return self._demote_within_track(levels_to_demote=self._level)

    def _promote_to_new_branch(self):
        sim_info = self._sim_info
        if not (sim_info.is_selectable and sim_info.valid_for_distribution):
            random_track = random.choice(self.current_track_tuning.branches)
            logger.error("Trying to branch an npc's career: {}. Randomly choosing a branch: {}", self, random_track)
            return self.set_new_career_track(random_track)
        if services.current_zone().ui_dialog_service.auto_respond:
            return self.set_new_career_track(self.current_track_tuning.branches[0])
        self._pending_promotion = True
        msg = self.get_select_career_track_pb(sim_info, self, self.current_track_tuning.branches)
        Distributor.instance().add_op(sim_info, GenericProtocolBufferOp(Operation.SELECT_CAREER_UI, msg))
        return EvaluationResult(Evaluation.PROMOTED, None)

    def on_branch_selection(self, career_track):
        result = self.set_new_career_track(career_track)
        if result is not None:
            result.display_dialog(self)

    def _promote_within_track(self, levels_to_promote=1):
        previous_salary = self.get_hourly_pay()
        previous_highest_level = self._sim_info.career_tracker.get_highest_level_reached_for_track(self.guid64, self._current_track.guid64)
        self._change_level_within_track(levels_to_promote)
        return self._handle_promotion(previous_salary, previous_highest_level)

    def _demote_within_track(self, levels_to_demote=1):
        self._change_level_within_track(-levels_to_demote)
        if self.demotion_buff is not None:
            self._sim_info.add_buff_from_op(self.demotion_buff.buff_type, buff_reason=self.demotion_buff.buff_reason)
        self.on_demoted(self._sim_info)
        self._send_telemetry(TELEMETRY_HOOK_CAREER_DEMOTION, level=self.level)
        current_gig = self.get_current_gig()
        if current_gig is not None:
            result = current_gig.get_demotion_evaluation_result(first_gig=not self._first_gig_completed)
            if result:
                return result
        return EvaluationResult(Evaluation.DEMOTED, self.career_messages.demote_career_notification)

    def _fire(self):
        self._sim_info.career_tracker.remove_career(self.guid64, post_quit_msg=False, test_event_origin=TestEventCareersOrigin.FIRED)
        if self.fired_buff is not None:
            self._sim_info.add_buff_from_op(self.fired_buff.buff_type, buff_reason=self.fired_buff.buff_reason)
        self._send_telemetry(TELEMETRY_HOOK_CAREER_DEMOTION, level=-1)
        return EvaluationResult(Evaluation.FIRED, self.career_messages.fire_career_notification)

    def _apply_on_target(self, money_earned, pto_earned, gig=None):
        self.resend_career_data()
        if self.career_messages.career_performance_warning.threshold.compare(self.work_performance):
            self.send_career_message(self.career_messages.career_performance_warning.dialog, on_response=self._career_performance_warning_response)
        if pto_earned > 0 and self.career_messages.pto_gained_text is not None:
            pto_notification = self.career_messages.pto_gained_text(self._sim_info)
        else:
            pto_notification = LocalizationHelperTuning.get_raw_text('')
        if gig is None:
            gig = self.get_current_gig()
        if gig is not None:
            result = gig.get_end_of_gig_evaluation_result()
            if result:
                return result
        if self.on_assignment:
            return EvaluationResult(Evaluation.ON_TARGET, self.career_messages.career_assignment_summary_notification, money_earned, pto_notification)
        if self.currently_at_work:
            return EvaluationResult(Evaluation.ON_TARGET, self.career_messages.career_daily_end_notification, money_earned, pto_notification)
        if self.taking_day_off:
            notification = self.career_messages.career_time_off_messages[self._taking_day_off_reason].day_end_notification
            if notification is not None:
                return EvaluationResult(Evaluation.ON_TARGET, notification, money_earned, pto_notification)
        return EvaluationResult(Evaluation.ON_TARGET, None)

    def _increase_overmax_level(self, levels_to_overmax=1):
        previous_salary = self.get_hourly_pay()
        self._overmax_level += levels_to_overmax
        self._sim_info.career_tracker.update_history(self)
        self.resend_career_data()
        self._send_telemetry(TELEMETRY_HOOK_CAREER_OVERMAX)
        self._remove_performance_statistics()
        self._remove_statistic_metric_listeners()
        self._add_performance_statistics()
        self._add_statistic_metric_listeners()
        salary = self.get_hourly_pay()
        salary_increase = salary - previous_salary
        overmax = self.current_track_tuning.overmax
        if overmax is not None:
            if overmax.reward_by_level and self._overmax_level in overmax.reward_by_level:
                reward_payout = overmax.reward_by_level[self._overmax_level].give_reward(self._sim_info)
                reward_text = LocalizationHelperTuning.get_bulleted_list((None,), (reward.get_display_text(SingleSimResolver(self._sim_info)) for reward in reward_payout))
            elif overmax.reward is not None:
                reward_payout = overmax.reward.give_reward(self._sim_info)
                reward_text = LocalizationHelperTuning.get_bulleted_list((None,), (reward.get_display_text(SingleSimResolver(self._sim_info)) for reward in reward_payout))
        else:
            reward_text = None
        if self.promotion_buff is not None:
            self._sim_info.add_buff_from_op(self.promotion_buff.buff_type, buff_reason=self.promotion_buff.buff_reason)
        current_gig = self.get_current_gig()
        if current_gig is not None:
            result = current_gig.get_overmax_evaluation_result(self._overmax_level + 1, reward_text)
            if result:
                return result
        if overmax.suppress_overmax_notifications:
            overmax_notification = None
        else:
            overmax_notification = self.career_messages.overmax_notification if reward_text is not None else self.career_messages.overmax_rewardless_notification
        return EvaluationResult(Evaluation.PROMOTED, overmax_notification, self._overmax_level + 1, salary, salary_increase, reward_text)

    def set_new_career_track(self, career_track):
        self._pending_promotion = False
        previous_salary = self.get_hourly_pay()
        previous_highest_level = max(self._sim_info.career_tracker.get_highest_level_reached_for_track(self.guid64, career_track.guid64), self._sim_info.career_tracker.get_highest_level_reached_for_track(self.guid64, self.start_track.guid64))
        self.career_stop()
        self._current_track = career_track
        self._level = 0
        self._user_level += 1
        self._reset_career_objectives(career_track, 0)
        self._sim_info.career_tracker.update_history(self)
        self.fame_moment_completed = False
        self.career_start(test_event_origin=TestEventCareersOrigin.NEW_CAREER_TRACK)
        self.resend_career_data()
        self.resend_at_work_info()
        return self._handle_promotion(previous_salary, previous_highest_level)

    def _reset_career_objectives(self, track, level):
        aspiration_tracker = self._sim_info.aspiration_tracker
        if aspiration_tracker is None:
            return
        career_aspiration = track.career_levels[level].get_aspiration()
        if career_aspiration is not None:
            aspiration_tracker.reset_milestone(career_aspiration)
            career_aspiration.register_callbacks()
            aspiration_tracker.process_test_events_for_aspiration(career_aspiration)

    def _get_promote_performance_level(self):
        performance_level = self.current_level_tuning.promote_performance_level
        overmax = self.current_track_tuning.overmax
        if overmax is not None:
            max_level = self.current_level_tuning.performance_stat.max_value_tuning
            performance_level = min(max_level, performance_level + self._overmax_level*overmax.performance_threshold_increase)
        return performance_level

    def evaluate_career_performance(self, money_earned, pto_earned, gig=None):
        current_level_tuning = self.current_level_tuning
        current_performance = self.work_performance
        resolver = SingleSimResolver(self._sim_info)
        if (self.can_be_fired or self.can_change_level(demote=True)) and current_performance <= current_level_tuning.demotion_performance_level and random.random() < self.demotion_chance_modifiers.get_multiplier(resolver):
            return self._demote()
        if self.can_change_level(demote=False):
            promotion_aspiration = current_level_tuning.aspiration
            aspiration_tracker = self._sim_info.aspiration_tracker
            if promotion_aspiration is None or aspiration_tracker is not None and aspiration_tracker.milestone_completed(promotion_aspiration):
                performance_threshold = self._get_promote_performance_level()
                resolver = SingleSimResolver(self._sim_info)
                if random.random() < self.early_promotion_chance.get_multiplier(resolver):
                    multiplier = self.early_promotion_modifiers.get_multiplier(resolver)
                    current_performance += performance_threshold*multiplier
                if current_performance >= performance_threshold:
                    max_career_levels = len(self._current_track.career_levels)
                    levels = 0
                    current_performance -= performance_threshold
                    while current_performance >= 0:
                        levels += 1
                        next_level = self._level + levels
                        if next_level < max_career_levels:
                            next_level_tuning = self._current_track.career_levels[next_level]
                            performance_threshold = next_level_tuning.promote_performance_level
                        else:
                            break
                        current_performance -= performance_threshold
                    return self._promote(levels_to_promote=levels)
        return self._apply_on_target(money_earned, pto_earned, gig=gig)

    def handle_career_loot(self, hours_worked, left_early=False):
        if self.on_assignment:
            logger.error("Shouldn't call handle_career_loot while on assignment", owner='nabaker')
        gig = self.get_current_gig()
        if gig and left_early and gig.odd_job_tuning is not None:
            gig.collect_rabbit_hole_rewards()
            money_earned = gig.get_pay(rabbit_hole=True)
            gig.pay_out_gig(money_earned)
            gig.collect_additional_rewards()
            pto_earned = 0
        else:
            (money_earned, pto_earned) = self._collect_rewards(hours_worked)
        if gig is not None:
            self.apply_gig_statistic_changes(gig)
            if gig.save_history:
                self._sim_info.career_tracker.add_gig_history(gig)
        if hours_worked <= 0:
            degree_tracker = self._sim_info.degree_tracker
            if degree_tracker is not None and degree_tracker.get_course_data(self.guid64) is not None:
                self.process_homework()
        result = self.evaluate_career_performance(money_earned, pto_earned)
        if result is not None:
            result.display_dialog(self)
        self._send_telemetry(TELEMETRY_HOOK_CAREER_DAILY_END)
        if not self.taking_day_off:
            span_worked = create_time_span(hours=hours_worked)
            services.get_event_manager().process_event(test_events.TestEvent.WorkdayComplete, sim_info=self._sim_info, career=self, time_worked=span_worked.in_ticks(), money_made=money_earned)
        self._first_gig_completed = True

    @property
    def has_completed_active_assignments(self):
        aspiration_tracker = self._sim_info.aspiration_tracker
        return self.on_assignment and all(aspiration_tracker.milestone_completed(assignment) for assignment in self._active_assignments)

    def _handle_assignment_results(self):
        if not self._sim_info.is_selectable:
            return
        assignments_finished = 0
        assignments_total = self.current_track_tuning.active_assignment_amount
        aspiration_tracker = self._sim_info.aspiration_tracker
        statistic_tracker = self._sim_info.statistic_tracker
        for assignment in self._active_assignments:
            result = aspiration_tracker.milestone_completed(assignment)
            if result:
                assignments_finished += 1
            self._send_assignment_telemetry(TELEMETRY_HOOK_CAREER_ASSIGNMENT_END, assignment, TELEMETRY_ASSIGNMENT_COMPLETED, result)
        if assignments_finished == 0:
            current_level_tuning = self.current_level_tuning
            penalty = current_level_tuning.performance_metrics.missed_work_penalty
            self.add_work_performance(-penalty)
            if statistic_tracker is not None:
                session_stat = statistic_tracker.get_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE, add=True)
                if session_stat is not None:
                    session_stat.add_value(-penalty)
        work_money = int(self.get_assignment_pay(assignments_finished))
        performance_mod = assignments_finished/assignments_total
        pto_to_add = self._compute_pto(1)
        pto_to_add *= performance_mod
        pto_delta = self.add_pto(pto_to_add)
        result = self.evaluate_career_performance(work_money, pto_delta)
        if result is not None:
            should_present_dialog = self.has_attended_first_day or result.evaluation != Evaluation.ON_TARGET
            if should_present_dialog:
                result.display_dialog(self)
        span_worked = create_time_span(hours=0)
        services.get_event_manager().process_event(test_events.TestEvent.WorkdayComplete, sim_info=self._sim_info, career=self, time_worked=span_worked.in_ticks(), money_made=work_money)
        if result is None:
            return
        return result.evaluation

    def handle_assignment_loot(self):
        work_money = int(self.get_assignment_pay(1))
        self._sim_info.household.funds.add(work_money, Consts_pb2.TELEMETRY_MONEY_CAREER, self._get_sim())
        self.apply_assignment_performance_change(self.current_track_tuning.active_assignment_amount)

    def _career_performance_warning_response(self, dialog):
        if not dialog.accepted:
            return
        sim = self._sim_info.get_sim_instance()
        if sim is None:
            return
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, interactions.priority.Priority.High, insert_strategy=interactions.context.QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
        sim.push_super_affordance(self.career_messages.career_performance_warning.affordance, sim, context)

    @flexmethod
    def _get_simolean_trait_bonus_pay(cls, inst, pay, sim_info=DEFAULT, career_track=DEFAULT, career_level=DEFAULT):
        if pay == 0:
            return pay
        sim_info = sim_info if sim_info is not DEFAULT else inst.sim_info
        career_track = career_track if career_track is not DEFAULT else inst.current_track_tuning
        career_level = career_level if career_level is not DEFAULT else inst.level
        level_tuning = career_track.career_levels[career_level]
        for trait_bonus in level_tuning.simolean_trait_bonus:
            if sim_info.trait_tracker.has_trait(trait_bonus.trait):
                pay += pay*(trait_bonus.bonus*0.01)
        return pay

    @flexmethod
    def get_hourly_pay(cls, inst, sim_info=DEFAULT, career_track=DEFAULT, career_level=DEFAULT, overmax_level=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        sim_info = sim_info if sim_info is not DEFAULT else inst.sim_info
        career_track = career_track if career_track is not DEFAULT else inst.current_track_tuning
        career_level = career_level if career_level is not DEFAULT else inst.level
        overmax_level = overmax_level if overmax_level is not DEFAULT else inst.overmax_level
        logger.assert_raise(career_level >= 0, 'get_hourly_pay: Current Level is negative: {}, Level: {}', type(inst_or_cls).__name__, career_level)
        logger.assert_raise(career_level < len(career_track.career_levels), 'get_hourly_pay: Current Level is bigger then the number of careers: {}, Level: {}', type(inst_or_cls).__name__, career_level)
        level_tuning = career_track.career_levels[career_level]
        hourly_pay = level_tuning.simoleons_per_hour
        if career_track.overmax is not None:
            hourly_pay += career_track.overmax.salary_increase*overmax_level
        hourly_pay = inst_or_cls._get_simolean_trait_bonus_pay(pay=hourly_pay, sim_info=sim_info, career_track=career_track, career_level=career_level)
        hourly_pay = int(hourly_pay)
        return hourly_pay

    def get_assignment_pay(self, assignments):
        sim_info = self.sim_info
        career_track = self.current_track_tuning
        level_tuning = self.current_level_tuning
        hourly_pay = level_tuning.simoleons_per_hour
        if hourly_pay is 0:
            return 0
        assignment_pay = level_tuning.simoleons_for_assignments_per_day*assignments/career_track.active_assignment_amount
        if career_track.overmax is not None:
            hourly_pay += career_track.overmax.salary_increase*self.overmax_level
        hourly_pay = self._get_simolean_trait_bonus_pay(pay=hourly_pay, sim_info=sim_info, career_track=career_track, career_level=level_tuning.level)
        assignment_pay = assignment_pay*hourly_pay/level_tuning.simoleons_per_hour
        return assignment_pay

    @flexmethod
    def get_daily_pay(cls, inst, career_track=DEFAULT, career_level=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        career_track = career_track if career_track is not DEFAULT else inst.current_track_tuning
        career_level = career_level if career_level is not DEFAULT else inst.level
        career_level_tuning = career_track.career_levels[career_level]
        join_time = inst.join_time if inst is not None else None
        schedule_shift_type = inst.schedule_shift_type if inst is not None else None
        work_schedule = get_career_schedule_for_level(career_level_tuning, join_time=join_time, schedule_shift_type=schedule_shift_type)
        if work_schedule is None:
            hours_per_day = Retirement.DAILY_HOURS_WORKED_FALLBACK
        else:
            ticks_per_week = sum(end_ticks - start_ticks for (start_ticks, end_ticks) in work_schedule.get_schedule_times())
            hours_per_day = date_and_time.ticks_to_time_unit(ticks_per_week, date_and_time.TimeUnit.HOURS, True)/7
        return int(hours_per_day*inst_or_cls.get_hourly_pay(career_track=career_track, career_level=career_level, **kwargs))

    def _compute_pto(self, work_time_multiplier):
        pto = self.current_level_tuning.pto_per_day
        pto *= work_time_multiplier
        level_tuning = self.current_track_tuning.career_levels[self.level]
        for trait_multiplier in level_tuning.pto_accrual_trait_multiplier:
            if self._sim_info.trait_tracker.has_trait(trait_multiplier.trait):
                pto *= trait_multiplier.multiplier
        return pto

    def _collect_rewards(self, time_at_work, pay_multiplier=1):
        if self.current_work_duration is None:
            logger.error('Career {} attempted to apply performance with no work duration set', self)
            return (0, 0)
        current_level_tuning = self.current_level_tuning
        performance_metrics = current_level_tuning.performance_metrics
        work_duration = (self._current_work_end - self._current_work_start).in_hours()
        percent_at_work = time_at_work/work_duration
        work_time_multiplier = 1
        if percent_at_work*100 < performance_metrics.full_work_day_percent:
            self.add_work_performance(-performance_metrics.missed_work_penalty)
            work_time_multiplier = percent_at_work/(performance_metrics.full_work_day_percent/100)
            missed_time_percent = (1 - percent_at_work)/(performance_metrics.full_work_day_percent/100)
            self._sim_info.apply_career_changes(missed_time_percent=missed_time_percent)
        work_money = math.ceil(self.get_hourly_pay()*work_duration*work_time_multiplier*pay_multiplier)
        self._sim_info.household.funds.add(work_money, Consts_pb2.TELEMETRY_MONEY_CAREER, self._get_sim())
        if self.taking_day_off_reason != career_ops.CareerTimeOffReason.PTO:
            pto_delta = self.add_pto(self._compute_pto(work_time_multiplier))
        else:
            pto_delta = 0
        return (work_money, pto_delta)

    def get_career_text_tokens(self):
        job = self.current_level_tuning.get_title(self._sim_info)
        career = self._current_track.get_career_name(self._sim_info)
        company = self.get_company_name()
        return (job, career, company)

    def send_career_message(self, dialog_factory, *additional_tokens, icon_override=None, on_response=None, display_career_info=False, additional_responses=None, **kwargs):
        if self._sim_info.is_npc:
            return
        dialog = dialog_factory(self._sim_info, resolver=SingleSimResolver(self._sim_info))
        if dialog is not None:
            if display_career_info:
                career_args = UiCareerNotificationArgs()
                career_args.career_uid = self.guid64
                career_args.career_level = self.level
                career_args.career_track = self._current_track.guid64
                career_args.user_career_level = self.user_level
                career_args.sim_id = self._sim_info.id
                career_args.paid_time_off_available = self.pto
                career_args.paid_time_off_disabled = self.disable_pto
                career_args.schedule_shift_type = self._current_shift_type
                try:
                    career_args.pay = self.get_hourly_pay(sim_info=self._sim_info, career_track=self._current_track, career_level=self.level, overmax_level=0)
                except:
                    pass
                work_scheduler = self._get_work_scheduler()
                if work_scheduler is not None:
                    work_scheduler.populate_scheduler_msg(career_args.work_schedule)
            else:
                career_args = None
            if additional_responses:
                dialog.set_responses(additional_responses)
            icon_override = IconInfoData(icon_resource=self._current_track.icon) if icon_override is None else icon_override
            localized_full_name = LocalizationHelperTuning.get_sim_full_name(self._sim_info)
            secondary_icon_override = IconInfoData(icon_resource=self._icon_override, obj_name=localized_full_name) if self._icon_override is not None else IconInfoData(obj_instance=self._sim_info)
            dialog.show_dialog(additional_tokens=self.get_career_text_tokens() + additional_tokens, icon_override=icon_override, secondary_icon_override=secondary_icon_override, on_response=on_response, career_args=career_args, **kwargs)

    def get_major(self):
        degree_tracker = self._sim_info.degree_tracker
        if degree_tracker is not None:
            return degree_tracker.get_major()

    def get_university(self):
        degree_tracker = self._sim_info.degree_tracker
        if degree_tracker is not None:
            return degree_tracker.get_university()

    def populate_set_career_op(self, career_op, gig=None):
        career_op.career_uid = self.guid64
        career_op.career_level = self.level
        career_op.company = self.get_company_name()
        career_op.career_track = self._current_track.guid64
        career_op.skip_next_shift = self.should_skip_next_shift()
        career_op.schedule_shift_type = self._current_shift_type
        work_scheduler = self._get_work_scheduler()
        if work_scheduler is not None:
            work_scheduler.populate_scheduler_msg(career_op.work_schedule)
        career_op.is_retired = False
        for assignment in self._active_assignments:
            career_op.active_assignments.extend([objective.guid64 for objective in assignment.objectives])
        if self.career_panel_type == CareerPanelType.UNIVERSITY_COURSE and self.is_course_slot:
            major = self.get_major()
            if major is not None:
                career_op.university_career_uid = major.guid64
            university = self.get_university()
            if university is not None:
                career_op.university_uid = university.guid64
            degree_tracker = self._sim_info.degree_tracker
            if degree_tracker is not None:
                career_op.company = degree_tracker.get_university().display_name
                career_op.performance_tooltip = degree_tracker.get_major().display_name
        elif self.career_category == CareerCategory.UniversityCourse:
            course_data = self.sim_info.degree_tracker.get_course_data(self.guid64)
            career_op.university_career_uid = course_data.guid64
            university = self.get_university()
            if university is not None:
                career_op.university_uid = university.guid64
        if not self.sim_info.is_npc:
            self.populate_set_career_op_with_data_for_played_sims(career_op, gig)

    def populate_set_career_op_with_data_for_played_sims(self, career_op, gig=None):
        career_op.pay = self.get_hourly_pay()
        career_op.pay_raise_count = self.overmax_level
        career_op.performance = int(self.work_performance)
        career_op.performance_complete = self.work_performance >= self._get_promote_performance_level()
        career_op.reputation = int(self.professional_reputation)
        career_op.paid_time_off_available = self.pto
        career_op.paid_time_off_disabled = self.disable_pto
        if self.current_track_tuning.display_overmax_instead_of_career_levels:
            career_op.user_career_level = self.overmax_level
        else:
            career_op.user_career_level = self.user_level
        career_op.auto_work = self.auto_work
        tooltip = self._get_performance_tooltip()
        if tooltip:
            career_op.performance_tooltip = tooltip
        career_op.preferred_region = self.preferred_region
        if gig is None:
            gig = self.get_current_gig()
        if gig is not None:
            gig.build_gig_msg(career_op.gig_info, self._sim_info, gig_time=gig.get_gig_time(), gig_customer=gig.get_gig_customer(), gig_extended_end_time=gig.extended_end_time)
        if self.career_display_name_override is not None:
            career_op.career_display_name_override = self.career_display_name_override(gig.display_name())
        if self.current_gig_limit > 1:
            career_op.career_button_tooltip_description = gig.display_name(self._sim_info)
        if gig is not None and gig is not None and self.career_panel_type == CareerPanelType.UNIVERSITY_COURSE and self.is_course_slot:
            degree_tracker = self._sim_info.degree_tracker
            if degree_tracker is not None:
                career_op.days_to_enroll = degree_tracker.get_remaining_days_to_reenrollment()
                career_op.enrollment_status = degree_tracker.get_enrollment_status()
                career_op.additional_description = degree_tracker.get_degree_info_description()
                career_op.career_button_tooltip_description = degree_tracker.get_degree_info_tooltip_description()
        elif self.career_category == CareerCategory.UniversityCourse:
            course_data = self.sim_info.degree_tracker.get_course_data(self.guid64)
            career_op.additional_description = self.current_track_tuning.get_career_name(self._sim_info)
            career_op.course_description = self.current_track_tuning.get_career_description(self._sim_info)
            related_skill = course_data.course_skill_data.related_skill
            if related_skill is not None:
                career_op.course_skill_name = related_skill.stat_name
        if self.is_active:
            career_op.follow_enabled = self._follow_enabled
        career_op.is_active = self.is_active
        if self.career_category in [CareerCategory.Work, CareerCategory.AdultPartTime]:
            career_op.burnout = self._sim_info.Buffs.has_buff_with_display_type(BuffDisplayType.BURNOUT)
        if self.workplace_rival_id is not None:
            career_op.workplace_rival_id = self.workplace_rival_id

    def send_prep_task_update(self):
        for gig in self.get_current_gigs():
            gig.send_prep_task_update()

    def sim_skewer_rabbit_hole_affordances_gen(self, context, **kwargs):
        for tone in self.get_available_tones_gen():
            yield AffordanceObjectPair(self.CAREER_TONE_INTERACTION, None, self.CAREER_TONE_INTERACTION, None, away_action=tone, away_action_sim_info=self._sim_info, **kwargs)
        tones = self.current_level_tuning.tones
        if tones is not None:
            for aop in tones.leave_work_early.potential_interactions(self._get_sim(), context, sim_info=self._sim_info, **kwargs):
                yield aop
            if tones.stay_late is not None:
                for aop in tones.stay_late.potential_interactions(self._get_sim(), context, sim_info=self._sim_info, **kwargs):
                    yield aop

    def get_available_tones_gen(self):
        tones = self.current_level_tuning.tones
        if tones is not None:
            available_actions = set(tones.optional_actions)
            available_actions.add(tones.get_default_action(self._sim_info))
            yield from available_actions

    def start_tones(self):
        if self._sim_info.is_npc:
            return
        tones = self.current_level_tuning.tones
        if tones is not None and self._sim_info.away_action_tracker is not None:
            tracker = self._sim_info.away_action_tracker
            tracker.add_on_away_action_started_callback(self._on_tone_started)
            tracker.add_on_away_action_ended_callback(self._on_tone_ended)
            tracker.create_and_apply_away_action(tones.get_default_action(self._sim_info))

    def restore_tones(self):
        if self._sim_info.is_npc:
            return
        if self.is_at_active_event:
            return
        if self.currently_at_work and self._sim_info.away_action_tracker is not None:
            tracker = self._sim_info.away_action_tracker
            if tracker.current_away_action is None:
                self.start_tones()
            else:
                tracker.add_on_away_action_started_callback(self._on_tone_started)
                tracker.add_on_away_action_ended_callback(self._on_tone_ended)

    def end_tones_and_get_hours_worked(self):
        if self._sim_info.is_npc or self._sim_info.away_action_tracker is None:
            return
        tracker = self._sim_info.away_action_tracker
        remove_away_action_callbacks = tracker.current_away_action is not None
        tracker.stop()
        if remove_away_action_callbacks:
            tracker.remove_on_away_action_started_callback(self._on_tone_started)
            tracker.remove_on_away_action_ended_callback(self._on_tone_ended)
        dominant_tone = None
        dominant_value = 0
        for tone in self.get_available_tones_gen():
            stat = self._sim_info.get_statistic(tone.runtime_commodity, add=False)
            if stat is not None:
                value = stat.get_value()
                if not dominant_tone is None:
                    if value > dominant_value:
                        dominant_tone = tone
                        dominant_value = value
                dominant_tone = tone
                dominant_value = value
        if dominant_tone is not None:
            tone = dominant_tone(tracker)
            tone.apply_dominant_tone_loot()
        hours_worked = self.get_hours_worked()
        self._remove_tone_commodities()
        return hours_worked

    def get_hours_worked(self):
        minutes = 0
        for tone in self.get_available_tones_gen():
            stat = self._sim_info.get_statistic(tone.runtime_commodity, add=False)
            if stat is not None:
                value = stat.get_value()
                minutes += value
        hours = minutes/MINUTES_PER_HOUR
        return hours

    def _on_tone_started(self, tone):
        if self._is_valid_tone(tone):
            stat = self._sim_info.get_statistic(tone.runtime_commodity)
            stat.add_statistic_modifier(CareerBase.TONE_STAT_MOD)

    def _on_tone_ended(self, tone):
        if self._is_valid_tone(tone):
            stat = self._sim_info.get_statistic(tone.runtime_commodity)
            stat.remove_statistic_modifier(CareerBase.TONE_STAT_MOD)

    def _remove_tone_commodities(self):
        for tone in self.get_available_tones_gen():
            self._sim_info.remove_statistic(tone.runtime_commodity)

    def _is_valid_tone(self, tone):
        for other_tone in self.get_available_tones_gen():
            if tone.guid64 == other_tone.guid64:
                return True
        return False

    def has_outfit(self):
        work_outfit = self.current_level_tuning.get_work_outfit(self.sim_info)
        return bool(work_outfit.outfit_generator)

    def _add_career_knowledge(self):
        for sim_info in self.get_coworker_sim_infos_gen():
            sim_info.relationship_tracker.add_knows_career(self._sim_info.id)
            self._sim_info.relationship_tracker.add_knows_career(sim_info.id)
        for sim_info in self._sim_info.household:
            sim_info.relationship_tracker.send_relationship_info(self._sim_info.id)

    def _remove_career_knowledge(self, update_ui):
        tracker = self._sim_info.relationship_tracker
        for target in tracker.get_target_sim_infos():
            if target is None:
                logger.error('\n                    SimInfo {} has a relationship with a None target. The target\n                    has probably been pruned and the data is out of sync. Please\n                    provide a save and GSI dump and file a DT for this.\n                    ', self._sim_info, owner='epanero')
            elif update_ui and target.household_id == self._sim_info.household_id:
                target.relationship_tracker.send_relationship_info(self._sim_info.id)
            else:
                target.relationship_tracker.remove_knows_career(self._sim_info.id, notify_client=update_ui)

    def setup_career_event(self):
        if self.career_event_manager is not None:
            if self.sim_info.is_npc:
                self.end_career_event_without_payout()
                home_zone_id = self._sim_info.household.home_zone_id
                if services.current_zone_id() != home_zone_id:
                    self._sim_info.inject_into_inactive_zone(home_zone_id)
                else:
                    strat = SimSpawnPointStrategy(spawner_tags=(SpawnPoint.ARRIVAL_SPAWN_POINT_TAG,), spawn_point_option=None, spawn_action=None)
                    request = SimSpawnRequest(self._sim_info, SimSpawnReason.LOT_OWNER, strat)
                    services.sim_spawner_service().submit_request(request)
            else:
                self.career_event_manager.request_career_event_zone_director()

    def _setup_assignments_for_career_joined(self, defer_assignment=False):
        if self.sim_info.is_npc:
            return
        tuned_delay = self.FIRST_TIME_ASSIGNMENT_DIALOG_DELAY
        if defer_assignment:
            tuned_delay += self.FIRST_TIME_DEFERRED_ASSIGNMENT_ADDITIONAL_DELAY.random_float()
        delay = clock.interval_in_sim_minutes(tuned_delay)
        self._assignment_offering_handle = alarms.add_alarm(self, delay, lambda _: self.offer_assignments())

    def get_assignments_to_offer(self, just_accepted=False, forced_assignment=None):
        weighted_assignments = []
        assignments = []
        self.assignment_handler_gsi_cache.clear()
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None and tutorial_service.is_tutorial_running():
            return []
        if forced_assignment is not None:
            return [forced_assignment]
        resolver = SingleSimResolver(self.sim_info)
        for assignment in self.current_track_tuning.assignments:
            test_result = assignment.tests.run_tests(resolver)
            if test_result:
                weighted_assignments.append((assignment.weight, assignment.career_assignment))
                if just_accepted and assignment.is_first_assignment:
                    assignments.append(assignment.career_assignment)
        if not weighted_assignments:
            return []
        if not assignments:
            first_assignment = sims4.random.weighted_random_item(weighted_assignments)
            assignments = [first_assignment]
        num_assignments = self.current_track_tuning.active_assignment_amount - 1
        if num_assignments > len(weighted_assignments):
            logger.error('Bad tuning - number of active assignments is greater than the number of weighted assignments.', self.active_assignment_amount, weighted_assignments, owner='shipark')
            return assignments
        if not just_accepted:
            for _ in range(int(num_assignments)):
                for _ in range(10):
                    assignment = sims4.random.weighted_random_item(weighted_assignments)
                    if assignment not in assignments:
                        assignments.append(assignment)
                        break
        return assignments

    def offer_assignments(self, forced_assignment=None):
        if self.on_assignment:
            return
        self._assignment_offering_handle = None
        assignments = self.get_assignments_to_offer(just_accepted=True, forced_assignment=forced_assignment)
        if not assignments:
            return
        for a in assignments:
            self._offered_assignment_ids.add(a.guid64)

        def on_assignment_dialog_response(dialog):
            if dialog.accepted:
                self._active_assignments = assignments
                self._offered_assignment_ids.clear()
                self._initialize_assignments(from_load=False, just_accepted=True)
                self.resend_at_work_info()
                self.send_assignment_update()
            for assignment in assignments:
                self._send_assignment_telemetry(TELEMETRY_HOOK_CAREER_INITIAL_ASSIGNMENT_OFFER, assignment, TELEMETRY_ASSIGNMENT_ACCEPTANCE, dialog.accepted)

        loc_strings = []
        for assignment in assignments:
            loc_strings.extend(objective.display_text() for objective in assignment.objectives)
        if not loc_strings:
            logger.error("Assignment {} has no objectives to be offered so it can't be offered as a career assignment.", assignments)
        assignment_text = LocalizationHelperTuning.get_new_line_separated_strings(*loc_strings)
        dialog = self.FIRST_TIME_ASSIGNMENT_DIALOG(self.sim_info, SingleSimResolver(self.sim_info))
        dialog.show_dialog(on_response=on_assignment_dialog_response, icon_override=IconInfoData(icon_resource=self._current_track.icon), additional_tokens=(assignment_text,))

    def _initialize_assignments(self, from_load=False, just_accepted=False):
        for assignment in self._active_assignments:
            assignment.register_callbacks()
            if not from_load:
                self._sim_info.add_statistic(self.WORK_SESSION_PERFORMANCE_CHANGE, self.WORK_SESSION_PERFORMANCE_CHANGE.initial_value)
                self._sim_info.aspiration_tracker.reset_milestone(assignment)
                self._sim_info.aspiration_tracker.process_test_events_for_aspiration(assignment)
        self.resend_career_data()

    def startup_career(self):
        self.create_objects()

    def on_loading_screen_animation_finished(self):
        if self._pending_promotion:
            self.promote()

    def on_zone_unload(self):
        if game_services.service_manager.is_traveling:
            if self._career_event_manager is not None:
                self._career_event_manager.save_scorable_situation_for_travel()
            self.career_stop(for_travel=True)

    def on_zone_load(self):
        self.setup_career_event()
        if game_services.service_manager.is_traveling:
            self.career_start(is_load=True)
        if self._guid_to_claimed_object_ids:
            object_manager = services.object_manager()
            inventory_manager = services.inventory_manager()
            for object_id_list in self._guid_to_claimed_object_ids.values():
                for object_id in object_id_list:
                    obj = object_manager.get(object_id)
                    if obj is None:
                        obj = inventory_manager.get(object_id)
                    if obj is not None:
                        obj.claim()
                    else:
                        object_manager.set_claimed_item(object_id)
        for gig in self.get_current_gigs():
            gig.on_zone_load()
        if self.workplace_rival_id is not None:
            rival_sim = services.sim_info_manager().get(self.workplace_rival_id)
            if rival_sim is None:
                self.workplace_rival_id = None
                self.resend_career_data()

    def get_persistable_sim_career_proto(self):
        proto = SimObjectAttributes_pb2.PersistableSimCareer()
        proto.career_uid = self.guid64
        proto.track_uid = self.current_track_tuning.guid64
        proto.track_level = self.level
        proto.user_display_level = self.user_level
        proto.overmax_level = self.overmax_level
        proto.attended_work = self.currently_at_work
        proto.requested_day_off_reason = self.requested_day_off_reason
        proto.taking_day_off_reason = self.taking_day_off_reason
        proto.pending_promotion = self._pending_promotion
        self._career_location.save_career_location(proto)
        proto.has_attended_first_day = self._has_attended_first_day
        proto.pto_taken = self._pto_taken
        if self._current_work_start is not None:
            proto.current_work_start = self._current_work_start.absolute_ticks()
            proto.current_work_end = self._current_work_end.absolute_ticks()
            proto.current_work_duration = self._current_work_duration.in_ticks()
            proto.career_session_extended = self._career_session_extended
        if self._rabbit_hole_id is not None:
            proto.rabbit_hole_id = self._rabbit_hole_id
        if self._join_time is not None:
            proto.join_time = self._join_time.absolute_ticks()
        if self._career_event_manager is not None:
            proto.career_event_manager_data = self._career_event_manager.get_career_event_manager_data_proto()
        for (career_event_id, day) in self._career_event_cooldown_map.items():
            with ProtocolBufferRollback(proto.career_event_cooldowns) as cooldown:
                cooldown.career_event_id = career_event_id
                cooldown.day = day
        if self.on_assignment:
            proto.active_assignments.extend([assignment.guid64 for assignment in self._active_assignments])
        proto.offered_assignments.extend(self._offered_assignment_ids)
        proto.fame_moment_completed = self.fame_moment_completed
        for gig in self.get_current_gigs():
            with ProtocolBufferRollback(proto.current_gigs) as current_gigs:
                gig.save_gig(current_gigs)
        proto.schedule_shift_type = self.schedule_shift_type
        proto.first_gig_completed = self._first_gig_completed
        proto.seen_scholarship_info = self._seen_scholarship_info
        if self._guid_to_claimed_object_ids:
            for (guid, object_id_list) in self._guid_to_claimed_object_ids.items():
                with ProtocolBufferRollback(proto.claimed_object_datas) as claimed_object_datas:
                    claimed_object_datas.guid = guid
                    claimed_object_datas.claimed_object_ids.extend(object_id_list)
        if self.is_active:
            proto.follow_enabled = self._follow_enabled
        icon_override_proto = sims4.resources.get_protobuff_for_key(self._icon_override)
        if icon_override_proto is not None:
            proto.icon_override = icon_override_proto
        if self.workplace_rival_id is not None:
            proto.workplace_rival_id = self.workplace_rival_id
        if self._outfit_index is not None:
            proto.outfit_index = self._outfit_index
        return proto

    def load_from_persistable_sim_career_proto(self, proto, skip_load=False):
        self._current_track = services.get_instance_manager(sims4.resources.Types.CAREER_TRACK).get(proto.track_uid)
        self._level = proto.track_level
        self._user_level = proto.user_display_level
        self._overmax_level = proto.overmax_level
        self._career_location.load_career_location(proto)
        if skip_load:
            self._join_time = services.time_service().sim_now
        else:
            self._join_time = DateAndTime(proto.join_time)
            self._at_work = proto.attended_work
            self._has_attended_first_day = proto.has_attended_first_day
            self._pto_taken = proto.pto_taken
            if proto.HasField('called_in_sick'):
                if proto.called_in_sick:
                    self._requested_day_off_reason = career_ops.CareerTimeOffReason.FAKE_SICK
            elif proto.HasField('requested_day_off_reason'):
                self._requested_day_off_reason = career_ops.CareerTimeOffReason(proto.requested_day_off_reason)
            self._taking_day_off_reason = career_ops.CareerTimeOffReason(proto.taking_day_off_reason)
            self._pending_promotion = proto.pending_promotion
            if not self._current_track.branches:
                self._pending_promotion = False
            if self._pending_promotion and self._level + 1 >= len(self._current_track.career_levels) and proto.HasField('current_work_start'):
                self._current_work_start = DateAndTime(proto.current_work_start)
                self._current_work_end = DateAndTime(proto.current_work_end)
                self._current_work_duration = TimeSpan(proto.current_work_duration)
                self._career_session_extended = proto.career_session_extended
            if proto.HasField('rabbit_hole_id'):
                self._rabbit_hole_id = proto.rabbit_hole_id
            else:
                self._rabbit_hole_id = None
            if has_field(proto, 'career_event_manager_data'):
                self._career_event_manager = CareerEventManager(self)
                self._career_event_manager.load_career_event_manager_data_proto(proto.career_event_manager_data)
            for cooldown in proto.career_event_cooldowns:
                self._career_event_cooldown_map[cooldown.career_event_id] = cooldown.day
        aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
        for active_assignment_id in proto.active_assignments:
            aspiration = aspiration_manager.get(active_assignment_id)
            if aspiration is None:
                logger.error('Career {} has an active assignment {} which corresponds to an invalid ID', self, active_assignment_id, owner='camilogarcia')
            else:
                self._active_assignments.append(aspiration)
        for offered_assignment in proto.offered_assignments:
            self._offered_assignment_ids.add(offered_assignment)
        self.fame_moment_completed = proto.fame_moment_completed
        if proto.HasField('upcoming_gig'):
            gig_type = services.get_instance_manager(sims4.resources.Types.CAREER_GIG).get(proto.upcoming_gig.gig_type)
            gig = gig_type(self.sim_info)
            gig.load_gig(proto.upcoming_gig)
            self._current_gigs.append(gig)
        if proto.HasField('schedule_shift_type'):
            self._current_shift_type = proto.schedule_shift_type
        else:
            self._current_shift_type = CareerShiftType.ALL_DAY
        if proto.HasField('first_gig_completed'):
            self._first_gig_completed = proto.first_gig_completed
        else:
            self._first_gig_completed = False
        if proto.HasField('seen_scholarship_info'):
            self._seen_scholarship_info = proto.seen_scholarship_info
        else:
            self._seen_scholarship_info = False
        if proto.claimed_object_datas:
            if self._guid_to_claimed_object_ids is not None:
                logger.error('loading career claimed objects but there are already ones claimed')
            self._guid_to_claimed_object_ids = {}
            for claimed_object_data in proto.claimed_object_datas:
                guid = claimed_object_data.guid
                self._guid_to_claimed_object_ids[guid] = set()
                for object_id in claimed_object_data.claimed_object_ids:
                    self._guid_to_claimed_object_ids[guid].add(object_id)
        if proto.current_gigs:
            for gig_info in proto.current_gigs:
                gig_type = services.get_instance_manager(sims4.resources.Types.CAREER_GIG).get(gig_info.gig_type)
                gig = gig_type(self.sim_info)
                gig.load_gig(gig_info)
                self._current_gigs.append(gig)
        if proto.HasField('follow_enabled'):
            self._follow_enabled = proto.follow_enabled
        if proto.HasField('icon_override'):
            self._icon_override = sims4.resources.Key(proto.icon_override.type, proto.icon_override.instance, proto.icon_override.group)
        if proto.HasField('workplace_rival_id'):
            self.workplace_rival_id = proto.workplace_rival_id
        if not proto.HasField('outfit_index'):
            if self.career_category not in WORK_PART_TIME_CAREER_CATEGORIES:
                self._outfit_index = 0
        else:
            self._outfit_index = proto.outfit_index
        if self._at_work and not self.is_work_time:
            logger.error('Career {} for Sim {} loaded with _at_work = True but not currently work time. Resetting work state.', self, self._sim_info)
            self._clear_work_status()
            if self._sim_info.is_npc or self._sim_info.away_action_tracker is not None:
                self._sim_info.away_action_tracker.reset_to_default_away_action()
            return
        self.career_start(is_load=True, schedule_init_only=self.is_course_slot)

    def get_career_seniority(self):
        duration = (services.time_service().sim_now - self._join_time).in_weeks()
        return clamp(EPSILON, math.tanh(duration), 1)

    def end_career_assignment(self, assignment):
        self._active_assignments.remove(assignment)

    def clear_career_assignments(self):
        self.active_assignments.clear()

    def get_custom_gsi_data(self):
        return {}

    def on_fame_moment_complete(self):
        self.fame_moment_completed = True

    def _has_single_gig(self):
        return len(self._current_gigs) == 1 and self.current_gig_limit == 1

    def add_gig(self, gig, gig_time, gig_customer=None, gig_budget=None):
        if self._has_single_gig():
            self._clear_gig(self._current_gigs[0])
        if len(self._current_gigs) < self.current_gig_limit:
            new_gig = gig(self.sim_info, customer=gig_customer, gig_budget=gig_budget)
            self._current_gigs.append(new_gig)
            new_gig.set_gig_time(gig_time)
            self._set_up_gig_timers(new_gig)
            new_gig.set_up_gig()

    def apply_gig_statistic_changes(self, gig):
        if gig is None:
            gig = self.get_current_gig()
        if gig is not None:
            performance_change = gig.get_career_performance(first_gig=not self._first_gig_completed)
            if performance_change:
                self.add_work_performance(performance_change)
            reputation_change = gig.get_professional_reputation()
            if reputation_change:
                self.add_professional_reputation(reputation_change)

    def apply_gig_reputation_change(self, gig):
        if gig is None:
            gig = self.get_current_gig()
        if gig is not None:
            reputation_change = gig.get_career_reputation()
            if not reputation_change:
                return
            self.add_professional_reputation(reputation_change)

    def get_current_gig(self):
        if self._has_single_gig():
            return self._current_gigs[0]

    def get_current_gigs(self):
        return self._current_gigs

    def get_gig(self, gig_id):
        for gig in self._current_gigs:
            if gig.guid64 == gig_id:
                return gig

    def clear_all_gigs(self):
        for gig in list(self._current_gigs):
            self._clear_gig(gig)

    def cancel_gig(self, gig_id=None):
        if not self._current_gigs:
            return
        gig = None
        if gig_id is None:
            if self._has_single_gig():
                gig = self._current_gigs[0]
            else:
                logger.error('Attempting to cancel unspecified gig on career {}', self, owner='madang')
                return
        else:
            gig = self.get_gig(gig_id)
        if gig is None:
            logger.error('Could not find gig_id {} in career {}', gig_id, self, owner='madang')
            return
        gig.notify_canceled()
        if not self.is_at_active_event:
            self.apply_gig_statistic_changes(gig)
            gig.collect_additional_rewards()
        cancellation_result = gig.get_end_of_gig_evaluation_result()
        if cancellation_result is not None:
            cancellation_result.display_dialog(self)
        if gig.has_attended_gig():
            self.leave_work_early()
        else:
            if self.is_work_time:
                self.end_career_session()
                return
            self._clear_gig(gig)
            aspiration_tracker = self._sim_info.aspiration_tracker
            aspiration = gig.get_aspiration()
            if aspiration_tracker is not None and aspiration is not None:
                aspiration_tracker.reset_milestone(aspiration)

    def _clear_gig(self, gig=None):
        if gig is None:
            if self._has_single_gig():
                gig = self._current_gigs[0]
            else:
                return
        if self._work_scheduler_override:
            self._work_scheduler_override.destroy()
            self._work_scheduler_override = None
        (follow_up_gig, schedule_time, customer) = self._get_follow_up_gig_data(gig)
        gig.clean_up_gig()
        self._current_gigs[:] = [current_gig for current_gig in self._current_gigs if not current_gig.guid64 == gig.guid64]
        if follow_up_gig is not None:
            self.add_gig(follow_up_gig, schedule_time, gig_customer=customer)
        self.resend_career_data()

    def _get_follow_up_gig_data(self, gig):
        if gig is None:
            gig = self.get_current_gig()
        if gig is None or gig.follow_up_gig is None:
            return (None, None, None)
        gig_result = gig.gig_result
        if gig_result is None:
            return (None, None, None)
        if gig_result != GigResult.GREAT_SUCCESS and gig_result != GigResult.SUCCESS:
            return (None, None, None)
        follow_up_gig = gig.follow_up_gig
        now = services.time_service().sim_now
        schedule_time = follow_up_gig.get_time_until_next_possible_gig(now)
        if schedule_time is None:
            logger.error("Current gig {} is trying to push follow-up gig {} but can't get a valid schedule time. Follow-up gig won't be pushed.", gig, follow_up_gig, owner='trevor')
            return (None, None, None)
        schedule_time = now + schedule_time
        customer = None
        customer_id = gig.get_gig_customer()
        if customer_id:
            customer = services.sim_info_manager().get(customer_id)
            if customer is None:
                logger.error("Current gig {} is trying to push follow-up gig {} with customer ID {} but the Sim can't be found.", gig, follow_up_gig, customer_id, owner='trevor')
                return (None, None, None)
        return (follow_up_gig, schedule_time, customer)

    def _clear_auditions(self):
        drama_scheduler = services.drama_scheduler_service()
        auditions = drama_scheduler.get_scheduled_nodes_by_drama_node_type(DramaNodeType.AUDITION)
        for audition in auditions:
            if audition.get_receiver_sim_info().id == self.sim_info.id:
                drama_scheduler.cancel_scheduled_node(audition.uid)

    def _set_up_gig_timers(self, gig):
        if gig is None:
            gig = self.get_current_gig()
        if gig is None or gig.gig_time is None:
            return
        if self.career_messages.career_early_warning_time is not None:
            early_warning_time_span = date_and_time.create_time_span(hours=self.career_messages.career_early_warning_time)
        else:
            early_warning_time_span = None
        self._work_scheduler_override = gig.gig_time(schedule_immediate=True, start_callback=self._start_work_callback, early_warning_callback=self.early_warning_callback, early_warning_time_span=early_warning_time_span, required_start_time=gig.get_gig_time())

    @constproperty
    def is_course_slot():
        return False

    def add_professional_reputation(self, amount, interaction=None):
        if self.reputation_stat is None:
            return
        stat_tracker = self._sim_info.statistic_tracker
        if stat_tracker is not None:
            rep_statistic = stat_tracker.get_statistic(self.reputation_stat)
            if rep_statistic is None:
                rep_statistic = self._sim_info.statistic_tracker.add_statistic(self.reputation_stat)
            if rep_statistic is not None:
                rep_statistic.add_value(amount, interaction)

    @property
    def professional_reputation(self):
        if self.reputation_stat is None:
            return 0
        if self._sim_info.statistic_tracker is not None:
            rep_statistic = self._sim_info.statistic_tracker.get_statistic(self.reputation_stat)
            if rep_statistic is not None:
                return rep_statistic.get_value()
        return self.reputation_stat.default_value
