import build_buyimport enumimport fishing.fishing_dataimport objects.components.typesimport randomimport servicesimport simsimport sims4.logimport sims4.resourcesfrom collections import namedtuplefrom crafting.crafting_grab_serving_mixin import GrabServingMixinfrom crafting.recipe_helpers import get_recipes_matching_tagfrom event_testing.resolver import InteractionResolver, SingleActorAndObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSingle, ParticipantTypeSingleSim, ParticipantTypeActorTargetSim, ParticipantTypeObjectfrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom objects.components.state import StateComponentfrom objects.components.state_references import TunableStateValueReferencefrom objects.components.stolen_component import MarkObjectAsStolenfrom objects.components.stored_object_info_tuning import StoredObjectTypefrom objects.components.types import STORED_SIM_INFO_COMPONENT, STORED_OBJECT_INFO_COMPONENTfrom objects.helpers.create_object_helper import CreateObjectHelperfrom objects.hovertip import TooltipFieldsCompletefrom objects.placement.placement_helper import _PlacementStrategyLocation, _PlacementStrategySlotfrom postures import PostureTrackGroup, PostureTrackfrom sims4.localization import LocalizationHelperTuningfrom sims4.random import weighted_random_itemfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableList, TunableTuple, TunableEnumEntry, TunableVariant, OptionalTunable, Tunable, TunableSet, TunableRange, TunableFactoryfrom singletons import DEFAULTfrom tag import Tag, TunableTags, TunableTagfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog_notification import UiDialogNotificationfrom vfx import PlayEffectlogger = sims4.log.Logger('Creation')ObjectCreationParams = namedtuple('ObjectCreationParams', ('definition', 'setup_params'))
class CreationDataBase:
    multiple_objects_from_creation_data = False

    def get_definition(self, resolver):
        raise NotImplementedError

    def get_creation_params(self, resolver):
        return ObjectCreationParams(self.get_definition(resolver), {})

    def get_creation_params_list(self, resolver):
        raise NotImplementedError

    def setup_created_object(self, resolver, created_object, **setup_params):
        pass

    def get_source_object(self, resolver):
        pass

class _ObjectDefinition(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'definition': TunableReference(description='\n            The definition of the object that is created.\n            ', manager=services.definition_manager(), pack_safe=True)}

    def get_definition(self, resolver):
        return self.definition

