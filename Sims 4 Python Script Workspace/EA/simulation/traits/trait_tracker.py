from __future__ import annotationsimport itertoolsimport collectionsfrom distributor.ops import TraitAppearanceUpdatefrom distributor.shared_messages import build_icon_info_msgfrom distributor.system import Distributorfrom interactions.utils.tunable_icon import TunableIconFactoryfrom sims.global_gender_preference_tuning import GlobalGenderPreferenceTuningfrom collections import defaultdictimport mtximport operatorimport randomfrom protocolbuffers import Commodities_pb2from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom crafting.crafting_tunable import CraftingTuningfrom crafting.food_restrictions_utils import FoodRestrictionUtilsfrom cas.cas_preference_item import ObjectPreferenceItemfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypeSimfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.tunable import TunableContinuationfrom objects import ALL_HIDDEN_REASONSfrom objects.mixins import AffordanceCacheMixin, ProvidedAffordanceDatafrom sims.relationship_expectations_tuning import RelationshipExpectationsTuningfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.sim_info_types import Gender, Species, SpeciesExtendedfrom sims.sim_info_utils import apply_super_affordance_commodity_flags, remove_super_affordance_commodity_flagsfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactory, TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableMapping, TunableEnumEntry, TunableList, TunableTuple, TunableSet, OptionalTunable, TunableReference, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classpropertyfrom statistics.commodity_messages import send_sim_commodity_list_update_messagefrom tag import Tagfrom traits.gameplay_object_preference_tracker_mixin import GameplayObjectPreferenceTrackerMixinfrom traits.preference_enums import PreferenceSubjectfrom traits.preference_tracker_mixin import PreferenceTrackerMixinfrom traits.preference_tuning import PreferenceTuningfrom traits.preference_utils import preferences_genfrom traits.trait_day_night_tracking import DayNightTrackingStatefrom traits.trait_quirks import add_quirksfrom traits.traits import logger, Trait, TraitAppearanceOverrideTuplefrom traits.trait_type import TraitTypefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom ui.ui_dialog_picker import ObjectPickerRow, UiObjectPickerfrom vfx.vfx_mask import generate_mask_messageimport game_servicesimport servicesimport sims.ghostimport sims4.telemetryimport telemetry_helperfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.occult.occult_enums import OccultType
    from sims.sim_info import SimInfo
    from sims.sim_info_types import Age
    from statistics.commodity import CommodityTELEMETRY_GROUP_TRAITS = 'TRAT'TELEMETRY_HOOK_ADD_TRAIT = 'TADD'TELEMETRY_HOOK_REMOVE_TRAIT = 'TRMV'TELEMETRY_FIELD_TRAIT_ID = 'idtr'TELEMETRY_FIELD_TRAIT_TYPE = 'ttyp'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_TRAITS)
class HasTraitTrackerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def trait_tracker(self):
        return self._trait_tracker

    def add_trait(self, *args, **kwargs):
        return self._trait_tracker._add_trait(*args, **kwargs)

    def get_traits(self):
        return self._trait_tracker.equipped_traits

    def has_trait(self, *args, **kwargs):
        return self._trait_tracker.has_trait(*args, **kwargs)

    def has_any_trait(self, *args, **kwargs):
        return self._trait_tracker.has_any_trait(*args, **kwargs)

    def remove_trait(self, *args, **kwargs):
        return self._trait_tracker._remove_trait(*args, **kwargs)

    def apply_reincarnation_carry_over_traits(self, new_sim_info:'SimInfo') -> 'None':
        for trait in self._trait_tracker.equipped_traits:
            if trait.reincarnation_carry_over_traits:
                for reincarnation_carry_over_traits in trait.reincarnation_carry_over_traits:
                    new_sim_info.add_trait(reincarnation_carry_over_traits)

    def get_separate_initial_commodity_sets(self) -> 'Tuple[Set[Commodity], Set[Commodity]]':
        initial_commodities = set()
        other_commodities = set()
        blacklisted_commodities = set()
        conditional_commodities = self._trait_tracker.conditional_commodities
        for trait in self._trait_tracker:
            initial_commodities.update(trait.initial_commodities)
            blacklisted_commodities.update(trait.initial_commodities_blacklist)
            other_commodities.update(trait.initial_non_motive_commodities)
            if conditional_commodities and trait in conditional_commodities:
                initial_commodities.update(conditional_commodities[trait])
        initial_commodities -= blacklisted_commodities
        other_commodities -= blacklisted_commodities
        return (frozenset(initial_commodities), frozenset(other_commodities))

    def get_initial_commodities(self) -> 'Set[Commodity]':
        (initial_commodities, other_commodities) = self.get_separate_initial_commodity_sets()
        return initial_commodities | other_commodities

    def on_all_traits_loaded(self):
        pass

    def _get_trait_ids(self):
        return self._trait_tracker.trait_ids

