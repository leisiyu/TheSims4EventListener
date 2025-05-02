from _sims4_collections import frozendictfrom _weakrefset import WeakSetfrom business.business_enums import BusinessTypefrom event_testing.resolver import DoubleSimResolver, SingleSimResolver, SingleObjectResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom objects import ALL_HIDDEN_REASONSfrom objects.components.state_references import TunableStateValueReferencefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, TunableSet, TunableTuple, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom small_business.small_business_tuning import SmallBusinessTunablesfrom tunable_multiplier import TunableMultiplierimport servicesimport sims4.resources
class CaregiverPassiveState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'locked_args': {'job_and_role_changes': frozendict()}}

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner.on_enter_passive_state()

    def _on_interaction_of_interest_complete(self, sim_info=None, **kwargs):
        self._change_state(self.owner.caregiver_active_state())

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return False
        care_dependent = self.owner.get_care_dependent_sim_info()
        if care_dependent is None:
            return False
        return sim_info is care_dependent

class CaregiverActiveState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'care_dependent_pre_tests': TunableTestSet(description='\n            Tests on the care dependent that must pass to enter the active state.\n            This is mainly used to check whether the dependent still needs any active care.\n            \n            This uses Single Sim Resolver for infant/toddler and Single Object Resolver\n            for baby bassinet.\n            '), 'caregiver_tests': TunableTestSet(description='\n            A test that will run against all caregiver candidates to pick the\n            appropriate active caregiver.\n            \n            This uses a Double Sim Resolver (caregiver, care_dependent)\n            '), 'caregiver_preference_multiplier': TunableMultiplier.TunableFactory(description='\n            A multiplier to apply scores onto caregiver candidates so to pick one\n            preferred active caregiver.\n            \n            This uses a Double Sim Resolver (caregiver, care_dependent)\n            '), 'locked_args': {'job_and_role_changes': frozendict()}}

    def __init__(self, *args, care_dependent_pre_tests=None, caregiver_tests=None, caregiver_preference_multiplier=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._care_dependent_pre_tests = care_dependent_pre_tests
        self._caregiver_tests = caregiver_tests
        self._caregiver_preference_multiplier = caregiver_preference_multiplier

    def on_activate(self, reader=None):
        self.owner.on_enter_active_state(self._care_dependent_pre_tests, self._caregiver_tests, self._caregiver_preference_multiplier)
        super().on_activate(reader)

    def _set_job_role_state(self):
        pass

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return False
        care_dependent = self.owner.get_care_dependent_sim_info()
        if care_dependent is None:
            return False
        if resolver is None or (resolver.interaction is None or resolver.interaction.target is None) or not resolver.interaction.target.is_sim:
            return False
        return resolver.interaction.target.sim_info is care_dependent

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.caregiver_passive_state())

    def timer_expired(self):
        super().timer_expired()
        self._change_state(self.owner.caregiver_active_waiting_state())

class CaregiverActiveWaitingState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'locked_args': {'job_and_role_changes': frozendict()}}

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner.set_all_caregivers_to_passive()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.caregiver_passive_state())

    def timer_expired(self):
        super().timer_expired()
        self._change_state(self.owner.caregiver_active_state())

