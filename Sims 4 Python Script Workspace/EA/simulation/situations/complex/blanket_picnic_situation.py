from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from default_property_stream_reader import DefaultPropertyStreamReader
    from event_testing.resolver import Resolver
    from objects.components.state import ObjectState, ObjectStateValue
    from objects.game_object import GameObject
    from role.role_state import RoleState
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from sims4 import PropertyStreamWriter
    from typing import *
    from situations.situation_job import SituationJobimport servicesimport sims4.resourcesfrom event_testing.test_events import TestEventfrom indexed_manager import CallbackTypesfrom objects.components import ComponentContainerfrom objects.components.object_relationship_component import ObjectRelationshipComponentfrom sims.sim_info_types import Agefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableList, TunableReference, TunablePackSafeReferencefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom tag import TagGATHERING_SIM_IDS_TOKEN = 'gathering_sim_ids'SEATED_SIM_IDS_TOKEN = 'seated_sim_ids'NEED_FED_SIM_IDS_TOKEN = 'need_fed_sim_ids'FOOD_PLACED_TOKEN = 'food_placed'TARGET_OBJECT_TOKEN = 'target_object'BASKET_OBJECT_TOKEN = 'basket_object'
class _GatherOnBlanket(CommonInteractionCompletedSituationState):

    def on_activate(self, reader:'DefaultPropertyStreamReader'=None) -> 'None':
        super().on_activate(reader=reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)

    def timer_expired(self) -> 'None':
        self.owner.cleanup_expired_sims()
        if self.owner is None:
            return
        self.owner.assign_host_if_necessary()
        self._change_state(self.owner.place_food_on_blanket_state())

    def _get_role_state_overrides(self, sim:'Sim', job_type:'SituationJob', role_state_type:'RoleState', role_affordance_target:'GameObject') -> 'Tuple[RoleState, GameObject]':
        return (role_state_type, self.owner.target_object)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        if event == TestEvent.InteractionExitedPipeline:
            if sim_info.id in self.owner.gathering_sim_ids:
                self.owner.cleanup_expired_sim(sim_info)
                if not self.owner.gathering_sim_ids:
                    self.owner.assign_host_if_necessary()
                    self._change_state(self.owner.place_food_on_blanket_state())
        else:
            try:
                self._sim_info = sim_info
                super().handle_event(sim_info, event, resolver)
            finally:
                self._sim_info = None

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self.owner.set_sim_as_ready(self._sim_info)
        if not self.owner.gathering_sim_ids:
            self.owner.assign_host_if_necessary()
            self._change_state(self.owner.place_food_on_blanket_state())

class _PlaceFoodOnBlanket(CommonInteractionCompletedSituationState):

    def on_activate(self, reader:'DefaultPropertyStreamReader'=None) -> 'None':
        super().on_activate(reader=reader)
        self.owner.set_food_placed(False)

    def _get_role_state_overrides(self, sim:'Sim', job_type:'SituationJob', role_state_type:'RoleState', role_affordance_target:'GameObject') -> 'Tuple[RoleState, GameObject]':
        return (role_state_type, self.owner.target_object)

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        if self.owner.basket_object is None or self.owner.ensure_food_is_placed():
            self.owner.set_food_placed(True)
            self._change_state(self.owner.eat_food_on_blanket_state())
        else:
            self.owner.end_situation()

