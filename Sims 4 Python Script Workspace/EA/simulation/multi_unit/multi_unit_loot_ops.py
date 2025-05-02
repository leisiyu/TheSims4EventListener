from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.base.interaction import Interactionfrom drama_scheduler.drama_enums import MultiUnitEventOutcomefrom drama_scheduler.drama_node_types import DramaNodeTypefrom interactions import ParticipantType, ParticipantTypeSingleSim, ParticipantTypeZoneIdfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunablePackSafeReference, TunableVariant, HasTunableSingletonFactory, AutoFactoryInitimport servicesimport sims4logger = sims4.log.Logger('MultiUnitLootOps')
class _ParticipantHomeZone(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that will provide the home zone.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

    def get_zone_id(self, *, resolver) -> 'int':
        participant = resolver.get_participant(self.participant)
        if participant is not None and participant.is_sim and participant.household is not None:
            return participant.household.home_zone_id

class _PickedZoneId(HasTunableSingletonFactory, AutoFactoryInit):

    def get_zone_id(self, *, resolver) -> 'int':
        return resolver.get_participant(ParticipantType.PickedZoneId)

class _CurrentZoneId(HasTunableSingletonFactory, AutoFactoryInit):

    def get_zone_id(self, *, resolver) -> 'int':
        return services.current_zone_id()

class SetMultiUnitEventOutcomeLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'receiver': TunableEnumEntry(description="\n            The recipient of the drama node event.  This is should be a household type,\n            referencing a Property Owner or Tenant.  However, a single Sim participant \n            type may be used, and this loot will look up the Sim's household.\n            ", tunable_type=ParticipantType, default=ParticipantType.ActorHousehold), 'event_zone': TunableVariant(description='\n            The zone participant to use when determining the drama node event.\n            ', use_picked_zone_id=_PickedZoneId.TunableFactory(), use_participant_home_zone=_ParticipantHomeZone.TunableFactory(), use_current_zone_id=_CurrentZoneId.TunableFactory(), default='use_picked_zone_id'), 'unit_event_outcome': TunableEnumEntry(description='\n            The outcome for this multi unit event, success or failure.\n            ', tunable_type=MultiUnitEventOutcome, default=MultiUnitEventOutcome.SUCCESS)}

    def __init__(self, receiver, event_zone, unit_event_outcome, **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._receiver_type = receiver
        self._event_zone = event_zone
        self._unit_event_outcome = unit_event_outcome

    def _apply_to_subject_and_target(self, subject, target, resolver) -> 'None':
        receiver = resolver.get_participant(self._receiver_type)
        if receiver.is_sim:
            receiver = services.household_manager().get_by_sim_id(receiver.sim_id)
        if receiver is not None and receiver is None:
            return
        unit_zone_id = self._event_zone.get_zone_id(resolver=resolver)
        if unit_zone_id is None:
            return
        service = services.drama_scheduler_service()
        for node in service.get_scheduled_nodes_by_drama_node_type(DramaNodeType.MULTI_UNIT_EVENT):
            if node.get_receiver_household() is receiver and node.get_unit_zone_id() == unit_zone_id:
                node.set_unit_event_outcome(self._unit_event_outcome)
                return
        if isinstance(self._event_zone, _CurrentZoneId):
            event_service = services.multi_unit_event_service()
            if event_service is not None:
                drama_node_id = event_service.get_multi_unit_zone_best_active_event(unit_zone_id)
                drama_node = service.get_scheduled_node_by_uid(drama_node_id) if drama_node_id is not None else None
                if drama_node is not None:
                    drama_node.set_unit_event_outcome(self._unit_event_outcome)
                    return

class EvictionLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description="\n            Participant that resolves to the evicted tenant's zone id\n            ", tunable_type=ParticipantTypeZoneId, default=ParticipantType.PickedZoneId), 'eviction_affordance': TunablePackSafeReference(description='\n            Interaction to apply to the owner with the tenant as the target\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'lease_break': Tunable(description='\n            Set to true if this is actually the tenant breaking the lease and not an eviction.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls) -> 'None':
        valid_receiver_types = [ParticipantType.PickedZoneId, ParticipantType.RandomZoneId, ParticipantType.ActorZoneId, ParticipantType.CurrentZoneId]
        if cls._participant not in valid_receiver_types:
            logger.error('Participant {} is not a valid participant type!', cls._participant)

    def __init__(self, participant:'ParticipantType', eviction_affordance:'Interaction', lease_break:'bool', **kwargs) -> 'None':
        super().__init__(**kwargs)
        self._participant = participant
        self._eviction_affordance = eviction_affordance
        self._lease_break = lease_break

    def _apply_to_subject_and_target(self, subject, target, resolver) -> 'None':
        zone_ids = resolver.get_participants(self._participant)
        if len(zone_ids) <= 0:
            logger.error('No participant found using zone participant: {}', self.participant)
            return
        target_zone_id = zone_ids[0]
        tenant_household_id = services.get_persistence_service().get_household_id_from_zone_id(target_zone_id)
        multi_unit_ownership_service = services.get_multi_unit_ownership_service()
        if multi_unit_ownership_service is None:
            return
        multi_unit_ownership_service.evict_tenant(tenant_hh_id=tenant_household_id, eviction_affordance=self._eviction_affordance, lease_break=self._lease_break)
