from weakref import WeakSetfrom clock import interval_in_real_secondsfrom element_utils import soft_sleep_foreverfrom event_testing.resolver import SingleObjectResolverfrom indexed_manager import CallbackTypesfrom interactions import ParticipantTypefrom interactions.priority import PriorityExtendedfrom interactions.privacy import PrivacyViolatorsfrom interactions.utils.loot import LootOperationListfrom objects.components import Component, types, componentmethod, componentmethod_with_fallbackfrom objects.components.utils.footprint_toggle_mixin import FootprintToggleMixinfrom objects.object_enums import ObjectRoutingBehaviorTrackingCategoryfrom routing.object_routing.object_routing_priority import ObjectRoutingPriorityfrom routing.route_enums import RoutingStageEventfrom sims.master_controller import WorkRequestfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableMapping, TunableReference, OptionalTunable, TunableTuple, TunableList, TunableEnumEntry, Tunablefrom singletons import UNSETimport alarmsimport servicesimport sims4.resources
class ObjectRoutingComponent(FootprintToggleMixin, Component, HasTunableFactory, AutoFactoryInit, component_name=types.OBJECT_ROUTING_COMPONENT):
    FACTORY_TUNABLES = {'routing_behavior_map': TunableMapping(description='\n            A mapping of states to behavior. When the object enters a state, its\n            corresponding routing behavior is started.\n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), value_type=OptionalTunable(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('ObjectRoutingBehavior',)), enabled_by_default=True, enabled_name='Start_Behavior', disabled_name='Stop_All_Behavior', disabled_value=UNSET)), 'privacy_rules': OptionalTunable(description='\n            If enabled, this object will care about privacy regions.\n            ', tunable=TunableTuple(description='\n                Privacy rules for this object.\n                ', on_enter=TunableTuple(description='\n                    Tuning for when this object is considered a violator of\n                    privacy.\n                    ', loot_list=TunableList(description='\n                        A list of loot operations to apply when the object\n                        enters a privacy region.\n                        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))))), 'tracking_category': TunableEnumEntry(description='\n            Used to classify routing objects for the purpose of putting them\n            into buckets for the object routing service to restrict the number\n            of simultaneously-active objects.\n            ', tunable_type=ObjectRoutingBehaviorTrackingCategory, default=ObjectRoutingBehaviorTrackingCategory.NONE), 'disable_fake_portals': Tunable(description='\n            If enabled, we will disable fake portals, such as curbs,\n            from being generated for routes with this object.\n            ', tunable_type=bool, default=False), 'allow_target_object_cache': Tunable(description="\n            If enabled, allow routable objects to cache target objects that\n            they may route to. Will try to prevent two routable objects from\n            selecting the same target. This applies only to the From Target\n            Object behavior type.\n            \n            e.g. Enabled for bots so they won't clean the same item. Disabled\n            for chickens so they can continue returning to the same coop.\n            ", tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running_behavior = None
        self._idle_element = None
        self._previous_parent_ref = None
        self._pending_running_behavior = None
        self._privacy_violations = WeakSet()
        self.locators = None
        self._social_transform_constraint = None
        self._controlling_social_interaction_id = None
        self._setup_completed = False
        self._deferred_behavior_type = None
        self._deferred_alarm_handle = None

    @property
    def previous_parent(self):
        if self._previous_parent_ref is not None:
            return self._previous_parent_ref()

    def _setup(self):
        if self._setup_completed:
            return
        self.owner.routing_component.pathplan_context.disable_fake_portals = self.disable_fake_portals
        master_controller = services.get_master_controller()
        master_controller.add_sim(self.owner)
        object_routing_service = services.get_object_routing_service()
        object_routing_service.add_routable_object(self.owner)
        if self.privacy_rules:
            privacy_service = services.privacy_service()
            privacy_service.add_vehicle_to_monitor(self.owner)
        self.owner.routing_component.on_sim_added()
        self.add_callbacks()
        self.owner.update_portal_locks()
        self._setup_completed = True

    def on_add(self, *_, **__):
        zone = services.current_zone()
        if not zone.is_zone_loading:
            self._setup()

    def on_finalize_load(self):
        self._setup()

    def on_remove(self):
        self._remove_target_callbacks()
        self.remove_callbacks()
        self.owner.routing_component.on_sim_removed()
        master_controller = services.get_master_controller()
        master_controller.remove_sim(self.owner)
        if self._running_behavior is not None:
            self._running_behavior.trigger_hard_stop()
        self._cancel_idle_behavior()
        object_routing_service = services.get_object_routing_service()
        object_routing_service.remove_routable_object(self.owner)
        if self.privacy_rules:
            privacy_service = services.privacy_service()
            privacy_service.remove_vehicle_to_monitor(self.owner)

    def add_callbacks(self):
        if self.privacy_rules:
            self.owner.register_on_location_changed(self._check_privacy)
        self.register_routing_event_callbacks()
        zone = services.current_zone()
        if zone is not None:
            zone.navmesh_change_callbacks.append(self._on_navmesh_updated)
            zone.wall_contour_update_callbacks.append(self._on_navmesh_updated)

    def remove_callbacks(self):
        if self.owner.is_on_location_changed_callback_registered(self._check_privacy):
            self.owner.unregister_on_location_changed(self._check_privacy)
        self.unregister_routing_event_callbacks()
        zone = services.current_zone()
        if zone is not None:
            if self._on_navmesh_updated in zone.navmesh_change_callbacks:
                zone.navmesh_change_callbacks.remove(self._on_navmesh_updated)
            if self._on_navmesh_updated in zone.wall_contour_update_callbacks:
                zone.wall_contour_update_callbacks.remove(self._on_navmesh_updated)

    def _add_target_callbacks(self):
        if self._running_behavior is None:
            return
        target_object = self._running_behavior.get_target_object()
        if target_object is None:
            return
        target_object.register_on_location_changed(self._on_target_location_changed)
        object_manager = services.object_manager()
        if object_manager is not None:
            object_manager.register_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_target_removed)

    def _remove_target_callbacks(self):
        if self._running_behavior is None:
            return
        target_object = self._running_behavior.get_target_object()
        if target_object is None:
            return
        if target_object.is_on_location_changed_callback_registered(self._on_target_location_changed):
            target_object.unregister_on_location_changed(self._on_target_location_changed)
        object_manager = services.object_manager()
        if object_manager is not None and object_manager.is_callback_registered(CallbackTypes.ON_OBJECT_REMOVE, self._on_target_removed):
            object_manager.unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_target_removed)

    def handle_privacy_violation(self, privacy):
        if not self.privacy_rules:
            return
        resolver = SingleObjectResolver(self.owner)
        loots = LootOperationList(resolver, self.privacy_rules.on_enter.loot_list)
        loots.apply_operations()
        if privacy not in self._privacy_violations:
            self._privacy_violations.add(privacy)

    def violates_privacy(self, privacy):
        if not self.privacy_rules:
            return False
        elif not privacy.vehicle_violates_privacy(self.owner):
            return False
        return True

    def _check_privacy(self, _, old_location, new_location):
        if not self.privacy_rules:
            return
        for privacy in services.privacy_service().privacy_instances:
            if not privacy.privacy_violators & PrivacyViolators.VEHICLES:
                pass
            else:
                new_violation = privacy not in self._privacy_violations
                violates_privacy = self.violates_privacy(privacy)
                if new_violation:
                    if violates_privacy:
                        self.handle_privacy_violation(privacy)
                        if not violates_privacy:
                            self._privacy_violations.discard(privacy)
                elif not violates_privacy:
                    self._privacy_violations.discard(privacy)

    def on_route_fail(self):
        self.owner.routing_component._on_routing_stage_event(RoutingStageEvent.OBJECT_ROUTE_FAIL, path=None)

    def _on_navmesh_updated(self):
        if self._running_behavior is not None and self._running_behavior.needs_replan():
            self.restart_running_behavior()

    def _on_target_location_changed(self, *_, **__):
        if self._running_behavior is not None:
            self.restart_running_behavior()

    def _on_target_removed(self, obj):
        if self._running_behavior is not None:
            target_object = self._running_behavior.get_target_object()
            if target_object is not None and obj.id == target_object.id:
                self.restart_running_behavior(deferred_start=True)

    def on_state_changed(self, state, old_value, new_value, from_init):
        if new_value is old_value:
            return
        if new_value not in self.routing_behavior_map:
            return
        self.stop_running_object_routing_behavior()
        routing_behavior_type = self.routing_behavior_map[new_value]
        if routing_behavior_type is UNSET:
            return
        routing_behavior = routing_behavior_type(self.owner)
        self._set_running_behavior(routing_behavior)
        self._cancel_idle_behavior()

    def on_location_changed(self, old_location):
        parent = self.owner.parent
        if parent is not None:
            self._previous_parent_ref = parent.ref()

    def component_reset(self, reset_reason):
        if self._running_behavior is not None:
            self._pending_running_behavior = type(self._running_behavior)
            self._running_behavior.trigger_hard_stop()
            self._set_running_behavior(None)
        services.get_master_controller().on_reset_sim(self.owner, reset_reason)

    def post_component_reset(self):
        if self._pending_running_behavior is not None:
            routing_behavior = self._pending_running_behavior(self.owner)
            self._set_running_behavior(routing_behavior)
            self._pending_running_behavior = None
            self._cancel_idle_behavior()

    def _cancel_idle_behavior(self):
        if self._idle_element is not None:
            self._idle_element.trigger_soft_stop()
            self._idle_element = None

    def _set_running_behavior(self, new_behavior):
        if new_behavior == self._running_behavior:
            return
        self._remove_target_callbacks()
        self._running_behavior = new_behavior
        if self.tracking_category and self.tracking_category is not ObjectRoutingBehaviorTrackingCategory.NONE:
            routing_service = services.get_object_routing_service()
            if routing_service:
                if new_behavior:
                    routing_service.on_active_routing_start(self.owner, self.tracking_category, new_behavior)
                else:
                    routing_service.on_active_routing_stop(self.owner, self.tracking_category)
        self._add_target_callbacks()

    @componentmethod
    def get_idle_element(self):
        self._idle_element = soft_sleep_forever()
        return (self._idle_element, self._cancel_idle_behavior)

    @componentmethod
    def get_next_work(self):
        if self._running_behavior is None or self.owner.has_work_locks:
            return WorkRequest()
        work_request = WorkRequest(work_element=self._running_behavior, required_sims=(self.owner,))
        return work_request

    @componentmethod
    def get_next_work_priority(self):
        return PriorityExtended.SubLow

    @componentmethod
    def on_requested_as_resource(self, other_work):
        if not any(resource.is_sim for resource in other_work.resources):
            return
        self.restart_running_behavior()

    @componentmethod_with_fallback(lambda : None)
    def get_running_behavior(self):
        return self._running_behavior

    def restart_running_behavior(self, deferred_start=False):
        routing_behavior_type = type(self._running_behavior) if self._running_behavior is not None else None
        self._running_behavior.restarting = True
        self._running_behavior.release_target()
        self.stop_running_object_routing_behavior()
        if deferred_start:
            self._deferred_behavior_type = routing_behavior_type
            self._deferred_alarm_handle = alarms.add_alarm_real_time(self, interval_in_real_seconds(1), self._deferred_start_behavior)
            return
        if routing_behavior_type is not None:
            routing_behavior = routing_behavior_type(self.owner)
            self._set_running_behavior(routing_behavior)

    def _deferred_start_behavior(self, *_):
        if self._deferred_behavior_type is not None:
            routing_behavior = self._deferred_behavior_type(self.owner)
            self._set_running_behavior(routing_behavior)
            alarms.cancel_alarm(self._deferred_alarm_handle)
            self._deferred_behavior_type = None
            self._deferred_alarm_handle = None

    @componentmethod_with_fallback(lambda : None)
    def stop_running_object_routing_behavior(self):
        if self._running_behavior is not None:
            self._remove_target_callbacks()
            self._running_behavior.trigger_soft_stop()
            self._set_running_behavior(None)

    @componentmethod
    def get_participant(self, participant_type=ParticipantType.Actor, **kwargs):
        participants = self.get_participants(participant_type=participant_type, **kwargs)
        if not participants:
            return
        if len(participants) > 1:
            raise ValueError('Too many participants returned for {}!'.format(participant_type))
        return next(iter(participants))

    @componentmethod
    def get_participants(self, participant_type, **kwargs):
        if participant_type is ParticipantType.Actor:
            obj = self._running_behavior._obj if self._running_behavior else None
            return (obj,)
        elif participant_type is ParticipantType.Object:
            target = self._running_behavior.get_target_object() if self._running_behavior else None
            return (target,)

    @componentmethod
    def get_object_routing_priority(self):
        if self._running_behavior is None:
            return ObjectRoutingPriority.NONE
        else:
            return self._running_behavior.object_routing_priority

    @componentmethod_with_fallback(lambda : None)
    def get_object_routing_behavior(self):
        return self._running_behavior

    @componentmethod_with_fallback(lambda : None)
    def get_social_transform_constraint(self):
        return self._social_transform_constraint

    @componentmethod_with_fallback(lambda *_: None)
    def set_social_transform_constraint(self, constraint):
        self._social_transform_constraint = constraint

    @componentmethod_with_fallback(lambda : None)
    def get_controlling_social_interaction_id(self):
        return self._controlling_social_interaction_id

    @componentmethod_with_fallback(lambda *_: None)
    def set_controlling_social_interaction_id(self, interaction_id):
        self._controlling_social_interaction_id = interaction_id

    @componentmethod_with_fallback(lambda *_: None)
    def get_mapped_object_routing_behavior(self, state_value):
        return self.routing_behavior_map.get(state_value)
