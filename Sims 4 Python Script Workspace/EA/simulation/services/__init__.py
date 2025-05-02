from __future__ import annotationsimport argparseimport functoolsimport gcimport timefrom services.tuning_managers import InstanceTuningManagersfrom sims4.resources import INSTANCE_TUNING_DEFINITIONSfrom sims4.tuning.instance_manager import TuningInstanceManagerimport game_servicesimport sims4.reloadimport sims4.service_managerfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from adoption.adoption_service import AdoptionService
    from apartments.landlord_service import LandlordService
    from autonomy.autonomy_service import AutonomyService
    from call_to_action.call_to_action_service import CallToActionService
    from careers.career_service import CareerService
    from civic_policies.street_civic_policy_service import StreetService
    from clans.clan_service import ClanService
    from clock import GameClock
    from clubs.club_service import ClubService
    from conditional_layers.conditional_layer_service import ConditionalLayerService
    from crafting.photography_service import PhotographyService
    from curfew.curfew_service import CurfewService
    from drama_scheduler.drama_scheduler import DramaScheduleService
    from dust.dust_service import DustService
    from dynamic_areas.dynamic_area import DynamicAreaService
    from ensemble.ensemble_service import EnsembleService
    from event_testing.event_manager_service import EventManagerService
    from experiment_service.experiment_service import ExperimentService
    from fashion_trends.fashion_trend_service import FashionTrendService
    from filters.demographics_service import DemographicsService
    from filters.neighborhood_population_service import NeighborhoodPopulationService
    from filters.sim_filter_service import SimFilterService
    from gameplay_options.misc_options_service import MiscOptionsService
    from global_flags.global_flag_service import GlobalFlagService
    from global_policies.global_policy_service import GlobalPolicyService
    from high_school_graduation.graduation_service import GraduationService
    from holidays.holiday_service import HolidayService
    from horse_competitions.hc_service import HorseCompetitionService
    from household_calendar.calendar_service import CalendarService
    from interactions.picker.purchase_picker_service import PurchasePickerService
    from interactions.privacy import PrivacyService
    from laundry.laundry_service import LaundryService
    from live_events.live_event_service import LiveEventService
    from lot_decoration.lot_decoration_service import LotDecorationService
    from lunar_cycle.lunar_cycle_service import LunarCycleService
    from lunar_cycle.lunar_events_service import LunarEventsService
    from multi_unit.multi_unit_event_service import MultiUnitEventService
    from multi_unit.multi_unit_ownership_service import MultiUnitOwnershipService
    from multi_unit.tenant_application_service import TenantApplicationService
    from narrative.narrative_service import NarrativeService
    from objects.animals.animal_service import AnimalService
    from objects.doors.door_service import DoorService
    from objects.gardening.gardening_service import GardeningService
    from objects.object_manager import InventoryManager, ObjectManager
    from objects.props.prop_manager import PropManager
    from organizations.organization_service import OrganizationService
    from performance.sim_responsiveness_service import SimResponsivenessService
    from plex.plex_service import PlexService
    from postures.posture_graph import PostureGraphService
    from protocolbuffers.FileSerialization_pb2 import NeighborhoodData
    from services.reincarnation_service import ReincarnationService
    from relationships.attraction_tuning import AttractionService
    from relationships.relationship_service import RelationshipService
    from relationships.satisfaction_tuning import SatisfactionService
    from seasons.season_service import SeasonService
    from server.clientmanager import ClientManager
    from server.config_service import ConfigService
    from services.cheat_service import CheatService
    from services.fire_service import FireService
    from services.matchmaking_service import MatchmakingService
    from services.object_lost_and_found_service import ObjectLostAndFoundService
    from services.object_routing_service import ObjectRoutingService
    from services.prom_service import PromService
    from services.rabbit_hole_service import RabbitHoleService
    from services.reset_and_delete_service import ResetAndDeleteService
    from services.roommate_service import RoommateService
    from services.style_service import StyleService
    from services.zone_reservation_service import ZoneReservationService
    from sickness.sickness_service import SicknessService
    from sims.aging.aging_service import AgingService
    from sims.culling.culling_service import CullingService
    from sims.daycare import DaycareService
    from sims.hidden_sim_service import HiddenSimService
    from sims.household import Household
    from sims.household_manager import HouseholdManager
    from sims.household_utilities.utilities_manager import ZoneUtilitiesManager
    from sims.master_controller import MasterController
    from sims.secrets.sim_secrets_service import SimSecretsService
    from sims.sim_info_manager import SimInfoManager
    from sims.sim_spawner_service import SimSpawnerService
    from situations.npc_hosted_situations import NPCHostedSituationService
    from situations.service_npcs.service_npc_manager import ServiceNpcService
    from situations.situation_manager import SituationManager
    from social_media.social_media_service import SocialMediaService
    from socials.clustering import SocialGroupClusterService
    from statistics.lifestyle_service import LifestyleService
    from story_progression.story_progression_service import StoryProgressionService
    from time_service import TimeService
    from travel_group.travel_group_manager import TravelGroupManager
    from trends.trend_service import TrendService
    from tutorials.tutorial_service import TutorialService
    from ui.ui_dialog_service import UiDialogService
    from unique_object.unique_object_service import UniqueObjectService
    from venues.venue_service import VenueGameService, VenueService
    from weather.weather_service import WeatherService
    from wills.will_service import WillService
    from world.lot import Lot
    from world.region import Region
    from world.region_service import RegionService
    from world.street import Street
    from zone import Zone
    from zone_modifier.zone_modifier_service import ZoneModifierService
    from zone_spin_up_service import ZoneSpinUpService
    import weakreftry:
    import _zone
