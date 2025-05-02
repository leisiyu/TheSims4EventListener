from __future__ import annotationsfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKING, Setif TYPE_CHECKING:
    from interactions.interaction_queue import InteractionQueue
    from interactions.si_state import SIState
    from sims.sim import Simimport servicesimport sims4.reloadfrom debugvis import Contextfrom business.business_enums import BusinessTypefrom objects.components import Component, componentmethod_with_fallbackfrom objects.components.sim_visualizer_enum import SimVisualizerFlag, SimVisualizerDatafrom objects.components.types import SIM_VISUALIZER_COMPONENTfrom sims4.math import UP_AXISwith sims4.reload.protected(globals()):
    _sim_visualizers = dict()
    _sim_visualizations_enabled = 0
    _global_mode_enabled = False
def any_enabled():
    return bool(_sim_visualizations_enabled)

def is_enabled(flag:'SimVisualizerFlag'):
    return flag & _sim_visualizations_enabled

def set_global_mode(enable:'bool'):
    global _global_mode_enabled
    _global_mode_enabled = enable

def global_mode_enabled() -> 'bool':
    return _global_mode_enabled

def enable_visualization(flag:'SimVisualizerFlag'):
    global _sim_visualizations_enabled
    _sim_visualizations_enabled |= flag

def disable_visualization(flag:'SimVisualizerFlag'):
    global _sim_visualizations_enabled
    _sim_visualizations_enabled ^= flag

class SimVisualizer:
    BONE_INDEX = 0
    BONE_OFFSET = UP_AXIS*-0.2

    def __init__(self, sim:'Sim', layer):
        self._layer = layer
        self._sim_ref = sim.ref()
        self._vis_helpers = {SimVisualizerFlag.SMALL_BUSINESS_REVIEWS: SmallBusinessReviewsVisualizationHelper, SimVisualizerFlag.SMALL_BUSINESS_SATISFACTION: SmallBusinessSatisfactionVisualizationHelper, SimVisualizerFlag.INTERACTION_QUEUE: InteractionQueueVisualizationHelper, SimVisualizerFlag.SITUATIONS: SituationVisualizationHelper}
        self._vis_data = dict()

    @property
    def layer(self):
        return self._layer

    def start(self):
        sim = self._sim_ref()
        if not sim:
            return
        if is_enabled(SimVisualizerFlag.NAME):
            self._update_name_visualizer(sim)
        if is_enabled(SimVisualizerFlag.SI_STATE):
            self._attach_si_state_watcher(sim)
        for helper in self._vis_helpers.values():
            if not is_enabled(helper.visualizer_flag):
                pass
            else:
                helper.update(sim, self)
        self._update_vis_layer()

    def add_data(self, key:'SimVisualizerData', data:'str', update_vis:'bool'=True):
        self._vis_data[key] = data
        if update_vis:
            self._update_vis_layer()

    def enable_vis_flag(self, flag:'SimVisualizerFlag'):
        sim = self._sim_ref()
        if not sim:
            return
        if flag == SimVisualizerFlag.NAME:
            self._update_name_visualizer(sim)
        elif flag == SimVisualizerFlag.SI_STATE:
            self._attach_si_state_watcher(sim)
        elif flag in self._vis_helpers:
            self._vis_helpers[flag].update(sim, self)
        self._update_vis_layer()

    def _update_name_visualizer(self, sim):
        self.add_data(SimVisualizerData.NAME, sim.full_name, update_vis=False)

    def _attach_si_state_watcher(self, sim):
        if SimVisualizerFlag.SI_STATE not in self._vis_helpers:
            self._vis_helpers[SimVisualizerFlag.SI_STATE] = SuperInteractionStateVisualizationHelper()
        helper = self._vis_helpers[SimVisualizerFlag.SI_STATE]
        helper.attach(sim, self.update_vis_flag)
        helper.update(sim, self)

    def disable_vis_flag(self, flag:'SimVisualizerFlag'):
        sim = self._sim_ref()
        if not sim:
            return
        if flag == SimVisualizerFlag.NAME:
            self.clear_data(SimVisualizerData.NAME)
        elif flag == SimVisualizerFlag.SI_STATE:
            helper = self._vis_helpers.get(SimVisualizerFlag.SI_STATE)
            if helper:
                helper.detach(sim)
                for data_key in helper.data_keys:
                    self.clear_data(data_key)
                del self._vis_helpers[SimVisualizerFlag.SI_STATE]
        if flag in self._vis_helpers:
            for data_key in self._vis_helpers[flag].data_keys:
                self.clear_data(data_key)
        self._update_vis_layer()

    def update_vis_flag(self, flag:'SimVisualizerFlag'):
        if flag not in self._vis_helpers:
            raise RuntimeError(f'No visualization helper associated with {flag}')
        sim = self._sim_ref()
        if not sim:
            return
        self._vis_helpers[flag].update(sim, self)
        self._update_vis_layer()

    def clear_data(self, key:'SimVisualizerData'):
        if key in self._vis_data:
            del self._vis_data[key]

    def _update_vis_layer(self):
        sim = self._sim_ref()
        if not sim:
            return
        with Context(self._layer) as layer:
            text = '\n'.join(self._vis_data[k] for k in sorted(self._vis_data))
            layer.add_text_object(sim, self.BONE_OFFSET, text, bone_index=self.BONE_INDEX)

    def stop(self):
        pass

