from __future__ import annotationsfrom routing import Locationfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.tests import CompoundTestList
    from singletons import DefaultType
    from objects.game_object import GameObject
    from typing import *from _collections import defaultdictfrom weakref import WeakKeyDictionaryfrom autonomy.autonomy_modifier import TunableAutonomyModifierfrom event_testing.resolver import SingleObjectResolver, DoubleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.utils.tunable_provided_affordances import TunableProvidedAffordancesfrom objects.components import types, componentmethod, componentmethod_with_fallbackfrom objects.components.get_put_component_mixin import GetPutComponentMixinfrom objects.components.types import NativeComponent, STORED_SIM_INFO_COMPONENT, TOOLTIP_COMPONENTfrom objects.object_enums import ResetReasonfrom objects.placement.placement_helper import _PlacementStrategyLocation, _PlacementStrategyHouseholdInventoryfrom objects.slots import get_slot_type_set_from_key, DecorativeSlotTuning, RuntimeSlotfrom postures.stand import StandSuperInteractionfrom sims4 import hash_utilfrom sims4.tuning.tunable import TunableList, TunableReference, TunableSet, TunableTuple, Tunable, TunableMapping, TunableVariant, OptionalTunable, HasTunableSingletonFactory, AutoFactoryInit, TunableSingletonFactoryfrom singletons import EMPTY_SET, DEFAULTimport distributor.opsimport native.animationimport servicesimport sims4.callback_utilsimport sims4.loglogger = sims4.log.Logger('SlotComponent')_slot_types_cache = {}_deco_slot_hashes = {}
def purge_cache():
    _slot_types_cache.clear()
    _deco_slot_hashes.clear()
sims4.callback_utils.add_callbacks(sims4.callback_utils.CallbackEvent.TUNING_CODE_RELOAD, purge_cache)
class _PlacementStrategyHouseholdInventoryFromSlot(_PlacementStrategyHouseholdInventory):
    FACTORY_TUNABLES = {'fallback_placement_strategy': OptionalTunable(description='\n            Fallback placement strategy if unable to place in household\n            Inventory.\n            ', tunable=_PlacementStrategyLocation.TunableFactory())}

    def try_place_object(self, obj, resolver, **kwargs):
        if super().try_place_object(obj, resolver, **kwargs):
            return True
        if self.fallback_placement_strategy is None:
            return False
        return self.fallback_placement_strategy.try_place_object(obj, resolver, **kwargs)

