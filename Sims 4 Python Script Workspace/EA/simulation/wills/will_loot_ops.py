from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from objects.game_object import GameObject
    from sims.sim_info import SimInfo
    from wills.will_service import WillService
    from typing import *from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, Tunable, OptionalTunable, TunableRange, TunablePackSafeReferencefrom wills.will import WillSectionTypeimport servicesimport sims4logger = sims4.log.Logger('WillLootOps', default_owner='madang')
class _WillLootOpBase(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver:'Resolver') -> 'None':
        raise NotImplementedError

class _CreateWill(_WillLootOpBase):

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver) -> 'None':
        will_service.create_will(subject)

class _DestroyWill(_WillLootOpBase):

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver) -> 'None':
        will_service.destroy_sim_will(subject.id)
        will_service.destroy_household_will(subject.household_id)

class _SetWillSelection(_WillLootOpBase):
    FACTORY_TUNABLES = {'section': TunableEnumEntry(description="\n            The section of the subject Sim's will to set.\n            Note: The Notes section of the will cannot be set in this loot, use \n            SetWillNoteImmediateInteraction to handle this directly.\n            ", tunable_type=WillSectionType, default=WillSectionType.BURIAL, invalid_enums=(WillSectionType.NOTE, WillSectionType.EMOTION_AND_NOTE), pack_safe=True), 'percentage': OptionalTunable(description='\n            If enabled, this field will set the desired Simoleon inheritance percentage\n            for a recipient (which includes charity).\n            ', tunable=TunableRange(description='\n                The desired Simoleon percentage.\n                ', tunable_type=float, default=0.0, minimum=0.0, maximum=1.0)), 'emotion_mood': OptionalTunable(description="\n            If enabled, this reference will be used to set the desired mood for the\n            subject Sim's EMOTION section in their will.\n            ", tunable=TunablePackSafeReference(description='\n                The desired mood to set as the Will emotion.\n                ', manager=services.get_instance_manager(sims4.resources.Types.MOOD))), 'funeral_activity': OptionalTunable(description="\n            If enabled, this reference will be used to set the desired SituationActivity\n            for the subject Sim's FUNERAL section in their will.\n            ", tunable=TunablePackSafeReference(description='\n                The desired SituationActivity to set as a Will Funeral Activity \n                preference.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION), class_restrictions=('SituationActivity',))), 'primary_participant': TunableEnumEntry(description='\n            The main participant for this Will selection.  All sections use this\n            participant except for CHARITY, FUNERAL, and EMOTION.\n            ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId), 'additional_participant': OptionalTunable(description='\n            If enabled, this serves as the second participant for certain sections\n            (HEIRLOOM and DEPENDENTS) that require it.\n            ', tunable=TunableEnumEntry(description='\n                The second participant in this interaction.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object))}

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver:'Resolver') -> 'None':
        sim_will = will_service.get_sim_will(subject.id)
        household_will = will_service.get_household_will(subject.household_id)
        if sim_will is None and household_will is None:
            logger.error('Cannot set a will section, {} is missing wills', subject)
            return
        if sim_will is not None:
            if self.section == WillSectionType.BURIAL:
                object_def_id = resolver.get_participant(self.primary_participant)
                if object_def_id:
                    sim_will.set_burial_preference(object_def_id)
            elif self.section == WillSectionType.FUNERAL:
                if self.funeral_activity is None:
                    logger.error('Cannot set FUNERAL section, {} is missing funeral_activity tuning', subject)
                    return
                sim_will.set_funeral_activity_preference(self.funeral_activity.guid64)
            elif self.section == WillSectionType.EMOTION:
                if self.emotion_mood is None:
                    logger.error('Cannot set EMOTION section, {} is missing emotion_mood tuning', subject)
                    return
                sim_will.set_emotion(self.emotion_mood)
            elif self.section == WillSectionType.HEIRLOOM:
                if self.additional_participant is None:
                    logger.error('Cannot set an heirloom recipient without an additional participant')
                    return
                heirloom_obj = resolver.get_participant(self.primary_participant)
                recipient_sim_id = resolver.get_participant(self.additional_participant)
                if heirloom_obj and recipient_sim_id:
                    sim_will.set_heirloom_recipient(heirloom_obj.id, recipient_sim_id)
        if household_will is not None:
            if self.section == WillSectionType.SIMOLEON or self.section == WillSectionType.CHARITY:
                if self.percentage is None:
                    logger.error('Cannot set a simoleon inheritance, no percentage set.')
                    return
                if self.section == WillSectionType.SIMOLEON:
                    household_id = resolver.get_participant(self.primary_participant)
                    if household_id:
                        household_will.set_simoleon_distribution(household_id, self.percentage)
                else:
                    household_will.set_charity_distribution(self.percentage)
            elif self.section == WillSectionType.DEPENDENT:
                if self.additional_participant is None:
                    logger.error('Cannot set an dependent recipient without an additional participant')
                    return
                dependent_sim_id = resolver.get_participant(self.primary_participant)
                recipient_household_id = resolver.get_participant(self.additional_participant)
                if dependent_sim_id is not None and recipient_household_id is not None:
                    household_will.set_dependent_distribution(dependent_sim_id, recipient_household_id)

class _ClearWillSection(_WillLootOpBase):
    FACTORY_TUNABLES = {'section': TunableEnumEntry(description="\n            The section of the subject Sim's will to clear.\n            ", tunable_type=WillSectionType, default=WillSectionType.BURIAL, pack_safe=True)}

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver:'Resolver') -> 'None':
        sim_will = will_service.get_sim_will(subject.id)
        household_will = will_service.get_household_will(subject.household_id)
        if sim_will is None and household_will is None:
            logger.error('Cannot clear a will section, {} is missing wills', subject)
            return
        if sim_will is not None:
            if self.section == WillSectionType.BURIAL:
                sim_will.clear_burial_preference()
            elif self.section == WillSectionType.FUNERAL:
                sim_will.clear_funeral_activity_preferences()
            elif self.section == WillSectionType.EMOTION_AND_NOTE:
                sim_will.clear_note_and_emotion()
            elif self.section == WillSectionType.HEIRLOOM:
                sim_will.clear_heirloom_distributions()
        if household_will is not None:
            if self.section == WillSectionType.DEPENDENT:
                household_will.clear_dependent_distributions()
            elif self.section == WillSectionType.SIMOLEON:
                household_will.clear_simoleon_distributions()

class _ApplyInheritance(_WillLootOpBase):

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver) -> 'None':
        deceased_sim = resolver.get_participant(ParticipantType.StoredSim)
        if deceased_sim is not None:
            will_service.claim_inheritance(deceased_sim, subject)

class _SetBurialUrn(_WillLootOpBase):

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'GameObject', resolver) -> 'None':
        sim_will = will_service.get_sim_will(subject.id)
        burial_def_id = sim_will.get_burial_preference()
        if burial_def_id:
            target.set_definition(burial_def_id)

