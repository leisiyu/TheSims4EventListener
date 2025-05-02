from __future__ import annotationsfrom sims4 import mathfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import flexmethod, classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_types import SituationMedalfrom typing import TYPE_CHECKINGfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetif TYPE_CHECKING:
    from typing import *
    from filters.tunable import FilterResultfrom event_testing.resolver import SingleActorAndObjectResolver, SingleSimResolverfrom event_testing.test_variants import TunableSituationRoleTestfrom situations.complex.instructed_class_situation_mixin import InstructedClassSituationMixin, _PreClassState, ClassReadyFlagsfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonSituationState, CommonInteractionCompletedSituationStatefrom situations.complex.guided_meditation_situation import _GuidedMeditationStatefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable import TunableTuple, TunableSimMinute, TunableList, TunableReference, TunableIntervalimport servicesimport sims4.logfrom small_business.small_business_tuning import SmallBusinessTunableslogger = sims4.log.Logger('Hobby Class', default_owner='rahissamiyordi')
class _PreHobbyClassState(_PreClassState):

    def __init__(self, **kwargs):
        super(_PreClassState, self).__init__(**kwargs)
        self._ready_flags = ClassReadyFlags.NONE

    def register_event(self):
        pass

    def _try_advance_state(self):
        if self._ready_flags == ClassReadyFlags.TIME_EXPIRED:
            instructor = next(iter(self.owner.all_sims_in_job_gen(self.owner.instructor_job)), None)
            if instructor is None:
                self.owner.add_situation_encouragement_buff()
                self.owner._self_destruct()
            self.owner._add_npc_class_members()
            if not self.owner.cancel_class_if_no_attendees():
                self.owner.remove_situation_encouragement_buff(instructor)
                self.owner.advance_state()

class _InHobbyClassState(_GuidedMeditationState):

    def on_activate(self, reader=None):
        super(CommonInteractionCompletedSituationState, self).on_activate(reader)

