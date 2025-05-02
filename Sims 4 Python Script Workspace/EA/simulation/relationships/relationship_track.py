from __future__ import annotationsimport collectionsimport operatorimport telemetry_helperfrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom relationships.cross_age_tuning import CrossAgeTuningSnippetfrom relationships.relationship_enums import RelationshipTrackTypefrom relationships.relationship_track_bit_data_tuning import TunableRelationshipIntervalBitDatafrom relationships.tunable import TunableRelationshipBitData, TunableRelationshipTrack2dLinkfrom sims.sim_info_types import Speciesfrom sims4.localization import TunableLocalizedStringfrom sims4.math import Thresholdfrom sims4.telemetry import TelemetryWriterfrom sims4.tuning.geometric import TunableVector2, TunableWeightedUtilityCurveAndWeightfrom sims4.tuning.instances import HashedTunedInstanceMetaclass, lock_instance_tunablesfrom sims4.tuning.tunable import TunableVariant, TunableList, TunableReference, TunableRange, Tunable, TunableSet, OptionalTunable, TunableTuple, TunableThreshold, TunableInterval, TunablePackSafeReference, TunableEnumEntry, TunableMappingfrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom sims4.utils import classpropertyfrom singletons import DEFAULTfrom statistics.continuous_statistic_tuning import TunedContinuousStatisticfrom tunable_multiplier import TestedSumimport alarmsimport date_and_timeimport event_testing.testsimport servicesimport simsimport sims4.logimport sims4.resourcesimport sims4.tuningfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.utils.tunable_icon import TunableIcon
    from relationships.relationship_objects.relationship import Relationship
    from relationships.relationship_bit import RelationshipBit
    from relationships.tunable import BitTrackNode, BaseRelationshipTrackData
    from sims.sim_info_tracker import SimInfoTracker
    from sims4.tuning.instance_manager import InstanceManager
    from statistics.base_statistic import BaseStatistic
    from statistics.continuous_statistic_tuning import _DecayOverrideNode
    import Commodities_pb2logger = sims4.log.Logger('Relationship', default_owner='msantander')TELEMETRY_GROUP_COMMODITIES = 'COMO'TELEMETRY_HOOK_STATE_UP = 'UPPP'TELEMETRY_HOOK_STATE_DOWN = 'DOWN'TELEMETRY_HOOK_DECAY_RATE_CHANGE = 'RCHG'writer = TelemetryWriter(TELEMETRY_GROUP_COMMODITIES)
