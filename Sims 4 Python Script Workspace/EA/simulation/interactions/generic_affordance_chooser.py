import servicesimport sims4from event_testing.results import TestResultfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom sims4.tuning.tunable import TunablePackSafeReferencefrom ui.ui_dialog import UiDialogOkCancelimport interactions
class GenericChooseBetweenTwoAffordancesSuperInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'choice_dialog': UiDialogOkCancel.TunableFactory(description='\n            A Dialog that prompts the user with a two button dialog. The\n            chosen button will result in one of two affordances being chosen.\n            '), 'accept_affordance': TunablePackSafeReference(description='\n            The affordance to push on the sim if the user clicks on the \n            accept/ok button.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',)), 'reject_affordance': TunablePackSafeReference(description='\n            The affordance to push on the Sim if the user chooses to click\n            on the reject/cancel button.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',))}

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if cls.accept_affordance is None and cls.reject_affordance is None:
            return TestResult(False, 'The accept and reject affordances are unavailable with the currently installed packs.')
        return super()._test(target, context, **interaction_parameters)

    def _run_interaction_gen(self, timeline):
        context = self.context.clone_for_sim(self.sim, insert_strategy=interactions.context.QueueInsertStrategy.LAST)
        if self.accept_affordance is None or self.reject_affordance is None:
            affordance = self.accept_affordance or self.reject_affordance
            self.sim.push_super_affordance(affordance, target=self.target, context=context)
            return

        def _on_response(dialog):
            affordance = self.accept_affordance if dialog.accepted else self.reject_affordance
            self.sim.push_super_affordance(affordance, target=self.target, context=context)

        dialog = self.choice_dialog(self.sim, resolver=self.get_resolver())
        dialog.show_dialog(on_response=_on_response)
