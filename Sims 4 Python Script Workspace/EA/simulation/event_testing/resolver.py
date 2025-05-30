import randomimport sysimport timefrom business.business_enums import BusinessTypefrom event_testing.results import TestResultfrom interactions import ParticipantType, ParticipantTypeSituationSimsfrom performance.test_profiling import TestProfileRecord, ProfileMetrics, record_profile_metricsfrom objects.components.types import GAME_COMPONENTfrom sims4.utils import classpropertyfrom singletons import DEFAULTimport cachesimport event_testing.test_constantsimport itertoolsimport servicesimport sims4.logimport sims4.reloadlogger = sims4.log.Logger('Resolver')with sims4.reload.protected(globals()):
    RESOLVER_PARTICIPANT = 'resolver'
    test_profile = NoneSINGLE_TYPES = frozenset((ParticipantType.Affordance, ParticipantType.InteractionContext, event_testing.test_constants.FROM_DATA_OBJECT, event_testing.test_constants.OBJECTIVE_GUID64, event_testing.test_constants.FROM_EVENT_DATA))
class Resolver:

    def __init__(self, skip_safe_tests=False, search_for_tooltip=False, additional_metric_key_data=None):
        self._skip_safe_tests = skip_safe_tests
        self._search_for_tooltip = search_for_tooltip
        self._additional_metric_key_data = additional_metric_key_data

    @property
    def skip_safe_tests(self):
        return self._skip_safe_tests

    @property
    def search_for_tooltip(self):
        return self._search_for_tooltip

    @property
    def interaction(self):
        pass

    def get_resolved_args(self, expected):
        if expected is None:
            raise ValueError('Expected arguments from test instance get_expected_args are undefined: {}'.format(expected))
        ret = {}
        for (event_key, participant_type) in expected.items():
            if participant_type in SINGLE_TYPES:
                value = self.get_participant(participant_type, event_key=event_key)
            else:
                value = self.get_participants(participant_type, event_key=event_key)
            ret[event_key] = value
        return ret

    @property
    def profile_metric_key(self):
        pass

    def set_additional_metric_key_data(self, additional_metric_key_data):
        self._additional_metric_key_data = additional_metric_key_data

    def __call__(self, test):
        global test_profile
        if test.expected_kwargs is None:
            expected_args = test.get_expected_args()
            if expected_args:
                test.expected_kwargs = tuple(expected_args.items())
            else:
                test.expected_kwargs = ()
        if test_profile is not None:
            start_time = time.perf_counter()
        resolved_args = {}
        for (event_key, participant_type) in test.expected_kwargs:
            if participant_type in SINGLE_TYPES:
                value = self.get_participants(participant_type, event_key=event_key)
                resolved_args[event_key] = value[0] if value else None
            else:
                resolved_args[event_key] = self.get_participants(participant_type, event_key=event_key)
        if test_profile is not None:
            resolve_end_time = time.perf_counter()
        result = test(**resolved_args)
        if test_profile is not None:
            test_end_time = time.perf_counter()
            resolve_time = resolve_end_time - start_time
            test_time = test_end_time - resolve_end_time
            from event_testing.tests import TestSetInstance
            from event_testing.test_based_score_threshold import TestBasedScoreThresholdTest
            is_test_set = isinstance(test, type) and issubclass(test, TestSetInstance)
            test_name = '[TS]{}'.format(test.__name__) if is_test_set else test.__class__.__name__
            if isinstance(test, TestBasedScoreThresholdTest):
                is_test_set = True
            resolver_name = type(self).__name__
            key_name = self.profile_metric_key
            try:
                record_profile_metrics(test_profile, test_name, resolver_name, key_name, resolve_time, test_time, is_test_set=is_test_set)
            except Exception as e:
                logger.exception('Resetting test_profile due to an exception {}.', e, owner='manus')
                test_profile = None
        return result

    def get_participant(self, participant_type, **kwargs):
        participants = self.get_participants(participant_type, **kwargs)
        if not participants:
            return
        if len(participants) > 1:
            raise ValueError('Too many participants returned for {}!'.format(participant_type))
        return next(iter(participants))

    def get_participants(self, participant_type, **kwargs):
        raise NotImplementedError('Attempting to use the Resolver.get_participants from {}, this is incorrect. Maybe try self._get_participants_base?'.format(self.__class__.__name__))

    def _get_participants_base(self, participant_type, **kwargs):
        if participant_type == RESOLVER_PARTICIPANT:
            return self
        return Resolver.get_particpants_shared(participant_type)

    def get_target_id(self, test, id_type=None):
        expected_args = test.get_expected_args()
        resolved_args = self.get_resolved_args(expected_args)
        resolved_args['id_type'] = id_type
        return test.get_target_id(**resolved_args)

    def get_posture_id(self, test):
        expected_args = test.get_expected_args()
        resolved_args = self.get_resolved_args(expected_args)
        return test.get_posture_id(**resolved_args)

    def get_tags(self, test):
        expected_args = test.get_expected_args()
        resolved_args = self.get_resolved_args(expected_args)
        return test.get_tags(**resolved_args)

    def get_localization_tokens(self, *args, **kwargs):
        return ()

    @staticmethod
    def get_particpants_shared(participant_type):
        if participant_type == ParticipantType.Lot:
            return (services.active_lot(),)
        elif participant_type == ParticipantType.LotOwners:
            owning_household = services.owning_household_of_active_lot()
            if owning_household is not None:
                return tuple(sim_info for sim_info in owning_household.sim_info_gen())
            return ()
        return ()
        if participant_type == ParticipantType.LotOwnersOrRenters:
            owning_household = services.owning_household_of_active_lot()
            if owning_household is not None:
                return tuple(sim_info for sim_info in owning_household.sim_info_gen())
            else:
                current_zone = services.current_zone()
                travel_group = services.travel_group_manager().get_travel_group_by_zone_id(current_zone.id)
                if travel_group is not None:
                    return tuple(sim_info for sim_info in travel_group.sim_info_gen())
            return ()
        if participant_type == ParticipantType.LotOwnerSingleAndInstanced:
            owning_household = services.owning_household_of_active_lot()
            if owning_household is not None:
                for sim_info in owning_household.sim_info_gen():
                    if sim_info.is_instanced():
                        return (sim_info,)
            return ()
        elif participant_type == ParticipantType.ActiveHousehold:
            active_household = services.active_household()
            if active_household is not None:
                return tuple(active_household.sim_info_gen())
            return ()
        elif participant_type == ParticipantType.AllInstancedActiveHouseholdSims:
            active_household = services.active_household()
            if active_household is not None:
                return tuple(active_household.instanced_sims_gen())
            return ()
        elif participant_type == ParticipantType.CareerEventSim:
            career = services.get_career_service().get_career_in_career_event()
            if career is not None:
                return (career.sim_info.get_sim_instance() or career.sim_info,)
            return ()
        return ()
        if participant_type == ParticipantType.AllInstancedActiveHouseholdSims:
            active_household = services.active_household()
            if active_household is not None:
                return tuple(active_household.instanced_sims_gen())
            return ()
        elif participant_type == ParticipantType.CareerEventSim:
            career = services.get_career_service().get_career_in_career_event()
            if career is not None:
                return (career.sim_info.get_sim_instance() or career.sim_info,)
            return ()
        return ()
        if participant_type == ParticipantType.AllInstancedSims:
            return tuple(services.sim_info_manager().instanced_sims_gen())
        if participant_type == ParticipantType.Street:
            street = services.current_zone().street
            street_service = services.street_service()
            if street_service is None:
                return ()
            street_civic_policy_provider = street_service.get_provider(street)
            if street_civic_policy_provider is None:
                return ()
            return (street_civic_policy_provider,)
        if participant_type == ParticipantType.VenuePolicyProvider:
            venue_service = services.venue_service()
            if venue_service.source_venue is None or venue_service.source_venue.civic_policy_provider is None:
                return ()
            return (venue_service.source_venue.civic_policy_provider,)
        if participant_type == ParticipantType.CurrentRegion:
            region_inst = services.current_region_instance()
            if region_inst is None:
                return ()
            return (region_inst,)
        if participant_type == ParticipantType.FashionTrends:
            fashion_trend_service = services.fashion_trend_service()
            if fashion_trend_service is None:
                return ()
            return (fashion_trend_service,)
        if participant_type == ParticipantType.CurrentZoneId:
            return (services.current_zone_id(),)
        if participant_type == ParticipantType.AllUnitZoneIds:
            all_unit_zone_ids = set(services.get_plex_service().get_plex_zones_in_group(services.current_zone_id()))
            return tuple(all_unit_zone_ids)
        elif participant_type == ParticipantType.CurrentlyOpenSmallBusinessOwner:
            business_manager = services.business_service().get_business_manager_for_zone()
            if business_manager is not None and business_manager.is_open and business_manager.business_type == BusinessType.SMALL_BUSINESS:
                sim_info_manager = services.sim_info_manager()
                owner_sim_info = sim_info_manager.get(business_manager.owner_sim_id)
                if owner_sim_info is not None:
                    return (owner_sim_info,)
                else:
                    return ()
            else:
                return ()
        return ()

    def _get_lot_level_from_object(self, obj):
        if obj is None:
            return ()
        if getattr(obj, 'is_lot_level', False):
            return (obj,)
        lot = services.active_lot()
        if lot is None:
            return ()
        lot_level = lot.get_lot_level_instance(obj.routing_surface.secondary_id)
        if lot_level is None:
            return ()
        return (lot_level,)

    def _get_animal_home_from_object(self, obj):
        if obj is None:
            return ()
        animal_service = services.animal_service()
        if animal_service is None:
            return ()
        animal_home = animal_service.get_animal_home_obj(obj)
        if animal_home is None:
            return ()
        return (animal_home,)

    def _get_animal_cost_from_object(self, obj, use_curr_value=False):
        if obj is None:
            return (0,)
        animal_service = services.animal_service()
        if animal_service is None:
            return (0,)
        animal_cost = animal_service.get_animal_cost_obj(self, obj, use_curr_value)
        if animal_cost is None:
            return (0,)
        return (animal_cost,)

    def _get_animal_home_assignees(self, home_obj):
        if home_obj is None:
            return ()
        animal_service = services.animal_service()
        if animal_service is None:
            return ()
        assignees = animal_service.get_animal_home_assignee_objs(home_obj)
        if not assignees:
            return ()
        return tuple(assignees)

