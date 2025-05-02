import event_testing.test_baseimport servicesfrom event_testing.results import TestResultfrom sims4.tuning.tunable import Tunable, AutoFactoryInit, HasTunableSingletonFactory
class LaundryHeroObjectTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'invert': Tunable(description="\n            If unchecked, test will pass if we have SP13 and hero object exists.\n            If checked, test will pass if we don't have SP13 or hero object doesn't exist.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {}

    def __call__(self):
        laundry_service = services.get_laundry_service()
        if laundry_service is None:
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, 'Laundry service not available.', tooltip=self.tooltip)
        if laundry_service.hero_object_exist:
            if self.invert:
                return TestResult(False, 'Laundry hero object exists, but test has Invert checked.', tooltip=self.tooltip)
            return TestResult.TRUE
        elif self.invert:
            return TestResult.TRUE
        else:
            return TestResult(False, "Laundry hero object doesn't exist.", tooltip=self.tooltip)
