from filters.tunable import TunableSimFilterfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import AutoFactoryInit, TunableLotDescription, TunableVariant, HasTunableSingletonFactory, TunableReference, TunableList, TunableTuple, Tunable, TunableRange, TunableHouseDescription, OptionalTunableimport build_buyimport servicesimport sims4.logimport sims4.resourcesfrom world import get_lot_id_from_instance_idlogger = sims4.log.Logger('CareerEventZone')
class RequiredCareerEventZoneTunableVariant(TunableVariant):
    __slots__ = ()

    def __init__(self, **kwargs):
        super().__init__(any=RequiredCareerEventZoneAny.TunableFactory(), home_zone=RequiredCareerEventZoneHome.TunableFactory(), lot_description=RequiredCareerEventZoneLotDescription.TunableFactory(), random_lot=RequiredCareerEventZoneRandom.TunableFactory(), career_customer_lot=RequiredCareerEventZoneCustomerLot.TunableFactory(), default='any', **kwargs)

class RequiredCareerEventZone(HasTunableSingletonFactory, AutoFactoryInit):

    def get_required_zone_id(self, sim_info):
        raise NotImplementedError

    def is_zone_id_valid(self, zone_id):
        return self.get_required_zone_id() == zone_id

class RequiredCareerEventZoneAny(RequiredCareerEventZone):

    def get_required_zone_id(self, sim_info):
        pass

    def is_zone_id_valid(self, zone_id):
        return True

class RequiredCareerEventZoneHome(RequiredCareerEventZone):

    def get_required_zone_id(self, sim_info):
        return sim_info.household.home_zone_id

class RequiredCareerEventZoneLotDescription(RequiredCareerEventZone):
    FACTORY_TUNABLES = {'lot_description': TunableLotDescription(description='\n            Lot description of required zone.\n            '), 'house_description': OptionalTunable(description='\n            If tuned, this house description will be used for this career event.\n            For example, for the acting career loads into the same lot but different\n            houses (studio sets). \n            ', tunable=TunableHouseDescription(description='\n                House description used for this career event.\n                '))}

    def get_required_zone_id(self, sim_info):
        lot_id = get_lot_id_from_instance_id(self.lot_description)
        if self.house_description is not None:
            for zone_proto in services.get_persistence_service().zone_proto_buffs_gen():
                if zone_proto.lot_description_id == self.lot_description:
                    zone_proto.pending_house_desc_id = self.house_description
                    break
        zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        return zone_id

class RequiredCareerEventZoneCustomerLot(RequiredCareerEventZone):
    FACTORY_TUNABLES = {'career': TunableReference(description="\n            The career used to look up the client's lot.\n            ", manager=services.get_instance_manager(sims4.resources.Types.CAREER))}

    def get_required_zone_id(self, sim_info):
        career = sim_info.careers.get(self.career.guid64, None)
        if career is None:
            logger.error("Trying to get the Customer's Lot but the Sim ({}) doesn't have the Career ({}).", sim_info, self.career)
            return 0
        else:
            customer_lot_id = career.get_customer_lot_id()
            if not customer_lot_id:
                logger.error("Trying to get the Customer's Lot but the Career ({}) doesn't have a Customer Lot ID. Sim {}", self.career, sim_info)
                return 0
        return customer_lot_id