class HobbyClassSituation(InstructedClassSituationMixin, SituationComplexCommon):
    REMOVE_INSTANCE_TUNABLES = ('post_class_state', '_buff', 'targeted_situation', '_resident_job', '_relationship_between_job_members', 'audio_sting_on_start', 'background_audio', 'instructor_in_position_interaction', 'force_invite_only', 'class_member_requirement') + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES
    INSTANCE_TUNABLES = {'pre_class_state': TunableTuple(description='\n                Pre Class Situation State.\n                ', situation_state=_PreHobbyClassState.TunableFactory(locked_args={'time_out': None}), time_out=TunableSimMinute(description='\n                   How long the pre class session will last.\n                   ', default=15, minimum=1), tuning_group=GroupNames.STATE), 'in_class_state': _InHobbyClassState.TunableFactory(description='\n            In class state, where the hobbies class occurs.\n            ', tuning_group=GroupNames.STATE), 'finished_class_loots': TunableList(description='\n            Loots that will apply when the situation ends. Canceled or completed.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True), tuning_group=GroupNames.SITUATION), 'number_of_npc_class_members': TunableInterval(description='\n            The range in % of how many NPCs of the business will join the class. This percentage will be\n            multiplied by the business rank to increase or decrease the number of attendees in the class \n            depending on how the business rank is.\n            ', tunable_type=int, default_lower=20, default_upper=70, minimum=0, maximum=100, tuning_group=GroupNames.SITUATION), 'member_situation_role_test': TunableSituationRoleTest(description='\n            The situation role test to determine whether npc sim should be\n            picked as class member depending on their roles.\n            ', tuning_group=GroupNames.SITUATION), 'no_class_members_dialog': TunableUiDialogNotificationSnippet(description='\n            The notification to display if there are no class members in position to start the class.\n            ', tuning_group=GroupNames.SITUATION)}

    def __init__(self, *arg, **kwargs):
        self._time_out_finished = False
        super().__init__(*arg, **kwargs)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreHobbyClassState, factory=cls.pre_class_state.situation_state), SituationStateData(2, _InHobbyClassState, factory=cls.in_class_state))

    @classmethod
    def default_job(cls):
        return cls._class_member_job

    @flexmethod
    def get_level_data(cls, inst, medal:'SituationMedal'=SituationMedal.TIN):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.situation_level_data is None:
            return
        if not inst_or_cls._time_out_finished:
            medal = SituationMedal.TIN
        return inst_or_cls.situation_level_data[medal].level_data

    @classproperty
    def should_remove_encouragement_buff(cls):
        return True

    def advance_state(self):
        next_state = self.get_next_class_state()
        self._change_state(next_state())

    def get_situation_goal_actor(self):
        if self._guest_list is None:
            return
        else:
            return services.sim_info_manager().get(self._guest_list.host_sim_id)

    def get_member_number(self) -> 'int':
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        if business_manager is None:
            return 0
        num_customers = len(business_manager._customer_manager._customers)
        sim_info = services.sim_info_manager().get(business_manager.owner_sim_id)
        rank_stat = sim_info.get_statistic(SmallBusinessTunables.SMALL_BUSINESS_RANK_RANKED_STATISTIC)
        rank_level = rank_stat.rank_level
        lower_bound = self.number_of_npc_class_members.lower_bound
        upper_bound = self.number_of_npc_class_members.upper_bound
        starting_rank = rank_stat.starting_rank_display_value
        max_rank = rank_stat.max_rank
        if rank_level <= starting_rank:
            percentage_attendees = lower_bound
        elif rank_level >= max_rank:
            percentage_attendees = upper_bound
        else:
            percentage_attendees = lower_bound + (upper_bound - lower_bound)*(rank_level - starting_rank)/(max_rank - starting_rank)
        member_num = math.ceil(percentage_attendees/100*num_customers)
        return member_num

    def get_tested_filter_result(self, filter_result_list:'List[FilterResult]') -> 'List[FilterResult]':
        tested_filter_result_job_list = []
        tested_filter_result_list = []
        for filter_result in filter_result_list:
            single_sim_resolver = SingleSimResolver(filter_result.sim_info)
            if single_sim_resolver(self.member_situation_job_test):
                tested_filter_result_job_list.append(filter_result)
        for filter_job_result in tested_filter_result_job_list:
            single_sim_resolver = SingleSimResolver(filter_job_result.sim_info)
            if single_sim_resolver(self.member_situation_role_test):
                tested_filter_result_list.append(filter_job_result)
        return tested_filter_result_list

    def _apply_finished_class_loots(self):
        instructor_sim_info = next(iter(sim.sim_info for sim in self.all_sims_in_job_gen(self.instructor_job)), None)
        class_member_sim_infos = tuple(sim.sim_info for sim in self.all_sims_in_job_gen(self._class_member_job))
        if instructor_sim_info is not None:
            resolver = SingleActorAndObjectResolver(instructor_sim_info, self.instructor_staffed_object, self)
            for loot in self.finished_class_loots:
                loot.apply_to_resolver(resolver)
        if not class_member_sim_infos:
            return
        for class_member_sim_info in class_member_sim_infos:
            resolver = SingleActorAndObjectResolver(class_member_sim_info, self.instructor_staffed_object, self)
            for loot in self.finished_class_loots:
                loot.apply_to_resolver(resolver)

    def _destroy(self):
        self.add_situation_encouragement_buff()
        self._apply_finished_class_loots()
        self._reset_all_goals()
        super(SituationComplexCommon, self)._destroy()

    def get_target_object(self):
        return self.instructor_staffed_object

    def get_next_class_state(self) -> '_InHobbyClassState':
        return self.in_class_state

    def add_situation_encouragement_buff(self):
        situation_manager = services.get_zone_situation_manager()
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_zone(services.current_zone_id())
        for sim in self._situation_sims:
            attendee_situations = situation_manager.get_situations_sim_is_in(sim)
            for situation in attendee_situations:
                if situation.should_have_encouragement_buff and situation.encouragement_buff is not None:
                    sim.add_buff(situation.encouragement_buff, additional_static_commodities_to_add=(business_manager.encouragement_commodity,))

    def _situation_timed_out(self, _):
        self._distribute_post_class_loots()
        self._time_out_finished = True
        super(SituationComplexCommon, self)._situation_timed_out(self)

    def cancel_class_if_no_attendees(self):
        if not any(self.all_sims_in_job_gen(self._class_member_job)):
            self._show_no_class_members_notification()
            self._self_destruct()
            return True

    def _show_no_class_members_notification(self):
        instructor = next(iter(self.all_sims_in_job_gen(self.instructor_job)), None)
        if instructor is None:
            return
        resolver = SingleSimResolver(instructor.sim_info)
        dialog = self.no_class_members_dialog(instructor.sim_info, resolver=resolver)
        dialog.show_dialog()

    def _reset_all_goals(self):
        self._goal_tracker.reset_all_goals_gen()
lock_instance_tunables(InstructedClassSituationMixin, exclusivity=BouncerExclusivityCategory.HOBBY_CLASS)