except ImportError:

    class _zone:

        @staticmethod
        def invite_sims_to_zone(*_, **__):
            pass

        @staticmethod
        def get_house_description_id(*_, **__):
            pass

        @staticmethod
        def get_building_type(*_, **__):
            return 0

        @staticmethod
        def get_eco_footprint_value(*_, **__):
            return 0

        @staticmethod
        def get_rent(*_, **__):
            return 0

        @staticmethod
        def set_initial_unit_rent_prices(*_, **__) -> 'int':
            return 0

        @staticmethod
        def get_signed_lease_length(*_, **__) -> 'int':
            return 0

        @staticmethod
        def get_lot_description_id(*_, **__):
            pass

        @staticmethod
        def get_world_description_id(*_, **__):
            pass

        @staticmethod
        def get_world_id(*_, **__):
            pass

        @staticmethod
        def get_world_and_lot_description_id_from_zone_id(*_, **__):
            pass

        @staticmethod
        def get_is_eco_footprint_compatible_for_world_description(*_, **__):
            return False

        @staticmethod
        def get_hide_from_lot_picker(*_, **__):
            pass

        @staticmethod
        def is_event_enabled(*_, **__):
            pass

        @staticmethod
        def is_granted_or_non_account_reward_item(*_, **__):
            pass
invite_sims_to_zone = _zone.invite_sims_to_zoneget_house_description_id = _zone.get_house_description_idis_event_enabled = _zone.is_event_enabledget_building_type = _zone.get_building_typeget_eco_footprint_value = _zone.get_eco_footprint_valueget_rent = _zone.get_rentset_initial_unit_rent_prices = _zone.set_initial_unit_rent_pricesget_signed_lease_length = _zone.get_signed_lease_lengthget_lot_description_id = _zone.get_lot_description_idget_world_description_id = _zone.get_world_description_idget_world_id = _zone.get_world_idget_world_and_lot_description_id_from_zone_id = _zone.get_world_and_lot_description_id_from_zone_idget_is_eco_footprint_compatible_for_world_description = _zone.get_is_eco_footprint_compatible_for_world_descriptionget_hide_from_lot_picker = _zone.get_hide_from_lot_pickeris_granted_or_non_account_reward_item = _zone.is_granted_or_non_account_reward_itemwith sims4.reload.protected(globals()):
    tuning_managers = InstanceTuningManagers()
    get_instance_manager = tuning_managers.__getitem__
    _account_service = None
    _zone_manager = None
    _server_clock_service = None
    _persistence_service = None
    _distributor_service = None
    _intern_service = None
    _terrain_service = None
    definition_manager = None
    snippet_manager = None
    _terrain_object = None
    _object_leak_tracker = Nonefor definition in INSTANCE_TUNING_DEFINITIONS:
    accessor_name = definition.manager_name
    accessor = functools.partial(tuning_managers.__getitem__, definition.TYPE_ENUM_VALUE)
    globals()[accessor_name] = accessorproduction_logger = sims4.log.ProductionLogger('Services')logger = sims4.log.Logger('Services')time_delta = Nonegc_collection_enable = True
