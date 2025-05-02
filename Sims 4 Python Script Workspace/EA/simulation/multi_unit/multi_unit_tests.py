from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.results import TestResult
    from interactions import ParticipantType
    from typing import *
    from sims4.localization import TunableLocalizedStringFactory
    from sims.sim_info import SimInfofrom business.business_enums import BusinessTypefrom interactions import ParticipantTypefrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom sims4.common import is_available_pack, Packfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, TunableEnumEntry, Tunable, OptionalTunablefrom zone_tests import ActiveZone, PickInfoZone, PickedZoneIds, ParticipantHomeZoneimport services
class _IsTenantTest(HasTunableSingletonFactory):

    def __call__(self, subjects:'List[SimInfo]', zone_id:'Optional[int]', tooltip:'TunableLocalizedStringFactory'=None) -> 'TestResult':
        business_service = services.business_service()
        for subject in subjects:
            if subject is None:
                return TestResult(False, 'Subject is none and cannot be.', tooltip=tooltip)
            home_zone_id = subject.household.home_zone_id
            if zone_id is not None and home_zone_id != zone_id:
                return TestResult(False, 'Sim {} is not a tenant of zone {}.', subject, zone_id, tooltip=tooltip)
            business_manager = business_service.get_business_manager_for_zone(home_zone_id)
            is_multi_unit_tenant = business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT
            if not is_multi_unit_tenant:
                return TestResult(False, 'Sim {} is not a tenant.', subject, tooltip=tooltip)
        return TestResult.TRUE

class _IsPropertyOwnerTest(HasTunableSingletonFactory):

    def __call__(self, subjects:'List[SimInfo]', zone_id:'Optional[int]', tooltip:'TunableLocalizedStringFactory'=None) -> 'TestResult':
        business_service = services.business_service()
        for subject in subjects:
            if subject is None:
                return TestResult(False, 'Subject is none and cannot be.', tooltip=tooltip)
            business_tracker = business_service.get_business_tracker_for_household(subject.household.id, BusinessType.RENTAL_UNIT)
            if business_tracker is None:
                return TestResult(False, 'Sim {} is not a property owner.', subject, tooltip=tooltip)
            if zone_id is not None:
                for business_zone_id in business_tracker.business_managers.keys():
                    if business_zone_id == zone_id:
                        break
                return TestResult(False, 'Sim {} is not a property owner of zone {}.', subject, zone_id, tooltip=tooltip)
        return TestResult.TRUE

class MultiUnitRoleTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'role_to_check': TunableVariant(description='\n            The role against which to verify the subject sim.\n            ', is_tenant=_IsTenantTest.TunableFactory(), is_property_owner=_IsPropertyOwnerTest.TunableFactory(), default='is_tenant'), 'subject': TunableEnumEntry(description='\n            Who to apply this test to*. Tune lot_source to use a zone as the subject. \n            \n            * Specifically, subject.household.home_zone_id\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'multi_units_unavailable_result': Tunable(description='\n            Result to return if multi units are unavailable.\n            ', tunable_type=bool, default=False), 'invert': Tunable(description="\n            If checked, this test will return the opposite of what it's tuned to\n            return.\n            ", tunable_type=bool, default=False), 'lot_source': OptionalTunable(description='\n            If specified, the role test will validate against the tuned zone.\n            ', tunable=TunableVariant(description='\n                Which Lot we want to test.\n                ', use_current_zone=ActiveZone.TunableFactory(), use_pick_info=PickInfoZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), use_participant_home_zone=ParticipantHomeZone.TunableFactory(), default='use_current_zone'))}

    def get_expected_args(self) -> 'Dict[str, ParticipantType]':
        args = {'subjects': self.subject}
        if self.lot_source is not None:
            args.update(self.lot_source.get_expected_args())
        return args

    def __call__(self, subjects:'List[SimInfo]', **kwargs) -> 'TestResult':
        if not is_available_pack(Pack.EP15):
            if self.multi_units_unavailable_result:
                return TestResult.TRUE
            return TestResult(False, 'EP15 Pack is not installed.', tooltip=self.tooltip)
        else:
            kwargs.update({'subjects': subjects})
            zone_id = None if self.lot_source is None else self.lot_source.get_zone_id(**kwargs)
            test_result = self.role_to_check(subjects, zone_id, self.tooltip)
            if test_result:
                if self.invert:
                    return TestResult(False, test_result.reason, tooltip=self.tooltip)
                return test_result
            elif self.invert:
                return TestResult.TRUE
        return test_result
        if self.invert:
            return TestResult.TRUE
        return test_result