class GlobalResolver(Resolver):

    def __init__(self, additional_metric_key_data=None):
        super().__init__(additional_metric_key_data=additional_metric_key_data)

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        raise ValueError('Trying to use GlobalResolver with type that is not supported by GlobalResolver: {}'.format(participant_type))

class AffordanceResolver(Resolver):

    def __init__(self, affordance, actor):
        super().__init__(skip_safe_tests=False, search_for_tooltip=False)
        self.affordance = affordance
        self.actor = actor

    def __repr__(self):
        return 'AffordanceResolver: affordance: {}, actor {}'.format(self.affordance, self.actor)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        elif participant_type == event_testing.test_constants.SIM_INSTANCE or participant_type == ParticipantType.Actor:
            if self.actor is not None:
                result = _to_sim_info(self.actor)
                if result:
                    return (result,)
            return ()
        return ()
        if participant_type == 0:
            logger.error('Calling get_participants with no flags on {}.', self)
            return ()
        if participant_type == ParticipantType.Affordance:
            return (self.affordance,)
        if participant_type == ParticipantType.AllRelationships:
            return (ParticipantType.AllRelationships,)
        return self._get_participants_base(participant_type, **kwargs)

    def __call__(self, test):
        if not test.supports_early_testing():
            return True
        if test.participants_for_early_testing is None:
            test.participants_for_early_testing = tuple(test.get_expected_args().values())
        for participant in test.participants_for_early_testing:
            if self.get_participants(participant) is None:
                return TestResult.TRUE
        return super().__call__(test)

