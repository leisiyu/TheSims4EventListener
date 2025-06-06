from sims.bills_enums import UtilityEndOfBillActionfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom sims4.resources import Typesfrom event_testing.resolver import SingleSimResolverfrom gsi_handlers.gsi_utils import format_enum_namefrom sims.bills import Billsfrom sims.household_utilities.utility_types import Utilitiesimport servicesimport world.streethousehold_archive_schema = GsiGridSchema(label='Household Archive', sim_specific=False)household_archive_schema.add_field('name', label='Name', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('hidden', label='Hidden', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('player', label='Player', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('played', label='Played', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('num_sims', label='Sim Count', type=GsiFieldVisualizers.INT)household_archive_schema.add_field('region', label='World', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('street', label='Street', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('zone_name', label='Lot', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('funds', label='Funds', type=GsiFieldVisualizers.INT)household_archive_schema.add_field('net_worth', label='Net Worth', type=GsiFieldVisualizers.INT)household_archive_schema.add_field('region_id', label='Region ID', type=GsiFieldVisualizers.INT)household_archive_schema.add_field('home_zone_id', label='Home Zone ID', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('household_id', label='Household ID', type=GsiFieldVisualizers.STRING, unique_field=True)household_archive_schema.add_field('premade_household_id', label='Premade Household ID', type=GsiFieldVisualizers.STRING)household_archive_schema.add_field('move_in_time', label='Home Zone Move In Time', type=GsiFieldVisualizers.STRING)with household_archive_schema.add_has_many('sim_infos', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_id', label='Sim_Id', type=GsiFieldVisualizers.INT)
    sub_schema.add_field('sim_name', label='Name', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('species', label='Species', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('gender', label='Gender', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('age', label='Age', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('is_ghost', label='Is Ghost', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('creation_source', label='Creation Source', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('is_instanced', label='Is Instanced', type=GsiFieldVisualizers.STRING)
    sub_schema.add_field('situations', label='Situations', type=GsiFieldVisualizers.STRING)with household_archive_schema.add_has_many('service_npcs', GsiGridSchema) as sub_schema:
    sub_schema.add_field('guid', label='service', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('hired', label='Hired', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('recurring', label='Recurring', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('last_started', label='Last Started', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('last_finished', label='Last Finished', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('preferred_sims', label='Preferred Sims', type=GsiFieldVisualizers.STRING, width=4)
    sub_schema.add_field('fired_sims', label='Fired Sims', type=GsiFieldVisualizers.STRING, width=4)
    sub_schema.add_field('hiring_sim', label='Hiring Sim', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('user_data', label='User Data', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('user_data_selection_and_count', label='User Data Selection', type=GsiFieldVisualizers.STRING, width=2)with household_archive_schema.add_has_many('bills', GsiGridSchema) as sub_schema:
    sub_schema.add_field('source', label='Source', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('amount', label='Amount', type=GsiFieldVisualizers.INT, width=1)with household_archive_schema.add_has_many('utilities', GsiGridSchema) as sub_schema:
    sub_schema.add_field('utility', label='Utility', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('consumed', label='Consumed', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('value', label='Value', type=GsiFieldVisualizers.FLOAT, width=1)
    sub_schema.add_field('due', label='Due', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('keep_excess', label='Keep Excess', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('active', label='Active', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('statistic', label='Consumption', type=GsiFieldVisualizers.STRING, width=1)with household_archive_schema.add_has_many('property_owner_events', GsiGridSchema) as sub_schema:
    sub_schema.add_field('household', label='Household', type=GsiFieldVisualizers.STRING, width=1)
    sub_schema.add_field('zone_id', label='Zone Id', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('event_drama_node', label='Event Drama Node', type=GsiFieldVisualizers.STRING, width=2)
    sub_schema.add_field('time_remaining', label='Time Remaining', type=GsiFieldVisualizers.STRING, width=1)
@GsiHandler('household_info', household_archive_schema)
def generate_household_data(*args, **kwargs):
    household_manager = services.household_manager()
    if household_manager is None:
        return
    persistence_service = services.get_persistence_service()
    if persistence_service is None:
        return
    multi_unit_event_service = services.multi_unit_event_service()
    ownership_service = services.get_multi_unit_ownership_service()
    household_data = []
    for household in household_manager._objects.values():
        neighborhood_proto = persistence_service.get_neighborhood_proto_buf_from_zone_id(household.home_zone_id)
        if neighborhood_proto is not None:
            region_id = neighborhood_proto.region_id
            region_name = neighborhood_proto.name
        else:
            region_id = 0
            region_name = 'None'
        street_id = household.get_home_world_id()
        if street_id == 0:
            street_name = 'None'
        else:
            street = world.street.get_street_instance_from_world_id(street_id)
            if street is None:
                street_name = str(street_id)
            else:
                street_name = street.__name__
        zone_data = persistence_service.get_zone_proto_buff(household.home_zone_id)
        zone_name = zone_data.name if zone_data is not None else 'None'
        entry = {'name': str(household.name), 'hidden': str(household.hidden), 'player': str(household.is_player_household), 'played': str(household.is_played_household), 'num_sims': str(len(household)), 'zone_name': zone_name, 'region': region_name, 'street': street_name, 'funds': str(household._funds.money), 'net_worth': str(household.household_net_worth()), 'region_id': str(region_id), 'home_zone_id': str(household.home_zone_id), 'household_id': str(household.id), 'premade_household_id': str(household.premade_household_id) if household.premade_household_id > 0 else 'None', 'move_in_time': str(household.home_zone_move_in_time)}
        sim_info_data = []
        entry['sim_infos'] = sim_info_data
        for sim_info in household.sim_info_gen():
            sim_info_entry = {'sim_id': str(sim_info.id), 'sim_name': sim_info.full_name, 'species': str(sim_info.species), 'gender': str(sim_info.gender), 'age': str(sim_info.age), 'is_ghost': str(sim_info.is_ghost), 'creation_source': format_enum_name(sim_info.creation_source), 'is_instanced': str(sim_info.is_instanced()), 'situations': sim_info.debug_get_current_situations_string()}
            sim_info_data.append(sim_info_entry)
        service_npcs = []
        entry['service_npcs'] = service_npcs
        if household._service_npc_record is not None:
            npc_tuning = services.get_instance_manager(Types.SERVICE_NPC)
            sim_mgr = services.sim_info_manager()
            for (service_type, rec) in household._service_npc_record.items():
                stype = npc_tuning.get(service_type)
                if rec.user_specified_selections is None:
                    user_data_selection_str = ''
                else:
                    user_data_selection_str = ', '.join(str(i) + '(' + str(j) + ')' for (i, j) in zip(rec.user_specified_selections[0], rec.user_specified_selections[1]))
                e = {'guid': stype.__name__ if stype is not None else str(service_type), 'hired': rec.hired, 'recurring': rec.recurring, 'last_started': str(rec.time_last_started_service), 'last_finished': str(rec.time_last_finished_service), 'preferred_sims': ', '.join(str(sim_mgr.get(i)) for i in rec._preferred_service_sim_ids), 'fired_sims': ', '.join(str(sim_mgr.get(i)) for i in rec._fired_service_sim_ids), 'hiring_sim': str(sim_mgr.get(rec.hiring_sim_id)), 'user_data': rec.user_specified_data_id, 'user_data_selection_and_count': user_data_selection_str}
                service_npcs.append(e)
        utilities = []
        entry['utilities'] = utilities
        bills = []
        entry['bills'] = bills
        if household.bills_manager is not None:
            bills_manager = household.bills_manager
            current_payment_owed = bills_manager.current_payment_owed
            detail_amount = 0
            for (source_key, details) in bills_manager._current_bill_details.items():
                source = Bills.get_bill_source_enum_from_key(source_key)
                e = {'source': source.name, 'amount': details.billable_amount}
                bills.append(e)
                detail_amount += details.billable_amount
            if current_payment_owed is not None:
                e = {'source': 'Lot', 'amount': current_payment_owed - detail_amount}
                bills.append(e)
                e = {'source': 'Total', 'amount': current_payment_owed}
                bills.append(e)
            if household.home_zone_id != 0:
                utility_manager = services.utilities_manager(household_id=household.id)
            else:
                utility_manager = None
            for utility in Utilities:
                utility_info = bills_manager.get_utility_info(utility)
                if utility_info is None:
                    pass
                else:
                    details = bills_manager.get_utility_bill_info(utility)
                    bill_details = bills_manager.current_source_owed(utility)
                    delinquent = bills_manager.is_utility_delinquent(utility)
                    if utility_manager is not None:
                        active_str = 'Y' if utility_manager.is_utility_active(utility) else 'N'
                    else:
                        active_str = 'NA'
                    keep_excess_str = 'Y' if bills_manager.get_end_of_bill_action(utility) == UtilityEndOfBillAction.STORE else 'N'
                    if bill_details is None:
                        current_owed = 0
                    else:
                        current_owed = bill_details.billable_amount
                    if delinquent:
                        due_str = '{} (PAST DUE)'.format(current_owed)
                    else:
                        due_str = str(current_owed)
                    e = {'utility': utility.name, 'consumed': details.net_consumption, 'value': details.billable_amount, 'due': due_str, 'keep_excess': keep_excess_str, 'active': active_str, 'statistic': str(utility_info.statistic)}
                    utilities.append(e)
        property_owner_events = []
        entry['property_owner_events'] = property_owner_events
        if ownership_service:
            property_owner_active_events = {}
            if household.is_active_household:
                property_owner_active_events = multi_unit_event_service.get_current_property_owner_events()
            else:
                property_owners_event_data = multi_unit_event_service.get_all_property_owner_event_data()
                for (unit_zone_id, drama_node_id) in property_owners_event_data.items():
                    if ownership_service.get_property_owner_household_id(unit_zone_id) == household.id:
                        property_owner_events[unit_zone_id] = drama_node_id
            for (unit_zone_id, drama_node_id) in property_owner_active_events.items():
                tenant_household = household_manager.get_by_home_zone_id(unit_zone_id)
                event_node = services.drama_scheduler_service().get_scheduled_node_by_uid(drama_node_id)
                if tenant_household and event_node:
                    e = {'household': tenant_household.name, 'zone_id': unit_zone_id, 'event_drama_node': str(event_node), 'time_remaining': str(event_node.get_time_remaining())}
                    property_owner_events.append(e)
        household_data.append(entry)
    return household_data
