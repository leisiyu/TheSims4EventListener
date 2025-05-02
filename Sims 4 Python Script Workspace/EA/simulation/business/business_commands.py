import build_buyimport distributorimport functoolsimport servicesimport sims4.commandsimport sims4.logimport telemetry_helperfrom bucks.bucks_enums import BucksTypefrom business.business_enums import BusinessEmployeeType, BusinessType, BusinessAdvertisingType, BusinessQualityType, SmallBusinessAttendanceSaleModefrom business.business_manager import TELEMETRY_GROUP_BUSINESS, TELEMETRY_HOOK_NEW_GAME_BUSINESS_PURCHASED, TELEMETRY_HOOK_BUSINESS_TYPE, TELEMETRY_HOOK_BUSINESS_SOLD, TELEMETRY_HOOK_BUSINESS_UNREGISTERED, TELEMETRY_HOOK_BUSINESS_IDfrom clubs import club_tuningfrom clubs.club_tuning import ClubRule, ClubRuleEncouragementStatus, ClubCriteriaCategory, FameRank, HouseholdValueCategory, MaritalStatus, CareSimType, ClubRuleCriteriaCareSimTypeSupervisedfrom distributor import shared_messagesfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom event_testing.resolver import DoubleSimResolverfrom event_testing.test_events import TestEventfrom google.protobuf import text_formatfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.utils.adventure import AdventureMomentKeyfrom objects.object_enums import ItemLocationfrom protocolbuffers import Business_pb2, Consts_pb2, DistributorOps_pb2, InteractionOps_pb2, UI_pb2, Clubs_pb2from retail.retail_balance_transfer_dialog import FundsTransferDialogfrom server_commands.argument_helpers import OptionalSimInfoParam, SimInfoParam, get_optional_target, RequiredTargetParam, TunableInstanceParam, SimInfoParamfrom server_commands.drama_commands import cancel_scheduled_node_by_instancefrom sims.sim_info_types import Agefrom sims4.commands import CommandTypefrom sims4.common import Packfrom small_business.small_business_manager import TELEMETRY_HOOK_BUSINESS_HIRE_EMPLOYEE, TELEMETRY_HOOK_BUSINESS_FIRE_EMPLOYEE, SmallBusinessManagerfrom small_business.small_business_tuning import SmallBusinessTunablesfrom relationships.relationship_enums import RelationshipTrackTypefrom ui.ui_dialog_picker import SimPickerRowfrom venues.venue_tuning import Venuelogger = sims4.log.Logger('Business', default_owner='trevor')business_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)
@sims4.commands.Command('business.set_open', command_type=CommandType.Live)
def set_open(is_open:bool, zone_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
    if business_manager is None:
        logger.error('Trying to open or close a business but there is no business in the provided zone, {}.', zone_id)
        return False
    business_manager.set_open(is_open)
    sims4.commands.automation_output('BusinessOpenResponse; Status:{0}'.format('Open' if business_manager.is_open else 'Closed'), _connection)

@sims4.commands.Command('business.set_open_small_business', command_type=CommandType.Live)
def set_open_small_business(is_open:bool, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_manager = None
    if is_open:
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    else:
        zone_id = services.current_zone_id()
        business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        if business_manager.owner_sim_id != sim_info.id:
            business_manager = None
    if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
        if is_open:
            logger.error('Trying to open a business but there is no business registered to sim, {}.', sim_info.id)
        else:
            logger.error('Trying to close a business but there is no open business in this lot registered to sim, {}.', sim_info.id)
        return False
    else:
        should_proceed = True
        if not is_open:
            situation = services.get_zone_situation_manager().get_situation_by_tag(frozenset([SmallBusinessTunables.HOBBY_CLASS_SITUATION_TAG]))
            if situation is not None:
                business_manager.show_hobby_class_cancel_dialog(sim_info, situation, _connection)
                should_proceed = False
            customer_appreciation_day_perk = SmallBusinessTunables.PERK_SETTINGS.customer_appreciation_day
            if customer_appreciation_day_perk is not None:
                owner_sim_info = services.sim_info_manager().get(business_manager._owner_sim_id)
                if owner_sim_info.has_buff(customer_appreciation_day_perk.buff.buff_type):
                    business_manager.show_customer_appreciation_day_cancel_dialog(sim_info)
                    should_proceed = False
        if should_proceed:
            business_manager.set_open(is_open)
            return True
    return False

@sims4.commands.Command('business.set_business_name_description', command_type=CommandType.Live)
def set_business_name_description(sim_id:int=0, business_name:str='', business_description:str='', _connection=None):
    if sim_id == 0:
        return
    business_manager = services.business_service().get_business_manager_for_sim(sim_id)
    if business_manager is not None:
        business_manager.set_name_and_description(business_name, business_description)

@sims4.commands.Command('business.set_sim_id_open_small_business_on_load', command_type=CommandType.Live)
def set_sim_id_open_business_on_load(household_id:int, owner_sim_id:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(owner_sim_id, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return
    business_tracker = services.business_service().get_business_tracker_for_household(household_id, BusinessType.SMALL_BUSINESS)
    if business_tracker is not None:
        business_tracker.set_sim_id_open_business_on_load(sim_info.id)

@sims4.commands.Command('business.set_small_business_attendance_sale_mode', command_type=CommandType.Live)
def set_small_business_attendance_sale_mode(sale_mode:int, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
        logger.error('Could find a small business registered to sim, {}.', sim_info.id)
        return False
    try:
        small_business_attendance_sale_mode = SmallBusinessAttendanceSaleMode(sale_mode)
    except KeyError:
        logger.error('Tried to use an invalid attendance sale mode: {}. ', sale_mode)
        return False
    business_manager.small_business_income_data.set_attendance_sales_mode(small_business_attendance_sale_mode)

@sims4.commands.Command('business.set_small_business_light_retail_sale_mode', command_type=CommandType.Live)
def set_small_business_light_retail_sale_mode(enabled:bool, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return
    business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
        logger.error('Could find a small business registered to sim, {}.', sim_info.id)
        return False
    business_manager.small_business_income_data.set_light_retail_sales_enabled(enabled)

@sims4.commands.Command('business.register_small_business', command_type=CommandType.Live)
def register_small_business(opt_sim:OptionalSimInfoParam=None, business_data:str=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    if sim_info.household is None:
        return False
    proto = Business_pb2.SetBusinessData()
    if business_data is None:
        proto.sim_id = sim_info.id
    else:
        text_format.Merge(business_data, proto)
    services.business_service().make_owner(sim_info.household.id, BusinessType.SMALL_BUSINESS, None, business_data=proto)
    business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    return business_manager is not None

@sims4.commands.Command('business.update_small_business', command_type=CommandType.Live)
def update_small_business(opt_sim:OptionalSimInfoParam=None, business_data:str=None, _connection=None):
    if business_data is None:
        return
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return
    proto = Business_pb2.SetBusinessData()
    text_format.Merge(business_data, proto)
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None:
        logger.error('Trying to update a business but there is no business registered to sim, {}.', sim_info.id)
        return False
    business_manager.update_small_business_from_ui(proto)
    business_manager.send_data_to_client()

@sims4.commands.Command('business.request_show_small_business_configurator', command_type=CommandType.Live)
def request_show_small_business_configurator(is_edit:bool=False, opt_sim:OptionalSimInfoParam=None, _connection=None):
    ticket_machines = list(services.object_manager().get_objects_with_tag_gen(SmallBusinessTunables.TICKET_MACHINE_TAG))
    msg = UI_pb2.ShowSmallBusinessConfigurator()
    msg.has_ticket_machine = len(ticket_machines) > 0
    msg.is_edit = is_edit
    sim_info = None
    if opt_sim:
        sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    business_service = services.business_service()
    active_sim_info = services.active_sim_info()
    if sim_info and active_sim_info.household_id != sim_info.household_id:
        return False
    if is_edit:
        business_manager = business_service.get_business_manager_for_sim(sim_id=active_sim_info.id)
        if business_manager is None:
            business_manager = business_service.get_business_manager_for_zone()
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            logger.error('Trying to open the Small Business Configurator but there is no small business')
            return False
        if business_manager.owner_sim_id != active_sim_info.id:
            owner_info = services.sim_info_manager().get(business_manager.owner_sim_id)
            if owner_info and owner_info.household_id != active_sim_info.household_id:
                return False
            client = services.client_manager().get_first_client()
            if not client.set_active_sim_info(owner_info):
                return False
            active_sim_info = owner_info
        rank_level = business_manager.get_business_rank_level()
        if rank_level < len(SmallBusinessTunables.BUSINESS_RANK_ENTRY_BASELINES):
            if hasattr(msg, 'base_entry_fee'):
                msg.base_entry_fee = SmallBusinessTunables.BUSINESS_RANK_ENTRY_BASELINES[rank_level]
            if hasattr(msg, 'base_hourly_fee'):
                msg.base_hourly_fee = SmallBusinessTunables.BUSINESS_RANK_HOURLY_BASELINES[rank_level]
    else:
        if sim_info.id != active_sim_info.id:
            client = services.client_manager().get_first_client()
            if not client.set_active_sim_info(sim_info):
                return False
            active_sim_info = sim_info
        business_manager = business_service.get_business_manager_for_sim(sim_id=active_sim_info.id)
        if sim_info and business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
            logger.error('Trying to register a new Small Business Configurator using a sim that already owns a small business')
            return False
        if hasattr(msg, 'base_entry_fee'):
            msg.base_entry_fee = SmallBusinessTunables.BUSINESS_RANK_ENTRY_BASELINES[0]
        if hasattr(msg, 'base_hourly_fee'):
            msg.base_hourly_fee = SmallBusinessTunables.BUSINESS_RANK_HOURLY_BASELINES[0]
    current_zone = services.current_zone()
    if current_zone is not None:
        is_current_zone_allowed_for_small_business = SmallBusinessManager.is_zone_allowed_for_small_business(current_zone.id, active_sim_info.household.id)
        is_home_zone_allowed_for_small_business = SmallBusinessManager.is_zone_allowed_for_small_business(active_sim_info.household.home_zone_id, active_sim_info.household.id)
        if hasattr(msg, 'is_current_zone_allowed_for_small_business'):
            msg.is_current_zone_allowed_for_small_business = is_current_zone_allowed_for_small_business
        if hasattr(msg, 'is_home_zone_allowed_for_small_business'):
            msg.is_home_zone_allowed_for_small_business = is_home_zone_allowed_for_small_business
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_SHOW_SMALL_BUSINESS_CONFIGURATOR)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('business.save_business_preset', command_type=CommandType.Live)
def save_business_preset(preset_data:str=None, _connection=None):
    proto = Business_pb2.BusinessRulePreset()
    if preset_data is None:
        logger.error('Trying to save a business preset, but no data came in.')
    text_format.Merge(preset_data, proto)
    services.business_service().add_rule_preset(proto.name, proto.rules)

@sims4.commands.Command('business.delete_business_preset', command_type=CommandType.Live)
def delete_business_preset(preset_name:str=None, _connection=None):
    if preset_name is None:
        logger.error('Trying to delete a business preset, but no name was passed.')
    services.business_service().remove_rule_preset(preset_name)

@sims4.commands.Command('business.add_small_business_value', command_type=CommandType.Live)
def add_small_business_value(value:int, opt_sim:OptionalSimInfoParam=None, show_confirmation=True, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None:
        logger.error('Trying add business value but there is no business registered to sim, {}.', sim_info.id)
        return False
    business_value_stat = sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_VALUE_STATISTIC)
    business_value_stat.add_value(value)

@sims4.commands.Command('business.sell_small_business', command_type=CommandType.Live)
def sell_small_business(opt_sim:OptionalSimInfoParam=None, show_confirmation=True, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None:
        logger.error('Trying to sell a business but there is no business registered to sim, {}.', sim_info.id)
        return False
    if show_confirmation is True or show_confirmation == 'True':
        sell_value = business_manager.get_business_value(sim_info)
        sim_name = sim_info.full_name
        small_business_name = business_manager.name
        dialog = business_manager.get_sell_store_dialog()
        dialog.show_dialog(on_response=lambda dialog_inst: sell_sim_business_response(dialog_inst, business_service, business_manager), additional_tokens=(sim_name, sell_value, small_business_name))
    else:
        sell_small_business_telemetry(business_manager)
        sell_sim_small_business(business_service, business_manager)

@sims4.commands.Command('business.transfer_business', command_type=CommandType.Live)
def transfer_business(opt_sim:OptionalSimInfoParam=None, opt_sim2:OptionalSimInfoParam=None, _connection=None):
    owner_sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if owner_sim_info is None:
        return
    new_owner_sim_info = get_optional_target(opt_sim2, target_type=OptionalSimInfoParam, _connection=_connection)
    if new_owner_sim_info is None:
        return
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_sim(sim_id=owner_sim_info.id)
    if business_manager is None:
        logger.error('Trying to transfer a business but there is no business registered to sim, {}.', new_owner_sim_info.id)
        return False
    if business_manager.is_open:
        hobby_class_situation = services.get_zone_situation_manager().get_situation_by_tag(frozenset([SmallBusinessTunables.HOBBY_CLASS_SITUATION_TAG]))
        if hobby_class_situation is not None:
            hobby_class_situation._self_destruct()
        business_manager.set_open(False)
    business_service.transfer_business_to_sim(owner_sim_info, new_owner_sim_info, business_manager.business_type)

@sims4.commands.Command('business.list_all_small_business_rules', command_type=CommandType.Automation)
def list_all_small_business_rules(_connection=None):
    interaction_groups_iterable = services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP).types.values()
    sims4.commands.automation_output('SmallBusinessAllRules; Status:Begin', _connection)
    for interaction_group in interaction_groups_iterable:
        if interaction_group.small_business_customer_rule:
            sims4.commands.output('Available rule : {}'.format(interaction_group.__name__), _connection)
            sims4.commands.automation_output('SmallBusinessAllRules; Status:Data, Value:{}'.format(interaction_group.__name__), _connection)
    sims4.commands.automation_output('SmallBusinessAllRules; Status:End', _connection)
    return True

@sims4.commands.Command('business.list_active_small_business_rules', command_type=CommandType.Automation)
def list_active_small_business_rules(opt_sim:OptionalSimInfoParam=None, exclude_default:bool=True, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is None:
        logger.error('Trying to show potential business interactions, but there is no business associated with selected sim.')
        return False
    sims4.commands.automation_output('SmallBusinessActiveRules; Status:Begin', _connection)
    for rule in business_manager.customer_rules:
        if isinstance(rule, ClubRule):
            if rule in SmallBusinessTunables.ALWAYS_ACTIVE_RULES and exclude_default:
                pass
            else:
                sims4.commands.output('Active rule: {}.'.format(rule.action.__name__), _connection)
                sims4.commands.automation_output('SmallBusinessActiveRules; Status:Data, Value:{}'.format(rule.action.__name__), _connection)
    sims4.commands.automation_output('SmallBusinessActiveRules; Status:End', _connection)
    return True

@sims4.commands.Command('business.add_small_business_rule', command_type=CommandType.Automation)
def add_small_business_rule(rule:TunableInstanceParam(sims4.resources.Types.CLUB_INTERACTION_GROUP), opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        business_manager.add_rule(ClubRule(action=rule, with_whom=None, restriction=ClubRuleEncouragementStatus.ENCOURAGED), False)
        business_manager.update_affordance_cache()
        business_manager.send_data_to_client()
        return True
    return False

@sims4.commands.Command('business.add_small_business_rule_for_employee', command_type=CommandType.Live)
def add_small_business_rule_for_employee(rule:TunableInstanceParam(sims4.resources.Types.CLUB_INTERACTION_GROUP), opt_sim:OptionalSimInfoParam=None, opt_employee:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        business_manager._employee_manager.add_employee_rule(opt_employee.target_id, ClubRule(action=rule, with_whom=None, restriction=ClubRuleEncouragementStatus.ENCOURAGED))
        business_manager.update_affordance_cache()

@sims4.commands.Command('business.list_all_small_business_employee_rules', command_type=CommandType.Automation)
def list_all_small_business_employee_rules(_connection=None):
    interaction_groups_iterable = services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP).types.values()
    sims4.commands.automation_output('SmallBusinessAllEmployeeRules; Status:Begin', _connection)
    for interaction_group in interaction_groups_iterable:
        if interaction_group.small_business_employee_rule:
            sims4.commands.output('Available Employee rule : {}'.format(interaction_group.__name__), _connection)
            sims4.commands.automation_output('SmallBusinessAllEmployeeRules; Status:Data, Value:{}'.format(interaction_group.__name__), _connection)
    sims4.commands.automation_output('SmallBusinessAllEmployeeRules; Status:End', _connection)
    return True

@sims4.commands.Command('business.clear_small_business_employee_rules', command_type=CommandType.Automation)
def clear_small_business_employee_rules(opt_sim:OptionalSimInfoParam=None, opt_employee:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if opt_employee is None or business_manager is None:
        return False
    for employee in business_manager.employee_assignments_gen():
        if employee.sim_id == opt_employee.target_id:
            employee.rules.clear()
            business_manager.update_affordance_cache()
            return True
    return False

@sims4.commands.Command('business.fetch_small_business_employee_rules', command_type=CommandType.Automation)
def fetch_small_business_employee_rules(opt_sim:OptionalSimInfoParam=None, opt_employee:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if opt_employee is None or business_manager is None:
        return False
    for employee in business_manager.employee_assignments_gen():
        if employee.sim_id == opt_employee.target_id:
            rules = [str(rule.action.__name__) for rule in employee.rules]
            sims4.commands.output('EmployeeRules:{}'.format(' '.join(rules)), _connection)
            sims4.commands.automation_output('SmallBusinessEmployee; Status:Data, EmployeeId:{}, EmployeeRules:{}'.format(opt_employee.target_id, ' '.join(rules)), _connection)
            return True
    return False

@sims4.commands.Command('business.list_all_small_business_attendance_criteria_options', command_type=CommandType.Automation)
def list_all_small_business_attendance_criteria_options(_connection=None):
    sims4.commands.automation_output('SmallBusinessAllCriteria; Status:Begin', _connection)
    for criteria_category in club_tuning.ClubCriteriaCategory:
        if criteria_category == ClubCriteriaCategory.CLUB_MEMBERSHIP:
            pass
        else:
            criteria_cls = club_tuning.CATEGORY_TO_CRITERIA_MAPPING[criteria_category]
            if criteria_cls.test():
                criteria_proto = Clubs_pb2.ClubCriteria()
                criteria = ''
                criteria_manager = None
                criteria_proto.category = criteria_category
                criteria_cls.populate_possibilities(criteria_proto)
                if criteria_category == ClubCriteriaCategory.SKILL:
                    criteria_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
                elif criteria_category == ClubCriteriaCategory.TRAIT:
                    criteria_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
                elif criteria_category == ClubCriteriaCategory.CAREER:
                    criteria_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
                for criteria_info in criteria_proto.criteria_infos:
                    if criteria_category == ClubCriteriaCategory.SKILL or criteria_category == ClubCriteriaCategory.TRAIT or criteria_category == ClubCriteriaCategory.CAREER:
                        if criteria_manager is not None:
                            criteria = criteria_manager.get(criteria_info.resource_value.instance).__name__
                    elif criteria_category == ClubCriteriaCategory.FAME_RANK:
                        criteria = FameRank(criteria_info.enum_value)
                    if criteria_category == ClubCriteriaCategory.AGE:
                        criteria = Age(criteria_info.enum_value)
                    elif criteria_category == ClubCriteriaCategory.HOUSEHOLD_VALUE:
                        criteria = HouseholdValueCategory(criteria_info.enum_value)
                    elif criteria_category == ClubCriteriaCategory.RELATIONSHIP:
                        criteria = MaritalStatus(criteria_info.enum_value)
                    elif criteria_category == ClubCriteriaCategory.CARE_SIM_TYPE_SUPERVISED:
                        criteria = CareSimType(criteria_info.enum_value)
                    if criteria_category == ClubCriteriaCategory.SKILL or criteria_category == ClubCriteriaCategory.TRAIT or criteria_category == ClubCriteriaCategory.CAREER:
                        sims4.commands.output('Category:{}, Criteria:{}'.format(club_tuning.ClubCriteriaCategory(criteria_category).name, criteria), _connection)
                        sims4.commands.automation_output('SmallBusinessAllCriteria; Status:Data, Category:{}, Criteria:{}'.format(club_tuning.ClubCriteriaCategory(criteria_category).name, criteria), _connection)
                    else:
                        sims4.commands.output('Category:{}, Criteria:{}, Value:{}'.format(club_tuning.ClubCriteriaCategory(criteria_category).name, criteria, criteria_info.enum_value), _connection)
                        sims4.commands.automation_output('SmallBusinessAllCriteria; Status:Data, Category:{}, Criteria:{}, Value: {}'.format(club_tuning.ClubCriteriaCategory(criteria_category).name, criteria, criteria_info.enum_value), _connection)
    sims4.commands.automation_output('SmallBusinessAllCriteria; Status:End', _connection)
    return True

@sims4.commands.Command('business.add_small_business_attendance_criteria_trait', command_type=CommandType.Automation)
def add_small_business_attendance_criteria_trait(param:TunableInstanceParam(sims4.resources.Types.TRAIT), opt_sim:OptionalSimInfoParam=None, required:bool=False, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        business_manager.debug_add_attendance_criteria(ClubCriteriaCategory.TRAIT, param, required)
        business_manager.send_data_to_client()
        return True
    return False

@sims4.commands.Command('business.add_small_business_attendance_criteria_skill', command_type=CommandType.Automation)
def add_small_business_attendance_criteria_skill(param:TunableInstanceParam(sims4.resources.Types.STATISTIC), opt_sim:OptionalSimInfoParam=None, required:bool=False, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None and param.is_skill:
        business_manager.debug_add_attendance_criteria(ClubCriteriaCategory.SKILL, param, required)
        business_manager.send_data_to_client()
        return True
    return False

@sims4.commands.Command('business.add_small_business_attendance_criteria_career', command_type=CommandType.Automation)
def add_small_business_attendance_criteria_career(param:TunableInstanceParam(sims4.resources.Types.CAREER), opt_sim:OptionalSimInfoParam=None, required:bool=False, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        business_manager.debug_add_attendance_criteria(ClubCriteriaCategory.CAREER, param, required)
        business_manager.send_data_to_client()
        return True
    return False

@sims4.commands.Command('business.add_small_business_attendance_criteria', command_type=CommandType.Automation)
def add_small_business_attendance_criteria(criteria_category:ClubCriteriaCategory, param:int, opt_sim:OptionalSimInfoParam=None, required:bool=False, supervised:bool=True, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        business_manager.debug_add_attendance_criteria(criteria_category, param, required, supervised)
        business_manager.send_data_to_client()
        return True
    return False

@sims4.commands.Command('business.list_active_small_business_attendance_criteria', command_type=CommandType.Automation)
def list_active_small_business_attendance_criteria(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        sims4.commands.automation_output('SmallBusinessActiveCriteria; Status:Begin', _connection)
        for criteria in business_manager.attendance_criteria:
            if isinstance(criteria, ClubRuleCriteriaCareSimTypeSupervised):
                sims4.commands.output('ClubRuleCriteriaCareSimTypeSupervised(care_sim_type_requirements={})'.format(criteria.care_sim_type_requirements), _connection)
                sims4.commands.automation_output('SmallBusinessActiveCriteria; Status:Data, Criteria:ClubRuleCriteriaCareSimTypeSupervised(care_sim_type_requirements={})'.format(criteria.care_sim_type_requirements), _connection)
            else:
                sims4.commands.output('{}'.format(criteria), _connection)
                sims4.commands.automation_output('SmallBusinessActiveCriteria; Status:Data, Criteria:{}'.format(criteria), _connection)
        sims4.commands.automation_output('SmallBusinessActiveCriteria; Status:End', _connection)
        return True
    return False

@sims4.commands.Command('business.clear_small_business_attendance_criteria', command_type=CommandType.Automation)
def clear_small_business_attendance_criteria(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        business_manager.debug_clear_attendance_criteria()
        business_manager.send_data_to_client()
        return True
    return False

@sims4.commands.Command('business.set_pay_level_small_business_employee', command_type=CommandType.Live)
def set_pay_level_small_business_employee(opt_sim:OptionalSimInfoParam=None, opt_employee:OptionalSimInfoParam=None, pay_level:int=0, show_employee_management:bool=False, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        employee_info = get_optional_target(opt_employee, target_type=OptionalSimInfoParam, _connection=_connection)
        business_manager.set_employee_pay_level(employee_info, pay_level)
        if show_employee_management:
            show_small_business_employee_management_dialog(opt_sim, _connection)

@sims4.commands.Command('business.show_small_business_employee_management_dialog', command_type=CommandType.Live)
def show_small_business_employee_management_dialog(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is None:
        return False
    sim_info_manager = services.sim_info_manager()
    msg = Business_pb2.ManageSmallBusinessEmployeesData()
    msg.hiring_sim_id = sim_info.sim_id
    requesting_sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=SmallBusinessTunables.SMALL_BUSINESS_HIRE_EMPLOYEE_CAP, sim_filter=SmallBusinessTunables.SMALL_BUSINESS_POTENTIAL_EMPLOYEE_FILTER, requesting_sim_info=requesting_sim_info, allow_yielding=False, allow_instanced_sims=True)
    if hasattr(msg, 'has_no_potential_employees'):
        msg.has_no_potential_employees = True
    for (business_employee_type, business_employee_data) in business_manager.tuning_data.employee_data_map.items():
        current_employees = business_manager.get_employees_by_type(business_employee_type)
        for employee_sim_id in current_employees:
            employee_sim_info = sim_info_manager.get(employee_sim_id)
            with ProtocolBufferRollback(msg.employees) as employee_msg:
                business_manager.populate_employee_msg(employee_sim_info, employee_msg, business_employee_type, business_employee_data)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_MANAGE_SMALL_BUSINESS_EMPLOYEES_DIALOG)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('business.hire_small_business_employee', command_type=CommandType.Automation)
def hire_small_business_employee(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is not None:
        sims = services.sim_info_manager().get_all()
        for sim in sims:
            if sim.sim_id != business_manager.owner_sim_id and not business_manager.is_employee(sim):
                business_manager.run_hire_interaction(sim, SmallBusinessTunables.EMPLOYEE_TYPE)
                sims4.commands.automation_output('SmallBusinessEmployee; Status:Hired, SimId:{}'.format(sim.sim_id), _connection)
                return True
    return False

@sims4.commands.Command('business.quit_small_business_employee_career', command_type=CommandType.Live)
def quit_small_business_employee_career(opt_sim:OptionalSimInfoParam=None, opt_owner:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_owner, _connection=_connection)
    if business_manager is None:
        sims4.commands.output('Small business unavailable', _connection)
        return False
    else:
        sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
        if sim_info:
            business_manager.remove_employee(sim_info)
            return True
    return False

@sims4.commands.Command('business.get_small_business_employees', command_type=CommandType.Automation)
def get_small_business_employees(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection)
    if business_manager is None:
        sims4.commands.output('Small business unavailable.', _connection)
        return False
    if not business_manager.has_employee_assignments:
        sims4.commands.automation_output('SmallBusinessEmployee; Status:None', _connection)
        return False
    employee_ids = [str(employee.sim_id) for employee in business_manager.employee_assignments_gen()]
    sims4.commands.output('EmployeeIDs:{}'.format(' '.join(employee_ids)), _connection)
    sims4.commands.automation_output('SmallBusinessEmployee; Status:Data, EmployeeIDs:{}'.format(' '.join(employee_ids)), _connection)
    return True

@sims4.commands.Command('business.list_small_business_perks_all', command_type=CommandType.Automation)
def list_small_business_perks(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection)
    if business_manager is None:
        sims4.commands.output('Small business unavailable.', _connection)
        return False
    sims4.commands.automation_output('SmallBusinessAllPerks; Status:Begin', _connection)
    for perk in business_manager.get_bucks_tracker().all_perks_of_type_gen(BucksType.BusinessPerkBucks):
        sims4.commands.output('{}'.format(perk), _connection)
        sims4.commands.automation_output('SmallBusinessAllPerks; Status:Data, Value:{}'.format(perk), _connection)
    sims4.commands.automation_output('SmallBusinessAllPerks; Status:End', _connection)
    return True

@sims4.commands.Command('business.unlock_all_small_business_perks', command_type=CommandType.Automation)
def unlock_small_business_perks(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection)
    if business_manager is None:
        sims4.commands.output('Small business unavailable.', _connection)
        return False
    tracker = business_manager.get_bucks_tracker()
    sims4.commands.automation_output('SmallBusinessUnlockPerks; Status:Begin', _connection)
    for perk in tracker.all_perks_of_type_gen(BucksType.BusinessPerkBucks):
        if not tracker.is_perk_unlocked(perk):
            tracker.unlock_perk(perk)
            sims4.commands.output('Small business perk unlocked: {}.'.format(perk), _connection)
            sims4.commands.automation_output('SmallBusinessUnlockPerks; Status:Data, Value:{}'.format(perk), _connection)
    sims4.commands.automation_output('SmallBusinessUnlockPerks; Status:End', _connection)
    return True

@sims4.commands.Command('business.set_rank', command_type=CommandType.Automation)
def set_small_business_rank(rank:int=0, opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection)
    if business_manager is None:
        sims4.commands.output('Small business unavailable', _connection)
        return False
    sim_info = services.sim_info_manager().get(business_manager.owner_sim_id)
    rank_stat = sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC)
    if rank_stat is not None and 0 <= rank and rank <= rank_stat.max_rank:
        require_points = rank_stat.points_to_rank(rank)
        rank_stat.set_value(require_points)
        return True
    else:
        sims4.commands.output('Invalid rank applied', _connection)
        return False

@sims4.commands.Command('business.get_rank', command_type=CommandType.Automation)
def get_small_business_rank(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection)
    if business_manager is None:
        sims4.commands.output('Small business unavailable', _connection)
        return False
    sim_info = services.sim_info_manager().get(business_manager.owner_sim_id)
    rank_stat = sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC)
    sims4.commands.output('{}'.format(rank_stat.rank_level), _connection)
    sims4.commands.automation_output('SmallBusinessRank; Rank:{}'.format(rank_stat.rank_level), _connection)
    return True

@sims4.commands.Command('business.enable_small_business_events', command_type=CommandType.Live)
def enable_small_business_events(enable:bool=True, _connection=None):
    small_business_trackers = services.business_service().get_business_trackers_for_business_type(BusinessType.SMALL_BUSINESS)
    small_business_managers = []
    for tracker in small_business_trackers:
        if len(tracker.business_managers.values()) > 0:
            small_business_managers.extend(list(tracker.business_managers.values()))
        if len(tracker.zoneless_business_managers.values()) > 0:
            small_business_managers.extend(list(tracker.zoneless_business_managers.values()))
    sim_info_manager = services.sim_info_manager()
    for business_manager in small_business_managers:
        if business_manager is None:
            sims4.commands.output('Small business unavailable', _connection)
        owner_sim = sim_info_manager.get(business_manager.owner_sim_id)
        if enable:
            if SmallBusinessTunables.BUSINESS_EVENTS_LOOT not in business_manager.tuning_data.loot_list_on_open:
                business_manager.tuning_data.loot_list_on_open = business_manager.tuning_data.loot_list_on_open + (SmallBusinessTunables.BUSINESS_EVENTS_LOOT,)
                sims4.commands.output('{}\'s Small business events are enabled on "Open business" action'.format(owner_sim), _connection)
            else:
                sims4.commands.output('{}\'s Small business events are already enabled on "Open business" action'.format(owner_sim), _connection)
            if business_manager.is_open and check_if_business_events_is_scheduled():
                sims4.commands.output("Scheduled {}'s Small business events are already scheduled".format(owner_sim), _connection)
                if SmallBusinessTunables.BUSINESS_EVENTS_LOOT in business_manager.tuning_data.loot_list_on_open:
                    business_manager.tuning_data.loot_list_on_open = tuple(item for item in business_manager.tuning_data.loot_list_on_open if item != SmallBusinessTunables.BUSINESS_EVENTS_LOOT)
                    sims4.commands.output('{}\'s Small business events are disabled on "Open business" action'.format(owner_sim), _connection)
                else:
                    sims4.commands.output("{}'s Small business events already disabled".format(owner_sim), _connection)
                if check_if_business_events_is_scheduled():
                    cancel_scheduled_node_by_instance(SmallBusinessTunables.BUSINESS_EVENTS_DRAMA_SCHEDULER, _connection=_connection)
                    sims4.commands.output("Scheduled {}'s Small business events are cancelled".format(owner_sim), _connection)
                else:
                    sims4.commands.output("Scheduled {}'s Small business events does not exist".format(owner_sim), _connection)
        else:
            if SmallBusinessTunables.BUSINESS_EVENTS_LOOT in business_manager.tuning_data.loot_list_on_open:
                business_manager.tuning_data.loot_list_on_open = tuple(item for item in business_manager.tuning_data.loot_list_on_open if item != SmallBusinessTunables.BUSINESS_EVENTS_LOOT)
                sims4.commands.output('{}\'s Small business events are disabled on "Open business" action'.format(owner_sim), _connection)
            else:
                sims4.commands.output("{}'s Small business events already disabled".format(owner_sim), _connection)
            if check_if_business_events_is_scheduled():
                cancel_scheduled_node_by_instance(SmallBusinessTunables.BUSINESS_EVENTS_DRAMA_SCHEDULER, _connection=_connection)
                sims4.commands.output("Scheduled {}'s Small business events are cancelled".format(owner_sim), _connection)
            else:
                sims4.commands.output("Scheduled {}'s Small business events does not exist".format(owner_sim), _connection)

def check_if_business_events_is_scheduled():
    return any(node.resource_key == SmallBusinessTunables.BUSINESS_EVENTS_DRAMA_SCHEDULER.resource_key for node in services.drama_scheduler_service().scheduled_nodes_gen())

@sims4.commands.Command('business.list_small_business_events', command_type=CommandType.Automation, pack=Pack.EP18)
def list_small_business_events(_connection=None):
    adventures_dict = SmallBusinessTunables.BUSINESS_EVENTS_INTERACTION.get_adventures()
    for (title, adventures) in adventures_dict.items():
        for adventure in adventures:
            for moment_key in adventure._tuned_values._adventure_moments.keys():
                sims4.commands.output('{}'.format(moment_key), _connection)

@sims4.commands.Command('business.set_cooldown_for_small_business_events', command_type=CommandType.Automation, pack=Pack.EP18)
def set_cooldown_for_small_business_events(cooldown_in_hours:int=1, adventure_key:AdventureMomentKey=None, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('Unable to find Sim info', _connection)
        return False
    tracker = sim_info.adventure_tracker
    if tracker is None:
        sims4.commands.output('Unable to find adventure tracker on sim {}'.format(str(sim_info)), _connection)
        return False
    if adventure_key is None:
        adventures_dict = SmallBusinessTunables.BUSINESS_EVENTS_INTERACTION.get_adventures()
        for adventures in adventures_dict.values():
            for adventure in adventures:
                for moment_key in adventure._tuned_values._adventure_moments:
                    tracker.set_adventure_moment_cooldown(interaction=SmallBusinessTunables.BUSINESS_EVENTS_INTERACTION, adventure_moment_id=moment_key, cooldown=cooldown_in_hours)
                    sims4.commands.output('Cooldown hours: {} is set for {}.'.format(cooldown_in_hours, moment_key), _connection)
    else:
        try:
            tracker.set_adventure_moment_cooldown(interaction=SmallBusinessTunables.BUSINESS_EVENTS_INTERACTION, adventure_moment_id=adventure_key, cooldown=cooldown_in_hours)
            sims4.commands.output('Cooldown hours: {} is set for {}.'.format(cooldown_in_hours, adventure_key), _connection)
        except ValueError:
            sims4.commands.output('{} is not a valid AdventureMomentKey entry. Example: BusinessEvent_Interview'.format(adventure_key), _connection)
            return False
    return True

@sims4.commands.Command('business.auto_create_business', command_type=CommandType.Live, pack=Pack.EP18)
def auto_create_business(sim_info:SimInfoParam=None, original_venue_key:int=0, zone_id:int=None, _connection=None):
    if sim_info is None:
        return False
    small_business_seed = Venue.DEFAULT_FALLBACK_SMALL_BUSINESS_SEED
    if original_venue_key != 0:
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_tuning = venue_manager.get(original_venue_key)
        if venue_tuning.small_business_seed is not None:
            small_business_seed = venue_tuning.small_business_seed
    small_business_seed.create_business(sim_info, zone_id=zone_id, is_auto_generated_business=True, send_localize_request=False)
    business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None:
        return
    sims4.commands.output(f'Small Businesss ({small_business_seed} for {sim_info}', _connection)

@sims4.commands.Command('business.set_next_adventure_moment', command_type=sims4.commands.CommandType.Automation, pack=Pack.EP18)
def set_next_adventure_moment(adventure_key:AdventureMomentKey=None, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('Unable to find Sim info', _connection)
        return False
    adventure_tracker = sim.sim_info.adventure_tracker
    if adventure_tracker is None:
        sims4.commands.output('{} has no adventure tracker'.format(sim), _connection)
        return False
    if adventure_key is None:
        adventure_tracker.get_adventure_moment = functools.partial(adventure_tracker.__class__.get_adventure_moment, adventure_tracker)
        sims4.commands.output('Random adventure moment will run next', _connection)
        return True
    try:
        adventure_tracker.get_adventure_moment = lambda *_: adventure_key
        sims4.commands.output('{} adventure moment will run next. Make sure to run the cheat without arguments to reset the default functional;ity of the adventure moments'.format(adventure_key), _connection)
        return True
    except ValueError:
        sims4.commands.output('{} is not a valid AdventureMomentKey entry. Example: BusinessEvent_Interview'.format(adventure_key), _connection)
        adventure_tracker.get_adventure_moment = functools.partial(adventure_tracker.__class__.get_adventure_moment, adventure_tracker)
        sims4.commands.output('Random adventure moment will run next', _connection)
        return False

@sims4.commands.Command('business.remove_small_business_events_cooldown_buff', command_type=CommandType.Automation, pack=Pack.EP18)
def remove_small_business_events_cooldown_buff(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('Unable to find Sim info', _connection)
        return False
    sim_info.remove_buff_by_type(SmallBusinessTunables.BUSINESS_EVENTS_COOLDOWN_BUFF)
    sims4.commands.output('Cooldown period to run next small business adventure moment is removed. Cooldown will again be added once another moment is run', _connection)
    return True

def fetch_small_business_interactions(business_manager, exclude_default):
    filtered_interactions = []
    for rule in business_manager.customer_rules:
        if isinstance(rule, ClubRule):
            if rule in SmallBusinessTunables.ALWAYS_ACTIVE_RULES and exclude_default:
                pass
            else:
                filtered_interactions.extend([affordance for affordance in rule.action()])
    filtered_interactions = list(set(filtered_interactions))
    return filtered_interactions

@sims4.commands.Command('business.list_possible_small_business_customer_interactions', command_type=CommandType.Automation)
def list_possible_small_business_customer_interactions(opt_sim:OptionalSimInfoParam=None, exclude_default:bool=True, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is None:
        logger.error('Trying to show potential business interactions, but there is no business associated with selected sim.')
        return False
    filtered_interactions = fetch_small_business_interactions(business_manager, exclude_default)
    sims4.commands.automation_output('SmallBusinessInteractions; Status:Start', _connection)
    for affordance in filtered_interactions:
        sims4.commands.output('{}'.format(affordance), _connection)
        sims4.commands.automation_output('SmallBusinessInteractions; Status:Data, Value:{}'.format(affordance), _connection)
    sims4.commands.automation_output('SmallBusinessInteractions; Status:End', _connection)
    return True

@sims4.commands.Command('business.list_objects_for_small_business_customer_interactions', command_type=CommandType.Automation)
def list_objects_for_customer_interactions(opt_sim:OptionalSimInfoParam=None, customer_sim:OptionalSimInfoParam=None, exclude_default:bool=True, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    customer_sim_info = get_optional_target(customer_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        logger.error('No sim found found')
        return
    business_manager = services.business_service().get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None:
        logger.error('Trying to show potential objects for interaction sales, but there is no business associated with selected sim.')
        return False
    filtered_interactions = fetch_small_business_interactions(business_manager, exclude_default)
    objects = services.object_manager(business_manager.business_zone_id).get_all()
    objects = [obj for obj in objects if obj.item_location == ItemLocation.ON_LOT]
    sims4.commands.automation_output('SmallBusinessObjects; Status:Start', _connection)
    if customer_sim_info is None:
        context = InteractionContext(sim_info.get_sim_instance(), InteractionContext.SOURCE_SCRIPT, Priority.High)
    else:
        context = InteractionContext(customer_sim_info.get_sim_instance(), InteractionContext.SOURCE_SCRIPT, Priority.High)
    for obj in objects:
        obj_interactions = [i.affordance for i in obj.potential_interactions(context)]
        common_interactions = [str(interaction) for interaction in filtered_interactions if interaction in obj_interactions]
        if len(common_interactions) > 0:
            sims4.commands.output('{} - {} - {}'.format(obj.id, obj, ' '.join(common_interactions)), _connection)
            sims4.commands.automation_output('SmallBusinessObjects; Status:Data, ID:{}, Name:{}, Interactions:{}'.format(obj.id, obj, ' '.join(common_interactions)), _connection)
    sims4.commands.automation_output('SmallBusinessObjects; Status:End', _connection)
    return True

@sims4.commands.Command('business.show_hire_small_business_employee_picker', command_type=CommandType.Live)
def show_hire_small_business_employee_picker(opt_sim:OptionalSimInfoParam=None, _connection=None):
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is None:
        logger.error('Trying to show potential employees, but there is no business associated with selected sim.')
        return False

    def get_sim_filter_gsi_name():
        return 'Small Business Command: Select Employee'

    requesting_sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=SmallBusinessTunables.SMALL_BUSINESS_HIRE_EMPLOYEE_CAP, sim_filter=SmallBusinessTunables.SMALL_BUSINESS_POTENTIAL_EMPLOYEE_FILTER, requesting_sim_info=requesting_sim_info, allow_yielding=False, allow_instanced_sims=True, gsi_source_fn=get_sim_filter_gsi_name)
    picker_dialog = SmallBusinessTunables.SMALL_BUSINESS_HIRE_EMPLOYEE_DIALOG(services.active_sim_info())
    relationship_service = services.relationship_service()
    employees_sim_infos = business_manager.get_employees_sim_info()
    for result in results[:SmallBusinessTunables.SMALL_BUSINESS_HIRE_EMPLOYEE_CAP]:
        if result.sim_info in employees_sim_infos:
            pass
        else:
            has_relationship_track = False
            for rel_track in relationship_service.relationship_tracks_gen(requesting_sim_info.sim_id, result.sim_info.sim_id, track_type=RelationshipTrackType.RELATIONSHIP):
                if not rel_track.is_short_term_context:
                    has_relationship_track = True
                    break
            if not has_relationship_track:
                pass
            else:
                dialog_row = SimPickerRow(result.sim_info.sim_id, tag=result.sim_info)
                is_enable = dialog_row.is_enable = relationship_service.get_relationship_score(requesting_sim_info.sim_id, result.sim_info.sim_id) > SmallBusinessTunables.MIN_RELATIONSHIP_FOR_SMALL_BUSINESS_EMPLOYEE_HIRE
                if not is_enable:
                    dialog_row.row_tooltip = lambda *_: SmallBusinessTunables.MIN_RELATIONSHIP_FOR_SMALL_BUSINESS_EMPLOYEE_HIRE_FAILED_TOOLTIP_TEXT
                picker_dialog.add_row(dialog_row)

    def on_response(dialog):
        if not dialog.accepted:
            return
        hired_sim_info = dialog.get_single_result_tag()
        business_manager.add_employee(hired_sim_info, SmallBusinessTunables.EMPLOYEE_TYPE)
        show_small_business_employee_management_dialog(opt_sim, _connection)

    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_HIRE_EMPLOYEE) as hook:
        hook.write_int(TELEMETRY_HOOK_BUSINESS_ID, business_manager.owner_sim_id)
    picker_dialog.show_dialog(on_response=on_response)
    return True

@sims4.commands.Command('business.set_customers_allowed', command_type=sims4.commands.CommandType.Automation)
def set_customers_allowed(customers_allowed:bool, zone_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to change customers allowed but there is no business in the zone, {}.', zone_id)
        return False
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is None:
        return False
    zone_director.set_customers_allowed(customers_allowed)
    return True

@sims4.commands.Command('business.show_summary_dialog', command_type=CommandType.Live)
def show_summary_dialog(zone_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is None:
        return False
    business_manager.show_summary_dialog()
    return True

@sims4.commands.Command('business.show_small_business_summary_dialog', command_type=CommandType.Live)
def show_small_business_summary_dialog(sim_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_sim(sim_id)
    if business_manager is None:
        return False
    business_manager.show_summary_dialog()
    return True

@sims4.commands.Command('business.show_balance_transfer_dialog', command_type=CommandType.Live)
def show_balance_transfer_dialog(_connection=None):
    FundsTransferDialog.show_dialog()

@sims4.commands.Command('business.set_star_rating_value', command_type=CommandType.Live)
def set_star_rating_value(rating_value:float, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    business_manager.set_star_rating_value(rating_value)

@sims4.commands.Command('business.push_active_sim_to_buy_business', command_type=CommandType.Live)
def push_active_sim_to_buy_business(business_type:BusinessType, _connection=None):
    output = sims4.commands.Output(_connection)
    active_sim = services.get_active_sim()
    if active_sim is None:
        output('There is no active sim.')
        return False
    business_tuning = services.business_service().get_business_tuning_data_for_business_type(business_type)
    if business_tuning is None:
        output("Couldn't find tuning for business type: {}", business_type)
        return False
    context = InteractionContext(active_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
    if not active_sim.push_super_affordance(business_tuning.buy_business_lot_affordance, active_sim, context):
        output('Failed to push the buy affordance on the active sim.')
        return False
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_NEW_GAME_BUSINESS_PURCHASED, household=active_sim.household) as hook:
        hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, business_type)
    return True

@sims4.commands.Command('business.push_active_sim_to_register_business', command_type=CommandType.Live)
def push_active_sim_to_register_business(business_type:BusinessType, _connection=None):
    output = sims4.commands.Output(_connection)
    active_sim = services.get_active_sim()
    if active_sim is None:
        output('There is no active sim.')
        return False
    business_tuning = services.business_service().get_business_tuning_data_for_business_type(business_type)
    if business_tuning is None:
        output("Couldn't find tuning for business type: {}", business_type)
        return False
    else:
        context = InteractionContext(active_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        if not active_sim.push_super_affordance(business_tuning.register_business_affordance, active_sim, context):
            output('Failed to push the register affordance on the active sim.')
            return False
    return True

@sims4.commands.Command('business.push_active_sim_to_buy_small_business_venue', command_type=CommandType.Live)
def push_active_sim_to_buy_small_business_venue(_connection=None):
    output = sims4.commands.Output(_connection)
    active_sim = services.get_active_sim()
    if active_sim is None:
        output('There is no active sim.')
        return False
    else:
        context = InteractionContext(active_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        if not active_sim.push_super_affordance(SmallBusinessTunables.BUY_SMALL_BUSINESS_VENUE_LOT_AFFORDANCE, active_sim, context):
            output('Failed to push the register affordance on the active sim.')
            return False
    return True

@sims4.commands.Command('business.send_buy_small_business_telemetry', command_type=CommandType.Live)
def send_buy_small_business_telemetry(sim_id, _connection=None):
    participant_sim = services.sim_info_manager().get(int(sim_id))
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_NEW_GAME_BUSINESS_PURCHASED, household=participant_sim.household) as hook:
        hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, BusinessType.SMALL_BUSINESS)

@sims4.commands.Command('business.show_employee_management_dialog', command_type=CommandType.Live)
def show_employee_management_dialog(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_services = services.business_service()
    business_manager = business_services.get_business_manager_for_zone()
    if business_manager is None:
        return False
    business_tracker = business_services.get_business_tracker_for_household(sim_info.household_id, business_manager.business_type)
    msg = Business_pb2.ManageEmployeesDialog()
    msg.hiring_sim_id = sim_info.sim_id

    def get_sim_filter_gsi_name():
        return 'Business Command: Get New Possible Employees'

    for (business_employee_type, business_employee_data) in business_manager.tuning_data.employee_data_map.items():
        with ProtocolBufferRollback(msg.jobs) as employee_job_msg:
            total_unlocked_slots = business_employee_data.employee_count_default + business_tracker.get_additional_employee_slots(business_employee_type)
            employee_job_msg.open_slots = total_unlocked_slots - business_manager.get_employee_count(business_employee_type)
            employee_job_msg.locked_slots = business_employee_data.employee_count_max - total_unlocked_slots
            employee_job_msg.job_type = int(business_employee_type)
            employee_job_msg.job_name = business_employee_data.job_name
            employee_job_msg.job_icon = create_icon_info_msg(IconInfoData(business_employee_data.job_icon))
            current_employees = business_manager.get_employees_by_type(business_employee_type)
            sim_info_manager = services.sim_info_manager()
            for employee_sim_id in current_employees:
                employee_sim_info = sim_info_manager.get(employee_sim_id)
                with ProtocolBufferRollback(employee_job_msg.employees) as employee_msg:
                    business_manager.populate_employee_msg(employee_sim_info, employee_msg, business_employee_type, business_employee_data)
            results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=business_employee_data.potential_employee_pool_size, sim_filter=business_employee_data.potential_employee_pool_filter, requesting_sim_info=sim_info, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
            for result in results:
                with ProtocolBufferRollback(employee_job_msg.available_sims) as employee_msg:
                    business_manager.populate_employee_msg(result.sim_info, employee_msg, business_employee_type, business_employee_data)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_MANAGE_EMPLOYEES_DIALOG)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('business.employee_hire', command_type=CommandType.Live)
def hire_business_employee(sim:RequiredTargetParam, employee_type:BusinessEmployeeType, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        owner_sim = services.get_active_sim()
        business_manager = services.business_service().get_business_manager_for_sim(owner_sim.sim_id)
        if business_manager is None:
            return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_hire_interaction(target_sim, employee_type)

@sims4.commands.Command('small_business.employee_fire', command_type=CommandType.Live)
def fire_business_employee(sim:RequiredTargetParam, run_interaction:bool=True, _connection=None):
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    owner_sim = services.get_active_sim()
    business_manager = services.business_service().get_business_manager_for_sim(owner_sim.sim_id)
    if business_manager is None:
        return False
    if not business_manager.is_employee(target_sim):
        return False
    if run_interaction:
        return business_manager.run_fire_employee_interaction(target_sim)
    business_manager.remove_employee(target_sim, is_quitting=False)
    show_small_business_employee_management_dialog(None, _connection)
    if SmallBusinessTunables.SMALL_BUSINESS_EMPLOYEE_ON_FIRE_LOOT is not None:
        double_sim_resolver = DoubleSimResolver(owner_sim, target_sim)
        SmallBusinessTunables.SMALL_BUSINESS_EMPLOYEE_ON_FIRE_LOOT.apply_to_resolver(double_sim_resolver)
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_FIRE_EMPLOYEE) as hook:
        hook.write_int(TELEMETRY_HOOK_BUSINESS_ID, business_manager.owner_sim_id)
    return True

@sims4.commands.Command('business.employee_fire', command_type=CommandType.Live)
def fire_business_employee(sim:RequiredTargetParam, run_interaction:bool=True, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        owner_sim = services.get_active_sim()
        business_manager = services.business_service().get_business_manager_for_sim(owner_sim.sim_id)
        if business_manager is None:
            return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    if run_interaction:
        return business_manager.run_fire_employee_interaction(target_sim)
    business_manager.remove_employee(target_sim, is_quitting=False)
    if business_manager.business_type == BusinessType.SMALL_BUSINESS:
        show_small_business_employee_management_dialog(None, _connection)
        if SmallBusinessTunables.SMALL_BUSINESS_EMPLOYEE_ON_FIRE_LOOT is not None:
            owner_sim = services.sim_info_manager().get(business_manager.owner_sim_id)
            double_sim_resolver = DoubleSimResolver(owner_sim, target_sim)
            SmallBusinessTunables.SMALL_BUSINESS_EMPLOYEE_ON_FIRE_LOOT.apply_to_resolver(double_sim_resolver)
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_FIRE_EMPLOYEE) as hook:
        hook.write_int(TELEMETRY_HOOK_BUSINESS_ID, business_manager.owner_sim_id)
    return True

@sims4.commands.Command('business.employee_promote', command_type=CommandType.Live)
def promote_business_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        owner_sim = services.get_active_sim()
        business_manager = services.business_service().get_business_manager_for_sim(owner_sim.sim_id)
        if business_manager is None:
            return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_promote_employee_interaction(target_sim)

@sims4.commands.Command('business.employee_demote', command_type=CommandType.Live)
def demote_business_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        owner_sim = services.get_active_sim()
        business_manager = services.business_service().get_business_manager_for_sim(owner_sim.sim_id)
        if business_manager is None:
            return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_demote_employee_interaction(target_sim)

@sims4.commands.Command('business.show_small_business_employee_task_manager', command_type=CommandType.Live)
def show_small_business_employee_task_manager(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_manager = verify_parameters_and_get_business_manager(opt_sim, _connection=_connection)
    if business_manager is None:
        return False
    sim_info_manager = services.sim_info_manager()
    msg = Business_pb2.ManageSmallBusinessEmployeesData()
    msg.hiring_sim_id = sim_info.sim_id
    for employee_data in business_manager.employee_assignments_gen():
        employee_sim_info = sim_info_manager.get(employee_data.sim_id)
        with ProtocolBufferRollback(msg.employees) as employee_msg:
            business_manager.populate_employee_msg(employee_sim_info, employee_msg)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_MANAGE_SMALL_BUSINESS_EMPLOYEE_TASKS_DIALOG)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('business.save_small_business_employees_rules', command_type=CommandType.Live)
def save_small_business_employees_rules(employee_rules_data:str=None, _connection=None):
    if employee_rules_data is None:
        return
    employees_msg = Business_pb2.ManageSmallBusinessEmployeesData()
    text_format.Merge(employee_rules_data, employees_msg)
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_sim(sim_id=employees_msg.hiring_sim_id)
    if business_manager is None:
        logger.error("Trying to save a small business employees' rules, but no business found for sim id {}.", employees_msg.hiring_sim_id)
        return False
    business_manager.update_employee_rules(employees_msg)

@sims4.commands.Command('business.set_markup', command_type=CommandType.Live)
def set_markup_multiplier(markup_multiplier:float, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to set business markup when not in a business zone.', owner='camilogarcia')
        return
    business_manager.set_markup_multiplier(markup_multiplier)

@sims4.commands.Command('business.sell_lot', command_type=CommandType.Live)
def sell_lot(zone_id:int=0, _connection=None):
    output = sims4.commands.Output(_connection)
    zone_id = zone_id if zone_id != 0 else services.current_zone_id()
    business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
    if business_manager is None:
        output("Trying to sell a lot that isn't a business lot {}.".format(zone_id))
        return False
    sell_value = _get_lot_business_sell_value(zone_id)
    household_name = services.active_household().name
    dialog = business_manager.get_sell_store_dialog()
    dialog.show_dialog(on_response=lambda dialog_id: sell_lot_response(dialog_id, zone_id=zone_id), additional_tokens=(sell_value, household_name))

@sims4.commands.Command('business.set_advertising', command_type=CommandType.Live)
def set_advertising_type(business_advertising_type_float:float, _connection=None, **kwargs):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to set business advertising type when not in a business zone.', owner='camilogarcia')
        return
    business_advertising_type = BusinessAdvertisingType(int(business_advertising_type_float))
    business_manager.set_advertising_type(business_advertising_type)

@sims4.commands.Command('business.set_quality', command_type=sims4.commands.CommandType.Live)
def set_quality(quality:BusinessQualityType, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to set the quality for a business but there was no valid business manager found for the current zone.')
        return False
    business_manager.set_quality_setting(quality)

@sims4.commands.Command('business.force_off_lot_update', command_type=CommandType.Live)
def force_off_lot_update(_connection=None):
    services.business_service()._off_lot_churn_callback(None)

@sims4.commands.Command('business.refresh_configuration', command_type=sims4.commands.CommandType.Live)
def refresh_configuration(_connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to refresh a business zone configuration but there was no valid business manager found for the current zone.')
        return
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is not None:
        zone_director.refresh_configuration()

@sims4.commands.Command('business.request_customer_situation', 'qa.business.request_customer_situation', command_type=sims4.commands.CommandType.Automation)
def request_customer_situation(situation_type:TunableInstanceParam(sims4.resources.Types.SITUATION)=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to request a customer but there was no valid business manager found for the current zone.')
        return
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is not None:
        zone_director.start_customer_situation(situation_type)

def _get_business_zones(zone_id:int):
    plex_service = services.get_plex_service()
    business_service = services.business_service()
    zone_ids = set((zone_id,))
    shared_zone_id = None
    plex_zone_ids = plex_service.get_plex_zones_in_group(zone_id)
    for plex_zone_id in plex_zone_ids:
        plex_id = plex_service.get_plex_id(plex_zone_id)
        if plex_service.is_shared_plex(plex_id):
            shared_zone_id = plex_id
        else:
            business_manager = business_service.get_business_manager_for_zone(plex_zone_id)
            if business_manager is None:
                pass
            else:
                zone_ids.add(plex_zone_id)
    return (zone_ids, shared_zone_id)

def _get_lot_business_sell_value(zone_id:int):
    (business_zone_ids, shared_zone_id) = _get_business_zones(zone_id)
    business_service = services.business_service()
    total_lot_value = 0
    for zone_id in business_zone_ids:
        business_manager = business_service.get_business_manager_for_zone(zone_id)
        lot_value = build_buy.get_lot_value(zone_id, is_furnished=business_manager.include_furniture_price_on_sell)[0]
        total_lot_value += max(0.0, business_manager._funds.money + lot_value)
    if shared_zone_id is not None:
        total_lot_value += build_buy.get_lot_value(shared_zone_id, is_furnished=True)[0]
    return total_lot_value

def _distribute_funds_from_business(zone_id:int):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    base_lot_value = build_buy.get_lot_value(zone_id, is_furnished=business_manager.include_furniture_price_on_sell)[0]
    lot_value = max(0.0, business_manager._funds.money + base_lot_value)
    business_manager.sell_business_finalize_funds(lot_value)

def sell_lot_response(dialog:int, zone_id:int):
    if not dialog.accepted:
        return
    (business_zone_ids, shared_zone_id) = _get_business_zones(zone_id)
    business_service = services.business_service()
    persistence_service = services.get_persistence_service()
    zone_manager = services.get_zone_manager()
    for zone_id in business_zone_ids:
        business_manager = business_service.get_business_manager_for_zone(zone_id)
        if business_manager is None:
            pass
        else:
            _distribute_funds_from_business(zone_id)
            if business_manager.clear_lot_ownership_on_sell:
                zone_manager.clear_lot_ownership(zone_id)
            if business_manager.disown_household_objects_on_sell:
                zone_manager.get(zone_id).disown_household_objects()
            unowned_business_type = business_manager.add_unowned_business_on_sell()
            business_service.remove_owner(zone_id, household_id=business_manager.owner_household_id, unowned_business_type=unowned_business_type)
            if zone_id == services.current_zone_id():
                build_buy.set_venue_owner_id(zone_id, 0)
            with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_SOLD, household=services.household_manager().get(business_manager.owner_household_id)) as hook:
                hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, business_manager.business_type)
            household = services.household_manager().get(business_manager.owner_household_id)
            services.get_event_manager().process_events_for_household(TestEvent.BusinessSold, household=household, event_business_type=business_manager.business_type)
            msg = InteractionOps_pb2.SellRetailLot()
            msg.retail_zone_id = zone_id
            distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_SELL_RETAIL_LOT, msg)
    if shared_zone_id is not None:
        active_hh_id = services.active_household_id()
        if active_hh_id is None:
            return
        lot_value = build_buy.get_lot_value(shared_zone_id, is_furnished=True)[0]
        household = services.household_manager().get(active_hh_id)
        household.funds.add(lot_value, Consts_pb2.FUNDS_RETAIL_PROFITS)
        zone_manager.clear_lot_ownership(shared_zone_id)

def sell_sim_business_response(dialog_inst, business_service, business_manager):
    if not dialog_inst.accepted:
        return
    sell_sim_small_business(business_service, business_manager)

def sell_sim_small_business(business_service, business_manager):
    if business_manager.is_open:
        hobby_class_situation = services.get_zone_situation_manager().get_situation_by_tag(frozenset([SmallBusinessTunables.HOBBY_CLASS_SITUATION_TAG]))
        if hobby_class_situation is not None:
            hobby_class_situation._self_destruct()
        business_manager.set_open(False)
    sim_info = services.sim_info_manager().get(business_manager.owner_sim_id)
    business_service.remove_owner_zoneless_business(sim_info, business_manager.business_type, sell=True)
    update_message = Business_pb2.DeleteSimBusiness()
    update_message.sim_id = business_manager.owner_sim_id
    op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SIM_BUSINESS_DELETE, update_message)
    Distributor.instance().add_op_with_no_owner(op)
    sell_small_business_telemetry(business_manager)
    services.get_event_manager().process_event(TestEvent.BusinessSold, sim_info=sim_info, event_business_type=business_manager.business_type)

def sell_small_business_telemetry(business_manager):
    household_id = business_manager.owner_household_id
    sim_owner_id = business_manager.owner_sim_id
    business_type = business_manager.business_type
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_UNREGISTERED, household=services.household_manager().get(household_id)) as hook:
        hook.write_enum(TELEMETRY_HOOK_BUSINESS_ID, sim_owner_id)
        hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, business_type)

def verify_parameters_and_get_business_manager(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        logger.error('No sim found found')
        return
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_sim(sim_id=sim_info.id)
    if business_manager is None:
        logger.error('No business manager found for the sim {}', sim_info)
    return business_manager

@sims4.commands.Command('business.finalize_multi_unit_sale', command_type=CommandType.Live)
def finalize_multi_unit_sale(zone_id:int=0, _connection=None):
    (business_zone_ids, shared_zone_id) = _get_business_zones(zone_id)
    business_service = services.business_service()
    for zone_id in business_zone_ids:
        business_manager = business_service.get_business_manager_for_zone(zone_id)
        household_id = business_manager.owner_household_id
        with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_SOLD, household=services.household_manager().get(household_id)) as hook:
            hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, business_manager.business_type)
        business_manager.make_unowned_on_load = True
        household = services.household_manager().get(business_manager.owner_household_id)
        services.get_event_manager().process_events_for_household(TestEvent.BusinessSold, household=household, event_business_type=business_manager.business_type)
    msg = InteractionOps_pb2.SellRetailLot()
    msg.retail_zone_id = zone_id
    distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_SELL_RETAIL_LOT, msg)

@sims4.commands.Command('business.finalize_small_business_venue_sale', command_type=CommandType.Live)
def finalize_small_business_venue_sale(zone_id:int=0, delta_funds:int=0, household_id:int=0, _connection=None):
    zone_manager = services.get_zone_manager()
    zone_manager.clear_lot_ownership(zone_id)
    if zone_id == services.current_zone_id():
        build_buy.set_venue_owner_id(zone_id, 0)
        msg = InteractionOps_pb2.SellRetailLot()
        msg.retail_zone_id = zone_id
        distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_SELL_RETAIL_LOT, msg)
    elif SmallBusinessTunables.ON_SOLD_SMALL_BUSINESS_VENUE_LOT_AFFORDANCE is not None:
        output = sims4.commands.Output(_connection)
        active_sim = services.get_active_sim()
        if active_sim is None:
            output('There is no active sim.')
        else:
            context = InteractionContext(active_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
            active_sim.push_super_affordance(SmallBusinessTunables.ON_SOLD_SMALL_BUSINESS_VENUE_LOT_AFFORDANCE, active_sim, context)

@sims4.commands.Command('business.get_hireable_employees', command_type=sims4.commands.CommandType.Automation)
def get_hireable_employees(employee_type:BusinessEmployeeType, _connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    automation_output('GetHireableEmployees; Status:Begin')
    business_services = services.business_service()
    business_manager = business_services.get_business_manager_for_zone()
    if business_manager is not None:
        employee_data = business_manager.tuning_data.employee_data_map.get(employee_type)
        if employee_data is not None:
            sim_info = services.active_sim_info()

            def get_sim_filter_gsi_name():
                return '[Automation] Business Command: Get New Possible Employees'

            results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=employee_data.potential_employee_pool_size, sim_filter=employee_data.potential_employee_pool_filter, requesting_sim_info=sim_info, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
            for result in results:
                automation_output('GetHireableEmployees; Status:Data, SimId:{}'.format(result.sim_info.id))
    automation_output('GetHireableEmployees; Status:End')
