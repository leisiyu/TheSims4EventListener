from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.script_object import ScriptObject
    from interactions.payment.payment_altering_service import PaymentAlteringServicefrom sims.funds import FundsSourcefrom _sims4_collections import frozendictimport functoolsimport objectsimport randomfrom caches import cachedfrom collections import namedtuple, defaultdictfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.utils.tunable_icon import TunableIconfrom objects.components.stored_info_component import StoredInfoComponentfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, TunableList, OptionalTunable, TunableEnumEntry, Tunable, TunableSet, TunableEnumWithFilter, TunableTuple, TunableEnumSet, TunableVariant, TunableMappingfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, flexproperty, classpropertyfrom singletons import DEFAULTimport sims4.localizationimport sims4.logimport sims4.telemetryfrom animation.animation_utils import flush_all_animationsfrom animation.posture_manifest import AnimationParticipant, SlotManifest, SlotManifestEntryfrom animation.posture_manifest_constants import SIT_PICKUP_POSTURESfrom bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom build_buy import add_object_to_buildbuy_systemfrom carry.carry_elements import CarryElementHelperfrom carry.carry_interactions import PickUpObjectSuperInteractionfrom carry.carry_postures import CarryingObjectfrom carry.carry_utils import SCRIPT_EVENT_ID_STOP_CARRY, SCRIPT_EVENT_ID_START_CARRY, PARAM_CARRY_TRACKfrom crafting import crafting_handlersfrom crafting.crafting_grab_serving_mixin import GrabServingMixinfrom crafting.crafting_ingredients import IngredientTuning, IngredientTooltipStyle, IngredientRequirement, IngredientRequirementByDeffrom crafting.crafting_process import CraftingProcess, CRAFTING_QUALITY_LIABILITYfrom crafting.crafting_tunable import CraftingTuningfrom crafting.recipe import CraftingObjectType, Recipe, PhaseName, Phasefrom distributor.shared_messages import IconInfoDatafrom element_utils import build_critical_section_with_finally, build_critical_section, unless, build_elementfrom event_testing.resolver import SingleSimResolver, SingleActorAndObjectResolverfrom event_testing.results import TestResult, EnqueueResult, ExecuteResultfrom interactions import ParticipantType, liability, ParticipantTypeSingle, ParticipantTypeSingleSimfrom interactions.aop import AffordanceObjectPairfrom interactions.base.basic import TunableBasicContentSetfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.base.picker_interaction import PickerSuperInteraction, AutonomousPickerSuperInteractionfrom interactions.base.super_interaction import SuperInteraction, RallySourcefrom interactions.constraints import Anywhere, Constraint, create_constraint_set, GLOBAL_STUB_ACTORfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom interactions.payment.payment_source import get_tunable_payment_source_variantfrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.parent_object import ParentObjectElementfrom interactions.utils.interaction_liabilities import CANCEL_INTERACTION_ON_EXIT_LIABILITY, CancelInteractionsOnExitLiabilityfrom interactions.utils.loot import LootOperationListfrom interactions.utils.reserve import TunableReserveObjectfrom objects.components.state import state_changefrom objects.components.state_references import TunableStateValueReferencefrom objects.components.types import CRAFTING_COMPONENTfrom objects.helpers.create_object_helper import CreateObjectHelperfrom objects.persistence_groups import PersistenceGroupsfrom objects.slots import SlotTypeReferences, get_surface_height_parameter_for_objectfrom objects.system import create_objectfrom postures import PostureTrackfrom postures.posture_specs import PostureSpecVariablefrom postures.posture_state_spec import PostureStateSpecfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom tag import Tagfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog_picker import RecipePickerRow, UiRecipePicker, RowMapTypeimport build_buyimport element_utilsimport servicesimport telemetry_helperfrom sims.family_recipes.family_recipes_tuning import FamilyRecipesTuninglogger = sims4.log.Logger('Interactions')TELEMETRY_GROUP_CRAFTING = 'CRFT'TELEMETRY_HOOK_NEW_OBJECT = 'NOBJ'TELEMETRY_FIELD_OBJECT_TYPE = 'obtp'TELEMETRY_FIELD_OBJECT_QUALITY = 'qual'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CRAFTING)NO_OTHER_SIMS = 0PARTY_CRAFTING = 1CRAFT_FOR_SPECIFIC_PARTICIPANT = 2
def create_craftable(chosen_recipe, crafter_sim, inventory_owner=None, quality=None, owning_household_id_override=None, place_in_inventory=False, post_add=None, seeded_random=None, **kwargs):
    if inventory_owner is None:
        inventory_owner = crafter_sim
    if seeded_random is None:
        seeded_random = random.Random()
    crafting_process = CraftingProcess(crafter=crafter_sim, recipe=chosen_recipe)

    def setup_object(obj):
        crafting_process.setup_crafted_object(obj, is_final_product=True, owning_household_id_override=owning_household_id_override, random=seeded_random)

    def _post_add(obj):
        if chosen_recipe.final_product.apply_states:
            for apply_state in chosen_recipe.final_product.apply_states:
                obj.set_state(apply_state.state, apply_state, force_update=True)
        stat = CraftingTuning.PROGRESS_STATISTIC
        tracker = obj.get_tracker(stat)
        if tracker.has_statistic(stat):
            tracker.set_max(stat)
        if quality is not None:
            obj.set_state(quality.state, quality)
        crafting_process.apply_simoleon_value(obj)
        cas_parts = crafting_process.recipe.final_product.stored_cas_parts
        if cas_parts:
            StoredInfoComponent.store_info_on_object(obj, _cas_parts=cas_parts)
        obj.append_tags(chosen_recipe.apply_tags)
        crafting_component = obj.get_component(objects.components.types.CRAFTING_COMPONENT)
        crafting_component.on_crafting_process_finished()
        if post_add is not None:
            post_add(obj)

    product = create_object(chosen_recipe.final_product.definition.id, init=setup_object, post_add=_post_add)
    try:
        if product.inventoryitem_component.inventory_only:
            place_in_inventory = True
        if product.inventoryitem_component is not None and place_in_inventory and inventory_owner is not None:
            inventory_owner.inventory_component.system_add_object(product)
    except:
        product.destroy(source=crafter_sim, cause='Except during creation of craftable.')
        raise
    return product

def _get_ingredient_candidates_cache_key(cls, crafter, crafting_target):
    key = [crafter, crafting_target]
    if cls.check_sim_inventory and crafter is not None:
        key.append(crafter.inventory_component.last_updated_timestamp)
    if cls.check_fridge_shared_inventory:
        fridge_inventory = services.active_lot().get_object_inventories(CraftingTuning.SHARED_FRIDGE_INVENTORY_TYPE)[0]
        key.append(fridge_inventory.last_updated_timestamp)
    if cls.check_target_inventory and crafting_target is not None:
        key.append(crafting_target.inventory_component.last_updated_timestamp)
    return tuple(key)

def get_ingredient_requirement_with_ingredient_replacement_rules(recipe_ingredient_requirements):
    new_ingredient_requirements = [requirement for requirement in recipe_ingredient_requirements]
    replacement_map = Recipe.INGREDIENT_REPLACEMENT_MAP
    ingredients_to_remove = []
    for ingredient_to_consume in new_ingredient_requirements:
        for replacement_entry in replacement_map:
            replacement_ingredient = replacement_entry.replacement_ingredient
            if replacement_ingredient.factory.is_equal(replacement_ingredient, ingredient_to_consume):
                ingredients_to_remove.extend(replacement_entry.ingredients_to_replace_list)
    if len(ingredients_to_remove) == 0:
        return new_ingredient_requirements
    for i in range(len(new_ingredient_requirements) - 1, -1, -1):
        ingredient_to_consume = new_ingredient_requirements[i]
        for ingredient_to_remove_factory in ingredients_to_remove:
            if ingredient_to_remove_factory.factory.is_equal(ingredient_to_remove_factory, ingredient_to_consume):
                new_ingredient_requirements.pop(i)
                break
    return new_ingredient_requirements