class InteractionResolver(Resolver):

    def __init__(self, affordance, interaction, target=DEFAULT, context=DEFAULT, custom_sim=None, super_interaction=None, skip_safe_tests=False, search_for_tooltip=False, **interaction_parameters):
        super().__init__(skip_safe_tests, search_for_tooltip)
        self.affordance = affordance
        self._interaction = interaction
        self.target = interaction.target if target is DEFAULT else target
        self.context = interaction.context if context is DEFAULT else context
        self.custom_sim = custom_sim
        self.super_interaction = super_interaction
        self.interaction_parameters = interaction_parameters

    def __repr__(self):
        return 'InteractionResolver: affordance: {}, interaction:{}, target: {}, context: {}, si: {}'.format(self.affordance, self.interaction, self.target, self.context, self.super_interaction)

    @property
    def interaction(self):
        return self._interaction

    @property
    def profile_metric_key(self):
        if self.affordance is None:
            return 'NoAffordance'
        return self.affordance.__name__

    def get_participants(self, participant_type, **kwargs):
        if participant_type == event_testing.test_constants.SIM_INSTANCE:
            participant_type = ParticipantType.Actor
        if participant_type == ParticipantType.Actor:
            sim = self.context.sim
            if sim is not None:
                result = _to_sim_info(sim)
                if result is not None:
                    return (result,)
                return ()
        else:
            if participant_type == ParticipantType.Object:
                if self.target is not None:
                    result = _to_sim_info(self.target)
                    if result is not None:
                        return (result,)
                return ()
            elif participant_type == ParticipantType.ObjectIngredients:
                if self.target is not None and self.target.crafting_component:
                    target_crafting_process = self.target.get_crafting_process()
                    if target_crafting_process is not None:
                        return tuple([ingredient_definition_tuple.definition for ingredient_definition_tuple in target_crafting_process.get_ingredients_object_definitions()])
                return ()
            return ()
            if participant_type == ParticipantType.ObjectTrendiOutfitTrend or participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                if self.target is not None:
                    fashion_trend_service = services.fashion_trend_service()
                    if fashion_trend_service is not None:
                        if participant_type == ParticipantType.ObjectTrendiOutfitTrend:
                            outfit_trend = fashion_trend_service.get_outfit_prevalent_trend(self.target)
                            if outfit_trend is not None:
                                return (outfit_trend,)
                            elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                                outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self.target)
                                if outfit_trend_tag is not None:
                                    return (outfit_trend_tag,)
                        elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                            outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self.target)
                            if outfit_trend_tag is not None:
                                return (outfit_trend_tag,)
                return ()
            elif participant_type == ParticipantType.TargetSim:
                if self.target is not None and self.target.is_sim:
                    result = _to_sim_info(self.target)
                    if result is not None:
                        return (result,)
                return ()
            return ()
            if participant_type == ParticipantType.ActorPostureTarget:
                if self.interaction is not None:
                    return self.interaction.get_participants(participant_type=participant_type)
                if self.super_interaction is not None:
                    return self.super_interaction.get_participants(participant_type=participant_type)
            elif participant_type == ParticipantType.AssociatedClub or participant_type == ParticipantType.AssociatedClubLeader or participant_type == ParticipantType.AssociatedClubMembers:
                associated_club = self.interaction_parameters.get('associated_club')
                if self.interaction is None and self.super_interaction is None or associated_club is not None:
                    if participant_type == ParticipantType.AssociatedClubLeader:
                        return (associated_club.leader,)
                    if participant_type == ParticipantType.AssociatedClub:
                        return (associated_club,)
                    if participant_type == ParticipantType.AssociatedClubMembers:
                        return tuple(associated_club.members)
            else:
                if participant_type == ParticipantType.ObjectCrafter:
                    if self.target is None or self.target.crafting_component is None:
                        return ()
                    crafting_process = self.target.get_crafting_process()
                    if crafting_process is None:
                        return ()
                    crafter_sim_info = crafting_process.get_crafter_sim_info()
                    if crafter_sim_info is None:
                        return ()
                    return (crafter_sim_info,)
                if participant_type in ParticipantTypeSituationSims:
                    provider_source = None
                    if self._interaction is not None:
                        provider_source = self._interaction
                    elif self.super_interaction is not None:
                        provider_source = self.super_interaction
                    elif self.affordance is not None:
                        provider_source = self.affordance
                    if provider_source is not None:
                        provider = provider_source.get_situation_participant_provider()
                        if provider is not None:
                            return provider.get_participants(participant_type, self)
                        logger.error("Requesting {} in {} that doesn't have a SituationSimParticipantProviderLiability", participant_type, provider_source)
                else:
                    if participant_type == ParticipantType.ObjectLotLevel:
                        return self._get_lot_level_from_object(self.target)
                    if participant_type == ParticipantType.ActorLotLevel:
                        return self._get_lot_level_from_object(self.context.sim)
        if participant_type == 0:
            logger.error('Calling get_participants with no flags on {}.', self)
            return ()
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.Affordance:
            return (self.affordance,)
        if participant_type == ParticipantType.InteractionContext:
            return (self.context,)
        if participant_type == ParticipantType.CustomSim:
            if self.custom_sim is not None:
                return (self.custom_sim.sim_info,)
            ValueError('Trying to use CustomSim without passing a custom_sim in InteractionResolver.')
        else:
            if participant_type == ParticipantType.AllRelationships:
                return (ParticipantType.AllRelationships,)
            elif participant_type == ParticipantType.ActorZoneId:
                sim = self.context.sim
                if sim is not None:
                    return (sim.household.home_zone_id,)
                return ()
            elif participant_type == ParticipantType.TargetSimZoneId:
                if self.target is not None and self.target.is_sim:
                    return (self.target.household.home_zone_id,)
                return ()
            return ()
            if participant_type == ParticipantType.TargetSimZoneId:
                if self.target is not None and self.target.is_sim:
                    return (self.target.household.home_zone_id,)
                return ()
            if participant_type == ParticipantType.PickedItemId:
                picked_item_ids = self.interaction_parameters.get('picked_item_ids')
                if picked_item_ids is not None:
                    return tuple(picked_item_ids)
            elif participant_type == ParticipantType.PickedZoneId:
                picked_zone_id = self.interaction_parameters.get('picked_zone_id')
                if picked_zone_id is not None:
                    return tuple(picked_zone_id)
            elif participant_type == ParticipantType.StoredPickedTattooOnActor:
                sim = self.context.sim
                if sim is not None:
                    result = _to_sim_info(sim)
                    if result is not None:
                        tattoo_tracker = result.tattoo_tracker
                        if tattoo_tracker is not None:
                            return (tattoo_tracker.get_picked_tattoo(),)
            elif participant_type == ParticipantType.StoredPickedTattooOnTarget and self.target is not None and self.target.is_sim:
                result = _to_sim_info(self.target)
                if result is not None:
                    tattoo_tracker = result.tattoo_tracker
                    if tattoo_tracker is not None:
                        return (tattoo_tracker.get_picked_tattoo(),)
        if self.interaction is not None:
            participants = self.interaction.get_participants(participant_type=participant_type, sim=self.context.sim, target=self.target, listener_filtering_enabled=False, **self.interaction_parameters)
        elif self.super_interaction is not None:
            participants = self.super_interaction.get_participants(participant_type=participant_type, sim=self.context.sim, target=self.target, listener_filtering_enabled=False, target_type=self.affordance.target_type, **self.interaction_parameters)
        else:
            participants = self.affordance.get_participants(participant_type=participant_type, sim=self.context.sim, target=self.target, carry_target=self.context.carry_target, listener_filtering_enabled=False, target_type=self.affordance.target_type, **self.interaction_parameters)
        resolved_participants = set()
        for participant in participants:
            resolved_participants.add(_to_sim_info(participant))
        return tuple(resolved_participants)

    def get_localization_tokens(self, *args, **kwargs):
        return self.interaction.get_localization_tokens(*args, **kwargs)

@caches.clearable_barebones_cache
def _to_sim_info(participant):
    sim_info = getattr(participant, 'sim_info', None)
    if sim_info is None or sim_info.is_baby:
        return participant
    return sim_info

class AwayActionResolver(Resolver):
    VALID_AWAY_ACTION_PARTICIPANTS = ParticipantType.Actor | ParticipantType.TargetSim | ParticipantType.Lot

    def __init__(self, away_action, skip_safe_tests=False, search_for_tooltip=False, **away_action_parameters):
        super().__init__(skip_safe_tests, search_for_tooltip)
        self.away_action = away_action
        self.away_action_parameters = away_action_parameters

    def __repr__(self):
        return 'AwayActionResolver: away_action: {}'.format(self.away_action)

    @property
    def sim(self):
        return self.get_participant(ParticipantType.Actor)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == 0:
            logger.error('Calling get_participants with no flags on {}.', self)
            return ()
        if participant_type == ParticipantType.Lot:
            return self.away_action.get_participants(participant_type=participant_type, **self.away_action_parameters)
        result = self._get_participants_base(participant_type)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type & AwayActionResolver.VALID_AWAY_ACTION_PARTICIPANTS:
            return self.away_action.get_participants(participant_type=participant_type, **self.away_action_parameters)
        raise ValueError('Trying to use AwayActionResolver without a valid type: {}'.format(participant_type))

    def get_localization_tokens(self, *args, **kwargs):
        return self.interaction.get_localization_tokens(*args, **kwargs)

