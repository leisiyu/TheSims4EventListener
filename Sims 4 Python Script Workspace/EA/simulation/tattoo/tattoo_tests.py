import event_testingimport servicesimport sims4from cas.cas import get_caspart_bodytypefrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom interactions import ParticipantTypeSingle, ParticipantTypefrom relationships.relationship_tests import MIN_RELATIONSHIP_VALUE, MAX_RELATIONSHIP_VALUEfrom sims.outfits.outfit_enums import BodyTypefrom sims4.math import Operatorfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, OptionalTunable, TunableTuple, TunableOperator, TunableList, TunableVariant, TunableThreshold, TunableReference, TunableInterval, Tunablefrom tattoo.tattoo_tuning import TattooQuality, TattooSentimentType
class TattoHasFreeSlotTestMixin:

    def test(self, sim, body_type, tooltip) -> TestResult:
        tattoo_tracker = sim.tattoo_tracker
        if tattoo_tracker is None:
            return TestResult(False, 'Tested {} has no tattoo_tracker', sim, tooltip=tooltip)
        result = None
        if body_type is not None:
            result = tattoo_tracker.has_free_layer_in_bodytype(body_type)
        else:
            result = tattoo_tracker.has_free_layer()
        if not result:
            return TestResult(False, 'Tested {} has no free slot in {}', sim, body_type, tooltip=tooltip)
        return TestResult.TRUE