class TimeStampService(sims4.service_manager.Service):

    def start(self):
        global gc_collection_enable, time_delta
        if gc_collection_enable:
            gc.disable()
            production_logger.info('GC disabled')
            gc_collection_enable = False
        else:
            gc.enable()
            production_logger.info('GC enabled')
            gc_collection_enable = True
        time_stamp = time.time()
        production_logger.info('TimeStampService start at {}'.format(time_stamp))
        logger.info('TimeStampService start at {}'.format(time_stamp))
        if time_delta is None:
            time_delta = time_stamp
        else:
            time_delta = time_stamp - time_delta
            production_logger.info('Time delta from loading start is {}'.format(time_delta))
            logger.info('Time delta from loading start is {}'.format(time_delta))
        return True

def start_global_services(initial_ticks):
    global _account_service, _zone_manager, _distributor_service, _intern_service
    create_server_clock(initial_ticks)
    from distributor.distributor_service import DistributorService
    from intern_service import InternService
    from server.account_service import AccountService
    from services.persistence_service import PersistenceService
    from services.terrain_service import TerrainService
    from sims4.tuning.serialization import FinalizeTuningService
    from zone_manager import ZoneManager
    parser = argparse.ArgumentParser()
    parser.add_argument('--python_autoleak', default=False, action='store_true')
    (args, unused_args) = parser.parse_known_args()
    if args.python_autoleak:
        create_object_leak_tracker()
    _account_service = AccountService()
    _zone_manager = ZoneManager()
    _distributor_service = DistributorService()
    _intern_service = InternService()
    init_critical_services = [server_clock_service(), get_persistence_service()]
    services = [_distributor_service, _intern_service, _intern_service.get_start_interning(), TimeStampService]
    instantiated_tuning_managers = []
    for definition in INSTANCE_TUNING_DEFINITIONS:
        instantiated_tuning_managers.append(tuning_managers[definition.TYPE_ENUM_VALUE])
    services.append(TuningInstanceManager(instantiated_tuning_managers))
    services.extend([FinalizeTuningService, TimeStampService, _intern_service.get_stop_interning(), get_terrain_service(), _zone_manager, _account_service])
    sims4.core_services.start_services(init_critical_services, services)

def stop_global_services():
    global _zone_manager, _account_service, _event_manager, _server_clock_service, _persistence_service, _terrain_service, _distributor_service, _intern_service, _object_leak_tracker
    _zone_manager.shutdown()
    _zone_manager = None
    tuning_managers.clear()
    _account_service = None
    _event_manager = None
    _server_clock_service = None
    _persistence_service = None
    _terrain_service = None
    _distributor_service = None
    _intern_service = None
    if _object_leak_tracker is not None:
        _object_leak_tracker = None

def create_object_leak_tracker(start=False):
    global _object_leak_tracker
    from performance.object_leak_tracker import ObjectLeakTracker
    if _object_leak_tracker is None:
        _object_leak_tracker = ObjectLeakTracker()
        if start:
            _object_leak_tracker.start_tracking()
        return True
    return False

def get_object_leak_tracker():
    return _object_leak_tracker

def get_zone_manager():
    return _zone_manager

def current_zone() -> 'Zone':
    if _zone_manager is not None:
        return _zone_manager.current_zone

def current_zone_id() -> 'Optional[int]':
    if _zone_manager is not None:
        return sims4.zone_utils.zone_id

def current_zone_info() -> 'Tuple[int, int, int, NeighborhoodData]':
    zone = current_zone()
    return zone.get_zone_info()

def current_region() -> 'Optional[Region]':
    zone = current_zone()
    if zone is not None:
        return zone.region

def current_region_instance():
    _region_service = region_service()
    if _region_service is None:
        return
    _current_region = current_region()
    if _current_region is None:
        return
    return _region_service.get_region_instance_by_tuning(_current_region)

def current_street() -> 'Optional[Street]':
    zone = current_zone()
    if zone is not None:
        return zone.street

def get_zone(zone_id:'int', allow_uninstantiated_zones:'bool'=False) -> 'Optional[Zone]':
    if _zone_manager is not None:
        return _zone_manager.get(zone_id, allow_uninstantiated_zones=allow_uninstantiated_zones)

