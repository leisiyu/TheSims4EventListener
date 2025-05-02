from __future__ import annotationsfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKINGfrom sims4.tuning.tunable import TunableReferenceif TYPE_CHECKING:
    from typing import *from buffs.buff import Bufffrom business.business_employee_situation_mixin import BusinessEmployeeSituationMixinfrom business.business_enums import BusinessTypefrom event_testing.test_events import TestEventfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypefrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom situations.situation_complex import CommonSituationState, SituationStateData, SituationComplexCommon, TunableInteractionOfInterest, TunableListfrom sims4.tuning.instances import create_tuning_blueprint_classfrom small_business.small_business_tuning import SmallBusinessTunablesimport sims4import serviceslogger = sims4.log.Logger('SmallBusinessSituation', default_owner='mmikolajczyk')
class _BusinessWork(CommonSituationState):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self, reader=None):
        super().on_activate(reader)
        business_manager = services.business_service().get_business_manager_for_zone(services.current_zone_id())
        if business_manager is None:
            logger.error('No business manager found')
            return

        def create_small_business_identifiable_tuning(base_class, name):
            tuning_blueprint_cls = create_tuning_blueprint_class(base_class)
            tuning_blueprint = tuning_blueprint_cls(name)
            return tuning_blueprint

        sim_info_manager = services.sim_info_manager()
        for guest_info in self.owner.guest_list.guest_info_gen():
            employee_data = business_manager.get_employee_assignment(guest_info.sim_id)
            if employee_data is None:
                pass
            else:
                self.owner.encouragement_buff = create_small_business_identifiable_tuning(Buff, business_manager.employee_encouragement_name + str(guest_info.sim_id))
                self.owner.encouragement_buff.visible = False
                sim = sim_info_manager.get(guest_info.sim_id)
                commodity = employee_data.encouragement
                commodity.ad_data = SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_AD_DATA if sim.is_player_sim else SmallBusinessTunables.BUSINESS_ENCOURAGEMENT_AD_DATA_ACTIVE_SIM
                sim.add_buff(self.owner.encouragement_buff, additional_static_commodities_to_add=(commodity,))

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, role_affordance_target)

class SmallBusinessEmployeeSituation(BusinessEmployeeSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'_default_job': sims4.tuning.tunable.TunableReference(description='\n            The default job for this situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), 'business_work': _BusinessWork.TunableFactory(description='\n            The state where employees work at the business.\n            ', display_name='Work at the business', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'go_home_interaction': TunableInteractionOfInterest(description='\n            The interaction that, when run on an employee, will have them end\n            this situation and go home.\n            '), 'change_to_default_ouftit_affordance': TunableReference(description='\n             The affordance used to make household sims change into regular clothes.\n             ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'end_of_shift_loot': TunableList(description='\n            A list of loot operations to apply before the employee ends the work\n            situation.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}

    def __init__(self, seed):
        super().__init__(seed)
        self.encouragement_buff = None
        self._employee_sim_info = None
        services.get_event_manager().register_single_event(self, TestEvent.InteractionComplete)
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.go_home_interaction.custom_keys_gen())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.business_work())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete:
            target_sim = resolver.interaction.get_participant(ParticipantType.TargetSim)
            if target_sim and target_sim.sim_info is self._employee_sim_info and resolver(self.go_home_interaction):
                self._on_business_closed()
        super().handle_event(sim_info, event, resolver)

    def get_employee_sim_info(self):
        for guest_info in self.guest_list.guest_info_gen():
            return services.sim_info_manager().get(guest_info.sim_id)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._employee_sim_info = sim.sim_info
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and sim.sim_info.sim_id != business_manager.owner_sim_id:
            self._clock_in()
            if business_manager.business_type == BusinessType.SMALL_BUSINESS:
                career = business_manager.get_employee_career(sim.sim_info)
                if career is not None and self._on_business_removed not in career.on_business_removed:
                    career.on_business_removed.append(self._on_business_removed)

    def _on_business_removed(self, owner_id):
        business_manager = services.business_service().get_business_manager_for_sim(owner_id)
        if business_manager is not None and business_manager.is_open:
            self._on_business_closed()
        return True

    def _on_business_closed(self):
        super()._on_business_closed()
        if self._employee_sim_info is not None:
            resolver = SingleSimResolver(self._employee_sim_info)
            for loot in self.end_of_shift_loot:
                loot.apply_to_resolver(resolver)

    def _destroy(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS and self._employee_sim_info is not None:
            career = business_manager.get_employee_career(self._employee_sim_info)
            if career is not None and self._on_business_removed in career.on_business_removed:
                career.on_business_removed.remove(self._on_business_removed)
        super()._destroy()

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        business_manager = services.business_service().get_business_manager_for_zone(services.current_zone_id())
        if business_manager is not None and not (business_manager.is_employee(sim.sim_info) or sim.sim_id == business_manager.owner_sim_id):
            return
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=None)
        if business_manager is not None and business_manager.small_business_income_data is not None:
            business_manager.small_business_income_data.start_interaction_sales_markup_tracking_for_sim(sim.sim_id)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        business_manager = services.business_service().get_business_manager_for_zone(services.current_zone_id())
        if business_manager is not None and business_manager.small_business_income_data is not None:
            business_manager.small_business_income_data.stop_interaction_sales_markup_tracking_for_sim(sim.sim_id)
        if self.encouragement_buff is not None:
            sim.remove_buff_by_type(self.encouragement_buff)
        if self._employee_sim_info.household_id == services.active_household().id:
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.Low)
            sim.push_super_affordance(self.change_to_default_ouftit_affordance, sim, context)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls._default_job, cls.business_work)]

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _BusinessWork, factory=cls.business_work)]

    @classmethod
    def default_job(cls):
        return cls._default_job

    @classmethod
    def get_tuned_jobs(cls):
        return [cls._default_job]

    @classproperty
    def should_have_encouragement_buff(cls):
        return True
