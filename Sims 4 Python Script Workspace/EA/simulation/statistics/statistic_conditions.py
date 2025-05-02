from __future__ import annotationsimport mathfrom _collections import defaultdictimport alarmsimport clockimport date_and_timeimport enumimport operatorimport servicesimport sims4.logimport sims4.mathimport sims4.resourcesfrom date_and_time import MINUTES_PER_HOURfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestVariant, TunableTestVariantFragfrom interactions import ParticipantType, ParticipantTypeActorTargetSim, ParticipantTypeSinglefrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import Anywherefrom objects import HiddenReasonFlagfrom objects.components.state import CommodityBasedObjectStateValue, ObjectStateValuefrom objects.components.state_references import TunableStateValueReferencefrom sims4.repr_utils import standard_reprfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableVariant, TunableReference, TunableThreshold, TunableFactory, TunableTuple, TunableSimMinute, HasTunableFactory, AutoFactoryInit, TunableSet, OptionalTunable, TunableList, TunableMapping, TunableEnumFlags, TunablePackSafeReferencefrom situations.situation_types import SituationCallbackOptionfrom typing import TYPE_CHECKINGfrom world.daytime_state_change import DaytimeStateChangeif TYPE_CHECKING:
    from event_testing.resolver import DataResolver
    from event_testing.test_base import BaseTest
    from interactions.base.interaction import Interaction
    from pivotal_moments.pivotal_moment import PivotalMoment
    from sims.sim_info import SimInfo
    from sims4.telemetry import _TelemetryHookWriter
    from sims4.utils import strformatter
    from statistics.base_statistic import BaseStatistic
    from typing import *TELEMETRY_CONDITION_EVENT = 1TELEMETRY_CONDITION_EVENT_TEST = 2TELEMETRY_CONDITION_TIME_RANGE = 3TELEMETRY_CONDITION_TIME_EVENT = 4TELEMETRY_CONDITION_PIVOTAL_MOMENT_COMPLETED = 5TELEMETRY_CONDITION_LIVE_EVENT_QUEST_AVAILABLE = 6logger = sims4.log.Logger('Condition')
class Condition:
    __slots__ = ('_satisfied', '_handle', '_owner', 'si_callback', 'save_id')

    def __init__(self, exit_action=None, interaction=None, situation=None, **kwargs):
        self._satisfied = False
        self._handle = None
        self._owner = None
        self.si_callback = None
        self.save_id = kwargs.get('save_id')

    def _satisfy(self, *_):
        if not self._satisfied:
            self._satisfied = True
            if not self.si_callback:
                logger.callstack('Condition is missing si_callback: {}', self, level=sims4.log.LEVEL_WARN, owner='tingyul')
                return
            self.si_callback(self._handle)

    def _unsatisfy(self, *_):
        self._satisfied = False

    @property
    def satisfied(self):
        return self._satisfied

    def attach_to_owner(self, owner, callback):
        raise NotImplementedError

    def detach_from_owner(self, owner, exiting=False):
        raise NotImplementedError

    def get_time_until_satisfy(self, interaction):
        return (None, None, None)

    def _get_target_and_tracker(self, interaction, participant, stat):
        target = interaction.get_participant(participant)
        if target is None:
            return (None, None)
        return (target, target.get_tracker(stat))

    def get_time_for_stat_satisfaction(self, interaction, subject, linked_stat, state_range):
        (target, tracker) = self._get_target_and_tracker(interaction, subject, linked_stat)
        if target is None or tracker is None:
            return (None, None, None)
        override_min_max_stats = interaction.progress_bar_enabled.override_min_max_values
        blacklist_statistics = interaction.progress_bar_enabled.blacklist_statistics
        best_time = None
        best_percent = None
        best_rate_of_change = None
        if tracker is not None:
            current_value = tracker.get_user_value(linked_stat)
            stat_op_list = interaction.instance_statistic_operations_gen()
            for stat_op in stat_op_list:
                if stat_op.stat is linked_stat:
                    if not stat_op.test_resolver(interaction.get_resolver()):
                        pass
                    else:
                        if blacklist_statistics and linked_stat in blacklist_statistics:
                            return (None, None, None)
                        if override_min_max_stats is not None and override_min_max_stats.statistic is stat_op.stat:
                            override_stat_values = True
                        else:
                            override_stat_values = False
                        stat_instance = tracker.get_statistic(stat_op.stat)
                        if stat_instance is None:
                            pass
                        else:
                            if stat_instance.continuous:
                                rate_change = stat_instance.get_change_rate()
                            else:
                                interval = stat_op._get_interval(interaction)
                                if not interval:
                                    pass
                                else:
                                    rate_change = stat_op.get_value()/interval
                                    if rate_change > 0:
                                        if state_range is not None:
                                            upper_bound = state_range.lower_bound
                                        else:
                                            upper_bound = self.threshold.value
                                        lower_bound = linked_stat.min_value
                                    else:
                                        if state_range is not None:
                                            lower_bound = state_range.upper_bound
                                        else:
                                            lower_bound = self.threshold.value
                                        upper_bound = linked_stat.max_value
                                    if override_stat_values:
                                        if override_min_max_stats.min_value is not None:
                                            lower_bound = override_min_max_stats.min_value
                                        if override_min_max_stats.max_value is not None:
                                            upper_bound = override_min_max_stats.max_value
                                    if rate_change > 0:
                                        threshold = upper_bound
                                        denominator = threshold - lower_bound
                                        percent = abs((current_value - lower_bound)/denominator) if denominator else 0
                                    else:
                                        threshold = lower_bound
                                        denominator = threshold - upper_bound
                                        percent = abs((current_value + denominator)/denominator) if denominator else 0
                                    if rate_change:
                                        if not denominator:
                                            pass
                                        else:
                                            time = (threshold - current_value)/rate_change
                                            rate_of_change = abs((1 - percent)/time if time != 0 else 0)
                                            if not best_time is None:
                                                if time < best_time:
                                                    best_time = time
                                                    best_percent = percent
                                                    best_rate_of_change = rate_of_change
                                            best_time = time
                                            best_percent = percent
                                            best_rate_of_change = rate_of_change
                            if rate_change > 0:
                                if state_range is not None:
                                    upper_bound = state_range.lower_bound
                                else:
                                    upper_bound = self.threshold.value
                                lower_bound = linked_stat.min_value
                            else:
                                if state_range is not None:
                                    lower_bound = state_range.upper_bound
                                else:
                                    lower_bound = self.threshold.value
                                upper_bound = linked_stat.max_value
                            if override_stat_values:
                                if override_min_max_stats.min_value is not None:
                                    lower_bound = override_min_max_stats.min_value
                                if override_min_max_stats.max_value is not None:
                                    upper_bound = override_min_max_stats.max_value
                            if rate_change > 0:
                                threshold = upper_bound
                                denominator = threshold - lower_bound
                                percent = abs((current_value - lower_bound)/denominator) if denominator else 0
                            else:
                                threshold = lower_bound
                                denominator = threshold - upper_bound
                                percent = abs((current_value + denominator)/denominator) if denominator else 0
                            if rate_change:
                                if not denominator:
                                    pass
                                else:
                                    time = (threshold - current_value)/rate_change
                                    rate_of_change = abs((1 - percent)/time if time != 0 else 0)
                                    if not best_time is None:
                                        if time < best_time:
                                            best_time = time
                                            best_percent = percent
                                            best_rate_of_change = rate_of_change
                                    best_time = time
                                    best_percent = percent
                                    best_rate_of_change = rate_of_change
        return (best_time, best_percent, best_rate_of_change)

