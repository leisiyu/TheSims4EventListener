import servicesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom situations.visiting.visiting_situation_common import VisitingNPCSituationimport sims4.tuning.tunableimport situations.bouncer.bouncer_typesimport situations.situation_complex
class GreetedNPCVisitingNPCSituation(VisitingNPCSituation):
    INSTANCE_TUNABLES = {'greeted_npc_sims': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                    The job given to NPC sims in the visiting situation.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), role_state=sims4.tuning.tunable.TunableReference(description='\n                    The role state given to NPC sims in the visiting situation.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GreetedNPCVisitingNPCState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.greeted_npc_sims.situation_job, cls.greeted_npc_sims.role_state)]

    @classmethod
    def default_job(cls):
        return cls.greeted_npc_sims.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(GreetedNPCVisitingNPCState())
lock_instance_tunables(GreetedNPCVisitingNPCSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.VISIT, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=True)
class GreetedNPCVisitingNPCState(situations.situation_complex.SituationState):
    pass
