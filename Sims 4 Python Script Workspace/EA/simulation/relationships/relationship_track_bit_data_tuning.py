from __future__ import annotationsimport operatorimport servicesfrom bisect import bisect_rightfrom relationships.relationship_track_tracker import RelationshipTrackTrackerfrom relationships.tunable import TrackMean, BitTrackNode, BaseRelationshipTrackInstanceData, BaseRelationshipTrackDatafrom sims4.log import Loggerfrom sims4.math import Threshold, clampfrom sims4.tuning.tunable import TunableList, HasTunableFactory, AutoFactoryInit, TunableInterval, Tunable, TunableReference, TunedIntervalfrom sims4.resources import Typesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from statistics.base_statistic import BaseStatistic
    from relationships.relationship_bit import RelationshipBit
    from relationships.relationship_track import RelationshipTrack
    from statistics.base_statistic_listener import BaseStatisticCallbackListener
    from relationships.relationship_objects.relationship import Relationshiplogger = Logger('Relationship', default_owner='mjuskelis')
class TunableRelationshipTrackBitInterval(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'bit': TunableReference(description='\n            The bit that we want to use in this interval.\n            ', manager=services.get_instance_manager(Types.RELATIONSHIP_BIT)), 'interval': TunableInterval(description='\n            The interval that this bit should be active for.\n            ', tunable_type=float, default_lower=-100, default_upper=100), 'stickiness': Tunable(description="\n            How far past the interval boundaries should we continue\n            using this bit before switching to the next bit?\n            \n            When transitioning between intervals, it can be useful\n            to have the previous value 'stick' beyond the boundaries\n            of the interval. This can help prevent the bits from\n            switching too frequently if the track's value fluctuates\n            around an interval boundary.\n            \n            For example,\n            if we're on bit A, which is tuned for interval -10 to 10,\n            with a stickiness of 5, we won't switch away from A until\n            we're either below -15 or above 15.\n            Once we've left A, we won't re-enter A until we go above\n            -10 or below 10, assuming no other bits have stickiness.\n            ", tunable_type=float, default=0)}

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self.interval_with_stickiness = TunedInterval(self.interval.lower_bound - self.stickiness, self.interval.upper_bound + self.stickiness)
        self.interval_average = self.interval.lower_bound + (self.interval.upper_bound - self.interval.lower_bound)/2

    def __repr__(self) -> 'str':
        return 'Bit:{}[{}-{}]'.format(self.bit, self.interval.lower_bound, self.interval.upper_bound)

    def as_bit_track_node(self) -> 'BitTrackNode':
        return BitTrackNode(self.bit, self.interval.lower_bound, self.interval.upper_bound)

class TunableRelationshipIntervalBitData(BaseRelationshipTrackData, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'entries': TunableList(description='\n            The collection of bit intervals to use for this track.\n            ', tunable=TunableRelationshipTrackBitInterval.TunableFactory())}

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self.bit_data = [entry() for entry in self.entries]
        self.bit_data.sort(key=lambda entry: entry.interval.lower_bound)
        self.bit_data_set = {bit_data.bit for bit_data in self.bit_data}
        self.all_lower_bounds = [bit_data.interval.lower_bound for bit_data in self.bit_data]
        self._verify_intervals()

    def _verify_intervals(self) -> 'None':
        if not self.bit_data:
            return
        track = self.bit_data[0].bit.triggered_track
        if self.bit_data[0].interval.lower_bound > track.min_value:
            logger.error("Bit interval tuning '{}' does not cover the min value of track '{}'", self, track)
        if self.bit_data[-1].interval.upper_bound < track.max_value:
            logger.error("Bit interval tuning '{}' does not cover the max value of track '{}'", self, track)
        for (node, next_node) in list(zip(self.bit_data, self.bit_data[1:])):
            if node.interval.upper_bound < next_node.interval.lower_bound:
                logger.error("There is a gap in bit interval tuning '{}', between '{}' and '{}'", self, node, next_node)
            elif node.interval.upper_bound > next_node.interval.lower_bound:
                logger.error("There is overlap in bit interval tuning '{}', between '{}' and '{}'", self, node, next_node)

    def build_track_data(self) -> 'None':
        pass

    def set_neutral_bit(self, bit:'RelationshipBit') -> 'None':
        pass

    def get_track_instance_data(self, track:'RelationshipTrack') -> 'BaseRelationshipTrackInstanceData':
        return RelationshipTrackBitIntervalInstanceData(track)

    def bit_track_node_gen(self) -> 'Generator[BitTrackNode]':
        for data_entry in self.bit_data:
            yield data_entry.as_bit_track_node()

    def get_track_mean_list_for_bit(self, bit:'RelationshipBit') -> 'List[TrackMean]':
        for data_entry in self.bit_data:
            if data_entry.bit is bit:
                return [TrackMean(bit.triggered_track, data_entry.interval_average)]
        logger.error("Unable to find Bit '{}' in Relationship Track Interval Bit Data '{}'", bit, self)
        return []

