from __future__ import annotationsimport servicesimport sims4import uifrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.tunable import TunableContinuationfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableList, TunableSet, TunableReference, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from scheduling import Timeline
    from objects.game_object import GameObject
    from interactions.context import InteractionContext
    from drama_scheduler.multi_unit_drama_node import MultiUnitEventDramaNode
class ContractorPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'continuation': TunableContinuation(description='\n            If enabled, you can tune a continuation to be pushed. PickedItemId\n            will be the id of the selected event. PickedZoneId will be the zone id of the unit.\n            ', tuning_group=GroupNames.PICKERTUNING), 'is_experienced_contractor': Tunable(description='\n            if true, the picker will only generate experienced contractors. If false, the picker will \n            generate inexperienced contractors.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'picker_row_cost_description': TunableLocalizedStringFactory(description='\n            Use this name in the Picker Row to display cost of the service.\n            Tokens:\n            {0.String} cost of hiring the contractor.\n            ', tuning_group=GroupNames.PICKERTUNING), 'picker_row_tenant_location_description': TunableLocalizedStringFactory(description='\n            Use this name in the Picker Row to display the location of tenant household.\n            Tokens:\n            {0.String} Tenant Household Name\n            ', tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline:'Timeline') -> 'bool':
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'None':
        property_owner_sim = context.sim
        if property_owner_sim is None:
            return
        event_service = services.multi_unit_event_service()
        inst_or_cls = inst if inst is not None else cls
        if event_service:
            property_owner_active_events = event_service.get_current_property_owner_events()
            for (tenant_zone_id, drama_node_id) in property_owner_active_events.items():
                active_drama_node_type = services.drama_scheduler_service().get_scheduled_node_by_uid(drama_node_id)
                if not active_drama_node_type.is_emergency_type_event():
                    pass
                else:
                    household = services.household_manager().get_by_home_zone_id(tenant_zone_id)
                    display_name = active_drama_node_type.get_event_name()
                    icon = active_drama_node_type.get_icon()
                    contractor_costs = active_drama_node_type.get_contractor_costs()
                    contractor_cost = contractor_costs[0] if inst_or_cls.is_experienced_contractor else contractor_costs[1]
                    cost_description = inst_or_cls.picker_row_cost_description(str(contractor_cost))
                    tenant_location_description = inst_or_cls.picker_row_tenant_location_description(household.name)
                    row = ui.ui_dialog_picker.ObjectPickerRow(is_enable=True, icon=icon, name=display_name, row_description=tenant_location_description, rarity_text=cost_description, tag=active_drama_node_type)
                    yield row

    def on_choice_selected(self, choice_tag:'MultiUnitEventDramaNode', **kwargs):
        tag = choice_tag
        if tag is not None:
            picked_item_set = frozenset({tag.guid64})
            picked_zone_id_set = frozenset({tag.get_unit_zone_id()})
            self.interaction_parameters['picked_item_ids'] = picked_item_set
            self.interaction_parameters['picked_zone_ids'] = picked_zone_id_set
            self.push_tunable_continuation(self.continuation, picked_item_ids=picked_item_set, picked_zone_ids=picked_zone_id_set)
