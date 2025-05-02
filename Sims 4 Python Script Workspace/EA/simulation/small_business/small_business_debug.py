import servicesfrom objects.components import sim_visualizer_componentfrom objects.components.sim_visualizer_enum import SimVisualizerFlag
def update_small_business_situation_debug_visualizer(sim):
    if False and sim_visualizer_component.is_enabled(SimVisualizerFlag.SMALL_BUSINESS_SATISFACTION) and sim:
        sim.update_visualizer_for_flag(SimVisualizerFlag.SMALL_BUSINESS_SATISFACTION)

def update_small_business_reviews_debug_visualizer(sim_id):
    if False and sim_visualizer_component.is_enabled(SimVisualizerFlag.SMALL_BUSINESS_REVIEWS):
        owner_sim_info = services.sim_info_manager().get(sim_id)
        sim = owner_sim_info.get_sim_instance()
        if sim:
            sim.update_visualizer_for_flag(SimVisualizerFlag.SMALL_BUSINESS_REVIEWS)
