import servicesimport sims4from sims4.tuning.tunable import TunableTuple, TunableReferencefrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateData
class SingleJobSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'job': TunableTuple(description='\n            The job and role which the career Sim is placed into.\n            ', situation_job=TunableReference(description='\n                A reference to a SituationJob that can be performed at this Situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), role_state=TunableReference(description='\n                A role state the Sim assigned to the job will perform.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, SingleJobSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job.situation_job, cls.job.role_state)]

    @classmethod
    def default_job(cls):
        return cls.job.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(SingleJobSituationState())

class SingleJobSituationState(SituationState):
    pass
