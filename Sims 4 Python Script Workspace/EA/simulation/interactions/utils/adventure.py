from __future__ import annotationsfrom interactions.utils.display_name import TunableDisplayNameVariantfrom interactions.utils.tunable_icon import TunableIconVariantfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from collections import defaultdictfrom weakref import WeakKeyDictionaryimport randomfrom protocolbuffers import Consts_pb2, SimObjectAttributes_pb2 as protocolsfrom alarms import add_alarm, cancel_alarmfrom date_and_time import create_time_span, DateAndTime, DATE_AND_TIME_ZEROfrom distributor.rollback import ProtocolBufferRollbackfrom element_utils import build_critical_section_with_finally, soft_sleep_forever, must_runfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestVariant, TunableTestSetfrom interactions.item_consume import ItemCostfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable import TunableContinuationfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.localization import TunableLocalizedStringFactoryVariant, TunableLocalizedStringFactoryfrom sims4.random import weighted_random_itemfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableMapping, TunableTuple, TunableList, TunableEnumEntry, Tunable, TunableVariant, TunableRange, TunableInterval, OptionalTunable, TunableFactory, TunableReferencefrom sims4.utils import classpropertyfrom snippets import define_snippetfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog import UiDialog, UiDialogResponsefrom ui.ui_dialog_labeled_icons import UiDialogLabeledIconsfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport clockimport servicesimport sims4.reloadimport sims4.telemetryimport telemetry_helperlogger = sims4.log.Logger('Adventure')TELEMETRY_GROUP_ADVENTURE = 'ADVN'TELEMETRY_HOOK_COMPATIBILITY = 'RESP'TELEMETRY_FIELD_ADVENTURE_ID = 'adid'TELEMETRY_FIELD_PLAYER_RESPONSE = 'resp'TELEMETRY_FIELD_TARGET_SIM_ID = 'tgid'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_ADVENTURE)with sims4.reload.protected(globals()):
    _initial_adventure_moment_key_overrides = WeakKeyDictionary()
def set_initial_adventure_moment_key_override(sim, initial_adventure_moment_key):
    _initial_adventure_moment_key_overrides[sim] = initial_adventure_moment_key

def get_last_adventure_shown():
    pass

class AdventureTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._adventure_mappings = dict()
        self._adventure_cooldowns = defaultdict(dict)
        self._success_override = None

    def set_adventure_moment(self, interaction, adventure_moment_id):
        self._adventure_mappings[interaction.guid64] = adventure_moment_id

    def remove_adventure_moment(self, interaction):
        if interaction.guid64 in self._adventure_mappings:
            del self._adventure_mappings[interaction.guid64]

    def set_adventure_moment_cooldown(self, interaction, adventure_moment_id, cooldown):
        moment_dict = self._adventure_cooldowns[interaction.guid64]
        if cooldown == DATE_AND_TIME_ZERO:
            moment_dict[adventure_moment_id] = DATE_AND_TIME_ZERO
        else:
            moment_dict[adventure_moment_id] = services.time_service().sim_now + create_time_span(hours=cooldown)

    def remove_adventure_moment_cooldown(self, interaction, adventure_moment_id):
        if interaction.guid64 in self._adventure_cooldowns:
            moment_dict = self._adventure_cooldowns[interaction.guid64]
            del moment_dict[adventure_moment_id]
            if not moment_dict:
                del self._adventure_cooldowns[interaction.guid64]

    def is_adventure_moment_available(self, interaction, adventure_moment_id, new_cooldown):
        if interaction.guid64 in self._adventure_cooldowns:
            moment_dict = self._adventure_cooldowns[interaction.guid64]
            if adventure_moment_id in moment_dict:
                cooldown = moment_dict[adventure_moment_id]
                if new_cooldown == DATE_AND_TIME_ZERO:
                    if cooldown != DATE_AND_TIME_ZERO:
                        moment_dict[adventure_moment_id] = DATE_AND_TIME_ZERO
                    return False
                if services.time_service().sim_now < cooldown:
                    return False
                self.remove_adventure_moment_cooldown(interaction, adventure_moment_id)
        return True

    def get_adventure_moment(self, interaction):
        return self._adventure_mappings.get(interaction.guid64)

    def clear_adventure_tracker(self):
        self._adventure_mappings = dict()
        self._adventure_cooldowns = defaultdict(dict)

    def save(self):
        data = protocols.PersistableAdventureTracker()
        for (adventure_id, adventure_moment_id) in self._adventure_mappings.items():
            with ProtocolBufferRollback(data.adventures) as adventure_pair:
                adventure_pair.adventure_id = adventure_id
                adventure_pair.adventure_moment_id = adventure_moment_id
        for (adventure_id, adventure_moment_dict) in self._adventure_cooldowns.items():
            for (adventure_moment_id, cooldown) in adventure_moment_dict.items():
                with ProtocolBufferRollback(data.adventure_cooldowns) as adventure_cooldown_data:
                    adventure_cooldown_data.adventure_id = adventure_id
                    adventure_cooldown_data.adventure_moment_id = adventure_moment_id
                    adventure_cooldown_data.adventure_cooldown = cooldown
        return data

    def load(self, data):
        for adventure_pair in data.adventures:
            self._adventure_mappings[adventure_pair.adventure_id] = adventure_pair.adventure_moment_id
        for adventure_cooldown_data in data.adventure_cooldowns:
            moment_dict = self._adventure_cooldowns[adventure_cooldown_data.adventure_id]
            moment_dict[adventure_cooldown_data.adventure_moment_id] = DateAndTime(adventure_cooldown_data.adventure_cooldown)

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.clear_adventure_tracker()
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._sim_info.id)
            if sim_msg is not None:
                self.load(sim_msg.attributes.adventure_tracker)

    def apply_success_override(self, types):
        if self._success_override is None:
            self._success_override = types
        else:
            self._success_override = types
            logger.warn('Replacing success override')

    def remove_success_override(self):
        if self._success_override is not None:
            self._success_override = None
        else:
            logger.warn("Attempting to remove an override that doesn't exist")

    def get_success_override_type(self):
        return self._success_override

