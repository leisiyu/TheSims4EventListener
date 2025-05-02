from business.unit_rating.unit_rating_enums import UnitRatingAlertStatefrom protocolbuffers.DistributorOps_pb2 import Operationfrom protocolbuffers import DistributorOps_pb2from business.business_enums import BusinessTypefrom business.business_rule_enums import BusinessRuleStatefrom date_and_time import create_time_spanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypefrom server_commands.argument_helpers import TunableInstanceParam, OptionalSimInfoParam, get_optional_targetfrom sims4.common import Packfrom sims4.resources import Typesimport servicesimport sims4.commands
@sims4.commands.Command('multi_unit.get_property_owner_household')
def print_property_owner_household(zone_id:int=None, _connection=None) -> bool:
    if zone_id is None:
        zone_id = services.current_zone_id()
    property_owner_hh_id = services.get_multi_unit_ownership_service().get_property_owner_household_id(zone_id)
    if property_owner_hh_id:
        property_owner_hh = services.household_manager().get(property_owner_hh_id)
        sims4.commands.output('Property Owner HH: ({})'.format(property_owner_hh), _connection)
        return True
    return False

@sims4.commands.Command('multi_unit.print_tenants_of_active_sim')
def print_tenants_of_active_sim(_connection=None) -> bool:
    active_sim_info = services.active_sim_info()
    resolver = SingleSimResolver(active_sim_info)
    tenants = resolver.get_participants(ParticipantType.ActorTenants)
    sims4.commands.output('Tenants of property owner ({}) are: ({})'.format(active_sim_info, tenants), _connection)
    return True

@sims4.commands.Command('multi_unit.print_property_owner_of_active_sim')
def print_property_owner_of_active_sim(_connection=None) -> bool:
    active_sim_info = services.active_sim_info()
    resolver = SingleSimResolver(active_sim_info)
    property_owners = resolver.get_participants(ParticipantType.ActorPropertyOwners)
    sims4.commands.output('Property owners of active sim ({}) are: ({})'.format(active_sim_info, property_owners), _connection)
    return True

@sims4.commands.Command('multi_unit.set_rule_state', command_type=sims4.commands.CommandType.Automation)
def set_rule(rule:TunableInstanceParam(sims4.resources.Types.BUSINESS_RULE), state:BusinessRuleState, zone_id:int=None, _connection=None) -> bool:
    output = sims4.commands.output
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is not None and business_manager.has_rules:
        business_manager.set_rule_state(rule.guid64, state, override_rule_cooldown_time=0)
        return True
    output("Attempted to set the business rule for zone {} that has no business or doesn't support business rules.".format(zone_id), _connection)
    return False

@sims4.commands.Command('multi_unit.apply_loot_to_zone')
def apply_loot_to_zone(loot_type:TunableInstanceParam(sims4.resources.Types.ACTION), zone_id:int=None, _connection=None) -> bool:
    if zone_id is None:
        zone_id = services.current_zone_id()
    if zone_id is None:
        sims4.commands.output('No zone_id found.', _connection)
        return False
    sim_info = services.active_sim_info()
    if sim_info is None:
        sims4.commands.output('No sim_info found.', _connection)
        return False
    target_household = services.household_manager().get_by_home_zone_id(zone_id)
    if target_household is None:
        sims4.commands.output('No household found for zone_id {}.'.format(zone_id), _connection)
        return False
    resolver = services.multi_unit_event_service().get_resolver(zone_id)
    loot_type.apply_to_resolver(resolver)
    return True

@sims4.commands.Command('multi_unit.trigger_apm_event')
def trigger_apm_event(drama_node:TunableInstanceParam(sims4.resources.Types.DRAMA_NODE), duration_hours:int=1, zone_id:int=None, _connection=None) -> bool:
    if zone_id is None:
        zone_id = services.current_zone_id()
    if zone_id is None:
        sims4.commands.output('No zone_id found.', _connection)
        return False
    target_household = services.household_manager().get_by_home_zone_id(zone_id)
    if target_household is None:
        sims4.commands.output('No household found for zone_id {}.'.format(zone_id), _connection)
        return False
    if drama_node.drama_node_type != DramaNodeType.MULTI_UNIT_EVENT:
        sims4.commands.output('Drama node {} is not a MultiUnitEventDramaNode'.format(drama_node), _connection)
        return False
    if not services.get_multi_unit_ownership_service().is_property_owner(services.active_household_id()):
        sims4.commands.output('Current household is not a property owner.', _connection)
        return False
    event_service = services.multi_unit_event_service()
    if event_service.tenant_unit_has_active_apm_event(zone_id):
        sims4.commands.output('Zone_id {} already has an active APM event.'.format(zone_id), _connection)
        return False
    resolver = event_service.get_resolver(zone_id)
    specific_time = services.time_service().sim_now + create_time_span(hours=duration_hours)
    services.drama_scheduler_service().schedule_node(drama_node, resolver, specific_time=specific_time)
    return True