class BaseRelationshipTrack:
    INSTANCE_TUNABLES = {'bit_data_tuning': TunableVariant(description='\n            Bit tuning for all the bits that compose this relationship \n            track.\n            The structure tuned here, either 2d or simple track should include \n            bits for all the possible range of the track.\n            ', bit_set=TunableRelationshipBitData(), _2dMatrix=TunableRelationshipTrack2dLink(), bit_intervals=TunableRelationshipIntervalBitData.TunableFactory()), '_neutral_bit': TunableReference(description="\n            The neutral bit for this relationship track.  This is the bit\n            that is displayed when there are holes in the relationship\n            track's bit data.\n            ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), tuning_group=GroupNames.CORE), 'ad_data': TunableList(description='\n            A list of Vector2 points that define the desire curve for this \n            relationship track.\n            ', tunable=TunableVector2(description='\n                Point on a Curve.\n                ', default=sims4.math.Vector2(0, 0)), tuning_group=GroupNames.SPECIAL_CASES), '_add_bit_on_threshold': OptionalTunable(description='\n            If enabled, the referenced bit will be added this track reaches the\n            threshold.\n            ', tunable=TunableTuple(description='\n                The bit & threshold pair.\n                ', bit=TunableReference(description='\n                    The bit to add.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), threshold=TunableThreshold(description='\n                    The threshold at which to add this bit.\n                    ')), tuning_group=GroupNames.CORE), 'causes_delayed_removal_on_convergence': Tunable(description='\n            If True, this track may cause the relationship to get culled\n            when it reaches convergence.  This is not guaranteed, based on\n            the culling rules.  Sim relationships will NOT be culled if any\n            of the folling conditions are met: \n            - Sim has any relationship bits that are tuned to prevent this. \n            - The sims are in the same household\n            \n            Note: This value is ignored by the Relationship Culling Story\n            Progression Action.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CORE), 'tested_initial_modifier': OptionalTunable(description='\n            If enabled, a modifier will be applied to the initial value when\n            the track is created.\n            ', tunable=TestedSum.TunableFactory(description='\n                The test to run and the outcome if test passes.\n                '), tuning_group=GroupNames.CORE), 'visible_test_set': OptionalTunable(event_testing.tests.TunableTestSet(description='\n                If set, tests whether relationship should be sent to client. If\n                no test given, then as soon as track is added to the\n                relationship, it will be visible to client.\n                '), disabled_value=DEFAULT, disabled_name='always_visible', enabled_name='run_test', tuning_group=GroupNames.SPECIAL_CASES), 'delay_until_decay_is_applied': OptionalTunable(description='\n            If enabled, the decay for this track will be disabled whenever\n            the value changes by any means other than decay.  It will then \n            be re-enabled after this amount of time (in sim minutes) passes.\n            ', tunable=TunableRange(description='\n                The amount of time, in sim minutes, that it takes before \n                decay is enabled.\n                ', tunable_type=int, default=10, minimum=1), tuning_group=GroupNames.DECAY), 'display_priority': OptionalTunable(description='\n            The display priority of this relationship track.  Tracks with a\n            display priority will be displayed in ascending order in the UI.\n            \n            So a relationship track with a display priority of 1 will show\n            above a relationship track with a display priority of 2.\n            Relationship tracks with the same display priority will show up\n            in potentially non-deterministic ways.\n            ', tunable=TunableRange(description='\n                The display priority of the relationship track.\n                ', tunable_type=int, default=0, minimum=0), export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'headline': OptionalTunable(description='\n            If enabled when this relationship track updates we will display\n            a headline update to the UI.\n            ', tunable=TunableReference(description='\n                The headline that we want to send down.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HEADLINE)), tuning_group=GroupNames.UI), 'display_popup_priority': TunableRange(description='\n            The display popup priority.  This is the priority that the\n            relationship score increases will display if there are multiple\n            relationship changes at the same time.\n            ', tunable_type=int, default=0, minimum=0, tuning_group=GroupNames.UI), 'display_in_sim_profile': Tunable(description='\n            If checked, this relationship track can be shown in the Sim\n            Profile.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'persist_at_convergence': Tunable(description='\n            If unchecked, this track will not be persisted if it is at\n            convergence. This prevents a ton of tracks, in particular short\n            term context tracks, from piling up on relationships with a value\n            of 0.\n            \n            If checked, the track will be persisted even if it is at 0. This\n            should only used on tracks where its presence matters.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'track_name': TunableLocalizedString(description='\n            Localized name of this relationship tracker displayed in game.\n            ', allow_none=True, tuning_group=GroupNames.UI)}

    def __init__(self, tracker:'SimInfoTracker') -> 'None':
        super().__init__(tracker, self.initial_value)
        self._per_instance_data = self.bit_data.get_track_instance_data(self)
        self.visible_to_client = True if self.visible_test_set is DEFAULT else False
        self._decay_alarm_handle = None
        self._cached_ticks_until_decay_begins = -1
        self._convergence_callback_data = None
        self._set_initial_decay()
        if not self._tracker.suppress_callback_setup_during_load:
            self._create_convergence_callback()

    def on_add(self) -> 'None':
        if not self.tracker.suppress_callback_setup_during_load:
            self._per_instance_data.setup_callbacks()
            (old_bit, new_bit) = self.update_instance_data()
            if not self.tracker.load_in_progress:
                sim_id_a = self.tracker.rel_data.sim_id_a
                sim_id_b = self.tracker.rel_data.sim_id_b
                if old_bit is not None and old_bit is not new_bit:
                    self.tracker.rel_data.relationship.remove_bit(sim_id_b, sim_id_a, old_bit)
                if new_bit is not None and not self.tracker.rel_data.relationship.has_bit(sim_id_b, new_bit):
                    self.tracker.rel_data.relationship.add_relationship_bit(sim_id_b, sim_id_a, new_bit)
        if self._add_bit_on_threshold is not None:
            self.create_and_add_callback_listener(self._add_bit_on_threshold.threshold, self._on_add_bit_from_threshold_callback)

    def _cleanup_convergence_callback(self):
        self.remove_callback_listener(self._convergence_callback_data)

    def _set_initial_decay(self):
        if self._should_decay():
            self.decay_enabled = True

    def _should_decay(self):
        if self.decay_rate == 0:
            return False
        if self.tracker.is_track_locked(self):
            return False
        if self.tracker.rel_data.is_object_rel():
            return True
        if self.decay_only_affects_played_sims:
            if not services.sim_info_manager():
                return False
            sim_info = self.tracker.rel_data.relationship.find_sim_info_a()
            target_sim_info = self.tracker.rel_data.relationship.find_sim_info_b()
            if sim_info is None or target_sim_info is None:
                return False
            active_household = services.active_household()
            if active_household is None:
                return False
            if sim_info in active_household or target_sim_info in active_household:
                return True
            if sim_info.is_player_sim or target_sim_info.is_player_sim:
                if not self.tracker.rel_data.relationship.can_cull_relationship(consider_convergence=False):
                    return False
                current_value = self.get_value()
                if self.decay_affecting_played_sims.range_decay_threshold.lower_bound < current_value and current_value < self.decay_affecting_played_sims.range_decay_threshold.upper_bound:
                    return True
        else:
            return True
        return False

    def _create_convergence_callback(self):
        if self._convergence_callback_data is None:
            self._convergence_callback_data = self.create_and_add_callback_listener(Threshold(self.convergence_value, operator.eq), self._on_convergence_callback)
        else:
            logger.error('Track {} attempted to create convergence callback twice.'.format(self))

    def _on_convergence_callback(self, _):
        if self.tracker.rel_data.relationship is None:
            logger.warn("_on_convergence_callback triggered after self.tracker.rel_data.relationship was destroyed. This shouldn't be happening. SP18+ this should be upgraded to an error.")
            return
        logger.debug('Track {} reached convergence; rel might get culled for {}', self, self.tracker.rel_data)
        self.tracker.rel_data.track_reached_convergence(self)

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        cls.bit_data = cls.bit_data_tuning()
        cls.bit_data.set_neutral_bit(cls._neutral_bit)
        cls.bit_data.build_track_data()
        cls._build_utility_curve_from_tuning_data(cls.ad_data)

    def fixup_callbacks_during_load(self) -> 'None':
        if not self._tracker.suppress_callback_setup_during_load:
            self._create_convergence_callback()
        super().fixup_callbacks_during_load()
        self._per_instance_data.setup_callbacks()

    def update_instance_data(self) -> 'Tuple[RelationshipBit, RelationshipBit]':
        return self._per_instance_data.request_full_update()

    def reset_decay_alarm(self, use_cached_time:'bool'=False) -> 'None':
        self._destroy_decay_alarm()
        if self._should_decay():
            delay_time_span = None
            if use_cached_time:
                if self._cached_ticks_until_decay_begins > 0:
                    delay_time_span = date_and_time.TimeSpan(self._cached_ticks_until_decay_begins)
                elif self._cached_ticks_until_decay_begins == 0:
                    self.decay_enabled = True
                    return
            if delay_time_span is None:
                delay_time_span = date_and_time.create_time_span(minutes=self.delay_until_decay_is_applied)
            self._decay_alarm_handle = alarms.add_alarm(self, delay_time_span, self._decay_alarm_callback, cross_zone=True)
            self.decay_enabled = False

    def get_bit_for_client(self) -> 'RelationshipBit':
        active_bit = self.get_active_bit()
        if active_bit is None:
            return self._neutral_bit
        return active_bit

    def get_active_bit(self) -> 'RelationshipBit':
        return self._per_instance_data.get_active_bit()

    def _destroy_decay_alarm(self):
        if self._decay_alarm_handle is not None:
            alarms.cancel_alarm(self._decay_alarm_handle)
            self._decay_alarm_handle = None

    def get_saved_ticks_until_decay_begins(self) -> 'int':
        if self.decay_enabled:
            return 0
        if self._decay_alarm_handle:
            return self._decay_alarm_handle.get_remaining_time().in_ticks()
        return self._cached_ticks_until_decay_begins

    def set_time_until_decay_begins(self, ticks_until_decay_begins:'int') -> 'None':
        if self.delay_until_decay_is_applied is None:
            self._cached_ticks_until_decay_begins = ticks_until_decay_begins
            if self._cached_ticks_until_decay_begins != 0.0 and self._cached_ticks_until_decay_begins != -1.0:
                logger.error('Rel Track {} loaded with bad persisted value {}', self, self._cached_ticks_until_decay_begins)
            return
        max_tuning = date_and_time.create_time_span(minutes=self.delay_until_decay_is_applied).in_ticks()
        self._cached_ticks_until_decay_begins = min(ticks_until_decay_begins, max_tuning)
        if self._cached_ticks_until_decay_begins < -1.0:
            logger.error('Rel Track {} loaded with bad persisted value {}', self, self._cached_ticks_until_decay_begins)

    def update_track_index(self, relationship:'Relationship') -> 'None':
        self._per_instance_data.full_load_update(relationship)

    @classproperty
    def track_type(cls) -> 'RelationshipTrackType':
        raise NotImplementedError

    def build_single_relationship_track_proto(self, relationship_track_update:'Commodities_pb2.RelationshipTrack') -> 'None':
        relationship_track_update.track_score = self.get_value()
        relationship_track_update.track_bit_id = self.get_bit_for_client().guid64
        relationship_track_update.track_id = self.guid64
        relationship_track_update.track_popup_priority = self.display_popup_priority
        relationship_track_update.change_rate = self.get_change_rate()
        relationship_track_update.track_name = self.track_name
