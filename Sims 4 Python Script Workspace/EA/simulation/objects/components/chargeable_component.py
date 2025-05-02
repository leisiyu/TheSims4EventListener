from __future__ import annotationsfrom sims4.tuning.tunable_base import GroupNamesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from objects.components.state import StateComponent, ObjectStateValue, StatisticModifierList, ObjectState
    from typing import List
    from statistics.commodity import Commodity
    from autonomy.autonomy_modifier import AutonomyModifierimport clockimport operatorimport protocolbuffersimport servicesimport sims4from objects.components.state_change import StateChangefrom objects.components import Componentfrom objects.components.types import CHARGEABLE_COMPONENTfrom objects.hovertip import TooltipFieldsCompletefrom sims4.common import Packfrom sims4.localization import TunableLocalizedStringfrom sims4.math import Thresholdfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReference, TunableList, TunableMappingfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims4.utils import classproperty
class ChargeableComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=CHARGEABLE_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.PersistableChargeableComponent):
    FACTORY_TUNABLES = {'charge_stat': TunableReference(description='\n            The stat that we want to track\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='Commodity', pack_safe=True), 'draining_text': TunableLocalizedString(description='\n            Charging text in the format Remaining charge {0.Timestamp}\n            '), 'charging_text': TunableLocalizedString(description='\n            Charging text in the format Charging {0.Timestamp}\n            '), 'charging_finished_text': TunableLocalizedString(description='\n            Charging text in the format Charging finished\n            '), 'drained_text': TunableLocalizedString(description='\n            Charging text in the format Drained\n            '), 'charging_state': TunableReference(description="\n            State that changes when it's charging\n            ", manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState', pack_safe=True), 'charging_state_values': TunableList(description='\n            Object State values to determine if the object is being charged or not\n            ', tunable=TunableReference(description='\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', pack_safe=True)), 'draining_state_value': TunableReference(description='\n            Object State values to determine if the object is draining or not\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', pack_safe=True), 'depletion_state': TunableReference(description='\n            Object State values to determine if the object is draining or not\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState', pack_safe=True), 'drained_state_value': TunableReference(description='\n            Object State values to determine if the object is draining or not\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', pack_safe=True), 'charging_state_text_map': TunableMapping(description='\n            Map that defines which cas_part should be equipped depending on the crystal state\n            Key: Charging state value\n            Value: String\n            ', key_name='charging_state', value_name='text', key_type=TunableReference(description='\n                Charging state value', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), value_type=TunableLocalizedString()), 'botched_state_value': TunableReference(description='\n            Botched state value\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), 'botched_state_text': TunableLocalizedString(description='\n            Text to show when the piece of botched')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_remaining_charge_time = 0
        self._last_remaining_drain_time = 0
        self._has_been_charged = False

    @classproperty
    def required_packs(cls):
        return (Pack.SP49,)

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.PersistableChargeableComponent
        data = persistable_data.Extensions[protocols.PersistableChargeableComponent.persistable_data]
        data.has_been_charged = self._has_been_charged
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        data = persistable_data.Extensions[protocols.PersistableChargeableComponent.persistable_data]
        if data.HasField('has_been_charged'):
            self._has_been_charged = data.has_been_charged

    def on_add(self):
        self._refresh()

    def on_added_to_inventory(self):
        self._refresh()

    def on_state_changed(self, state, old_value, new_value, from_init):
        if self._is_charging():
            self._has_been_charged = True
        self._refresh()

    def get_decay_modifiers(self, state:'ObjectState') -> 'List[AutonomyModifier]':
        list_modifiers = []
        if StateChange.AUTONOMY_MODIFIERS in state.new_client_state.ops:
            modifiers = state.new_client_state.ops[StateChange.AUTONOMY_MODIFIERS]
            for modifier in modifiers.autonomy_modifiers:
                if modifier.decay_modifiers is not None and self.charge_stat in modifier.decay_modifiers:
                    list_modifiers.append(modifier)
        return list_modifiers

    def _get_charging_text(self) -> 'TunableLocalizedString':
        return self.charging_state_text_map[self.owner.state_component.get_state(self.charging_state)]

    def _get_remaining_charge_time(self, stat:'Commodity') -> 'int':
        time = stat.get_decay_time(Threshold(0, operator.le), use_decay_modifier=False)
        current_value = time if time is not None and time > 0 else stat.get_value()
        list_modifiers = self.get_decay_modifiers(self.draining_state_value)
        state_component = self.owner.state_component
        if state_component.has_state(self.depletion_state):
            list_modifiers.extend(self.get_decay_modifiers(self.owner.state_component.get_state(self.depletion_state)))
        modifier_value = 1
        for modifier in list_modifiers:
            modifier_value *= modifier.decay_modifiers[self.charge_stat]
        res = current_value/modifier_value
        return res

    def get_timer_message(self, is_charge_station:'bool'=False) -> 'protocolbuffers.UI_pb2.ObjectTimer':
        is_botched = self._is_botched()
        if self._has_been_charged or not is_botched:
            return
        statistic_component = self.owner.statistic_component
        if statistic_component is None:
            return
        commodity_tracker = statistic_component.get_commodity_tracker()
        if commodity_tracker is None:
            return
        stat = statistic_component.get_stat_instance(self.charge_stat)
        if stat is None:
            return
        charging_message = None
        is_charging = False
        is_draining = False
        is_drained = False
        if is_botched:
            time = 0
            text = self.botched_state_text
            finished_text = self.botched_state_text
        else:
            is_charging = self._is_charging()
            is_draining = self._is_draining()
            is_drained = self._is_drained()
            if is_charging:
                time = commodity_tracker.get_decay_time(self.charge_stat, Threshold(stat.max_value))
                charging_message = self._get_charging_text()
                if time is not None:
                    self._last_remaining_charge_time = time
                else:
                    time = self._last_remaining_charge_time
                text = self.charging_finished_text if time == 0 else self.charging_text
                finished_text = self.charging_finished_text
            else:
                if is_draining:
                    time = stat.get_decay_time(Threshold(0, operator.le), use_decay_modifier=True)
                    if time is not None:
                        self._last_remaining_drain_time = time
                    else:
                        time = self._last_remaining_drain_time
                elif is_drained:
                    time = 0
                else:
                    time = self._get_remaining_charge_time(stat)
                text = self.drained_text if time == 0 else self.draining_text
                finished_text = self.drained_text
        game_clock = services.game_clock_service()
        timer_msg = protocolbuffers.UI_pb2.ObjectTimer()
        timer_msg.last_updated_time = game_clock.now() + clock.interval_in_sim_minutes(time)
        timer_msg.time = int(time)
        timer_msg.text = text
        timer_msg.finished_text = finished_text
        timer_msg.must_update_timer = is_charging or is_draining
        if not is_charge_station:
            timer_msg.timer_header = charging_message
        return timer_msg

    def _is_charging(self) -> 'bool':
        return self.owner.state_component.get_state(self.charging_state) in self.charging_state_values

    def _is_draining(self) -> 'bool':
        return self.owner.state_component.get_state(self.charging_state) == self.draining_state_value

    def _is_botched(self) -> 'bool':
        return self.owner.state_component.get_state(self.botched_state_value.state) == self.botched_state_value

    def _is_drained(self) -> 'bool':
        return self.owner.state_component.get_state(self.drained_state_value.state) == self.drained_state_value

    def _refresh(self):
        timer_msg = self.get_timer_message()
        timer_msgs = []
        if timer_msg is not None:
            timer_msgs.append(timer_msg)
        tooltip_component = self.owner.tooltip_component
        if tooltip_component is not None:
            tooltip_component.update_tooltip_field(TooltipFieldsComplete.object_timers, timer_msgs, should_update=True, immediate=True)
