import servicesfrom event_testing.test_events import TestEventfrom sims4.tuning.instances import lock_instance_tunablesfrom situations.custom_states.custom_states_situation import CustomStatesSituationfrom situations.situation import Situationfrom situations.situation_time_jump import SituationTimeJumpSimulate
class TemporaryCloneSituation(CustomStatesSituation):
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._register_test_event(TestEvent.HouseholdChanged)

    def load_situation(self):
        clone_guest_info = next(iter(self._guest_list.get_persisted_sim_guest_infos()))
        if clone_guest_info is None:
            return False
        clone_sim_info = services.sim_info_manager().get(clone_guest_info.sim_id)
        if clone_sim_info is None:
            return False
        if not clone_sim_info.household.hidden:
            return False
        if clone_sim_info.zone_id != services.current_zone_id():
            self._remove_clone_sim_info(clone_sim_info)
            return False
        return super().load_situation()

    def _destroy(self):
        zone = services.current_zone()
        if zone is not None and not zone.is_zone_shutting_down:
            clone_sim = self.get_clone()
            self._remove_clone_sim_info(clone_sim)
        super()._destroy()

    def get_clone(self):
        for sim in self._situation_sims:
            return sim

    def sim_left_lot(self):
        self._register_test_event(TestEvent.ObjectDestroyed)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj = resolver.get_resolved_arg('obj')
            if destroyed_obj is self.get_clone():
                self._self_destruct()
        if event == TestEvent.HouseholdChanged:
            removed_sim = resolver.event_kwargs.get('sim_removed')
            if removed_sim is not None:
                return
            if not self.is_sim_info_in_situation(sim_info):
                return
            if not sim_info.household.hidden:
                self._self_destruct()

    @classmethod
    def _remove_clone_sim_info(cls, clone_sim):
        if clone_sim is not None and clone_sim.household.hidden:
            services.sim_info_manager().remove_permanently(clone_sim.sim_info)
lock_instance_tunables(TemporaryCloneSituation, duration=0, time_jump=SituationTimeJumpSimulate())