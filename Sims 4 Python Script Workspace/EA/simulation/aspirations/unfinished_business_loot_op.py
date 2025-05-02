import servicesimport sims4from interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.telemetry import TelemetryWriterfrom sims4.tuning.tunable import TunableReference, HasTunableSingletonFactory, AutoFactoryInit, TunableVariantfrom aspirations.unfinished_business_aspiration_tuning import UnfinishedBusinessimport telemetry_helperTELEMETRY_GROUP_UNFINISHED_BUSINESS = 'UNBU'TELEMETRY_HOOK_OBJECTIVE_ADDED = 'GADD'TELEMETRY_HOOK_OBJECTIVE_COMPLETED = 'GCMP'unfinished_business_telemetry_writer = TelemetryWriter(TELEMETRY_GROUP_UNFINISHED_BUSINESS)
class _AddUnfinishedBusinessObjective(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'objective': TunableReference(description='\n            The objective to add to the unfinished business aspiration.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True)}

    def __call__(self, subject, target, source_op):
        if self.objective is None:
            return
        if UnfinishedBusiness.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK is None:
            return
        if subject.aspiration_tracker is None:
            return
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return
        new_objective = subject.aspiration_tracker.register_additional_objectives(unfinished_business_aspiration, [self.objective])
        test = [objective.objective_test for objective in new_objective]
        services.get_event_manager().register_tests(unfinished_business_aspiration, test)
        subject.aspiration_tracker.process_test_events_for_aspiration(unfinished_business_aspiration)
        for objective in new_objective:
            subject.aspiration_tracker.force_send_objective_update(objective)
        with telemetry_helper.begin_hook(unfinished_business_telemetry_writer, TELEMETRY_HOOK_OBJECTIVE_ADDED, False, None, subject) as hook:
            hook.write_float('sage', subject.age)
            hook.write_guid('goid', self.objective.guid)

class _RemoveUnfinishedBusinessObjective(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'objective': TunableReference(description='\n            The objective to remove to the unfinished business aspiration.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True)}

    def __call__(self, subject, target, source_op):
        if self.objective is None:
            return
        if UnfinishedBusiness.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK is None:
            return
        if subject.aspiration_tracker is None:
            return
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return
        subject.aspiration_tracker.remove_additional_objective(unfinished_business_aspiration, self.objective)
        subject.aspiration_tracker.process_test_events_for_aspiration(unfinished_business_aspiration)
        subject.aspiration_tracker.force_send_objective_update(self.objective)

class _RemoveAllUnfinishedBusinessObjectives(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, subject, target, source_op):
        if UnfinishedBusiness.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK is None:
            return
        if subject.aspiration_tracker is None:
            return
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return
        curr_objectives = list(subject.aspiration_tracker.get_additional_objectives(unfinished_business_aspiration))
        subject.aspiration_tracker.clear_additional_objectives_for_aspiration(unfinished_business_aspiration)
        subject.aspiration_tracker.process_test_events_for_aspiration(unfinished_business_aspiration)
        for objective in curr_objectives:
            subject.aspiration_tracker.force_send_objective_update(objective)

class _ClearCompletedObjectives(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, subject, target, source_op):
        if UnfinishedBusiness.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK is None:
            return
        if subject.aspiration_tracker is None:
            return
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return
        completed_objectives = subject.aspiration_tracker.completed_objectives
        curr_objectives = subject.aspiration_tracker.get_additional_objectives(unfinished_business_aspiration)
        for objective in curr_objectives:
            if objective in completed_objectives:
                subject.aspiration_tracker.remove_additional_objective(unfinished_business_aspiration, objective)
                subject.aspiration_tracker.process_test_events_for_aspiration(unfinished_business_aspiration)
                subject.aspiration_tracker.force_send_objective_update(objective)

class UnfinishedBusinessAspirationLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'operation': TunableVariant(description='\n            Timed aspiration related operations to perform.\n            ', add_objective=_AddUnfinishedBusinessObjective.TunableFactory(), remove_objective=_RemoveUnfinishedBusinessObjective.TunableFactory(), remove_all_objectives=_RemoveAllUnfinishedBusinessObjectives.TunableFactory(), clear_completed_objectives=_ClearCompletedObjectives.TunableFactory(), default='add_objective')}

    def __init__(self, operation, **kwargs):
        super().__init__(**kwargs)
        self.operation = operation

    def _apply_to_subject_and_target(self, subject, target, resolver):
        self.operation(subject, target, source_op=self)
