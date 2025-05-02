import servicesfrom business.business_enums import BusinessTypefrom date_and_time import create_time_spanfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemafrom sims4.log import StackVarmulti_unit_info_schema = GsiGridSchema(label='Multi-Unit/Multi Unit Info', auto_refresh=True)multi_unit_info_schema.add_field('zone_id', label='Zone Id')multi_unit_info_schema.add_field('house_description_id', label='House Description Id')multi_unit_info_schema.add_field('owner_hh_id', label='Property Owner Household Id')multi_unit_info_schema.add_field('owner_hh_name', label='Property Owner Household', width=0.75)multi_unit_info_schema.add_field('tenant_hh_id', label='Tenant Household Id')multi_unit_info_schema.add_field('tenant_hh_name', label='Tenant Household', width=0.75)multi_unit_info_schema.add_field('rent', label='Rent', width=0.5)multi_unit_info_schema.add_field('max_rent', label='Max Rent', width=0.5)multi_unit_info_schema.add_field('tile_count', label='Tile Count', width=0.5)multi_unit_info_schema.add_field('overdue_rent', label='Overdue Rent', width=0.5)multi_unit_info_schema.add_field('remaining_lease_length', label='Remaining Lease', width=0.5)multi_unit_info_schema.add_field('signed_lease_length', label='Signed Lease', width=0.5)multi_unit_info_schema.add_field('lease_start_date', label='Lease Start Date')with multi_unit_info_schema.add_has_many('business_rules', GsiGridSchema, label='Business Rules') as sub_schema:
    sub_schema.add_field('rule_id', label='Rule Id')
    sub_schema.add_field('rule_name', label='Name')
    sub_schema.add_field('rule_state', label='State')
    sub_schema.add_field('remaining_cooldown_time', label='Remaining Cooldown Time')
    sub_schema.add_field('remaining_auto_resolve_time', label='Remaining Auto Resolve Time')multi_unit_events_schema = GsiGridSchema(label='Multi-Unit/Multi Unit Events', auto_refresh=True)multi_unit_events_schema.add_field('unit_zone_id', label='Unit Zone Id')multi_unit_events_schema.add_field('master_zone_id', label='Master Zone Id')multi_unit_events_schema.add_field('drama_node_id', label='Drama Node Id')multi_unit_events_schema.add_field('active_event_type', label='Active Event Type')multi_unit_events_schema.add_field('tenant_event_timer', label='Tenant Event Timer')eviction_schema = GsiGridSchema(label='Multi-Unit/Multi Unit Eviction Log')eviction_schema.add_field('owner_hh_id', label='Property Owner Household Id')eviction_schema.add_field('owner_hh_name', label='Property Owner Household')eviction_schema.add_field('tenant_hh_id', label='Tenant Household Id')eviction_schema.add_field('tenant_hh_name', label='Tenant Household')eviction_schema.add_field('eviction_reason', label='Eviction Reason')eviction_archiver = GameplayArchiver('EvictionLog', eviction_schema)unit_rating_changes_schema = GsiGridSchema(label='Multi-Unit/Unit Rating Change Operation Log')unit_rating_changes_schema.add_field('zone_id_or_zone_ids', label='Zone Id(s)')unit_rating_changes_schema.add_field('change_type', label='Change')unit_rating_changes_schema.add_field('resolver_type', label='Resolver')unit_rating_changes_schema.add_field('receiver_type', label='Receiver')with unit_rating_changes_schema.add_has_many('callstack', GsiGridSchema) as sub_schema:
    sub_schema.add_field('code', label='Code', width=6)
    sub_schema.add_field('file', label='File', width=2)
    sub_schema.add_field('full_file', label='Full File', hidden=True)
    sub_schema.add_field('line', label='Line')with unit_rating_changes_schema.add_has_many('potential_sources', GsiGridSchema) as sub_schema:
    sub_schema.add_field('source', label='source', width=2)
    sub_schema.add_field('value', label='value', value=8)with unit_rating_changes_schema.add_has_many('updated_ratings', GsiGridSchema) as sub_schema:
    sub_schema.add_field('zone_id', label='Zone', width=2)
    sub_schema.add_field('dynamic_rating', label='New Dynamic Rating', value=8)unit_rating_change_archive = GameplayArchiver('UnitRatingChangeLog', unit_rating_changes_schema)
