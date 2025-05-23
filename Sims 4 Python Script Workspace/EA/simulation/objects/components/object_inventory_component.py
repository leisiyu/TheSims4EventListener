from animation.posture_manifest import AnimationParticipantfrom event_testing.resolver import DoubleObjectResolver, SingleObjectResolverfrom event_testing.tests import CompoundTestListLoadingMixin, CompoundTestListfrom objects.components import componentmethod, typesfrom objects.components.get_put_component_mixin import GetPutComponentMixinfrom objects.components.inventory import InventoryComponentfrom objects.components.inventory_enums import InventoryTypefrom objects.components.inventory_item_trigger import ItemStateTriggerfrom objects.components.inventory_owner_tuning import InventoryTuningfrom objects.object_enums import ItemLocation, ResetReasonfrom objects.system import create_objectfrom objects.gallery_tuning import ContentSourcefrom postures.posture_specs import PostureSpecVariablefrom sims4.tuning.tunable import TunableList, TunableReference, TunableEnumEntry, Tunable, OptionalTunable, TunableTupleimport servicesimport sims4.resourcesfrom zone_tests import ZoneTestlogger = sims4.log.Logger('Inventory', default_owner='tingyul')
class TunableInventoryConditionalObjectTestSet(CompoundTestListLoadingMixin):
    DEFAULT_LIST = CompoundTestList()

    def __init__(self, description:str=None, **kwargs):
        super().__init__(description=description, tunable=TunableList(TunableInventoryConditionalObjectTestVariant(), description='A list of tests.  All of these must pass for the group to pass.'), **kwargs)

class TunableInventoryConditionalObjectTestVariant(sims4.tuning.tunable.TunableVariant):

    def __init__(self, description='A tunable test support for adding conditional objects on start', **kwargs):
        super().__init__(zone=ZoneTest.TunableFactory(), description=description, **kwargs)

