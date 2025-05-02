from __future__ import annotationsfrom distributor.system import Distributorfrom filters.sim_template import SimTemplateTypefrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom typing import TYPE_CHECKINGimport date_and_timeimport persistence_error_typesimport protocolbuffersimport randomimport servicesimport sims4.logimport sims4.resourcesfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimAndHouseholdResolverfrom filters.household_template import HouseholdTemplatefrom filters.tunable import TunableSimFilterfrom server_commands import household_commandsfrom multi_unit.multi_unit_tuning import MultiUnitTuningfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom sims.household import Householdfrom sims.sim_info_types import Age, Species, Genderfrom sims.sim_spawner import SimSpawnerfrom sims4.common import Packfrom sims4.math import clampfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableList, TunableInterval, TunableReference, TunableRange, TunableMapping, TunablePackSafeReferencefrom sims4.utils import classpropertyfrom tunable_multiplier import TunableMultiplierfrom world.premade_household_template import PremadeHouseholdTemplatefrom world.premade_sim_fixup_helper import PremadeSimFixupHelperif TYPE_CHECKING:
    from typing import *
    from protocolbuffers.Business_pb2 import PotentialTenantApplicationHouseholdslogger = sims4.log.Logger('TenantApplicationService', default_owner='micfisher')
class TenantApplicationHousehold:

    def __init__(self, household_name:'str', household_occupants:'List[Tuple[Age, Species]]', desired_beds:'int', desired_rent:'Mapping[int, float]', household_data:'int', household_name_key:'int'=0, zone_id:'int'=0) -> 'None':
        self.household_name = household_name
        self.household_occupants = household_occupants
        self.desired_beds = desired_beds
        self.desired_rent = desired_rent
        self.household_data = household_data
        self.household_name_key = household_name_key
        self.zone_id = zone_id

