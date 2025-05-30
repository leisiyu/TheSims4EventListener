import mathfrom protocolbuffers import GameplaySaveData_pb2from filters.household_template import HouseholdTemplatefrom sims4.tuning.tunable import TunableLiteralOrRandomValue, Tunable, TunableRange, TunableTuple, TunableList, TunableVariant, TunableSet, TunableReference, TunableMapping, TunableRegionDescription, TunablePercent, TunableInterval, TunableHouseDescriptionfrom story_progression import StoryProgressionFlagsfrom story_progression.story_progression_action import _StoryProgressionActionfrom story_progression.story_progression_action_fame import StoryProgressionActionFamefrom story_progression.story_progression_action_relationship_culling import StoryProgressionRelationshipCullingfrom story_progression.story_progression_action_sim_info_culling import StoryProgressionActionMaxPopulationfrom story_progression.story_progression_action_university import StoryProgressionActionUniversityfrom tunable_time import TunableTimeOfWeek, Daysfrom venues.venue_enums import VenueTypesimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('StoryProgression', default_owner='msantander')gameplay_neighborhood_data_constants = GameplaySaveData_pb2.GameplayNeighborhoodData
class TunableStoryProgressionActionVariant(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(initial_population=StoryProgressionInitialPopulation.TunableFactory(locked_args={'_time_of_week': None}), max_population=StoryProgressionActionMaxPopulation.TunableFactory(), rentable_lot_population=StoryProgressionDestinationPopulateAction.TunableFactory(), relationship_culling=StoryProgressionRelationshipCulling.TunableFactory(), fame=StoryProgressionActionFame.TunableFactory(), university=StoryProgressionActionUniversity.TunableFactory())

class StoryProgressionPopulateAction(_StoryProgressionAction):
    FACTORY_TUNABLES = {'_region_to_population_density': TunableMapping(description='\n        Based on region what percent of available lots will be filled.\n        ', key_name='Region Description', key_type=TunableRegionDescription(pack_safe=True), value_name='Population Density', value_type=TunableTuple(density=TunablePercent(description='\n                Percent of how much of the residential lots will be occupied of\n                all the available lots in that region.  If the current lot\n                density is greater than this value, then no household will be\n                moved in.\n                ', default=40), min_empty=TunableRange(description='\n                Minimum number of empty lots that should stay empty for this neighborhood.\n                ', tunable_type=int, default=2, minimum=0))), '_time_of_week': TunableTuple(description='\n        Only run this action when it is between a certain time of the week.\n        ', start_time=TunableTimeOfWeek(default_day=Days.SUNDAY, default_hour=2), end_time=TunableTimeOfWeek(default_day=Days.SUNDAY, default_hour=6))}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_time_checked = None

    def _get_neighborhood_proto(self):
        neighborhood_id = services.current_zone().neighborhood_id
        if neighborhood_id == 0:
            return
        return services.get_persistence_service().get_neighborhood_proto_buff(neighborhood_id)

    def _get_neighborhood_availability_data(self, neighborhood_proto_buff):
        num_zones_filled = 0
        available_zone_ids = set()
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        household_manager = services.household_manager()
        for lot_owner_info in neighborhood_proto_buff.lots:
            for lot_owner in lot_owner_info.lot_owner:
                if lot_owner.household_id > 0:
                    household = household_manager.get(lot_owner.household_id)
                    if household is None:
                        pass
                    else:
                        num_zones_filled += 1
                        break
            venue_tuning = venue_manager.get(lot_owner_info.venue_key)
            if not venue_tuning is None:
                pass
            if lot_owner_info.lot_template_id > 0:
                available_zone_ids.add(lot_owner_info.zone_instance_id)
        available_zone_ids.discard(services.current_zone_id())
        return (num_zones_filled, available_zone_ids)

    def _should_process(self):
        client = services.client_manager().get_first_client()
        if client is None:
            return False
        if client.account is None or client.household is None:
            return False
        neighborhood_population_service = services.neighborhood_population_service()
        if neighborhood_population_service is None:
            return False
        elif neighborhood_population_service.is_processing_requests:
            return False
        return True

    def should_process(self, options):
        if not self._should_process():
            return False
        if options & StoryProgressionFlags.ALLOW_POPULATION_ACTION:
            current_time = services.time_service().sim_now
            if not current_time.time_between_week_times(self._time_of_week.start_time(), self._time_of_week.end_time()):
                return False
            if self._last_time_checked is not None:
                time_elapsed = current_time - self._last_time_checked
                if time_elapsed.in_days() <= 1:
                    return False
        else:
            return False
        return True

    def _zone_population_completed_callback(self, success):
        pass

class StoryProgressionInitialPopulation(StoryProgressionPopulateAction):
    FACTORY_TUNABLES = {'_homeless_households': TunableInterval(description='\n        Random number of homeless households to create.\n        ', tunable_type=int, default_lower=1, default_upper=3, minimum=0)}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._homeless_households_completed = False

    @property
    def _initial_population_complete(self):
        if not self._homeless_households_completed:
            return False
        neighborhood_proto_buff = self._get_neighborhood_proto()
        if neighborhood_proto_buff is None:
            return True
        return neighborhood_proto_buff.gameplay_data.npc_population_state == gameplay_neighborhood_data_constants.COMPLETED

    def should_process(self, options):
        if not self._should_process():
            return False
        elif self._initial_population_complete:
            return False
        return True

    def _zone_population_completed_callback(self, success):
        neighborhood_proto_buff = self._get_neighborhood_proto()
        if success:
            neighborhood_proto_buff.gameplay_data.npc_population_state = gameplay_neighborhood_data_constants.COMPLETED

    def _homeless_household_completed_callback(self, success):
        self._homeless_households_completed = success

    def process_action(self, story_progression_flags):
        neighborhood_population_service = services.neighborhood_population_service()
        if neighborhood_population_service is None:
            return
        households = services.household_manager().values()
        num_homeless_households = sum(1 for household in households if household.home_zone_id == 0)
        if num_homeless_households >= self._homeless_households.lower_bound:
            self._homeless_household_completed_callback(True)
        else:
            num_homeless_households_to_add = self._homeless_households.random_int() - num_homeless_households
            neighborhood_population_service.add_homeless_household_request(num_homeless_households_to_add, self._homeless_household_completed_callback)
        neighborhood_proto_buff = self._get_neighborhood_proto()
        if neighborhood_proto_buff is None:
            return
        if StoryProgressionFlags.ALLOW_INITIAL_POPULATION not in story_progression_flags:
            self._zone_population_completed_callback(True)
            return
        if neighborhood_proto_buff.gameplay_data.npc_population_state != gameplay_neighborhood_data_constants.COMPLETED:
            neighborhood_proto_buff.gameplay_data.npc_population_state = gameplay_neighborhood_data_constants.STARTED
            self._zone_population_completed_callback(True)

class StoryProgressionDestinationPopulateAction(_StoryProgressionAction):
    FACTORY_TUNABLES = {'_region_to_rentable_zone_density': TunableMapping(description='\n        Based on region what percent of available lots will be filled.\n        ', key_name='Region Description', key_type=TunableRegionDescription(pack_safe=True), value_name='Rentable Zone Density', value_type=TunableTuple(_venues_to_populate=TunableSet(description='\n                A set of venue references that are considered to be rentable.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True)), household_description_to_ideal_travel_group_size=TunableMapping(description='\n                Based on the house description how many sims should go on vacation\n                ', key_name='House Description', key_type=TunableHouseDescription(pack_safe=True), value_name='Travel Group Size', value_type=TunableLiteralOrRandomValue(description='\n                    The maximum number of sims that should go on vacation to\n                    that lot.\n                    ', tunable_type=int, minimum=0)), bed_count_to_travel_group_size=TunableMapping(description='\n                Based on the house description how many sims should go on vacation\n                ', key_name='Number of beds', key_type=Tunable(description='\n                    The number of beds on the lot to determine how many sims\n                    can go in the vacation group.\n                    ', tunable_type=int, default=1), value_name='Travel Group Size', value_type=TunableLiteralOrRandomValue(description='\n                    The maximum number of sims that should go on vacation to\n                    that lot.\n                    ', tunable_type=int, minimum=0)), travel_group_size_to_household_template=TunableMapping(description='\n                Mapping to travel group size to household templates. If there\n                are no household that fulfill the requirement of renting a\n                zone, then random household template will chosen to be created\n                to rent a zone.\n                ', key_type=Tunable(tunable_type=int, default=1), value_type=TunableList(description='\n                    Household template that will be created for renting a zone.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE), class_restrictions=('HouseholdTemplate',)))), density=TunablePercent(description='\n                Percent of lots will be occupied once a user sim has rented a lot.\n                ', default=80), min_to_populate=TunableRange(description='\n                Minimum number of lots that should be rented.\n                ', tunable_type=int, default=3, minimum=0), duration=TunableLiteralOrRandomValue(description="\n                The maximum in sim days npc's should stay on vacation.\n                ", tunable_type=int, minimum=1, default=1)))}

    def should_process(self, options):
        if services.active_household_id() == 0:
            return False
        return True

    def _get_rentable_zones(self, rentable_zone_density_data, neighborhood_proto_buff):
        num_zones_rented = 0
        available_zone_ids = []
        travel_group_manager = services.travel_group_manager()
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        for lot_owner_info in neighborhood_proto_buff.lots:
            if lot_owner_info.venue_key == 0:
                pass
            elif venue_manager.get(lot_owner_info.venue_key) not in rentable_zone_density_data._venues_to_populate:
                pass
            else:
                zone_id = lot_owner_info.zone_instance_id
                if travel_group_manager.is_zone_rented(zone_id):
                    num_zones_rented += 1
                else:
                    available_zone_ids.append(zone_id)
        return (num_zones_rented, available_zone_ids)

    def process_action(self, story_progression_flags):
        zone = services.current_zone()
        neighborhood_proto = services.get_persistence_service().get_neighborhood_proto_buff(zone.neighborhood_id)
        region_id = neighborhood_proto.region_id
        rentable_zone_density_data = self._region_to_rentable_zone_density.get(region_id)
        if rentable_zone_density_data is None:
            return
        (num_zones_rented, available_zone_ids) = self._get_rentable_zones(rentable_zone_density_data, neighborhood_proto)
        num_available_zone_ids = len(available_zone_ids)
        if num_available_zone_ids == 0:
            return
        number_zones_to_fill = 0
        num_desired_zones_filled = math.floor((num_zones_rented + num_available_zone_ids)*rentable_zone_density_data.density)
        if num_desired_zones_filled < rentable_zone_density_data.min_to_populate:
            num_desired_zones_filled = rentable_zone_density_data.min_to_populate
        if num_zones_rented < num_desired_zones_filled:
            number_zones_to_fill = num_desired_zones_filled - num_zones_rented
        neighborhood_population_service = services.neighborhood_population_service()
        if neighborhood_population_service is None:
            return
        neighborhood_population_service.add_rentable_lot_request(number_zones_to_fill, zone.neighborhood_id, None, available_zone_ids, rentable_zone_density_data)