class _ObjectDefinitionTested(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'fallback_definition': TunableReference(description='\n            Should no test pass, use this definition.\n            ', manager=services.definition_manager(), allow_none=True), 'definitions': TunableList(description='\n            A list of potential object definitions to use.\n            ', tunable=TunableTuple(weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this definition relative to other\n                    definitions in this list.\n                    '), definition=TunableReference(description='\n                    The definition of the object to be created.\n                    ', manager=services.definition_manager(), pack_safe=True)))}

    def get_definition(self, resolver):
        definition = weighted_random_item([(pair.weight.get_multiplier(resolver), pair.definition) for pair in self.definitions])
        if definition is not None:
            return definition
        return self.fallback_definition

class _RecipeBase(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'show_crafted_by_text': Tunable(description='\n            Show crafted by text on the tooltip of item created by this recipe. \n            Will not be visible if crafter is not a sim.\n            ', tunable_type=bool, default=True)}

    def setup_created_object(self, resolver, created_object, chosen_creation_data=DEFAULT):
        from crafting.crafting_process import CraftingProcess
        if chosen_creation_data is DEFAULT or chosen_creation_data is None:
            logger.warn('chosen_creation_data not passed in!')
            return
        crafter = resolver.get_participant(ParticipantType.Actor)
        if crafter.is_sim:
            crafting_process = CraftingProcess(crafter=crafter, recipe=chosen_creation_data)
        else:
            crafting_process = CraftingProcess(crafter=None, recipe=chosen_creation_data)
        if not self.show_crafted_by_text:
            crafting_process.remove_crafted_by_text()
        crafting_process.setup_crafted_object(created_object, is_final_product=True, random=random.Random())

    def get_creation_params(self, resolver):
        raise NotImplementedError

    def get_definition(self, resolver):
        raise NotImplementedError

class _RecipeByTag(_RecipeBase, CreationDataBase):

    @TunableFactory.factory_option
    def recipe_factory_tuning(pack_safe=False):
        return {'recipe_tag': TunableTag(description='\n                The recipe tag to use to create the object.\n                ', filter_prefixes=('Recipe',), pack_safe=pack_safe)}

    def choose_recipe(self):
        filtered_defs = get_recipes_matching_tag(self.recipe_tag)
        if not filtered_defs:
            logger.warn('_RecipeByTag could not find a recipe with the tag {}.', self.recipe_tag, owner='skorman')
            return
        return random.choice(filtered_defs)

    def get_creation_params(self, resolver):
        recipe = self.choose_recipe()
        return ObjectCreationParams(recipe.final_product.definition, {'chosen_creation_data': recipe})

    def get_definition(self, resolver):
        return self.get_creation_params(resolver).definition

class _RecipeDefinition(_RecipeBase, CreationDataBase):

    @TunableFactory.factory_option
    def recipe_factory_tuning(pack_safe=False):
        return {'recipe': TunableReference(description='\n                The recipe to use to create the object.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), pack_safe=pack_safe)}

    def get_creation_params(self, resolver):
        return ObjectCreationParams(self.get_definition(resolver), {'chosen_creation_data': self.recipe})

    def get_definition(self, resolver):
        return self.recipe.final_product.definition

class _RandomRecipeBase:

    def get_definition(self, resolver):
        logger.error('\n            get_definition is being called in _RandomRecipeBase, this \n            should not be a standard behavior when creating an object. \n            get_creation_params is the expected way to get the definition\n            ', owner='jdimailig')
        return self.get_creation_params(resolver).definition

    def setup_created_object(self, resolver, created_object, chosen_creation_data=DEFAULT):
        if chosen_creation_data is DEFAULT:
            logger.error('chosen_creation_data not passed in!')
            return
        (recipe_factory, recipe) = chosen_creation_data
        if recipe_factory is None or recipe is None:
            return
        recipe_factory.setup_created_object(resolver, created_object, chosen_creation_data=recipe)

    def get_creation_params(self, resolver):
        raise NotImplementedError

class _RandomWeightedTaggedRecipe(_RandomRecipeBase, CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'weighted_recipe_tags': TunableList(description='\n            A list of weighted list of recipe tags that can be available for \n            recipe creation.\n            ', tunable=TunableTuple(description='\n                The weighted recipe tag.\n                ', recipe_tag=_RecipeByTag.TunableFactory(recipe_factory_tuning={'pack_safe': True}), weight=TunableMultiplier.TunableFactory()), minlength=1)}

    def get_creation_params(self, resolver):
        weighted_recipe_creation_data = list((weighted_recipe.weight.get_multiplier(resolver), weighted_recipe.recipe_tag) for weighted_recipe in self.weighted_recipe_tags)
        recipe_factory = weighted_random_item(weighted_recipe_creation_data)
        recipe = recipe_factory.choose_recipe()
        return ObjectCreationParams(recipe.final_product.definition, {'chosen_creation_data': (recipe_factory, recipe)})

class _RandomWeightedRecipe(_RandomRecipeBase, CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'weighted_recipes': TunableList(description='\n            A list of weighted list of recipes that can be available for recipe creation.\n            ', tunable=TunableTuple(description='\n                The weighted recipe.\n                ', recipe=_RecipeDefinition.TunableFactory(recipe_factory_tuning={'pack_safe': True}), weight=TunableMultiplier.TunableFactory()), minlength=1)}

    def get_creation_params(self, resolver):
        weighted_recipe_creation_data = list((weighted_recipe.weight.get_multiplier(resolver), weighted_recipe.recipe) for weighted_recipe in self.weighted_recipes)
        recipe_factory = weighted_random_item(weighted_recipe_creation_data)
        return ObjectCreationParams(recipe_factory.get_definition(resolver), {'chosen_creation_data': (recipe_factory, recipe_factory.recipe)})

class _CloneObject(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):

    class _ParticipantObject(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                Used to clone a participant object.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object)}

        def get_object(self, resolver):
            return resolver.get_participant(self.participant)

    class _SlottedObject(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'slotted_to_participant': TunableTuple(description='\n                Used to clone an object slotted to a participant.\n                ', parent_object_participant=TunableEnumEntry(description='\n                    The participant object which will contain the specified\n                    slot where the object to be cloned is slotted.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Object), parent_slot_type=TunableReference(description='\n                    A particular slot type where the cloned object can be found.  The\n                    first slot of this type found on the source_object will be used.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)))}

        def get_object(self, resolver):
            parent_object = resolver.get_participant(self.slotted_to_participant.parent_object_participant)
            if parent_object is not None:
                for runtime_slot in parent_object.get_runtime_slots_gen(slot_types={self.slotted_to_participant.parent_slot_type}, bone_name_hash=None):
                    if runtime_slot.empty:
                        pass
                    else:
                        return runtime_slot.children[0]

    FACTORY_TUNABLES = {'source_object': TunableVariant(description='\n            Where the object to be cloned can be found.\n            ', is_participant=_ParticipantObject.TunableFactory(), slotted_to_participant=_SlottedObject.TunableFactory(), default='slotted_to_participant'), 'definition_override': OptionalTunable(description='\n            Override to specify a different definition than that of the object\n            being cloned.\n            ', tunable=TunableReference(description='\n                The definition of the object that is created.\n                ', manager=services.definition_manager()))}

    def get_definition(self, resolver):
        if self.definition_override is not None:
            return self.definition_override
        else:
            source_object = self.get_source_object(resolver)
            if source_object is not None:
                return source_object.definition

    def get_source_object(self, resolver):
        return self.source_object.get_object(resolver)

class _CreateAllObjectsWithTags(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tags_list': TunableTags(description='\n            Any object with one of these tags will be created.\n            ', minlength=1)}
    multiple_objects_from_creation_data = True

    def get_creation_params(self, resolver):
        logger.error('\n            get_creation_params should never be called for creation_data that is \n            creating multiple objects. get_creation_params_list should be used instead\n            ', owner='cparrish')
        raise NotImplementedError

    def get_creation_params_list(self, resolver):
        multi_object_creation_params = []
        for definition in services.definition_manager().get_definitions_for_tags_gen(self.tags_list):
            object_creation_params = ObjectCreationParams(definition, {})
            multi_object_creation_params.append(object_creation_params)
        return multi_object_creation_params

    def get_definition(self, resolver):
        logger.error('\n            get_definition is being called in _CreateAllObjectsWithTags, this \n            should not be a standard behavior when creating an object. \n            get_creation_params is the expected way to get the list of definitions\n            ', owner='cparrish')
        return self.get_creation_params(resolver).definition

class _CreatePhotoObject(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Used to create photo of a participant object.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)}

    def get_definition(self, resolver):
        object_to_shoot = resolver.get_participant(self.participant)
        if hasattr(object_to_shoot, 'get_photo_definition'):
            photo_definition = object_to_shoot.get_photo_definition()
            if photo_definition is not None:
                return photo_definition
        logger.error('{} create object basic extra tries to create a photo of {}, but none of the component provides get_photo_definition function', resolver, object_to_shoot, owner='cjiang')

    def setup_created_object(self, resolver, created_object, **__):
        crafter = resolver.get_participant(ParticipantType.Actor)
        created_object.add_dynamic_component(STORED_SIM_INFO_COMPONENT, sim_id=crafter.id)

class _FishingDataFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Participant on which we will get the fishing data information \n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object)}

    def get_fish_definition(self, resolver):
        target = resolver.get_participant(self.participant)
        if target is None:
            logger.error('{} create object tried to create an object using fishing data, but the participant {} is None.', resolver, self.participant, owner='mkartika')
            return
        fishing_location_component = target.fishing_location_component
        if fishing_location_component is None:
            logger.error('{} create object tried to create an object using fishing data on {}, but has no tuned Fishing Location Component.', resolver, target, owner='mkartika')
            return
        fishing_data = fishing_location_component.fishing_data
        if fishing_data is None:
            logger.error('{} create object tried to create an object using fishing data on {}, but has no tuned Fishing Data.', resolver, target, owner='shouse')
            return
        else:
            fish = fishing_data.choose_fish(resolver, require_bait=False)
            if fish is None:
                logger.error('{} create object tried to create an object using fishing data on {}, but caught no fish.', resolver, target, owner='mkartika')
                return
        return fish

class _FishingDataFromReference(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'fishing_data': fishing.fishing_data.TunableFishingDataReference(description='\n            Fishing data reference.\n            ')}

    def get_fish_definition(self, resolver):
        fishing_data = self.fishing_data
        if fishing_data is None:
            logger.error('{} create object tried to create an object without fishing data, so caught no fish.', resolver, owner='shouse')
            return
        else:
            fish = self.fishing_data.choose_fish(resolver, require_bait=False)
            if fish is None:
                logger.error('{} create object tried to create an object using fishing data {}, but caught no fish.', resolver, self.fishing_data, owner='mkartika')
                return
        return fish

class TunableFishingDataTargetVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, participant=_FishingDataFromParticipant.TunableFactory(), reference=_FishingDataFromReference.TunableFactory(), default='participant', **kwargs)

