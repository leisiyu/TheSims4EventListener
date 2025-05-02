from __future__ import annotationsfrom event_testing.test_events import TestEventfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from clubs.club_tuning import ClubRule
    from interactions.payment.payment_info import PaymentBusinessRevenueType
    from interactions.utils.loot import LootActions
    from objects.game_object import GameObjectimport alarmsimport clockimport event_testingimport servicesimport sims4from event_testing.resolver import SingleSimResolver, DataResolverfrom interactions.base.interaction import Interactionfrom interactions.small_business_satisfaction_liability import SmallBusinessSatisfactionLiabilityfrom sims4.math import clampfrom sims.sim_info import SimInfofrom small_business.small_business_debug import update_small_business_situation_debug_visualizerfrom small_business.small_business_tuning import SmallBusinessTunableslogger = sims4.log.Logger('SmallBusinessWaitSatisfaction', default_owner='pgoujet')WAITING_TIMER_TOKEN = 'waiting_timer_id'WAITING_OCCURRENCES_TOKEN = 'occurrences_id'HAS_PERFORM_INTERACTION_TOKEN = 'has_perform_interaction_id'IS_PERFORMING_INTERACTION_TOKEN = 'is_performing_interaction_id'TIME_START_LOGIC_TOKEN = 'time_start_id'TOTAL_TIME_WAITING_TOKEN = 'total_time_waiting_id'LAST_INTERACTION_TIME_TOKEN = 'last_interaction_time_id'LAST_WAITING_TIME_CHECK_TOKEN = 'last_waiting_check_id'CURRENT_INDEX_RATIO_TOKEN = 'current_index_ratio_id'CURRENT_COUNTER_INTERACTION_TOKEN = 'current_counter_interaction'CURRENT_MARKUP_RATIO = 'current_markup_ratio'CURRENT_MARKUP_REWARD_KEY = 'current_markup_reward_key'