class ObjectInventoryComponent(GetPutComponentMixin, InventoryComponent, component_name=types.INVENTORY_COMPONENT):
    DEFAULT_OBJECT_INVENTORY_AFFORDANCES = TunableList(TunableReference(description='\n            Affordances for all object inventories.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    FACTORY_TUNABLES = {'description': '\n            Generate an object inventory for this object\n            ', 'inventory_type': TunableEnumEntry(description='\n            Inventory Type must be set for the object type you add this for.\n            ', tunable_type=InventoryType, default=InventoryType.UNDEFINED, invalid_enums=(InventoryType.UNDEFINED, InventoryType.SIM)), 'visible': Tunable(description='\n            If this inventory is visible to player.', tunable_type=bool, default=True), 'starting_objects': TunableList(description='\n            Objects in this list automatically populate the inventory when its\n            owner is created. Currently, to keep the game object count down, an\n            object will not be added if the object inventory already has\n            another object of the same type.', tunable=TunableReference(manager=services.definition_manager(), description='Objects to populate inventory with.', pack_safe=True)), 'purchasable_objects': OptionalTunable(description='\n            If this list is enabled, an interaction to buy the purchasable\n            objects through a dialog picker will show on the inventory object.\n            \n            Example usage: a list of books for the bookshelf inventory.\n            ', tunable=TunableTuple(show_description=Tunable(description='\n                    Toggles whether the object description should show in the \n                    purchase picker.\n                    ', tunable_type=bool, default=False), objects=TunableList(description='\n                    A list of object definitions that can be purchased.\n                    ', tunable=TunableReference(manager=services.definition_manager(), description='')))), 'purge_inventory_state_triggers': TunableList(description='\n            Trigger the destruction of all inventory items if the inventory owner hits\n            any of the tuned state values.\n            \n            Only considers state-values present at and after zone-load finalize (ignores\n            default values that change during load based on state triggers, for example). \n            ', tunable=TunableReference(description='\n                The state value of the owner that triggers inventory item destruction.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))), 'score_contained_objects_for_autonomy': Tunable(description='\n            Whether or not to score for autonomy any objects contained in this object.', tunable_type=bool, default=True), 'item_state_triggers': TunableList(description="\n            The state triggers to modify inventory owner's state value based on\n            inventory items states.\n            ", tunable=ItemStateTrigger.TunableFactory()), 'allow_putdown_in_inventory': Tunable(description="\n            This inventory allows Sims to put objects away into it, such as books\n            or other carryables. Ex: mailbox has an inventory but we don't want\n            Sims putting away items in the inventory.", tunable_type=bool, default=True), 'test_set': OptionalTunable(description='\n            If enabled, the ability to pick up items from and put items in this\n            object is gated by this test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TestSetInstance',))), 'count_statistic': OptionalTunable(description='\n            A statistic whose value will be the number of objects in this\n            inventory. It will automatically be added to the object owning this\n            type of component.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Statistic',))), 'return_owned_objects': Tunable(description="\n            If enabled, inventory objects will return to their household\n            owner's inventory when this object is destroyed off lot. This is\n            because build buy can undo actions on lot and cause object id\n            collisions.\n            \n            We first consider the closest instanced Sims, and finally move to\n            the household inventory if we can't move to a Sim's inventory.\n            ", tunable_type=bool, default=False), '_use_top_item_tooltip': Tunable(description="\n            If checked, this inventory would use the top item's tooltip as its\n            own tooltip. \n            ", tunable_type=bool, default=False), 'conditional_objects': TunableList(description='\n            Given the test requirements, the inventory will be populated with \n            these objects when its owner is created. Currently, to keep the game \n            object count down, an object will not be added if the object inventory \n            already has another object of the same type.', tunable=TunableTuple(tests=TunableInventoryConditionalObjectTestSet(), objects=TunableList(tunable=TunableReference(manager=services.definition_manager(), description='Objects to populate inventory with.', pack_safe=True))))}

    def __init__(self, owner, inventory_type, visible, starting_objects, purchasable_objects, purge_inventory_state_triggers, score_contained_objects_for_autonomy, item_state_triggers, allow_putdown_in_inventory, test_set, count_statistic, return_owned_objects, _use_top_item_tooltip, conditional_objects, **kwargs):
        super().__init__(owner, **kwargs)
        self._inventory_type = inventory_type
        self.visible = visible
        self.starting_objects = starting_objects
        self.conditional_objects = conditional_objects
        self.purchasable_objects = purchasable_objects
        self.purge_inventory_state_triggers = purge_inventory_state_triggers
        self.score_contained_objects_for_autonomy = score_contained_objects_for_autonomy
        self.item_state_triggers = item_state_triggers
        self.allow_putdown_in_inventory = allow_putdown_in_inventory
        self.test_set = test_set
        self.count_statistic = count_statistic
        self.return_owned_objects = return_owned_objects
        self._use_top_item_tooltip = _use_top_item_tooltip

    @property
    def inventory_type(self):
        return self._inventory_type

    @property
    def default_item_location(self):
        return ItemLocation.OBJECT_INVENTORY

    @componentmethod
    def get_inventory_access_constraint(self, sim, is_put, carry_target, use_owner_as_target_for_resolver=False):
        if use_owner_as_target_for_resolver:

            def constraint_resolver(animation_participant, default=None):
                if animation_participant in (AnimationParticipant.SURFACE, PostureSpecVariable.SURFACE_TARGET, AnimationParticipant.TARGET, PostureSpecVariable.INTERACTION_TARGET):
                    return self.owner
                return default

        else:
            constraint_resolver = None
        return self._get_access_constraint(sim, is_put, carry_target, resolver=constraint_resolver)

    @componentmethod
    def get_inventory_access_animation(self, *args, **kwargs):
        return self._get_access_animation(*args, **kwargs)

    @property
    def should_score_contained_objects_for_autonomy(self):
        return self.score_contained_objects_for_autonomy

    @property
    def use_top_item_tooltip(self):
        return self._use_top_item_tooltip

    def _get_inventory_count_statistic(self):
        return self.count_statistic

    def on_add(self):
        for trigger in self.item_state_triggers:
            self.add_state_trigger(trigger(self))
        super().on_add()

    def on_reset_component_get_interdependent_reset_records(self, reset_reason, reset_records):
        if not services.current_zone().is_zone_shutting_down:
            lost_and_found = services.get_object_lost_and_found_service()
            zone = services.current_zone()
            clones_to_delete_by_zone = lost_and_found.clones_to_delete_by_zone.get(zone.id, set())
            clones_to_delete_by_street = lost_and_found.clones_to_delete_by_street.get(zone.open_street_id, set())
            is_owner_lost = self.owner.id in clones_to_delete_by_zone or self.owner.id in clones_to_delete_by_street
            if not is_owner_lost:
                household_manager = services.household_manager()
                objects_to_transfer = list(iter(self))
                for obj in objects_to_transfer:
                    if obj.id is 0:
                        logger.error('Trying to transfer an object {} with id 0 to the owner sim or household inventory', obj)
                    else:
                        household_id = obj.get_household_owner_id()
                        if household_id is not None:
                            household = household_manager.get(household_id)
                            if household is not None:
                                household.move_object_to_sim_or_household_inventory(obj)
        super().on_reset_component_get_interdependent_reset_records(reset_reason, reset_records)

    def on_post_bb_fixup(self):
        self._add_starting_objects()

    def _add_starting_objects(self):
        for definition in self.starting_objects:
            self._add_object(definition)
        self._add_conditional_objects()

    def _add_conditional_objects(self):
        if not self.conditional_objects:
            return
        resolver = SingleObjectResolver(self.owner)
        for entry in self.conditional_objects:
            if entry.tests.run_tests(resolver):
                for definition in entry.objects:
                    self._add_object(definition)

    def _add_object(self, definition):
        if self.has_item_with_definition(definition):
            return
        new_object = create_object(definition, loc_type=ItemLocation.OBJECT_INVENTORY)
        if new_object is None:
            logger.error('Failed to create object {}', definition)
            return
        else:
            new_object.set_household_owner_id(self.owner.get_household_owner_id())
            if not self.player_try_add_object(new_object):
                logger.error('Failed to add object {} to inventory {}', new_object, self)
                new_object.destroy(source=self.owner, cause='Failed to add starting object to inventory.')
                return

    def component_interactable_gen(self):
        yield self

    def component_super_affordances_gen(self, **kwargs):
        if self.visible:
            for affordance in self.DEFAULT_OBJECT_INVENTORY_AFFORDANCES:
                yield affordance

    def _can_access(self, sim):
        if self.test_set is not None:
            resolver = DoubleObjectResolver(sim, self.owner)
            result = self.test_set(resolver)
            if not result:
                return False
        return True

    @componentmethod
    def can_access_for_pickup(self, sim):
        if not self._can_access(sim):
            return False
        elif any(self.owner.state_value_active(value) for value in InventoryTuning.INVALID_ACCESS_STATES):
            return False
        return True

    @componentmethod
    def can_access_for_putdown(self, sim):
        if not self.allow_putdown_in_inventory:
            return False
        elif not self._can_access(sim):
            return False
        return True

    def _check_state_value_for_purge(self, state_value):
        return state_value in self.purge_inventory_state_triggers

    def _purge_inventory_from_state_change(self, new_value):
        if not self._check_state_value_for_purge(new_value):
            return
        current_zone = services.current_zone()
        if current_zone is None:
            return
        if not current_zone.zone_spin_up_service.is_finished:
            return
        self.purge_inventory()

    def on_state_changed(self, state, old_value, new_value, from_init):
        if self.purge_inventory_state_triggers and not from_init:
            self._purge_inventory_from_state_change(new_value)

    def _purge_inventory_from_load_finalize(self):
        owner_state_component = self.owner.state_component
        if owner_state_component is None:
            logger.error('Attempting to purge an inventory based on state-triggers but the owner ({}) has                          no state component. Purge fails.', self.owner)
            return
        for active_state_value in owner_state_component.values():
            if self._check_state_value_for_purge(active_state_value):
                self.purge_inventory()
                return

    def on_finalize_load(self):
        if self.purge_inventory_state_triggers:
            self._purge_inventory_from_load_finalize()