@sims4.commands.Command('multi_unit.show_current_property_owner_events')
def show_current_property_owner_events(_connection=None) -> bool:
    if not services.get_multi_unit_ownership_service().is_property_owner(services.active_household_id()):
        sims4.commands.output('Current household is not a property owner.', _connection)
        return False
    active_event_map = services.multi_unit_event_service().get_current_property_owner_events()
    if active_event_map is None:
        sims4.commands.output('No multi-unit events found for current property owner household.', _connection)
        return False
    household_manager = services.household_manager()
    drama_scheduler = services.drama_scheduler_service()
    for (unit_zone_id, drama_node_id) in active_event_map.items():
        household = household_manager.get_by_home_zone_id(unit_zone_id)
        event_node = drama_scheduler.get_scheduled_node_by_uid(drama_node_id)
        if household and event_node:
            sims4.commands.output('Household: {}, Event: {}'.format(household.name, event_node), _connection)
    return True

@sims4.commands.Command('multi_unit.set_unit_rent_price')
def set_unit_rent_price(zone_id:int, rent_price:int, _connection=None) -> bool:
    output = sims4.commands.output
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
        business_manager.set_rent(rent_price)
        output('Successfully set rent price to {} for zone {}.'.format(rent_price, zone_id), _connection)
        return True
    output('Attempted to set the rent price for zone {} that has no rental unit business.'.format(zone_id), _connection)
    return False

@sims4.commands.Command('multi_unit.set_unit_signed_lease_length')
def set_unit_signed_lease_length(zone_id:int, length:int, _connection=None) -> bool:
    output = sims4.commands.output
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
        business_manager.signed_lease_length = length
        output('Successfully set signed lease length to {} for zone {}.'.format(length, zone_id), _connection)
        return True
    output('Attempted to set the signed lease length for zone {} that has no rental unit business.'.format(zone_id), _connection)
    return False

@sims4.commands.Command('multi_unit.enable_events', pack=Pack.EP15, command_type=sims4.commands.CommandType.Live)
def enable_events(enable:bool, _connection=None):
    services.multi_unit_event_service().set_events_enabled(enable)

@sims4.commands.Command('multi_unit.force_mu_events_on_current_zone')
def force_mule_events_on_current_zone(enable:bool=None, _connection=None):
    if enable is None:
        enable = not services.multi_unit_event_service().enable_non_rental_unit_events
    services.multi_unit_event_service().set_enable_non_rental_unit_events(enable)

@sims4.commands.Command('multi_unit.set_tenant_alert_visible', pack=Pack.EP15, command_type=sims4.commands.CommandType.Live)
def set_tenant_alert_visible(visible:bool, zone_id:int=None, _connection=None) -> bool:
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
        business_manager.tenant_alert_visible = visible
        business_manager._distribute_business_manager_data_message()
        return True
    return False

@sims4.commands.Command('multi_unit.evict', pack=Pack.EP15, command_type=sims4.commands.CommandType.Live)
def evict_tenant(tenant_household_id:int, _connection=None) -> bool:
    multi_unit_ownership_service = services.get_multi_unit_ownership_service()
    if multi_unit_ownership_service is not None:
        return multi_unit_ownership_service.evict_tenant(tenant_household_id)
    return False