class SmallBusinessCustomerSatisfaction:

    def __init__(self):
        self.sim = None
        self._waiting_timers_data = None
        self._waiting_ratio_rewards_data = None
        self._start_value_waiting_ratio = 0.0
        self._interaction_count_rewards_data = None
        self._perform_interaction = False
        self.registered_affordances = []
        self._alarm_waiting_time = None
        self._has_perform_any_interaction = False
        self._number_occurrences_waiting = 0
        self._alarm_activity_timer = None
        self._alarm_check_waiting_ratio = None
        self._customer_start_time = 0.0
        self._total_time_waiting = 0.0
        self._last_interaction_time = 0.0
        self._last_waiting_time_check = 0.0
        self._current_index_waiting_ratio = 0
        self._interaction_counter = 0
        self._current_wait_ratio = 0.0
        self._markup_ratio_per_payment_type = None
        self._markup_ratio_per_markup_value = None
        self._current_markup_ratio = 0.0
        self._satisfaction_markup_ratios_rewards = None
        self._current_markup_ratio_reward_key = None

    def get_is_performing_interaction(self) -> 'bool':
        return self._perform_interaction

    def get_wait_ratio(self) -> 'float':
        return self._current_wait_ratio

    def get_current_index_waiting_ratio(self) -> 'int':
        return self._current_index_waiting_ratio

    def get_interaction_count(self) -> 'int':
        return self._interaction_counter

    def get_current_markup_ratio(self) -> 'float':
        return self._current_markup_ratio

    def start(self, sim:'GameObject', rules:'[ClubRule]', waiting_timer_data:'[(float, LootActions)]', activity_timer_data:'(float, LootActions)', waiting_ratio_rewards:'[(float, LootActions)]', start_value_waiting_ratio:'float', interaction_count_rewards_data:'[(int, LootActions)]', satisfaction_markup_ratios_rewards:'[(float, LootActions)]', markup_ratio_per_payment_type:'[(PaymentBusinessRevenueType, float)]', markup_ratio_per_markup_value:'[(float, float)]', save_reader, guest_id:'int'):
        logger.debug('Start of Satisfaction Logic')
        self._perform_interaction = False
        self._has_perform_any_interaction = False
        self.sim = sim
        self._waiting_timers_data = waiting_timer_data
        self._activity_timer_data = activity_timer_data
        self._waiting_ratio_rewards_data = waiting_ratio_rewards
        self._start_value_waiting_ratio = start_value_waiting_ratio
        self._interaction_count_rewards_data = interaction_count_rewards_data
        self._satisfaction_markup_ratios_rewards = satisfaction_markup_ratios_rewards
        self._markup_ratio_per_payment_type = markup_ratio_per_payment_type
        self._markup_ratio_per_markup_value = markup_ratio_per_markup_value
        self._interaction_counter = 0
        self._current_markup_ratio = 0.0
        self._current_markup_ratio_reward_key = None
        current_time = services.time_service().sim_now.absolute_minutes()
        self._customer_start_time = current_time
        self._last_interaction_time = current_time
        self._total_time_waiting = current_time
        self._last_waiting_time_check = current_time
        self._current_index_waiting_ratio = 0
        for rule in rules:
            for affordance in list(rule.action.affordances):
                services.get_event_manager().register_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, affordance)
                self.registered_affordances.append(affordance)
            for affordance_list in rule.action.affordance_lists:
                for affordance in affordance_list:
                    services.get_event_manager().register_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, affordance)
                    self.registered_affordances.append(affordance)
        services.get_event_manager().register(self, (event_testing.test_events.TestEvent.SmallBusinessPaymentRegistered,))
        self._load_data(save_reader, guest_id)

    def _load_data(self, save_reader, guest_id:'int'):
        timer_duration = None
        if save_reader is not None:
            guest_id_str = str(guest_id)
            timer_duration = save_reader.read_float(guest_id_str + WAITING_TIMER_TOKEN, None)
            self._number_occurrences_waiting = save_reader.read_uint8(guest_id_str + WAITING_OCCURRENCES_TOKEN, 0)
            self._has_perform_any_interaction = save_reader.read_bool(guest_id_str + HAS_PERFORM_INTERACTION_TOKEN, False)
            self._perform_interaction = save_reader.read_bool(guest_id_str + IS_PERFORMING_INTERACTION_TOKEN, False)
            self._customer_start_time = save_reader.read_float(guest_id_str + TIME_START_LOGIC_TOKEN, 0.0)
            self._total_time_waiting = save_reader.read_float(guest_id_str + TOTAL_TIME_WAITING_TOKEN, 0.0)
            self._last_interaction_time = save_reader.read_float(guest_id_str + LAST_INTERACTION_TIME_TOKEN, 0.0)
            self._last_waiting_time_check = save_reader.read_float(guest_id_str + LAST_WAITING_TIME_CHECK_TOKEN, 0.0)
            self._current_index_waiting_ratio = save_reader.read_uint8(guest_id_str + CURRENT_INDEX_RATIO_TOKEN, 0)
            self._interaction_counter = save_reader.read_uint16(guest_id_str + CURRENT_COUNTER_INTERACTION_TOKEN, 0)
            self._current_markup_ratio = save_reader.read_float(guest_id_str + CURRENT_MARKUP_RATIO, 0.0)
            self._current_markup_ratio_reward_key = save_reader.read_float(guest_id_str + CURRENT_MARKUP_REWARD_KEY, None)
        if timer_duration is not None:
            self._alarm_waiting_time = alarms.add_alarm(self, clock.interval_in_sim_minutes(timer_duration), self._waiting_timer_ended)
        else:
            self._start_waiting_timer(self._number_occurrences_waiting)
        if self._has_perform_any_interaction:
            self._alarm_check_waiting_ratio = alarms.add_alarm(self, clock.interval_in_sim_minutes(SmallBusinessTunables.SATISFACTION_WAITING_RATIO_FREQUENCY), self._check_ratio_timer_expired, False)

    def end(self):
        logger.debug('End of Satisfaction Logic')
        if self._has_perform_any_interaction:
            self._check_waiting_ratio(False, False)
        if self._alarm_waiting_time is not None:
            self._alarm_waiting_time.cancel()
            self._alarm_waiting_time = None
        if self._alarm_check_waiting_ratio is not None:
            self._alarm_check_waiting_ratio.cancel()
            self._alarm_check_waiting_ratio = None
        for affordance in self.registered_affordances:
            services.get_event_manager().unregister_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, affordance)
        services.get_event_manager().unregister(self, (event_testing.test_events.TestEvent.SmallBusinessPaymentRegistered,))

    def save_satisfaction_data(self, writer, guest_id:'int'):
        guest_id_str = str(guest_id)
        if self._alarm_waiting_time is not None:
            writer.write_float(guest_id_str + WAITING_TIMER_TOKEN, self._alarm_waiting_time.get_remaining_time().in_minutes())
        writer.write_uint8(guest_id_str + WAITING_OCCURRENCES_TOKEN, self._number_occurrences_waiting)
        writer.write_bool(guest_id_str + HAS_PERFORM_INTERACTION_TOKEN, self._has_perform_any_interaction)
        writer.write_bool(guest_id_str + IS_PERFORMING_INTERACTION_TOKEN, self._perform_interaction)
        writer.write_float(guest_id_str + TIME_START_LOGIC_TOKEN, self._customer_start_time)
        writer.write_float(guest_id_str + TOTAL_TIME_WAITING_TOKEN, self._total_time_waiting)
        writer.write_float(guest_id_str + LAST_INTERACTION_TIME_TOKEN, self._last_interaction_time)
        writer.write_float(guest_id_str + LAST_WAITING_TIME_CHECK_TOKEN, self._last_waiting_time_check)
        writer.write_uint8(guest_id_str + CURRENT_INDEX_RATIO_TOKEN, self._current_index_waiting_ratio)
        writer.write_uint16(guest_id_str + CURRENT_COUNTER_INTERACTION_TOKEN, self._interaction_counter)
        writer.write_float(guest_id_str + CURRENT_MARKUP_RATIO, self._current_markup_ratio)
        if self._current_markup_ratio_reward_key is not None:
            writer.write_float(guest_id_str + CURRENT_MARKUP_REWARD_KEY, self._current_markup_ratio_reward_key)

    def _start_waiting_ratio(self):
        current_time = services.time_service().sim_now.absolute_minutes()
        self._last_interaction_time = current_time
        self._total_time_waiting = (current_time - self._customer_start_time)*self._start_value_waiting_ratio
        self._last_waiting_time_check = current_time
        self._current_index_waiting_ratio = self._get_index_waiting_ratio(self._start_value_waiting_ratio)

    def handle_event(self, sim_info:'SimInfo', event, resolver):
        if sim_info and sim_info.sim_id == self.sim.id:
            if event == event_testing.test_events.TestEvent.InteractionStart:
                self._start_interaction(resolver.interaction)
        elif event == event_testing.test_events.TestEvent.SmallBusinessPaymentRegistered:
            self._handle_small_business_payment_registered_event(resolver)

    def _start_interaction(self, interaction):
        if not any(isinstance(liability, SmallBusinessSatisfactionLiability) for liability in interaction.liabilities):
            self._interaction_counter += 1
            logger.debug('Interaction {} started {}', self._interaction_counter, interaction)
            self._perform_interaction = True
            current_time = services.time_service().sim_now.absolute_minutes()
            self._total_time_waiting += current_time - self._last_interaction_time
            self._last_waiting_time_check = current_time
            if self._alarm_check_waiting_ratio is not None:
                self._alarm_check_waiting_ratio.cancel()
                self._alarm_check_waiting_ratio = None
            if self._alarm_waiting_time is not None:
                self._alarm_waiting_time.cancel()
                self._alarm_waiting_time = None
            if self._activity_timer_data is not None:
                self._alarm_activity_timer = alarms.add_alarm(self, clock.interval_in_sim_minutes(self._activity_timer_data.timer), self._activity_timer_expired)
            small_business_satisfaction_liability = SmallBusinessSatisfactionLiability(interaction, self.on_end_liability_interaction)
            interaction.add_liability(small_business_satisfaction_liability.LIABILITY_TOKEN, small_business_satisfaction_liability)

    def on_end_liability_interaction(self):
        logger.debug('END interaction LIABILITY')
        services.get_event_manager().process_event(TestEvent.SmallBusinessCustomerActivityDone)
        self._check_interaction_count_reward()
        self._start_waiting_timer(self._number_occurrences_waiting)
        if not self._has_perform_any_interaction:
            self._start_waiting_ratio()
            self._has_perform_any_interaction = True
            logger.debug('Start waiting ratio for sim : {}', self.sim)
        else:
            current_time = services.time_service().sim_now.absolute_minutes()
            self._last_interaction_time = current_time
            self._last_waiting_time_check = current_time
        if self._alarm_activity_timer is not None:
            self._alarm_activity_timer.cancel()
            self._alarm_activity_timer = None
        self._check_waiting_ratio(True, True)
        self._perform_interaction = False

    def _activity_timer_expired(self, _):
        self._activity_timer_ended()

    def _activity_timer_ended(self):
        if self._activity_timer_data is not None:
            loot_action = self._activity_timer_data.loot_action
            if loot_action is not None:
                resolver = SingleSimResolver(self.sim.sim_info)
                if resolver is not None:
                    loot_action.apply_to_resolver(resolver)
        logger.debug('Activity timer ended')
        self._alarm_activity_timer = alarms.add_alarm(self, clock.interval_in_sim_minutes(self._activity_timer_data.timer), self._activity_timer_expired)

    def _waiting_timer_ended(self, _):
        if self._waiting_timers_data is not None and self._number_occurrences_waiting < len(self._waiting_timers_data):
            loot_action = self._waiting_timers_data[self._number_occurrences_waiting].loot_action
            if loot_action is not None:
                resolver = SingleSimResolver(self.sim.sim_info)
                if resolver is not None:
                    loot_action.apply_to_resolver(resolver)
        self._number_occurrences_waiting = self._number_occurrences_waiting + 1
        self._start_waiting_timer(self._number_occurrences_waiting)
        logger.debug('Interaction timer ended : {}', self._number_occurrences_waiting)

    def _start_waiting_timer(self, occurrences:'int'):
        if occurrences < len(self._waiting_timers_data):
            duration = clock.interval_in_sim_minutes(self._waiting_timers_data[occurrences].timer)
            self._alarm_waiting_time = alarms.add_alarm(self, duration, self._waiting_timer_ended)

    def _check_ratio_timer_expired(self, _):
        self._check_waiting_ratio(True, False)

    def _check_waiting_ratio(self, should_restart_timer:'bool', should_ignore_increase_ratio:'bool'):
        current_time = services.time_service().sim_now.absolute_minutes()
        if not self._perform_interaction:
            self._total_time_waiting += current_time - self._last_waiting_time_check
        self._last_waiting_time_check = current_time
        total_time = current_time - self._customer_start_time
        if total_time > 0:
            self._current_wait_ratio = clamp(0.0, self._total_time_waiting/total_time, 1.0)
            new_reward_index = self._get_index_waiting_ratio(self._current_wait_ratio)
            logger.debug('Waiting ratio for sim {} : {} previous index reward : {}  new index reward: {}', self.sim, self._current_wait_ratio, self._current_index_waiting_ratio, new_reward_index)
            if new_reward_index != self._current_index_waiting_ratio and should_ignore_increase_ratio and new_reward_index < self._current_index_waiting_ratio:
                self._current_index_waiting_ratio = new_reward_index
                self._reward_waiting_ratio(self._current_index_waiting_ratio)
        if should_restart_timer:
            self._alarm_check_waiting_ratio = alarms.add_alarm(self, clock.interval_in_sim_minutes(SmallBusinessTunables.SATISFACTION_WAITING_RATIO_FREQUENCY), self._check_ratio_timer_expired)

    def _get_index_waiting_ratio(self, value:'float'):
        if self._waiting_ratio_rewards_data is not None:
            for (index, ratio_reward) in enumerate(self._waiting_ratio_rewards_data):
                if ratio_reward.max_range_ratio_value >= value:
                    return index
        return 0

    def _reward_waiting_ratio(self, index:'int'):
        if self._waiting_ratio_rewards_data is not None and len(self._waiting_ratio_rewards_data) > index:
            loot_action = self._waiting_ratio_rewards_data[index].loot_action
            if loot_action is not None:
                resolver = SingleSimResolver(self.sim.sim_info)
                if resolver is not None:
                    loot_action.apply_to_resolver(resolver)

    def _check_interaction_count_reward(self):
        if self._interaction_count_rewards_data is not None:
            for reward in self._interaction_count_rewards_data:
                if reward.interaction_count == self._interaction_counter:
                    resolver = SingleSimResolver(self.sim.sim_info)
                    if reward.loot_action is not None:
                        reward.loot_action.apply_to_resolver(resolver)

    def _handle_small_business_payment_registered_event(self, resolver:'DataResolver') -> 'None':
        if resolver.event_kwargs is not None and ('payer_sim_id' in resolver.event_kwargs and 'markup' in resolver.event_kwargs) and 'revenue_type' in resolver.event_kwargs:
            payer_sim_id = resolver.event_kwargs['payer_sim_id']
            if payer_sim_id is not self.sim.sim_id:
                return
            markup = resolver.event_kwargs['markup']
            revenue_type = resolver.event_kwargs['revenue_type']
            if markup in self._markup_ratio_per_markup_value and revenue_type in self._markup_ratio_per_payment_type:
                payment_type_ratio = self._markup_ratio_per_payment_type[revenue_type]
                markup_value_ratio = self._markup_ratio_per_markup_value[markup]
                computed_ratio = payment_type_ratio*markup_value_ratio
                self._current_markup_ratio += computed_ratio
                self._check_payment_markup_ratio_reward()
            elif markup not in self._markup_ratio_per_markup_value:
                logger.error('Tried getting the markup satisfaction ratio for a invalid markup [{}]. Valid markup multipliers are: {}.', markup, self._markup_ratio_per_markup_value.keys())

    def _check_payment_markup_ratio_reward(self) -> 'None':
        if self._satisfaction_markup_ratios_rewards is not None and len(self._satisfaction_markup_ratios_rewards) > 0:
            final_reward = self._satisfaction_markup_ratios_rewards[0].loot_action
            final_reward_key = self._satisfaction_markup_ratios_rewards[0].minimum_ratio_value
            for reward in self._satisfaction_markup_ratios_rewards:
                if self._current_markup_ratio > reward.minimum_ratio_value:
                    final_reward = reward.loot_action
                    final_reward_key = reward.minimum_ratio_value
                else:
                    break
            if final_reward is not None and self._current_markup_ratio_reward_key is not final_reward_key:
                self._current_markup_ratio_reward_key = final_reward_key
                resolver = SingleSimResolver(self.sim.sim_info)
                if resolver is not None:
                    final_reward.apply_to_resolver(resolver)