class _CreateObjectFromFishingData(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'source': TunableFishingDataTargetVariant(description='\n            Source on which we will get the fishing data information \n            ')}

    def get_definition(self, resolver):
        return self.source.get_fish_definition(resolver)

class _CreateObjectFromStoredObjectInfo(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'stored_object_info_participant': TunableEnumEntry(description='\n            The Sim participant of this interaction which contains the stored\n            object info that is used to create this object.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'stored_object_type': TunableEnumEntry(description='\n            The type of object being stored. This will be used to retrieve the\n            stored object from the Stored Object Info Component of the target.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID, invalid_enums=(StoredObjectType.INVALID,))}

    def get_definition(self, resolver):
        source_object = resolver.get_participant(self.stored_object_info_participant)
        if source_object is None:
            logger.error('{} create object basic extra tried to create an obj using stored object info, but the participant is None.', resolver, owner='jwilkinson')
            return
        stored_obj_info_component = source_object.get_component(STORED_OBJECT_INFO_COMPONENT)
        if stored_obj_info_component is None:
            logger.error("{} create object basic extra tried to create an obj using stored object info, but the participant doesn't have a stored object info component.", resolver, owner='jwilkinson')
            return
        definition_id = stored_obj_info_component.get_stored_object_info_definition_id(self.stored_object_type)
        definition = services.definition_manager().get(definition_id)
        return definition

    def setup_created_object(self, resolver, created_object, **__):
        source_object = resolver.get_participant(self.stored_object_info_participant)
        stored_obj_info_component = source_object.get_component(STORED_OBJECT_INFO_COMPONENT)
        if stored_obj_info_component is None:
            logger.error("{} create object basic extra tried to setup a created obj using stored object info, but the participant doesn't have a stored object info component.", resolver, owner='jwilkinson')
            return
        custom_name = stored_obj_info_component.get_stored_object_info_custom_name(self.stored_object_type)
        if custom_name is not None:
            created_object.set_custom_name(custom_name)
        states = stored_obj_info_component.get_stored_object_info_states(self.stored_object_type)
        if states:
            state_manager = services.get_instance_manager(sims4.resources.Types.OBJECT_STATE)
            for (state_guid, state_value_guid) in states:
                state = state_manager.get(state_guid)
                if state is None:
                    pass
                else:
                    state_value = state_manager.get(state_value_guid)
                    if state_value is None:
                        pass
                    else:
                        created_object.set_state(state, state_value, immediate=True)

