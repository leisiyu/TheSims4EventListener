from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from role.role_state import RoleState
    from situations.situation_job import SituationJobimport sims4import servicesfrom event_testing.resolver import SingleSimResolverfrom sims4.tuning.tunable import Tunable, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import TunableSituationJobAndRoleStatefrom situations.complex.eviction_situation import EvictionSituationfrom business.business_enums import BusinessTypefrom multi_unit.rental_unit_manager import PropertyOwnerActionfrom situations.situation_guest_list import SituationGuestInfo, SituationInvitationPurposefrom ui.ui_dialog import UiDialogOkCancel, ButtonTypelogger = sims4.log.Logger('EvictionSituation', default_owner='rpang')
class EvictionPropertyOwnerSituation(EvictionSituation):
    INSTANCE_TUNABLES = {'confirmation_dialog': OptionalTunable(description='\n        An optional confirmation dialog to confirm whether to evict a tenant or not\n        ', tunable=UiDialogOkCancel.TunableFactory(description='\n                Message to display to confirm whether to evict a tenant\n                '), tuning_group=GroupNames.UI), 'sell_furniture': Tunable(description='\n            Set to true to sell all furniture off and compensate tenant funds\n            ', tunable_type=bool, default=False), 'eviction_owner_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the property owner\n            ', tuning_group=GroupNames.ROLES), 'eviction_tenant_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the evicted tenant\n            ', tuning_group=GroupNames.ROLES)}

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.eviction_owner_job_and_role_state.job, cls.eviction_owner_job_and_role_state.role_state), (cls.eviction_tenant_job_and_role_state.job, cls.eviction_tenant_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        return cls.eviction_owner_job_and_role_state.job

    @property
    def is_user_facing(self):
        if not self.is_property_owner_on_site():
            return False
        return super().is_user_facing

    def __init__(self, *arg, **kwargs) -> 'None':
        super().__init__(*arg, **kwargs)
        self._eviction_zone_id = 0

    def start_situation(self) -> 'None':
        sim_info = services.sim_info_manager().get(self._host_sim_id)
        if sim_info is None:
            logger.error('EvictionPropertyOwnerSituation::start_situation() Unable to get host sim info: simID={}', self._host_sim_id)
            self._self_destruct()
            return
        tenant_sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        if tenant_sim_info is None:
            self._self_destruct()
            return
        if tenant_sim_info.household is not None:
            self._eviction_zone_id = tenant_sim_info.household.home_zone_id
        dialog = None
        if self.confirmation_dialog is not None:
            resolver = SingleSimResolver(sim_info)
            dialog = self.confirmation_dialog(None, resolver)
            if dialog is None:
                logger.error('EvictionPropertyOwnerSituation::start_situation() Unable to setup confirmation dialog properly')
        super().start_situation()
        self._change_state(self.eviction_preparation_state())
        if dialog is not None:
            dialog.show_dialog(on_response=self._on_confirmation_dialog_response)
        else:
            services.get_persistence_service().lock_save(self)
            self._start_eviction()

    def pre_destroy(self) -> 'None':
        if not services.get_persistence_service().is_save_locked_exclusively_by_holder(self):
            self._self_destruct()
            return
        services.get_persistence_service().unlock_save(self)
        tenant_sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        if tenant_sim_info is None:
            logger.error('EvictionPropertyOwnerSituation::pre_destroy() Unable to find tenant in guest list to evict')
            self._self_destruct()
            return
        is_tenant_evicted = self.move_household(evict_sim_info=tenant_sim_info, destination_zone_id=self.TENANT_EVICTION_DESTINATION_ZONE_ID, set_household_ownership=True, move_to_household_bin=True)
        if not is_tenant_evicted:
            logger.error('EvictionPropertyOwnerSituation::pre_destroy() Unable to evict tenant household properly. Tenant simID={}', tenant_sim_info.sim_id)
            self._self_destruct()
            return
        if self.is_property_owner_on_site():
            property_owner_sim_info = services.sim_info_manager().get(self._host_sim_id)
            is_owner_moved = self.move_household(evict_sim_info=property_owner_sim_info, destination_zone_id=property_owner_sim_info.household.home_zone_id, set_household_ownership=False, move_to_household_bin=True)
            if not is_owner_moved:
                logger.error('EvictionPropertyOwnerSituation::pre_destroy() Failed to move owner back to home lot: simID={}', self._host_sim_id)
        business_manager = services.business_service().get_business_manager_for_zone(self._eviction_zone_id)
        if business_manager is not None and business_manager.business_type == BusinessType.RENTAL_UNIT:
            business_manager.send_property_owner_action_telemetry(PropertyOwnerAction.EvictTenant, 'A tenant has been evicted by property owner.')
        self._on_eviction_complete()
        self._self_destruct()

    def _destroy(self) -> 'None':
        if services.get_persistence_service().is_save_locked_exclusively_by_holder(self):
            services.get_persistence_service().unlock_save(self)
        super()._destroy()

    def is_property_owner_on_site(self) -> 'bool':
        property_owner_sim_info = services.sim_info_manager().get(self._host_sim_id)
        if property_owner_sim_info is None:
            logger.error('EvictionPropertyOwnerSituation::is_property_owner_on_site() Unable to get property owner sim info: simID={}', self._host_sim_id)
            return False
        return property_owner_sim_info.zone_id == self._eviction_zone_id

    def _start_eviction(self) -> 'None':
        property_owner_sim_info = services.sim_info_manager().get(self._host_sim_id)
        tenant_sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        multi_unit_ownership_service = services.get_multi_unit_ownership_service()
        if property_owner_sim_info is None or tenant_sim_info is None or multi_unit_ownership_service is None:
            logger.error('EvictionPropertyOwnerSituation::_on_eviction_complete() Unable to get property owner ({}) and/or tenant sim info ({}) or multi_unit_owership_service is None', property_owner_sim_info, tenant_sim_info)
            return
        multi_unit_ownership_service.apply_loot_on_eviction(property_owner_hh_id=property_owner_sim_info.household.id, tenant_hh_id=tenant_sim_info.household.id)
        if not self.is_property_owner_on_site():
            self.pre_destroy()

    def _on_confirmation_dialog_response(self, dialog):
        if dialog.response == dialog.response and dialog.response == ButtonType.DIALOG_RESPONSE_OK:
            services.get_persistence_service().lock_save(self)
            self._start_eviction()
            return
        self._self_destruct()

    def _on_eviction_complete(self) -> 'None':
        property_owner_sim_info = services.sim_info_manager().get(self._host_sim_id)
        tenant_sim_info = self._get_sim_info_from_guest_list(self.eviction_tenant_job_and_role_state.job)
        multi_unit_ownership_service = services.get_multi_unit_ownership_service()
        if property_owner_sim_info is None or tenant_sim_info is None or multi_unit_ownership_service is None:
            logger.error('EvictionPropertyOwnerSituation::_on_eviction_complete() Unable to get property owner ({}) and/or tenant sim info ({}) or multi_unit_owership_service is None', property_owner_sim_info, tenant_sim_info)
            return
        multi_unit_ownership_service.update_ownership_on_eviction(property_owner_hh_id=property_owner_sim_info.household.id, tenant_hh_id=tenant_sim_info.household.id, zone_id=self._eviction_zone_id, is_owner=True, is_zone_loading=self.is_property_owner_on_site())