class ZoneTestNpc(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        household = services.household_manager().get(zone_proto.household_id)
        return household is not None and not household.is_player_household

class ZoneTestActivePlayer(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return zone_proto.household_id == services.active_household_id()

class ZoneTestOwnedByHousehold(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return zone_proto.household_id != 0

class ZoneTestActiveZone(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return zone_proto.zone_id == services.current_zone_id()

class ZoneTestIsPlex(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return services.get_plex_service().is_zone_a_plex(zone_proto.zone_id)

class ZoneTestVenueType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'venues': TunableList(description='\n            If the venue is in this list, the test passes.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True))}

    def is_valid_zone(self, zone_proto):
        venue_tuning_id = build_buy.get_current_venue(zone_proto.zone_id)
        return venue_tuning_id in (venue.guid64 for venue in self.venues)

class ZoneTestHasModifier(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'blacklist_zone_modifiers': TunableList(description='\n            A zone cannot have the selected number of modifiers to pass this test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), class_restrictions=('ZoneModifier',), pack_safe=True)), 'whitelist_zone_modifiers': TunableList(description='\n            A zone must have the selected number of these modifiers to pass this test..\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), class_restrictions=('ZoneModifier',), pack_safe=True)), 'num_whitelist_required': Tunable(description='\n            The number of whitelist modifiers that the zone is required to\n            have in order to pass this test.\n            ', tunable_type=int, default=1), 'num_blacklist_allowed': Tunable(description='\n            The threshold of blacklist modifiers owned by the zone that\n            will trigger a test failure.\n            ', tunable_type=int, default=0)}

    def is_valid_zone(self, zone_proto) -> bool:
        zone_modifier_service = services.get_zone_modifier_service()
        target_zone_modifiers = zone_modifier_service.get_zone_modifiers(zone_proto.zone_id)
        mod_count = 0
        if self.whitelist_zone_modifiers:
            for modifier in self.whitelist_zone_modifiers:
                if modifier in target_zone_modifiers:
                    mod_count += 1
                    if mod_count >= self.num_whitelist_required:
                        return True
        mod_count = 0
        if self.blacklist_zone_modifiers:
            for modifier in self.blacklist_zone_modifiers:
                if modifier in target_zone_modifiers:
                    mod_count += 1
                    if mod_count > self.num_blacklist_allowed:
                        return False
        return True

class RequiredCareerEventZoneRandom(RequiredCareerEventZone):
    FORBIDDEN = 'FORBIDDEN'
    FACTORY_TUNABLES = {'random_weight_terms': TunableList(description='\n            A list of tests to use and the weights to add for each test.\n            By default, zones start with a weight of 1.0 and this can be\n            increased through these tests.\n            ', tunable=TunableTuple(test=TunableVariant(belongs_to_active_player=ZoneTestActivePlayer.TunableFactory(), is_owned_by_any_household=ZoneTestOwnedByHousehold.TunableFactory(), is_npc_household=ZoneTestNpc.TunableFactory(), venue_type=ZoneTestVenueType.TunableFactory(), is_active_zone=ZoneTestActiveZone.TunableFactory(), is_plex=ZoneTestIsPlex.TunableFactory(), has_zone_modifiers=ZoneTestHasModifier.TunableFactory(), default='venue_type'), weight=TunableVariant(add_weight=TunableRange(description='\n                        The amount of extra weight to add to the probability of zones\n                        that pass this test.\n                        ', tunable_type=float, default=1.0, minimum=0.0), locked_args={'forbid': FORBIDDEN}, default='add_weight'), negate=Tunable(description='\n                    If checked, extra weight will be applied to zones that do NOT\n                    pass this test, instead of zones that do pass.\n                    ', tunable_type=bool, default=False))), 'household_weighting': OptionalTunable(description='\n            If enabled, and a household lives in the zone, calculated weight will be multiplied by the 0-1 score\n            returned by a household sim filter tested against the household.\n            ', tunable=TunableTuple(primary_filter=TunableReference(description='\n                    Filter used to determine the base score of the household using the sim that scores the highest.  If\n                    Highest score is 0, then the weight modifier will be 0, and zone will be ineligible.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',)), blacklist_filter=TunableReference(description='\n                    Specifies the blacklist filter for the household filter.  Uses 1- score of highest scoring sim in\n                    household using this filter to modify the calculated base score.  If highest score is 1, then the\n                    weight modifier will be 0 and zone will be ineligible.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',), allow_none=True)))}

    def _get_random_weight(self, zone_proto):
        weight = 1.0
        for random_weight_term in self.random_weight_terms:
            if random_weight_term.negate ^ random_weight_term.test.is_valid_zone(zone_proto):
                if random_weight_term.weight == self.FORBIDDEN:
                    return 0.0
                weight += random_weight_term.weight
        if zone_proto.household_id:
            household = services.household_manager().get(zone_proto.household_id)
            if household is not None:
                households_and_scores = services.sim_filter_service().submit_household_filter(self.household_weighting.primary_filter, None, blacklist_filter=self.household_weighting.blacklist_filter, household_constraints=[zone_proto.household_id], allow_yielding=False)
                if not households_and_scores:
                    return 0.0
                weight *= households_and_scores[0][1]
        return weight

    def get_required_zone_id(self, sim_info):
        zone_ids = [(self._get_random_weight(zone_proto), zone_proto.zone_id) for zone_proto in services.get_persistence_service().zone_proto_buffs_gen()]
        zone_reservation_service = services.get_zone_reservation_service()
        zone_ids = [(x, zone_id) for (x, zone_id) in zone_ids if not zone_reservation_service.is_reserved(zone_id)]
        zone_id = weighted_random_item(zone_ids)
        if zone_id is None:
            logger.warn('Failed to find any zones that were not forbidden for career event travel with terms: {}', self.random_weight_terms, owner='bhill')
            return
        return zone_id
