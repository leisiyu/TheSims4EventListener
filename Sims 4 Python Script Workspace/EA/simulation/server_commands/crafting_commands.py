from carry.carry_postures import CarryingObjectfrom crafting import recipefrom crafting.crafting_ingredients import IngredientTuningfrom crafting.crafting_interactions import create_craftable, get_ingredient_requirement_with_ingredient_replacement_rules, StartCraftingMixin, get_ingredient_requirements, build_requirement_datafrom crafting.crafting_process import CRAFTING_QUALITY_LIABILITYfrom crafting.recipe import Recipefrom objects.object_enums import ItemLocationfrom objects.system import create_objectfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParamimport crafting.crafting_processimport servicesimport sims4.commandsfrom sims4.resources import Typesfrom tag import Tagfrom jewelry_crafting.jewelry_crafting_tuning import JewelryCraftingTuningfrom objects.definition_manager import DefinitionManagerfrom objects.components.types import CHARGEABLE_COMPONENTfrom crafting.crafting_tunable import CraftingTuning
@sims4.commands.Command('crafting.shorten_phases', command_type=sims4.commands.CommandType.Automation)
def shorten_phases(enabled:bool=None, _connection=None):
    output = sims4.commands.Output(_connection)
    if enabled is None:
        do_enabled = not crafting.crafting_process.shorten_all_phases
    else:
        do_enabled = enabled
    crafting.crafting_process.shorten_all_phases = do_enabled
    if enabled is None:
        if do_enabled:
            output('Crafting phases are shortened.')
        else:
            output('Crafting phases are normal length.')
    return True

