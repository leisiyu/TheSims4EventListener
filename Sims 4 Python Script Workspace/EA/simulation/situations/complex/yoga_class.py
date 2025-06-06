from event_testing.resolver import SingleSimResolverfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_liabilities import SituationLiability, SITUATION_LIABILITYfrom scheduler import SituationWeeklySchedulefrom sims4.tuning.tunable import TunableInterval, TunableVariant, TunableTuple, TunableSimMinute, TunableList, TunableSet, TunableEnumWithFilter, TunableMapping, TunableEnumEntry, OptionalTunable, TunableReference, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.complex.instructed_class_situation_mixin import InstructedClassSituationMixin, _PreClassState, _PostClassStatefrom situations.situation import Situationfrom situations.situation_by_definition_or_tags import SituationSearchByDefinitionOrTagsVariantfrom situations.situation_complex import SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport enumimport servicesimport sims4import situationsimport taglogger = sims4.log.Logger('Yoga Class', default_owner='jdimailig')
class _ClassPoseState(CommonInteractionCompletedSituationState):
    CLASS_MEMBER_DELAY_TIMEOUT = 'class_member_delay_timeout'
    MISS_INTERACTION_TIMEOUT = 'miss_interaction_timeout'
    FACTORY_TUNABLES = {'member_delay_time': TunableInterval(description='\n            The delay between when the instructor does a pose and when a class\n            member copies that pose.\n            ', tunable_type=float, default_lower=1, default_upper=2), 'miss_interaction_time_delay': TunableSimMinute(description='\n            The delay if the interaction we are monitoring to finish this state\n            is missing, we will move on.\n            ', default=30)}

    def __init__(self, member_delay_time, miss_interaction_time_delay, **kwargs):
        super().__init__(**kwargs)
        self.member_delay_time = member_delay_time
        self.miss_interaction_time_delay = miss_interaction_time_delay

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self.owner is None:
            return
        class_member_job = self.owner.get_class_member_job()
        for sim in self.owner.all_sims_in_job_gen(class_member_job):
            alarm_name = '{}_{}'.format(self.CLASS_MEMBER_DELAY_TIMEOUT, sim.id)
            class_member_delay = self.member_delay_time.random_float()
            self._create_or_load_alarm(alarm_name, class_member_delay, lambda _, sim=sim: self._member_delay_timer_expired(sim), should_persist=True)
        self._create_or_load_alarm(self.MISS_INTERACTION_TIMEOUT, self.miss_interaction_time_delay, lambda _: self._on_interaction_of_interest_complete(), should_persist=True)

    def _member_delay_timer_expired(self, sim):
        class_member_job = self.owner.get_class_member_job()
        role_state = self._job_and_role_changes.get(class_member_job)
        if role_state is None:
            logger.error("{} doesn't have role state for job {}", self, class_member_job)
            return
        if self.owner.sim_has_job(sim, class_member_job):
            self.owner._set_sim_role_state(sim, role_state)

    def _set_job_role_state(self):
        class_member_job = self.owner.get_class_member_job()
        for (job, role_state) in self._job_and_role_changes.items():
            if job is not class_member_job:
                self.owner._set_job_role_state(job, role_state)

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, resolver=None, sim_info=None, **kwargs):
        if self.owner is None and resolver is not None:
            logger.error('Yoga class situation no longer attached to {} upon completion of {} by {}', type(self), resolver.interaction.affordance, sim_info)
            return
        self.owner.advance_state()

class _ClassPoseBridge(_ClassPoseState):
    pass

class _ClassPoseDance(_ClassPoseState):
    pass

class _ClassPoseDownwardDog(_ClassPoseState):
    pass

class _ClassPoseGreeting(_ClassPoseState):
    pass

class _ClassPoseHalfMoon(_ClassPoseState):
    pass

class _ClassPoseHalfMoon_Mirror(_ClassPoseState):
    pass

class _ClassPoseTree(_ClassPoseState):
    pass

class _ClassPoseTree_Mirror(_ClassPoseState):
    pass

class _ClassPoseTriangle(_ClassPoseState):
    pass

class _ClassPoseTriangle_Mirror(_ClassPoseState):
    pass

class _ClassPoseCorpse(_ClassPoseState):
    pass

class _ClassPoseBoat(_ClassPoseState):
    pass

class _ClassPoseWarrior(_ClassPoseState):
    pass

class _ClassPoseHandstand(_ClassPoseState):
    pass

class _ClassPoseSidePlank(_ClassPoseState):
    pass

