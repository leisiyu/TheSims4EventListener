import servicesimport sims4import telemetry_helperfrom aspirations.unfinished_business_aspiration_tuning import UnfinishedBusinessfrom aspirations.unfinished_business_loot_op import unfinished_business_telemetry_writer, TELEMETRY_HOOK_OBJECTIVE_ADDEDfrom event_testing.resolver import InteractionResolver, SingleSimResolverfrom interactions import ParticipantTypeSimfrom interactions.base.picker_interaction import PickerSuperInteractionfrom sims4.tuning.tunable import TunableList, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import UiItemPicker, BasePickerRowlogger = sims4.log.Logger('UnfinishedBusinessObjectivePickerInteraction')TELEMETRY_SIM_AGE = 'sage'TELEMETRY_OBJECTIVE_ID = 'goid'
class ObjectivePickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiItemPicker.TunableFactory(description='\n            The objective picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'objectives': TunableList(description='\n            A list of all of the Objectives that will be displayed in the picker.\n            ', tunable=sims4.tuning.tunable.TunableReference(description='\n                    An Objective that should be shown if it passes its tests.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.PICKERTUNING), 'picker_target': TunableEnumEntry(tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        objective_target = self.get_participant(self.picker_target)
        self._show_picker_dialog(objective_target, target_sim=objective_target)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        pass

    def on_choice_selected(self, picked_choice, **kwargs):
        pass

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        pass

class UnfinishedBusinessObjectivePickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiItemPicker.TunableFactory(description='\n            The objective picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'objectives': TunableList(description='\n            A list of all of the Objectives that will be displayed in the picker.\n            ', tunable=sims4.tuning.tunable.TunableReference(description='\n                    An Objective that should be shown if it passes its tests.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE), pack_safe=True), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.PICKERTUNING), 'picker_target': TunableEnumEntry(tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        objective_target = self.get_participant(self.picker_target)
        self._show_picker_dialog(objective_target, target_sim=objective_target)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        if target.aspiration_tracker is None:
            return
        if UnfinishedBusiness.global_unfinished_business_aspiration is None:
            logger.warn('Global Unfinished Business Aspiration tuning is missing. Verify in OE that the tuning is set.')
            return
        current_unfinished_business_objectives = target.aspiration_tracker.get_additional_objectives(UnfinishedBusiness.global_unfinished_business_aspiration)
        resolver = SingleSimResolver(target)
        for objective in cls.objectives:
            if objective in current_unfinished_business_objectives:
                pass
            elif objective in target.aspiration_tracker.completed_objectives:
                pass
            elif not objective.tests_for_picker_availability or not objective.tests_for_picker_availability.run_tests(resolver):
                pass
            else:
                row = BasePickerRow(name=objective.display_text(), row_description=objective.tooltip(), icon=objective.picker_icon, tag=objective)
                yield row

    def on_choice_selected(self, picked_choice, **kwargs):
        if picked_choice is None:
            return
        target = self.get_participant(self.picker_target)
        if target is None:
            return
        if target.aspiration_tracker is None:
            return
        unfinished_business_aspiration = UnfinishedBusiness.global_unfinished_business_aspiration
        if unfinished_business_aspiration is None:
            return
        new_objective = target.aspiration_tracker.register_additional_objectives(unfinished_business_aspiration, [picked_choice])
        test = [objective.objective_test for objective in new_objective]
        services.get_event_manager().register_tests(unfinished_business_aspiration, test)
        target.aspiration_tracker.process_test_events_for_aspiration(unfinished_business_aspiration)
        for objective in new_objective:
            target.aspiration_tracker.force_send_objective_update(objective)
            with telemetry_helper.begin_hook(unfinished_business_telemetry_writer, TELEMETRY_HOOK_OBJECTIVE_ADDED, False, sim=target) as hook:
                hook.write_float(TELEMETRY_SIM_AGE, target.age)
                hook.write_guid(TELEMETRY_OBJECTIVE_ID, objective.guid64)