class TraitTracker(AffordanceCacheMixin, PreferenceTrackerMixin, GameplayObjectPreferenceTrackerMixin, SimInfoTracker):

    @staticmethod
    def _verify_exclusive_sets(instance_class, tunable_name, source, value, **kwargs):
        all_traits_in_sets = set()
        for exclusive_set in value:
            for entry in exclusive_set:
                all_traits_in_sets.add(entry.trait)
        for trait in all_traits_in_sets:
            sets = TraitTracker._get_exclusivity_sets(trait, exclusive_sets=value)
            duplicated_sets = [item for (item, count) in collections.Counter(sets).items() if count > 1]
            for duplicated_set in duplicated_sets:
                logger.error(f'Trait {trait} found multiple times in set index {value.index(duplicated_set)}!')
            higher_traits = TraitTracker._get_exclusive_traits_by_comparison(trait, lambda us, them: us < them, value)
            equal_traits = TraitTracker._get_exclusive_traits_by_comparison(trait, lambda us, them: us == them, value)
            lower_traits = TraitTracker._get_exclusive_traits_by_comparison(trait, lambda us, them: us > them, value)
            higher_equal = set(higher_traits.intersection(equal_traits))
            lower_equal = set(lower_traits.intersection(equal_traits))
            higher_lower = set(higher_traits.intersection(lower_traits))
            for invalid_trait in higher_equal:
                logger.error(f'Trait {invalid_trait} is both higher ranked and equally ranked to trait {trait}; this is invalid!')
            for invalid_trait in lower_equal:
                logger.error(f'Trait {invalid_trait} is both lower ranked and equally ranked to trait {trait}; this is invalid!')
            for invalid_trait in higher_lower:
                logger.error(f'Trait {invalid_trait} is both higher ranked and lower ranked than trait {trait}; this is invalid!')

    GENDER_TRAITS = TunableMapping(description='\n        A mapping from gender to trait. Any Sim with the specified gender will\n        have the corresponding gender trait.\n        ', key_type=TunableEnumEntry(description="\n            The Sim's gender.\n            ", tunable_type=Gender, default=Gender.MALE), value_type=TunableReference(description='\n            The trait associated with the specified gender.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',)))
    DEFAULT_GENDER_OPTION_TRAITS = TunableMapping(description="\n        A mapping from gender to default gender option traits. After loading the\n        sim's trait tracker, if no gender option traits are found (e.g. loading\n        a save created prior to them being added), the tuned gender option traits\n        for the sim's gender will be added.\n        ", key_type=TunableEnumEntry(description="\n            The Sim's gender.\n            ", tunable_type=Gender, default=Gender.MALE), value_type=TunableSet(description='\n            The default gender option traits to be added for this gender.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True)))
    SPECIES_TRAITS = TunableMapping(description='\n        A mapping from species to trait. Any Sim of the specified species will\n        have the corresponding species trait.\n        ', key_type=TunableEnumEntry(description="\n            The Sim's species.\n            ", tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunableReference(description='\n            The trait associated with the specified species.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True))
    SPECIES_EXTENDED_TRAITS = TunableMapping(description='\n        A mapping from extended species to trait. Any Sim of the specified \n        extended species will have the corresponding extended species trait.\n        ', key_type=TunableEnumEntry(description="\n            The Sim's extended species.\n            ", tunable_type=SpeciesExtended, default=SpeciesExtended.SMALLDOG, invalid_enums=(SpeciesExtended.INVALID,)), value_type=TunableReference(description='\n            The trait associated with the specified extended species.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True))
    TRAIT_INHERITANCE = TunableList(description='\n        Define how specific traits are transferred to offspring. Define keys of\n        sets of traits resulting in the assignment of another trait, weighted\n        against other likely outcomes.\n        ', tunable=TunableTuple(description='\n            A set of trait requirements and outcomes. Please note that inverted\n            requirements are not necessary. The game will automatically swap\n            parents A and B to try to fulfill the constraints.\n            \n            e.g. Alien Inheritance\n                Alien inheritance follows a simple set of rules:\n                 Alien+Alien always generates aliens\n                 Alien+None always generates part aliens\n                 Alien+PartAlien generates either aliens or part aliens\n                 PartAlien+PartAlien generates either aliens, part aliens, or regular Sims\n                 PartAlien+None generates either part aliens or regular Sims\n                 \n                Given the specifications involving "None", we need to probably\n                blacklist the two traits to detect a case where only one of the\n                two parents has a meaningful trait:\n                \n                a_whitelist = Alien\n                b_whitelist = Alien\n                outcome = Alien\n                \n                a_whitelist = Alien\n                b_blacklist = Alien,PartAlien\n                outcome = PartAlien\n                \n                etc...\n            ', parent_a_whitelist=TunableList(description='\n                One of the parents must have ALL the traits specified in the Parent A Whitelist\n                and none of the traits in the Parent A Blacklist.\n                ', tunable=TunablePackSafeReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',)), allow_none=True), parent_a_blacklist=TunableList(description='\n                One of the parents must have ALL the traits specified in the Parent A Whitelist\n                and none of the traits in the Parent A Blacklist.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True)), parent_b_whitelist=TunableList(description='\n                If either Parent A field has traits specified then the other parent must have\n                all the traits specified in the Parent B Whitelist and none of the traits specified\n                in the Parent B Blacklist. If both parents match the Parent A requirements \n                (which would always be true if both Parent A fields are empty), then this passes \n                if either of the parents match the Parent B requirements.\n                ', tunable=TunablePackSafeReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',)), allow_none=True), parent_b_blacklist=TunableList(description='\n                If either Parent A field has traits specified then the other parent must have\n                all the traits specified in the Parent B Whitelist and none of the traits specified\n                in the Parent B Blacklist. If both parents match the Parent A requirements \n                (which would always be true if both Parent A fields are empty), then this passes \n                if either of the parents match the Parent B requirements.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True)), outcomes=TunableList(description='\n                A weighted list of potential outcomes given that the\n                requirements have been satisfied.\n                ', tunable=TunableTuple(description='\n                    A weighted outcome. The weight is relative to other entries\n                    within this outcome set.\n                    ', weight=Tunable(description='\n                        The relative weight of this outcome versus other\n                        outcomes in this same set.\n                        ', tunable_type=float, default=1), trait=TunableReference(description='\n                        The potential inherited trait.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), allow_none=True, pack_safe=True)))))
    KNOWLEDGE_TRAIT_TYPES = TunableSet(description='\n        Sims are allowed to get knowledge about traits of these types.\n        ', tunable=TraitType)
    EXCLUSIVE_SET = TunableList(description='\n        A list of trait groups to determine which traits are exclusive from each\n        other within the same group. We will prevent a trait from being added if\n        a trait with a higher weight excludes it. We will remove traits with a\n        lower or equal weight when we add a new trait.\n        \n        For example:\n            Group 1 has:\n                Trait A, Weight 3\n                Trait B, Weight 2\n                Trait C, Weight 1\n            Group 2 has:\n                Trait B, Weight 3\n                Trait D, Weight 1\n                Trait E, Weight 1\n        \n        If our sim has Trait A and tries to add:\n            Trait B will not be added.\n            Trait C will not be added.\n            Trait D will be added.\n            Trait E will be added.\n        If our sim has Trait B and tries to add:\n            Trait A will remove Trait B and add Trait A.\n            Trait C will not be added.\n            Trait D will not be added.\n            Trait E will not be added.\n        If our sim has Trait C and tries to add:\n            Trait A will remove Trait C and add Trait A.\n            Trait B will remove Trait C and add Trait B.\n            Trait D will be added.\n            Trait E will be added.\n        If our sim has Trait D and tries to add:\n            Trait A will be added.\n            Trait B will remove Trait D and add Trait B.\n            Trait C will be added.\n            Trait E will remove Trait D and add Trait E.\n        If our sim has Trait E and tries to add:\n            Trait A will be added.\n            Trait B will remove Trait E and add Trait B.\n            Trait C will be added.\n            Trait D will remove Trait E and add Trait D.\n        ', tunable=TunableList(tunable=TunableTuple(trait=TunableReference(description='\n                    A trait in the exclusive group.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), weight=Tunable(description='\n                    The weight to determine if this trait should be added and remove\n                    other traits in the exclusive group, or not add this trait at all.\n                    ', tunable_type=int, default=1)), minlength=1), verify_tunable_callback=_verify_exclusive_sets)

    def __init__(self, sim_info):
        super().__init__()
        self._sim_info = sim_info
        self._sim_info.on_base_characteristic_changed.append(self.add_auto_traits)
        self._disabled_trait_types = set()
        self._equipped_traits = set()
        self._unlocked_equip_slot = 0
        self._buff_handles = {}
        self._always_on_buff_handles = {}
        self.trait_vfx_mask = 0
        self.trait_exclude_vfx_mask = 0
        self._hiding_relationships = False
        self._day_night_state = None
        self._test_events = None
        self._load_in_progress = False
        self._delayed_active_lod_traits = None
        self._conditional_commodities = {}
        self._equipped_personality_traits = list()
        self._ungranted_traits = list()

    def __iter__(self):
        return self._equipped_traits.__iter__()

    def __len__(self):
        return len(self._equipped_traits)

    def can_add_trait(self, trait:'Trait', skip_personality_trait_count_check:'bool'=False) -> 'bool':
        if not self._has_valid_lod(trait):
            logger.info('Trying to equip a trait {} for Sim {} without meeting the min lod (sim: {} < trait: {})', trait, self._sim_info, self._sim_info.lod, trait.min_lod_value)
            return False
        if self.has_trait(trait):
            logger.info('Trying to equip an existing trait {} for Sim {}', trait, self._sim_info)
            return False
        if skip_personality_trait_count_check or trait.is_personality_trait and self.available_personality_trait_count == 0:
            logger.info('Reach max trait number {} for Sim {}', self.available_personality_trait_count, self._sim_info)
            return False
        if trait.is_preference_trait and self._preference_group_at_capacity(trait):
            logger.info('Reached max preferences for group {} for Sim {}', PreferenceTuning.try_get_preference_group_for_trait(trait), self._sim_info)
            return False
        if not trait.is_valid_trait(self._sim_info):
            logger.info("Trying to equip a trait {} that conflicts with Sim {}'s age {} or gender {}", trait, self._sim_info, self._sim_info.age, self._sim_info.gender)
            return False
        if self.is_conflicting(trait):
            logger.info('Trying to equip a conflicting trait {} for Sim {}', trait, self._sim_info)
            return False
        if trait.trait_type == TraitType.LIFESTYLE and not services.lifestyle_service().lifestyles_enabled:
            logger.info('Trying to equip a lifestyle trait {} for Sim {} without lifestyles enabled', trait, self._sim_info)
            return False
        if trait.entitlement is not None and not mtx.has_entitlement(trait.entitlement):
            logger.info('Trying to equip a trait {} for Sim {} without proper entitlement', trait, self._sim_info)
            return False
        elif self._is_excluded(trait):
            logger.info('Trying to equip a trait {} for Sim {} which is excluded by a different trait.', trait, self._sim_info)
            return False
        return True

    def add_auto_traits(self):
        for trait in itertools.chain(self.GENDER_TRAITS.values(), self.SPECIES_TRAITS.values(), self.SPECIES_EXTENDED_TRAITS.values()):
            if self.has_trait(trait):
                self._remove_trait(trait)
        auto_traits = (self.GENDER_TRAITS.get(self._sim_info.gender), self.SPECIES_TRAITS.get(self._sim_info.species), self.SPECIES_EXTENDED_TRAITS.get(self._sim_info.extended_species))
        for trait in auto_traits:
            if trait is None:
                pass
            else:
                self._add_trait(trait)

    def remove_invalid_traits(self):
        for trait in tuple(self._equipped_traits):
            if not trait.is_valid_trait(self._sim_info):
                self._sim_info.remove_trait(trait)

    def remove_ungranted_traits(self):
        for trait in self._ungranted_traits:
            self._remove_trait(trait, skip_telemetry=True)

    def sort_and_send_commodity_list(self) -> 'None':
        if not self._sim_info.is_selectable:
            return
        final_list = []
        (commodities, other_commodities) = self._sim_info.get_separate_initial_commodity_sets()
        for trait in self._equipped_traits:
            if not trait.ui_commodity_sort_override:
                pass
            else:
                final_list = [override_commodity for override_commodity in trait.ui_commodity_sort_override if override_commodity in commodities]
                break
        if not final_list:
            final_list = sorted(commodities, key=operator.attrgetter('ui_sort_order'))
        self._send_commodity_list_msg(final_list, other_commodities)

    def _send_commodity_list_msg(self, commodity_list:'List[Commodity]', other_commodities:'Set[Commodity]') -> 'None':
        list_msg = Commodities_pb2.CommodityListUpdate()
        list_msg.sim_id = self._sim_info.sim_id
        commodity_lists = [commodity_list, other_commodities]
        for commodities in commodity_lists:
            if not hasattr(list_msg, 'commodity_lists'):
                break
            with ProtocolBufferRollback(list_msg.commodity_lists) as commodity_list_msg:
                for commodity in commodities:
                    if commodity.visible:
                        stat = self._sim_info.commodity_tracker.get_statistic(commodity)
                        if stat and stat.is_visible_commodity():
                            with ProtocolBufferRollback(commodity_list_msg.commodities) as commodity_msg:
                                stat.populate_commodity_update_msg(commodity_msg, is_rate_change=False)
        send_sim_commodity_list_update_message(self._sim_info, list_msg)

    @property
    def conditional_commodities(self):
        return self._conditional_commodities

    def on_all_households_and_sim_infos_loaded(self):
        self._check_conditional_commodities()

    def _check_conditional_commodities(self):
        previous_initial_commodities = self._sim_info.get_initial_commodities()
        commodities_to_remove = set()
        for (trait, _) in self._conditional_commodities.items():
            if trait.conditional_commodities:
                commodities_to_remove.update(self._update_conditional_commodities_dict(trait, from_load=True, from_delay=True))
        self._update_commodities(previous_initial_commodities, commodities_to_remove)

    def _update_conditional_commodities_dict(self, trait, add=True, from_load=False, from_delay=False):
        if not add:
            if trait in self._conditional_commodities:
                del self._conditional_commodities[trait]
            return set()
        if trait not in self._conditional_commodities:
            self._conditional_commodities[trait] = []
        commodities_to_remove = set()
        for commodity_info in trait.conditional_commodities:
            if from_load and from_delay != commodity_info.delay:
                pass
            elif commodity_info.tests.run_tests(resolver=SingleSimResolver(self._sim_info)):
                self._conditional_commodities[trait].append(commodity_info.commodity)
            elif commodity_info.commodity in self._conditional_commodities[trait]:
                self._conditional_commodities[trait].remove(commodity_info.commodity)
            elif self._sim_info.lod >= commodity_info.commodity.min_lod_value:
                commodities_to_remove.add(commodity_info.commodity)
        return commodities_to_remove

    def _remove_commodities(self, commodities):
        if not commodities:
            return
        should_update_commodity_ui = False
        for commodity in commodities:
            commodity_inst = self._sim_info.commodity_tracker.get_statistic(commodity)
            if commodity_inst is None:
                pass
            else:
                if commodity_inst.is_visible_commodity():
                    should_update_commodity_ui = True
                commodity_inst.core = False
                self._sim_info.commodity_tracker.remove_statistic(commodity)
        if should_update_commodity_ui:
            self.sort_and_send_commodity_list()

    def _add_commodities(self, commodities):
        if not commodities:
            return
        should_update_commodity_ui = False
        for commodity_to_add in commodities:
            commodity_inst = self._sim_info.commodity_tracker.add_statistic(commodity_to_add)
            if commodity_inst is None:
                pass
            else:
                commodity_inst.core = True
                if should_update_commodity_ui or commodity_inst.is_visible_commodity():
                    should_update_commodity_ui = True
        if should_update_commodity_ui:
            self.sort_and_send_commodity_list()

    def _update_commodities(self, previous_initial_commodities, commodities_to_remove=set()):
        current_initial_commodities = self._sim_info.get_initial_commodities()
        commodities_to_remove.update(previous_initial_commodities)
        commodities_to_remove = commodities_to_remove - current_initial_commodities
        self._remove_commodities(commodities_to_remove)
        commodities_to_add = current_initial_commodities - previous_initial_commodities
        self._add_commodities(commodities_to_add)

    def _add_trait(self, trait:'Trait', index_in_personality_list:'Optional[int]'=None, from_delayed_lod:'bool'=False, is_extra_personality_trait:'bool'=False) -> 'bool':
        if not self.can_add_trait(trait, skip_personality_trait_count_check=is_extra_personality_trait):
            return False
        if trait.trait_type in self._disabled_trait_types:
            return False
        owner_sim_info = self._sim_info
        if not self._load_in_progress:
            initial_commodities_modified = trait.modifies_initial_commodities()
            if initial_commodities_modified:
                previous_initial_commodities = owner_sim_info.get_initial_commodities()
        self._equipped_traits.add(trait)
        if trait.is_personality_trait:
            if index_in_personality_list is not None:
                self._equipped_personality_traits.insert(index_in_personality_list, trait)
            else:
                self._equipped_personality_traits.append(trait)
        if self._load_in_progress:
            return True
        if initial_commodities_modified:
            if trait.conditional_commodities:
                commodities_to_remove = self._update_conditional_commodities_dict(trait)
            else:
                commodities_to_remove = set()
            self._update_commodities(previous_initial_commodities, commodities_to_remove)
        self._apply_trait(trait, from_delayed_lod=from_delayed_lod)
        if is_extra_personality_trait:
            owner_sim_info.extra_personality_trait_slot.add(trait.guid64)
        self.refresh_trait_appearances([trait for (trait, _) in self.traits_with_display_overrides_gen(match_trait=trait)])
        return True

    def _apply_trait(self, trait:'Trait', from_delayed_lod:'bool'=False) -> 'None':
        from_load = from_delayed_lod or self._load_in_progress
        owner_sim_info = self._sim_info
        self._fixup_exclusivity(trait)
        try:
            self._add_always_on_buffs(trait)
        except Exception as e:
            logger.exception('Error adding always on buffs while adding trait: {0}. {1}.', trait.__name__, e, owner='nabaker')
        if trait.buffs_add_on_spawn_only and owner_sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            try:
                self._add_buffs(trait)
            except Exception as e:
                logger.exception('Error adding buffs while adding trait: {0}. {1}.', trait.__name__, e, owner='asantos')
        self._add_vfx_mask(trait, send_op=not from_load)
        self._add_day_night_tracking(trait)
        self.update_trait_effects()
        if trait.is_ghost_trait:
            sims.ghost.Ghost.enable_ghost_routing(owner_sim_info)
        if trait.disable_aging:
            owner_sim_info.update_age_callbacks()
        age_transition = owner_sim_info.get_age_transition_data(owner_sim_info.age)
        if trait in age_transition.trait_age_duration_mutliplier.keys():
            owner_sim_info.update_age_callbacks()
        if trait.is_robot_trait and not from_load:
            owner_sim_info.set_days_alive_to_zero()
        sim = owner_sim_info.get_sim_instance()
        provided_affordances = []
        for provided_affordance in trait.target_super_affordances:
            provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
            provided_affordances.append(provided_affordance_data)
        self.add_to_affordance_caches(trait.super_affordances, provided_affordances)
        self.add_to_actor_mixer_cache(trait.actor_mixers)
        self.add_to_provided_mixer_cache(trait.provided_mixers)
        apply_super_affordance_commodity_flags(sim, trait, trait.super_affordances)
        self._hiding_relationships |= trait.hide_relationships
        if sim is not None:
            teleport_style_interaction = trait.get_teleport_style_interaction_to_inject()
            if teleport_style_interaction is not None:
                sim.add_teleport_style_interaction_to_inject(teleport_style_interaction)
        food_restriction_tracker = owner_sim_info.food_restriction_tracker
        if food_restriction_tracker is not None:
            for ingredient in trait.restricted_ingredients:
                food_restriction_tracker.add_food_restriction(ingredient)
        if not from_load:
            if trait.trait_type in self.KNOWLEDGE_TRAIT_TYPES:
                if owner_sim_info.household is not None:
                    for household_sim in owner_sim_info.household:
                        if household_sim is owner_sim_info:
                            pass
                        else:
                            household_sim.relationship_tracker.add_known_trait(trait, owner_sim_info.sim_id)
                else:
                    logger.error("Attempting to add a trait to a Sim that doesn't have a household. This shouldn't happen. Sim={}, trait={}", owner_sim_info, trait)
            owner_sim_info.resend_trait_ids(traits_to_add=[trait.guid64])
            if trait.disable_aging is not None:
                owner_sim_info.resend_age_progress_data()
            if sim is not None:
                with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ADD_TRAIT, sim=sim) as hook:
                    hook.write_int(TELEMETRY_FIELD_TRAIT_ID, trait.guid64)
                    hook.write_string(TELEMETRY_FIELD_TRAIT_TYPE, str(trait.trait_type))
            if trait.always_send_test_event_on_add or sim is not None:
                services.get_event_manager().process_event(test_events.TestEvent.TraitAddEvent, sim_info=owner_sim_info, trait_guid=trait.guid64, trait_type=trait.trait_type, custom_keys=(trait.guid64, trait.trait_type))
            if trait.loot_on_trait_add is not None:
                resolver = SingleSimResolver(owner_sim_info)
                for loot_action in trait.loot_on_trait_add:
                    loot_action.apply_to_resolver(resolver)
            if trait.trait_statistic is not None:
                trait.trait_statistic.on_trait_added(owner_sim_info, trait)
            self._register_trait_events(trait)
            owner_sim_info.relationship_tracker.update_compatibilities()

    def _remove_trait(self, trait:'Trait', skip_telemetry:'bool'=False) -> 'bool':
        if not self.has_trait(trait):
            return False
        owner_sim_info = self._sim_info
        if not self._load_in_progress:
            initial_commodities_modified = trait.modifies_initial_commodities()
            if initial_commodities_modified:
                previous_initial_commodities = owner_sim_info.get_initial_commodities()
        self._equipped_traits.remove(trait)
        if trait.is_personality_trait:
            self._equipped_personality_traits.remove(trait)
        if self._load_in_progress:
            return
        if initial_commodities_modified:
            if trait.conditional_commodities:
                self._update_conditional_commodities_dict(trait, add=False)
            self._update_commodities(previous_initial_commodities)
        self._remove_buffs(trait)
        self._remove_always_on_buffs(trait)
        self._remove_vfx_mask(trait)
        self._remove_day_night_tracking(trait)
        self._remove_build_buy_purchase_tracking(trait)
        self._remove_trait_knowledge(trait)
        self._remove_sexuality_knowledge(trait)
        self._remove_relationship_expectations_knowledge(trait)
        self.update_trait_effects()
        self.update_affordance_caches()
        age_transition = owner_sim_info.get_age_transition_data(owner_sim_info.age)
        if trait.disable_aging or trait in age_transition.trait_age_duration_mutliplier.keys():
            owner_sim_info.update_age_callbacks()
        owner_sim_info.resend_trait_ids(traits_to_remove=[trait.guid64])
        if trait.is_ghost_trait:
            for ghost_only_trait in sims.ghost.Ghost.GHOST_ONLY_TRAITS:
                self._remove_trait(ghost_only_trait)
            owner_sim_info.run_ghost_outfit_fixup()
        if trait.disable_aging is not None:
            owner_sim_info.resend_age_progress_data()
        if not any(t.is_ghost_trait for t in self._equipped_traits):
            sims.ghost.Ghost.remove_ghost_from_sim(owner_sim_info)
        sim = owner_sim_info.get_sim_instance()
        if sim is not None:
            if not skip_telemetry:
                with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_REMOVE_TRAIT, sim=sim) as hook:
                    hook.write_int(TELEMETRY_FIELD_TRAIT_ID, trait.guid64)
                    hook.write_string(TELEMETRY_FIELD_TRAIT_TYPE, str(trait.trait_type))
            services.get_event_manager().process_event(test_events.TestEvent.TraitRemoveEvent, sim_info=owner_sim_info, trait_guid=trait.guid64, trait_type=trait.trait_type, custom_keys=(trait.guid64, trait.trait_type))
            teleport_style_interaction = trait.get_teleport_style_interaction_to_inject()
            if teleport_style_interaction is not None:
                sim.try_remove_teleport_style_interaction_to_inject(teleport_style_interaction)
        remove_super_affordance_commodity_flags(sim, trait)
        self._hiding_relationships = any(trait.hide_relationships for trait in self)
        if trait.trait_statistic is not None:
            trait.trait_statistic.on_trait_removed(owner_sim_info, trait)
        self._unregister_trait_events(trait)
        food_restriction_tracker = owner_sim_info.food_restriction_tracker
        if food_restriction_tracker is not None:
            for ingredient in trait.restricted_ingredients:
                food_restriction_tracker.remove_food_restriction(ingredient)
        owner_sim_info.relationship_tracker.update_compatibilities()
        self.refresh_trait_appearances([trait for (trait, _) in self.traits_with_display_overrides_gen(match_trait=trait)])
        return True

    def disable_traits_of_type(self, trait_type):
        if trait_type in self._disabled_trait_types:
            return
        self._disabled_trait_types.add(trait_type)
        self.remove_traits_of_type(trait_type)

    def enable_traits_of_type(self, trait_type):
        if trait_type not in self._disabled_trait_types:
            return
        self._disabled_trait_types.remove(trait_type)

    def get_traits_of_type(self, trait_type):
        return [t for t in self._equipped_traits if t.trait_type == trait_type]

    def get_traits_with_tags(self, trait_tags:'Set[Tag]'):
        return [t for t in self._equipped_traits if t.has_any_tag(trait_tags)]

    def get_traits_in_preference_group(self, group_id:'int') -> 'List[Trait]':
        traits_in_group = []
        for trait in self._equipped_traits:
            if not trait.is_preference_trait:
                pass
            else:
                possible_group = PreferenceTuning.try_get_preference_group_for_trait(trait)
                if possible_group is None:
                    logger.error('Preference Item {} is not part of any group!', trait.preference_item)
                elif possible_group.guid64 != group_id:
                    pass
                else:
                    traits_in_group.append(trait)
        return traits_in_group

    def _preference_group_at_capacity(self, trait:'Trait') -> 'bool':
        if not trait.is_preference_trait:
            return False
        group = PreferenceTuning.try_get_preference_group_for_trait(trait)
        if group is None:
            return False
        return group.capacity <= len(self.get_traits_in_preference_group(group.guid64))

    def get_object_preferences(self, preference_types):
        return [t for t in self.get_preferences(preference_types) if t.is_object_preference]

    def get_gameplay_object_preferences(self):
        return self.get_traits_of_type(TraitType.GAMEPLAY_OBJECT_PREFERENCE)

    def get_preferences(self, preference_types):
        return [t for t in self._equipped_traits if t.trait_type in preference_types]

    def possible_preferences_gen(self, decorator_only=False):
        for preference in preferences_gen():
            if not decorator_only or not preference.decorator_preference:
                pass
            elif self.can_add_trait(preference):
                yield preference

    def add_gameplay_object_preference(self, trait, preference_type, **kwargs):
        if trait.is_gameplay_object_preference_trait:
            self._gameplay_object_to_preference[trait] = preference_type
            self._object_to_gameplay_object_preference_type[trait.preference_item] = preference_type
            return self._add_trait(trait, **kwargs)
        return False

    def remove_gameplay_object_preference(self, trait, **kwargs):
        if trait in self._gameplay_object_to_preference:
            del self._gameplay_object_to_preference[trait]
            del self._object_to_gameplay_object_preference_type[trait.preference_item]
            return self._remove_trait(trait, **kwargs)
        return False

    def remove_all_gameplay_object_preferences(self):
        self._gameplay_object_to_preference = {}
        self.remove_traits_of_type(TraitType.GAMEPLAY_OBJECT_PREFERENCE)

    def remove_traits_of_type(self, trait_type):
        for trait in list(self._equipped_traits):
            if trait.trait_type == trait_type:
                self._remove_trait(trait)

    def clear_traits(self):
        for trait in list(self._equipped_traits):
            self._remove_trait(trait)

    def clear_personality_traits(self):
        for trait in self.personality_traits:
            self._remove_trait(trait)

    def has_trait(self, trait):
        return trait in self._equipped_traits

    def has_any_trait(self, traits):
        return bool(self._equipped_traits & set(traits))

    def has_characteristic_preferences(self):
        for trait in self._equipped_traits:
            if trait.is_preference_trait and trait.is_preference_subject(PreferenceSubject.CHARACTERISTIC):
                return True
        return False

    def is_conflicting(self, trait):
        if trait is None:
            return False
        if set(trait.conflicting_traits) & self._equipped_traits:
            return True
        for t in self._equipped_traits:
            if trait in t.conflicting_traits:
                return True
        return False

    @staticmethod
    def _get_exclusivity_sets(trait, exclusive_sets=None):
        sets = []
        for exclusive_set in exclusive_sets if exclusive_sets is not None else TraitTracker.EXCLUSIVE_SET:
            for entry in exclusive_set:
                if entry.trait == trait:
                    sets.append(exclusive_set)
        return sets

    @staticmethod
    def _try_get_weight_in_set(trait, exclusivity_set):
        for entry in exclusivity_set:
            if entry.trait == trait:
                return entry.weight

    @staticmethod
    def _get_exclusive_traits_by_comparison(trait, weight_comparison, exclusive_sets=None):
        comparison_traits = set()
        sets = TraitTracker._get_exclusivity_sets(trait, exclusive_sets)
        for exclusive_set in sets:
            self_weight = TraitTracker._try_get_weight_in_set(trait, exclusive_set)
            if self_weight is None:
                logger.error(f'Found trait {trait} in set {exclusive_set} with no weight. Skipping set.')
            else:
                for entry in exclusive_set:
                    trait_entry = entry.trait
                    weight_entry = entry.weight
                    if trait_entry != trait and weight_comparison(self_weight, weight_entry):
                        comparison_traits.add(trait_entry)
        return comparison_traits

    def _is_excluded(self, trait):
        higher_traits = self._get_exclusive_traits_by_comparison(trait, lambda my_weight, their_weight: their_weight > my_weight)
        higher_traits_on_sim = [item for item in higher_traits if self.has_trait(item)]
        return len(higher_traits_on_sim) > 0

    def _fixup_exclusivity(self, trait_to_add):
        lower_or_equal_traits = self._get_exclusive_traits_by_comparison(trait_to_add, lambda my_weight, their_weight: their_weight <= my_weight)
        for trait in lower_or_equal_traits:
            self._remove_trait(trait)

    @staticmethod
    def _get_inherited_traits_internal(traits_a, traits_b, trait_entry):
        if trait_entry.parent_a_whitelist and not all(t in traits_a for t in trait_entry.parent_a_whitelist):
            return False
        if any(t in traits_a for t in trait_entry.parent_a_blacklist):
            return False
        if trait_entry.parent_b_whitelist and not all(t in traits_b for t in trait_entry.parent_b_whitelist):
            return False
        elif any(t in traits_b for t in trait_entry.parent_b_blacklist):
            return False
        return True

    def get_inherited_traits(self, other_sim):
        traits_a = list(self)
        traits_b = list(other_sim.trait_tracker)
        inherited_entries = []
        for trait_entry in TraitTracker.TRAIT_INHERITANCE:
            if not self._get_inherited_traits_internal(traits_a, traits_b, trait_entry):
                if self._get_inherited_traits_internal(traits_b, traits_a, trait_entry):
                    inherited_entries.append(tuple((outcome.weight, outcome.trait) for outcome in trait_entry.outcomes))
            inherited_entries.append(tuple((outcome.weight, outcome.trait) for outcome in trait_entry.outcomes))
        return inherited_entries

    def get_leave_lot_now_interactions(self, must_run=False):
        interactions = set()
        for trait in self:
            if trait.npc_leave_lot_interactions:
                if must_run:
                    interactions.update(trait.npc_leave_lot_interactions.leave_lot_now_must_run_interactions)
                else:
                    interactions.update(trait.npc_leave_lot_interactions.leave_lot_now_interactions)
        return interactions

    @property
    def personality_traits(self):
        return tuple(self._equipped_personality_traits)

    @property
    def gender_option_traits(self):
        return tuple(trait for trait in self if trait.is_gender_option_trait)

    @property
    def aspiration_traits(self):
        return tuple(trait for trait in self if trait.is_aspiration_trait)

    @property
    def trait_ids(self):
        return [t.guid64 for t in self._equipped_traits]

    @property
    def equipped_traits(self):
        return self._equipped_traits

    @property
    def ungranted_traits(self):
        return self._ungranted_traits

    def get_default_trait_asm_params(self, actor_name):
        asm_param_dict = {}
        for trait_asm_param in Trait.default_trait_params:
            asm_param_dict[(trait_asm_param, actor_name)] = False
        return asm_param_dict

    @property
    def equip_slot_number(self):
        age = self._sim_info.age
        slot_number = self._unlocked_equip_slot
        slot_number += self._sim_info.get_aging_data().get_cas_personality_trait_count(age)
        return slot_number

    @property
    def empty_slot_number(self):
        equipped_personality_traits = sum(1 for trait in self if trait.is_personality_trait)
        empty_slot_number = self.equip_slot_number - equipped_personality_traits
        return max(empty_slot_number, 0)

    @property
    def max_personality_trait_count(self):
        age = self._sim_info.age
        return self.equip_slot_number + self._sim_info.get_aging_data().get_discoverable_personality_trait_count(age)

    @property
    def available_personality_trait_count(self) -> 'int':
        equipped_personality_traits = sum(1 for trait in self if self._should_occupy_personality_trait_slot(trait))
        return self.max_personality_trait_count - equipped_personality_traits

    def _should_occupy_personality_trait_slot(self, trait:'Trait') -> 'bool':
        if not trait.is_personality_trait:
            return False
        elif trait.guid64 in self._sim_info.extra_personality_trait_slot:
            return False
        return True

    def _add_buffs(self, trait:'Trait') -> 'None':
        if trait.guid64 in self._buff_handles:
            return
        buff_handles = []
        for buff in trait.buffs:
            buff_handle = self._sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason, remove_on_zone_unload=trait.buffs_add_on_spawn_only)
            if buff_handle is not None:
                buff_handles.append(buff_handle)
        if buff_handles:
            self._buff_handles[trait.guid64] = buff_handles

    def _add_always_on_buffs(self, trait:'Trait') -> 'None':
        if trait.guid64 in self._always_on_buff_handles:
            return
        buff_handles = []
        for buff in trait.always_on_buffs:
            buff_handle = self._sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason, remove_on_zone_unload=False)
            if buff_handle is not None:
                buff_handles.append(buff_handle)
        if buff_handles:
            self._always_on_buff_handles[trait.guid64] = buff_handles

    def _remove_buffs(self, trait:'Trait') -> 'None':
        if trait.guid64 in self._buff_handles:
            for buff_handle in self._buff_handles[trait.guid64]:
                self._sim_info.remove_buff(buff_handle)
            del self._buff_handles[trait.guid64]

    def _remove_always_on_buffs(self, trait:'Trait') -> 'None':
        if trait.guid64 in self._always_on_buff_handles:
            for buff_handle in self._always_on_buff_handles[trait.guid64]:
                self._sim_info.remove_buff(buff_handle)
            del self._always_on_buff_handles[trait.guid64]

    def _add_vfx_mask(self, trait, send_op=False):
        trait_vfx_mask = trait.vfx_mask
        trait_exclude_vfx_mask = trait.exclude_vfx_mask
        if trait_vfx_mask is None and trait_exclude_vfx_mask is None:
            return
        if trait_vfx_mask is not None:
            for mask in trait_vfx_mask:
                self.trait_vfx_mask |= mask
        if trait_exclude_vfx_mask is not None:
            for mask in trait_exclude_vfx_mask:
                self.trait_exclude_vfx_mask |= mask
        if send_op and self._sim_info is services.active_sim_info():
            generate_mask_message(self.trait_vfx_mask, self._sim_info)

    def _remove_vfx_mask(self, trait):
        trait_vfx_mask = trait.vfx_mask
        trait_exclude_vfx_mask = trait.exclude_vfx_mask
        if trait_vfx_mask is None and trait_exclude_vfx_mask is None:
            return
        if trait_vfx_mask is not None:
            for mask in trait_vfx_mask:
                self.trait_vfx_mask ^= mask
        if trait_exclude_vfx_mask is not None:
            for mask in trait_exclude_vfx_mask:
                self.trait_exclude_vfx_mask ^= mask
        if self._sim_info is services.active_sim_info():
            generate_mask_message(self.trait_vfx_mask, self._sim_info)

    def update_trait_effects(self):
        if self._load_in_progress:
            return
        self._update_voice_effect()
        self._update_plumbbob_override()

    def _update_voice_effect(self):
        try:
            voice_effect_request = max((trait.voice_effect for trait in self if trait.voice_effect is not None), key=operator.attrgetter('priority'))
            self._sim_info.voice_effect = voice_effect_request.voice_effect
        except ValueError:
            self._sim_info.voice_effect = None

    def _update_plumbbob_override(self):
        try:
            plumbbob_override_request = max((trait.plumbbob_override for trait in self if trait.plumbbob_override is not None), key=operator.attrgetter('priority'))
            self._sim_info.plumbbob_override = (plumbbob_override_request.active_sim_plumbbob, plumbbob_override_request.active_sim_club_leader_plumbbob)
        except ValueError:
            self._sim_info.plumbbob_override = None

    def _add_default_gender_option_traits(self):
        gender_option_traits = self.DEFAULT_GENDER_OPTION_TRAITS.get(self._sim_info.gender)
        for gender_option_trait in gender_option_traits:
            if not self.has_trait(gender_option_trait):
                self._add_trait(gender_option_trait)

    def fixup_gender_preference_statistics(self):
        for (gender, gender_preference_statistic) in self._sim_info.get_gender_preferences_gen():
            attraction_traits = GlobalGenderPreferenceTuning.ROMANTIC_PREFERENCE_TRAITS_MAPPING[gender]
            if self.has_trait(attraction_traits.is_attracted_trait):
                if not gender_preference_statistic.get_value() >= GlobalGenderPreferenceTuning.GENDER_PREFERENCE_THRESHOLD:
                    gender_preference_statistic.set_value(gender_preference_statistic.max_value)
                    if self.has_trait(attraction_traits.not_attracted_trait) and not gender_preference_statistic.get_value() < GlobalGenderPreferenceTuning.GENDER_PREFERENCE_THRESHOLD:
                        gender_preference_statistic.set_value(gender_preference_statistic.min_value)
            elif self.has_trait(attraction_traits.not_attracted_trait) and not gender_preference_statistic.get_value() < GlobalGenderPreferenceTuning.GENDER_PREFERENCE_THRESHOLD:
                gender_preference_statistic.set_value(gender_preference_statistic.min_value)

    def on_sim_startup(self):
        sim = self._sim_info.get_sim_instance()
        for trait in tuple(self):
            if trait in self:
                if trait.buffs_add_on_spawn_only:
                    self._add_buffs(trait)
                apply_super_affordance_commodity_flags(sim, trait, trait.super_affordances)
                teleport_style_interaction = trait.get_teleport_style_interaction_to_inject()
                if teleport_style_interaction is not None:
                    sim.add_teleport_style_interaction_to_inject(teleport_style_interaction)
                    logger.error('Trait:{} was removed during startup', trait)
            else:
                logger.error('Trait:{} was removed during startup', trait)
        if any(trait.is_ghost_trait for trait in self):
            sims.ghost.Ghost.enable_ghost_routing(self._sim_info)

    def on_zone_unload(self):
        if self._test_events is not None:
            self._test_events.clear()
            self._test_events = None
        if game_services.service_manager.is_traveling:
            for trait in tuple(self):
                if not trait.buffs_add_on_spawn_only:
                    self._remove_buffs(trait)
                if not (trait in self and trait.persistable):
                    self._remove_trait(trait)

    def on_zone_load(self):
        if game_services.service_manager.is_traveling:
            for trait in tuple(self):
                if trait in self and not trait.buffs_add_on_spawn_only:
                    self._add_buffs(trait)

    def on_sim_removed(self):
        for trait in tuple(self):
            if trait.buffs_add_on_spawn_only:
                self._remove_buffs(trait)
            if not trait.persistable:
                self._remove_trait(trait)

    def save(self):
        data = protocols.PersistableTraitTracker()
        trait_ids = [trait.guid64 for trait in self._equipped_traits if trait.persistable and not trait.is_personality_trait]
        personality_trait_ids = [trait.guid64 for trait in self._equipped_personality_traits if trait.persistable]
        trait_ids.extend(personality_trait_ids)
        if self._delayed_active_lod_traits is not None:
            trait_ids.extend(trait.guid64 for trait in self._delayed_active_lod_traits)
        data.trait_ids.extend(trait_ids)
        self.save_gameplay_object_preferences(data)
        return data

    def set_load_in_progress(self, value):
        if value:
            if self._equipped_traits:
                logger.error(' Loading trait tracker with traits already equipped: {}', self._equipped_traits)
            self._load_in_progress = value
            return
        try:
            commodities_to_remove = set()
            for trait in self._equipped_traits:
                if trait.conditional_commodities:
                    commodities_to_remove.update(self._update_conditional_commodities_dict(trait, from_load=True))
            self._update_commodities(set(), commodities_to_remove)
            for trait in self._equipped_traits:
                self._apply_trait(trait)
        finally:
            self._load_in_progress = value

    def load(self, data, skip_load):
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        self._sim_info._update_age_trait(self._sim_info.age)
        premade_sim_needing_fixup = not self._sim_info.premade_sim_fixup_completed
        for trait_instance_id in data.trait_ids:
            trait = trait_manager.get(trait_instance_id)
            if not services.is_granted_or_non_account_reward_item(trait.guid64):
                self._ungranted_traits.append(trait)
            if not self._has_valid_lod(trait):
                if trait.min_lod_value == SimInfoLODLevel.ACTIVE:
                    if self._delayed_active_lod_traits is None:
                        self._delayed_active_lod_traits = list()
                    self._delayed_active_lod_traits.append(trait)
                    if skip_load and not (premade_sim_needing_fixup or trait.allow_from_gallery):
                        pass
                    else:
                        self._sim_info.add_trait(trait, from_load=True)
            elif skip_load and not (premade_sim_needing_fixup or trait.allow_from_gallery):
                pass
            else:
                self._sim_info.add_trait(trait, from_load=True)
        if set(self._equipped_personality_traits) - set(self._ungranted_traits) or not self._sim_info.is_baby:
            possible_traits = [trait for trait in trait_manager.types.values() if trait.is_personality_trait and self.can_add_trait(trait) and services.is_granted_or_non_account_reward_item(trait.guid64)]
            if possible_traits:
                chosen_trait = random.choice(possible_traits)
                self._add_trait(chosen_trait)
        self._add_default_gender_option_traits()
        add_quirks(self._sim_info)
        self.load_gameplay_object_preferences(trait_manager, data)
        ghost_only_traits_set = sims.ghost.Ghost.GHOST_ONLY_TRAITS & set(self)
        if not self.get_traits_of_type(TraitType.GHOST):
            for ghost_only_trait in ghost_only_traits_set:
                self._remove_trait(ghost_only_trait)
        self._sim_info.on_all_traits_loaded()

    def _has_any_trait_with_day_night_tracking(self):
        return any(trait for trait in self if trait.day_night_tracking is not None)

    def _add_day_night_tracking(self, trait):
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        if trait.day_night_tracking is not None and not sim.is_on_location_changed_callback_registered(self._day_night_tracking_callback):
            sim.register_on_location_changed(self._day_night_tracking_callback)
        self.update_day_night_tracking_state(force_update=True)

    def _remove_day_night_tracking(self, trait):
        self._day_night_state = None
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        if trait.day_night_tracking is None or self._has_any_trait_with_day_night_tracking():
            return
        sim.unregister_on_location_changed(self._day_night_tracking_callback)

    def _day_night_tracking_callback(self, *_, **__):
        self.update_day_night_tracking_state()

    def update_day_night_tracking_state(self, force_update=False, full_reset=False):
        if not self._has_any_trait_with_day_night_tracking():
            return
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        if full_reset:
            self._clear_all_day_night_buffs()
        time_service = services.time_service()
        is_day = time_service.is_day_time()
        in_sunlight = time_service.is_in_sunlight(sim)
        new_state = self._day_night_state is None
        if new_state:
            self._day_night_state = DayNightTrackingState(is_day, in_sunlight)
        update_day_night = new_state or self._day_night_state.is_day != is_day
        update_sunlight = new_state or self._day_night_state.in_sunlight != in_sunlight
        if force_update or update_day_night or not update_sunlight:
            return
        self._day_night_state.is_day = is_day
        self._day_night_state.in_sunlight = in_sunlight
        for trait in self:
            if not trait.day_night_tracking:
                pass
            else:
                day_night_tracking = trait.day_night_tracking
                if update_day_night or force_update:
                    self._add_remove_day_night_buffs(day_night_tracking.day_buffs, add=is_day)
                    self._add_remove_day_night_buffs(day_night_tracking.night_buffs, add=not is_day)
                if not update_sunlight:
                    if force_update:
                        self._add_remove_day_night_buffs(day_night_tracking.sunlight_buffs, add=in_sunlight)
                        self._add_remove_day_night_buffs(day_night_tracking.shade_buffs, add=not in_sunlight)
                self._add_remove_day_night_buffs(day_night_tracking.sunlight_buffs, add=in_sunlight)
                self._add_remove_day_night_buffs(day_night_tracking.shade_buffs, add=not in_sunlight)

    def update_day_night_buffs_on_buff_removal(self, buff_to_remove):
        if not self._has_any_trait_with_day_night_tracking():
            return
        for trait in self:
            if trait.day_night_tracking:
                if not trait.day_night_tracking.force_refresh_buffs:
                    pass
                else:
                    force_refresh_buffs = trait.day_night_tracking.force_refresh_buffs
                    if any(buff.buff_type is buff_to_remove.buff_type for buff in force_refresh_buffs):
                        self.update_day_night_tracking_state(full_reset=True, force_update=True)
                        return

    def _clear_all_day_night_buffs(self):
        for trait in self:
            if not trait.day_night_tracking:
                pass
            else:
                day_night_tracking = trait.day_night_tracking
                self._add_remove_day_night_buffs(day_night_tracking.day_buffs, add=False)
                self._add_remove_day_night_buffs(day_night_tracking.night_buffs, add=False)
                self._add_remove_day_night_buffs(day_night_tracking.sunlight_buffs, add=False)
                self._add_remove_day_night_buffs(day_night_tracking.shade_buffs, add=False)

    def _add_remove_day_night_buffs(self, buffs, add=True):
        for buff in buffs:
            if add:
                self._sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason)
            else:
                self._sim_info.remove_buff_by_type(buff.buff_type)

    def _has_any_trait_with_build_buy_purchase_tracking(self):
        return any(trait for trait in self if trait.build_buy_purchase_tracking is not None)

    def _add_build_buy_purchase_tracking(self, trait):
        if trait.build_buy_purchase_tracking is not None and not services.get_event_manager().is_registered_for_event(self, test_events.TestEvent.ObjectAdd):
            services.get_event_manager().register(self, (test_events.TestEvent.ObjectAdd,))

    def _remove_build_buy_purchase_tracking(self, trait):
        if trait.build_buy_purchase_tracking is None or self._has_any_trait_with_build_buy_purchase_tracking():
            return
        services.get_event_manager().unregister(self, (test_events.TestEvent.ObjectAdd,))

    def _handle_build_buy_purchase_event(self, trait, resolver):
        if not trait.build_buy_purchase_tracking:
            return
        for loot_action in trait.build_buy_purchase_tracking:
            loot_action.apply_to_resolver(resolver)

    def handle_event(self, sim_info, event_type, resolver):
        if event_type == test_events.TestEvent.ObjectAdd:
            for trait in self:
                self._handle_build_buy_purchase_event(trait, resolver)

    def on_sim_ready_to_simulate(self):
        for trait in self:
            self._add_day_night_tracking(trait)
            self._add_build_buy_purchase_tracking(trait)

    def get_provided_super_affordances(self):
        affordances = set()
        target_affordances = list()
        for trait in self._equipped_traits:
            affordances.update(trait.super_affordances)
            for provided_affordance in trait.target_super_affordances:
                provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
                target_affordances.append(provided_affordance_data)
        return (affordances, target_affordances)

    def get_actor_and_provided_mixers_list(self):
        actor_mixers = [trait.actor_mixers for trait in self._equipped_traits]
        provided_mixers = [trait.provided_mixers for trait in self._equipped_traits]
        return (actor_mixers, provided_mixers)

    def get_sim_info_from_provider(self):
        return self._sim_info

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.MINIMUM

    def on_lod_update(self, old_lod:'SimInfoLODLevel', new_lod:'SimInfoLODLevel') -> 'None':
        if new_lod == old_lod:
            return
        increase_lod = old_lod < new_lod
        for trait in tuple(self._equipped_traits):
            if self._has_valid_lod(trait):
                if increase_lod:
                    initial_commodities = trait.get_non_blacklisted_initial_commodities()
                    initial_commodities = initial_commodities - frozenset(self._sim_info.get_blacklisted_statistics())
                    for commodity in initial_commodities:
                        commodity_inst = self._sim_info.commodity_tracker.get_statistic(commodity, add=True)
                        if commodity_inst is not None:
                            commodity_inst.core = True
                    if trait.min_lod_value >= SimInfoLODLevel.ACTIVE:
                        if self._delayed_active_lod_traits is None:
                            self._delayed_active_lod_traits = list()
                        self._delayed_active_lod_traits.append(trait)
                    self._sim_info.remove_trait(trait)
            else:
                if trait.min_lod_value >= SimInfoLODLevel.ACTIVE:
                    if self._delayed_active_lod_traits is None:
                        self._delayed_active_lod_traits = list()
                    self._delayed_active_lod_traits.append(trait)
                self._sim_info.remove_trait(trait)
        if self._delayed_active_lod_traits is not None:
            for trait in self._delayed_active_lod_traits:
                self._add_trait(trait, from_delayed_lod=True)
            self._delayed_active_lod_traits = None

    def _has_valid_lod(self, trait):
        if self._sim_info.lod < trait.min_lod_value:
            return False
        return True

    @property
    def hide_relationships(self):
        return self._hiding_relationships

    def _register_trait_events(self, trait):
        if self._sim_info.is_npc:
            return
        if not trait.event_test_based_loots:
            return
        event_manager = services.get_event_manager()
        for (index, event_test_data) in enumerate(trait.event_test_based_loots):
            test_events = [(test_event, None) for test_event in event_test_data.test.get_test_events_to_register()]
            test_events.extend(event_test_data.test.get_custom_event_registration_keys())
            for test_key in test_events:
                if self._test_events is None or test_key not in self._test_events:
                    event_manager.register_with_custom_key(self, test_key[0], test_key[1])
                if self._test_events is None:
                    self._test_events = defaultdict(list)
                self._test_events[test_key].append((trait, index))

    def register_all_trait_events(self):
        for trait in self._equipped_traits:
            self._register_trait_events(trait)

    def _unregister_trait_events(self, trait):
        if self._test_events is None:
            return
        event_manager = services.get_event_manager()
        for (test_key, traits) in tuple(self._test_events.items()):
            for trait_data in tuple(traits):
                if trait is not trait_data[0]:
                    pass
                else:
                    traits.remove(trait_data)
                    if traits:
                        pass
                    else:
                        event_manager.unregister_with_custom_key(self, test_key[0], test_key[1])
                        del self._test_events[test_key]

    def _remove_trait_knowledge(self, trait, update_ui=True):
        if trait.trait_type not in self.KNOWLEDGE_TRAIT_TYPES:
            return
        tracker = self._sim_info.relationship_tracker
        for target in tracker.get_target_sim_infos():
            if target is None:
                logger.error('\n                            SimInfo {} has a relationship with a None target. The target\n                            has probably been pruned and the data is out of sync. Please\n                            provide a save and GSI dump and file a DT for this.\n                            ', self._sim_info, owner='asantos')
            else:
                target.relationship_tracker.remove_known_trait(trait, self._sim_info.id, notify_client=update_ui)

    def _remove_sexuality_knowledge(self, trait, update_ui=True):
        gender_preference_traits = GlobalGenderPreferenceTuning.get_preference_traits()
        is_romance_trait = trait in gender_preference_traits[0]
        is_woohoo_trait = trait in gender_preference_traits[1]
        if is_romance_trait or not is_woohoo_trait:
            return
        tracker = self._sim_info.relationship_tracker
        for target in tracker.get_target_sim_infos():
            if target is None:
                logger.error('\n                            SimInfo {} has a relationship with a None target. The target\n                            has probably been pruned and the data is out of sync. Please\n                            provide a save and GSI dump and file a bug for this.\n                            ', self._sim_info, owner='amwu')
            elif is_romance_trait:
                target.relationship_tracker.remove_knows_romantic_preference(self._sim_info.id, notify_client=update_ui)
            elif is_woohoo_trait:
                target.relationship_tracker.remove_knows_woohoo_preference(self._sim_info.id, notify_client=update_ui)

    def _remove_relationship_expectations_knowledge(self, trait:'Trait', update_ui:'bool'=True):
        relationship_expectations_traits = RelationshipExpectationsTuning.get_relationship_expectations_traits()
        if trait not in relationship_expectations_traits:
            return
        relationship_service = services.relationship_service()
        target_sim_infos = relationship_service.get_target_sim_infos(self._sim_info.sim_id)
        for target in target_sim_infos:
            if target is None:
                logger.error('\n                             SimInfo {} has a relationship with a None target. The target\n                             has probably been pruned and the data is out of sync. Please\n                             provide a save and GSI dump and file a bug for this.\n                             ', self._sim_info, owner='swhitehurst')
            else:
                relationship_service.remove_knows_relationship_expectations(target.sim_id, self._sim_info.sim_id, notify_client=update_ui)

    def _test_key(self, key, resolver):
        if self._test_events is None or key not in self._test_events:
            return
        for (trait, test_index) in self._test_events[key]:
            if resolver(trait.event_test_based_loots[test_index].test):
                trait.event_test_based_loots[test_index].loot.apply_to_resolver(resolver)

    def handle_event(self, sim_info, event, resolver):
        if sim_info is not self._sim_info:
            return
        self._test_key((event, None), resolver)
        for custom_key in resolver.custom_keys:
            self._test_key((event, custom_key), resolver)

    def refresh_trait_appearances(self, traits:'Iterable[Trait]') -> 'None':
        trait_ids = set([trait.guid64 for trait in traits])
        if trait_ids:
            op = TraitAppearanceUpdate(sim_id=self._sim_info.id, trait_ids=trait_ids)
            Distributor.instance().add_op_with_no_owner(op)

    def traits_with_display_overrides_gen(self, match_age:'Optional[Age]'=None, match_occult_type:'Optional[OccultType]'=None, match_trait:'Optional[Trait]'=None) -> 'Generator[Tuple[Trait, TraitAppearanceOverrideTuple]]':
        filter_overrides = match_age is not None or (match_occult_type is not None or match_trait is not None)
        for trait in self:
            if not trait.display_overrides:
                pass
            else:
                for override in trait.display_overrides:
                    if filter_overrides:
                        has_match = False
                        for match in override.match_all:
                            if match_age is not None and any([isinstance(age, Age) and match_age == age for age in match]):
                                has_match = True
                                break
                            elif match_occult_type is not None and any([isinstance(occult, OccultType) and match_occult_type == occult for occult in match]):
                                has_match = True
                                break
                            elif not match_trait is not None or match_trait in match:
                                has_match = True
                                break
                        if has_match:
                            yield (trait, override)
                            yield (trait, override)
                    else:
                        yield (trait, override)

class UiTraitPicker(UiObjectPicker):
    FACTORY_TUNABLES = {'sort_filter_categories': Tunable(description='\n           Sort filter categories into alphabetical order.\n           ', tunable_type=bool, default=False), 'remove_empty_filter_categories': Tunable(description='\n           Remove filter categories with no content.\n           ', tunable_type=bool, default=False), 'filter_categories': TunableList(description='\n            The categories to display in the dropdown for this picker.\n            ', tunable=TunableTuple(trait_category=TunableEnumEntry(tunable_type=TraitType, default=TraitType.PERSONALITY), icon=TunableIconFactory(), category_name=TunableLocalizedString()))}

    def _build_customize_picker(self, picker_data):
        with ProtocolBufferRollback(picker_data.filter_data) as filter_data_list:
            for category in self.filter_categories:
                with ProtocolBufferRollback(filter_data_list.filter_data) as category_data:
                    category_data.tag_type = category.trait_category.value + 1
                    build_icon_info_msg(category.icon(None), None, category_data.icon_info)
                    category_data.description = category.category_name
            filter_data_list.use_dropdown_filter = self.use_dropdown_filter
            filter_data_list.sort_filter_categories = self.sort_filter_categories
            filter_data_list.remove_empty_filter_categories = self.remove_empty_filter_categories
        picker_data.object_picker_data.num_columns = self.num_columns
        for row in self.picker_rows:
            row_data = picker_data.object_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class TraitPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiTraitPicker.TunableFactory(description='\n            The trait picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'is_add': Tunable(description='\n            If this interaction is trying to add a trait to the sim or to\n            remove a trait from the sim.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'already_equipped_tooltip': OptionalTunable(description='\n            If tuned, we show this tooltip if row is disabled when trait is \n            already equipped.\n            ', tunable=TunableLocalizedStringFactory(description='\n                Tooltip to display.\n                '), tuning_group=GroupNames.PICKERTUNING), 'filter_by_types': OptionalTunable(description='\n            If specified, limits the traits that appear in this picker to specific types of traits.\n            If disabled, all traits are available.\n            ', tunable=TunableWhiteBlackList(tunable=TunableEnumEntry(default=TraitType.PERSONALITY, tunable_type=TraitType)), tuning_group=GroupNames.PICKERTUNING), 'filter_by_tags': OptionalTunable(description='\n            If specified, limits the traits that appear in this picker to traits with specific tags.\n            If disabled, all traits are available.\n            ', tunable=TunableSet(description='\n                The traits must have any of these tags in order to satisfy the\n                requirement.\n                ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True), minlength=1), tuning_group=GroupNames.PICKERTUNING), 'continuation': OptionalTunable(description='\n            If enabled then a continuation will be pushed after the\n            picker selection has been made.\n            ', tunable=TunableContinuation(description='\n                If specified, a continuation to push when a picker\n                selection has been made.\n                '), tuning_group=GroupNames.PICKERTUNING), 'picker_target': TunableEnumEntry(tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        trait_target = self.get_participant(self.picker_target)
        self._show_picker_dialog(trait_target, target_sim=trait_target)
        return True

    @classmethod
    def _match_trait_type(cls, trait):
        if cls.filter_by_types is None:
            return True
        return cls.filter_by_types.test_item(trait.trait_type)

    @classmethod
    def _match_trait_tag(cls, trait:'Trait') -> 'bool':
        if cls.filter_by_tags is None:
            return True
        return trait.has_any_tag(cls.filter_by_tags)

    @classmethod
    def _trait_selection_gen(cls, target):
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        trait_tracker = target.sim_info.trait_tracker
        if cls.is_add:
            for trait in trait_manager.types.values():
                if not cls._match_trait_type(trait):
                    pass
                elif not cls._match_trait_tag(trait):
                    pass
                elif trait.sim_info_fixup_actions:
                    pass
                elif trait_tracker.can_add_trait(trait) or not trait_tracker.has_trait(trait) or cls.already_equipped_tooltip is not None:
                    yield trait
        else:
            for trait in trait_tracker.equipped_traits:
                if not cls._match_trait_type(trait):
                    pass
                else:
                    yield trait

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        trait_target = inst_or_cls.get_participant(cls.picker_target, target=target, context=context, **kwargs)
        trait_tracker = trait_target.sim_info.trait_tracker
        for trait in cls._trait_selection_gen(trait_target):
            if trait.display_name:
                display_name = trait.display_name(trait_target)
                is_enabled = True
                row_tooltip = None
                is_enabled = not trait_tracker.has_trait(trait)
                row_tooltip = None if is_enabled or cls.already_equipped_tooltip is None else lambda *_: cls.already_equipped_tooltip(target)
                row = ObjectPickerRow(name=display_name, row_description=trait.trait_description(trait_target), icon=trait.icon, tag_list=[trait.trait_type.value + 1], tag=trait, is_enable=is_enabled, row_tooltip=row_tooltip)
                yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        trait = choice_tag
        if trait is not None:
            if self.is_add:
                trait_target = self.get_participant(self.picker_target)
                trait_target.sim_info.add_trait(trait)
            else:
                trait_target = self.get_participant(self.picker_target)
                trait_target.sim_info.remove_trait(trait)
            if self.continuation is not None:
                self.push_tunable_continuation(self.continuation)

class AgentPickerSuperInteraction(TraitPickerSuperInteraction):

    @classmethod
    def _trait_selection_gen(cls, target):
        career_tracker = target.sim_info.career_tracker
        for career in career_tracker:
            for trait in career.current_level_tuning.agents_available:
                yield trait

class MatchmakingTraitPickerSuperInteraction(TraitPickerSuperInteraction):
    INSTANCE_TUNABLES = {'only_active_personality_traits': Tunable(description='\n            If this interaction is only displaying personality traits the current Sim has.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.UI)}

    @classmethod
    def _trait_selection_gen(cls, target):
        if cls.only_active_personality_traits:
            trait_tracker = target.sim_info.trait_tracker
            for trait in trait_tracker.equipped_traits:
                if not cls._match_trait_type(trait):
                    pass
                else:
                    yield trait
        else:
            yield from super()._trait_selection_gen(target)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if cls.only_active_personality_traits:
            trait_target = inst_or_cls.get_participant(cls.picker_target, target=target, context=context, **kwargs)
            matchmaking_service = services.get_matchmaking_service()
            if matchmaking_service is None:
                return
            for trait in cls._trait_selection_gen(trait_target):
                if trait.display_name:
                    display_name = trait.display_name(trait_target)
                    is_enabled = True
                    row_tooltip = None
                    actor_target = inst_or_cls.get_participant(inst_or_cls.picker_target)
                    matchmaking_data = matchmaking_service.actor_id_to_matchmaking_data[actor_target.sim_info.sim_id]
                    is_selected = True if trait.guid64 in matchmaking_data.selected_trait_ids else False
                    row = ObjectPickerRow(name=display_name, row_description=trait.trait_description(trait_target), icon=trait.icon, tag_list=[trait.trait_type.value + 1], tag=trait, is_enable=is_enabled, row_tooltip=row_tooltip, is_selected=is_selected)
                    yield row
        else:
            yield from super(__class__, inst_or_cls).picker_rows_gen(target, context, **kwargs)

    def on_choice_selected(self, trait, **kwargs):
        raise NotImplementedError

    def on_multi_choice_selected(self, picked_traits, **kwargs):
        matchmaking_service = services.get_matchmaking_service()
        if matchmaking_service is None:
            return
        if len(picked_traits) == 0:
            return
        selected_trait_ids = set()
        for picked_trait in picked_traits:
            selected_trait_ids.add(picked_trait.guid64)
        actor_target = self.get_participant(self.picker_target)
        matchmaking_service.set_selected_traits_for_sim_profile(actor_target.sim_info, selected_trait_ids)

class ReincarnationTraitPickerSuperInteraction(TraitPickerSuperInteraction):
    INSTANCE_TUNABLES = {'conflict_trait_tooltip': TunableLocalizedStringFactory(description='\n            Tooltip to display if the trait is conflict with any other trait\n            that is already equipped on sim.\n            ', tuning_group=GroupNames.PICKERTUNING), 'existing_trait_tooltip': TunableLocalizedStringFactory(description='\n            Tooltip to display if the trait is already exist on sim. \n            ', tuning_group=GroupNames.PICKERTUNING), 'invalid_trait_tooltip': TunableLocalizedStringFactory(description="\n            Tooltip to display if the trait is conflict with sim's age or gender.\n            ", tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _trait_selection_gen(cls, target):
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        traits_list = target.sim_info.reincarnation_data.trait_ids
        for trait_id in traits_list:
            trait = trait_manager.get(trait_id)
            if not cls._match_trait_type(trait):
                pass
            elif not cls._match_trait_tag(trait):
                pass
            else:
                yield trait

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        trait_target = inst_or_cls.get_participant(cls.picker_target, target=target, context=context, **kwargs)
        for trait in cls._trait_selection_gen(trait_target):
            is_enabled = True
            tooltip = cls._get_trait_tooltip(trait, trait_target.sim_info)
            is_enabled = False
            if not tooltip is not None or trait.display_name:
                display_name = trait.display_name(trait_target)
                row = ObjectPickerRow(name=display_name, row_description=trait.trait_description(trait_target), icon=trait.icon, tag_list=[trait.trait_type.value + 1], tag=trait, is_enable=is_enabled, row_tooltip=tooltip)
                yield row

    @classmethod
    def _get_trait_tooltip(cls, trait:'Trait', sim_info:'SimInfo') -> 'TunableLocalizedString':
        if not trait.is_valid_trait(sim_info):
            return cls.invalid_trait_tooltip
        for equipped_trait in sim_info.get_traits():
            if equipped_trait.guid64 == trait.guid64:
                return cls.existing_trait_tooltip
            if equipped_trait.is_conflicting(trait):
                return cls.conflict_trait_tooltip

    def on_choice_selected(self, choice_tag, **kwargs):
        trait = choice_tag
        if trait is not None:
            trait_target = self.get_participant(self.picker_target)
            trait_target.sim_info.add_trait(trait, is_extra_personality_trait=True)
            if self.continuation is not None:
                self.push_tunable_continuation(self.continuation)

    def on_multi_choice_selected(self, picked_traits, **kwargs):
        if len(picked_traits) == 0:
            return
        trait_target = self.get_participant(self.picker_target)
        for picked_trait in picked_traits:
            trait_target.sim_info.add_trait(picked_trait)
        if self.continuation is not None:
            self.push_tunable_continuation(self.continuation)
lock_instance_tunables(ReincarnationTraitPickerSuperInteraction, is_add=True, already_equipped_tooltip=None)