import servicesfrom sims4.resources import Typesfrom interactions.base.picker_interaction import PickerSuperInteractionfrom objects.components.state_references import TunableStateTypeReference, TunableStateValueReferencefrom sims4.tuning.tunable import TunableTuple, TunableMapping, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import GridPickerRow
class SkillStatePickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'skills_states': TunableMapping(description='\n            List of all skills and their statuses that can be taught in a hobby class.\n            ', key_type=TunableReference(description='\n                    Skills that can be taught from a hobby class.\n                    ', manager=services.get_instance_manager(Types.STATISTIC), class_restrictions=('Skill',), pack_safe=True), value_type=TunableTuple(state=TunableStateTypeReference(description='\n                    The state of the skill to know if it is on or off to be taught.\n                    ', pack_safe=True), enabled_state_value=TunableStateValueReference(description='\n                    State value that target object will be changed to if skill is selected.\n                    ', pack_safe=True), disabled_state_value=TunableStateValueReference(description='\n                    State value that target object will be changed to if skill is unselected.\n                    ', pack_safe=True)), tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        for (skill, skill_state) in cls.skills_states.items():
            is_selected = False
            is_selected = True
            sim_skill = inst.sim.sim_info.get_statistic(skill, add=False)
            sim_skill_level = 0
            sim_skill_level = sim_skill.get_user_value()
            row = GridPickerRow(name=skill.stat_name, icon=skill.icon, row_description=skill.skill_description(context.sim), tag=skill, option_id=skill.guid64, is_selected=is_selected, skill_level=sim_skill_level)
            yield row

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        for (skill, skill_state) in self.skills_states.items():
            for picked_skill in picked_choice:
                if picked_skill == skill:
                    self.target.set_state(skill_state.state, skill_state.enabled_state_value)
                    break
            self.target.set_state(skill_state.state, skill_state.disabled_state_value)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True