class _WillNotification(_WillLootOpBase):
    FACTORY_TUNABLES = {'review': Tunable(description="\n            If checked, generate a TNS for the subject Sim to review their own will.\n            Otherwise, generate a TNS for the subject Sim, who is a will recipient, to \n            read a deceased Sim's will.\n            ", tunable_type=bool, default=True)}

    def __call__(self, will_service:'WillService', subject:'SimInfo', target:'None', resolver) -> 'None':
        if self.review:
            will_service.show_will_contents_notification(subject)
        else:
            deceased_sim_info = resolver.get_participant(ParticipantType.StoredSim)
            if deceased_sim_info is not None:
                will_service.show_will_contents_notification(deceased_sim_info)

class WillLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'operation': TunableVariant(description='\n            Will related operation to perform.\n            ', create_will=_CreateWill.TunableFactory(), destroy_will=_DestroyWill.TunableFactory(), set_will_selection=_SetWillSelection.TunableFactory(), clear_will_section=_ClearWillSection.TunableFactory(), apply_inheritance=_ApplyInheritance.TunableFactory(), set_burial_urn=_SetBurialUrn.TunableFactory(), will_notification=_WillNotification.TunableFactory(), default='create_will')}

    def __init__(self, operation, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self.operation = operation

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'GameObject', resolver:'Resolver') -> 'None':
        will_service = services.get_will_service()
        if will_service is None:
            return
        self.operation(will_service, subject, target, resolver)
