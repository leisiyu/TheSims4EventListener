from event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom filters.tunable import TraitFilterTermfrom interactions.base.create_object_interaction import CreateCarriedObjectSuperInteractionfrom interactions.context import InteractionContext, QueueInsertStrategyfrom sims4.tuning.tunable import TunableList, TunableTuple, Tunable, TunableInterval, TunableReference, TunableEnumWithFilter, TunableEnumEntry, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom tag import Tagimport interactionsimport itertoolsimport randomimport servicesimport sims4logger = sims4.log.Logger('ProtesterSituation', default_owner='jdimailig')
class _ProtestingState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'attractor_point_identifier': TunableEnumWithFilter(description='\n            The identifier that will be used to select which attractor points\n            we will use.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=('AtPo',), tuning_group=GroupNames.PICKERTUNING), 'create_sign_interaction': TunableReference(description='\n            Interaction which will create the protester sign and kick off the protest\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('CreateCarriedObjectSuperInteraction',)), 'fallback_signs': TunableList(description='\n            The list of possible signs to use if no suitable sign could be found.\n            These should be a fairly generic signs.\n            ', tunable=TunableReference(manager=services.definition_manager())), 'locked_args': {'job_and_role_changes': sims4.collections.frozendict(), 'allow_join_situation': False, 'time_out': None}}

    def __init__(self, attractor_point_identifier, create_sign_interaction, fallback_signs, **kwargs):
        super().__init__(**kwargs)
        self._attractor_point_identifier = attractor_point_identifier
        self._create_sign_interaction = create_sign_interaction
        self._fallback_signs = fallback_signs
        self._sign_definition = None

    def set_sign_definition(self, sign_definition):
        self._sign_definition = sign_definition

    def get_sign_definition(self):
        if self._sign_definition is None:
            protestable = self.owner.find_protestable_using_guest_list()
            if protestable is not None:
                self._sign_definition = protestable.sign_definition
        if self._fallback_signs:
            self._sign_definition = random.choice(self._fallback_signs)
        if not (self._sign_definition is None and self._sign_definition):
            logger.error('Could not find a sign for the protester to hold.  Please verify tuning on situation: {0}.', self.owner)
        return self._sign_definition

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
        attractor_points = list(services.object_manager().get_objects_with_tag_gen(self._attractor_point_identifier))
        chosen_point = random.choice(attractor_points) if attractor_points else None
        if chosen_point == None:
            logger.warn('No attractor points with tag {} found for situation {}.', self._attractor_point_identifier, self.owner)
        sign_definition = self.get_sign_definition()
        if sign_definition is not None:
            sim.push_super_affordance(self._create_sign_interaction, chosen_point, context, **{CreateCarriedObjectSuperInteraction.INTERACTION_PARAM_KEY: sign_definition})
        return (role_state_type, role_affordance_target)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def _additional_tests(self, sim_info, event, resolver):
        if sim_info.is_selectable or sim_info in [sim.sim_info for sim in self.owner.all_sims_in_situation_gen()]:
            return True
        return False

class ProtestSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'number_of_protesters': TunableInterval(description='\n                The number of other protesters to bring to the situation.\n                \n                This is an inclusive min/max range.\n                ', tunable_type=float, minimum=1, default_lower=3, default_upper=5, tuning_group=GroupNames.SITUATION), 'protester_job': TunablePackSafeReference(description='\n                The SituationJob for the Protester.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',), tuning_group=GroupNames.SITUATION), 'protester_role': TunablePackSafeReference(description='\n                The SituationRole for the Protester.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), class_restrictions=('RoleState',), tuning_group=GroupNames.SITUATION), 'protester_search_filter': TunablePackSafeReference(description='\n                Sim filter used to find sims or conform them into protesters.\n                We will select the cause for the protesters at runtime \n                from the specified weighted causes list below.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('DynamicSimFilter',), tuning_group=GroupNames.SITUATION), 'protesting_situation_state': _ProtestingState.TunableFactory(description='\n                The protest state.  Interactions of interest should be set \n                to interactions that may be run in order to end the situation.\n                ', tuning_group=GroupNames.SITUATION), 'protestables': TunableList(description='\n            List of possible protests and the signs for them.\n            These will be picked from based off the cause\n            ', tunable=TunableTuple(description='\n                A protestable.  It is a cause and the sign to use for the cause.\n                ', sign_definition=TunableReference(description='\n                    The definition of a protester flag.\n                    ', manager=services.definition_manager()), cause=TunableReference(description='\n                    The trait associated with this flag.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True)), tuning_group=GroupNames.SITUATION), 'weighted_causes': TunableList(description='\n            A weighted list of causes to choose for the protest.  We will pick\n            a random cause from this list as the subject of the protest.\n            ', tunable=TunableTuple(cause=TunablePackSafeReference(description='\n                    The cause that this protest will promote/protest.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',)), weight=Tunable(tunable_type=int, default=1)), tuning_group=GroupNames.SITUATION), 'allow_instanced_sims_as_protesters': Tunable(description="\n            Whether or not to allow usage of instanced Sims as protesters.  Usually you will only want non-instanced\n            Sims so that the situation can spawn and create them as needed.  For example in City Life, protesters\n            would spawn and congregate in the open street, and we didn't want them to be just any person already in the\n            world.  For Multi-Unit Tenant Revolts, we are okay with tenants instanced in world to be included.\n            \n            IMPORTANT: Note that if you want to a allow instanced Sims, you have to enable allow_repurpose_game_breaker \n            on the Sim filter terms for the situation job if you need to repurpose instanced Sims.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), 'protester_request_priority': TunableEnumEntry(description='\n            Define the request priority for protesters.  This determines the importance of Sims filling this situation \n            over any other situations requesting Sims. \n            ', tunable_type=BouncerRequestPriority, default=BouncerRequestPriority.BACKGROUND_LOW, invalid_enums=(BouncerRequestPriority.GAME_BREAKER, BouncerRequestPriority.LEAVE), tuning_group=GroupNames.SITUATION), 'protester_exclusion_tests': TunableTestSet(description='\n            A set of tests that are run on sims found via the filter.  If a Sim passes these tests, \n            they cannot be considered a protester.\n            ', tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _ProtestingState, factory=cls.protesting_situation_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.protester_job, cls.protester_role)]

    @classmethod
    def default_job(cls):
        return cls.protester_job

    @classmethod
    def get_predefined_guest_list(cls):
        weighted_causes = tuple((item.weight, item.cause) for item in cls.weighted_causes)
        cause = sims4.random.weighted_random_item(weighted_causes)
        protester_filter = cls.protester_search_filter(filter_terms=(TraitFilterTerm(invert_score=False, minimum_filter_score=0, trait=cause, ignore_if_wrong_pack=False),))
        num_protesters_to_request = cls.number_of_protesters.random_int()
        exclude_instanced_sims = not cls.allow_instanced_sims_as_protesters
        blacklist_sim_ids = set()
        if exclude_instanced_sims:
            blacklist_sim_ids.update(sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen())
        blacklist_sim_ids.update(sim_info.id for sim_info in services.active_household().sim_info_gen())
        situation_manager = services.get_zone_situation_manager()
        global_auto_fill_blacklist = situation_manager.get_auto_fill_blacklist()
        blacklist_sim_ids.update(global_auto_fill_blacklist)
        protester_results = services.sim_filter_service().submit_matching_filter(sim_filter=protester_filter, callback=None, allow_yielding=False, allow_instanced_sims=cls.allow_instanced_sims_as_protesters, number_of_sims_to_find=num_protesters_to_request, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if cls.protester_exclusion_tests:
            for result in tuple(protester_results):
                if cls.protester_exclusion_tests.run_tests(SingleSimResolver(result.sim_info)):
                    protester_results.remove(result)
        if not protester_results:
            return
        guest_list = SituationGuestList(invite_only=True)
        spawning_option = RequestSpawningOption.MUST_SPAWN if exclude_instanced_sims else RequestSpawningOption.DONT_CARE
        for result in protester_results:
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, cls.protester_job, spawning_option, cls.protester_request_priority))
        return guest_list

    def start_situation(self):
        super().start_situation()
        protestable = self.find_protestable_using_guest_list()
        initial_state = self.protesting_situation_state()
        if protestable:
            initial_state.set_sign_definition(protestable.sign_definition)
        self._change_state(initial_state)

    def _choose_protestable_from_sim(self, sim):
        possible_protests = [protestable for protestable in self.protestables if sim.has_trait(protestable.cause)]
        if not possible_protests:
            return
        return random.choice(possible_protests)

    def find_protestable_using_guest_list(self):
        for guest in self._guest_list.get_guest_infos_for_job(self.protester_job):
            sim_info = services.sim_info_manager().get(guest.sim_id)
            if sim_info is not None:
                return self._choose_protestable_from_sim(sim_info)