def active_lot() -> 'Optional[Lot]':
    zone = current_zone()
    if zone is not None:
        return zone.lot

def active_lot_id():
    lot = active_lot()
    if lot is not None:
        return lot.lot_id

def client_object_managers():
    if game_services.service_manager is not None:
        return game_services.service_manager.client_object_managers
    return ()

def sim_info_manager() -> 'SimInfoManager':
    return game_services.service_manager.sim_info_manager

def posture_graph_service(zone_id:'Optional[int]'=None) -> 'Optional[PostureGraphService]':
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.posture_graph_service
        return
    return _zone_manager.get(zone_id).posture_graph_service

def sim_spawner_service(zone_id:'Optional[int]'=None) -> 'SimSpawnerService':
    if zone_id is None:
        return current_zone().sim_spawner_service
    return _zone_manager.get(zone_id).sim_spawner_service

def locator_manager():
    return current_zone().locator_manager

def object_manager(zone_id:'Optional[int]'=None) -> 'Optional[ObjectManager]':
    if zone_id is None:
        zone = current_zone()
    else:
        zone = _zone_manager.get(zone_id)
    if zone is not None:
        return zone.object_manager

def inventory_manager(zone_id:'Optional[int]'=None) -> 'Optional[InventoryManager]':
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.inventory_manager
        return
    return _zone_manager.get(zone_id).inventory_manager

def prop_manager(zone_id:'Optional[int]'=None) -> 'Optional[PropManager]':
    if zone_id is None:
        zone = current_zone()
    else:
        zone = _zone_manager.get(zone_id)
    if zone is not None:
        return zone.prop_manager

def social_group_manager():
    return current_zone().social_group_manager

def client_manager() -> 'ClientManager':
    return game_services.service_manager.client_manager

def get_first_client():
    return client_manager().get_first_client()

def get_selectable_sims():
    return get_first_client().selectable_sims

def owning_household_id_of_active_lot() -> 'Optional[int]':
    zone = current_zone()
    if zone is not None:
        return zone.lot.zone_owner_household_id

def owning_household_of_active_lot() -> 'Optional[Household]':
    zone = current_zone()
    if zone is not None:
        return household_manager().get(zone.lot.zone_owner_household_id)

def object_preference_overrides_tracker(create_tracker=True):
    zone = current_zone()
    if zone is not None:
        if zone.object_preference_overrides_tracker is None:
            from autonomy.autonomy_object_preference_tracker import AutonomyObjectPreferenceTracker
            zone.object_preference_overrides_tracker = AutonomyObjectPreferenceTracker()
        return zone.object_preference_overrides_tracker

def object_preference_tracker(require_active_household=False, disable_overrides=False):
    zone = current_zone()
    if zone is None:
        return

    def override_tracker(base_tracker):
        if disable_overrides or zone.object_preference_overrides_tracker is None:
            return base_tracker
        return zone.object_preference_overrides_tracker.override_tracker(base_tracker)

    travel_group = travel_group_manager().get_travel_group_by_zone_id(zone.id)
    if travel_group is not None:
        if require_active_household:
            household = household_manager().get(zone.lot.zone_owner_household_id)
            if household is not None:
                if not household.is_active_household:
                    return override_tracker(None)
            elif not travel_group.is_active_sim_in_travel_group:
                return override_tracker(None)
        if travel_group.object_preference_tracker is not None:
            return override_tracker(travel_group.object_preference_tracker)
    household = household_manager().get(zone.lot.zone_owner_household_id)
    if household is None or not (require_active_household and household.is_active_household):
        return override_tracker(None)
    return override_tracker(household.object_preference_tracker)

def get_active_sim():
    client = client_manager().get_first_client()
    if client is not None:
        return client.active_sim

def active_sim_info():
    client = client_manager().get_first_client()
    if client is not None:
        return client.active_sim_info

def active_household():
    client = client_manager().get_first_client()
    if client is not None:
        return client.household

def active_household_id():
    client = client_manager().get_first_client()
    if client is not None:
        return client.household_id

def active_household_lot_id():
    household = active_household()
    if household is not None:
        home_zone = get_zone(household.home_zone_id)
        if home_zone is not None:
            lot = home_zone.lot
            if lot is not None:
                return lot.lot_id

def privacy_service() -> 'PrivacyService':
    return current_zone().privacy_service

