from __future__ import annotationsimport interactionsfrom interactions.utils.outcome_enums import OutcomeResultfrom business.business_enums import BusinessTypefrom objects.collection_manager_enums import CollectionIdentifierfrom objects.game_object_properties import GameObjectPropertyfrom sims import bills_enumsfrom sims4.common import is_available_pack, Packfrom sims4.tuning import instancesfrom situations.situation_by_definition_or_tags import SituationSearchByDefinitionOrTagsVariantfrom typing import TYPE_CHECKINGfrom venues.venue_enums import VenueTypesfrom zone_tests import ActiveZone, PickInfoZone, PickedZoneIds, ParticipantHomeZoneif TYPE_CHECKING:
    from typing import *
    from situations.situation import Situation
    from role.role_state import RoleStateimport itertoolsfrom aspirations.aspiration_types import AspriationTypefrom bucks.bucks_enums import BucksTypefrom build_buy import FloorFeatureTypefrom careers.career_enums import GigResult, CareerCategoryfrom crafting.photography_enums import PhotoStyleTypefrom event_testing import TargetIdTypesfrom event_testing.resolver import RESOLVER_PARTICIPANT, SingleSimResolverfrom event_testing.results import TestResult, TestResultNumericfrom event_testing.test_events import TestEventfrom gameplay_scenarios.scenario_tests import ScenarioSimStatusTestfrom caches import cached_testfrom interactions import ParticipantType, ParticipantTypeActorTargetSim, ParticipantTypeSingle, TargetType, ParticipantTypeSingleSim, ParticipantTypeObject, ParticipantTypeCASPart, ParticipantTypeSimfrom interactions.context import InteractionSourcefrom objects import ALL_HIDDEN_REASONSfrom objects.components.portal_locking_enums import LockPriority, LockTypefrom relationships.relationship_tests import RelationshipTestBasedScorefrom sims.household_utilities.utility_types import Utilitiesfrom sims.sim_info_tests import SimInfoTestfrom sims.sim_info_types import Genderfrom sims4.math import Operatorfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableFactory, TunableEnumEntry, TunableSingletonFactory, Tunable, OptionalTunable, TunableList, TunableTuple, TunableThreshold, TunableSet, TunableReference, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableInterval, TunableEnumFlags, TunableEnumSet, TunableRange, TunablePackSafeReference, TunableEnumWithFilter, TunableCasPartfrom sims4.utils import flexpropertyfrom singletons import DEFAULTfrom situations.situation_serialization import GLOBAL_SITUATION_LINKED_SIM_IDfrom situations.situation_types import SituationMedal, SituationStage, SituationUserFacingTypefrom socials.social_tests import SocialContextTestfrom tag import Tagfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport build_buyimport cachesimport clockimport date_and_timeimport enumimport event_testing.event_data_constimport event_testing.test_baseimport objects.components.statistic_typesimport scheduler_utilsimport servicesimport sims.bills_enumsimport sims.sim_info_typesimport sims4.tuning.tunableimport snippetsimport tunable_timelogger = sims4.log.Logger('Tests')
class CollectionThresholdTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.CollectionChanged,)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(participant_type_enum, participant_type_default, description='Who or what to apply this test to')}

    FACTORY_TUNABLES = {'description': 'Tests for a provided amount of a given collection type.', 'who': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'collection_type': TunableEnumEntry(description='\n            The collection we are checking on.  If collection type is\n            unidentified then we will look through all collections.\n            ', tunable_type=CollectionIdentifier, default=CollectionIdentifier.Unindentified), 'complete_collection': Tunable(description='\n            Setting this to True (checked) will override the threshold and\n            check for collection completed\n            ', tunable_type=bool, default=False), 'threshold': TunableThreshold(description='\n            Threshold for which the Sim experiences motive failure\n            ', value=Tunable(description='\n                The value of the threshold that the collection is compared\n                against.\n                ', tunable_type=int, default=1), default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function)), 'specific_items': OptionalTunable(description='\n            If enabled then the collection threshold test will check for\n            specific items within the collection.  When enabled both the\n            Collection Type and Complete Collection tuning will be ignored.\n            ', tunable=TunableList(description='\n                List of allowed objects within a collection that we want to\n                check.\n                ', tunable=TunableReference(description='\n                    Object reference to each collectible object.\n                    ', manager=services.definition_manager())))}

    def __init__(self, who, collection_type, complete_collection, threshold, specific_items, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.who = who
        self.collection_type = collection_type
        self.complete_collection = complete_collection
        self.threshold = threshold
        if specific_items is not None:
            self.specific_items = set(specific_item.id for specific_item in specific_items)
        else:
            self.specific_items = None

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=None):
        if test_targets is None:
            return TestResult(False, 'Test Targets are None, valid during zone load.')
        curr_value = 0
        for target in test_targets:
            household = target.household
            if household is None:
                return TestResult(False, 'Household is None when running test, valid during zone load.')
            collection_tracker = household.collection_tracker
            if self.specific_items is not None:
                curr_value += collection_tracker.get_num_of_collected_items_by_definition_ids(self.specific_items)
            elif self.complete_collection:
                if self.collection_type == CollectionIdentifier.Unindentified:
                    for collection_id in CollectionIdentifier:
                        if collection_id != CollectionIdentifier.Unindentified and collection_tracker.check_collection_complete_by_id(collection_id):
                            curr_value += 1
                elif collection_tracker.check_collection_complete_by_id(self.collection_type):
                    curr_value += 1
            elif self.collection_type == CollectionIdentifier.Unindentified:
                for collection_id in CollectionIdentifier:
                    if collection_id != CollectionIdentifier.Unindentified:
                        (base_count, bonus_count) = collection_tracker.get_num_collected_items_per_collection_id(collection_id)
                        curr_value += base_count + bonus_count
            else:
                (base_count, bonus_count) = collection_tracker.get_num_collected_items_per_collection_id(self.collection_type)
                curr_value += base_count + bonus_count
        if self.threshold.compare(curr_value):
            return TestResult.TRUE
        operator_symbol = Operator.from_function(self.threshold.comparison).symbol
        return TestResultNumeric(False, '{} failed collection check: {} {} {}', self.who.name, curr_value, operator_symbol, self.threshold.value, current_value=curr_value, goal_value=self.threshold.value, is_money=False, tooltip=self.tooltip)

    def goal_value(self):
        if self.complete_collection:
            return 1
        return self.threshold.value
TunableCollectionThresholdTest = TunableSingletonFactory.create_auto_factory(CollectionThresholdTest)
class CollectedItemTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.CollectedItem,)
    COLLECTION_TYPE = 0
    SPECIFIC_ITEMS = 1
    FACTORY_TUNABLES = {'test_type': TunableVariant(description='\n            The type of test that will be run.\n            ', collection_type=TunableTuple(description='\n                If selected we will check that the collected item is from the\n                collection that we are looking for.\n                ', collection_types=TunableList(description='\n                    A list of collections to check against.  The test will pass if it\n                    is a part of any of them.  If this list is empty, then it will pass if\n                    it is part of any collection.\n                    ', tunable=TunableEnumEntry(description='\n                        The collection we are checking against.\n                        ', tunable_type=CollectionIdentifier, default=CollectionIdentifier.Unindentified, invalid_enums=(CollectionIdentifier.Unindentified,))), locked_args={'test_type': COLLECTION_TYPE}), specific_items=TunableTuple(description='\n                If selected we will check that the collected item is from a\n                specific list of collectable items that we are looking for.\n                ', specific_items=TunableList(description='\n                    List of allowed objects within a collection that we want to\n                    check.\n                    ', tunable=TunableReference(description='\n                        Object reference to each collectible object.\n                        ', manager=services.definition_manager())), locked_args={'test_type': SPECIFIC_ITEMS}), default='collection_type')}

    def get_expected_args(self):
        return {'collection_id': event_testing.test_constants.FROM_EVENT_DATA, 'collected_item_id': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, collection_id=None, collected_item_id=None):
        if self.test_type.test_type == self.COLLECTION_TYPE:
            if collection_id is None:
                return TestResult(False, 'Collected Item is None, valid during zone load.')
            if self.test_type.collection_types and collection_id not in self.test_type.collection_types:
                return TestResult(False, 'Collected Item is of wrong collection type.')
        elif self.test_type.test_type == self.SPECIFIC_ITEMS:
            if collected_item_id is None:
                return TestResult(False, 'Collected Item is None, valid during zone load.')
            if collected_item_id not in set(specific_item.id for specific_item in self.test_type.specific_items):
                return TestResult(False, 'Collected item is not in in the list of collected items that we are looking for.')
        return TestResult.TRUE

class TopicTest(event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': 'Gate topics of the actor or target Sim.', 'subject': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='Who or what to apply this test to'), 'target_sim': TunableEnumEntry(ParticipantType, ParticipantType.Invalid, description='Set if topic needs a specfic target.  If no target, keep as Invalid.'), 'whitelist_topics': TunableList(TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TOPIC)), description='The Sim must have any topic in this list to pass this test.'), 'blacklist_topics': TunableList(TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TOPIC)), description='The Sim cannot have any topic contained in this list to pass this test.')}

    def __init__(self, subject, target_sim, whitelist_topics, blacklist_topics, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.subject = subject
        self.target_sim = target_sim
        self.whitelist_topics = whitelist_topics
        self.blacklist_topics = blacklist_topics

    def get_expected_args(self):
        if self.target_sim == ParticipantType.Invalid:
            return {'subjects': self.subject}
        else:
            return {'subjects': self.subject, 'targets_to_match': self.target_sim}

    def _topic_exists(self, sim, target):
        if self.whitelist_topics:
            if any(t.topic_exist_in_sim(sim, target=target) for t in self.whitelist_topics):
                return TestResult.TRUE
            return TestResult(False, "{} doesn't have any topic in white list", sim, tooltip=self.tooltip)
        if self.blacklist_topics and any(t.topic_exist_in_sim(sim, target=target) for t in self.blacklist_topics):
            return TestResult(False, '{} has topic in black list', sim, tooltip=self.tooltip)
        return TestResult.TRUE

    @cached_test
    def __call__(self, subjects=None, targets_to_match=None):
        for subject in subjects:
            if subject.is_sim:
                if subject.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, '{} failed topic check: It is not an instantiated sim.', subject, tooltip=self.tooltip)
                subject = subject.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if targets_to_match is not None:
                for target_to_match in targets_to_match:
                    result = self._topic_exists(subject, target_to_match)
                    if not result:
                        return result
            else:
                result = self._topic_exists(subject, None)
                if not result:
                    return result
        return TestResult.TRUE
TunableTopicTest = TunableSingletonFactory.create_auto_factory(TopicTest)
class UseDefaultOfflotToleranceFactory(TunableSingletonFactory):

    @staticmethod
    def factory():
        return objects.components.statistic_types.StatisticComponentGlobalTuning.DEFAULT_OFF_LOT_TOLERANCE

    FACTORY_TYPE = factory

class LotOwnerTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'lot_source': TunableVariant(description='\n            Which Lot we want to test.\n            ', use_current_zone=ActiveZone.TunableFactory(), use_pick_info=PickInfoZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), use_participant_home_zone=ParticipantHomeZone.TunableFactory(), default='use_current_zone'), 'owns_lot': Tunable(description='\n            If checked and subject owns the current lot then this test will\n            pass. If unchecked, subject does not own lot, this test will pass.\n            ', tunable_type=bool, default=True), 'consider_rented_lot_as_owned': Tunable(description='\n            If checked, rented lots are considered owned. If unchecked, rented\n            lots are considered unowned.\n            ', tunable_type=bool, default=True), 'consider_business_lot_as_owned': Tunable(description='\n            If checked, business lots are considered owned. If unchecked, business\n            lots are considered unowned.\n            ', tunable_type=bool, default=True), 'invert': Tunable(description='\n            If checked, this test will return the opposite of what it\'s tuned to\n            return. For instance, if this test is tuned to return True if the\n            active household owns the lot, but "Invert" is checked, it will\n            actually return False.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        args = self.lot_source.get_expected_args()
        args.update({'test_targets': self.subject})
        return args

    def _is_lot_owner(self, zone_id, target):
        if target.household is None:
            return False
        if target.household.home_zone_id == zone_id:
            return True
        if self.consider_rented_lot_as_owned and target.is_renting_zone(zone_id):
            return True
        if self.consider_business_lot_as_owned:
            business_manager = services.business_service().get_business_manager_for_zone(zone_id)
            if business_manager is not None and business_manager.owner_household_id == target.household_id:
                return True
            persistence_service = services.get_persistence_service()
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            if zone_data is not None:
                lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
                for lot_owner in lot_data.lot_owner:
                    if lot_owner.household_id == target.household_id:
                        return True
        return False

    @cached_test
    def __call__(self, test_targets=None, **kwargs):
        zone_id = self.lot_source.get_zone_id(**kwargs)
        if zone_id is not None:
            for target in test_targets:
                if self._is_lot_owner(zone_id, target):
                    if not self.owns_lot:
                        if self.invert:
                            return TestResult.TRUE
                        return TestResult(False, '{} owns the lot, but is not supposed to.', target, tooltip=self.tooltip)
                        if self.owns_lot:
                            if self.invert:
                                return TestResult.TRUE
                            return TestResult(False, '{} does not own the lot, but is supposed to.', target, tooltip=self.tooltip)
                elif self.owns_lot:
                    if self.invert:
                        return TestResult.TRUE
                    return TestResult(False, '{} does not own the lot, but is supposed to.', target, tooltip=self.tooltip)
            if self.invert:
                return TestResult(False, 'Test passed but is tuned to invert the result.', tooltip=self.tooltip)
            return TestResult.TRUE
        return TestResult(False, 'No valid zone found.', tooltip=self.tooltip)

class HasLotOwnerTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': '\n            Test to check if the lot has an owner or not.\n            ', 'has_owner': Tunable(description='\n            If checked then the test will return true if the lot has an\n            owner.\n            If unchecked then the test will return true if the lot does not\n            have an owner.\n            ', tunable_type=bool, default=True), 'lot_source': TunableVariant(description='\n            Which Lot we want to test.\n            ', use_current_zone=ActiveZone.TunableFactory(), use_pick_info=PickInfoZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), use_participant_home_zone=ParticipantHomeZone.TunableFactory(), default='use_current_zone'), 'consider_rented_lot_as_owned': Tunable(description='\n            If unchecked, test will not consider, renting as ownership. If\n            checked and a sim is renting the current lot then the test will\n            treat being rented as having an owner.  If unchecked and a sim\n            is renting the current lot then the test will not treat this\n            lot as having an owner.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return self.lot_source.get_expected_args()

    @cached_test
    def __call__(self, **kwargs):
        zone_id = self.lot_source.get_zone_id(**kwargs)
        zone = services.get_zone(zone_id, allow_uninstantiated_zones=True)
        if not zone.lot:
            return TestResult(False, 'HasLotOwnerTest: No lot found.', tooltip=self.tooltip)
        has_lot_owner = services.get_persistence_service().get_household_id_from_zone_id(zone_id) != 0
        if self.consider_rented_lot_as_owned:
            has_lot_owner = services.travel_group_manager().is_zone_rented(zone_id)
        if (has_lot_owner or self.has_owner) and not has_lot_owner:
            return TestResult(False, 'HasLotOwnerTest: Trying to check if the lot has an owner, but the lot does not have an owner.', tooltip=self.tooltip)
        if self.has_owner or has_lot_owner:
            return TestResult(False, 'HasLotOwnerTest: Trying to check if the lot does not have an owner, but the lot has an owner.', tooltip=self.tooltip)
        return TestResult.TRUE

class DuringWorkHoursTest(event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': 'Returns True if run during a time that the subject Sim should be at work.', 'subject': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'is_during_work': Tunable(description='\n            Check to return True if during work hours.\n            ', tunable_type=bool, default=False), 'fail_if_taking_day_off_during_work': Tunable(description="\n            If checked, this test will fail if the Sim is taking\n            PTO/vacation/sick day during work hours and is_during_work is\n            checked. If not checked, this test won't care about whether or not\n            the Sim is taking the day off.\n            ", tunable_type=bool, default=False), 'career': OptionalTunable(description='\n            If tuned, this test will run against a specific career instead of \n            against any career.\n            ', tunable=TunablePackSafeReference(description='\n                The specific career to test against.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)))}

    def __init__(self, subject, is_during_work, fail_if_taking_day_off_during_work, career, **kwargs):
        super().__init__(**kwargs)
        self.subject = subject
        self.is_during_work = is_during_work
        self.fail_if_taking_day_off_during_work = fail_if_taking_day_off_during_work
        self.career = career

    def get_expected_args(self):
        return {'subjects': self.subject}

    @cached_test
    def __call__(self, subjects=()):
        is_work_time = False
        taking_day_off = False
        for subject in subjects:
            career_tracker = subject.career_tracker
            if self.career is not None:
                career = career_tracker.get_career_by_uid(self.career.guid64)
                if not career_tracker.career_during_work_hours(career):
                    pass
                else:
                    is_work_time = True
                    taking_day_off = career.taking_day_off
                    break
            else:
                career = career_tracker.career_currently_within_hours
                if career is None:
                    pass
                else:
                    is_work_time = True
                    taking_day_off = career.taking_day_off
                    break
            is_work_time = True
            taking_day_off = career.taking_day_off
            break
        if is_work_time:
            if not (self.is_during_work and self.fail_if_taking_day_off_during_work and taking_day_off):
                return TestResult.TRUE
            return TestResult(False, 'Current time is within career work hours.', tooltip=self.tooltip)
        if self.is_during_work:
            return TestResult(False, 'Current time is not within career work hours.', tooltip=self.tooltip)
        return TestResult.TRUE
TunableDuringWorkHoursTest = TunableSingletonFactory.create_auto_factory(DuringWorkHoursTest)
class AtWorkTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.WorkdayStart,)
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'is_at_work': Tunable(description='\n            Check to return True if any of the subjects are at work.\n            ', tunable_type=bool, default=True), 'active_work_restriction': OptionalTunable(description='\n            If enabled, if this is set the test will only pass if the Sim is at\n            an active event. If not set, the test will instead only pass if the\n            Sim is not at an active event.\n            ', tunable=Tunable(tunable_type=bool, default=True))}

    def get_expected_args(self):
        return {'subjects': self.subject}

    @cached_test
    def __call__(self, subjects=(), **kwargs):
        for subject in subjects:
            career = subject.career_tracker.get_currently_at_work_career()
            if career is not None:
                break
        career = None
        if career is not None:
            if not self.is_at_work:
                return TestResult(False, 'Sim is at work {}', career, tooltip=self.tooltip)
            if self.active_work_restriction is not None and career.is_at_active_event != self.active_work_restriction:
                return TestResult(False, '{} does not meet active work restriction: {}', career, self.active_work_restriction, tooltip=self.tooltip)
        elif self.is_at_work:
            return TestResult(False, 'Sim is not at work', tooltip=self.tooltip)
        return TestResult.TRUE