class _EatFoodOnBlanket(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'food_all_eaten_states': TunableList(description='\n            A list of object state values that each could represent all the food being eaten.\n            ', tunable=TunableReference(description='\n                An object state value that can represent the food all being eaten.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True))}

    def __init__(self, food_all_eaten_states:'List[ObjectStateValue]', *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._food_all_eaten_states = food_all_eaten_states
        self._ending_situation = False
        self._place_new_food = False

    def on_activate(self, reader:'DefaultPropertyStreamReader'=None) -> 'None':
        super().on_activate(reader=reader)
        self.owner.set_all_sims_need_fed()
        created_object = self.owner.created_object
        if created_object:
            if isinstance(created_object, ComponentContainer) and len(created_object.component_definitions) == 0:
                self._ending_situation = True
                self.owner.end_situation()
            else:
                self.owner.created_object.add_state_changed_callback(self._food_state_change)

    def timer_expired(self) -> 'None':
        self.owner.end_situation()

    def _get_role_state_overrides(self, sim:'Sim', job_type:'SituationJob', role_state_type:'RoleState', role_affordance_target:'GameObject') -> 'Tuple[RoleState, GameObject]':
        return (role_state_type, self.owner.target_object)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        try:
            self._sim_info = sim_info
            super().handle_event(sim_info, event, resolver)
        finally:
            self._sim_info = None

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self.owner.set_sim_as_fed(self._sim_info)
        if not self.owner.need_fed_sim_ids:
            if self._place_new_food:
                self._change_state(self.owner.place_food_on_blanket_state())
            elif not self._ending_situation:
                self._change_state(self.owner.eat_food_on_blanket_state())

    def on_deactivate(self) -> 'None':
        created_object = self.owner.created_object
        if created_object:
            if isinstance(created_object, ComponentContainer) and len(created_object.component_definitions) == 0:
                self._ending_situation = True
                self.owner.end_situation()
            else:
                self.owner.created_object.remove_state_changed_callback(self._food_state_change)
        super().on_deactivate()

    def _food_state_change(self, owner:'GameObject', state:'ObjectState', old_value:'ObjectStateValue', new_value:'ObjectStateValue') -> 'None':
        if new_value in self._food_all_eaten_states:
            if self.owner.is_basket_empty():
                self._ending_situation = True
                self.owner.end_situation()
            else:
                self._place_new_food = True

class BlanketPicnicSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'host_job': TunableReference(description='\n            The situation job for the Sim that initiated the gathering.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), 'guest_job': TunableReference(description='\n            The situation job for those gathering to eat on the blanket.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), 'gather_on_blanket_state': _GatherOnBlanket.TunableFactory(description='\n            The state to bring all picked Sims to gather on the blanket.\n            ', display_name='1. Gather on Blanket State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'place_food_on_blanket_state': _PlaceFoodOnBlanket.TunableFactory(description='\n            The state to place food on the blanket.\n            ', display_name='2. Place Food on Blanket State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'eat_food_on_blanket_state': _EatFoodOnBlanket.TunableFactory(description='\n            The state to have the Sims start eating food from the blanket.\n            ', display_name='3. Eat Food on Blanket State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'basket_object_tag': TunableEnumEntry(description='\n            The tag that marks an object as a valid picnic basket.\n            Will be compared against the tags of any object in the basket slot.\n            ', tunable_type=Tag, default=Tag.INVALID), 'basket_slot_name': Tunable(description='\n            The name of the slot that picnic basket could be placed in.\n            ', tunable_type=str, default='_deco_med_'), 'food_object_tag': TunableEnumEntry(description="\n            The tag that marks an object as a valid food object.\n            Will be compared against the tags of the objects in\n            the picnic basket's inventory, if there is a basket.\n            ", tunable_type=Tag, default=Tag.INVALID), 'food_slot_name': Tunable(description='\n            The name of the slot that the food object will be placed in.\n            ', tunable_type=str, default='_ctnm_eat_')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self.gathering_sim_ids = set()
        self._seated_sim_ids = set()
        self.need_fed_sim_ids = set()
        self._food_placed = False
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            self.gathering_sim_ids.update(reader.read_uint64s(GATHERING_SIM_IDS_TOKEN, ()))
            self._seated_sim_ids.update(reader.read_uint64s(SEATED_SIM_IDS_TOKEN, ()))
            self.need_fed_sim_ids.update(reader.read_uint64s(NEED_FED_SIM_IDS_TOKEN, ()))
            self._food_placed = reader.read_bool(FOOD_PLACED_TOKEN, False)
        self.target_object = self._get_target_object()
        self.created_object = self._get_created_object()
        self.basket_object = self._get_basket_object()
        object_manager = services.object_manager()
        object_manager.register_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_object_removed)
        if self.target_object:
            self.target_object.add_state_changed_callback(self._blanket_state_change)
            self.target_object.register_on_location_changed(self._on_blanket_location_changed)

    def _destroy(self) -> 'None':
        object_manager = services.object_manager()
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_object_removed)
        if self.target_object:
            self.target_object.remove_state_changed_callback(self._blanket_state_change)
            self.target_object.unregister_on_location_changed(self._on_blanket_location_changed)
        super()._destroy()

    def start_situation(self) -> 'None':
        super().start_situation()
        self._change_state(self.gather_on_blanket_state())

    def end_situation(self) -> 'None':
        self._self_destruct()

    def _on_add_sim_to_situation(self, sim:'Sim', job_type:'SituationJob', role_state_type_override:'RoleState'=None) -> 'None':
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override)
        if self.target_object:
            ObjectRelationshipComponent.setup_relationship(sim, self.target_object)
        self.gathering_sim_ids.add(sim.id)

    def _on_remove_sim_from_situation(self, sim:'Sim') -> 'None':
        super()._on_remove_sim_from_situation(sim)
        if self.target_object:
            self.target_object.objectrelationship_component.remove_relationship(sim.id)
        self.gathering_sim_ids.discard(sim.id)
        self._seated_sim_ids.discard(sim.id)
        self.need_fed_sim_ids.discard(sim.id)

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, ...]':
        return (SituationStateData(1, _GatherOnBlanket, factory=cls.gather_on_blanket_state), SituationStateData(2, _PlaceFoodOnBlanket, factory=cls.place_food_on_blanket_state), SituationStateData(3, _EatFoodOnBlanket, factory=cls.eat_food_on_blanket_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return list(cls.gather_on_blanket_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls) -> 'SituationJob':
        return cls.guest_job

    def get_target_object(self) -> 'Optional[GameObject]':
        return self.target_object

    def _get_target_object(self) -> 'Optional[GameObject]':
        reader = self._seed.custom_init_params_reader
        if reader is None:
            blanket_object_id = self._seed.extra_kwargs.get('default_target_id', None)
        else:
            blanket_object_id = reader.read_uint64(TARGET_OBJECT_TOKEN, None)
        if blanket_object_id:
            return services.object_manager().get(blanket_object_id)
        else:
            return

    def get_created_object(self, food_placed_override:'bool'=False) -> 'Optional[GameObject]':
        if self.created_object is not None:
            return self.created_object
        return self._get_created_object(food_placed_override)

    def _get_created_object(self, food_placed_override:'bool'=False) -> 'Optional[GameObject]':
        if self._food_placed or food_placed_override:
            for slot in self.target_object.get_runtime_slots_gen():
                if slot.slot_name_or_hash == self.food_slot_name:
                    child_objects = slot.children
                    if not child_objects:
                        return
                    possible_food = child_objects[0]
                    if self.food_object_tag in possible_food.get_tags():
                        self.created_object = possible_food
                        return possible_food
                    self.created_object = None
                    return

    def _get_basket_object(self) -> 'Optional[GameObject]':
        reader = self._seed.custom_init_params_reader
        if reader is None:
            for slot in self.target_object.get_runtime_slots_gen():
                if slot.slot_name_or_hash == self.basket_slot_name:
                    child_objects = slot.children
                    if not child_objects:
                        return
                    else:
                        possible_basket = child_objects[0]
                        if self.basket_object_tag in possible_basket.get_tags():
                            return possible_basket
                    return
        else:
            basket_object_id = reader.read_uint64(BASKET_OBJECT_TOKEN, None)
            if basket_object_id:
                return services.object_manager().get(basket_object_id)

    def ensure_food_is_placed(self) -> 'bool':
        if self.get_created_object(True) is not None:
            return True
        if self.basket_object is None or self.is_basket_empty():
            return False
        food_object = self.basket_object.inventory_component.get_objects_by_tag(self.food_object_tag)[0]
        for slot in self.target_object.get_runtime_slots_gen():
            if slot.slot_name_or_hash == self.food_slot_name:
                if not slot.is_valid_for_placement(obj=food_object):
                    return False
                slot.add_child(food_object)
                return True
        return False

    def is_basket_empty(self) -> 'bool':
        if self.basket_object is None:
            return True
        return self.basket_object.inventory_component.get_count_by_tag(self.food_object_tag) <= 0

    def cleanup_expired_sims(self) -> 'None':
        sim_info_manager = services.sim_info_manager()
        for sim_id in tuple(self.gathering_sim_ids):
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            else:
                sim = sim_info.get_sim_instance()
                if sim is not None and self.is_sim_in_situation(sim):
                    self.remove_sim_from_situation(sim)
        self.gathering_sim_ids.clear()
        if self.num_of_sims == 0:
            self.end_situation()

    def cleanup_expired_sim(self, sim_info:'SimInfo') -> 'None':
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is not None and self.is_sim_in_situation(sim):
            self.remove_sim_from_situation(sim)
            self.gathering_sim_ids.discard(sim_info.id)
            if self.num_of_sims == 0:
                self.end_situation()

    def set_sim_as_ready(self, sim_info:'SimInfo') -> 'None':
        if sim_info is None:
            return
        self.gathering_sim_ids.discard(sim_info.id)
        self._seated_sim_ids.add(sim_info.id)

    def set_sim_as_fed(self, sim_info:'SimInfo') -> 'None':
        if sim_info is None:
            return
        self.need_fed_sim_ids.discard(sim_info.id)

    def set_all_sims_need_fed(self) -> 'None':
        for sim_id in self._seated_sim_ids:
            self.need_fed_sim_ids.add(sim_id)

    def assign_host_if_necessary(self) -> 'None':
        if self.get_num_sims_in_job(job_type=self.host_job) > 0:
            return
        for sim in self.all_sims_in_situation_gen():
            if sim.age >= Age.YOUNGADULT:
                self._set_job_for_sim(sim, self.host_job)
                return

    def set_food_placed(self, food_placed:'bool') -> 'None':
        self._food_placed = food_placed

    def _save_custom_situation(self, writer:'PropertyStreamWriter') -> 'None':
        super()._save_custom_situation(writer)
        if not len(self.gathering_sim_ids) == 0:
            writer.write_uint64s(GATHERING_SIM_IDS_TOKEN, self.gathering_sim_ids)
        if not len(self._seated_sim_ids) == 0:
            writer.write_uint64s(SEATED_SIM_IDS_TOKEN, self._seated_sim_ids)
        if not len(self.need_fed_sim_ids) == 0:
            writer.write_uint64s(NEED_FED_SIM_IDS_TOKEN, self.need_fed_sim_ids)
        if self._food_placed:
            writer.write_bool(FOOD_PLACED_TOKEN, self._food_placed)
        if self.target_object is not None:
            writer.write_uint64(TARGET_OBJECT_TOKEN, self.target_object.id)
        if self.basket_object is not None:
            writer.write_uint64(BASKET_OBJECT_TOKEN, self.basket_object.id)

    def _on_object_removed(self, obj:'GameObject') -> 'None':
        if obj.id == self.target_object.id:
            self._self_destruct()

    def _blanket_state_change(self, owner:'GameObject', state:'ObjectState', old_value:'ObjectStateValue', new_value:'ObjectStateValue') -> 'None':
        self._self_destruct()

    def _on_blanket_location_changed(self, obj:'GameObject', *args, **kwargs) -> 'None':
        if obj.id == self.target_object.id:
            self._self_destruct()
lock_instance_tunables(BlanketPicnicSituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)