class _ClassPoseSidePlank_Mirror(_ClassPoseState):
    pass

class ClassPoseVariant(TunableVariant):

    def __init__(self, description='The variant of different class poses.', **kwargs):
        super().__init__(description=description, pose_greeting=_ClassPoseGreeting.TunableFactory(), pose_bridge=_ClassPoseBridge.TunableFactory(), pose_dance=_ClassPoseBridge.TunableFactory(), pose_downwarddog=_ClassPoseDownwardDog.TunableFactory(), pose_halfmoon=_ClassPoseHalfMoon.TunableFactory(), pose_halfmoon_mirror=_ClassPoseHalfMoon_Mirror.TunableFactory(), pose_tree=_ClassPoseTree.TunableFactory(), pose_tree_mirror=_ClassPoseTree_Mirror.TunableFactory(), pose_triangle=_ClassPoseTriangle.TunableFactory(), pose_triangle_mirror=_ClassPoseTriangle_Mirror.TunableFactory(), pose_Corpse=_ClassPoseCorpse.TunableFactory(), pose_boat=_ClassPoseBoat.TunableFactory(), pose_warrior=_ClassPoseWarrior.TunableFactory(), pose_handstand=_ClassPoseHandstand.TunableFactory(), pose_sideplank=_ClassPoseSidePlank.TunableFactory(), pose_sideplank_mirror=_ClassPoseSidePlank_Mirror.TunableFactory(), default='pose_greeting', **kwargs)

class ClassPoseEnum(enum.Int):
    GREETING = 0
    BRIDGE = 1
    DANCE = 2
    DOWNWARD_DOG = 3
    HALFMOON = 4
    TREE = 5
    TRIANGLE = 6
    CORPSE = 7
    BOAT = 8
    WARRIOR = 9
    HANDSTAND = 10
    SIDEPLANK = 11
    HALFMOON_MIRRORED = 12
    SIDEPLANK_MIRRORED = 13
    TREE_MIRRORED = 14
    TRIANGLE_MIRRORED = 15
