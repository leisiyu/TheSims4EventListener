from __future__ import annotationsfrom business.business_enums import BusinessTypefrom business.business_rule_enums import BusinessRuleStatefrom business.business_tests import BusinessManagerFinderVariantfrom interactions import ParticipantTypefrom interactions.base.picker_interaction import PickerSingleChoiceSuperInteractionfrom interactions.utils.tunable import TunableContinuationfrom multi_unit.rental_unit_manager import RentalUnitManagerfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableEnumEntry, Tunable, TunableEnumSet, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import ObjectPickerRowfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.context import InteractionContext
    from objects.game_object import GameObject
    from business.business_rule import BusinessRule
    from scheduling import Timelineimport servicesimport sims4logger = sims4.log.Logger('Business Rules interaction', default_owner='bzhu')
class BusinessRulePickerSuperInteraction(PickerSingleChoiceSuperInteraction):
    INSTANCE_TUNABLES = {'continuation': TunableContinuation(description='\n            If enabled, you can tune a continuation to be pushed. PickedItemId\n            will be the id of the selected rule.\n            ', tuning_group=GroupNames.PICKERTUNING), 'business_rule_target': TunableEnumEntry(description='\n            The target of this interaction whose business unit will be used to generate \n            rule data.  For Property Owner fine interactions, this should be set to \n            either ActorTenantHouseholds or PickedZoneId (the current zone).\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor, tuning_group=GroupNames.PICKERTUNING), 'rule_states': TunableEnumSet(description='\n            Business rules in this state set will show up in the picker.\n            ', enum_type=BusinessRuleState, enum_default=BusinessRuleState.ENABLED, invalid_enums=(BusinessRuleState.DISABLED,), tuning_group=GroupNames.PICKERTUNING), 'generate_property_owner_rule_fines': Tunable(description="\n            If checked, generate choices representing fines for the desired rules for \n            either the current rental zone or all of the active Property Owner's rental \n            units.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'property_owner_rule_fine_picker_row_name': OptionalTunable(description='\n            If enabled, use this name in the Picker Row to display the fines for each \n            affected tenant household.  Otherwise, the Business Rule name will be used.\n            Tokens:\n            {0.String} Rule Name\n            {1.String} Rule Fine\n            {2.String} Tenant Household Name\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def get_single_choice_and_row(cls, inst, context:'InteractionContext', target:'GameObject', **kwargs) -> 'Tuple[BusinessRule, ObjectPickerRow]':
        inst_or_cls = inst if inst is not None else cls
        first_rule = None
        first_row = None
        for rule in inst_or_cls._valid_business_rules_gen(target, context):
            if first_rule is not None and first_row is not None:
                return (None, None)
            row = inst_or_cls.create_row(rule)
            first_rule = rule
            first_row = row
        return (first_rule, first_row)

    @flexmethod
    def create_row(cls, inst, rule:'BusinessRule', select_default=False) -> 'ObjectPickerRow':
        inst_or_cls = inst if inst is not None else cls
        display_name = rule.rule_name
        if inst_or_cls.property_owner_rule_fine_picker_row_name:
            household = services.household_manager().get(rule.household_id)
            if household is not None:
                display_name = inst_or_cls.property_owner_rule_fine_picker_row_name(rule.rule_name, str(rule.fine), household.name)
        return ObjectPickerRow(name=display_name, row_description=rule.rule_description, tag=rule)

    @flexmethod
    def _valid_business_rules_gen(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'None':
        inst_or_cls = inst if inst is not None else cls
        business_rule_target = inst_or_cls.business_rule_target
        target_sim = None
        if not inst_or_cls.generate_property_owner_rule_fines:
            if business_rule_target == ParticipantType.Actor:
                target_sim = context.sim
            elif business_rule_target == ParticipantType.TargetSim:
                target_sim = target
            if target_sim is None or not target_sim.is_sim:
                logger.error('The target {} for rule interaction is invalid', business_rule_target.name)
                return
            target_zone_id = target_sim.sim_info.household.home_zone_id
            business_manager = services.business_service().get_business_manager_for_zone(target_zone_id)
            if business_manager is not None and business_manager.has_rules:
                yield from business_manager.get_rules_by_states(*inst_or_cls.rule_states)
        else:
            business_managers = []
            if business_rule_target == ParticipantType.ActorTenantHouseholds:
                household_id = services.active_household_id()
                business_tracker = services.business_service().get_business_tracker_for_household(household_id, BusinessType.RENTAL_UNIT)
                if business_tracker.business_managers:
                    business_managers = business_tracker.business_managers.values()
            elif business_rule_target == ParticipantType.PickedZoneId:
                current_zone_id = services.current_zone_id()
                business_manager = services.business_service().get_business_manager_for_zone(current_zone_id)
                if business_manager.has_rules:
                    business_managers = [business_manager]
            if not business_managers:
                return
            for business_manager in business_managers:
                if business_manager.has_rules:
                    yield from business_manager.get_rules_by_states(*inst_or_cls.rule_states)

    @flexmethod
    def picker_rows_gen(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'None':
        inst_or_cls = inst if inst is not None else cls
        for business_rule in inst_or_cls._valid_business_rules_gen(target, context):
            yield inst_or_cls.create_row(business_rule)

    def _run_interaction_gen(self, timeline:'Timeline') -> 'bool':
        picked_item_ids = self.interaction_parameters.get('picked_item_ids')
        if picked_item_ids is None:
            return False
        picked_item_set = set()
        picked_zone_id_set = set()
        for picked_item_id in picked_item_ids:
            picked_item_set.add(picked_item_id.guid64)
            picked_zone_id_set.add(picked_item_id.zone_id)
        self.push_tunable_continuation(self.continuation, picked_item_ids=picked_item_set, picked_zone_ids=picked_zone_id_set)
        return True

    def on_choice_selected(self, choice_tag:'BusinessRule', **kwargs) -> 'None':
        rule = choice_tag
        if rule is not None:
            picked_item_set = frozenset({rule.guid64})
            picked_zone_id_set = frozenset({rule.zone_id})
            self.interaction_parameters['picked_item_ids'] = picked_item_set
            self.interaction_parameters['picked_zone_ids'] = picked_zone_id_set
            self.push_tunable_continuation(self.continuation, picked_item_ids=picked_item_set, picked_zone_ids=picked_zone_id_set)

class RentArrearsPickerSuperInteraction(PickerSingleChoiceSuperInteraction):
    INSTANCE_TUNABLES = {'continuation': TunableContinuation(description='\n            If enabled, you can tune a continuation to be pushed. PickedZoneId will be\n            the zone id of the selected rental unit where we want to handle the overrdue \n            rent.\n            ', tuning_group=GroupNames.PICKERTUNING), 'rent_arrears_target': BusinessManagerFinderVariant(description='\n            The target of this interaction whose business unit will be used to generate \n            rent arrears.\n            ', allow_multiples=True, tuning_group=GroupNames.PICKERTUNING), 'rent_arrears_picker_row_name': TunableLocalizedStringFactory(description='\n            Use this name in the Picker Row to display the rent arrears for each \n            affected tenant household.\n            Tokens:\n            {0.String} Rent amount\n            {1.String} Tenant Household Name\n            ', tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def get_single_choice_and_row(cls, inst, context:'InteractionContext', target:'GameObject', **kwargs) -> 'Tuple[RentalUnitManager, ObjectPickerRow]':
        inst_or_cls = inst if inst is not None else cls
        first_manager = None
        first_row = None
        for manager in inst_or_cls._valid_rental_unit_manager_gen(target, context):
            if first_manager is not None and first_row is not None:
                return (None, None)
            row = inst_or_cls.create_row(manager)
            first_manager = manager
            first_row = row
        return (first_manager, first_row)

    @flexmethod
    def create_row(cls, inst, manager:'RentalUnitManager') -> 'ObjectPickerRow':
        inst_or_cls = inst if inst is not None else cls
        row_name = ''
        household = services.household_manager().get_by_home_zone_id(manager.business_zone_id)
        if household is not None:
            row_name = inst_or_cls.rent_arrears_picker_row_name(str(manager.overdue_rent), household.name)
        return ObjectPickerRow(name=row_name, row_description=row_name, tag=manager)

    @flexmethod
    def _valid_rental_unit_manager_gen(cls, inst, target:'GameObject', context:'InteractionContext') -> 'None':
        inst_or_cls = inst if inst is not None else cls
        participant = inst_or_cls.rent_arrears_target.participant
        participant_targets = inst_or_cls.get_participants(participant_type=participant, sim=context.sim, target=target)
        rental_unit_managers = inst_or_cls.rent_arrears_target.get_business_managers(list(participant_targets))
        if not rental_unit_managers:
            return
        for manager in rental_unit_managers:
            if manager.business_type == BusinessType.RENTAL_UNIT and manager.overdue_rent > 0:
                yield manager

    @flexmethod
    def picker_rows_gen(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'None':
        inst_or_cls = inst if inst is not None else cls
        for manager in inst_or_cls._valid_rental_unit_manager_gen(target, context):
            yield inst_or_cls.create_row(manager)

    def _run_interaction_gen(self, timeline:'Timeline') -> 'bool':
        self._show_picker_dialog(self.sim, target_sim=self.target)
        return True

    def on_choice_selected(self, choice_tag:'RentalUnitManager', **kwargs) -> 'None':
        rental_unit_manager = choice_tag
        if rental_unit_manager is not None:
            picked_item_set = set()
            picked_item_set.add(rental_unit_manager.business_zone_id)
            self.interaction_parameters['picked_zone_ids'] = picked_item_set
            self.push_tunable_continuation(self.continuation, picked_item_ids=picked_item_set)