class SlotComponentElement(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'autonomy_modifiers': TunableList(description='\n            Objects parented to this object will have these autonomy modifiers\n            applied to them.\n            ', tunable=TunableAutonomyModifier(locked_args={'relationship_multipliers': None})), 'return_owned_objects': Tunable(description="\n            If enabled, child objects will return to their owner's inventory\n            when this object is destroyed in the specified item location.\n            \n            We first consider the closest instanced Sims, and finally move to\n            the household inventory if we can't move to a Sim's inventory.\n            ", tunable_type=bool, default=False), 'slot_provided_affordances': TunableProvidedAffordances(description='\n            Affordances provided on objects slotted into the owner of this\n            component.\n            ', class_restrictions=('SuperInteraction',), locked_args={'allow_self': False, 'target': ParticipantType.Object, 'carry_target': ParticipantType.Invalid, 'is_linked': False}), 'state_values_tuning': TunableSet(description='\n            Objects parented to this object will have these state values \n            applied to them. The original value will be restored if the child \n            is removed.\n            ', tunable=TunableTuple(required_slot_types=TunableList(description='\n                    If any required slots are specified, the slot used for\n                    parenting must correspond to one of the slot types in \n                    this list for the state change to occur.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE), pack_safe=True)), state_to_set=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)))), 'on_destroy_behavior': TunableMapping(description='\n            Mapping of slot type to placement behavior to execute on children \n            slotted in to slots of that type when this object is destroyed.\n            \n            This takes precedence over return owned objects.\n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE), pack_safe=True), value_type=TunableTuple(loot=TunableList(description='\n                    Loot that will be applied to child when the parent is destroyed.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), placement=TunableVariant(description='\n                    Where the child will be placed when the parent is destroyed\n                    ', default='position', position=_PlacementStrategyLocation.TunableFactory(), household_inventory=_PlacementStrategyHouseholdInventoryFromSlot.TunableFactory()))), 'parent_state_values_tuning': TunableSet(description='\n            The object state to set to this object when a child object has been added to it. \n            Note: The object state will revert to its default state after the child object has been removed.\n            ', tunable=TunableTuple(required_slot_types=TunableList(description='\n                    If any required slots are specified, the slot used for\n                    parenting must correspond to one of the slot types in \n                    this list for the state change to occur.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE), pack_safe=True)), state_to_set=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)))), 'specific_slot_set': TunableReference(description='\n            Set of slots the object may be attached to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE_SET), allow_none=True), 'slot_content_states': OptionalTunable(description='\n            Set the state of the object when something has been slotted or the slot has been emptied\n            ', tunable=TunableTuple(empty_state=TunableReference(description='\n                    State to be applied when object is empty\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)), not_empty_state=TunableReference(description='\n                    State to be applied when object is not empty\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handles = None
        self.state_values = None
        self.parent_state_values = None
        self._slotted_objects = set()

    @property
    def num_slotted_objects(self):
        return len(self._slotted_objects)

    def register_slotted_object(self, child):
        self._slotted_objects.add(child.id)

    def unregister_slotted_object(self, child):
        self._slotted_objects.remove(child.id)
TunableSlotComponentElement = TunableSingletonFactory.create_auto_factory(SlotComponentElement)
class SlotComponent(GetPutComponentMixin, NativeComponent, component_name=types.SLOT_COMPONENT, key=787604481):
    FACTORY_TUNABLES = {'default_slot': TunableSlotComponentElement(description='\n            Default behaviour for all the slots in case there is no element\n            in specific_slots with the target slot_type\n            ', locked_args={'specific_slot_set': None}), 'specific_slots': TunableList(description="\n            List of behaviours with specific_slot defined. When a slot-dependant\n            method is called we will iterate through this list to check if there's\n            any element with the object slot type\n            ", tunable=TunableSlotComponentElement()), 'send_telemetry': Tunable(description='\n            If true will send telemetry event when object has been slotted\n            ', tunable_type=bool, default=False), 'update_children_tooltip': Tunable(description='\n            If true will update children tooltip component when they are added,\n            removed or the state of this object has changed\n            ', tunable_type=bool, default=False), 'reslot_children_on_model_change': Tunable(description='\n            If true, will attempt to re-slot children when the model of this object has changed.\n            ', tunable_type=bool, default=False), 'overwrite_sim_info_of_parent': Tunable(description='\n            If enabled on a child object, and Accept Child Sim Info Overwrites on the parent object is true,\n            the parent object will have its StoredSimInfoComponent updated to that of the child object when\n            the child is slotted.\n            ', tunable_type=bool, default=False), 'accept_child_sim_info_overwrites': Tunable(description='\n            Must be true on the parent object for Overwrite Sim Info Of Parent to succeed when the child\n            object is slotted.\n            ', tunable_type=bool, default=False), 'allow_slotting_tests': TunableTestSet(description='\n            If specified, at least one of these tests must pass in order for\n            objects to be able to be slotted onto this object.\n            '), 'post_load_affordance_update': Tunable(description='\n            Should this slot component update its slot affordances after load \n            (if you think you need this, check with GPE).\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, default_slot:'Union[SlotComponentElement, DefaultType]'=DEFAULT, specific_slots:'Union[List[SlotComponentElement], DefaultType]'=DEFAULT, send_telemetry:'Union[bool, DefaultType]'=DEFAULT, update_children_tooltip:'Union[bool, DefaultType]'=DEFAULT, reslot_children_on_model_change:'Union[bool, DefaultType]'=DEFAULT, overwrite_sim_info_of_parent:'Union[bool, DefaultType]'=DEFAULT, accept_child_sim_info_overwrites:'Union[bool, DefaultType]'=DEFAULT, allow_slotting_tests:'Union[CompoundTestList, DefaultType]'=DEFAULT, post_load_affordance_update:'Union[bool, DefaultType]'=DEFAULT, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._disabled_slot_hashes = None
        self._containment_slot_info_cache = None
        self._slots_dic = {}
        self.default_slot = default_slot if default_slot is not DEFAULT else None
        self._send_telemetry = send_telemetry if send_telemetry is not DEFAULT else False
        self._update_children_tooltip = update_children_tooltip if update_children_tooltip is not DEFAULT else False
        self._reslot_children_on_model_change = reslot_children_on_model_change if reslot_children_on_model_change is not DEFAULT else False
        self._overwrite_sim_info_of_parent = overwrite_sim_info_of_parent if overwrite_sim_info_of_parent is not DEFAULT else False
        self._accept_child_sim_info_overwrites = accept_child_sim_info_overwrites if accept_child_sim_info_overwrites is not DEFAULT else False
        self._allow_slotting_tests = allow_slotting_tests if allow_slotting_tests is not DEFAULT else None
        self._post_load_affordance_update = post_load_affordance_update if post_load_affordance_update is not DEFAULT else False
        if specific_slots is not None:
            for slot in specific_slots:
                for slot_type in slot.specific_slot_set.slot_types:
                    self._slots_dic[slot_type] = slot
        self._should_add_state_changed = False
        self._state_changed_changed_callback_added = False
        if specific_slots is not DEFAULT and self._update_children_tooltip:
            if self.owner.state_component is not None:
                self.owner.state_component.add_state_changed_callback(self._owner_state_change)
                self._state_changed_changed_callback_added = True
            else:
                self._should_add_state_changed = True
        if self._reslot_children_on_model_change:
            self.owner.register_for_on_model_changed_callback(self._owner_model_change)

    def _get_slot_element(self, parent_slots):
        if parent_slots:
            for parent_slot_type in parent_slots:
                if parent_slot_type in self._slots_dic:
                    return self._slots_dic[parent_slot_type]
        return self.default_slot

    def component_reset(self, reset_reason):
        if reset_reason == ResetReason.BEING_DESTROYED:
            zone = services.current_zone()
            if zone.is_zone_shutting_down:
                return
            parent_resolver = SingleObjectResolver(self.owner)
            is_on_active_lot = self.owner.is_on_active_lot()
            if self.default_slot is not None:
                list_slots = []
                if self._slots_dic:
                    list_slots.extend(self._slots_dic.values())
                for slot_element in list_slots:
                    if slot_element.on_destroy_behavior:
                        for child in list(self.owner.children_recursive_gen()):
                            for (slot_hash, slot_types) in self.get_containment_slot_infos():
                                if slot_hash != child.bone_name_hash:
                                    pass
                                else:
                                    for slot_type in slot_types:
                                        behavior = slot_element.on_destroy_behavior.get(slot_type)
                                        if behavior is not None:
                                            break
                                    transform = child.transform
                                    surface = child.routing_surface
                                    child.set_parent(None, transform=transform, routing_surface=surface)
                                    child_resolver = SingleObjectResolver(child)
                                    for loot_action in behavior.loot:
                                        loot_action.apply_to_resolver(child_resolver)
                                    if not behavior.placement.try_place_object(child, parent_resolver):
                                        child.set_parent(self.owner, transform=transform, routing_surface=surface)
                                    break
                    if slot_element.return_owned_objects and not is_on_active_lot:
                        household_manager = services.household_manager()
                        for child in list(self.owner.children_recursive_gen()):
                            household_id = child.get_household_owner_id()
                            if household_id is not None:
                                household = household_manager.get(household_id)
                                if household is not None:
                                    if zone.have_sims_spawned():
                                        household.move_object_to_sim_or_household_inventory(child, sort_by_distance=True)
                                    else:
                                        zone.add_item_to_add_to_inventory(household_id, child)
                                        transform = child.transform
                                        surface = child.routing_surface
                                        child.set_parent(None, transform=transform, routing_surface=surface)
            if self._state_changed_changed_callback_added:
                self.owner.state_component.remove_state_changed_callback(self._owner_state_change)
            if self._reslot_children_on_model_change:
                self.owner.unregister_for_on_model_changed_callback(self._owner_model_change)

    def _get_parent_slot(self, slot_hash):
        slots = self.get_containment_slot_infos()
        for slot in slots:
            if slot[0] == slot_hash:
                return slot[1]

    def update_flags(self, child, location):
        parent_slot = self._get_parent_slot(location.slot_hash) if location is not None else child.parent_slot if child.parent_slot is not None else None
        slot_element = self._get_slot_element(parent_slot)
        if slot_element is not None and slot_element.slot_provided_affordances:
            flags = set()
            for provided_affordance_data in slot_element.slot_provided_affordances:
                if not provided_affordance_data.object_filter.is_object_valid(child):
                    pass
                else:
                    flags |= provided_affordance_data.affordance.commodity_flags
            if flags and not child.is_prop:
                child.add_dynamic_commodity_flags(self, flags)

    def on_child_added(self, child, location):
        parent_slot = self._get_parent_slot(location.slot_hash) if location is not None else child.parent_slot if child.parent_slot is not None else None
        slot_element = self._get_slot_element(parent_slot)
        if self.owner.state_component is not None:
            self.owner.state_component.add_state_changed_callback(self._owner_state_change)
            self._should_add_state_changed = False
            self._state_changed_changed_callback_added = True
        if self._should_add_state_changed and slot_element is not None:
            if child.statistic_component is not None:
                if slot_element.handles is None:
                    slot_element.handles = WeakKeyDictionary()
                if child not in slot_element.handles:
                    child.add_statistic_component()
                    handles = []
                    for modifier in slot_element.autonomy_modifiers:
                        handles.append(child.add_statistic_modifier(modifier))
                    slot_element.handles[child] = handles
            if slot_element.autonomy_modifiers and slot_element.state_values_tuning:
                slot_element.state_values = self._update_state_value_tuning_on_add(child, slot_element.state_values, slot_element.state_values_tuning, location)
            if slot_element.parent_state_values_tuning is not None:
                slot_element.parent_state_values = self._update_state_value_tuning_on_add(child, slot_element.parent_state_values, slot_element.parent_state_values_tuning, location, True)
            if slot_element.slot_content_states:
                self._register_slotted_object(slot_element, child)
            if slot_element.slot_provided_affordances:
                flags = set()
                for provided_affordance_data in slot_element.slot_provided_affordances:
                    if not provided_affordance_data.object_filter.is_object_valid(child):
                        pass
                    else:
                        flags |= provided_affordance_data.affordance.commodity_flags
                if flags and not child.is_prop:
                    child.add_dynamic_commodity_flags(self, flags)
        child.on_placed_in_slot(self.owner)
        if child.display_component is not None:
            child.display_component.slotted_to_object(self.owner)
        if child.state_component and child.state_component.overlapping_slot_states:
            self.owner.register_for_on_children_changed_callback(child.state_component.handle_overlapping_slots)
            child.state_component.handle_overlapping_slots(child, location)
        if self._update_children_tooltip:
            self._update_child_tooltip(child)
            child.register_on_location_changed(self.handle_child_location_changed)
        if child.slot_component is not None:
            child_should_transfer = child.slot_component.get_should_overwrite_sim_info_of_parent()
            parent_should_accept = self._accept_child_sim_info_overwrites
            if child_should_transfer and parent_should_accept:
                child_sim_info_component = child.get_component(STORED_SIM_INFO_COMPONENT)
                if child_sim_info_component is not None and child_sim_info_component.has_stored_data():
                    if self.owner.has_component(STORED_SIM_INFO_COMPONENT):
                        self.owner.remove_component(STORED_SIM_INFO_COMPONENT)
                    child_sim_id = child_sim_info_component.get_stored_sim_id()
                    self.owner.add_dynamic_component(STORED_SIM_INFO_COMPONENT, sim_id=child_sim_id)
                    for child in self.owner.children:
                        if child.canvas_component is not None and hasattr(child.canvas_component, 'on_parent_change'):
                            child.canvas_component.on_parent_change(self.owner)
                else:
                    parent_sim_info_component = self.owner.get_component(STORED_SIM_INFO_COMPONENT)
                    if parent_sim_info_component is not None and parent_sim_info_component.has_stored_data():
                        parent_sim_info_component.clear_all_stored_data()

    def on_child_removed(self, child, new_location:'Location', new_parent=None):
        slot_element = None
        if child.parent_slot is not None:
            slot_element = self._get_slot_element(child.parent_slot.slot_types)
        if slot_element is not None:
            if child in slot_element.handles:
                child.add_statistic_component()
                handles = slot_element.handles.pop(child)
                for handle in handles:
                    child.remove_statistic_modifier(handle)
            if child in slot_element.state_values:
                state_values = slot_element.state_values.pop(child)
                for state_value in state_values:
                    child.set_state(state_value.state, state_value)
            if child in slot_element.parent_state_values:
                state_values = slot_element.parent_state_values.pop(child)
                for state_value in state_values:
                    self.owner.set_state(state_value.state, state_value)
            if slot_element.handles and slot_element.state_values and slot_element.parent_state_values is not None and slot_element.slot_content_states:
                self._unregister_slotted_object(slot_element, child)
        if not child.is_prop:
            child.remove_dynamic_commodity_flags(self)
        child.on_removed_from_slot(self.owner)
        if child.display_component is not None:
            child.display_component.unslotted_from_object(self.owner)
        if child.state_component and child.state_component.overlapping_slot_states:
            self.owner.unregister_for_on_children_changed_callback(child.state_component.handle_overlapping_slots)
        if child.slot_component is not None:
            child_transferred = child.slot_component.get_should_overwrite_sim_info_of_parent()
            parent_accepted = self._accept_child_sim_info_overwrites
            if child_transferred and parent_accepted:
                parent_sim_info_component = self.owner.get_component(STORED_SIM_INFO_COMPONENT)
                if parent_sim_info_component is not None and parent_sim_info_component.has_stored_data():
                    parent_sim_info_component.clear_all_stored_data()

    def slotting_tests_pass(self, child:'GameObject') -> 'bool':
        if not self._allow_slotting_tests:
            return True
        resolver = DoubleObjectResolver(child, self.owner)
        return self._allow_slotting_tests.run_tests(resolver)

    def _update_child_tooltip(self, child):
        if child.has_component(TOOLTIP_COMPONENT):
            child.get_component(TOOLTIP_COMPONENT).update_object_tooltip()

    def _owner_state_change(self, owner, state, old_value, new_value):
        for child in list(self.owner.children_recursive_gen()):
            self._update_child_tooltip(child)

    def _owner_model_change(self, owner:'GameObject', old_model_key:'sims4.resources.Key', new_model_key:'sims4.resources.Key') -> 'None':
        for child in list(self.owner.get_all_children_gen()):
            parent_slot_hash = child.parent_slot.slot_name_or_hash
            self.slot_object(parent_slot=parent_slot_hash, slotting_object=child, target=self.owner, suppress_telemetry=True)

    def handle_child_location_changed(self, obj, *args, **kwargs):
        if obj.parent != self.owner:
            self._update_child_tooltip(obj)
            obj.unregister_on_location_changed(self.handle_child_location_changed)

    def _register_slotted_object(self, slot_element, child):
        old_value = slot_element.num_slotted_objects
        slot_element.register_slotted_object(child)
        new_value = slot_element.num_slotted_objects
        state_value = slot_element.slot_content_states.not_empty_state
        if old_value == 0 and new_value > 0:
            self.owner.set_state(state_value.state, state_value)

    def _unregister_slotted_object(self, slot_element, child):
        old_value = slot_element.num_slotted_objects
        slot_element.unregister_slotted_object(child)
        new_value = slot_element.num_slotted_objects
        state_value = slot_element.slot_content_states.empty_state
        if new_value == 0 and old_value > 0:
            self.owner.set_state(state_value.state, state_value)

    @distributor.fields.ComponentField(op=distributor.ops.SetDisabledSlots, default=None)
    def disabled_slot_hashes(self):
        return self._disabled_slot_hashes

    resend_disabled_slot_hashes = disabled_slot_hashes.get_resend()

    @componentmethod_with_fallback(lambda : None)
    def disable_slots(self, slot_hashes):
        if self._disabled_slot_hashes is None:
            self._disabled_slot_hashes = set()
        self._disabled_slot_hashes |= slot_hashes
        self.resend_disabled_slot_hashes()

    @componentmethod_with_fallback(lambda : None)
    def enable_slots(self, slot_hashes):
        if self._disabled_slot_hashes is None:
            return
        self._disabled_slot_hashes -= slot_hashes
        self.resend_disabled_slot_hashes()
        if not self._disabled_slot_hashes:
            self._disabled_slot_hashes = None

    @componentmethod_with_fallback(lambda : None)
    def disable_slot(self, slot_hash):
        if self._disabled_slot_hashes is None:
            self._disabled_slot_hashes = set()
        self._disabled_slot_hashes.add(slot_hash)
        self.resend_disabled_slot_hashes()

    @componentmethod_with_fallback(lambda : None)
    def enable_slot(self, slot_hash):
        if self._disabled_slot_hashes is None:
            return
        if slot_hash in self._disabled_slot_hashes:
            self._disabled_slot_hashes.discard(slot_hash)
            self.resend_disabled_slot_hashes()
        if not self._disabled_slot_hashes:
            self._disabled_slot_hashes = None

    @componentmethod_with_fallback(lambda : EMPTY_SET)
    def get_disabled_slot_hashes(self):
        if self._disabled_slot_hashes:
            return self._disabled_slot_hashes
        return set()

    @componentmethod
    def get_surface_access_constraint(self, sim, is_put, carry_target):
        return self._get_access_constraint(sim, is_put, carry_target)

    @componentmethod
    def get_surface_access_animation(self, put):
        return self._get_access_animation(put)

    @componentmethod_with_fallback(lambda : False)
    def get_should_overwrite_sim_info_of_parent(self) -> 'bool':
        return self._overwrite_sim_info_of_parent

    @staticmethod
    def to_slot_hash(slot_name_or_hash):
        if slot_name_or_hash is None:
            return 0
        if isinstance(slot_name_or_hash, int):
            return slot_name_or_hash
        else:
            return hash_util.hash32(slot_name_or_hash)

    @componentmethod
    def get_slot_info(self, slot_name_or_hash=None, object_slots=None):
        slot_type_containment = sims4.ObjectSlots.SLOT_CONTAINMENT
        owner = self.owner
        if object_slots is None:
            object_slots = owner.slots_resource
        slot_name_hash = SlotComponent.to_slot_hash(slot_name_or_hash)
        if self.has_slot(slot_name_hash, object_slots):
            slot_transform = object_slots.get_slot_transform_by_hash(slot_type_containment, slot_name_hash)
            return (slot_name_hash, slot_transform)
        raise KeyError('Slot {} not found on owner object: {}'.format(slot_name_or_hash, owner))

    @componentmethod
    def has_slot(self, slot_name_or_hash, object_slots=None):
        owner = self.owner
        if object_slots is None:
            object_slots = owner.slots_resource
        return object_slots.has_slot(sims4.ObjectSlots.SLOT_CONTAINMENT, SlotComponent.to_slot_hash(slot_name_or_hash))

    @componentmethod
    def get_deco_slot_hashes(self, deco_slot_hash_index):
        if deco_slot_hash_index not in _deco_slot_hashes:
            self.get_containment_slot_infos()
        if deco_slot_hash_index in _deco_slot_hashes:
            return _deco_slot_hashes[deco_slot_hash_index]
        return frozenset()

    def get_containment_slot_infos(self):
        object_slots = self.owner.slots_resource
        if object_slots is None:
            logger.warn('Attempting to get slots from object {} with no slot', self.owner)
            return []
        if self._containment_slot_info_cache is None:
            self._containment_slot_info_cache = self.get_containment_slot_infos_static(object_slots, self.owner.rig, self.owner)
        return self._containment_slot_info_cache

    @staticmethod
    def get_containment_slot_infos_static(object_slots, rig, owner):
        subroot_index = owner.subroot_index if owner is not None and owner.is_part else None
        if (rig, subroot_index) in _deco_slot_hashes:
            deco_slot_hashes = None
        else:
            deco_slot_hashes = []
        containment_slot_infos = []
        for slot_index in range(object_slots.get_slot_count(sims4.ObjectSlots.SLOT_CONTAINMENT)):
            slot_hash = object_slots.get_slot_name_hash(sims4.ObjectSlots.SLOT_CONTAINMENT, slot_index)
            key = (rig, slot_index)
            if key in _slot_types_cache:
                slot_types = _slot_types_cache[key]
                if slot_types:
                    containment_slot_infos.append((slot_hash, slot_types))
                    slot_type_set_key = object_slots.get_containment_slot_type_set(slot_index)
                    deco_size = object_slots.get_containment_slot_deco_size(slot_index)
                    slot_types = set()
                    slot_type_set = get_slot_type_set_from_key(slot_type_set_key)
                    if slot_type_set is not None:
                        slot_types.update(slot_type_set.slot_types)
                    slot_types.update(DecorativeSlotTuning.get_slot_types_for_slot(deco_size))
                    if slot_types:
                        try:
                            native.animation.get_joint_transform_from_rig(rig, slot_hash)
                        except KeyError:
                            slot_name = sims4.hash_util.unhash_with_fallback(slot_hash)
                            rig_name = None
                            rig_name = rig_name or str(rig)
                            logger.error("Containment slot {} doesn't have matching bone in {}'s rig ({}). This slot cannot be used by gameplay systems.", slot_name, owner, rig_name)
                            slot_types = ()
                        except ValueError:
                            rig_name = None
                            rig_name = rig_name or str(rig)
                            logger.error('RigName: {} with rig key: {} does not exist for object {}.  ', rig_name, rig, owner)
                            slot_types = ()
                    if deco_slot_hashes is not None and DecorativeSlotTuning.slot_types_are_all_decorative(slot_types):
                        deco_slot_hashes.append(slot_hash)
                    slot_types = frozenset(slot_types)
                    _slot_types_cache[key] = slot_types
                    if slot_types:
                        containment_slot_infos.append((slot_hash, slot_types))
            else:
                slot_type_set_key = object_slots.get_containment_slot_type_set(slot_index)
                deco_size = object_slots.get_containment_slot_deco_size(slot_index)
                slot_types = set()
                slot_type_set = get_slot_type_set_from_key(slot_type_set_key)
                if slot_type_set is not None:
                    slot_types.update(slot_type_set.slot_types)
                slot_types.update(DecorativeSlotTuning.get_slot_types_for_slot(deco_size))
                if slot_types:
                    try:
                        native.animation.get_joint_transform_from_rig(rig, slot_hash)
                    except KeyError:
                        slot_name = sims4.hash_util.unhash_with_fallback(slot_hash)
                        rig_name = None
                        rig_name = rig_name or str(rig)
                        logger.error("Containment slot {} doesn't have matching bone in {}'s rig ({}). This slot cannot be used by gameplay systems.", slot_name, owner, rig_name)
                        slot_types = ()
                    except ValueError:
                        rig_name = None
                        rig_name = rig_name or str(rig)
                        logger.error('RigName: {} with rig key: {} does not exist for object {}.  ', rig_name, rig, owner)
                        slot_types = ()
                if deco_slot_hashes is not None and DecorativeSlotTuning.slot_types_are_all_decorative(slot_types):
                    deco_slot_hashes.append(slot_hash)
                slot_types = frozenset(slot_types)
                _slot_types_cache[key] = slot_types
                if slot_types:
                    containment_slot_infos.append((slot_hash, slot_types))
        if deco_slot_hashes:
            if owner is not None and owner.parts:
                part_deco_slot_lists = defaultdict(list)
                part_owner = owner.part_owner if owner.is_part else owner
                stand_body_posture_type = StandSuperInteraction.STAND_POSTURE_TYPE
                parts = tuple(p for p in part_owner.parts if p.supports_posture_type(stand_body_posture_type))
                if parts:
                    for deco_slot_hash in deco_slot_hashes:
                        closest_part = None
                        joint_transform = native.animation.get_joint_transform_from_rig(rig, deco_slot_hash)
                        location = sims4.math.Location(joint_transform, None, parent=owner, slot_hash=deco_slot_hash)
                        slot_position = location.transform.translation
                        closest_part = min(parts, key=lambda p: (p.get_joint_transform().translation - slot_position).magnitude_2d_squared())
                        deco_list = part_deco_slot_lists[closest_part]
                        deco_list.append(deco_slot_hash)
                        part_deco_slot_lists[closest_part] = deco_list
                else:
                    logger.error('Object {} has deco slots but none of its parts supports stand.', part_owner)
                _deco_slot_hashes[(rig, None)] = frozenset()
                for (part, deco_slot_list) in part_deco_slot_lists.items():
                    _deco_slot_hashes[(rig, (part.subroot_index, part.part_definition))] = frozenset(deco_slot_list)
            else:
                _deco_slot_hashes[(rig, None)] = frozenset(deco_slot_hashes)
        return containment_slot_infos

    @componentmethod_with_fallback(lambda part=None: EMPTY_SET)
    def get_provided_slot_types(self, part=None):
        result = set()
        for (_, slot_types) in (part or self).get_containment_slot_infos():
            result.update(slot_types)
        return result

    @componentmethod_with_fallback(lambda slot_types=None, bone_name_hash=None, owner_only=False: iter(()))
    def get_runtime_slots_gen(self, slot_types=None, bone_name_hash=None, owner_only=False):
        owner = self.owner
        parts = owner.parts
        for (slot_hash, slot_slot_types) in self.get_containment_slot_infos():
            if not slot_types is not None or not slot_types.intersection(slot_slot_types):
                pass
            elif not bone_name_hash is not None or slot_hash != bone_name_hash:
                pass
            else:
                if not parts:
                    yield RuntimeSlot(owner, slot_hash, slot_slot_types, self._send_telemetry)
                elif owner_only:
                    pass
                else:
                    for p in parts:
                        if p.has_slot(slot_hash):
                            yield RuntimeSlot(p, slot_hash, slot_slot_types, self._send_telemetry)
                            break
                    yield RuntimeSlot(owner, slot_hash, slot_slot_types, self._send_telemetry)
                for p in parts:
                    if p.has_slot(slot_hash):
                        yield RuntimeSlot(p, slot_hash, slot_slot_types, self._send_telemetry)
                        break
                yield RuntimeSlot(owner, slot_hash, slot_slot_types, self._send_telemetry)

    @componentmethod_with_fallback(lambda parent_slot=None, slotting_object=None, target=None, object_to_ignore=None, suppress_telemetry=False: False)
    def slot_object(self, parent_slot:'Optional[Union[str, int]]'=None, slotting_object:'Optional[GameObject]'=None, target:'Optional[GameObject]'=None, objects_to_ignore:'List[GameObject]'=None, suppress_telemetry:'bool'=False) -> 'bool':
        if target is None:
            target = self.owner
        if isinstance(parent_slot, str):
            send_telemetry = False if suppress_telemetry else self._send_telemetry
            runtime_slot = RuntimeSlot(self.owner, sims4.hash_util.hash32(parent_slot), EMPTY_SET, send_telemetry)
            if runtime_slot is None:
                logger.warn('The target object {} does not have a slot {}', self.owner, parent_slot, owner='nbaker')
                return False
            if runtime_slot.is_valid_for_placement(obj=slotting_object, objects_to_ignore=objects_to_ignore):
                runtime_slot.add_child(slotting_object)
                return True
            logger.warn("The target object {} slot {} isn't valid for placement", self.owner, parent_slot, owner='nbaker')
        if parent_slot is not None:
            for runtime_slot in target.get_runtime_slots_gen(slot_types={parent_slot}, bone_name_hash=None):
                if runtime_slot.is_valid_for_placement(obj=slotting_object, objects_to_ignore=objects_to_ignore):
                    runtime_slot.add_child(slotting_object)
                    return True
            logger.warn('The created object {} cannot be placed in the slot {} on target object or part {}', slotting_object, parent_slot, target, owner='nbaker')
            return False

    @componentmethod_with_fallback(lambda *_, **__: iter(()))
    def child_provided_aops_gen(self, target, context, **kwargs):
        slot_element = self._get_slot_element(target.parent_slot.slot_types)
        if slot_element.slot_provided_affordances:
            for provided_affordance_data in slot_element.slot_provided_affordances:
                if not provided_affordance_data.object_filter.is_object_valid(target):
                    pass
                else:
                    yield from provided_affordance_data.affordance.potential_interactions(target, context, **kwargs)

    def validate_definition(self):
        if self.owner.parts:
            invalid_runtime_slots = []
            for runtime_slot in self.get_runtime_slots_gen(owner_only=True):
                surface_slot_types = ', '.join(sorted(t.__name__ for t in runtime_slot.slot_types if t.implies_owner_object_is_surface))
                if surface_slot_types:
                    invalid_runtime_slots.append('{} ({})'.format(runtime_slot.slot_name_or_hash, surface_slot_types))
            if invalid_runtime_slots:
                part_tuning = []
                for part in sorted(self.owner.parts, key=lambda p: -1 if p.is_base_part else p.subroot_index):
                    part_name = 'Base Part' if part.is_base_part else 'Part {}'.format(part.subroot_index)
                    part_definition = part.part_definition
                    part_tuning.append('        {:<10} {}'.format(part_name + ':', part_definition.__name__))
                    if part_definition.subroot is not None:
                        part_tuning.append('          {}'.format(part_definition.subroot.__name__))
                        for bone_name in part_definition.subroot.bone_names:
                            part_tuning.append('            {}'.format(bone_name))
                part_tuning = '\n'.join(part_tuning)
                invalid_runtime_slots.sort()
                invalid_runtime_slots = '\n'.join('        ' + i for i in invalid_runtime_slots)
                error_message = '\n    This multi-part object has some surface slots that don\'t belong to any of\n    its parts. (Surface slots are slots that have a Slot Type Set or Deco Size\n    configured in Medator.) There are several possible causes of this error:\n    \n      * The slot isn\'t actually supposed to be a containment slot, and the slot\n        type set or deco size needs to be removed in Medator.\n    \n      * If there are decorative slots that aren\'t part of a subroot, the object\n        needs a "base part" -- a part with no subroot index to own the deco \n        slots. This needs to be added to the object\'s part tuning.\n      \n      * If these slots are normally part of a subroot, there may be a part\n        missing from the object\'s tuning, or one or more of the part types might\n        be wrong. This might mean the object tuning and catalog product don\'t\n        match, possibly because the person who assigned object tuning to the\n        catalog products thought two similar models could share exactly the same\n        tuning but they don\'t use the same rig.\n        \n      * There may be some bone names missing from one or more of the subroots\'\n        tuning files.\n        \n    Here are the names of the orphan slots (and the slot types tuned on them):\n{}\n\n    Here is the current part tuning for {}:\n{}'.format(invalid_runtime_slots, type(self.owner).__name__, part_tuning)
                raise ValueError(error_message)

    def _update_state_value_tuning_on_add(self, child, state_values_dict, state_values_tuning, location, is_parent=False):
        if state_values_dict is None:
            state_values_dict = WeakKeyDictionary()
        if child not in state_values_dict:
            state_values = []
            for state_value_tuning in state_values_tuning:
                required_slots = set(state_value_tuning.required_slot_types)
                if required_slots and not any(location.slot_hash == slot_hash and required_slots & slot_types for (slot_hash, slot_types) in self.get_containment_slot_infos()):
                    pass
                else:
                    state_value = state_value_tuning.state_to_set
                    state = state_value.state
                    if is_parent:
                        self._check_and_set_state(self.owner, state, state_value, state_values)
                    else:
                        self._check_and_set_state(child, state, state_value, state_values)
            state_values_dict[child] = state_values
        return state_values_dict

    def on_finalize_load(self):
        if self.default_slot is not None:
            list_slots = [self.default_slot]
            if self._slots_dic:
                list_slots.extend(self._slots_dic.values())
            for slot_element in list_slots:
                if slot_element.slot_provided_affordances:
                    flags = set()
                    for provided_affordance_data in slot_element.slot_provided_affordances:
                        flags |= provided_affordance_data.affordance.commodity_flags
                    if flags and slot_element.handles is not None:
                        for child in slot_element.handles:
                            if not child.is_prop:
                                child.add_dynamic_commodity_flags(self, flags)

    def _check_and_set_state(self, obj, state, state_value, state_values):
        if not obj.has_state(state):
            return
        current_value = obj.get_state(state)
        if current_value != state_value:
            state_values.append(current_value)
            obj.set_state(state, state_value)
