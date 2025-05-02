import servicesimport sims4.commandsimport distributor.opsfrom sims.sim_spawner import SimSpawnerfrom user_account_data.user_account_data_enums import UserAccountDataTypeEnumfrom distributor.system import Distributorfrom protocolbuffers import DistributorOps_pb2from google.protobuf import text_formatlogger = sims4.log.Logger('User Account Data')
@sims4.commands.Command('user_account_data.get_user_account_data', command_type=sims4.commands.CommandType.Live)
def get_user_account_data(user_account_data_str:str='', _connection=None):
    if user_account_data_str != '':
        user_account_data = DistributorOps_pb2.UserAccountData()
        text_format.Merge(user_account_data_str, user_account_data)
        if user_account_data.data_type == UserAccountDataTypeEnum.PIVOTAL_MOMENTS:
            tutorial_service = services.get_tutorial_service()
            if tutorial_service is not None:
                tutorial_service.on_account_data_loaded(user_account_data)
            else:
                logger.warn('Could not load tutorial service')
                if user_account_data.data_type == UserAccountDataTypeEnum.GAMEPLAY_VALUES:
                    account = services.account_service().get_current_account()
                    if account is not None:
                        account.handle_get_user_account_data(user_account_data)
                    else:
                        logger.warn('Could not load user account.')
        elif user_account_data.data_type == UserAccountDataTypeEnum.GAMEPLAY_VALUES:
            account = services.account_service().get_current_account()
            if account is not None:
                account.handle_get_user_account_data(user_account_data)
            else:
                logger.warn('Could not load user account.')
    else:
        logger.info('No UserAccountData received')

@sims4.commands.Command('user_account_data.debug_get_user_account_data', command_type=sims4.commands.CommandType.DebugOnly)
def debug_get_user_account_data(data_type_str:str='', _connection=None):
    output = sims4.commands.Output(_connection)
    data_type = UserAccountDataTypeEnum.NONE
    if data_type_str.lower() == 'pivotalmoments':
        data_type = UserAccountDataTypeEnum.PIVOTAL_MOMENTS
    elif data_type_str.lower() == 'rewards':
        data_type = UserAccountDataTypeEnum.REWARDS
    elif data_type_str.lower() == 'events':
        data_type = UserAccountDataTypeEnum.EVENTS
    if data_type is not UserAccountDataTypeEnum.NONE:
        opGetAccountData = distributor.ops.GetAccountDataForCurrentUser(data_type)
        Distributor.instance().add_op_with_no_owner(opGetAccountData)
    else:
        output('No valid data type')

@sims4.commands.Command('user_account_data.debug_set_dummy_user_account_data', command_type=sims4.commands.CommandType.DebugOnly)
def set_dummy_events_account_data(data_type_str:str='', _connection=None):
    data_type = UserAccountDataTypeEnum.NONE
    if data_type_str.lower() == 'pivotalmoments':
        data_type = UserAccountDataTypeEnum.PIVOTAL_MOMENTS
    elif data_type_str.lower() == 'rewards':
        data_type = UserAccountDataTypeEnum.REWARDS
    elif data_type_str.lower() == 'events':
        data_type = UserAccountDataTypeEnum.EVENTS
    if data_type is not UserAccountDataTypeEnum.NONE:
        user_account_data = DistributorOps_pb2.UserAccountData()
        user_account_data.data_type = data_type
        opSetAccountData = distributor.ops.SetAccountDataForCurrentUser(user_account_data)
        Distributor.instance().add_op_with_no_owner(opSetAccountData)
    else:
        sims4.commands.output('No valid data type', _connection)

@sims4.commands.Command('user_account_data.print_gameplay_values')
def print_gameplay_values(_connection=None) -> bool:
    output = sims4.commands.Output(_connection)
    account = services.account_service().get_current_account()
    if account is None:
        output('Account not found')
        return False
    for (name, value) in account.gameplay_items_gen():
        output(name + ', ' + value)
    return True

@sims4.commands.Command('user_account_data.set_gameplay_value')
def set_gameplay_value(name:str='', value:str='', _connection=None) -> bool:
    output = sims4.commands.Output(_connection)
    account = services.account_service().get_current_account()
    if account is None:
        output('Account not found')
        return False
    if not value:
        output('Value cannot be empty')
        return False
    account.set_account_gameplay_value(name, value)
    return True
