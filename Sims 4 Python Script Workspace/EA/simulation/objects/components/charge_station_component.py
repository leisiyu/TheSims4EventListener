from objects.components import Componentfrom objects.components.state import StateComponentfrom objects.components.tooltip_component import TooltipComponentfrom objects.components.types import CHARGING_STATION_COMPONENT, CHARGEABLE_COMPONENTfrom objects.hovertip import TooltipFieldsfrom routing import Locationfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.math import Thresholdfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReference, TunableList
class ChargingStationComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=CHARGING_STATION_COMPONENT):

    def on_add(self):
        self._refresh()

    def on_remove(self):
        self._refresh()
        for child in self.owner.children:
            state_component = child.state_component
            state_component.remove_state_changed_callback(self._on_child_state_changed)

    def on_child_added(self, child, location):
        state_component = child.state_component
        state_component.add_state_changed_callback(self._on_child_state_changed)
        self._refresh()

    def _on_child_state_changed(self, owner, state, old_value, new_value):
        self._refresh()

    def on_child_removed(self, child, new_location:Location, new_parent=None):
        state_component = child.state_component
        state_component.remove_state_changed_callback(self._on_child_state_changed)
        self._refresh()

    def on_state_changed(self, state, old_value, new_value, from_init):
        self._refresh()

    def _refresh(self):
        timer_msgs = []
        for child in self.owner.children:
            chargeable_component = child.get_component(CHARGEABLE_COMPONENT)
            if chargeable_component:
                timer_msg = chargeable_component.get_timer_message(True)
            if timer_msg is not None:
                timer_msg.object_name = LocalizationHelperTuning.get_object_name(child.definition)
                timer_msgs.append(timer_msg)
        tooltip_component = self.owner.tooltip_component
        if tooltip_component is not None:
            tooltip_component.update_tooltip_field(TooltipFields.object_timers, timer_msgs, should_update=True, immediate=True)