class StatisticCondition(Condition):
    __slots__ = ('who', 'stat', 'threshold', 'absolute', '_unsatisfy_handle')

    def __init__(self, who=None, stat=None, threshold=None, absolute=False, **kwargs):
        super().__init__(**kwargs)
        self.who = who
        self.stat = stat
        self.threshold = threshold
        self.absolute = absolute
        self._unsatisfy_handle = None

    def __str__(self):
        return standard_repr(self, '{}.{} {}'.format(self.who.name, self.stat.__name__, self.threshold))

    def create_threshold(self, tracker):
        threshold = sims4.math.Threshold()
        threshold.comparison = self.threshold.comparison
        if self.absolute:
            cur_val = 0
        else:
            cur_val = tracker.get_value(self.stat, add=True)
        if self.threshold.comparison is operator.ge:
            pass
        if self.threshold.comparison is operator.le:
            pass
        if self.absolute or self.threshold.comparison is operator.ge:
            threshold.value = min([cur_val + self.threshold.value, self.stat.max_value])
        elif self.threshold.comparison is operator.le:
            threshold.value = max([cur_val + self.threshold.value, self.stat.min_value])
        else:
            raise NotImplementedError
        return threshold

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        (_, tracker) = self._get_target_and_tracker(owner, self.who, self.stat)
        if tracker is None:
            self._satisfy()
            return (None, None)
        threshold = self.create_threshold(tracker)
        value = tracker.get_value(self.stat)
        if threshold.compare(value):
            self._satisfy()
        self._handle = tracker.create_and_add_listener(self.stat, threshold, self._satisfy)
        self._unsatisfy_handle = tracker.create_and_add_listener(self.stat, threshold.inverse(), self._unsatisfy)
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        self._owner = None
        self.si_callback = None
        (_, tracker) = self._get_target_and_tracker(owner, self.who, self.stat)
        if tracker is None:
            return
        if self._handle is not None:
            tracker.remove_listener(self._handle)
            self._handle = None
        if self._unsatisfy_handle is not None:
            tracker.remove_listener(self._unsatisfy_handle)
            self._unsatisfy_handle = None

    def get_time_until_satisfy(self, interaction):
        return self.get_time_for_stat_satisfaction(interaction, self.who, self.stat, None)