class SingleSimResolver(Resolver):

    def __init__(self, sim_info_to_test, additional_participants={}, additional_localization_tokens=(), additional_metric_key_data=None):
        super().__init__(additional_metric_key_data=additional_metric_key_data)
        self.sim_info_to_test = sim_info_to_test
        self._additional_participants = additional_participants
        self._additional_localization_tokens = additional_localization_tokens
        self._source = None
        if event_testing.resolver.test_profile is not None:
            frame = sys._getframe(self.profile_metric_stack_depth)
            qualified_name = frame.f_code.co_filename
            unqualified_name = qualified_name.split('\\')[-1]
            self._source = unqualified_name

    def __repr__(self):
        return 'SingleSimResolver: sim_to_test: {}'.format(self.sim_info_to_test)

    @property
    def profile_metric_key(self):
        return '{}:{}'.format(self._source, self._additional_metric_key_data)

    @classproperty
    def profile_metric_stack_depth(cls):
        return 1

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.Actor or participant_type == ParticipantType.CustomSim:
            return (self.sim_info_to_test,)
        if participant_type == ParticipantType.ActorHouseholdMembers and self.sim_info_to_test is not None and self.sim_info_to_test.household is not None:
            return tuple(self.sim_info_to_test.household)
        elif participant_type == ParticipantType.SignificantOtherActor:
            significant_other = self.sim_info_to_test.get_significant_other_sim_info()
            if significant_other is not None:
                return (significant_other,)
            return ()
        elif participant_type == ParticipantType.AllSignificantOthersActor:
            significant_others = self.sim_info_to_test.get_significant_other_sim_info(True)
            if significant_others is not None:
                return tuple(significant_others)
            return ()
        elif participant_type == ParticipantType.PregnancyPartnerActor:
            pregnancy_partner = self.sim_info_to_test.pregnancy_tracker.get_partner()
            if pregnancy_partner is not None:
                return (pregnancy_partner,)
            return ()
        return ()
        if participant_type == ParticipantType.AllSignificantOthersActor:
            significant_others = self.sim_info_to_test.get_significant_other_sim_info(True)
            if significant_others is not None:
                return tuple(significant_others)
            return ()
        elif participant_type == ParticipantType.PregnancyPartnerActor:
            pregnancy_partner = self.sim_info_to_test.pregnancy_tracker.get_partner()
            if pregnancy_partner is not None:
                return (pregnancy_partner,)
            return ()
        return ()
        if participant_type == ParticipantType.AllRelationships:
            if self.sim_info_to_test and self.sim_info_to_test.relationship_tracker is not None:
                infos = []
                for sim_id in self.sim_info_to_test.relationship_tracker.target_sim_gen():
                    sim = services.sim_info_manager().get(sim_id)
                    infos.append(sim)
                return tuple(infos)
            return ParticipantType.AllRelationships
        elif participant_type == ParticipantType.ActorFeudTarget:
            feud_target = self.sim_info_to_test.get_feud_target()
            if feud_target is not None:
                return (feud_target,)
            return ()
        return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.InteractionContext or participant_type == ParticipantType.Affordance:
            return ()
        if participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self.sim_info_to_test,)
        if participant_type == ParticipantType.Familiar:
            return self._get_familiar_for_sim_info(self.sim_info_to_test)
        if participant_type in self._additional_participants:
            return self._additional_participants[participant_type]
        if participant_type == ParticipantType.PickedZoneId:
            return frozenset()
        if participant_type == ParticipantType.ActorLot:
            sim_home_lot = self.sim_info_to_test.get_home_lot()
            if sim_home_lot is None:
                return ()
            return (sim_home_lot,)
        if participant_type == ParticipantType.RoutingSlaves:
            sim_inst = self.sim_info_to_test.get_sim_instance()
            routing_slave_data = sim_inst.get_routing_slave_data() if sim_inst is not None else None
            if routing_slave_data is None:
                return ()
            return tuple({data.slave for data in routing_slave_data})
        if participant_type == ParticipantType.StoredCASPartsOnObject:
            return ()
        if participant_type == ParticipantType.ActorLotLevel:
            return self._get_lot_level_from_object(self.sim_info_to_test.get_sim_instance())
        if participant_type == ParticipantType.ActorClanLeader:
            clan_service = services.clan_service()
            if clan_service is None:
                return ()
            clan_leader = clan_service.get_clan_leader(self.sim_info_to_test)
            if clan_leader is None:
                return ()
            return (clan_leader,)
        if participant_type == ParticipantType.GraduatesCurrent:
            graduation_service = services.get_graduation_service()
            if graduation_service is None:
                return tuple()
            return tuple(graduation_service.current_graduating_sims())
        if participant_type == ParticipantType.GraduatesWaiting:
            graduation_service = services.get_graduation_service()
            if graduation_service is None:
                return tuple()
            return tuple(graduation_service.waiting_to_graduate_sims())
        if participant_type == ParticipantType.ActorBassinet:
            baby_bassinet = services.object_manager().get(self.sim_info_to_test.sim_id)
            if baby_bassinet is None or not baby_bassinet.is_bassinet:
                return ()
            return (baby_bassinet,)
        if participant_type == ParticipantType.ActorPropertyOwners:
            multi_unit_ownership_service = services.get_multi_unit_ownership_service()
            if multi_unit_ownership_service is None:
                return ()
            sim_household = self.sim_info_to_test.household
            if sim_household is None:
                return ()
            property_owner_hh_id = multi_unit_ownership_service.get_property_owner_household_id(sim_household.home_zone_id)
            if property_owner_hh_id is None:
                return ()
            else:
                property_owner_hh = services.household_manager().get(property_owner_hh_id)
                if property_owner_hh is not None:
                    return tuple(property_owner_hh)
            return ()
        if participant_type == ParticipantType.ActorPropertyOwnerHousehold:
            property_owner_hh_id = None
            multi_unit_ownership_service = services.get_multi_unit_ownership_service()
            if multi_unit_ownership_service is None:
                return ()
            sim_household = self.sim_info_to_test.household
            if sim_household is None:
                return ()
            else:
                property_owner_hh_id = multi_unit_ownership_service.get_property_owner_household_id(sim_household.home_zone_id)
                if property_owner_hh_id is not None:
                    return (property_owner_hh_id,)
            return ()
        if participant_type == ParticipantType.ActorTenants:
            multi_unit_ownership_service = services.get_multi_unit_ownership_service()
            if multi_unit_ownership_service is None:
                return ()
            sim_household = self.sim_info_to_test.household
            if sim_household is None:
                return ()
            tenant_hh_ids = multi_unit_ownership_service.get_tenants_household_ids(sim_household.id)
            tenant_households = [services.household_manager().get(hh_id) for hh_id in tenant_hh_ids]
            return tuple(list(itertools.chain(tenant_household.sim_infos for tenant_household in tenant_households)))
        if participant_type == ParticipantType.ActorTenantHouseholds:
            multi_unit_ownership_service = services.get_multi_unit_ownership_service()
            if multi_unit_ownership_service is None:
                return ()
            sim_household = self.sim_info_to_test.household
            if sim_household is None:
                return ()
            tenant_hh_ids = multi_unit_ownership_service.get_tenants_household_ids(sim_household.id)
            return tuple(tenant_hh_ids)
        if participant_type == ParticipantType.RandomZoneId:
            if ParticipantType.PickedZoneId not in self._additional_participants:
                return ()
            picked_zone_id = self._additional_participants[ParticipantType.PickedZoneId]
            if not picked_zone_id:
                return ()
            neighbor_unit_zone_ids = set(services.get_plex_service().get_plex_zones_in_group(picked_zone_id[0]))
            sim_household = self.sim_info_to_test.household
            if sim_household is not None:
                neighbor_unit_zone_ids.discard(sim_household.home_zone_id)
            if not neighbor_unit_zone_ids:
                return ()
            random_zone_id = random.choice(tuple(neighbor_unit_zone_ids))
            return (random_zone_id,)
        if participant_type == ParticipantType.PickedZoneHouseholdSims:
            if ParticipantType.PickedZoneId not in self._additional_participants:
                logger.error('Participant {} requires PickedZoneId to be set in resolver.', participant_type)
                return ()
            picked_zone_id = self._additional_participants[ParticipantType.PickedZoneId]
            if not picked_zone_id:
                return ()
            household = services.household_manager().get_by_home_zone_id(picked_zone_id[0])
            if household is None:
                return ()
            return household.sim_infos
        if participant_type == ParticipantType.ActorZoneId:
            sim_household = self.sim_info_to_test.household
            if sim_household is None:
                return ()
            return (sim_household.home_zone_id,)
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        elif participant_type == ParticipantType.SmallBusinessEmployees:
            owner_sim = services.get_active_sim()
            business_manager = services.business_service().get_business_manager_for_sim(owner_sim.sim_id)
            if business_manager:
                employee_list = business_manager.get_employees_sim_info()
                return employee_list
            return ()
        return ()
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        raise ValueError('Trying to use {} with unsupported participant: {}'.format(type(self).__name__, participant_type))

    def _get_familiar_for_sim_info(self, sim_info):
        familiar_tracker = self.sim_info_to_test.familiar_tracker
        if familiar_tracker is None:
            return ()
        familiar = familiar_tracker.get_active_familiar()
        if familiar is None:
            return ()
        if familiar.is_sim:
            return (familiar.sim_info,)
        return (familiar,)

    def get_localization_tokens(self, *args, **kwargs):
        return (self.sim_info_to_test,) + self._additional_localization_tokens

    def set_additional_participant(self, participant_type, value):
        self._additional_participants[participant_type] = value

