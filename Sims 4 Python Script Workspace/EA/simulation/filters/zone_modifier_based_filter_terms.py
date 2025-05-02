from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from filters.tunable import BaseFilterTerm, Listimport sims4from filters.tunable import FilterTermVariant, BaseFilterTermfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableList, OptionalTunable, TunableMapping, TunableReferencefrom snippets import define_snippetimport services
class ZoneModifierBasedFilterTerms(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'default_filter_terms': OptionalTunable(description='\n            Default filter terms to use if none of the specified ZoneModifiers is active.\n            ', tunable=TunableList(tunable=FilterTermVariant()), disabled_value=()), 'zone_modifier_to_filter_terms': TunableMapping(description='\n            A mapping of zone modifier to filter terms.\n            If more than one of these zone modifiers is active, the filters are applied additively. \n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), pack_safe=True), value_type=TunableList(tunable=FilterTermVariant()))}

    def get_filter_terms(self) -> 'List[BaseFilterTerm]':
        zone_modifier_service = services.get_zone_modifier_service()
        zone_modifiers = zone_modifier_service.get_zone_modifiers(services.current_zone_id())
        filter_terms = ()
        for zone_modifier in zone_modifiers:
            if zone_modifier in self.zone_modifier_to_filter_terms:
                filter_terms += self.zone_modifier_to_filter_terms[zone_modifier]
        if filter_terms:
            return filter_terms
        return self.default_filter_terms
(_, TunableZoneModifierBasedFilterTermsSnippet) = define_snippet('zone_modifier_based_filter_terms', ZoneModifierBasedFilterTerms.TunableFactory())