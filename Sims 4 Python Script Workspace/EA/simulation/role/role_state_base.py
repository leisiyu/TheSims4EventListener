import weakreffrom event_testing.resolver import SingleSimResolverfrom interactions.interaction_finisher import FinishingTypefrom objects.doors.door_tuning import DoorTuningfrom sims4.utils import classpropertyimport functoolsimport servicesimport sims4.loglogger = sims4.log.Logger('Roles')
class RoleStateBase:

    @classproperty
    def role_priority(cls):
        raise NotImplementedError

    @classproperty
    def buffs(cls):
        raise NotImplementedError

    @classproperty
    def off_lot_autonomy_buff(cls):
        raise NotImplementedError

    @classproperty
    def role_specific_affordances(cls):
        raise NotImplementedError

    @classproperty
    def on_activate(cls):
        raise NotImplementedError

    @classproperty
    def portal_disallowance_tags(self):
        return set()

    @classproperty
    def allow_npc_routing_on_active_lot(cls):
        raise NotImplementedError

    @classproperty
    def autonomy_state_override(cls):
        raise NotImplementedError

    def __init__(self, sim):
        self._sim_ref = sim.ref()
        self._buff_handles = []
        self._off_lot_autonomy_buff_handle = None
        self._interaction_id_to_cancel = None
        self._on_hit_marks_push_affordance_callback = None
        self._role_affordance_target_ref = None
        self._situation_ref = None

    @property
    def sim(self):
        if self._sim_ref is not None:
            return self._sim_ref()

    def _ungreeted_sim_disallowed_from_portal(self, portal):
        if portal.is_ungreeted_sim_disallowed():
            return True
        portal_disallowed_tags = portal.get_portal_disallowed_tags()
        if not portal_disallowed_tags & self.portal_disallowance_tags:
            return False
        if portal.state_component is None:
            return False
        if portal.state_component.state_value_active(DoorTuning.FRONT_DOOR_AVAILABILITY_STATE.enabled):
            return True
        if portal.state_component.state_value_active(DoorTuning.FRONT_DOOR_STATE.enabled):
            return True
        elif portal.state_component.state_value_active(DoorTuning.INACTIVE_APARTMENT_DOOR_STATE.enabled) and self.sim.household_id != portal.household_owner_id:
            return True
        return False

    def _refresh_door_portal_allowance(self, portal):
        if self._ungreeted_sim_disallowed_from_portal(portal):
            portal.add_disallowed_object(self.sim, self)
        else:
            portal.remove_disallowed_object(self.sim, self)

    def _refresh_all_door_portal_allowance(self):
        object_manager = services.object_manager()
        for portal in object_manager.portal_cache_gen():
            self._refresh_door_portal_allowance(portal)

    def _apply_commodity_flag(self, affordances, add_dynamic_commodity_flag_function):
        flags = set()
        for affordance in affordances:
            flags |= affordance.commodity_flags
        if flags:
            add_dynamic_commodity_flag_function(self, flags)

    def on_role_activate(self, role_affordance_target=None, situation=None, reactivate=False, **affordance_override_kwargs):
        if self.portal_disallowance_tags:
            self._refresh_all_door_portal_allowance()
            object_manager = services.object_manager()
            object_manager.register_portal_added_callback(self._refresh_door_portal_allowance)
            object_manager.register_front_door_candidates_changed_callback(self._refresh_all_door_portal_allowance)
            object_manager.register_all_portals_refreshed_callback(self._refresh_all_door_portal_allowance)
        for buff_ref in self.buffs:
            if buff_ref is None:
                logger.warn('{} has empty buff in buff list. Please fix tuning.', self)
            else:
                self._buff_handles.append(self.sim.add_buff(buff_ref.buff_type, buff_reason=buff_ref.buff_reason))
        if self.off_lot_autonomy_buff.buff_type is not None:
            self._off_lot_autonomy_buff_handle = self.sim.add_buff(self.off_lot_autonomy_buff.buff_type, buff_reason=self.off_lot_autonomy_buff.buff_reason)
        self._apply_commodity_flag(self.role_specific_affordances, self.sim.add_dynamic_commodity_flags)
        self._apply_commodity_flag(self.preroll_affordances, self.sim.add_dynamic_preroll_commodity_flags)
        zone = services.current_zone()
        if self.off_lot_autonomy_buff is not None and self.on_activate is not None:
            if not reactivate:
                if role_affordance_target is not None:
                    self._role_affordance_target_ref = weakref.ref(role_affordance_target)
                if situation is not None:
                    self._situation_ref = weakref.ref(situation)
            else:
                role_affordance_target = self._role_affordance_target_ref() if self._role_affordance_target_ref is not None else None
                situation = self._situation_ref() if self._situation_ref is not None else None
            defer_activate_on_load = self.on_activate.defer_on_activate_to_hitting_marks
            run_on_activate_on_load = not (defer_activate_on_load or self.on_activate.skip_on_load)
            if run_on_activate_on_load or zone.is_zone_running:
                self._interaction_id_to_cancel = self.on_activate(self, role_affordance_target, situation=situation, **affordance_override_kwargs)
            elif defer_activate_on_load:
                self._on_hit_marks_push_affordance_callback = functools.partial(self.on_activate, self, role_affordance_target, situation=situation, **affordance_override_kwargs)
        if not self.allow_npc_routing_on_active_lot:
            self.sim.inc_lot_routing_restriction_ref_count()

    def on_hit_their_marks(self):
        if self._on_hit_marks_push_affordance_callback is not None:
            self._interaction_id_to_cancel = self._on_hit_marks_push_affordance_callback()
        if self.loot_on_load:
            resolver = SingleSimResolver(self.sim.sim_info)
            for loot_action in self.loot_on_load:
                loot_action.apply_to_resolver(resolver)

    def _get_target_for_push_affordance(self, target_type):
        raise NotImplementedError

    def on_role_deactivated(self):
        sim = self.sim
        if sim is None:
            return
        if self.portal_disallowance_tags:
            object_manager = services.object_manager()
            object_manager.unregister_portal_added_callback(self._refresh_door_portal_allowance)
            object_manager.unregister_front_door_candidates_changed_callback(self._refresh_all_door_portal_allowance)
            object_manager.unregister_all_portals_refreshed_callback(self._refresh_all_door_portal_allowance)
            for portal in object_manager.portal_cache_gen():
                portal.remove_disallowed_object(self.sim, self)
        for buff_handle in self._buff_handles:
            sim.remove_buff(buff_handle)
        self._buff_handles = []
        if self._off_lot_autonomy_buff_handle is not None:
            sim.remove_buff(self._off_lot_autonomy_buff_handle)
            self._off_lot_autonomy_buff_handle = None
        if self.role_specific_affordances:
            self.sim.remove_dynamic_commodity_flags(self)
        if self.preroll_affordances:
            self.sim.remove_dynamic_preroll_commodity_flags(self)
        if not self.allow_npc_routing_on_active_lot:
            self.sim.dec_lot_routing_restriction_ref_count()
        if self._interaction_id_to_cancel is not None:
            for interaction in sim.get_all_running_and_queued_interactions():
                if not interaction.id == self._interaction_id_to_cancel:
                    if interaction.is_continuation_by_id(self._interaction_id_to_cancel):
                        interaction.cancel(FinishingType.SITUATIONS, 'Role State owning Interaction was deactivated')
                interaction.cancel(FinishingType.SITUATIONS, 'Role State owning Interaction was deactivated')