INSTRUCTOR_STAFFED_OBJECT = 'instructor_staffed_object'TEMP_OBJECT_IDS = 'temporary_object_ids'YOGA_CLASS_GROUP = 'Yoga Class'
class YogaClassSituation(InstructedClassSituationMixin, situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'class_pose_map': TunableMapping(description='\n            The static map to mapping yoga pose state to the certain pose enum.\n            Put it here instead of in the module tuning is for pack safe reason.\n            This should only be tuned on prototype, and not suggesting to change/override\n            in tuning instance unless you have very strong reason.\n            ', key_type=TunableEnumEntry(tunable_type=ClassPoseEnum, default=ClassPoseEnum.GREETING), key_name='pose_enum', value_type=ClassPoseVariant(), value_name='pose_content', tuning_group=YOGA_CLASS_GROUP), 'class_pose_states': TunableList(description='\n                The sequence of the yoga poses we want the class to run.\n                ', tunable=TunableEnumEntry(tunable_type=ClassPoseEnum, default=ClassPoseEnum.GREETING), tuning_group=GroupNames.STATE), '_alternate_instructor_job': TunableReference(description='\n                The situation job given to instructors staffing a mat if the player uses it to host their own class.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',), tuning_group=GroupNames.SITUATION), 'instructor_situations': SituationSearchByDefinitionOrTagsVariant(description="\n            Situations that define NPC instructors.  NPC instructors will normally be on the guest list for scheduled\n            classes, but player-run classes that are run on instructor's mats will find the instructor tied to the mat\n            using this tuning in order to place them into the 'alternate instructor job'.\n            ", tuning_group=GroupNames.SITUATION), 'instructor_mat_tags': TunableSet(description="\n                The instructor's yoga mat tags.\n                ", tunable=TunableEnumWithFilter(tunable_type=tag.Tag, filter_prefixes=('Func_YogaClass',), default=tag.Tag.INVALID), tuning_group=YOGA_CLASS_GROUP)}
    REMOVE_INSTANCE_TUNABLES = set(Situation.SITUATION_SCORING_REMOVE_INSTANCE_TUNABLES + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES + Situation.SITUATION_USER_FACING_REMOVE_INSTANCE_TUNABLES + ('_instructor_job',)) - {'_display_name', 'venue_situation_player_job'}

    @classmethod
    def _states(cls):
        class_pose_map = cls.class_pose_map
        situation_states = [SituationStateData(1, _PreClassState, factory=cls.pre_class_state.situation_state), SituationStateData(2, _PostClassState, factory=cls.post_class_state.situation_state), SituationStateData(3, _ClassPoseBridge, factory=class_pose_map[ClassPoseEnum.BRIDGE]), SituationStateData(4, _ClassPoseDance, factory=class_pose_map[ClassPoseEnum.DANCE]), SituationStateData(5, _ClassPoseDownwardDog, factory=class_pose_map[ClassPoseEnum.DOWNWARD_DOG]), SituationStateData(6, _ClassPoseGreeting, factory=class_pose_map[ClassPoseEnum.GREETING]), SituationStateData(7, _ClassPoseHalfMoon, factory=class_pose_map[ClassPoseEnum.HALFMOON]), SituationStateData(8, _ClassPoseTree, factory=class_pose_map[ClassPoseEnum.TREE]), SituationStateData(9, _ClassPoseTriangle, factory=class_pose_map[ClassPoseEnum.TRIANGLE]), SituationStateData(10, _ClassPoseCorpse, factory=class_pose_map[ClassPoseEnum.CORPSE]), SituationStateData(11, _ClassPoseBoat, factory=class_pose_map[ClassPoseEnum.BOAT]), SituationStateData(12, _ClassPoseWarrior, factory=class_pose_map[ClassPoseEnum.WARRIOR]), SituationStateData(13, _ClassPoseHandstand, factory=class_pose_map[ClassPoseEnum.HANDSTAND]), SituationStateData(14, _ClassPoseSidePlank, factory=class_pose_map[ClassPoseEnum.SIDEPLANK])]
        factory_method = class_pose_map.get(ClassPoseEnum.TREE_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(15, _ClassPoseTree_Mirror, factory=factory_method))
        factory_method = class_pose_map.get(ClassPoseEnum.TRIANGLE_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(16, _ClassPoseTriangle_Mirror, factory=class_pose_map[ClassPoseEnum.TRIANGLE_MIRRORED]))
        factory_method = class_pose_map.get(ClassPoseEnum.HALFMOON_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(17, _ClassPoseHalfMoon_Mirror, factory=class_pose_map[ClassPoseEnum.HALFMOON_MIRRORED]))
        factory_method = class_pose_map.get(ClassPoseEnum.SIDEPLANK_MIRRORED, None)
        if factory_method is not None:
            situation_states.append(SituationStateData(18, _ClassPoseSidePlank_Mirror, factory=class_pose_map[ClassPoseEnum.SIDEPLANK_MIRRORED]))
        return tuple(situation_states)

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._next_pose_index = 0

    def load_situation(self):
        load_result = super().load_situation()
        if load_result:
            self._load_class_pose_index()
        return load_result

    def _load_class_pose_index(self):
        curr_pose = next((pose for (pose, state) in self.class_pose_map.items() if state.factory is type(self._cur_state)), None)
        if curr_pose is not None:
            self._next_pose_index = self.class_pose_states.index(curr_pose) + 1

    @property
    def instructor_job(self):
        return self.venue_situation_player_job

    def _set_instructor_staffed_object(self):
        reader = self._seed.custom_init_params_reader
        if reader is None:
            default_target_id = self._seed.extra_kwargs.get('default_target_id', None)
        else:
            default_target_id = reader.read_uint64(INSTRUCTOR_STAFFED_OBJECT, None)
        if default_target_id is not None:
            self._instructor_staffed_object = services.object_manager().get(default_target_id)
        elif self._instructor_staffed_object is None:
            self._instructor_staffed_object = self._find_instructor_staffed_object()
        if self._instructor_staffed_object is None:
            self._self_destruct()

    def _find_instructor_staffed_object(self):
        object_manager = services.object_manager()
        yoga_mat_tags = self.instructor_mat_tags
        yoga_mat_list = list(object_manager.get_objects_with_tags_gen(*yoga_mat_tags))
        return next(iter(yoga_mat_list), None)

    def _validate_instructors(self):
        lead_instructor = super()._validate_instructors()
        if lead_instructor is not None:
            self._reassign_instructors(lead_instructor)
        return lead_instructor

    def _reassign_instructors(self, lead_instructor):
        instructor_situations = self.instructor_situations.get_all_matching_situations()
        for yoga_idle_situation in instructor_situations:
            staffed_object = yoga_idle_situation.get_staffed_object()
            if staffed_object is not self._instructor_staffed_object:
                pass
            else:
                yoga_instructor = next(yoga_idle_situation.all_sims_in_situation_gen(), None)
                if yoga_instructor is not lead_instructor:
                    self.invite_sim_to_job(yoga_instructor.sim_info, self._alternate_instructor_job)

    def get_next_class_state(self):
        next_state = None
        if self._next_pose_index < len(self.class_pose_states):
            next_state_enum = self.class_pose_states[self._next_pose_index]
            next_state = self.class_pose_map[next_state_enum]
            self._next_pose_index += 1
        else:
            next_state = self.post_class_state.situation_state
        return next_state

    def on_hit_their_marks(self):
        instructor_sim = next(self.all_sims_in_job_gen(self.instructor_job), None)
        if instructor_sim is None:
            self._self_destruct()
            return
        super().on_hit_their_marks()
        instructor_si = next(iter(interaction for interaction in instructor_sim.get_all_running_and_queued_interactions() if interaction.affordance is self.instructor_in_position_interaction), None)
        if instructor_si is None:
            self._self_destruct()
            return
        situation_liability = SituationLiability(self)
        instructor_si.add_liability(SITUATION_LIABILITY, situation_liability)