class AssignmentActiveFactory(TunableFactory, AutoFactoryInit):

    @staticmethod
    def factory(career):
        if career is None:
            return False
        return career.on_assignment

    FACTORY_TYPE = factory

class AssignmentSpecificFactory(TunableFactory):

    @staticmethod
    def factory(career, assignment):
        if career is None or not career.on_assignment:
            return False
        return assignment in career.active_assignments

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(assignment=sims4.tuning.tunable.TunableReference(description='\n                Aspiration that needs to be completed for satisfying the\n                daily assignment.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationAssignment', pack_safe=True))

class CareerAssignmentTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.WorkdayStart,)
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'test_type': TunableVariant(description='\n            Type of assignment test we want to run.\n            \n            in_assignment will return True if the Sim is on any type of \n            asignment for its current career.\n            \n            in_specific_assignment will return True only if the current\n            active assignment matches the assignment specified.\n            ', in_assignment=AssignmentActiveFactory(), in_specific_assignment=AssignmentSpecificFactory(), default='in_assignment'), 'negate': Tunable(description='\n            If checked, test will pass if the Sim is not on an assignment.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets, **kwargs):
        for sim in test_targets:
            career = sim.career_tracker.get_on_assignment_career()
            if career is not None:
                break
        career = None
        if career is not None and self.test_type is not None and self.test_type(career):
            if self.negate:
                return TestResult(False, 'Sim has an assignment', tooltip=self.tooltip)
            return TestResult.TRUE
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'Sim has no assignment', tooltip=self.tooltip)

class CareerDailyTaskCompletedTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.WorkDailyTaskProgress,)
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'career': OptionalTunable(description='\n            If tuned, this test will run against a specific career instead of \n            against any career.\n            ', tunable=TunablePackSafeReference(description='\n                The specific career to test against.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)))}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets, **kwargs):
        for sim in test_targets:
            if sim.careers or not sim.has_custom_career:
                return TestResult(False, '{0} does not currently have a career.', sim, tooltip=self.tooltip)
            if sim.careers:
                for career in sim.careers.values():
                    if not self.career is None:
                        if self.career.guid64 == career.guid64:
                            metrics = career.current_level_tuning.performance_metrics
                            for metric in metrics.statistic_metrics:
                                stat = sim.get_statistic(metric.statistic, add=False)
                                progress_value = stat.get_value()
                                if progress_value >= 100:
                                    return TestResult.TRUE
                    metrics = career.current_level_tuning.performance_metrics
                    for metric in metrics.statistic_metrics:
                        stat = sim.get_statistic(metric.statistic, add=False)
                        progress_value = stat.get_value()
                        if progress_value >= 100:
                            return TestResult.TRUE
                return TestResult(False, 'Daily assignment not complete.', tooltip=self.tooltip)
        return TestResult(False, 'Sim has no career.', tooltip=self.tooltip)

class CareerGigCustomerLotTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'career': TunablePackSafeReference(description='\n            The career to test for the gig\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER))}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets, **kwargs):
        if self.career is None:
            return TestResult(False, "No career is tuned or career isn't available ", tooltip=self.tooltip)
        tested_career_uid = self.career.guid64
        current_zone_id = services.current_zone_id()
        for sim in test_targets:
            career = sim.career_tracker.get_career_by_uid(tested_career_uid)
            if career is None:
                pass
            elif career.get_current_gig() is None:
                pass
            elif career.get_customer_lot_id() == current_zone_id:
                return TestResult.TRUE
        return TestResult(False, "Sim is not at gig's customer lot", tooltip=self.tooltip)

class CareerGigResultTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'career': TunablePackSafeReference(description='\n            The career to hold the gig.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'gig_result': TunableEnumEntry(description='\n            The gig result to test to\n            ', tunable_type=GigResult, default=GigResult.SUCCESS)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets, **kwargs):
        if self.career is None:
            return TestResult(False, "No career is tuned or career isn't available ", tooltip=self.tooltip)
        tested_career_uid = self.career.guid64
        for sim in test_targets:
            career = sim.career_tracker.get_career_by_uid(tested_career_uid)
            if career is None:
                pass
            elif career.get_current_gig() is None:
                pass
            elif career.get_current_gig().gig_result == self.gig_result:
                return TestResult.TRUE
        return TestResult(False, 'Gig result does not match', tooltip=self.tooltip)

class CareerGigTestTypeBase(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'active_objective': OptionalTunable(description='\n            If enabled, this objective is also required to be active on any of\n            the tuned Gigs.\n            ', tunable=sims4.tuning.tunable.TunableReference(description='\n                The objective that needs to be active on the gig.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True)), 'before_photos': OptionalTunable(description='\n            If enabled, test against the existence of before photos. If disabled, ignore.\n            ', tunable=Tunable(description='\n                If True, pass only if the the gig has before photos. If False,\n                pass if the gig does not have any before photos.\n                ', tunable_type=bool, default=True)), 'after_photos': OptionalTunable(description='\n            If enabled, test against the existence of after photos. If disabled, ignore.\n            ', tunable=Tunable(description='\n                If True, pass only if the the gig has after photos. If False,\n                pass if the gig does not have any after photos.\n                ', tunable_type=bool, default=True)), 'selected_photo_pairs': OptionalTunable(description='\n            If enabled, test against the existence of selected photo pairs. If disabled, ignore.\n            ', tunable=Tunable(description='\n                If True, pass only if the the active gig has a stored gig history and selected\n                photo pairs. If False, pass if the gig does not have any selected photos.\n                ', tunable_type=bool, default=False))}

    def test(self, career):
        if career is None:
            return False
        current_gigs = career.get_current_gigs()
        if not current_gigs:
            return False
        if self.active_objective is not None:
            for gig in current_gigs:
                if gig.is_objective_active(self.active_objective):
                    return True
            return False
        current_gig = career.get_current_gig()
        if current_gig is not None:
            gig_history_key = current_gig.get_gig_history_key()
            career_sim_info = career.sim_info
            gig_history = career_sim_info.career_tracker.get_gig_history_by_key(gig_history_key)
            if self.before_photos is not None and (gig_history is None or self.before_photos == len(gig_history.before_photos) == 0):
                return False
            if self.after_photos is not None and (gig_history is None or self.after_photos == len(gig_history.after_photos) == 0):
                return False
            elif self.selected_photo_pairs is not None and (gig_history is None or self.selected_photo_pairs == len(gig_history.selected_photos) == 0):
                return False
        return True

class GigActiveFactory(CareerGigTestTypeBase):
    pass

class GigSpecificFactory(CareerGigTestTypeBase):
    FACTORY_TUNABLES = {'gigs': TunableList(description="\n           A list of gigs. If any tuned gig is the sim's current gig, this test\n           will return True.\n           ", tunable=sims4.tuning.tunable.TunableReference(description='\n                Aspiration that needs to be completed for satisfying the\n                daily assignment.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_GIG), pack_safe=True), minlength=1)}

    def test(self, career):
        if not super().test(career):
            return False
        if career is None:
            return False
        current_gigs = career.get_current_gigs()
        if not current_gigs:
            return False
        for current_gig in current_gigs:
            current_gig_id = current_gig.guid64
            if any(gig.guid64 == current_gig_id for gig in self.gigs):
                return True
        return False

class CareerMaxGigFactory(CareerGigTestTypeBase):

    def test(self, career):
        if career is None:
            return False
        current_gigs = career.get_current_gigs()
        if not current_gigs:
            return False
        elif len(current_gigs) == career.current_gig_limit:
            return True
        return False

class CareerGigTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'test_type': TunableVariant(description='\n            The test to perform. Can check a specific list of gigs, if any gig \n            is currently scheduled, or if the Sim already has the max number of\n            gigs for the career.\n            ', any_gig=GigActiveFactory.TunableFactory(description='\n                Return True if any gig is scheduled for the career.\n                '), specific_gigs=GigSpecificFactory.TunableFactory(description='\n                Return True if any of the tuned gigs is scheduled for the\n                career.\n                '), has_max_gigs=CareerMaxGigFactory.TunableFactory(description='\n                Return True if the participant already has the max number of \n                gigs allowed for the career.\n                '), default='any_gig'), 'career': TunablePackSafeReference(description='\n            The career to test for gigs\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'negate': Tunable(description='\n            If checked, test will pass if the Sim does not have the gigs.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets, **kwargs):
        if self.career is None:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, "No career is tuned or career isn't available ", tooltip=self.tooltip)
        tested_career_uid = self.career.guid64
        has_career_gig = False
        for sim in test_targets:
            career = sim.career_tracker.get_career_by_uid(tested_career_uid)
            if career is None:
                pass
            else:
                result = self.test_type.test(career)
                if result:
                    has_career_gig = True
                    break
        if self.negate:
            if has_career_gig:
                return TestResult(False, 'Sim has gig', tooltip=self.tooltip)
            return TestResult.TRUE
        if has_career_gig:
            return TestResult.TRUE
        return TestResult(False, 'Sim does not have gig', tooltip=self.tooltip)
        return TestResult(False, 'No test targets', tooltip=self.tooltip)

class GigHistoryCustomerFactory(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {'targets': ParticipantType.TargetSim}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        if target is None:
            return False
        gig_history = subject.career_tracker.get_gig_history_by_customer(target.id)
        if gig_history is None:
            return False
        if include_active_gig or subject.career_tracker.is_gig_history_active(gig_history):
            return False
        return gig_history.gig_result.within_range(min_gig_result, max_gig_result)

class GigHistoryLotFactory(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        zone_id = services.current_zone_id()
        career_tracker = subject.career_tracker
        for gig_history in career_tracker.gig_history.values():
            if not zone_id != gig_history.lot_id:
                if include_active_gig or career_tracker.is_gig_history_active(gig_history):
                    pass
                elif gig_history.gig_result.within_range(min_gig_result, max_gig_result):
                    return True
        return False

class GigHistoryAnyFactory(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        return subject.career_tracker.has_gig_history_with_result(min_gig_result, max_gig_result, include_active_gig=include_active_gig)

class GigHistorySelectedPhotosCustomer(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {'targets': ParticipantType.TargetSim}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        if target is None:
            return False
        gig_history = subject.career_tracker.get_gig_history_by_customer(target.id)
        if gig_history is None:
            return False
        return subject.career_tracker.has_selected_photos(gig_history)

class GigHistorySelectedPhotosLot(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        zone_id = services.current_zone_id()
        career_tracker = subject.career_tracker
        gig_history = career_tracker.get_gig_history_by_venue(zone_id)
        if gig_history is None:
            return False
        return subject.career_tracker.has_selected_photos(gig_history)

class GigHistorySelectedPhotosAny(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        return subject.career_tracker.has_any_selected_photos()

class GigHistoryBeforePhotosAny(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        return subject.career_tracker.has_any_before_photos()

class GigHistoryAfterPhotosAny(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def test(self, subject, target, min_gig_result, max_gig_result, include_active_gig):
        return subject.career_tracker.has_any_after_photos()

class CareerGigHistoryTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'has_gig_history': Tunable(description="\n            If checked, the test must find a valid gig in the subject's history.\n            If not checked, the test must not find a valid gig in the subject's history.\n            ", tunable_type=bool, default=True), 'test_type': TunableVariant(description='\n            The test to perform. Can check for gig histories based on customer, lot, or any available.\n            ', has_selected_photos_customer=GigHistorySelectedPhotosCustomer.TunableFactory(), has_selected_photos_lot=GigHistorySelectedPhotosLot.TunableFactory(), has_selected_photos_any=GigHistorySelectedPhotosAny.TunableFactory(), has_before_photos_any=GigHistoryBeforePhotosAny.TunableFactory(), has_after_photos_any=GigHistoryAfterPhotosAny.TunableFactory(), any_gig_history=GigHistoryAnyFactory.TunableFactory(), gig_history_customer=GigHistoryCustomerFactory.TunableFactory(), gig_history_lot=GigHistoryLotFactory.TunableFactory(), default='any_gig_history'), 'min_gig_result': TunableEnumEntry(description='\n            The worst acceptable gig result to pass.\n            ', tunable_type=GigResult, default=GigResult.CRITICAL_FAILURE), 'max_gig_result': TunableEnumEntry(description='\n            The best acceptable gig result to pass.\n            ', tunable_type=GigResult, default=GigResult.GREAT_SUCCESS), 'include_active_gig': Tunable(description="\n            If checked, the test can pass on the gig history for the active gig.\n            If not checked, test must find a valid gig history that doesn't match the customer & type of the active gig.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        expected_args = {'subjects': ParticipantType.Actor}
        test_args = self.test_type.get_expected_args()
        expected_args.update(test_args)
        return expected_args

    @cached_test
    def __call__(self, subjects, targets=None, **kwargs):
        for subject in subjects:
            if targets:
                for target in targets:
                    result = self.test_type.test(subject, target, self.min_gig_result, self.max_gig_result, self.include_active_gig)
                    if result == self.has_gig_history:
                        return TestResult.TRUE
            else:
                result = self.test_type.test(subject, None, self.min_gig_result, self.max_gig_result, self.include_active_gig)
                if result == self.has_gig_history:
                    return TestResult.TRUE
        return TestResult(False, 'No valid gig history found.')

class CareerPreviousCareerTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'career': TunablePackSafeReference(description="\n            The career to check against subject's previous career.\n            ", manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'career_category': OptionalTunable(description="\n            Specify what category of careers to look within to get the sim's\n            previous career. If not tuned, will return the last sim's career from all careers. \n            ", tunable=TunableEnumEntry(description='\n                The career category to look within for previous career. \n                ', tunable_type=CareerCategory, default=CareerCategory.Invalid)), 'subject': TunableEnumEntry(description='\n            The participant to check their previous career of. \n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'negate': Tunable(description='\n            If checked, negate the outcome such that if it would pass it will\n            now fail and vice-versa.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subjects': self.subject}

    def __call__(self, subjects):
        for subject in subjects:
            if self.career is None:
                return TestResult(False, 'Tuned career is None, field is a pack safe reference.', subject, tooltip=self.tooltip)
            previous_career_id = subject.career_tracker.get_previous_career_id(self.career_category)
            if previous_career_id is None:
                if self.negate:
                    return TestResult.TRUE
                if self.career_category is None:
                    return TestResult(False, 'Sim {} has no previous career.', subject, tooltip=self.tooltip)
                return TestResult(False, 'Sim {} has no previous career in career category {}.', subject, self.career_category, tooltip=self.tooltip)
            if self.career.guid64 != previous_career_id:
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'Previous career {} does not match tuned career for {}', previous_career_id, subject, tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, "Tuned career matched sim's previous career, but result was negated.", tooltip=self.tooltip)
        return TestResult.TRUE

class SimoleonsTestEvents(enum.Int):
    AllSimoloenEvents = 0
    OnExitBuildBuy = TestEvent.OnExitBuildBuy
    SimoleonsEarned = TestEvent.SimoleonsEarned
    SimoleonsEarnedBB = TestEvent.SimoleonsEarnedBB
    SimoleonsEarnedFireInsuranceFraud = TestEvent.FireInsuranceFraud

class _SimoleonTestValueContextBase(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who to examine for Simoleon values.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantType.Actor, invalid_enums=(ParticipantTypeSingleSim.Invalid,))}

    def test(self, resolver):
        return TestResult.TRUE

    def get_value(self, resolver):
        subject = resolver.get_participant(self.subject)
        return self._get_value(subject)

    def _get_value(self, subject):
        raise NotImplementedError

class _SimoleonTestValueContextNetWorth(_SimoleonTestValueContextBase):

    def _get_value(self, subject):
        household = services.household_manager().get_by_sim_id(subject.sim_id)
        return household.household_net_worth()

class _SimoleonTestValueContextPropertyOnly(_SimoleonTestValueContextBase):

    def _get_value(self, subject):
        household = services.household_manager().get_by_sim_id(subject.sim_id)
        return household.get_property_value()

class _SimoleonTestValueContextTotalCash(_SimoleonTestValueContextBase):

    def _get_value(self, subject):
        household = services.household_manager().get_by_sim_id(subject.sim_id)
        return household.funds.money

class _SimoleonTestValueContextCurrentValue(_SimoleonTestValueContextBase):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who to examine for Simoleon values.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantType.Object)}

    def _get_value(self, subject):
        if hasattr(subject, 'get_object_property'):
            return subject.get_object_property(GameObjectProperty.MODIFIED_PRICE)
        return getattr(subject, 'current_value', 0)

class _SimoleonTestValueContextRetailFunds(_SimoleonTestValueContextBase):

    def test(self, resolver):
        sim = resolver.get_participant(self.subject)
        if sim is None:
            return TestResultNumeric(False, 'Subject {} could not be resolved in the SimoleonValueTest.', self.subject, current_value=0, goal_value=0)
        if services.business_service().get_business_manager_for_zone():
            return TestResult.TRUE
        return TestResultNumeric(False, "Current lot is either not a business lot or the Sim {} doesn't own it.", sim, current_value=0, goal_value=0)

    def _get_value(self, _):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager:
            return business_manager.funds.money
        return 0

class SimoleonsTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'value_context': TunableVariant(description='\n            The context against which to test the value.\n            ', net_worth=_SimoleonTestValueContextNetWorth.TunableFactory(), property_only=_SimoleonTestValueContextPropertyOnly.TunableFactory(), total_cash=_SimoleonTestValueContextTotalCash.TunableFactory(), current_value=_SimoleonTestValueContextCurrentValue.TunableFactory(), retail_funds=_SimoleonTestValueContextRetailFunds.TunableFactory(), default='net_worth'), 'is_apartment': OptionalTunable(description='\n                If checked, test will pass if the zone is an apartment. If\n                unchecked, test passes if the zone is NOT an apartment. Useful\n                 in aspiration tuning, to discriminate between property\n                types in tests of lot value. Allows "Own a House worth X" and\n                "Own an Apartment worth X"\n                ', disabled_name="Don't_Test", enabled_name='Is_or_is_not_apartment_zone', tunable=TunableTuple(description='\n                    Test whether the zone is an apartment or not.\n                    ', is_apartment=Tunable(description='\n                        If checked, test will pass if the zone is an apartment.\n                        If unchecked, test passes if the zone is NOT an\n                        apartment.\n                        ', tunable_type=bool, default=True), consider_penthouse_an_apartment=Tunable(description='\n                        If enabled, we will consider penthouses to be\n                        apartments when testing them against the apartment\n                        check.\n                        ', tunable_type=bool, default=True))), 'value_threshold': TunableThreshold(description='\n            Amounts in Simoleons required to pass\n            '), 'test_event': TunableEnumEntry(description='\n            The event that we want to trigger this instance of the tuned test on. NOTE: OnClientConnect is\n            still used as a trigger regardless of this choice in order to update the UI.\n            ', tunable_type=SimoleonsTestEvents, default=SimoleonsTestEvents.AllSimoloenEvents)}

    def __init__(self, value_context, is_apartment, value_threshold, test_event, **kwargs):
        super().__init__(**kwargs)
        self.value_context = value_context
        self.is_apartment = is_apartment
        self.value_threshold = value_threshold
        if test_event == SimoleonsTestEvents.AllSimoloenEvents:
            self.test_events = (TestEvent.SimoleonsEarned, TestEvent.OnExitBuildBuy)
        else:
            self.test_events = (test_event,)

    def get_expected_args(self):
        return {'resolver': RESOLVER_PARTICIPANT}

    @cached_test
    def __call__(self, resolver):
        if self.is_apartment is not None:
            zone_id = services.current_zone_id()
            is_zone_apartment = services.get_plex_service().is_zone_an_apartment(zone_id, consider_penthouse_an_apartment=self.is_apartment.consider_penthouse_an_apartment)
            if self.is_apartment.is_apartment != is_zone_apartment:
                return TestResult(False, 'Zone failed apartment test', tooltip=self.tooltip)
        test_result = self.value_context.test(resolver)
        if not test_result:
            test_result.goal_value = self.value_threshold.value
            test_result.tooltip = self.tooltip
            return test_result
        if resolver.get_participant(self.value_context.subject) is None:
            return TestResult(False, 'Participant is None')
        value = self.value_context.get_value(resolver)
        if not self.value_threshold.compare(value):
            operator_symbol = Operator.from_function(self.value_threshold.comparison).symbol
            return TestResultNumeric(False, 'Failed value check: {} {} {} (current value: {})', self.value_context, operator_symbol, self.value_threshold.value, value, current_value=value, goal_value=self.value_threshold.value, is_money=True, tooltip=self.tooltip)
        return TestResultNumeric(True, current_value=value, goal_value=self.value_threshold.value, is_money=True)

    def goal_value(self):
        return self.value_threshold.value

    @property
    def is_goal_value_money(self):
        return True
TunableSimoleonsTest = TunableSingletonFactory.create_auto_factory(SimoleonsTest)
class PartySizeTest(event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': 'Require the party size of the subject sim to match a threshold.', 'subject': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='The subject of this party size test.'), 'threshold': TunableThreshold(description='The party size threshold for this test.')}

    def __init__(self, subject, threshold, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.subject = subject
        self.threshold = threshold

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=None):
        for target in test_targets:
            if target is None:
                return TestResult(False, 'Party Size test failed because subject is not set.', tooltip=self.tooltip)
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, '{} failed topic check: It is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            main_group = target.get_main_group()
            if main_group is None:
                return TestResult(False, 'Party Size test failed because subject has no party attribute.', tooltip=self.tooltip)
            group_size = len(main_group)
            if not self.threshold.compare(group_size):
                return TestResult(False, 'Party Size Failed.', tooltip=self.tooltip)
        return TestResult.TRUE
TunablePartySizeTest = TunableSingletonFactory.create_auto_factory(PartySizeTest)
class PartyAgeTest(event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': 'Require all sims in the party meet with the age requirement.', 'subject': TunableEnumEntry(description='\n            The subject of this party age test.', tunable_type=ParticipantType, default=ParticipantType.Actor), 'ages_allowed': TunableEnumSet(description='\n            All valid ages.', enum_type=sims.sim_info_types.Age, enum_default=sims.sim_info_types.Age.ADULT, default_enum_list=[sims.sim_info_types.Age.TEEN, sims.sim_info_types.Age.YOUNGADULT, sims.sim_info_types.Age.ADULT, sims.sim_info_types.Age.ELDER]), 'check_ensemble': Tunable(description="\n            If enabled then we will check against the subject's rally ensemble\n            instead.\n            ", tunable_type=bool, default=False), 'threshold': TunableThreshold(description='\n            The number of sims that must pass these tests per group to pass the\n            test.\n            ', default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function))}

    def __init__(self, subject, ages_allowed, check_ensemble, threshold, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.subject = subject
        self.ages_allowed = ages_allowed
        self.check_ensemble = check_ensemble
        self.threshold = threshold

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=None):
        for target in test_targets:
            if target is None:
                return TestResult(False, 'Party Age test failed because subject is not set.', tooltip=self.tooltip)
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, '{} failed topic check: It is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if self.check_ensemble:
                party = services.ensemble_service().get_ensemble_sims_for_rally(target)
            else:
                party = target.get_main_group()
            if not party:
                return TestResult(False, 'Party Age test failed because subject has no party attribute.', tooltip=self.tooltip)
            passing_sims = sum(1 for sim in party if sim.age in self.ages_allowed)
            if not self.threshold.compare(passing_sims):
                return TestResult(False, "Party has members that age doesn't meet with the requirement", tooltip=self.tooltip)
        return TestResult.TRUE
TunablePartyAgeTest = TunableSingletonFactory.create_auto_factory(PartyAgeTest)
class TotalSimoleonsEarnedTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.SimoleonsEarned,)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'description': 'This test is specifically for account based Achievements, upon         event/situation completion testing if the players account has earned enough Simoleons         from event rewards to pass a threshold.', 'threshold': TunableThreshold(description='The simoleons threshold for this test.'), 'earned_source': TunableEnumEntry(event_testing.event_data_const.SimoleonData, event_testing.event_data_const.SimoleonData.TotalMoneyEarned, description='The individual source that we want to track the simoleons from.')}

    def __init__(self, threshold, earned_source, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.threshold = threshold
        self.earned_source = earned_source

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, data_object=None, objective_guid64=None):
        simoleons_earned = data_object.get_simoleons_earned(self.earned_source)
        if simoleons_earned is None:
            simoleons_earned = 0
        relative_start_value = data_object.get_starting_values(objective_guid64)
        if relative_start_value is not None:
            simoleons = 0
            simoleons_earned -= relative_start_value[simoleons]
        if not self.threshold.compare(simoleons_earned):
            return TestResultNumeric(False, 'TotalEventsSimoleonsEarnedTest: not enough Simoleons.', current_value=simoleons_earned, goal_value=self.threshold.value, is_money=True)
        return TestResult.TRUE

    def save_relative_start_values(self, objective_guid64, data_object):
        data_object.set_starting_values(objective_guid64, [data_object.get_simoleons_earned(self.earned_source)])

    def validate_tuning_for_objective(self, objective):
        if self.threshold == 0:
            logger.error('Error in objective {}. Threshold has value of 0.', objective)

    def goal_value(self):
        return self.threshold.value

    @property
    def is_goal_value_money(self):
        return True
TunableTotalSimoleonsEarnedTest = TunableSingletonFactory.create_auto_factory(TotalSimoleonsEarnedTest)
class TotalInteractedObjectValueTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.OnSendToInventory, TestEvent.MoneyLoot)
    USES_DATA_OBJECT = True
    DEPRECIATED_VALUE = 0
    CATALOG_VALUE = 1
    FACTORY_TUNABLES = {'description': '\n            A tunable factory that tests if an interaction is successfully executed against an object, \n            and sums its values against the data_object. \n            example: if the player Sim has swiped enough Simoleons to pass a threshold.\n            ', 'affordances': TunableList(TunableReference(description='\n            If any of the participants are running any of these affordances,\n            this test will pass.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction', pack_safe=True)), 'object_value_type': TunableVariant(description='\n            This is used to determine which value will be used for the object, its catalog, or depreciated value.\n            ', locked_args={'depreciated_value': DEPRECIATED_VALUE, 'catalog_value': CATALOG_VALUE}, default='depreciated_value'), 'threshold': TunableThreshold(description='\n            Amount in Simoleons required to pass\n            ')}

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64, 'amount': event_testing.test_constants.FROM_EVENT_DATA, 'depreciated_value': event_testing.test_constants.FROM_EVENT_DATA, 'interaction': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, data_object:'event_testing.event_data_object.EventObjectData'=None, objective_guid64:'int'=None, amount:'int'=None, depreciated_value:'int'=None, interaction:'interactions.base.super_interaction.SuperInteraction'=None) -> 'TestResult':
        if objective_guid64 is None:
            return TestResult(False, 'TotalInteractedObjectValueTest: objective_guid64 is none.', tooltip=self.tooltip)
        if data_object is None:
            return TestResult(False, 'TotalInteractedObjectValueTest: data_object is none.', tooltip=self.tooltip)
        count_data = data_object.get_objective_count_data()
        current_amount = 0
        if objective_guid64 in count_data:
            current_amount = count_data[objective_guid64].get_count()
        if amount is None:
            return TestResult(False, 'TotalInteractedObjectValueTest: amount is none, valid during zone load.', tooltip=self.tooltip)
        if interaction is None:
            return TestResult(False, 'TotalInteractedObjectValueTest: No interaction found, this is normal during zone load.', tooltip=self.tooltip)
        if interaction.global_outcome_result != OutcomeResult.SUCCESS:
            return TestResult(False, 'TotalInteractedObjectValueTest: interaction({}) failed.', interaction.affordance, tooltip=self.tooltip)
        if interaction.get_interaction_type() not in self.affordances:
            return TestResult(False, 'TotalInteractedObjectValueTest: interaction is not on the affordances.', tooltip=self.tooltip)
        if depreciated_value is not None and self.object_value_type == self.DEPRECIATED_VALUE:
            current_amount += depreciated_value
        else:
            current_amount += amount
        if not self.threshold.compare(current_amount):
            return TestResultNumeric(False, 'TotalInteractedObjectValueTest: not enough Simoleons acquired through interactions.', current_value=current_amount, goal_value=self.threshold.value, is_money=True, tooltip=self.tooltip)
        return TestResult.TRUE

    def validate_tuning_for_objective(self, objective:'instances.HashedTunedInstanceMetaclass') -> 'None':
        if self.threshold == 0:
            logger.error('Error in objective {}. Threshold has value of 0.', objective)

    def goal_value(self) -> 'int':
        return self.threshold.value

    @property
    def is_goal_value_money(self) -> 'bool':
        return True

class TotalTimePlayedTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.TestTotalTime,)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'description': 'This test is specifically for account based Achievements, upon         client connect testing if the players account has played the game long enough         in either sim time or server time to pass a threshold of sim or server minutes, respectively.        NOTE: The smallest ', 'use_sim_time': Tunable(bool, False, description='Whether to use sim time, or server time.'), 'threshold': TunableThreshold(description='The amount of time played to pass, measured         in the specified unit of time.'), 'time_unit': TunableEnumEntry(date_and_time.TimeUnit, date_and_time.TimeUnit.MINUTES, description='The unit of time         used for testing')}

    def __init__(self, use_sim_time, threshold, time_unit, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.use_sim_time = use_sim_time
        self.threshold = threshold
        self.treshold_value_in_time_units = threshold.value
        self.time_unit = time_unit
        if use_sim_time:
            threshold_value = clock.interval_in_sim_time(threshold.value, time_unit)
        else:
            threshold_value = clock.interval_in_real_time(threshold.value, time_unit)
            self.threshold.value = threshold_value.in_ticks()

    def get_expected_args(self):
        return {'data': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, data=None, objective_guid64=None):
        if data is None:
            return TestResult(False, 'Data object is None, valid during zone load.')
        if self.use_sim_time:
            value_to_test = data.get_time_data(event_testing.event_data_const.TimeData.SimTime)
        else:
            value_to_test = data.get_time_data(event_testing.event_data_const.TimeData.ServerTime)
        relative_start_value = data.get_starting_values(objective_guid64)
        if relative_start_value is not None:
            time = 0
            value_to_test -= relative_start_value[time]
        if not self.threshold.compare(value_to_test):
            value_in_time_units = date_and_time.ticks_to_time_unit(value_to_test, self.time_unit, self.use_sim_time)
            return TestResultNumeric(False, 'TotalTimePlayedTest: not enough time played.', current_value=int(value_in_time_units), goal_value=self.goal_value(), is_money=False)
        return TestResult.TRUE

    def save_relative_start_values(self, objective_guid64, data_object):
        if self.use_sim_time:
            value_to_test = data_object.get_time_data(event_testing.event_data_const.TimeData.SimTime)
        else:
            value_to_test = data_object.get_time_data(event_testing.event_data_const.TimeData.ServerTime)
        data_object.set_starting_values(objective_guid64, [value_to_test])

    def goal_value(self):
        return int(self.treshold_value_in_time_units)
TunableTotalTimePlayedTest = TunableSingletonFactory.create_auto_factory(TotalTimePlayedTest)
class RoutabilityTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of the test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The target of the test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'negate': Tunable(description='\n            If checked, passes the test if the sim does NOT have permissions\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subjects': self.subject, 'targets': self.target}

    def __call__(self, subjects=(), targets=()):
        for subject in subjects:
            if not subject.is_sim:
                return TestResult(False, "subject of routability test isn't sim.", tooltip=self.tooltip)
            subject_household_home_zone_id = subject.household.home_zone_id
            for target in targets:
                if target.is_sim:
                    target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if not target:
                    if self.negate:
                        return TestResult(True)
                    return TestResult(False, "target of routability test isn't instantiated", tooltip=self.tooltip)
                if target.is_on_active_lot():
                    target_zone_id = target.zone_id
                    if subject_household_home_zone_id == target_zone_id:
                        pass
                    else:
                        current_lot = services.get_zone(target_zone_id).lot
                        if current_lot and current_lot.zone_owner_household_id == subject.household.id:
                            pass
                        elif subject.is_renting_zone(target_zone_id):
                            pass
                        else:
                            subject_instance = subject.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                            if not subject_instance:
                                if self.negate:
                                    return TestResult(True)
                                return TestResult(False, "subject of routability test isn't instantiated, and not their home lot, and target not in open streets", tooltip=self.tooltip)
                            for role in subject_instance.autonomy_component.active_roles():
                                if not role.has_full_permissions:
                                    if self.negate:
                                        return TestResult(True)
                                    return TestResult(False, "subject of routability test's roll doesn't have full permissions.", tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'subject has permission to route to target', tooltip=self.tooltip)
        return TestResult(True)

class PostureTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.target is None and (value.container_supports is not None or any(posture.multi_sim for posture in value.required_postures)):
            logger.error('Posture Test in {} for multi-Sim postures requires a target participant.', source, owner='rmccord')
        elif value.target is not None and value.container_supports is None and not any(posture.multi_sim for posture in value.required_postures):
            logger.error('Posture Test in {} has target tuned but does not reference multi sim postures.', source, owner='rmccord')

    FACTORY_TUNABLES = {'description': '\n            Require the participants of this interaction to pass certain posture\n            tests.\n            ', 'subject': TunableEnumEntry(description='\n            The subject of this posture test.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantType.Actor), 'target': OptionalTunable(description='\n            If checking for multi sim postures, this is the linked Sim\n            participant to check for. This must be tuned if container supports\n            is enabled or if a multi sim posture exists in the list of required\n            postures.\n            ', tunable=TunableEnumEntry(description=',\n                The target of multi Sim postures.\n                ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.TargetSim)), 'required_postures': TunableList(description='\n            If this list is not empty, the subject is required to be\n            in at least one of the postures specified here.\n            \n            Note: If a multi Sim posture is tuned in this list, target must\n            also be tuned.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.POSTURE))), 'prohibited_postures': TunableList(description='\n            The test will fail if the subject is in any of these postures.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.POSTURE), pack_safe=True)), 'container_supports': OptionalTunable(description="\n            Test whether or not the subject's current posture's container\n            supports the specified posture.\n            ", tunable=TunableReference(description="\n                The posture that the container of the subject's current posture\n                must support.\n                ", manager=services.get_instance_manager(sims4.resources.Types.POSTURE))), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        required_args = {'actors': self.subject}
        if self.target is not None:
            required_args['targets'] = self.target
        return required_args

    @cached_test
    def __call__(self, actors, targets=None):
        subject_sim = next(iter(actors), None)
        target_sim = next(iter(targets), None) if targets is not None else None
        if subject_sim is None:
            return TestResult(False, 'Posture test failed because the actor is None.')
        subject_sim = subject_sim.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if subject_sim is None:
            return TestResult(False, 'Posture test failed because the actor is non-instantiated.', tooltip=self.tooltip)
        if target_sim is not None:
            target_sim = target_sim.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if self.required_postures:
            for aspect in subject_sim.posture_state.aspects:
                if any(aspect.posture_type is required_posture and (not required_posture.multi_sim or aspect.linked_sim is target_sim) for required_posture in self.required_postures):
                    break
            return TestResult(False, '{} is not in any of the required postures.', subject_sim, tooltip=self.tooltip)
        if self.prohibited_postures:
            for posture_aspect in subject_sim.posture_state.aspects:
                if any(posture_aspect.posture_type is prohibited_posture for prohibited_posture in self.prohibited_postures):
                    return TestResult(False, '{} is in a prohibited posture ({})', subject_sim, posture_aspect, tooltip=self.tooltip)
        if self.container_supports is not None:
            container = subject_sim.posture.target
            if container is None or not container.is_part:
                return TestResult(False, 'Posture container for {} is None or not a part', subject_sim.posture, tooltip=self.tooltip)
            parts = {container}
            parts.update(container.get_overlapping_parts())
            if not any(p.supports_posture_type(self.container_supports) for p in parts):
                return TestResult(False, 'Posture container {} does not support {}', container, self.container_supports, tooltip=self.tooltip)
            if self.container_supports.multi_sim:
                if target_sim is None:
                    return TestResult(False, 'Posture test failed because the target is None')
                if target_sim is None:
                    return TestResult(False, 'Posture test failed because the target is non-instantiated.')
                if not container.has_adjacent_part(target_sim):
                    return TestResult(False, 'Posture container {} requires an adjacent part for {} since {} is multi-Sim', container, target_sim, self.container_supports, tooltip=self.tooltip)
        return TestResult.TRUE

class IdentityTest(AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': '\n            Require the specified participants to be the same, or,\n            alternatively, require them to be different.\n            ', 'subject_a': TunableEnumEntry(description='\n            The participant to be compared to subject_b.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'subject_b': TunableEnumEntry(description='\n            The participant to be compared to subject_a.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'subjects_match': Tunable(description='\n            If True, subject_a must match subject_b. If False, they must not.\n            ', tunable_type=bool, default=False), 'use_definition': Tunable(description='\n            If checked, the two subjects will only compare definition. Not the\n            instance. This will mean two different types of chairs, for\n            instance, can return True if they use the same chair object\n            definition.\n            ', tunable_type=bool, default=False), 'use_value': Tunable(description='\n            If checked, the two subjects will only compare values instead of idenity. A long integer A and B will be \n            equal in value but different in identity, check this if you only want to compare values.\n            ', tunable_type=bool, default=False), 'use_part_owner': Tunable(description='\n            If checked, the two subjects will compare based on the part owner\n            if either are a part. \n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subject_a': self.subject_a, 'subject_b': self.subject_b, 'affordance': ParticipantType.Affordance, 'context': ParticipantType.InteractionContext}

    @cached_test
    def __call__(self, subject_a=None, subject_b=None, affordance=None, context=None):
        subject_a = next(iter(subject_a), None)
        subject_b = next(iter(subject_b), None)
        if affordance.target_type == TargetType.ACTOR:
            if self.subject_a == ParticipantType.TargetSim or self.subject_a == ParticipantType.Object:
                subject_a = context.sim.sim_info
            if self.subject_b == ParticipantType.TargetSim or self.subject_b == ParticipantType.Object:
                subject_b = context.sim.sim_info
        if subject_a.is_sim:
            subject_a = subject_a.sim_info
        if subject_b.is_sim:
            subject_b = subject_b.sim_info
        if affordance is not None and self.subject_a == ParticipantType.ActorPostureTarget and subject_a is not None and self.subject_b == ParticipantType.ActorPostureTarget and subject_b is not None and self.use_definition:
            subject_a = subject_a.definition
            subject_b = subject_b.definition
        if self.use_part_owner:
            if subject_a.is_part:
                subject_a = subject_a.part_owner
            if subject_b.is_part:
                subject_b = subject_b.part_owner
        if self.use_value:
            if self.subjects_match and subject_a != subject_b:
                return TestResult(False, '{} must match {}, but {} is not equal to {}', self.subject_a, self.subject_b, subject_a, subject_b, tooltip=self.tooltip)
            if self.subjects_match or subject_a == subject_b:
                return TestResult(False, '{} must not match {}, but {} is equal to {}', self.subject_a, self.subject_b, subject_a, subject_b, tooltip=self.tooltip)
        elif self.subjects_match:
            if subject_a is not subject_b:
                return TestResult(False, '{} must match {}, but {} is not {}', self.subject_a, self.subject_b, subject_a, subject_b, tooltip=self.tooltip)
        elif subject_a is subject_b:
            return TestResult(False, '{} must not match {}, but {} is {}', self.subject_a, self.subject_b, subject_a, subject_b, tooltip=self.tooltip)
        return TestResult.TRUE
TunableIdentityTest = TunableSingletonFactory.create_auto_factory(IdentityTest)
class SituationRunningTestEvents(enum.Int):
    SituationEnded = event_testing.test_events.TestEvent.SituationEnded
    SituationStarted = event_testing.test_events.TestEvent.SituationStarted

class SituationRunningTest(AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': '\n            A test to see if the participant is part of any situations that are\n            running that satisfy the conditions of the test.\n            ', 'participant': OptionalTunable(tunable=TunableEnumEntry(description='\n                The subject of this situation test.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor)), 'situation_whitelist': OptionalTunable(TunableSet(description='\n            Only whitelisted situations, specified by this set of references or\n            by tags in Tag Whitelist, can cause this test to pass. If no\n            situations are specified in this whitelist, all situations are\n            considered whitelisted.\n            ', tunable=TunableReference(services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True))), 'situation_blacklist': OptionalTunable(description='\n            Blacklisted situations, specified by this set of references or by\n            tag in Tag Blacklist, will cause this test to fail.\n            ', tunable=TunableSet(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True))), 'tag_whitelist': OptionalTunable(description='\n            Only whitelisted situations, specified by this set of tags or by\n            references in Situation Whitelist, can cause this test to pass. If\n            this whitelist is not enabled, all situations are considered\n            whitelisted.\n            ', tunable=TunableSet(tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=('situation',), default=Tag.INVALID, pack_safe=True))), 'tag_blacklist': TunableSet(description='\n            Blacklisted situations, specified by this set of tags or by\n            references in Situation Tag Blacklist, will cause this test to\n            fail.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=('situation',), default=Tag.INVALID, pack_safe=True)), 'level': OptionalTunable(tunable=TunableThreshold(description='\n                A check for the level of the situation we are checking.\n                ')), 'check_for_initiating_sim': Tunable(description='\n            If checked, the situation must be initiated by the tuned Participant.\n            ', tunable_type=bool, default=False), 'test_event': TunableEnumEntry(description='\n            The test event that this test will run on when tuned within an\n            objective or the main goal trigger of a sitaution.\n            \n            If you are tuning this on an interaction then it will do nothing.\n            ', tunable_type=SituationRunningTestEvents, default=SituationRunningTestEvents.SituationEnded)}

    @property
    def test_events(self):
        return (self.test_event,)

    def get_expected_args(self):
        if self.participant is not None:
            return {'test_targets': self.participant, 'situation': event_testing.test_constants.FROM_EVENT_DATA}
        else:
            return {'situation': event_testing.test_constants.FROM_EVENT_DATA}

    def _check_situations(self, situations, target):
        if not situations:
            if self.situation_whitelist is None and (self.tag_whitelist is None and (self.situation_blacklist is not None or self.tag_blacklist)) and not (self.level or self.check_for_initiating_sim):
                return TestResult.TRUE
            return TestResult(False, 'SituationTest: No situation matches criteria.', tooltip=self.tooltip)
        if any(situation.tags & self.tag_blacklist for situation in situations):
            return TestResult(False, 'SituationTest: blacklisted by tag.', tooltip=self.tooltip)
        if self.situation_blacklist is not None and any(type(situation) in self.situation_blacklist for situation in situations):
            return TestResult(False, 'SituationTest: blacklisted by reference.', tooltip=self.tooltip)
        for situation in situations:
            if self.tag_whitelist is not None and not situation.tags & self.tag_whitelist:
                pass
            elif self.situation_whitelist is not None and type(situation) not in self.situation_whitelist:
                pass
            elif self.level is not None:
                level = situation.score
                if not level is None:
                    if not self.level.compare(level):
                        pass
                    elif self.check_for_initiating_sim and situation.initiating_sim_info is not target:
                        pass
                    else:
                        return TestResult.TRUE
            elif self.check_for_initiating_sim and situation.initiating_sim_info is not target:
                pass
            else:
                return TestResult.TRUE
        return TestResult(False, 'SituationRunningTest: No situation matching test criteria found.', tooltip=self.tooltip)

    @cached_test
    def __call__(self, test_targets=None, situation=None):
        if test_targets is not None:
            for target in test_targets:
                if not target.is_sim:
                    return TestResult(False, 'SituationTest: Target {} is not a sim.', target, tooltip=self.tooltip)
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'SituationTest: uninstantiated sim {} cannot be in any situations.', target, tooltip=self.tooltip)
                target_sim = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if target_sim is None:
                    return TestResult(False, 'SituationTest: uninstantiated sim {} cannot be in any situations.', target, tooltip=self.tooltip)
                if situation is None:
                    situations = services.get_zone_situation_manager().get_situations_sim_is_in(target_sim)
                else:
                    situations = (situation,)
                return self._check_situations(situations, target)
        else:
            if situation is None:
                situations = services.get_zone_situation_manager().running_situations()
            else:
                situations = (situation,)
            return self._check_situations(situations, None)
TunableSituationRunningTest = TunableSingletonFactory.create_auto_factory(SituationRunningTest)
class CanCreateUserFacingSituationTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'allow_non_prestige_is_exempt': Tunable(description='\n            If checked, this test will return True if all the situations that\n            are running allow non-prestige events to be started.\n            ', tunable_type=bool, default=False), 'negate': Tunable(description="\n            If checked then this test will pass if the milestone is not\n            complete otherwise it will pass if it's been earned.\n            ", tunable_type=bool, default=False), 'subject': OptionalTunable(description='\n            If enabled, then this test ignores any situations that are linked to sims other than the specified subjects.\n            ', tunable=TunableEnumEntry(description='\n                The subject who can have a global situation created for him.\n                ', tunable_type=ParticipantTypeSim, default=ParticipantType.Actor))}

    def get_expected_args(self):
        if self.subject is not None:
            return {'subjects': self.subject}
        return {}

    @cached_test
    def __call__(self, subjects=None):
        for situation in services.get_zone_situation_manager().get_user_facing_situations_gen():
            if situation.linked_sim_id != GLOBAL_SITUATION_LINKED_SIM_ID and subjects:
                for subject in subjects:
                    if subject.sim_id == situation.linked_sim_id:
                        break
            else:
                if not self.allow_non_prestige_is_exempt:
                    if self.negate:
                        return True
                    return TestResult(False, 'CanCreateUserFacingSituationTest: Cannot                                       create a user facing situation as another                                       one is already running.', tooltip=self.tooltip)
                if not situation.allow_non_prestige_events:
                    if self.negate:
                        return True
                    return TestResult(False, 'CanCreateUserFacingSituationTest: Cannot                                       create a user facing situation as another                                       user facing situation that does not allow                                       non-prestige events to be created is running.', tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'CanCreateUserFacingSituationTest: Able to create a user-facing situation                               (and the result is negated).', tooltip=self.tooltip)
        else:
            return TestResult.TRUE

class UserFacingSituationRunningTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'ignore_user_facing_types': TunableEnumSet(description='\n            Ignore these specific user-facing situation types. \n            e.g. pivotal moment types are generally considered compatible with other types so when using this test \n            to determine whether or not starting another user-facing situation is valid they should be ignored.\n            ', enum_type=SituationUserFacingType, default_enum_list=[SituationUserFacingType.PIVOTAL_MOMENT], allow_empty_set=True), 'is_running': Tunable(description='\n            If checked then this test will return true if a user facing\n            situation is running in the current zone.  If not checked then\n            this test will return false if a user facing situation is\n            running in this zone.\n            ', tunable_type=bool, default=False)}

    def __init__(self, ignore_user_facing_types, is_running, **kwargs):
        super().__init__(**kwargs)
        self.ignore_user_facing_types = ignore_user_facing_types
        self.is_running = is_running

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        situation_manager = services.get_zone_situation_manager()
        is_user_facing_situation_running = situation_manager.is_user_facing_situation_running(user_facing_types_to_ignore=self.ignore_user_facing_types)
        if self.is_running:
            if is_user_facing_situation_running:
                return TestResult.TRUE
            return TestResult(False, 'UserFacingSituationRunningTest: A user facing situation is not running.', tooltip=self.tooltip)
        elif is_user_facing_situation_running:
            return TestResult(False, 'UserFacingSituationRunningTest: A user facing situation is running.', tooltip=self.tooltip)
        else:
            return TestResult.TRUE
TunableUserFacingSituationRunningTest = TunableSingletonFactory.create_auto_factory(UserFacingSituationRunningTest)
class SituationJobTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Require the tuned participant to have a specific situation job.\n            If multiple participants, ALL participants must have the required\n            job to pass.\n            ', 'participant': TunableEnumEntry(description='\n                The subject of this situation job test.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'situation_jobs': TunableSet(description='\n                The participant must have this job in this list or a job that\n                matches the role_tags.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), pack_safe=True)), 'role_tags': TunableSet(description='\n                The  participant must have a job that matches the role_tags or\n                have the situation_job.\n                ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, pack_safe=True)), 'negate': Tunable(description='\n                If checked then the test result will be reversed, so it will\n                test to see if they are not in a job or not in role state\n                that has matching tags.\n                ', tunable_type=bool, default=False)}

    def __init__(self, participant, situation_jobs, role_tags, negate, **kwargs):
        super().__init__(**kwargs)
        self.participant = participant
        self.situation_jobs = situation_jobs
        self.role_tags = role_tags
        self.negate = negate

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=None):
        if not test_targets:
            return TestResult(False, 'SituationJobTest: No test targets to check.')
        for target in test_targets:
            if not target.is_sim:
                return TestResult(False, 'SituationJobTest: Test being run on target {} that is not a sim.', target, tooltip=self.tooltip)
            if isinstance(target, sims.sim_info.SimInfo):
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'SituationJobTest: {} is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            sim_has_job = False
            for situation in services.get_zone_situation_manager().get_situations_sim_is_in(target):
                current_job_type = situation.get_current_job_for_sim(target)
                if current_job_type in self.situation_jobs:
                    sim_has_job = True
                    break
                elif self.role_tags & situation.get_role_tags_for_sim(target):
                    sim_has_job = True
                    break
            if self.negate:
                if sim_has_job:
                    return TestResult(False, "SituationJobTest: Sim has the required jobs when it shouldn't.", tooltip=self.tooltip)
                    if not sim_has_job:
                        return TestResult(False, 'SituationJobTest: Sim does not have required situation job.', tooltip=self.tooltip)
            elif not sim_has_job:
                return TestResult(False, 'SituationJobTest: Sim does not have required situation job.', tooltip=self.tooltip)
        return TestResult.TRUE
TunableSituationJobTest = TunableSingletonFactory.create_auto_factory(SituationJobTest)
class SituationRoleTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Require the tuned participant to have a specific role.\n            If multiple participants, ALL participants must have the required\n            role to pass and not have the forbidden role.\n            ', 'situation_required_roles': TunableSet(description='\n            The participant must have the roles in this list.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.ROLE_STATE), pack_safe=True)), 'situation_forbidden_roles': TunableSet(description='\n            The participant cannot have any of the listed roles.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.ROLE_STATE), pack_safe=True))}

    def __init__(self, situation_required_roles:'List[RoleState]', situation_forbidden_roles:'List[RoleState]', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self.situation_required_roles = situation_required_roles
        self.situation_forbidden_roles = situation_forbidden_roles

    def get_expected_args(self) -> 'Dict[str, ParticipantType]':
        return {'resolver': RESOLVER_PARTICIPANT}

    @cached_test
    def __call__(self, resolver=None) -> 'TestResult':
        test_targets = resolver.get_participants(ParticipantType.Actor)
        if not test_targets:
            return TestResult(False, 'SituationRoleTest: No test targets to check.')
        for target in test_targets:
            if not target.is_sim:
                return TestResult(False, 'SituationRoleTest: Test being run on target {} that is not a sim.', target, tooltip=self.tooltip)
            if isinstance(target, sims.sim_info.SimInfo):
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'SituationRoleTest: {} is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            sim_has_required_roles = True
            sim_has_forbidden_role = False
            for role in target.active_roles():
                if len(self.situation_required_roles) > 0:
                    for required_role in self.situation_required_roles:
                        if role.guid64 != required_role.guid64:
                            sim_has_required_roles = False
                            break
                if len(self.situation_forbidden_roles) > 0:
                    for forbidden_role in self.situation_forbidden_roles:
                        if role.guid64 == forbidden_role.guid64:
                            sim_has_forbidden_role = True
                            break
            if not sim_has_required_roles:
                return TestResult(False, 'SituationRoleTest: Sim has not required roles.', tooltip=self.tooltip)
            if sim_has_forbidden_role:
                return TestResult(False, 'SituationRoleTest: Sim has forbidden roles.', tooltip=self.tooltip)
        return TestResult.TRUE
TunableSituationRoleTest = TunableSingletonFactory.create_auto_factory(SituationRoleTest)
class SituationAvailabilityTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': "Test whether it's possible for this Sim to host a particular Situation.", 'situation': TunableReference(description='\n            The Situation to test against\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))}

    def __init__(self, situation, **kwargs):
        super().__init__(**kwargs)
        self.situation = situation

    def get_expected_args(self):
        return {'hosts': ParticipantType.Actor, 'targets': ParticipantType.TargetSim}

    @cached_test
    def __call__(self, hosts, targets=None):
        for host in hosts:
            if self.situation.cost() > host.household.funds.money:
                return TestResult(False, 'Cannot afford this Situation.', tooltip=self.tooltip)
            for target in targets:
                target_sim_id = 0 if target is None else target.id
                if not self.situation.is_situation_available(host, target_sim_id):
                    return TestResult(False, 'Sim not allowed to host this Situation or Target not allowed to come.')
        return TestResult.TRUE
TunableSituationAvailabilityTest = TunableSingletonFactory.create_auto_factory(SituationAvailabilityTest)
class SituationInJoinableStateTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': "Test whether it's possible for this Sim to host a particular Situation.", 'situation': TunableReference(description='\n            The Situation to test against\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), allow_none=True), 'situation_tags': TunableSet(description='\n            Tags for arbitrary groupings of situation types.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['situation'], default=Tag.INVALID, pack_safe=True))}

    def __init__(self, situation, situation_tags, **kwargs):
        super().__init__(**kwargs)
        self.situation = situation
        self.situation_tags = situation_tags

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        situation_to_test = []
        situation_manager = services.get_zone_situation_manager()
        if self.situation is not None:
            running_situation = situation_manager.get_situation_by_type(self.situation)
            if running_situation is not None:
                situation_to_test.append(running_situation)
        if self.situation_tags:
            situation_to_test.extend(situation_manager.get_situations_by_tags(self.situation_tags))
        if not situation_to_test:
            return TestResult(False, 'No running situation found for situation {} or situation_tag {}.'.format(self.situation, self.situation_tags), tooltip=self.tooltip)
        for situation in situation_to_test:
            if not situation.is_in_joinable_state():
                return TestResult(False, 'Situation {} is not in running state.'.format(situation), tooltip=self.tooltip)
        return TestResult.TRUE
TunableSituationInJoinableStateTest = TunableSingletonFactory.create_auto_factory(SituationInJoinableStateTest)
class SituationCountTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'situation': TunablePackSafeReference(description='\n            A reference to the type of situation to test.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'additional_situations': TunableList(description='\n            References to additional situations to test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True)), 'test': TunableThreshold(description='\n            A Threshold test that specifies the allowed values for the count\n            of the tuned situation.\n            ')}

    def __init__(self, situation, additional_situations, test, **kwargs):
        super().__init__(**kwargs)
        self._situations = additional_situations
        if situation is not None:
            self._situations = self._situations + (situation,)
        self._test = test

    def get_expected_args(self):
        return {}

    def __call__(self):
        if not self._situations:
            return TestResult(False, 'There are no tuned situations loaded, so fail.')
        situation_manager = services.get_zone_situation_manager()
        situations = [situation for situation in situation_manager.get_all() if type(situation) in self._situations]
        if self._test.compare(len(situations)):
            return TestResult.TRUE
        return TestResult(False, 'Not enough situations of the tuned types in the zone.', tooltip=self.tooltip)
TunableSituationCountTest = TunableSingletonFactory.create_auto_factory(SituationCountTest)
class SituationSimCountTest(event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': 'Require a specific situation that the subject sim has to have a certain number of sims that matches a threshold.', 'situation_tags': TunableSet(description='\n            Tags for arbitrary groupings of situation types.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['situation'], default=Tag.INVALID, pack_safe=True)), 'subject': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='The subject of this situation size test.'), 'threshold': TunableThreshold(description='The number of sims required for this test.')}

    def __init__(self, situation_tags, subject, threshold, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.situation_tags = situation_tags
        self.subject = subject
        self.threshold = threshold

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=None, situation=None):
        for target in test_targets:
            if target is None:
                return TestResult(False, 'Situation Sim Count test failed because the subject is not set.', tooltip=self.tooltip)
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, '{} failed topic check: It is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            situation_manager = services.get_zone_situation_manager()
            target_situations = []
            for t in self.situation_tags:
                target_situations.extend(situation_manager.get_situations_sim_is_in_by_tag(target, t))
                target_situations.extend(situation_manager.get_situations_sim_is_in_by_tag(target, t, SituationStage.DYING))
            if len(target_situations) > 0:
                for s in target_situations:
                    if self.threshold.compare(s.num_of_sims):
                        return TestResult.TRUE
            return TestResult(False, 'Situation Sim Count test failed because the subject is not in any situations of the specified category that meet the threshold.', tooltip=self.tooltip)
