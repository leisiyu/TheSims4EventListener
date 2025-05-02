from __future__ import annotationsfrom event_testing.tests import TunableTestSetfrom interactions.payment.payment_info import PaymentBusinessRevenueTypefrom sims4.resources import Typesfrom sims4.utils import classpropertyfrom collections import Counterfrom event_testing.resolver import SingleSimResolverfrom snippets import TunableAffordanceListReferencefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfoimport randomimport stringfrom buffs.buff import Bufffrom business.business_situation_mixin import BusinessSituationMixinfrom carry.carry_elements import run_fixup_carryable_simsfrom carry.carry_utils import get_carried_objects_genfrom carry.carry_postures import CarryingObjectfrom carry.carry_tuning import CarryTuningfrom clubs.club_tuning import ClubCriteriaCategoryfrom dynamic_areas.dynamic_area_enums import DynamicAreaTypefrom interactions.interaction_finisher import FinishingTypefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom objects.components.sim_visualizer_component import SimVisualizerDatafrom server.pick_info import PickInfo, PickTypefrom situations.situation_guest_list import SituationGuestInfofrom situations.bouncer.bouncer_request import RequestSpawningOptionfrom situations.bouncer.bouncer_types import BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, CommonSituationState, SituationComplexCommon, SituationStateData, TunableInteractionOfInterestfrom situations.situation_types import SituationSerializationOptionfrom sims.sim_info_types import Age, Speciesfrom sims.sim_spawner import SimSpawnerfrom small_business.small_business_customer_wait_satisfaction import SmallBusinessCustomerSatisfactionfrom small_business.small_business_debug import update_small_business_situation_debug_visualizerfrom small_business.small_business_tuning import SmallBusinessTunablesfrom small_business.small_business_customer_loot_ops import SmallBusinessCustomerStatesfrom sims4.tuning.instances import create_tuning_blueprint_classfrom sims4.tuning.tunable import TunableSimMinute, TunableList, TunableTuple, TunableRange, Tunable, TunableReference, TunableEnumEntry, TunableMappingimport carryimport interactionsimport objects.systemimport sims4import serviceslogger = sims4.log.Logger('SmallBusinessSituation', default_owner='mmikolajczyk')
class _ConsiderVisit(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        if self.owner is None:
            return
        self._change_state(self.owner.leave_state())

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, role_affordance_target)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return
        return sim_info.id == self.owner.guest_id

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.check_in_state())

    def on_activate(self, reader=None):
        super().on_activate(reader)
        sim_info = services.sim_info_manager().get(self.owner.guest_id)
        if sim_info is not None and sim_info.household == services.active_household():
            self._change_state(self.owner.check_in_state())

class _CheckIn(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        if self.owner is None:
            return
        self._change_state(self.owner.leave_state())

    def on_activate(self, reader=None):
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(self.test_event, custom_key)
        super(CommonInteractionCompletedSituationState, self).on_activate(reader)
        if self.owner is not None:
            self.owner.pick_up_dependent()

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, role_affordance_target)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return
        return sim_info.id == self.owner.guest_id

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.put_down_state())

