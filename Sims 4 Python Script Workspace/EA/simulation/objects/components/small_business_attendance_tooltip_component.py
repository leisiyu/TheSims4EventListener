from __future__ import annotationsimport sims4from sims4.common import Packfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from business.business_manager import BusinessManager
    from Localization_pb2 import LocalizedString
    from objects.components.state import StateComponent
    from small_business.small_business_income_data import SmallBusinessIncomeData
    from event_testing.resolver import DataResolverimport servicesfrom business.business_enums import BusinessType, SmallBusinessAttendanceSaleModefrom event_testing.test_events import TestEventfrom objects.components import Componentfrom objects.components.tooltip_component import TooltipComponentfrom objects.components.types import SMALL_BUSINESS_ATTENDANCE_TOOLTIP_COMPONENTfrom objects.hovertip import TooltipFieldsfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedStringfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, TunableTuple, OptionalTunable, TunablePackSafeReference
class SmallBusinessAttendanceTooltipComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=SMALL_BUSINESS_ATTENDANCE_TOOLTIP_COMPONENT):
    FACTORY_TUNABLES = {'entrance_fee_text': OptionalTunable(description='\n            If enabled, will display entrance fee text.\n            ', tunable=TunableLocalizedStringFactory(description='\n                Text used to introduce the entry fee.\n                ')), 'on_entry_fee_text': OptionalTunable(description='\n            If enabled, will display on entry fee text.\n            ', tunable=TunableLocalizedStringFactory(description='\n                Text used to specify the on-entry fee, in a format similar to "{0.Money}"\n                ')), 'hourly_fee_text': OptionalTunable(description='\n            If enabled, will display hourly fee text.\n            ', tunable=TunableLocalizedStringFactory(description='\n                Text used to specify the hourly fee, in a format similar to "{0.Money}/hr"\n                ')), 'no_fee_text': OptionalTunable(description='\n            If enabled, will display no fee text.\n            ', tunable=TunableLocalizedString(description='\n                Text used to specify that there\'s no entry fee, will be "None".\n                ')), 'markup_text': OptionalTunable(description='\n            If enabled, will display markup text.\n            ', tunable=TunableLocalizedStringFactory(description='\n                Text to specify the business\' markup, in a format similar to "({0.Number}% Markup)"\n                ')), 'tooltip_field_entrance_fee': OptionalTunable(description='\n            If enabled, this component will override to provide the Entrance Fee information.\n            ', tunable=TunableEnumEntry(description='\n                The tooltip field this component will override to provide the Entrance Fee information.\n                ', tunable_type=TooltipFields, default=TooltipFields.crafted_by_text)), 'tooltip_field_markup': OptionalTunable(description='\n            If enabled, this component will override to provide the Markup information.\n            ', tunable=TunableEnumEntry(description='\n                The tooltip field this component will override to provide the Markup information.\n                ', tunable_type=TooltipFields, default=TooltipFields.subtext)), 'small_business_open_close_object_states': OptionalTunable(description='\n            If enabled, tooltip will be displayed based on small business open close states.\n            ', tunable=TunableTuple(description='\n                Object State and State Values that represent the Open/Close states for the Small Business\n                ', object_state=TunablePackSafeReference(description='\n                    Object State for the Small Business being open/closed.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState'), open_state_value=TunablePackSafeReference(description='\n                    State value for the Small Business being open.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), closed_state_value=TunablePackSafeReference(description='\n                    State value for the Small Business being closed.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'))), 'small_business_retail_object_states': OptionalTunable(description='\n            If enabled, tooltip will be displayed based light retail states.\n            ', tunable=TunableTuple(description='\n                Object State and State Values that represent the Light Retail states for the Small Business\n                ', object_state=TunablePackSafeReference(description='\n                    Object State for the Small Business being open/closed.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState'), light_retail_state_value=TunablePackSafeReference(description='\n                    State value for when light retail surface is active for Small Business.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue')))}

    @classproperty
    def required_packs(cls):
        return (Pack.EP18,)

    def on_add(self):
        services.get_event_manager().register(self, (TestEvent.BusinessDataUpdated,))
        self._refresh()

    def on_remove(self):
        services.get_event_manager().unregister(self, (TestEvent.BusinessDataUpdated,))
        self._refresh()

    def on_state_changed(self, state, old_value, new_value, from_init):
        self._refresh()

    def on_finalize_load(self):
        self._refresh()

    def handle_event(self, sim_info, event:'TestEvent', resolver:'DataResolver') -> 'None':
        if event == TestEvent.BusinessDataUpdated:
            self._refresh()

    def _refresh(self):
        tooltip_component = self.owner.tooltip_component
        state_component = self.owner.state_component
        clear_tooltips = False
        if tooltip_component is not None and state_component is not None:
            business_manager = services.business_service().get_business_manager_for_zone()
            open_state_value = None
            if self.small_business_open_close_object_states is not None:
                open_state_value = state_component.get_state(self.small_business_open_close_object_states.object_state)
            light_retail_state_value = None
            if self.small_business_retail_object_states is not None:
                light_retail_state_value = state_component.get_state(self.small_business_retail_object_states.object_state)
            if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                if self.small_business_open_close_object_states is not None and open_state_value == self.small_business_open_close_object_states.open_state_value:
                    small_business_income_data = business_manager.small_business_income_data
                    attendance_sale_mode = small_business_income_data.attendance_sale_mode
                    attendance_mode_text = self.no_fee_text
                    if attendance_sale_mode == SmallBusinessAttendanceSaleMode.ENTRY_FEE and self.on_entry_fee_text is not None:
                        attendance_mode_text = self.on_entry_fee_text(small_business_income_data.get_entry_fee())
                    elif self.hourly_fee_text is not None:
                        attendance_mode_text = self.hourly_fee_text(small_business_income_data.get_hourly_fee())
                    if self.tooltip_field_entrance_fee is not None and self.entrance_fee_text is not None:
                        tooltip_component.update_tooltip_field(self.tooltip_field_entrance_fee, self.entrance_fee_text(attendance_mode_text), should_update=True, immediate=True)
                    if self.markup_text is not None:
                        if self.small_business_retail_object_states is None:
                            tooltip_component.update_tooltip_field(self.tooltip_field_markup, self.markup_text(SmallBusinessAttendanceTooltipComponent.get_markup_percentage(business_manager.markup_multiplier)), should_update=True, immediate=True)
                        elif self.small_business_retail_object_states is not None and light_retail_state_value == self.small_business_retail_object_states.light_retail_state_value:
                            tooltip_component.update_tooltip_field(self.tooltip_field_markup, self.markup_text(SmallBusinessAttendanceTooltipComponent.get_markup_percentage(business_manager.markup_multiplier)), should_update=True, immediate=True)
                        else:
                            tooltip_component.update_tooltip_field(self.tooltip_field_markup, None, None, should_update=True, immediate=True)
                else:
                    clear_tooltips = True
            else:
                clear_tooltips = True
            if clear_tooltips:
                if self.tooltip_field_entrance_fee is not None:
                    tooltip_component.update_tooltip_field(self.tooltip_field_entrance_fee, None, should_update=True, immediate=True)
                if self.tooltip_field_markup is not None:
                    tooltip_component.update_tooltip_field(self.tooltip_field_markup, None, should_update=True, immediate=True)

    @staticmethod
    def get_markup_percentage(markup_multiplier:'float') -> 'int':
        if markup_multiplier >= 1.0:
            return int((markup_multiplier - 1.0)*100)
        else:
            return -int((1.0 - markup_multiplier)*100)
