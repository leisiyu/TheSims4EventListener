from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from crafting.recipe import Phase
    from typing import *from crafting.crafting_tunable import CraftingTuningfrom crafting.recipe import Recipe, loggerfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom objects import PaintingState, PuzzleStatefrom objects.components import crafting_componentfrom objects.components.canvas_component import CanvasType, CanvasStateTypefrom objects.hovertip import TooltipFieldsCompletefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import TunedInstanceMetaclass, lock_instance_tunables, TuningClassMixinfrom sims4.tuning.tunable import TunableResourceKey, TunableEnumFlags, TunableList, TunableTuple, TunableReference, TunableRange, HasTunableFactory, AutoFactoryInit, OptionalTunable, Tunable, TunableVariantfrom sims4.utils import blueprintmethod, blueprintpropertyimport servicesimport sims4.resources
class PaintingTexture(TuningClassMixin, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RECIPE)):
    INSTANCE_TUNABLES = {'for_puzzles': Tunable(description='\n            If True, use this texture for puzzles. This enables the use of 8 reveal state levels instead of 4.\n            ', tunable_type=bool, default=False), 'texture': TunableResourceKey(None, resource_types=[sims4.resources.Types.TGA], allow_none=True), 'tests': TunableTestSet(), 'canvas_types': TunableEnumFlags(CanvasType, CanvasType.NONE, description='\n            The canvas types (generally, aspect ratios) with which this texture\n            may be used.\n            ')}

    @blueprintmethod
    def _tuning_loaded_callback(self):
        if self.texture:
            if self.for_puzzles:
                self._base_canvas_state = PuzzleState.from_key(self.texture)
            else:
                self._base_canvas_state = PaintingState.from_key(self.texture)
        else:
            self._base_canvas_state = None

    @blueprintmethod
    def apply_to_object(self, obj):
        obj.canvas_component.painting_state = self._base_canvas_state

class PaintingStyle(TuningClassMixin, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RECIPE)):
    INSTANCE_TUNABLES = {'_display_name': TunableLocalizedString(description='\n                The style name that will be displayed on the hovertip.\n                '), '_textures': TunableList(description='\n                A set of PaintingTextures from which one will be chosen for an\n                artwork created using this PaintingStyle.\n                ', tunable=TunableTuple(description='\n                    A particular painting texture and a weight indicating how\n                    often it will be picked from among available textures when\n                    this style is used.\n                    ', texture=TunableReference(description='\n                        A particular painting texture to use as part of this\n                        style.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=(PaintingTexture,), pack_safe=True), weight=TunableRange(float, 1.0, minimum=0, description='\n                        The relative likelihood (among available textures) that\n                        this one will be chosen.\n                        ')))}

    @blueprintproperty
    def display_name(self):
        return self._display_name

    @blueprintmethod
    def pick_texture(self, crafter, canvas_types:'CanvasType', random=None) -> 'PaintingTexture':
        if crafter is not None:
            resolver = SingleSimResolver(crafter.sim_info)
        weights = []
        for weighted_texture in self._textures:
            weight = weighted_texture.weight
            texture = weighted_texture.texture
            if not crafter is None:
                if texture.tests.run_tests(resolver):
                    weights.append((weight, texture))
            weights.append((weight, texture))
        texture = sims4.random.pop_weighted(weights, random=random)
        if texture is None and self._textures:
            for weighted_texture in self._textures:
                texture = weighted_texture.texture
                if canvas_types & texture.canvas_types:
                    logger.error('Tuning Error: No texture of {0} passed tests for {1}, defaulting to {2}', self._textures, crafter.sim_info, texture, owner='nbaker')
                    return texture
            texture = self._textures[0].texture
            logger.error('Tuning Error: No texture of {0} was correct type for {1}, defaulting to {2}', self._textures, crafter.sim_info, texture, owner='nbaker')
            return texture
        return texture

class PaintingRecipe(Recipe):
    INSTANCE_TUNABLES = {'painting_style': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.RECIPE), class_restrictions=(PaintingStyle,))}

    @blueprintmethod
    def _verify_tuning_callback(self):
        super()._verify_tuning_callback()
        if self._first_phases:
            if self.painting_style is None:
                logger.error('PaintingRecipe {} does not have a painting_style tuned.', self.__name__)
            if not self.has_canvas_product():
                logger.error("PaintingRecipe {}'s does not have a CanvasComponent product: {}", self.__name__, self.final_product_type)

    @blueprintproperty
    def style_display_name(self):
        return self.painting_style.display_name

    @blueprintmethod
    def has_canvas_product(self):

        def query(phase:'Phase') -> 'bool':
            object_info = phase.object_info
            if object_info is None or object_info.definition is None:
                return False
            elif object_info.definition.cls.tuned_components.canvas is not None:
                return True
            return False

        return self.query_phases(query)

    @blueprintmethod
    def pick_texture(self, crafted_object, crafter, random=None) -> 'PaintingTexture':
        canvas_types = crafted_object.canvas_component.canvas_types
        texture = self.painting_style.pick_texture(crafter, canvas_types, random=random)
        return texture

    @blueprintmethod
    def setup_crafted_object(self, crafted_object, crafter, is_final_product, random=None):
        super().setup_crafted_object(crafted_object, crafter, is_final_product)
        if crafted_object.canvas_component is not None:
            texture = self.pick_texture(crafted_object, crafter, random=random)
            if texture is None:
                logger.error('Tuning Error: No texture found for {0}', crafted_object, owner='nbaker')
                return
            reveal_level = crafted_object.canvas_component.painting_reveal_level
            if crafted_object.canvas_component.canvas_state_type == CanvasStateType.PUZZLE:
                crafted_object.canvas_component.set_painting_texture_id(texture.texture.instance)
            else:
                texture.apply_to_object(crafted_object)
            if reveal_level is not None:
                crafted_object.canvas_component.painting_reveal_level = reveal_level

    @blueprintmethod
    def update_hovertip(self, owner, crafter=None):
        owner.update_tooltip_field(TooltipFieldsComplete.simoleon_value, owner.current_value)
        owner.update_tooltip_field(TooltipFieldsComplete.style_name, self.style_display_name)
        owner.update_object_tooltip()
lock_instance_tunables(PaintingRecipe, multi_serving_name=None, push_consume=False)
class PaintByReferenceRecipe(PaintingRecipe):

    @blueprintmethod
    def _verify_tuning_callback(self):
        self._verify_recipe_tuning_callback()

    @blueprintmethod
    def setup_crafted_object(self, crafted_object, crafter, is_final_product, random=None):
        self._setup_crafted_object(crafted_object, crafter, is_final_product, random)
