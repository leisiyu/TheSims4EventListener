from __future__ import annotationsimport servicesimport sims4from business.business_enums import BusinessTypefrom business.business_zone_director_mixin import CustomerAndEmployeeZoneDirectorMixinfrom sims4.tuning.tunable import TunableList, TunableReference, Tunable, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_curve import SituationCurvefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom small_business.small_business_tuning import SmallBusinessTunablesfrom sims.sim_spawner import SimSpawnerfrom sims.sim_info import SimInfofrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import Optional, Tuplelogger = sims4.log.Logger('Small Business', default_owner='bshefket')
class SmallBusinessZoneDirectorMixin(CustomerAndEmployeeZoneDirectorMixin):
    INSTANCE_TUNABLES = {'customer_situation_type_curve': SituationCurve.TunableFactory(description="\n            When customer situations are being generated, they'll be pulled\n            based on the tuning in this.\n            ", tuning_group=GroupNames.BUSINESS, get_create_params={'user_facing': False}), 'player_customer_situation': TunablePackSafeReference(description='\n            The situation Player customers will run.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('SmallBusinessCustomerSituation',), tuning_group=GroupNames.BUSINESS, allow_none=True), 'employee_situation': TunablePackSafeReference(description='\n            Employee situation to put employees in. \n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('SmallBusinessEmployeeSituation',), tuning_group=GroupNames.BUSINESS, allow_none=True), 'owner_situation': TunablePackSafeReference(description='\n            Owner situation to put active owner in. \n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('SmallBusinessEmployeeSituation',), tuning_group=GroupNames.BUSINESS, allow_none=True), 'npc_owner_situation': TunablePackSafeReference(description='\n            The situation NPC employees will run.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('SmallBusinessEmployeeSituation',), tuning_group=GroupNames.BUSINESS, allow_none=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def supported_business_types(self) -> 'Tuple[Optional[BusinessType]]':
        pass

    def _get_employee_situation_for_employee_type(self, employee_type):
        return self.employee_situation

    def _get_npc_employee_situation_for_employee_type(self, employee_type):
        return self.employee_situation

    def _get_desired_employee_count(self, employee_type):
        pass

    def handle_sim_summon_request(self, sim_info, purpose):
        if self._business_manager is not None and (self._business_manager.is_open and self._business_manager.business_type == BusinessType.SMALL_BUSINESS) and sim_info.household_id != self._business_manager.owner_household_id:
            self.start_sims_customer_situations([sim_info])
        else:
            super().handle_sim_summon_request(sim_info, purpose)

    def _customer_situation_alarm_callback(self, *_, **__):
        if self._business_manager is None or self._business_manager.is_open and self._business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return
        self._on_customer_situation_request()

    def _decide_whether_to_load_zone_situation_seed(self, seed):
        if not super()._decide_whether_to_load_zone_situation_seed(seed):
            return False
        business_manager = services.business_service().get_business_manager_for_zone()
        if seed.situation_type is self.employee_situation:
            if business_manager is None:
                return False
            for sim_info in seed.guest_list.guest_info_gen():
                return business_manager.is_employee(sim_info)
        if seed.situation_type is self.npc_owner_situation or seed.situation_type is self.owner_situation or seed.situation_type is self.player_customer_situation:
            return business_manager is not None
        return True

    def _on_customer_situation_request(self):
        self.remove_stale_customer_situations()
        desired_customer_count = self._get_ideal_customer_count()
        current_customer_count = len(self._customer_situation_ids)
        needed_customer_count = desired_customer_count - current_customer_count
        if needed_customer_count > 0:
            (new_customer_situation, params) = self.customer_situation_type_curve.get_situation_and_params()
            if new_customer_situation is None:
                return
            situation_id = self.start_customer_situation(new_customer_situation, create_params=params, failure_log_level=sims4.log.LEVEL_DEBUG)
            if situation_id is None:
                return
            created_situation = services.get_zone_situation_manager().get(situation_id)
            needed_customer_count -= created_situation.num_invited_sims

    def _get_ideal_customer_count(self) -> 'int':
        ideal_count = self.customer_situation_type_curve.get_desired_sim_count().upper_bound
        return ideal_count

    def _can_start_employee_situation(self, employee_id) -> 'bool':
        sim_info = services.sim_info_manager().get(employee_id)
        if self._business_manager.business_type == BusinessType.SMALL_BUSINESS and sim_info.household_id != self._business_manager.owner_household_id and sim_info.household_id == services.active_household_id():
            return False
        return True

    def start_sims_customer_situations(self, sim_infos:'[SimInfo]'):
        sim_info_manager = services.sim_info_manager()
        situation_manager = services.get_zone_situation_manager()
        business_owner_household_id = sim_info_manager.get(self.business_manager.owner_sim_id).household.id
        for sim_info in sim_infos:
            if not sim_info.is_player_sim:
                if not self.business_manager.is_employee(sim_info):
                    if sim_info.household.id == business_owner_household_id:
                        pass
                    else:
                        situation = None
                        if sim_info.is_player_sim:
                            situation = self.player_customer_situation
                        else:
                            (situation, _) = self.customer_situation_type_curve.get_situation_and_params()
                        if situation is None:
                            return
                        guest_list = SituationGuestList(invite_only=True)
                        guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, situation.default_job(), RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH, expectation_preference=True))
                        situation_id = situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False)
                        if situation_id is None:
                            logger.error('Trying to create a new player customer situation for small business but failed.')
                        else:
                            self._customer_situation_ids.append(situation_id)
            if sim_info.household.id == business_owner_household_id:
                pass
            else:
                situation = None
                if sim_info.is_player_sim:
                    situation = self.player_customer_situation
                else:
                    (situation, _) = self.customer_situation_type_curve.get_situation_and_params()
                if situation is None:
                    return
                guest_list = SituationGuestList(invite_only=True)
                guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, situation.default_job(), RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH, expectation_preference=True))
                situation_id = situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False)
                if situation_id is None:
                    logger.error('Trying to create a new player customer situation for small business but failed.')
                else:
                    self._customer_situation_ids.append(situation_id)

    def start_traveled_sims_customer_situations(self):
        sim_info_manager = services.sim_info_manager()
        traveled_sims = sim_info_manager.get_traveled_to_zone_sim_infos()
        self.start_sims_customer_situations(traveled_sims)

    def start_owner_employee_situation(self, owner_sim_id:'int', is_npc:'bool'):
        situation_manager = services.get_zone_situation_manager()
        sim_info = services.sim_info_manager().get(owner_sim_id)
        situation = self.npc_owner_situation if is_npc else self.owner_situation
        if situation is None:
            return
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, situation.default_job(), RequestSpawningOption.DONT_CARE, BouncerRequestPriority.GAME_BREAKER, expectation_preference=True))
        situation_id = situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False)
        if situation_id is None:
            logger.error('Trying to create a new player employee situation for small business but failed.')
        if is_npc:
            self._employee_situation_ids[SmallBusinessTunables.EMPLOYEE_TYPE].add(situation_id)

    def create_situations_during_zone_spin_up(self):
        if self.business_manager is not None and self.business_manager.is_open and self.business_manager.business_type == BusinessType.SMALL_BUSINESS:
            self._business_manager.start_already_opened_business()
        super().create_situations_during_zone_spin_up()