class StateCondition(Condition):

    def __init__(self, subject, state, **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._state = state

    def __str__(self):
        return 'State {} on {}'.format(self._state, self._subject)

    def _on_owner_state_changed(self, owner, state, old_value, new_value):
        if state is self._state.state and self._state is new_value:
            self._satisfy(None)

    def attach_to_owner(self, owner, callback):
        subject = owner.get_participant(self._subject)
        if subject is not None and subject.state_component:
            self.si_callback = callback
            subject.add_state_changed_callback(self._on_owner_state_changed)
        return (None, None)

    def detach_from_owner(self, owner, **kwargs):
        subject = owner.get_participant(self._subject)
        if subject is not None and subject.state_component:
            subject.remove_state_changed_callback(self._on_owner_state_changed)
        self.si_callback = None

    def get_time_until_satisfy(self, interaction):
        if self._state.state.linked_stat is None:
            return (None, None, None)
        return self.get_time_for_stat_satisfaction(interaction, self._subject, self._state.state.linked_stat, self._state.range)

class TimeBasedCondition(Condition):
    __slots__ = '_interval'

    def __init__(self, interval_in_sim_minutes:'float'=0, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._interval = interval_in_sim_minutes

    def __str__(self) -> 'str':
        return 'Time Interval: {}'.format(self._interval)

    def set_alarm(self) -> 'None':
        time_span = clock.interval_in_sim_minutes(self._interval)
        alarm_owner = self._owner.sim if hasattr(self._owner, 'sim') else self._owner
        self._handle = alarms.add_alarm(alarm_owner, time_span, self._satisfy)

    def attach_to_owner(self, owner:'Union[Interaction, PivotalMoment]', callback:'Callable[[], None]') -> 'Tuple[None, alarms.AlarmHandle]':
        self._owner = owner
        self.si_callback = callback
        self.set_alarm()
        return (None, self._handle)

    def detach_from_owner(self, _:'Union[Interaction, PivotalMoment]', exiting:'bool'=False) -> 'None':
        if self._handle is not None:
            alarms.cancel_alarm(self._handle)
            self._handle = None
        self._owner = None
        self.si_callback = None

    def get_time_until_satisfy(self, interaction:'Interaction') -> 'Tuple[Optional[float], Optional[float], Optional[float]]':
        rounded_interval = math.floor(self._interval)
        if rounded_interval == 0:
            return (None, None, None)
        if self._satisfied:
            remaining_time = 0
        else:
            remaining_time = math.floor(self._handle.get_remaining_time().in_minutes())
        percent_done = (rounded_interval - remaining_time)/rounded_interval
        change_rate = 0
        if self._interval != 0:
            change_rate = 1/self._interval
        return (self._interval, percent_done, change_rate)

    @property
    def telemetry_triggering_condition(self) -> 'int':
        return TELEMETRY_CONDITION_TIME_RANGE

    def write_telemetry_data(self, hook:'_TelemetryHookWriter', arg_name:'str') -> 'None':
        hook.write_int(arg_name, self._interval)

class TimedEventCondition(TimeBasedCondition):
    __slots__ = ('_interval', '_event_type')

    def __init__(self, event_type:'TestEvent', interval_in_sim_minutes:'float'=0, **kwargs) -> 'None':
        super().__init__(interval_in_sim_minutes, **kwargs)
        self._event_type = event_type

    def __str__(self) -> 'str':
        return 'Event {}, Time Interval: {}'.format(self._event_type, self._interval)

    def attach_to_owner(self, owner:'Union[Interaction, PivotalMoment]', callback:'Callable[[], None]') -> 'Tuple[None, alarms.AlarmHandle]':
        services.get_event_manager().register(self, (self._event_type,))
        return super().attach_to_owner(owner, callback)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'DataResolver') -> 'None':
        alarms.cancel_alarm(self._handle)
        self.set_alarm()

    def detach_from_owner(self, _:'Union[Interaction, PivotalMoment]', exiting:'bool'=False) -> 'None':
        super().detach_from_owner(_, exiting)
        services.get_event_manager().unregister(self, (self._event_type,))

    @property
    def telemetry_triggering_condition(self) -> 'int':
        return TELEMETRY_CONDITION_TIME_EVENT

class EventBasedCondition(Condition):
    __slots__ = ('_event_type', '_event_custom_key')

    def __init__(self, event_type:'TestEvent', event_custom_key:'Optional[BaseStatistic]', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._event_type = event_type
        self._event_custom_key = event_custom_key

    def __str__(self):
        return 'Event {}'.format(self._event_type)

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        if self._event_custom_key is not None:
            self._handle = services.get_event_manager().register_with_custom_key(self, self._event_type, self._event_custom_key)
        else:
            self._handle = services.get_event_manager().register(self, (self._event_type,))
        return (None, self._handle)

    def handle_event(self, sim_info, event, resolver):
        self._satisfy(event)

    def detach_from_owner(self, _, exiting=False):
        if self._event_custom_key is not None:
            services.get_event_manager().unregister_with_custom_key(self, self._event_type, self._event_custom_key)
        else:
            services.get_event_manager().unregister(self, (self._event_type,))
        self._handle = None
        self._owner = None
        self.si_callback = None

    @property
    def telemetry_triggering_condition(self) -> 'int':
        return TELEMETRY_CONDITION_EVENT

    def write_telemetry_data(self, hook:'_TelemetryHookWriter', arg_name:'str') -> 'None':
        hook.write_enum(arg_name, self._event_type)

class EventTestCondition(EventBasedCondition):
    __slots__ = ('_event_type', '_event_custom_key', '_test')

    def __init__(self, event_type:'TestEvent', event_custom_key:'Optional[BaseStatistic]', test:'BaseTest', **kwargs) -> 'None':
        super().__init__(event_type, event_custom_key, **kwargs)
        self._test = test

    def __str__(self) -> 'str':
        return 'Event {}, test {}'.format(self._event_type, self._test)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'DataResolver') -> 'None':
        test_result = resolver(self._test)
        if test_result:
            self._satisfy(event)

    @property
    def telemetry_triggering_condition(self) -> 'int':
        return TELEMETRY_CONDITION_EVENT_TEST

class LiveEventQuestAvailability(Condition):
    __slots__ = ('available_quests',)

    def __init__(self, available_quests:'List[int]', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self.available_quests = available_quests

    def __str__(self) -> 'str':
        return 'Live Event Quest Available {}'.format(self.available_quests)

    def attach_to_owner(self, owner:'Union[Interaction, PivotalMoment]', callback:'Callable[[], None]') -> 'Tuple[None, alarms.AlarmHandle]':
        self._owner = owner
        self.si_callback = callback
        self._handle = services.get_event_manager().register(self, (TestEvent.LiveEventQuestsActive,))
        return (None, self._handle)

    def handle_event(self, _, event:'TestEvent', resolver:'DataResolver') -> 'None':
        active_quest_ids = resolver.event_kwargs.get('active_quest_ids')
        if active_quest_ids is None:
            return
        for quest in self.available_quests:
            if quest.guid64 in active_quest_ids:
                self._satisfy(event)
                return

    def detach_from_owner(self, _:'Union[Interaction, PivotalMoment]', exiting:'bool'=False) -> 'None':
        services.get_event_manager().unregister(self, (TestEvent.LiveEventQuestsActive,))
        self._handle = None
        self._owner = None
        self.si_callback = None

    @property
    def telemetry_triggering_condition(self) -> 'int':
        return TELEMETRY_CONDITION_LIVE_EVENT_QUEST_AVAILABLE

    def write_telemetry_data(self, hook:'_TelemetryHookWriter', arg_name:'str') -> 'None':
        questIdsString = None
        for (i, quest) in enumerate(self.available_quests):
            if quest.guid64:
                questIdsString = quest.guid64 if questIdsString is None else ', ' + quest.guid64
        if questIdsString:
            hook.write_guid(arg_name, quest.guid64)

class PivotalMomentCondition(Condition):
    __slots__ = ('_pivotal_moments', 'complete_pivotal_moment_id')

    def __init__(self, pivotal_moments:'List[PivotalMoment]', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._pivotal_moments = pivotal_moments
        self.complete_pivotal_moment_id = 0

    def __str__(self) -> 'str':
        return 'Pivotal moments {}'.format(self._pivotal_moments)

    def attach_to_owner(self, owner:'Union[Interaction, PivotalMoment]', callback:'Callable[[], None]') -> 'Tuple[None, alarms.AlarmHandle]':
        self._owner = owner
        self.si_callback = callback
        self._handle = services.get_event_manager().register(self, (TestEvent.PivotalMomentCompleted,))
        return (None, self._handle)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'DataResolver') -> 'None':
        if 'pivotal_moment' not in resolver.event_kwargs:
            return
        self.complete_pivotal_moment_id = resolver.event_kwargs.get('pivotal_moment')
        for pivotal_moment in self._pivotal_moments:
            if pivotal_moment.guid64 == self.complete_pivotal_moment_id:
                self._satisfy(event)
                return

    def detach_from_owner(self, _:'Union[Interaction, PivotalMoment]', exiting:'bool'=False):
        services.get_event_manager().unregister(self, (TestEvent.PivotalMomentCompleted,))
        self._handle = None
        self._owner = None
        self.si_callback = None

    @property
    def telemetry_triggering_condition(self) -> 'int':
        return TELEMETRY_CONDITION_PIVOTAL_MOMENT_COMPLETED

    def write_telemetry_data(self, hook:'_TelemetryHookWriter', arg_name:'str') -> 'None':
        hook.write_guid(arg_name, self.complete_pivotal_moment_id)

class InUseCondition(HasTunableFactory, AutoFactoryInit, Condition):
    FACTORY_TUNABLES = {'description': '\n            A condition that is satisfied when an object is no longer in use,\n            optionally specifying an affordance that the user of the object must\n            be running.\n            ', 'participant': TunableEnumEntry(description='\n            The participant of the interaction used to fetch the users against\n            which the condition test is run.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'affordance': OptionalTunable(description='\n            If specified, then the condition is satisfied if no user of the\n            specified object is running this affordance. If unspecified, will\n            be satisfied if object is no longer in use by any Sim.\n            ', tunable=TunableReference(description='\n                Only looking to see if this interaction is running and stopping\n                when this interaction is no longer running\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction'), disabled_name='Unspecified', enabled_name='Specific_Interaction')}

    def __str__(self):
        return 'In Use: {}'.format(self.affordance)

    def _get_use_list_obj(self):
        obj = self._owner.get_participant(self.participant)
        if obj.is_part:
            obj = obj.part_owner
        return obj

    def _on_use_list_changed(self, **kwargs):
        obj = self._get_use_list_obj()
        if self.affordance is None:
            if obj.in_use:
                return
        else:
            for user in obj.get_users(sims_only=True):
                for si in user.si_state:
                    if si.get_interaction_type() is self.affordance:
                        return
        self._satisfy(None)

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        obj = self._get_use_list_obj()
        if obj is not None:
            obj.register_on_use_list_changed(self._on_use_list_changed)
        return (None, None)

    def detach_from_owner(self, *_, **__):
        obj = self._get_use_list_obj()
        if obj is not None:
            obj.unregister_on_use_list_changed(self._on_use_list_changed)
        self._owner = None
        self.si_callback = None

class GroupBasedCondition(Condition, HasTunableFactory):
    FACTORY_TUNABLES = {'threshold': TunableThreshold(description='Threshold tested against group size.'), 'satisfy_if_missing_leader': Tunable(description='Test if the group leader is missing', tunable_type=bool, default=False)}

    def __init__(self, threshold, satisfy_if_missing_leader, **kwargs):
        super().__init__(**kwargs)
        self._threshold = threshold
        self._satisfy_if_missing_leader = satisfy_if_missing_leader
        self._social_group = None
        self._previously_satisfied = self._threshold.compare(0)

    def __str__(self):
        return 'Group Threshold: {}'.format(self._threshold)

    def _group_changed(self, group):
        leader_missing = False
        if self._threshold.compare(group.get_active_sim_count()):
            if group.group_leader_sim.id not in [member.sim_id for member in group.social_group_members]:
                leader_missing = True
            if self._satisfy_if_missing_leader and self._satisfy_if_missing_leader == leader_missing and not self._previously_satisfied:
                self._previously_satisfied = True
                self._satisfy()
            elif not leader_missing:
                self._previously_satisfied = False
                self._unsatisfy()
        else:
            self._previously_satisfied = False

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        social_group_owner = owner.super_interaction
        self._social_group = social_group_owner.social_group
        self._social_group.on_group_changed.append(self._group_changed)
        self._group_changed(self._social_group)
        return (None, None)

    def detach_from_owner(self, *_, **__):
        if self._social_group is not None:
            if self._group_changed in self._social_group.on_group_changed:
                self._social_group.on_group_changed.remove(self._group_changed)
            self._social_group = None
        self._owner = None
        self.si_callback = None

class ConstraintBasedCondition(HasTunableFactory, AutoFactoryInit, Condition):
    FACTORY_TUNABLES = {'constraints_to_use': OptionalTunable(description='\n            If enabled, this condition will use custom constraints. If disabled,\n            it will use the geometric constraints of the interaction on which\n            this is tuned.\n            ', tunable=TunableTuple(relative_participant=TunableEnumEntry(description="\n                    The participant that constraints will be generated\n                    relative to. For performance reasons, it is best to choose\n                    a participant that won't be moving during this interaction \n                    (usually the actor) since constraints must be recalculated\n                    whenever this participant moves.\n                    ", tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), _constraints=TunableMapping(description='\n                    Mapping between a participant and a set of constraints. The\n                    participant is what we check constraints against. This\n                    participant should rarely be the same as the relative\n                    participant since most constraints would have no meaning (an\n                    object is always within a radius of itself, etc).Constraints\n                    currently only supports geometry constraints.\n                    ', key_name='constrained_participant', value_name='constraints', key_type=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), value_type=TunableList(tunable=TunableGeometricConstraintVariant(constraint_locked_args={'multi_surface': True}, circle_locked_args={'require_los': False}, disabled_constraints={'spawn_points', 'current_position'}), minlength=1), minlength=1)), disabled_name='reuse_interaction_constraints', enabled_name='use_custom_constraints')}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tuned_constraints = None
        self._constraints = dict()
        self._relative_object = None

    def __str__(self):
        return 'Constraint: {}, Relative Object: {}'.format(self._constraints, self._relative_object)

    def generate_constraints(self, participant=None):
        for (participant, constraints) in self._tuned_constraints.items():
            constraint = Anywhere()
            for tuned_constraint in constraints:
                constraint = constraint.intersect(tuned_constraint.create_constraint(None, target=self._relative_object, target_position=self._relative_object.position))
            self._constraints[participant] = constraint

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        if self.constraints_to_use:
            self._tuned_constraints = defaultdict()
            for (participant, constraint_list) in self.constraints_to_use._constraints.items():
                constrained_object = owner.get_participant(participant)
                self._tuned_constraints[constrained_object] = constraint_list
            self._relative_object = owner.get_participant(self.constraints_to_use.relative_participant)
        else:
            self._tuned_constraints = dict()
            for (participant, constraints) in owner._constraints.items():
                constrained_object = owner.get_participant(participant)
                self._tuned_constraints[constrained_object] = [constraint.value for constraint in constraints[0]]
            self._relative_object = owner.get_participant(owner._constraints_actor)
        self.generate_constraints()
        for (participant, _) in self._constraints.items():
            self._check_constraint(participant)
            participant.register_on_location_changed(self._check_constraint)
        self._relative_object.register_on_location_changed(self._check_constraint)
        return (None, None)

    def _check_constraint(self, moved_participant, *_, **__):
        if moved_participant is self._relative_object:
            self.generate_constraints()
            participants_to_check = self._constraints.keys()
        else:
            participants_to_check = [moved_participant]
        for participant in participants_to_check:
            constraint = self._constraints[participant]
            if constraint.geometry is not None and not constraint.geometry.test_transform(participant.transform):
                self._satisfy()
                return
            self._unsatisfy()

    def detach_from_owner(self, *_, **__):
        self._relative_object.unregister_on_location_changed(self._check_constraint)
        for (participant, _) in self._constraints.items():
            participant.unregister_on_location_changed(self._check_constraint)
        self._owner = None
        self.si_callback = None

class TunableCondition(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, stat_based=TunableStatisticCondition(description='A condition based on the status of a statistic.'), state_based=TunableStateCondition(description='A condition based on the state of an object.'), time_based=TunableTimeRangeCondition(description='The minimum and maximum amount of time required to satisfy this condition.'), timed_event_based=TunableTimedEventCondition(description='A time range required to satisfy this condition, with an event to reset the timer.'), event_based=TunableEventBasedCondition(description='A condition that is satisfied by some event'), event_test_based=TunableEventTestCondition(description='A condition that is satisfied by some event, if a test passes.'), pivotal_moment=TunablePivotalMomentCondition(description='A condition that is satisfied by a pivotal moment being completed.'), career_based=TunableCareerCondition(description='A condition that is satisfied by career data'), wakeup_time_based=TunableWakeupCondition(description='A condition that is satisfied by being close to the schedule time for the sims career'), sim_spawn_based=TunableSimSpawnCondition(description='A condition that is satisfied when a Sim spawns in the world.'), group_based=GroupBasedCondition.TunableFactory(), daytime_state_change_based=DaytimeStateChangeCondition.TunableFactory(), in_use_based=InUseCondition.TunableFactory(), mood_based=MoodBasedCondition.TunableFactory(), object_relationship_based=ObjectRelationshipCondition.TunableFactory(), buff_based=BuffCondition.TunableFactory(), child_based=ObjectChildrenChangedCondition.TunableFactory(), constraint_based=ConstraintBasedCondition.TunableFactory(), rabbit_hole_based=TunableRabbitHoleExitCondition(), hidden_or_shown=HiddenOrShownCondition.TunableFactory(), situation_based=SituationCondition.TunableFactory(), default='stat_based', **kwargs)

class TunableTimeRangeCondition(TunableFactory):

    @staticmethod
    def factory(min_time, max_time, interaction=None, **kwargs):
        import random
        if min_time is None:
            time_in_sim_minutes = max_time
        elif max_time is None:
            time_in_sim_minutes = min_time
        elif min_time == max_time:
            time_in_sim_minutes = min_time
        else:
            time_in_sim_minutes = random.uniform(min_time, max_time)
        return TimeBasedCondition(time_in_sim_minutes, interaction=interaction, **kwargs)

    @staticmethod
    def _on_tunable_loaded_callback(cls, fields:'str', source:'strformatter', *, min_time, max_time, **kwargs) -> 'None':
        pass

    FACTORY_TYPE = factory

    def __init__(self, description:'str'='A time range in Sim minutes for this condition to be satisfied.', add_save_id:'bool'=False, **kwargs) -> 'None':
        if add_save_id:
            kwargs['save_id'] = Tunable(description="ID of this trigger so a pivotal moment can save that it's been satisfied.\n                    This must be unique per trigger set. Any ids that are the same across sets will all be considered satisfied\n                    if one is satisfied.", tunable_type=int, default=0)
        super().__init__(description=description, verify_tunable_callback=self._on_tunable_loaded_callback, min_time=TunableSimMinute(description='\n                             Minimum amount of time (in sim minutes) for this condition to be satisfied.\n                             ', default=1), max_time=TunableSimMinute(description='\n                             Maximum amount of time (in sim minutes) for this condition to be satisfied.\n                             ', default=None), **kwargs)

class RabbitHoleTimeBasedCondition(Condition):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._total_time_span = None

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        self._total_time_span = services.get_rabbit_hole_service().get_time_for_head_rabbit_hole(owner.sim.id)

    def detach_from_owner(self, _, exiting=False):
        self._handle = None
        self._owner = None
        self.si_callback = None

    def get_time_until_satisfy(self, interaction):
        if self._total_time_span is None:
            self._total_time_span = services.get_rabbit_hole_service().get_time_for_head_rabbit_hole(self._owner.sim.id)
            if self._total_time_span is None:
                return (None, None, None)
        total_time_minutes = self._total_time_span.in_minutes()
        time_left_span = services.get_rabbit_hole_service().get_time_for_head_rabbit_hole(self._owner.sim.id)
        if time_left_span is None:
            logger.error('Rabbit hole time condition is tuned on affordance ({}) but rabbit hole service cannot generate a time for it', self._owner)
            return (None, None, None)
        remaining_time_minutes = time_left_span.in_minutes()
        percent_done = 1 - remaining_time_minutes/total_time_minutes
        return (total_time_minutes, percent_done, 1/total_time_minutes)

class TunableRabbitHoleExitCondition(TunableTimeRangeCondition):

    @staticmethod
    def factory(min_time, max_time, interaction, **kwargs):
        return RabbitHoleTimeBasedCondition()

    FACTORY_TYPE = factory

    def __init__(self, description='An exit condition for rabbithole interactions', **kwargs):
        super().__init__(description=description, **kwargs)

class TunableTimedEventCondition(TunableFactory):

    @staticmethod
    def factory(event_to_listen_for:'TestEvent', min_time:'float', max_time:'float', interaction:'Interaction'=None, **kwargs) -> 'TimedEventCondition':
        import random
        if min_time is None:
            time_in_sim_minutes = max_time
        elif max_time is None:
            time_in_sim_minutes = min_time
        elif min_time == max_time:
            time_in_sim_minutes = min_time
        else:
            time_in_sim_minutes = random.uniform(min_time, max_time)
        return TimedEventCondition(event_to_listen_for, time_in_sim_minutes, interaction=interaction, **kwargs)

    @staticmethod
    def _on_tunable_loaded_callback(cls, fields:'str', source:'strformatter', *, event_to_listen_for, min_time, max_time, **kwargs) -> 'None':
        pass

    FACTORY_TYPE = factory

    def __init__(self, description:'str'='A time range in Sim minutes for this condition to be satisfied.', add_save_id:'bool'=False, **kwargs) -> 'None':
        if add_save_id:
            kwargs['save_id'] = Tunable(description="ID of this trigger so a pivotal moment can save that it's been satisfied.\n                    This must be unique per trigger set. Any ids that are the same across sets will all be considered satisfied\n                    if one is satisfied.", tunable_type=int, default=0)
        super().__init__(description=description, verify_tunable_callback=self._on_tunable_loaded_callback, event_to_listen_for=TunableEnumEntry(TestEvent, TestEvent.Invalid, description='Event that causes the timer to reset.'), min_time=TunableSimMinute(description='\n                             Minimum amount of time (in sim minutes) for this condition to be satisfied.\n                             ', default=1), max_time=TunableSimMinute(description='\n                             Maximum amount of time (in sim minutes) for this condition to be satisfied.\n                             ', default=None), **kwargs)

class TunableStatisticCondition(TunableFactory):
    FACTORY_TYPE = StatisticCondition

    def __init__(self, description='Apply an operation to a statistic.', **kwargs):
        super().__init__(who=TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='Who or what to apply this test to'), stat=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), description='The commodity we are gaining.'), threshold=TunableThreshold(description='A commodity value and comparison that defines the exit condition hits (or hit commodity.maximum).'), absolute=Tunable(bool, True, description="True = treat the threshold value as an absolute commodity value.  Otherwise, it is relative to the Sim's start value."), **kwargs)