def autonomy_service() -> 'AutonomyService':
    return current_zone().autonomy_service

def get_aging_service() -> 'AgingService':
    return game_services.service_manager.aging_service

def get_cheat_service() -> 'CheatService':
    return game_services.service_manager.cheat_service

def neighborhood_population_service() -> 'NeighborhoodPopulationService':
    return current_zone().neighborhood_population_service

def get_reset_and_delete_service() -> 'ResetAndDeleteService':
    return current_zone().reset_and_delete_service

def venue_service() -> 'VenueService':
    return current_zone().venue_service

def venue_game_service() -> 'Optional[VenueGameService]':
    return getattr(game_services.service_manager, 'venue_game_service', None)

def zone_spin_up_service() -> 'ZoneSpinUpService':
    return current_zone().zone_spin_up_service

def household_manager() -> 'HouseholdManager':
    return game_services.service_manager.household_manager

def travel_group_manager(zone_id:'Optional[int]'=None) -> 'Optional[TravelGroupManager]':
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.travel_group_manager
        return
    return _zone_manager.get(zone_id).travel_group_manager

def utilities_manager(household_id:'Optional[int]'=None) -> 'Optional[ZoneUtilitiesManager]':
    if household_id:
        return get_utilities_manager_by_household_id(household_id)
    return get_utilities_manager_by_zone_id(current_zone_id())

def get_utilities_manager_by_household_id(household_id:'int') -> 'Optional[ZoneUtilitiesManager]':
    return game_services.service_manager.utilities_manager.get_manager_for_household(household_id)

def get_utilities_manager_by_zone_id(zone_id:'int') -> 'Optional[ZoneUtilitiesManager]':
    return game_services.service_manager.utilities_manager.get_manager_for_zone(zone_id)

def ui_dialog_service() -> 'UiDialogService':
    return current_zone().ui_dialog_service

def config_service() -> 'ConfigService':
    return game_services.service_manager.config_service

def sim_quadtree() -> 'Any':
    return current_zone().sim_quadtree

def single_part_condition_list() -> 'Dict[weakref.ReferenceType]':
    return current_zone().single_part_condition_list

def multi_part_condition_list() -> 'Dict[weakref.ReferenceType]':
    return current_zone().multi_part_condition_list

def get_event_manager() -> 'EventManagerService':
    return game_services.service_manager.event_manager_service

def get_current_venue():
    service = venue_service()
    if service is not None:
        return service.active_venue

def get_intern_service():
    return _intern_service

def get_zone_situation_manager(zone_id:'Optional[int]'=None) -> 'SituationManager':
    if zone_id is None:
        return current_zone().situation_manager
    return _zone_manager.get(zone_id).situation_manager

def npc_hosted_situation_service() -> 'NPCHostedSituationService':
    return current_zone().n_p_c_hosted_situation_service

def ensemble_service() -> 'EnsembleService':
    return current_zone().ensemble_service

def sim_filter_service(zone_id:'Optional[int]'=None) -> 'SimFilterService':
    if zone_id is None:
        return current_zone().sim_filter_service
    return _zone_manager.get(zone_id).sim_filter_service

def get_photography_service() -> 'PhotographyService':
    return current_zone().photography_service

def social_group_cluster_service() -> 'SocialGroupClusterService':
    return current_zone().social_group_cluster_service

def on_client_connect(client):
    sims4.core_services.service_manager.on_client_connect(client)
    game_services.service_manager.on_client_connect(client)
    current_zone().service_manager.on_client_connect(client)

def on_client_disconnect(client):
    sims4.core_services.service_manager.on_client_disconnect(client)
    if game_services.service_manager.allow_shutdown:
        game_services.service_manager.on_client_disconnect(client)
    current_zone().service_manager.on_client_disconnect(client)

def on_enter_main_menu():
    pass

def account_service():
    return _account_service

def business_service():
    bs = game_services.service_manager.business_service
    return bs

def payment_altering_service():
    ps = game_services.service_manager.payment_altering_service
    return ps

def dynamic_area_service() -> 'DynamicAreaService':
    return current_zone().dynamic_area_service

def get_terrain_service():
    global _terrain_service
    if _terrain_service is None:
        from services.terrain_service import TerrainService
        _terrain_service = TerrainService()
    return _terrain_service