class DoubleSimResolver(SingleSimResolver):

    def __init__(self, sim_info, target_sim_info, **kwargs):
        super().__init__(sim_info, **kwargs)
        self.target_sim_info = target_sim_info

    def __repr__(self):
        return 'DoubleSimResolver: sim: {} target_sim: {}'.format(self.sim_info_to_test, self.target_sim_info)

    @classproperty
    def profile_metric_stack_depth(cls):
        return 2

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.TargetSim or participant_type == ParticipantType.Object:
            return (self.target_sim_info,)
        if participant_type == ParticipantType.TargetHouseholdMembers and self.target_sim_info is not None and self.target_sim_info.household is not None:
            return tuple(self.target_sim_info.household)
        if participant_type == ParticipantType.TargetSimZoneId and self.target_sim_info is not None and self.target_sim_info.household is not None:
            return (self.target_sim_info.household.home_zone_id,)
        if participant_type == ParticipantType.SignificantOtherTargetSim:
            return (self.target_sim_info.get_significant_other_sim_info(),)
        if participant_type == ParticipantType.AllSignificantOthersTargetSim:
            return tuple(self.target_sim_info.get_significant_other_sim_info(True))
        if participant_type == ParticipantType.FamiliarOfTarget:
            return self._get_familiar_for_sim_info(self.target_sim_info)
        if participant_type == ParticipantType.TargetClanLeader and self.target_sim_info is not None:
            clan_service = services.clan_service()
            if clan_service is None:
                return ()
            clan_leader = clan_service.get_clan_leader(self.target_sim_info)
            if clan_leader is None:
                return ()
            return (clan_leader,)
        if participant_type == ParticipantType.TargetBassinet:
            baby_bassinet = services.object_manager().get(self.target_sim_info.sim_id)
            if baby_bassinet is None or not baby_bassinet.is_bassinet:
                return ()
            return (baby_bassinet,)
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return ()
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return ()
        return super().get_participants(participant_type, **kwargs)

    def get_localization_tokens(self, *args, **kwargs):
        return (self.sim_info_to_test, self.target_sim_info) + self._additional_localization_tokens

class SingleSimAndHouseholdResolver(SingleSimResolver):

    def __init__(self, sim_info, target_household, **kwargs):
        super().__init__(sim_info, **kwargs)
        self.target_household = target_household

    def __repr__(self):
        return 'SingleSimAndHouseholdResolver: sim: {} household: {}'.format(self.sim_info_to_test, self.target_household)

    @classproperty
    def profile_metric_stack_depth(cls):
        return 2

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.TargetHousehold:
            return (self.target_household,)
        if participant_type == ParticipantType.TargetHouseholdMembers:
            return tuple(self.target_household)
        return super().get_participants(participant_type, **kwargs)

class DataResolver(Resolver):

    def __init__(self, sim_info, event_kwargs=None, custom_keys=(), additional_metric_key_data=None):
        super().__init__(additional_metric_key_data=additional_metric_key_data)
        self.sim_info = sim_info
        if event_kwargs is not None:
            self._interaction = event_kwargs.get('interaction', None)
            self.on_zone_load = event_kwargs.get('init', False)
        else:
            self._interaction = None
            self.on_zone_load = False
        self.event_kwargs = event_kwargs
        self.data_object = None
        self.objective_guid64 = None
        self.custom_keys = custom_keys

    def __repr__(self):
        return 'DataResolver: participant: {}'.format(self.sim_info)

    def __call__(self, test, data_object=None, objective_guid64=None):
        if data_object is not None:
            self.data_object = data_object
            self.objective_guid64 = objective_guid64
        return super().__call__(test)

    @property
    def interaction(self):
        return self._interaction

    @property
    def profile_metric_key(self):
        interaction_name = None
        if self._interaction is not None:
            interaction_name = self._interaction.aop.affordance.__name__
        objective_name = 'Invalid'
        additional_metric_key_str = 'Invalid'
        if self.objective_guid64 is not None:
            objective_manager = services.get_instance_manager(sims4.resources.Types.OBJECTIVE)
            objective = objective_manager.get(self.objective_guid64)
            objective_name = objective.__name__
        if self._additional_metric_key_data is not None:
            return 'objective:{} (interaction:{}) (additional_metric_key_data:{})'.format(objective_name, interaction_name, self._additional_metric_key_data)
        return 'objective:{} (interaction:{})'.format(objective_name, interaction_name)

    def get_resolved_arg(self, key):
        return self.event_kwargs.get(key, None)

    def get_participants(self, participant_type, event_key=None):
        result = self._get_participants_base(participant_type, event_key=event_key)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self.sim_info,)
        if participant_type == event_testing.test_constants.FROM_DATA_OBJECT:
            return (self.data_object,)
        if participant_type == event_testing.test_constants.OBJECTIVE_GUID64:
            return (self.objective_guid64,)
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            if not self.event_kwargs:
                return ()
            return (self.event_kwargs.get(event_key),)
        if self._interaction is not None:
            return tuple(getattr(participant, 'sim_info', participant) for participant in self._interaction.get_participants(participant_type))
        if participant_type == ParticipantType.Actor:
            return (self.sim_info,)
        if participant_type == ParticipantType.AllRelationships:
            sim_mgr = services.sim_info_manager()
            relations = set(sim_mgr.get(relations.get_other_sim_id(self.sim_info.sim_id)) for relations in self.sim_info.relationship_tracker)
            return tuple(relations)
        if participant_type == ParticipantType.TargetSim:
            if not self.event_kwargs:
                return ()
            target_sim_id = self.event_kwargs.get(event_testing.test_constants.TARGET_SIM_ID)
            if target_sim_id is None:
                return ()
            return (services.sim_info_manager().get(target_sim_id),)
        if participant_type == ParticipantType.ActiveHousehold:
            active_household = services.active_household()
            if active_household is not None:
                return tuple(active_household.sim_info_gen())
        if self.on_zone_load:
            return ()
        raise ValueError('Trying to use DataResolver with type that is not supported by DataResolver: {}'.format(participant_type))

