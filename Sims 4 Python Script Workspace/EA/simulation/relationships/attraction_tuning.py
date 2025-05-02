from __future__ import annotationsimport servicesimport sims4from event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom event_testing.resolver import DoubleSimResolverfrom interactions.utils.tunable_icon import TunableIconfrom sims4.common import Packfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePackSafeReference, TunableList, Tunable, TunableReferencefrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKINGfrom sims4.log import Loggerif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from event_testing.test_events import TestEvent
    from relationships.relationship_service import RelationshipService
    from sims.sim_info import SimInfo
    from typing import *logger = Logger('Attraction', default_owner='mjuskelis')
class AttractionTuning:
    ATTRACTION_RELATIONSHIP_TRACK = TunablePackSafeReference(description='\n        The unidirectional relationship track that represents how attracted\n        the actor sim is towards the target sim.\n        ', manager=services.get_instance_manager(Types.STATISTIC), class_restrictions=('RelationshipTrack',), export_modes=ExportModes.All)
    UNKNOWN_ICON = TunableIcon(description='\n        The icon to display in the Sim Profile when the active sim\n        does not know the attraction that the target sim feels towards\n        the active sim.\n        ', export_modes=ExportModes.All)
    UNKNOWN_TITLE = TunableLocalizedString(description='\n        The title to use in the Sim Profile when the active sim\n        does not know the attraction that the target sim feels towards\n        the active sim.\n        ', export_modes=ExportModes.All)
    UNKNOWN_DESCRIPTION = TunableLocalizedString(description='\n        The description to use in the Sim Profile when the active sim\n        does not know the attraction that the target sim feels towards\n        the active sim.\n        ', export_modes=ExportModes.All)
    BASE_ATTRACTION_VALUE = Tunable(description='\n        The intial value of attraction from an actor sim towards a target sim when\n        calculating attraction.\n        \n        Turn Ons and Turn Offs add their attraction modifiers to this value to\n        calculate the total attraction.\n        ', tunable_type=float, default=0)
    TRACK_ATTRACTION_TESTS = TunableTestSet(description="\n        If these tests pass for the actor and target,\n        then we will track the actor's attraction\n        towards the target. \n        ")
    LOOT_BEFORE_ATTRACTION_FIRST_ADDED = TunableList(description='\n        Loot actions that are applied right before an attraction track is\n        first added for the actor sim towards the target sim.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))
    LOOT_ON_ATTRACTION_ADDED = TunableList(description='\n        Loot actions that are applied right after an attraction track is\n        first added for the actor sim towards the target sim.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))

class AttractionService(Service):
    ATTRACTION_RECALCULATION_EVENTS = (TestEvent.KnowledgeChanged,)
    ATTRACTION_VALIDATION_EVENTS = (TestEvent.TraitAddEvent, TestEvent.TraitRemoveEvent)
    ATTRACTION_RELBIT_CHANGES = (TestEvent.AddRelationshipBit, TestEvent.RemoveRelationshipBit)
    ALL_EVENTS = ATTRACTION_RECALCULATION_EVENTS + ATTRACTION_VALIDATION_EVENTS + ATTRACTION_RELBIT_CHANGES

    def __init__(self) -> 'None':
        self._attraction_refresh_enabled = True
        self._relationship_service = None

    @classproperty
    def required_packs(self):
        return (Pack.EP16,)

    def start(self) -> 'None':
        self._relationship_service = services.relationship_service()

    def on_zone_load(self) -> 'None':
        services.get_event_manager().register(self, self.ALL_EVENTS)

    def on_zone_unload(self) -> 'None':
        services.get_event_manager().unregister(self, self.ALL_EVENTS)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        if event in self.ATTRACTION_RECALCULATION_EVENTS:
            actor_sim_id = resolver.get_resolved_arg('actor_sim_id')
            target_sim_id = resolver.get_resolved_arg('target_sim_id')
            self.refresh_attraction(actor_sim_id, target_sim_id)
        if event in self.ATTRACTION_VALIDATION_EVENTS:
            sim_id = sim_info.sim_id
            self._remove_invalid_attraction_for_sim(sim_id)
        if event in self.ATTRACTION_RELBIT_CHANGES:
            relbit = resolver.get_resolved_arg('relationship_bit')
            if relbit.triggered_track != AttractionTuning.ATTRACTION_RELATIONSHIP_TRACK:
                sim_id = resolver.get_resolved_arg('sim_id')
                self._remove_invalid_attraction_for_sim(sim_id)

    def _set_attraction_refresh_enabled(self, enabled:'bool') -> 'None':
        self._attraction_refresh_enabled = enabled

    def refresh_attraction(self, actor_sim_id:'int', target_sim_id:'int') -> 'None':
        if self._attraction_refresh_enabled and self._relationship_service is None:
            return
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        if actor_sim_info is None or target_sim_info is None:
            return
        resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        should_have_track = AttractionTuning.TRACK_ATTRACTION_TESTS.run_tests(resolver)
        has_track = self._relationship_service.has_relationship_track(actor_sim_id, target_sim_id, AttractionTuning.ATTRACTION_RELATIONSHIP_TRACK)
        if not should_have_track:
            self._relationship_service.remove_relationship_track(actor_sim_id, target_sim_id, AttractionTuning.ATTRACTION_RELATIONSHIP_TRACK)
            return
        if has_track or should_have_track:
            for loot in AttractionTuning.LOOT_BEFORE_ATTRACTION_FIRST_ADDED:
                loot.apply_to_resolver(resolver)
            self._update_attraction_value(actor_sim_id, target_sim_id)
            for loot in AttractionTuning.LOOT_ON_ATTRACTION_ADDED:
                loot.apply_to_resolver(resolver)
        else:
            self._update_attraction_value(actor_sim_id, target_sim_id)

    def _update_attraction_value(self, actor_sim_id:'int', target_sim_id:'int') -> 'None':
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        if actor_sim_info is None or target_sim_info is None:
            return
        resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        attraction_value = AttractionTuning.BASE_ATTRACTION_VALUE
        actor_traits = set(filter(lambda trait: trait.is_attraction_trait, actor_sim_info.trait_tracker))
        for trait in actor_traits:
            attraction_value += trait.attraction_modifier.get_modified_value(resolver)
        self._relationship_service.set_relationship_score(actor_sim_id, target_sim_id, attraction_value, AttractionTuning.ATTRACTION_RELATIONSHIP_TRACK)

    def _remove_invalid_attraction_for_sim(self, sim_id:'int') -> 'None':
        if self._relationship_service is None:
            return
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(sim_id)
        for relationship in self._relationship_service.get_all_sim_relationships(sim_id):
            target_sim_id = relationship.get_other_sim_id(sim_id)
            resolver = DoubleSimResolver(actor_sim_info, sim_info_manager.get(target_sim_id))
            if relationship.has_track(sim_id, AttractionTuning.ATTRACTION_RELATIONSHIP_TRACK) and not AttractionTuning.TRACK_ATTRACTION_TESTS.run_tests(resolver):
                relationship.remove_track(sim_id, target_sim_id, AttractionTuning.ATTRACTION_RELATIONSHIP_TRACK)
