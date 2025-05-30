from __future__ import annotationsimport randomfrom event_testing.resolver import DoubleSimResolver, SingleSimResolver, SingleActorAndObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSavedActorfrom interactions.utils import LootTypefrom interactions.utils.loot_basic_op import BaseLootOperation, BaseTargetedLootOperation, LootOperationTargetFilterTestMixinfrom interactions.utils.success_chance import SuccessChancefrom interactions.utils.tunable_icon import TunableIconfrom relationships.relationship_enums import RelationshipTrackType, SentimentSignType, SentimentDurationTypefrom relationships.relationship_track import ObjectRelationshipTrackfrom sims4 import mathfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableVariant, TunableInterval, TunableEnumEntry, TunableReference, TunablePercent, TunableFactory, TunableRate, TunableList, OptionalTunable, TunableTuple, TunableRange, HasTunableSingletonFactory, TunableEnumFlags, TunablePackSafeReference, AutoFactoryInitfrom sims4.tuning.tunable_base import RateDescriptionsfrom singletons import DEFAULTfrom statistics.skill import Skillfrom statistics.skill_loot_data import TunableSkillLootData, TunableVariantSkillLootDatafrom statistics.skill_loot_data import SkillEffectivenessfrom statistics.statistic_enums import PeriodicStatisticBehavior, StatisticLockActionfrom tunable_multiplier import TunableStatisticModifierCurve, TunableObjectCostModifierCurve, TunableMultiplierfrom ui.ui_dialog_notification import UiDialogNotificationimport enumimport objects.components.typesimport servicesimport sims4.logimport sims4.resourcesimport statistics.statistic_categoriesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from relationships.relationship_track import RelationshipTracklogger = sims4.log.Logger('SimStatistics')autonomy_logger = sims4.log.Logger('Autonomy')GAIN_TYPE_RATE = 0GAIN_TYPE_AMOUNT = 1
class StatisticOperation(BaseLootOperation):
    STATIC_CHANGE_INTERVAL = 1
    DISPLAY_TEXT = TunableLocalizedStringFactory(description='\n        A string displaying the amount that this stat operation awards. It will\n        be provided two tokens: the statistic name and the value change.\n        ')
    DEFAULT_PARTICIPANT_ARGUMENTS = {'subject': TunableEnumFlags(description='\n             The owner of the stat that we are operating on.\n             ', enum_type=ParticipantType, default=ParticipantType.Actor, invalid_enums=(ParticipantType.Invalid,))}

    @staticmethod
    def get_statistic_override(*, pack_safe):
        return (pack_safe,)

    STATISTIC_RESTRICTIONS = ('Commodity', 'Statistic', 'Skill', 'LifeSkillStatistic', 'RankedStatistic', 'TraitStatistic')

    @TunableFactory.factory_option
    def statistic_override(pack_safe=False):
        return {'stat': TunableReference(description='\n                The statistic we are operating on.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=pack_safe, class_restrictions=StatisticOperation.STATISTIC_RESTRICTIONS)}

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if hasattr(value, 'stat') and hasattr(value.stat, 'track_type'):
            logger.error('{}: Tuned Stat {} is a RelationshipTrack, which is not supported.', source, value.stat)

    FACTORY_TUNABLES = {'advertise': Tunable(description='\n            This statistic operation should advertise to autonomy.  This only\n            advertises if the statistic operation is used as part of Periodic\n            Statistic Change.\n            ', tunable_type=bool, needs_tuning=True, default=True), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, stat=None, **kwargs):
        super().__init__(**kwargs)
        self._stat = stat
        self._ad_multiplier = 1
        self._loot_type = LootType.GENERIC
        if issubclass(self._stat, Skill):
            self._loot_type = LootType.SKILL

    def __repr__(self):
        return '<{} {} {}>'.format(type(self).__name__, self.stat, self.subject)

    @property
    def stat(self):
        return self._stat

    @property
    def loot_type(self):
        return self._loot_type

    @property
    def ad_multiplier(self):
        return self._ad_multiplier

    def _apply_to_subject_and_target(self, subject, target, resolver):
        stat = self.get_stat(None)
        if not subject.is_locked(stat):
            tracker = subject.get_tracker(stat)
            if tracker is not None:
                self._apply(tracker, resolver=resolver)

    def _apply(self, tracker, resolver=None):
        raise NotImplementedError

    def get_value(self, obj=None, interaction=None, sims=None):
        raise NotImplementedError

    def _attempt_to_get_real_stat_value(self, obj, interaction):
        if interaction is not None:
            obj = interaction.get_participant(ParticipantType.Actor)
        if obj is None and obj is not None:
            stat_value = obj.get_stat_value(self.stat)
            if stat_value is not None:
                return stat_value
        return self.stat.default_value

    def _get_interval(self, aop):
        return aop.super_affordance.approximate_duration

    def get_fulfillment_rate(self, interaction):
        if not self._advertise:
            return 0
        value = self.get_value(interaction=interaction)
        if interaction.target is not None:
            value *= interaction.target.get_stat_multiplier(self.stat, self.subject)
        interval = self._get_interval(interaction)
        if interval <= 0:
            logger.error('Tuning error: affordance interval should be greater than 0 (defaulting to 1)')
            interval = 1
        score = value/interval
        return score

    def _get_display_text(self, resolver=None):
        if self.stat.stat_name is None or not self.stat.stat_name.hash:
            return
        else:
            value = self.get_value()
            if value:
                return self.DISPLAY_TEXT(*self._get_display_text_tokens())

    def _get_display_text_tokens(self, resolver=None):
        return (self.stat.stat_name, self.get_value())

def _get_tunable_amount(gain_type=GAIN_TYPE_AMOUNT):
    if gain_type == GAIN_TYPE_RATE:
        return TunableRate(description='\n            The gain, per interval for this operation.\n            ', display_name='Rate', rate_description=RateDescriptions.PER_SIM_MINUTE, tunable_type=float, default=0)
    if gain_type == GAIN_TYPE_AMOUNT:
        return Tunable(description='\n            The one-time gain for this operation.\n            ', tunable_type=float, default=0)
    raise ValueError('Unsupported gain type: {}'.format(gain_type))

class StatisticChangeOp(StatisticOperation):

    class MaxPoints(HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'max_points': Tunable(description='\n                The point total that a stat cannot go above when increasing. \n                If the increase would go above this point total, instead it will\n                just be equal to this point total.\n                ', tunable_type=int, default=0)}

        def __init__(self, *args, max_points=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.max_points = max_points

        def __call__(self, stat):
            return self.max_points

    class MaxRank(HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'max_rank': TunableRange(description='\n                The rank that a stat cannot go beyond when increasing.\n                If the increase would go beyond achieving this rank, instead\n                it will be set to the min points required to meet this rank.\n                This will prevent any gains toward the next rank from occurring.\n                \n                NOTE: Must be used with a RankedStatistic or it will return 0\n                as the max.\n                ', tunable_type=int, default=0, minimum=0)}

        def __init__(self, *args, max_rank=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.max_rank = max_rank

        def __call__(self, stat):
            if hasattr(stat, 'points_to_rank'):
                return stat.points_to_rank(self.max_rank)
            return 0

    FACTORY_TUNABLES = {'amount': lambda *args, **kwargs: _get_tunable_amount(*args, **kwargs), 'maximum': TunableVariant(description='\n        A variant containing the different ways you can cap the max amount a\n        statistic reaches as result of a change.\n        ', points=MaxPoints.TunableFactory(), rank=MaxRank.TunableFactory(), locked_args={'no_max': None}, default='no_max'), 'exclusive_to_owning_si': Tunable(description='\n            If enabled, this gain will be exclusive to the SI that created it\n            and will not be allowed to occur if the sim is running mixers from\n            a different SI.\n            If disabled, this gain will happen as long as this\n            SI is active, regardless of which SI owns the mixer the sim is\n            currently running.\n            This is only effective on Sims.\n            ', tunable_type=bool, needs_tuning=True, default=True), 'periodic_change_behavior': TunableEnumEntry(description='\n         When applying this change operation at the beginning of an interaction\n         as part of a periodic statistic change and statistic is\n         a continuous statistic, tune the behavior of this operation when\n         interaction begins.\n         \n         Terminology:\n         BaseBehavior: For change operations that succeed chance\n         and test or if chance is 100% or no tests, the statistic stores the\n         start time and when interaction ends determine how much time is passed\n         and multiply amount.  Continuous statistic WILL NOT decay with this\n         behavior.  This is for better performance.\n         \n         IntervalBehavior:  If continuous statistic is using interval behavior.\n         the amount tuned will be given at specified interval if chance and\n         tests succeeds.  Continuous statistics WILL decay between interval\n         time.\n                 \n         Tuning Behavior \n         APPLY_AT_START_ONLY: If chance and tests for change operation is\n         successful, periodic update will occur and follow BaseBehavior.  If\n         either fail, change operation is not given at any point.\n         \n         RETEST_ON_INTERVAL: If test and chance succeeds, then this will follow\n         BaseBehavior.  If test or chance fails, this operation will follow\n         interval behavior.\n         \n         APPLY_AT_INTERVAL_ONLY: This will strictly follow Interval Behavior.\n         ', tunable_type=PeriodicStatisticBehavior, default=PeriodicStatisticBehavior.APPLY_AT_START_ONLY), 'statistic_multipliers': TunableList(description='\n        Tunables for adding statistic based multipliers to the payout in the\n        format:\n        \n        amount *= statistic.value\n        ', tunable=TunableStatisticModifierCurve.TunableFactory()), 'object_cost_multiplier': OptionalTunable(description='\n        When enabled allows you to multiply the stat gain amount based on the \n        value of the object specified.\n        ', tunable=TunableObjectCostModifierCurve.TunableFactory()), 'tunable_multipliers': TunableList(description='\n        List of multipliers to be applied when gaining amount\n        ', tunable=TunableMultiplier.TunableFactory())}

    def __init__(self, amount=0, min_value=None, max_value=None, exclusive_to_owning_si=None, periodic_change_behavior=PeriodicStatisticBehavior.APPLY_AT_START_ONLY, maximum=None, statistic_multipliers=None, object_cost_multiplier=None, tunable_multipliers=None, **kwargs):
        super().__init__(**kwargs)
        self._amount = amount
        self.maximum = maximum
        self._min_value = min_value
        self._max_value = None
        if max_value is not None:
            self._max_value = max_value
        elif maximum is not None:
            self._max_value = maximum(self.stat)
        self._exclusive_to_owning_si = exclusive_to_owning_si
        self.periodic_change_behavior = periodic_change_behavior
        self._statistic_multipliers = statistic_multipliers
        self._object_cost_multiplier = object_cost_multiplier
        self._tunable_multipliers = tunable_multipliers

    @property
    def exclusive_to_owning_si(self):
        return self._exclusive_to_owning_si

    def get_value(self, obj=None, interaction=None, sims=None):
        multiplier = 1
        if sims:
            targets = sims.copy()
        elif interaction is not None:
            targets = interaction.get_participants(ParticipantType.Actor)
        else:
            targets = None
        if targets:
            multiplier = self.stat.get_skill_based_statistic_multiplier(targets, self._amount)
            for sim in targets:
                resolver = interaction.get_resolver() if interaction is not None else SingleSimResolver(sim)
                local_mult = self._get_local_statistic_multipliers(resolver)
                multiplier *= local_mult
        if self._object_cost_multiplier is not None:
            resolver = interaction.get_resolver() if interaction is not None else SingleActorAndObjectResolver(sim, object)
            multiplier *= self._get_object_cost_multiplier(resolver)
        return self._amount*multiplier

    def _get_interval(self, aop):
        return StatisticOperation.STATIC_CHANGE_INTERVAL

    def _apply(self, tracker, resolver=None):
        interaction = resolver.interaction if resolver is not None else None
        multiplier = self._get_local_multipliers(resolver=resolver)
        amount = self._amount*multiplier
        tracker.add_value(self.stat, amount, min_value=self._min_value, max_value=self._max_value, interaction=interaction)

    def _remove(self, tracker, interaction=None):
        resolver = interaction.get_resolver if interaction is not None else SingleSimResolver(tracker.owner)
        multiplier = self._get_local_multipliers(resolver=resolver)
        amount = self._amount*multiplier
        tracker.add_value(self.stat, -amount, min_value=self._min_value, max_value=self._max_value, interaction=interaction)

    def _get_local_multipliers(self, resolver):
        multiplier = self._get_local_statistic_multipliers(resolver)
        multiplier *= self._get_object_cost_multiplier(resolver)
        multiplier *= self._get_local_tunable_multipliers(resolver)
        return multiplier

    def _get_local_tunable_multipliers(self, resolver):
        total_multiplier = 1
        if self._tunable_multipliers is not None:
            for multiplier in self._tunable_multipliers:
                total_multiplier *= multiplier.get_multiplier(resolver)
        return total_multiplier

    def _get_local_statistic_multipliers(self, resolver):
        multiplier = 1
        if self._statistic_multipliers is not None:
            for data in self._statistic_multipliers:
                multiplier *= data.get_multiplier(resolver, None)
        return multiplier

    def _get_object_cost_multiplier(self, resolver):
        multiplier = 1
        if self._object_cost_multiplier is not None:
            multiplier *= self._object_cost_multiplier.get_multiplier(resolver, None)
        return multiplier

class StatisticSetOp(StatisticOperation):
    FACTORY_TUNABLES = {'value': Tunable(description='\n            The new statistic value.', tunable_type=int, default=None)}

    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} set to {}>'.format(self.__class__.__name__, self.stat.__name__, self.value)
        return '<{}: Stat is None in StatisticSetOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        stat_value = self._attempt_to_get_real_stat_value(obj, interaction)
        return self.value - stat_value

    def _apply(self, tracker, resolver=None):
        interaction = resolver.interaction if resolver is not None else None
        tracker.set_value(self.stat, self.value, interaction=interaction)

class StatisticSetRankOp(StatisticOperation):

    @TunableFactory.factory_option
    def statistic_override(pack_safe=False):
        return {'stat': TunableReference(description='\n                The statistic we are operating on.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=pack_safe, class_restrictions=('RankedStatistic',))}

    FACTORY_TUNABLES = {'value': Tunable(description='\n            The new rank value.\n            ', tunable_type=int, default=None)}

    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} set rank to {}>'.format(self.__class__.__name__, self.stat.__name__, self.value)
        return '<{}: Stat is None in StatisticSetRankOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        stat_value = self._attempt_to_get_real_stat_value(obj, interaction)
        rank_value = self.stat.points_to_rank(self.value)
        return rank_value - stat_value

    def _apply(self, tracker, resolver=None):
        interaction = resolver.interaction if resolver is not None else None
        tracker.set_value(self.stat, self.stat.points_to_rank(self.value), interaction=interaction)

class StatisticSetRangeOp(StatisticOperation):

    class _StatisticSetRangeFloat(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'value_range': TunableInterval(description='\n                The upper and lower bound of the range.\n                ', tunable_type=float, default_lower=1, default_upper=2)}

        def get_value(self):
            return self.value_range.random_float()

    class _StatisticSetRangeInt(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'value_range': TunableInterval(description='\n                The upper and lower bound of the range.\n                ', tunable_type=int, default_lower=1, default_upper=2)}

        def get_value(self):
            return self.value_range.random_int()

    FACTORY_TUNABLES = {'locked_args': {'subject': ParticipantType.Actor}, 'value_type': TunableVariant(float_range=_StatisticSetRangeFloat.TunableFactory(), int_range=_StatisticSetRangeInt.TunableFactory(), default='int_range')}
    REMOVE_INSTANCE_TUNABLES = ('advertise', 'tests', 'chance')

    def __init__(self, value_type=None, **kwargs):
        super().__init__(**kwargs)
        self.value_type = value_type

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} set in range [{},{}]>'.format(self.__class__.__name__, self.stat.__name__, self.value_type.value_range.lower_bound, self.value_type.value_range.upper_bound)
        return '<{}: Stat is None in StatisticSetRangeOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        stat_value = self._attempt_to_get_real_stat_value(obj, interaction)
        return self.value_type.value_range.upper_bound - stat_value

    def _apply(self, tracker, resolver=None):
        value = self.value_type.get_value()
        tracker.set_value(self.stat, value, interaction=None)

class StatisticSetMaxOp(StatisticOperation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} maximum>'.format(self.__class__.__name__, self.stat.__name__)
        return '<{}: Stat is None in StatisticSetMaxOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        stat_value = self._attempt_to_get_real_stat_value(obj, interaction)
        return self.stat.max_value - stat_value

    def _apply(self, tracker, **kwargs):
        tracker.set_max(self.stat)

class StatisticSetMinOp(StatisticOperation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} minimum>'.format(self.__class__.__name__, self.stat.__name__)
        return '<{}: Stat is None in StatisticSetMinOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        stat_value = self._attempt_to_get_real_stat_value(obj, interaction)
        return self.stat.min_value - stat_value

    def _apply(self, tracker, **kwargs):
        tracker.set_min(self.stat)

class StatisticAddOp(StatisticOperation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} add stat>'.format(self.__class__.__name__, self.stat.__name__)
        return '<{}: Stat is None in StatisticAddOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        return 0

    def _apply(self, tracker, **kwargs):
        tracker.add_statistic(self.stat)

class StatisticRemoveOp(StatisticOperation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} remove/set to convergence>'.format(self.__class__.__name__, self.stat.__name__)
        return '<{}: Stat is None in StatisticRemoveOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        return 0

    def _apply(self, tracker, **kwargs):
        tracker.remove_statistic(self.stat)

class StatisticLockOp(BaseLootOperation):
    FACTORY_TUNABLES = {'stat': TunablePackSafeReference(description='\n            The statistic we are operating on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity',)), 'lock': Tunable(description='\n            Lock or unlock a statistic.\n            ', tunable_type=bool, default=True), 'lock_action': TunableEnumEntry(description='\n            Determine what to do with the value of a\n            statistic when we lock it.\n            ', tunable_type=StatisticLockAction, default=StatisticLockAction.DO_NOT_CHANGE_VALUE)}

    def __init__(self, stat, lock, lock_action, **kwargs):
        super().__init__(**kwargs)
        self._stat = stat
        self._lock = lock
        self._lock_action = lock_action

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if self._stat is None:
            return
        statistic_component = subject.get_component(objects.components.types.STATISTIC_COMPONENT)
        if statistic_component is None:
            logger.error('Trying to lock statistic {} on {}, but it has no Statistic Component.', self._stat, subject)
            return
        interaction = resolver.interaction
        if self._lock:
            statistic_component.lock_statistic(self._stat, self._lock_action, 'locked by loot in interaction {} at {}'.format(interaction, services.time_service().sim_now))
        else:
            statistic_component.unlock_statistic(self._stat, 'unlocked by loot in interaction {} at {}'.format(interaction, services.time_service().sim_now))

class TransferType(enum.Int):
    ADDITIVE = 0
    SUBTRACTIVE = 1
    REPLACEMENT = 2
    AVERAGE = 3

class StatisticTransferOp(StatisticOperation):
    FACTORY_TUNABLES = {'statistic_donor': TunableEnumEntry(description='\n            The owner of the statistic we are transferring the value from.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'transferred_stat': TunableReference(description='\n            The statistic whose value to transfer.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'transfer_type': TunableEnumEntry(description='\n            Type of statistic transfer to use.\n            ', tunable_type=TransferType, default=TransferType.ADDITIVE), 'transfer_type_average_advanced': OptionalTunable(description='\n            If enabled, the average calculation will be the sum of multiplying\n            the stat value and stat quantity then dividing with total quantity.\n            T  = Transferred Stat value\n            S  = Stat value\n            QT = Quantity Transferred Stat value\n            QS = Quantity Stat value\n            Result = ((T * QT) + (S * QS)) / (QT + QS)\n            \n            If disabled, the result will calculate Mean of 2 stat values.\n            Result = (T + S) / 2\n            ', tunable=TunableTuple(description='\n                Statistic quantities for both subject and donor.\n                ', quantity_transferred_stat=TunableReference(description='\n                    Statistic quantity donor which will be applied to the\n                    average calculation.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), quantity_stat=TunableReference(description='\n                    Statistic quantity subject which will be applied to the\n                    average calculation.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))))}

    def __init__(self, statistic_donor=None, transferred_stat=None, transfer_type=None, transfer_type_average_advanced=None, **kwargs):
        super().__init__(**kwargs)
        self._statistic_donor = statistic_donor
        self._transferred_stat = transferred_stat
        self._transfer_type = transfer_type
        self._transfer_type_average_advanced = transfer_type_average_advanced

    def __repr__(self):
        if self.stat is not None:
            return '<{}: {} transfer>'.format(self.__class__.__name__, self.stat.__name__)
        return '<{}: Stat is None in StatisticTransferOp>'.format(self.__class__.__name__)

    def get_value(self, obj=None, interaction=None, sims=None):
        return self.stat.get_value()

    def _apply(self, tracker, resolver=None):
        interaction = resolver.interaction if resolver is not None else None
        donors = resolver.get_participants(self._statistic_donor) if resolver is not None else []
        for donor in donors:
            transfer_stat_tracker = donor.get_tracker(self._transferred_stat)
            if transfer_stat_tracker is None:
                pass
            else:
                transfer_value = transfer_stat_tracker.get_value(self._transferred_stat)
                if self._transfer_type == TransferType.ADDITIVE:
                    tracker.add_value(self.stat, transfer_value, interaction=interaction)
                elif self._transfer_type == TransferType.SUBTRACTIVE:
                    tracker.add_value(self.stat, -transfer_value, interaction=interaction)
                elif self._transfer_type == TransferType.REPLACEMENT:
                    tracker.set_value(self.stat, transfer_value, interaction=interaction)
                elif self._transfer_type == TransferType.AVERAGE:
                    subject_value = tracker.get_value(self.stat)
                    if self._transfer_type_average_advanced is None:
                        average_value = (subject_value + transfer_value)/2
                    else:
                        subject = tracker.owner
                        if subject is None:
                            logger.error('Failed to find the owner for tracker {}.', tracker, owner='mkartika')
                        else:
                            q_stat_tracker = subject.get_tracker(self._transfer_type_average_advanced.quantity_stat)
                            q_transfer_stat_tracker = donor.get_tracker(self._transfer_type_average_advanced.quantity_transferred_stat)
                            if q_stat_tracker is None:
                                logger.error('Failed to find quantity stat tracker for stat {} on {}.', self._transfer_type_average_advanced.quantity_stat, subject, owner='mkartika')
                            elif q_transfer_stat_tracker is None:
                                logger.error('Failed to find quantity stat tracker for stat {} on {}.', self._transfer_type_average_advanced.quantity_transferred_stat, donor, owner='mkartika')
                            else:
                                q_value = q_stat_tracker.get_value(self._transfer_type_average_advanced.quantity_stat)
                                q_transfer_value = q_transfer_stat_tracker.get_value(self._transfer_type_average_advanced.quantity_transferred_stat)
                                average_value = (subject_value*q_value + transfer_value*q_transfer_value)/(q_value + q_transfer_value)
                                tracker.set_value(self.stat, average_value, interaction=interaction)
                    tracker.set_value(self.stat, average_value, interaction=interaction)

class NormalizeStatisticsOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'stats_to_normalize': TunableList(description='\n            Stats to be affected by the normalization.\n            ', tunable=TunableReference(services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=statistics.commodity.Commodity)), 'normalize_percent': TunablePercent(description='\n            In seeking the average value, this is the percent of movement toward the average value \n            the stat will move to achieve the new value. For example, if you have a Sim with 50 \n            fun, and a Sim with 100 fun, and want to normalize them exactly halfway to their \n            average of 75, tune this to 100%. A value of 50% would move one Sim to 67.5 and the other\n            to 77.5\n            ', default=100, maximum=100, minimum=0)}

    def __init__(self, stats_to_normalize, normalize_percent, **kwargs):
        super().__init__(**kwargs)
        self._stats = stats_to_normalize
        self._normalize_percent = normalize_percent

    def _apply_to_subject_and_target(self, subject, target, resolver):
        for stat_type in self._stats:
            source_tracker = target.get_tracker(stat_type)
            if source_tracker is None:
                return
            if not source_tracker.has_statistic(stat_type):
                pass
            else:
                target_tracker = subject.get_tracker(stat_type)
                if target_tracker is None:
                    return
                source_value = source_tracker.get_value(stat_type)
                target_value = target_tracker.get_value(stat_type)
                average_value = (source_value + target_value)/2
                source_percent_gain = (source_value - average_value)*self._normalize_percent
                target_percent_gain = (target_value - average_value)*self._normalize_percent
                target_tracker.set_value(stat_type, source_value - source_percent_gain)
                source_tracker.set_value(stat_type, target_value - target_percent_gain)

class SkillEffectivenessLoot(StatisticChangeOp):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The sim(s) to operation is applied to.', tunable_type=ParticipantType, default=ParticipantType.Actor), 'effectiveness': TunableEnumEntry(description='\n            Enum to determine which curve to use when giving points to sim.', tunable_type=SkillEffectiveness, needs_tuning=True, default=SkillEffectiveness.STANDARD), 'level': Tunable(description='\n            x-point on skill effectiveness curve.', tunable_type=int, default=0), 'locked_args': {'amount': 0}}

    def __init__(self, stat, amount, effectiveness, level, **kwargs):
        if stat is None:
            final_amount = 0
        else:
            final_amount = stat.get_skill_effectiveness_points_gain(effectiveness, level)
        super().__init__(stat=stat, amount=final_amount, **kwargs)

class TunableStatisticChange(TunableVariant):

    def __init__(self, *args, locked_args=None, variant_locked_args=None, gain_type=GAIN_TYPE_AMOUNT, include_relationship_ops=True, statistic_override=None, description='A variant of statistic operations.', **kwargs):
        if include_relationship_ops:
            kwargs['object_relationship_change'] = StatisticAddObjectRelationship.TunableFactory(description='\n                Add to the object relationship score statistic for this Super Interaction.\n                ', amount=gain_type, **ObjectRelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_change'] = StatisticAddRelationship.TunableFactory(description='\n                Adds to the relationship score statistic for this Super Interaction\n                ', amount=gain_type, **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_change_multiple'] = StatisticAddRelationshipMultiple.TunableFactory(description='\n                Modifies the relationship track score of multiple tracks at \n                once.\n                ', amount=gain_type, **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_set'] = StatisticSetRelationship.TunableFactory(description='\n                Sets the relationship score statistic to a specific value.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_set_convergence_value'] = StatisticSetRelationshipTrackConvergenceValue.TunableFactory(description='\n                Sets the convergence value on the given relationship track.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_remove_track'] = StatisticRemoveRelationshipTrack.TunableFactory(description='\n                Removes the given relationship track.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_set_multiple'] = StatisticSetRelationshipMultiple.TunableFactory(description='\n                Sets the relationship track score of multiple tracks at \n                once.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_set_max'] = StatisticSetRelationshipMax.TunableFactory(description='\n                Sets a relationship track to its maximum value.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['random_relationship_set'] = RandomSimStatisticAddRelationship.TunableFactory(description='\n                Adds the relationship statistic score about an amount to a \n                random sim selected out of all the known sims for the Actor.\n                ', locked_args={'target_participant_type': ParticipantType.Actor, 'advertise': False, 'stat': None}, **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_set_interval_decay_rate_override'] = RelationshipSetIntervalDecayRateOverride.TunableFactory(description='\n                Apply interval decay rate overrides, which skips all other decay rate logic.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_clear_interval_decay_rate_override'] = RelationshipClearIntervalDecayRateOverride.TunableFactory(description='\n                Clear interval decay rate overrides.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_set_decay_enabled_override'] = RelationshipSetDecayEnabledOverride.TunableFactory(description="\n                Force relationship track's decay to be enabled or disabled. Will supersede any other logic.\n                ", **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
            kwargs['relationship_clear_decay_enabled_override'] = RelationshipClearDecayEnabledOverride.TunableFactory(description='\n                Clear any decay enabled override for the given relationship track. Allows other logic to drive decay\n                enabled.\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS)
        super().__init__(*args, description=description, statistic_change=StatisticChangeOp.TunableFactory(description='\n                Modify the value of a statistic.\n                ', locked_args=locked_args, statistic_override=statistic_override, amount=gain_type, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_add=StatisticAddOp.TunableFactory(description='\n                Attempt to add the specified statistic.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_remove=StatisticRemoveOp.TunableFactory(description='\n                Attempt to remove the specified statistic.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_set=StatisticSetOp.TunableFactory(description='\n                Set a statistic to the provided value.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_set_rank=StatisticSetRankOp.TunableFactory(description='\n                Set a Ranked Statistic to a specific rank level.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_set_max=StatisticSetMaxOp.TunableFactory(description='\n                Set a statistic to its maximum value.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_set_min=StatisticSetMinOp.TunableFactory(description='\n                Set a statistic to its minimum value.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_set_in_range=StatisticSetRangeOp.TunableFactory(description='\n                Set a statistic to a random value in the tuned range.\n                ', locked_args=locked_args, statistic_override=statistic_override, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_transfer=StatisticTransferOp.TunableFactory(description='\n                Transfer a statistic value from one target to another.\n                ', locked_args=locked_args, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), statistic_lock=StatisticLockOp.TunableFactory(description='\n                Lock or Unlock a statistic.\n                '), statistic_remove_by_category=RemoveStatisticByCategory.TunableFactory(description='\n                Remove all statistics of a specific category.\n                '), statistic_change_by_category=ChangeStatisticByCategory.TunableFactory(description='\n                Change value of  all statistics of a specific category.\n                '), locked_args=variant_locked_args, **kwargs)

class TunableProgressiveStatisticChange(TunableVariant):

    def __init__(self, *args, locked_args=None, **kwargs):
        super().__init__(*args, description='A variant of statistic operations.', statistic_change=StatisticChangeOp.TunableFactory(description='\n                Modify the value of a statistic.\n                ', locked_args=locked_args, **StatisticOperation.DEFAULT_PARTICIPANT_ARGUMENTS), relationship_change=StatisticAddRelationship.TunableFactory(description='\n                Adds to the relationship score statistic for this Super Interaction\n                ', **RelationshipOperation.DEFAULT_PARTICIPANT_ARGUMENTS), **kwargs)

class DynamicSkillLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'skill_loot_data_override': TunableSkillLootData(description="\n            This data will override loot data in the interaction. In\n            interaction, tuning field 'skill_loot_data' is used to determine\n            skill loot data."), 'exclusive_to_owning_si': Tunable(description='\n            If enabled, this gain will be exclusive to the SI that created it\n            and will not be allowed to occur if the sim is running mixers from\n            a different SI.\n            If disabled, this gain will happen as long as this\n            SI is active, regardless of which SI owns the mixer the sim is\n            currently running.\n            This is only effective on Sims.\n            ', tunable_type=bool, needs_tuning=True, default=True)}

    def __init__(self, skill_loot_data_override, exclusive_to_owning_si, **kwargs):
        super().__init__(**kwargs)
        self._skill_loot_data_override = skill_loot_data_override
        self._exclusive_to_owning_si = exclusive_to_owning_si

    @property
    def periodic_change_behavior(self):
        return PeriodicStatisticBehavior.APPLY_AT_START_ONLY

    @property
    def exclusive_to_owning_si(self):
        return self._exclusive_to_owning_si

    def _get_skill_level_data(self, interaction):
        stat = self._skill_loot_data_override.stat
        if stat is None and interaction is not None:
            stat = interaction.stat_from_skill_loot_data
            if stat is None:
                return (None, None, None)
        effectiveness = self._skill_loot_data_override.effectiveness
        if effectiveness is None and interaction is not None:
            effectiveness = interaction.skill_effectiveness_from_skill_loot_data
            if effectiveness is None:
                logger.error('Skill Effectiveness is not tuned for this loot operation in {}', interaction)
                return (None, None, None)
        level_range = self._skill_loot_data_override.level_range
        if interaction is not None:
            level_range = interaction.level_range_from_skill_loot_data
        return (stat, effectiveness, level_range)

    def get_stat(self, interaction):
        stat = self._skill_loot_data_override.stat
        if stat is None:
            stat = interaction.stat_from_skill_loot_data
        return stat

    def get_value(self, obj=None, interaction=None, sims=None):
        amount = 0
        multiplier = 1
        if interaction is not None:
            (stat_type, effectiveness, level_range) = self._get_skill_level_data(interaction)
            if stat_type is None:
                return 0
            tracker = obj.get_tracker(stat_type)
            if tracker is None:
                return stat_type.default_value
            amount = self._get_change_amount(tracker, stat_type, effectiveness, level_range)
            if sims:
                targets = sims.copy()
            else:
                targets = interaction.get_participants(ParticipantType.Actor)
            if targets:
                multiplier = stat_type.get_skill_based_statistic_multiplier(targets, amount)
        return amount*multiplier

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (stat_type, effectiveness, level_range) = self._get_skill_level_data(resolver.interaction)
        if stat_type is None:
            return
        tracker = subject.get_tracker(stat_type)
        if tracker is not None:
            amount = self._get_change_amount(tracker, stat_type, effectiveness, level_range)
            tracker.add_value(stat_type, amount, interaction=resolver.interaction)

    def _get_change_amount(self, tracker, stat_type, effectiveness, level_range):
        cur_level = tracker.get_user_value(stat_type)
        if level_range is not None:
            point_level = math.clamp(level_range.lower_bound, cur_level, level_range.upper_bound)
        else:
            point_level = cur_level
        amount = stat_type.get_skill_effectiveness_points_gain(effectiveness, point_level)
        return amount

class DynamicVariantSkillLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'skill_loot_data': TunableVariantSkillLootData(description='\n            The reference to the skill data.\n            ')}

    def __init__(self, skill_loot_data, **kwargs):
        super().__init__(**kwargs)
        self._skill_loot_data = skill_loot_data

    def _get_skill_level_data(self, subject, interaction):
        stat = self._skill_loot_data.stat(subject, interaction)
        if stat is None:
            return (None, None, None)
        effectiveness = self._skill_loot_data.effectiveness
        if effectiveness is None:
            logger.error('Skill Effectiveness is not tuned for this loot operation in {}')
            return (None, None, None)
        level_range = self._skill_loot_data.level_range
        return (stat, effectiveness, level_range)

    def _get_change_amount(self, tracker, stat_type, effectiveness, level_range):
        cur_level = tracker.get_user_value(stat_type)
        if level_range is not None:
            point_level = math.clamp(level_range.lower_bound, cur_level, level_range.upper_bound)
        else:
            point_level = cur_level
        amount = stat_type.get_skill_effectiveness_points_gain(effectiveness, point_level)
        return amount

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (stat_type, effectiveness, level_range) = self._get_skill_level_data(subject, resolver.interaction)
        if stat_type is None:
            return
        tracker = subject.get_tracker(stat_type)
        if tracker is not None:
            amount = self._get_change_amount(tracker, stat_type, effectiveness, level_range)
            tracker.add_value(stat_type, amount, interaction=resolver.interaction)

class BaseStatisticByCategoryOp(BaseLootOperation):
    FACTORY_TUNABLES = {'statistic_category': TunableEnumEntry(statistics.statistic_categories.StatisticCategory, statistics.statistic_categories.StatisticCategory.INVALID, description='The category of commodity to remove.')}

    def __init__(self, statistic_category, **kwargs):
        super().__init__(**kwargs)
        self._category = statistic_category

class RemoveStatisticByCategory(BaseStatisticByCategoryOp):
    FACTORY_TUNABLES = {'count_to_remove': OptionalTunable(description='\n            If enabled, randomly remove x number of commodities from the tuned category.\n            If disabled, all commodities specified by category will be removed.\n            ', tunable=TunableRange(tunable_type=int, default=1, minimum=1))}

    def __init__(self, count_to_remove, **kwargs):
        super().__init__(**kwargs)
        self._count_to_remove = count_to_remove

    def _apply_to_subject_and_target(self, subject, target, resolver):
        category = self._category
        commodity_tracker = subject.commodity_tracker
        if commodity_tracker is None:
            return
        qualified_commodities = [c for c in commodity_tracker.get_all_commodity_classes() if category in c.get_categories()]
        if self._count_to_remove:
            random.shuffle(qualified_commodities)
        count_to_remove = min(self._count_to_remove, len(qualified_commodities)) if self._count_to_remove else len(qualified_commodities)
        for i in range(count_to_remove):
            commodity = qualified_commodities[i]
            if commodity.remove_on_convergence:
                commodity_tracker.remove_statistic(commodity.stat_type)
            else:
                commodity_tracker.set_value(commodity.stat_type, commodity.get_initial_value())

class TunableChangeAmountFactory(TunableFactory):

    @staticmethod
    def apply_change(sim, statistic, change_amout):
        stat_type = type(statistic)
        tracker = sim.get_tracker(type(statistic))
        if tracker is not None:
            tracker.add_value(stat_type, change_amout)

    FACTORY_TYPE = apply_change

    def __init__(self, **kwargs):
        super().__init__(change_amout=Tunable(description='\n                            Amount of change to be applied to statistics that match category.', tunable_type=float, default=0), **kwargs)

class TunablePercentChangeAmountFactory(TunableFactory):

    @staticmethod
    def apply_change(subject, statistic, percent_change_amount):
        stat_type = type(statistic)
        tracker = subject.get_tracker(stat_type)
        if tracker is not None:
            current_value = tracker.get_value(stat_type)
            change_amount = current_value*percent_change_amount
            tracker.add_value(stat_type, change_amount)

    FACTORY_TYPE = apply_change

    def __init__(self, **kwargs):
        super().__init__(percent_change_amount=TunablePercent(description='\n                             Percent of current value of statistic should amount\n                             be changed.  If you want to decrease the amount by\n                             50% enter -50% into the tuning field.', default=-50, minimum=-100), **kwargs)

class ChangeStatisticByCategory(BaseStatisticByCategoryOp):
    FACTORY_TUNABLES = {'change': TunableVariant(stat_change=TunableChangeAmountFactory(), percent_change=TunablePercentChangeAmountFactory())}

    def __init__(self, change, **kwargs):
        super().__init__(**kwargs)
        self._change = change

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject.commodity_tracker is not None:
            category = self._category
            for commodity in tuple(subject.commodity_tracker):
                if category in commodity.get_categories():
                    self._change(subject, commodity)

class ObjectStatisticChangeOp(StatisticChangeOp):
    FACTORY_TUNABLES = {'locked_args': {'subject': None, 'advertise': False, 'tests': (), 'chance': SuccessChance.ONE, 'exclusive_to_owning_si': False}}

    def apply_to_object(self, obj):
        tracker = obj.get_tracker(self.stat)
        if tracker is not None:
            self._apply(tracker)

    def remove_from_object(self, obj):
        tracker = obj.get_tracker(self.stat)
        if tracker is not None:
            self._remove(tracker)

    def get_fulfillment_rate(self, interaction):
        return 0

class HideRelationshipMixin:
    FACTORY_TUNABLES = {'hide_relationship': Tunable(description="\n            Sets the relationship's hidden property to this value after a \n            successful interaction.\n            ", tunable_type=bool, default=False)}

    def __init__(self, hide_relationship, **kwargs):
        super().__init__(**kwargs)
        self.hide_relationship = hide_relationship

    def apply_hide_relationship(self, subject_sim_id:'int', target_sim_id:'int') -> 'None':
        if services.relationship_service().is_hidden(subject_sim_id, target_sim_id) is not self.hide_relationship:
            services.relationship_service().hide_relationship(subject_sim_id, target_sim_id, self.hide_relationship)

class RelationshipOperationBase(HideRelationshipMixin, LootOperationTargetFilterTestMixin, StatisticOperation):
    FACTORY_TUNABLES = {'headline_icon_modifier': OptionalTunable(description='\n            If enabled then when updating the relationship track we will\n            use an icon modifier when sending the headline.\n            ', tunable=TunableIcon(description='\n                The icon that we will use as a modifier to the headline.\n                ')), 'locked_args': {'advertise': False, 'stat': None}}
    DEFAULT_PARTICIPANT_ARGUMENTS = {'subject': TunableEnumFlags(description='\n            The owner Sim for this relationship change. Relationship is updated\n            between the participant sim and the target objects as defined by\n            the object relationship track.\n            ', enum_type=ParticipantType, invalid_enums=ParticipantType.Invalid, default=ParticipantType.Actor), 'target_participant_type': TunableEnumFlags(description="\n            The target Sim for this relationship change. Any\n            relationship that would be given to 'self' is discarded.\n            ", enum_type=ParticipantType, invalid_enums=(ParticipantType.Invalid,), default=ParticipantType.Invalid)}

    def __init__(self, track_range=None, headline_icon_modifier=None, **kwargs):
        super().__init__(**kwargs)
        self._track_range = track_range
        self._headline_icon_modifier = headline_icon_modifier
        self._loot_type = LootType.RELATIONSHIP

    def _pre_process_for_source_and_target(self, source_sim_info, target_sim_info):
        pass

    def find_op_participants(self, interaction, source=None, target=None):
        if source is None:
            actors = interaction.get_participants(self.subject)
            if not actors:
                return (source, target)
            source = next(iter(actors))
        if target is None:
            targets = interaction.get_participants(self.target_participant_type)
            for potential_target in targets:
                if potential_target is not source:
                    target = potential_target
                    break
        return (source, target)

    def _get_interval(self, aop):
        return StatisticOperation.STATIC_CHANGE_INTERVAL

    def _apply_to_subject_and_target(self, subject, target, resolver):
        sim_mgr = services.sim_info_manager()
        relationship_service = services.relationship_service()
        if subject == ParticipantType.AllRelationships:
            if target == ParticipantType.AllRelationships:
                logger.error('Could not evaluate participants for {} since both subject and target were AllRelationships. Need a source sim info.', self)
                return
            target_sim_info = self._get_sim_info_from_participant(target)
            if not target_sim_info:
                return
            source_sim_infos = set(sim_mgr.get(relations.get_other_sim_id(target_sim_info.sim_id)) for relations in relationship_service.get_all_sim_relationships(target_sim_info.sim_id))
            source_sim_infos.discard(None)
            target_sim_infos = (target_sim_info,)
        elif target == ParticipantType.AllRelationships:
            source_sim_info = self._get_sim_info_from_participant(subject)
            if not source_sim_info:
                return
            target_sim_infos = set(sim_mgr.get(relations.get_other_sim_id(source_sim_info.sim_id)) for relations in relationship_service.get_all_sim_relationships(source_sim_info.sim_id))
            target_sim_infos.discard(None)
            source_sim_infos = (source_sim_info,)
        else:
            source_sim_infos = (self._get_sim_info_from_participant(subject),) if subject else None
            if not (source_sim_infos and source_sim_infos[0]):
                return
            target_sim_infos = (self._get_sim_info_from_participant(target),) if target else None
            if not (target_sim_infos and target_sim_infos[0]):
                return
        for target_sim_info in target_sim_infos:
            for source_sim_info in source_sim_infos:
                if source_sim_info is target_sim_info:
                    if not self.target_participant_type & (ParticipantType.PickedSim | ParticipantType.AllInstancedActiveHouseholdSims):
                        logger.error('Attempting to give relationship loot between the same sim {} in {} with resolver: {}', target_sim_info, self, resolver, owner='nabaker')
                        self._pre_process_for_source_and_target(source_sim_info, target_sim_info)
                        self._apply_to_sim_info(source_sim_info, target_sim_info.sim_id)
                else:
                    self._pre_process_for_source_and_target(source_sim_info, target_sim_info)
                    self._apply_to_sim_info(source_sim_info, target_sim_info.sim_id)

    def _get_sim_info_from_participant(self, participant):
        if isinstance(participant, int):
            sim_info_manager = services.sim_info_manager()
            if sim_info_manager is None:
                return
            sim_info = sim_info_manager.get(participant)
        else:
            sim_info = getattr(participant, 'sim_info', participant)
        if sim_info is None:
            logger.error('Could not get Sim Info from {0} in StatisticAddRelationship loot op.', participant)
        return sim_info

    def _apply_to_sim_info(self, source_sim_info, target_sim_id, **kwargs):
        self._apply_relationship_operation(source_sim_info.sim_id, target_sim_id, headline_icon_modifier=self._headline_icon_modifier, **kwargs)
        self.apply_hide_relationship(source_sim_info.sim_id, target_sim_id)

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        raise NotImplementedError

    def _get_display_text(self, resolver=None):
        value = self.get_value()
        if value:
            return self.DISPLAY_TEXT(*self._get_display_text_tokens(resolver))

    def _get_display_text_tokens(self, resolver=None):
        subject = None
        target = None
        if resolver is not None:
            subject = resolver.get_participant(self._subject)
            target = resolver.get_participant(self._target_participant_type)
        return (subject, target, self.get_value())

class RelationshipOperation(RelationshipOperationBase):
    FACTORY_TUNABLES = {'track': TunableReference(description='\n                The track to be manipulated.', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack'), 'track_range': TunableInterval(description='\n            The relationship track must > lower_bound and <= upper_bound for\n            the operation to apply.', tunable_type=float, default_lower=-101, default_upper=100)}

    def __init__(self, track_range=None, track=DEFAULT, **kwargs):
        super().__init__(**kwargs)
        self._track_range = track_range
        self._track = DEFAULT if track is None else track

    def __repr__(self):
        return '<{} {} {}, subject: {} target:{}>'.format(type(self).__name__, self._track, self._track_range, self.subject, self.target_participant_type)

    def get_stat(self, interaction, source=None, target=None):
        (source, target) = self.find_op_participants(interaction, source, target)
        if source is None or target is None:
            return
        if isinstance(target, int):
            target_sim_id = target
        else:
            target_sim_id = target.sim_id
        return services.relationship_service().get_relationship_track(source.sim_id, target_sim_id, self._track, add=True)

    def _apply_to_sim_info(self, source_sim_info, target_sim_id, **kwargs):
        relationship_service = services.relationship_service()
        value = relationship_service.get_relationship_score(source_sim_info.sim_id, target_sim_id, self._track)
        if value in self._track_range:
            apply_initial_modifier = not relationship_service.has_relationship_track(source_sim_info.sim_id, target_sim_id, self._track)
            super()._apply_to_sim_info(source_sim_info, target_sim_id, apply_initial_modifier=apply_initial_modifier, **kwargs)

class RelationshipMultiplierMixin:
    FACTORY_TUNABLES = {'relationship_multiplier': OptionalTunable(description='\n            A multiplier made for relationship operations.\n            ', tunable=TunableMultiplier.TunableFactory())}

    def __init__(self, relationship_multiplier=None, **kwargs):
        super().__init__(**kwargs)
        self._relationship_multiplier = relationship_multiplier
        self._relationship_multiplier_value = 1

    def _pre_process_for_source_and_target(self, source_sim_info, target_sim_info):
        if self._relationship_multiplier is not None:
            resolver = DoubleSimResolver(source_sim_info, target_sim_info)
            self._relationship_multiplier_value = self._relationship_multiplier.get_multiplier(resolver)

    def _get_multiplied_value(self, value):
        return value*self._relationship_multiplier_value

class StatisticAddRelationship(RelationshipMultiplierMixin, RelationshipOperation):
    FACTORY_TUNABLES = {'amount': lambda *args, **kwargs: _get_tunable_amount(*args, **kwargs), 'add_track_if_not_present': Tunable(description="\n                    When changing the value of a track, add the track if it's not already present.\n                    False means if the track is not already present, the operation is skipped", tunable_type=bool, default=True)}

    def __init__(self, amount=None, add_track_if_not_present=True, **kwargs):
        super().__init__(**kwargs)
        self._amount = amount
        self._add_track_if_not_present = add_track_if_not_present

    def get_value(self, **kwargs):
        return self._get_multiplied_value(self._amount)

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        relationship_service = services.relationship_service()
        if self._add_track_if_not_present or not relationship_service.has_relationship_track(actor_sim_id, target_sim_id, self._track):
            return
        relationship_service.add_relationship_score(actor_sim_id, target_sim_id, self.get_value(), track=self._track.stat_type, **kwargs)

class RandomSimStatisticAddRelationship(StatisticAddRelationship):
    KNOWN_SIMS = 0
    ALL_SIMS = 1

    @staticmethod
    def _verify_tunable_callback(cls, tunable_name, source, value):
        if value._store_single_result_on_interaction and not (value._number_of_random_sims is None or value._number_of_random_sims == 1):
            logger.error('RandomSimStatisticAddRelationship is tuned to store result on interaction and is expecting more than one result. {}', source)

    FACTORY_TUNABLES = {'who': TunableVariant(description="\n            Which Sims are valid choices before running tests.\n            If set to known_sims_only then it will only choose between Sims \n            that the subject sim already knows.\n            \n            IF set to all_sims then it will choose between all of the sims, \n            including those that the Sim hasn't met.\n            ", locked_args={'known_sims_only': KNOWN_SIMS, 'all_sims': ALL_SIMS}, default='known_sims_only'), 'tests_on_random_sim': TunableTestSet(description='\n            Tests that will be run to filer the Sims where we will pick the\n            random sim to apply this statistic change.\n            '), 'number_of_random_sims': OptionalTunable(description='\n            If enabled allows you to specify the number of Sims to choose to\n            add the relationship with.\n            ', tunable=TunableRange(description='\n                The number of Sims to choose to add relationship with from\n                the list of valid choices.\n                ', tunable_type=int, minimum=1, default=1)), 'loot_applied_notification': OptionalTunable(description='\n            If enable the notification will be displayed passing the subject\n            and the random sim as tokens.\n            ', tunable=UiDialogNotification.TunableFactory(description='\n                Notification that will be shown when the loot is applied.\n                ')), 'create_sim_if_no_results': OptionalTunable(description='\n            If enabled, will result in a new Sim Info being created to meet\n            the conditions of the supplied Sim Template.\n            ', tunable=TunableReference(description='\n                A reference to a Sim Filter to use to create a Sim.\n                                \n                This does not guarantee that the created Sim will pass\n                tests_on_random_sim. However the resulting sim will be used as\n                a valid result.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',))), 'store_single_result_on_interaction': OptionalTunable(description='\n            If enabled will place the result into the SavedActor specified on\n            the interaction.\n            \n            This will only work if the value of number_or_random_sims is 1.\n            This will overwrite whatever else is currently set in the\n            SavedActor space chosen.\n            ', tunable=TunableEnumEntry(description='\n            \n                ', tunable_type=ParticipantTypeSavedActor, default=ParticipantTypeSavedActor.SavedActor1)), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, who=None, tests_on_random_sim=None, number_of_random_sims=None, loot_applied_notification=None, create_sim_if_no_results=None, store_single_result_on_interaction=None, **kwargs):
        super().__init__(**kwargs)
        self._who = who
        self._tests_on_random_sim = tests_on_random_sim
        self._number_of_random_sims = number_of_random_sims
        self._loot_applied_notification = loot_applied_notification
        self._create_sim_if_no_results = create_sim_if_no_results
        self._store_single_result_on_interaction = store_single_result_on_interaction

    def _apply_to_subject_and_target(self, subject, target, resolver):
        source_sim_info = self._get_sim_info_from_participant(subject)
        if not source_sim_info:
            return
        valid_sim_infos = []
        if self._who == self.KNOWN_SIMS:
            target_sim_infos = services.relationship_service().get_target_sim_infos(source_sim_info.sim_id)
            for target_sim_info in target_sim_infos:
                test_resolver = DoubleSimResolver(source_sim_info, target_sim_info)
                if self._tests_on_random_sim.run_tests(test_resolver):
                    valid_sim_infos.append(target_sim_info)
        elif self._who == self.ALL_SIMS:
            sim_info_manager = services.sim_info_manager()
            for sim_info in sim_info_manager.values():
                test_resolver = DoubleSimResolver(source_sim_info, sim_info)
                if self._tests_on_random_sim.run_tests(test_resolver):
                    valid_sim_infos.append(sim_info)
        if not valid_sim_infos:
            if not self._create_sim_if_no_results:
                return
            result = self._create_sim_if_no_results.create_sim_info(0)
            if result:
                valid_sim_infos.append(result.sim_info)
        for _ in range(self._number_of_random_sims or 1):
            if not valid_sim_infos:
                break
            target_sim_info = random.choice(valid_sim_infos)
            valid_sim_infos.remove(target_sim_info)
            if source_sim_info is target_sim_info:
                target_sim_info = random.choice(valid_sim_infos)
                valid_sim_infos.remove(target_sim_info)
            self._apply_to_sim_info(source_sim_info, target_sim_info.sim_id)
            if self._loot_applied_notification is not None:
                dialog = self._loot_applied_notification(source_sim_info, resolver=DoubleSimResolver(source_sim_info, target_sim_info))
                dialog.show_dialog()
            if self._store_single_result_on_interaction:
                interaction = resolver.interaction
                if interaction is not None:
                    for (index, tag) in enumerate(list(ParticipantTypeSavedActor)):
                        if tag is self._store_single_result_on_interaction:
                            interaction.set_saved_participant(index, target_sim_info)
                            break

class TunableRelationshipTrackSelectionStrategyBase(HasTunableSingletonFactory, AutoFactoryInit):

    def get_tracks(self, actor_sim_id:'int', target_sim_id:'int') -> 'List[RelationshipTrack]':
        raise NotImplementedError

class TunableSentimentTrackSelectionByType(TunableRelationshipTrackSelectionStrategyBase):
    FACTORY_TUNABLES = {'sentiment_sign': OptionalTunable(description='\n            If tuned, only sentiments with the tuned sign will be affected.\n            ', tunable=TunableEnumEntry(tunable_type=SentimentSignType, default=SentimentSignType.INVALID, invalid_enums=(SentimentSignType.INVALID,))), 'sentiment_duration': OptionalTunable(description='\n            If tuned, only sentiments with the tuned duration will be affected.\n            ', tunable=TunableEnumEntry(tunable_type=SentimentDurationType, default=SentimentDurationType.INVALID, invalid_enums=(SentimentDurationType.INVALID,)))}

    def get_tracks(self, actor_sim_id:'int', target_sim_id:'int') -> 'List[RelationshipTrack]':
        sentiment_list = []
        rel_service = services.relationship_service()
        for track in rel_service.relationship_tracks_gen(actor_sim_id, target_sim_id, track_type=RelationshipTrackType.SENTIMENT):
            if self.sentiment_sign is not None and self.sentiment_sign != track.sign:
                pass
            elif self.sentiment_duration is not None and self.sentiment_duration != track.duration:
                pass
            else:
                sentiment_list.append(track)
        return sentiment_list

class StatisticAddRelationshipMultiple(RelationshipMultiplierMixin, RelationshipOperationBase):
    FACTORY_TUNABLES = {'amount': lambda *args, **kwargs: _get_tunable_amount(*args, **kwargs), 'track_selection_strategy': TunableVariant(description='\n            The strategy we will use for selecting tracks for this op to\n            operate on.\n            ', sentiments_by_type=TunableSentimentTrackSelectionByType.TunableFactory(), default='sentiments_by_type')}

    def __init__(self, amount=None, track_selection_strategy=None, **kwargs):
        super().__init__(**kwargs)
        self._amount = amount
        self._track_selection_strategy = track_selection_strategy

    def get_value(self, **kwargs):
        return self._get_multiplied_value(self._amount)

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        rel_value = self.get_value()
        relationship_service = services.relationship_service()
        for track in self._track_selection_strategy.get_tracks(actor_sim_id, target_sim_id):
            relationship_service.add_relationship_score(actor_sim_id, target_sim_id, rel_value, track=track.stat_type, **kwargs)

class StatisticSetRelationship(RelationshipMultiplierMixin, RelationshipOperation):
    FACTORY_TUNABLES = {'value': Tunable(description='\n                The value to set the relationship to.', tunable_type=float, default=0), 'add_track_if_not_present': Tunable(description="\n                When setting the value of a track, add the track if it's not already present.\n                False means if the track is not already present, the operation is skipped", tunable_type=bool, default=True)}

    def __init__(self, value=None, add_track_if_not_present=True, **kwargs):
        super().__init__(**kwargs)
        self._value = value
        self._add_track_if_not_present = add_track_if_not_present

    def get_value(self, **kwargs):
        return self._get_multiplied_value(self._value) - self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        relationship_service = services.relationship_service()
        if self._add_track_if_not_present or not relationship_service.has_relationship_track(actor_sim_id, target_sim_id, self._track):
            return
        relationship_service.set_relationship_score(actor_sim_id, target_sim_id, self._get_multiplied_value(self._value), track=self._track.stat_type, **kwargs)

class StatisticSetRelationshipTrackConvergenceValue(RelationshipOperation):
    FACTORY_TUNABLES = {'convergence_value': Tunable(description='\n            The convergence value to set on the tuned relationship track.\n            ', tunable_type=float, default=0)}

    def __init__(self, convergence_value=None, **kwargs):
        super().__init__(**kwargs)
        self._convergence_value = convergence_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        relationship_service = services.relationship_service()
        if not relationship_service.has_relationship_track(actor_sim_id, target_sim_id, self._track):
            return
        targeted_track = relationship_service.get_relationship_track(actor_sim_id, target_sim_id, self._track)
        targeted_track.convergence_value = self._convergence_value

class StatisticRemoveRelationshipTrack(RelationshipOperation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_value(self, **kwargs):
        return self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        services.relationship_service().remove_relationship_track(actor_sim_id, target_sim_id, self._track)

class StatisticSetRelationshipMultiple(RelationshipMultiplierMixin, RelationshipOperationBase):
    FACTORY_TUNABLES = {'value': lambda *args, **kwargs: _get_tunable_amount(*args, **kwargs), 'track_selection_strategy': TunableVariant(description='\n            The strategy we will use for selecting tracks for this op to\n            operate on.\n            ', sentiments_by_type=TunableSentimentTrackSelectionByType.TunableFactory(), default='sentiments_by_type')}

    def __init__(self, value=None, track_selection_strategy=None, **kwargs):
        super().__init__(**kwargs)
        self._value = value
        self._track_selection_strategy = track_selection_strategy

    def get_value(self, **kwargs):
        return self._get_multiplied_value(self._value)

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        rel_value = self.get_value()
        relationship_service = services.relationship_service()
        for track in self._track_selection_strategy.get_tracks(actor_sim_id, target_sim_id):
            relationship_service.set_relationship_score(actor_sim_id, target_sim_id, rel_value, track=track.stat_type, **kwargs)

class StatisticSetRelationshipMax(RelationshipOperation):

    def get_value(self, obj=None, interaction=None, sims=None):
        return self._track.max_value - self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        services.relationship_service().set_track_to_max(actor_sim_id, target_sim_id, self._track.stat_type)

class ObjectRelationshipOperation(RelationshipOperationBase):
    FACTORY_TUNABLES = {'track': TunableReference(description='\n            The track to be manipulated.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='ObjectRelationshipTrack'), 'track_range': TunableInterval(description='\n            The relationship track must > lower_bound and <= upper_bound for\n            the operation to apply.', tunable_type=float, default_lower=-101, default_upper=100)}

    def __init__(self, track_range=None, track=DEFAULT, headline_icon_modifier=None, **kwargs):
        super().__init__(**kwargs)
        self._track_range = track_range
        self._track = DEFAULT if track is None else track

    def get_stat(self, interaction, source=None, target=None):
        (source, target) = self.find_op_participants(interaction, source, target)
        if source is None or target is None:
            logger.error('None participant found while applying Object Relationship Operations. Source: {}, Target: {}', source, target)
            return
        obj_tag_set = ObjectRelationshipTrack.OBJECT_BASED_FRIENDSHIP_TRACKS[self._track]
        return services.relationship_service().get_object_relationship_track(source.sim_info.sim_id, obj_tag_set, target.definition.id, track=self._track, add=True)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        source_sim_info = self._get_sim_info_from_participant(subject)
        if not source_sim_info:
            return
        self._apply_to_sim_info(source_sim_info, target)

    def _apply_to_sim_info(self, source_sim_info, target, **kwargs):
        obj_tag_set = ObjectRelationshipTrack.OBJECT_BASED_FRIENDSHIP_TRACKS[self._track]
        relationship_service = services.relationship_service()
        if not target.has_any_tag(obj_tag_set.tags):
            logger.error('Attempting to add object-type-rel between sim {} and object {} for track {}, but the target object does not have the appropriate tags {}', source_sim_info, target, self._track, obj_tag_set.tags, owner='shipark')
            return
        track = relationship_service.get_object_relationship_track(source_sim_info.sim_id, obj_tag_set, target_def_id=target.definition.id, track=self._track.stat_type, add=True)
        if track.get_value() in self._track_range:
            apply_initial_modifier = not relationship_service.has_object_relationship_track(source_sim_info.sim_id, obj_tag_set, self._track)
            super()._apply_to_sim_info(source_sim_info, target.id, apply_initial_modifier=apply_initial_modifier, **kwargs)

class StatisticAddObjectRelationship(ObjectRelationshipOperation):
    FACTORY_TUNABLES = {'amount': lambda *args, **kwargs: _get_tunable_amount(*args, **kwargs)}

    def __init__(self, amount=None, **kwargs):
        super().__init__(**kwargs)
        self._amount = amount

    def get_value(self, **kwargs):
        return self._amount

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        services.relationship_service().add_object_relationship_score(actor_sim_id, ObjectRelationshipTrack.OBJECT_BASED_FRIENDSHIP_TRACKS[self._track], self._amount, track=self._track.stat_type)

    def _apply(self, tracker, target_sim, **kwargs):
        tracker.add_value(self._track, self._amount, **kwargs)

class RelationshipSetIntervalDecayRateOverride(RelationshipOperation):
    FACTORY_TUNABLES = {'new_rates': TunableList(description="\n            The interval decay rates that we are going to use instead of\n            the stat's default rates.\n            \n            Note: This will skip all other decay rate logic if applied.\n            ", tunable=TunableTuple(description='\n                The interval/decay rate pair.\n                ', interval=TunableInterval(description='\n                    The range at which this decay rate will apply. It is inclusive\n                    on the lower bound and exclusive on the upper bound.\n                    ', tunable_type=float, default_lower=-100, default_upper=100), decay_override=Tunable(description='\n                    The value that the base decay will be overridden with.\n                    ', tunable_type=float, default=0.0)))}

    def __init__(self, new_rates:'List[Any]'=None, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._new_rates = new_rates

    def get_value(self, **kwargs):
        return self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        track = services.relationship_service().get_relationship_track(actor_sim_id, target_sim_id, self._track)
        if track is None:
            return
        track.set_interval_decay_rate_override(self._new_rates)

class RelationshipClearIntervalDecayRateOverride(RelationshipOperation):

    def get_value(self, **kwargs):
        return self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        track = services.relationship_service().get_relationship_track(actor_sim_id, target_sim_id, self._track)
        if track is None:
            return
        track.clear_interval_decay_rate_override()

class RelationshipSetDecayEnabledOverride(RelationshipOperation):
    FACTORY_TUNABLES = {'decay_enabled': Tunable(description='\n            If enabled, will force decay to always be active.\n            If disabled, will never allow decay to be active.\n            ', tunable_type=bool, default=False)}

    def __init__(self, decay_enabled:'bool'=False, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._decay_enabled = decay_enabled

    def get_value(self, **kwargs) -> 'float':
        return self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        track = services.relationship_service().get_relationship_track(actor_sim_id, target_sim_id, self._track)
        if track is None:
            return
        track.set_decay_enabled_override(self._decay_enabled)

class RelationshipClearDecayEnabledOverride(RelationshipOperation):

    def get_value(self, **kwargs) -> 'float':
        return self._track.default_value

    def _apply_relationship_operation(self, actor_sim_id:'int', target_sim_id:'int', **kwargs) -> 'None':
        track = services.relationship_service().get_relationship_track(actor_sim_id, target_sim_id, self._track)
        if track is None:
            return
        track.clear_decay_enabled_override()