class SingleObjectResolver(Resolver):

    def __init__(self, obj):
        super().__init__()
        self._obj = obj

    def __repr__(self):
        return 'SingleObjectResolver: object: {}'.format(self._obj)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.Object:
            return (self._obj,)
        elif participant_type == ParticipantType.ObjectIngredients:
            if self._obj.crafting_component:
                crafting_process = self._obj.get_crafting_process()
                if crafting_process is not None:
                    return tuple([ingredient_definition_tuple.definition for ingredient_definition_tuple in crafting_process.get_ingredients_object_definitions()])
            return ()
        return ()
        if participant_type == ParticipantType.ObjectTrendiOutfitTrend or participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
            if self._obj is not None:
                fashion_trend_service = services.fashion_trend_service()
                if fashion_trend_service is not None:
                    if participant_type == ParticipantType.ObjectTrendiOutfitTrend:
                        outfit_trend = fashion_trend_service.get_outfit_prevalent_trend(self._obj)
                        if outfit_trend is not None:
                            return (outfit_trend,)
                        elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                            outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self._obj)
                            if outfit_trend_tag is not None:
                                return (outfit_trend_tag,)
                    elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                        outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self._obj)
                        if outfit_trend_tag is not None:
                            return (outfit_trend_tag,)
            return ()
        if participant_type == ParticipantType.Actor:
            return (self._obj,)
        if participant_type == ParticipantType.StoredSim:
            stored_sim_info = self._obj.get_stored_sim_info()
            return (stored_sim_info,)
        if participant_type == ParticipantType.StoredSim2:
            stored_sim_info2 = self._obj.get_secondary_stored_sim_info()
            return (stored_sim_info2,)
        if participant_type == ParticipantType.StoredSimOrNameData:
            stored_sim_name_data = self._obj.get_stored_sim_info_or_name_data()
            return (stored_sim_name_data,)
        elif participant_type == ParticipantType.StoredSimOrNameDataList:
            stored_sim_name_data_list = self._obj.get_stored_sim_info_or_name_data_list()
            if len(stored_sim_name_data_list) != 0:
                return tuple(stored_sim_name_data_list)
            return ()
        return ()
        if participant_type == ParticipantType.OwnerSim:
            owner_sim_info_id = self._obj.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            return (owner_sim_info,)
        if participant_type == ParticipantType.ObjectParent:
            if self._obj is None or self._obj.parent is None:
                return ()
            return (self._obj.parent,)
        if participant_type == ParticipantType.ObjectChildren:
            if self._obj is None:
                return ()
            if self._obj.is_part:
                return tuple(self._obj.part_owner.children_recursive_gen())
            return tuple(self._obj.children_recursive_gen())
        if participant_type == ParticipantType.RandomInventoryObject:
            return (random.choice(tuple(self._obj.inventory_component.visible_storage)),)
        if participant_type == ParticipantType.PickedObject or participant_type == ParticipantType.CarriedObject or participant_type == ParticipantType.LiveDragActor:
            if self._obj.is_sim:
                return (self._obj.sim_info,)
            return (self._obj,)
        if participant_type == ParticipantType.RoutingOwner:
            routing_owner = self._obj.get_routing_owner()
            if routing_owner is None:
                return ()
            if routing_owner.is_sim:
                return (routing_owner.sim_info,)
            return (routing_owner,)
        elif participant_type == ParticipantType.RoutingTarget:
            routing_target = self._obj.get_routing_target()
            if routing_target is None:
                return ()
            if routing_target.is_sim:
                return (routing_target.sim_info,)
            return (routing_target,)
        else:
            if participant_type == ParticipantType.StoredCASPartsOnObject:
                stored_cas_parts = self._obj.get_stored_cas_parts()
                if stored_cas_parts is None:
                    return ()
                return tuple(iter(self._obj.get_stored_cas_parts()))
            if participant_type == ParticipantType.ObjectLotLevel or participant_type == ParticipantType.ActorLotLevel:
                return self._get_lot_level_from_object(self._obj)
            if participant_type == ParticipantType.ObjectAnimalHome:
                return self._get_animal_home_from_object(self._obj)
            if participant_type == ParticipantType.ObjectAnimalCost:
                return self._get_animal_cost_from_object(self._obj)
            if participant_type == ParticipantType.ObjectAnimalCurrentValue:
                return self._get_animal_cost_from_object(self._obj, True)
            if participant_type == ParticipantType.AnimalHomeAssignees:
                return self._get_animal_home_assignees(self._obj)
            if participant_type == ParticipantType.ObjectRelationshipsComponent:
                sim_ids = () if self._obj.objectrelationship_component is None else self._obj.objectrelationship_component.relationships.keys()
                sim_info_manager = services.sim_info_manager()
                relations = set(sim_info_manager.get(sim_id) for sim_id in sim_ids)
                return tuple(relations)
            if participant_type == ParticipantType.GraduatesCurrent:
                graduation_service = services.get_graduation_service()
                if graduation_service is None:
                    return tuple()
                return tuple(graduation_service.current_graduating_sims())
            if participant_type == ParticipantType.GraduatesWaiting:
                graduation_service = services.get_graduation_service()
                if graduation_service is None:
                    return tuple()
                return tuple(graduation_service.waiting_to_graduate_sims())
            if participant_type == ParticipantType.HeirloomCreatorSim:
                creator_sim_info = self._obj.get_creator_sim_info()
                if creator_sim_info is None:
                    return tuple()
                return (creator_sim_info,)
            if participant_type == ParticipantType.ActorHouseholdMembers:
                household_id = self._obj.household_owner_id
                household_info = services.household_manager().get(household_id)
                if household_info is None:
                    return tuple()
                return tuple(household_info)
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        raise ValueError('Trying to use SingleObjectResolver with something that is not an Object: {}'.format(participant_type))

    def get_localization_tokens(self, *args, **kwargs):
        return (self._obj,)

