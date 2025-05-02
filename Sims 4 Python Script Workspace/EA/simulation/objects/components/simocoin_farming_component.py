from __future__ import annotationsimport clockimport protocolbuffersimport servicesimport sims4from objects.components import Componentfrom objects.components.types import SIMOCOIN_FARMING_COMPONENTfrom objects.hovertip import TooltipFieldsCompletefrom sims4.common import Packfrom sims4.localization import TunableLocalizedStringfrom sims4.math import Thresholdfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunablePackSafeReferencefrom sims4.utils import classpropertyfrom protocolbuffers import UI_pb2 as ui_protocols
class SimoCoinFarmingComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=SIMOCOIN_FARMING_COMPONENT):
    FACTORY_TUNABLES = {'farming_stat': TunablePackSafeReference(description='\n            The stat that we want to track\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='Commodity'), 'farming_text': TunableLocalizedString(description="\n            'Crypto farming' text\n            "), 'farming_finished_text': TunableLocalizedString(description="\n            'Crypto farming' text\n            "), 'remaining_time_farming_text': TunableLocalizedString(description='\n            Farming text in the format {0.Timestamp} until farming is complete\n            '), 'farming_state_value': TunablePackSafeReference(description="\n            State that changes when it's farming\n            ", manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), 'farming_state': TunablePackSafeReference(description="\n            State that changes when it's farming\n            ", manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_remaining_farming_time = 0

    @classproperty
    def required_packs(cls):
        return (Pack.EP18,)

    def on_state_changed(self, state, old_value, new_value, from_init):
        if state is self.farming_state and new_value is not self.farming_state_value:
            self.owner.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_DISABLED
            self.owner.update_object_tooltip()
        else:
            self._refresh()

    def get_timer_message(self) -> 'protocolbuffers.UI_pb2.ObjectTimer':
        is_farming = self._is_farming()
        if not is_farming:
            return
        statistic_component = self.owner.statistic_component
        if statistic_component is None:
            return
        commodity_tracker = statistic_component.get_commodity_tracker()
        if commodity_tracker is None:
            return
        stat = statistic_component.get_stat_instance(self.farming_stat)
        if stat is None:
            return
        time = 0
        if is_farming:
            min_value = stat.min_value + 1
            time = commodity_tracker.get_decay_time(self.farming_stat, Threshold(min_value))
            if time is not None:
                self._last_remaining_farming_time = time
            else:
                time = self._last_remaining_farming_time
        game_clock = services.game_clock_service()
        timer_msg = protocolbuffers.UI_pb2.ObjectTimer()
        timer_msg.last_updated_time = game_clock.now() + clock.interval_in_sim_minutes(time)
        timer_msg.time = int(time)
        timer_msg.text = self.remaining_time_farming_text
        timer_msg.finished_text = self.farming_finished_text
        timer_msg.must_update_timer = is_farming
        timer_msg.timer_header = self.farming_text if is_farming else self.farming_finished_text
        return timer_msg

    def _is_farming(self) -> 'bool':
        statistic_component = self.owner.statistic_component
        commodity_tracker = statistic_component.get_commodity_tracker()
        if commodity_tracker is None:
            return False
        stat = statistic_component.get_stat_instance(self.farming_stat)
        if stat is None:
            return False
        else:
            current_state = self.owner.state_component.get_state(self.farming_state)
            if current_state is self.farming_state_value:
                time = commodity_tracker.get_decay_time(self.farming_stat, Threshold(stat.min_value))
                return time is not None and time > 0
        return False

    def _refresh(self):
        timer_msg = self.get_timer_message()
        timer_msgs = None
        if timer_msg is not None:
            timer_msgs = [timer_msg]
        tooltip_component = self.owner.tooltip_component
        if tooltip_component is not None:
            tooltip_component.update_tooltip_field(TooltipFieldsComplete.object_timers, timer_msgs, should_update=True, immediate=True)