class StartCraftingMixin:
    INSTANCE_TUNABLES = {'check_target_inventory': Tunable(description="\n            If checked, look through the target object's inventory for \n            gathering ingredients.\n            ", tunable_type=bool, default=False), 'check_sim_inventory': Tunable(description="\n            If checked, look through the sims's inventory for \n            gathering ingredients.\n            ", tunable_type=bool, default=True), 'check_fridge_shared_inventory': Tunable(description='\n            If checked, look through the fridge shared inventory for \n            gathering ingredients.\n            ', tunable_type=bool, default=True), 'set_target_as_current_ico': Tunable(description='\n            After creating the crafting component, if this is checked, the\n            value of current_ico on the crafting_process will be set to the\n            target.\n            \n            This is a way to make an object that we are not creating as an ICO\n            to behave a bit like an ICO. By setting the current_ico to the\n            target it allows the crafting interactions to return the target as\n            the carry target, enabling the non ICO object to be carried to\n            where it needs to be.\n            \n            For an example of when you might want to set this consider the Kave\n            bowl. The Kava Bowl acts as both an ICO and a Final Product that\n            holds individual servings. The only way to carry the Kava Bowl to\n            the correct place to run the interaction is to set the current_ico\n            to the kava bowl despite it not actually being a traditional ICO.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orderer_ids = []

    def _set_orderers(self, sim):
        if self.craft_for_other_sims.option == PARTY_CRAFTING:
            party_sims = sim.get_sims_for_rally(self.craft_for_other_sims.rally_source)
            if party_sims:
                self.orderer_ids.extend(sim.id for sim in party_sims)
            else:
                self.orderer_ids.append(sim.id)
        elif self.craft_for_other_sims.option == CRAFT_FOR_SPECIFIC_PARTICIPANT:
            participant = self.get_participant(participant_type=self.craft_for_other_sims.participant)
            if participant is not None:
                self.orderer_ids.append(participant.id)
        else:
            self.orderer_ids.append(sim.id)

    def _get_bucks_available(self, bucks_type, paying_sim):
        tracker = BucksUtils.get_tracker_for_bucks_type(bucks_type, owner_id=paying_sim.id)
        if tracker is None:
            return 0
        return tracker.get_bucks_amount_for_type(bucks_type)

    @flexmethod
    def _get_recipe_price_discounts(cls, inst, recipe, is_retail=False, ingredient_modifier=1, resolver=None, extra_cost=0):
        inst_or_cls = inst if inst is not None else cls
        if resolver is None:
            resolver = inst_or_cls.get_resolver()
        multiplier = inst_or_cls.price_multiplier.get_multiplier(resolver) if hasattr(inst_or_cls, 'price_multiplier') else 1
        (_, _, discounted_price) = recipe.get_price(is_retail=is_retail, ingredient_modifier=ingredient_modifier, multiplier=multiplier, extra_cost=extra_cost)
        unresolved_multipliers = inst_or_cls.bucks_price_multipliers if hasattr(inst_or_cls, 'bucks_price_multipliers') else {}
        resolved_multipliers = {}
        for buck_type in unresolved_multipliers:
            resolved_multipliers[buck_type] = unresolved_multipliers[buck_type].get_multiplier(resolver)
        bucks_prices = recipe.get_bucks_prices(is_retail=is_retail, multipliers=resolved_multipliers)
        return (discounted_price, bucks_prices)

    def _handle_begin_crafting(self, recipe, crafter, ordering_sim=None, crafting_target=None, orderer_ids=DEFAULT, ingredients=(), funds_source=None, paying_sim=None, ingredient_cost_only=False, situation_id=None, use_fresh_ingredients=False, use_prepped_ingredients=False, defined_ingredients=None, extra_cost=0, family_recipe=None):
        if orderer_ids is DEFAULT:
            orderer_ids = []
        if self.ingredient_source:
            ingredients = self._recipe_ingredients_map.get(recipe)
        if (ingredients or hasattr(self, 'ingredient_source') and recipe.use_ingredients or ingredient_cost_only) and ingredients is not None:
            (test_result, ingredients_to_consume) = self.validate_and_satisfy_ingredients(crafter, ingredients, all_ingredients_required=recipe.all_ingredients_required, crafting_target=crafting_target)
            if not test_result:
                return EnqueueResult(test_result, None)
            (ingredient_modifier, avg_quality_bonus, ingredient_log) = self._get_ingredients_modifier_and_quality_bonus(ingredients)
        else:
            ingredients_to_consume = {}
            ingredient_log = []
            ingredient_modifier = 1
            avg_quality_bonus = 0
            test_result = TestResult(True)
        is_retail = False
        if paying_sim is None:
            if ordering_sim is not None and crafter is not ordering_sim:
                paying_sim = ordering_sim
                if hasattr(self, 'ingredient_source') and self.ingredient_source:
                    is_retail = False
                else:
                    is_retail = True
            else:
                paying_sim = crafter
        (discounted_price, discounted_bucks_prices) = self._get_recipe_price_discounts(recipe, is_retail=is_retail, ingredient_modifier=ingredient_modifier, extra_cost=extra_cost)
        if family_recipe is not None:
            definition_manager = services.definition_manager()
            buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
            buff = buff_manager.get(family_recipe.buff_id)
            buff_cost = 0
            if buff is not None:
                buff_cost = buff.buff_type.buff_cost
            extra_ingredient = definition_manager.get(family_recipe.ingredient_id)
            family_recipes_tracker = paying_sim.sim_info.family_recipes_tracker
            if family_recipes_tracker is None:
                return
            cost_modifier = family_recipes_tracker.get_family_recipe_cost_modifier(recipe)
            discounted_price += extra_ingredient.price + round(buff_cost*cost_modifier)
        ordered_ids_count = len(orderer_ids)
        discounted_price *= ordered_ids_count
        if ingredient_cost_only:
            discounted_price = 0
        if funds_source is None:
            if not paying_sim.family_funds.can_afford(discounted_price):
                return
        elif funds_source.max_funds(paying_sim) < discounted_price:
            return
        for (bucks_type, amount) in discounted_bucks_prices.items():
            available = self._get_bucks_available(bucks_type, paying_sim)
            amount *= ordered_ids_count
            if available < amount:
                return
        reserved_ingredients = []
        earmarked_servings = {}
        for (ingredient_object, count) in ingredients_to_consume.items():
            inventory = ingredient_object.get_inventory()
            if inventory is not None:
                tracker = None if not hasattr(ingredient_object, 'get_tracker') else ingredient_object.get_tracker(CraftingTuning.SERVINGS_STATISTIC)
                if tracker is not None and tracker.has_statistic(CraftingTuning.SERVINGS_STATISTIC):
                    earmarked_servings[ingredient_object] = count
                elif not inventory.try_move_object_to_hidden_inventory(ingredient_object, count=count):
                    logger.error('Tried reserving the ingredient object, {}, but failed.', ingredient_object, owner='camilogarcia')
                    test_result = TestResult(False, 'Failed to reserve ingredients in _handle_begin_crafting.')
                else:
                    reserved_ingredients.append(ingredient_object)
                reserved_ingredients.append(ingredient_object)
            else:
                logger.error('Trying to consume ingredient {} thats not on an inventory.', ingredient_object, owner='camilogarcia')
        original_target = None
        if self.context.pick is not None:
            original_target = self.context.pick.target
        else:
            original_target = self.target
        self.crafting_process = None
        if original_target is not None and (original_target.has_component(CRAFTING_COMPONENT) and hasattr(self, 'remove_previous_crafting_component')) and self.remove_previous_crafting_component:
            original_target.remove_component(CRAFTING_COMPONENT)
        self.crafting_process = CraftingProcess(self.context.sim, crafter, recipe, discounted_price, paying_sim, reserved_ingredients=reserved_ingredients, orderer_ids=orderer_ids, original_target=original_target, ingredient_quality_bonus=avg_quality_bonus, funds_source=funds_source, bucks_cost=discounted_bucks_prices, situation_id=situation_id, defined_ingredients=defined_ingredients, earmarked_servings=earmarked_servings, family_recipe=family_recipe, saved_participants=self._saved_participants)
        if self.set_target_as_current_ico:
            self.crafting_process.current_ico = original_target
        if test_result:
            result = self.crafting_process.push_si_for_first_phase(self, crafting_target, use_fresh_ingredients=use_fresh_ingredients, use_prepped_ingredients=use_prepped_ingredients)
            crafting_handlers.log_ingredient_calculation(self.crafting_process, crafter.id, ingredient_log)
        if not (test_result and result):
            for ingredient in reserved_ingredients:
                if not crafter.inventory_component.try_move_hidden_object_to_inventory(ingredient, count=ingredient.stack_count()):
                    logger.error('Could not return reserved ingredient {} to crafter. Interaction: {}', ingredient, self, owner='rmccord')
            result = EnqueueResult(test_result, None)
        else:
            if situation_id is not None:
                situation = services.get_zone_situation_manager().get(situation_id)
                if situation is None:
                    logger.error('Attempting to set crafting process on situation with id {} that is not running.', situation_id)
                else:
                    situation.set_crafting_process(self.crafting_process)
            for (ingredient, count) in earmarked_servings.items():
                servings = ingredient.get_stat_instance(CraftingTuning.SERVINGS_STATISTIC)
                servings.tracker.add_value(CraftingTuning.SERVINGS_STATISTIC, -count)
        return result

    @staticmethod
    def get_default_candidate_ingredients(crafter, check_sim_inventory=True, check_fridge_shared_inventory=True):
        candidate_ingredients = []
        if crafter is not None:
            sim_inventory = crafter.inventory_component
            for obj in sim_inventory:
                if obj.definition.has_build_buy_tag(IngredientTuning.INGREDIENT_TAG):
                    candidate_ingredients.append(obj)
        if check_sim_inventory and check_fridge_shared_inventory:
            fridge_inventory = services.active_lot().get_object_inventories(CraftingTuning.SHARED_FRIDGE_INVENTORY_TYPE)[0]
            if fridge_inventory is not None:
                for obj in fridge_inventory:
                    if obj.definition.has_build_buy_tag(IngredientTuning.INGREDIENT_TAG):
                        candidate_ingredients.append(obj)
        return candidate_ingredients

    @classmethod
    @cached(key=_get_ingredient_candidates_cache_key)
    def _get_ingredient_candidates(cls, crafter, crafting_target=None):
        all_ingredients = StartCraftingMixin.get_default_candidate_ingredients(crafter, check_sim_inventory=cls.check_sim_inventory, check_fridge_shared_inventory=cls.check_fridge_shared_inventory)
        if crafting_target is not None:
            if crafting_target.inventory_component is None:
                logger.error('Inventory component is None, this interaction is likely mistuned. \n\tinteraction={}', cls.__name__)
                return all_ingredients
            for obj in crafting_target.inventory_component:
                if obj.definition.has_build_buy_tag(IngredientTuning.INGREDIENT_TAG):
                    all_ingredients.append(obj)
        candidate_ingredients = []
        for ingredient in all_ingredients:
            if IngredientRequirement.is_possibly_valid_ingredient(ingredient):
                candidate_ingredients.append(ingredient)
        candidate_ingredients.sort(key=lambda x: IngredientTuning.get_quality_bonus(x) + IngredientTuning.get_ingredient_sort_value(x))
        return candidate_ingredients

    def validate_and_satisfy_ingredients(self, crafter, ingredient_requirements, all_ingredients_required=False, crafting_target=None):
        ingredients_used = {}
        all_satisfied = True
        for ingredient_requirement in ingredient_requirements:
            ingredient_requirement.check_ingredients_used(ingredients_used)
            all_satisfied = all_satisfied & ingredient_requirement.satisfied
        if not all_satisfied:
            candidate_ingredients = self._get_ingredient_candidates(crafter, crafting_target=crafting_target)
            for ingredient_requirement in ingredient_requirements:
                ingredient_requirement.attempt_satisfy_ingredients(candidate_ingredients, ingredients_used)
                if all_ingredients_required and not ingredient_requirement.satisfied:
                    return (TestResult(False, 'All ingredients required but not satisfied.'), ingredients_used)
        return (TestResult(True), ingredients_used)

    def _get_ingredients_modifier_and_quality_bonus(self, ingredient_requirements):
        total_required = sum(ingredient_requirement.count_required for ingredient_requirement in ingredient_requirements)
        total_satisfied = sum(ingredient_requirement.count_satisfied for ingredient_requirement in ingredient_requirements)
        ingredient_logger = []
        total_quality = sum(ingredient_requirement.get_cumulative_quality(ingredient_logger) for ingredient_requirement in ingredient_requirements)
        avg_quality_bonus = total_quality/total_required if total_required != 0 else 0
        ingredient_modifier = (total_required - total_satisfied)/total_required if total_required != 0 else 1
        return (ingredient_modifier, avg_quality_bonus, ingredient_logger)

    def get_valid_recipe_list(self, candidate_ingredients:'Sequence[ScriptObject]'=(), ingredient_cost_only:'bool'=False, crafter=None) -> 'List[Recipe]':
        return [(0, recipe) for recipe in self.recipes if not ingredient_cost_only or recipe.all_ingredients_available(candidate_ingredients, True)]

    def find_best_recipe(self, valid_recipes:'List[Recipe]') -> 'Recipe':
        weights = []
        crafter = self.target if self.target.is_sim else self.sim
        for recipe in valid_recipes:
            if recipe.all_ingredients_required:
                pass
            else:
                result = CraftingProcess.recipe_test(self.target, self.context, recipe, crafter, 0, build_error_list=False, from_autonomy=True, check_bucks_costs=False)
                if result:
                    weights.append((recipe.calculate_autonomy_weight(self.sim), recipe))
        if not weights:
            logger.error('Failed to find recipes to pick for : {} ', self)
            return
        recipe = sims4.random.pop_weighted(weights)
        return recipe

def get_ingredient_requirements_only_prepped(ingredient_requirements, all_ingredients_required):
    if not all_ingredients_required:
        only_prepped_ingredients = [ingredient_requirement for ingredient_requirement in ingredient_requirements if ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG)]
    else:
        only_prepped_ingredients = get_ingredient_requirement_with_ingredient_replacement_rules(ingredient_requirements)
    return only_prepped_ingredients

def get_ingredient_requirements_only_fresh(ingredient_requirements):
    only_fresh_ingredients = [ingredient_requirement for ingredient_requirement in ingredient_requirements if not ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG)]
    return only_fresh_ingredients

def get_ingredient_requirements_both_fresh_and_prepped(ingredient_requirements):
    both_fresh_prepped_ingredients = get_ingredient_requirement_with_ingredient_replacement_rules(ingredient_requirements)
    return both_fresh_prepped_ingredients

def get_ingredient_requirements(ingredient_requirements, all_ingredients_required):
    both_fresh_prepped_ingredients = get_ingredient_requirement_with_ingredient_replacement_rules(ingredient_requirements)
    if all_ingredients_required:
        only_fresh_ingredients = get_ingredient_requirements_only_fresh(ingredient_requirements)
        only_prepped_ingredients = list(both_fresh_prepped_ingredients)
    else:
        only_prepped_ingredients = []
        only_fresh_ingredients = []
        for ingredient_requirement in ingredient_requirements:
            if ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG):
                only_prepped_ingredients.append(ingredient_requirement)
            else:
                only_fresh_ingredients.append(ingredient_requirement)
    return (only_fresh_ingredients, only_prepped_ingredients, both_fresh_prepped_ingredients)

def add_new_ingredient_requirement(defined_ingredients, new_ingredient_id:'int'):
    if defined_ingredients is None:
        new_ingredient_requirements = []
    else:
        new_ingredient_requirements = [requirement for requirement in defined_ingredients]
    definition_manager = services.definition_manager()
    ingredient_definition = definition_manager.get(new_ingredient_id)
    ingredient_requirement = IngredientRequirementByDef(ingredient_ref=ingredient_definition)
    new_ingredient_requirements.append(ingredient_requirement)
    return new_ingredient_requirements

def build_requirement_data(requirements_for_recipe, all_ingredients_required):
    adjusted_ingredient_price = 1
    ingredients_found_count = 0
    ingredients_needed_count = 0
    enable_recipe = True
    has_required_ingredients = True
    for ingredient_requirement in requirements_for_recipe:
        ingredients_found_count += ingredient_requirement.count_satisfied
        ingredients_needed_count += ingredient_requirement.count_required
    if ingredients_found_count < ingredients_needed_count:
        enable_recipe = False
        has_required_ingredients = False
    if all_ingredients_required and ingredients_needed_count:
        adjusted_ingredient_price = (ingredients_needed_count - ingredients_found_count)/ingredients_needed_count
    return (enable_recipe, has_required_ingredients, adjusted_ingredient_price)

