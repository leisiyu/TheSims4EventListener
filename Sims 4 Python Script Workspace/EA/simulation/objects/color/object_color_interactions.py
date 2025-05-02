from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from event_testing.results import TestResultfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom objects.color.object_color_dialog import UiDialogObjectColorPickerfrom objects.color.object_color_enums import ObjectColorPickerPalette, ObjectColorPickerStylefrom objects.components.types import LIGHTING_COMPONENTfrom objects.lighting.lighting_utils import TunableLightTargetVariantfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, OptionalTunable, TunableEnumEntryimport sims4.log
class PickObjectColorImmediateInteraction(ImmediateSuperInteraction):

    class _ToLight(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'light_target': TunableLightTargetVariant(description='\n                Define the set of lights this operation applies to (e.g. All\n                Lights, This Room, All Candles, etc...)\n                ')}

        def test(self, target) -> 'TestResult':
            if target is None or not target.has_component(LIGHTING_COMPONENT):
                return TestResult(False, 'Not a light')
            return TestResult.TRUE

        def execute(self, interaction:'PickObjectColorImmediateInteraction') -> 'None':

            def _on_update(*, color, slider_value, **kwargs):
                for light_target in self.light_target.get_light_target_gen(interaction.target):
                    if not light_target.is_lighting_enabled():
                        pass
                    else:
                        light_target.set_user_intensity_override(slider_value)
                        light_target.set_light_color(color)

            color = interaction.target.get_light_color()
            if color is not None:
                (r, g, b, _) = sims4.color.to_rgba_as_int(color)
            else:
                r = g = b = sims4.color.MAX_INT_COLOR_VALUE
            intensity = interaction.target.get_user_intensity_overrides()
            dialog = UiDialogObjectColorPicker(interaction.target, r, g, b, slider_value=intensity, on_update=_on_update, palette=interaction.palette_colors, style=interaction.dialog_style)
            dialog.show_dialog()

    class _ToGhost(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {}

        def test(self, target) -> 'TestResult':
            if target is None or not (target.is_sim and target.is_ghost):
                return TestResult(False, 'Only ghost sims are supported.')
            return TestResult.TRUE

        def execute(self, interaction:'PickObjectColorImmediateInteraction') -> 'None':

            def _on_update(*, checkbox_state, color_item, **kwargs):
                if checkbox_state or color_item is None:
                    interaction.target.set_ghost_color(base_color=None, edge_color=None)
                else:
                    interaction.target.set_ghost_color(base_color=color_item.color[0], edge_color=color_item.color[1])

            color = interaction.target.ghost_base_color
            if color is not None:
                (r, g, b, _) = sims4.color.to_rgba_as_int(color)
            else:
                r = g = b = sims4.color.MAX_INT_COLOR_VALUE
            dialog = UiDialogObjectColorPicker(interaction.target, r, g, b, checkbox_state=color is None, on_update=_on_update, palette=interaction.palette_colors, style=interaction.dialog_style)
            dialog.show_dialog()

    INSTANCE_TUNABLES = {'object_color_operation': TunableVariant(description="\n            Define the operation we're going to execute. We can either apply\n            the color to a light or to a ghost sim.\n            ", to_light=_ToLight.TunableFactory(), to_ghost=_ToGhost.TunableFactory(), default='to_light'), 'palette_label': OptionalTunable(description='\n            Override the label of the color palette. \n            ', tunable=TunableLocalizedString()), 'slider_label': OptionalTunable(description='\n            Override the label of the slider. \n            ', tunable=TunableLocalizedString()), 'palette_colors': TunableEnumEntry(description='\n            The palette of colors to show in the dialog.\n            ', tunable_type=ObjectColorPickerPalette, default=ObjectColorPickerPalette.INVALID, invalid_enums=(ObjectColorPickerPalette.INVALID,)), 'dialog_style': TunableEnumEntry(description='\n            Formatting of the color picker dialog. \n            ', tunable_type=ObjectColorPickerStyle, default=ObjectColorPickerStyle.SIMPLE)}

    @classmethod
    def _test(cls, target, context, **kwargs) -> 'TestResult':
        result = cls.object_color_operation.test(target)
        if not result:
            return result
        return super()._test(target, context, **kwargs)

    def _run_interaction_gen(self, timeline) -> 'None':
        self.object_color_operation.execute(self)