TunableSituationSimCountTest = TunableSingletonFactory.create_auto_factory(SituationSimCountTest)
class SituationGuestAttireTest(event_testing.test_base.BaseTest):

    class _StyleOrColorSelection(HasTunableSingletonFactory, AutoFactoryInit):

        def test(self, style_tag:'Optional[Tag]', color_tag:'Optional[Tag]', situation:'Situation', negate:'bool') -> 'TestResult':
            if style_tag is None and color_tag is None:
                if negate:
                    return TestResult.TRUE
                return TestResult(False, 'Guest Attire not specified for situation {}'.format(situation))
            if negate:
                return TestResult(False, "Guest Attire 'Style' or 'Color' specified for situation {}, but test tuned to negate.".format(situation))
            return TestResult.TRUE

    class _StyleAndColorSelection(HasTunableSingletonFactory, AutoFactoryInit):

        def test(self, style_tag:'Optional[Tag]', color_tag:'Optional[Tag]', situation:'Situation', negate:'bool') -> 'TestResult':
            if style_tag is None or color_tag is None:
                if negate:
                    return TestResult.TRUE
                return TestResult(False, "Guest Attire does not have both 'Style' and 'Color' specified for situation {}.".format(situation))
            if negate:
                return TestResult(False, "Guest Attire 'Style' and 'Color' are specified for situation {}, but test tuned to negate.".format(situation))
            return TestResult.TRUE

    class _StyleSelection(HasTunableSingletonFactory, AutoFactoryInit):

        def test(self, style_tag:'Optional[Tag]', color_tag:'Optional[Tag]', situation:'Situation', negate:'bool') -> 'TestResult':
            if style_tag is None:
                if negate:
                    return TestResult.TRUE
                return TestResult(False, "Guest Attire 'Style' is not specified for situation {}.".format(situation))
            if negate:
                return TestResult(False, "Guest Attire 'Style' is specified for situation {}, but test tuned to negate.".format(situation))
            return TestResult.TRUE

    class _ColorSelection(HasTunableSingletonFactory, AutoFactoryInit):

        def test(self, style_tag:'Optional[Tag]', color_tag:'Optional[Tag]', situation:'Situation', negate:'bool') -> 'TestResult':
            if color_tag is None:
                if negate:
                    return TestResult.TRUE
                return TestResult(False, "Guest Attire 'Color' is not specified for situation {}.".format(situation))
            if negate:
                return TestResult(False, "Guest Attire 'Color' is specified for situation {}, but test tuned to negate.".format(situation))
            return TestResult.TRUE

    FACTORY_TUNABLES = {'situation': TunablePackSafeReference(description='\n            A reference to the type of situation to test.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), allow_none=False), 'attire_selection': TunableVariant(description='\n            Define what attire selection matters for the test.\n            ', style_or_color=_StyleOrColorSelection.TunableFactory(), style_and_color=_StyleAndColorSelection.TunableFactory(), style_picked=_StyleSelection.TunableFactory(), color_picked=_ColorSelection.TunableFactory(), default='style_or_color'), 'negate': Tunable(description='\n            Pass the test if no customized style has been applied.\n            ', tunable_type=bool, default=False)}

    def __init__(self, situation, attire_selection, negate, **kwargs):
        super().__init__(**kwargs)
        self.situation = situation
        self.attire_selection = attire_selection
        self.negate = negate

    def get_expected_args(self):
        return {}

    def __call__(self) -> 'TestResult':
        situation_manager = services.get_zone_situation_manager()
        running_situation = situation_manager.get_situation_by_type(self.situation)
        if running_situation is None:
            return TestResult(False, 'No running situation found for situation {}.'.format(self.situation))
        (style_tag, color_tag) = running_situation.guest_attire_selection()
        result = self.attire_selection.test(style_tag, color_tag, self.situation, self.negate)
        return result
TunableSituationGuestAttireTest = TunableSingletonFactory.create_auto_factory(SituationGuestAttireTest)
class BillsTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': "Require the participant's bill status to match the specified conditions.", 'participant': TunableEnumEntry(description='\n            The subject whose household is the object of this delinquency test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'delinquency_states': OptionalTunable(TunableList(TunableTuple(description='\n            Tuple containing a utility and its required delinquency state.\n            ', utility=TunableEnumEntry(Utilities, None), is_delinquent=Tunable(description='\n                Whether this utility is required to be delinquent or not delinquent.\n                ', tunable_type=bool, default=True)))), 'additional_bills_delinquency_states': OptionalTunable(TunableList(TunableTuple(description='\n            Tuple containing an AdditionalBillSource and its required\n            delinquency state. EX: This interaction requires that the\n            Maid_Service bill source not be delinquent.\n            ', bill_source=TunableEnumEntry(sims.bills_enums.AdditionalBillSource, None), is_delinquent=Tunable(description='\n                Whether this AdditionalBillSource is required to be delinquent or not delinquent.\n                ', tunable_type=bool, default=True)))), 'payment_due': OptionalTunable(description='\n            Whether or not the participant is required to have a bill payment due.\n            ', tunable=TunableTuple(description='\n                Whether or not the participant is required to have a bill payment due.\n                ', due_type=TunableEnumEntry(description='\n                    What state do we expect the bills to be in.\n                    ', tunable_type=bills_enums.BillDueType, default=bills_enums.BillDueType.IS_DUE), bill_type=TunableEnumEntry(description='\n                    What type of bill should we care about. In EP15 we allow for \n                    separate payment of housing bills (rent, property taxes) and \n                    non housing bills (utilities and other). If EP15 is not installed\n                    we will compare for any bill. With EP15 we will only check for the type\n                    supplied here.\n                    ', tunable_type=bills_enums.BillTypes, default=bills_enums.BillTypes.ALL_BILLS), utility_consumption_threshold=OptionalTunable(description="\n                    Tests to see if the bill's net consumption of utilities passes the threshold. \n                    Only tested if the bill's payment is currently due (and is required to be due).\n                    ", tunable=TunableThreshold(description='\n                        Minimum amount needed to pass this test (if bill is due).\n                        ')))), 'test_participant_owned_households': Tunable(description="\n            If checked, this test will check the delinquency states of all the\n            participant's households.  If unchecked, this test will check the\n            delinquency states of the owning household of the active lot.\n            ", tunable_type=bool, default=False), 'is_repo_man_due': OptionalTunable(description='\n            If enabled we will only pass this test if the bill is delinquent enough to require the repo man to\n            show up.\n            ', tunable=Tunable(description='\n                Check if the repo man is due to collect bad bills or not.\n                ', tunable_type=bool, default=True))}

    def __init__(self, participant, delinquency_states, additional_bills_delinquency_states, payment_due, test_participant_owned_households, is_repo_man_due, **kwargs):
        super().__init__(**kwargs)
        self.participant = participant
        self.delinquency_states = delinquency_states
        self.additional_bills_delinquency_states = additional_bills_delinquency_states
        self.payment_due = payment_due
        self.test_participant_owned_households = test_participant_owned_households
        self.is_repo_man_due = is_repo_man_due

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=None):
        if not self.test_participant_owned_households:
            target_households = [services.owning_household_of_active_lot()]
        else:
            target_households = []
            for target in test_targets:
                target_households.append(services.household_manager().get_by_sim_id(target.id))
        for household in target_households:
            if self.delinquency_states is not None:
                for state in self.delinquency_states:
                    if household is None:
                        if state.is_delinquent:
                            return TestResult(False, 'BillsTest: Required {} to be delinquent, but there is no active household.', state.utility, tooltip=self.tooltip)
                            if household.bills_manager.is_utility_delinquent(state.utility) != state.is_delinquent:
                                return TestResult(False, "BillsTest: Participant's delinquency status for the {} utility is not correct.", state.utility, tooltip=self.tooltip)
                    elif household.bills_manager.is_utility_delinquent(state.utility) != state.is_delinquent:
                        return TestResult(False, "BillsTest: Participant's delinquency status for the {} utility is not correct.", state.utility, tooltip=self.tooltip)
            if self.additional_bills_delinquency_states is not None:
                for state in self.additional_bills_delinquency_states:
                    if household is None:
                        if state.is_delinquent:
                            return TestResult(False, 'BillsTest: Required {} to be delinquent, but there is no active household.', state.bill_source, tooltip=self.tooltip)
                    elif household.bills_manager.is_additional_bill_source_delinquent(state.bill_source) != state.is_delinquent:
                        return TestResult(False, "BillsTest: Participant's delinquency status for the {} additional bill source is not correct.", state.bill_source, tooltip=self.tooltip)
            if self.payment_due is not None:
                if household is not None:
                    household_payment_due = household.bills_manager.mailman_has_delivered_bills()
                else:
                    household_payment_due = False
                if self.payment_due.due_type == bills_enums.BillDueType.IS_DUE and not household_payment_due:
                    return TestResult(False, "BillsTest: Participant's active bill status does not match the specified active bill status.", tooltip=self.tooltip)
                if self.payment_due.due_type == bills_enums.BillDueType.IS_NOT_DUE and household_payment_due:
                    return TestResult(False, "BillsTest: Participant's active bill status does not match the specified active bill status.", tooltip=self.tooltip)
                if is_available_pack(Pack.EP15) and self.payment_due.bill_type == bills_enums.BillTypes.ALL_BILLS:
                    if self.payment_due.due_type == bills_enums.BillDueType.IS_DUE and household_payment_due and self.payment_due.utility_consumption_threshold is not None:
                        total_net_consumption = household.bills_manager.get_utility_bill_total_net_production()
                        if not self.payment_due.utility_consumption_threshold.compare(total_net_consumption):
                            return TestResult(False, "BillsTest: Participant's net utility consumption did not pass the threshold.", tooltip=self.tooltip)
                elif self.payment_due.bill_type == bills_enums.BillTypes.HOUSING_BILLS:
                    if household is not None:
                        housing_costs_owed = household.bills_manager.housing_costs_owed
                        if self.payment_due.due_type == bills_enums.BillDueType.IS_DUE:
                            if not housing_costs_owed > 0:
                                return TestResult(False, "BillsTest: Participant's HOUSING_BILLS do not match the specified payment_due.bill_type: {}.", self.payment_due.due_type, tooltip=self.tooltip)
                        elif self.payment_due.due_type == bills_enums.BillDueType.IS_NOT_DUE:
                            if not housing_costs_owed == 0:
                                return TestResult(False, "BillsTest: Participant's HOUSING_BILLS do not match the specified payment_due.bill_type: {}.", self.payment_due.due_type, tooltip=self.tooltip)
                        elif not housing_costs_owed < 0:
                            return TestResult(False, "BillsTest: Participant's HOUSING_BILLS do not match the specified payment_due.bill_type: {}.", self.payment_due.due_type, tooltip=self.tooltip)
                elif household is not None:
                    non_housing_costs_owed = household.bills_manager.non_housing_costs_owed
                    if self.payment_due.due_type == bills_enums.BillDueType.IS_DUE:
                        if not non_housing_costs_owed > 0:
                            return TestResult(False, "BillsTest: Participant's NON_HOUSING_BILLS do not match the specified payment_due.bill_type: {}.", self.payment_due.due_type, tooltip=self.tooltip)
                    elif self.payment_due.due_type == bills_enums.BillDueType.IS_NOT_DUE:
                        if not non_housing_costs_owed == 0:
                            return TestResult(False, "BillsTest: Participant's NON_HOUSING_BILLS do not match the specified payment_due.bill_type: {}.", self.payment_due.due_type, tooltip=self.tooltip)
                    elif not non_housing_costs_owed < 0:
                        return TestResult(False, "BillsTest: Participant's NON_HOUSING_BILLS do not match the specified payment_due.bill_type: {}.", self.payment_due.due_type, tooltip=self.tooltip)
                    if self.payment_due.utility_consumption_threshold is not None and household.bills_manager.mailman_has_delivered_bills():
                        total_net_consumption = household.bills_manager.get_utility_bill_total_net_production()
                        if not self.payment_due.utility_consumption_threshold.compare(total_net_consumption):
                            return TestResult(False, "BillsTest: Participant's net utility consumption did not pass the threshold.", tooltip=self.tooltip)
            if self.is_repo_man_due is not None:
                if self.is_repo_man_due:
                    if not household.bills_manager.is_repo_man_due:
                        return TestResult(False, 'Checking if the repo man is due and they are not.', tooltip=self.tooltip)
                        if household.bills_manager.is_repo_man_due:
                            return TestResult(False, 'Checking if the repo man is not due and they are.', tooltip=self.tooltip)
                elif household.bills_manager.is_repo_man_due:
                    return TestResult(False, 'Checking if the repo man is not due and they are.', tooltip=self.tooltip)
        return TestResult.TRUE
TunableBillsTest = TunableSingletonFactory.create_auto_factory(BillsTest)
class HouseholdCanPostAlertTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject whose household to check.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor)}

    def get_expected_args(self):
        return {'test_targets': self.subject}

    def __call__(self, test_targets=None):
        for target in test_targets:
            if target.is_sim:
                household = target.household
                if household.missing_pet_tracker.alert_posted:
                    return TestResult(False, 'HouseholdCanPostAlertTest: Household with id {} has already posted an alert.', household.id, tooltip=self.tooltip)
                return TestResult.TRUE
            else:
                return TestResult(False, 'HouseholdCanPostAlertTest: Test target {} is not a Sim.', target)
        return TestResult.TRUE

class HouseholdMissingPetTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject whose household to check.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor)}

    def get_expected_args(self):
        return {'test_targets': self.subject}

    def __call__(self, test_targets=None):
        for target in test_targets:
            if target.is_sim:
                household = target.household
                if household.missing_pet_tracker.missing_pet_id != 0:
                    return TestResult.TRUE
                return TestResult(False, 'HouseholdMissingPetTest: Household with id {} has no missing pets.', household.id)
            else:
                return TestResult(False, 'HouseholdMissingPetTest: Test target {} is not a Sim.', target)
        return TestResult.TRUE

class HouseholdSizeTest(event_testing.test_base.BaseTest, HasTunableSingletonFactory):
    test_events = (TestEvent.HouseholdChanged,)
    COUNT_FROM_PARTICIPANT = 0
    COUNT_EXPLICIT = 1
    COUNT_ACTUAL_SIZE = 2
    COUNT_TESTED_SIM_INFOS = 3
    FACTORY_TUNABLES = {'description': "\n            Require the specified participant's household to have a specified\n            number of free Sim slots.\n            ", 'participant': TunableEnumEntry(description='\n            The subject whose household is the object of this test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'test_type': TunableVariant(description='\n            The type of test to \n            ', participant=TunableTuple(description="\n                Use this option when you're testing a specific Sim being added\n                to the household.\n                ", locked_args={'count_type': COUNT_FROM_PARTICIPANT}, participant=TunableEnumEntry(description='\n                    The participant whose required slot count we consider.\n                    ', tunable_type=ParticipantType, default=ParticipantType.TargetSim)), count=TunableTuple(description="\n                Use this option when you're testing for a specific number of\n                free slots in the household.\n                ", locked_args={'count_type': COUNT_EXPLICIT}, count=TunableThreshold(description='\n                    The number of required free slots for the specified\n                    household.\n                    ', value=Tunable(description='\n                        The value of a threshold.\n                        ', tunable_type=int, default=1), default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function))), actual_size=TunableTuple(description="\n                Use this option when you're testing the actual number of sims\n                in a household.  This should not be used for testing if you\n                are able to add a sim to the household and should only be used\n                for functionality that depents on the actual household members\n                being there and not counting reserved slots.\n                ex. Achievement for having a household of 8 sims.\n                ", locked_args={'count_type': COUNT_ACTUAL_SIZE}, count=TunableThreshold(description='\n                    The number of household members.\n                    ', value=Tunable(description='\n                        The value of a threshold.\n                        ', tunable_type=int, default=1), default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function))), test_sim_infos=TunableTuple(description="\n                Use this option when you're testing that a number of sims\n                in a household pass some tuned test.\n                ex. At least three sims in household are toddlers.\n                ", locked_args={'count_type': COUNT_TESTED_SIM_INFOS}, count=TunableThreshold(description='\n                    The number of household members.\n                    ', value=Tunable(description='\n                        The value of a threshold.\n                        ', tunable_type=int, default=1), default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function)), test=TunableVariant(description='\n                    A test to apply to each sim in the household. If the test\n                    passes for a given sim, that will count toward the total.\n                    ', sim_info=SimInfoTest.TunableFactory(locked_args={'tooltip': None, 'who': ParticipantType.Actor}), scenario_sim_status=ScenarioSimStatusTest.TunableFactory(locked_args={'tooltip': None, 'target_sim': ParticipantType.Actor}), default='sim_info')), default='count')}

    def __init__(self, participant, test_type, **kwargs):
        super().__init__(**kwargs)
        self.participant = participant
        self._sub_test = None
        self.count_type = test_type.count_type
        if self.count_type == self.COUNT_FROM_PARTICIPANT:
            self._expected_args = {'participants': self.participant, 'targets': test_type.participant}
        elif self.count_type == self.COUNT_EXPLICIT:
            self._expected_args = {'participants': self.participant}
            self._count = test_type.count
        elif self.count_type == self.COUNT_ACTUAL_SIZE:
            self._expected_args = {'participants': self.participant}
            self._count = test_type.count
        elif self.count_type == self.COUNT_TESTED_SIM_INFOS:
            self._expected_args = {'participants': self.participant}
            self._count = test_type.count
            self._sub_test = test_type.test

    def get_expected_args(self):
        return self._expected_args

    @cached_test
    def __call__(self, participants={}, targets={}):
        for participant in participants:
            if not participant.is_sim:
                return TestResult(False, 'Participant {} is not a sim.', participant, tooltip=self.tooltip)
            if participant.household is None:
                return TestResult(False, "Participant {} doesn't have household.", participant, tooltip=self.tooltip)
            if self.count_type == self.COUNT_FROM_PARTICIPANT:
                if not targets:
                    return TestResult(False, 'No targets found for HouseholdSizeTest when it requires them.', tooltip=self.tooltip)
                for target in targets:
                    if not target.is_sim:
                        return TestResult(False, 'Target {} is not a sim.', target, tooltip=self.tooltip)
                    if not participant.household.can_add_sim_info(target):
                        return TestResult(False, 'Cannot add {} to {}', target, participant.household, tooltip=self.tooltip)
            elif self.count_type == self.COUNT_EXPLICIT:
                free_slot_count = participant.household.free_slot_count
                if not self._count.compare(free_slot_count):
                    return TestResult(False, "Household doesn't meet free slot count requirement.", tooltip=self.tooltip)
            elif self.count_type == self.COUNT_ACTUAL_SIZE:
                household_size = participant.household.household_size
                if not self._count.compare(household_size):
                    return TestResult(False, "Household doesn't meet size requirements.", tooltip=self.tooltip)
                    if self.count_type == self.COUNT_TESTED_SIM_INFOS:
                        count = 0
                        for sim_info in participant.household:
                            resolver = SingleSimResolver(sim_info)
                            if resolver(self._sub_test):
                                count += 1
                        if not self._count.compare(count):
                            return TestResult(False, "Household doesn't meet tested size requirements.", tooltip=self.tooltip)
            elif self.count_type == self.COUNT_TESTED_SIM_INFOS:
                count = 0
                for sim_info in participant.household:
                    resolver = SingleSimResolver(sim_info)
                    if resolver(self._sub_test):
                        count += 1
                if not self._count.compare(count):
                    return TestResult(False, "Household doesn't meet tested size requirements.", tooltip=self.tooltip)
        return TestResult.TRUE

class ServiceNpcHiredTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': "\n            Tests on the state of service npc requests of the participant's household.\n             EX whether a maid was requested or has been cancelled\n             ", 'participant': TunableEnumEntry(description="\n            The subject of this test. We will use the subject's household\n            to test if the household has requested a service\n            ", tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'service': TunableReference(description='\n            The service tuning to perform the test against\n            ', manager=services.get_instance_manager(sims4.resources.Types.SERVICE_NPC), pack_safe=True), 'hired': Tunable(description="\n            Whether to test if service is hired or not hired.\n            EX: If True, we test that you have hired the tuned service.\n            If False, we test that you don't have the service hired.\n            ", tunable_type=bool, default=True)}

    def __init__(self, participant, service, hired, **kwargs):
        super().__init__(**kwargs)
        self.participant = participant
        self.service = service
        self.hired = hired

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=None):
        if self.service is None:
            if not self.hired:
                return TestResult.TRUE
            return TestResult(False, 'Service was not found, most likely due to pack safeness.', tooltip=self.tooltip)
        for target in test_targets:
            if not target.is_sim:
                return TestResult(False, '{} is not a sim.', target, tooltip=self.tooltip)
            household = target.household
            service_record = household.get_service_npc_record(self.service.guid64, add_if_no_record=False)
            if self.hired:
                if service_record is None or not service_record.hired:
                    return TestResult(False, '{} has not hired service {}.', household, self.service, tooltip=self.tooltip)
                    if service_record is not None and service_record.hired:
                        return TestResult(False, '{} has already hired service {}.', household, self.service, tooltip=self.tooltip)
            elif service_record is not None and service_record.hired:
                return TestResult(False, '{} has already hired service {}.', household, self.service, tooltip=self.tooltip)
        return TestResult.TRUE
TunableServiceNpcHiredTest = TunableSingletonFactory.create_auto_factory(ServiceNpcHiredTest)
class UserRunningInteractionTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.test_for_not_running and value.all_participants_running:
            logger.error('Test for not running and all participants running cannot both be true', owner='nbaker')

    FACTORY_TUNABLES = {'description': '\n            A test that verifies if any of the users of the selected participant are\n            running a specific interaction.\n            ', 'participant': TunableEnumEntry(description='\n            The participant of the interaction used to fetch the users against\n            which the test is run.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'affordances': TunableList(TunableReference(description='\n            If any of the participants are running any of these affordances,\n            this test will pass.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction', pack_safe=True)), 'affordance_lists': TunableList(description='\n            If any of the participants are running any of the affordances in\n            these lists, this test will pass.\n            ', tunable=snippets.TunableAffordanceListReference()), 'test_for_not_running': Tunable(description='\n            Changes this test to check for the opposite case, as in verifying that this interaction is not running.\n            ', tunable_type=bool, default=False), 'all_participants_running': Tunable(description='\n            Returns true only if *all* valid particpants are running a valid \n            affordance.\n            \n            Incompatible with test for not running being true', tunable_type=bool, default=False), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_all_affordances()

    def update_all_affordances(self):
        self.all_affordances = set(self.affordances)
        for affordance_list in self.affordance_lists:
            self.all_affordances.update(affordance_list)

    def get_expected_args(self):
        return {'test_targets': self.participant}

    def matching_interaction_in_si_state(self, si_state):
        return any(si.get_interaction_type() in self.all_affordances for si in si_state)

    @cached_test
    def __call__(self, test_targets=()):
        interaction_is_running = False
        for target in test_targets:
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, '{} is not an instanced object', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if self.matching_interaction_in_si_state(target.si_state):
                    interaction_is_running = True
                elif self.all_participants_running:
                    return TestResult(False, 'Target sim is not running one of {} and test specifies all participants running', self.all_affordances, tooltip=self.tooltip)
            if target.is_part:
                target = target.part_owner
            for user in target.get_users(sims_only=True):
                if self.matching_interaction_in_si_state(user.si_state):
                    interaction_is_running = True
                    if not self.all_participants_running:
                        break
                        if self.all_participants_running:
                            return TestResult(False, 'user {} is not running one of {} and test specifies all participants running', user, self.all_affordances, tooltip=self.tooltip)
                elif self.all_participants_running:
                    return TestResult(False, 'user {} is not running one of {} and test specifies all participants running', user, self.all_affordances, tooltip=self.tooltip)
            if interaction_is_running and not self.all_participants_running:
                break
        if self.test_for_not_running:
            if interaction_is_running:
                return TestResult(False, 'User is running one of {}', self.all_affordances, tooltip=self.tooltip)
            return TestResult.TRUE
        if interaction_is_running:
            return TestResult.TRUE
        else:
            return TestResult(False, 'No user found running one of {}', self.all_affordances, tooltip=self.tooltip)

class ParticipantRunningInteractionTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant of the interaction to test. The test will pass if any participant\n            is running any of the affordances.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'affordances': TunableList(TunableReference(description='\n            The affordances to test.  The test will pass if any participant is running any of \n            the affordances.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction', pack_safe=True)), 'affordance_lists': TunableList(description='\n            The affordances to test.  The test will pass if any participant is running any of \n            the affordances.\n            ', tunable=snippets.TunableAffordanceListReference(pack_safe=True)), 'test_for_not_running': Tunable(description='\n            Changes this test to check for the opposite case, as in verifying that none of these \n            affordances are being run by any of the participants.', tunable_type=bool, default=False), 'test_interaction_queue': Tunable(description="\n            Besides SI states, also check interactions pending in the sim's interaction queue.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=()):
        all_affordances = set(self.affordances)
        for affordance_list in self.affordance_lists:
            all_affordances.update(affordance_list)
        found_sim = False
        for sim_info in test_targets:
            if not sim_info.is_sim:
                pass
            else:
                found_sim = True
                sim = sim_info.get_sim_instance()
                if sim is None:
                    pass
                else:
                    iterable_interactions = itertools.chain(sim.si_state, sim.queue) if self.test_interaction_queue else sim.si_state
                    for interaction in iterable_interactions:
                        if interaction.is_finishing:
                            pass
                        elif interaction.get_interaction_type() in all_affordances:
                            if self.test_for_not_running:
                                return TestResult(False, 'Sim {} is running one of {}', sim, all_affordances, tooltip=self.tooltip)
                            return TestResult.TRUE
                    transition_controller = sim.transition_controller
                    if transition_controller is not None and transition_controller.interaction is not None and transition_controller.interaction.get_interaction_type() in all_affordances:
                        if self.test_for_not_running:
                            return TestResult(False, 'Sim {} is transitioning to one of {}', sim, all_affordances, tooltip=self.tooltip)
                        return TestResult.TRUE
        if not found_sim:
            return TestResult(False, 'No sim found in participant type: {}', test_targets, tooltip=self.tooltip)
        if self.test_for_not_running:
            return TestResult.TRUE
        return TestResult(False, 'No sim was running one of {}', all_affordances, tooltip=self.tooltip)

class AchievementEarnedFactory(TunableFactory):

    @staticmethod
    def factory(sim, tooltip, unlocked, achievement, negate=False):
        if achievement is None:
            if hasattr(unlocked, 'aspiration_type'):
                return TestResult(False, 'UnlockedTest: non-achievement object {} passed to AchievementEarnedFactory.', unlocked, tooltip=tooltip)
            return TestResult.TRUE
        milestone_unlocked = sim.account.achievement_tracker.milestone_completed(achievement)
        if milestone_unlocked != negate:
            return TestResult.TRUE
        return TestResult(False, 'UnlockedTest: Sim has not unlocked achievement {} or unexpectedly did so.', achievement, tooltip=tooltip)

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(description='\n            This option tests for completion of a tuned Achievement.\n            ', achievement=TunableReference(description='\n                The achievement we want to test.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ACHIEVEMENT)), negate=Tunable(description='\n                If enabled, we will require that the achievement is NOT unlocked.\n                ', tunable_type=bool, default=False), **kwargs)

class AspirationEarnedFactory(TunableFactory):

    @staticmethod
    def factory(sim_info, tooltip, unlocked, aspiration, negate=False):
        if sim_info.aspiration_tracker is None:
            return TestResult(False, 'UnlockedTest: aspiration tracker not present on Sim info {}.', sim_info, tooltip=tooltip)
        milestone_unlocked = sim_info.aspiration_tracker.milestone_completed(aspiration)
        if milestone_unlocked != negate:
            return TestResult.TRUE
        return TestResult(False, 'UnlockedTest: Sim has not unlocked aspiration {} or unexpectedly did so.', aspiration, tooltip=tooltip)

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(description='\n            This option tests for completion of a tuned Aspiration.\n            ', aspiration=TunableReference(description='\n                The aspiration we want to test.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION)), negate=Tunable(description='\n                If enabled, we will require that the aspiration is NOT unlocked.\n                ', tunable_type=bool, default=False), **kwargs)

class TestHouseholdMilestoneEarned(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'household_milestone': TunableReference(description='\n            The household milestone to check unlock status against. \n            ', pack_safe=True, manager=services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE)), 'negate': Tunable(description="\n            If checked then this test will pass if the milestone is not\n            complete otherwise it will pass if it's been earned.\n            ", tunable_type=bool, default=False)}

    def __call__(self, sim_info, tooltip, unlocked):
        if self.household_milestone is None:
            return TestResult(False, 'Tuned milestone on {} cannot be None.', self, tooltip=tooltip)
        if sim_info.household is not None and sim_info.household.household_milestone_tracker is not None:
            milestone_unlocked = sim_info.household.household_milestone_tracker.milestone_completed(self.household_milestone)
            if milestone_unlocked == self.negate:
                return TestResult(False, 'UnlockedTest: milestone ({}) has an unlocked status of ({}), which is not the required value.', self.household_milestone, milestone_unlocked, tooltip=tooltip)
        return TestResult.TRUE

class TestAspirationUnlock(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'check_aspiration_type': OptionalTunable(description='\n            If enabled then we will check the aspiration type of the aspiration\n            that was just unlocked.\n            ', tunable=TunableEnumEntry(description='\n                The aspiration type that we are checking if it just completed.\n                ', tunable_type=AspriationType, default=AspriationType.FULL_ASPIRATION)), 'check_complete_only_in_sequence': OptionalTunable(description='\n            If enabled then we will check that the aspiration that was just\n            unlocked has a specific value of complete only in sequence set.\n            ', tunable=Tunable(description='\n                If complete only in sequence should be also be set or not.\n                ', tunable_type=bool, default=True))}

    def __call__(self, sim_info, tooltip, unlocked):
        if unlocked is None:
            return TestResult(False, 'UnlockedTest: No aspiration Unlocked.', tooltip=tooltip)
        aspiration_type = getattr(unlocked, 'aspiration_type', None)
        if aspiration_type is None:
            return TestResult(False, 'UnlockedTest: non-aspiration object {} passed to TestAspirationUnlock.', unlocked, tooltip=tooltip)
        if self.check_aspiration_type is not None and aspiration_type != self.check_aspiration_type:
            return TestResult(False, "UnlockedTest: aspiration object {} passed in isn't of type {}.", unlocked, self.check_aspiration_type, tooltip=tooltip)
        if self.check_complete_only_in_sequence is not None and unlocked.do_not_register_events_on_load != self.check_complete_only_in_sequence:
            return TestResult(False, 'UnlockedTest: aspiration object {} does not have do_not_register_events_on_load equal to {}.', unlocked, self.check_complete_only_in_sequence, tooltip=tooltip)
        return TestResult.TRUE

class TestAspirationsAvailable(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'negate': Tunable(description='\n            If checked then this test will pass if all aspirations are\n            complete otherwise it will pass if there is a still an aspiration\n            that can be unlocked.\n            ', tunable_type=bool, default=False)}

    def __call__(self, sim_info, tooltip, unlocked):
        if sim_info.is_toddler_or_younger:
            return TestResult(False, "Todders and below can't have primary aspirations.", tooltip=tooltip)
        aspiration_tracker = sim_info.aspiration_tracker
        for aspiration_track in services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK).types.values():
            if not aspiration_track.is_valid_for_sim(sim_info):
                pass
            else:
                for aspiration in aspiration_track.aspirations.values():
                    if not aspiration_tracker.milestone_completed(aspiration):
                        if self.negate:
                            return TestResult(False, 'TestAspirationsAvailable: There is an aspiration {} that has not been completed.', aspiration, tooltip=tooltip)
                        return TestResult.TRUE
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'TestAspirationsAvailable: There are no aspirations still to unlock.', tooltip=tooltip)

class TestBuildBuyRewardEarned(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'object_definition': TunableReference(description='\n            Tests if the specified Object Definition has been unlocked in Build/Buy.\n            \n            This test will NOT work for Build Buy objects that are always unlocked.\n            It needs to have been locked before and unlocked through something like\n            a Build Buy Object Reward.\n            ', manager=services.definition_manager()), 'negate': Tunable(description='\n            If checked, the test will pass if the Build/Buy object is still locked.\n            ', tunable_type=bool, default=False)}

    def _get_resource_key(self):
        return sims4.resources.Key(Types.OBJCATALOG, self.object_definition.id)

    def __call__(self, sim_info, tooltip, unlocked):
        has_key = self._get_resource_key() in sim_info.household.build_buy_unlocks
        if has_key != self.negate:
            return TestResult.TRUE
        return TestResult(False, 'UnlockedTest: Build/Buy object ({}) has an unlocked status of ({}), which is not the required value.', self.object_definition, has_key, tooltip=tooltip)

class UnlockedTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.UnlockEvent,)
    USES_EVENT_DATA = True

    @TunableFactory.factory_option
    def unlock_type_override(allow_achievment=True):
        kwargs = {}
        default = 'aspiration'
        kwargs['aspiration'] = AspirationEarnedFactory()
        kwargs['aspiration_unlocked'] = TestAspirationUnlock.TunableFactory()
        kwargs['aspirations_available'] = TestAspirationsAvailable.TunableFactory()
        kwargs['build_buy_reward_earned'] = TestBuildBuyRewardEarned.TunableFactory()
        kwargs['household_milestone_earned'] = TestHouseholdMilestoneEarned.TunableFactory()
        if allow_achievment:
            default = 'achievement'
            kwargs['achievement'] = AchievementEarnedFactory()
        return {'unlock_to_test': TunableVariant(description='\n            The unlocked aspiration, career, achievement, or milestone want to test for.\n            ', default=default, **kwargs), 'participant': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='The subject of this test.')}

    def __init__(self, *, unlock_to_test, participant, **kwargs):
        super().__init__(**kwargs)
        self.unlock_to_test = unlock_to_test
        self.participant = participant

    def get_expected_args(self):
        return {'sims': self.participant, 'unlocked': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, sims=None, unlocked=None):
        for sim in sims:
            return self.unlock_to_test(sim, self.tooltip, unlocked)
TunableUnlockedTest = TunableSingletonFactory.create_auto_factory(UnlockedTest)
class DayTimeTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Test to see if the current time falls within the tuned range\n            and/or is on a valid day.\n            ', 'days_available': OptionalTunable(scheduler_utils.TunableDayAvailability()), 'time_range': OptionalTunable(TunableTuple(description='\n            The time the test is valid.  If days_available is tuned and the\n            time range spans across two days with the second day tuned as\n            unavailable, the test will pass for that day until time range is\n            invalid.  Example: Time range 20:00 - 4:00, Monday is valid,\n            Tuesday is invalid.  Tuesday at 2:00 the test passes.  Tuesday at\n            4:01 the test fails.\n            ', begin_time=tunable_time.TunableTimeOfDay(default_hour=0), duration=tunable_time.TunableTimeOfDay(default_hour=1))), 'is_day': OptionalTunable(description="\n            If enabled, allows you to only pass the test if it's either day or\n            night, as per the Region's tuned sunrise and sunset times.\n            ", tunable=Tunable(description="\n                If checked, this test will only pass if all other criteria are\n                met and it's currently day time (between the sunrise and sunset\n                times tuned for the current region).\n                \n                If unchecked, this test will only pass if all other criteria are\n                met and it's currently night time (between the sunset and\n                sunrise times tune for the current region).\n                ", tunable_type=bool, default=True))}

    def __init__(self, days_available, time_range, is_day, **kwargs):
        super().__init__(**kwargs)
        self.days_available = days_available
        self.time_range = time_range
        self.is_day = is_day
        self.weekly_schedule = set()
        if time_range is not None:
            for day in days_available:
                if days_available[day]:
                    days_as_time_span = date_and_time.create_time_span(days=day)
                    start_time = self.time_range.begin_time + days_as_time_span
                    end_time = start_time + date_and_time.create_time_span(hours=self.time_range.duration.hour(), minutes=self.time_range.duration.minute())
                    self.weekly_schedule.add((start_time, end_time))

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        if self.is_day is not None and services.time_service().is_day_time() != self.is_day:
            return TestResult(False, 'Day and Time Test: Test wants it to be {} but it currently is not.', 'day' if self.is_day else 'night', tooltip=self.tooltip)
        current_time = services.time_service().sim_now
        if self.weekly_schedule:
            for times in self.weekly_schedule:
                if current_time.time_between_week_times(times[0], times[1]):
                    return TestResult.TRUE
            return TestResult(False, 'Day and Time Test: Current time and/or day is invalid.', tooltip=self.tooltip)
        if self.days_available is not None:
            day = current_time.day()
            if self.days_available[day]:
                return TestResult.TRUE
            return TestResult(False, 'Day and Time Test: {} is not a valid day.', tunable_time.Days(day), tooltip=self.tooltip)
        if self.time_range is not None:
            begin = self.time_range.begin_time
            end = begin + date_and_time.create_time_span(hours=self.time_range.duration.hour(), minutes=self.time_range.duration.minute())
            if current_time.time_between_day_times(begin, end):
                return TestResult.TRUE
            return TestResult(False, 'Day and Time Test: Current time outside of tuned time range of {} - {}.', begin, end, tooltip=self.tooltip)
        return TestResult.TRUE
TunableDayTimeTest = TunableSingletonFactory.create_auto_factory(DayTimeTest)
class SocialGroupTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': "Require a Sim to be part of a specified social group type, and optionally if that group's size is within a tunable threshold.", 'subject': TunableEnumEntry(description='\n            The subject of this social group test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'social_group_type': OptionalTunable(description='\n            If enabled, the participant must have this type of group available.\n            If this is disabled, any group will work.\n            ', tunable=TunableReference(description='\n                The required social group type.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SOCIAL_GROUP)), disabled_name='Any_Group'), 'threshold': OptionalTunable(description="\n            If enabled, tests the group size to ensure it's within a threshold.\n            ", tunable=TunableThreshold(description='\n                Optional social group size threshold test.\n                ')), 'check_if_entire_group_is_active': OptionalTunable(description='\n                If enabled then this test will check to see if the entire group\n                is active or not.\n                ', tunable=Tunable(description='\n                    If checked then the test will pass if the entire social\n                    group is active.  If unchecked then the test will pass\n                    if there are sims in the social group that are not active.\n                    ', tunable_type=bool, default=True)), 'additional_participant': OptionalTunable(description='\n                Test if this participant is or is not in the same social group\n                as Subject.\n                ', tunable=TunableTuple(participant=TunableEnumEntry(description='\n                        The participant that must also be or not be in the social group.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Actor), in_group=Tunable(description="\n                        If enabled, this additional participant must be in the group.\n                        If disabled, this additional participant can't be in the group.\n                        ", tunable_type=bool, default=True)))}

    def get_expected_args(self):
        expected_args = {'test_targets': self.subject}
        if self.additional_participant is not None:
            expected_args['additional_targets'] = self.additional_participant.participant
        return expected_args

    @cached_test
    def __call__(self, test_targets=None, additional_targets=None):
        for target in test_targets:
            if target is None:
                pass
            else:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'Social Group test failed: {} is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                for group in target.get_groups_for_sim_gen():
                    if not self.social_group_type is None:
                        if type(group) is self.social_group_type:
                            group_size = group.get_active_sim_count()
                            if self.threshold is not None and not self.threshold.compare(group_size):
                                return TestResult(False, 'Social Group test failed: group size not within threshold.', tooltip=self.tooltip)
                            if len(group) == group_size:
                                if not self.check_if_entire_group_is_active:
                                    return TestResult(False, 'Social Group test failed: Social group is entirey active but we are checking for it not to be.', tooltip=self.tooltip)
                            elif self.check_if_entire_group_is_active:
                                return TestResult(False, 'Social Group test failed: Social group is not entirely active but we are checking for it to be.', tooltip=self.tooltip)
                            if self.check_if_entire_group_is_active is not None and additional_targets is not None:
                                group_sim_ids = set(group.member_sim_ids_gen())
                                if self.additional_participant.in_group:
                                    if any(sim.sim_id not in group_sim_ids for sim in additional_targets):
                                        return TestResult(False, 'Social Group test failed: Additional participant not in group.', tooltip=self.tooltip)
                                elif any(sim.sim_id in group_sim_ids for sim in additional_targets):
                                    return TestResult(False, 'Social Group test failed: Additional participant in group.', tooltip=self.tooltip)
                            return TestResult.TRUE
                    group_size = group.get_active_sim_count()
                    if self.threshold is not None and not self.threshold.compare(group_size):
                        return TestResult(False, 'Social Group test failed: group size not within threshold.', tooltip=self.tooltip)
                    if len(group) == group_size:
                        if not self.check_if_entire_group_is_active:
                            return TestResult(False, 'Social Group test failed: Social group is entirey active but we are checking for it not to be.', tooltip=self.tooltip)
                    elif self.check_if_entire_group_is_active:
                        return TestResult(False, 'Social Group test failed: Social group is not entirely active but we are checking for it to be.', tooltip=self.tooltip)
                    if self.check_if_entire_group_is_active is not None and additional_targets is not None:
                        group_sim_ids = set(group.member_sim_ids_gen())
                        if self.additional_participant.in_group:
                            if any(sim.sim_id not in group_sim_ids for sim in additional_targets):
                                return TestResult(False, 'Social Group test failed: Additional participant not in group.', tooltip=self.tooltip)
                        elif any(sim.sim_id in group_sim_ids for sim in additional_targets):
                            return TestResult(False, 'Social Group test failed: Additional participant in group.', tooltip=self.tooltip)
                    return TestResult.TRUE
        return TestResult(False, "Social Group test failed: subject not part of a '{}' social group.", self.social_group_type, tooltip=self.tooltip)

class InteractionRestoredFromLoadTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'description': 'Test whether an interaction was pushed from load or from normal gameplay.', 'from_load': Tunable(description='\n            If checked, this test will pass if the interaction was restored from\n            save load (restored interactions are pushed behind the loading screen).\n            If not checked, this test will only pass if the interaction was pushed\n            during normal gameplay.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'context': ParticipantType.InteractionContext}

    def __call__(self, context=None):
        if context is not None and context.restored_from_load != self.from_load:
            return TestResult(False, 'InteractionRestoredFromLoadTest failed. We wanted interaction restored from load to be {}.', self.from_load, tooltip=self.tooltip)
        return TestResult.TRUE

class SocialBoredomTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'threshold': TunableThreshold(description="\n            The test will fail if the affordance's boredom does not satisfy this\n            threshold.\n            ")}

    def get_expected_args(self):
        return {'affordance': ParticipantType.Affordance, 'social_group': ParticipantType.SocialGroup, 'subject': ParticipantType.Actor, 'target': ParticipantType.TargetSim}

    @cached_test
    def __call__(self, affordance=None, social_group=None, subject=None, target=None):
        subject = next(iter(subject), None)
        target = next(iter(target), None)
        social_group = next(iter(social_group), None)
        if subject is not None:
            subject = subject.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if target is not None:
            target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if subject is None or target is None:
            return TestResult(False, '{} does not target instantiated Sims', affordance)
        if social_group is None:
            return TestResult(False, 'There is no social group associated with {}', affordance)
        boredom = social_group.get_boredom(subject, target, affordance)
        if not self.threshold.compare(boredom):
            return TestResult(False, 'Failed threshold test {} {}', boredom, self.threshold, tooltip=self.tooltip)
        return TestResult.TRUE

class CareerHighestLevelAchievedTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'career_blacklist': TunableSet(description='\n            A set of careers that will not be looked at.\n            ', tunable=TunableReference(description='\n                The career we will not check.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), pack_safe=True)), 'careers_to_check': OptionalTunable(description='\n            If enabled then we will only look at the careers listed in this.\n            set.  Otherwise will will look at all careers.\n            ', tunable=TunableSet(description='\n                A set of careers that will be looked at.\n                ', tunable=TunableReference(description='\n                    The career we will check.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), pack_safe=True))), 'passing_threshold': TunableThreshold(description='\n            Threshold for determining if a career is considered passing for\n            this test.\n            '), 'careers_to_find': TunableRange(description='\n            The number of careers that need to match the passing threshold for\n            this test to pass.\n            ', tunable_type=int, default=1, minimum=1)}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self, subjects, targets=None, tooltip=None):
        highest_level = 0
        for subject in subjects:
            found_careers = 0
            if self.careers_to_check is not None:
                careers_to_check = self.careers_to_check
            else:
                careers_to_check = services.get_instance_manager(sims4.resources.Types.CAREER).types.values()
            for career in careers_to_check:
                if career in self.career_blacklist:
                    pass
                else:
                    level_reached = subject.career_tracker.get_highest_level_reached(career.guid64)
                    if level_reached > highest_level:
                        highest_level = level_reached
                    if not self.passing_threshold.compare(level_reached):
                        pass
                    else:
                        found_careers += 1
                        if found_careers >= self.careers_to_find:
                            break
            if found_careers < self.careers_to_find:
                if self.careers_to_find > 1:
                    current_value = found_careers
                    goal_value = self.careers_to_find
                else:
                    current_value = highest_level
                    goal_value = self.passing_threshold.value
                return TestResultNumeric(False, 'CareerHighestLevelAchievedTest: Not enough careers found passing the threshold.', current_value=current_value, goal_value=goal_value, is_money=False, tooltip=tooltip)
        return TestResult.TRUE

    def goal_value(self):
        if self.careers_to_find > 1:
            return self.careers_to_find
        else:
            return self.passing_threshold.value