class _PutDownDependent(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        if self.owner is None:
            return
        self._change_state(self.owner.leave_state())

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._is_walking_to_location = True
        for sim in self.owner.all_sims_in_situation_gen():
            if sim.sim_id == self.owner.guest_id and self.owner.pick_up_dependent():
                self._push_interaction(sim)
                return
        self._change_state(self.owner.customer_visit_state())

    def _build_terrain_interaction_target_and_context(self, carried_sim, carrying_sim, near_object, pick_type):
        routing_surface = carried_sim.routing_surface
        (translation, orientation, _) = CarryingObject.get_good_location_on_floor(carried_sim, starting_transform=near_object.transform, starting_routing_surface=routing_surface)
        location = sims4.math.Location(sims4.math.Transform(translation), routing_surface)
        target = objects.terrain.TerrainPoint(location)
        pick = PickInfo(pick_type=pick_type, target=target, location=translation, routing_surface=routing_surface)
        return (target, InteractionContext(carrying_sim, InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, Priority.High, pick=pick))

    def _get_object_of_interest(self, carried_sim_info):
        area = services.dynamic_area_service().get_dynamic_area(DynamicAreaType.BUSINESS_PUBLIC)
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        if business_manager is None:
            logger.error('No business manager found')
            return
        motives = frozenset([business_manager.encouragement_commodity])
        age = carried_sim_info.age
        species = carried_sim_info.species
        object_manager = services.object_manager()
        for data in SmallBusinessTunables.DEPENDENT_PLACEMENT_OBJECT_TAGS:
            if age == data.age and species == data.species:
                objects_matching_tags = object_manager.get_objects_matching_tags(data.object_tags)
                tag_objects = [obj for obj in objects_matching_tags if obj.id in area.objects]
                if tag_objects:
                    random.shuffle(tag_objects)
                    for obj in tag_objects:
                        if obj.commodity_flags & motives:
                            return obj
                    return tag_objects[0]
                for obj_id in area.objects:
                    obj = services.object_manager().get(obj_id)
                    if obj and obj.is_inside_building:
                        return obj

    def _push_interaction(self, carrying_sim):
        for carried_sim in self.owner.all_sims_in_situation_gen():
            if carried_sim.sim_id == self.owner.guest_supervised_id:
                obj = self._get_object_of_interest(carried_sim)
                if obj is None:
                    obj = carried_sim
                (target, context) = self._build_terrain_interaction_target_and_context(carried_sim, carrying_sim, obj, PickType.PICK_TERRAIN)
                carrying_sim.push_super_affordance(self.owner.terrain_walk_to, target, context)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return
        return sim_info.id == self.owner.guest_id

    def _on_interaction_of_interest_complete(self, **kwargs):
        if self._is_walking_to_location:
            self._is_walking_to_location = False
            (carried_sim, carrying_sim) = (None, None)
            for sim in self.owner.all_sims_in_situation_gen():
                if sim.sim_id == self.owner.guest_supervised_id:
                    carried_sim = sim
                elif sim.sim_id == self.owner.guest_id:
                    carrying_sim = sim
            (target, context) = self._build_terrain_interaction_target_and_context(carried_sim, carrying_sim, carrying_sim, PickType.PICK_TERRAIN)
            context.carry_target = carried_sim
            carrying_sim.push_super_affordance(self.owner.terrain_place, target, context)
        else:
            self._change_state(self.owner.customer_visit_state())

class _BusinessVisit(CommonSituationState):
    FACTORY_TUNABLES = {'timeout_variation': TunableSimMinute(description='\n            Maximum random value to change the timeout by', default=0, minimum=0), 'switch_next_state_tests': TunableList(description='\n            Tests to pass by the sim to switch to next state. All tests must pass.\n            ', tunable=TunableTuple(test=TunableTestSet(), time_to_add=TunableSimMinute(description="\n                    Time to add to the timeout if the test doesn't pass\n                    ", default=60)))}

    def __init__(self, timeout_variation:'TunableSimMinute', switch_next_state_tests:'TunableTestSet', **kwargs):
        super().__init__(**kwargs)
        self._timeout_variation = timeout_variation
        self._switch_next_state_tests = switch_next_state_tests

    def on_activate(self, reader=None):
        self._time_out += random.uniform(-self._timeout_variation, self._timeout_variation)
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        if business_manager is None:
            logger.error('No business manager found')
            return
        self._time_out = self._get_customer_total_time_with_modifiers(self._time_out, self.owner.business_owner_info)
        super().on_activate(reader)
        if not reader:
            guest = services.sim_info_manager().get(self.owner.guest_id)
            if self.owner.adult_guest_stays_on_lot:
                self.owner.add_as_business_customer(guest)
            else:
                situation_manager = services.get_zone_situation_manager()
                situation_manager.make_sim_leave_now_must_run(guest)
            if self.owner.guest_supervised_id != -1:
                dependent = services.sim_info_manager().get(self.owner.guest_supervised_id)
                self.owner.add_as_business_customer(dependent)

        def create_small_business_identifiable_tuning(base_class, name):
            tuning_blueprint_cls = create_tuning_blueprint_class(base_class)
            tuning_blueprint = tuning_blueprint_cls(name)
            return tuning_blueprint

        self.owner.encouragement_buff = create_small_business_identifiable_tuning(Buff, self.owner.encouragement_name)
        self.owner.encouragement_buff.visible = False
        sim_info_manager = services.sim_info_manager()
        for guest_info in self.owner.guest_list.guest_info_gen():
            if guest_info.sim_id == self.owner.guest_id and self.owner.adult_guest_stays_on_lot:
                sim = sim_info_manager.get(guest_info.sim_id)
                sim.add_buff(self.owner.encouragement_buff, additional_static_commodities_to_add=(business_manager.encouragement_commodity,))
            if guest_info.sim_id == self.owner.guest_supervised_id:
                sim = sim_info_manager.get(guest_info.sim_id)
                sim.add_buff(self.owner.encouragement_buff, additional_static_commodities_to_add=(business_manager.encouragement_commodity,))

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, role_affordance_target)

    def timer_expired(self):
        sim_info = services.sim_info_manager().get(self.owner.guest_id)
        time_to_add = self.owner.can_switch_state(sim_info, self._switch_next_state_tests)
        if sim_info.household == services.active_household() or len(services.ensemble_service().get_all_ensembles_for_sim(sim_info.get_sim_instance())) > 0:
            self._create_or_load_alarm(self._time_out_string, self._time_out, lambda _: self.timer_expired(), should_persist=True)
        elif time_to_add:
            self._create_or_load_alarm(self._time_out_string, time_to_add, lambda _: self.timer_expired(), should_persist=True)
        elif self.owner.guest_supervised_id != -1 and not self.owner.adult_guest_stays_on_lot:
            supervised_sim_info = services.sim_info_manager().get(self.owner.guest_supervised_id)
            self.owner.unregister_customer(supervised_sim_info)
            self._change_state(self.owner.say_goodbye_state())
        else:
            self._change_state(self.owner.check_out_state())

    def _get_customer_total_time_with_modifiers(self, current_time:'float', owner_info:'SimInfo'):
        pheromone_perk_mod = SmallBusinessTunables.PERK_SETTINGS.eau_the_store_pheromone
        if pheromone_perk_mod is not None and owner_info.has_trait(pheromone_perk_mod.perk_trait):
            return current_time + current_time*pheromone_perk_mod.percentage
        else:
            return current_time

