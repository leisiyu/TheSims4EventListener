from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from typing import *
    from interactions.base.interaction import Interaction
    from protocolbuffers.FileSerialization_pb2 import SaveSlotData
    from sims.sim import Sim
    from sims.sim_info import SimInfofrom protocolbuffers import GameplaySaveData_pb2from _collections import defaultdictfrom business.business_enums import BusinessTypefrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom multi_unit.multi_unit_tuning import PropertyOwnerTuning, MultiUnitTuningfrom multi_unit.multi_unit_handler import log_eviction_outcomefrom multi_unit.rental_unit_manager import PropertyOwnerActionfrom relationships.relationship_track import RelationshipTrackfrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyimport sims4import servicesimport persistence_error_typeslogger = sims4.log.Logger('Multi Unit Ownership Service', default_owner='shipark')
class MultiUnitOwnershipService(Service):
    OWNERSHIP_VALIDATION_EVENTS = (TestEvent.AgedUp, TestEvent.HouseholdChanged)

    def __init__(self) -> 'None':
        super().__init__()
        self._npc_property_owner_id = None
        self._property_owners = defaultdict(list)

    @classproperty
    def required_packs(cls) -> 'Tuple[Pack]':
        return (Pack.EP15,)

    @classproperty
    def save_error_code(cls) -> 'None':
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_MULTI_UNIT_OWNERSHIP_SERVICE

    def save(self, save_slot_data:'SaveSlotData'=None, **__) -> 'None':
        if self._npc_property_owner_id is None:
            return
        multi_unit_ownership_proto = GameplaySaveData_pb2.PersistableMultiUnitOwnershipService()
        multi_unit_ownership_proto.npc_property_owner_id = self._npc_property_owner_id
        save_slot_data.gameplay_data.multi_unit_ownership_service = multi_unit_ownership_proto

    def setup(self, save_slot_data:'SaveSlotData'=None, **__) -> 'None':
        if save_slot_data.gameplay_data.HasField('multi_unit_ownership_service'):
            self._npc_property_owner_id = save_slot_data.gameplay_data.multi_unit_ownership_service.npc_property_owner_id

    def on_zone_load(self) -> 'None':
        services.get_event_manager().register(self, self.OWNERSHIP_VALIDATION_EVENTS)

    def on_zone_unload(self) -> 'None':
        services.get_event_manager().unregister(self, self.OWNERSHIP_VALIDATION_EVENTS)

    def has_property_owner(self, zone_id:'int') -> 'bool':
        return self.get_property_owner_household_id(zone_id) is not None

    def is_property_owner(self, hh_id:'int') -> 'bool':
        return len(self.get_tenants_household_ids(hh_id)) > 0

    def get_tenants_household_ids(self, property_owner_hh_id:'int', from_load=False) -> 'list[int]':
        tenants_hh_ids = self._property_owners.get(property_owner_hh_id)
        if tenants_hh_ids is None or from_load:
            tenants_hh_ids = self._setup_tenant_relationships(property_owner_hh_id)
            if len(tenants_hh_ids) > 0:
                self._property_owners[property_owner_hh_id] = tenants_hh_ids
        return tenants_hh_ids

    def get_property_owner_household_id(self, zone_id:'int') -> 'Optional[int]':
        property_owner_hh_id = self._get_property_owner_hh_id(zone_id)
        if property_owner_hh_id is not None:
            return property_owner_hh_id
        return self._setup_property_owner_relationships(zone_id)

    def evict_tenant(self, tenant_hh_id:'int', eviction_affordance:'Interaction'=None, lease_break:'bool'=False) -> 'bool':
        logger.info('MultiUnitOwnershipService::evict_tenant() Attempting to evict tenant household ID: {}', tenant_hh_id)
        tenant_household = services.household_manager().get(tenant_hh_id)
        if tenant_household is None:
            logger.error('MultiUnitOwnershipService::evict_tenant() No valid household found matching tenant household ID: {}', tenant_hh_id)
            return False
        tenant_zone_id = tenant_household.home_zone_id
        property_owner_hh_id = self._get_property_owner_hh_id(tenant_zone_id)
        if property_owner_hh_id is None:
            logger.error('MultiUnitOwnershipService::evict_tenant() No valid property owner household found for tenant {} (zoneID: {})', tenant_hh_id, tenant_zone_id)
            return False
        property_owner_sim = services.get_active_sim()
        if not (property_owner_sim is None or property_owner_sim.sim_info.is_child_or_younger or property_owner_sim.is_human):
            property_owner_hh = services.household_manager().get(property_owner_hh_id)
            for potential_sim in property_owner_hh.instanced_sims_gen():
                if potential_sim.is_human and potential_sim.sim_info.is_teen_or_older:
                    property_owner_sim = potential_sim
                    break
        tenant_sim = None
        for potential_sim in tenant_household.instanced_sims_gen():
            if potential_sim.is_human and potential_sim.sim_info.is_teen_or_older:
                tenant_sim = potential_sim
                break
        current_zone_id = services.current_zone_id()
        if tenant_sim is not None and (property_owner_sim is not None and tenant_zone_id == current_zone_id) and self._try_push_eviction_interaction(eviction_affordance, property_owner_sim, tenant_sim):
            return True
        if not lease_break:
            self.apply_loot_on_eviction(property_owner_hh_id=property_owner_hh_id, tenant_hh_id=tenant_hh_id)
        logger.info('MultiUnitOwnershipService::evict_tenant() No instanced tenant sim found or owner is not on tenant lot, evict directly')
        services.household_manager().move_household_out_of_lot(tenant_household, False, 0)
        tenant_household.set_household_lot_ownership(zone_id=0)
        self.update_ownership_on_eviction(property_owner_hh_id=property_owner_hh_id, tenant_hh_id=tenant_hh_id, zone_id=tenant_zone_id, is_owner=True, is_zone_loading=False)
        business_manager = services.business_service().get_business_manager_for_zone(tenant_zone_id)
        if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
            business_manager.send_property_owner_action_telemetry(PropertyOwnerAction.EvictTenant, 'A tenant has been evicted by property owner.')

    def apply_loot_on_eviction(self, property_owner_hh_id:'int', tenant_hh_id:'int'):
        property_owner_household = services.household_manager().get(property_owner_hh_id)
        property_owner_sim_info = next(property_owner_household.sim_info_gen(), None)
        tenant_sim_household = services.household_manager().get(tenant_hh_id)
        tenant_sim_info = next(tenant_sim_household.sim_info_gen(), None)
        if tenant_sim_info is not None:
            property_owner_sim_resolver = DoubleSimResolver(property_owner_sim_info, tenant_sim_info)
            for loot_action in PropertyOwnerTuning.PROPERTY_OWNER_EVICTION_LOOT:
                loot_action.apply_to_resolver(property_owner_sim_resolver)

    def update_ownership_on_eviction(self, property_owner_hh_id:'int', tenant_hh_id:'int', zone_id:'int', is_owner:'bool', is_zone_loading:'bool'=True) -> 'None':
        log_eviction_outcome(property_owner_hh_id, tenant_hh_id, zone_id)
        if is_owner and not is_zone_loading:
            self._remove_tenant(property_owner_hh_id, tenant_hh_id)
        self._apply_relationship_between_households(property_owner_hh_id, tenant_hh_id, False)
        business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
        if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
            business_manager.set_open(False)

    def on_all_households_and_sim_infos_loaded(self, client) -> 'None':
        self._refresh_active_ownership_relationships()

    def handle_household_lot_owner_changed(self, home_zone_id:'int') -> 'None':
        self.get_property_owner_household_id(home_zone_id)

    def handle_event(self, sim_info:'SimInfo', event_type:'TestEvent', resolver:'Resolver') -> 'None':
        self._handle_sim_household_changed(sim_info, event_type, resolver)

    def handle_last_household_member_removed(self, former_household_id:'int', sim_info:'SimInfo') -> 'None':
        self._update_ownership_rel(sim_info, former_household_id, add=False)

    def handle_household_removal(self, household_id:'int', home_zone_id:'int') -> 'None':
        self._remove_property_owner_household(household_id)
        self._remove_tenant_household(household_id, home_zone_id)

    def _try_push_eviction_interaction(self, eviction_affordance:'Interaction', property_owner_sim:'Sim', tenant_sim:'Sim') -> 'bool':
        logger.info('MultiUnitOwnershipService::evict_tenant() Owner currently on tenant lot, evict with situation')
        if eviction_affordance is None:
            eviction_affordance = PropertyOwnerTuning.TENANT_EVICTION_AFFORDANCE
        if eviction_affordance is None:
            logger.error('MultiUnitOwnershipService::evict_tenant() No tuning defined for eviction affordance')
            return False
        else:
            context = InteractionContext(sim=property_owner_sim, source=InteractionContext.SOURCE_SCRIPT, priority=Priority.High, run_priority=Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            if not property_owner_sim.push_super_affordance(eviction_affordance, tenant_sim, context):
                logger.error('MultiUnitOwnershipService::evict_tenant() Failed to push the eviction affordance onto the tenant sim: {}', property_owner_sim.id)
                return False
        return True

    def _refresh_active_ownership_relationships(self):
        households = {services.owning_household_of_active_lot(), services.active_household()}
        households.discard(None)
        for household in households:
            home_zone_id = household.home_zone_id
            self.get_property_owner_household_id(home_zone_id)
            self.get_tenants_household_ids(household.id, from_load=True)

    def _get_property_owner_hh_id(self, zone_id:'int') -> 'Optional[int]':
        household_manager = services.household_manager()
        for (property_owner_hh_id, tenant_hh_ids) in self._property_owners.items():
            for tenant_hh_id in tenant_hh_ids:
                tenant_household = household_manager.get(tenant_hh_id)
                if tenant_household is None:
                    logger.error('The MPOS has a stale tenant entry (hh id: {}) for property owner (hh id: {}) ', property_owner_hh_id, tenant_hh_id)
                else:
                    tenant_home_zone_id = tenant_household.home_zone_id
                    if zone_id == tenant_home_zone_id:
                        return property_owner_hh_id

    def _add_tenant(self, property_owner_hh_id:'int', tenant_hh_id:'int') -> 'None':
        tenants = self._property_owners.get(property_owner_hh_id)
        if tenants is None:
            tenants = []
        if tenant_hh_id in tenants:
            logger.error('MultiUnitOwnershipService::_add_tenant() Trying to add duplicate tenant ({}) for same property owner ({})', tenant_hh_id, property_owner_hh_id)
            return
        tenants.append(tenant_hh_id)
        self._property_owners[property_owner_hh_id] = tenants

    def _remove_tenant(self, property_owner_hh_id:'int', tenant_hh_id:'int') -> 'None':
        tenants_hh_ids = self._property_owners.get(property_owner_hh_id)
        if tenants_hh_ids is not None and tenant_hh_id in tenants_hh_ids:
            tenants_hh_ids.remove(tenant_hh_id)

    def _handle_sim_household_changed(self, sim_info:'SimInfo', event_type:'TestEvent', resolver:'Resolver') -> 'None':
        sim_hh_id = sim_info.household_id
        if sim_hh_id is None:
            return
        add = True
        if event_type == TestEvent.HouseholdChanged:
            removed_sim = resolver.event_kwargs.get('sim_removed')
            if removed_sim is not None:
                add = False
                sim_info = removed_sim
        if sim_info.id == self._npc_property_owner_id:
            self._handle_npc_property_owner_changed()
        self._update_ownership_rel(sim_info, sim_hh_id, add=add)

    def _handle_npc_property_owner_changed(self):
        self._npc_property_owner_id = None
        self._refresh_active_ownership_relationships()

    def _update_ownership_rel(self, sim_info:'SimInfo', sim_hh_id:'int', add=True):
        household_manager = services.household_manager()
        for (property_owner_hh_id, tenant_hh_ids) in self._property_owners.items():
            if property_owner_hh_id == sim_hh_id:
                for tenant_hh_id in tenant_hh_ids:
                    if tenant_hh_id == sim_hh_id:
                        pass
                    else:
                        tenant_household = household_manager.get(tenant_hh_id)
                        if tenant_household is None:
                            logger.error('Attempting to add rel to tracked tenant household with id {} but none exists.', tenant_hh_id)
                        else:
                            self._apply_relationship_between_household_sims((sim_info,), tenant_household.sim_infos, add=add)
            if sim_hh_id in tenant_hh_ids:
                if property_owner_hh_id == sim_hh_id:
                    pass
                else:
                    property_owner_household = household_manager.get(property_owner_hh_id)
                    if property_owner_household is None:
                        logger.error('Attempting to add rel to tracked property owner household with id {} but none exists', property_owner_hh_id)
                    else:
                        self._apply_relationship_between_household_sims(property_owner_household.sim_infos, (sim_info,), add=add)

    def _remove_tenant_household(self, tenant_hh_id:'int', zone_id:'int') -> 'None':
        business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        if business_manager is None or business_manager.business_type != BusinessType.RENTAL_UNIT or not business_manager.is_open:
            return
        property_owner_hh_id = business_manager.owner_household_id
        self._remove_tenant(property_owner_hh_id, tenant_hh_id)
        business_manager.set_open(False)
        if services.active_household_id() == property_owner_hh_id:
            dialog = MultiUnitTuning.NO_TENANT_LEFT_NOTIFICATION(services.active_sim_info())
            dialog.show_dialog()

    def _remove_property_owner_household(self, hh_id:'int') -> 'None':
        if hh_id not in self._property_owners:
            return
        del self._property_owners[hh_id]

    def refresh_relationships(self, zone_id:'int') -> 'None':
        self.get_property_owner_household_id(zone_id)

    @staticmethod
    def _apply_relationship_between_sims(property_owner_sim_info:'SimInfo', tenant_sim_info:'SimInfo', add=True) -> 'None':
        tenant_sim_info.relationship_tracker.get_relationship_track(property_owner_sim_info.id, RelationshipTrack.FRIENDSHIP_TRACK, add=True)
        property_owner_sim_info.relationship_tracker.get_relationship_track(tenant_sim_info.id, RelationshipTrack.FRIENDSHIP_TRACK, add=True)
        if add:
            tenant_sim_info.relationship_tracker.add_relationship_bit(property_owner_sim_info.id, PropertyOwnerTuning.PROPERTY_OWNER_REL_BIT, force_add=True)
            property_owner_sim_info.relationship_tracker.add_relationship_bit(tenant_sim_info.id, PropertyOwnerTuning.TENANT_REL_BIT, force_add=True)
        else:
            tenant_sim_info.relationship_tracker.remove_relationship_bit(property_owner_sim_info.id, PropertyOwnerTuning.PROPERTY_OWNER_REL_BIT)
            property_owner_sim_info.relationship_tracker.remove_relationship_bit(tenant_sim_info.id, PropertyOwnerTuning.TENANT_REL_BIT)

    def _apply_relationship_between_households(self, property_owner_hh_id:'int', tenant_hh_id:'int', add=True) -> 'None':
        if property_owner_hh_id == tenant_hh_id:
            return
        household_manager = services.household_manager()
        property_owner_household = household_manager.get(property_owner_hh_id)
        tenant_household = household_manager.get(tenant_hh_id)
        if tenant_household is None or property_owner_household is None:
            return
        self._apply_relationship_between_household_sims(property_owner_household.sim_infos, tenant_household.sim_infos, add=add)

    def _apply_relationship_between_household_sims(self, property_owner_household_members:'Tuple(SimInfo)', tenant_household_members:'Tuple(SimInfo)', add:'bool'=True) -> 'None':
        tested_tenants = [tenant_hh_member for tenant_hh_member in tenant_household_members if PropertyOwnerTuning.TENANT_SIM_TESTS.run_tests(SingleSimResolver(tenant_hh_member))]
        for property_owner_hh_member in property_owner_household_members:
            property_owner_sim_resolver = SingleSimResolver(property_owner_hh_member)
            if not PropertyOwnerTuning.PROPERTY_OWNER_SIM_TESTS.run_tests(property_owner_sim_resolver):
                pass
            else:
                for tenant_hh_member in tested_tenants:
                    self._apply_relationship_between_sims(property_owner_hh_member, tenant_hh_member, add=add)

    def _setup_tenant_relationships(self, property_owner_hh_id:'int') -> 'list[int]':
        tenant_household_ids = []
        multi_unit_business_tracker = services.business_service().get_business_tracker_for_household(property_owner_hh_id, BusinessType.RENTAL_UNIT)
        if multi_unit_business_tracker is None:
            return tenant_household_ids
        persistence_service = services.get_persistence_service()
        for rental_unit_zone_id in multi_unit_business_tracker.business_managers.keys():
            tenant_household_id = persistence_service.get_household_id_from_zone_id(rental_unit_zone_id)
            if tenant_household_id and tenant_household_id != 0:
                tenant_household_ids.append(tenant_household_id)
                self._apply_relationship_between_households(property_owner_hh_id, tenant_household_id)
        return tenant_household_ids

    def _get_npc_property_owner(self) -> 'Optional[SimInfo]':
        npc_property_owner_filter = PropertyOwnerTuning.NPC_PROPERTY_OWNER_FILTER
        if npc_property_owner_filter is None:
            return
        if self._npc_property_owner_id is not None:
            if services.sim_filter_service().does_sim_match_filter(self._npc_property_owner_id, sim_filter=npc_property_owner_filter):
                return services.sim_info_manager().get(self._npc_property_owner_id)
            self._npc_property_owner_id = None
        npc_property_owner_sim_infos = services.sim_filter_service().submit_matching_filter(sim_filter=npc_property_owner_filter, number_of_sims_to_find=1, allow_instanced_sims=True, allow_yielding=False)
        if npc_property_owner_sim_infos:
            npc_property_owner_sim_info = npc_property_owner_sim_infos[0].sim_info
            self._npc_property_owner_id = npc_property_owner_sim_info.id
            return npc_property_owner_sim_info
        logger.error('No npc property owner sim info found.')

    def _setup_property_owner_relationships(self, zone_id:'int') -> 'Optional[int]':
        zone_business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        if zone_business_manager is None or zone_business_manager.business_type != BusinessType.RENTAL_UNIT:
            return
        property_owner_hh_id = zone_business_manager.owner_household_id
        household_manager = services.household_manager()
        tenant_household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
        tenant_household = household_manager.get(tenant_household_id)
        if tenant_household_id == 0 or tenant_household is None or not tenant_household.sim_infos:
            return property_owner_hh_id
        if tenant_household_id == property_owner_hh_id:
            return property_owner_hh_id
        if property_owner_hh_id is None:
            npc_property_owner_sim_info = self._get_npc_property_owner()
            if npc_property_owner_sim_info is None:
                logger.error('Unable to complete relationship setup because no valid npc sim info was found.')
                return
            property_owner_hh_id = npc_property_owner_sim_info.household.id
        self._apply_relationship_between_households(property_owner_hh_id, tenant_household_id)
        self._add_tenant(property_owner_hh_id, tenant_household_id)
        return property_owner_hh_id
