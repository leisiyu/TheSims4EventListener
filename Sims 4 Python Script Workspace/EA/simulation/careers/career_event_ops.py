from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from careers.career_event import CareerEvent
    from event_testing.resolver import Resolver
    from typing import *from interactions import ParticipantTypeSingleSimfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, TunableFactory, HasTunableSingletonFactory, AutoFactoryInitfrom singletons import DEFAULTimport servicesimport sims4.loglogger = sims4.log.Logger('CareerEventOps')
class CareerEventLootOp(BaseLootOperation):

    class _CareerEventLootOpBase(HasTunableSingletonFactory, AutoFactoryInit):

        def perform(self, resolver:'Resolver', career_event:'CareerEvent') -> 'Optional[str]':
            raise NotImplementedError

    class _MakeSimTemporary(_CareerEventLootOpBase):
        FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n                The sim to make temporary.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

        def perform(self, resolver:'Resolver', career_event:'CareerEvent') -> 'Optional[str]':
            participant = resolver.get_participant(self.subject)
            if participant is None:
                return 'Make Sim Temporary failed to find valid participant: {}'.format(self.subject)
            career_event.make_sim_temporary(participant)

    FACTORY_TUNABLES = {'operation_type': TunableVariant(description='\n            The type of career event operation to perform.\n            ', make_sim_temporary=_MakeSimTemporary.TunableFactory(), default='make_sim_temporary')}

    def __init__(self, operation_type:'_CareerEventLootOpBase', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._operation_type = operation_type

    @TunableFactory.factory_option
    def subject_participant_type_options(description:'Optional[str]'=DEFAULT, **kwargs) -> 'Dict[str, Optional[TunableEnumEntry]]':
        return {}

    def _apply_to_subject_and_target(self, subject:'None', target:'None', resolver:'Resolver') -> 'None':
        career = services.get_career_service().get_career_in_career_event()
        if career is None:
            logger.error('Career event Op {} called when there is no career event occurring', self)
            return
        career_event = career.career_event_manager.get_top_career_event()
        if career_event is None:
            logger.error('Career event Op {} called when there is no career event occurring', self)
            return
        error_string = self._operation_type.perform(resolver, career_event)
        if error_string:
            logger.error('Career event Op {} failed due to: {}', self, error_string)