class _CheckOut(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'switch_next_state_tests': TunableList(description='\n            Tests to pass by the sim to switch to next state. All tests must pass.\n            ', tunable=TunableTuple(test=TunableTestSet(), time_to_add=TunableSimMinute(description="\n                    Time to add to the timeout if the test doesn't pass\n                    ", default=60)))}

    def __init__(self, switch_next_state_tests:'TunableTestSet', **kwargs):
        super().__init__(**kwargs)
        self._switch_next_state_tests = switch_next_state_tests

    def timer_expired(self):
        if self.owner is None:
            return
        sim_info = services.sim_info_manager().get(self.owner.guest_id)
        time_to_add = self.owner.can_switch_state(sim_info, self._switch_next_state_tests)
        if time_to_add:
            self._create_or_load_alarm(self._time_out_string, time_to_add, lambda _: self.timer_expired(), should_persist=True)
        else:
            self._change_state(self.owner.leave_state())

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self.owner.guest_supervised_id != -1 and not self.owner.adult_guest_stays_on_lot:
            self._change_state(self.owner.leave_state())
        self.owner._cleanup_small_business_situation()

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, role_affordance_target)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return
        return sim_info.id == self.owner.guest_id

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.leave_state())

class _SayGoodbyeState(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        if self.owner is None:
            return
        self._change_state(self.owner.leave_state())

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return
        return sim_info.id == self.owner.guest_supervised_id

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.leave_state())

class _LeaveState(CommonSituationState):

    def timer_expired(self):
        if self.owner is None:
            return
        situation_manager = services.get_zone_situation_manager()
        for sim in self.owner.all_sims_in_situation_gen():
            situation_manager.make_sim_leave_now_must_run(sim)

    def on_activate(self, reader=None):
        super().on_activate(reader)
        situation_manager = services.get_zone_situation_manager()
        if self.owner.guest_supervised_id != -1:
            for sim in self.owner.all_sims_in_situation_gen():
                if sim.sim_id == self.owner.guest_id:
                    for (_, _, carried_object) in get_carried_objects_gen(sim):
                        if carried_object.id == self.owner.guest_supervised_id:
                            situation_manager.add_sim_to_auto_fill_blacklist(sim.sim_id, self.owner._default_job)
                            sim_interactions = sim.get_all_running_and_queued_interactions()
                            for running_interaction in sim_interactions:
                                if running_interaction.get_interaction_type() is self.owner.terrain_walk_to:
                                    running_interaction.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Sim leaving the business.')
                            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
                            sim.push_super_affordance(self.owner.leave_affordance, sim, context, care_dependent=carried_object)
                            return
        for sim in self.owner.all_sims_in_situation_gen():
            if sim.sim_id == self.owner.guest_id:
                situation_manager.add_sim_to_auto_fill_blacklist(sim.id, self.owner._default_job)
                situation_manager.make_sim_leave_now_must_run(sim)
            elif sim.is_human and sim.age is not Age.CHILD:
                context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
                sim.push_super_affordance(self.owner.toddler_or_infant_fadeout, sim, context)
            else:
                situation_manager.make_sim_leave_now_must_run(sim)

