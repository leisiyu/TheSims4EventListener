import contextlibimport distributorimport event_testingimport operatorimport servicesimport sims4.logimport sims4.resourcesimport statisticsimport tagimport telemetry_helperimport ui.screen_slamfrom bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions.utils.tunable_icon import TunableIconfrom protocolbuffers import SimObjectAttributes_pb2 as protocols, Commodities_pb2from sims.sim_info_tests import SimInfoGameplayOptionsTestfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryfrom sims4.math import Thresholdfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import OptionalTunable, TunableList, Tunable, TunableMapping, TunableTuple, TunableEnumEntry, TunableResourceKey, TunableRange, TunableReference, TunableColorfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import constproperty, classproperty, flexmethodfrom singletons import DEFAULTfrom statistics.commodity_messages import send_sim_ranked_stat_update_message, send_sim_ranked_stat_change_rank_change_update_messagefrom statistics.progressive_statistic_callback_mixin import ProgressiveStatisticCallbackMixinfrom statistics.statistic_enums import StatisticLockActionfrom ui.ui_dialog_notification import UiDialogNotificationfrom ui.ui_flyaway_enums import UIFlyAwayLocationslogger = sims4.log.Logger('RankedStatistic', default_owner='rfleig')TELEMETRY_GROUP_RANKED_STAT = 'RKST'TELEMETRY_HOOK_RANKED_STAT_LEVEL_CHANGE = 'LEVE'TELEMETRY_FIELD_RANKED_STAT_TYPE = 'type'TELEMETRY_FIELD_RANKED_STAT_LEVEL = 'leve'TELEMETRY_FIELD_RANKED_STAT_PREV = 'pvrk'TELEMETRY_FIELD_RANKED_STAT_ALIGNMENT_SCORE = 'alsc'ranked_stat_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_RANKED_STAT)
class RankedStatistic(ProgressiveStatisticCallbackMixin, statistics.continuous_statistic_tuning.TunedContinuousStatistic, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)):

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        ranks_tuned = [level_data for level_data in cls.event_data.values() if level_data.rank_up]
        ranks_needed = len(ranks_tuned) + 1
        actual_ranks = len(cls.rank_tuning)
        tuned_rank_up_notifications = len(cls.rank_up_notification_tuning)
        tuned_rank_down_notifications = len(cls.rank_down_notification_tuning)
        if actual_ranks != ranks_needed:
            logger.error('{} ranks have been enabled, but there is tuning for {} ranks in the rank_tuning. Please double check the tuning for {}', ranks_needed, actual_ranks, cls)
        if actual_ranks != tuned_rank_up_notifications:
            logger.error('There are {} ranks tuned but {} rank up notifications tuned. These need to be the same. Please double check the tuning for {}', actual_ranks, tuned_rank_up_notifications, cls)
        if tuned_rank_down_notifications > 0 and actual_ranks != tuned_rank_down_notifications:
            logger.error('There are {} ranks tuned but {} rank down notifications tuned. These need to be the same. Please double check the tuning for {}', actual_ranks, tuned_rank_down_notifications, cls)

    INSTANCE_TUNABLES = {'stat_name': TunableLocalizedString(description='\n            Localized name of this statistic.\n            ', allow_none=True), 'event_intervals': TunableList(description='\n            The level boundaries for an event, specified as a delta from the\n            previous value.\n            ', tunable=Tunable(description='\n                Points required to reach this level.\n                ', tunable_type=int, default=0), export_modes=ExportModes.All), 'event_data': TunableMapping(description='\n            The data associated with a specific tuned event. \n            \n            The Key is the event number as tuned in the event intervals.\n            \n            The value is a list of loots to apply when the event occurs and an\n            bool for whether or not to rank up the stat. \n            ', key_type=int, value_type=TunableTuple(description='\n                The data associated with a tuned event from event_intervals.\n                ', rank_up=Tunable(description="\n                    If checked then this event will cause the statistic to rank\n                    up and all that entails. Currently that will increment\n                    the rank count.\n                    \n                    There should be a rank up entry for each of the levels \n                    tuned, except the initial rank. We assume that you don't \n                    need to rank into the initial rank. This means you will \n                    need one more level tuned than number of rank up events\n                    found in this list.\n                    ", tunable_type=bool, default=False), loot=TunableList(description='\n                    A list of loots to apply when this event happens. This loot\n                    is only applied the first time you reach a specific level.\n                    If you want the loot applied every time you reach a level\n                    (for instance after you decay to a previous level and then\n                    regain a level) please use the loot_always tuning.\n                    ', tunable=TunableReference(description='\n                        The loot to apply.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), tooltip=TunableLocalizedStringFactory(description='\n                    The tooltip to display in the UI for each of the event\n                    lines. This is to be used for telling the user what loot \n                    they are going to get at an individual event.\n                    '), level_down_loot=TunableList(description='\n                    A list of loots to apply when the Sim loses enough points \n                    to level down.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), tests=event_testing.tests.TunableTestSet(description="\n                    Tests to run when reaching this level. If the tests don't \n                    pass then the value will be set back to min points for \n                    the rank before it. This means that the Sim won't be able\n                    to make any progress towards the rank with the failed\n                    tests.\n                    ", export_modes=ExportModes.ServerXML), loot_always=TunableList(description='\n                    This loot is always awarded on level up, regardless of \n                    whether or not this level has already been achieved or not.\n                    \n                    If you want the loot to only be applied the first time you\n                    reach a certain level then please use the loot tuning.\n                    ', tunable=TunableReference(description='\n                        The loot to award on level up.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), loot_always_on_load=TunableList(description='\n                    This loot is always awarded when a sim loads with this\n                    level.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), export_class_name='EventDataTuple'), tuple_name='TunableEventData', export_modes=ExportModes.All), 'initial_rank': Tunable(description='\n            The offset of the initial rank for this stat in UI.\n            \n            The use case of initial rank is if the display of the stat\n            in UI needs to start with an initial fill (e.g. Occult Tracker),\n            or if the fill first starts as empty (e.g. Fame). Discuss with UI\n            what is required.\n            ', tunable_type=int, default=1, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'rank_tuning': TunableMapping(description='\n            This is the tuning that is associated with a specific rank level \n            instead of each individual event level. When the rank has increased \n            the matching information will be retrieved from here and used.\n            \n            There needs to be an equal number of ranks tuned to match all of \n            the rank up events in event data plus an extra one for the \n            rank you start out on initially.\n            ', key_type=int, value_type=TunableTuple(description='\n                A tuple of all the data for each Rank associated wit this\n                ranked statistic.\n                ', rank_name=TunableLocalizedString(description="\n                    The rank's normal name.\n                    "), icon=OptionalTunable(description='\n                    If enabled then the Rank Statistic will have an icon \n                    associated with this Rank.\n                    ', tunable=TunableResourceKey(description='\n                        Icon to be displayed for the rank.\n                        ', resource_types=sims4.resources.CompoundTypes.IMAGE), enabled_by_default=True), rank_description=OptionalTunable(description='\n                    When enabled this string will be used as the description\n                    for the rank.\n                    ', tunable=TunableLocalizedString(description="\n                        The rank's description.\n                        ")), rank_short_name=OptionalTunable(description='\n                    When enabled this string will be used as an alternate \n                    short name for the rank.\n                    ', tunable=TunableLocalizedString(description="\n                        The rank's short name.\n                        ")), rank_color=TunableColor.TunableColorRGBA(description='\n                    Tunable color tint provided by the rank.\n                    ', export_modes=(ExportModes.ClientBinary,), tuning_group=GroupNames.UI), hide_in_ui=Tunable(description='\n                    If checked, this rank will not be shown in some places in the UI (XP bars, Relationship tooltip, Gallery)\n                    ', tunable_type=bool, default=False), export_class_name='RankDataTuple'), tuple_name='TunableRankData', export_modes=ExportModes.All), 'rank_down_notification_tuning': TunableMapping(description='\n            A mapping of Rank to tuning needed to display all the notifications\n            when a Sim ranks down. \n            \n            The number of notifications tuned must match the number of items\n            in rank_tuning.\n            ', key_type=int, value_type=TunableTuple(description='\n                A Tuple containing both the rank down screen slam and the rank\n                down notification to display.\n                ', show_notification_tests=event_testing.tests.TunableTestSet(description='\n                    Tests that must be true when the we want to show notification.\n                    '), rank_down_screen_slam=OptionalTunable(description='\n                    Screen slam to show when Sim goes down to this rank level.\n                    Localization Tokens: Sim - {0.SimFirstName}, Rank Name - \n                    {1.String}, Rank Number - {2.Number}\n                    ', tunable=ui.screen_slam.TunableScreenSlamSnippet()), rank_down_notification=OptionalTunable(description='\n                    The notification to display when the Sim obtains this\n                    rank. The text will be provided two tokens: the Sim owning\n                    the stat and a number representing the 1-based rank\n                    level.\n                    ', tunable=UiDialogNotification.TunableFactory(locked_args={'text_tokens': DEFAULT, 'icon': None, 'secondary_icon': None})))), 'rank_up_notification_tuning': TunableMapping(description='\n            A mapping of Rank to tuning needed to display all the notifications\n            when a Sim ranks up. \n            \n            The number of notifications tuned must match the number of items\n            in rank_tuning.\n            ', key_type=int, value_type=TunableTuple(description='\n                A Tuple containing both the rank up screen slam and the rank\n                up notification to display.\n                ', show_notification_tests=event_testing.tests.TunableTestSet(description='\n                    Tests that must be true when the we want to show notification.\n                    '), rank_up_screen_slam=OptionalTunable(description='\n                    Screen slam to show when reaches this rank level.\n                    Localization Tokens: Sim - {0.SimFirstName}, Rank Name - \n                    {1.String}, Rank Number - {2.Number}\n                    \n                    This will only happen the first time a rank is reached.\n                    ', tunable=ui.screen_slam.TunableScreenSlamSnippet()), rank_up_notification=OptionalTunable(description='\n                    The notification to display when the Sim obtains this\n                    rank. The text will be provided two tokens: the Sim owning\n                    the stat and a number representing the 1-based rank\n                    level.\n                    \n                    This will only happen the first time a rank is reached. If\n                    you want to show a display on subsequent rank ups you can \n                    tune the re_rank_up_notifcation.\n                    ', tunable=UiDialogNotification.TunableFactory(locked_args={'text_tokens': DEFAULT, 'icon': None, 'secondary_icon': None})), re_rank_up_notification=OptionalTunable(description='\n                    The notification to display when the Sim obtains this rank\n                    every time other than the first time. For instance if the\n                    Sim achieves rank 3, drops down to rank 2 because of decay,\n                    and then re-achieves rank 3, that is when this dialog will\n                    be displayed.\n                    \n                    If you want this dialog to be displayed the first time the\n                    Sim reaches a rank please tune rank_up_notification instead.\n                    ', tunable=UiDialogNotification.TunableFactory(locked_args={'text_tokens': DEFAULT, 'icon': None, 'secondary_icon': None})))), 'tags': TunableList(description='\n            The associated categories of the ranked statistic.\n            ', tunable=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)), 'icon': TunableIcon(description="\n            The ranked stat's icon.\n            ", allow_none=True, export_modes=ExportModes.All), 'initial_loot_for_visible_stat': TunableList(description='\n            A list of loots to apply when the Sim first receives this ranked\n            statistic.\n            \n            NOTE: If the "visible" field below is set to false (unchecked), then we do NOT support using initial loots. \n            If you need an initial loot on a statistic without "visible" checked, then whatever system is adding the\n            stat is responsible for adding the loot. We cannot do it here because of an issue where the loot will be\n            reapplied every time we add this statistic, but when it decays to its convergence value we remove the \n            statistic.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'min_decay_per_highest_level_achieved': TunableMapping(description='\n            A mapping of highest level reached to the absolute minimum \n            that this Ranked Stat is allowed to decay to in ranks.\n            ', key_type=int, value_type=TunableRange(description='\n                The lowest level this stat can decay to based on the associated\n                highest level reached.\n                ', tunable_type=int, minimum=1, default=1)), 'associated_bucks_types': TunableList(description='\n            A list of bucks types that are associated with this ranked stat.\n            These bucks types may have tuned data that is affected by ranking\n            up/down.\n            ', tunable=TunableEnumEntry(description='\n                A buck type that is associated with this ranked stat.\n                ', tunable_type=BucksType, default=BucksType.INVALID), unique_entries=True, export_modes=ExportModes.All), 'zero_out_on_lock': Tunable(description='\n            If checked, when this ranked stat is locked it will zero out\n            the value, highest_level, and bucks.\n            ', tunable_type=bool, default=True), 'headline': OptionalTunable(description='\n            If enabled when this relationship track updates we will display\n            a headline update to the UI.\n            ', tunable=TunableReference(description='\n                The headline that we want to send down.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HEADLINE)), tuning_group=GroupNames.UI), 'send_stat_update_for_npcs': Tunable(description="\n            If checked then whenever we attempt to send the ranked stat update\n            message it will be sent, even if the Sim is an NPC.\n            \n            NOTE: We don't want to mark very many of the stats like this. This \n            is being done to make sure that Fame gets sent so we don't have\n            to request Fame when building the tooltip for sims which could be\n            really slow.\n            ", tunable_type=bool, default=False), 'center_bar_tooltip': Tunable(description='\n            If true, always put motive panel ranked stat bar tooltip at the center.\n            If false, put tooltip on each increment mark instead.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All), 'visible': Tunable(description="\n            Whether or not statistic should be sent to client.\n            \n            NOTE: Please work with your UI engineering partner to determine if this \n            should be True. If False, for performance reasons, \n            the stat will be removed from the sim if their\n            current value matches the default convergence value. \n            \n            NOTE: If this is left false, then we do NOT support using initial loots above. If you need this to \n            be false but also want an initial loot, then whatever is triggering this statistic will need to handle\n            whatever loot. This is to prevent us continually giving the loot as this decays and gets readded. Since we\n            do not remove the stat if this is set to true this problem doesn't exist and initial loots are allowed.\n            ", tunable_type=bool, default=False, export_modes=ExportModes.All), 'rank_down_inclusive': Tunable(description='\n            If True, rank-down will occur when the stat value hits the\n            threshold boundary between ranks. Otherwise, rank down will use the\n            default behavior and rank down once the threshold is crossed.\n            \n            For example: a ranked stat has two levels, level 1 with a range of 0-10, \n            level 2 with a range of 10-20, and the current value and level are 15 and 2.\n            If the stat was decremented by 5, setting the value to exactly the\n            threshold boundary of 10, inclusive rules will calculate the new level as 1,\n            whereas exclusive rules will calculate the level as 2. Exclusive rank-downs are\n            the default behavior.\n            ', tunable_type=bool, default=False), 'zero_point': Tunable(description='\n            The value of the statistic that represents no progress. Values less\n            than the zero-point value represent negative progress. Values greater\n            than the zero-point value represent positive progress.\n            ', tunable_type=int, default=1, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'display_updates_from_add': Tunable(description="\n            If True, any rank updates that occur when setting the initial\n            value will be sent to UI. If False, only changes in the\n            stat's value from its initial value will be displayed.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.UI), 'bar_color_override': TunableColor.TunableColorRGBA(description='\n            Tunable color tint on the progress bar.\n            ', export_modes=(ExportModes.ClientBinary,), tuning_group=GroupNames.UI), 'starting_rank_display_value': Tunable(description="\n            The rank of the stat when it is first added. Used for\n            display before the stat has been initialized. \n            \n            The starting rank is derived from the tuned event\n            intervals and the threshold that corresponds to\n            the stat's initial value.\n            ", tunable_type=int, default=1, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'gameplay_options_test': OptionalTunable(description='\n            If enabled, run a GameplayOptions test to see if we can add this statistic.\n            ', tunable=SimInfoGameplayOptionsTest.TunableFactory(), tuning_group=GroupNames.TESTS), 'ui_flyaway_string': OptionalTunable(description='\n            If assigned, this will be the string used to trigger a flyaway on the UI when the value of this ranked stat changes.\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.UI)}
    REMOVE_INSTANCE_TUNABLES = ('min_value_tuning', 'max_value_tuning')

    def __init__(self, tracker):
        self._rank_level = self.initial_rank
        self._inclusive_rank_threshold = False
        self.highest_level = 0
        super().__init__(tracker, self.initial_value)
        self._current_event_level = 0
        self.previous_event_level = 0
        self._notifications_disabled = False
        self._initial_loots_awarded = False
        self._suppress_level_telemetry = False

    @classmethod
    def _verify_tuning_callback(cls):
        initial_value = cls.initial_value
        starting_rank = 1
        point_value = 0
        for (level, level_threshold) in enumerate(cls.get_level_list()):
            level += 1
            point_value += level_threshold
            if level_threshold == 0:
                break
            if (point_value > initial_value or point_value == initial_value) and cls.event_data[level].rank_up:
                starting_rank += 1
        if cls.starting_rank_display_value != starting_rank:
            logger.error(" {}: 'starting_rank_display_value' is {} and should be {}.", cls.__name__, cls.starting_rank_display_value, starting_rank)
        if cls.visible is False and len(cls.initial_loot_for_visible_stat):
            logger.error(' {}: visible is set to false but we have an initial loot. We should never have initial loot on a ranked statistic that can be removed due to returning to the default value. This will cause issues with future re-adding of the stat.', cls.__name__)

    @constproperty
    def is_ranked():
        return True

    @property
    def rank_level(self):
        return self._rank_level

    @property
    def process_non_selectable_sim(self):
        return True

    @rank_level.setter
    def rank_level(self, value):
        self._rank_level = value
        services.get_event_manager().process_event(TestEvent.RankedStatisticChange, sim_info=self.tracker.owner.sim_info)

    @property
    def highest_rank_achieved(self):
        rank_level = self.initial_rank
        for i in range(1, self.highest_level + 1):
            if self.event_data.get(i).rank_up:
                rank_level += 1
        return rank_level

    @property
    def is_visible(self):
        if self.tracker is None or not self.tracker.owner.is_sim:
            return False
        return self.visible

    def increase_rank_level(self, new_rank=True, from_add=False):
        self.rank_level += 1
        self._on_rank_up(new_rank=new_rank, from_add=from_add)

    def increase_rank_levels(self, levels):
        start_level = self.rank_level
        self.rank_level = start_level + levels
        self.send_rank_change_update_message(start_level, start_level + levels)

    def decrease_rank_level(self):
        previous_rank = self.rank_level
        self.rank_level = max(self.rank_level - 1, 0)
        self._on_rank_down()
        if not self.tracker.owner.is_npc:
            self._handle_level_change_telemetry(self.rank_level, previous_rank)

    def _on_rank_up(self, new_rank=True, from_add=False):
        current_rank = self.rank_level
        if from_add and self.display_updates_from_add:
            self.send_rank_change_update_message(current_rank - 1, current_rank)
        sim_info = self.tracker.owner.sim_info
        rank_data = self.rank_tuning.get(current_rank)
        rank_up_data = self.rank_up_notification_tuning.get(current_rank)
        if rank_data is None:
            logger.error('Sim {}: {} is trying to rank up to level {} but there is no rank tuning.', sim_info, self, current_rank)
            return
        if from_add or sim_info.is_selectable and rank_up_data is not None and self.can_show_notification(rank_up_data):
            icon_override = None if rank_data.icon is None else IconInfoData(icon_resource=rank_data.icon)
            if new_rank:
                self._show_initial_rank_up_notifications(sim_info, current_rank, rank_data, rank_up_data, icon_override)
            else:
                self._show_re_rank_up_notifications(sim_info, current_rank, rank_data, rank_up_data, icon_override)

    def _show_initial_rank_up_notifications(self, sim_info, current_rank, rank_data, rank_up_data, icon_override):
        if rank_up_data.rank_up_notification is not None:
            notification = rank_up_data.rank_up_notification(sim_info, resolver=SingleSimResolver(sim_info))
            notification.show_dialog(icon_override=icon_override, secondary_icon_override=IconInfoData(obj_instance=sim_info), additional_tokens=(current_rank,))
        if rank_up_data.rank_up_screen_slam is not None:
            rank_up_data.rank_up_screen_slam.send_screen_slam_message(sim_info, sim_info, rank_data.rank_name, current_rank)

    def _show_re_rank_up_notifications(self, sim_info, current_rank, rank_data, rank_up_data, icon_override):
        if rank_up_data.re_rank_up_notification is not None:
            notification = rank_up_data.re_rank_up_notification(sim_info, resolver=SingleSimResolver(sim_info))
            notification.show_dialog(icon_override=icon_override, secondary_icon_override=IconInfoData(obj_instance=sim_info), additional_tokens=(current_rank,))

    def _on_rank_down(self):
        current_rank = self.rank_level
        self.send_rank_change_update_message(current_rank + 1, current_rank)
        sim_info = self.tracker.owner.sim_info
        rank_data = self.rank_tuning.get(current_rank)
        rank_down_data = self.rank_down_notification_tuning.get(current_rank)
        if rank_data is None:
            logger.error('Sim {}: {} is trying to rank down to level {} but there is no rank tuning.', sim_info, self, current_rank)
            return
        if self.can_show_notification(rank_down_data):
            if rank_down_data.rank_down_notification is not None:
                notification = rank_down_data.rank_down_notification(sim_info, resolver=SingleSimResolver(sim_info))
                icon_override = None if rank_data.icon is None else IconInfoData(icon_resource=rank_data.icon)
                notification.show_dialog(icon_override=icon_override, secondary_icon_override=IconInfoData(obj_instance=sim_info), additional_tokens=(current_rank,))
            if rank_down_data.rank_down_screen_slam is not None:
                rank_down_data.rank_down_screen_slam.send_screen_slam_message(sim_info, sim_info, rank_data.rank_name, current_rank)
        for bucks_type in self.associated_bucks_types:
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(bucks_type, owner_id=self.tracker.owner.id)
            if bucks_tracker is not None:
                bucks_tracker.validate_perks(bucks_type, self.rank_level)

    @classmethod
    def can_add(cls, owner, force_add=False, from_load=False, **kwargs) -> bool:
        if force_add or from_load:
            return True
        elif super().can_add(owner, **kwargs):
            if cls.gameplay_options_test is not None:
                resolver = SingleSimResolver(owner)
                return resolver(cls.gameplay_options_test)
            else:
                return True
        return True
        return False

    def on_add(self):
        super().on_add()
        self.tracker.owner.sim_info.on_add_ranked_statistic()
        self.on_stat_event(self.highest_level, self.get_user_value(), from_add=True)
        self.previous_event_level = self.get_user_value()
        if self.tracker.owner.is_simulating and self.is_visible:
            self.apply_initial_loot()

    @classmethod
    def get_level_list(cls):
        return list(cls.event_intervals)

    @classmethod
    def get_level_threshold(cls, level):
        return sum(cls.get_level_list()[:level])

    @flexmethod
    def _get_level_calculation_function(cls, inst):
        if inst is not None and inst._inclusive_rank_threshold:
            return lambda current_value: current_value <= 0
        return lambda current_value: current_value < 0

    def _reset_rank_threshold_inclusivity(self):
        self._inclusive_rank_threshold = False

    def on_initial_startup(self):
        super().on_initial_startup()
        self.decay_enabled = self.tracker.owner.is_selectable and not self.tracker.owner.is_locked(self)

    @staticmethod
    def _callback_handler(stat_inst):
        stat_inst._reset_rank_threshold_inclusivity()
        new_level = stat_inst.get_user_value()
        stat_inst.on_stat_event(stat_inst.previous_event_level, new_level)
        stat_inst.previous_event_level = new_level
        stat_inst.refresh_threshold_callback()

    def on_stat_event(self, old_level, new_level, from_add=False):
        batch_rank_levels = 0
        while old_level < new_level:
            previous_level = old_level
            old_level += 1
            event_data = self.event_data.get(old_level)
            if event_data is not None:
                if self.tracker.owner.is_simulating:
                    resolver = SingleSimResolver(self.tracker.owner)
                    is_new_level = old_level > self.highest_level
                    if is_new_level:
                        for loot in event_data.loot:
                            loot.apply_to_resolver(resolver)
                        self.highest_level = old_level
                    if event_data.rank_up:
                        self.increase_rank_level(new_rank=is_new_level, from_add=from_add)
                    for loot in event_data.loot_always:
                        loot.apply_to_resolver(resolver)
                elif event_data.rank_up:
                    batch_rank_levels += 1
            if self.tracker.owner.is_npc:
                if not from_add:
                    self._handle_level_change_telemetry(old_level, previous_level)
            self._handle_level_change_telemetry(old_level, previous_level)
        if batch_rank_levels > 0:
            self.increase_rank_levels(batch_rank_levels)
        else:
            self.create_and_send_commodity_update_msg(is_rate_change=False)

    @contextlib.contextmanager
    def suppress_level_up_telemetry(self):
        if self._suppress_level_telemetry:
            yield None
        else:
            self._suppress_level_telemetry = True
            try:
                yield None
            finally:
                self._suppress_level_telemetry = False

    def _handle_level_change_telemetry(self, current_level, previous_level):
        if not self._suppress_level_telemetry:
            with telemetry_helper.begin_hook(ranked_stat_telemetry_writer, TELEMETRY_HOOK_RANKED_STAT_LEVEL_CHANGE, sim_info=self._tracker._owner) as hook:
                hook.write_guid(TELEMETRY_FIELD_RANKED_STAT_TYPE, self.guid64)
                hook.write_int(TELEMETRY_FIELD_RANKED_STAT_LEVEL, current_level)
                hook.write_int(TELEMETRY_FIELD_RANKED_STAT_PREV, previous_level)
                hook.write_int(TELEMETRY_FIELD_RANKED_STAT_ALIGNMENT_SCORE, self.get_value())

    @sims4.utils.classproperty
    def max_value(cls):
        return cls.get_max_skill_value()

    @sims4.utils.classproperty
    def min_value(cls):
        return 0

    @sims4.utils.classproperty
    def best_value(cls):
        return cls.max_value

    @sims4.utils.classproperty
    def max_rank(cls):
        (_, rank) = cls.calculate_level_and_rank(cls.max_value)
        return rank

    @flexmethod
    def convert_to_user_value(cls, inst, value):
        if not cls.get_level_list():
            return 0
        inst_or_cls = inst if inst is not None else cls
        level_fnc = inst_or_cls._get_level_calculation_function()
        current_value = value
        for (level, level_threshold) in enumerate(cls.get_level_list()):
            current_value -= level_threshold
            if level_fnc(current_value):
                return level
        return level + 1

    def can_show_notification(self, rank_data):
        if self._notifications_disabled:
            return False
        elif rank_data is not None and rank_data.show_notification_tests is not None:
            resolver = event_testing.resolver.SingleSimResolver(self.tracker.owner)
            result = rank_data.show_notification_tests.run_tests(resolver)
            if not result:
                return False
        return True

    def _get_next_level_threshold(self):
        if self._inclusive_rank_threshold:
            return Threshold(self._get_next_level_bound(), operator.gt)
        return Threshold(self._get_next_level_bound(), operator.ge)

    def set_value(self, value, *args, from_load=False, interaction=None, from_transfer=False, **kwargs):
        old_points = self.get_value()
        old_user_value = self.get_user_value()
        value_to_set = value
        if not from_load:
            value_to_set = self._get_valid_value(value, old_user_value)
        minimum_level = self._get_minimum_decay_level()
        value_to_set = max(value_to_set, minimum_level)
        super().set_value(value_to_set, *args, from_load=from_load, interaction=interaction, **kwargs)
        new_user_value = self.get_user_value()
        if not from_load:
            if value < old_points:
                if value == self.get_level_threshold(new_user_value):
                    self._inclusive_rank_threshold = True
                    new_user_value = self.get_user_value()
                self._handle_level_down(old_user_value, new_user_value)
            sim_info = self._tracker._owner
            new_points = self.get_value()
            stat_type = self.stat_type
            if old_points == self.initial_value or old_points != new_points:
                services.get_event_manager().process_event(TestEvent.StatValueUpdate, sim_info=sim_info, statistic=stat_type, custom_keys=(stat_type,))
        if from_transfer:
            self.rank_level = self.get_user_value()
        self.send_commodity_progress_msg(is_rate_change=False)
        self.send_change_update_message(value - old_points, from_load=from_load)
        self.send_ui_flyaway_message(value - old_points, from_load=from_load)
        self.previous_event_level = new_user_value
        self.refresh_threshold_callback()

    def _update_value(self):
        minimum_decay = self._get_minimum_decay_level()
        old_value = self._value
        old_user_value = self.convert_to_user_value(self._value)
        super()._update_value(minimum_decay_value=minimum_decay)
        new_value = self._value
        new_user_value = self.convert_to_user_value(self._value)
        self._handle_level_down(old_user_value, new_user_value)
        if old_user_value > new_user_value:
            self.previous_event_level = new_user_value
            self.refresh_threshold_callback()
        stat_type = self.stat_type
        if new_value > old_value:
            sim_info = self._tracker._owner if self._tracker is not None else None
            services.get_event_manager().process_event(TestEvent.StatValueUpdate, sim_info=sim_info, statistic=stat_type, custom_keys=(stat_type,))

    def _get_minimum_decay_level(self):
        min_rank = self.min_decay_per_highest_level_achieved.get(self.highest_level, None)
        if min_rank is None:
            return 0
        points = self.points_to_rank(min_rank)
        return points

    def _handle_level_down(self, old_value, new_value):
        while new_value < old_value:
            event_data = self.event_data.get(old_value)
            if event_data is not None:
                resolver = SingleSimResolver(self.tracker.owner)
                for loot in event_data.level_down_loot:
                    loot.apply_to_resolver(resolver)
                if event_data.rank_up:
                    self.decrease_rank_level()
            old_value -= 1

    def get_next_rank_level(self):
        current_value = self.get_user_value()
        index = current_value + 1
        if index > len(self.event_data):
            return current_value
        while not self.event_data[index].rank_up:
            if index == len(self.event_data):
                break
            index += 1
        return index

    @constproperty
    def remove_on_convergence():
        return False

    def send_commodity_progress_msg(self, is_rate_change=True):
        self.create_and_send_commodity_update_msg(is_rate_change=is_rate_change)

    @classmethod
    def points_to_level(cls, event_level):
        level = 0
        running_sum = 0
        level_list = cls.get_level_list()
        while level < len(level_list) and level < event_level:
            running_sum += level_list[level]
            level += 1
        return running_sum

    @classmethod
    def points_to_rank(cls, rank_level):
        rank = cls.initial_rank
        level = 0
        running_sum = 0
        level_list = cls.get_level_list()
        while rank < rank_level and level < len(level_list):
            event_data = cls.event_data.get(level)
            if cls.event_data[level].rank_up:
                rank += 1
            if event_data is not None and rank < rank_level:
                running_sum += level_list[level]
            level += 1
        return running_sum

    def points_to_current_rank(self):
        return self.points_to_rank(self.rank_level)

    def create_and_send_commodity_update_msg(self, is_rate_change=True, allow_npc=False, from_add=False):
        ranked_stat_msg = Commodities_pb2.RankedStatisticProgressUpdate()
        ranked_stat_msg.stat_id = self.guid64
        ranked_stat_msg.change_rate = self.get_change_rate()
        ranked_stat_msg.rank = self.rank_level
        difference = self.get_value() - self.points_to_current_rank()
        ranked_stat_msg.curr_rank_points = int(difference) if difference > 0 else 0
        send_sim_ranked_stat_update_message(self.tracker.owner, ranked_stat_msg, allow_npc=allow_npc or self.send_stat_update_for_npcs)

    @classmethod
    def send_commodity_update_message(cls, sim_info, old_value, new_value):
        commodity_tracker = sim_info.commodity_tracker
        if commodity_tracker is None:
            return
        stat_instance = commodity_tracker.get_statistic(cls)
        if stat_instance is None:
            return
        stat_instance.create_and_send_commodity_update_msg(is_rate_change=True)

    def send_change_update_message(self, amount, from_load=False):
        if from_load:
            return
        if self.headline is None:
            return
        sim = self.tracker.owner
        if sim.is_selectable:
            self.headline.send_headline_message(sim, amount)

    def send_ui_flyaway_message(self, amount:int, from_load:bool=False) -> None:
        if self.ui_flyaway_string is None:
            return
        if from_load:
            return
        if amount == 0:
            return
        sim = self.tracker.owner
        if sim.is_selectable:
            text = self.ui_flyaway_string(amount)
            op = distributor.ops.TriggerUIFlyAway(sim.sim_id, text, 'good' if amount > 0 else 'bad', UIFlyAwayLocations.FLYAWAY_LOCATION_ASPIRATION_PANEL_BUTTON)
            Distributor.instance().add_op(sim, op)

    def send_rank_change_update_message(self, previous_rank, current_rank):
        msg = Commodities_pb2.RankedStatisticRankChangedUpdate()
        msg.stat_id = self.guid64
        msg.previous_rank = previous_rank
        msg.current_rank = current_rank
        send_sim_ranked_stat_change_rank_change_update_message(self.tracker.owner, msg)
        self.send_commodity_progress_msg()

    def on_sim_ready_to_simulate(self):
        level = self.get_user_value()
        event_data = self.event_data.get(level)
        if event_data is not None:
            resolver = SingleSimResolver(self.tracker.owner)
            for loot in event_data.loot_always_on_load:
                loot.apply_to_resolver(resolver)
        self.apply_initial_loot()

    def apply_initial_loot(self):
        if not self.initial_loot_for_visible_stat:
            return
        if self._initial_loots_awarded:
            return
        resolver = SingleSimResolver(self.tracker.owner)
        for loot in self.initial_loot_for_visible_stat:
            loot.apply_to_resolver(resolver)
        self._initial_loots_awarded = True

    def _get_valid_value(self, value, old_score):
        new_score = self.convert_to_user_value(value)
        if old_score <= new_score:
            resolver = SingleSimResolver(self.tracker.owner)
            while old_score <= new_score:
                old_score += 1
                event_data = self.event_data.get(old_score)
                if event_data is not None and not event_data.tests.run_tests(resolver=resolver):
                    points = self.points_to_level(old_score - 1)
                    return points
        return value

    def on_lock(self, action_on_lock):
        self._notifications_disabled = True
        should_zero_out = self.zero_out_on_lock or action_on_lock == StatisticLockAction.USE_MIN_VALUE_TUNING
        if should_zero_out:
            self.highest_level = 0
        super().on_lock(action_on_lock)
        if should_zero_out:
            self.reset_bucks()
        self._notifications_disabled = False

    def reset_bucks(self):
        for bucks_type in self.associated_bucks_types:
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(bucks_type, self.tracker.owner.id)
            if bucks_tracker is not None:
                bucks_tracker.try_modify_bucks(bucks_type, -bucks_tracker.get_bucks_amount_for_type(bucks_type))

    @flexmethod
    def calculate_level_and_rank(cls, inst, value):
        level = 0
        rank = cls.initial_rank
        inst_or_cls = inst if inst is not None else cls
        level_fnc = inst_or_cls._get_level_calculation_function()
        for points_to_next_level in cls.get_level_list():
            value -= points_to_next_level
            if level_fnc(value):
                break
            level += 1
            level_data = cls.event_data.get(level)
            if level_data is not None and level_data.rank_up:
                rank += 1
        return (level, rank)

    def set_level_and_rank(self):
        (level, rank) = self.calculate_level_and_rank(self.get_value())
        self.previous_event_level = level
        self.rank_level = rank

    def should_display_delayed_decay_warning(self):
        if self.highest_level == 0:
            return False
        return super().should_display_delayed_decay_warning()

    @classproperty
    def valid_for_stat_testing(cls):
        return True

    @classmethod
    def load_statistic_data(cls, tracker, data):
        super().load_statistic_data(tracker, data)
        stat = tracker.get_statistic(cls)
        if stat is not None:
            stat._initial_loots_awarded = data.initial_loots_awarded
            stat._inclusive_rank_threshold = data.inclusive_rank_threshold
            stat.set_level_and_rank()
            stat.highest_level = data.highest_level
            stat.load_time_of_last_value_change(data)
            stat.fixup_callbacks_during_load()

    @classmethod
    def save_for_delayed_active_lod(cls, commodity_proto, commodities, skills, ranked_statistics):
        ranked_statistics.append(commodity_proto)

    def get_save_message(self, tracker):
        message = protocols.RankedStatistic()
        message.name_hash = self.guid64
        message.value = self.get_saved_value()
        message.highest_level = self.highest_level
        message.initial_loots_awarded = self._initial_loots_awarded
        message.inclusive_rank_threshold = self._inclusive_rank_threshold
        if self._time_of_last_value_change:
            message.time_of_last_value_change = self._time_of_last_value_change.absolute_ticks()
        return message

    def save_statistic(self, commodities, skills, ranked_statistics, tracker):
        ranked_statistics.append(self.get_save_message(tracker))
