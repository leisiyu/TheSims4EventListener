import servicesimport sims4from date_and_time import create_time_spanfrom event_testing.tests import TunableTestSetfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.context import InteractionSourcefrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.tunable import TunableContinuationfrom interactions.utils.tunable_icon import TunableIconVariantfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableList, OptionalTunable, TunableRange, HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableIntervalfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.localization import LocalizationHelperTuningfrom sims4.utils import flexmethodfrom snippets import define_snippetfrom tunable_time import TunableTimeSpan, TunableTimeOfDayfrom ui.ui_dialog_picker import BasePickerRow, ObjectPickerRow, UiItemPicker, UiDropdownPicker, UiObjectPickerimport sims4.loglogger = sims4.log.Logger('PickerInteractions')
class PickerItemBase(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'icon': OptionalTunable(description='\n            If enabled, specify the icon to be displayed in UI.\n            ', tunable=TunableIconVariant()), 'name': OptionalTunable(description='\n            If enabled, display this name in the UI.\n            Otherwise the display name of the first affordance\n            in the continuation will be used as the name.\n            ', tunable=TunableLocalizedStringFactory()), 'item_description': OptionalTunable(description='\n            When enabled, the tuned string will be shown as a description.\n            ', tunable=TunableLocalizedStringFactory()), 'item_tooltip': OptionalTunable(description='\n            When enabled, the tuned string will be shown as a tooltip.\n            ', tunable=TunableLocalizedStringFactory()), 'disable_tooltip': OptionalTunable(description='\n            When tuned, and the item is disabled, the tuned string \n            will be shown as a tooltip.\n            Otherwise it will try to grab a tooltip off a failed test.\n            ', tunable=TunableLocalizedStringFactory()), 'enable_tests': OptionalTunable(description='\n            Tests which would dictate if this option is enabled\n            in the pie menu.  ORs of ANDs.\n            If disabled, it will default to the tests for the\n            first affordance in the continuation chain.\n            ', tunable=TunableTestSet()), 'localization_tokens': OptionalTunable(description="\n            Additional localization tokens for this item\n            to use in the name/description.\n            This is in addition to the display name tokens\n            tuned in the continuation's first affordance.\n            ", tunable=LocalizationTokens.TunableFactory()), 'visibility_tests': OptionalTunable(description='\n            Tests which would dictate if this option is visible\n            in the pie menu.  ORs of ANDs.\n            If disabled, this item will always be visible.\n            ', tunable=TunableTestSet())}
(_, TunablePickerItemBaseSnippet) = define_snippet('picker_item_base', PickerItemBase.TunableFactory())
class InteractionPickerItem(PickerItemBase):
    FACTORY_TUNABLES = {'continuation': TunableContinuation(description='\n            The continuation to push when this item is selected.\n            ', minlength=1)}
(_, TunableInteractionPickerItemSnippet) = define_snippet('interaction_picker_item', InteractionPickerItem.TunableFactory())
class WeatherEventPickerItem(PickerItemBase):
    FACTORY_TUNABLES = {'weather_event': TunableReference(description='\n            The weather event to apply when this item is selected.\n            ', manager=services.get_instance_manager(sims4.resources.Types.WEATHER_EVENT), pack_safe=True)}