class CaregiverSituation(SituationComplexCommon):
    CAREGIVER_EVENTS = (TestEvent.SituationStarted, TestEvent.AvailableDaycareSimsChanged)
    INSTANCE_TUNABLES = {'caregiver_passive_job_and_role_states': TunableSituationJobAndRoleState(description='\n            The job and role assigned to passive caregivers.\n            ', tuning_group=GroupNames.ROLES), 'caregiver_active_job_and_role_states': TunableSituationJobAndRoleState(description='\n            The job and role assigned to active caregivers.\n            ', tuning_group=GroupNames.ROLES), 'caregiver_passive_state': CaregiverPassiveState.TunableFactory(tuning_group=GroupNames.STATE), 'caregiver_active_state': CaregiverActiveState.TunableFactory(tuning_group=GroupNames.STATE), 'caregiver_active_waiting_state': CaregiverActiveWaitingState.TunableFactory(tuning_group=GroupNames.STATE), 'caregiver_data': TunableTuple(description='\n            The relationship bits to apply to Sims.\n            ', caregiver_bit=TunableReference(description="\n                The bit that is applied to Sims that are the situation owner's\n                Sim's caregiver. This is, for example, a bit on an adult\n                targeting a toddler.\n                ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), care_dependent_bit=TunableReference(description='\n                The bit that is applied to Sims that are the situation owner\n                This is, for example, a bit on a toddler targeting an adult.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT))), 'caregiver_relationships': TunableSet(description='\n            A list of bits that make Sims primary caregivers. If any Sim with\n            any of these bits is instantiated and living in the same household \n            as the care dependent, they are considered caregivers.\n            \n            If no primary caregiver exists, and no caregiver service exists,\n            active TYAE Sims are made caregivers.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_caregivers = WeakSet()

    @classproperty
    def is_newborn_situation(cls):
        return False

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(0, CaregiverPassiveState), SituationStateData(1, CaregiverActiveState), SituationStateData(2, CaregiverActiveWaitingState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return ((cls.caregiver_passive_job_and_role_states.job, cls.caregiver_passive_job_and_role_states.role_state), (cls.caregiver_active_job_and_role_states.job, cls.caregiver_active_job_and_role_states.role_state))

    def get_care_dependent_sim_info(self):
        if self._guest_list.host_sim is None:
            return
        if self.is_newborn_situation:
            if self._guest_list.host_sim.sim_info.household is None:
                return
        else:
            if self._guest_list.host_sim.household is None:
                return
            if self._guest_list.host_sim.is_being_destroyed:
                return
        return self._guest_list.host_sim.sim_info

    def set_all_caregivers_to_passive(self):
        for situation_sim in self.all_sims_in_situation_gen():
            if self.sim_has_job(situation_sim, self.caregiver_active_job_and_role_states.job):
                self._set_job_for_sim(situation_sim, self.caregiver_passive_job_and_role_states.job)

    def on_enter_passive_state(self):
        self._update_caregiver_status()
        self.set_all_caregivers_to_passive()

    def on_enter_active_state(self, care_dependent_pre_tests, caregiver_tests, caregiver_preference_multiplier):
        care_dependent = self.get_care_dependent_sim_info()
        if care_dependent is None:
            return
        if self.is_newborn_situation:
            resolver = SingleObjectResolver(self._guest_list.host_sim)
        else:
            resolver = SingleSimResolver(care_dependent)
        if not care_dependent_pre_tests.run_tests(resolver):
            self._change_state(self.caregiver_passive_state())
            return
        self._update_caregiver_status()
        active_caregiver_candidates = []
        for caregiver in tuple(self.all_sims_in_situation_gen()):
            if caregiver.is_being_destroyed:
                pass
            else:
                resolver = DoubleSimResolver(caregiver.sim_info, care_dependent)
                if caregiver_tests.run_tests(resolver):
                    active_caregiver_candidates.append((caregiver_preference_multiplier.get_multiplier(resolver), caregiver))
        if not active_caregiver_candidates:
            self._change_state(self.caregiver_active_waiting_state())
            return
        active_caregiver = sims4.random.weighted_random_item(active_caregiver_candidates)
        self._set_job_for_sim(active_caregiver, self.caregiver_active_job_and_role_states.job)

    def _is_valid_caregiver(self, care_dependent, caregiver, ignore_zone=False, require_bit=True):
        if ignore_zone or care_dependent.zone_id != caregiver.zone_id:
            return False
        if caregiver.is_toddler_or_younger:
            return False
        if caregiver.is_pet:
            return False
        business_manager = services.business_service().get_business_manager_for_zone(services.current_zone_id())
        if business_manager and business_manager.owner_sim_id == caregiver.sim_id and business_manager.business_type == BusinessType.SMALL_BUSINESS:
            return True
        if business_manager and business_manager.business_type == BusinessType.SMALL_BUSINESS and not business_manager.dependents_supervised:
            sim = caregiver.get_sim_instance()
            customer_situations = services.get_zone_situation_manager().get_situations_sim_is_in_by_tag(sim, SmallBusinessTunables.SMALL_BUSINESS_VISIT_ROLE_TAG)
            if customer_situations:
                return False
        if care_dependent.is_in_travel_group():
            if care_dependent.vacation_or_home_zone_id == caregiver.vacation_or_home_zone_id and require_bit and any(caregiver.relationship_tracker.has_bit(care_dependent.sim_id, rel_bit) for rel_bit in self.caregiver_relationships):
                return True
            else:
                daycare_service = services.daycare_service()
                if daycare_service is not None and daycare_service.is_daycare_service_npc_available(sim_info=caregiver, household=care_dependent.household):
                    return True
        elif care_dependent.household_id == caregiver.household_id and any(caregiver.relationship_tracker.has_bit(care_dependent.sim_id, rel_bit) for rel_bit in self.caregiver_relationships):
            return True
        else:
            daycare_service = services.daycare_service()
            if daycare_service is not None and daycare_service.is_daycare_service_npc_available(sim_info=caregiver, household=care_dependent.household):
                return True
        daycare_service = services.daycare_service()
        if daycare_service is not None and daycare_service.is_daycare_service_npc_available(sim_info=caregiver, household=care_dependent.household):
            return True
        return False

    def _update_caregiver_status(self):
        care_dependent = self.get_care_dependent_sim_info()
        if care_dependent is None:
            return
        available_sims = tuple(sim_info for sim_info in services.daycare_service().get_available_sims_gen())
        current_caregivers = set(self._situation_sims)
        for sim in current_caregivers:
            self._pending_caregivers.discard(sim)
        eligible_caregivers = set(sim_info for sim_info in available_sims if self._is_valid_caregiver(care_dependent, sim_info))
        if care_dependent.is_in_travel_group():
            eligible_caregivers = set(sim_info for sim_info in available_sims if self._is_valid_caregiver(care_dependent, sim_info, require_bit=False))
        if not (eligible_caregivers or eligible_caregivers):
            eligible_caregivers = set(sim_info for sim_info in care_dependent.household.caretaker_sim_info_gen() if sim_info in available_sims)
        for sim in self._pending_caregivers:
            eligible_caregivers.discard(sim.sim_info)
        for potential_caregiver in tuple(eligible_caregivers):
            sim = potential_caregiver.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is None or sim.is_being_destroyed:
                eligible_caregivers.discard(potential_caregiver)
            elif sim in current_caregivers:
                pass
            else:
                self.invite_sim_to_job(sim, job=self.caregiver_passive_job_and_role_states.job)
                self._pending_caregivers.add(sim)
                care_dependent.relationship_tracker.add_relationship_bit(potential_caregiver.sim_id, self.caregiver_data.care_dependent_bit)
                potential_caregiver.relationship_tracker.add_relationship_bit(care_dependent.sim_id, self.caregiver_data.caregiver_bit)
        for sim in tuple(current_caregivers):
            if sim.sim_info not in eligible_caregivers:
                self._remove_caregiver_rel_bits(care_dependent, sim.sim_info)
                self.remove_sim_from_situation(sim)
                current_caregivers.discard(sim)

    def _remove_caregiver_rel_bits(self, care_dependent, other_sim_info=None):
        if care_dependent is None:
            return
        if other_sim_info is not None:
            care_dependent.relationship_tracker.remove_relationship_bit(other_sim_info.id, self.caregiver_data.care_dependent_bit)
            other_sim_info.relationship_tracker.remove_relationship_bit(care_dependent.id, self.caregiver_data.caregiver_bit)
        else:
            for relationship in care_dependent.relationship_tracker:
                other_sim_id = relationship.get_other_sim_id(care_dependent.sim_id)
                relationship.remove_bit(care_dependent.sim_id, other_sim_id, self.caregiver_data.care_dependent_bit)
                relationship.remove_bit(other_sim_id, care_dependent.sim_id, self.caregiver_data.caregiver_bit)

    def get_care_dependent_if_last_caregiver(self, sim_info, excluding_interaction_types=None):
        care_dependent = self._guest_list.host_sim
        if care_dependent is None:
            return
        if care_dependent.household.home_zone_id == services.current_zone_id():
            return
        if not care_dependent.relationship_tracker.has_relationship(sim_info.id):
            return
        for relationship in care_dependent.relationship_tracker:
            if relationship.get_other_sim_info(care_dependent.sim_id) is sim_info:
                if not relationship.has_bit(care_dependent.sim_id, self.caregiver_data.care_dependent_bit):
                    return
                    if relationship.has_bit(care_dependent.sim_id, self.caregiver_data.care_dependent_bit):
                        if excluding_interaction_types is not None:
                            other_sim = relationship.get_other_sim(care_dependent.sim_id)
                            if other_sim is None:
                                pass
                            elif other_sim.has_any_interaction_running_or_queued_of_types(excluding_interaction_types):
                                pass
                            else:
                                return
                        else:
                            return
            elif relationship.has_bit(care_dependent.sim_id, self.caregiver_data.care_dependent_bit):
                if excluding_interaction_types is not None:
                    other_sim = relationship.get_other_sim(care_dependent.sim_id)
                    if other_sim is None:
                        pass
                    elif other_sim.has_any_interaction_running_or_queued_of_types(excluding_interaction_types):
                        pass
                    else:
                        return
                else:
                    return
        return care_dependent

    def start_situation(self):
        self._change_state(self.caregiver_passive_state())
        services.get_event_manager().register(self, self.CAREGIVER_EVENTS)
        return super().start_situation()

    def _destroy(self):
        services.get_event_manager().unregister(self, self.CAREGIVER_EVENTS)
        care_dependent = self._guest_list.host_sim
        self._remove_caregiver_rel_bits(care_dependent)
        super()._destroy()

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event in self.CAREGIVER_EVENTS:
            self._update_caregiver_status()

    def get_target_object(self):
        return self._guest_list.host_sim
lock_instance_tunables(CaregiverSituation, exclusivity=BouncerExclusivityCategory.CAREGIVER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)
class CaregiverNewbornStateMixin:
    FACTORY_TUNABLES = {'newborn_object_state_value_of_interest': TunableList(description='\n            On newborn object (bassinet) entering these object state values, the situation will \n            change to the next appropriate situation state.\n            ', tunable=TunableStateValueReference(pack_safe=True))}

    def __init__(self, *args, newborn_object_state_value_of_interest=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._newborn_object_state_value_of_interest = newborn_object_state_value_of_interest

    def on_activate(self, reader=None):
        for state_value in self._newborn_object_state_value_of_interest:
            self._test_event_register(TestEvent.NewbornStateChanged, custom_key=state_value.guid64)
        super().on_activate(reader)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return False
        care_dependent = self.owner.get_care_dependent_sim_info()
        if care_dependent is None:
            return False
        return sim_info is care_dependent

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.NewbornStateChanged and self._additional_tests(sim_info, event, resolver):
            self._on_interaction_of_interest_complete(sim_info=sim_info, resolver=resolver)

class CaregiverNewbornPassiveState(CaregiverNewbornStateMixin, CaregiverPassiveState):
    pass

class CaregiverNewbornActiveState(CaregiverNewbornStateMixin, CaregiverActiveState):
    pass

class CaregiverNewbornSituation(CaregiverSituation):
    INSTANCE_TUNABLES = {'caregiver_passive_state': CaregiverNewbornPassiveState.TunableFactory(tuning_group=GroupNames.STATE), 'caregiver_active_state': CaregiverNewbornActiveState.TunableFactory(tuning_group=GroupNames.STATE)}

    @classproperty
    def is_newborn_situation(cls):
        return True

    @classmethod
    def _states(cls):
        return (SituationStateData(0, CaregiverNewbornPassiveState), SituationStateData(1, CaregiverNewbornActiveState), SituationStateData(2, CaregiverActiveWaitingState))
