from __future__ import annotationsimport argparseimport servicesimport sims4from distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom event_testing.resolver import SingleSimResolverfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, TunablePackSafeReference, TunableList, TunableTuplefrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.custom_states.custom_states_situation import CustomStatesSituationfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationDisplayType, SituationUserFacingType, SituationSerializationOptionfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from rewards.reward import Reward
    from Situations_pb2 import SituationLevelUpdate
    from situations.situation_goal import SituationGoal
    from typing import *logger = sims4.log.Logger('Pivotal Moments Situation', default_owner='asantos')
class QuestPopupSupression:
    suppress_quest_popups = False

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(QuestPopupSupression, cls).__new__(cls)
            parser = argparse.ArgumentParser()
            parser.add_argument('--SuppressQuestPopups', default=False, action='store_true')
            (args, unused_args) = parser.parse_known_args()
            cls.instance.suppress_quest_popups = args.SuppressQuestPopups
        return cls.instance

class PivotalMomentSituation(CustomStatesSituation):
    INSTANCE_TUNABLES = {'potential_rewards': TunableList(description='\n            List of potential Rewards among which only one is to be given when completing this situation.\n            The first one passing its tests will be given.\n            ', tunable=TunableTuple(reward=TunableReference(description='\n                    One of the rewards the situation can give upon completion.\n            ', manager=services.get_instance_manager(sims4.resources.Types.REWARD)))), 'pivotal_moment': TunablePackSafeReference(description='\n            Pivotal moment related to this situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='PivotalMoment'), 'loots_on_run': TunableList(description='\n            Loot Actions that will be applied to the active sim when the situation starts/load.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)))}
    REMOVE_INSTANCE_TUNABLES = ('_level_data', 'screen_slam_gold', 'screen_slam_silver', 'screen_slam_bronze', 'screen_slam_no_medal', '_cost', 'compatible_venues', 'venue_invitation_message', 'venue_situation_player_job', 'category', 'max_participants', '_initiating_sim_tests', '_icon', 'entitlement', 'job_display_ordering', 'situation_display_type_override')

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._canceled = False
        self._completed = False

    @property
    def cancelable(self) -> 'bool':
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            return self.situation_cancelable
        if not tutorial_service.is_pivotal_moment_active_quest(self.get_pivotal_moment_id()):
            return self.situation_cancelable
        return tutorial_service.is_quest_situation_cancelable(self.guid64)

    @property
    def user_facing_type(self) -> 'SituationUserFacingType':
        return SituationUserFacingType.PIVOTAL_MOMENT

    @classproperty
    def allow_non_prestige_events(cls) -> 'bool':
        return True

    @classmethod
    def get_predefined_guest_list(cls):
        sim_info = services.active_sim_info()
        sim_id = 0 if sim_info is None else sim_info.id
        guest_list = SituationGuestList(invite_only=True, host_sim_id=sim_id)
        for sim_info in services.active_household():
            guest_list.add_guest_info(SituationGuestInfo(sim_info.id, cls.resident_job(), RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_HOSTING))
        return guest_list

    def start_situation(self):
        super().start_situation()
        self._run_startup_loots()

    def load_situation(self):
        result = super().load_situation()
        if result:
            self._run_startup_loots()
        return result

    def get_pivotal_moment_id(self) -> 'int':
        return self.pivotal_moment.guid64

    def get_reward(self) -> 'Optional[Reward]':
        sim_info = services.active_sim_info()
        if not self.potential_rewards:
            return
        for potential_reward in self.potential_rewards:
            if potential_reward.reward.is_valid(sim_info):
                return potential_reward.reward

    def on_refresh_completed_goals(self, goal:'SituationGoal') -> 'None':
        goals = self.get_situation_goal_info()
        if len(goals) == 0:
            self._completed = True
            self._self_destruct()

    def pre_destroy(self) -> 'None':
        self._canceled = True
        self._self_destruct()
        self.send_situation_canceled_telemetry()

    def on_remove(self) -> 'None':
        super().on_remove()
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            return
        pivotal_moment_inst = tutorial_service.get_pivotal_moment_inst(self.get_pivotal_moment_id())
        if pivotal_moment_inst is None:
            return
        if self._canceled:
            pivotal_moment_inst.on_situation_canceled()
        elif self._completed:
            rewarded = tutorial_service.is_pivotal_moment_rewarded(self.pivotal_moment.guid64)
            is_pivotal_moment_from_quest = tutorial_service.is_pivotal_moment_active_quest(self.pivotal_moment.guid64)
            quest_supressor = QuestPopupSupression()
            popup_is_suppressed = is_pivotal_moment_from_quest and quest_supressor.suppress_quest_popups
            reward = self.get_reward()
            if reward is not None:
                if not popup_is_suppressed:
                    pivotal_moment_inst.show_outcome_dialog(self.display_name, reward, rewarded, self.display_style)
                if not rewarded:
                    reward.give_reward(services.active_sim_info())
            pivotal_moment_inst.on_pivotal_moment_complete(not rewarded)

    def on_situation_goal_completed(self, completed_goal:'SituationGoal') -> 'None':
        if completed_goal is None:
            return
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is None:
            return
        pivotal_moment_inst = tutorial_service.get_pivotal_moment_inst(self.get_pivotal_moment_id())
        if pivotal_moment_inst is None:
            return
        pivotal_moment_inst.on_pivotal_moment_goal_complete(completed_goal.guid64)

    def build_situation_level_update_message_internal(self, delta:'int'=0) -> 'SituationLevelUpdate':
        from protocolbuffers import Situations_pb2
        level_msg = Situations_pb2.SituationLevelUpdate()
        level_msg.score_upper_bound = 0
        level_msg.current_level = 0
        reward = self.get_reward()
        if reward is not None:
            build_icon_info_msg(IconInfoData(icon_resource=reward.icon), reward.name, level_msg.level_icon, tooltip=reward.reward_description)
        return level_msg

    def offer_initial_situation_goals(self):
        if self._seed and self._seed.goal_tracker_seedling and not self._seed.goal_tracker_seedling.minor_goals:
            logger.error('Pivotal Moment Situation {} has no minor goals saved, but we expect it to. Re-offering situation goals', self)
            self._goal_tracker.refresh_goals()
        else:
            self.on_first_assignment_pass_completed()

    def _run_startup_loots(self) -> 'None':
        if self.loots_on_run:
            resolver = SingleSimResolver(services.active_sim_info())
            for loot_action in self.loots_on_run:
                loot_action.apply_to_resolver(resolver)

    @classproperty
    def situation_live_event_id(cls) -> 'int':
        ret_val = super().situation_live_event_id
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None:
            pivId = cls.pivotal_moment.guid64
            event_id_list = tutorial_service.get_live_event_id_for_quest(pivId)
            ret_val = next(iter(event_id_list), 0)
        return ret_val

    @property
    def situation_display_type(self) -> 'int':
        event_id = self.situation_live_event_id
        if event_id != 0:
            return SituationDisplayType.LIVE_EVENT
        else:
            return super().situation_display_type

    @classproperty
    def situation_display_type_override(cls) -> 'int':
        event_id = cls.situation_live_event_id
        if event_id != 0:
            return SituationDisplayType.LIVE_EVENT
        else:
            return SituationDisplayType.PIVOTAL_MOMENT
