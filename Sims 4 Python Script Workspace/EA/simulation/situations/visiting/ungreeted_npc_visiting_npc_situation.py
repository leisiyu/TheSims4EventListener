import servicesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom situations.visiting.visiting_situation_common import VisitingNPCSituationimport sims4.tuning.tunableimport situations.bouncer.bouncer_typesimport situations.situation_complex
class UngreetedNPCVisitingNPCSituation(VisitingNPCSituation):
    INSTANCE_TUNABLES = {'ungreeted_npc_sims': sims4.tuning.tunable.TunableTuple(situation_job=sims4.tuning.tunable.TunableReference(description='\n                    The job given to NPC sims in the visiting situation.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), role_state=sims4.tuning.tunable.TunableReference(description='\n                    The role state given to NPC sims in the visiting situation.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',)), tuning_group=GroupNames.ROLES)}

    @classmethod
    def _get_greeted_status(cls):
        return situations.situation_types.GreetedStatus.WAITING_TO_BE_GREETED

    @classmethod
    def _states(cls):
        return (SituationStateData(1, UngreetedNPCVisitingNPCState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.ungreeted_npc_sims.situation_job, cls.ungreeted_npc_sims.role_state)]

    @classmethod
    def default_job(cls):
        return cls.ungreeted_npc_sims.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(UngreetedNPCVisitingNPCState())

    def _on_make_waiting_player_greeted(self, door_bell_ringing_sim):
        self._greet()

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if self.manager.is_player_greeted():
            self._greet()

    def _greet(self):
        for sim in self.all_sims_in_situation_gen():
            self.manager.create_greeted_npc_visiting_npc_situation(sim.sim_info)

    def _on_sim_removed_from_situation_prematurely(self, sim, sim_job):
        if self.num_of_sims > 0:
            return
        self._self_destruct()
lock_instance_tunables(UngreetedNPCVisitingNPCSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.UNGREETED, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)
class UngreetedNPCVisitingNPCState(situations.situation_complex.SituationState):
    pass
