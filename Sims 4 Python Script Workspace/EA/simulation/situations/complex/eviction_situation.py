from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from role.role_state import RoleState
    from sims.sim_info import SimInfo
    from situations.situation_job import SituationJobimport sims4import servicesimport enumfrom protocolbuffers import Consts_pb2from event_testing.resolver import SingleSimResolverfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationUserFacingType, SituationDisplayPriorityfrom ui.ui_dialog import UiDialogOkfrom server_commands.household_commands import trigger_move_out, get_household_home_lot_furnishings_valuefrom world.travel_service import travel_sims_to_zonelogger = sims4.log.Logger('EvictionSituation', default_owner='rpang')
class EvictionTrigger(enum.Int):
    NONE = 0
    TENANT_AGREEMENT = 1
    TENANT_INTERACTION = 2
    UNIT_INSPECTION = 3
    WORLD_MAP = 4
    EVICTION_CHEAT = 5

class EvictionPreparationState(CommonSituationState):
    pass

class EvictionSituation(SituationComplexCommon):
    INSTANCE_SUBCLASSES_ONLY = True
    TENANT_EVICTION_DESTINATION_ZONE_ID = 0
    INSTANCE_TUNABLES = {'eviction_preparation_state': EvictionPreparationState.TunableFactory(description='\n            The state in which the sim prepares before being evicted\n            ', display_name='01_eviction_preparation_state', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'timeout_dialog': UiDialogOk.TunableFactory(description='\n            Dialog that appears when the eviction situation times out\n            ', tuning_group=GroupNames.UI), 'save_lock_tooltip_message': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game while this situation is running.\n            Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI)}

    @property
    def user_facing_type(self) -> 'enum.Int':
        return SituationUserFacingType.UNIVERSITY_HOUSING_KICK_OUT_EVENT

    @property
    def situation_display_priority(self) -> 'enum.Int':
        return SituationDisplayPriority.HIGH

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, ...]':
        return (SituationStateData.from_auto_factory(1, cls.eviction_preparation_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return list()

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        pass

    def __init__(self, *arg, **kwargs) -> 'None':
        super().__init__(*arg, **kwargs)
        self._host_sim_id = self._seed.guest_list.host_sim_id

    def _situation_timed_out(self, *args, **kwargs) -> 'None':

        def on_response(dialog):
            self.pre_destroy()

        sim_info = services.sim_info_manager().get(self._host_sim_id)
        if sim_info is not None:
            resolver = SingleSimResolver(sim_info)
            dialog = self.timeout_dialog(None, resolver)
            if dialog is not None:
                dialog.show_dialog(on_response=on_response)

    def move_household(self, evict_sim_info:'SimInfo', destination_zone_id:'int', set_household_ownership:'bool', move_to_household_bin:'bool') -> 'bool':
        household = evict_sim_info.household if evict_sim_info is not None else None
        if household is None:
            logger.error('EvictionSituation::evict_household() Unable to get household to evict with simID: {}, destZoneID: {}', evict_sim_info.sim_id, destination_zone_id)
            return False
        furnishing_value = 0
        if household.home_zone_id == services.current_zone_id():
            furnishing_value = get_household_home_lot_furnishings_value(household)
        if destination_zone_id == 0 and destination_zone_id == 0:
            if move_to_household_bin:
                services.household_manager().move_household_out_of_lot(household, False, furnishing_value)
            else:
                household.funds.add(furnishing_value, Consts_pb2.FUNDS_LOT_SELL)
                trigger_move_out(moving_household_id=household.id, is_in_game_evict=True)
        else:
            sims_to_travel = set()
            for sim_info in household.instanced_sims_gen():
                sims_to_travel.add(sim_info.sim_id)
            travel_sims_to_zone(sims_to_travel, destination_zone_id)
        if set_household_ownership:
            household.set_household_lot_ownership(zone_id=destination_zone_id)
        return True

    def _on_eviction_complete(self) -> 'None':
        raise NotImplementedError

    def get_lock_save_reason(self) -> 'TunableLocalizedString':
        return self.save_lock_tooltip_message
