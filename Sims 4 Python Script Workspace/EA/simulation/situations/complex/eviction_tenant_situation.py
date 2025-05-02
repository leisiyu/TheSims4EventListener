from __future__ import annotationsfrom sims.sim_info import SimInfofrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from role.role_state import RoleState
    from situations.situation_job import SituationJobimport sims4import servicesimport enumfrom business.business_enums import BusinessTypefrom business.business_rule_enums import BusinessRuleStatefrom event_testing.resolver import SingleSimResolverfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntryfrom situations.situation_complex import TunableSituationJobAndRoleStatefrom situations.complex.eviction_situation import EvictionSituationfrom ui.ui_dialog import UiDialogOklogger = sims4.log.Logger('EvictionSituation', default_owner='rpang')
class EvictionReason(enum.Int):
    NONE = 0
    UNPAID_RENT = 1
    LEASE_EXPIRED = 2
    RULE_BROKEN = 3
    UNJUST_EVICTION = 4

class EvictionTenantSituation(EvictionSituation):
    INSTANCE_TUNABLES = {'eviction_dialog_map': TunableMapping(description='\n            Map of eviction reasons to tunable dialog that will notify player when they are getting evicted\n            ', key_type=TunableEnumEntry(tunable_type=EvictionReason, default=EvictionReason.NONE, invalid_enums=EvictionReason.NONE, pack_safe=False), key_name='Eviction Reason', value_type=UiDialogOk.TunableFactory(), value_name='Eviction Start Dialog', tuning_group=GroupNames.UI), 'eviction_owner_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the property owner\n            ', tuning_group=GroupNames.ROLES), 'eviction_tenant_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the evicted tenant\n            ', tuning_group=GroupNames.ROLES)}

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.eviction_owner_job_and_role_state.job, cls.eviction_owner_job_and_role_state.role_state), (cls.eviction_tenant_job_and_role_state.job, cls.eviction_tenant_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        return cls.eviction_tenant_job_and_role_state.job

    def __init__(self, *arg, **kwargs) -> 'None':
        super().__init__(*arg, **kwargs)
        self._eviction_zone_id = 0

    def start_situation(self) -> 'None':
        end_situation = True
        tenant_sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        if tenant_sim_info is None:
            self._self_destruct()
            return
        if tenant_sim_info.household is not None:
            self._eviction_zone_id = tenant_sim_info.household.home_zone_id
        eviction_reason = self.get_eviction_reason()
        dialog_entry = self.eviction_dialog_map.get(eviction_reason, None)
        if dialog_entry is not None:
            resolver = SingleSimResolver(tenant_sim_info)
            dialog = dialog_entry(None, resolver)
            dialog.show_dialog()
            end_situation = False
        if end_situation:
            logger.error('EvictionTenantSituation::start_situation() Eviction was missing some info, unable to start situation properly')
            self._self_destruct()
            return
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(self.eviction_preparation_state())

    def pre_destroy(self) -> 'None':
        if not services.get_persistence_service().is_save_locked_exclusively_by_holder(self):
            self._self_destruct()
            return
        services.get_persistence_service().unlock_save(self)
        sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        household = sim_info.household if sim_info is not None else None
        if household is None:
            self._self_destruct()
            return
        self.move_household(evict_sim_info=sim_info, destination_zone_id=self.TENANT_EVICTION_DESTINATION_ZONE_ID, set_household_ownership=True, move_to_household_bin=False)
        self._on_eviction_complete()
        self._self_destruct()

    def _destroy(self) -> 'None':
        if services.get_persistence_service().is_save_locked_exclusively_by_holder(self):
            services.get_persistence_service().unlock_save(self)
        super()._destroy()

    def _on_eviction_complete(self) -> 'None':
        multi_unit_ownership_service = services.get_multi_unit_ownership_service()
        if multi_unit_ownership_service is None:
            return
        property_owner_hh_id = multi_unit_ownership_service.get_property_owner_household_id(self._eviction_zone_id)
        tenant_sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        if property_owner_hh_id is None or tenant_sim_info is None:
            logger.error('EvictionTenantSituation::_on_eviction_complete() Unable to get property owner hh id ({}) and/or tenant sim info ({})', property_owner_hh_id, tenant_sim_info)
            return
        multi_unit_ownership_service.update_ownership_on_eviction(property_owner_hh_id=property_owner_hh_id, tenant_hh_id=tenant_sim_info.household.id, zone_id=self._eviction_zone_id, is_owner=False, is_zone_loading=True)

    def get_eviction_reason(self) -> 'EvictionReason':
        eviction_reason = EvictionReason.NONE
        business_manager = services.business_service().get_business_manager_for_zone(self._eviction_zone_id)
        if business_manager.business_type == BusinessType.RENTAL_UNIT:
            if len(business_manager.get_rules_by_states(BusinessRuleState.BROKEN)) > 0:
                eviction_reason = EvictionReason.RULE_BROKEN
            elif business_manager.overdue_rent > 0:
                eviction_reason = EvictionReason.UNPAID_RENT
            elif business_manager.is_grace_period:
                eviction_reason = EvictionReason.LEASE_EXPIRED
            else:
                eviction_reason = EvictionReason.UNJUST_EVICTION
        return eviction_reason
