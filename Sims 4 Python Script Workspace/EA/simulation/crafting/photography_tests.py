from event_testing.resolver import SingleActorAndObjectResolver, PhotoResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInitfrom caches import cached_testimport event_testing
class TookPhotoTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.PhotoTaken,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'tests': TunableTestSet(description='\n            A set of tests that are run with the photographer as the actor,\n            and the photograph as the object and PhotographyTargets as the\n            subjects.\n            ')}

    def get_expected_args(self):
        return {'subject': ParticipantType.Actor, 'photo_object': event_testing.test_constants.FROM_EVENT_DATA, 'photo_targets': event_testing.test_constants.FROM_EVENT_DATA, 'res_key': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, photo_object=None, subject=None, photo_targets=None, res_key=None):
        subject = next(iter(subject), None) if subject is not None else None
        resolver = PhotoResolver(subject, photo_object, photo_targets, res_key, source=self)
        return self.tests.run_tests(resolver)