class StartCraftingSuperInteraction(StartCraftingMixin, PickerSuperInteraction):
    CAS_UNLOCKED_ICON = TunableIcon(description='\n        Icon to be displayed if this row is unlocked in cas.\n        ')
    CAS_LOCKED_ICON = TunableIcon(description='\n        Icon to be displayed if this row is locked in cas.\n        ')
    INSTANCE_TUNABLES = {'crafter': TunableEnumEntry(description='\n            Who is to be crafting the recipe.  Typically this is set to Actor \n            if this affordance is targetting an object.\n            \n            You can set this to TargetSim if you want to have the appearance\n            of directing a Sim to craft the recipe.  Note that in these\n            cases, which object they use to craft is determined by autonomy.\n            \n            See also "Funds Source" and "Paying Sim" for additional tuning\n            if this is for the purpose of employee crafting.\n            \n            Note: If the world object needed for crafting is not on the lot\n            this will fail with a warning that it could not find an affordance\n            to run phases for the recipe on.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'funds_source': get_tunable_payment_source_variant(description='\n            When deducting the cost of the recipe, it will be deducted \n            from this funds source.\n            '), 'paying_sim': OptionalTunable(description='\n            If set, force the paying Sim to be this participant.\n            \n            This does not normally need to be set.\n            \n            In general, the behavior is that the person crafting the item \n            incurs the cost of the recipe.  \n            For orders, it is the person who is ordering the recipe.\n            \n            For driving other Sims to craft items \n            (e.g. Actor is a Sim, and crafter above is TargetSim)\n            it\'s not necessarily an "order" because the actor will not \n            wait for the order to complete.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)), 'recipes': TunableList(description='\n            The recipes a Sim can craft.\n            ', tunable=TunableReference(description='\n                Recipe to craft.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), pack_safe=True, reload_dependent=True)), 'craft_for_other_sims': TunableVariant(description='\n            Options for crafting this drink for other sims.\n            ', no_other_sims=TunableTuple(description="\n                Don't craft this for any other sims.\n                ", locked_args={'option': NO_OTHER_SIMS}), party_crafting=TunableTuple(description='\n                Craft for all for the Sims in a rally source.\n                ', rally_source=TunableEnumSet(description='\n                    A list of different sources that we want to use to figure\n                    out the Sims to craft drinks for.\n                    ', enum_type=RallySource, enum_default=RallySource.ENSEMBLE, default_enum_list=frozenset((RallySource.ENSEMBLE,))), locked_args={'option': PARTY_CRAFTING}), craft_for_specific_participant=TunableTuple(description='\n                Craft for the Sim of a specific participant type. \n                ', participant=TunableEnumEntry(description='\n                    The specific participant that we want to craft for. \n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.PickedSim), locked_args={'option': CRAFT_FOR_SPECIFIC_PARTICIPANT}), default='no_other_sims'), 'create_unavailable_recipe_description': TunableLocalizedStringFactory(default=4228422038, tuning_group=GroupNames.UI), 'basic_reserve_object': TunableReserveObject(), 'use_ingredients_default_value': Tunable(description='\n            Default value if the interaction should use ingredients. \n            If this interaction is not using the recipe picker but the \n            interaction picker, this is the way to tune if a cooking \n            interaction will use ingredients or not.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'favorite_recipe': OptionalTunable(description='\n            If enabled, the interaction will use Sim\'s favorite recipe (which\n            is constrained by the tag sets) to push the crafting interaction.\n            If the tag sets is empty, then pick any of the sim\'s favorite\n            recipe. If the sim has no favorite recipe set, then randomly select\n            a valid one from the interaction recipe, and persist that on the\n            sim if "Persist New Favorite Recipe" tuning is checked.\n            ', tunable=TunableTuple(recipe_tags=TunableSet(tunable=TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=['recipe'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True)), persist_new_favorite_recipe=Tunable(description="\n                    When the sim has no favorite recipe set, then randomly \n                    select a valid one from the interaction recipe.\n                    \n                    If checked, the new selected favorite recipe will be \n                    persisted as favorite recipe for the sim. Otherwise, \n                    it won't be persisted.\n                    ", tunable_type=bool, default=True), pie_menu_tooltip=OptionalTunable(description='\n                    If enabled, then a greyed-out tooltip will be displayed if there\n                    are no valid favorite recipe. When disabled, the test to check for valid\n                    choices will run first and if it fail any other tuned test in the\n                    interaction will not get run. When enabled, the tooltip will be the\n                    last fallback tooltip, and if other tuned interaction tests have\n                    tooltip, those tooltip will show first. [cjiang/scottd]\n                    ', tunable=TunableLocalizedStringFactory(description='\n                        The tooltip text to show in the greyed-out tooltip when no valid\n                        favorite recipe exists.\n                        '))), disabled_name='use_picker', enabled_name='use_favorite_recipe'), 'price_multiplier': TunableMultiplier.TunableFactory(description='\n            Tested multipliers to apply to the price of the item.\n            ', tuning_group=GroupNames.PICKERTUNING, multiplier_options={'use_tooltip': True}), 'bucks_price_multipliers': TunableMapping(description='\n            Mapping of buck type to tested multiplier to apply to the bucks price\n            of the item.\n            ', key_type=TunableEnumEntry(description='\n                Buck type to apply price multiplier to.\n                ', tunable_type=BucksType, default=BucksType.INVALID), value_type=TunableMultiplier.TunableFactory(description='\n                Tested multipliers to apply to the bucks price of the item.\n                ', multiplier_options={'use_tooltip': True}), tuning_group=GroupNames.PICKERTUNING), 'ingredient_cost_only': Tunable(description='\n            If true, this interaction will require ingredients for all recipes and not have a simoleon cost.\n            ', tunable_type=bool, default=False), 'show_disabled_crafting_recipes': Tunable(description='\n            If checked, the disabled recipe will show up in the crafting picker with a greyed-out \n            tooltip. Otherwise the disabled item will not show up!\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'remove_previous_crafting_component': Tunable(description='\n        If set to True, when more than one interaction is queued a new crafting component is added to object, \n        if set to False second interaction will be cancelled immediately.\n        ', tunable_type=bool, default=True), 'allow_empty_recipes': Tunable(description='\n            If set to True, the interaction will be available even if there are no valid recipes, \n            ', tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        for recipe in cls.recipes:
            recipe.validate_for_start_crafting()

    def __init__(self, *args, recipe_ingredients_map=None, **kwargs):
        self._recipe_ingredients_map = recipe_ingredients_map
        self._suppressed_picker_columns = []
        super().__init__(*args, recipe_ingredients_map=recipe_ingredients_map, **kwargs)

    @flexmethod
    def _use_ellipsized_name(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls.favorite_recipe is None

    def _run_interaction_gen(self, timeline):
        self._set_orderers(self.sim)
        crafter = self.get_crafter_participant()
        if self.favorite_recipe is None:
            self._show_picker_dialog(crafter, target_sim=crafter, order_count=len(self.orderer_ids), crafter=crafter, funds_source=self.funds_source)
            return True
        else:
            return self._push_make_favorite_recipe(crafter=crafter)

    def get_crafter_participant(self):
        crafter = self.get_participant(self.crafter)
        if crafter is None:
            logger.error('Crafter participant is None, this interaction is likely mistuned. \n\tinteraction={} \n\tparticipant_type={}', self, self.crafter, owner='jdimailig')
        if crafter is None:
            return self.sim
        return crafter

    def _get_valid_columns(self, dialog):
        columns_list = dialog.picker_columns
        if not self._suppressed_picker_columns:
            return columns_list
        valid_columns = []
        for column in columns_list:
            if column.column_data_name is not None and column.column_data_name not in self._suppressed_picker_columns:
                valid_columns.append(column)
        return valid_columns

    def _push_make_favorite_recipe(self, orderer=DEFAULT, crafter=DEFAULT, handle_crafting_func=DEFAULT):
        if orderer is DEFAULT:
            orderer = self.sim
        if crafter is DEFAULT:
            crafter = self.sim
        paying_sim = None if self.paying_sim is None else self.get_participant(self.paying_sim)
        favorite_recipe = orderer.sim_info.get_favorite_recipe(self.favorite_recipe.recipe_tags)
        if favorite_recipe is None:
            test_paying_sim = orderer if paying_sim is None else paying_sim
            favorite_recipe = self._pick_random_favorite_recipe(crafter, test_paying_sim)
            if favorite_recipe is None:
                return False
            if self.favorite_recipe.persist_new_favorite_recipe:
                orderer.sim_info.set_favorite_recipe(favorite_recipe)
        if handle_crafting_func is DEFAULT:
            return self._handle_begin_crafting(favorite_recipe, crafter, ordering_sim=orderer, orderer_ids=self.orderer_ids, funds_source=self.funds_source, paying_sim=paying_sim, ingredient_cost_only=self.ingredient_cost_only)
        else:
            return handle_crafting_func(favorite_recipe)

    def _pick_random_favorite_recipe(self, crafter, payer):
        candidate_recipes = []
        for recipe in self.recipes:
            if recipe.use_ingredients is not None:
                pass
            else:
                is_order_interaction = issubclass(type(self), StartCraftingOrderSuperInteraction)
                (discounted_price, bucks_prices) = self._get_recipe_price_discounts(recipe, is_retail=is_order_interaction)
                recipe_test_result = CraftingProcess.recipe_test(self.target, self.context, recipe, crafter, discounted_price, paying_sim=payer, discounted_bucks_prices=bucks_prices)
                if recipe_test_result.visible and not recipe_test_result.errors:
                    candidate_recipes.append(recipe)
        if not candidate_recipes:
            return
        return random.choice(candidate_recipes)

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if not cls.recipes:
            return cls.allow_empty_recipes
        if cls.pie_menu_test_tooltip is None:
            return super().has_valid_choice(target, context, **kwargs)
        orderer = context.sim
        crafter = target if target is not None and target.is_sim else orderer
        if hasattr(cls, 'proxied_affordance'):
            is_order_interaction = issubclass(cls.proxied_affordance, StartCraftingOrderSuperInteraction)
        else:
            is_order_interaction = issubclass(cls, StartCraftingOrderSuperInteraction)
        resolver = cls.get_resolver(target=target, context=context)
        if cls.favorite_recipe is not None:
            favorite_recipe = orderer.sim_info.get_favorite_recipe(cls.favorite_recipe.recipe_tags)
            if favorite_recipe is not None:
                (discounted_price, discounted_bucks_prices) = cls._get_recipe_price_discounts(favorite_recipe, is_retail=is_order_interaction, resolver=resolver)
                return CraftingProcess.recipe_test(target, context, favorite_recipe, crafter, discounted_price, paying_sim=orderer, discounted_bucks_prices=discounted_bucks_prices)
        for recipe in cls.recipes:
            (discounted_price, discounted_bucks_prices) = cls._get_recipe_price_discounts(recipe, is_retail=is_order_interaction, resolver=resolver)
            recipe_test_result = CraftingProcess.recipe_test(target, context, recipe, crafter, discounted_price, paying_sim=orderer, discounted_bucks_prices=discounted_bucks_prices)
            if recipe_test_result.visible and not recipe_test_result.errors:
                return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, crafter=DEFAULT, order_count=1, recipe_ingredients_map=None, funds_source=None, **kwargs):
        crafter = context.sim
        inventory_target = target
        subclass_of_order_interaction = issubclass(cls, StartCraftingOrderSuperInteraction)
        inventory_target = inst.get_participant(participant_type=cls.ingredient_source)
        candidate_ingredients = cls._get_ingredient_candidates(crafter, crafting_target=inventory_target)
        recipe_list = []
        if crafter is DEFAULT and subclass_of_order_interaction and cls.ingredient_source and inst is not None:
            recipe_list = inst.get_valid_recipe_list(crafter=crafter)
            recipes_to_hash = [valid_recipe[1] for valid_recipe in recipe_list]
            resolver = inst.get_resolver()
        else:
            recipe_list = cls.recipes
            recipes_to_hash = recipe_list
            resolver = cls.get_resolver(target=target, context=context)
        is_ingredients_only = cls.ingredient_cost_only
        any_recipe_has_ingredients = False
        hashable_recipe_list = tuple(recipes_to_hash)
        hashable_candidate_ingredients = tuple(candidate_ingredients)
        (recipe_to_requirements_map, requirements_to_candidates_map) = cls._prebuild_recipe_requirement_candidate_maps(hashable_recipe_list, hashable_candidate_ingredients, is_ingredients_only)
        recipe_ingredients_map = {}
        buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
        buff = None
        buff_id = 0
        for recipe_tuple in recipe_list:
            if inst is not None:
                (buff_id, recipe) = recipe_tuple
            else:
                recipe = recipe_tuple
            is_family_recipe = buff_id != 0
            all_ingredients_required = is_ingredients_only or recipe.all_ingredients_required
            requirements_for_recipe = cls._try_build_ingredient_requirements_for_recipe(recipe, recipe_to_requirements_map, requirements_to_candidates_map, crafter, buff_id, candidate_ingredients)
            (only_fresh_ingredients, only_prepped_ingredients, both_fresh_prepped_requirements) = get_ingredient_requirements(requirements_for_recipe, all_ingredients_required)
            recipe_ingredients_map[recipe] = requirements_for_recipe
            (enable_recipe_both_fresh_prepped, _, adjusted_ingredient_price_both_fresh_prepped) = build_requirement_data(both_fresh_prepped_requirements, all_ingredients_required)
            (enable_recipe_only_prepped, _, adjusted_ingredient_price_only_prepped) = build_requirement_data(only_prepped_ingredients, all_ingredients_required)
            (enable_recipe_only_fresh, has_required_ingredients, adjusted_ingredient_price_only_fresh) = build_requirement_data(only_fresh_ingredients, all_ingredients_required)
            if not requirements_for_recipe is not None or recipe.use_ingredients is not None or not is_ingredients_only or (not all_ingredients_required or (has_required_ingredients or not crafter is not context.sim)) or not cls.show_disabled_crafting_recipes:
                pass
            else:
                is_order_interaction = False
                is_order_interaction = True
                (multiplier, discount_tooltip) = cls.price_multiplier.get_multiplier_and_tooltip(resolver)
                (original_price, discounted_price, ingredients_price_both_fresh_prepped) = recipe.get_price(is_order_interaction, adjusted_ingredient_price_both_fresh_prepped, multiplier)
                (_, _, ingredients_price_only_prepped) = recipe.get_price(is_order_interaction, adjusted_ingredient_price_only_prepped, multiplier)
                (_, _, ingredients_price_only_fresh) = recipe.get_price(is_order_interaction, adjusted_ingredient_price_only_fresh, multiplier)
                original_price *= order_count
                discounted_price *= order_count
                ingredients_price_both_fresh_prepped *= order_count
                ingredients_price_only_prepped *= order_count
                ingredients_price_only_fresh *= order_count
                payment_altering_service = services.payment_altering_service()
                retail_payment_multiplier = 1.0
                retail_payment_multiplier = payment_altering_service.get_picker_payment_modifier(context.sim.id, context.sim, target if target.is_sim else crafter)
                original_price = int(original_price*retail_payment_multiplier)
                discounted_price = int(discounted_price*retail_payment_multiplier)
                original_price = discounted_price = 0
                (ingredients_price_both_fresh_prepped, ingredients_price_only_prepped, ingredients_price_only_fresh) = (0, 0, 0)
                discounted_price = ingredients_price_only_fresh
                unresolved_multipliers = cls.bucks_price_multipliers
                resolved_multipliers = {}
                for buck_type in unresolved_multipliers:
                    (bucks_multiplier, bucks_discount_tooltip) = unresolved_multipliers[buck_type].get_multiplier_and_tooltip(resolver)
                    resolved_multipliers[buck_type] = bucks_multiplier
                discounted_bucks_prices = recipe.get_bucks_prices(is_retail=is_order_interaction, multipliers=resolved_multipliers, order_count=order_count)
                BucksCostsData = namedtuple('BucksCostsData', ('bucks_type', 'amount'))
                bucks_costs = []
                for (buck_type, cost_amount) in discounted_bucks_prices.items():
                    costs = BucksCostsData(buck_type, cost_amount)
                    bucks_costs.append(costs)
                funds_source = cls.funds_source
                paying_sim = context.sim
                recipe_test_result_no_ingredients = CraftingProcess.recipe_test(target, context, recipe, crafter, original_price, paying_sim=paying_sim, funds_source=funds_source, discounted_bucks_prices=discounted_bucks_prices, check_price=False, show_recipe_by_skill=is_family_recipe)
                if (not subclass_of_order_interaction or (not cls.ingredient_source or has_required_ingredients) or not is_order_interaction or not payment_altering_service is not None or not is_ingredients_only or not cls.use_ingredients_default_value or funds_source is None) and paying_sim is None and crafter is None and funds_source.funds_source == FundsSource.HOUSEHOLD:
                    pass
                else:
                    recipe_test_result_only_fresh = CraftingProcess.recipe_test_price(recipe_test_result_no_ingredients, recipe, crafter, ingredients_price_only_fresh, paying_sim=paying_sim, funds_source=funds_source, discounted_bucks_prices=discounted_bucks_prices)
                    recipe_test_result_only_prepped = CraftingProcess.recipe_test_price(recipe_test_result_no_ingredients, recipe, crafter, ingredients_price_only_prepped, paying_sim=paying_sim, funds_source=funds_source, discounted_bucks_prices=discounted_bucks_prices)
                    recipe_test_result_both_fresh_prepped = CraftingProcess.recipe_test_price(recipe_test_result_no_ingredients, recipe, crafter, ingredients_price_both_fresh_prepped, paying_sim=paying_sim, funds_source=funds_source, discounted_bucks_prices=discounted_bucks_prices)
                    if recipe_test_result_only_fresh.visible or recipe_test_result_only_prepped.visible or not recipe_test_result_both_fresh_prepped.visible:
                        pass
                    else:
                        row = RecipePickerRow(icon=recipe.icon_override, name=recipe.get_recipe_name(crafter), skill_level=recipe.required_skill_level, linked_recipe=recipe.base_recipe, display_name=recipe.get_recipe_picker_name(crafter), tag=recipe, tag_list=recipe.tuning_tags, mtx_id=recipe.entitlement, subrow_sort_id=recipe.subrow_sort_id, group_recipe_override=recipe.group_recipe_override, linked_recipe_override=recipe.linked_recipe_override, price=original_price, is_enable=recipe_test_result_no_ingredients.enabled and (not all_ingredients_required or enable_recipe_only_fresh), is_enable_fresh=enable_recipe_only_fresh & recipe_test_result_only_fresh.enabled, is_enable_prepped=enable_recipe_only_prepped & recipe_test_result_only_prepped.enabled, is_enable_both_fresh_prepped=enable_recipe_both_fresh_prepped & recipe_test_result_both_fresh_prepped.enabled, price_with_ingredients=ingredients_price_only_fresh, price_with_only_prepped_ingredients=ingredients_price_only_prepped, price_with_both_fresh_prepped_ingredients=ingredients_price_both_fresh_prepped, pie_menu_influence_by_active_mood=recipe_test_result_only_fresh.influence_by_active_mood, discounted_price=discounted_price, bucks_costs=bucks_costs, enable_speed_up_background=recipe.enable_speed_up_background, food_restriction_ingredients=recipe.food_restriction_ingredients, recipe_id=recipe.guid64)
                        buff = buff_manager.get(buff_id)
                        row.buff_id = buff_id
                        cls._add_discount_info_to_recipe_picker_row(row, multiplier, subclass_of_order_interaction, has_required_ingredients)
                        cls._add_cas_info_to_recipe_picker_row(row, recipe, crafter)
                        cls._add_icon_info_to_recipe_picker_row(row, recipe)
                        all_ingredient_requirements = tuple(ingredient_requirement for ingredient_requirement in recipe_ingredients_map.get(recipe, ()))
                        row.both_fresh_prepped_ingredients = [ingredient_requirement.get_display_data() for ingredient_requirement in both_fresh_prepped_requirements]
                        row.only_fresh_ingredients = [ingredient_requirement.get_display_data() for ingredient_requirement in only_fresh_ingredients]
                        row.only_prepped_ingredients = [ingredient_requirement.get_display_data() for ingredient_requirement in only_prepped_ingredients]
                        any_recipe_has_ingredients = True
                        prepped_ingredients_satisfied = False
                        for ingredient_requirement in all_ingredient_requirements:
                            if not ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG) or ingredient_requirement.count_satisfied > 0:
                                prepped_ingredients_satisfied = True
                                break
                        row.cooking_time_reduced = prepped_ingredients_satisfied
                        cls._add_description_and_tooltip_info_to_recipe_picker_row(row, recipe, crafter, multiplier, all_ingredients_required, has_required_ingredients, is_ingredients_only, recipe_test_result_only_fresh, recipe_test_result_only_prepped, recipe_test_result_both_fresh_prepped, discount_tooltip, buff)
                        yield row
        if recipe_ingredients_map is None and inst is not None:
            inst._recipe_ingredients_map = recipe_ingredients_map
            if any_recipe_has_ingredients or RowMapType.INGREDIENTS not in inst._suppressed_picker_columns:
                inst._suppressed_picker_columns.append(RowMapType.INGREDIENTS)

    @staticmethod
    @cached
    def get_requirement_factories_for_recipe(recipe, is_ingredients_only):
        if recipe.use_ingredients is None and not is_ingredients_only:
            return
        else:
            ingredients_requirements_to_use = None
            if is_ingredients_only and recipe.ingredient_cost_only_ingredients is not None:
                ingredients_requirements_to_use = recipe.sorted_ingredients_only_requirements
            elif recipe.use_ingredients is not None:
                ingredients_requirements_to_use = recipe.sorted_ingredient_requirements
            if ingredients_requirements_to_use is None or len(ingredients_requirements_to_use) <= 0:
                logger.warn('{} recipe needs ingredients, but none are tuned.', recipe)
                return
        return ingredients_requirements_to_use

    @staticmethod
    @cached
    def get_valid_ingredients_from_list_for_requirement_factory(requirement_factory, candidate_ingredients):
        ingredients = []
        built_requirement = requirement_factory()
        for candidate in candidate_ingredients:
            if built_requirement.is_valid_ingredient(candidate):
                ingredients.append(candidate)
        return ingredients

    @classmethod
    @cached
    def _prebuild_recipe_requirement_candidate_maps(cls, recipe_list, candidate_ingredients, is_ingredients_only):
        recipe_to_requirements = {}
        requirement_to_ingredients = {}
        for recipe in recipe_list:
            ingredients_requirements_to_use = cls.get_requirement_factories_for_recipe(recipe, is_ingredients_only)
            if ingredients_requirements_to_use is None:
                pass
            else:
                recipe_to_requirements[recipe] = ingredients_requirements_to_use
                for requirement in ingredients_requirements_to_use:
                    if requirement not in requirement_to_ingredients:
                        requirement_to_ingredients[requirement] = []
        for (requirement, ingredients) in requirement_to_ingredients.items():
            ingredients.extend(cls.get_valid_ingredients_from_list_for_requirement_factory(requirement, candidate_ingredients))
        return (recipe_to_requirements, requirement_to_ingredients)

    @staticmethod
    def _try_build_ingredient_requirements_for_recipe(recipe, recipe_to_requirements_map, requirements_to_ingredients_map, crafter=None, buff_id=0, candidate_ingredients=None):
        requirements = []
        if recipe not in recipe_to_requirements_map:
            return requirements
        requirements_factories = recipe_to_requirements_map[recipe]
        ingredients_used = {}
        for tuned_ingredient_factory in requirements_factories:
            candidate_ingredients = requirements_to_ingredients_map.get(tuned_ingredient_factory, [])
            ingredient_requirement = tuned_ingredient_factory()
            ingredient_requirement.attempt_satisfy_ingredients(candidate_ingredients, ingredients_used)
            requirements.append(ingredient_requirement)
        return requirements

    @staticmethod
    def _add_icon_info_to_recipe_picker_row(recipe_picker_row, recipe):
        if recipe.has_final_product_definition:
            recipe_icon = IconInfoData(icon_resource=recipe.icon_override, obj_def_id=recipe.final_product_definition_id, obj_geo_hash=recipe.final_product_geo_hash, obj_material_hash=recipe.final_product_material_hash)
        else:
            recipe_icon = IconInfoData(recipe.icon_override)
        recipe_picker_row.icon_info = recipe_icon

    @classmethod
    def _add_description_and_tooltip_info_to_recipe_picker_row(cls, recipe_picker_row, recipe, crafter, original_cost_multiplier, all_ingredients_required, has_required_ingredients, is_ingredients_only, recipe_test_result_fresh, recipe_test_result_prepped, recipe_test_result_both_fresh_prepped, discount_tooltip, buff=None):

        def get_tooltip_data(ingredients, recipe_test_result, use_prepped_ingredients=False):
            ingredient_comma_list = None
            if recipe_test_result.errors:
                if len(recipe_test_result.errors) > 1:
                    localized_error_string = LocalizationHelperTuning.get_bulleted_list((None,), recipe_test_result.errors)
                else:
                    localized_error_string = recipe_test_result.errors[0]
                description = cls.create_unavailable_recipe_description(localized_error_string)
                tooltip = lambda *_, **__: cls.create_unavailable_recipe_description(localized_error_string)
            else:
                description = recipe.recipe_description(crafter)
                if (recipe.use_ingredients is not None or is_ingredients_only) and ingredients is not None:
                    tooltip_ingredients = [ingredient.ingredient_name for ingredient in ingredients]
                    ingredients_list_string = LocalizationHelperTuning.get_bulleted_list((None,), tooltip_ingredients)
                    ingredient_comma_list = LocalizationHelperTuning.get_comma_separated_list(*tooltip_ingredients)
                    tooltip = None
                    if all_ingredients_required:
                        if len(recipe_picker_row.both_fresh_prepped_ingredients) != 0:
                            tooltip = functools.partial(IngredientTuning.REQUIRED_INGREDIENT_LIST_STRING, ingredients_list_string)
                        if not has_required_ingredients:
                            tooltip_style = None
                            if is_ingredients_only and recipe.ingredient_cost_only_ingredients is not None:
                                tooltip_style = recipe.ingredient_cost_only_ingredients.missing_ingredient_tooltip_style
                            elif recipe.use_ingredients is not None:
                                tooltip_style = recipe.use_ingredients.missing_ingredient_tooltip_style
                            if tooltip_style == IngredientTooltipStyle.DEFAULT_MISSING_INGREDIENTS:
                                description = IngredientTuning.REQUIRED_INGREDIENT_LIST_STRING(ingredients_list_string)
                    elif len(ingredients) != 0:
                        tooltip = functools.partial(IngredientTuning.OPTIONAL_INGREDIENT_LIST_STRING, ingredients_list_string)
                    if tooltip is not None:
                        if use_prepped_ingredients and recipe.enable_speed_up_background:
                            cooking_time_reduced_text = Recipe.cooking_time_reduced_inactive_text
                            if recipe_picker_row.cooking_time_reduced:
                                cooking_time_reduced_text = Recipe.cooking_time_reduced_text
                            if recipe.recipe_description:
                                text = sims4.localization.LocalizationHelperTuning.get_new_line_separated_strings(recipe.recipe_description(crafter), tooltip(), cooking_time_reduced_text())
                            else:
                                text = sims4.localization.LocalizationHelperTuning.get_new_line_separated_strings(tooltip(), cooking_time_reduced_text())
                            tooltip = functools.partial(sims4.localization.LocalizationHelperTuning.RAW_TEXT, text)
                        elif recipe.recipe_description:
                            tooltip = functools.partial(sims4.localization.LocalizationHelperTuning.RAW_TEXT, sims4.localization.LocalizationHelperTuning.get_new_line_separated_strings(recipe.recipe_description(crafter), tooltip()))
                    else:
                        tooltip = functools.partial(recipe.recipe_description, crafter)
                else:
                    tooltip = functools.partial(recipe.recipe_description, crafter)
            if discount_tooltip is not None:
                tooltip = discount_tooltip
            if original_cost_multiplier != 1 and buff is not None:
                text = sims4.localization.LocalizationHelperTuning.get_new_line_separated_strings(tooltip(), FamilyRecipesTuning.FAMILY_RECIPE_NOTEBOOK_DATA.family_recipe_notebook_text.buff_notebook_text(), buff.buff_type.buff_name())
                tooltip = functools.partial(sims4.localization.LocalizationHelperTuning.RAW_TEXT, text)
            return (tooltip, description, ingredient_comma_list)

        (recipe_picker_row.row_tooltip, recipe_picker_row.row_description, recipe_picker_row.ingredients_list) = get_tooltip_data(recipe_picker_row.only_fresh_ingredients, recipe_test_result_fresh)
        (recipe_picker_row.tooltip_only_prepped, recipe_picker_row.description_only_prepped, recipe_picker_row.ingredients_list_only_prepped) = get_tooltip_data(recipe_picker_row.only_prepped_ingredients, recipe_test_result_prepped, use_prepped_ingredients=True)
        (recipe_picker_row.tooltip_both_fresh_prepped, recipe_picker_row.description_both_fresh_prepped, recipe_picker_row.ingredients_list_both_fresh_prepped) = get_tooltip_data(recipe_picker_row.both_fresh_prepped_ingredients, recipe_test_result_both_fresh_prepped, use_prepped_ingredients=True)

    @classmethod
    def _add_discount_info_to_recipe_picker_row(cls, recipe_picker_row, original_cost_multiplier, subclass_of_order_interaction, has_required_ingredients):
        if original_cost_multiplier != 1:
            recipe_picker_row.is_discounted = True
        else:
            is_order_interaction_with_source_and_ingredients = subclass_of_order_interaction and (cls.ingredient_source and has_required_ingredients)
            is_start_interaction_with_ingredients = not subclass_of_order_interaction and (issubclass(cls, StartCraftingSuperInteraction) and has_required_ingredients)
            recipe_picker_row.is_discounted = is_order_interaction_with_source_and_ingredients or is_start_interaction_with_ingredients

    @classmethod
    def _add_cas_info_to_recipe_picker_row(cls, recipe_picker_row, recipe, crafter):
        stored_cas_parts = recipe.final_product.stored_cas_parts
        locked_in_cas_icon = None
        if stored_cas_parts:
            household = crafter.household
            sim_id = crafter.id if crafter is not None else None
            if all(household.part_in_reward_inventory(stored_cas_part, sim_id) for stored_cas_part in stored_cas_parts):
                locked_in_cas_icon = cls.CAS_UNLOCKED_ICON
            else:
                locked_in_cas_icon = cls.CAS_LOCKED_ICON
        recipe_picker_row.locked_in_cas_icon = locked_in_cas_icon

    def _setup_dialog(self, dialog, crafter=DEFAULT, order_count=1, **kwargs):
        crafter = self.sim if crafter is DEFAULT else crafter
        dialog.set_target_sim(crafter)
        for row in self.picker_rows_gen(self.target, self.context, crafter=crafter, order_count=order_count, **kwargs):
            dialog.add_row(row)
        dialog.set_picker_columns_override(self._get_valid_columns(dialog=dialog))

    def on_choice_selected(self, choice_tag, ingredient_data=None, ingredient_check=None, prepped_ingredient_check=None, defined_ingredients=None, extra_cost=0, crafting_target=None, family_recipe=None, **kwargs):
        recipe = choice_tag
        if recipe is not None:
            ingredients = None
            recipe_requires_ingredients = (recipe.all_ingredients_required if recipe.use_ingredients is not None else False) or self.ingredient_cost_only
            if ingredient_check or (prepped_ingredient_check or self.use_ingredients_default_value) or recipe_requires_ingredients:
                if self._recipe_ingredients_map is not None:
                    ingredients = self._recipe_ingredients_map.get(recipe)
                else:
                    ingredients = ingredient_data.get(recipe)
            if defined_ingredients is not None:
                ingredients = defined_ingredients
            elif ingredient_check and prepped_ingredient_check:
                ingredients = get_ingredient_requirements_both_fresh_and_prepped(ingredients)
            elif prepped_ingredient_check:
                ingredients = get_ingredient_requirements_only_prepped(ingredients, recipe_requires_ingredients)
            elif ingredient_check or recipe_requires_ingredients:
                ingredients = get_ingredient_requirements_only_fresh(ingredients)
            if family_recipe is not None:
                ingredients = add_new_ingredient_requirement(ingredients, family_recipe.ingredient_id)
            paying_sim = None if self.paying_sim is None else self.get_participant(self.paying_sim)
            return self._handle_begin_crafting(recipe, self.get_crafter_participant(), orderer_ids=self.orderer_ids, ingredients=ingredients, funds_source=self.funds_source, paying_sim=paying_sim, ingredient_cost_only=self.ingredient_cost_only, use_fresh_ingredients=ingredient_check, use_prepped_ingredients=prepped_ingredient_check, defined_ingredients=defined_ingredients, extra_cost=extra_cost, crafting_target=crafting_target, family_recipe=family_recipe)
        return EnqueueResult.NONE

class StartCraftingOrderHandler:

    def __init__(self, orderer, crafter, start_crafting_si, funds_source=None):
        self._orderer = orderer
        self._crafter = crafter
        self._process = None
        self._start_crafting_si = start_crafting_si
        self._funds_source = funds_source

    def clear(self):
        self._orderer = None
        self._crafter = None
        self._process = None
        self._start_crafting_si = None
        self._funds_source = None

    def get_existing_order(self, recipe):

        def is_crafting_interaction(interaction):
            if not isinstance(interaction, CraftingPhaseSuperInteractionMixin):
                return False
            if not interaction.phase.allows_multiple_orders:
                return False
            elif interaction.recipe.serve_affordance is not recipe.serve_affordance:
                return False
            return True

        for interaction in self._crafter.si_state:
            if is_crafting_interaction(interaction):
                return interaction
        for interaction in self._crafter.queue:
            if is_crafting_interaction(interaction):
                return interaction

    def push_wait_for_order(self, crafting_si):

        def exit_wait_for_order():
            if self._process is not None:
                self._process.remove_order(self._orderer)
            self.clear()

        if self._start_crafting_si.immediate:
            context = self._start_crafting_si.context.clone_from_immediate_context(self._start_crafting_si)
        else:
            context = self._start_crafting_si.context.clone_for_continuation(self._start_crafting_si)
        result = self._orderer.push_super_affordance(self._start_crafting_si.order_wait_affordance, self._crafter, context, exit_functions=(exit_wait_for_order,), depended_on_si=self._start_crafting_si.depended_on_si)
        if result:
            liability = crafting_si.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY)
            if liability is None:
                liability = CancelInteractionsOnExitLiability()
                crafting_si.add_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY, liability)
            liability.add_cancel_entry(self._orderer, result.interaction)
        else:
            self.clear()
            logger.error('Failed to push wait for drink: {}', result)
        return result

    def start_order_affordance(self, recipe):

        def place_order():
            depended_on_si = self._start_crafting_si.depended_on_si
            if depended_on_si is None or not depended_on_si.has_been_canceled:
                self.place_order_for_recipe(recipe)

        result = self._orderer.push_super_affordance(self._start_crafting_si.order_craft_affordance, self._crafter, self._start_crafting_si.context, depended_on_si=self._start_crafting_si.depended_on_si, exit_functions=(place_order,))
        if not result:
            self.clear()
        return result

    def place_order_for_recipe(self, recipe):
        if self._crafter is None:
            return EnqueueResult(TestResult.NONE, ExecuteResult.NONE)
        if not self._crafter.is_simulating:
            return EnqueueResult(TestResult.NONE, ExecuteResult.NONE)
        crafting_si = self.get_existing_order(recipe)
        result = False
        if crafting_si is not None:
            for sim_id in self._start_crafting_si.orderer_ids:
                crafting_si.process.add_order(sim_id, recipe)
            self._process = crafting_si.process
            result = self.push_wait_for_order(crafting_si)
        elif self._start_crafting_si._handle_begin_crafting(recipe, self._crafter, ordering_sim=self._orderer, orderer_ids=self._start_crafting_si.orderer_ids, funds_source=self._funds_source, ingredient_cost_only=self._start_crafting_si.ingredient_cost_only):
            crafting_si = self.get_existing_order(recipe)
            if crafting_si is not None:
                self._process = crafting_si.process
                result = self.push_wait_for_order(crafting_si)
        if not result:
            self.clear()
        return result

class StartCraftingOrderSuperInteraction(StartCraftingSuperInteraction):
    INSTANCE_TUNABLES = {'crafter': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'order_craft_affordance': TunableReference(description='\n            The affordance used to order the chosen craft\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'order_wait_affordance': TunableReference(description='\n            The affordance used to wait for an ordered craft\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'tooltip_crafting_almost_done': OptionalTunable(description='\n            If enabled and the crafter is crafting a recipe on its final\n            phase, the order will be greyed out with this tooltip.\n            ', tunable=TunableLocalizedStringFactory(description='"\n                Grayed-out tooltip message when another order can\'t be added because the crafter is almost done.\n                ', default=1860708663), enabled_name='tooltip', disabled_name='hidden'), 'ingredient_source': OptionalTunable(description='\n            The ingredient source from which to get crafting ingredients from.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor))}

    @classmethod
    def _test(cls, target, context, **kwargs):
        test_result = super()._test(target, context, **kwargs)
        if not test_result:
            return test_result
        who = cls.get_participant(participant_type=cls.crafter, sim=context.sim, target=target)
        if who is None:
            return TestResult(False, 'Crafter Participant is None. Check tuning.')
        if not who.is_sim:
            return TestResult(False, 'Crafter Participant is not a Sim. Check tuning.')
        if who.is_being_destroyed:
            return TestResult(False, 'Crafter Participant is being destroyed.')
        for interaction in who.si_state:
            if not interaction.phase.allows_multiple_orders:
                return TestResult(False, "The crafter is in a phase doesn't allow multiple orders.")
            if isinstance(interaction, CraftingPhaseSuperInteractionMixin) and interaction.process.is_last_phase:
                return TestResult(False, 'The crafter is almost done.', tooltip=cls.tooltip_crafting_almost_done)
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline):
        self._set_orderers(self.sim)
        crafter = self.get_participant(self.crafter, target=self.target)
        if self.favorite_recipe is None:
            self._show_picker_dialog(self.sim, target_sim=crafter, order_count=len(self.orderer_ids), crafter=crafter)
            return True
        crafter = self.get_participant(self.crafter, target=self.target)
        start_crafting_handler = StartCraftingOrderHandler(self.sim, crafter, self, funds_source=self.funds_source)
        return self._push_make_favorite_recipe(orderer=self.sim, crafter=crafter, handle_crafting_func=start_crafting_handler.start_order_affordance)

    def on_choice_selected(self, choice_tag, **kwargs):
        recipe = choice_tag
        if recipe is None:
            return
        crafter = self.get_participant(self.crafter, target=self.target)
        start_crafting_handler = StartCraftingOrderHandler(self.sim, crafter, self, funds_source=self.funds_source)
        start_crafting_handler.start_order_affordance(recipe)
lock_instance_tunables(StartCraftingOrderSuperInteraction, basic_reserve_object=None)
class StartGroupCraftingSuperInteraction(StartCraftingSuperInteraction):
    INSTANCE_TUNABLES = {'group_crafting_situation': TunableReference(description='\n            The situation to start to actual handle crafting.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))}

    def _handle_begin_crafting(self, recipe, crafter, ordering_sim=None, crafting_target=None, orderer_ids=DEFAULT, ingredients=(), funds_source=None, paying_sim=None, ingredient_cost_only=False, situation_id=None, **kwargs):
        if self.context.pick is not None:
            original_target = self.context.pick.target
        else:
            original_target = self.target
        situation_manager = services.get_zone_situation_manager()
        guest_list = SituationGuestList(host_sim_id=crafter.sim_id, invite_only=False)
        guest_list.add_guest_info(SituationGuestInfo(crafter.sim_id, self.group_crafting_situation.head_crafter, RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_HOSTING, expectation_preference=True))
        for sim_id in self.interaction_parameters['picked_item_ids']:
            guest_list.add_guest_info(SituationGuestInfo(sim_id, self.group_crafting_situation.other_crafters, RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        situation_manager.create_situation(self.group_crafting_situation, guest_list=guest_list, user_facing=False, start_crafting_interaction=type(self), target=original_target, recipe=recipe, ordering_sim=ordering_sim, crafting_target=crafting_target, orderer_ids=orderer_ids, ingredients=ingredients, funds_source=funds_source, paying_sim=paying_sim, ingredient_cost_only=ingredient_cost_only)
        return EnqueueResult.NONE

class SituationStartGroupCraftingInteraction(StartCraftingMixin, ImmediateSuperInteraction):
    REMOVE_INSTANCE_TUNABLES = ('check_target_inventory', 'check_sim_inventory', 'check_fridge_shared_inventory', 'set_target_as_current_ico')

    @property
    def check_target_inventory(self):
        return self.interaction_parameters['start_crafting_interaction'].check_target_inventory

    @property
    def check_sim_inventory(self):
        return self.interaction_parameters['start_crafting_interaction'].check_sim_inventory

    @property
    def check_fridge_shared_inventory(self):
        return self.interaction_parameters['start_crafting_interaction'].check_fridge_shared_inventory

    @property
    def set_target_as_current_ico(self):
        return self.interaction_parameters['start_crafting_interaction'].set_target_as_current_ico

    @property
    def price_multiplier(self):
        return self.interaction_parameters['start_crafting_interaction'].price_multiplier

    @property
    def bucks_price_multipliers(self):
        return self.interaction_parameters['start_crafting_interaction'].bucks_price_multipliers

    def _run_interaction_gen(self, timeline):
        self._handle_begin_crafting(self.interaction_parameters['recipe'], self.interaction_parameters['crafter'], ordering_sim=self.interaction_parameters['ordering_sim'], crafting_target=self.interaction_parameters['crafting_target'], orderer_ids=self.interaction_parameters['orderer_ids'], ingredients=self.interaction_parameters['ingredients'], funds_source=self.interaction_parameters['recipe_funds_source'], paying_sim=self.interaction_parameters['paying_sim'], ingredient_cost_only=self.interaction_parameters['ingredient_cost_only'], situation_id=self.interaction_parameters['situation_id'])

class StartCraftingAutonomouslySuperInteraction(StartCraftingMixin, AutonomousPickerSuperInteraction):
    INSTANCE_TUNABLES = {'recipes': TunableList(description='\n            The recipes a Sim can craft.\n            ', tunable=TunableReference(description='\n                Recipe to craft.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), pack_safe=True, reload_dependent=True)), 'test_reserve_object': TunableReserveObject(description="\n            The reservation type to use when testing for this interaction's\n            autonomous availability.\n            "), 'craft_for_other_sims': TunableVariant(description='\n            Options for crafting this drink for other sims.\n            ', no_other_sims=TunableTuple(description="\n                Don't craft this for any other sims.\n                ", locked_args={'option': NO_OTHER_SIMS}), party_crafting=TunableTuple(description='\n                Craft for all for the Sims in a rally source.\n                ', rally_source=TunableEnumSet(description='\n                    A list of different sources that we want to use to figure\n                    out the Sims to craft drinks for.\n                    ', enum_type=RallySource, enum_default=RallySource.ENSEMBLE, default_enum_list=frozenset((RallySource.ENSEMBLE,))), locked_args={'option': PARTY_CRAFTING}), craft_for_specific_participant=TunableTuple(description='\n                Craft for the Sim of a specific participant type. \n                ', participant=TunableEnumEntry(description='\n                    The specific participant that we want to craft for. \n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.PickedSim), locked_args={'option': CRAFT_FOR_SPECIFIC_PARTICIPANT}), default='no_other_sims'), 'price_multiplier': TunableMultiplier.TunableFactory(description='\n            Tested multipliers to apply to the price of the item.\n            '), 'bucks_price_multipliers': TunableMapping(description='\n            Mapping of buck type to tested multiplier to apply to the bucks price\n            of the item.\n            ', key_type=TunableEnumEntry(description='\n                Buck type to apply price multiplier to.\n                ', tunable_type=BucksType, default=BucksType.INVALID), value_type=TunableMultiplier.TunableFactory(description='\n                Tested multipliers to apply to the bucks price of the item.\n                '), tuning_group=GroupNames.PICKERTUNING), 'funds_source': get_tunable_payment_source_variant(description='\n            When deducting the cost of the recipe, it will be deducted \n            from this funds source.\n            '), 'ingredient_cost_only': Tunable(description='\n            If true, this interaction will require ingredients for all recipes and not have a simoleon cost.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        for recipe in cls.recipes:
            recipe.validate_for_start_crafting()

    @classmethod
    def _test(cls, target, context, **kwargs):
        if target is not None:
            targets = (target,) if not target.parts else [part for part in target.parts if part.supports_affordance(cls)]
            for target in targets:
                reservation_handler = cls.test_reserve_object(context.sim, cls, reserve_target=target)
                if reservation_handler.may_reserve(context=context):
                    break
            return TestResult(False, 'Object {} is in use, cannot autonomously used by sim {}', target, context.sim)
        return cls._autonomous_test(target, context, context.sim)

    @classmethod
    def _autonomous_test(cls, target, context, who):
        food_restriction_tracker = who.sim_info.food_restriction_tracker
        candidate_ingredients = cls._get_ingredient_candidates(who, crafting_target=target)
        for recipe in cls.recipes:
            if food_restriction_tracker is not None and food_restriction_tracker.recipe_has_restriction(recipe):
                pass
            else:
                result = CraftingProcess.recipe_test(target, context, recipe, who, 0, build_error_list=False, from_autonomy=True, check_bucks_costs=False)
                if cls.ingredient_cost_only and not recipe.all_ingredients_available(candidate_ingredients, cls.ingredient_cost_only):
                    pass
                elif result:
                    return TestResult.TRUE
        return TestResult(False, 'There are no autonomously completable recipes.')

    @classmethod
    def get_situation_score(cls, sim):
        (situation, score) = super().get_situation_score(sim)
        if situation is not None:
            return (situation, score)
        for recipe in cls.recipes:
            if recipe.final_product.definition is not None:
                (situation, score) = services.get_zone_situation_manager().get_situation_score_for_action(sim, object_def=recipe.final_product.definition)
                if situation is not None:
                    return (situation, score)
        return (None, None)

    @property
    def create_target(self):
        if self.recipes:
            first_phases = self.recipes[0].first_phases
            if first_phases:
                first_phase = first_phases[0]
                if hasattr(first_phase, 'factory'):
                    object_info = first_phase.factory._object_info
                object_info = first_phase.object_info
                if object_info is not None:
                    return object_info.definition
        return super().create_target

    def _run_interaction_gen(self, timeline):
        self._set_orderers(self.sim)
        candidate_ingredients = self._get_ingredient_candidates(self.sim, crafting_target=self.target)
        valid_recipes_tuple = self.get_valid_recipe_list(candidate_ingredients=candidate_ingredients, ingredient_cost_only=self.ingredient_cost_only)
        valid_recipes = [valid_recipe[1] for valid_recipe in valid_recipes_tuple]
        recipe = self.find_best_recipe(valid_recipes)
        if recipe is None:
            return False
        return self._handle_begin_crafting(recipe, self.sim, orderer_ids=self.orderer_ids, funds_source=self.funds_source, ingredient_cost_only=self.ingredient_cost_only)

class StartCraftingOrderAutonomouslySuperInteraction(StartCraftingAutonomouslySuperInteraction):
    INSTANCE_TUNABLES = {'crafter': TunableEnumEntry(ParticipantType, ParticipantType.Object, description='Who or what to apply this test to'), 'order_craft_affordance': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), description='The affordance used to order the chosen craft'), 'order_wait_affordance': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), description='The affordance used to wait for an ordered craft'), 'tooltip_crafting_almost_done': OptionalTunable(description="\n            If enabled and the crafter is crafting a recipe on it's final\n            phase, the order will be greyed out with this tooltip.\n            ", tunable=TunableLocalizedStringFactory(description='"\n                Grayed-out tooltip message when another order can\'t be added because the crafter is almost done.\n                ', default=1860708663), enabled_name='tooltip', disabled_name='hidden')}

    @classmethod
    def _test(cls, target, context, **kwargs):
        crafter = cls.get_participant(participant_type=cls.crafter, sim=context.sim, target=target)
        test_result = cls._autonomous_test(target, context, crafter)
        if not test_result:
            return test_result
        for interaction in crafter.si_state:
            if isinstance(interaction, CraftingPhaseSuperInteractionMixin) and interaction.phase.allows_multiple_orders:
                tooltip = None
                if cls.tooltip_crafting_almost_done is not None:
                    tooltip = cls.create_localized_string(cls.tooltip_crafting_almost_done, target=target, context=context)
                return TestResult(False, 'The crafter is almost done.', tooltip=tooltip)
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline):
        self._set_orderers(self.sim)
        valid_recipes_tuple = self.get_valid_recipe_list()
        valid_recipes = [valid_recipe[1] for valid_recipe in valid_recipes_tuple]
        recipe = self.find_best_recipe(valid_recipes)
        if recipe is None:
            return False
        crafter = self.get_participant(self.crafter, target=self.target)
        start_crafting_handler = StartCraftingOrderHandler(self.sim, crafter, self, funds_source=self.funds_source)
        start_crafting_handler.start_order_affordance(recipe)
        return True

class CraftingResumeInteraction(SuperInteraction):
    CRAFTING_RESUME_INTERACTION = TunableReference(description='\n        A Tunable Reference to the CraftingResumeInteraction for interaction\n        save/load to reference in order to resume crafting interactions.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='CraftingResumeInteraction')
    INSTANCE_TUNABLES = {'create_unavailable_recipe_description': TunableLocalizedStringFactory(default=4228422038, tuning_group=GroupNames.UI), 'resume_phase_name': TunableEnumEntry(PhaseName, None, description='The name of the phase to resume for this certain resume interaction. None means starts at current phase.')}

    def _run_interaction_gen(self, timeline):
        if self.sim is None:
            logger.error('Sim resume does not exist and will not be able to set owner of the completed recipe: {}', self.process.recipe.__name__)
            return False
        self.process.change_crafter(self.sim)
        if self.resume_phase_name is not None:
            resume_phase = self.process.get_phase_by_name(self.resume_phase_name)
            if resume_phase is None:
                logger.error("Try to resume phase {} which doesn't exist in recipe {}", self.resume_phase_name, self.process.recipe.__name__)
                return False
            self.process.send_process_update(self, increment_turn=False)
            return self.process.push_si_for_current_phase(self, next_phases=[resume_phase])
        curr_phase = self.process.phase
        if curr_phase is None:
            logger.error('Trying to resume a crafting interaction that is finished.')
            return False
        if curr_phase.super_affordance is None:
            logger.error("{} doesn't have a tuned super affordance in stage {}", self.process.recipe.__name__, type(curr_phase).__name__)
            return False
        self.process.send_process_update(self, increment_turn=False)
        return self.process.push_si_for_current_phase(self, from_resume=curr_phase.repeat_on_resume)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        process = inst_or_cls.get_process(target=target)
        if process is None:
            target = inst.target if target is DEFAULT else target
            if target is None:
                logger.error('Trying to create display name for {} with None target.', inst_or_cls, owner='jjacobson')
            elif not target.has_component(CRAFTING_COMPONENT):
                logger.error('Trying to create display name for {} with target {} that has no Crafting Component', inst_or_cls, target, owner='jjacobson')
            else:
                logger.error('Trying to create display name for {} with target {} that has no crafting process.', inst_or_cls, target, owner='jjacobson')
            return
        create_display_name = inst_or_cls.display_name
        return create_display_name(process.recipe.get_recipe_name(process.crafter))

    @flexmethod
    def get_process(cls, inst, target=DEFAULT):
        target = inst.target if target is DEFAULT else target
        if target is not None and target.has_component(CRAFTING_COMPONENT):
            return target.get_crafting_process()

    @property
    def process(self):
        return self.get_process()

    @classmethod
    def _test(cls, target, context, **kwargs):
        process = cls.get_process(target=target)
        if process is None:
            return TestResult(False, 'No crafting process on target.')
        if process.recipe.resumable_by_different_sim or process.crafter is not context.sim:
            return TestResult(False, "This sim can't resume crafting this target")
        result = process.resume_test(target, context)
        if not result:
            return result
        result = CraftingProcess.recipe_test(target, context, process.recipe, context.sim, 0, first_phase=process.phase, from_resume=True, check_bucks_costs=False)
        if result:
            return TestResult.TRUE
        error_tooltip = None
        if result.errors:
            if len(result.errors) > 1:
                localized_error_string = LocalizationHelperTuning.get_bulleted_list((None,), result.errors)
            else:
                localized_error_string = result.errors[0]
            error_tooltip = lambda *_, **__: cls.create_unavailable_recipe_description(localized_error_string)
        return TestResult(False, 'Recipe is not completable.', tooltip=error_tooltip)

class CraftingInteractionMixin:
    handles_go_to_next_recipe_phase = True

    @flexmethod
    def get_participants(cls, inst, participant_type:'ParticipantType', sim=DEFAULT, target=DEFAULT, **interaction_parameters) -> 'set':
        result = super(CraftingInteractionMixin, inst if inst is not None else cls).get_participants(participant_type, sim=sim, target=target, **interaction_parameters)
        result = set(result)
        if participant_type & ParticipantType.CraftingProcess:
            if inst is not None:
                result.add(inst.process)
            else:
                process = interaction_parameters.get('crafting_process', None)
                if process is not None:
                    result.add(process)
        if inst is not None:
            if inst.process is not None and inst.process.current_ico is not None:
                result.add(inst.process.current_ico)
        else:
            process = interaction_parameters.get('crafting_process', None)
            if process is not None and process.current_ico is not None:
                result.add(process.current_ico)
        return tuple(result)

    @property
    def carry_target(self):
        carry_target = super().carry_target
        if carry_target is not None:
            return carry_target
        else:
            ico = self.process.current_ico
            if ico is not None and ico.set_ico_as_carry_target:
                return ico

    def send_progress_bar_message(self, **_):
        self.process.send_process_update(self, increment_turn=False)

class CraftingMixerInteractionMixin(CraftingInteractionMixin):

    @property
    def phase(self) -> 'Phase':
        return self.super_interaction.phase

    @property
    def process(self) -> 'CraftingProcess':
        return self.super_interaction.process

    @property
    def recipe(self) -> 'Recipe':
        return self.super_interaction.recipe

class CraftingStepInteraction(CraftingMixerInteractionMixin, MixerInteraction):
    INSTANCE_TUNABLES = {'skill_offset': Tunable(int, 0, description='Skill offset for procedural animations.  Used to determine which animations to pull from the recipe animation lists when procedural animations is selected.'), 'go_to_next_phase': Tunable(bool, False, description='Set to true if selecting this mixer interaction will push the next phase in the cooking process')}

    def _pre_perform(self):
        if self.phase.anim_overrides is not None:
            self.anim_overrides = self.phase.anim_overrides
            logger.info('Setting recipe phase animation overrides on {}', self, owner='rmccord')
        result = super()._pre_perform()
        return result

    def _do_perform_gen(self, timeline):
        result = yield from super()._do_perform_gen(timeline)
        if result:
            if self.go_to_next_phase or self.process.should_go_to_next_phase_on_mixer_completion:
                self.super_interaction._go_to_next_phase()
            crafting_liability = self.super_interaction.get_liability(CRAFTING_QUALITY_LIABILITY)
            if crafting_liability is not None and self.phase.progress_based:
                crafting_liability.send_quality_update()
            self.process.send_process_update(self.super_interaction)
        return result

class CraftingPhaseSuperInteractionMixin(CraftingInteractionMixin):
    INSTANCE_TUNABLES = {'crafting_type_requirement': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=CraftingObjectType, allow_none=True, description="This specifies the crafting object type that is required for this interaction to work.This allows the crafting system to know what type of object the SI was expecting when it can't find that SI."), 'force_final_product': Tunable(description="\n            Whether or not to force the final product to set as a result of this interaction completing.  \n            Normally this is governed by the phase when a crafting process is transferred to an ICO or creation of the \n            final product.\n              \n            Set this to true in cases where this doesn't make sense.\n            \n            e.g. Crafting on a cauldron places the process early on the cauldron which starts out as an ICO, \n            but at the completion of the last crafting SI, the cauldron itself 'becomes' a the final product.\n            ", tunable_type=bool, default=False), 'destroy_ico_object_if_reset': Tunable(description='\n            If this is enabled and the sim is reset while they are performing \n            this interaction, we will destroy the ico object and end the\n            crafting process. We should use this in cases where the ICO object\n            cannot be safely reset. This will also refund the household.\n            ', tunable_type=bool, default=False), 'stop_other_sims_crafting': Tunable(description='\n            If this crafting interaction is being run as part of group crafting\n            then we will inform the situation that we would like the helping\n            crafters to stop.  Example: When the sim transitions off the counter\n            to putting the items in the stove the other sims helping craft\n            should no longer be running interactions on the counters chopping\n            food.\n            ', tunable_type=bool, default=False)}
    _object_info = None

    def __init__(self, *args, crafting_process, phase, **kwargs):
        self.process = crafting_process
        self.phase = phase
        self._went_to_next_phase_or_finished_crafting = False
        self._pushed_cancel_replacement_aop = False
        self._cancel_phase_ran = False
        super().__init__(*args, crafting_process=crafting_process, phase=phase, **kwargs)
        self.add_exit_function(self._maybe_push_cancel_phase_exit_behavior)

    def on_reset(self):
        if self.destroy_ico_object_if_reset:
            ico_object = self.process.current_ico
            if ico_object is not None:
                ico_object.make_transient()
                self.process.refund_payment(explicit=True)
        super().on_reset()

    def is_guaranteed(self):
        return not self.has_active_cancel_replacement

    @classmethod
    def _test(cls, target, context, *args, **kwargs):
        result = super()._test(target, context, *args, **kwargs)
        if not result:
            return result
        return TestResult.TRUE

    @property
    def recipe(self) -> 'Recipe':
        return self.process.recipe

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        target = inst.carry_target if target is DEFAULT else target
        return inst.create_localized_string(inst.phase.interaction_name, target=target, **kwargs)

    @property
    def object_info(self):
        if self._object_info is not None:
            return self._object_info
        return self.phase.object_info

    @property
    def create_target(self):
        if self.object_info is None:
            return
        return self.object_info.definition

    @property
    def auto_goto_next_phase(self):
        return True

    @flexproperty
    def advance_phase_on_resume(cls, inst):
        return False

    def _maybe_push_cancel_phase_exit_behavior(self):
        self._maybe_push_cancel_phase()
        return True

    def _maybe_push_cancel_phase(self):
        if self.process.cancel_crafting(self):
            self._cancel_phase_ran = True
            self._went_to_next_phase_or_finished_crafting = True
            self._pushed_cancel_replacement_aop = True
        return self._pushed_cancel_replacement_aop

    def _try_exit_via_cancel_aop(self, carry_cancel_override=None, **kwargs):
        if self._maybe_push_cancel_phase():
            return False
        return super()._try_exit_via_cancel_aop(carry_cancel_override=carry_cancel_override, **kwargs)

    def _go_to_next_phase(self, completing_interaction=None):
        if self._cancel_phase_ran:
            return False
        else:
            if not self.will_exit:
                self.completed_by_mixer()
            if self.process.increment_phase(interaction=completing_interaction):
                if self.process.push_si_for_current_phase(self):
                    self._went_to_next_phase_or_finished_crafting = True
                    self.process.send_process_update(self)
                    return True
                return False
        return False
        if self.created_target is not None:
            self.created_target.on_crafting_process_finished()
            if self.context.pick is not None:
                original_target = self.context.pick.target
            else:
                original_target = self.target
            if original_target is not None and (original_target.has_component(CRAFTING_COMPONENT) and hasattr(self, 'remove_crafting_component_on_end')) and self.remove_crafting_component_on_end:
                original_target.remove_component(CRAFTING_COMPONENT)
        elif self.process.current_ico is not None:
            self.process.current_ico.on_crafting_process_finished()
        self._went_to_next_phase_or_finished_crafting = True
        return True

    def should_push_consume(self, check_phase=True, from_exit=True):
        if self.recipe.push_consume:
            if self.consume_object is None or not self.consume_object.valid_for_distribution:
                return False
            phase_complete = True
            if check_phase:
                last_phase_valid = self.process.is_last_phase and (self.process.is_single_phase_process or not from_exit)
                phase_complete = self.process.is_complete or last_phase_valid
            if self.uncanceled:
                if self.recipe.push_consume_threshold is not None:
                    commodity_value = self.sim.commodity_tracker.get_value(self.recipe.push_consume_threshold.commodity)
                    if self.recipe.push_consume_threshold.threshold.compare(commodity_value):
                        return True
                else:
                    return True
        return False

    @property
    def consume_object(self):
        if self.created_target is not None:
            return self.created_target
        return self.process.current_ico

    def add_consume_exit_behavior(self):

        def maybe_push_consume():
            if self.should_push_consume():
                (aop, context) = self.get_consume_aop_and_context()
                if aop is not None:
                    return aop.test_and_execute(context)
            return True

        self.add_exit_function(maybe_push_consume)

    def get_consume_aop_and_context(self):
        affordance = self.consume_object.get_consume_affordance()
        if affordance is None:
            logger.warn('{}: object is missing consume affordance. It might not have been created as the final product of the recipe: {}', self, self.consume_object)
            return (None, None)
        affordance = self.generate_continuation_affordance(affordance)
        aop = AffordanceObjectPair(affordance, self.consume_object, affordance, None)
        context = self.context.clone_for_continuation(self, carry_target=None, preferred_objects=set())
        return (aop, context)

    def _should_go_to_next_phase(self, result):
        if self.phase.point_of_no_return:
            return True
        return result

    def _do_perform_gen(self, timeline):
        if self.stop_other_sims_crafting:
            self.process.stop_linked_situation_crafters()
        result = yield from super()._do_perform_gen(timeline)
        if self._should_go_to_next_phase(result) and self.auto_goto_next_phase:
            if self.force_final_product:
                current_ico = self.process.current_ico
                current_ico.crafting_component.set_final_product(True)
            return self._go_to_next_phase()
        return result
lock_instance_tunables(CraftingPhaseSuperInteractionMixin, display_name=None, display_name_overrides=None, allow_user_directed=False, allow_autonomous=False)
class CraftingPhaseCreateObjectSuperInteraction(CraftingPhaseSuperInteractionMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'remove_crafting_component_on_end': Tunable(description='\n            If set to True, crafting component(if exists) on the target object will be removed after interaction is completed.\n            ', tunable_type=bool, default=False)}

    @flexproperty
    def stat_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.stat is not None:
            return cls.skill_loot_data.stat
        return inst.recipe.skill_loot_data.stat

    @flexproperty
    def skill_effectiveness_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.effectiveness is not None:
            return cls.skill_loot_data.effectiveness
        return inst.recipe.skill_loot_data.effectiveness

    @flexproperty
    def level_range_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.level_range is not None:
            return cls.skill_loot_data.level_range
        return inst.recipe.skill_loot_data.level_range

    def _custom_claim_callback(self):
        for participant in self.get_participants(ParticipantType.CraftingProcess):
            multiplier = participant.get_stat_multiplier(CraftingTuning.QUALITY_STATISTIC, ParticipantType.CraftingProcess)
            self.process.add_interaction_quality_multiplier(multiplier)
        self.process.current_ico = self.created_target
        previous_ico = self.process.previous_ico
        if previous_ico is not None:
            self.process.previous_ico = None
            if previous_ico is self.target:
                self.set_target(self.created_target)
            if self.process.previous_phase is None or self.process.previous_phase.recipe.final_product_definition is not previous_ico.definition:
                previous_ico.transient = True
                if not previous_ico.get_users():
                    self.add_exit_function(previous_ico.destroy)
        if self.phase.object_info_is_final_product:
            resolver = SingleActorAndObjectResolver(self.sim.sim_info, self.created_target, source=self)
            if self.process.recipe.final_product.conditional_apply_states:
                for conditional_state in self.process.recipe.final_product.conditional_apply_states:
                    if resolver(conditional_state.test):
                        self.created_target.set_state(conditional_state.state.state, conditional_state.state)
            if CraftingTuning.FOOD_POISONING_STATE is not None and self.process.recipe.food_poisoning_chance:
                chance = self.process.recipe.food_poisoning_chance.get_chance(resolver)
                if random.random() <= chance:
                    self.created_target.set_state(CraftingTuning.FOOD_POISONING_STATE, CraftingTuning.FOOD_POISONING_STATE_VALUE)
            self.process.apply_quality_and_value(self.created_target)
            if self.process.family_recipe is not None:
                handle_vfx = FamilyRecipesTuning.FAMILY_RECIPE_DATA.family_recipe_vfx(self.created_target)
                handle_vfx.start(self.created_target)
            loot = LootOperationList(self.get_resolver(), self.process.recipe.final_product.loot_list)
            loot.apply_operations()
            cas_parts = self.process.recipe.final_product.stored_cas_parts
            if cas_parts:
                StoredInfoComponent.store_info_on_object(self.created_target, _cas_parts=cas_parts)
        elif self.object_info is not None:
            loot = LootOperationList(self.get_resolver(), self.object_info.loot_list)
            loot.apply_operations()

    def _build_sequence_with_callback(self, callback=None, sequence=()):
        raise NotImplementedError()

    @property
    def _apply_state_xevt_id(self) -> 'int':
        raise NotImplementedError()

    @property
    def create_object_owner(self):
        return self.sim

    @property
    def should_reserve_created_object(self):
        return True

    @flexproperty
    def advance_phase_on_resume(cls, inst):
        return True

    def _should_persist_before_claim(self):
        return True

    def build_basic_content(self, sequence, **kwargs):
        super_build_basic_content = super().build_basic_content
        success = False

        def post_setup_crafted_object(crafted_object):
            self.process.setup_crafted_object(crafted_object, is_final_product=self.phase.object_info_is_final_product, random=random)

        def setup_crafted_object(crafted_object):
            if not self._should_persist_before_claim():
                crafted_object.persistence_group = PersistenceGroups.NONE
            for initial_state in reversed(self.object_info.initial_states):
                crafted_object.set_state(initial_state.state, initial_state, from_init=True)

        reserver = self if self.should_reserve_created_object else None
        self._object_create_helper = CreateObjectHelper(self.create_object_owner, self.object_info.definition.id, reserver, init=setup_crafted_object, tag='crafted object for recipe', post_add=post_setup_crafted_object)

        def callback(*_, **__):
            nonlocal success
            if self.process._paying_sim and not self.process.check_is_affordable():
                self.cancel(FinishingType.INTERACTION_QUEUE, cancel_reason_msg='Not enough bucks/simoleons for interaction.')
                success = False
            else:
                self._object_create_helper.claim()
                self._custom_claim_callback()
                self.process.pay_for_item()
                self._log_telemetry()
                success = True

        def crafting_sequence(timeline):
            nonlocal sequence
            sequence = super_build_basic_content(sequence, **kwargs)
            sequence = build_critical_section(sequence, flush_all_animations)
            for apply_state in reversed(self.object_info.apply_states):
                sequence = state_change(targets={self.created_target}, new_value_ending=apply_state, xevt_id=self._apply_state_xevt_id, animation_context=self.animation_context, sequence=sequence)
            sequence = element_utils.must_run(self._build_sequence_with_callback(callback, sequence))
            result = yield from element_utils.run_child(timeline, sequence)
            return result

        return (self._object_create_helper.create(crafting_sequence), lambda _: success)

    def _exited_pipeline(self, *args, **kwargs):
        super()._exited_pipeline(*args, **kwargs)
        if self.process is not None:
            self.process.refund_payment()

    def _log_telemetry(self):
        if self.phase.object_info_is_final_product:
            obj = self.process.current_ico
            quality_value = 0
            if obj is None:
                logger.error('Crafting process telemetry not having a crafted object for phase {} with recipe {}', self.phase, self.recipe, owner='camilogarcia')
                return
            if obj.has_state(CraftingTuning.MASTERWORK_STATE) and obj.get_state(CraftingTuning.MASTERWORK_STATE) is CraftingTuning.MASTERWORK_STATE_VALUE:
                quality_value = 4
            elif obj.has_state(CraftingTuning.QUALITY_STATE):
                quality_value = CraftingTuning.QUALITY_STATE_VALUE_MAP.get(obj.get_state(CraftingTuning.QUALITY_STATE)).state_star_number
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_NEW_OBJECT, sim=self.sim) as hook:
                hook.write_guid(TELEMETRY_FIELD_OBJECT_TYPE, obj.definition.id)
                hook.write_int(TELEMETRY_FIELD_OBJECT_QUALITY, quality_value)

class CraftingPhaseCreateObjectInSlotSuperInteraction(CraftingPhaseCreateObjectSuperInteraction):
    INSTANCE_TUNABLES = {'parenting_element': ParentObjectElement.TunableFactory(description='\n                Use this element to instruct the game where the newly-created\n                object should go.  The constraint to ensure the slot is empty\n                will be created automatically.\n                ', locked_args={'_child_object': None}), 'ignore_object_placmenent_verification': Tunable(description='\n                If enabled, when parenting the object at the end of crafting\n                process the placement of the object will ignore verification\n                like slot validation and slot availability.  \n                This is valid to tune ONLY if we are guaranteeing this phase\n                of the crafting process will delete the ico, since if its not\n                deleted, on  save load we will have two object on the same spot \n                and build buy will push one to the household inventory.\n                An example of a valid use case for this is the pumpkin carving\n                station where the ico is a carved generic pumpking and we want\n                to replace it for the final product on the same slot.\n                ', tunable_type=bool, default=False)}

    @property
    def _apply_state_xevt_id(self):
        return self.parenting_element.timing.xevt_id

    def disable_carry_interaction_mask(self):
        return True

    def _build_sequence_with_callback(self, callback=None, sequence=()):

        def get_child_object(*_, **__):
            return self.created_target

        return (build_critical_section_with_finally(self.parenting_element(self, get_child_object, ignore_object_placmenent_verification=True, sequence=sequence), lambda _: callback()),)

class CraftingPhaseCreateObjectInInventorySuperInteraction(CraftingPhaseCreateObjectSuperInteraction):
    INSTANCE_TUNABLES = {'inventory_participant': TunableEnumEntry(description='\n                The participant type who has the inventory for the created\n                target to go into.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'use_family_inventory': Tunable(description='\n                If checked, this object will be added to the family inventory \n                of the tuned sim participant. If the participant is not a sim,\n                this tunable will be ignored.', tunable_type=bool, default=False)}

    @classmethod
    def _constraint_gen(cls, sim, target, **kwargs):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, **kwargs):
            yield constraint

    @property
    def _apply_state_xevt_id(self):
        return SCRIPT_EVENT_ID_START_CARRY

    @property
    def should_reserve_created_object(self):
        return False

    @property
    def auto_goto_next_phase(self):
        return not self.use_family_inventory

    def add_object_to_inventory(self, *_, **__):
        result = False
        inventory_target = self.get_participant(participant_type=self.inventory_participant)
        created_target = self.created_target
        if inventory_target is not None:
            result = inventory_target.inventory_component.player_try_add_object(self.created_target)
        if not result:
            self.cancel(FinishingType.CRAFTING, cancel_reason_msg="Fail to add created object {} into {}'s inventory.".format(created_target, inventory_target))

    def add_object_to_household_inventory(self, *_, **__):
        self._go_to_next_phase()
        self.created_target.set_post_bb_fixup_needed()
        if not build_buy.move_object_to_household_inventory(self.created_target):
            logger.error('CraftingInteractions: Failed to add created target {} to household inventory.', self.created_target, owner='rmccord')

    def _build_sequence_with_callback(self, callback=None, sequence=()):
        if self.use_family_inventory:
            return build_element((sequence, lambda _: callback(), self.add_object_to_household_inventory))
        return build_element((self.add_object_to_inventory, sequence, lambda _: callback()))

    @property
    def allow_outcomes(self):
        if self._object_create_helper is None or self._object_create_helper.is_object_none:
            return False
        return super().allow_outcomes

class CraftingPhaseSendObjectForDeliverySuperInteraction(CraftingPhaseSuperInteractionMixin, SuperInteraction):

    def build_basic_content(self, sequence, **kwargs):
        super_build_basic_content = super().build_basic_content

        def _setup_object_for_delivery(timeline):
            purchasing_sim = self.process.paying_sim
            purchasing_sim.household.delivery_tracker.request_delivery(self.process.recipe.guid64, purchasing_sim.id)
            self.process.pay_for_item()

        sequence = super_build_basic_content(sequence, **kwargs)
        sequence = element_utils.must_run((_setup_object_for_delivery, sequence))
        return sequence
UNCLAIMED_CRAFTABLE_LIABILITY = 'UnclaimedCraftableLiability'
class UnclaimedCraftableLiability(Liability):

    def __init__(self, object_to_claim, recipe_cost, recipe_bucks_price, owning_sim, **kwargs):
        super().__init__(**kwargs)
        self._object_to_claim = object_to_claim
        self._original_object_location = object_to_claim.location
        self._recipe_cost = recipe_cost
        self._recipe_bucks_price = recipe_bucks_price
        self._owning_sim = owning_sim

    def release(self):
        if self._object_to_claim.location == self._original_object_location:
            self._object_to_claim.schedule_destroy_asap(source=self._owning_sim, cause='Destroying unclaimed craftable')
            self._owning_sim.family_funds.add(self._recipe_cost, 0, self._owning_sim)
            for (bucks_type_key, amount) in self._recipe_bucks_price.items():
                (bucks_type, _) = bucks_type_key
                tracker = BucksUtils.get_tracker_for_bucks_type(bucks_type, owner_id=self._owning_sim.id, add_if_none=amount > 0)
                if tracker is not None:
                    tracker.try_modify_bucks(bucks_type, amount)

    def should_transfer(self, continuation):
        return False

class CreateConsumableAndPushConsumeSuperInteraction(CraftingPhaseCreateObjectInInventorySuperInteraction):

    def _run_interaction_gen(self, timeline):
        result = yield from super()._run_interaction_gen(timeline)
        if not result:
            return result
        else:
            (aop, context) = self.get_consume_aop_and_context()
            if aop is not None and context is not None:
                result = aop.interaction_factory(context)
                if result:
                    result.interaction.add_liability(UNCLAIMED_CRAFTABLE_LIABILITY, UnclaimedCraftableLiability(self.consume_object, self.recipe.crafting_price, self.recipe.crafting_bucks_price, self.sim))
                    aop.execute_interaction(result.interaction)
                return result
        return False

    def get_consume_aop_and_context(self):
        (aop, _) = super().get_consume_aop_and_context()
        if aop is None:
            return (None, None)
        context = self.context.clone_for_insert_next(carry_target=None)
        return (aop, context)

class CraftingPhaseCreateCarriedObjectSuperInteraction(CraftingPhaseCreateObjectSuperInteraction):
    INSTANCE_TUNABLES = {'posture_type': TunableReference(description='\n            Posture to use to carry the object.\n            ', manager=services.get_instance_manager(sims4.resources.Types.POSTURE), allow_none=True), 'carry_track_override': OptionalTunable(description='\n            If enabled, specify which hand the Sim must use to carry the\n            created object.\n            ', tunable=TunableEnumEntry(description='\n                Which hand to carry the object in.\n                ', tunable_type=PostureTrack, default=PostureTrack.RIGHT))}

    @property
    def auto_goto_next_phase(self):
        return True

    @property
    def _apply_state_xevt_id(self):
        return SCRIPT_EVENT_ID_START_CARRY

    def _build_sequence_with_callback(self, callback=None, sequence=()):

        def create_si_fn():
            if self.should_push_consume(from_exit=False):
                return self.get_consume_aop_and_context()
            return (None, None)

        carry_element_helper = CarryElementHelper(interaction=self, carry_target=self.created_target, carry_track=self.carry_track_override, create_owning_si_fn=create_si_fn, callback=callback, sequence=sequence)
        return carry_element_helper.enter_carry_while_holding()

class CraftingPhaseCreateObjectFromCarryingSuperInteraction(CraftingPhaseCreateObjectSuperInteraction):
    INSTANCE_TUNABLES = {'apply_final_states_xevt_id': OptionalTunable(Tunable(int, 100, description='Event ID at which the new ICO will have its final state changes applied.'), disabled_name='use_stop_carry_event', enabled_name='use_custom_event_id')}

    def disable_carry_interaction_mask(self):
        return True

    def setup_asm_default(self, asm, actor_name, target_name, carry_target_name, create_target_name=None, **kwargs):
        result = super().setup_asm_default(asm, actor_name, target_name, carry_target_name, **kwargs)
        if result:
            if create_target_name is None:
                logger.error('Attempt to run {} without a create_target name in the animation {}', self, asm, owner='cjiang')
            elif asm.get_actor_definition(create_target_name) is not None:
                return asm.add_potentially_virtual_actor(actor_name, self.sim, create_target_name, self.created_target, target_participant=AnimationParticipant.CREATE_TARGET)
        return result

    def _custom_claim_callback(self):
        if not services.current_zone().lot.is_position_on_lot(self.created_target.position, 0):
            self.created_target.persistence_group = PersistenceGroups.IN_OPEN_STREET
        else:
            self.created_target.persistence_group = PersistenceGroups.OBJECT
            add_object_to_buildbuy_system(self.created_target.id)
        super()._custom_claim_callback()
        self.carry_target.remove_from_client()
        self.add_consume_exit_behavior()

    def _should_persist_before_claim(self):
        return False

    @property
    def _apply_state_xevt_id(self):
        if self.apply_final_states_xevt_id is None:
            return SCRIPT_EVENT_ID_STOP_CARRY
        return self.apply_final_states_xevt_id

    def _build_sequence_with_callback(self, callback=None, sequence=()):
        carry_element_helper = CarryElementHelper(interaction=self, sequence=sequence, callback=callback)
        return carry_element_helper.exit_carry_while_holding()

    @flexproperty
    def advance_phase_on_resume(cls, inst):
        return False

    def _should_go_to_next_phase(self, result):
        if not result:
            return self.transition.succeeded
        return result

class CraftingPhasePickUpObjectSuperInteraction(CraftingPhaseSuperInteractionMixin, PickUpObjectSuperInteraction):
    pass

class CraftingPhaseStagingSuperInteraction(CraftingPhaseSuperInteractionMixin, SuperInteraction):
    _content_sets_cls = SuperInteraction._content_sets

    @flexproperty
    def _content_sets(cls, inst):
        if inst is not None and inst.phase.content_set is not None:
            if cls._content_sets_cls.has_affordances():
                logger.error("{}: this interaction has a content set tuned but is being used in a recipe phase ({}) which has its own content set.  The interaction's content set will be ignored.", cls.__name__, inst.phase)
            return inst.phase.content_set
        return cls._content_sets_cls

    @flexproperty
    def stat_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.stat is not None:
            return cls.skill_loot_data.stat
        return inst.recipe.skill_loot_data.stat

    @flexproperty
    def skill_effectiveness_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.effectiveness is not None:
            return cls.skill_loot_data.effectiveness
        return inst.recipe.skill_loot_data.effectiveness

    @flexproperty
    def level_range_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.level_range is not None:
            return cls.skill_loot_data.level_range
        return inst.recipe.skill_loot_data.level_range

    @property
    def auto_goto_next_phase(self):
        return self.basic_content is None or not self.basic_content.staging

    @property
    def phase_index(self):
        return self.process.get_progress()

    def _run_interaction_gen(self, timeline):
        self.add_consume_exit_behavior()
        result = yield from super()._run_interaction_gen(timeline)
        return result

class CraftingPhaseTransferCraftingComponentSuperInteraction(CraftingPhaseStagingSuperInteraction):
    INSTANCE_TUNABLES = {'crafting_component_recipient': TunableEnumEntry(description='\n            The participant of this interaction to which the Crafting process is transferred.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'override_crafting_process': Tunable(description='\n            If set to True, when crafting component is added to object, set the crafting process\n            even if the object already had a crafting component.\n            ', tunable_type=bool, default=False)}

    def build_basic_elements(self, sequence):
        super_basic_elements = super().build_basic_elements(sequence=sequence)

        def transfer_crafting_component(_):
            subject = self.get_participant(self.crafting_component_recipient)
            self.process.add_crafting_component_to_object(subject, self.override_crafting_process)
            self.process.increment_phase(interaction=self)
            if self.process._paying_sim and not self.process.check_is_affordable():
                self.cancel(FinishingType.INTERACTION_QUEUE, cancel_reason_msg='Not enough bucks/simoleons for interaction.')
            else:
                self.process.pay_for_item()
                self.process.apply_quality_and_value(subject)

        return element_utils.build_element((transfer_crafting_component, super_basic_elements))

    def _exited_pipeline(self, *args, **kwargs):
        super()._exited_pipeline(*args, **kwargs)
        if self.process is not None and not self.process.is_complete:
            self.process.refund_payment()

class GrabServingSuperInteraction(GrabServingMixin, SuperInteraction):
    GRAB_WHILE_STANDING_PENALTY = Tunable(description='\n        An additional penalty to apply to the constraint of grabbing a serving\n        of food while standing so Sims will prefer to sit before grabbing the\n        food if possible.\n        ', tunable_type=int, default=5)
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(one_shot=True, no_content=True, default='no_content'), 'posture_type': TunableReference(description='\n            Posture to use to carry the object.\n            ', manager=services.get_instance_manager(sims4.resources.Types.POSTURE)), 'si_to_push': TunableReference(description='\n            SI to push after picking up the object. ATTENTION: Any ads\n            specified by the SI to push will bubble up and attach themselves to\n            the _Grab interaction!\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True), 'default_grab_serving_animation': TunableAnimationReference(description='\n             The animation to play for this interaction in the case that the\n             object we are grabbing is not in an inventory.  If the object is\n             in an inventory, we will dynamically generate the animation we\n             need to grab it.\n             '), 'decrease_serving': Tunable(description='\n            If checked then we will decrease the number of servings by 1 when\n            this interaction is run.\n            ', tunable_type=bool, default=True), 'consume_affordances_override': TunableList(description='\n            A list of consume affordances to attempt to run on the consumable.\n            \n            This is a priority based list - the affordances will test in the\n            order they are tuned, running the first one that passes.\n            \n            If none pass, this reverts to using the consume affordance tuned on\n            the consumable.\n            ', tunable=TunableReference(description='\n                An affordance to test and potentially run on the consumable.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True)), 'apply_pickup_constraints_if_already_carrying': Tunable(description='\n            If the target object is already being carried, do we still want to\n            apply pickup constraints?\n            ', tunable_type=bool, default=True), 'grab_all_servings': Tunable(description="\n            If true, interaction will grab/pick one serving and add the remaining ones into the sim's inventory\n            ", tunable_type=bool, default=False), 'send_item_crafted_event': Tunable(description='\n            If true, ItemCrafted event will be sent in the beginning of grabbing the crafted object from appliance. \n            It should be set to true for unmanned appliances. For usual(manned) appliances this is normally sent when crafting is finished.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_handled_mutation = False

    @classmethod
    def autonomy_ads_gen(cls, target=None, include_hidden_false_ads=False):
        yield from super().autonomy_ads_gen(target=target, include_hidden_false_ads=include_hidden_false_ads)
        if cls.si_to_push:
            yield from cls.si_to_push.autonomy_ads_gen(target=target, include_hidden_false_ads=include_hidden_false_ads)

    @classmethod
    def _false_advertisements_gen(cls):
        yield from super()._false_advertisements_gen()
        if cls.si_to_push:
            yield from cls.si_to_push._false_advertisements_gen()

    @classproperty
    def static_commodities_data(cls):
        static_commodity_set = super().static_commodities_data
        if not cls.si_to_push:
            return static_commodity_set
        return cls._static_commodities_set | cls.si_to_push.static_commodities_data

    def is_guaranteed(self):
        return not self.has_active_cancel_replacement

    @classproperty
    def commodity_flags(cls):
        if cls.si_to_push:
            return frozenset(cls._commodity_flags) | cls.si_to_push.commodity_flags
        return frozenset(cls._commodity_flags)

    @classmethod
    def _statistic_operations_gen(cls):
        for op in super()._statistic_operations_gen():
            yield op
        if cls.si_to_push is not None:
            for op in cls.si_to_push._statistic_operations_gen():
                yield op

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor, **kwargs):
        yielded_geometry = False
        if target is None:
            return
        if target.is_in_inventory():
            if inst is not None:
                inventory_owner = inst.object_with_inventory
            else:
                inventory_owner = None
            inventory_owner = target.get_inventory().owner
            constraint = inventory_owner.get_inventory_access_constraint(sim, is_put=False, carry_target=target, use_owner_as_target_for_resolver=True)
            yield constraint
        else:
            total_constraint = Anywhere()
            for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type, **kwargs):
                for inner_constraint in constraint:
                    if inner_constraint.geometry or inner_constraint.tentative:
                        yielded_geometry = True
                total_constraint = total_constraint.intersect(constraint)
            if participant_type != ParticipantType.Actor:
                return total_constraint
            total_constraint = total_constraint.intersect(target.get_carry_transition_constraint(sim, target.position, target.routing_surface))
            if yielded_geometry or (target.parent is not sim or inst.apply_pickup_constraints_if_already_carrying) and target.parent is None or inst is None:
                yield total_constraint
                return
            surface = target.parent
            surface = surface.part_owner
            target_obj_def = inst.create_target
            target_obj_def = inst.created_target.definition
            if surface.is_part and inst.target.has_component(CRAFTING_COMPONENT) or inst.created_target is not None and target_obj_def is None:
                return
            slot_manifest = SlotManifest()
            slot_manifest_entry = SlotManifestEntry(target_obj_def, surface, SlotTypeReferences.SIT_EAT_SLOT)
            slot_manifest.add(slot_manifest_entry)
            posture_manifest = SIT_PICKUP_POSTURES
            posture_state_spec = PostureStateSpec(posture_manifest, slot_manifest, PostureSpecVariable.ANYTHING)
            slot_constraint = Constraint(posture_state_spec=posture_state_spec, debug_name='IdealGrabServingConstraint')
            ideal_constraint = slot_constraint.intersect(total_constraint)
            fallback_constraint = total_constraint.generate_constraint_with_cost(cls.GRAB_WHILE_STANDING_PENALTY)
            total_constraint_set = create_constraint_set((fallback_constraint, ideal_constraint))
            yield total_constraint_set

    @property
    def create_target(self):
        recipe = self._get_recipe()
        if recipe is None:
            return
        return recipe.final_product_definition

    def on_added_to_queue(self, *args, **kwargs):
        crafting_component = self.target.crafting_component
        if crafting_component is not None:
            mutated_listeners = crafting_component.object_mutated_listeners
            if self.on_mutated not in mutated_listeners:
                mutated_listeners.append(self.on_mutated)
        return super().on_added_to_queue(*args, **kwargs)

    def _exited_pipeline(self, *args, **kwargs):
        self._detach_mutated_listener()
        return super()._exited_pipeline(*args, **kwargs)

    def _detach_mutated_listener(self):
        if self.target is not None and self.target.crafting_component is not None:
            mutated_listeners = self.target.crafting_component.object_mutated_listeners
            if self.on_mutated in mutated_listeners:
                mutated_listeners.remove(self.on_mutated)

    def setup_crafted_object(self, crafted_object):
        self._setup_crafted_object(self._get_recipe(), self.target, crafted_object)
        if self.target.is_in_inventory():
            inventory_owner = self.target.get_inventory().owner
            inventory_owner.inventory_component.system_add_object(crafted_object)

    def on_mutated(self):
        if not self._has_handled_mutation:
            self.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Crafting Target Object Mutated to Empty Platter')
        self._has_handled_mutation = True

    def _get_recipe(self):
        if self.use_linked_recipe_mapping:
            return self._get_linked_recipe()
        return self.get_base_recipe()

    def get_base_recipe(self):
        if self.target is not None and self.target.has_component(CRAFTING_COMPONENT):
            recipe = self.target.get_recipe()
            return recipe.get_base_recipe()

    def _get_linked_recipe(self):
        if self.target is not None and self.target.has_component(CRAFTING_COMPONENT):
            recipe = self.target.get_recipe()
            return recipe.get_linked_recipe(self.get_interaction_type())

    @classmethod
    def _define_supported_postures(cls):
        posture_manifest = cls.posture_type(GLOBAL_STUB_ACTOR, None, None).asm.get_supported_postures_for_actor('x')
        return frozendict({ParticipantType.Actor: posture_manifest})

    def setup_asm_default(self, asm, *args, **kwargs):
        result = super().setup_asm_default(asm, *args, **kwargs)
        surface_height = get_surface_height_parameter_for_object(self.target, sim=self.sim)
        asm.set_parameter('surfaceHeight', surface_height)
        return result

    def _grab_remaining_servings(self, crafted_object):
        if self.grab_all_servings:
            servings = self.target.get_stat_instance(CraftingTuning.SERVINGS_STATISTIC)
            num_servings = servings.tracker.get_value(CraftingTuning.SERVINGS_STATISTIC) if servings is not None else 0
            if num_servings > 0:
                crafted_object.inventoryitem_component.update_stack_count(int(num_servings))
                servings.tracker.add_value(CraftingTuning.SERVINGS_STATISTIC, -int(num_servings))

    def build_basic_elements(self, sequence):
        super_build_basic_elements = super().build_basic_elements
        self._object_create_helper = CreateObjectHelper(self.sim, self.create_target, self, post_add=self.setup_crafted_object, tag='Grab a Serving')

        def on_enter_carry(*_, **__):
            self._object_create_helper.claim()
            self._detach_mutated_listener()
            servings = self.target.get_stat_instance(CraftingTuning.SERVINGS_STATISTIC)
            if self.decrease_serving:
                servings.tracker.add_value(CraftingTuning.SERVINGS_STATISTIC, -1)
            self._grab_remaining_servings(self.created_target)
            if self.send_item_crafted_event and self.created_target is not None and self.created_target.crafting_component is not None:
                self.created_target.crafting_component.send_item_crafted_event()

        self.store_event_handler(on_enter_carry, handler_id=SCRIPT_EVENT_ID_START_CARRY)

        def create_si():
            context = self.context.clone_for_continuation(self)
            for consume_affordance in self.consume_affordances_override:
                affordance = self.generate_continuation_affordance(consume_affordance)
                kwargs_copy = self._kwargs.copy()
                kwargs_copy['saved_participants'] = self._saved_participants
                aop = AffordanceObjectPair(affordance, self.created_target, affordance, None, **kwargs_copy)
                if aop.test(context):
                    return (aop, context)
            affordance = self.created_target.get_consume_affordance(context=context)
            affordance = self.generate_continuation_affordance(affordance)
            if affordance is None:
                logger.error('{} cannot find the consume interaction from the final product {}.', self, self.created_target)
                return (None, None)
            aop = AffordanceObjectPair(affordance, self.created_target, affordance, None)
            target_parent = self.target.parent
            preferred_locations = set()
            if target_parent is not None:
                for child in target_parent.get_all_children_gen():
                    preferred_locations.add(child.id)
            aop.interaction_parameters['preferred_posture_targets'] = preferred_locations
            return (aop, context)

        def grab_sequence(timeline):
            nonlocal sequence
            inventory_target = None
            if not self.target.is_in_sim_inventory():
                inventory_target = self.sim.posture_state.surface_target
            if self.target.is_in_inventory() and inventory_target is not None:
                custom_animation = inventory_target.inventory_component._get_put.get_access_animation_factory(is_put=False)

                def setup_asm(asm):
                    result = self.sim.posture.setup_asm_interaction(asm, self.sim, inventory_target, custom_animation.actor_name, custom_animation.target_name, carry_target=self.created_target, carry_target_name=custom_animation.carry_target_name, surface_target=inventory_target)
                    carry_track = self.sim.posture_state.get_free_carry_track(obj=self.created_target)
                    asm.set_actor_parameter(custom_animation.carry_target_name, self.created_target, PARAM_CARRY_TRACK, carry_track.name.lower())
                    return result

                sequence = custom_animation(self, sequence=sequence, setup_asm_override=setup_asm)
            else:
                sequence = self.default_grab_serving_animation(self, sequence=sequence)
            sequence = super_build_basic_elements(sequence=sequence)
            carry_element_helper = CarryElementHelper(interaction=self, carry_target=self.created_target, create_owning_si_fn=create_si, sequence=sequence)
            sequence = carry_element_helper.enter_carry_while_holding()
            result = yield from element_utils.run_child(timeline, sequence)
            return result

        return unless(lambda *_: self._has_handled_mutation, self._object_create_helper.create(grab_sequence))

class DebugCreateCraftableInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiRecipePicker.TunableFactory(description="\n            The interaction's recipe picker.\n            ", tuning_group=GroupNames.PICKERTUNING), 'recipe_tag': TunableEnumWithFilter(tunable_type=Tag, filter_prefixes=('Recipe',), default=Tag.INVALID, invalid_enums=(Tag.INVALID,)), 'quality': OptionalTunable(tunable=TunableStateValueReference(description='\n                The quality of the cheated consumable\n                '))}

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        sim = inst.sim if inst is not None else context.sim
        recipes = services.get_instance_manager(sims4.resources.Types.RECIPE).get_ordered_types(only_subclasses_of=Recipe)
        for (i, recipe) in enumerate(recipes):
            if cls.recipe_tag not in recipe.recipe_tags:
                pass
            elif recipe.final_product.definition is None:
                pass
            else:
                recipe_icon = IconInfoData(icon_resource=recipe.icon_override, obj_def_id=recipe.final_product_definition_id, obj_geo_hash=recipe.final_product_geo_hash, obj_material_hash=recipe.final_product_material_hash)
                row = RecipePickerRow(name=recipe.get_recipe_name(sim), icon=recipe.icon_override, row_description=recipe.recipe_description(sim), linked_recipe=recipe.base_recipe, display_name=recipe.get_recipe_picker_name(sim), icon_info=recipe_icon, tag=recipe, skill_level=i, group_recipe_override=recipe.group_recipe_override, linked_recipe_override=recipe.linked_recipe_override, enable_speed_up_background=recipe.enable_speed_up_background, food_restriction_ingredients=recipe.food_restriction_ingredients)
                yield row

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True

    def _on_picker_selected(self, dialog):
        for recipe in dialog.get_result_tags():
            craftable = create_craftable(recipe, self.sim, quality=self.quality)
            if not craftable.is_in_inventory():
                CarryingObject.snap_to_good_location_on_floor(craftable, starting_transform=self.target.transform, starting_routing_surface=self.target.routing_surface)
