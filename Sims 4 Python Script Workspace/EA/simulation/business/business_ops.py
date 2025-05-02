from __future__ import annotationsfrom business.business_enums import BusinessTypefrom business.business_rule_enums import BusinessRuleStatefrom business.business_zone_director_mixin import CustomerAndEmployeeZoneDirectorMixinfrom interactions import ParticipantType, ParticipantTypeZoneId, ParticipantTypeSingleSimfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableReference, TunableFactory, TunableVariant, TunableTuple, TunableEnumFlags, TunableSimMinutefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from business.business_rule import BusinessRule
    from event_testing.resolver import Resolverimport servicesimport sims4import singletonslogger = sims4.log.Logger('Business Loot', default_owner='bzhu')
class ModifyCustomerFlow(BaseLootOperation):
    FACTORY_TUNABLES = {'allow_customers': Tunable(description='\n            If checked then set the current business, if there is one active,\n            to allow for customers to arrive.\n            \n            If unchecked then set the current business, if there is one active,\n            to disallow customers from arriving.\n            ', tunable_type=bool, default=True), 'locked_args': {'subject': None}}

    def __init__(self, *args, allow_customers=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._allow_customers = allow_customers

    def _apply_to_subject_and_target(self, subject, target, resolver):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return
        zone_director = services.venue_service().get_zone_director()
        if zone_director is None:
            return
        if not isinstance(zone_director, CustomerAndEmployeeZoneDirectorMixin):
            return
        zone_director.set_customers_allowed(self._allow_customers)

class SetBusinessRuleComplianceState(BaseLootOperation):
    RULE_REFERENCE = 0
    RULE_PARTICIPANT = 1
    FACTORY_TUNABLES = {'state': TunableEnumEntry(description='\n            The compliance state you want to set the rule to.\n            ', tunable_type=BusinessRuleState, default=BusinessRuleState.ENABLED), 'override_rule_cooldown': TunableVariant(description="\n            A cooldown override applied to the rule. If the rule is set to broken, rule will be auto-resolved \n            after cooldown time. If rule is set to enabled, rule violation won't be checked again during cooldown time.\n            If rule is set to disabled, nothing will happen.\n            ", use_custom_cooldown=TunableSimMinute(default=360, minimum=1), default='use_default_cooldown', locked_args={'apply_no_cooldown': 0, 'use_default_cooldown': singletons.DEFAULT})}

    def __init__(self, rule:'BusinessRule', state:'BusinessRuleState', override_rule_cooldown:'int', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self.rule = rule
        self.state = state
        self.override_rule_cooldown = override_rule_cooldown

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), description='The business zone that the rule state change is applied to.', participant_type_enum=ParticipantTypeZoneId, default_participant=ParticipantTypeZoneId.PickedZoneId, **kwargs)

    @TunableFactory.factory_option
    def business_rule_options(pack_safe:'bool'=True) -> 'Dict[str, Tunable]':
        return {'rule': TunableVariant(description='\n                The rule subject.\n                ', rule_reference=TunableTuple(description='\n                    Reference to the rule.\n                    ', reference=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUSINESS_RULE), pack_safe=pack_safe), locked_args={'id_type': SetBusinessRuleComplianceState.RULE_REFERENCE}), participant_type=TunableTuple(description='\n                    The id of rule the loot will be applied to. Participant must have the rule. \n                    Typically should be PickedItemId if this loot is being applied by the continuation of a\n                    BusinessRulePickerInteraction.\n                    ', participant=TunableEnumFlags(enum_type=ParticipantType, default=ParticipantType.PickedItemId), locked_args={'id_type': SetBusinessRuleComplianceState.RULE_PARTICIPANT}), default='rule_reference')}

    def _get_rule_id(self, resolver:'Resolver') -> 'int':
        if self.rule.id_type == SetBusinessRuleComplianceState.RULE_REFERENCE:
            rule_id = self.rule.reference.guid64
        elif self.rule.id_type == SetBusinessRuleComplianceState.RULE_PARTICIPANT:
            rule_ids = resolver.get_participants(self.rule.participant)
            rule_id = rule_ids[0] if len(rule_ids) > 0 else None
        return rule_id

    def _apply_to_subject_and_target(self, subject:'int', target:'None', resolver:'None') -> 'None':
        rule_id = self._get_rule_id(resolver)
        if rule_id is None:
            logger.error('There is no rule to apply rule state change operation to.')
            return
        if subject is not None:
            business_manager = services.business_service().get_business_manager_for_zone(zone_id=subject)
            if business_manager is not None:
                if business_manager.has_rules:
                    business_manager.set_rule_state(rule_id, self.state, override_rule_cooldown_time=self.override_rule_cooldown)
            else:
                logger.error('There is no business associated with participant {}.', subject)

class SetRentArrearsLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'is_overdue': Tunable(description='\n            If enabled, set the overdue rent amount on the rental unit to the appropriate\n            amount (based on their current rent and overdue duration).  If not enabled,\n            then clear the overdue rent amount.\n            ', tunable_type=bool, default=False)}

    def __init__(self, is_overdue:'bool', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self.is_overdue = is_overdue

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), description='The business zone that the rent arrears is applied to.', participant_type_enum=ParticipantTypeZoneId, default_participant=ParticipantTypeZoneId.PickedZoneId, **kwargs)

    def _apply_to_subject_and_target(self, subject:'int', target:'None', resolver:'None') -> 'None':
        if subject is None:
            logger.error('There is no Rental Unit zone to apply the set overdue rent operation.')
            return
        rental_unit_manager = services.business_service().get_business_manager_for_zone(subject)
        if rental_unit_manager is not None and rental_unit_manager.business_type == BusinessType.RENTAL_UNIT:
            if self.is_overdue:
                rental_unit_manager.make_rent_overdue()
            else:
                rental_unit_manager.clear_all_rent()
