import servicesfrom protocolbuffers import DistributorOps_pb2from _collections import defaultdictfrom distributor.rollback import ProtocolBufferRollbackfrom sims4.callback_utils import RemovableCallableListfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom careers.career_tuning import Careerfrom careers.career_enums import CareerShiftTypefrom sims.outfits.outfit_enums import OutfitCategoryimport sims4.loglogger = sims4.log.Logger('SmallBusinessEmployees', default_owner='mmikolajczyk')
class SmallBusinessCareer(Career):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._levels_per_owner = defaultdict(int)
        self.on_business_removed = RemovableCallableList()

    def join_career(self, career_history=None, career_track=None, user_level_override=None, career_level_override=None, give_skipped_rewards=True, defer_rewards=False, schedule_shift_override=CareerShiftType.ALL_DAY, show_join_msg=True, disallowed_reward_types=(), force_rewards_to_sim_info_inventory=False, defer_first_assignment=False, schedule_init_only=False, allow_outfit_generation=True, show_icon_override_picker=True, owner_id=None):
        super().join_career(career_history, career_track, user_level_override, career_level_override, give_skipped_rewards, defer_rewards, schedule_shift_override, show_join_msg, disallowed_reward_types, force_rewards_to_sim_info_inventory, defer_first_assignment, schedule_init_only, allow_outfit_generation, show_icon_override_picker, owner_id)
        self._levels_per_owner[owner_id] = 1

    def add_new_business(self, owner_id, level):
        self._levels_per_owner[owner_id] = level
        self._sim_info.career_tracker.resend_career_data()

    def remove_business(self, owner_id) -> bool:
        outfit_index = self.get_career_index(owner_id)
        if outfit_index < 0:
            return False
        if self._levels_per_owner.pop(owner_id):
            outfit_tracker = self._sim_info.get_outfits()
            if outfit_tracker is None:
                return False
            outfit_tracker.remove_outfit(OutfitCategory.SMALL_BUSINESS, outfit_index)
            self._sim_info.career_tracker.resend_career_data()
            if len(self._levels_per_owner) > 0:
                self.on_business_removed(owner_id)
        return len(self._levels_per_owner) == 0

    def set_career_level(self, owner_id, level):
        self._levels_per_owner[owner_id] = level

    def get_career_level_for_owner(self, owner_id):
        return self._levels_per_owner[owner_id]

    def get_career_index(self, owner_id):
        level_list = list(self._levels_per_owner.keys())
        if owner_id in level_list:
            return level_list.index(owner_id)
        return -1

    def get_employers_count(self):
        return len(self._levels_per_owner)

    @flexmethod
    def is_valid_career(cls, inst, sim_info=DEFAULT, from_join=False):
        inst_or_cls = inst if inst is not None else cls
        if not inst_or_cls.is_career_available(sim_info=sim_info, from_join=from_join):
            return False
        if not inst_or_cls.is_career_selectable(sim_info=sim_info):
            return False
        owners_to_remove = []
        business_service = services.business_service()
        for (owner_id, level) in inst._levels_per_owner.items():
            if owner_id != 0:
                business_manager = business_service.get_business_manager_for_sim(owner_id)
                if business_manager is None:
                    owners_to_remove.append(owner_id)
        for owner_id in owners_to_remove:
            inst.remove_business(owner_id)
        return len(inst._levels_per_owner) > 0

    def get_persistable_sim_career_proto(self):
        proto = super().get_persistable_sim_career_proto()
        if sims4.protocol_buffer_utils.has_field(proto, 'small_business_career_data'):
            for (owner_id, level) in self._levels_per_owner.items():
                with ProtocolBufferRollback(proto.small_business_career_data) as career_data:
                    business_manager = services.business_service().get_business_manager_for_sim(owner_id)
                    if business_manager is None:
                        continue
                    career_data.career_level = level
                    career_data.owner_id = owner_id
        return proto

    def load_from_persistable_sim_career_proto(self, proto, skip_load=False):
        if sims4.protocol_buffer_utils.has_field(proto, 'small_business_career_data'):
            for data in proto.small_business_career_data:
                self._levels_per_owner[data.owner_id] = data.career_level
        super().load_from_persistable_sim_career_proto(proto, skip_load)

    def populate_set_career_op(self, career_op, gig=None):
        super().populate_set_career_op(career_op, gig)
        for (owner_id, level) in self._levels_per_owner.items():
            business_manager = services.business_service().get_business_manager_for_sim(owner_id)
            if business_manager is None:
                pass
            elif business_manager._icon is not None:
                career_data = DistributorOps_pb2.SmallBusinessCareerData()
                career_data.business_name = business_manager.name
                career_data.business_icon = sims4.resources.get_protobuff_for_key(business_manager._icon)
                career_data.owner_id = owner_id
                career_op.small_business_career_data.append(career_data)