class _RandomFromTags(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'filter_tags': TunableTags(description='\n            Define tags to try and create the object. Picks randomly from\n            objects with these tags.\n            ', minlength=1)}

    def get_definition(self, resolver):
        definition_manager = services.definition_manager()
        filtered_defs = list(definition_manager.get_definitions_for_tags_gen(self.filter_tags))
        if len(filtered_defs) > 0:
            return random.choice(filtered_defs)
        logger.error('{} create object basic extra tries to find object definitions tagged as {} , but no object definitions were found.', resolver, self.filter_tags, owner='jgiordano')

class _CraftableServing(CreationDataBase, GrabServingMixin, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'serving_source': TunableEnumEntry(description='\n            The source of the \n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_definition(self, resolver):
        recipe = self._get_recipe(resolver)
        if recipe is None:
            return
        return recipe.final_product_definition

    def _get_recipe(self, resolver):
        target = resolver.get_participant(self.serving_source)
        if target is None or not target.has_component(objects.components.types.CRAFTING_COMPONENT):
            logger.error('{} does not have a crafting component!', target)
            return
        recipe = target.get_recipe()
        if self.use_linked_recipe_mapping:
            interaction = resolver.interaction
            if interaction is not None:
                return recipe.get_linked_recipe(interaction.get_interaction_type())
        return recipe.get_base_recipe()

    def setup_created_object(self, resolver, created_object, **__):
        target = resolver.get_participant(self.serving_source)
        self._setup_crafted_object(self._get_recipe(resolver), target, created_object)

class _UrnstoneDefinitionTested(CreationDataBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'fallback_definition': TunableReference(description='\n            Should no test pass, use this definition.\n            ', manager=services.definition_manager(), allow_none=True), 'definitions': TunableList(description='\n            A list of potential object definitions to use.\n            ', tunable=TunableTuple(weight=TunableMultiplier.TunableFactory(description='\n                The weight of this definition relative to other\n                definitions in this list.\n                '), definition=TunableReference(description='\n                    The definition of the object to be created.\n                    ', manager=services.definition_manager(), pack_safe=True)))}

    def get_definition(self, resolver):
        will_service = services.get_will_service()
        if will_service is not None:
            definition_manager = services.definition_manager()
            sim = resolver.get_participant(ParticipantType.Actor)
            if sim is not None:
                sim_will = will_service.get_sim_will(sim.sim_id)
                if sim_will is not None:
                    def_id = sim_will.get_burial_preference()
                    if def_id is not None:
                        definition = definition_manager.get(def_id)
                        if definition is not None:
                            return definition
        definition = weighted_random_item([(pair.weight.get_multiplier(resolver), pair.definition) for pair in self.definitions])
        if definition is not None:
            return definition
        return self.fallback_definition

class TunableObjectCreationDataVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, definition=_ObjectDefinition.TunableFactory(), definition_tested=_ObjectDefinitionTested.TunableFactory(), recipe=_RecipeDefinition.TunableFactory(), recipe_by_tag=_RecipeByTag.TunableFactory(), random_recipe=_RandomWeightedRecipe.TunableFactory(), random_recipe_by_tags=_RandomWeightedTaggedRecipe.TunableFactory(), serving=_CraftableServing.TunableFactory(), clone_object=_CloneObject.TunableFactory(), create_photo_object=_CreatePhotoObject.TunableFactory(), random_by_tags=_RandomFromTags.TunableFactory(), from_stored_object_info=_CreateObjectFromStoredObjectInfo.TunableFactory(), from_fishing_data=_CreateObjectFromFishingData.TunableFactory(), urnstone_definition_tested=_UrnstoneDefinitionTested.TunableFactory(), default='definition', **kwargs)

class StateInitializationPreference(enum.Int):
    DEFAULT = 0
    PRE_ADD = 1
    POST_ADD = 2

class ObjectCreationMixin:
    INVENTORY = 'inventory'
    CARRY = 'carry'
    INSTANCE_TUNABLES = FACTORY_TUNABLES = {'creation_data': TunableObjectCreationDataVariant(description='\n            Define the object to create.\n            '), 'initial_states': TunableList(description='\n            A list of states to apply to the object when it is created.\n            ', tunable=TunableTuple(description='\n                The state to apply and optional tests to decide if the state\n                should apply.\n                ', state=TunableStateValueReference(), tests=OptionalTunable(description='\n                    If enabled, the state will only get set on the created\n                    object if the tests pass. Note: These tests can not be\n                    performed on the newly created object.\n                    ', tunable=TunableTestSet()), timing=TunableEnumEntry(description='\n                    The timing for when the state should be applied on the object:\n                    DEFAULT: Will be done as soon as the object is created, and re-applied right after it is tracked.\n                    PRE_ADD: As soon as the object is created, before it is tracked.\n                    POST_ADD: Right after the object gets tracked.\n                    \n                    Most existing instances use DEFAULT for legacy reasons, \n                    but POST_ADD should be sufficient for most new instances. \n                    Please ask a GPE if you are not sure which option to use.\n                    ', tunable_type=StateInitializationPreference, default=StateInitializationPreference.DEFAULT))), 'destroy_on_placement_failure': Tunable(description="\n            If checked, the created object will be destroyed on placement failure.\n            If unchecked, the created object will be placed into an appropriate\n            inventory on placement failure if possible.  If THAT fails, object\n            will be destroyed.\n            By default it goes into location target's inventory, you can use \n            fallback_location_target_override to make the created object go to\n            another participant's inventory.\n            ", tunable_type=bool, default=False), 'owner_sim': TunableEnumEntry(description='\n            The participant Sim whose household should own the object. Leave this\n            as Invalid to not assign ownership.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantType.Invalid), 'location': TunableVariant(description='\n            Where the object should be created.\n            ', default='position', position=_PlacementStrategyLocation.TunableFactory(), slot=_PlacementStrategySlot.TunableFactory(), inventory=TunableTuple(description='\n                An inventory based off of the chosen Participant Type.\n                ', locked_args={'location': INVENTORY}, location_target=TunableEnumEntry(description='\n                    "The owner of the inventory the object will be created in."\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor), mark_object_as_stolen_from_career=Tunable(description='\n                    Marks the object as stolen from a career by the tuned location_target participant.\n                    This should only be checked if this basic extra is on a CareerSuperInteraction.\n                    ', tunable_type=bool, default=False), place_in_hidden_inventory=Tunable(description='\n                    If True, the object is placed in the hidden inventory rather than the user-facing inventory.\n                    ', tunable_type=bool, default=False), place_in_hh_inventory=Tunable(description='\n                    If True, the object is placed in the household inventory rather than the user-facing inventory.\n                    ', tunable_type=bool, default=False)), carry=TunableTuple(description='\n                Carry the object. Note: This expects an animation in the\n                interaction to trigger the carry.\n                ', locked_args={'location': CARRY}, carry_track_override=OptionalTunable(description='\n                    If enabled, specify which carry track the Sim must use to carry the\n                    created object.\n                    ', tunable=TunableEnumEntry(description='\n                        Which hand to carry the object in.\n                        ', tunable_type=PostureTrack, default=PostureTrack.RIGHT)))), 'reserve_object': OptionalTunable(description='\n            If this is enabled, the created object will be reserved for use by\n            the set Sim.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)), 'fallback_location_target_override': OptionalTunable(description="\n            This will be ignored if destroy_on_placement_failure is checked. If this is enabled, we override fallback\n            location target.\n            Currently this is used when location target is different with the target whose inventory we want this\n            created object to go into. For example we want to create an object near another object but we want this\n            object to go to actor's inventory when placement fails.\n            ", tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor)), 'notification_inventory': OptionalTunable(description='\n            The notification to show when created object is placed in an inventory.\n            ', tunable=TunableTuple(participant_inventory=UiDialogNotification.TunableFactory(description="\n                    The notification to show when created object is placed in a participant's (such as sim's) inventory.\n                    "), household_inventory=UiDialogNotification.TunableFactory(description='\n                    The notification to show when created object is placed in a household inventory.\n                    '))), 'success_loots': OptionalTunable(description='\n            A list of loots to award if the object is successfully placed.\n            To reference the created object, use the Object participant.\n            The Actor participant is the active sim.\n            ', tunable=TunableList(tunable=TunableReference(description='\n                    Tunable Loot awarded if the object is successfully placed.\n                    ', manager=services.get_instance_manager(Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))), 'temporary_tags': OptionalTunable(description='\n            If enabled, these Tags are added to the created object and DO NOT\n            persist.\n            ', tunable=TunableSet(description='\n                A set of temporary tags that are added to the created object.\n                These tags DO NOT persist.\n                ', tunable=TunableEnumEntry(description='\n                    A tag that is added to the created object. This tag DOES\n                    NOT persist.\n                    ', tunable_type=Tag, default=Tag.INVALID), minlength=1)), 'require_claim': Tunable(description="\n            If checked, the created object will be claimed, and will need to\n            be reclaimed on load.  If it isn't reclaimed on load, the object\n            will be destroyed.\n            ", tunable_type=bool, default=False), 'set_sim_as_owner': Tunable(description='\n            If checked and owner_sim is set, the sim will also be set on the\n            object ownership component and not just the household.\n            ', tunable_type=bool, default=False), 'set_sim_as_inventory_owner': Tunable(description='\n            Behaves like set sim as owner, but for all the objects created by default in objects inventory.\n            ', tunable_type=bool, default=False), 'set_value_to_crafted_tooltip': Tunable(description='\n            If checked, the value will be set to the tooltip if this item has\n            a crafting component.\n            ', tunable_type=bool, default=True), 'spawn_vfx': OptionalTunable(description='\n            If enabled, play the one-shot VFX when the object is created in world.\n            ', tunable=PlayEffect.TunableFactory())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resolver = None
        self._object_helper = None
        self._assigned_ownership = set()
        self._definition = None
        self._setup_params = None

    def initialize_helper(self, resolver, post_add=None, creation_params=None):

        def initialize_created_obj(obj):
            self._setup_created_object(obj, creation_stage=StateInitializationPreference.PRE_ADD)

        self._assigned_ownership.clear()
        self.resolver = resolver
        reserved_sim = None
        if self.reserve_object is not None:
            reserved_sim_info = self.resolver.get_participant(self.reserve_object)
            reserved_sim = reserved_sim_info.get_sim_instance()
        interaction = None
        if isinstance(self.resolver, InteractionResolver):
            interaction = self.resolver.interaction
        if creation_params is None:
            if self.creation_data.multiple_objects_from_creation_data:
                logger.error('creation_params should only be None iff we are not creating multiple objects.\n{}', type(self.creation_data))
            (self._definition, self._setup_params) = self.creation_data.get_creation_params(resolver)
        else:
            (self._definition, self._setup_params) = creation_params
        self._object_helper = CreateObjectHelper(reserved_sim, self._definition, interaction, object_to_clone=self.creation_data.get_source_object(self.resolver), init=initialize_created_obj, post_add=post_add)

    @property
    def definition(self):
        return self.creation_data.get_definition(self.resolver)

    def create_object(self, resolver, creation_params=None):
        if self.creation_data.multiple_objects_from_creation_data and creation_params is None:
            logger.error('When creating multiple objects, creation_params kwarg must be defined.\nCreationData:\n{}', self.creation_data)
        self.initialize_helper(resolver, post_add=self._try_place_object, creation_params=creation_params)
        created_object = self._object_helper.create_object()
        self._object_helper = None
        return created_object

    def _try_place_object(self, created_object):
        if not self._place_object(created_object):
            self._on_placement_failure(created_object)
        elif self.success_loots:
            resolver = SingleActorAndObjectResolver(services.active_sim_info(), created_object, self)
            for loot in self.success_loots:
                loot.apply_to_resolver(resolver)

    def _on_placement_failure(self, created_object):
        pass

    def _setup_created_object(self, created_object, creation_stage):
        self.creation_data.setup_created_object(self.resolver, created_object, **self._setup_params)
        if self.owner_sim != ParticipantType.Invalid:
            owner_sim = self.resolver.get_participant(self.owner_sim)
            if owner_sim is not None and owner_sim.is_sim:
                created_object.update_ownership(owner_sim, make_sim_owner=self.set_sim_as_owner, make_sim_inventory_owner=self.set_sim_as_inventory_owner)
                self._assigned_ownership.add(created_object.id)
        for initial_state in self.initial_states:
            if created_object.state_component is None:
                created_object.add_component(StateComponent(created_object))
            if not initial_state.tests is None:
                if initial_state.tests.run_tests(self.resolver):
                    is_valid_creation_stage = initial_state.timing == StateInitializationPreference.DEFAULT or initial_state.timing == creation_stage
                    if created_object.has_state(initial_state.state.state) and is_valid_creation_stage:
                        created_object.set_state(initial_state.state.state, initial_state.state, from_creation=True)
            is_valid_creation_stage = initial_state.timing == StateInitializationPreference.DEFAULT or initial_state.timing == creation_stage
            if created_object.has_state(initial_state.state.state) and is_valid_creation_stage:
                created_object.set_state(initial_state.state.state, initial_state.state, from_creation=True)
        if self.temporary_tags is not None:
            created_object.append_tags(self.temporary_tags)
        if created_object.has_component(objects.components.types.CRAFTING_COMPONENT):
            created_object.crafting_component.update_simoleon_tooltip()
            created_object.crafting_component.update_quality_tooltip()
            if self.set_value_to_crafted_tooltip:
                created_object.update_tooltip_field(TooltipFieldsComplete.simoleon_value, created_object.current_value)
        created_object.update_object_tooltip()
        if self.require_claim:
            created_object.claim()

    def _get_ignored_object_ids(self):
        pass

    def _place_object_no_fallback(self, created_object):
        if hasattr(self.location, 'try_place_object'):
            ignored_object_ids = self._get_ignored_object_ids()
            return self.location.try_place_object(created_object, self.resolver, ignored_object_ids=ignored_object_ids)
        elif self.location.location == self.CARRY:
            return True
        return False

    def _get_fallback_location_target(self, created_object):
        if self.fallback_location_target_override is not None:
            target_override = self.resolver.get_participant(self.fallback_location_target_override)
            if target_override is not None:
                return target_override
            logger.error('Fallback location target override for participant {} and created object {} is none.\n                                Invalid participant?', self.fallback_location_target_override, created_object)
        if hasattr(self.location, '_get_reference_objects_gen'):
            for obj in self.location._get_reference_objects_gen(created_object, self.resolver):
                return obj
        return self.resolver.get_participant(self.location.location_target)

    def _place_object(self, created_object):
        self._setup_created_object(created_object, creation_stage=StateInitializationPreference.POST_ADD)
        if self._place_object_no_fallback(created_object):
            if self.spawn_vfx is not None:
                effect = self.spawn_vfx(created_object)
                effect.start_one_shot()
            return True
        if not self.destroy_on_placement_failure:
            participant = self._get_fallback_location_target(created_object)
            if isinstance(participant, sims.sim_info.SimInfo):
                participant = participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            location_type = getattr(self.location, 'location', None)
            if participant.is_sim and location_type == self.INVENTORY and self.location.mark_object_as_stolen_from_career:
                interaction = self.resolver.interaction
                if interaction is None:
                    logger.error('Mark Object As Stolen From Career is checked on CreateObject loot {}. \n                                    This should only be check on basic extra in a CareerSuperInteraction.', self)
                    return False
                career_uid = interaction.interaction_parameters.get('career_uid')
                if career_uid is not None:
                    career = interaction.sim.career_tracker.get_career_by_uid(career_uid)
                    if career is not None:
                        name_data = career.get_career_location().get_persistable_company_name_data()
                        text = None
                        guid = None
                        if isinstance(name_data, str):
                            text = name_data
                        else:
                            guid = name_data
                        MarkObjectAsStolen.mark_object_as_stolen(created_object, stolen_from_text=text, stolen_from_career_guid=guid)
                else:
                    logger.error('Interaction {} is tuned with a CreateObject basic extra that has mark_object_as_stolen_from_career as True,\n                                    but is not a CareerSuperInteraction. This is not supported.', interaction)
            if not self.location.place_in_hh_inventory:
                if self.owner_sim != ParticipantType.Invalid and created_object.id not in self._assigned_ownership:
                    if participant.is_sim:
                        participant_household_id = participant.household.id
                    else:
                        participant_household_id = participant.get_household_owner_id()
                    created_object.set_household_owner_id(participant_household_id)
                    self._assigned_ownership.add(created_object.id)
                if participant.inventory_component.player_try_add_object(created_object, hidden=location_type == self.INVENTORY and self.location.place_in_hidden_inventory):
                    if self.notification_inventory:
                        interaction = self.resolver.interaction
                        if interaction is not None:
                            interaction.interaction_parameters['created_target_id'] = created_object.id
                        obj_name = [LocalizationHelperTuning.get_object_name(created_object)]
                        notification = self.notification_inventory.participant_inventory(participant, self.resolver)
                        notification.show_dialog(additional_tokens=(LocalizationHelperTuning.get_bulleted_list((None,), obj_name),))
                    return True
            actor = self.resolver.get_participant(ParticipantType.Actor)
            sim = actor if participant is not None and (participant.inventory_component is not None and (created_object.inventoryitem_component is not None and location_type == self.INVENTORY)) and actor is not None and actor.is_sim else None
            if self.location.place_in_hh_inventory:
                owning_household = services.owning_household_of_active_lot()
                if owning_household is not None:
                    for sim_info in owning_household.sim_info_gen():
                        if sim_info.is_instanced():
                            sim = sim_info.get_sim_instance()
                            break
            if not sim.is_npc:
                try:
                    created_object.set_household_owner_id(sim.household.id)
                    if build_buy.move_object_to_household_inventory(created_object):
                        if self.notification_inventory:
                            interaction = self.resolver.interaction
                            if interaction is not None:
                                interaction.interaction_parameters['created_target_id'] = created_object.id
                            obj_name = [LocalizationHelperTuning.get_object_name(created_object)]
                            notification = self.notification_inventory.household_inventory(sim, self.resolver)
                            notification.show_dialog(additional_tokens=(LocalizationHelperTuning.get_bulleted_list((None,), obj_name),))
                        return True
                    logger.error('Creation: Failed to place object {} in household inventory.', created_object, owner='rmccord')
                except KeyError:
                    pass
        return False