(_, TunableWeatherEventPickerItemSnippet) = define_snippet('weather_event_picker_item', WeatherEventPickerItem.TunableFactory())
class WeatherEventPickerSuperInteraction(PickerSuperInteraction):
    WEATHER_EVENT_DURATION = 0
    INSTANCE_TUNABLES = {'picker_dialog': UiItemPicker.TunableFactory(description='\n            The item picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'possible_actions': TunableList(description='\n            A list of weather events that will show up in the dialog picker\n            ', tunable=TunableWeatherEventPickerItemSnippet(), minlength=1, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = cls if inst is None else inst
        resolver = inst_or_cls.get_resolver(target=target, context=context, **kwargs)
        for choice in inst_or_cls.possible_actions:
            if not choice.visibility_tests or not choice.visibility_tests.run_tests(resolver):
                pass
            else:
                tokens = tuple() if choice.localization_tokens is None else choice.localization_tokens.get_tokens(resolver)
                display_name = inst_or_cls.get_name(target=target, context=context) if choice.name is None else inst_or_cls.create_localized_string(choice.name, tokens, target=target, context=context, **kwargs)
                icon_info = None if choice.icon is None else choice.icon(resolver)
                display_description = None if choice.item_description is None else inst_or_cls.create_localized_string(choice.item_description, tokens, target=target, context=context, **kwargs)
                if choice.enable_tests:
                    test_result = choice.enable_tests.run_tests(resolver)
                else:
                    test_result = inst_or_cls.test(target=target, context=context)
                row_tooltip = choice.item_tooltip
                row_tooltip = test_result.tooltip
                is_enabled = bool(test_result)
                row_tooltip = choice.disable_tooltip
                row = BasePickerRow(is_enable=is_enabled, name=display_name, icon_info=icon_info, row_description=display_description, tag=choice, row_tooltip=row_tooltip)
                yield row

    def on_choice_selected(self, choice, **kwargs):
        if choice is not None:
            weather_service = services.weather_service()
            if weather_service is not None:
                weather_service.start_weather_event(choice.weather_event, self.WEATHER_EVENT_DURATION)

class NumberPickerSuperInteraction(PickerSuperInteraction):
    WEATHER_EVENT_DURATION = 0
    INSTANCE_TUNABLES = {'picker_dialog': UiDropdownPicker.TunableFactory(description='\n            The item picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'numbers': TunableInterval(description='\n            Range of numbers to show.\n            ', tunable_type=int, default_lower=1, default_upper=6, minimum=1, tuning_group=GroupNames.PICKERTUNING), 'default_number': OptionalTunable(description='\n            If enabled, the specified number will be selected by default.\n            ', tunable=TunableRange(description='\n                Number selected by default.\n                ', tunable_type=int, minimum=1, default=1, tuning_group=GroupNames.PICKERTUNING), tuning_group=GroupNames.PICKERTUNING), 'text_format': OptionalTunable(description='\n            Text used to format the number into something readable.\n            Number will, naturally, be the first (and only) parameter.\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, default_override=None, **kwargs):
        inst_or_cls = cls if inst is None else inst
        default = inst_or_cls.default_number if default_override is None else default_override
        for x in range(inst_or_cls.numbers.lower_bound, inst_or_cls.numbers.upper_bound + 1):
            if inst_or_cls.text_format is not None:
                name = inst_or_cls.text_format(x)
            else:
                name = LocalizationHelperTuning.get_raw_text(str(x))
            row = ObjectPickerRow(name=name, icon_info=inst_or_cls.picker_dialog.default_item_icon(None), is_selected=x == default, tag=x)
            yield row

    def on_choice_selected(self, choice, **kwargs):
        pass

class TimePickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiDropdownPicker.TunableFactory(description='\n            The picker use.\n            ', tuning_group=GroupNames.PICKERTUNING), 'time_increment': TunableTimeSpan(description='\n            Interval between selections.\n            ', default_hours=1, tuning_group=GroupNames.PICKERTUNING), 'start_time': TunableTimeOfDay(description='\n            Starting time for the selection of times.\n            ', tuning_group=GroupNames.PICKERTUNING), 'end_time': TunableTimeOfDay('\n            End time for the list of times.\n            ', tuning_group=GroupNames.PICKERTUNING), 'can_start_with_current_time': OptionalTunable(description='\n            If enabled, then if the current time is between start time and end time, options before the current time\n            will be skipped, and the first (and default) option will be "Now", using the specified string.  \n            ', tunable=TunableLocalizedStringFactory(description="\n                'Now' text if starting with current time.\n                "), tuning_group=GroupNames.PICKERTUNING), 'default_time': OptionalTunable(description='\n            If enabled, the time closest to this time will be selected by default.\n            ', tunable=TunableTimeOfDay(), tuning_group=GroupNames.PICKERTUNING), 'text_format': TunableLocalizedStringFactory(description='\n            Text used to format the number into something readable.\n            Time will, naturally, be the first (and only) parameter.\n            ', tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, default_override=None, days_away=0, **kwargs):
        inst_or_cls = cls if inst is None else inst
        default = inst_or_cls.default_time if default_override is None else default_override
        end_time = inst_or_cls.end_time
        start_time = inst_or_cls.start_time
        one_day_time_span = create_time_span(days=1)
        time_increment = inst_or_cls.time_increment()
        found_closest = False
        end_time = end_time + one_day_time_span
        current_time = services.time_service().sim_now.time_of_day()
        if current_time > end_time:
            return
        compare_time = default if default is not None else start_time
        found_closest = True
        row = ObjectPickerRow(name=inst_or_cls.can_start_with_current_time(), icon_info=inst_or_cls.picker_dialog.default_item_icon(None), is_selected=True, tag=None)
        yield row
        increments_to_jump = (current_time - start_time).in_ticks()//time_increment.in_ticks() + 1
        start_time = start_time + time_increment*increments_to_jump
        half_increment_ticks = time_increment.in_ticks()/2
        while end_time <= start_time and days_away == 0 and (inst_or_cls.can_start_with_current_time and current_time > compare_time) and start_time <= end_time:
            selected = False
            selected = True
            found_closest = True
            row = ObjectPickerRow(name=inst_or_cls.text_format(start_time), icon_info=inst_or_cls.picker_dialog.default_item_icon(None), is_selected=selected, tag=start_time)
            yield row
            start_time = start_time + time_increment

    def on_choice_selected(self, choice, **kwargs):
        pass

class InteractionPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiObjectPicker.TunableFactory(description='\n            The item picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'possible_actions': TunableList(description='\n            A list of the interactions that will show up in the dialog picker\n            ', tunable=TunableInteractionPickerItemSnippet(), minlength=1, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        args = self._kwargs.copy()
        args.update({'target_sim': self.sim})
        self._show_picker_dialog(self.sim, **args)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = cls if inst is None else inst
        cloned_context = context.clone_for_insert_next(source=InteractionSource.SCRIPT_WITH_USER_INTENT)
        for choice in inst_or_cls.possible_actions:
            first_continuation = next(iter(choice.continuation), None)
            if first_continuation is None:
                pass
            else:
                affordance = first_continuation.affordance
                resolver = affordance.get_resolver(target=target, context=cloned_context, **kwargs)
                if not choice.visibility_tests or not choice.visibility_tests.run_tests(resolver):
                    pass
                else:
                    tokens = tuple() if choice.localization_tokens is None else choice.localization_tokens.get_tokens(resolver)
                    display_name = affordance.get_name(target=target, context=cloned_context) if choice.name is None else affordance.create_localized_string(choice.name, tokens, target=target, context=cloned_context, **kwargs)
                    icon_info = None if choice.icon is None else choice.icon(resolver)
                    display_description = None if choice.item_description is None else affordance.create_localized_string(choice.item_description, tokens, target=target, context=cloned_context, **kwargs)
                    if choice.enable_tests:
                        test_result = choice.enable_tests.run_tests(resolver)
                    else:
                        test_result = affordance.test(target=target, context=cloned_context)
                    row_tooltip = choice.item_tooltip
                    row_tooltip = test_result.tooltip
                    is_enabled = bool(test_result)
                    row_tooltip = choice.disable_tooltip
                    row = ObjectPickerRow(is_enable=is_enabled, name=display_name, icon_info=icon_info, row_description=display_description, tag=choice, row_tooltip=row_tooltip)
                    yield row

    def on_choice_selected(self, choice, **kwargs):
        if choice is not None:
            self.push_tunable_continuation(choice.continuation)
