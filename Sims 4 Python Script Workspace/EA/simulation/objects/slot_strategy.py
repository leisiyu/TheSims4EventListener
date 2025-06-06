from build_buy import _buildbuy, remove_object_from_household_inventoryfrom objects.gallery_tuning import ContentSourcefrom random import shufflefrom event_testing.resolver import InteractionResolver, DoubleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSinglefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, TunableReference, OptionalTunable, TunableVariant, TunableList, Tunable, TunableRangeimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('SlotStrategy', default_owner='amwu')
class SlotStrategyVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, slot_type_strategy=SlotStrategyTargetSlotType.TunableFactory(), auto_slotting=SlotStrategyAutoSlot.TunableFactory(), default='slot_type_strategy', **kwargs)

class SelectObjectVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, object_participant=SelectSourceParticipant.TunableFactory(), inventory_objects=SelectInventoryObjects.TunableFactory(), default='object_participant', **kwargs)

class SelectObjectBase:

    def __init__(self, resolver, slot_target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resolver = resolver
        self.slot_target = slot_target

    def get_objects(self, *args, **kwargs):
        raise NotImplementedError

class SelectSourceParticipant(HasTunableFactory, AutoFactoryInit, SelectObjectBase):
    FACTORY_TUNABLES = {'transfer_participant': TunableEnumEntry(description='\n            A participant to be slotted.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_objects(self, *args, **kwargs):
        return {participant for participant in self.resolver.get_participants(self.transfer_participant)}

class SelectInventoryObjects(HasTunableFactory, AutoFactoryInit, SelectObjectBase):
    FACTORY_TUNABLES = {'inventory_participant': TunableEnumEntry(description='\n            The participant with the inventory we want to pull objects from.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'object_tests': TunableTestSet(description='\n            Tests whether or not an object in the inventory should be\n            transferred to a target slot or not.\n            \n            If this is being tuned in an interaction, the object in question\n            will be the Picked Item participant. This is so that we can keep\n            the resolver in case we want to test the actor or target as well.\n            \n            In other cases, the participant will be Actor, and the slot target\n            will be Object.\n            ')}

    def get_objects(self, *args, preferred_slots=None, **kwargs):
        inventory_owner = self.resolver.get_participant(self.inventory_participant)
        if inventory_owner is None:
            logger.error('Inventory Participant {} is None for slot object selection {}', self.inventory_participant, self.resolver)
            return set()
        is_interaction_resolver = isinstance(self.resolver, InteractionResolver)
        if is_interaction_resolver:
            interaction_params = self.resolver.interaction_parameters.copy()
            inventory_owner = self.resolver.interaction.get_participant(self.inventory_participant)
        valid_objects = set()
        if inventory_owner.inventory_component is None:
            logger.error('Inventory Component for Participant {} is None for slot object selection {}', self.inventory_participant, self.resolver)
            return set()
        for obj in inventory_owner.inventory_component:
            if is_interaction_resolver:
                interaction_parameters = {'picked_item_ids': [obj.id]}
                self.resolver.interaction_parameters.update(interaction_parameters)
                resolver = self.resolver
            else:
                resolver = DoubleObjectResolver(obj, self.slot_target)
            if not self.object_tests.run_tests(resolver):
                pass
            elif preferred_slots is not None and not any([slot_type in obj.all_valid_slot_types for slot_type in preferred_slots]):
                pass
            else:
                valid_objects.add(obj)
        if is_interaction_resolver:
            self.resolver.interaction_parameters = interaction_params
        return valid_objects

class SlotStrategyBase(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'max_number_of_objects': TunableRange(description='\n            The number of objects we would like to slot into the target.\n            Obviously the number of valid objects available and the number of\n            free slots must accommodate this interval. However, it will fail\n            silently if we run out of either. This is essentially a firemeter\n            on how many objects we care to try and slot.\n            ', tunable_type=int, default=15, minimum=1, maximum=20), 'objects_to_slot': SelectObjectVariant(description='\n            The selection for objects to be slotted into the slot target.\n            '), 'slot_clone': Tunable(description='\n            Slot a clone of the object.\n            ', tunable_type=bool, default=False), 'slot_target': TunableEnumEntry(description='\n            The participant we want to slot objects into.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'require_claiming': OptionalTunable(description='\n            If enabled, if True:\n            Object slotted by this strategy will require claiming on load \n            (by some 3rd party) or they will be destroyed on load.\n            \n            If False:\n            If previously requiring claiming on load, objects slotted by this\n            strategy will no longer require claiming on load, and thus will \n            persist without fetters.\n            ', tunable=Tunable(description='\n                If checked, objects that are slotted by this strategy will\n                require claiming on load or they will be destroyed.\n                \n                If unchecked, objects that are slotted by this strategy will \n                no longer require claiming on load to avoid destruction if \n                they previously did.\n                ', tunable_type=bool, default=False)), 'use_part_owner': Tunable(description='\n            If enabled and slot target is a part, we will slot objects to the part owner\n            instead of the part.\n            ', tunable_type=bool, default=False)}

    def __init__(self, resolver, target=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        if target is None:
            self.target = resolver.get_participant(self.slot_target)
        if self.target.is_part:
            self.target = self.target.part_owner
        self.source = self.objects_to_slot(resolver, self.target)

    def slot_objects(self):
        raise NotImplementedError

    def _do_claim(self, obj):
        if self.require_claiming is None:
            return
        if self.require_claiming is False:
            obj.remove_claim_requirement()
        else:
            obj.claim()

    def _retrieve_from_household_inventory(self, obj):
        object_id = obj.id
        household_id = obj.get_household_owner_id()
        household_manager = services.household_manager()
        object_data_raw = _buildbuy.get_object_data_in_household_inventory(object_id, household_id)
        if object_data_raw is None:
            logger.error('Failed to retrieve object data for {} from household inventory.', object_id)
            return
        obj.destroy()
        removed = remove_object_from_household_inventory(object_id, household_manager.get(household_id), update_funds=False)
        if not removed:
            logger.error('Failed to remove object {} from household inventory.', object_id)
            return
        obj = household_manager.create_object_from_raw_inv_data(object_id, object_data_raw, load_object=True)
        return obj

class SlotStrategyTargetSlotType(SlotStrategyBase):
    FACTORY_TUNABLES = {'target_slot_type': TunableReference(description='\n            Slot type to place the transfered objects into the participant\n            target. Obviously the slot type must be available on the target\n            object and the source must support it.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))}

    def slot_objects(self) -> int:
        num_slotted = 0
        for obj in self.source.get_objects(preferred_slots=(self.target_slot_type,)):
            if num_slotted >= self.max_number_of_objects:
                break
            inventory = obj.get_inventory()
            for runtime_slot in self.target.get_runtime_slots_gen(slot_types={self.target_slot_type}):
                result = runtime_slot.is_valid_for_placement(obj=obj)
                if result and inventory is not None:
                    if self.slot_clone:
                        slot_clone = obj.inventoryitem_component.get_clone_for_stack_split()
                        slot_clone.set_stack_count(1)
                        obj = slot_clone
                    elif not inventory.try_remove_object_by_id(obj.id):
                        logger.error('Failed to remove object {} from inventory', obj, inventory)
                        break
                    elif obj.content_source == ContentSource.HOUSEHOLD_INVENTORY_PROXY:
                        obj = self._retrieve_from_household_inventory(obj)
                        if obj is None:
                            logger.error('Failed to remove object {} from household inventory', obj)
                            break
                    runtime_slot.add_child(obj)
                    self._do_claim(obj)
                    num_slotted += 1
                    break
        return num_slotted

class SlotStrategyAutoSlot(SlotStrategyBase):
    FACTORY_TUNABLES = {'slot_types': TunableList(description='\n            The slot types we want to fill. Order denotes priority, as we will grab unique objects that fill those slots.\n            ', tunable=TunableReference(description='\n                Slot type to place the transfered objects into the participant\n                target. Obviously the slot type must be available on the target\n                object and the source must support it.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)), unique_entries=True), 'evenly_distribute_slot_types': Tunable(description='\n            If enabled, we will attempt to go down the slot types list\n            one at a time and pull a unique object, then repeat the\n            list until the desired number of objects has been slotted,\n            we run out of objects, or we run out of slots.\n            ', tunable_type=bool, default=True)}

    def slot_objects(self):
        provided_slot_types = self.target.get_provided_slot_types()
        desired_slot_types = [slot_type for slot_type in self.slot_types if slot_type in provided_slot_types]
        num_slotted = 0
        continue_slotting = True
        slotted_objects = set()
        while num_slotted < self.max_number_of_objects and continue_slotting:
            continue_slotting = False
            for slot_type in desired_slot_types:
                available_slots = [runtime_slot for runtime_slot in self.target.get_runtime_slots_gen(slot_types={slot_type}) if not runtime_slot.children]
                shuffle(available_slots)
                if not available_slots:
                    pass
                else:
                    objects_to_slot = self.source.get_objects(preferred_slots=(slot_type,))
                    objects_to_slot.difference_update(slotted_objects)
                    for obj in objects_to_slot:
                        for runtime_slot in available_slots:
                            if runtime_slot.is_valid_for_placement(obj=obj):
                                inventory = obj.get_inventory()
                                if inventory is not None and not inventory.try_remove_object_by_id(obj.id):
                                    logger.error('Failed to remove object {} from inventory', obj, inventory)
                                elif obj.content_source == ContentSource.HOUSEHOLD_INVENTORY_PROXY:
                                    obj = self._retrieve_from_household_inventory(obj)
                                    if obj is None:
                                        logger.error('Failed to remove object {} from household inventory', obj)
                                        break
                                runtime_slot.add_child(obj)
                                services.dynamic_area_service().add_object(obj)
                                self._do_claim(obj)
                                num_slotted += 1
                                slotted_objects.add(obj)
                                continue_slotting = True
                                break
                        if (num_slotted >= self.max_number_of_objects or self.evenly_distribute_slot_types) and continue_slotting:
                            break
        return num_slotted
