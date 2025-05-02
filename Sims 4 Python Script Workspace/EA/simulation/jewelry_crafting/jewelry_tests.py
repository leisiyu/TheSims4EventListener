from __future__ import annotationsfrom objects.components.types import JEWELRY_COMPONENTfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfo
    from sims4.tuning.instances import HashedTunedInstanceMetaclassfrom event_testing.test_base import BaseTestfrom event_testing.results import TestResultfrom interactions import ParticipantTypeSingle, ParticipantTypefrom sims.outfits.outfit_enums import BodyTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, OptionalTunable, TunableList
class EquippedJewelryTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Returns True if:\n                * Target not defined, BodyParts not defined -> There sim has anything equipped\n                * Target defined, BodyParts not defined -> Target is equipped in any body part\n                * Target not defined, BodyParts not defined -> The sim anything equipped in defined body parts\n                * Target defined, BodyParts defined -> Target is equipped in specific body parts\n            ', 'subject': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'target': OptionalTunable(tunable=TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Object)), 'body_parts': OptionalTunable(description="\n            If enabled, checks that the given object's body part is in the list\n            ", tunable=TunableList(description='\n                ', tunable=TunableEnumEntry(description='\n                    List of body parts to check against\n                    ', tunable_type=BodyType, default=BodyType.ACNE)))}

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.target}

    def __call__(self, subject:'Tuple[SimInfo]', target:'Tuple[HashedTunedInstanceMetaclass]') -> 'TestResult':
        sim = next(iter(subject), None)
        obj = next(iter(target), None)
        obj_id = obj.id if obj is not None else None
        if self.target is not None:
            jewelry_component = obj.get_component(JEWELRY_COMPONENT)
            if jewelry_component is None:
                return TestResult(False, 'Tested {} has no jewelry_component', obj, tooltip=self.tooltip)
        jewelry_tracker = sim.jewelry_tracker
        if jewelry_tracker is None:
            return TestResult(False, 'Tested {} has no jewelry_tracker', sim, tooltip=self.tooltip)
        result = jewelry_tracker.jewel_equipped_test(obj_id, self.body_parts)
        if not result:
            return TestResult(False, 'Tested {} is not equipped in current outfit', sim, tooltip=self.tooltip)
        return TestResult.TRUE
