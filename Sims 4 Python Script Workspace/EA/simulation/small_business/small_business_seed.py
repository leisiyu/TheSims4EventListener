from __future__ import annotationsfrom business.business_tuning import BusinessTuningfrom clubs import UnavailableClubCriteriaErrorfrom clubs.club_enums import ClubRuleEncouragementStatusfrom protocolbuffers import Business_pb2from business.business_enums import BusinessType, BusinessOriginTelemetryContext, SmallBusinessAttendanceSaleModefrom clubs.club_tuning import ClubRuleCriteriaSkill, ClubRuleCriteriaTrait, ClubRuleCriteriaRelationship, ClubRuleCriteriaCareer, ClubRuleCriteriaHouseholdValue, ClubRuleCriteriaAge, ClubRuleCriteriaFameRank, ClubRuleCriteriaCareSimTypeSupervised, ClubRulefrom interactions.utils.tunable_icon import TunableIconAllPacksfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableMapping, TunableList, TunableTuple, TunableReference, Tunable, TunableVariant, TunableEnumEntryimport servicesimport sims4.resourcesfrom small_business.small_business_tuning import SmallBusinessTunablesfrom typing import TYPE_CHECKINGfrom world.premade_sim_template import PremadeSimTemplateif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfo
    from clubs.club_tuning import ClubRuleCriteriaBaselogger = sims4.log.Logger('SmallBusinessSeed')
class _AttendanceCriteriaEntry(TunableTuple):

    def __init__(self, criteria_tunable:'ClubRuleCriteriaBase', lock_supervised:'bool'=True):
        kwargs = {}
        if lock_supervised:
            locked_args = {'criteria_supervised': False}
        else:
            locked_args = None
            kwargs['criteria_supervised'] = Tunable(description=',\n                    Check if you want the rule the attending sim that matches rule to be supervised.\n                    ', tunable_type=bool, default=True)
        super().__init__(criteria=criteria_tunable.TunableFactory(), criteria_required=Tunable(description=',\n                Check if you want the rule the attendance sim is required to match.\n                ', tunable_type=bool, default=True), locked_args=locked_args, **kwargs)

