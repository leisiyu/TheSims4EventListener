from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from date_and_time import TimeSpan, create_time_spanfrom sims4.tuning.tunable import TunableList, TunableTuplefrom situations.situation import Situationfrom situations.tunable import TunableSituationPhase, TunableSituationConditionimport alarmsimport clockimport interactions.utils.exit_condition_managerimport servicesimport sims4.loglogger = sims4.log.Logger('Situations')
class SituationSimple(Situation):
    INSTANCE_TUNABLES = {'_phases': TunableList(tunable=TunableSituationPhase(description='\n                    Situation reference.\n                    ')), '_exit_conditions': TunableList(description='\n                A list of condition groups of which if any are satisfied, the group is satisfied.\n                ', tunable=TunableTuple(conditions=TunableList(description='\n                        A list of conditions that all must be satisfied for the\n                        group to be considered satisfied.\n                        ', tunable=TunableSituationCondition(description='\n                            A condition for a situation or single phase.\n                            '))))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._phase = None
        self._phase_index = -1
        self._exit_condition_manager = interactions.utils.exit_condition_manager.ConditionalActionManager()
        self._phase_exit_condition_manager = interactions.utils.exit_condition_manager.ConditionalActionManager()
        self._phase_duration_alarm_handle = None

    def _destroy(self):
        self._remove_exit_conditions()
        self._remove_phase_exit_conditions()
        super()._destroy()

    def _initialize_situation_jobs(self):
        super()._initialize_situation_jobs()
        initial_phase = self.get_initial_phase_type()
        for job_tuning in initial_phase.jobs_gen():
            self._add_job_type(job_tuning[0], job_tuning[1])

    def start_situation(self):
        super().start_situation()
        self._attach_exit_conditions()
        self._transition_to_next_phase()

    def _load_situation_states_and_phases(self):
        super()._load_situation_states_and_phases()
        self._attach_exit_conditions()
        self._load_phase()

    def _save_custom(self, seed):
        super()._save_custom(seed)
        remaining_time = TimeSpan.ZERO if self._phase_duration_alarm_handle is None else self._phase_duration_alarm_handle.get_remaining_time()
        seed.add_situation_simple_data(self._phase_index, remaining_time)
        return seed

    @classmethod
    def should_load_after_time_jump(cls, seed):
        elapsed_time = create_time_span(minutes=services.current_zone().time_elapsed_since_last_save().in_minutes())
        if seed.duration_override is not None and elapsed_time > seed.duration_override:
            return False
        seed.duration_override -= elapsed_time
        return True

    def on_time_jump(self):
        elapsed_time = services.current_zone().time_elapsed_since_last_save()
        while True:
            if self._phase_duration_alarm_handle is None:
                break
            phase_duration = self._phase_duration_alarm_handle.get_remaining_time()
            if elapsed_time > phase_duration:
                elapsed_time -= phase_duration
                self._transition_to_next_phase()
            else:
                phase_duration -= elapsed_time
                self._remove_phase_exit_conditions()
                self._attach_phase_exit_conditions(duration_override=phase_duration)
                break
        return True

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if len(cls._phases) == 0:
            logger.error('Simple Situation {} has no tuned phases.', cls, owner='sscholl')
        if cls._phases[len(cls._phases) - 1].get_duration() != TimeSpan.ZERO:
            logger.error('Situation {} last phase does not have a duration of 0.', cls, owner='sscholl')

    @classmethod
    def get_tuned_jobs(cls):
        job_list = []
        initial_phase = cls.get_initial_phase_type()
        for job in initial_phase.jobs_gen():
            job_list.append(job[0])
        return job_list

    @classmethod
    def get_initial_phase_type(cls):
        return cls._phases[0]

    @classmethod
    def get_phase(cls, index):
        if cls._phases == None or index >= len(cls._phases):
            return
        return cls._phases[index]

    def _transition_to_next_phase(self, conditional_action=None):
        new_index = self._phase_index + 1
        new_phase = self.get_phase(new_index)
        logger.debug('Transitioning from phase {} to phase {}', self._phase_index, new_index)
        self._remove_phase_exit_conditions()
        self._phase_index = new_index
        self._phase = new_phase
        self._attach_phase_exit_conditions()
        for (job_type, role_state_type) in new_phase.jobs_gen():
            self._set_job_role_state(job_type, role_state_type)
        client = services.client_manager().get_first_client()
        if client:
            output = sims4.commands.AutomationOutput(client.id)
            if output:
                output('SituationPhaseTransition; Phase:{}'.format(new_index))

    def _load_phase(self):
        seedling = self._seed.situation_simple_seedling
        logger.debug('Loading phase {}', seedling.phase_index)
        self._phase_index = seedling.phase_index
        self._phase = self.get_phase(self._phase_index)
        self._attach_phase_exit_conditions(seedling.remaining_phase_time)

    def get_phase_state_name_for_gsi(self):
        return str(self._phase_index)

    def _attach_phase_exit_conditions(self, duration_override:'Optional[TimeSpan]'=None) -> 'None':
        self._phase_exit_condition_manager.attach_conditions(self, self._phase.exit_conditions_gen(), self._transition_to_next_phase)
        duration = duration_override if duration_override is not None else self._phase.get_duration()
        if duration != TimeSpan.ZERO:
            self._phase_duration_alarm_handle = alarms.add_alarm(self, duration, self._transition_to_next_phase)

    def _remove_phase_exit_conditions(self):
        self._phase_exit_condition_manager.detach_conditions(self)
        if self._phase_duration_alarm_handle is not None:
            alarms.cancel_alarm(self._phase_duration_alarm_handle)
            self._phase_duration_alarm_handle = None

    def _attach_exit_conditions(self):
        self._remove_exit_conditions()
        self._exit_condition_manager.attach_conditions(self, self.exit_conditions_gen(), self._situation_ended_callback)

    def _remove_exit_conditions(self):
        self._exit_condition_manager.detach_conditions(self)

    def exit_conditions_gen(self):
        for ec in self._exit_conditions:
            yield ec

    def _situation_ended_callback(self, conditional_action=None):
        logger.debug('Situation exit condition met: {}', self)
        self._self_destruct()