@sims4.commands.Command('multi_unit.show_rental_unit_management', pack=Pack.EP15, command_type=sims4.commands.CommandType.Live)
def show_rental_unit_management(zone_id:int=None, house_description_id:int=None, is_application_process:bool=False, opt_sim:OptionalSimInfoParam=None, tenant_view_override:bool=False, _connection=None) -> bool:
    output = sims4.commands.output
    msg = DistributorOps_pb2.RentalUnitManagementData()
    is_tenant_view = zone_id is None or tenant_view_override
    if is_tenant_view or zone_id == -1:
        sim_info = get_optional_target(opt_sim, _connection)
        if sim_info is None:
            sim_info = services.get_active_sim().sim_info
        zone_id = sim_info.household.home_zone_id
        if zone_id is None:
            output('No home zone id was found for siminfo {}.'.format(sim_info.id), _connection)
            return False
        multi_unit_ownership_service = services.get_multi_unit_ownership_service()
        if not multi_unit_ownership_service.has_property_owner(zone_id):
            output('SimInfo {} is not a tenant of a Multi-Unit.'.format(sim_info.id), _connection)
            return False
        if house_description_id is None or house_description_id == -1:
            house_description_id = services.get_persistence_service().get_house_description_id(zone_id)
    if not is_tenant_view:
        msg.is_application_process = is_application_process
        tenant_service = services.get_tenant_application_service()
        msg.potential_tenants = tenant_service.build_potential_household_list_msg()
    if house_description_id is None:
        output('No house description id was found for zone {}'.format(zone_id), _connection)
        return False
    msg.zone_id = zone_id
    msg.house_description_id = house_description_id
    business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
    if business_manager is None or business_manager.business_type is not BusinessType.RENTAL_UNIT:
        output('Zone {} does not have a RentalUnit type BusinessManager.'.format(zone_id), _connection)
        return False
    if is_tenant_view:
        msg.business_data_update = business_manager.build_rental_unit_data_message()
        if business_manager.is_owned_by_npc:
            multi_unit_ownership_service = services.get_multi_unit_ownership_service()
            npc_property_owner_sim_info = multi_unit_ownership_service._get_npc_property_owner()
            if npc_property_owner_sim_info is None:
                output('Zone {} is owned by an NPC but no NPC household id was found.'.format(zone_id), _connection)
            else:
                msg.npc_property_owner_household_id = npc_property_owner_sim_info.household_id
    msg.is_tenant_view = is_tenant_view
    msg.remaining_lease = business_manager.get_remaining_lease_length()
    op = GenericProtocolBufferOp(Operation.SHOW_RENTAL_UNIT_MANAGEMENT, msg)
    Distributor.instance().add_op_with_no_owner(op)
    return True

@sims4.commands.Command('multi_unit.select_tenant', pack=Pack.EP15, command_type=sims4.commands.CommandType.Live)
def select_tenant(household_id:int, zone_id:int, household_name:str, _connection=None) -> None:
    tenant_app_service = services.get_tenant_application_service()
    if tenant_app_service is None:
        return
    tenant_app_service.move_in_household(household_id, zone_id, household_name)

@sims4.commands.Command('multi_unit.force_tenant_list_refresh', pack=Pack.EP15, command_type=sims4.commands.CommandType.DebugOnly)
def select_tenant(_connection=None) -> None:
    tenant_app_service = services.get_tenant_application_service()
    if tenant_app_service is None:
        return
    tenant_app_service._force_list_refresh = True
    tenant_app_service.generate_household_list()
    sims4.commands.output('Potential tenant household list successfully refreshed.', _connection)

@sims4.commands.Command('multi_unit.notify_rating_changed', pack=Pack.EP15, command_type=sims4.commands.CommandType.Live)
def notify_rating_changed(zone_id:int, old_star:int, new_star:int, rating_delta:int=None, _connection=None) -> bool:
    output = sims4.commands.output
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
        business_manager.on_rating_change(old_star + 1, new_star + 1, rating_delta)
        return True
    return False

@sims4.commands.Command('multi_unit.trigger_mule_event_alarm', pack=Pack.EP15, command_type=sims4.commands.CommandType.DebugOnly)
def trigger_mule_event_alarm(_connection=None) -> bool:
    zone_id = services.current_zone_id()
    if zone_id is None:
        sims4.commands.output('No zone_id found.', _connection)
        return False
    event_service = services.multi_unit_event_service()
    if event_service.tenant_unit_has_active_mule_event(zone_id):
        sims4.commands.output('Current zone already has an active MULE event.', _connection)
        return False
    resolver = event_service.get_resolver(zone_id)
    event_service.TENANT_EVENT_TABLE.apply_to_resolver(resolver)
    return True

@sims4.commands.Command('multi_unit.trigger_apm_event_alarm', pack=Pack.EP15, command_type=sims4.commands.CommandType.DebugOnly)
def trigger_apm_event_alarm(_connection=None) -> bool:
    event_service = services.multi_unit_event_service()
    events = event_service.get_current_property_owner_events()
    if len(events) >= event_service.PROPERTY_OWNER_MAX_ACTIVE_EVENTS:
        sims4.commands.output('Current Property Owner already has the maximum number of APM events allowed.', _connection)
        return False
    else:
        selected_unit_zone_id = event_service.select_unit_zone_id()
        if selected_unit_zone_id is not None:
            resolver = event_service.get_resolver(selected_unit_zone_id)
            event_service.PROPERTY_OWNER_EVENT_TABLE.apply_to_resolver(resolver)
            sims4.commands.output('Event launched for zone {}'.format(selected_unit_zone_id), _connection)
            return True
    return False