def call_to_action_service() -> 'CallToActionService':
    return game_services.service_manager.call_to_action_service

def trend_service() -> 'TrendService':
    return game_services.service_manager.trend_service

def fashion_trend_service() -> 'Optional[FashionTrendService]':
    return getattr(game_services.service_manager, 'fashion_trend_service', None)

def time_service() -> 'TimeService':
    return game_services.service_manager.time_service

def game_clock_service() -> 'GameClock':
    return game_services.service_manager.game_clock

def server_clock_service():
    if _server_clock_service is None:
        return
    return _server_clock_service

def create_server_clock(initial_ticks):
    global _server_clock_service
    import clock
    _server_clock_service = clock.ServerClock(ticks=initial_ticks)

def get_master_controller() -> 'MasterController':
    return current_zone().master_controller

def get_persistence_service():
    global _persistence_service
    if _persistence_service is None:
        from services.persistence_service import PersistenceService
        _persistence_service = PersistenceService()
    return _persistence_service

def get_distributor_service():
    return _distributor_service

def get_fire_service() -> 'FireService':
    return current_zone().fire_service

def get_career_service() -> 'CareerService':
    return current_zone().career_service

def get_story_progression_service() -> 'StoryProgressionService':
    return current_zone().story_progression_service

def daycare_service() -> 'Optional[DaycareService]':
    zone = current_zone()
    if zone is not None:
        return zone.daycare_service

def get_adoption_service() -> 'AdoptionService':
    return current_zone().adoption_service

def get_laundry_service() -> 'Optional[LaundryService]':
    zone = current_zone()
    if zone is not None and hasattr(zone, 'laundry_service'):
        return zone.laundry_service

def get_object_routing_service() -> 'Optional[ObjectRoutingService]':
    zone = current_zone()
    if zone is not None and hasattr(zone, 'object_routing_service'):
        return zone.object_routing_service

def get_landlord_service() -> 'Optional[LandlordService]':
    return getattr(game_services.service_manager, 'landlord_service', None)

def get_roommate_service() -> 'Optional[RoommateService]':
    return getattr(game_services.service_manager, 'roommate_service', None)

def get_club_service() -> 'Optional[ClubService]':
    return getattr(game_services.service_manager, 'club_service', None)

def get_social_media_service() -> 'Optional[SocialMediaService]':
    return getattr(game_services.service_manager, 'social_media_service', None)

def get_matchmaking_service() -> 'Optional[MatchmakingService]':
    return getattr(game_services.service_manager, 'matchmaking_service', None)

def get_culling_service() -> 'CullingService':
    return game_services.service_manager.culling_service

def get_gardening_service() -> 'GardeningService':
    return current_zone().gardening_service

def drama_scheduler_service() -> 'DramaScheduleService':
    return current_zone().drama_schedule_service

def get_plex_service() -> 'PlexService':
    return current_zone().plex_service

def get_door_service() -> 'DoorService':
    return current_zone().door_service

def get_zone_modifier_service() -> 'ZoneModifierService':
    return current_zone().zone_modifier_service

def get_demographics_service() -> 'DemographicsService':
    return current_zone().demographics_service

def get_service_npc_service() -> 'ServiceNpcService':
    return current_zone().service_npc_service

def conditional_layer_service() -> 'ConditionalLayerService':
    return current_zone().conditional_layer_service

def dust_service() -> 'Optional[DustService]':
    zone = current_zone()
    if hasattr(zone, 'dust_service'):
        return zone.dust_service

def get_sickness_service() -> 'SicknessService':
    return game_services.service_manager.sickness_service

def animal_service() -> 'Optional[AnimalService]':
    return getattr(game_services.service_manager, 'animal_service', None)

def get_prom_service() -> 'Optional[PromService]':
    return getattr(game_services.service_manager, 'prom_service', None)

def get_curfew_service() -> 'CurfewService':
    return game_services.service_manager.curfew_service

def get_locale():
    client = get_first_client()
    return client.account.locale

def relationship_service() -> 'RelationshipService':
    return game_services.service_manager.relationship_service

def sim_secrets_service() -> 'Optional[SimSecretsService]':
    return getattr(game_services.service_manager, 'sim_secrets_service', None)

def hidden_sim_service() -> 'HiddenSimService':
    return game_services.service_manager.hidden_sim_service