class SmallBusinessSeed(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SMALL_BUSINESS_SEED)):
    INSTANCE_TUNABLES = {'business_name_key': TunableLocalizedString(description='\n            The localized name of the business.\n            '), 'business_description_key': TunableLocalizedString(description='\n            The description of business.\n            '), 'business_icon': TunableIconAllPacks(), 'customer_rules': TunableList(description='\n            The list of rules that customers will follow.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP), pack_safe=True)), 'attendance_criteria': TunableList(description='\n            The list of rules that sims should match in order to visit this business.\n            ', tunable=TunableVariant(skill=_AttendanceCriteriaEntry(ClubRuleCriteriaSkill), trait=_AttendanceCriteriaEntry(ClubRuleCriteriaTrait), relationship=_AttendanceCriteriaEntry(ClubRuleCriteriaRelationship), career=_AttendanceCriteriaEntry(ClubRuleCriteriaCareer), household_value=_AttendanceCriteriaEntry(ClubRuleCriteriaHouseholdValue), age=_AttendanceCriteriaEntry(ClubRuleCriteriaAge), fame_rank=_AttendanceCriteriaEntry(ClubRuleCriteriaFameRank), care_sim_type=_AttendanceCriteriaEntry(ClubRuleCriteriaCareSimTypeSupervised, lock_supervised=False), default='skill')), 'attendance_sale_mode': TunableEnumEntry(description='\n            Default sale mode when business is created.\n            ', tunable_type=SmallBusinessAttendanceSaleMode, default=SmallBusinessAttendanceSaleMode.DISABLED), 'business_perks': TunableList(description='\n            A perks that will be added to business perks tracker.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK))), 'markup_multiplier': Tunable(description='\n            Default markup multiplier when business is created.\n            ', tunable_type=float, default=1.0), 'employee_data': TunableMapping(description='\n            The rules that each employee will follow.  Link a premade sim \n            to be an employee and will follow specific rules.\n            ', key_type=TunableReference(description='\n                Premade sim template that will become the employee of this business.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE), class_restrictions='PremadeSimTemplate', pack_safe=True), value_type=TunableTuple(employee_rules=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP), pack_safe=True))))}

    @classmethod
    def _verify_tuning_callback(cls) -> 'None':
        business_type_data = BusinessTuning.BUSINESS_TYPE_TO_BUSINESS_DATA_MAP.get(BusinessType.SMALL_BUSINESS)
        if business_type_data is None:
            logger.error('There is no business tuning data for Small Business.')
        valid_multipliers = [entry.markup_multiplier for entry in business_type_data.markup_multiplier_data]
        if cls.markup_multiplier not in valid_multipliers:
            logger.error('{} markup multiplier is set to an invalid multiplier. Invalid multiplier is: {} Valid multipliers are: {}.', cls, cls.markup_multiplier, valid_multipliers)

    @classmethod
    def create_business(cls, owner_sim_info:'SimInfo', premade_sim_infos:'Optional[Dict[PremadeSimTemplate, SimInfo]]'=None, zone_id:'int'=None, is_auto_generated_business:'bool'=False, send_localize_request:'bool'=True) -> 'None':
        business_data = Business_pb2.SetBusinessData()
        business_data.sim_id = owner_sim_info.id
        services.business_service().make_owner(owner_sim_info.household.id, BusinessType.SMALL_BUSINESS, zone_id=None, telemetry_context=BusinessOriginTelemetryContext.PREMADE, from_load=True, business_data=business_data)
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=owner_sim_info.id)
        if business_manager is None:
            return
        business_manager._icon = cls.business_icon
        for rule in cls.customer_rules:
            business_manager.add_rule(ClubRule(action=rule, with_whom=None, restriction=ClubRuleEncouragementStatus.ENCOURAGED), True)
        for criteria_data_entry in cls.attendance_criteria:
            try:
                new_criteria = criteria_data_entry.criteria()
                new_criteria.required = criteria_data_entry.criteria_required
                new_criteria.supervised = criteria_data_entry.criteria_supervised
                if new_criteria.supervised:
                    business_manager.dependents_supervised = True
                business_manager.attendance_criteria.append(new_criteria)
            except UnavailableClubCriteriaError:
                continue
        business_manager.had_ticket_machine_once = is_auto_generated_business
        business_manager.small_business_income_data.set_attendance_sales_mode(cls.attendance_sale_mode, send_data_to_client=False)
        business_manager.set_markup_multiplier(cls.markup_multiplier)
        bucks_tracker = business_manager.get_bucks_tracker()
        for perk in cls.business_perks:
            bucks_tracker.unlock_perk(perk, suppress_telemetry=True)
        if premade_sim_infos is not None:
            for (sim_template, employee_info) in cls.employee_data.items():
                if sim_template not in premade_sim_infos:
                    pass
                else:
                    sim_info = premade_sim_infos[sim_template]
                    if sim_info is not owner_sim_info:
                        business_manager.add_employee(sim_info, SmallBusinessTunables.EMPLOYEE_TYPE, is_npc_employee=True, show_notification=False)
                    employee_rules = []
                    for rule in employee_info.employee_rules:
                        club_rule = ClubRule(action=rule, with_whom=None, restriction=ClubRuleEncouragementStatus.ENCOURAGED)
                        employee_rules.append(club_rule)
                    business_manager.update_employee_club_rules(sim_info.sim_id, employee_rules)
        business_manager.business_has_been_autocreated = is_auto_generated_business
        business_manager.set_name_and_description_key(cls.business_name_key, cls.business_description_key, send_localize_request)
        if zone_id is None:
            business_manager.reset_allowed_zones()
        else:
            business_manager.add_allowed_zone_id(zone_id)
        if is_auto_generated_business:
            business_manager.setup_business_for_sim_info(owner_sim_info)