class YogaClassScheduleMixin:
    INSTANCE_TUNABLES = {'yoga_class': OptionalTunable(description='\n            When enabled, this zone director has the ability to schedule classes according\n            to a tuned yoga_class_schedule.\n            ', tunable=TunableTuple(yoga_class_schedule=SituationWeeklySchedule.TunableFactory(description='\n                    The schedule to trigger yoga class automatically.\n                    ', schedule_entry_data={'pack_safe': True}), yoga_instructor_idle_situation=TunablePackSafeReference(description="\n                    The idle situation to find an NPC yoga instructor to lead a scheduled yoga class.\n                    \n                    A scheduled class cannot start unless there is a free idle instructor in the zone.\n                     \n                    The situation tuned here is normally scheduled in the zone director's situation shifts.\n                    ", manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), yoga_class_starting_notification=TunableUiDialogNotificationSnippet(description='\n                    The notification that is displayed whenever an NPC run yoga class starts.\n                    ')), tuning_group=YOGA_CLASS_GROUP)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._yoga_class_schedule = None
        if self.yoga_class.yoga_class_schedule is not None:
            self._yoga_class_schedule = self.yoga_class.yoga_class_schedule(start_callback=self._start_yoga_class)

    def on_shutdown(self):
        super().on_shutdown()
        if self._yoga_class_schedule is not None:
            self._yoga_class_schedule.destroy()

    def _start_yoga_class(self, scheduler, alarm_data, extra_data):
        entry = alarm_data.entry
        yoga_class_situation_type = entry.situation
        situation_manager = services.get_zone_situation_manager()
        for yoga_idle_situation in situation_manager.get_situations_by_type(self.yoga_class.yoga_instructor_idle_situation):
            yoga_instructor = next(yoga_idle_situation.all_sims_in_situation_gen(), None)
            if yoga_instructor is None:
                logger.warn('No yoga instructor found in the yoga idle situation, cannot start class')
            else:
                yoga_instructor_mat = yoga_idle_situation.get_staffed_object()
                if yoga_instructor_mat is None:
                    logger.warn('Yoga instructor is not yet staffing a yoga mat.')
                elif any(yoga_class_situation_type.tags & situation.tags for situation in situation_manager.get_situations_sim_is_in(yoga_instructor)):
                    pass
                else:
                    instructor_sis = yoga_instructor.get_all_running_and_queued_interactions()
                    for si in instructor_sis:
                        si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='YogaClassStart')
                    guest_list = SituationGuestList()
                    guest_info = SituationGuestInfo.construct_from_purpose(yoga_instructor.id, yoga_class_situation_type.venue_situation_player_job, SituationInvitationPurpose.INVITED)
                    guest_list.add_guest_info(guest_info)
                    try:
                        creation_source = self.instance_name
                    except:
                        creation_source = 'yoga class start'
                    created_class_id = situation_manager.create_situation(yoga_class_situation_type, guest_list=guest_list, user_facing=False, default_target_id=yoga_instructor_mat.id, creation_source=creation_source)
                    class_situation = situation_manager.get(created_class_id)
                    invited_sim = services.get_active_sim()
                    if invited_sim is None:
                        pass
                    else:
                        class_member_job = class_situation.get_class_member_job()
                        if class_member_job.can_sim_be_given_job(invited_sim.id, invited_sim.sim_info):
                            resolver = SingleSimResolver(yoga_instructor)
                            dialog = self.yoga_class.yoga_class_starting_notification(yoga_instructor.sim_info, resolver=resolver)
                            dialog.show_dialog(additional_tokens=(class_situation.display_name,))
