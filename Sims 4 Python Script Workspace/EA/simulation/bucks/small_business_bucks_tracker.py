from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims4.collections import frozendictimport servicesimport sims4import telemetry_helperfrom bucks.bucks_enums import BucksTypefrom bucks.bucks_tracker import BucksTrackerBasefrom business.business_manager import TELEMETRY_GROUP_BUSINESS, TELEMETRY_HOOK_BUSINESS_IDfrom collections import namedtuplefrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom distributor.ops import SetBuckFundsfrom sims4.tuning.tunable import TunableMapping, Tunable, TunableTuple, TunableReference, OptionalTunablefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable_base import ExportModesfrom event_testing.resolver import SingleSimResolverfrom small_business.small_business_tuning import SmallBusinessTunablesfrom statistics.ranked_statistic import RankedStatisticTELEMETRY_HOOK_PURCHASE_SMALL_BUSINESS_PERK = 'BSPP'TELEMETRY_HOOK_BUSINESS_PERK_ID = 'bspc'TELEMETRY_HOOK_PERK_POINTS_LEFT = 'bspp'business_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)logger = sims4.log.Logger('SmallBusinessBucksTracker', default_owner='mlopezsierra')
class SmallBusinessBucksTracker(BucksTrackerBase):
    BUCKS_TRACKER_REWARDS_CATEGORIES = TunableMapping(description='\n        Ordered list of buck perks categories that will appear in the \n        rewards UI along with the perks that belong in the category.\n        ', key_type=Tunable(description='\n            An integer value used to set the specific order of the categoriescl\n            in the UI. the lower numbers are displayed first in the UI.\n            ', tunable_type=int, default=0), value_type=TunableTuple(description='\n            Tuning structure holding all of the localized string data for the \n            tuned Perk Category.        \n            ', category_name=TunableLocalizedString(description='\n                This is the localized name of the category that will show up \n                in the club bucks UI.\n                '), category_tooltip=TunableLocalizedString(description='\n                This is the description that will show up when the user hovers\n                over the catgory name for a while.\n                '), rewards=TunableMapping(description='\n                An ordered list of the rewards that will appear in this\n                category.\n                ', key_type=Tunable(description='\n                    An integer value used to order the appearance of the rewards\n                    inside of the category. The smaller numbers are sorted to\n                    the front of the list.\n                    ', tunable_type=int, default=0), value_type=TunableReference(description='\n                    The Buck Perk (reward) to display in the category panel of\n                    the UI.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True, allow_none=True), allow_none=True, tuple_name='RewardCategoryMapping'), export_class_name='RewardCategoryInfoTuple'), tuple_name='CategoryMapping', export_modes=ExportModes.ClientBinary)
    FROZEN_PERKS_TOOLTIP = OptionalTunable(description='\n        If tuned, the tooltip when this row is frozen.\n        ', tunable=TunableLocalizedString())

    def __init__(self, owner_id):
        sim_info = services.sim_info_manager().get(owner_id)
        super().__init__(sim_info)
        self._frozen_perks = {}
        self._frozen_business_rank_value = -1
        self._frozen_perks_initialized = False
        self._bucks[SmallBusinessTunables.SMALL_BUSINESS_PERKS_BUCKS_TYPE.value] = 0

    def transfer_owner(self, sim_info, old_owner_business_rank_value):
        self.set_owner(sim_info)
        self.check_frozen_perks(business_rank_value=old_owner_business_rank_value)
        for perk_dict in self._unlocked_perks.values():
            for (perk, perk_data) in perk_dict.items():
                if self.is_perk_unlocked_and_unfrozen(perk):
                    self._award_buffs(perk)
                    self._award_traits(perk)
        bucks_type = SmallBusinessTunables.SMALL_BUSINESS_PERKS_BUCKS_TYPE
        if bucks_type in self._bucks:
            self.distribute_bucks(bucks_type)

    def is_perk_unlocked_and_unfrozen(self, perk):
        return super().is_perk_unlocked(perk) and not self.is_perk_frozen(perk)

    def is_perk_frozen(self, perk):
        return perk.guid64 in self._frozen_perks

    def unfreeze_perk(self, perk):
        if self.is_perk_frozen(perk):
            if self._frozen_perks[perk.guid64]:
                self.unlock_perk(perk)
            del self._frozen_perks[perk.guid64]

    def freeze_perk(self, perk):
        if not self.is_perk_frozen(perk):
            is_unlocked = self.is_perk_unlocked(perk)
            self._frozen_perks[perk.guid64] = is_unlocked
            if is_unlocked:
                self.lock_perk(perk)

    def _perks_tooltip_helper(self, perk, resolver):
        if self.is_perk_frozen(perk):
            return self.FROZEN_PERKS_TOOLTIP

    def distribute_bucks(self, bucks_type):
        if self._owner is not None and bucks_type in self._bucks:
            op = SetBuckFunds(bucks_type, self._bucks[bucks_type], sim_id=self._owner.id)
            Distributor.instance().add_op_with_no_owner(op)

    def check_business_rank_frozen(self, business_rank_value:'float', ranked_statistic:'RankedStatistic', resolver:'SingleSimResolver'):
        sim_info = services.sim_info_manager().get(self._owner.id)
        if sim_info is None:
            return
        if business_rank_value <= 0:
            return
        level_user_value = ranked_statistic.convert_to_user_value(business_rank_value)
        if level_user_value not in ranked_statistic.event_data.keys():
            return
        current_level = ranked_statistic.event_data[level_user_value]
        test_result = current_level.tests.run_tests(resolver)
        if not test_result:
            self._frozen_business_rank_value = business_rank_value
        elif self._frozen_business_rank_value > 0:
            sim_info.commodity_tracker.set_value(ranked_statistic, self._frozen_business_rank_value)
            self._frozen_business_rank_value = -1

    def check_frozen_perks(self, business_rank_value=None):
        self._frozen_perks_initialized = True
        bucks_perks_by_rank = SmallBusinessBucksTracker.BUCKS_TRACKER_REWARDS_CATEGORIES
        if bucks_perks_by_rank is None:
            return
        sim_info = services.sim_info_manager().get(self._owner.id)
        if sim_info is None:
            return
        resolver = SingleSimResolver(sim_info)
        statistic_type = SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC
        if statistic_type is None:
            return
        business_rank = business_rank_value if business_rank_value is not None else self._frozen_business_rank_value
        if business_rank >= 0:
            self.check_business_rank_frozen(business_rank, statistic_type, resolver)
        statistic = sim_info.commodity_tracker.get_statistic(statistic_type, add=True)
        if statistic is not None:
            self.update_perks_by_rank(bucks_perks_by_rank, statistic, resolver)

    def update_perks_by_rank(self, perks_by_rank:'frozendict', statistic:'RankedStatistic', resolver:'SingleSimResolver'):
        event_level = 1
        while event_level <= len(perks_by_rank):
            current_level = statistic.event_data[event_level]
            test_result = current_level.tests.run_tests(resolver).result
            perks = perks_by_rank[event_level].rewards.values()
            for perk in perks:
                if perk is None:
                    pass
                elif test_result and self.is_perk_frozen(perk):
                    self.unfreeze_perk(perk)
                    while True:
                        while perk.next_level_perk is not None:
                            perk = perk.next_level_perk
                            self.unfreeze_perk(perk)
                        if not test_result:
                            self.freeze_perk(perk)
                            while perk.next_level_perk is not None:
                                perk = perk.next_level_perk
                                self.freeze_perk(perk)
                elif not test_result:
                    self.freeze_perk(perk)
                    while perk.next_level_perk is not None:
                        perk = perk.next_level_perk
                        self.freeze_perk(perk)
            event_level += 1

    def send_perks_list_for_bucks_type(self, bucks_type, sort_key=None, reverse=True):
        if not self._frozen_perks_initialized:
            self.check_frozen_perks()
        super().send_perks_list_for_bucks_type(bucks_type, sort_key, reverse)

    def save_data(self, owner_msg):
        super().save_data(owner_msg)
        with ProtocolBufferRollback(owner_msg.bucks_data) as bucks_data:
            bucks_data.frozen_business_rank_value = self._frozen_business_rank_value
            bucks_data.frozen_perk_ids.extend({perk_id for (perk_id, is_unlocked) in self._frozen_perks.items() if is_unlocked})

    def load_data(self, owner_proto):
        super().load_data(owner_proto)
        for bucks_data in owner_proto.bucks_data:
            self._frozen_business_rank_value = bucks_data.frozen_business_rank_value
            for perk_id in set(bucks_data.frozen_perk_ids):
                self._frozen_perks[perk_id] = True

    def on_all_households_and_sim_infos_loaded(self):
        bucks_type = SmallBusinessTunables.SMALL_BUSINESS_PERKS_BUCKS_TYPE
        if bucks_type is not None and bucks_type in self._bucks:
            self.distribute_bucks(bucks_type)
        for perk_dict in self._unlocked_perks.values():
            for (perk, perk_data) in perk_dict.items():
                if self.is_perk_unlocked_and_unfrozen(perk):
                    self._award_buffs(perk)
                    self._award_traits(perk)

    def get_current_business_xp(self) -> 'float':
        if self._owner is None:
            return 0.0
        statistic = self._owner.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC)
        if statistic is None:
            return 0.0
        return statistic.get_value()

    def _handle_perk_unlock_telemetry(self, perk):
        if perk.associated_bucks_type is BucksType.INVALID:
            return
        new_bucks_total = self.get_bucks_amount_for_type(perk.associated_bucks_type)
        with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_PURCHASE_SMALL_BUSINESS_PERK) as hook:
            hook.write_guid(TELEMETRY_HOOK_BUSINESS_ID, self._owner.id)
            hook.write_guid(TELEMETRY_HOOK_BUSINESS_PERK_ID, perk.guid64)
            hook.write_int(TELEMETRY_HOOK_PERK_POINTS_LEFT, new_bucks_total)

    def is_bucks_type_allowed_to_load(self, bucks_type:'BucksType'):
        return bucks_type == SmallBusinessTunables.SMALL_BUSINESS_PERKS_BUCKS_TYPE.value
