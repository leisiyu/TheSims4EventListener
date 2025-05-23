from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.household import Household
    from sims.sim_info import SimInfo
    from typing import *from business.business_enums import BusinessType, BusinessOriginTelemetryContextfrom filters.household_template import HouseholdTemplate, _get_tunable_household_member_listfrom filters.sim_template import SimTemplateTypefrom sims.sim_spawner import SimSpawnerfrom sims4.tuning.tunable import OptionalTunable, TunableWorldDescription, Tunable, TunableList, TunableLotDescriptionfrom sims4.utils import classpropertyfrom world import get_lot_id_from_instance_idimport servicesimport sims4.loglogger = sims4.log.Logger('PremadeHousehold', default_owner='tingyul')
class PremadeHouseholdTemplate(HouseholdTemplate):
    INSTANCE_TUNABLES = {'_household_members': _get_tunable_household_member_list(template_type=SimTemplateType.PREMADE_HOUSEHOLD), '_hidden': Tunable(description='\n            If enabled, the household is hidden from Manage Households,\n            accessible from Managed Worlds.\n            ', tunable_type=bool, default=False), '_townie_street': OptionalTunable(description='\n            If enabled, this household is a townie household and is\n            assigned to a street.\n            ', tunable=TunableWorldDescription()), 'owned_residential_rental_lots': TunableList(description='\n            The lots owned by this household, if this is a Property Owner HH.\n            ', tunable=TunableLotDescription())}

    @classmethod
    def _tuning_loaded_callback(cls):
        for household_member_data in cls._household_members:
            sim_template = household_member_data.sim_template
            if sim_template.household_template is not None:
                logger.error('PremadeSimTemplate {} is used by multiple PreamdeHouseholdTemplates {}, {}', sim_template, sim_template.household_template, cls)
            sim_template.household_template = cls

    @classproperty
    def template_type(cls):
        return SimTemplateType.PREMADE_HOUSEHOLD

    @classmethod
    def create_premade_household(cls):
        account = services.account_service().get_account_by_id(SimSpawner.SYSTEM_ACCOUNT_ID)
        household = cls.create_household(None, account, creation_source='premade_household_template')
        if cls._hidden:
            household.set_to_hidden()
        if household is not None:
            household.name = cls.__name__
        household.premade_household_template_id = cls.guid64
        return household

    @classmethod
    def apply_fixup_to_household(cls, household:'Household', premade_sim_infos:'List[SimInfo]') -> 'None':
        if cls._townie_street is not None:
            if household.home_zone_id:
                logger.error('{} has Townie Street is tuned but household {} is not a townie household', cls, household)
            else:
                world_id = services.get_world_id(cls._townie_street)
                if not world_id:
                    logger.error('{} has invalid townie street: {}', cls, cls._townie_street)
                else:
                    household.set_home_world_id(world_id)
        if household.premade_household_template_id is not None:
            logger.info('Premade household template fixup applied. Household id: {}, Template id: {}', household.id, household.premade_household_template_id)
            household_template = cls._get_household_template_from_id(household.premade_household_template_id)
            if household_template is not None:
                tag_to_sim_info = {}
                household_members = household_template.get_household_members()
                for member in household_members:
                    premade_sim_info = premade_sim_infos.get(member.sim_template)
                    if premade_sim_info is not None:
                        tag_to_sim_info[member.household_member_tag] = premade_sim_info
                cls.set_household_relationships_by_tags(tag_to_sim_info, household)
                if household_template.owned_residential_rental_lots:
                    business_service = services.business_service()
                    persistence_service = services.get_persistence_service()
                    for lot_description in household_template.owned_residential_rental_lots:
                        lot_id = get_lot_id_from_instance_id(lot_description)
                        if not lot_id:
                            pass
                        else:
                            zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True, ignore_shared_plex=True)
                            zone_ids = business_service.make_owner(household.id, BusinessType.RENTAL_UNIT, zone_id, telemetry_context=BusinessOriginTelemetryContext.PREMADE)
                            if services.current_zone_id() in zone_ids:
                                services.get_multi_unit_ownership_service().get_tenants_household_ids(household.id, from_load=True)
                            for business_zone_id in zone_ids:
                                business_manager = business_service.get_business_manager_for_zone(business_zone_id)
                                if business_manager and business_manager.business_type == BusinessType.RENTAL_UNIT:
                                    business_manager.on_zone_load()
                                    if household.id == services.active_household_id():
                                        business_manager.send_data_to_client()
            household.premade_household_template_id = 0

    @classmethod
    def _get_household_template_from_id(cls, template_id):
        template_manager = services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE)
        household_template = template_manager.get(template_id)
        return household_template