class ObjectCreation(ObjectCreationMixin, HasTunableSingletonFactory, AutoFactoryInit):
    pass

class ObjectCreationOp(ObjectCreationMixin, BaseLootOperation):
    FACTORY_TUNABLES = {'creation_data': TunableObjectCreationDataVariant(description='\n            Define the object to create\n            ', all_objects_with_tag=_CreateAllObjectsWithTags.TunableFactory()), 'quantity': TunableRange(description='\n            The number of objects that will be created.\n            ', tunable_type=int, default=1, minimum=1, maximum=10)}

    def __init__(self, *, creation_data, initial_states, destroy_on_placement_failure, owner_sim, location, reserve_object, temporary_tags, quantity, notification_inventory, success_loots, fallback_location_target_override, require_claim, set_sim_as_owner, set_sim_as_inventory_owner, set_value_to_crafted_tooltip, spawn_vfx, **kwargs):
        super().__init__(**kwargs)
        self.creation_data = creation_data
        self.initial_states = initial_states
        self.destroy_on_placement_failure = destroy_on_placement_failure
        self.owner_sim = owner_sim
        self.location = location
        self.reserve_object = reserve_object
        self.temporary_tags = temporary_tags
        self.quantity = quantity
        self.notification_inventory = notification_inventory
        self.success_loots = success_loots
        self.fallback_location_target_override = fallback_location_target_override
        self.set_value_to_crafted_tooltip = set_value_to_crafted_tooltip
        self.require_claim = require_claim
        self.set_sim_as_owner = set_sim_as_owner
        self.set_sim_as_inventory_owner = set_sim_as_inventory_owner
        self.spawn_vfx = spawn_vfx

    def _apply_to_subject_and_target(self, subject, target, resolver):
        for _ in range(self.quantity):
            if not self.creation_data.multiple_objects_from_creation_data:
                self.create_object(resolver)
            else:
                self._create_objects(resolver)

    def _create_objects(self, resolver):
        creation_params_list = self.creation_data.get_creation_params_list(resolver)
        for creation_params in creation_params_list:
            self.create_object(resolver, creation_params=creation_params)

    def _on_placement_failure(self, obj):
        obj.destroy(cause='Object failed placement.')