class TenantApplicationService(Service):
    MAX_NUMBER_OF_HOUSEHOLDS = 15
    PREMADE_TENANT_HOUSEHOLD_TEMPLATES = TunableList(description='\n        A list of all premade Tenant Household Templates that are part of the household generator.\n        ', tunable=TunableReference(description='\n            Individual Tenant Household Templates to randomly pick from.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE), class_restrictions='PremadeHouseholdTemplate', pack_safe=True, allow_none=True))
    RANDOM_TENANT_HOUSEHOLD_TEMPLATES = TunableList(description='\n        A list of all Tenant Household Templates that can appear in the household generator. Used if all premades are\n        already selected.\n        ', tunable=TunableReference(description='\n            Individual Tenant Household Templates to randomly pick from.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE), class_restrictions='HouseholdTemplate', pack_safe=True))
    HOMELESS_HOUSEHOLD_TENANT_FILTER = TunablePackSafeReference(description='\n        The filter that should apply to homeless households to ensure we only get the households we want.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=TunableSimFilter)
    BLACKLIST_HOUSEHOLD_FILTER = TunablePackSafeReference(description="\n        The filter that should apply to homeless households to ensure we don't get anything included in this filter.\n        ", manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=TunableSimFilter)
    HOMELESS_HOUSEHOLD_WEIGHT = TunableRange(description='\n        The weight that a homeless household will be selected.\n        ', tunable_type=int, minimum=1, maximum=10, default=6)
    PREMADE_HOUSEHOLD_TEMPLATE_WEIGHT = TunableRange(description='\n        The weight that a premade household template will be selected.\n        ', tunable_type=int, minimum=1, maximum=10, default=3)
    NUMBER_OF_POTENTIAL_HOUSEHOLDS = TunableMapping(description='\n        A mapping of star rating to a range of number of households that should appear in the list of \n        potential tenant households.\n        ', key_type=TunableRange(description='\n            The range of star ratings, should be 1-5.\n            ', tunable_type=int, minimum=1, maximum=5, default=1), value_type=TunableInterval(description='\n            The minimum and maximum number of households to be displayed, depending on the star rating.\n            ', tunable_type=int, default_lower=1, default_upper=10, minimum=1, maximum=15))
    DESIRED_RENT_BOUNDS = TunableMapping(description='\n        A mapping of star rating (as an integer) to percentage of max rent, within a range.\n        ', key_type=TunableRange(description='\n            The range of star ratings, should be 1-5.\n            ', tunable_type=int, minimum=1, maximum=5, default=1), value_type=TunableInterval(description='\n            A tuple containing the lower bound and upper bound of the percentage of max rent for this star rating.\n            ', tunable_type=float, default_lower=0.25, default_upper=0.75, minimum=0, maximum=1))
    DESIRED_RENT_MULTIPLIER = TunableMultiplier.TunableFactory(description="\n        A multiplier to change an existing household's desired rent. Template households are tuned on the \n        household template.\n        ")

    def __init__(self) -> 'None':
        self._potential_tenant_household_list = []
        self._premade_tenant_household_selected = dict.fromkeys([household_template.guid64 for household_template in self.PREMADE_TENANT_HOUSEHOLD_TEMPLATES], False)
        self._potential_tenant_household_map = {}
        self._num_tenant_households_map = {}
        self._last_data_update_time = date_and_time.DATE_AND_TIME_ZERO
        self._force_list_refresh = False

    @classproperty
    def required_packs(cls) -> 'Tuple[Pack, ...]':
        return (Pack.EP15,)

    def get_sim_ages_and_species_from_household(self, household_data:'Union[Household, HouseholdTemplate]'=None) -> 'List[Tuple[Age, Species]]':
        sim_ages_and_species = []
        if isinstance(household_data, Household):
            for household_member in household_data.sim_infos:
                sim_ages_and_species.append((household_member.age, household_member.extended_species))
        elif household_data.template_type == SimTemplateType.PREMADE_HOUSEHOLD:
            household_member_data = household_data.get_household_members()
            for household_member in household_member_data:
                sim_info_base = SimInfoBaseWrapper()
                sim_info_base.load_from_resource(household_member.sim_template._sim_creation_info.resource_key)
                sim_ages_and_species.append((sim_info_base.age, sim_info_base.extended_species))
        else:
            household_member_data = household_data.get_household_members()
            for household_member in household_member_data:
                sim_ages_and_species.append((household_member.sim_template._sim_creation_info.age_variant.get_age(), household_member.sim_template.sim_creator.species))
        return sim_ages_and_species

    def select_homeless_household(self, homeless_households:'List[Household]') -> 'None':
        homeless_household = homeless_households.pop()
        self._potential_tenant_household_map[homeless_household.id] = homeless_household
        self.add_household_template(homeless_household)

    def select_premade_tenant_household_template(self, available_premade_templates:'List[HouseholdTemplate]') -> 'None':
        premade_template = available_premade_templates.pop()
        self._potential_tenant_household_map[premade_template.guid64] = premade_template
        self.add_household_template(premade_template)

    def select_random_tenant_household_template(self) -> 'None':
        premade_template = random.choice(self.RANDOM_TENANT_HOUSEHOLD_TEMPLATES)
        self.add_household_template(premade_template)

    def get_desired_rent(self, household_data:'Union[Household, HouseholdTemplate]') -> 'Mapping[int, float]':
        desired_rent_percentages = {}
        if isinstance(household_data, Household):
            resolver = SingleSimAndHouseholdResolver(household_data.sim_infos[0], household_data)
            multiplier = self.DESIRED_RENT_MULTIPLIER.get_multiplier(resolver)
        else:
            multiplier = household_data.desired_rent_multiplier
        for (star_rating, (lower_bound, upper_bound)) in self.DESIRED_RENT_BOUNDS.items():
            desired_rent_percentage = random.uniform(lower_bound, upper_bound)*multiplier
            desired_rent_percentages[star_rating] = clamp(0, desired_rent_percentage, 1)
        return desired_rent_percentages

    def add_household_template(self, household_data:'Union[Household, HouseholdTemplate]') -> 'None':
        if isinstance(household_data, Household):
            self._potential_tenant_household_list.append(TenantApplicationHousehold(household_data.name, self.get_sim_ages_and_species_from_household(household_data), self.get_beds_wanted(household_data), self.get_desired_rent(household_data), household_data.id))
        else:
            if issubclass(household_data, PremadeHouseholdTemplate):
                household_member_data = household_data.get_household_members()
                household_name_key = household_member_data[0].sim_template._sim_creation_info.last_name.hash
                household_name = ''
            else:
                gender = Gender.MALE if round(random.random(), 2) > 0.5 else Gender.FEMALE
                household_name = SimSpawner.get_random_last_name(gender=gender)
                if household_name == '':
                    logger.error('Household name should not be empty, but get_random_last_name returned empty string.')
                household_name_key = 0
            self._potential_tenant_household_list.append(TenantApplicationHousehold(household_name, self.get_sim_ages_and_species_from_household(household_data), self.get_beds_wanted(household_data), self.get_desired_rent(household_data), household_data.guid64, household_name_key))

    def move_in_household(self, household_id:'int', zone_id:'int', household_name:'str') -> 'None':
        household_data = self._potential_tenant_household_map.get(household_id)
        if household_data is None:
            return
        if isinstance(household_data, Household):
            household = household_data
            household_data.move_into_zone(zone_id)
        elif self._premade_tenant_household_selected.get(household_id) is not None:
            self._premade_tenant_household_selected[household_id] = True
            household = household_data.create_household(zone_id, family_name=household_name)
            household.premade_household_template_id = household_id
            helper = PremadeSimFixupHelper()
            helper.fix_up_premade_sims()
        else:
            household = household_data.create_household(zone_id, family_name=household_name)
            for sim_info in household.sim_infos():
                sim_info.last_name = household_name
        for sim_info in household:
            Distributor.instance().add_object(sim_info)
        household_commands.move_into_zone(zone_id, household.id, True)
        self._force_list_refresh = True

    def get_extended_species_from_creation_info(self, household_member:'Dict[int, int, SimTemplateType]') -> 'int':
        if not household_member:
            return -1
        if not household_member.sim_template:
            return -1
        sim_info_base = SimInfoBaseWrapper()
        sim_info_base.load_from_resource(household_member.sim_template._sim_creation_info.resource_key)
        return sim_info_base.extended_species

    def get_beds_wanted(self, household_data:'Union[Household, HouseholdTemplate]') -> 'int':
        share_bed_bits = set(RelationshipGlobalTuning.SIGNIFICANT_OTHER_RELATIONSHIP_BITS)
        share_bed_bits.add(RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT)
        share_bed_bits.add(RelationshipGlobalTuning.ENGAGEMENT_RELATIONSHIP_BIT)
        bed_count = 0
        if isinstance(household_data, Household):
            sim_infos_needing_beds = [sim_info for sim_info in household_data if sim_info.is_toddler_or_younger or not sim_info.is_pet]
            while sim_infos_needing_beds:
                sim_info = sim_infos_needing_beds.pop()
                relationship_tracker = sim_info.relationship_tracker
                for target_sim_info in tuple(sim_infos_needing_beds):
                    if relationship_tracker.has_any_bits(target_sim_info.sim_id, share_bed_bits) and sim_info.is_young_adult_or_older and target_sim_info.is_young_adult_or_older:
                        sim_infos_needing_beds.remove(target_sim_info)
                        break
                bed_count += 1
            return bed_count
        if household_data.template_type == SimTemplateType.PREMADE_HOUSEHOLD:
            household_member_data_needing_beds = [data for data in household_data.get_household_members() if data.sim_template.matches_creation_data(age_min=Age.CHILD) and self.get_extended_species_from_creation_info(data) == Species.HUMAN]
        else:
            household_member_data_needing_beds = [data for data in household_data.get_household_members() if data.sim_template.matches_creation_data(age_min=Age.CHILD, species=Species.HUMAN)]
        while household_member_data_needing_beds:
            data = household_member_data_needing_beds.pop()
            for target_data in tuple(household_member_data_needing_beds):
                for relationship_data in household_data.relationship_data_gen(data.household_member_tag, target_data.household_member_tag):
                    if any(bit in share_bed_bits for bit in relationship_data.relationship_bits):
                        household_member_data_needing_beds.remove(target_data)
                        break
                for relationship_data in household_data.relationship_data_gen(target_data.household_member_tag, data.household_member_tag):
                    if not relationship_data.is_spouse:
                        if any(bit in share_bed_bits for bit in relationship_data.relationship_bits):
                            household_member_data_needing_beds.remove(target_data)
                            break
                    household_member_data_needing_beds.remove(target_data)
                    break
            bed_count += 1
        return bed_count

    def generate_household_list(self) -> 'None':
        if self._last_data_update_time == date_and_time.DATE_AND_TIME_ZERO or MultiUnitTuning.TIME_BETWEEN_FILL_VACANCY_DATA_REFRESH() < services.time_service().sim_now - self._last_data_update_time or self._force_list_refresh:
            self._force_list_refresh = False
            self.select_potential_tenant_household_list()

    def select_potential_tenant_household_list(self) -> 'None':
        select_homeless_households = False
        select_premade_templates = False
        homeless_households = []
        available_premade_tenant_households = []
        self._potential_tenant_household_list.clear()
        self._potential_tenant_household_map.clear()
        self._num_tenant_households_map.clear()
        total_weight = 0
        for (star_rating, (lower_bound, upper_bound)) in self.NUMBER_OF_POTENTIAL_HOUSEHOLDS.items():
            self._num_tenant_households_map[star_rating] = random.randint(lower_bound, upper_bound)
        homeless_households_and_scores = services.sim_filter_service().submit_household_filter(self.HOMELESS_HOUSEHOLD_TENANT_FILTER, lambda x, y: x, allow_yielding=False, blacklist_filter=self.BLACKLIST_HOUSEHOLD_FILTER)
        if homeless_households_and_scores is not None:
            for (household, _) in homeless_households_and_scores:
                if not household.hidden:
                    homeless_households.append(household)
        for household_template in self.PREMADE_TENANT_HOUSEHOLD_TEMPLATES:
            if not self._premade_tenant_household_selected[household_template.guid64]:
                available_premade_tenant_households.append(household_template)
        if len(homeless_households) > 0:
            select_homeless_households = True
            total_weight += self.HOMELESS_HOUSEHOLD_WEIGHT
            random.shuffle(homeless_households)
        if len(available_premade_tenant_households) > 0:
            select_premade_templates = True
            total_weight += self.PREMADE_HOUSEHOLD_TEMPLATE_WEIGHT
            random.shuffle(available_premade_tenant_households)
        for index in range(self.MAX_NUMBER_OF_HOUSEHOLDS):
            rand_val = random.random()
            if select_homeless_households and rand_val > self.HOMELESS_HOUSEHOLD_WEIGHT/total_weight or not (select_homeless_households and select_premade_templates):
                self.select_homeless_household(homeless_households)
                if len(homeless_households) == 0:
                    select_homeless_households = False
                    total_weight -= self.HOMELESS_HOUSEHOLD_WEIGHT
            elif select_premade_templates:
                self.select_premade_tenant_household_template(available_premade_tenant_households)
                if len(available_premade_tenant_households) == 0:
                    select_premade_templates = False
                    total_weight -= self.PREMADE_HOUSEHOLD_TEMPLATE_WEIGHT
            elif select_homeless_households or not select_premade_templates:
                self.select_random_tenant_household_template()
        self._last_data_update_time = services.time_service().sim_now

    def build_potential_household_list_msg(self) -> 'PotentialTenantApplicationHouseholds':
        self.generate_household_list()
        msg = protocolbuffers.Business_pb2.PotentialTenantApplicationHouseholds()
        for potential_tenant in self._potential_tenant_household_list:
            with ProtocolBufferRollback(msg.potential_households) as potential_household_msg:
                potential_household_msg.household_name = potential_tenant.household_name
                for household_occupant in potential_tenant.household_occupants:
                    with ProtocolBufferRollback(potential_household_msg.household_occupants) as household_occupants:
                        (household_occupants.occupant_age, household_occupants.occupant_species) = household_occupant
                potential_household_msg.desired_beds = potential_tenant.desired_beds
                for (star_rating, desired_rent_multiplier) in potential_tenant.desired_rent.items():
                    with ProtocolBufferRollback(potential_household_msg.desired_rent) as desired_rent_msg:
                        desired_rent_msg.star_rating = star_rating
                        desired_rent_msg.rent_multiplier = desired_rent_multiplier
                potential_household_msg.household_id = potential_tenant.household_data
                potential_household_msg.household_name_key = potential_tenant.household_name_key
        for (star_rating, num_households) in self._num_tenant_households_map.items():
            with ProtocolBufferRollback(msg.num_households) as num_households_msg:
                num_households_msg.star_rating = star_rating
                num_households_msg.num_households = num_households
        return msg

    @classproperty
    def save_error_code(cls) -> 'persistence_error_types.ErrorCodes':
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_TENANT_APPLICATION_SERVICE

    def save(self, object_list=None, zone_data=None, open_street_data=None, save_slot_data=None) -> 'None':
        super().save(self)
        save_data = save_slot_data.gameplay_data.tenant_applications_data
        save_data.Clear()
        for (template_guid, household_selected) in self._premade_tenant_household_selected.items():
            with ProtocolBufferRollback(save_data.template_selected_map) as template_selected_proto:
                template_selected_proto.template_guid = template_guid
                template_selected_proto.household_selected = household_selected

    def load(self, zone_data=None) -> 'None':
        super().load(self)
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.gameplay_data.HasField('tenant_applications_data'):
            for household_status in save_slot_data_msg.gameplay_data.tenant_applications_data.template_selected_map:
                self._premade_tenant_household_selected[household_status.template_guid] = household_status.household_selected