class TattooHasFreeSlotTest(TattoHasFreeSlotTestMixin, HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Returns True if:\n                * body_type not defined -> Is there any free slot\n                * body_type defined -> Is there any free slot in the defined body_parts\n            ', 'subject': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'body_type': OptionalTunable(description='\n            If enabled, checks there is a free slot in the defined body_part\n            ', tunable=TunableEnumEntry(description='\n                Body part to check against\n                ', tunable_type=BodyType, default=BodyType.TATTOO_ARM_LOWER_LEFT))}

    def get_expected_args(self):
        return {'subject': self.subject}

    def _evaluate(self, tooltip=None, subject=(), target=()):
        sim = next(iter(subject), None)
        return self.test(sim=sim, body_type=self.body_type, tooltip=tooltip)

class TattooHasFreeSlotParticipantBodyTypeTest(TattoHasFreeSlotTestMixin, HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Returns true if defined subject has a free slot in the same body type as the defined participant\n            ', 'subject': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'participant_body_type': TunableEnumEntry(description='\n            Participant to get the body type from\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.participant_body_type}

    def _evaluate(self, tooltip=None, subject=(), target=()):
        sim = next(iter(subject), None)
        participant = next(iter(target), None)
        body_type = get_caspart_bodytype(participant)
        return self.test(sim=sim, body_type=body_type, tooltip=tooltip)

class TattooDataTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Checks tattoo data from defined body types\n            ', 'subject': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'body_types': TunableList(description='\n            Body parts to check against. If empty, will check in each tattoo slot\n            ', tunable=TunableEnumEntry(tunable_type=BodyType, default=BodyType.TATTOO_ARM_LOWER_LEFT)), 'quality': OptionalTunable(description='\n            If defined, checks if the tattoo quality is within defined values\n            ', tunable=TunableTuple(quality=TunableEnumEntry(tunable_type=TattooQuality, default=TattooQuality.NONE), comparison=TunableOperator(description='The type of comparison to perform.', default=Operator.GREATER))), 'sentiment_type': OptionalTunable(description='\n            If defined, checks if the tattoo sentiment type is within the defined values\n            ', tunable=TunableEnumEntry(tunable_type=TattooSentimentType, default=TattooSentimentType.NONE)), 'sentimental_target': OptionalTunable(description='\n            If defined, will count the tattoos:\n                If TARGET_COMPARISON is EQUAL, tattoos that have the same sentimental target as the defined participant\n                If TARGET_COMPARISON is NOT_EQUAL, tattoos have a different sentimental target as the defined participant\n            ', tunable=TunableTuple(target_participant=TunableEnumEntry(description='\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), target_comparison=TunableOperator(description='\n                    ', default=Operator.EQUAL, invalid_enums=(Operator.GREATER, Operator.GREATER_OR_EQUAL, Operator.LESS, Operator.LESS_OR_EQUAL)))), 'relationship': OptionalTunable(description='\n            If set, the test will use the relationship score between dedicated sims and relationship_target for defined track\n            ', tunable=TunableTuple(track=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack', allow_none=True, pack_safe=True), relationship_score_interval=TunableInterval(tunable_type=float, default_lower=MIN_RELATIONSHIP_VALUE, default_upper=MAX_RELATIONSHIP_VALUE, minimum=MIN_RELATIONSHIP_VALUE, maximum=MAX_RELATIONSHIP_VALUE), relationship_target=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor))), 'check_is_dead': Tunable(description='\n            If defined, will check if the tattoos are dedicated to a dead sim\n            ', tunable_type=bool, default=False), 'invert': Tunable(description='If true, invert the result of this test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        args = {'subject': self.subject}
        if self.relationship is not None:
            args['relationship_target'] = self.relationship.relationship_target
        if self.sentimental_target is not None:
            args['sentimental_target'] = self.sentimental_target.target_participant
        return args

    def _get_result(self, result:bool, sim, tooltip) -> TestResult:
        if self.invert:
            result = not result
        if result:
            return TestResult.TRUE
        else:
            return TestResult(False, "{0}'s tattoos didn't meet the specified criteria", sim, tooltip=tooltip)

    def _get_dedicated_sims(self, tattoos_data:list()) -> set():
        dedicated_sim_ids = set()
        non_dedicated_tattoo_data = list()
        for tattoo_data in tattoos_data:
            if tattoo_data.sentimental_target:
                dedicated_sim_ids.add(tattoo_data.sentimental_target)
            else:
                non_dedicated_tattoo_data.append(tattoo_data)
        return (dedicated_sim_ids, non_dedicated_tattoo_data)

    def _filter_dead(self, sim_ids:list()) -> bool:
        result = set()
        for sim_id in sim_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if not sim_info is None:
                if sim_info.is_dead:
                    result.add(sim_id)
            result.add(sim_id)
        return result

    def _filter_relationship(self, sim_ids:list(), relationship_target) -> set():
        result = set()
        rel_tracker = relationship_target.relationship_tracker
        for dedicated_sim in sim_ids:
            rel_score = rel_tracker.get_relationship_score(dedicated_sim, self.relationship.track)
            if rel_score is not None and self.relationship.relationship_score_interval.lower_bound <= rel_score and rel_score <= self.relationship.relationship_score_interval.upper_bound:
                result.add(dedicated_sim)
        return result

    def _evaluate(self, tooltip=None, subject=(), relationship_target=(), sentimental_target=()):
        sim = next(iter(subject), None)
        relationship_target = next(iter(relationship_target), None)
        sentimental_target = next(iter(sentimental_target), None)
        tattoo_tracker = sim.tattoo_tracker
        if tattoo_tracker is None:
            return self._get_result(False, sim, tooltip)
        quality = None
        quality_comparison = None
        if self.quality:
            quality = self.quality.quality
            quality_comparison = self.quality.comparison
        target_sim_id = sentimental_target.id if sentimental_target is not None else None
        target_comparison = self.sentimental_target.target_comparison if self.sentimental_target is not None else None
        result = tattoo_tracker.get_filtered_tattoo_data(self.body_types, quality, quality_comparison, self.sentiment_type, target_sim_id, target_comparison)
        if not result:
            return self._get_result(False, sim, tooltip)
        (dedicated_sims, non_dedicated_tattoo_data) = self._get_dedicated_sims(result)
        if non_dedicated_tattoo_data and (self.sentiment_type is None and self.relationship is None) and (self.check_is_dead or self.sentimental_target is None):
            return self._get_result(True, sim, tooltip)
        if not dedicated_sims:
            return self._get_result(False, sim, tooltip)
        if self.check_is_dead:
            dedicated_sims = self._filter_dead(dedicated_sims)
        if self.relationship is not None:
            dedicated_sims = self._filter_relationship(dedicated_sims, relationship_target)
        if not dedicated_sims:
            return self._get_result(False, sim, tooltip)
        return self._get_result(True, sim, tooltip)

class TattooSentimentalTattoosTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'sentiment_type': TunableEnumEntry(description='\n            Sentiment type to check.\n            ', tunable_type=TattooSentimentType, default=TattooSentimentType.NONE), 'value_threshold': TunableThreshold(description='\n            Sentimental tattoos amount required to pass\n            '), 'subject': TunableEnumEntry(description='\n            Participant wearing the tattoos.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': OptionalTunable(description='\n            If defined, will count the tattoos:\n                If TARGET_COMPARISON is EQUAL, tattoos that have the same sentimental target as the defined participant\n                If TARGET_COMPARISON is NOT_EQUAL, tattoos have a different sentimental target as the defined participant\n            ', tunable=TunableTuple(target_participant=TunableEnumEntry(description='\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), target_comparison=TunableOperator(description='\n                    ', default=Operator.EQUAL, invalid_enums=(Operator.GREATER, Operator.GREATER_OR_EQUAL, Operator.LESS, Operator.LESS_OR_EQUAL))))}

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.target.target_participant if self.target is not None else None}

    def _evaluate(self, subject=(), target=(), *args, **kwargs):
        subject = next(iter(subject), None)
        target = next(iter(target), None)
        target_sim_id = target.id if target is not None else None
        target_comparison = self.target.target_comparison if self.target is not None else None
        sim_ids = subject.tattoo_tracker.get_sentimental_tattoo_sims(self.sentiment_type, target_sim_id, target_comparison)
        if self.value_threshold.compare(len(sim_ids)):
            return TestResult.TRUE
        return TestResult(False, 'Sentimental tattoos type {} value does not pass the value threshold.', self.sentiment_type, tooltip=self.tooltip)

class TattooTests(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'test_type': TunableVariant(description='\n            The type of tatoo test to run.\n            ', tattooing_has_free_slot=TattooHasFreeSlotTest.TunableFactory(), tattooing_has_free_slot_participant_body_type=TattooHasFreeSlotParticipantBodyTypeTest.TunableFactory(), tattooing_data=TattooDataTest.TunableFactory(), tattooing_sentimental_tattoos=TattooSentimentalTattoosTest.TunableFactory())}

    def get_expected_args(self):
        return self.test_type.get_expected_args()

    def __call__(self, *args, **kwargs):
        return self.test_type._evaluate(*args, tooltip=self.tooltip, **kwargs)
