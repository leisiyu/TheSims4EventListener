from developmental_milestones.developmental_milestone_enums import DevelopmentalMilestoneStatesfrom developmental_milestones.developmental_milestone_tracker import MilestoneTelemetryContextfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableEnumEntry, TunablePackSafeReference, TunableList, Tunable, TunableReferenceimport servicesimport sims4.logfrom situations.situation_goal_targeted_sim import SituationGoalRelationshipChangeTargetedSimlogger = sims4.log.Logger('DevelopmentalMilestones', default_owner='miking')
class DevelopmentalMilestoneStateChangeLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'developmental_milestone': TunablePackSafeReference(description='\n            Milestone to set.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DEVELOPMENTAL_MILESTONE)), 'developmental_milestone_state': TunableEnumEntry(description="\n            The state to set on the milestone. Re-locking milestones is not supported.\n            Note that setting to state 'available' sets the milestone state but does not affect the corresponding commodity.\n            ", tunable_type=DevelopmentalMilestoneStates, default=DevelopmentalMilestoneStates.UNLOCKED, invalid_enums=(DevelopmentalMilestoneStates.LOCKED,))}

    def __init__(self, *args, developmental_milestone, developmental_milestone_state, **kwargs):
        super().__init__(*args, **kwargs)
        self._developmental_milestone = developmental_milestone
        self._developmental_milestone_state = developmental_milestone_state

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        if self._developmental_milestone is None:
            return
        tracker = subject.sim_info.developmental_milestone_tracker if subject.sim_info is not None else None
        if tracker is None:
            logger.warn('Attempting to set milestone state for {} but subject {} does not have a developmental milestone tracker.', self._developmental_milestone, subject)
            return
        if not tracker.is_milestone_valid_for_sim(self._developmental_milestone):
            logger.warn('Milestone {} is not valid for Sim {}.', self._developmental_milestone, subject)
            return
        if tracker.is_milestone_unlocked(self._developmental_milestone):
            logger.info('Milestone {} is already unlocked for Sim {}.', self._developmental_milestone, subject)
            return
        if self._developmental_milestone_state is DevelopmentalMilestoneStates.ACTIVE and tracker.is_milestone_active(self._developmental_milestone):
            logger.info('Milestone {} is already active for Sim {}.', self._developmental_milestone, subject)
            return
        tracker.recursively_unlock_prerequisites(self._developmental_milestone, telemetry_context=MilestoneTelemetryContext.LOOT)
        if not tracker.is_milestone_active(self._developmental_milestone):
            logger.warn('DevelopmentalMilestoneStateChangeLootOp loot_recursively_unlock_prerequisites did not activate milestone {}. Activating it manually.', self._developmental_milestone)
            tracker.activate_milestone(self._developmental_milestone, telemetry_context=MilestoneTelemetryContext.LOOT)
        if self._developmental_milestone_state is DevelopmentalMilestoneStates.UNLOCKED:
            tracker.unlock_milestone(self._developmental_milestone, telemetry_context=MilestoneTelemetryContext.LOOT)

class DevelopmentalMilestoneReevaluateRelationshipGoalOp(BaseLootOperation):
    FACTORY_TUNABLES = {'developmental_milestone': TunablePackSafeReference(description='\n            Milestone to set.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DEVELOPMENTAL_MILESTONE)), 'relationship_bits': TunableList(description="\n            List of relationship bits used to reevaluate if a relationship has reached the active milestone's goal.\n            ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), class_restrictions=('RelationshipBit',), pack_safe=True)), 'any_bits_in_common': Tunable(description='\n            If enabled, this will search for relationships that have any of the tuned listed bits. If disabled,\n            it will search for relationships that have ALL the tuned relationship bits in common.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, developmental_milestone, relationship_bits, any_bits_in_common, **kwargs):
        super().__init__(**kwargs)
        self.developmental_milestone = developmental_milestone
        self.relationship_bits = relationship_bits
        self.any_bits_in_common = any_bits_in_common

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        if self.developmental_milestone is None:
            return
        sim_with_bits_gen = subject.relationship_tracker.target_sim_with_bits_gen(self.relationship_bits, has_any=self.any_bits_in_common)
        milestone_tracker = subject.developmental_milestone_tracker
        if milestone_tracker is None:
            logger.warn('{} does not have a developmental milestone tracker.', subject)
            return
        for other_sim_id in sim_with_bits_gen:
            milestone_tracker.add_milestone_evaluation(self.developmental_milestone, subject, other_sim_id)
        milestone_tracker.process_evaluation(self.developmental_milestone)

    def _verify_tuning_callback(self):
        pass