def weather_service() -> 'Optional[WeatherService]':
    return getattr(game_services.service_manager, 'weather_service', None)

def season_service() -> 'Optional[SeasonService]':
    return getattr(game_services.service_manager, 'season_service', None)

def lot_decoration_service() -> 'Optional[LotDecorationService]':
    return getattr(game_services.service_manager, 'lot_decoration_service', None)

def get_style_service() -> 'StyleService':
    return game_services.service_manager.style_service

def get_tutorial_service() -> 'TutorialService':
    return game_services.service_manager.tutorial_service

def calendar_service() -> 'CalendarService':
    return current_zone().calendar_service

def get_rabbit_hole_service() -> 'RabbitHoleService':
    return game_services.service_manager.rabbit_hole_service

def holiday_service() -> 'Optional[HolidayService]':
    return getattr(game_services.service_manager, 'holiday_service', None)

def global_policy_service() -> 'Optional[GlobalPolicyService]':
    return getattr(game_services.service_manager, 'global_policy_service', None)

def narrative_service() -> 'Optional[NarrativeService]':
    return getattr(game_services.service_manager, 'narrative_service', None)

def organization_service() -> 'Optional[OrganizationService]':
    return getattr(game_services.service_manager, 'organization_service', None)

def get_object_lost_and_found_service() -> 'ObjectLostAndFoundService':
    return game_services.service_manager.object_lost_and_found_service

def street_service() -> 'Optional[StreetService]':
    return getattr(game_services.service_manager, 'street_service', None)

def region_service() -> 'Optional[RegionService]':
    return getattr(game_services.service_manager, 'region_service', None)

def lifestyle_service() -> 'LifestyleService':
    return game_services.service_manager.lifestyle_service

def get_live_event_service() -> 'Optional[LiveEventService]':
    return getattr(game_services.service_manager, 'live_event_service', None)

def get_zone_reservation_service() -> 'ZoneReservationService':
    return game_services.service_manager.zone_reservation_service

def purchase_picker_service() -> 'PurchasePickerService':
    return game_services.service_manager.purchase_picker_service

def global_flag_service() -> 'GlobalFlagService':
    return game_services.service_manager.global_flag_service

def misc_options_service() -> 'MiscOptionsService':
    return game_services.service_manager.misc_options_service

def lunar_cycle_service() -> 'LunarCycleService':
    return game_services.service_manager.lunar_cycle_service

def lunar_events_service() -> 'LunarEventsService':
    return game_services.service_manager.lunar_events_service

def clan_service() -> 'Optional[ClanService]':
    return getattr(game_services.service_manager, 'clan_service', None)

def get_graduation_service() -> 'Optional[GraduationService]':
    return getattr(game_services.service_manager, 'graduation_service', None)

def get_horse_competition_service() -> 'Optional[HorseCompetitionService]':
    return getattr(game_services.service_manager, 'horse_competition_service', None)

def get_sim_responsiveness_service() -> 'SimResponsivenessService':
    return game_services.service_manager.sim_responsiveness_service

def multi_unit_event_service() -> 'Optional[MultiUnitEventService]':
    return getattr(game_services.service_manager, 'multi_unit_event_service', None)

def get_multi_unit_ownership_service() -> 'Optional[MultiUnitOwnershipService]':
    return getattr(game_services.service_manager, 'multi_unit_ownership_service', None)

def get_tenant_application_service() -> 'Optional[TenantApplicationService]':
    return getattr(game_services.service_manager, 'tenant_application_service', None)

def get_attraction_service() -> 'Optional[AttractionService]':
    return getattr(game_services.service_manager, 'attraction_service', None)

def get_satisfaction_service() -> 'Optional[SatisfactionService]':
    return getattr(game_services.service_manager, 'satisfaction_service', None)

def get_reincarnation_service() -> 'Optional[ReincarnationService]':
    return getattr(game_services.service_manager, 'reincarnation_service', None)

def get_will_service() -> 'Optional[WillService]':
    return getattr(game_services.service_manager, 'will_service', None)

def unique_object_service() -> 'UniqueObjectService':
    return game_services.service_manager.unique_object_service

def get_experiment_service() -> 'Optional[ExperimentService]':
    return game_services.service_manager.experiment_service

def c_api_gsi_dump():
    import server_commands.developer_commands
    server_commands.developer_commands.gsi_dump()