class DoubleObjectResolver(Resolver):

    def __init__(self, source_obj, target_obj):
        super().__init__()
        self._source_obj = source_obj
        self._target_obj = target_obj

    def __repr__(self):
        return 'DoubleObjectResolver: actor_object: {}, target_object:{}'.format(self._source_obj, self._target_obj)

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == ParticipantType.Actor or (participant_type == ParticipantType.PickedObject or participant_type == ParticipantType.CarriedObject) or participant_type == ParticipantType.LiveDragActor:
            if self._source_obj.is_sim:
                return (self._source_obj.sim_info,)
            return (self._source_obj,)
        if participant_type == ParticipantType.Listeners or (participant_type == ParticipantType.Object or participant_type == ParticipantType.TargetSim) or participant_type == ParticipantType.LiveDragTarget:
            if self._target_obj.is_sim:
                return (self._target_obj.sim_info,)
            return (self._target_obj,)
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.LinkedPostureSim and self._source_obj.is_sim:
            posture = self._source_obj.posture
            if posture.multi_sim:
                return (posture.linked_posture.sim.sim_info,)
        if participant_type == ParticipantType.SignificantOtherTargetSim and self._target_obj.is_sim:
            return (self._target_obj.sim_info.get_significant_other_sim_info(),)
        if participant_type == ParticipantType.AllSignificantOthersTargetSim and self._target_obj.is_sim:
            return tuple(self._target_obj.sim_info.get_significant_other_sim_info(True))
        if participant_type == ParticipantType.ObjectParent:
            if self._target_obj is None or self._target_obj.parent is None:
                return ()
            return (self._target_obj.parent,)
        if participant_type == ParticipantType.RoutingOwner:
            if self._source_obj.get_routing_owner().is_sim:
                return (self._source_obj.get_routing_owner().sim_info,)
            return (self._source_obj.get_routing_owner(),)
        if participant_type == ParticipantType.RoutingTarget:
            if self._source_obj.get_routing_target().is_sim:
                return (self._source_obj.get_routing_target().sim_info,)
            return (self._source_obj.get_routing_target(),)
        if participant_type == ParticipantType.ActorLotLevel:
            return self._get_lot_level_from_object(self._source_obj)
        if participant_type == ParticipantType.ObjectLotLevel:
            return self._get_lot_level_from_object(self._target_obj)
        if participant_type == ParticipantType.ObjectAnimalHome:
            return self._get_animal_home_from_object(self._source_obj)
        if participant_type == ParticipantType.ObjectAnimalCost:
            return self._get_animal_cost_from_object(self._source_obj)
        if participant_type == ParticipantType.ObjectAnimalCurrentValue:
            return self._get_animal_cost_from_object(self._source_obj, True)
        if participant_type == ParticipantType.ActorClanLeader:
            clan_service = services.clan_service()
            if self._source_obj.is_sim and clan_service is None:
                return ()
            clan_leader = clan_service.get_clan_leader(self._source_obj.sim_info)
            if clan_leader is None:
                return ()
            return (clan_leader,)
        if participant_type == ParticipantType.Affordance or participant_type == ParticipantType.InteractionContext:
            return ()
        if participant_type == ParticipantType.TargetClanLeader:
            clan_service = services.clan_service()
            if self._target_obj.is_sim and clan_service is None:
                return ()
            clan_leader = clan_service.get_clan_leader(self._target_obj.sim_info)
            if clan_leader is None:
                return ()
            return (clan_leader,)
        raise ValueError('Trying to use DoubleObjectResolver with something that is not supported: Participant {} for objects {} and {}, Resolver {}'.format(participant_type, self._source_obj, self._target_obj, self))

    def get_localization_tokens(self, *args, **kwargs):
        return (self._source_obj, self._target_obj)

class SingleActorAndObjectResolver(Resolver):

    def __init__(self, actor_sim_info, obj, source):
        super().__init__()
        self._sim_info = actor_sim_info
        self._obj = obj
        self._source = source

    def __repr__(self):
        return 'SingleActorAndObjectResolver: sim_info: {}, object: {}'.format(self._sim_info, self._obj)

    @property
    def profile_metric_key(self):
        return 'source:{} object:{}'.format(self._source, self._obj)

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == ParticipantType.Actor or participant_type == ParticipantType.CustomSim or participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self._sim_info,)
        if participant_type == ParticipantType.Object:
            return (self._obj,)
        elif participant_type == ParticipantType.ObjectIngredients:
            if self._obj.crafting_component:
                crafting_process = self._obj.get_crafting_process()
                if crafting_process is not None:
                    return tuple([ingredient_definition_tuple.definition for ingredient_definition_tuple in crafting_process.get_ingredients_object_definitions()])
            return ()
        return ()
        if participant_type == ParticipantType.ObjectTrendiOutfitTrend or participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
            if self._obj is not None:
                fashion_trend_service = services.fashion_trend_service()
                if fashion_trend_service is not None:
                    if participant_type == ParticipantType.ObjectTrendiOutfitTrend:
                        outfit_trend = fashion_trend_service.get_outfit_prevalent_trend(self._obj)
                        if outfit_trend is not None:
                            return (outfit_trend,)
                        elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                            outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self._obj)
                            if outfit_trend_tag is not None:
                                return (outfit_trend_tag,)
                    elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                        outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self._obj)
                        if outfit_trend_tag is not None:
                            return (outfit_trend_tag,)
            return ()
        if participant_type == ParticipantType.ObjectParent:
            if self._obj is None or self._obj.parent is None:
                return ()
            return (self._obj.parent,)
        if participant_type == ParticipantType.StoredSim:
            stored_sim_info = self._obj.get_stored_sim_info()
            return (stored_sim_info,)
        if participant_type == ParticipantType.StoredSim2:
            stored_sim_info2 = self._obj.get_secondary_stored_sim_info()
            return (stored_sim_info2,)
        if participant_type == ParticipantType.StoredCASPartsOnObject:
            stored_cas_parts = self._obj.get_stored_cas_parts()
            if stored_cas_parts is None:
                return ()
            return tuple(iter(self._obj.get_stored_cas_parts()))
        if participant_type == ParticipantType.OwnerSim:
            owner_sim_info_id = self._obj.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            return (owner_sim_info,)
        if participant_type == ParticipantType.Affordance or participant_type == ParticipantType.InteractionContext or participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.ObjectLotLevel:
            return self._get_lot_level_from_object(self._obj)
        if participant_type == ParticipantType.ActorLotLevel:
            return self._get_lot_level_from_object(self._sim_info.get_sim_instance())
        if participant_type == ParticipantType.HeirloomCreatorSim:
            creator_sim_info = self._obj.get_creator_sim_info()
            if creator_sim_info is None:
                return tuple()
            return (creator_sim_info,)
        if participant_type == ParticipantType.OtherSimsInCurrentGame:
            if self._obj is None or self._obj.is_sim or not self._obj.has_component(GAME_COMPONENT):
                return ()
            players = [player.sim_info for player in self._obj.game_component.get_all_players()]
            if self._sim_info is not None and self._sim_info in players:
                players.remove(self._sim_info)
            return tuple(players)
        raise ValueError('Trying to use SingleActorAndObjectResolver with something that is not supported: {}'.format(participant_type))

    def get_localization_tokens(self, *args, **kwargs):
        return (self._sim_info, self._obj)