@sims4.commands.Command('crafting.get_recipes_with_tag', command_type=sims4.commands.CommandType.Automation)
def get_recipes_with_tag(tag:Tag, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    recipes = services.get_instance_manager(sims4.resources.Types.RECIPE).get_ordered_types(only_subclasses_of=Recipe)
    automation_output('CraftingGetRecipesWithTag; Status:Begin')
    for (i, recipe) in enumerate(recipes):
        if tag not in recipe.recipe_tags:
            pass
        elif recipe.final_product.definition is None:
            pass
        else:
            automation_output('CraftingGetRecipesWithTag; Status:Data, RecipeId:{}, Recipe:{}, ProductId:{}'.format(recipe.guid64, recipe.__name__, recipe.final_product_definition_id))
            output('{}:{}'.format(recipe.guid64, recipe.__name__))
    automation_output('CraftingGetRecipesWithTag; Status:End')
    return True

@sims4.commands.Command('crafting.get_recipes_with_tags_for_appliance', command_type=sims4.commands.CommandType.Automation)
def get_recipes_with_tags_for_appliance(appliance_definition_id, *tags, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    automation_output('CraftingGetRecipesWithTagsForAppliance; Status:Begin')
    for appliance_definition_tag_tuple in Recipe.TEST_APPLIANCE_DEFINITIONS_TAGS_PAIRS:
        appliance_definition = appliance_definition_tag_tuple[0]
        if appliance_definition.id != int(appliance_definition_id):
            pass
        else:
            super_affordance = appliance_definition_tag_tuple[1]
            if hasattr(super_affordance, 'recipes'):
                for (i, recipe) in enumerate(super_affordance.recipes):
                    if not all(item in recipe.recipe_tags for item in tags):
                        pass
                    elif recipe.final_product.definition is None:
                        pass
                    else:
                        automation_output('CraftingGetRecipesWithTagsForAppliance; Status:Data, RecipeId:{}, Recipe:{}, ProductId:{},  SuperAffordanceId:{}, SuperAffordance:{}'.format(recipe.guid64, recipe.__name__, recipe.final_product_definition_id, super_affordance.guid64, super_affordance.__name__))
                        output('RecipeId:{}, Recipe:{}, ProductId:{},  SuperAffordanceId:{}, SuperAffordance:{}'.format(recipe.guid64, recipe.__name__, recipe.final_product_definition_id, super_affordance.guid64, super_affordance.__name__))
    automation_output('CraftingGetRecipesWithTagsForAppliance; Status:End')
    return True

@sims4.commands.Command('crafting.get_testing_appliance_tag_pairs', command_type=sims4.commands.CommandType.Automation)
def get_testing_appliance_tag_pairs(_connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    automation_output('CraftingGetTestingApplianceTagPairs; Status:Begin')
    for appliance_definition_tag_tuple in Recipe.TEST_APPLIANCE_DEFINITIONS_TAGS_PAIRS:
        appliance_definition = appliance_definition_tag_tuple[0]
        tags = appliance_definition_tag_tuple[2]
        for tag_list in tags:
            tag_list_str = [str(tag) for tag in tag_list]
            tag_string = ','.join(tag_list_str)
            output('ApplianceDefinition:{}, DefinitionId:{}, Tag Set:{}'.format(appliance_definition, appliance_definition.id, tag_string))
            automation_output('CraftingGetTestingApplianceTagPairs; Status:Data, ApplianceDefinition:{}, DefinitionId:{}, Tag Set:{}'.format(appliance_definition, appliance_definition.id, tag_string))
    automation_output('CraftingGetTestingApplianceTagPairs; Status:End')
    return True

@sims4.commands.Command('crafting.create_recipe', command_type=sims4.commands.CommandType.Automation)
def create_recipe(recipe:TunableInstanceParam(Types.RECIPE), opt_sim:OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        output('No sim for recipe creation')
        automation_output('CraftingCreateRecipe; Status:No Sim')
        return False
    craftable = create_craftable(recipe, sim)
    if craftable is None:
        output('Failed To Create Craftable')
        automation_output('CraftingCreateRecipe; Status:Failed To Create Craftable')
        return False
    CarryingObject.snap_to_good_location_on_floor(craftable, starting_transform=sim.transform, starting_routing_surface=sim.routing_surface)
    automation_output('CraftingCreateRecipe; Status:Success, ObjectId:{}'.format(craftable.id))
    return True

@sims4.commands.Command('crafting.show_quality')
def show_quality(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No sim for crafting.show_quality', _connection)
        return False
    crafting_liability = None
    for si in sim.si_state:
        crafting_liability = si.get_liability(CRAFTING_QUALITY_LIABILITY)
        if crafting_liability is not None:
            break
    if crafting_liability is None:
        sims4.commands.output('Sim {} is not doing any crafting interaction'.format(sim), _connection)
        return False
    (quality_state, quality_stats_value) = crafting_liability.get_quality_state_and_value()
    quality_state_strings = ['None', 'Poor', 'Normal', 'Outstanding']
    quality_state = quality_state or 0
    sims4.commands.output('Sim {} current crafting quality is {}({})'.format(sim, quality_state_strings[quality_state], quality_stats_value), _connection)
    return True

@sims4.commands.Command('crafting.ingredients_required_toggle', command_type=sims4.commands.CommandType.Cheat)
def toggle_ingredients_required(_connection=None):
    recipe.debug_ingredient_requirements = not recipe.debug_ingredient_requirements
    if recipe.debug_ingredient_requirements:
        message = 'Ingredient requirements have been enabled.'
    else:
        message = 'Ingredient requirements disabled. Craft at will.'
    sims4.commands.output(message, _connection)

@sims4.commands.Command('crafting.add_recipe_ingredients', command_type=sims4.commands.CommandType.Automation)
def add_recipe_ingredients(recipe_id:int, sim_id:OptionalTargetParam=None, use_fresh:bool=None, use_prepped:bool=None, _connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim = get_optional_target(sim_id, _connection)
    recipe_manager = services.get_instance_manager(sims4.resources.Types.RECIPE)
    recipe = recipe_manager.get(recipe_id)
    ingredient_list = [ingredient_requirement_factory() for ingredient_requirement_factory in recipe.use_ingredients.ingredient_list]
    ingredient_filtered_list = None
    if use_fresh and use_prepped:
        ingredient_filtered_list = get_ingredient_requirement_with_ingredient_replacement_rules(ingredient_list)
    elif use_prepped:
        ingredient_filtered_list = [ingredient_requirement for ingredient_requirement in ingredient_list if ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG)]
    elif use_fresh:
        ingredient_filtered_list = [ingredient_requirement for ingredient_requirement in ingredient_list if not ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG)]
    if ingredient_filtered_list is None:
        return
    for ingredient_requirement in ingredient_filtered_list:
        definition = ingredient_requirement.get_definition()
        if definition is None:
            for definition_by_tag in services.definition_manager().get_definitions_for_tags_gen((ingredient_requirement._tag,)):
                definition = definition_by_tag
                break
        else:
            new_object = create_object(definition, loc_type=ItemLocation.SIM_INVENTORY)
            if new_object is not None and sim.inventory_component.can_add(new_object):
                sim.inventory_component.player_try_add_object(new_object)
    automation_output('CraftingAddRecipeIngredients; Status:Success, RecipeId:{}'.format(recipe_id))
    return True

@sims4.commands.Command('crafting.get_ingredient_requirements_of_recipe', command_type=sims4.commands.CommandType.Automation)
def get_ingredient_requirements_of_recipe(recipe_id:int, use_fresh:bool, use_prepped:bool, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    recipe_manager = services.get_instance_manager(sims4.resources.Types.RECIPE)
    recipe = recipe_manager.get(recipe_id)
    ingredient_list = [ingredient_requirement_factory() for ingredient_requirement_factory in recipe.use_ingredients.ingredient_list]
    ingredient_filtered_list = []
    if use_fresh and use_prepped:
        ingredient_filtered_list = get_ingredient_requirement_with_ingredient_replacement_rules(ingredient_list)
    elif use_prepped:
        ingredient_filtered_list = [ingredient_requirement for ingredient_requirement in ingredient_list if ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG)]
    elif use_fresh:
        ingredient_filtered_list = [ingredient_requirement for ingredient_requirement in ingredient_list if not ingredient_requirement.has_tag(IngredientTuning.PREPPED_INGREDIENT_TAG)]
    automation_output('CraftingGetIngredientRequirementsOfRecipe; Status:Begin')
    for ingredient_requirement in ingredient_filtered_list:
        definition = ingredient_requirement.get_definition()
        name = None
        if definition is None:
            name = ingredient_requirement._tag
        else:
            name = definition.name
        output('RequirementName:{}, RequirementCount:{}'.format(name, ingredient_requirement.count_required))
        automation_output('CraftingGetIngredientRequirementsOfRecipe; Status:Data, RequirementName:{}, RequirementCount:{}'.format(name, ingredient_requirement.count_required))
    automation_output('CraftingGetIngredientRequirementsOfRecipe; Status:End')
    return True

@sims4.commands.Command('crafting.get_available_ingredients', command_type=sims4.commands.CommandType.Automation)
def get_available_ingredients(sim_id:OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim = get_optional_target(sim_id, _connection)
    all_ingredients = StartCraftingMixin.get_default_candidate_ingredients(sim, check_sim_inventory=True, check_fridge_shared_inventory=True)
    automation_output('CraftingGetAvailableIngredients; Status:Begin')
    for ingredient in all_ingredients:
        output('{}:{}'.format(ingredient, ingredient.stack_count()))
        automation_output('CraftingGetAvailableIngredients; Status:Data, IngredientName:{}, IngredientCount:{}'.format(ingredient, ingredient.stack_count()))
    automation_output('CraftingGetAvailableIngredients; Status:End')
    return True

@sims4.commands.Command('crafting.get_recipe_price', command_type=sims4.commands.CommandType.Automation)
def get_recipe_price(recipe_id:int, sim_id:OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    recipe_manager = services.get_instance_manager(sims4.resources.Types.RECIPE)
    recipe = recipe_manager.get(recipe_id)
    all_ingredients_required = recipe.all_ingredients_required
    ingredient_requirement_list = []
    sim = get_optional_target(sim_id, _connection)
    candidate_ingredients = StartCraftingMixin.get_default_candidate_ingredients(sim, check_sim_inventory=True, check_fridge_shared_inventory=True)
    for tuned_ingredient_factory in recipe.use_ingredients.ingredient_list:
        ingredients_used = {}
        ingredient_requirement = tuned_ingredient_factory()
        ingredient_requirement.attempt_satisfy_ingredients(candidate_ingredients, ingredients_used)
        ingredient_requirement_list.append(ingredient_requirement)
    (only_fresh_ingredients, only_prepped_ingredients, both_fresh_prepped_requirements) = get_ingredient_requirements(ingredient_requirement_list, all_ingredients_required)
    (_, _, adjusted_ingredient_price_both_fresh_prepped) = build_requirement_data(both_fresh_prepped_requirements, all_ingredients_required)
    (_, _, adjusted_ingredient_price_only_prepped) = build_requirement_data(only_prepped_ingredients, all_ingredients_required)
    (_, _, adjusted_ingredient_price_only_fresh) = build_requirement_data(only_fresh_ingredients, all_ingredients_required)
    (original_price, discounted_price, ingredients_price_both_fresh_prepped) = recipe.get_price(False, adjusted_ingredient_price_both_fresh_prepped)
    (_, _, ingredients_price_only_prepped) = recipe.get_price(False, adjusted_ingredient_price_only_prepped)
    (_, _, ingredients_price_only_fresh) = recipe.get_price(False, adjusted_ingredient_price_only_fresh)
    output('Original Price:{}'.format(original_price))
    output('Discounted Price:{}'.format(discounted_price))
    output('Only Fresh Price:{}'.format(ingredients_price_only_fresh))
    output('Only Prepped Price:{}'.format(ingredients_price_only_prepped))
    output('Both Fresh and Prepped Price:{}'.format(ingredients_price_both_fresh_prepped))
    automation_output('CraftingGetRecipePrice; Status:Begin')
    automation_output('CraftingGetRecipePrice; Status:Data, OriginalPrice:{}'.format(original_price))
    automation_output('CraftingGetRecipePrice; Status:Data, DiscountedPrice:{}'.format(discounted_price))
    automation_output('CraftingGetRecipePrice; Status:Data, OnlyFreshPrice:{}'.format(ingredients_price_only_fresh))
    automation_output('CraftingGetRecipePrice; Status:Data, OnlyPreppedPrice:{}'.format(ingredients_price_only_prepped))
    automation_output('CraftingGetRecipePrice; Status:Data, BothFreshPreppedPrice:{}'.format(ingredients_price_both_fresh_prepped))
    automation_output('CraftingGetRecipePrice; Status:End')
    return True

@sims4.commands.Command('crafting.get_materials_design', command_type=sims4.commands.CommandType.Automation)
def get_materials_design(design_id:int, is_crystal:bool=False, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    definition_manager = services.definition_manager()
    recipes = JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes + JewelryCraftingTuning.JEWELRY_DATA.gemstone_cutting_recipes
    recipe = next((design for design in recipes if design.final_product_definition_id == design_id), None)
    if recipe is None:
        output('No recipe found')
        automation_output('CraftingGetMaterialsDesigns; Status:End')
        return False
    if JewelryCraftingTuning.JEWELRY_NO_CRYSTAL_NEEDED_TAG in recipe.final_product_definition.build_buy_tags and is_crystal:
        output('This design has no crystals')
        automation_output('CraftingGetMaterialsDesigns; Status:End')
        return True
    if is_crystal:
        material_filtered_list = JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_crystals + JewelryCraftingTuning.JEWELRY_DATA.purchasable_crystals
    else:
        material_filtered_list = JewelryCraftingTuning.JEWELRY_DATA.purchasable_metals + JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_metals
    automation_output('CraftingGetMaterialsDesigns; Status:Begin')
    for material_requirement in material_filtered_list:
        material_id = material_requirement.id
        material_definition = definition_manager.get(material_id)
        material_name = material_definition.name
        output('RequirementName:{}, RequirementID:{}'.format(material_name, material_id))
        automation_output('CraftingGetMaterialsDesigns; Status:Data, RequirementName:{}, RequirementID:{}'.format(material_name, material_id))
    automation_output('CraftingGetMaterialsDesigns; Status:End')
    return True

@sims4.commands.Command('crafting.get_jewelry_design', command_type=sims4.commands.CommandType.Automation)
def get_jewelry_design(_connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    designs_list = JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes
    automation_output('CraftingGetJewelryDesigns; Status:Begin')
    for design in designs_list:
        output('RequirementName:{}, RequirementID:{}'.format(design.final_product_definition.name, design.final_product_definition.id))
        automation_output('CraftingGetJewelryDesigns; Status:Data, RequirementName:{}, RequirementID:{}'.format(design.final_product_definition.name, design.final_product_definition.id))
    automation_output('CraftingGetJewelryDesigns; Status:End')
    return True

@sims4.commands.Command('crafting.get_gemstone_design', command_type=sims4.commands.CommandType.Automation)
def get_gemstone_design(_connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    designs_list = JewelryCraftingTuning.JEWELRY_DATA.gemstone_cutting_recipes
    automation_output('CraftingGetCutGemstoneDesigns; Status:Begin')
    for design in designs_list:
        output('RequirementName:{}, RequirementID:{}'.format(design.final_product_definition.name, design.final_product_definition.id))
        automation_output('CraftingGetCutGemstoneDesigns; Status:Data,RequirementName:{}, RequirementID:{}'.format(design.final_product_definition.name, design.final_product_definition.id))
    automation_output('CraftingGetCutGemstoneDesigns; Status:End')
    return True

@sims4.commands.Command('crafting.get_jewelry_price', command_type=sims4.commands.CommandType.Automation)
def get_jewelry_price(recipe_id:int, sim_id:OptionalTargetParam=None, workbench_id:OptionalTargetParam=None, metal_id:int=0, crystal_id:int=0, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    definition_manager = services.definition_manager()
    is_jewelry_recipe = False
    recipes = JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes + JewelryCraftingTuning.JEWELRY_DATA.gemstone_cutting_recipes
    recipe = next((design for design in recipes if design.final_product_definition_id == recipe_id), None)
    if recipe in JewelryCraftingTuning.JEWELRY_DATA.gemstone_cutting_recipes:
        is_jewelry_recipe = False
    elif recipe in JewelryCraftingTuning.JEWELRY_DATA.jewelry_recipes:
        is_jewelry_recipe = True
    else:
        output('No recipe found')
        automation_output('CraftingGetJewelryPrice; Status:No Recipe')
        return False
    shape_price = recipe.crafting_price
    sim = get_optional_target(sim_id, _connection)
    workbench = get_optional_target(workbench_id, _connection)
    if sim is None:
        output('No sim for price calculation')
        automation_output('CraftingGetJewelryPrice; Status:No Sim')
        return False
    if workbench is None:
        output('No gemology table for price calculation')
        automation_output('CraftingGetJewelryPrice; Status:No Gemology Table')
        return False
    sim_inventory = sim.inventory_component
    workbench_inventory = workbench.inventory_component
    metal_definition = definition_manager.get(metal_id)
    crystal_definition = definition_manager.get(crystal_id)
    if metal_definition is None and is_jewelry_recipe:
        output('This recipe needs a metal id')
        automation_output('CraftingGetJewelryPrice; Status:Metal id needed')
        return False
    if metal_definition is not None:
        metal_count = sim_inventory.get_count(metal_definition)
        if metal_count == 0:
            metal_count += workbench_inventory.get_count(metal_definition) if workbench_inventory is not None else 0
        metal_real_price = int(metal_definition.price*JewelryCraftingTuning.JEWELRY_DATA.purchase_multiplier)
        metal_price = metal_real_price if metal_count == 0 else 0
    else:
        metal_real_price = 0
        metal_price = 0
    if crystal_definition is None and (is_jewelry_recipe is False or JewelryCraftingTuning.JEWELRY_NO_CRYSTAL_NEEDED_TAG not in recipe.final_product_definition.build_buy_tags):
        output('This recipe needs a crystal id')
        automation_output('CraftingGetJewelryPrice; Status:Crystal id needed')
        return False
    if crystal_definition is not None and JewelryCraftingTuning.JEWELRY_NO_CRYSTAL_NEEDED_TAG not in recipe.final_product_definition.build_buy_tags:
        crystal_count = sim_inventory.get_count(crystal_definition)
        if crystal_count == 0:
            crystal_count += workbench_inventory.get_count(crystal_definition) if workbench_inventory is not None else 0
        crystal_real_price = int(crystal_definition.price*JewelryCraftingTuning.JEWELRY_DATA.purchase_multiplier)
        crystal_price = crystal_real_price if crystal_count == 0 else 0
    else:
        crystal_real_price = 0
        crystal_price = 0
    original_price = shape_price + crystal_real_price + metal_real_price
    discounted_price = shape_price + crystal_price + metal_price
    output('Original Price:{}'.format(original_price))
    output('Discounted Price:{}'.format(discounted_price))
    output('Metal Price:{}'.format(metal_real_price))
    output('Crystal Price:{}'.format(crystal_real_price))
    output('Design Price:{}'.format(shape_price))
    automation_output('CraftingGetJewelryPrice; Status:Begin')
    automation_output('CraftingGetJewelryPrice; Status:Data, OriginalPrice:{}'.format(original_price))
    automation_output('CraftingGetJewelryPrice; Status:Data, DiscountedPrice:{}'.format(discounted_price))
    automation_output('CraftingGetJewelryPrice; Status:Data, MetalPrice:{}'.format(metal_real_price))
    automation_output('CraftingGetJewelryPrice; Status:Data, CrystalPrice:{}'.format(crystal_real_price))
    automation_output('CraftingGetJewelryPrice; Status:Data, DesignPrice:{}'.format(shape_price))
    automation_output('CraftingGetJewelryPrice; Status:End')
    return True

@sims4.commands.Command('crafting.populate_crafting_inventory', command_type=sims4.commands.CommandType.Automation)
def populate_crafting_inventory(item_inventory_id:OptionalTargetParam=None, _connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    item = get_optional_target(item_inventory_id, _connection)
    item_inventory = item.inventory_component
    definition_manager = services.definition_manager()
    crystal_list = JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_crystals + JewelryCraftingTuning.JEWELRY_DATA.purchasable_crystals
    metal_list = JewelryCraftingTuning.JEWELRY_DATA.purchasable_metals + JewelryCraftingTuning.JEWELRY_DATA.non_purchasable_metals
    for crystal in crystal_list:
        crystal_definition = definition_manager.get(crystal.id)
        if crystal_definition is None:
            pass
        else:
            new_object = create_object(crystal_definition, loc_type=ItemLocation.OBJECT_INVENTORY)
            if new_object is not None and item_inventory.can_add(new_object):
                item_inventory.player_try_add_object(new_object)
    for metal in metal_list:
        metal_definition = definition_manager.get(metal.id)
        if metal_definition is None:
            pass
        else:
            new_object = create_object(metal_definition, loc_type=ItemLocation.OBJECT_INVENTORY)
            if new_object is not None and item_inventory.can_add(new_object):
                item_inventory.player_try_add_object(new_object)
    automation_output('CraftingPopulateCraftingInventory; Status:Success, InventoryId:{}'.format(item_inventory_id))
    return True

@sims4.commands.Command('crafting.get_last_jewelry_created', command_type=sims4.commands.CommandType.Automation)
def get_last_jewelry_created(_connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    output = sims4.commands.Output(_connection)
    automation_output('CraftingGetLastJewelryCreatedInfo; Status:Begin')
    quality_state_strings = ['Botched', 'Poor', 'Normal', 'Excellent', 'Masterpiece']
    jewelries_created = [item for item in services.object_manager().get_all_objects_with_component_gen(CHARGEABLE_COMPONENT)]
    last_jewelry_created = jewelries_created[-1]
    if last_jewelry_created is None:
        output('A Jewelry needs to be created')
        automation_output('CraftingGetLastJewelryCreatedInfo; Status:Jewelry needed')
        return False
    is_botched = last_jewelry_created.chargeable_component._is_botched()
    is_drained = last_jewelry_created.chargeable_component._is_drained()
    jewelry_owner = last_jewelry_created.crafting_component.owner
    if is_botched:
        quality = quality_state_strings[0]
    elif jewelry_owner.has_state(CraftingTuning.MASTERWORK_STATE) and jewelry_owner.get_state(CraftingTuning.MASTERWORK_STATE) is CraftingTuning.MASTERWORK_STATE_VALUE:
        quality = quality_state_strings[4]
    else:
        quality = quality_state_strings[CraftingTuning.QUALITY_STATE_VALUE_MAP.get(jewelry_owner.get_state(CraftingTuning.QUALITY_STATE)).state_star_number]
    output('Last Jewelry created ID:{}'.format(last_jewelry_created.id))
    output('Is Jewelry Botched:{}'.format(is_botched))
    output('Is Jewelry Drained:{}'.format(is_drained))
    output('Jewelry Quality:{}'.format(quality))
    output('Jewelry Price:{}'.format(last_jewelry_created.current_value))
    automation_output('CraftingGetLastJewelryCreatedInfo; Status:Success, JewelryId:{}, IsBotched:{}, IsDrained:{}, Quality:{}, Price:{}'.format(last_jewelry_created.id, is_botched, is_drained, quality, last_jewelry_created.current_value))
    automation_output('CraftingGetLastJewelryCreatedInfo; Status:End')
    return True
