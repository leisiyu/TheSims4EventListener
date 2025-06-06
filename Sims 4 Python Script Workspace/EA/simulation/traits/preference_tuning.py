from __future__ import annotationsfrom interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableRange, TunableReference, TunableList, TunableSetfrom sims4.tuning.tunable_base import ExportModesimport servicesimport sims4from typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from cas.cas_preference_group import CasPreferenceGroup
    from traits.traits import Trait
    from cas.cas_preference_item import CasPreferenceItem
class PreferenceTuning:
    PREFERENCE_CAPACITY = TunableRange(description='\n        The preference limit on an object.            \n        ', tunable_type=int, minimum=1, default=15, export_modes=ExportModes.All)
    CAS_PREFERENCE_GROUPS = TunableSet(description='\n        The list of all preference groups.\n        ', tunable=TunableReference(description='\n            A single preference group.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAS_PREFERENCE_GROUP), pack_safe=True), export_modes=ExportModes.All)
    CAS_PREFERENCE_LIKE_RATE = TunableRange(description='\n        The rate of like preferences assigned at random in CAS (0: none, 1: all).            \n        ', tunable_type=float, minimum=0, maximum=1, default=0.75, export_modes=ExportModes.All)
    DECORATOR_CAREER_PREFERENCE_CATEGORIES = TunableList(description='\n        A list of preference categories that contain the set of preferences\n        pulled from clients that create constraints for the GP10 Decorator Career.\n        ', tunable=TunableReference(description='\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAS_PREFERENCE_CATEGORY), pack_safe=True, export_modes=ExportModes.All))
    CAS_PREFERENCE_MOLECULE_EMPTY_TOOLTIP = TunableLocalizedString(description='\n        The tooltip displayed over the preference molecule if the Sim does not have any set preferences.\n        ', export_modes=ExportModes.ClientBinary)
    CAS_PREFERENCES_CATEGORY_TAB_ICON = TunableIcon(description='\n        The icon shown in the Sim Preferences Selection Panel Tab for Categories.\n        ', export_modes=ExportModes.ClientBinary)
    CAS_PREFERENCES_CATEGORY_TAB_ICON_SELECTED = TunableIcon(description='\n        The icon shown in the Sim Preferences Selection Panel Tab for Categories.\n        ', export_modes=ExportModes.ClientBinary)
    CAS_PREFERENCES_CATEGORY_TAB_TOOLTIP = TunableLocalizedString(description='\n        The tooltip string shown in the Sim Preferences Selection Panel Tab for Categories.\n        ', export_modes=ExportModes.ClientBinary)
    PREFERENCE_SIM_PANEL_EMPTY = TunableLocalizedString(description='\n        The string shown in the Sim Preferences Panel when the Sim has no set preferences.\n        ', export_modes=ExportModes.ClientBinary)
    MAX_PREFERENCE_WARNING = TunableLocalizedString(description='\n        The string shown in the CAS when the Sim has reached the preference capacity.\n        ', export_modes=ExportModes.ClientBinary)
    RANDOMIZE_DIAG_TEXT = TunableLocalizedString(description='\n        The text within the warning dialog that is shown when traits are randomized.\n        ', export_modes=ExportModes.ClientBinary)
    RANDOMIZE_DIAG_TITLE = TunableLocalizedString(description='\n        The title within the warning dialog that is shown when traits are randomized.\n        ', export_modes=ExportModes.ClientBinary)
    RANDOMIZE_DIAG_TOOLTIP = TunableLocalizedString(description='\n        The tooltip string shown on the Randomize button in the Sim Preferences Selection Panel.\n        ', export_modes=ExportModes.ClientBinary)

    @classmethod
    def try_get_preference_group_for_preference_item(cls, item:'CasPreferenceItem') -> 'Optional[CasPreferenceGroup]':
        category = item.cas_preference_category
        for group in cls.CAS_PREFERENCE_GROUPS:
            if category in group.categories:
                return group

    @classmethod
    def try_get_preference_group_for_trait(cls, trait:'Trait') -> 'Optional[CasPreferenceGroup]':
        if trait.is_preference_trait:
            return cls.try_get_preference_group_for_preference_item(trait.preference_item)
