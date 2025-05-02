from objects.color.object_color_enums import ObjectColorPickerPalettefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableTuple, TunableColor, TunableList, OptionalTunable, TunableMapping, TunableEnumEntryfrom sims4.tuning.tunable_base import ExportModes
class TunableObjectColorTuple(TunableTuple):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(color=TunableList(description='\n                The list of colors associated with this selectable item.\n                It requires at least one color, but some use cases may\n                use multiple colors. \n                ', tunable=TunableColor.TunableColorRGBA(description='\n                    Tunable RGBA values used to set the color. Tuning the\n                    A value will not do anything as it is not used.\n                    '), minlength=1), name=TunableLocalizedString(description=' \n                The name of the color that appears when you mouse over it.\n                '))

class TunablePaletteEntryTuple(TunableTuple):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(colors=TunableList(description='\n                A list of all the different colors you can set the object to be.\n                ', tunable=TunableObjectColorTuple(), export_modes=ExportModes.ClientBinary), use_default=OptionalTunable(description='\n                An optional label that if provided will cause the dialog to display\n                an additional checkbox to allow the player to select the default\n                color.\n                ', tunable=TunableLocalizedString(), export_modes=ExportModes.All))

class ObjectColorTuning:
    OBJECT_COLOR_PALETTE = TunableMapping(description='\n        The dictionary of object color palette information.\n        ', key_type=TunableEnumEntry(description='\n            The key for the palette entry.\n            ', tunable_type=ObjectColorPickerPalette, default=ObjectColorPickerPalette.INVALID, invalid_enums=(ObjectColorPickerPalette.INVALID, ObjectColorPickerPalette.LIGHTING)), value_type=TunablePaletteEntryTuple(), export_modes=ExportModes.All, tuple_name='ObjectColorPaletteTuple')

    @classmethod
    def get_color_item(cls, palette:ObjectColorPickerPalette, color:int) -> TunablePaletteEntryTuple:
        if palette not in ObjectColorTuning.OBJECT_COLOR_PALETTE:
            return
        entry = ObjectColorTuning.OBJECT_COLOR_PALETTE[palette]
        for item in entry.colors:
            if item.color[0] == color:
                return item