class CareerAttendedFirstDay(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'career': TunablePackSafeReference(description='\n            The career to see if the Sim has gone to work for.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER))}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self, subjects, targets=None, tooltip=None):
        for subject in subjects:
            if self.career is None:
                return TestResult(False, 'Career is None, probably due to packsafeness.', subject, tooltip=tooltip)
            career = subject.careers.get(self.career.guid64, None)
            if career is None:
                return TestResult(False, '{} does not have career {}', subject, self.career, tooltip=tooltip)
            if not career.has_attended_first_day:
                return TestResult(False, '{} has not attended first day of {}', subject, self.career, tooltip=tooltip)
        return TestResult.TRUE

class _TargetSpecificCareer(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'career': TunablePackSafeReference(description='\n            The career to test against.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER))}

    def run_check(self, subject, check_to_run, tooltip):
        if self.career is None:
            return TestResult(False, 'Career is None, probably due to packsafeness.', subject, tooltip=tooltip)
        career = subject.careers.get(self.career.guid64, None)
        if career is None:
            return TestResult(False, '{} does not have career {}', subject, self.career, tooltip=tooltip)
        return check_to_run(subject, career)

class _TargetAllCareers(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'all_must_pass': Tunable(description='\n            If checked, will fail if any career fails, even if others pass.\n            ', tunable_type=bool, default=False)}

    def run_check(self, subject, check_to_run, tooltip):
        if len(subject.careers) <= 0:
            return TestResult(False, 'Subject {} has no careers', subject, tooltip=tooltip)
        for career in subject.careers.values():
            result = check_to_run(subject, career)
            if result:
                if self.all_must_pass or result:
                    return result
            return result
        if self.all_must_pass:
            return TestResult.TRUE
        return TestResult(False, "None of subject {}'s careers passed test {}", subject, check_to_run, tooltip=tooltip)

class _TargetSomeCareers(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'careers': TunableSet(description='\n            The set of careers to test against.\n            ', tunable=TunablePackSafeReference(description='\n                The career to test against.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), minlength=1), 'all_must_pass': Tunable(description='\n            If checked, will fail if any career fails, even if others pass.\n            ', tunable_type=bool, default=False)}

    def run_check(self, subject, check_to_run, tooltip):
        if len(subject.careers) <= 0:
            return TestResult(False, 'Subject {} has no careers', subject, tooltip=tooltip)
        for career_def in self.careers:
            career = subject.careers.get(career_def.guid64, None)
            if career is None:
                if self.all_must_pass:
                    return TestResult(False, 'Subject {} was missing career {}', subject, career_def, tooltip=tooltip)
                    result = check_to_run(subject, career)
                    if result:
                        if self.all_must_pass or result:
                            return result
                    return result
            else:
                result = check_to_run(subject, career)
                if result:
                    if self.all_must_pass or result:
                        return result
                return result
        if self.all_must_pass:
            return TestResult.TRUE
        return TestResult(False, "None of subject {}'s careers passed test {}", subject, check_to_run, tooltip=tooltip)

class _CareerSourceTunable(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'career_source': TunableVariant(description='\n            Which career(s) to test against.\n            ', all_careers=_TargetAllCareers.TunableFactory(description='\n                Test against all careers on the subject.\n                '), single_career=_TargetSpecificCareer.TunableFactory(description='\n                Test against a single, specific career.\n                '), some_careers=_TargetSomeCareers.TunableFactory(description='\n                Test against a subset of careers.\n                '), default='single_career')}

    def run_check(self, subject, check_to_run, tooltip):
        return self.career_source.run_check(subject, check_to_run, tooltip)

class CareerDaysWorked(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'career_source': _CareerSourceTunable.TunableFactory(description='\n            Which career(s) to test against.\n            '), 'threshold': TunableThreshold(description='\n            Threshold test for days worked.\n            '), 'active_only': Tunable(description='\n            If checked, only workdays that the player has actively played will\n            count.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self, subjects, tooltip=None):
        for subject in subjects:
            result = self.career_source.run_check(subject, self.test_days_worked_for_career, tooltip)
            if not result:
                return result
        return TestResult.TRUE

    def get_days_worked(self, career):
        if self.active_only:
            return career.active_days_worked_statistic.get_value()
        return career.days_worked_statistic.get_value()

    def test_days_worked_for_career(self, subject, career, tooltip=None):
        if not self.threshold.compare(self.get_days_worked(career)):
            return TestResult(False, 'Threshold not met. Sim: {}, Career: {}, Threshold: {}', subject, career, self.threshold, tooltip=tooltip)
        return TestResult.TRUE

class CareerStoryProgressionModificationType(enum.Int):
    JOIN = 1
    QUIT = 2
    RETIRE = 3

class HasCareerTestFactory(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'has_career': Tunable(description='\n            If true all subjects must have a career for the test to pass. If False then none of the subjects \n            can have a career for the test to pass.\n            ', tunable_type=bool, default=True), 'story_progression_requirement': OptionalTunable(description='\n            If Has Career is tuned to true, the subjects must have a career that allows for the specified modification\n            by the story progression system.  If Has Career is tuned to false, this field is ignored.\n            ', tunable=TunableEnumEntry(tunable_type=CareerStoryProgressionModificationType, default=CareerStoryProgressionModificationType.JOIN))}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self, subjects, targets=None, tooltip=None):
        for subject in subjects:
            if self.has_career:
                if subject.careers or not subject.has_custom_career:
                    return TestResult(False, '{0} does not currently have a career.', subject, tooltip=tooltip)
                if subject.careers:
                    visible_career_found = False
                    story_progression_requirements_met = self.story_progression_requirement is None
                    for career in subject.careers.values():
                        if career.is_visible_career:
                            visible_career_found = True
                        if self._check_story_progression_requirement(subject, career):
                            story_progression_requirements_met = True
                    if not visible_career_found:
                        return TestResult(False, '{0} does not currently have a visible career.', subject, tooltip=tooltip)
                    if not story_progression_requirements_met:
                        return TestResult(False, '{0} does not currently have a career that supports {1} modifications by the story progression system.', subject, self.story_progression_requirement, tooltip=tooltip)
                        if subject.has_custom_career:
                            return TestResult(False, '{0} currently has a career'.format(subject), tooltip=tooltip)
                        if subject.careers:
                            for career in subject.careers.values():
                                if career.is_visible_career:
                                    return TestResult(False, '{0} currently has a career'.format(subject), tooltip=tooltip)
            else:
                if subject.has_custom_career:
                    return TestResult(False, '{0} currently has a career'.format(subject), tooltip=tooltip)
                if subject.careers:
                    for career in subject.careers.values():
                        if career.is_visible_career:
                            return TestResult(False, '{0} currently has a career'.format(subject), tooltip=tooltip)
        return TestResult.TRUE

    def _check_story_progression_requirement(self, subject, career):
        if self.story_progression_requirement is None:
            return True
        else:
            resolver = SingleSimResolver(subject)
            multipliers = None
            if self.story_progression_requirement == CareerStoryProgressionModificationType.JOIN:
                multipliers = career.career_story_progression.joining
            elif self.story_progression_requirement == CareerStoryProgressionModificationType.QUIT:
                multipliers = career.career_story_progression.quitting
            elif self.story_progression_requirement == CareerStoryProgressionModificationType.RETIRE:
                multipliers = career.career_story_progression.retiring
            if multipliers is not None:
                return multipliers.get_multiplier(resolver)
        return False

class QuittableCareerTestFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'has_quittable_career': Tunable(description='\n            If True then all of the subjects must have a quittable career in \n            order for the test to pass. If False then none of the subjects \n            can have a quittable career in order to pass.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {}

    @caches.cached
    def __call__(self, subjects, targets=None, tooltip=None):
        for subject in subjects:
            if self.has_quittable_career:
                if not any(c.can_quit for c in subject.careers.values()):
                    return TestResult(False, '{0} does not have any quittable careers', subject, tooltip=tooltip)
                    if any(c.can_quit for c in subject.careers.values()):
                        return TestResult(False, '{0} has at least one career that is quittable', subject, tooltip=tooltip)
            elif any(c.can_quit for c in subject.careers.values()):
                return TestResult(False, '{0} has at least one career that is quittable', subject, tooltip=tooltip)
        return TestResult.TRUE

    def goal_value(self):
        return 1

class SpecifiedCareerMixin:
    FACTORY_TUNABLES = {'fallback_to_picker': Tunable(description='\n            If the tuned career is not set, should we expect the career to\n            be passed in via PickedItemIds?\n            ', tunable_type=bool, default=True)}

    @property
    def tuned_career(self):
        raise NotImplementedError

    def get_expected_args(self):
        if self.fallback_to_picker and self.tuned_career is None:
            return {'career_pick': ParticipantType.PickedItemId}
        return {}

    def do_test(self, subjects, career_id, tooltip):
        raise NotImplementedError

    @caches.cached
    def __call__(self, subjects, career_pick=None, targets=None, tooltip=None):
        career_id = None
        if self.tuned_career is None:
            if career_pick:
                career_id = career_pick[0]
        else:
            career_id = self.career.guid64
        return self.do_test(subjects, career_id, tooltip)

    def get_target_id(self, subjects, career_pick=None, targets=None, tooltip=None, id_type=None):
        if not career_pick:
            return
        if id_type == TargetIdTypes.DEFAULT or id_type == TargetIdTypes.DEFINITION:
            return career_pick[0]
        if id_type == TargetIdTypes.INSTANCE:
            for subject in subjects:
                this_career = subject.careers.get(career_pick[0])
                if this_career is not None:
                    return this_career.id
        logger.error('Unique target ID type: {} is not supported for test: {}', id_type, self)

    def goal_value(self):
        return 1