class AdventureMomentKey(DynamicEnumLocked):
    INVALID = 0

class AdventureMoment(HasTunableFactory, AutoFactoryInit):
    LOOT_NOTIFICATION_TEXT = TunableLocalizedStringFactory(description='\n        A string used to recursively build loot notification text. It will be\n        given two tokens: a loot display text string, if any, and the previously\n        built LOOT_NOTIFICATION_TEXT string.\n        ')
    NOTIFICATION_TEXT = TunableLocalizedStringFactory(description='\n        A string used to format notifications. It will be given two arguments:\n        the notification text and the built version of LOOT_NOTIFICATION_TEXT,\n        if not empty.\n        ')
    CHEAT_TEXT = TunableTuple(description='\n        Strings to be used for display text on cheat buttons to trigger all\n        adventure moments. \n        ', previous_display_text=TunableLocalizedStringFactory(description='\n            Text that will be displayed on previous cheat button.\n            '), next_display_text=TunableLocalizedStringFactory(description='\n            Text that will be displayed on next cheat button.\n            '), text_pattern=TunableLocalizedStringFactory(description='\n            Format for displaying next and previous buttons text including the\n            progress.\n            '), tooltip=TunableLocalizedStringFactory(description='\n            Tooltip to show when disabling previous or next button.\n            '))
    COST_TYPE_SIMOLEONS = 0
    COST_TYPE_ITEMS = 1
    CHEAT_PREVIOUS_INDEX = 1
    CHEAT_NEXT_INDEX = 2
    guid64 = 0
    FACTORY_TUNABLES = {'description': '\n            A phase of an adventure. Adventure moments may present\n            some information in a dialog form and for a choice to be\n            made regarding how the overall adventure will branch.\n            ', '_visibility': OptionalTunable(description='\n            Control whether or not this moment provides visual feedback to\n            the player (i.e., a modal dialog).\n            ', tunable=UiDialog.TunableFactory(), disabled_name='not_visible', enabled_name='show_dialog'), '_finish_actions': TunableList(description='\n            A list of choices that can be made by the player to determine\n            branching for the adventure. They will be displayed as buttons\n            in the UI. If no dialog is displayed, then the first available\n            finish action will be selected. If this list is empty, the\n            adventure ends.\n            ', tunable=TunableTuple(availability_tests=TunableTestSet(description='\n                    A set of tests that must pass in order for this Finish\n                    Action to be available on the dialog. A Finish Action failing\n                    all tests is handled as if it were never tuned.\n                    '), display_text=TunableLocalizedStringFactoryVariant(description="\n                   This finish action's title. This will be the button text in\n                   the UI.\n                   ", allow_none=True), display_subtext=TunableLocalizedStringFactoryVariant(description='\n                    If tuned, this text will display below the button for this Finish Action.\n                    \n                    Span tags can be used to change the color of the text to green/positive and red/negative.\n                    <span class="positive">TEXT</span> will make the word TEXT green\n                    <span class="negative">TEXT</span> will make the word TEXT red\n                    ', allow_none=True), disabled_text=OptionalTunable(description="\n                    If enabled, this is the string that will be displayed if \n                    this finishing action is not available because the tests \n                    don't pass.\n                    ", tunable=TunableLocalizedStringFactory()), display_overrides=TunableList(description="\n                    The potential overrides used for the Adventure button. If the\n                    tests pass, the overrides will be applied. Otherwise, the\n                    'Display Text' will be used and no Icon will be set.\n                    ", tunable=TunableTuple(description='\n                        A tuple of a test and the overrides that would be chosen if the test passes.\n                        ', test=TunableTestSet(description='\n                            The test to run to see if overrides will be used.\n                            '), display_text_override=OptionalTunable(description='\n                            If enabled, we will override the display text.\n                            ', tunable=TunableLocalizedStringFactory(description='\n                                The localized string for this button response.\n                                ')), button_icon_override=OptionalTunable(description="\n                            If enabled, we will override the button's icon.\n                            ", tunable=TunableIconVariant(description='\n                                The icon to show next to the the display text.\n                                ')))), cost=TunableVariant(description='\n                    The cost associated with this finish action. Only one type\n                    of cost may be tuned. The player is informed of the cost\n                    before making the selection by modifying the display_text\n                    string to include this information.\n                    ', simoleon_cost=TunableTuple(description="The specified\n                        amount will be deducted from the Sim's funds.\n                        ", locked_args={'cost_type': COST_TYPE_SIMOLEONS}, amount=TunableRange(description='How many Simoleons to\n                            deduct.\n                            ', tunable_type=int, default=0, minimum=0)), item_cost=TunableTuple(description="The specified items will \n                        be removed from the Sim's inventory.\n                        ", locked_args={'cost_type': COST_TYPE_ITEMS}, item_cost=ItemCost.TunableFactory()), default=None), action_results=TunableList(description='\n                    A list of possible results that can occur if this finish\n                    action is selected. Action results can award loot, display\n                    notifications, and control the branching of the adventure by\n                    selecting the next adventure moment to run.\n                    ', tunable=TunableTuple(weight_modifiers=TunableList(description='\n                            A list of modifiers that affect the probability that\n                            this action result will be chosen. These are exposed\n                            in the form (test, multiplier). If the test passes,\n                            then the multiplier is applied to the running total.\n                            The default multiplier is 1. To increase the\n                            likelihood of this action result being chosen, tune\n                            multiplier greater than 1. To decrease the\n                            likelihood of this action result being chose, tune\n                            multipliers lower than 1. If you want to exclude\n                            this action result from consideration, tune a\n                            multiplier of 0.\n                            ', tunable=TunableTuple(description='\n                                A pair of test and weight multiplier. If the\n                                test passes, the associated weight multiplier is\n                                applied. If no test is specified, the multiplier\n                                is always applied.\n                                ', test=TunableTestVariant(description='\n                                    The test that has to pass for this weight\n                                    multiplier to be applied. The information\n                                    available to this test is the same\n                                    information available to the interaction\n                                    owning this adventure.\n                                    ', test_locked_args={'tooltip': None}), weight_multiplier=Tunable(description='\n                                    The weight multiplier to apply if the\n                                    associated test passes.\n                                    ', tunable_type=float, default=1))), notification=OptionalTunable(description='\n                            If set, this notification will be displayed.\n                            ', tunable=TunableUiDialogNotificationSnippet()), next_moments=TunableList(description='\n                            A list of adventure moment keys. One of these keys will\n                            be selected to determine which adventure moment is\n                            selected next. If the list is empty, the adventure ends\n                            here. Any of the keys tuned here will have to be tuned\n                            in the _adventure_moments tunable for the owning adventure.\n                            ', tunable=AdventureMomentKey), loot_actions=TunableList(description='\n                            List of Loot actions that are awarded if this action result is selected.\n                            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), continuation=TunableContinuation(description='\n                            A continuation to push when running finish actions.\n                            '), results_dialog=OptionalTunable(description='\n                            A results dialog to show. This dialog allows a list\n                            of icons with labels.\n                            ', tunable=UiDialogLabeledIcons.TunableFactory()), events_to_send=TunableList(description='\n                            A list of events to send.\n                            ', tunable=TunableEnumEntry(description='\n                                events types to send\n                                ', tunable_type=TestEvent, default=TestEvent.Invalid))))))}

    def __init__(self, parent_adventure, **kwargs):
        super().__init__(**kwargs)
        self._parent_adventure = parent_adventure
        self.resolver = self._interaction.get_resolver()

    @property
    def _interaction(self):
        return self._parent_adventure.interaction

    @property
    def _sim(self):
        return self._interaction.sim

    def run_adventure(self, guid64:'int'=0) -> 'None':
        self.guid64 = guid64
        if self._visibility is None:
            if self._finish_actions:
                self._run_first_valid_finish_action()
        else:
            dialog = self._get_dialog()
            if dialog is not None:
                self._parent_adventure.showing_dialog()
                self._parent_adventure.force_action_result = True
                dialog.show_dialog(auto_response=0)

    def _run_first_valid_finish_action(self):
        resolver = self.resolver
        for (action_id, finish_action) in enumerate(self._finish_actions):
            if finish_action.availability_tests.run_tests(resolver):
                return self._run_action_from_index(action_id)

    def _is_action_result_available(self, action_result):
        if not action_result.next_moments:
            return True
        for moment_key in action_result.next_moments:
            if self._parent_adventure.is_adventure_moment_available(moment_key):
                return True
        return False

    def _run_action_from_cheat(self, action_index):
        cheat_index = action_index - len(self._finish_actions) + 1
        if cheat_index == self.CHEAT_PREVIOUS_INDEX:
            self._parent_adventure.run_cheat_previous_moment()
        elif cheat_index == self.CHEAT_NEXT_INDEX:
            self._parent_adventure.run_cheat_next_moment()

    def _get_action_result_weight(self, action_result):
        interaction_resolver = self.resolver
        weight = 1
        for modifier in action_result.weight_modifiers:
            if not modifier.test is None:
                if interaction_resolver(modifier.test):
                    weight *= modifier.weight_multiplier
            weight *= modifier.weight_multiplier
        return weight

    def _apply_action_cost(self, action):
        if action.cost.cost_type == self.COST_TYPE_SIMOLEONS:
            if not self._sim.family_funds.try_remove(action.cost.amount, Consts_pb2.TELEMETRY_INTERACTION_COST, sim=self._sim):
                return False
        elif action.cost.cost_type == self.COST_TYPE_ITEMS:
            item_cost = action.cost.item_cost
            return item_cost.consume_interaction_cost(self._interaction)()
        return True

    def _run_action_from_index(self, action_index):
        try:
            finish_action = self._finish_actions[action_index]
        except IndexError as err:
            logger.exception('Exception {} while attempting to get finish action.\nFinishActions length: {}, ActionIndex: {},\nCurrent Moment: {},\nResolver: {}.\n', err, len(self._finish_actions), action_index, self._parent_adventure._current_moment_key, self.resolver)
            return
        action_result = None
        if self._sim.sim_info.adventure_tracker is not None:
            sim_adventure_tracker = self._sim.sim_info.adventure_tracker
            action_result = self.determine_more_desirable_result(finish_action, sim_adventure_tracker.get_success_override_type())
        if self._sim is not None and action_result is None:
            forced_action_result = False
            weight_pairs = [(self._get_action_result_weight(action_result), action_result) for action_result in finish_action.action_results if self._is_action_result_available(action_result)]
            if self._parent_adventure.force_action_result:
                forced_action_result = True
                weight_pairs = [(self._get_action_result_weight(action_result), action_result) for action_result in finish_action.action_results]
            action_result = weighted_random_item(weight_pairs)
        if action_result is not None or finish_action.action_results or not self._apply_action_cost(finish_action):
            return
        if action_result is not None:
            loot_display_text = None
            resolver = self.resolver
            for actions in action_result.loot_actions:
                for (loot_op, test_ran) in actions.get_loot_ops_gen(resolver):
                    (success, _) = loot_op.apply_to_resolver(resolver, skip_test=test_ran)
                    if success and action_result.notification is not None:
                        current_loot_display_text = loot_op.get_display_text()
                        if current_loot_display_text is not None:
                            if loot_display_text is None:
                                loot_display_text = current_loot_display_text
                            else:
                                loot_display_text = self.LOOT_NOTIFICATION_TEXT(loot_display_text, current_loot_display_text)
            if action_result.notification is not None:
                if loot_display_text is not None:
                    notification_text = lambda *tokens: self.NOTIFICATION_TEXT(action_result.notification.text(*tokens), loot_display_text)
                else:
                    notification_text = action_result.notification.text
                dialog = action_result.notification(self._sim, self.resolver)
                dialog.text = notification_text
                dialog.show_dialog()
            if action_result.next_moments:
                if forced_action_result:
                    next_moment_key = random.choice(action_result.next_moments)
                else:
                    next_moment_key = random.choice(tuple(moment_key for moment_key in action_result.next_moments if self._parent_adventure.is_adventure_moment_available(moment_key)))
                self._parent_adventure.queue_adventure_moment(next_moment_key)
            event_manager = services.get_event_manager()
            for event_type in action_result.events_to_send:
                event_manager.process_event(event_type, sim_info=self._sim.sim_info)
            if action_result.results_dialog:
                dialog = action_result.results_dialog(self._sim, resolver=self.resolver)
                dialog.show_dialog()
            if action_result.continuation:
                self._interaction.push_tunable_continuation(action_result.continuation)

    def _is_cheat_response(self, response):
        cheat_response = int(response) - len(self._finish_actions)
        if cheat_response < 0:
            return False
        return True

    def _send_telemetry_for_player_choice(self, response_index:'int') -> 'None':
        target_sim_id = 0
        if target_sim_id != self._sim.id:
            target_sim_id = self.resolver.target.sim_id
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_COMPATIBILITY, sim_info=self._sim.sim_info) as hook:
            hook.write_int(TELEMETRY_FIELD_ADVENTURE_ID, self.guid64)
            hook.write_localized_string(TELEMETRY_FIELD_PLAYER_RESPONSE, self._interaction.create_localized_string(self._finish_actions[response_index].display_text))
            hook.write_int(TELEMETRY_FIELD_TARGET_SIM_ID, target_sim_id)

    def _on_dialog_response(self, dialog):
        self._parent_adventure.showing_dialog(False)
        response_index = dialog.response
        if response_index is None:
            return
        if False and self._is_cheat_response(response_index):
            self._run_action_from_cheat(response_index)
            return
        if response_index >= len(self._finish_actions):
            return
        self._send_telemetry_for_player_choice(response_index)
        self._run_action_from_index(response_index)

    def _get_action_display_text(self, action):
        display_name = self._interaction.create_localized_string(action.display_text)
        if action.cost is not None:
            if action.cost.cost_type == self.COST_TYPE_SIMOLEONS:
                amount = action.cost.amount
                display_name = self._interaction.SIMOLEON_COST_NAME_FACTORY(display_name, amount)
            elif action.cost.cost_type == self.COST_TYPE_ITEMS:
                item_cost = action.cost.item_cost
                display_name = item_cost.get_interaction_name(self._interaction, display_name)
        return lambda *_, **__: display_name

    def _get_dialog(self) -> 'None':
        resolver = self.resolver
        dialog = self._visibility(self._sim, resolver)
        responses = []
        has_valid_response = False
        for (action_id, finish_action) in enumerate(self._finish_actions):
            result = finish_action.availability_tests.run_tests(resolver)
            if not result:
                if finish_action.disabled_text is not None:
                    disabled_text = finish_action.disabled_text if not result else None
                    if not disabled_text:
                        has_valid_response = True
                    (icon_override, display_text_override) = (None, None)
                    for override in finish_action.display_overrides:
                        result = override.test.run_tests(resolver)
                        if result:
                            display_text_override = override.display_text_override
                            icon_override = override.button_icon_override(resolver).icon_resource
                    responses.append(UiDialogResponse(dialog_response_id=action_id, text=display_text_override or self._get_action_display_text(finish_action), subtext=self._interaction.create_localized_string(finish_action.display_subtext), disabled_text=self._interaction.create_localized_string(disabled_text) if disabled_text is not None else None, button_icon=icon_override))
            disabled_text = finish_action.disabled_text if not result else None
            if not disabled_text:
                has_valid_response = True
            (icon_override, display_text_override) = (None, None)
            for override in finish_action.display_overrides:
                result = override.test.run_tests(resolver)
                if result:
                    display_text_override = override.display_text_override
                    icon_override = override.button_icon_override(resolver).icon_resource
            responses.append(UiDialogResponse(dialog_response_id=action_id, text=display_text_override or self._get_action_display_text(finish_action), subtext=self._interaction.create_localized_string(finish_action.display_subtext), disabled_text=self._interaction.create_localized_string(disabled_text) if disabled_text is not None else None, button_icon=icon_override))
        if not has_valid_response:
            return
        if False and _show_all_adventure_moments:
            responses.extend(self._parent_adventure.get_cheat_responses(action_id))
        dialog.set_responses(responses)
        dialog.add_listener(self._on_dialog_response)
        return dialog

    @staticmethod
    def display_moment_data_(adventure_moment, prefix, resolver, _connection=None):
        output = sims4.commands.Output(_connection)
        action_index = 1
        if adventure_moment._visibility is not None:
            output(prefix + 'Dialog text ID: {}'.format(adventure_moment._visibility._tuned_values.text._string_id))
        for action in adventure_moment._finish_actions:
            output(prefix + 'finish action {}'.format(action_index))
            if action.availability_tests:
                output(prefix + '  availability tests: {}'.format(action.availability_tests))
                try:
                    output(prefix + '  availability test result: {}'.format(action.availability_tests.run_tests(resolver)))
                except:
                    output(prefix + '  availability test result: Unable to determine outside actual running interaction')
            if adventure_moment._visibility is not None and action.display_text:
                output(prefix + '  display text ID: {}'.format(action.display_text._string_id))
            results_index = 1
            for result in action.action_results:
                output(prefix + '  action result {}'.format(results_index))
                if result.next_moments:
                    output(prefix + '    next moments')
                    for next_moment in result.next_moments:
                        output(prefix + '      {}'.format(next_moment))
                if result.weight_modifiers:
                    modifier_index = 1
                    weight = 1
                    for modifier in result.weight_modifiers:
                        output(prefix + '    weight modifier {}'.format(modifier_index))
                        multiplier = modifier.weight_multiplier
                        output(prefix + '      multiplier: {}'.format(multiplier))
                        output(prefix + '      test: {}'.format(modifier.test))
                        if modifier.test:
                            try:
                                result = resolver(modifier.test)
                                output(prefix + '      test results: {}'.format(result))
                                if weight is not None:
                                    weight *= multiplier
                            except:
                                output(prefix + '      test results: Unable to determine outside actual running interaction')
                                weight = None
                        modifier_index += 1
                    if weight is None:
                        output(prefix + '    weight: Unable to determine outside actual running interaction')
                    else:
                        output(prefix + '    weight: {}'.format(weight))
                results_index += 1
            action_index += 1

    @staticmethod
    def get_folloup_moments_gen(adventure_moment):
        for action in adventure_moment._finish_actions:
            for result in action.action_results:
                if result.next_moments:
                    yield from result.next_moments

    def determine_more_desirable_result(self, possible_results, desirability_criteria):
        if len(possible_results) < 2:
            return
        if desirability_criteria is None:
            return
        for action in possible_results.action_results:
            if action.loot_actions is not None and len(action.loot_actions) > 0:
                for result_list in action.loot_actions:
                    for result in result_list.loot_actions:
                        if result in desirability_criteria:
                            result_increases_stat = result.get_value() > 0
                            if result_increases_stat:
                                return action
(TunableAdventureMomentReference, TunableAdventureMomentSnippet) = define_snippet('Adventure_Moment', AdventureMoment.TunableFactory())
class Adventure(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            A series of individual moments linked together in a game-like\n            fashion.\n            ', '_adventure_moments': TunableMapping(description='\n            The individual adventure moments for this adventure. Every moment\n            used in the adventure must be defined here. For instance, if there\n            is an adventure moment that triggers another adventure moment, the\n            latter must also be defined in this list.\n            ', key_type=AdventureMomentKey, value_type=TunableTuple(adventure_moment=TunableAdventureMomentSnippet(pack_safe=True), sim_specific_cooldown=TunableVariant(description='\n                    The type of sim specific cooldown,\n                    \n                    Hours means cooldown for specified number of sim hours\n                    No cooldown means no cooldown\n                    One shot means a sim will only see it once.\n                    \n                    (Note:  If we hit a visible (or resumed) adventure, after\n                    that point if all actions are on cooldown, the cooldowns will be\n                    ignored.)\n                    ', hours=TunableRange(description='\n                        A cooldown that last for the specified number of hours\n                        ', tunable_type=float, default=50, minimum=1), locked_args={'one_shot': DATE_AND_TIME_ZERO, 'no_cooldown': None}, default='no_cooldown'))), '_initial_moments': TunableList(description='\n            A list of adventure moments that are valid as initiating moments for\n            this adventure.\n            ', tunable=TunableTuple(description='\n                A tuple of moment key and weight. The higher the weight, the\n                more likely it is this moment will be selected as the initial\n                moment.\n                ', adventure_moment_key=TunableEnumEntry(description='\n                    The key of the initial adventure moment.\n                    ', tunable_type=AdventureMomentKey, default=AdventureMomentKey.INVALID), weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this potential initial moment relative\n                    to other items within this list.\n                    '))), '_trigger_interval': TunableInterval(description='\n            The interval, in Sim minutes, between the end of one adventure\n            moment and the beginning of the next one.\n            ', tunable_type=float, default_lower=8, default_upper=12, minimum=0), '_maximum_triggers': Tunable(description='\n            The maximum number of adventure moments that can be triggered by\n            this adventure. Any moment being generated from the adventure beyond\n            this limit will be discarded. Set to 0 to allow for an unlimited\n            number of adventure moments to be triggered.\n            ', tunable_type=int, default=0), '_resumable': Tunable(description='\n            A Sim who enters a resumable adventure will restart the same\n            adventure at the moment they left it at.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adventure_moment_count = 0
        self._alarm_handle = None
        self._current_moment_key = None
        self._canceled = False
        self.force_action_result = False
        self._sleep_element = None

    def _build_outer_elements(self, sequence):
        sequence = sequence if self.interaction.immediate else (sequence, must_run(self._wait_for_dialogs_gen))
        return build_critical_section_with_finally(sequence, self._end_adventure)

    def _wait_for_dialogs_gen(self, timeline):
        if self._sleep_element:
            yield timeline.run_child(self._sleep_element)

    def _end_adventure(self, *_, **__):
        if self._alarm_handle is not None:
            cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _soft_stop(self):
        self._canceled = True
        return super()._soft_stop()

    @property
    def tracker(self):
        return self.interaction.sim.sim_info.adventure_tracker

    def _get_cheat_display_text(self, display_text, progress, total_progress):
        display_name = self.interaction.create_localized_string(display_text)
        display_name = AdventureMoment.CHEAT_TEXT.text_pattern(display_name, progress, total_progress)
        return lambda *_, **__: display_name

    def get_cheat_responses(self, last_action_id):
        responses = []
        total_moments = len(self._adventure_moment_keys)
        disabled_text = AdventureMoment.CHEAT_TEXT.tooltip
        curr_index = self._adventure_moment_keys.index(self._current_moment_key)
        responses.append(UiDialogResponse(dialog_response_id=last_action_id + AdventureMoment.CHEAT_PREVIOUS_INDEX, text=self._get_cheat_display_text(AdventureMoment.CHEAT_TEXT.previous_display_text, curr_index, total_moments), disabled_text=disabled_text() if curr_index <= 0 else None))
        responses.append(UiDialogResponse(dialog_response_id=last_action_id + AdventureMoment.CHEAT_NEXT_INDEX, text=self._get_cheat_display_text(AdventureMoment.CHEAT_TEXT.next_display_text, curr_index + 2, total_moments), disabled_text=disabled_text() if curr_index >= total_moments - 1 else None))
        return responses

    def run_cheat_previous_moment(self):
        pass

    def run_cheat_next_moment(self):
        pass

    def queue_adventure_moment(self, adventure_moment_key):
        if self._maximum_triggers and self._adventure_moment_count >= self._maximum_triggers:
            return
        time_span = clock.interval_in_sim_minutes(self._trigger_interval.random_float())

        def callback(alarm_handle):
            self._alarm_handle = None
            if not self._canceled:
                self.tracker.remove_adventure_moment(self.interaction)
                self._run_adventure_moment(adventure_moment_key)

        self.tracker.set_adventure_moment(self.interaction, adventure_moment_key)
        self._alarm_handle = add_alarm(self, time_span, callback)

    def _run_adventure_moment(self, adventure_moment_key, count_moment=True):
        if adventure_moment_key in self._adventure_moments:
            adventure_moment_data = self._adventure_moments[adventure_moment_key]
            self._current_moment_key = adventure_moment_key
            self.set_adventure_moment_cooldown(adventure_moment_key)
            if isinstance(adventure_moment_data.adventure_moment, TunableFactory.TunableFactoryWrapper):
                adventure_moment_data.adventure_moment(self).run_adventure()
            else:
                adventure_moment_data.adventure_moment(self).run_adventure(adventure_moment_data.adventure_moment.guid64)
        if count_moment:
            self._adventure_moment_count += 1

    def showing_dialog(self, is_showing=True):
        if is_showing:
            if self._sleep_element is None:
                self._sleep_element = soft_sleep_forever()
        elif self._sleep_element is not None:
            self._sleep_element.trigger_soft_stop()
            self._sleep_element = None

    def _get_initial_adventure_moment_key(self):
        initial_adventure_moment_key = _initial_adventure_moment_key_overrides.get(self.interaction.sim)
        if initial_adventure_moment_key is not None and self.is_adventure_moment_available(initial_adventure_moment_key):
            return initial_adventure_moment_key
        if self._resumable:
            initial_adventure_moment_key = self.tracker.get_adventure_moment(self.interaction)
            if initial_adventure_moment_key is not None:
                self.force_action_result = True
                return initial_adventure_moment_key
        participant_resolver = self.interaction.get_resolver()
        return weighted_random_item([(moment.weight.get_multiplier(participant_resolver), moment.adventure_moment_key) for moment in self._initial_moments if self.is_adventure_moment_available(moment.adventure_moment_key)])

    def set_adventure_moment_cooldown(self, adventure_moment_key):
        if adventure_moment_key in self._adventure_moments:
            adventure_moment_data = self._adventure_moments[adventure_moment_key]
            if adventure_moment_data.sim_specific_cooldown is None:
                self.tracker.remove_adventure_moment_cooldown(self.interaction, adventure_moment_key)
                return
            self.tracker.set_adventure_moment_cooldown(self.interaction, adventure_moment_key, adventure_moment_data.sim_specific_cooldown)

    def is_adventure_moment_available(self, adventure_moment_key):
        if adventure_moment_key in self._adventure_moments:
            adventure_moment_data = self._adventure_moments[adventure_moment_key]
            return self.tracker.is_adventure_moment_available(self.interaction, adventure_moment_key, adventure_moment_data.sim_specific_cooldown)
        return True

    def _do_behavior(self):
        if self.tracker is not None:
            initial_moment = self._get_initial_adventure_moment_key()
            if initial_moment is not None:
                self._run_adventure_moment(initial_moment)

    @staticmethod
    def display_adventure_enums(tuned_values, display_moment_data, resolver, _connection=None):
        output = sims4.commands.Output(_connection)
        for (name, tuning) in tuned_values._adventure_moments.items():
            output('      Enum Key: {}:'.format(name))
            output('        Moment Tuning: {}'.format(tuning.adventure_moment))
            if display_moment_data:
                output('          sim specific cooldown:  {}'.format(tuning.sim_specific_cooldown))
                tuning.adventure_moment.factory.display_moment_data_(tuning.adventure_moment._tuned_values, '          ', resolver, _connection)

    @staticmethod
    def display_initial_moment_data(tuned_values, resolver, _connection):
        output = sims4.commands.Output(_connection)
        initial_index = 1
        for initial_moment in tuned_values._initial_moments:
            output('      Initial Moment {}'.format(initial_index))
            output('        adventure_moment_key: {}'.format(initial_moment.adventure_moment_key))
            weight = initial_moment.weight
            base_value = weight.base_value
            output('        weight base value: {}'.format(base_value))
            modifier_index = 1
            for multiplier in weight.multipliers:
                output('        multiplier {}'.format(modifier_index))
                multiple = multiplier.multiplier
                output('          multiplier: {}'.format(multiple))
                output('          tests: {}'.format(multiplier.tests))
                try:
                    result = multiplier.tests.run_tests(resolver)
                    output('          tests result: {}'.format(result))
                    if base_value is not None:
                        base_value *= multiple
                except:
                    output('          tests result: Unable to determine outside actual running interaction'.format(result))
                modifier_index += 1
            if base_value is None:
                output('        weight: Unable to determine outside actual running interaction')
            else:
                output('        weight: {}'.format(base_value))
            initial_index += 1

    @staticmethod
    def display_adventure_moment_data(tuned_values, moment_key, title, index, resolver, _connection):
        tuning = tuned_values._adventure_moments.get(moment_key)
        if tuning is None:
            return False
        output = sims4.commands.Output(_connection)
        if index >= 0:
            output('  ' + title)
            output('    Adventure {}'.format(index))
        output('      Moment Tuning: {}'.format(tuning.adventure_moment))
        output('        sim specific cooldown:  {}'.format(tuning.sim_specific_cooldown))
        tuning.adventure_moment.factory.display_moment_data_(tuning.adventure_moment._tuned_values, '        ', resolver, _connection)
        return True

    @staticmethod
    def find_moment_path(tuned_values, adventure_moment, moment_key, explored_keys):
        for followup_key in adventure_moment.factory.get_folloup_moments_gen(adventure_moment._tuned_values):
            if followup_key is moment_key:
                return [followup_key]
            if followup_key in explored_keys:
                pass
            else:
                explored_keys.add(followup_key)
                tuning = tuned_values._adventure_moments.get(followup_key)
                result = Adventure.find_moment_path(tuned_values, tuning.adventure_moment, moment_key, explored_keys)
                if result is not None:
                    result.append(followup_key)
                    return result

    @staticmethod
    def find_moment_gen(tuned_values, tuning_name):
        for (moment_key, tuning) in tuned_values._adventure_moments.items():
            if tuning_name in str(tuning.adventure_moment).lower():
                explored_keys = set()
                result = []
                for initial_moment in tuned_values._initial_moments:
                    followup_key = initial_moment.adventure_moment_key
                    result = [moment_key]
                    break
                    if followup_key is moment_key and followup_key in explored_keys:
                        pass
                    else:
                        explored_keys.add(followup_key)
                        target_tuning = tuned_values._adventure_moments.get(followup_key)
                        result = Adventure.find_moment_path(tuned_values, target_tuning.adventure_moment, moment_key, explored_keys)
                        if result is not None:
                            result.append(followup_key)
                            result.reverse()
                            break
                yield (moment_key, tuning.adventure_moment, result)