@GsiHandler('multi_unit_info', multi_unit_info_schema)
def generate_multi_unit_data():
    multi_unit_info = []
    business_trackers = services.business_service().get_business_trackers_for_business_type(BusinessType.RENTAL_UNIT)
    persistence_service = services.get_persistence_service()
    for tracker in business_trackers:
        for business_manager in tracker.business_managers.values():
            rental_unit_info = {'zone_id': str(business_manager.business_zone_id)}
            tenant_household = services.household_manager().get_by_home_zone_id(business_manager.business_zone_id)
            owner_household = services.household_manager().get(business_manager.owner_household_id)
            house_description_id = persistence_service.get_house_description_id(business_manager.business_zone_id)
            if house_description_id is not None:
                rental_unit_info['house_description_id'] = str(house_description_id)
            if tenant_household is not None:
                rental_unit_info['tenant_hh_id'] = str(tenant_household.id)
                rental_unit_info['tenant_hh_name'] = tenant_household.name
            if owner_household is not None:
                rental_unit_info['owner_hh_id'] = str(business_manager.owner_household_id)
                rental_unit_info['owner_hh_name'] = owner_household.name
            rental_unit_info['rent'] = business_manager.rent
            rental_unit_info['max_rent'] = business_manager.max_rent
            rental_unit_info['tile_count'] = business_manager.lot_tile_count
            rental_unit_info['overdue_rent'] = business_manager.overdue_rent
            rental_unit_info['remaining_lease_length'] = business_manager.get_remaining_lease_length()
            rental_unit_info['signed_lease_length'] = business_manager.signed_lease_length
            rental_unit_info['lease_start_date'] = str(business_manager._open_time)
            if business_manager.has_rules:
                rule_entries = []
                for business_rule in business_manager.active_rules.values():
                    cooldown_time = create_time_span(minutes=business_rule.get_remaining_cooldown_time())
                    auto_resolve_time = create_time_span(minutes=business_rule.get_remaining_auto_resolve_time())
                    business_rule_info = {'rule_id': business_rule.guid64, 'rule_name': type(business_rule).__name__, 'rule_state': business_rule.rule_state.name, 'remaining_cooldown_time': str(cooldown_time), 'remaining_auto_resolve_time': str(auto_resolve_time)}
                    rule_entries.append(business_rule_info)
                rental_unit_info['business_rules'] = rule_entries
            multi_unit_info.append(rental_unit_info)
    return multi_unit_info

@GsiHandler('multi_unit_events', multi_unit_events_schema)
def generate_multi_unit_events():
    multi_unit_events = []
    multi_unit_event_service = services.multi_unit_event_service()
    if multi_unit_event_service is None:
        return multi_unit_events
    plex_service = services.get_plex_service()
    current_zone_id = services.current_zone_id()
    multi_unit_active_events = multi_unit_event_service.get_multi_unit_lot_active_events()
    tenant_alarm_timers = multi_unit_event_service.get_tenant_unit_alarm_times()
    zone_ids = set()
    zone_ids.add(current_zone_id)
    zone_ids.update(multi_unit_active_events.keys())
    zone_ids.update(tenant_alarm_timers.keys())
    for unit_zone_id in zone_ids:
        drama_node_id = multi_unit_active_events.get(unit_zone_id, None)
        alarm_time = tenant_alarm_timers.get(unit_zone_id, None)
        master_zone_id = plex_service.get_master_zone_id(unit_zone_id)
        zone_event_state = {'unit_zone_id': hex(unit_zone_id), 'master_zone_id': hex(master_zone_id) if unit_zone_id != master_zone_id else '-', 'drama_node_id': str(drama_node_id), 'active_event_type': str(multi_unit_event_service.get_multi_unit_zone_active_event_type(unit_zone_id)), 'tenant_event_timer': str(alarm_time)}
        multi_unit_events.append(zone_event_state)
    return multi_unit_events

def log_eviction_outcome(owner_hh_id:int, tenant_hh_id:int, zone_id:int):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
    if business_manager is None or business_manager.business_type != BusinessType.RENTAL_UNIT:
        return
    owner_household = services.household_manager().get(owner_hh_id)
    tenant_household = services.household_manager().get(tenant_hh_id)
    eviction_info = {'owner_hh_id': owner_hh_id, 'owner_hh_name': owner_household.name if owner_household is not None else '', 'tenant_hh_id': tenant_hh_id, 'tenant_hh_name': tenant_household.name if tenant_household is not None else ''}
    eviction_reason = []
    if business_manager.has_rules:
        for rule in business_manager.active_rules.values():
            rule_info = f'{type(rule).__name__}: {str(rule.rule_state)}'
            eviction_reason.append(rule_info)
    if business_manager.overdue_rent > 0:
        overdue_info = f'Overdue rent: {business_manager.overdue_rent}'
        eviction_reason.append(overdue_info)
    if not len(eviction_reason):
        eviction_reason.append('Unjust Eviction')
    eviction_info['eviction_reason'] = ',\n'.join(eviction_reason)
    eviction_archiver.archive(data=eviction_info)

def log_unit_rating_change(zone_id_or_zone_ids, change_type, resolver_type, receiver_type, callstack_info):
    gsi_stack_info = []
    for stack_level in reversed(callstack_info[:-1]):
        short_file = stack_level[0].split('\\')[-1]
        gsi_stack_info.append({'full_file': stack_level[0], 'file': short_file, 'line': stack_level[1], 'code': stack_level[3]})
    stack_variables = StackVar(('loot', 'interaction', 'reward_instance', 'drama_node_inst', 'broadcaster'))
    potential_sources = [{'source': str(k), 'value': str(v)} for (k, v) in stack_variables._attr_values.items()]
    business_service = services.business_service()
    updated_ratings = []
    for zone_id in zone_id_or_zone_ids:
        business_manager = business_service.get_business_manager_for_zone(zone_id=zone_id)
        if not business_manager is None:
            if business_manager.business_type != BusinessType.RENTAL_UNIT:
                pass
            else:
                updated_ratings.append({'zone_id': str(zone_id), 'dynamic_rating': business_manager.dynamic_unit_rating})
    rating_change_info = {'zone_id_or_zone_ids': str(zone_id_or_zone_ids), 'change_type': change_type, 'resolver_type': resolver_type, 'receiver_type': receiver_type, 'callstack': gsi_stack_info, 'potential_sources': potential_sources, 'updated_ratings': updated_ratings}
    unit_rating_change_archive.archive(data=rating_change_info)
