from distributor.ops import SwitchActiveHouseholdControlfrom distributor.system import Distributorfrom interactions import ParticipantTypeSingleObjectfrom interactions.base.picker_interaction import PickerSuperInteractionMixinfrom interactions.base.super_interaction import SuperInteractionfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumFlagsfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import SimPickerRow, UiSimPickerimport servicesimport sims4.loglogger = sims4.log.Logger('SwitchActiveHouseholdControlPicker', default_owner='yecao')
class SwitchActiveHouseholdControlPickerInteraction(PickerSuperInteractionMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiSimPicker.TunableFactory(description='\n            The switch active household control picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'participant_type': TunableEnumFlags(description='\n            The Participant we should find the household from.\n            ', enum_type=ParticipantTypeSingleObject, default=ParticipantTypeSingleObject.Object)}

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if cls._get_valid_sim_info_choices(target, context):
            return True
        return False

    def _run_interaction_gen(self, timeline):
        sim_info = self._check_sim_location()
        if not sim_info:
            self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        else:
            self._do_switch_operation(sim_info)
        return True

    def _check_sim_location(self):
        valid_sim_choices = self._get_valid_sim_info_choices(self.target, self.context)
        first_sim_info = valid_sim_choices[0]
        if len(valid_sim_choices) < 2:
            return first_sim_info
        previous_sim_zone_id = first_sim_info.zone_id
        for sim_info in valid_sim_choices[1:len(valid_sim_choices)]:
            if previous_sim_zone_id != sim_info.zone_id:
                return False
            previous_sim_zone_id = sim_info.zone_id
        return first_sim_info

    @flexmethod
    def _get_valid_sim_info_choices(cls, inst, target, context):
        inst_or_cls = inst if inst is not None else cls
        resolver = inst_or_cls.get_resolver(target, context)
        if inst_or_cls.participant_type is None:
            logger.error('Need to set participant type in tuning for {}.', inst_or_cls)
            return
        target_object = resolver.get_participant(inst_or_cls.participant_type)
        if target_object is None:
            logger.error('Unable to retrieve participant object for switch active household with participant type {}.', inst_or_cls.participant_type)
            return
        household_id = target_object.get_household_owner_id()
        household = services.household_manager().get(household_id)
        if household is None or len(household.sim_infos) == 0:
            return
        else:
            valid_sim_info_list = []
            for sim_info in household.sim_infos:
                if sim_info.zone_id != 0:
                    valid_sim_info_list.append(sim_info)
            if len(valid_sim_info_list) == 0:
                return
        return valid_sim_info_list

    def _do_switch_operation(self, sim_info):
        persistent_service = services.get_persistence_service()
        household_name = persistent_service.get_sim_proto_buff(sim_info.sim_id).household_name
        op = SwitchActiveHouseholdControl(sim_id=sim_info.sim_id, zone_id=sim_info.zone_id, household_id=sim_info.household_id, household_name=household_name)
        Distributor.instance().add_op_with_no_owner(op)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        persistence_service = services.get_persistence_service()
        inst_or_cls = inst if inst is not None else cls
        for sim_info in inst_or_cls._get_valid_sim_info_choices(target, context):
            zone_name = persistence_service.get_zone_proto_buff(sim_info.zone_id).name
            yield SimPickerRow(sim_id=sim_info.sim_id, tag=sim_info, select_default=False, sim_location=zone_name)

    def on_choice_selected(self, choice_tag, **kwargs):
        if not choice_tag:
            return
        self._do_switch_operation(choice_tag)
lock_instance_tunables(SwitchActiveHouseholdControlPickerInteraction, allow_while_save_locked=False, pie_menu_option=None)