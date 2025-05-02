from distributor.rollback import ProtocolBufferRollbackfrom protocolbuffers import DistributorOps_pb2import distributorimport weakreffrom distributor.system import Distributorfrom protocolbuffers.Consts_pb2 import MSG_GAMEPLAY_OPTIONSfrom protocolbuffers.GameplaySaveData_pb2 import AccountEventDataTrackerimport achievements.achievementsimport game_servicesimport protocolbuffers.GameplaySaveData_pb2 as gameplay_save_datafrom typing import TYPE_CHECKINGimport servicesimport sims4.logfrom user_account_data.user_account_data_enums import UserAccountDataTypeEnumif TYPE_CHECKING:
    from server.client import Client
    from typing import *logger = sims4.log.Logger('Account')
class Account:

    def __init__(self, account_id, persona_name):
        self.id = account_id
        self._households = weakref.WeakSet()
        self._persona_name = persona_name
        self.clients = weakref.WeakSet()
        self._achievement_tracker = achievements.achievements.AchievementTracker(account_id)
        self.save_slot_id = 0
        self._gameplay_data = {}
        services.account_service().add_account(self)
        self.locale = None

    def __repr__(self):
        return 'ID: {}; SaveSlotID: {}; locale:{}'.format(self.id, self.save_slot_id, self.locale)

    @property
    def achievement_tracker(self):
        return self._achievement_tracker

    @property
    def persona_name(self):
        return self._persona_name

    def on_load_options(self):
        self._load_options()

    def on_pre_sim_info_load_options(self):
        self._load_pre_sim_info_options()

    def on_all_households_and_sim_infos_loaded(self, client):
        self._achievement_tracker.set_update_alarm()

    def on_client_connect(self, client):
        self._achievement_tracker.send_event_data_to_client()
        opGetGameplayData = distributor.ops.GetAccountDataForCurrentUser(UserAccountDataTypeEnum.GAMEPLAY_VALUES)
        Distributor.instance().add_op_with_no_owner(opGetGameplayData)

    def on_client_disconnect(self, client):
        self._achievement_tracker.clear_tracked_client_data()
        self._achievement_tracker.clear_update_alarm()

    def add_household(self, household):
        self._households.add(household)

    def remove_household(self, household):
        self._households.discard(household)

    def get_household(self, zone_id):
        for household in self._households:
            if household.zone_id == zone_id:
                return household

    def get_client(self, zone_id):
        for client in self.clients:
            if client.zone_id == zone_id:
                return client

    def register_client(self, client):
        self.clients.add(client)

    def unregister_client(self, client):
        if client.household in self._households:
            self._households.remove(client.household)
        else:
            logger.info("unregister_client called for household not in account's households list (size={0}, household={1}).", len(self._households), client.household)
        self.clients.remove(client)

    def _load_options(self):
        account_data_msg = services.get_persistence_service().get_account_proto_buff()
        options_proto = account_data_msg.gameplay_account_data.gameplay_options
        if options_proto is None:
            logger.warn('Trying to load options in account.py but options_proto is None.')
            return
        zone = services.current_zone()
        if zone is None:
            logger.warn('Trying to load game options but zone is None.')
            return
        game_services.service_manager.load_options(options_proto)
        zone.service_manager.load_options(options_proto)

    def _load_pre_sim_info_options(self):
        account_data_msg = services.get_persistence_service().get_account_proto_buff()
        options_proto = account_data_msg.gameplay_account_data.gameplay_options
        if options_proto is None:
            logger.warn('Trying to load options in account.py but options_proto is None.')
            return
        zone = services.current_zone()
        if zone is None:
            logger.warn('Trying to load game options but zone is None.')
            return
        game_services.service_manager.pre_sim_info_load_options(options_proto)
        zone.service_manager.pre_sim_info_load_options(options_proto)

    def _save_options(self, options_proto):
        if options_proto is None:
            logger.warn('Trying to save options in account.py but options_proto is None.')
            return
        zone = services.current_zone()
        if zone is None:
            logger.warn('Trying to save game options but the zone is None.')
            return
        zone.service_manager.save_options(options_proto)
        game_services.service_manager.save_options(options_proto)

    def load_account(self, account_proto):
        self.id = account_proto.nucleus_id
        self.save_slot_id = account_proto.save_slot_id
        self._achievement_tracker.load(account_proto.gameplay_account_data.achievement_data)

    def get_gameplay_value(self, name:str):
        if name in self._gameplay_data:
            return self._gameplay_data[name]

    def gameplay_items_gen(self):
        for (name, value) in self._gameplay_data.items():
            yield (name, value)

    def handle_get_user_account_data(self, user_account_data:DistributorOps_pb2.UserAccountData()) -> None:
        if self._gameplay_data:
            return
        if user_account_data.data_type != UserAccountDataTypeEnum.GAMEPLAY_VALUES:
            return
        user_gameplay_data = gameplay_save_data.UserAccountStoredGameplayData()
        user_gameplay_data.ParseFromString(user_account_data.data)
        for user_gameplay_data_item in user_gameplay_data.stored_data:
            self._gameplay_data[user_gameplay_data_item.key] = user_gameplay_data_item.value

    def set_account_gameplay_value(self, name:str, value:str) -> None:
        self._gameplay_data[name] = value

    def save_account(self):
        account_data_msg = services.get_persistence_service().get_account_proto_buff()
        account_data_msg.nucleus_id = self.id
        account_data_msg.gameplay_account_data.achievement_data = AccountEventDataTracker()
        self.achievement_tracker.save(account_data_msg.gameplay_account_data.achievement_data)
        user_account_gameplay_data = gameplay_save_data.UserAccountStoredGameplayData()
        for (key, value) in self._gameplay_data.items():
            with ProtocolBufferRollback(user_account_gameplay_data.stored_data) as stored_data:
                stored_data.key = key
                stored_data.value = value
        user_account_data = DistributorOps_pb2.UserAccountData()
        user_account_data.data_type = UserAccountDataTypeEnum.GAMEPLAY_VALUES
        user_account_data.data = user_account_gameplay_data.SerializeToString()
        opSetGameplayData = distributor.ops.SetAccountDataForCurrentUser(user_account_data)
        Distributor.instance().add_op_with_no_owner(opSetGameplayData)

    def send_options_to_client(self, client, get_default):
        gameplay_options = gameplay_save_data.GameplayOptions()
        if not get_default:
            self._save_options(gameplay_options)
        client.send_message(MSG_GAMEPLAY_OPTIONS, gameplay_options)
