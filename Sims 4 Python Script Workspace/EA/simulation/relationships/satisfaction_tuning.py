from __future__ import annotationsimport servicesimport telemetry_helperfrom event_testing.resolver import DoubleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions.utils.tunable_icon import TunableIconfrom relationships.relationship_track import RelationshipTrackfrom sims4.common import Packfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.telemetry import TelemetryWriterfrom sims4.tuning.tunable import TunablePackSafeReference, Tunablefrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from event_testing.test_events import TestEvent
    from relationships.relationship_objects.relationship import Relationship
    from relationships.relationship_service import RelationshipService
    from sims.sim_info import SimInfo
    from typing import *TELEMETRY_HOOK_DECAY_RATE_AB_GROUP_SET = 'RSDR'TELEMETRY_GROUP_AB_TESTING = 'ABTE'ab_test_writer = TelemetryWriter(TELEMETRY_GROUP_AB_TESTING)
class SatisfactionTuning:
    RELATIONSHIP_SATISFACTION_TRACK = TunablePackSafeReference(description='\n        A reference to the relationship track that represents\n        relationship satisfaction.\n        ', manager=services.get_instance_manager(Types.STATISTIC), class_restrictions=('RelationshipTrack',), export_modes=ExportModes.All)
    UNKNOWN_ICON = TunableIcon(description='\n        The icon to display in the Sim Profile when the active sim\n        does not know the relationship satisfaction that the target sim feels towards\n        the active sim.\n        ', export_modes=ExportModes.All)
    UNKNOWN_TITLE = TunableLocalizedString(description='\n        The title to use in the Sim Profile when the active sim\n        does not know the relationship satisfaction that the target sim feels towards\n        the active sim.\n        ', export_modes=ExportModes.All)
    UNKNOWN_DESCRIPTION = TunableLocalizedString(description='\n        The description to use in the Sim Profile when the active sim\n        does not know the relationship satisfaction that the target sim feels towards\n        the active sim.\n        ', export_modes=ExportModes.All)
    SHOULD_TRACK_TESTS = TunableTestSet(description='\n        If these tests fail for the given actor and target,\n        we want to freeze relationship satisfaction and hide\n        it. When the tests succeed, we want to show relationship\n        satisfaction and allow it to decay. We do not add/remove\n        relationship satisfaction itself from the actor\n        and target.\n        \n        When this test is used, we automatically test both\n        directions, so you only need to write the test for\n        one direction.\n        ')

class SatisfactionService(Service):
    RELATIONSHIP_SATISFACTION_PAUSE_EVENTS = (TestEvent.AgedUp,)
    ALL_EVENTS = RELATIONSHIP_SATISFACTION_PAUSE_EVENTS
    RELATIONSHIP_SATISFACTION_FEATURE_ID = 17603432245669232131
    AB_TEST_GROUP_ID = None

    def __init__(self) -> 'None':
        self._relationship_service = None

    @classproperty
    def required_packs(self) -> 'Tuple[Pack]':
        return (Pack.EP16,)

    def start(self) -> 'None':
        self._relationship_service = services.relationship_service()
        services.get_event_manager().register(self, self.ALL_EVENTS)

    def on_client_connect(self, client):
        services.current_zone().refresh_feature_params(self.RELATIONSHIP_SATISFACTION_FEATURE_ID)

    def _set_invalid_test_group(self) -> 'None':
        self._clear_ab_test_group()
        new_decay_rate = None
        for relationship in self._relationship_service:
            track_a = relationship.get_track(relationship.sim_id_a, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK)
            if track_a is not None:
                new_decay_rate = track_a.decay_rate
                break
            track_b = relationship.get_track(relationship.sim_id_b, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK)
            if track_b is not None:
                new_decay_rate = track_b.decay_rate
                break
        if new_decay_rate is None:
            return
        with telemetry_helper.begin_hook(ab_test_writer, TELEMETRY_HOOK_DECAY_RATE_AB_GROUP_SET) as hook:
            hook.write_float('nval', new_decay_rate)
            hook.write_int('mesg', 0)

    def _set_ab_test_group(self, group_id:'int') -> 'None':
        if self.AB_TEST_GROUP_ID == group_id:
            return
        self.AB_TEST_GROUP_ID = group_id
        fired_telemetry = False

        def pre_decay_changed(old_value:'float', new_value:'float') -> 'None':
            nonlocal fired_telemetry
            if fired_telemetry:
                return
            fired_telemetry = True
            with telemetry_helper.begin_hook(ab_test_writer, TELEMETRY_HOOK_DECAY_RATE_AB_GROUP_SET) as hook:
                hook.write_float('nval', new_value)
                hook.write_int('mesg', self.AB_TEST_GROUP_ID)

        for relationship in self._relationship_service:
            track_a = relationship.get_track(relationship.sim_id_a, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK)
            if track_a is not None:
                track_a._set_ab_testing_group(self.AB_TEST_GROUP_ID, pre_decay_changed)
            track_b = relationship.get_track(relationship.sim_id_b, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK)
            if track_a is not None:
                track_b._set_ab_testing_group(self.AB_TEST_GROUP_ID, pre_decay_changed)

    def _clear_ab_test_group(self):
        self.AB_TEST_GROUP_ID = None
        for relationship in self._relationship_service:
            track_a = relationship.get_track(relationship.sim_id_a, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK)
            if track_a is not None:
                track_a._clear_ab_testing_group()
            track_b = relationship.get_track(relationship.sim_id_b, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK)
            if track_a is not None:
                track_b._clear_ab_testing_group()

    def shutdown(self) -> 'None':
        services.get_event_manager().unregister(self, self.ALL_EVENTS)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        if event in self.RELATIONSHIP_SATISFACTION_PAUSE_EVENTS:
            self._update_satisfaction_paused(sim_info.sim_id)

    @staticmethod
    def _toggle_satisfaction_active(rel:'Relationship', active:'bool') -> 'None':
        a_track = rel.get_track(rel.sim_id_a, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK, add=False)
        b_track = rel.get_track(rel.sim_id_b, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK, add=False)
        romance_track = rel.get_track(rel.sim_id_a, RelationshipTrack.ROMANCE_TRACK, add=False)
        if a_track is None or b_track is None or romance_track is None:
            return
        a_track.set_decay_enabled_override(active)
        b_track.set_decay_enabled_override(active)
        a_track.visible_to_client = active
        b_track.visible_to_client = active
        romance_track.set_decay_enabled_override(active)

    def _update_satisfaction_paused(self, sim_id:'int') -> 'None':
        if self._relationship_service is None:
            return
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(sim_id)
        for relationship in self._relationship_service.get_all_sim_relationships(sim_id):
            if not relationship.has_track(sim_id, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK):
                pass
            else:
                target_sim_id = relationship.get_other_sim_id(sim_id)
                target_sim_info = sim_info_manager.get(target_sim_id)
                forward_resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
                backward_resolver = DoubleSimResolver(target_sim_info, actor_sim_info)
                is_tracking = relationship.get_track(sim_id, SatisfactionTuning.RELATIONSHIP_SATISFACTION_TRACK, add=False).decay_enabled
                should_be_tracking = bool(SatisfactionTuning.SHOULD_TRACK_TESTS.run_tests(forward_resolver) and SatisfactionTuning.SHOULD_TRACK_TESTS.run_tests(backward_resolver))
                if is_tracking != should_be_tracking:
                    self._toggle_satisfaction_active(relationship, should_be_tracking)