class SmallBusinessCustomerSituation(BusinessSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'_default_job': TunableReference(description='\n            The default job for this situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), 'consider_visit_state': _ConsiderVisit.TunableFactory(description='\n            The state where sims decide if they will attend the business.\n            ', display_name='1. Consider Visit State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'check_in_state': _CheckIn.TunableFactory(description='\n            The state where sims use the ticket machine to check in.\n            ', display_name='2. Start Check In State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'put_down_state': _PutDownDependent.TunableFactory(description='\n            The state where sims puts down the dependent if they are carrying one.\n            ', display_name='3. Put Down Dependent State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'customer_visit_state': _BusinessVisit.TunableFactory(description='\n            The state where sims follow business rules freely.\n            ', display_name='4. Start customer behavior', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'check_out_state': _CheckOut.TunableFactory(description='\n            The state where sims use the ticket machine to check out before leaving.\n            ', display_name='5. Start check out state', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'say_goodbye_state': _SayGoodbyeState.TunableFactory(description='\n            The state where dependent sim left alone says goodbye before disappearing.\n            ', display_name='6. Dependent customer says goodbye', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _LeaveState.TunableFactory(description='\n            The state forcing sims to immediately leave.\n            ', display_name='7. Customer leaves the lot', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'satisfaction_waiting_timers': TunableList(description='\n            Launch a timer when customer is not performing the desired interaction.\n            Loot action is triggered when the timer is expired.\n            Each time the timer expired, it launch a new one with the data of the next row in the list.\n            ', tunable=TunableTuple(timer=TunableSimMinute(description='\n                    Timer before applying (in sim minutes)\n                    ', default=1.0, minimum=0.0), loot_action=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))), 'satisfaction_activity_timer': TunableTuple(description='\n            Launch a timer when customer is performing a business interaction.\n            Loot action is triggered when the timer is expired.\n            Each time the timer expired, it launch a new one.\n            ', timer=TunableSimMinute(description='\n                Timer before applying (in sim minutes)\n                ', default=1.0, minimum=0.0), loot_action=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'satisfaction_waiting_ratios_rewards': TunableList(description='.\n            Give a loot action depending on the waiting ratio. \n            Will select the first row of the value being bigger than the waiting ratio\n            Should be ordered smallest to largest.\n            ', tunable=TunableTuple(max_range_ratio_value=TunableRange(description='\n                    Return the loot action if the waiting ratio is under this range value\n                    ', tunable_type=float, default=0.0, minimum=0.0, maximum=1.0), loot_action=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))), 'satisfaction_start_waiting_ratio': TunableRange(description='.\n            When satisfaction waiting ratio start (after first desired interaction), set the waiting time to correspond \n            to this waiting ratio. Allow for customer to start with a ratio that is not 100 or 0 percent\n            ', tunable_type=float, default=0.5, minimum=0.0, maximum=1.0), 'satisfaction_interaction_counter_rewards': TunableList(description='.\n            Give customer a loot action after performing a specific number of interactions in the business\n            ', tunable=TunableTuple(interaction_count=Tunable(description='\n                    Number of interaction required to be rewarded\n                    ', tunable_type=int, default=1), loot_action=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))), 'satisfaction_markup_ratios_rewards': TunableList(description='\n            Give customer a loot action after their total payments markup ratio has reached a certain amount.\n            This value can be below or above 0. Below stands for the customer not being satisfied with the price\n            i.e. a higher markup, while upper stands for the customer being happy with the price thanks to a discount.\n            \n            The lowest reward will be used for all values below it. \n            The highest reward will be used for all values above it.\n            ', tunable=TunableTuple(minimum_ratio_value=Tunable(description='\n                    Minimum ratio that should be in place in order for this loot to be applied.\n                    ', tunable_type=float, default=0.0), loot_action=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))), 'satisfaction_markup_ratio_per_markup_value': TunableMapping(description='\n            Map of values that establish how much should the markup value affect the ratio used for the price satisfaction.\n            \n            The key of the map refers to the markup value, while the value refers to the ratio value which will be used\n            in the computation.\n            ', key_type=Tunable(description='\n                Markup value.\n                ', tunable_type=float, default=0.0), key_name='markup_value', value_type=Tunable(description='\n                Ratio value which will be used in the computation.\n                ', tunable_type=float, default=0.0), value_name='ratio_value'), 'satisfaction_markup_ratio_per_payment_type': TunableMapping(description='\n            Map of values that establish how much should the payment type (interaction, hourly fee, entry fee...) affect the ratio used for the price satisfaction.\n            \n            The key of the map refers to the payment type, while the value refers to the ratio value which will be used\n            in the computation.\n            ', key_type=TunableEnumEntry(description='\n                The type of the payment.\n                ', tunable_type=PaymentBusinessRevenueType, default=PaymentBusinessRevenueType.SMALL_BUSINESS_INTERACTION_FEE), key_name='payment_type', value_type=Tunable(description='\n                Ratio value which will be used in the computation.\n                ', tunable_type=float, default=0.0), value_name='ratio_value'), 'terrain_place': TunableReference(description='\n            The affordance used to put down the carried sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'terrain_walk_to': TunableReference(description='\n            The affordance used to walk to the object of interest.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'leave_affordance': TunableReference(description='\n             The affordance used to make sims leave the lot as soon as possible.\n             ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'calculate_entry_affordance': TunableReference(description='\n            The affordance used to decide if sim will go into the business.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'toddler_or_infant_fadeout': TunableReference(description='\n            The affordance used to despawn infants and toddlers with fase out.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'pick_up_affordances': TunableList(description='\n            The affordances used to force the sim to pick their dependent back up if they \n            put them down too soon.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True)), 'satisfaction_loot': TunableList(description='\n            A list of loot operations to apply for leaving customers.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, seed):
        super().__init__(seed)
        self.encouragement_buff = None
        self.encouragement_name = 'SmallBusinessEncouragement'
        self.adult_guest_stays_on_lot = True
        self._satisfaction_logic = None
        self._satisfaction_logic_supervised = None
        self.guest_id = -1
        self.guest_supervised_id = -1
        self.business_owner_info = None
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        if business_manager is not None:
            self.business_owner_info = services.sim_info_manager().get(business_manager.owner_sim_id)
        if self.business_owner_info is None:
            logger.error('Trying to start a client situation for a business without an owner.')
            return
        if self.guest_list.guest_info_count == 0:
            guests = self.get_guests_info()
            for guest in guests:
                self.guest_list.add_guest_info(guest)
        else:
            to_remove = set()
            for guest_info in self.guest_list.guest_info_gen():
                sim_info = services.sim_info_manager().get(guest_info.sim_id)
                if sim_info is None:
                    to_remove.add(guest_info)
                elif sim_info.age > Age.CHILD and sim_info.species == Species.HUMAN:
                    self.guest_id = guest_info.sim_id
                elif sim_info.household == services.active_household():
                    self.guest_id = guest_info.sim_id
                else:
                    self.guest_supervised_id = guest_info.sim_id
            for guest_info in to_remove:
                self.guest_list.remove_guest_info(guest_info)

    def load_situation(self) -> 'bool':
        result = super().load_situation()
        if self.guest_id == -1:
            result = False
        return result

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._satisfaction_logic is not None:
            self._satisfaction_logic.save_satisfaction_data(writer, self.guest_id)
        if self._satisfaction_logic_supervised is not None:
            self._satisfaction_logic_supervised.save_satisfaction_data(writer, self.guest_supervised_id)

    def add_as_business_customer(self, sim):
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        if business_manager is not None:
            business_manager.add_customer(sim.sim_info)

    def unregister_customer(self, sim_info):
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=self.business_owner_info.sim_id)
        if business_manager is not None and business_manager.is_sim_a_customer(sim_info):
            resolver = SingleSimResolver(sim_info)
            for loot in self.satisfaction_loot:
                loot.apply_to_resolver(resolver)
            business_manager.remove_customer(sim_info, True)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.consider_visit_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _ConsiderVisit, factory=cls.consider_visit_state), SituationStateData(2, _CheckIn, factory=cls.check_in_state), SituationStateData(3, _PutDownDependent, factory=cls.put_down_state), SituationStateData(4, _BusinessVisit, factory=cls.customer_visit_state), SituationStateData(5, _CheckOut, factory=cls.check_out_state), SituationStateData(6, _SayGoodbyeState, factory=cls.say_goodbye_state), SituationStateData(7, _LeaveState, factory=cls.leave_state))

    @classmethod
    def default_job(cls):
        return cls._default_job

    @classmethod
    def get_tuned_jobs(cls):
        return [cls._default_job]

    @classproperty
    def should_have_encouragement_buff(cls):
        return True

    @classproperty
    def situation_serialization_option(cls):
        if services.current_zone().is_zone_shutting_down:
            return SituationSerializationOption.DONT
        return SituationSerializationOption.LOT

    def get_guests_info(self) -> '[SituationGuestInfo]':
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        guests = []
        if business_manager is None:
            logger.error('No business manager found')
            return guests
        self.adult_guest_stays_on_lot = business_manager.dependents_supervised
        attendance_criteria = business_manager.attendance_criteria
        supervised_criteria = []
        accept_ghosts = False
        for crit in attendance_criteria:
            if crit.CATEGORY == ClubCriteriaCategory.CARE_SIM_TYPE_SUPERVISED:
                supervised_criteria.append(crit)
            if crit.CATEGORY == ClubCriteriaCategory.OCCULT:
                accept_ghosts = SmallBusinessTunables.GHOST_TRAIT in crit.traits
        sim_info_service = services.sim_info_manager()
        customer_reputation_criteria = self._get_business_reputation_sim_filter(self.business_owner_info)

        def _score_extra_points_for_reputation(sim_info):
            extra_score = 0
            if customer_reputation_criteria is not None:
                resolver = SingleSimResolver(sim_info)
                if sims4.random.random_chance(customer_reputation_criteria.probability*100):
                    extra_score += 0.5
            return extra_score

        def _score_potential_customer(sim_info):
            score = 1
            if self.business_owner_info.household == sim_info.household:
                return (sim_info.sim_id, -1)
            if accept_ghosts or sim_info.is_ghost:
                return (sim_info.sim_id, -1)
            for criteria in attendance_criteria:
                if criteria.test_sim_info(sim_info):
                    score += 1
                else:
                    if criteria.required:
                        return (sim_info.sim_id, 0)
                    score += SmallBusinessTunables.MIN_ATTENDANCE_CRITERIA_SCORE
            score += _score_extra_points_for_reputation(sim_info)
            return (sim_info.sim_id, score)

        allowed_sim_ids_scored = [scored_sim for scored_sim in (_score_potential_customer(sim_info) for sim_info in services.sim_info_manager().get_all()) if scored_sim[1] > 0]
        if not allowed_sim_ids_scored:
            zone_director = services.venue_service().get_zone_director()
            if zone_director and zone_director.get_customer_situation_count() > 0:
                business_manager.send_no_customers_notification(SmallBusinessTunables.ALL_CUSTOMER_MATCHING_CRITERIA_ON_COOLDOWN_TNS)
            else:
                business_manager.send_no_customers_notification(SmallBusinessTunables.NO_CUSTOMERS_MATCHING_CRITERIA_TNS)
            return guests
        sorted_ids = sorted(allowed_sim_ids_scored, key=lambda k: k[1], reverse=True)
        max_score = sorted_ids[0][1]
        max_random_check = Counter(sorted_id[1] == max_score for sorted_id in sorted_ids)[1]
        filter_service = services.sim_filter_service()
        situation_manager = services.get_zone_situation_manager()
        start = 0
        ids_count = len(sorted_ids)
        auto_fill_blacklist = situation_manager.get_auto_fill_blacklist(sim_job=self._default_job)
        while start < ids_count:
            max_end = start + max_random_check
            end = ids_count if max_end > ids_count else max_end
            test_set = sorted_ids[start:end]
            random.shuffle(test_set)
            for sim in test_set:
                sim_id = sim[0]
                sim_info = sim_info_service.get(sim_id)
                sim_instance = sim_info.get_sim_instance()
                if sim_instance:
                    pass
                elif sim_id in auto_fill_blacklist:
                    pass
                elif filter_service.does_sim_match_filter(sim_id, sim_filter=SmallBusinessTunables.SMALL_BUSINESS_CUSTOMER_FILTER(), gsi_source_fn=self.get_sim_filter_gsi_name()):
                    if len(supervised_criteria) > 0:
                        supervising_visitor = sim_info_service.get(sim_id)
                        potential_sims = supervised_criteria[0].get_matching_sims_in_household(supervising_visitor)
                        for supervised_sim in potential_sims:
                            if supervised_sim.is_instanced():
                                pass
                            else:
                                self.guest_supervised_id = supervised_sim.sim_id
                                guests.append(SituationGuestInfo(supervised_sim.sim_id, self.default_job(), RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
                                break
                    self.guest_id = sim_id
                    guests.append(SituationGuestInfo(sim_id, self.default_job(), RequestSpawningOption.CANNOT_SPAWN if len(guests) > 0 else RequestSpawningOption.MUST_SPAWN, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
                    return guests
            start = end
        zone_director = services.venue_service().get_zone_director()
        if len(auto_fill_blacklist) > 0 or zone_director and zone_director.get_customer_situation_count() > 0:
            business_manager.send_no_customers_notification(SmallBusinessTunables.ALL_CUSTOMER_MATCHING_CRITERIA_ON_COOLDOWN_TNS)
        else:
            business_manager.send_no_customers_notification(SmallBusinessTunables.NO_CUSTOMERS_MATCHING_CRITERIA_TNS)
        return guests

    def _destroy(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            business_service = services.business_service()
            business_manager = business_service.get_business_manager_for_sim(sim_id=self.business_owner_info.sim_id)
            if business_manager is not None and self._on_business_closed in business_manager.on_store_closed:
                business_manager.on_store_closed.unregister(self._on_business_closed)
        super()._destroy()

    def on_remove(self):
        super().on_remove()
        self._cleanup_small_business_situation()

    def _cleanup_small_business_situation(self):
        if self.encouragement_buff is not None:
            for sim in self._situation_sims:
                sim_interactions = sim.get_all_running_and_queued_interactions()
                for interaction in sim_interactions:
                    interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Leaving the business.')
                sim.remove_buff_by_type(self.encouragement_buff)

    def start_situation(self):
        if self.guest_id == -1:
            self._self_destruct()
            return

        def _on_carry_fixup_finished() -> 'None':
            sim = services.sim_info_manager().get(self.guest_id).get_sim_instance()
            supervised_sim = services.sim_info_manager().get(self.guest_supervised_id).get_sim_instance()
            if sim is None or supervised_sim is None:
                self._self_destruct()
                return
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            sim.push_super_affordance(self.calculate_entry_affordance, sim, context)
            supervised_sim.fade_in()
            sim.fade_in()

        def _on_spawn_supervised(sim):
            if sim.is_human and sim.age is not Age.CHILD or sim.is_human or sim.age is Age.CHILD:
                leader_sim = services.object_manager().get(self.guest_id)
                sims_to_run_carry = {leader_sim.sim_info, sim.sim_info}
                leader_sim.waiting_for_carry_fixup = True
                sim.waiting_for_carry_fixup = True
                run_fixup_carryable_sims(sims_to_run_carry=sims_to_run_carry, clear_mixer_cache_on_fixup=True, on_fixup_complete=_on_carry_fixup_finished)
            else:
                _on_carry_fixup_finished()

        def _on_spawn_leader(sim):
            SimSpawner.spawn_sim(services.sim_info_manager().get(self.guest_supervised_id), spawn_action=_on_spawn_supervised, sim_spawner_tags=self.default_job().sim_spawner_tags)

        if self.guest_supervised_id != -1:
            SimSpawner.spawn_sim(services.sim_info_manager().get(self.guest_id), spawn_action=_on_spawn_leader, sim_spawner_tags=self.default_job().sim_spawner_tags)
        super().start_situation()
        self._change_state(self.consider_visit_state())

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=self.business_owner_info.sim_id)
        if business_manager is None or not business_manager.is_open:
            situation_manager = services.get_zone_situation_manager()
            situation_manager.make_sim_leave_now_must_run(sim)
            return
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=None)
        if sim.id == self.guest_id and self.adult_guest_stays_on_lot:
            self._satisfaction_logic = SmallBusinessCustomerSatisfaction()
            self._satisfaction_logic.start(sim, business_manager.customer_rules, self.satisfaction_waiting_timers, self.satisfaction_activity_timer, self.satisfaction_waiting_ratios_rewards, self.satisfaction_start_waiting_ratio, self.satisfaction_interaction_counter_rewards, self.satisfaction_markup_ratios_rewards, self.satisfaction_markup_ratio_per_payment_type, self.satisfaction_markup_ratio_per_markup_value, self._seed.custom_init_params_reader, self.guest_id)
        elif sim.id == self.guest_supervised_id:
            self._satisfaction_logic_supervised = SmallBusinessCustomerSatisfaction()
            self._satisfaction_logic_supervised.start(sim, business_manager.customer_rules, self.satisfaction_waiting_timers, self.satisfaction_activity_timer, self.satisfaction_waiting_ratios_rewards, self.satisfaction_start_waiting_ratio, self.satisfaction_interaction_counter_rewards, self.satisfaction_markup_ratios_rewards, self.satisfaction_markup_ratio_per_payment_type, self.satisfaction_markup_ratio_per_markup_value, self._seed.custom_init_params_reader, self.guest_supervised_id)
        if self.encouragement_buff:
            self.add_as_business_customer(sim)
        if business_manager.small_business_income_data is not None:
            business_manager.small_business_income_data.start_interaction_sales_markup_tracking_for_sim(sim.sim_id)

    def _on_business_closed(self):
        self._cleanup_small_business_situation()
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone()
        if self.guest_supervised_id != -1:
            is_held = False
            if self.guest_id != -1:
                sim = services.sim_info_manager().get(self.guest_id).get_sim_instance()
                if sim is not None:
                    for (_, _, carried_object) in get_carried_objects_gen(sim):
                        if carried_object.id == self.guest_supervised_id:
                            self._change_state(self.leave_state())
                            is_held = True
                            break
            if not is_held:
                self._change_state(self.say_goodbye_state())
        else:
            self._change_state(self.leave_state())
        if business_manager is not None:
            for sim in self.all_sims_in_situation_gen():
                self.unregister_customer(sim.sim_info)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if sim.id == self.guest_id and self._satisfaction_logic:
            self._satisfaction_logic.end()
        elif sim.id == self.guest_supervised_id and self._satisfaction_logic_supervised:
            self._satisfaction_logic_supervised.end()
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=self.business_owner_info.sim_id)
        if business_manager is not None:
            self.unregister_customer(sim.sim_info)
            if business_manager.small_business_income_data is not None:
                business_manager.small_business_income_data.stop_interaction_sales_markup_tracking_for_sim(sim.sim_id)
        if sim.is_being_destroyed and sim.id == self.guest_id and self.guest_supervised_id != -1:
            self._change_state(self.say_goodbye_state())
        if len(self._situation_sims) == 0:
            self._self_destruct()

    def set_small_business_customer_situation_state(self, new_situation_state):
        if new_situation_state == SmallBusinessCustomerStates.DELIBERATE:
            self._change_state(self.consider_visit_state())
        elif new_situation_state == SmallBusinessCustomerStates.CHECK_IN:
            self._change_state(self.check_in_state())
        elif new_situation_state == SmallBusinessCustomerStates.BUSINESS_VISIT:
            self._change_state(self.put_down_state())
        elif new_situation_state == SmallBusinessCustomerStates.CHECK_OUT:
            self._change_state(self.check_out_state())
        elif new_situation_state == SmallBusinessCustomerStates.LEAVE:
            self._change_state(self.leave_state())

    def get_visualizer_data_string(self, visualizer_data:'SimVisualizerData') -> 'string':
        result = ''
        if self._satisfaction_logic is not None:
            if visualizer_data == SimVisualizerData.SATISFACTION_PERFORM_INTERACTION:
                result += str(self._satisfaction_logic.get_is_performing_interaction()) + ' '
            elif visualizer_data == SimVisualizerData.SATISFACTION_WAIT_RATIO:
                result += str(round(self._satisfaction_logic.get_wait_ratio(), 2)) + ' '
            elif visualizer_data == SimVisualizerData.SATISFACTION_INDEX_WAIT_RATIO:
                result += str(self._satisfaction_logic.get_current_index_waiting_ratio()) + ' '
            elif visualizer_data == SimVisualizerData.SATISFACTION_INTERACTION_COUNTER:
                result += str(self._satisfaction_logic.get_interaction_count()) + ' '
            elif visualizer_data == SimVisualizerData.SATISFACTION_MARKUP_RATIO:
                result += str(self._satisfaction_logic.get_current_markup_ratio()) + ' '
        if self._satisfaction_logic_supervised is not None:
            if visualizer_data == SimVisualizerData.SATISFACTION_PERFORM_INTERACTION:
                result += str(self._satisfaction_logic_supervised.get_is_performing_interaction())
            elif visualizer_data == SimVisualizerData.SATISFACTION_WAIT_RATIO:
                result += str(round(self._satisfaction_logic_supervised.get_wait_ratio(), 2))
            elif visualizer_data == SimVisualizerData.SATISFACTION_INDEX_WAIT_RATIO:
                result += str(self._satisfaction_logic_supervised.get_current_index_waiting_ratio())
            elif visualizer_data == SimVisualizerData.SATISFACTION_INTERACTION_COUNTER:
                result += str(self._satisfaction_logic_supervised.get_interaction_count())
            elif visualizer_data == SimVisualizerData.SATISFACTION_MARKUP_RATIO:
                result += str(self._satisfaction_logic_supervised.get_current_markup_ratio())
        return result

    def _get_business_reputation_sim_filter(self, owner_info):
        statistic_type = SmallBusinessTunables.SMALL_BUSINESS_REPUTATION_RANKED_STATISTIC
        if statistic_type is None:
            return
        elif owner_info is not None:
            statistic = owner_info.commodity_tracker.get_statistic(statistic_type, add=True)
            if statistic is not None:
                reputation_level = statistic.get_user_value() + 1
                reputation_filter = SmallBusinessTunables.SMALL_BUSINESS_CUSTOMER_REPUTATION_FILTER
                if reputation_level in reputation_filter:
                    return reputation_filter[reputation_level]
                else:
                    return
        return

    def pick_up_dependent(self) -> 'bool':
        if self.guest_supervised_id != -1:
            (caregiver_sim, carried_sim) = (None, None)
            for sim in self.all_sims_in_situation_gen():
                if sim.sim_id == self.guest_id:
                    for (_, _, carried_object) in get_carried_objects_gen(sim):
                        if carried_object and carried_object.id == self.guest_supervised_id:
                            return True
                    caregiver_sim = sim
                else:
                    resolver = SingleSimResolver(sim.sim_info)
                    carryable_sim_eligibility_tests = CarryTuning.CARRYABLE_SIMS_FIXUP_RULES.carryable_sim_eligibility_tests
                    if carryable_sim_eligibility_tests.run_tests(resolver):
                        carried_sim = sim
            if carried_sim is None or caregiver_sim is None:
                return False
            context = InteractionContext(caregiver_sim, InteractionContext.SOURCE_SCRIPT, Priority.High, carry_target=carried_sim)
            for affordance in self.pick_up_affordances:
                if not affordance.is_affordance_available(context=context):
                    pass
                elif not affordance.test(target=carried_sim, context=context):
                    pass
                else:
                    caregiver_sim.push_super_affordance(affordance, carried_sim, context)
                    return True
        return False

    def can_switch_state(self, sim_info:'SimInfo', switch_next_state_tests) -> 'Optional[TunableSimMinute]':
        if not switch_next_state_tests:
            return
        resolver = SingleSimResolver(sim_info)
        for element in switch_next_state_tests:
            test = element.test
            time_to_add = element.time_to_add
            if not test.run_tests(resolver):
                return time_to_add
