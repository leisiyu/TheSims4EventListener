import servicesimport sims4from drama_scheduler.drama_node_types import DramaNodeTypefrom interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot import LootOperationListfrom sims4.tuning.tunable import TunableList, OptionalTunable, TunableReference, TunableTuple, TunableEnumEntryfrom tunable_utils.tunable_object_generator import TunableObjectGeneratorVariant
class LootElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'loot_list': TunableList(description='\n            A list of loot operations. This includes Loot Actions and Random Weighted Loots.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), 'object_override': OptionalTunable(description='\n            If disabled, this loot is executed once, and all participants tuned\n            in the various actions are retrieved from the owning interaction.\n            \n            If enabled, this loot is executed once for each of the generated\n            objects. The Object participant corresponds to this object. All\n            other participants (e.g. Actor) are retrieved from the owning\n            interaction.\n            ', tunable=TunableObjectGeneratorVariant(participant_default=ParticipantType.ObjectChildren)), 'picked_zone_for_multi_unit_event_tuning': OptionalTunable(description='\n            If enabled, find the unit_zone_id of the tenant with the desired active Multi\n            Unit (APM) event.  This will be sent to the InteractionResolver as the \n            PickedZoneId participant in order to apply the loot.\n            ', tunable=TunableTuple(event_target=TunableEnumEntry(description='\n                    The target of the interaction whose business unit will be used to  \n                    look up active APM events.  For Property Owner event interactions, \n                    this should be set to either ActorTenantHouseholds or CurrentZoneId.\n                    ', tunable_type=ParticipantType, default=ParticipantType.ActorTenantHouseholds), event_drama_node=TunableReference(description='\n                    The desired Multi Unit Event drama node.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions=('MultiUnitEventDramaNode',), pack_safe=True)))}

    def _do_behavior(self, *args, **kwargs):
        interaction_parameters = {}
        if self.picked_zone_for_multi_unit_event_tuning:
            picked_zone_id = self._get_multi_unit_picked_zone_id()
            if picked_zone_id is not None:
                interaction_parameters['picked_zone_id'] = {picked_zone_id}
        if self.object_override is None:
            resolver = self.interaction.get_resolver(**interaction_parameters)
            loots = (LootOperationList(resolver, self.loot_list),)
        else:
            loots = []
            for obj in self.object_override.get_objects(self.interaction):
                resolver = self.interaction.get_resolver(target=obj, **interaction_parameters)
                loots.append(LootOperationList(resolver, self.loot_list))
        for loot in loots:
            loot.apply_operations()

    def _get_multi_unit_picked_zone_id(self) -> int:
        unit_zone_ids = []
        if self.picked_zone_for_multi_unit_event_tuning.event_target == ParticipantType.ActorTenantHouseholds:
            tenant_hh_ids = services.get_multi_unit_ownership_service().get_tenants_household_ids(services.active_household_id())
            for household_id in tenant_hh_ids:
                household = services.household_manager().get(household_id)
                if household is not None:
                    unit_zone_ids.append(household.home_zone_id)
        elif self.picked_zone_for_multi_unit_event_tuning.event_target == ParticipantType.CurrentZoneId:
            unit_zone_ids = [services.current_zone_id()]
        for node in services.drama_scheduler_service().get_scheduled_nodes_by_drama_node_type(DramaNodeType.MULTI_UNIT_EVENT):
            if node.guid64 == self.picked_zone_for_multi_unit_event_tuning.event_drama_node.guid64 and node.get_unit_zone_id() in unit_zone_ids:
                return node.get_unit_zone_id()
