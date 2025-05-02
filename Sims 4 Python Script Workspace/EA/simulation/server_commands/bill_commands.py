from business.business_enums import BusinessTypefrom multi_unit.rental_unit_manager import RentalUnitManagerfrom sims.bills_enums import AdditionalBillSourcefrom sims.household_utilities.utility_types import Utilitiesfrom sims4.commands import NO_CONTEXTimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Commands', default_owner='tastle')
@sims4.commands.Command('households.toggle_bill_notifications', 'households.toggle_bill_dialogs', 'bills.toggle_bill_notifications', command_type=sims4.commands.CommandType.Automation)
def toggle_bill_notifications(enable:bool=None, _connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    enable_notifications = enable if enable is not None else not bills_manager.bill_notifications_enabled
    if enable_notifications:
        bills_manager.bill_notifications_enabled = True
        sims4.commands.output('Bill notifications for household {} enabled.'.format(household), _connection)
    else:
        bills_manager.bill_notifications_enabled = False
        sims4.commands.output('Bill notifications for household {} disabled.'.format(household), _connection)

@sims4.commands.Command('households.make_bill_source_delinquent', 'bills.make_bill_source_delinquent')
def make_bill_source_delinquent(additional_bill_source_name='Miscellaneous', _connection=None):
    try:
        additional_bill_source = AdditionalBillSource(additional_bill_source_name)
    except:
        sims4.commands.output('{0} is not a valid AdditionalBillSource.'.format(additional_bill_source_name), _connection)
        return False
    if additional_bill_source is None:
        sims4.commands.output('No additional bill source found.', _connection)
        return
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    bills_manager.add_additional_bill_cost(additional_bill_source, 1)
    make_bills_delinquent(_connection=_connection)

@sims4.commands.Command('households.make_bills_delinquent', 'bills.make_bills_delinquent')
def make_bills_delinquent(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    if bills_manager.current_payment_owed is None:
        previous_send_notification = bills_manager.bill_notifications_enabled
        bills_manager.bill_notifications_enabled = False
        bills_manager.allow_bill_delivery()
        bills_manager.trigger_bill_notifications_from_delivery()
        for utility in Utilities:
            bills_manager._shut_off_utility(utility)
        bills_manager.bill_notifications_enabled = previous_send_notification

@sims4.commands.Command('households.pay_bills', 'bills.pay_bills')
def pay_bills(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    bills_manager.pay_bill()

@sims4.commands.Command('households.force_bills_due', 'bills.force_bills_due', command_type=sims4.commands.CommandType.Automation)
def force_bills_due(household_id:int=0, _connection=None):
    if household_id == 0:
        household = services.active_household()
    else:
        household = services.household_manager().get(household_id)
    if household is None:
        sims4.commands.output('No active household found and no household passed in.', _connection)
        return
    bills_manager = household.bills_manager
    if bills_manager.current_payment_owed is None:
        previous_send_notification = bills_manager.bill_notifications_enabled
        bills_manager.bill_notifications_enabled = False
        bills_manager.allow_bill_delivery()
        if bills_manager.current_payment_owed is not None:
            bills_manager.trigger_bill_notifications_from_delivery()
        bills_manager.bill_notifications_enabled = previous_send_notification
        rental_unit_manager = services.business_service().get_business_manager_for_zone(household.home_zone_id)
        if rental_unit_manager is None or rental_unit_manager.business_type != BusinessType.RENTAL_UNIT:
            return
        rental_unit_manager.make_rent_due()

@sims4.commands.Command('bills.put_bills_in_hidden_inventory')
def put_bills_in_hidden_inventory(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    if bills_manager.current_payment_owed is None:
        bills_manager.allow_bill_delivery()

@sims4.commands.Command('households.autopay_bills', 'bills.autopay_bills', command_type=sims4.commands.CommandType.Cheat)
def autopay_bills(enable:bool=None, _connection=NO_CONTEXT):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    autopay_bills = enable if enable is not None else not bills_manager.autopay_bills
    bills_manager.autopay_bills = autopay_bills
    sims4.commands.output('Autopay Bills for household {} set to {}.'.format(household, autopay_bills), _connection)

@sims4.commands.Command('households.clear_rent_due', 'bills.clear_rent_due', command_type=sims4.commands.CommandType.DebugOnly)
def clear_rent_due(household_id:int=0, _connection=None):
    if household_id is 0:
        household = services.active_household()
    else:
        household = services.household_manager().get(household_id)
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    rental_unit_manager = services.business_service().get_business_manager_for_zone(household.home_zone_id)
    if rental_unit_manager is None or not isinstance(rental_unit_manager, RentalUnitManager):
        sims4.commands.output('Active household does not have an EP15 rental unit.', _connection)
        return
    rental_unit_manager.clear_all_rent()

@sims4.commands.Command('households.show_lease_status', 'bills.show_lease_status', command_type=sims4.commands.CommandType.DebugOnly)
def show_lease_status(household_id:int=0, _connection=None):
    if household_id is 0:
        household = services.active_household()
    else:
        household = services.household_manager().get(household_id)
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    rental_unit_manager = services.business_service().get_business_manager_for_zone(household.home_zone_id)
    if rental_unit_manager is None or not isinstance(rental_unit_manager, RentalUnitManager):
        sims4.commands.output('Active household does not have an rental unit manager associated.', _connection)
        return
    sims4.commands.output(f'Lease Length = {rental_unit_manager.signed_lease_length}', _connection)
    sims4.commands.output(f'Remaining Lease Length = {rental_unit_manager.get_remaining_lease_length()}', _connection)
    sims4.commands.output(f'Rent Rate = {rental_unit_manager.rent}', _connection)
    sims4.commands.output(f'Rent Due = {rental_unit_manager.due_rent}', _connection)
    sims4.commands.output(f'Rent OverDue = {rental_unit_manager.overdue_rent}', _connection)

@sims4.commands.Command('households.force_rent_overdue', 'bills.force_rent_overdue')
def force_rent_overdue(household_id:int=0, _connection=None):
    if household_id == 0:
        household = services.active_household()
    else:
        household = services.household_manager().get(household_id)
    if household is None:
        sims4.commands.output('No active household found and no household passed in.', _connection)
        return
    rental_unit_manager = services.business_service().get_business_manager_for_zone(household.home_zone_id)
    if rental_unit_manager is None or rental_unit_manager.business_type != BusinessType.RENTAL_UNIT:
        sims4.commands.output(f'Household id {household.id} does not have an rental unit manager associated.', _connection)
        return
    if rental_unit_manager.get_currently_owed_rent() is 0:
        force_bills_due(household_id, _connection)
    rental_unit_manager.make_rent_overdue()
