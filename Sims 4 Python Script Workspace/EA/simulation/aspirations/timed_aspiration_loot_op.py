import enumimport servicesimport sims4import randomfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunablePackSafeReference, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableList, TunableReference, TunableRange, TunableEnumEntryfrom protocolbuffers import Sims_pb2logger = sims4.log.Logger('Aspirations', default_owner='yecao')
class AddObjectiveActionType(enum.Int):
    INITIAL_ADD = 0
    OBJECTIVE_UPDATE = 1

class _AddObjectiveList(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'objectives': TunableList(description='\n            A list of objectives that can be added to the Timed Aspiration.\n            ', tunable=TunableReference(description='\n                    An objective to add.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True)), 'number_to_add': TunableRange(description='\n            Number of objectives that will be added to Timed Aspiration, \n            objectives will be selected randomly from the list.\n            ', tunable_type=int, default=1, minimum=1), 'add_objective_action_type': TunableEnumEntry(description='\n            Action type for the add operation. \n            Choose InitialAdd if we want the objectives to be added to the TimedAspiration immediately \n            at the start of the timed aspiration.\n            Choose ObjectiveUpdate if the objective is added from completion loot of the previous objective \n            and needed to wait for the completion animation to be finished.\n            ', tunable_type=AddObjectiveActionType, default=AddObjectiveActionType.OBJECTIVE_UPDATE)}

    def __call__(self, subject, target, source_op):
        if not self.objectives:
            return
        timed_aspiration_data = subject.aspiration_tracker.get_timed_aspiration_data(source_op.aspiration)
        if timed_aspiration_data is None:
            logger.error('{} does not have timed aspiration: {}. Sim should have the timed aspiration first to add more objectives on that aspiration.', subject, source_op.aspiration)
            return
        current_objectives = subject.aspiration_tracker.get_objectives(source_op.aspiration)
        new_objectives_list = list(self.objectives)
        random.shuffle(new_objectives_list)
        objectives_to_add = []
        if len(objectives_to_add) < self.number_to_add:
            if new_objectives_list[-1] not in current_objectives:
                objectives_to_add.append(new_objectives_list[-1])
            new_objectives_list.pop()
            if not new_objectives_list:
                break
        new_objectives = subject.aspiration_tracker.register_additional_objectives(source_op.aspiration, objectives_to_add)
        tests = [objective.objective_test for objective in new_objectives]
        services.get_event_manager().register_tests(source_op.aspiration, tests)
        subject.aspiration_tracker.process_test_events_for_aspiration(source_op.aspiration)
        if self.add_objective_action_type == AddObjectiveActionType.INITIAL_ADD:
            timed_aspiration_data.send_timed_aspiration_to_client(Sims_pb2.TimedAspirationUpdate.ADD)
        else:
            timed_aspiration_data.send_timed_aspiration_to_client(Sims_pb2.TimedAspirationUpdate.OBJECTIVE_UPDATE)

class _TimedAspirationActivate(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, subject, target, source_op):
        subject.aspiration_tracker.activate_timed_aspiration(source_op.aspiration)

class _TimedAspirationDeactivate(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, subject, target, source_op):
        subject.aspiration_tracker.deactivate_timed_aspiration(source_op.aspiration)

class TimedAspirationLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'aspiration': TunablePackSafeReference(description='\n            The timed aspiration we will do the loot op on. Only sim with active LOD will be able to\n            do the operations.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='TimedAspiration'), 'operation': TunableVariant(description='\n            Timed aspiration related operations to perform.\n            ', timed_aspiration_activate=_TimedAspirationActivate.TunableFactory(), timed_aspiration_deactivate=_TimedAspirationDeactivate.TunableFactory(), add_objective_list=_AddObjectiveList.TunableFactory(), default='timed_aspiration_activate')}

    def __init__(self, operation, aspiration, **kwargs):
        super().__init__(**kwargs)
        self.aspiration = aspiration
        self.operation = operation

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if self.aspiration is None:
            logger.error('Aspiration is not specified in TimedAspirationLootOp.')
            return
        if subject is None:
            logger.error('Timed Aspiration loot found None owner sim. subject {}. Loot: {}', self.subject, self, owner='yecao')
            return
        if subject.aspiration_tracker is None:
            logger.error('Aspiration tracker is not found for subject {}, aspiration tracker is only on sim with active LOD', subject, owner='yecao')
            return
        self.operation(subject, target, source_op=self)
