from distributor.shared_messages import IconInfoDatafrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom sims4.resources import Typesfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableMapping, OptionalTunable, TunableTuple, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.complex.service_npc_situation import TunableFinishJobStateAndTestfrom situations.service_npcs import ServiceNpcEndWorkReasonfrom situations.situation import TunableEnumEntryfrom situations.situation_complex import CommonSituationState, TunableInteractionOfInterest, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, SituationStatefrom situations.situation_types import SituationCreationUIOptionimport event_testingimport functoolsimport servicesimport sims4logger = sims4.log.Logger('ServiceNPCCustomSituation', default_owner='mbilello')
class ServiceNPCCustomSituationStates(DynamicEnumLocked):
    DEFAULT = 0

class ServiceNPCCustomSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'transition_out_interaction': OptionalTunable(description='\n             When this interaction is run, this state can be transitioned out of;\n             we will try to advance to another state.  This can be used as a way \n             to switch states before the timeout occurs.\n             ', tunable=TunableInteractionOfInterest()), 'state_specific_transitions': TunableMapping(description='\n            Mapping to allow direct transitions to other states using interactions.\n            ', key_type=TunableEnumEntry(ServiceNPCCustomSituationStates, default=ServiceNPCCustomSituationStates.DEFAULT), value_type=TunableInteractionOfInterest()), 'locked_args': {'allow_join_situation': False}}

    def __init__(self, state_type, *args, enable_disable=None, transition_out_interaction=None, state_specific_transitions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_type = state_type
        self._transition_out_interaction = transition_out_interaction
        self._state_specific_transitions = state_specific_transitions
        self._test_custom_keys = set()
        if self._transition_out_interaction is not None:
            self._transition_out_interaction = transition_out_interaction
            self._test_custom_keys.update(self._transition_out_interaction.custom_keys_gen())
        for state_specific_transition in self._state_specific_transitions.values():
            self._test_custom_keys.update(state_specific_transition.custom_keys_gen())

    @property
    def state_type(self):
        return self._state_type

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for custom_key in self._test_custom_keys:
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        finish_job_states = self.owner.finish_job_states
        for finish_job_state in finish_job_states.values():
            for (_, custom_key) in finish_job_state.enter_state_test.get_custom_event_registration_keys():
                self._test_event_register(event_testing.test_events.TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if not self.owner.is_sim_info_in_situation(sim_info):
            target_sim_info = resolver.get_participant(ParticipantType.TargetSim)
            if target_sim_info is None or not self.owner.is_sim_info_in_situation(target_sim_info):
                return
        if event == TestEvent.InteractionComplete:
            for (state_type, state_specific_transition) in self._state_specific_transitions.items():
                if resolver(state_specific_transition):
                    self.owner.try_set_next_state(state_type)
                    return
            if self._transition_out_interaction is not None and resolver(self._transition_out_interaction):
                self.owner.try_set_next_state()
        finish_job_states = self.owner.finish_job_states
        for (finish_reason, finish_job_state) in finish_job_states.items():
            if resolver(finish_job_state.enter_state_test):
                self._change_state(LeaveSituationState(finish_reason))
                break

    def timer_expired(self):
        self.owner.try_set_next_state()

class LeaveSituationState(SituationState):

    def __init__(self, leave_role_reason=None):
        super().__init__()
        self._leave_role_reason = leave_role_reason

    def on_activate(self, reader):
        super().on_activate(reader)
        if reader is None:
            service_sim = self.owner.service_sim()
            self.owner._on_leaving_situation(self._leave_role_reason)
            if service_sim is None:
                logger.warn('Service sim is None for {}.', self)
                return
            services.get_zone_situation_manager().make_sim_leave_now_must_run(service_sim)

class ServiceNPCCustomSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_default_job': TunableSituationJobAndRoleState(description='\n                The job for the service NPC in this situation and the \n                corresponding starting role state for service Sim.\n                ', display_name='Service Npc Job'), '_default_state': ServiceNPCCustomSituationState.TunableFactory(description='\n                Default state for the service NPC, which can never be disabled.\n                ', locked_args={'state_type': ServiceNPCCustomSituationStates.DEFAULT}, tuning_group=GroupNames.SITUATION), '_managed_states': TunableMapping(description='\n            A mapping of state types to a tuple of interactions to enable and disable the state, \n            plus the buff that sets the state from the load\n            ', key_type=TunableEnumEntry(ServiceNPCCustomSituationStates, default=ServiceNPCCustomSituationStates.DEFAULT, invalid_enums=(ServiceNPCCustomSituationStates.DEFAULT,)), value_type=TunableTuple(description='\n                Tuple of interactions to enable and disable the state, \n                plus the buff that sets the state from the load\n                ', state=ServiceNPCCustomSituationState.TunableFactory(), enable_disable=OptionalTunable(description='\n                    Interactions to enable and disable the state\n                    ', display_name='Enable/Disable Support', tunable=TunableTuple(enable_interaction=TunableInteractionOfInterest(description='\n                            Interaction of interest which will cause this state to be enabled.\n                            '), disable_interaction=TunableInteractionOfInterest(description='\n                            Interaction of interest which will cause this state to be disabled.\n                            '), disabling_buff=TunableReference(description='\n                            The Buff that disables the state, used to set\n                            the state from the load.\n                            ', manager=services.get_instance_manager(Types.BUFF))))), tuning_group=GroupNames.SITUATION), 'finish_job_states': TunableMapping(description='\n            Tune pairs of job finish role states with job finish tests. When\n            those tests pass, the sim will transition to the paired role state.\n            The situation will also be transitioned to the Leaving situation\n            state.\n            ', key_type=ServiceNpcEndWorkReason, value_type=TunableFinishJobStateAndTest())}

    @classmethod
    def _states(cls):
        state_data = []
        state_index = ServiceNPCCustomSituationStates.DEFAULT.value
        state_data.append(SituationStateData(state_index, ServiceNPCCustomSituationState, factory=cls._default_state))
        for (state_type, state_tuning) in cls._managed_states.items():
            state_index = state_type.value
            state_data.append(SituationStateData(state_index, ServiceNPCCustomSituationState, factory=functools.partial(state_tuning.state, state_type)))
        state_data.append(SituationStateData(state_index + 1, LeaveSituationState, factory=cls._default_state))
        return state_data

    @classmethod
    def default_job(cls):
        return cls._default_job.job

    @classmethod
    def _state_to_uid(cls, state_to_find):
        return state_to_find.state_type.value

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._default_state._tuned_values.job_and_role_changes.items())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked_states = set()
        self._state_disabling_buffs = set()
        for (state_type, state_tuning) in self._managed_states.items():
            enable_disable = state_tuning.enable_disable
            if enable_disable is None:
                pass
            else:
                self._register_test_event_for_keys(TestEvent.InteractionComplete, enable_disable.disable_interaction.custom_keys_gen())
                self._register_test_event_for_keys(TestEvent.InteractionComplete, enable_disable.enable_interaction.custom_keys_gen())
                self._state_disabling_buffs.add(enable_disable.disabling_buff)

    def start_situation(self):
        super().start_situation()
        self._change_state(self._default_state())

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override)
        sim.Buffs.on_buff_added.append(self._updated_disabled_states)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        sim.Buffs.on_buff_added.remove(self._updated_disabled_states)

    def _updated_disabled_states(self, buff_type, sim_id):
        if buff_type not in self._state_disabling_buffs:
            return
        for (state_type, state_tuning) in self._managed_states.items():
            if state_tuning.enable_disable is None:
                pass
            elif state_tuning.enable_disable.disabling_buff == buff_type:
                self._disable_state(state_type)

    def get_employee(self):
        return next(iter(self.all_sims_in_situation_gen()), None)

    def get_employee_sim_info(self):
        employee = self.get_employee()
        if employee is None:
            return
        return employee.sim_info

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        target_sim_info = resolver.get_participant(ParticipantType.TargetSim)
        if not (target_sim_info is sim_info and self.is_sim_info_in_situation(sim_info)):
            return
        for (state_type, state_tuning) in self._managed_states.items():
            enable_disable = state_tuning.enable_disable
            if enable_disable is None:
                pass
            else:
                if resolver(enable_disable.disable_interaction):
                    self._disable_state(state_type)
                if resolver(enable_disable.enable_interaction):
                    self._enable_state(state_type)

    def try_set_next_state(self, next_state_type=None):
        if next_state_type is None or next_state_type in self._locked_states:
            next_state_type = ServiceNPCCustomSituationStates.DEFAULT
        if len(self._managed_states.keys()) > 0:
            if self._cur_state.state_type == ServiceNPCCustomSituationStates.DEFAULT:
                next_state_type = list(self._managed_states.keys())[0]
            else:
                found = False
                for state_type in self._managed_states.keys():
                    if found:
                        next_state_type = state_type
                        break
                    if self._cur_state.state_type == state_type:
                        found = True
                if next_state_type == ServiceNPCCustomSituationStates.DEFAULT:
                    next_state_type = list(self._managed_states.keys())[0]
        self._change_to_state_type(next_state_type)

    def _change_to_state_type(self, state_type):
        if state_type == ServiceNPCCustomSituationStates.DEFAULT:
            self._change_state(self._default_state())
        else:
            self._change_state(self._managed_states[state_type].state(state_type))

    def _enable_state(self, state_type):
        if state_type in self._locked_states:
            self._locked_states.remove(state_type)

    def _disable_state(self, state_type):
        self._locked_states.add(state_type)
        if self._cur_state.state_type == state_type:
            self.try_set_next_state()

    def _on_leaving_situation(self, end_work_reason):
        service_npc_type = self._service_npc_type
        household = self._hiring_household
        try:
            now = services.time_service().sim_now
            time_worked = now - self._service_start_time
            time_worked_in_hours = time_worked.in_hours()
            cost = service_npc_type.get_cost(time_worked_in_hours)
            if cost > 0:
                (paid_amount, billed_amount) = service_npc_type.try_charge_for_service(household, cost)
                if billed_amount:
                    end_work_reason = ServiceNpcEndWorkReason.NOT_PAID
            else:
                billed_amount = 0
            service_record = household.get_service_npc_record(service_npc_type.guid64)
            service_record.time_last_finished_service = now
            self._send_leave_notification(end_work_reason, paid_amount, billed_amount)
            service_sim = self.service_sim()
            if (end_work_reason == ServiceNpcEndWorkReason.FIRED or end_work_reason == ServiceNpcEndWorkReason.NOT_PAID) and service_record is not None:
                service_record.add_fired_sim(service_sim.id)
                service_record.remove_preferred_sim(service_sim.id)
                services.current_zone().service_npc_service.on_service_sim_fired(service_sim.id, service_npc_type)
            zone_id = household.home_zone_id
            travel_group = services.travel_group_manager().get_travel_group_by_zone_id(zone_id)
            if travel_group is not None:
                travel_group.object_preference_tracker.clear_sim_restriction(service_sim.id)
            household.object_preference_tracker.clear_sim_restriction(service_sim.id)
        except Exception as e:
            logger.exception('Exception while executing _on_leaving_situation for situation {}', self, exc=e)
        finally:
            services.current_zone().service_npc_service.cancel_service(household, service_npc_type)
        return end_work_reason

    def _send_leave_notification(self, end_work_reason, *localization_args):
        end_work_tuning = self.finish_job_states[end_work_reason]
        notification = end_work_tuning.notification
        if notification is None:
            return
        recipient = services.get_active_sim()
        if recipient is not None:
            dialog = notification(recipient)
            dialog.show_dialog(additional_tokens=localization_args, icon_override=IconInfoData(obj_instance=self.service_sim()))

    def get_phase_state_name_for_gsi(self):
        if self._cur_state is None:
            return 'None'
        else:
            return self._cur_state.state_type.name

    def _gsi_additional_data_gen(self):
        yield ('Locked States', str(self._locked_states))
lock_instance_tunables(ServiceNPCCustomSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, venue_situation_player_job=None)