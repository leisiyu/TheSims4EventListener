from _math import Vector3Immutableimport servicesimport sims4from business.business_enums import BusinessTypefrom crafting.crafting_tunable import CraftingTuningfrom event_testing.resolver import DataResolverfrom event_testing.test_events import TestEventfrom objects.components import Component, typesfrom objects.components.state_references import TunableStateValueReferencefrom objects.components.statistic_component import StatisticComponentfrom objects.game_object_properties import GameObjectPropertyfrom objects.hovertip import TooltipFieldsCompletefrom routing import Locationfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInitfrom sims4.utils import classpropertyfrom singletons import UNSETfrom vfx import PlayEffectfrom sims4.common import Packlogger = sims4.log.Logger('Light Retail Surface', default_owner='bshefket')
def meets_zone_requirement():
    zone_director = services.venue_service().get_zone_director()
    return zone_director is not None and zone_director.supports_business_type(BusinessType.SMALL_BUSINESS)

class LightRetailSurfaceComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.LIGHT_RETAIL_SURFACE_COMPONENT):
    LIGHT_RETAIL_ENABLED_STATE = TunableStateValueReference(description='\n        The state value that object has Light Retail Surfaces enabled.\n        ', pack_safe=True)
    LIGHT_RETAIL_DISABLED_STATE = TunableStateValueReference(description='\n        The state value that object has Light Retail Surfaces disabled.\n        ', pack_safe=True)
    LIGHT_RETAIL_ACTIVE_STATE = TunableStateValueReference(description='\n        The state in case the business is registered.\n        ', pack_safe=True)
    LIGHT_RETAIL_INACTIVE_STATE = TunableStateValueReference(description='\n        The state in case the business is unregistered.\n        ', pack_safe=True)
    LIGHT_RETAIL_OPEN_STATE = TunableStateValueReference(description='\n        The state in case the business is open.\n        ', pack_safe=True)
    LIGHT_RETAIL_CLOSED_STATE = TunableStateValueReference(description='\n        The state in case the business is closed.\n        ', pack_safe=True)
    SET_FOR_SALE_VFX = PlayEffect.TunableFactory(description='\n        An effect that will play on an object when it gets set for sale.\n        ')
    SET_NOT_FOR_SALE_VFX = PlayEffect.TunableFactory(description='\n        An effect that will play on an object when it gets set not for sale.\n        ')

    @classproperty
    def required_packs(cls):
        return (Pack.EP18,)

    def on_state_changed(self, state, old_value, new_value, from_init):
        if not meets_zone_requirement():
            return
        if from_init or old_value is new_value:
            return
        if state is self.LIGHT_RETAIL_ACTIVE_STATE.state:
            slot_component = self.owner.slot_component
            if new_value is self.LIGHT_RETAIL_ACTIVE_STATE:
                for child in self.owner.children:
                    slot_component.update_flags(child, self.owner.location)
            if new_value is self.LIGHT_RETAIL_INACTIVE_STATE:
                for child in self.owner.children:
                    child.remove_dynamic_commodity_flags(slot_component)
        if state is self.LIGHT_RETAIL_ENABLED_STATE.state:
            if new_value is self.LIGHT_RETAIL_ENABLED_STATE:
                for child in self.owner.children:
                    self.SET_FOR_SALE_VFX(child).start_one_shot()
            if new_value is self.LIGHT_RETAIL_DISABLED_STATE:
                for child in self.owner.children:
                    self.SET_NOT_FOR_SALE_VFX(child).start_one_shot()
        if state is self.LIGHT_RETAIL_OPEN_STATE.state:
            if new_value is self.LIGHT_RETAIL_OPEN_STATE:
                self.update_tooltips()
            if new_value is self.LIGHT_RETAIL_CLOSED_STATE:
                self.update_tooltips(False)

    def on_add(self):
        services.get_event_manager().register(self, (TestEvent.BusinessDataUpdated,))

    def on_remove(self):
        services.get_event_manager().unregister(self, (TestEvent.BusinessDataUpdated,))

    def handle_event(self, sim_info, event:TestEvent, resolver:DataResolver) -> None:
        if event == TestEvent.BusinessDataUpdated:
            self.update_tooltips()

    def update_tooltips(self, show=True):
        for child in self.owner.children:
            child_tooltip = child.tooltip_component
            if child_tooltip is not None:
                if show:
                    child_tooltip.update_object_tooltip()
                else:
                    child_tooltip.update_tooltip_field(TooltipFieldsComplete.mark_up_value_tooltip, None)
                    child_tooltip.update_tooltip_field(TooltipFieldsComplete.simoleon_value, None)

    def on_child_added(self, child, location):
        if not meets_zone_requirement():
            return
        if self.owner.state_value_active(self.LIGHT_RETAIL_ENABLED_STATE):
            vfx_transform = location.world_transform
            if child.live_drag_component.is_ending_drag:
                vfx_transform = location.transform
            self.SET_FOR_SALE_VFX(None, transform_override=vfx_transform).start_one_shot()

    def on_child_removed(self, child, new_location:Location, new_parent=None):
        if not meets_zone_requirement():
            return
        if new_parent is not None and (new_parent is UNSET or new_parent.state_value_active(self.LIGHT_RETAIL_ENABLED_STATE)):
            return
        if self.owner.state_value_active(self.LIGHT_RETAIL_ENABLED_STATE):
            self.SET_NOT_FOR_SALE_VFX(None, transform_override=new_location.world_transform).start_one_shot()

    def get_mark_up_values_for_item(self, child_item):
        business_manager = services.business_service().get_business_manager_for_zone(self.owner.zone_id)
        if business_manager is not None and business_manager.is_open:
            simoleon_value = child_item.get_object_property(GameObjectProperty.MODIFIED_PRICE)
            servings = child_item.get_stat_instance(CraftingTuning.SERVINGS_STATISTIC)
            num_servings = servings.tracker.get_value(CraftingTuning.SERVINGS_STATISTIC) if servings is not None else 0
            if num_servings > 0:
                simoleon_value = num_servings*simoleon_value
            mark_up_value = 0
            if business_manager.business_type == BusinessType.SMALL_BUSINESS:
                mark_up_value = business_manager.small_business_income_data.get_markup_multiplier()
            mark_up_transferred = int((mark_up_value - 1)*100)
            return (mark_up_transferred, simoleon_value)
        return (None, 0)