class RelationshipTrackBitIntervalInstanceData(BaseRelationshipTrackInstanceData):

    def __init__(self, track:'RelationshipTrack') -> 'None':
        super().__init__(track)
        self._listeners = None
        self._current_index = None

    def get_active_bit(self) -> 'Optional[RelationshipBit]':
        if self._current_index is None:
            return
        return self._track_data.bit_data[self._current_index].bit

    def get_active_bit_by_value(self) -> 'Optional[RelationshipBit]':
        index = self._get_index_for_score(self._track.get_value())
        return self._track_data.bit_data[index].bit

    def _get_index_for_score(self, score:'float') -> 'int':
        return clamp(0, bisect_right(self._track_data.all_lower_bounds, score) - 1, len(self._track_data.bit_data))

    def full_load_update(self, relationship:'Relationship') -> 'None':
        rel_data = self._track.tracker.rel_data
        (old_bit, new_bit) = self.request_full_update()
        if relationship.has_bit(rel_data.sim_id_b, new_bit):
            return
        for (i, entry) in enumerate(self._track_data.bit_data):
            if i == self._current_index:
                pass
            elif relationship.has_bit(rel_data.sim_id_b, entry.bit):
                relationship.remove_bit(rel_data.sim_id_b, rel_data.sim_id_a, entry.bit, notify_client=False)
        self._apply_bit_change(old_bit, new_bit)

    def request_full_update(self) -> 'Tuple[Optional[RelationshipBit], Optional[RelationshipBit]]':
        return self._update()

    def _update(self) -> 'Tuple[Optional[RelationshipBit], Optional[RelationshipBit]]':
        track_data = self._track_data
        score = self._track.get_value()
        old_entry = None
        if self._current_index is not None:
            old_entry = track_data.bit_data[self._current_index]
            if score in old_entry.interval_with_stickiness:
                return (None, None)
        self._current_index = self._get_index_for_score(score)
        new_entry = track_data.bit_data[self._current_index]
        self.setup_callbacks()
        logger.debug('Updating track {}\n\tScore: {}\n\tOriginal Node: {}\n\tCurrent Node: {}\n\tIndex: {}', self._track, score, old_entry, new_entry, self._current_index)
        if old_entry == new_entry:
            return (None, None)
        old_bit = old_entry.bit if old_entry is not None else None
        new_bit = new_entry.bit if new_entry is not None else None
        logger.debug('\tOld bit: {}\n\tNew Bit: {}', old_bit, new_bit)
        return (old_bit, new_bit)

    def setup_callbacks(self) -> 'None':
        self._clear_listeners()
        self._listeners = self._create_listeners()

    def _create_listeners(self) -> 'Tuple[Optional[BaseStatisticCallbackListener], Optional[BaseStatisticCallbackListener]]':
        if self._current_index is None:
            return (None, None)
        if self._current_index < 0 or self._current_index > len(self._track_data.bit_data):
            logger.error("Current index '{}' is out of bounds of bit interval list for track '{}'.\n\tWe cannot set up callbacks", self._current_index, self._track)
            return (None, None)
        current_entry = self._track_data.bit_data[self._current_index]
        lower_bound_callback = None
        if self._current_index > 0:
            threshold = Threshold(current_entry.interval_with_stickiness.lower_bound, operator.lt)
            lower_bound_callback = self._track.tracker.create_and_add_listener(self._track.stat_type, threshold, self._on_listener_triggered)
        upper_bound_callback = None
        if self._current_index < len(self._track_data.bit_data) - 1:
            threshold = Threshold(current_entry.interval_with_stickiness.upper_bound, operator.gt)
            upper_bound_callback = self._track.tracker.create_and_add_listener(self._track.stat_type, threshold, self._on_listener_triggered)
        return (lower_bound_callback, upper_bound_callback)

    def _on_listener_triggered(self, _:'BaseStatistic') -> 'None':
        (bit_to_remove, bit_to_add) = self._update()
        self._apply_bit_change(bit_to_remove, bit_to_add)

    def _clear_listeners(self) -> 'None':
        if self._listeners:
            for listener in self._listeners:
                if listener is not None:
                    self._track.tracker.remove_listener(listener)
            self._listeners = None