class DoubleSimAndObjectResolver(Resolver):

    def __init__(self, actor_sim_info, target_sim_info, obj, source):
        super().__init__()
        self._actor_sim_info = actor_sim_info
        self._target_sim_info = target_sim_info
        self._obj = obj
        self._source = source

    def __repr__(self):
        return f'DoubleActorAndObjectResolver: actor_sim_info: {self._actor_sim_info}, target_sim_info: {self._target_sim_info}, object: {self._obj}'

    @property
    def profile_metric_key(self):
        return f'source:{self._source} object:{self._obj}'

    def get_participants(self, participant_type, **kwargs):
        result = self._get_participants_base(participant_type, **kwargs)
        if result is not None:
            return result
        if participant_type == ParticipantType.Actor or participant_type == ParticipantType.CustomSim or participant_type == event_testing.test_constants.SIM_INSTANCE:
            return (self._actor_sim_info,)
        if participant_type == ParticipantType.ActorHouseholdMembers and self._actor_sim_info is not None and self._actor_sim_info.household is not None:
            return tuple(self._actor_sim_info.household)
        if participant_type == ParticipantType.TargetSim:
            return (self._target_sim_info,)
        if participant_type == ParticipantType.TargetHouseholdMembers and self._target_sim_info is not None and self._target_sim_info.household is not None:
            return tuple(self._target_sim_info.household)
        if participant_type == ParticipantType.SignificantOtherTargetSim:
            return (self._target_sim_info.get_significant_other_sim_info(),)
        if participant_type == ParticipantType.AllSignificantOthersTargetSim:
            return tuple(self._target_sim_info.get_significant_other_sim_info(True))
        if participant_type == ParticipantType.Object:
            return (self._obj,)
        elif participant_type == ParticipantType.ObjectIngredients:
            if self._obj.crafting_component:
                crafting_process = self._obj.get_crafting_process()
                if crafting_process is not None:
                    return tuple([ingredient_definition_tuple.definition for ingredient_definition_tuple in crafting_process.get_ingredients_object_definitions()])
            return ()
        return ()
        if participant_type == ParticipantType.ObjectTrendiOutfitTrend or participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
            if self._obj is not None:
                fashion_trend_service = services.fashion_trend_service()
                if fashion_trend_service is not None:
                    if participant_type == ParticipantType.ObjectTrendiOutfitTrend:
                        outfit_trend = fashion_trend_service.get_outfit_prevalent_trend(self._obj)
                        if outfit_trend is not None:
                            return (outfit_trend,)
                        elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                            outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self._obj)
                            if outfit_trend_tag is not None:
                                return (outfit_trend_tag,)
                    elif participant_type == ParticipantType.ObjectTrendiOutfitTrendTag:
                        outfit_trend_tag = fashion_trend_service.get_outfit_prevalent_trend_tag(self._obj)
                        if outfit_trend_tag is not None:
                            return (outfit_trend_tag,)
            return ()
        if participant_type == ParticipantType.ObjectParent:
            if self._obj is None or self._obj.parent is None:
                return ()
            return (self._obj.parent,)
        if participant_type == ParticipantType.StoredSim:
            stored_sim_info = self._obj.get_stored_sim_info()
            return (stored_sim_info,)
        if participant_type == ParticipantType.StoredSim2:
            stored_sim_info2 = self._obj.get_secondary_stored_sim_info()
            return (stored_sim_info2,)
        if participant_type == ParticipantType.StoredCASPartsOnObject:
            stored_cas_parts = self._obj.get_stored_cas_parts()
            if stored_cas_parts is None:
                return ()
            return tuple(iter(self._obj.get_stored_cas_parts()))
        if participant_type == ParticipantType.OwnerSim:
            owner_sim_info_id = self._obj.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            return (owner_sim_info,)
        if participant_type == ParticipantType.Affordance:
            return ()
        if participant_type == ParticipantType.InteractionContext:
            return ()
        if participant_type == event_testing.test_constants.FROM_EVENT_DATA:
            return ()
        if participant_type == ParticipantType.ObjectLotLevel:
            return self._get_lot_level_from_object(self._obj)
        if participant_type == ParticipantType.ActorLotLevel:
            return self._get_lot_level_from_object(self._actor_sim_info.get_sim_instance())
        if participant_type == ParticipantType.HeirloomCreatorSim:
            creator_sim_info = self._obj.get_creator_sim_info()
            if creator_sim_info is None:
                return tuple()
            return (creator_sim_info,)
        raise ValueError(f'Trying to use DoubleActorAndObjectResolver with something that is not supported: {participant_type}')

    def get_localization_tokens(self, *args, **kwargs):
        return (self._sim_info, self._target_sim_info, self._obj)

class PhotoResolver(SingleActorAndObjectResolver):

    def __init__(self, photographer, photo_object, photo_targets, res_key, source):
        super().__init__(photographer, photo_object, source)
        self._photo_targets = photo_targets
        self._res_key = res_key

    def __repr__(self):
        return 'PhotoResolver: photographer: {}, photo_object:{}, photo_targets:{}, res_key:{}'.format(self._sim_info, self._obj, self._photo_targets, self._res_key)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.PhotographyTargets:
            return self._photo_targets
        return super().get_participants(participant_type, **kwargs)

class ZoneResolver(GlobalResolver):

    def __init__(self, zone_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_id = zone_id

    def __repr__(self):
        return 'ZoneResolver: zone_id: {}'.format(self._zone_id)

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.PickedZoneId:
            return (self._zone_id,)
        return super().get_participants(participant_type, **kwargs)

class StreetResolver(GlobalResolver):

    def __init__(self, street, **kwargs):
        super().__init__(**kwargs)
        self._street = street

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.Street:
            street_service = services.street_service()
            if street_service is None:
                return ()
            street_civic_policy_provider = street_service.get_provider(self._street)
            if street_civic_policy_provider is None:
                return ()
            return (street_civic_policy_provider,)
        return super().get_participants(participant_type, **kwargs)

class VenuePolicyProviderResolver(GlobalResolver):

    def __init__(self, venue_policy_provider, **kwargs):
        super().__init__(**kwargs)
        self._venue_policy_provider = venue_policy_provider

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.VenuePolicyProvider:
            return (self._venue_policy_provider,)
        return super().get_participants(participant_type, **kwargs)

class LotResolver(GlobalResolver):

    def __init__(self, lot, **kwargs):
        super().__init__(**kwargs)
        self._lot = lot

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.Lot:
            return (self._lot,)
        return super().get_participants(participant_type, **kwargs)

class HouseholdResolver(Resolver):

    def __init__(self, household, additional_participants={}, **kwargs):
        super().__init__(**kwargs)
        self._household = household
        self._additional_participants = additional_participants

    def get_participants(self, participant_type, **kwargs):
        if participant_type == ParticipantType.ActorHousehold:
            return (self._household,)
        if participant_type == ParticipantType.ActorHouseholdMembers:
            return tuple(self._household)
        if participant_type in self._additional_participants:
            return self._additional_participants[participant_type]
        base_results = self._get_participants_base(participant_type, **kwargs)
        if base_results is None:
            raise ValueError('Trying to use HouseholdResolver with something that is not supported: {}'.format(participant_type))
        return base_results