class SimVisualizerComponent(Component, component_name=SIM_VISUALIZER_COMPONENT):
    VIS_NAME = 'SimVisComponent'

    def on_add(self):
        from server_commands.visualization_commands import _start_sim_visualizer
        _start_sim_visualizer(self.owner, services.client_manager().get_first_client_id(), self.VIS_NAME, _sim_visualizers, SimVisualizer)
        visualizer = self._get_visualizer()
        self.owner.on_start_up.append(lambda _: visualizer.start())

    def _get_visualizer(self) -> 'SimVisualizer':
        visualizer_key = (self.owner.id, self.VIS_NAME)
        visualizer = _sim_visualizers.get(visualizer_key)
        return visualizer

    @componentmethod_with_fallback(lambda *_, **__: None)
    def add_visualizer_data(self, key:'SimVisualizerData', data:'str'):
        self._get_visualizer().add_data(key, data)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def update_visualizer_for_flag(self, flag:'SimVisualizerFlag'):
        visualizer = self._get_visualizer()
        if visualizer is not None:
            visualizer.update_vis_flag(flag)

    def enable_vis_flag(self, flag:'SimVisualizerFlag'):
        visualizer = self._get_visualizer()
        visualizer.enable_vis_flag(flag)

    def disable_vis_flag(self, flag:'SimVisualizerFlag'):
        visualizer = self._get_visualizer()
        visualizer.disable_vis_flag(flag)

    def on_remove(self):
        from server_commands.visualization_commands import _stop_sim_visualizer
        _stop_sim_visualizer(self.owner, services.client_manager().get_first_client_id(), self.VIS_NAME, _sim_visualizers)

class SimVisualizationHelper:

    @classproperty
    def visualizer_flag(cls) -> 'SimVisualizerFlag':
        raise NotImplementedError

    @classmethod
    def update(cls, sim:'Sim', visualizer:'SimVisualizer'):
        raise NotImplementedError

    @classproperty
    def data_keys(self) -> 'Set[SimVisualizerData]':
        raise NotImplementedError

class SituationVisualizationHelper(SimVisualizationHelper):
    _KEYS = {SimVisualizerData.SITUATIONS_SIM_IS_IN, SimVisualizerData.SITUATION_JOBS, SimVisualizerData.SITUATION_ROLES}

    @classproperty
    def visualizer_flag(cls) -> 'SimVisualizerFlag':
        return SimVisualizerFlag.SITUATIONS

    @classmethod
    def update(cls, sim:'Sim', visualizer:'SimVisualizer'):
        sim_situations = services.get_zone_situation_manager().get_situations_sim_is_in(sim)
        if not sim_situations:
            for key in cls.data_keys:
                visualizer.clear_data(key)
            return
        situations_str = ', '.join(str(sit.__class__.__name__) for sit in sim_situations)
        jobs_str = ', '.join(str(sit.get_current_job_for_sim(sim).__name__) for sit in sim_situations)
        roles_str = ', '.join(str(sit.get_current_role_state_for_sim(sim).__name__) for sit in sim_situations)
        visualizer.add_data(SimVisualizerData.SITUATIONS_SIM_IS_IN, f'Situation(s): {situations_str}')
        visualizer.add_data(SimVisualizerData.SITUATION_JOBS, f'Job(s): {jobs_str}')
        visualizer.add_data(SimVisualizerData.SITUATION_ROLES, f'Role(s): {roles_str}')

    @classproperty
    def data_keys(cls) -> 'Set[SimVisualizerData]':
        return cls._KEYS