class TunableStateCondition(TunableFactory):

    @staticmethod
    def factory(subject, state, **kwargs):
        if isinstance(state, ObjectStateValue):
            return StateCondition(subject, state, **kwargs)
        linked_stat = state.state.state.linked_stat
        if state.boundary:
            threshold = sims4.math.Threshold(state.state.range.upper_bound, operator.ge)
        else:
            threshold = sims4.math.Threshold(state.state.range.lower_bound, operator.le)
        return StatisticCondition(subject, linked_stat, threshold, absolute=True)

    FACTORY_TYPE = factory

    def __init__(self, description='A condition to determine if an object is in a particular state.', **kwargs):
        super().__init__(subject=TunableEnumEntry(ParticipantType, ParticipantType.Object, description='The subject to check the condition on.'), state=TunableVariant(description='The state to check for.', on_trigger=TunableStateValueReference(description='Satisfy the condition when this state is triggered.'), on_boundary=TunableTuple(description='Satisfy the condition when a boundary of this stat-based state is reached', state=TunableStateValueReference(class_restrictions=CommodityBasedObjectStateValue, description='The state required to satisfy the condition'), boundary=TunableVariant(description='The boundary required to be reached for the condition to be satisfied.', locked_args={'upper': True, 'lower': False}, default='upper')), default='on_trigger'), **kwargs)

class EventConditionCustomKeyVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, statistic=TunablePackSafeReference(description='\n                The statistic that the event must carry as custom key.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), default='statistic', **kwargs)

class TunableEventBasedCondition(TunableFactory):

    @staticmethod
    def factory(event_to_listen_for:'TestEvent', event_custom_key:'Optional[BaseStatistic]', **kwargs) -> 'EventBasedCondition':
        return EventBasedCondition(event_to_listen_for, event_custom_key, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description:'str'='A condition that is satisfied by some event', add_save_id=False, **kwargs):
        if add_save_id:
            kwargs['save_id'] = Tunable(description="ID of this trigger so a pivotal moment can save that it's been satisfied.\n            This must be unique per trigger set. Any ids that are the same across sets will all be considered satisfied\n            if one is satisfied.", tunable_type=int, default=0)
        super().__init__(description=description, event_to_listen_for=TunableEnumEntry(TestEvent, TestEvent.Invalid, description='Event that this exit condition should listen for '), event_custom_key=OptionalTunable(description='\n                             If enabled, only listen for events of the selected type when paired with this custom key.\n                             ', tunable=EventConditionCustomKeyVariant(description='\n                                 When registering the event listener, it will only listen for events with this key.\n                                 ')), **kwargs)

class TunableEventTestCondition(TunableFactory):

    @staticmethod
    def factory(event_to_listen_for:'TestEvent', test:'BaseTest', event_custom_key:'Optional[BaseStatistic]', **kwargs) -> 'EventTestCondition':
        return EventTestCondition(event_to_listen_for, event_custom_key, test, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description:'str'='A condition that is satisfied by some event when a test passes.', add_save_id:'bool'=False, use_test_variant_frag:'bool'=False, **kwargs) -> 'None':
        if add_save_id:
            kwargs['save_id'] = Tunable(description="ID of this trigger so a pivotal moment can save that it's been satisfied.\n            This must be unique per trigger set. Any ids that are the same across sets will all be considered satisfied\n            if one is satisfied.", tunable_type=int, default=0)
        if use_test_variant_frag:
            test_tunable = TunableTestVariantFrag(description='Pass this test to satisfy the condition.')
        else:
            test_tunable = TunableTestVariant(description='Pass this test to satisfy the condition.')
        super().__init__(description=description, event_to_listen_for=TunableEnumEntry(TestEvent, TestEvent.Invalid, description='Event that this exit condition should listen for '), test=test_tunable, event_custom_key=OptionalTunable(description='\n                             If enabled, only listen for events of the selected type when paired with this custom key.\n                             ', tunable=EventConditionCustomKeyVariant(description='\n                                     When registering the event listener, it will only listen for events with this key.\n                                     ')), **kwargs)

class TunableLiveEventQuestAvailability(TunableFactory):

    @staticmethod
    def factory(available_quests:'List[PivotalMoment]', **kwargs) -> 'LiveEventQuestAvailability':
        return LiveEventQuestAvailability(available_quests, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description:'str'='A condition that is satisfied when a quest live event provides active quests.', add_save_id:'bool'=False, **kwargs) -> 'None':
        if add_save_id:
            kwargs['save_id'] = Tunable(description="ID of this trigger so a pivotal moment can save that it's been satisfied.\n                     This must be unique per trigger set. Any ids that are the same across sets will all be considered satisfied\n                     if one is satisfied.", tunable_type=int, default=0)
        super().__init__(description=description, available_quests=TunableList(description='\n                             List of quests that need to be provided by a live event before the condition \n                             is satisfied.', tunable=TunableReference(description='\n                                 A quest that could satisfy this condition when active.\n                                 ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('LiveEventQuest',)), minlength=1), **kwargs)

class TunablePivotalMomentCondition(TunableFactory):

    @staticmethod
    def factory(pivotal_moments:'List[PivotalMoment]', **kwargs) -> 'PivotalMomentCondition':
        return PivotalMomentCondition(pivotal_moments, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description:'str'='A condition that is satisfied when a pivotal moment from the tuned list is completed.', add_save_id:'bool'=False, **kwargs) -> 'None':
        if add_save_id:
            kwargs['save_id'] = Tunable(description="ID of this trigger so a pivotal moment can save that it's been satisfied.\n            This must be unique per trigger set. Any ids that are the same across sets will all be considered satisfied\n            if one is satisfied.", tunable_type=int, default=0)
        super().__init__(description=description, pivotal_moments=TunableList(description='\n                             List of pivotal moments that the condition waits to complete.\n                             The condition is satisfied when any of these is completed.', tunable=TunableReference(description='\n                                 A pivotal moment that could satisfy this condition when completed.\n                                 ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('PivotalMoment',)), minlength=1), **kwargs)

class TunableCareerCondition(TunableFactory):

    @staticmethod
    def factory(*args, **kwargs):
        return CareerCondition(*args, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description='A Career Condition to cause an interaction to exit.', **kwargs):
        super().__init__(description=description, who=TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='Who or what to apply this test to'), **kwargs)

class CareerCondition(Condition):
    __slots__ = ('who', '_career')

    def __init__(self, who=None, **kwargs):
        super().__init__(**kwargs)
        self.who = who
        self._career = None

    def __str__(self):
        return 'Career: {}'.format(self.who)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.CareerStayLate and sim_info is self._owner.sim.sim_info:
            alarms.cancel_alarm(self._handle)
            self._schedule_alarm(self._career)

    def _schedule_alarm(self, career):
        time_to_work_end = career.time_until_end_of_work()
        self._handle = alarms.add_alarm(self._owner.sim.sim_info, time_to_work_end, self._satisfy)

    def attach_to_owner(self, owner, callback):
        self.si_callback = callback
        self._career = self._get_target_career(owner)
        self._owner = owner
        self._schedule_alarm(self._career)
        services.get_event_manager().register_single_event(self, TestEvent.CareerStayLate)
        return (None, self._handle)

    def detach_from_owner(self, owner, exiting=False):
        if self._handle is not None:
            alarms.cancel_alarm(self._handle)
            self._handle = None
        self.si_callback = None
        services.get_event_manager().unregister_single_event(self, TestEvent.CareerStayLate)

    def _get_target_career(self, interaction, exiting=False):
        target_sim = interaction.get_participant(self.who)
        if exiting and target_sim is None:
            return
        target_career = interaction.get_career()
        return target_career

    def get_time_until_satisfy(self, interaction):
        career = self._get_target_career(interaction)
        if career is None:
            return (None, None, None)
        time_to_work_end = career.time_until_end_of_work().in_minutes()
        time_worked = career.get_hours_worked()*MINUTES_PER_HOUR
        total_time = time_worked + time_to_work_end
        if total_time == 0:
            return (None, None, None)
        percentage_done = time_worked/total_time
        rate = 1/total_time
        return (time_to_work_end, percentage_done, rate)

class DaytimeStateChangeCondition(HasTunableFactory, AutoFactoryInit, TimeBasedCondition):
    FACTORY_TUNABLES = {'who': TunableEnumEntry(description="\n            The Sim who we're running this test on\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor), '_daytime': TunableEnumEntry(description='\n            The daytime state change (i.e. sunrise) that triggers the condition\n            ', tunable_type=DaytimeStateChange, default=DaytimeStateChange.Sunset)}

    def __str__(self):
        return 'DaytimeStateChange: {}, trigger on next {}'.format(self.who, self._daytime)

    def attach_to_owner(self, owner, callback):
        sim = owner.get_participant(self.who)
        if sim is None:
            return
        region_instance = services.current_region()
        if region_instance is None:
            logger.error('region instance is unexpectedly None')
            return
        state_change_time = None
        if self._daytime == DaytimeStateChange.Sunrise:
            state_change_time = region_instance.get_sunrise_time()
        elif self._daytime == DaytimeStateChange.Sunset:
            state_change_time = region_instance.get_sunset_time()
        else:
            logger.error('Unhandled case for DaytimeStateChange value: {}', self._daytime)
            return
        time_span = services.game_clock_service().now().time_till_next_day_time(state_change_time)
        self._interval = time_span.in_minutes()
        super().attach_to_owner(owner, callback)

class TunableWakeupCondition(TunableFactory):

    @staticmethod
    def factory(*args, **kwargs):
        return WakeupCondition(*args, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description='A Tunable Condition that takes into account when the Sim needs to be up for their work schedule.', **kwargs):
        super().__init__(description=description, who=TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='Who or what to apply this test to'), hours_prior_to_schedule_start=Tunable(float, 0, description='The number of hours prior to the schedule start to satisfy this condition.'), **kwargs)

class WakeupCondition(TimeBasedCondition):

    def __init__(self, who=None, hours_prior_to_schedule_start=0, **kwargs):
        super().__init__(*(0,), **kwargs)
        self.who = who
        self.hours_prior_to_schedule_start = hours_prior_to_schedule_start

    def __str__(self):
        return 'Wakeup: {}, {} hours before schedule'.format(self.who, self.hours_prior_to_schedule_start)

    def attach_to_owner(self, owner, callback):
        sim = owner.get_participant(self.who)
        if sim is None:
            return
        offset_time = date_and_time.create_time_span(hours=self.hours_prior_to_schedule_start)
        time_span_until_work_start_time = sim.get_time_until_next_wakeup(offset_time=offset_time)
        if time_span_until_work_start_time.in_ticks() <= 0:
            logger.error('Wakeup time is in the past.', owner='rez')
            time_span_until_work_start_time += date_and_time.create_time_span(days=1)
        self._interval = time_span_until_work_start_time.in_minutes()
        return super().attach_to_owner(owner, callback)

class SimSpawnCondition(Condition):

    def __init__(self, participant_type=None, **kwargs):
        super().__init__(**kwargs)
        self._participant_type = participant_type
        self._sim_id = None

    def __str__(self):
        return 'Sim Spawn: {}'.format(self._sim_id)

    def attach_to_owner(self, owner, callback):
        self.si_callback = callback
        self._sim_id = owner.get_participant(self._participant_type)
        if self._sim_id is not None and isinstance(self._sim_id, int):
            object_manager = services.object_manager()
            object_manager.add_sim_spawn_condition(self._sim_id, self._satisfy)
        else:
            logger.error('SimSpawnCondition: invalid sim id found {} with participant type {}', self._sim_id, self._participant_type)
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        if self._sim_id is not None and isinstance(self._sim_id, int):
            object_manager = services.object_manager()
            object_manager.remove_sim_spawn_condition(self._sim_id, self._satisfy)
        else:
            logger.error('SimSpawnCondition: invalid sim id found {} with participant type {}', self._sim_id, self._participant_type)
        self.si_callback = None

class TunableSimSpawnCondition(TunableFactory):

    @staticmethod
    def factory(*args, **kwargs):
        return SimSpawnCondition(*args, **kwargs)

    FACTORY_TYPE = factory

    def __init__(self, description='A Sim spawning Condition to cause an interaction to exit.', **kwargs):
        super().__init__(description=description, participant_type=TunableEnumEntry(ParticipantType, ParticipantType.PickedItemId, description='Who or what to apply this test to'), **kwargs)

class MoodBasedCondition(HasTunableFactory, AutoFactoryInit, Condition):
    FACTORY_TUNABLES = {'description': '\n            A condition that is satisfied when a Sim enters a specific mood.\n            ', 'participant': TunableEnumEntry(description="\n            The Sim whose mood we're checking against.\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor), 'mood': TunableReference(description='\n            The mood that satisfies the condition.\n            ', manager=services.get_instance_manager(sims4.resources.Types.MOOD), class_restrictions=('Mood',), needs_tuning=True), 'invert': Tunable(description='\n            If enabled, this condition will satisfy when the Sim is not in this\n            mood.\n            ', tunable_type=bool, default=False)}

    def __str__(self):
        if self.invert:
            return 'Not in Mood: {}'.format(self.mood)
        return 'Mood: {}'.format(self.mood)

    def _on_mood_changed(self, **kwargs):
        sim = self._owner.get_participant(self.participant)
        if sim is None:
            logger.error('MoodBasedCondition: Failed to find Sim for participant {} in {}', self.participant, self._owner)
            return
        in_mood = sim.get_mood() is self.mood
        if in_mood == self.invert:
            self._unsatisfy()
        else:
            self._satisfy()

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        sim = owner.get_participant(self.participant)
        sim.Buffs.on_mood_changed.append(self._on_mood_changed)
        self._on_mood_changed()
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        sim = owner.get_participant(self.participant)
        if sim is not None and self._on_mood_changed in sim.Buffs.on_mood_changed:
            sim.Buffs.on_mood_changed.remove(self._on_mood_changed)
        self._owner = None
        self.si_callback = None

class ObjectRelationshipCondition(HasTunableFactory, AutoFactoryInit, Condition):
    FACTORY_TUNABLES = {'description': '\n            A condition that is satisfied when a Sim reaches a specific object\n            relationship threshold.\n            ', 'sim': TunableEnumEntry(description="\n            The Sim whose object relationship we're checking.\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor), 'object': TunableEnumEntry(description="\n            The object whose object relationship we're checking.\n            ", tunable_type=ParticipantType, default=ParticipantType.Object), 'threshold': TunableThreshold(description='\n            The relationship threshold that will trigger this condition.\n            ')}

    def __init__(self, interaction=None, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction

    def __str__(self):
        return 'Object Relationship: {} {}'.format(self.threshold.comparison, self.threshold.value)

    def _on_relationship_changed(self):
        sim = self._owner.get_participant(self.sim)
        obj = self._owner.get_participant(self.object)
        relationship_value = obj.objectrelationship_component.get_relationship_value(sim.id)
        if relationship_value is not None and self.threshold.compare(relationship_value):
            self._satisfy()
            if self._interaction:
                self._interaction._send_progress_bar_update_msg(1, 0, self._owner)
        if self._satisfied or self._interaction:
            initial_value = obj.objectrelationship_component.get_relationship_initial_value()
            denominator = self.threshold.value - initial_value
            if denominator != 0:
                rate_change = relationship_value - initial_value/self.threshold.value - initial_value
                self._owner._send_progress_bar_update_msg(rate_change/100, 0, self._owner)

    def attach_to_owner(self, owner, callback):
        self._owner = owner
        self.si_callback = callback
        sim = owner.get_participant(self.sim)
        obj = self._owner.get_participant(self.object)
        if sim is None:
            logger.error('Trying to add a condition for {} to test object relationship, but the                           ParticipantType {} tuned for Sim is not valid.', self._owner, sim, owner='tastle')
        elif obj is None:
            logger.error('Trying to add a condition for {} to test object relationship, but the                           ParticipantType {} tuned for Object is not valid.', self._owner, obj, owner='tastle')
        elif obj.objectrelationship_component is None:
            logger.error('Trying to add a condition on interaction {} to test object relationship, but                           {} has no object relationship component.', self._owner, obj, owner='tastle')
        else:
            obj.objectrelationship_component.add_relationship_changed_callback_for_sim_id(sim.sim_id, self._on_relationship_changed)
            self._on_relationship_changed()
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        sim = owner.get_participant(self.sim)
        obj = self._owner.get_participant(self.object)
        if sim is None or obj is None:
            return
        if obj.objectrelationship_component is not None:
            obj.objectrelationship_component.remove_relationship_changed_callback_for_sim_id(sim.sim_id, self._on_relationship_changed)
        self._owner = None
        self.si_callback = None

class BuffCondition(HasTunableFactory, AutoFactoryInit, Condition):

    class Timing(enum.Int):
        ON_ADD = 0
        ON_REMOVE = 1
        HAS_BUFF = 2
        NOT_HAS_BUFF = 3

    FACTORY_TUNABLES = {'description': '\n            A condition that is satisfied when a Sim gains or loses a buff.\n            ', 'participant': TunableEnumEntry(description="\n            The participant whose buffs we're checking.\n            ", tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'buff': TunablePackSafeReference(description="\n            The buff we're checking.\n            ", manager=services.get_instance_manager(sims4.resources.Types.BUFF)), 'timing': TunableEnumEntry(description='\n            When the condition satisfies.\n            Choices:\n            ON_ADD: Only check the condition on the edge of the buff being\n            added.  This will not satisfy if you have the buff when the\n            interaction starts.\n            ON_REMOVE: Only check the condition on the edge of the buff being\n            removed.  This will not satisfy if you do not have the buff when\n            the interaction starts.\n            HAS_BUFF: Check for the buff existing at any time this condition\n            is active.  This will satisfy if you have the buff when the\n            interaction starts.\n            NOT_HAS_BUFF: Check for the buff not existing at any time this\n            condition is active.  This will satisfy if you do not have the buff\n            when the interaction starts.\n            ', tunable_type=Timing, default=Timing.ON_ADD)}

    def __str__(self):
        return 'BuffCondition: {} {} {}'.format(self.participant, self.buff, self.timing)

    def attach_to_owner(self, owner, callback):
        self.si_callback = callback
        self._owner = owner
        if self.buff is None:
            return (None, None)
        sim = self._owner.get_participant(self.participant)
        if self.timing == BuffCondition.Timing.HAS_BUFF:
            if sim.has_buff(self.buff):
                self._satisfy()
        elif self.timing == BuffCondition.Timing.NOT_HAS_BUFF and not sim.has_buff(self.buff):
            self._satisfy()
        self._enable_buff_watcher()
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        if self.buff is not None:
            self._disable_buff_watcher()
        self._owner = None
        self.si_callback = None

    def _enable_buff_watcher(self):
        sim = self._owner.get_participant(self.participant)
        sim.Buffs.on_buff_added.append(self._on_buff_added)
        sim.Buffs.on_buff_removed.append(self._on_buff_removed)

    def _disable_buff_watcher(self):
        sim = self._owner.get_participant(self.participant)
        if self._on_buff_added in sim.Buffs.on_buff_added:
            sim.Buffs.on_buff_added.remove(self._on_buff_added)
        if self._on_buff_removed in sim.Buffs.on_buff_removed:
            sim.Buffs.on_buff_removed.remove(self._on_buff_removed)

    def _on_buff_added(self, buff_type, sim_id):
        if buff_type is self.buff:
            if self.timing == BuffCondition.Timing.ON_ADD or self.timing == BuffCondition.Timing.HAS_BUFF:
                self._satisfy()
            else:
                self._unsatisfy()

    def _on_buff_removed(self, buff_type, sim_id):
        if buff_type is self.buff:
            if self.timing == BuffCondition.Timing.ON_REMOVE or self.timing == BuffCondition.Timing.NOT_HAS_BUFF:
                self._satisfy()
            else:
                self._unsatisfy()

class ObjectChildrenChangedCondition(HasTunableFactory, AutoFactoryInit, Condition):
    CONDITION_SINGLE_CHILD = 'condition_single_child'
    CONDITION_CHILDREN_COUNT = 'condition_children_count'
    CONDITION_ALL_CHILDREN = 'condition_all_children'
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant to be checked for a change in children.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'slot_types': OptionalTunable(description='\n            If enabled, we will restrict the contition tests against slots in\n            this list. Otherwise we will consider all slots.\n            ', tunable=TunableSet(description='\n                A list of slot types to restrict the test against.\n                ', tunable=TunableReference(description=' \n                    The slot type to be tested against. This check will check to \n                    see if there is a child in the specified slot.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE), class_restrictions=('SlotType',)))), 'condition': TunableVariant(description='\n            The condition we want to test for.\n            ', single_child_changed=TunableTuple(description='\n                When a child is added to the specified slot types, we\n                will pass the test.\n                ', negate=Tunable(description='\n                    If enabled, we will check for a child removed instead of\n                    added to the slot types. Otherwise, we check for a child\n                    added to the specified slot types.\n                    ', tunable_type=bool, default=False), locked_args={'condition_type': CONDITION_SINGLE_CHILD}), children_count=TunableTuple(description='\n                When the number of children in the specified slot types passes\n                the threshold, we will satisfy the condition.\n                ', threshold=TunableThreshold(description='\n                    The threshold against the number of children in the\n                    specified slot types.\n                    ', value=Tunable(description='\n                        The number of objects we expect to be in the specified\n                        slot types.\n                        ', tunable_type=int, default=0)), locked_args={'condition_type': CONDITION_CHILDREN_COUNT}), all_or_none=TunableTuple(description='\n                Satisfied when we run out of slots of the specified types.\n                ', negate=Tunable(description='\n                    If checked, we will satisfy when all the slots are empty.\n                    Otherwise we satisfy when all slots are filled.\n                    ', tunable_type=bool, default=False), locked_args={'condition_type': CONDITION_ALL_CHILDREN}), default='single_child_changed')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent_object_ref = None

    def attach_to_owner(self, owner, callback):
        self.si_callback = callback
        self._owner = owner
        parent = self._owner.get_participant(self.participant)
        if parent is None:
            return
        self._parent_object_ref = parent.ref()
        if self.condition.condition_type == ObjectChildrenChangedCondition.CONDITION_CHILDREN_COUNT:
            self._threshold_test(parent)
        elif self.condition.condition_type == ObjectChildrenChangedCondition.CONDITION_ALL_CHILDREN:
            self._all_slots_test(parent)
        parent.register_for_on_children_changed_callback(self._on_child_changed_callback)

    @property
    def parent_object(self):
        if self._parent_object_ref is not None:
            return self._parent_object_ref()

    def detach_from_owner(self, owner, exiting=False):
        self._owner = None
        self.si_callback = None
        parent = self.parent_object
        if parent is None:
            return
        parent.unregister_for_on_children_changed_callback(self._on_child_changed_callback)

    def _threshold_test(self, parent, *_, **__):
        runtime_slots = list(parent.get_runtime_slots_gen(slot_types=self.slot_types, bone_name_hash=None))
        if self.condition.threshold.compare(sum([int(not runtime_slot.empty) for runtime_slot in runtime_slots])):
            self._satisfy()
        else:
            self._unsatisfy()

    def _all_slots_test(self, parent, *_, **__):
        runtime_slots = list(parent.get_runtime_slots_gen(slot_types=self.slot_types, bone_name_hash=None))
        if self.condition.negate and all([runtime_slot.empty for runtime_slot in runtime_slots]) or self.condition.negate or all([not runtime_slot.empty for runtime_slot in runtime_slots]):
            self._satisfy()
        else:
            self._unsatisfy()

    def _child_changed_test(self, parent, child, location=None):
        if location is None:
            if self.condition.negate:
                self._staisfy()
        elif location.parent is parent:
            for runtime_slot in parent.get_runtime_slots_gen(slot_types=self.slot_types, bone_name_hash=None):
                if location.slot_hash == runtime_slot.slot_name_hash and not self.condition.negate:
                    self._satisfy()
                    break

    def _on_child_changed_callback(self, child, location=None, new_parent=None):
        parent = self.parent_object
        if parent is None:
            return
        if self.condition.condition_type == ObjectChildrenChangedCondition.CONDITION_CHILDREN_COUNT:
            self._threshold_test(parent)
        elif self.condition.condition_type == ObjectChildrenChangedCondition.CONDITION_ALL_CHILDREN:
            self._all_slots_test(parent)
        elif self.condition.condition_type == ObjectChildrenChangedCondition.CONDITION_SINGLE_CHILD:
            self._child_changed_test(parent, child, location=location)

class HiddenOrShownCondition(HasTunableFactory, AutoFactoryInit, Condition):

    class Timing(enum.Int):
        ON_HIDDEN = 0
        ON_SHOWN = ...
        IS_HIDDEN = ...
        NOT_HIDDEN = ...

    FACTORY_TUNABLES = {'description': '\n            A condition that is satisfied when an object is hidden or shown.\n            ', 'participant': TunableEnumEntry(description='\n            The participant whose hidden flags we are checking.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'hidden_flags': TunableEnumFlags(description='\n            The hidden reason we care about. If any of the flags exist as\n            hidden reasons, we satisfy this condition. If this is empty, then\n            we will care about any reason that would cause the object to be\n            hidden, and expect zero flags remaining when the object is shown.\n            ', enum_type=HiddenReasonFlag, default=HiddenReasonFlag.RABBIT_HOLE, allow_no_flags=True), 'timing': TunableEnumEntry(description='\n            When the condition satisfies.\n            Choices:\n            ON_HIDDEN: Only check the condition on the edge of the object being\n            hidden. This will not satisfy if you are hidden when the\n            interaction starts.\n            ON_SHOWN: Only check the condition on the edge of the object being\n            shown. This will not satisfy if you are not hidden when the \n            interaction starts.\n            IS_HIDDEN: Check that the object is hidden at any time this \n            condition is active. This will satisfy if you are hidden when the\n            interaction starts.\n            NOT_HIDDEN: Check that the object is not hidden at any time this\n            condition is active. This will satisfy if you are not hidden\n            when the interaction starts.\n            ', tunable_type=Timing, default=Timing.ON_HIDDEN)}

    def __str__(self):
        return 'HiddenOrShownCondition: {} {} {}'.format(self.participant, self.hidden_flags, self.timing)

    def attach_to_owner(self, owner, callback):
        self.si_callback = callback
        self._owner = owner
        obj = self._owner.get_participant(self.participant)
        is_hidden = obj.is_hidden()
        if self.timing == HiddenOrShownCondition.Timing.IS_HIDDEN:
            if is_hidden and self.hidden_flags and obj.has_hidden_flags(self.hidden_flags):
                self._satisfy()
        elif self.timing == HiddenOrShownCondition.Timing.NOT_HIDDEN and (is_hidden and self.hidden_flags) and not obj.has_hidden_flags(self.hidden_flags):
            self._satisfy()
        self._enable_hidden_flags_watcher()
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        self._disable_hidden_flags_watcher()
        self._owner = None
        self.si_callback = None

    def _enable_hidden_flags_watcher(self):
        obj = self._owner.get_participant(self.participant)
        obj.register_on_hidden_or_shown(self._on_hidden_or_shown)

    def _disable_hidden_flags_watcher(self):
        obj = self._owner.get_participant(self.participant)
        if obj.is_on_hidden_or_shown_callback_registered(self._on_hidden_or_shown):
            obj.unregister_on_hidden_or_shown(self._on_hidden_or_shown)

    def _on_hidden_or_shown(self, obj, hidden_flags_delta, added=False):
        if added and self.hidden_flags and obj.has_hidden_flags(self.hidden_flags):
            if self.timing == HiddenOrShownCondition.Timing.ON_HIDDEN or self.timing == HiddenOrShownCondition.Timing.IS_HIDDEN:
                self._satisfy()
            else:
                self._unsatisfy()
        elif added or not (self.hidden_flags and obj.has_hidden_flags(self.hidden_flags)):
            if self.timing == HiddenOrShownCondition.Timing.ON_SHOWN or self.timing == HiddenOrShownCondition.Timing.NOT_HIDDEN:
                self._satisfy()
            else:
                self._unsatisfy()

class SituationCondition(HasTunableFactory, AutoFactoryInit, Condition):

    class Timing(enum.Int):
        ON_END = 0
        RUNNING = 1
        NOT_RUNNING = 2

    FACTORY_TUNABLES = {'description': '\n            A condition that is satisfied when any of listed situation started or ended.\n            ', 'situation_types': TunableList(description='\n            A list of all situations the Sim needs to leave.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True)), 'timing': TunableEnumEntry(description='\n            When the condition satisfies.\n            Choices:\n            ON_END: Only check the condition when a situation ends. Condition will\n            only succeed if the situation is already running before the interaction.\n            RUNNING: Check for the situation running at any time this condition\n            is active.\n            NOT_RUNNING: Check for the situation not running at any time this\n            condition is active.\n            ', tunable_type=Timing, default=Timing.ON_END)}

    def __str__(self):
        return 'SituationCondition: {} {} {}'.format(self.situation_types, self.timing)

    def attach_to_owner(self, owner, callback):
        self.si_callback = callback
        self._owner = owner
        self._situation_ids = []
        situation_manager = services.get_zone_situation_manager()
        running_situations = situation_manager.running_situations()
        for situation in running_situations:
            if isinstance(situation, self.situation_types):
                if self.timing == SituationCondition.Timing.RUNNING:
                    self._satisfy()
                    break
                elif self.timing == SituationCondition.Timing.ON_END:
                    situation_manager.register_for_callback(situation.id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
                    self._situation_ids.append(situation.id)
        if self.timing == SituationCondition.Timing.NOT_RUNNING:
            self._satisfy()
        return (None, None)

    def detach_from_owner(self, owner, exiting=False):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.unregister_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
        self._owner = None
        self.si_callback = None
        self._situation_ids.clear()

    def _situation_end_callback(self, situation_id:'int', callback_option:'SituationCallbackOption', _) -> 'None':
        self._satisfy()