class SmallBusinessSatisfactionVisualizationHelper(SimVisualizationHelper):
    _KEYS = {SimVisualizerData.SATISFACTION_RANKING, SimVisualizerData.SATISFACTION_PERFORM_INTERACTION, SimVisualizerData.SATISFACTION_WAIT_RATIO, SimVisualizerData.SATISFACTION_INDEX_WAIT_RATIO, SimVisualizerData.SATISFACTION_INTERACTION_COUNTER, SimVisualizerData.SATISFACTION_BUFF_BUCKET_TOTALS, SimVisualizerData.SATISFACTION_BUCKET_TOTAL, SimVisualizerData.SATISFACTION_MARKUP_RATIO}

    @classproperty
    def visualizer_flag(cls) -> 'SimVisualizerFlag':
        return SimVisualizerFlag.SMALL_BUSINESS_SATISFACTION

    @classmethod
    def update(cls, sim:'Sim', visualizer:'SimVisualizer'):
        business_manager = services.business_service().get_business_manager_for_zone(services.current_zone_id())
        sim_situations = services.get_zone_situation_manager().get_situations_sim_is_in(sim)
        if not (sim_situations and business_manager):
            for key in cls.data_keys:
                visualizer.clear_data(key)
            return
        star_rating = business_manager.get_customer_star_rating(sim.id)
        visualizer.add_data(SimVisualizerData.SATISFACTION_RANKING, f'Star Rank: {star_rating}')
        perform_str = ', '.join(sit.get_visualizer_data_string(SimVisualizerData.SATISFACTION_PERFORM_INTERACTION) for sit in sim_situations)
        visualizer.add_data(SimVisualizerData.SATISFACTION_PERFORM_INTERACTION, f'Is Performing: {perform_str}')
        wait_ratio_str = ', '.join(sit.get_visualizer_data_string(SimVisualizerData.SATISFACTION_WAIT_RATIO) for sit in sim_situations)
        index_wait_ratio_str = ', '.join(sit.get_visualizer_data_string(SimVisualizerData.SATISFACTION_INDEX_WAIT_RATIO) for sit in sim_situations)
        visualizer.add_data(SimVisualizerData.SATISFACTION_WAIT_RATIO, f'Wait Ratio: {wait_ratio_str} Index reward : {index_wait_ratio_str}')
        interaction_counter_str = ', '.join(str(sit.get_visualizer_data_string(SimVisualizerData.SATISFACTION_INTERACTION_COUNTER)) for sit in sim_situations)
        visualizer.add_data(SimVisualizerData.SATISFACTION_INTERACTION_COUNTER, f'Interaction Counter: {interaction_counter_str}')
        buff_bucket_total = business_manager.get_customer_bucket_totals(sim.id)
        if buff_bucket_total is not None:
            buff_bucket_total_result = []
            star_curve = business_manager.tuning_data.customer_star_buff_bucket_to_rating_curve
            total_bucket = 0
            if star_curve is not None:
                star_value = business_manager.tuning_data.default_customer_star_rating
                curve_values = star_curve.get_inverse_function_values(star_value)
                if len(curve_values) > 0:
                    total_bucket = curve_values[0]
            for (key, value) in business_manager.get_customer_bucket_totals(sim.id).items():
                num = business_manager.get_interpolated_buff_bucket_value(key, value)
                buff_bucket_total_result.append(f'{key}: {num}')
                total_bucket += num
            buff_bucket_total_str = '\n'.join(buff_bucket_total_result)
            visualizer.add_data(SimVisualizerData.SATISFACTION_BUFF_BUCKET_TOTALS, f'Buff bucket totals:
{buff_bucket_total_str}')
            visualizer.add_data(SimVisualizerData.SATISFACTION_BUCKET_TOTAL, f'bucket total: {total_bucket}')
        markup_ratio_str = ', '.join(str(sit.get_visualizer_data_string(SimVisualizerData.SATISFACTION_MARKUP_RATIO)) for sit in sim_situations)
        visualizer.add_data(SimVisualizerData.SATISFACTION_MARKUP_RATIO, f'Satisfaction Markup Ratio: {markup_ratio_str}')

    @classproperty
    def data_keys(cls) -> 'Set[SimVisualizerData]':
        return cls._KEYS
