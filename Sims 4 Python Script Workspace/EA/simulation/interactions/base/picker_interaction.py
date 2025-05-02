from __future__ import annotationsfrom interactions.utils.display_name import TunableDisplayNameVariantfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.base.interaction import Interaction
    from objects import base_interactions
    from objects.definition import Definition
    from objects.game_object import GameObjectfrom _collections import defaultdictimport functoolsimport randomfrom autonomy.autonomy_modifier import OffLotAutonomyRulesfrom autonomy.autonomy_preference import ObjectPreferenceTagfrom build_buy import get_object_in_household_inventory, find_objects_in_household_inventoryfrom crafting.crafting_tunable import CraftingTuningfrom event_testing.resolver import SingleObjectResolver, InteractionResolver, SingleSimResolver, DoubleSimAndObjectResolver, SingleActorAndObjectResolverfrom event_testing.tests import TunableTestSet, TunableGlobalTestSetfrom filters.tunable import TunableSimFilterfrom fishing.fishing_tuning import FishingTuningfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.object_picker_mixins import GigObjectsPickerMixin, TunableObjectTaggedObjectFilterTestSet, StyleTagObjectPickerMixinfrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import ANYWHEREfrom interactions.context import InteractionContext, QueueInsertStrategy, InteractionSourcefrom interactions.picker.picker_enums import PickerInteractionDeliveryMethod, SimPickerLinkContinuation, PriceOption, DuplicateObjectsSuppressionTypefrom interactions.picker.picker_pie_menu_interaction import _PickerPieMenuProxyInteractionfrom interactions.picker.purchase_picker_service import PurchasePickerGroupfrom interactions.utils.destruction_liability import DeleteObjectLiability, DELETE_OBJECT_LIABILITYfrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.loot_ops import SlotObjectsfrom interactions.utils.object_definition_or_tags import ObjectDefinitonsOrTagsVariantfrom interactions.utils.outcome import InteractionOutcome, TunableOutcomefrom interactions.utils.outcome_enums import OutcomeResultfrom interactions.utils.tunable import TunableContinuationfrom objects.auto_pick import AutoPick, AutoPickRandomfrom objects.components.inventory_enums import InventoryTypefrom objects.components.state import TimedStateChangeOpfrom objects.components.statistic_types import StatisticComponentGlobalTuningfrom objects.components.types import STATE_COMPONENTfrom objects.hovertip import TooltipFields, TooltipFieldsCompletefrom objects.object_tests import InventoryTestfrom objects.object_factories import ObjectTypeFactory, ObjectTagFactoryfrom objects.script_object import ScriptObjectfrom objects.terrain import get_venue_instance_from_pick_locationfrom plex.plex_enums import PlexBuildingTypefrom postures.posture_graph import DistanceEstimatorfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims.sim_info_types import Agefrom sims4 import mathfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning, TunableLocalizedStringFactoryVariantfrom sims4.random import pop_weightedfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, TunableVariant, Tunable, TunableTuple, TunableReference, TunableSet, TunableList, TunableFactory, TunableThreshold, TunableMapping, TunableRange, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumWithFilter, TunableSimMinute, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom snippets import TunableVenueListReferencefrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog import PhoneRingTypefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom ui.ui_dialog_picker import logger, TunablePickerDialogVariant, SimPickerRow, ObjectPickerRow, ObjectPickerTuningFlags, PurchasePickerRow, LotPickerRowfrom world import regionimport build_buyimport element_utilsimport event_testing.resultsimport gsi_handlersimport servicesimport simsimport sims4.mathimport sims4.resourcesimport tagimport telemetry_helperTELEMETRY_GROUP_PICKERINTERACTION = 'PINT'TELEMETRY_HOOK_INTERACTION_START = 'ACTV'TELEMETRY_FIELD_INTERACTION_ID = 'actv'TELEMETRY_FIELD_PICKED_COUNT = 'snum'TELEMETRY_GROUP_OBJECT_PICKER = 'OPIN'TELEMETRY_HOOK_OBJECT_PICKED = 'RSLT'TELEMETRY_FIELD_OBJECT_INTERACTION_ID = 'inid'TELEMETRY_FIELD_OBJECT_PICKED_COUNT = 'onum'TELEMETRY_FIELD_OBJECT_PICKED = 'obid'pickerinteraction_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_PICKERINTERACTION)object_picked_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_OBJECT_PICKER)
class _TunablePieMenuOptionTuple(TunableTuple):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, show_disabled_item=Tunable(description='\n                If checked, the disabled item will show as disabled in the Pie\n                Menu with a greyed-out tooltip. Otherwise the disabled item will\n                not show up in the pie menu.\n                ', tunable_type=bool, default=False), pie_menu_category=TunableReference(description="\n                If set, then the generated Pie Menu interaction will be\n                categorized under this Pie Menu category, as opposed to using\n                the interaction's Pie Menu category.\n                ", manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True, tuning_group=GroupNames.UI), force_pie_menu_category=Tunable(description='\n                If enabled, we will use the pie_menu_category tuned here even if the row_data (for instance, recipes) \n                of this picker normally specify their own picker categories. This can be useful when re-using row data\n                in a new pie menu picker with a different intended category.\n                ', tunable_type=bool, default=False), pie_menu_name=TunableLocalizedStringFactory(description="\n                The localized name for the pie menu item. The content should\n                always have {2.String} to wrap picker row data's name.\n                "), **kwargs)

class PickerSuperInteractionMixin:
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The object picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'pie_menu_option': OptionalTunable(description='\n            Whether use Pie Menu to show choices other than picker dialog.\n            ', tunable=_TunablePieMenuOptionTuple(), disabled_name='use_picker', enabled_name='use_pie_menu', tuning_group=GroupNames.PICKERTUNING), 'pie_menu_test_tooltip': OptionalTunable(description='\n            If enabled, then a greyed-out tooltip will be displayed if there\n            are no valid choices. When disabled, the test to check for valid\n            choices will run first and if it fail any other tuned test in the\n            interaction will not get run. When enabled, the tooltip will be the\n            last fallback tooltip, and if other tuned interaction tests have\n            tooltip, those tooltip will show first. [cjiang/scottd]\n            ', tunable=TunableLocalizedStringFactory(description='\n                The tooltip text to show in the greyed-out tooltip when no valid\n                choices exist.\n                '), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _test(cls, *args, picked_row=None, **kwargs):
        result = super()._test(*args, **kwargs)
        if not result:
            return result
        if picked_row is not None and not picked_row.is_enable:
            return event_testing.results.TestResult(False, 'This picker SI has no valid choices.', tooltip=picked_row.row_tooltip)
        if not cls.has_valid_choice(*args, **kwargs):
            disabled_tooltip = cls.get_disabled_tooltip(*args, **kwargs)
            return event_testing.results.TestResult(False, 'This picker SI has no valid choices.', tooltip=disabled_tooltip)
        return event_testing.results.TestResult.TRUE

    @flexmethod
    def _get_name(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        text = super(__class__, inst_or_cls)._get_name(*args, **kwargs)
        if inst_or_cls._use_ellipsized_name():
            text = LocalizationHelperTuning.get_ellipsized_text(text)
        return text

    @flexmethod
    def _use_ellipsized_name(cls, inst):
        return True

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        return True

    @classmethod
    def get_disabled_tooltip(cls, *args, **kwargs):
        return cls.pie_menu_test_tooltip

    @classmethod
    def use_pie_menu(cls):
        if cls.pie_menu_option is not None:
            return True
        return False

    def _show_picker_dialog(self, owner, **kwargs):
        if self.use_pie_menu():
            return
        dialog = self._create_dialog(owner, **kwargs)
        dialog.show_dialog()

    def _create_dialog(self, owner, target_sim=None, target=None, **kwargs):
        if self.picker_dialog.title is None:
            title = lambda *_, **__: self.get_name(apply_name_modifiers=False)
        else:
            title = self.picker_dialog.title
        dialog = self.picker_dialog(owner, title=title, resolver=self.get_resolver())
        self._setup_dialog(dialog, **kwargs)
        dialog.set_target_sim(target_sim)
        dialog.set_target(target)
        dialog.current_selected = self._get_current_selected_count()
        dialog.add_listener(self._on_picker_selected)
        return dialog

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if cls.use_pie_menu():
            if context.source == InteractionSource.AUTONOMY and not cls.allow_autonomous:
                return
            recipe_ingredients_map = {}
            funds_source = cls.funds_source if hasattr(cls, 'funds_source') else None
            for row_data in cls.picker_rows_gen(target, context, funds_source=funds_source, recipe_ingredients_map=recipe_ingredients_map, **kwargs):
                if not row_data.available_as_pie_menu:
                    pass
                else:
                    affordance = _PickerPieMenuProxyInteraction.generate(cls, picker_row_data=row_data)
                    for aop in affordance.potential_interactions(target, context, recipe_ingredients_map=recipe_ingredients_map, **kwargs):
                        yield aop
        else:
            yield from super().potential_interactions(target, context, **kwargs)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        raise NotImplementedError

    def _setup_dialog(self, dialog, **kwargs):
        for row in self.picker_rows_gen(self.target, self.context, **kwargs):
            dialog.add_row(row)

    def _on_picker_selected(self, dialog):
        if dialog.multi_select:
            tag_objs = dialog.get_result_tags()
            self.on_multi_choice_selected(tag_objs, ingredient_check=dialog.ingredient_check)
        else:
            tag_obj = dialog.get_single_result_tag()
            self.on_choice_selected(tag_obj, ingredient_check=dialog.ingredient_check, prepped_ingredient_check=dialog.prepped_ingredient_check)

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        raise NotImplementedError

    def on_choice_selected(self, picked_choice, **kwargs):
        raise NotImplementedError

    def _get_current_selected_count(self):
        return 0

class ProximityPickerMixin:

    def _get_choice_by_proximity(self, chosen_objects:'List[GameObject]') -> 'Optional[GameObject]':
        proximity_participant = self.get_participant(self.order_by_proximity.participant)
        if proximity_participant is None:
            proximity_participant = self.sim
        return self.get_choice_by_proximity(chosen_objects, proximity_participant, self.order_by_proximity.use_parent_object_proximity)

    def get_choice_by_proximity(self, chosen_objects:'List[GameObject]', proximity_participant:'GameObject', use_parent_object_proximity:'bool') -> 'Optional[GameObject]':
        posture_graph_service = services.posture_graph_service()
        choice = None
        min_distance = sims4.math.MAX_FLOAT
        distance_estimator = DistanceEstimator(posture_graph_service, self.sim, self, ANYWHERE)
        for obj in chosen_objects:
            if use_parent_object_proximity:
                locations = obj.get_parenting_root().get_locations_for_posture(None)
            else:
                locations = obj.get_locations_for_posture(None)
            for location in locations:
                distance = distance_estimator.estimate_distance((proximity_participant.location, location))
                if distance < min_distance:
                    min_distance = distance
                    choice = obj
        return choice

class PickerSuperInteraction(PickerSuperInteractionMixin, ImmediateSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.allow_user_directed or cls.pie_menu_option is not None:
            logger.error('{} is tuned to be disallowed user directed but has Pie Menu options. Suggestion: allow the interaction to be user directed.', cls.__name__)
        return super()._verify_tuning_callback()
lock_instance_tunables(PickerSuperInteraction, outcome=InteractionOutcome())
class PickerSingleChoiceSuperInteraction(PickerSuperInteraction, ProximityPickerMixin):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'single_choice_display_name': OptionalTunable(tunable=TunableLocalizedStringFactory(description="\n                The name of the interaction if only one option is available. There\n                should be a single token for the item that's used. The token will\n                be replaced with the name of a Sim in Sim Pickers, or an object\n                for recipes, etc.\n                 \n                Picked Sim/Picked Object participants can be used as display\n                name tokens.\n                ", default=None), tuning_group=GroupNames.UI), 'single_choice_display_name_overrides': OptionalTunable(tunable=TunableDisplayNameVariant(description='\n                Set name modifiers or random names.\n                '), tuning_group=GroupNames.UI), 'force_show_dialog_when_single_choice': Tunable(description="\n            If true, shows dialog even if there's only one possible choice\n            ", tunable_type=bool, default=False)}

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if context.source == InteractionSource.AUTONOMY and not cls.allow_autonomous:
            return
        single_row = None
        (_, single_row) = cls.get_single_choice_and_row(context=context, target=target, **kwargs)
        if cls.single_choice_display_name is not None and single_row is None:
            yield from super().potential_interactions(target, context, **kwargs)
        else:
            picked_id = cls._get_id_from_row_tag(single_row.tag)
            picked_item_ids = () if single_row is None else (picked_id,)
            yield AffordanceObjectPair(cls, target, cls, None, picked_item_ids=picked_item_ids, picked_row=single_row, **kwargs)

    @flexmethod
    def get_name_override_and_test_result(cls, inst, single_choice=False, **kwargs) -> 'Tuple[Optional[Any], event_testing.TestResult]':
        if single_choice:
            inst_or_cls = inst if inst is not None else cls
            if inst_or_cls.single_choice_display_name is not None:
                if inst_or_cls.single_choice_display_name_overrides is not None:
                    return inst_or_cls.single_choice_display_name_overrides.get_display_name_and_result(inst_or_cls, **kwargs)
                if inst_or_cls.display_name_overrides is not None:
                    return inst_or_cls.display_name_overrides.get_display_name_and_result(inst_or_cls, **kwargs)
        return super(__class__, inst if inst is not None else cls).get_name_override_and_test_result(**kwargs)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, picked_row=None, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        context = inst_or_cls.context if context is DEFAULT else context
        target = inst_or_cls.target if target is DEFAULT else target
        if inst_or_cls.single_choice_display_name is not None and picked_row is not None:
            (override_tunable, _) = inst_or_cls.get_name_override_and_test_result(target=target, context=context, single_choice=True, **interaction_parameters)
            loc_string = override_tunable.new_display_name if override_tunable is not None else None
            if loc_string is None:
                loc_string = inst_or_cls.single_choice_display_name
            display_name = inst_or_cls.create_localized_string(loc_string, picked_row.name, target=target, context=context, **interaction_parameters)
            return display_name
        return super(PickerSingleChoiceSuperInteraction, inst_or_cls)._get_name(target=target, context=context, **interaction_parameters)

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=None, target=None, **kwargs):
        return (None, None)

    def _get_id_from_choice(self, choice):
        return choice

    @classmethod
    def _get_id_from_row_tag(cls, tag):
        return tag

    def _show_picker_dialog(self, owner, target_sim=None, target=None, choices=(), **kwargs):
        if self.use_pie_menu():
            return
        picked_item_ids = self.interaction_parameters.get('picked_item_ids')
        picked_item_ids = list(picked_item_ids) if picked_item_ids is not None else None
        if len(choices) == 1 and picked_item_ids and not self.force_show_dialog_when_single_choice:
            picked_id = picked_item_ids[0]
            choice_id = self._get_id_from_choice(choices[0])
            if choice_id == picked_id:
                self.on_choice_selected(picked_id)
                return
        dialog = self._create_dialog(owner, target_sim=None, target=target, **kwargs)
        dialog.show_dialog()

class AutonomousPickerSuperInteraction(SuperInteraction, ProximityPickerMixin):
    pass
lock_instance_tunables(AutonomousPickerSuperInteraction, allow_user_directed=False, basic_reserve_object=None, disable_transitions=True)
class SimPickerMixin:
    INSTANCE_TUNABLES = {'actor_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the actor when a picker\n            selection has been made.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'target_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the target sim when a picker\n            selection has been made.\n            ', locked_args={'actor': ParticipantType.TargetSim}, tuning_group=GroupNames.PICKERTUNING), 'picked_continuation': TunableContinuation(description='\n            If specified, a continuation to push on each sim selected in the\n            picker.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'continuations_are_sequential': Tunable(description='\n            This specifies that the continuations tuned in picked_continuation\n            are applied sequentially to the list of picked sims.\n            \n            e.g. The first continuation will be pushed on the first picked sim.\n            The second continuation will be pushed on the second picked sim,\n            etc. Note: There should never be more picked sims than\n            continuations, however, there can be less picked sims than\n            continuations, to allow for cases where the number of sims is a\n            range.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'continuations_are_multi_push': Tunable(description='\n            If true, will attempt to push all the continuations on each of the respective sims in order.\n            If False will stop pushing for each sim after an interaction has been successfully pushed.\n            \n            For picked continuations, this is ignored if continuations are sequential.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'continuation_linking': TunableTuple(description='\n            How/if to link the continuations pushed by this picker. Specify \n            which continuations should be cancelled if any of the other \n            continuations are cancelled.\n            ', continuations_to_cancel=TunableEnumEntry(description='\n                Whose, if any, continuations pushed by this picker should cancel\n                if any of the other continuations pushed by this picker are\n                canceled. \n                \n                e.g. if "ACTOR" is selected, then if the target continuation or\n                any of the picked continuations are canceled the actor \n                continuation will also be canceled.\n                \n                Note:  Currently, if there is no actor or target continuation\n                then no link occurs.\n                ', tunable_type=SimPickerLinkContinuation, default=SimPickerLinkContinuation.NEITHER), cancel_entire_chain=Tunable(description='\n                By default (False) only the specific continuation pushed on the\n                target specified by continuation to cancel will be cancelled \n                if any other continuation (or it\'s continuations) are cancelled.\n                If true, that continuation as well as any continuations of that \n                continuation will be cancelled.\n                \n                e.g. \n                actorA continuation continues to actorB or actorC\n                targetA continuation continues to targetB or targetC\n                \n                if "continuations to cancel" is TARGET or ALL then if this\n                is false, canceling actorA, actorB, or actorC will cancel\n                targetA ONLY.  If the target has already continued to targetB\n                or targetC they will remain untouched.  However if this true, \n                canceling actorA, actorB, or actorC will cancel targetA, \n                targetB, or targetC if the target has already continued on to\n                either of them.\n                ', tunable_type=bool, default=False), tuning_group=GroupNames.PICKERTUNING), 'sim_filter': OptionalTunable(description='\n            Optional Sim Filter to run Sims through. Otherwise we will just get\n            all Sims that pass the tests.\n            ', tunable=TunablePackSafeReference(description='\n                Sim Filter to run all Sims through before tests.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',)), disabled_name='no_filter', enabled_name='sim_filter_selected', tuning_group=GroupNames.PICKERTUNING), 'sim_filter_household_override': OptionalTunable(description="\n            Sim filter by default uses the actor's household for household-\n            related filter terms, such as the In Family filter term. If this is\n            enabled, a different participant's household will be used. If the\n            participant is an object instead of a Sim, the object's owner\n            household will be used.\n            ", tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim, invalid_enums=(ParticipantTypeSingle.Actor,)), tuning_group=GroupNames.PICKERTUNING), 'sim_filter_requesting_sim': TunableEnumEntry(description='\n            Determine which Sim filter requests are relative to. For example, if\n            you want all Sims in a romantic relationship with the target, tune\n            TargetSim here, and then a relationship filter.\n            \n            NOTE: Tuning filters is, performance-wise, preferable to tests.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor, tuning_group=GroupNames.PICKERTUNING), 'create_sim_if_no_valid_choices': Tunable(description='\n            If checked, this picker will generate a sim that matches the tuned\n            filter if no other matching sims are available. This sim will match\n            the tuned filter, but not necessarily respect other rules of this \n            picker (like radius, tests, or instantiation). If you need one of\n            those things, see a GPE about improving this option.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'sim_tests': event_testing.tests.TunableTestSet(description='\n            A set of tests that are run against the prospective sims. At least\n            one test must pass in order for the prospective sim to show. All\n            sims will pass if there are no tests. Picked_sim is the participant\n            type for the prospective sim.\n            ', tuning_group=GroupNames.PICKERTUNING), 'include_uninstantiated_sims': Tunable(description='\n            If unchecked, uninstantiated sims will never be available in the\n            picker. if checked, they must still pass the filters and tests This\n            is an optimization tunable.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'include_instantiated_sims': Tunable(description='\n            If unchecked, instantiated sims will never be available in the\n            picker. if checked, they must still pass the filters and tests.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'include_actor_sim': Tunable(description='\n            If checked then the actor sim can be included in the picker options\n            and will not be blacklisted.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_target_sim': Tunable(description='\n            If checked then the target sim can be included in the picker options\n            and will not be blacklisted.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_rabbithole_sims': Tunable(description='\n            If unchecked, rabbithole sims will never be available in the\n            picker. if checked, they must still pass the filters and tests.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_missing_pets': Tunable(description='\n            If unchecked, missing pet sims will never be available in the\n            picker. if checked, they must still pass the filters and tests.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'radius': OptionalTunable(description='\n            If enabled then Sim must be in a certain range for consideration.\n            This should only be enabled when include_instantiated_sims is True\n            and include_uninstantiated_sims is False.\n            ', tunable=TunableRange(description='\n                Sim must be in a certain range for consideration.\n                ', tunable_type=int, default=5, minimum=1, maximum=50), tuning_group=GroupNames.PICKERTUNING), 'success_loot_actions': TunableList(description='\n            List of loot actions to apply on successful picker selection.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if cls.include_instantiated_sims and cls.include_uninstantiated_sims and cls.radius is not None:
            logger.error('Tuning: If include_instantiated_sims is False or include_uninstantiated_sims is True, radius should be disabled: {}', cls)

    @flexmethod
    def _get_requesting_sim_info_for_picker(cls, inst, context, *, target, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls.get_participant(inst_or_cls.sim_filter_requesting_sim, sim=context.sim, target=target, **kwargs)

    @flexmethod
    def _get_actor_for_picker(cls, inst, context, *, target, **kwargs):
        sim = inst.sim if inst is not None else context.sim
        if sim is not None:
            return sim.sim_info

    @flexmethod
    def get_sim_filter_gsi_name(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return str(inst_or_cls)

    @flexmethod
    def _get_valid_household_choices_gen(cls, inst:'Interaction', target:'GameObject', context:'InteractionContext', **kwargs) -> 'None':
        inst_or_cls = inst if inst is not None else cls
        requesting_sim_info = inst_or_cls._get_requesting_sim_info_for_picker(context, target=target, carry_target=context.carry_target, **kwargs)
        if requesting_sim_info is None:
            return
        household_id = None
        if inst_or_cls.sim_filter_household_override is not None:
            resolver = inst_or_cls.get_resolver(target=target, context=context)
            participant = resolver.get_participant(inst_or_cls.sim_filter_household_override)
            if participant is not None:
                if participant.is_sim:
                    household_id = participant.household_id
                else:
                    household_id = participant.get_household_owner_id()
                    if household_id is None:
                        household_id = 0
        results = services.sim_filter_service().submit_household_filter(sim_filter=inst_or_cls.sim_filter, callback=None, requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name)
        if results:
            yield from results

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, test_function=None, min_required=1, included_override=set(), excluded_override=set(), **kwargs):
        sim_info_manager = services.sim_info_manager()
        if included_override:
            for sim_id in included_override:
                sim_info = sim_info_manager.get(sim_id)
                if sim_info is not None:
                    yield sim_info
            return
        inst_or_cls = inst if inst is not None else cls
        requesting_sim_info = inst_or_cls._get_requesting_sim_info_for_picker(context, target=target, carry_target=context.carry_target, **kwargs)
        if requesting_sim_info is None:
            return
        actor_sim_info = inst_or_cls._get_actor_for_picker(context, target=target, **kwargs)
        household_id = None
        is_picker_dialog = hasattr(inst_or_cls, 'picker_dialog')
        resolver = inst_or_cls.get_resolver(target=target, context=context)
        participant = resolver.get_participant(inst_or_cls.sim_filter_household_override)
        if participant.is_sim:
            household_id = participant.household_id
        else:
            household_id = participant.get_household_owner_id()
            household_id = 0
        participant = resolver.get_participant(inst_or_cls.picker_dialog.override_owner)
        actor_sim_info = participant
        sim_infos = sim_info_manager.get_all()
        pre_filtered_sim_infos = inst_or_cls.sim_filter.get_pre_filtered_sim_infos(requesting_sim_info=requesting_sim_info)
        sim_infos = pre_filtered_sim_infos
        valid_sims_found = 0
        for sim_info in sim_infos:
            if not sim_info.can_instantiate_sim:
                pass
            elif sim_info.sim_id in excluded_override:
                pass
            elif inst_or_cls.include_actor_sim or sim_info is actor_sim_info:
                pass
            elif inst_or_cls.include_target_sim or (not target is not None or not target.is_sim) or sim_info is target.sim_info:
                pass
            elif inst_or_cls.include_uninstantiated_sims or not sim_info.is_instanced():
                pass
            elif inst_or_cls.include_instantiated_sims or sim_info.is_instanced():
                pass
            elif inst_or_cls.radius is not None:
                sim = sim_info.get_sim_instance()
                if not sim is None:
                    if actor_sim_info is None:
                        pass
                    else:
                        actor_sim = actor_sim_info.get_sim_instance()
                        if actor_sim is None:
                            pass
                        else:
                            delta = actor_sim.intended_position - sim.intended_position
                            if delta.magnitude() > inst_or_cls.radius:
                                pass
                            elif services.relationship_service().is_hidden(actor_sim_info.sim_id, sim_info.sim_id):
                                pass
                            else:
                                results = services.sim_filter_service().submit_filter(inst_or_cls.sim_filter, None, sim_constraints=(sim_info.sim_id,), requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name, include_rabbithole_sims=inst_or_cls.include_rabbithole_sims, include_missing_pets=inst_or_cls.include_missing_pets)
                                if not results:
                                    pass
                                else:
                                    if inst:
                                        interaction_parameters = inst.interaction_parameters.copy()
                                    else:
                                        interaction_parameters = kwargs.copy()
                                    interaction_parameters['picked_item_ids'] = {sim_info.sim_id}
                                    resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                                    if not inst_or_cls.sim_tests or not inst_or_cls.sim_tests.run_tests(resolver):
                                        pass
                                    elif test_function is not None:
                                        sim = sim_info.get_sim_instance()
                                        if not sim is None:
                                            if not test_function(sim):
                                                pass
                                            else:
                                                valid_sims_found += 1
                                                yield results[0]
                                    else:
                                        valid_sims_found += 1
                                        yield results[0]
            elif services.relationship_service().is_hidden(actor_sim_info.sim_id, sim_info.sim_id):
                pass
            else:
                results = services.sim_filter_service().submit_filter(inst_or_cls.sim_filter, None, sim_constraints=(sim_info.sim_id,), requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name, include_rabbithole_sims=inst_or_cls.include_rabbithole_sims, include_missing_pets=inst_or_cls.include_missing_pets)
                if not results:
                    pass
                else:
                    if inst:
                        interaction_parameters = inst.interaction_parameters.copy()
                    else:
                        interaction_parameters = kwargs.copy()
                    interaction_parameters['picked_item_ids'] = {sim_info.sim_id}
                    resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                    if not inst_or_cls.sim_tests or not inst_or_cls.sim_tests.run_tests(resolver):
                        pass
                    elif test_function is not None:
                        sim = sim_info.get_sim_instance()
                        if not sim is None:
                            if not test_function(sim):
                                pass
                            else:
                                valid_sims_found += 1
                                yield results[0]
                    else:
                        valid_sims_found += 1
                        yield results[0]
        number_required_sims_not_found = min_required - valid_sims_found
        if (inst_or_cls.sim_filter_household_override is not None or is_picker_dialog) and inst_or_cls.picker_dialog.override_owner is not None and inst_or_cls.sim_filter_household_override is not None and participant is not None and is_picker_dialog and (inst_or_cls.picker_dialog.override_owner is not None and (participant is not None and participant.is_sim)) and inst_or_cls.sim_filter is not None and pre_filtered_sim_infos is not None and inst_or_cls.create_sim_if_no_valid_choices and number_required_sims_not_found > 0:
            results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=number_required_sims_not_found, sim_filter=inst_or_cls.sim_filter, requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name)
            if results:
                yield from results

    def _push_continuation(self, sim, tunable_continuation, sim_ids, insert_strategy, picked_zone_set):
        continuation = None
        picked_item_set = {target_sim_id for target_sim_id in sim_ids if target_sim_id is not None}
        self.interaction_parameters['picked_item_ids'] = frozenset(picked_item_set)
        self.push_tunable_continuation(tunable_continuation, insert_strategy=insert_strategy, picked_item_ids=picked_item_set, picked_zone_ids=picked_zone_set, multi_push=self.continuations_are_multi_push)
        new_continuation = sim.queue.find_pushed_interaction_by_id(self.group_id)
        while new_continuation is not None:
            continuation = new_continuation
            new_continuation = sim.queue.find_continuation_by_id(continuation.id)
        return continuation

    def _push_continuations(self, sim_ids, zone_datas=None):
        if not self.picked_continuation:
            insert_strategy = QueueInsertStrategy.LAST
        else:
            insert_strategy = QueueInsertStrategy.NEXT
        picked_zone_set = None
        if zone_datas is not None:
            try:
                picked_zone_set = {zone_data.zone_id for zone_data in zone_datas if zone_data is not None}
            except TypeError:
                picked_zone_set = {zone_datas.zone_id}
            self.interaction_parameters['picked_zone_ids'] = frozenset(picked_zone_set)
        actor_continuation = None
        target_continuation = None
        picked_continuations = []
        if self.actor_continuation:
            actor_continuation = self._push_continuation(self.sim, self.actor_continuation, sim_ids, insert_strategy, picked_zone_set)
        if self.target_continuation:
            target_sim = self.get_participant(ParticipantType.TargetSim)
            if target_sim is not None:
                target_continuation = self._push_continuation(target_sim, self.target_continuation, sim_ids, insert_strategy, picked_zone_set)
        if self.picked_continuation:
            num_continuations = len(self.picked_continuation)
            for (index, target_sim_id) in enumerate(sim_ids):
                if target_sim_id is None:
                    pass
                else:
                    logger.info('SimPicker: picked Sim_id: {}', target_sim_id, owner='jjacobson')
                    target_sim = services.object_manager().get(target_sim_id)
                    if target_sim is None:
                        logger.error("You must pick on lot sims for a tuned 'picked continuation' to function.", owner='jjacobson')
                    else:
                        self.interaction_parameters['picked_item_ids'] = frozenset((target_sim_id,))
                        if self.continuations_are_sequential:
                            if index < num_continuations:
                                continuation = (self.picked_continuation[index],)
                            else:
                                logger.error('There are not enough tuned picked continuations for the interaction {}, so picked sim {} and all others afterwards will be skipped.', self, target_sim, owner='johnwilkinson')
                                break
                        else:
                            continuation = self.picked_continuation
                        self.push_tunable_continuation(continuation, insert_strategy=insert_strategy, actor=target_sim, picked_zone_ids=picked_zone_set, multi_push=self.continuations_are_multi_push)
                        picked_continuation = target_sim.queue.find_pushed_interaction_by_id(self.group_id)
                        if picked_continuation is not None:
                            new_continuation = target_sim.queue.find_continuation_by_id(picked_continuation.id)
                            while new_continuation is not None:
                                picked_continuation = new_continuation
                                new_continuation = target_sim.queue.find_continuation_by_id(picked_continuation.id)
                            picked_continuations.append(picked_continuation)
        link_type = self.continuation_linking.continuations_to_cancel
        if link_type != SimPickerLinkContinuation.NEITHER:
            link_chain = self.continuation_linking.cancel_entire_chain
            if actor_continuation is not None:
                if target_continuation is not None and (link_type == SimPickerLinkContinuation.TARGET or link_type == SimPickerLinkContinuation.ALL):
                    actor_continuation.attach_interaction(target_continuation, cancel_continuations=link_chain)
                for interaction in picked_continuations:
                    if link_type == SimPickerLinkContinuation.ACTOR or link_type == SimPickerLinkContinuation.ALL:
                        interaction.attach_interaction(actor_continuation, cancel_continuations=link_chain)
                    if not link_type == SimPickerLinkContinuation.PICKED:
                        if link_type == SimPickerLinkContinuation.ALL:
                            actor_continuation.attach_interaction(interaction, cancel_continuations=link_chain)
                    actor_continuation.attach_interaction(interaction, cancel_continuations=link_chain)
            if target_continuation is not None:
                if actor_continuation is not None and (link_type == SimPickerLinkContinuation.ACTOR or link_type == SimPickerLinkContinuation.ALL):
                    target_continuation.attach_interaction(actor_continuation, cancel_continuations=link_chain)
                for interaction in picked_continuations:
                    if link_type == SimPickerLinkContinuation.TARGET or link_type == SimPickerLinkContinuation.ALL:
                        interaction.attach_interaction(target_continuation, cancel_continuations=link_chain)
                    if not link_type == SimPickerLinkContinuation.PICKED:
                        if link_type == SimPickerLinkContinuation.ALL:
                            target_continuation.attach_interaction(interaction, cancel_continuations=link_chain)
                    target_continuation.attach_interaction(interaction, cancel_continuations=link_chain)

    def _apply_loot(self, results):
        interaction_parameters = {}
        resolver = self.get_resolver()
        if results is not None:
            interaction_parameters['picked_item_ids'] = results
        resolver.interaction_parameters = interaction_parameters
        for loot in self.success_loot_actions:
            loot.apply_to_resolver(resolver)

class SimPickerInteraction(SimPickerMixin, PickerSingleChoiceSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The object picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.SIM | ObjectPickerTuningFlags.SKILLS_SIM, tuning_group=GroupNames.PICKERTUNING), 'default_selection_tests': OptionalTunable(description='\n            If enabled, any Sim who passes these tests will be selected by\n            default when the picker pops up.\n            ', tunable=event_testing.tests.TunableTestSet(description='\n                A set of tests that will automatically select Sims that pass\n                when the Sim Picker pops up.\n                '), tuning_group=GroupNames.PICKERTUNING), 'default_selections_sort_to_front': Tunable(description='\n            If checked then any Sim that passes the default selection tests\n            will be sorted to the top of the list.\n            ', tunable_type=bool, default=False), 'carry_item_from_inventory': OptionalTunable(description='\n            If enabled continuations will set the carry target on the \n            interaction context to an object with the specified tag found on\n            the inventory of the Sim running this interaction.\n            ', tunable=tag.TunableTags(description='\n                The set of tags that are used to determine which objects to highlight.\n                ')), 'cell_enabled_tests': OptionalTunable(description='\n            Test to see if the cell should be enabled or not.\n            If it does not pass, it will disable the cell and optionally\n            override the tooltip.\n            A string tuned for Tooltip here will use tokens from the interaction\'s\n            tuned Display Names Text Tokens. For example, a tooltip string containing\n            "{0.SimFirstName}" would use the first entry tuned there.\n            ', tunable=event_testing.tests.TunableTestSetWithTooltip(), tuning_group=GroupNames.PICKERTUNING), 'requires_age_romance_check': Tunable(description='\n            If this is checked then we will check to see if the Sims ages allow romance (basically\n            t->yae and yae-> not allowed). If it is disallowed we will pass that piece of\n            information on to the ui via the tags list and it can use it to filter other filters\n            in a multi-picker situation. This should only be checked for use with picker\n            interactions inside of a multi-picker.\n            ', tunable_type=bool, default=False), 'report_picked_count': Tunable(description='\n            If checked, this interaction will send off telemetry data when sims are chosen for the interaction,\n            reporting the interaction ID, the initiating Sim ID, the number of picked sims, and the zone id.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.TELEMETRY), 'show_households': Tunable(description='\n            If checked, this interaction will generate and show households (instead of \n            Sims) in the picker.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        if self.show_households:
            choices = list(self._get_valid_household_choices_gen(self.target, self.context))
        else:
            choices = list(self._get_valid_sim_choices_gen(self.target, self.context, min_required=self.picker_dialog.min_selectable))
        if len(choices) < self.picker_dialog.min_choices:
            return False
        if self.picker_dialog.min_selectable == 0 and not choices:
            self._on_successful_picker_selection()
            return True
        if len(choices) == 1:
            if self.show_households:
                self._kwargs['picked_item_ids'] = (choices[0][0].id,)
            else:
                self._kwargs['picked_item_ids'] = (choices[0].sim_info.sim_id,)
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target, choices=choices)
        return True

    def _setup_dialog(self, dialog, **kwargs):
        super()._setup_dialog(dialog, **kwargs)
        if self.default_selections_sort_to_front:
            dialog.sort_selected_items_to_front()

    def _get_id_from_choice(self, choice):
        if self.show_households:
            return choice[0].id
        return choice.sim_info.id

    @flexmethod
    def create_row(cls, inst:'Interaction', tag:'int'=None, select_default:'bool'=False, sim_id:'int'=None, household_id:'int'=None) -> 'SimPickerRow':
        second_tag_list = None
        inst_or_cls = inst if inst is not None else cls
        if sim_id is not None:
            allow_romance = True
            if inst is not None:
                actor_sim_info = inst.sim.sim_info
                target_id = sim_id
                target_sim_info = services.sim_info_manager().get(target_id)
                if target_sim_info.age <= Age.TEEN:
                    allow_romance = False
                second_tag_list = (1,) if not ((actor_sim_info.age <= Age.TEEN and target_sim_info.age >= Age.YOUNGADULT or actor_sim_info.age >= Age.YOUNGADULT) and allow_romance) else None
        return SimPickerRow(sim_id=sim_id, tag=tag, select_default=select_default, second_tag_list=second_tag_list, household_id=household_id)

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=None, target=None, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if context is None:
            return (None, None)
        single_choice = None
        for choice in inst_or_cls._get_valid_sim_choices_gen(target, context, **kwargs):
            if single_choice is not None:
                return (None, None)
            else:
                single_choice = choice
                if single_choice is not None:
                    sim_id = single_choice.sim_info.sim_id
                    row = inst_or_cls.create_row(sim_id)
                    if inst_or_cls.cell_enabled_tests is not None:
                        if inst:
                            interaction_parameters = inst.interaction_parameters.copy()
                        else:
                            interaction_parameters = kwargs.copy()
                        interaction_parameters['picked_item_ids'] = {sim_id}
                        resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                        result = inst_or_cls.cell_enabled_tests.run_tests(resolver)
                        if not result:
                            row.is_enable = False
                            if result.tooltip is not None:
                                row.row_tooltip = result.tooltip
                    return (single_choice.sim_info, row)
        if single_choice is not None:
            sim_id = single_choice.sim_info.sim_id
            row = inst_or_cls.create_row(sim_id)
            if inst_or_cls.cell_enabled_tests is not None:
                if inst:
                    interaction_parameters = inst.interaction_parameters.copy()
                else:
                    interaction_parameters = kwargs.copy()
                interaction_parameters['picked_item_ids'] = {sim_id}
                resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                result = inst_or_cls.cell_enabled_tests.run_tests(resolver)
                if not result:
                    row.is_enable = False
                    if result.tooltip is not None:
                        row.row_tooltip = result.tooltip
            return (single_choice.sim_info, row)
        return (None, None)

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if cls.picker_dialog is not None and cls.picker_dialog.min_selectable == 0 and cls.picker_dialog.min_choices == 0:
            return True
        choice_count = 0
        if cls.create_sim_if_no_valid_choices:
            return True
        if cls.show_households:
            choices = cls._get_valid_household_choices_gen(target, context, **kwargs)
        else:
            choices = cls._get_valid_sim_choices_gen(target, context, **kwargs)
        for _ in choices:
            if cls.picker_dialog is None:
                return True
            choice_count += 1
            if choice_count >= cls.picker_dialog.min_selectable and choice_count >= cls.picker_dialog.min_choices:
                return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, default_selection=set(), **kwargs):
        inst_or_cls = inst if inst is not None else cls
        interaction_parameters = {}
        resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
        if inst_or_cls.show_households:
            results = list(inst_or_cls._get_valid_household_choices_gen(target, context, **kwargs))
        else:
            results = list(inst_or_cls._get_valid_sim_choices_gen(target, context, **kwargs))
        for filter_result in results:
            household_id = None
            sim_id = None
            if inst_or_cls.show_households:
                household_id = filter_result[0].id
                logger.info('SimPicker: add household_id:{}', household_id)
                interaction_parameters['picked_item_ids'] = {household_id}
                tag = household_id
            else:
                sim_id = filter_result.sim_info.id
                logger.info('SimPicker: add sim_id:{}', sim_id)
                interaction_parameters['picked_item_ids'] = {sim_id}
                tag = sim_id
            resolver.interaction_parameters = interaction_parameters
            if not inst_or_cls.default_selection_tests is not None or inst_or_cls.default_selection_tests.run_tests(resolver) or sim_id in default_selection or household_id in default_selection:
                select_default = True
            else:
                select_default = False
            row = inst_or_cls.create_row(tag=tag, select_default=select_default, sim_id=sim_id, household_id=household_id)
            result = inst_or_cls.cell_enabled_tests.run_tests(resolver)
            row.is_enable = False
            localization_tokens = inst_or_cls.get_localization_tokens(**interaction_parameters)
            row.row_tooltip = lambda *_, result_tooltip=result.tooltip, tokens=localization_tokens: result_tooltip(*tokens)
            yield row

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            results = dialog.get_result_tags()
            if len(results) >= dialog.min_selectable:
                self._on_successful_picker_selection(results)

    def _on_successful_picker_selection(self, results=()):
        self._apply_loot(results)
        self._push_continuations(results)
        if self.report_picked_count:
            with telemetry_helper.begin_hook(pickerinteraction_telemetry_writer, TELEMETRY_HOOK_INTERACTION_START, sim=self.sim) as hook:
                hook.write_int(TELEMETRY_FIELD_INTERACTION_ID, self.guid64)
                hook.write_int(TELEMETRY_FIELD_PICKED_COUNT, len(results))

    def _set_inventory_carry_target(self):
        if self.carry_item_from_inventory is not None:
            for obj in self.sim.inventory_component:
                if any(obj.definition.has_build_buy_tag(tag) for tag in self.carry_item_from_inventory):
                    self.context.carry_target = obj
                    break

    def _push_continuations(self, *args, **kwargs):
        self._set_inventory_carry_target()
        super()._push_continuations(*args, **kwargs)

    def on_choice_selected(self, choice_tag, **kwargs):
        sim = choice_tag
        if sim is not None:
            self._on_successful_picker_selection(results=(sim,))

class PickerTravelHereSuperInteraction(SimPickerInteraction):
    INSTANCE_TUNABLES = {'get_display_name_from_destination': Tunable(description='\n            If checked then we will attempt to get the Travel With Interaction\n            Name from the venue we are trying to travel to and use that instead\n            of display name.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        target = inst_or_cls.target if target is DEFAULT else target
        context = inst_or_cls.context if context is DEFAULT else context
        zone_id = context.pick.get_zone_id_from_pick_location()
        if inst is not None:
            inst.interaction_parameters['picked_zone_ids'] = frozenset({zone_id})
        if inst_or_cls.get_display_name_from_destination:
            venue_instance = get_venue_instance_from_pick_location(context.pick)
            if venue_instance is not None and venue_instance.travel_with_interaction_name is not None:
                return venue_instance.travel_with_interaction_name(target, context)
        return super(__class__, inst_or_cls)._get_name(target=target, context=context, **interaction_parameters)

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, **kwargs):
        zone_id = context.pick.get_zone_id_from_pick_location()
        for filter_result in super()._get_valid_sim_choices_gen(target, context, **kwargs):
            if filter_result.sim_info.zone_id != zone_id:
                yield filter_result

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=None, target=None, **kwargs):
        return (None, None)

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            results = dialog.get_result_tags()
            self._on_successful_picker_selection(results)

    def _on_successful_picker_selection(self, results=()):
        zone_ids = self.interaction_parameters.get('picked_zone_ids', None)
        if zone_ids is None:
            zone_id = self.context.pick.get_zone_id_from_pick_location()
            zone_ids = frozenset({zone_id})
        zone_datas = []
        for zone_id in zone_ids:
            zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
            if zone_data is not None:
                zone_datas.append(zone_data)
        self._push_continuations(results, zone_datas=zone_datas)
lock_instance_tunables(PickerTravelHereSuperInteraction, single_choice_display_name=None)
class AutonomousSimPickerSuperInteraction(SimPickerMixin, AutonomousPickerSuperInteraction):
    INSTANCE_TUNABLES = {'test_compatibility': Tunable(description='\n            If checked then the actor continuation will be tested for\n            interaction compatibility.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'order_by_proximity': OptionalTunable(description='\n            If order_by_proximity is enabled, we find the nearest sim to this Participant. \n            ', tunable=TunableTuple(participant=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), locked_args={'use_parent_object_proximity': False}), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if not cls.has_valid_choice(target, context, **interaction_parameters):
            return event_testing.results.TestResult(False, 'This picker SI has no valid choices.')
        return super()._test(target, context, **interaction_parameters)

    def find_best_sim_id(self, valid_sim_filter_results):
        return self.find_best_sim_id_base(valid_sim_filter_results)

    def find_best_sim_id_base(self, valid_sim_filter_results):
        if self.order_by_proximity:
            choice = self._get_choice_by_proximity(valid_sim_filter_results)
        else:
            weights = [(filter_result.score, filter_result.sim_info.id) for filter_result in valid_sim_filter_results]
            choice = sims4.random.pop_weighted(weights)
        return choice

    def _run_interaction_gen(self, timeline):
        continuation = self.actor_continuation[0]
        affordance = continuation.si_affordance_override if continuation.si_affordance_override is not None else continuation.affordance
        compatibility_func = functools.partial(self.are_affordances_linked, affordance, self.context) if self.test_compatibility else None
        valid_sims = [filter_result for filter_result in self._get_valid_sim_choices_gen(self.target, self.context, test_function=compatibility_func)]
        chosen_sim = self.find_best_sim_id(valid_sims)
        if chosen_sim is not None:
            chosen_sim = (chosen_sim,)
            self._apply_loot(chosen_sim)
            self._push_continuations(chosen_sim)
        return True

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        continuation = cls.actor_continuation[0]
        affordance = continuation.si_affordance_override if continuation.si_affordance_override is not None else continuation.affordance
        compatibility_func = functools.partial(cls.are_affordances_linked, affordance, context) if cls.test_compatibility else None
        if cls.create_sim_if_no_valid_choices:
            return True
        for _ in cls._get_valid_sim_choices_gen(target, context, test_function=compatibility_func, **kwargs):
            return True
        return False

    @classmethod
    def are_affordances_linked(cls, affordance, context, chosen_sim):
        aop = AffordanceObjectPair(affordance, chosen_sim, affordance, None)
        chosen_sim_si_state = chosen_sim.si_state
        for existing_si in chosen_sim_si_state.all_guaranteed_si_gen(context.priority, group_id=context.group_id):
            if not aop.affordance.is_linked_to(existing_si.affordance):
                return False
        return True

class LotPickerMixin:
    INSTANCE_TUNABLES = {'default_inclusion': TunableVariant(description='\n            This defines which venue types are valid for this picker.\n            ', include_all=TunableTuple(description='\n                This will allow all venue types to be valid, except those blacklisted.\n                ', include_all_by_default=Tunable(bool, True), exclude_venues=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), tuning_group=GroupNames.VENUES, pack_safe=True), display_name='Blacklist Items'), exclude_lists=TunableList(TunableVenueListReference(), display_name='Blacklist Lists'), locked_args={'include_all_by_default': True}), exclude_all=TunableTuple(description='\n                This will prevent all venue types from being valid, except those whitelisted.\n                ', include_all_by_default=Tunable(bool, False), include_venues=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), tuning_group=GroupNames.VENUES, pack_safe=True), display_name='Whitelist Items'), include_lists=TunableList(TunableVenueListReference(), display_name='Whitelist Lists'), locked_args={'include_all_by_default': False}), default='include_all', tuning_group=GroupNames.PICKERTUNING), 'building_types_excluded': TunableSet(description='\n            A set of building types to exclude for this map view picker. This\n            allows us to do things like exclude apartments or penthouses.\n            ', tunable=TunableEnumEntry(description='\n                The Plex Building Type we want to exclude. Default is standard\n                lots. Fully Contained Plexes are apartments, and Penthouses are\n                regular lots that sit on top of apartment buildings and have a\n                common area.\n                ', tunable_type=PlexBuildingType, default=PlexBuildingType.FULLY_CONTAINED_PLEX, invalid_enums=(PlexBuildingType.INVALID,)), tuning_group=GroupNames.PICKERTUNING), 'include_actor_home_lot': Tunable(description='\n            If checked, the actors home lot will always be included regardless\n            of venue tuning.  If unchecked, it will NEVER be included.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_target_home_lot': Tunable(description='\n            If checked, the target(s) home lot will always be included regardless\n            of venue tuning.  If unchecked, it will NEVER be included.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_active_lot': Tunable(description='\n            If checked, the active lot may or may not appear based on \n            venue/situation tuning. If not checked, the active lot will always \n            be excluded.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'test_region_compatibility': Tunable(description="\n            If enabled, this picker will filter out regions that are\n            inaccessible from the actor sim's current region.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'exclude_rented_zones': Tunable(description='\n            If enabled, this picker will filter out zones that have already\n            been rented. This should likely be restricted to interactions that\n            are attempting to rent a zone or join a vacation.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'testable_region_inclusion': TunableMapping(description='\n            Mapping of region to tests that should be run to verify if region\n            should be added.\n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True), value_type=TunableTestSet(description='\n                A series of tests that must pass in order for the region to be\n                available for picking.\n                '), tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_valid_lot_choices(cls, inst, target, context, target_list=None):
        inst_or_cls = inst if inst is not None else cls
        actor = context.sim
        if actor is None:
            return []
        target_zone_ids = []
        actor_zone_id = actor.household.home_zone_id
        results = []
        if target_list is None:
            if target.household is not None:
                target_zone_ids.append(target.household.home_zone_id)
        else:
            sim_info_manager = services.sim_info_manager()
            for target_sim_id in target_list:
                target_sim_info = sim_info_manager.get(target_sim_id)
                if target_sim_info is not None and target_sim_info.household is not None:
                    target_zone_ids.append(target_sim_info.household.home_zone_id)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        active_zone_id = services.current_zone().id
        travel_group_manager = services.travel_group_manager()
        current_region = region.get_region_instance_from_zone_id(actor.zone_id)
        if current_region is None and inst_or_cls.test_region_compatibility:
            logger.error('Could not find region for Sim {}'.format(actor), owner='rmccord')
            return []
        plex_service = services.get_plex_service()
        persistence_service = services.get_persistence_service()
        for zone_data in persistence_service.zone_proto_buffs_gen():
            zone_id = zone_data.zone_id
            if inst_or_cls.include_active_lot or zone_id == active_zone_id:
                pass
            elif inst_or_cls.test_region_compatibility:
                dest_region = region.get_region_instance_from_zone_id(zone_id)
                if not current_region.is_region_compatible(dest_region):
                    pass
                elif inst_or_cls.building_types_excluded and plex_service.get_plex_building_type(zone_id) in inst_or_cls.building_types_excluded:
                    pass
                elif zone_id == actor_zone_id:
                    if inst_or_cls.include_actor_home_lot:
                        results.append(zone_data)
                        if zone_id in target_zone_ids:
                            if inst_or_cls.include_target_home_lot:
                                results.append(zone_data)
                                venue_tuning_id = build_buy.get_current_venue(zone_id)
                                if venue_tuning_id is None:
                                    pass
                                else:
                                    venue_tuning = venue_manager.get(venue_tuning_id)
                                    if venue_tuning is None:
                                        pass
                                    elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                                        pass
                                    else:
                                        region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                                        if region_tests is not None:
                                            resolver = SingleSimResolver(actor.sim_info)
                                            if region_tests.run_tests(resolver):
                                                results.append(zone_data)
                                            else:
                                                default_inclusion = inst_or_cls.default_inclusion
                                                if inst_or_cls.default_inclusion.include_all_by_default:
                                                    if venue_tuning in default_inclusion.exclude_venues:
                                                        pass
                                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                        pass
                                                    else:
                                                        results.append(zone_data)
                                                elif venue_tuning in default_inclusion.include_venues:
                                                    results.append(zone_data)
                                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                                    results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_tuning in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_tuning in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                        else:
                            venue_tuning_id = build_buy.get_current_venue(zone_id)
                            if venue_tuning_id is None:
                                pass
                            else:
                                venue_tuning = venue_manager.get(venue_tuning_id)
                                if venue_tuning is None:
                                    pass
                                elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                                    pass
                                else:
                                    region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                                    if region_tests is not None:
                                        resolver = SingleSimResolver(actor.sim_info)
                                        if region_tests.run_tests(resolver):
                                            results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_tuning in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_tuning in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_tuning in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_tuning in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                elif zone_id in target_zone_ids:
                    if inst_or_cls.include_target_home_lot:
                        results.append(zone_data)
                        venue_tuning_id = build_buy.get_current_venue(zone_id)
                        if venue_tuning_id is None:
                            pass
                        else:
                            venue_tuning = venue_manager.get(venue_tuning_id)
                            if venue_tuning is None:
                                pass
                            elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                                pass
                            else:
                                region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                                if region_tests is not None:
                                    resolver = SingleSimResolver(actor.sim_info)
                                    if region_tests.run_tests(resolver):
                                        results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_tuning in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_tuning in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_tuning in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_tuning in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                else:
                    venue_tuning_id = build_buy.get_current_venue(zone_id)
                    if venue_tuning_id is None:
                        pass
                    else:
                        venue_tuning = venue_manager.get(venue_tuning_id)
                        if venue_tuning is None:
                            pass
                        elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                            pass
                        else:
                            region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                            if region_tests is not None:
                                resolver = SingleSimResolver(actor.sim_info)
                                if region_tests.run_tests(resolver):
                                    results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_tuning in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_tuning in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_tuning in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_tuning in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
            elif inst_or_cls.building_types_excluded and plex_service.get_plex_building_type(zone_id) in inst_or_cls.building_types_excluded:
                pass
            elif zone_id == actor_zone_id:
                if inst_or_cls.include_actor_home_lot:
                    results.append(zone_data)
                    if zone_id in target_zone_ids:
                        if inst_or_cls.include_target_home_lot:
                            results.append(zone_data)
                            venue_tuning_id = build_buy.get_current_venue(zone_id)
                            if venue_tuning_id is None:
                                pass
                            else:
                                venue_tuning = venue_manager.get(venue_tuning_id)
                                if venue_tuning is None:
                                    pass
                                elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                                    pass
                                else:
                                    region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                                    if region_tests is not None:
                                        resolver = SingleSimResolver(actor.sim_info)
                                        if region_tests.run_tests(resolver):
                                            results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_tuning in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_tuning in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_tuning in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_tuning in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                    else:
                        venue_tuning_id = build_buy.get_current_venue(zone_id)
                        if venue_tuning_id is None:
                            pass
                        else:
                            venue_tuning = venue_manager.get(venue_tuning_id)
                            if venue_tuning is None:
                                pass
                            elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                                pass
                            else:
                                region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                                if region_tests is not None:
                                    resolver = SingleSimResolver(actor.sim_info)
                                    if region_tests.run_tests(resolver):
                                        results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_tuning in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_tuning in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_tuning in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_tuning in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
            elif zone_id in target_zone_ids:
                if inst_or_cls.include_target_home_lot:
                    results.append(zone_data)
                    venue_tuning_id = build_buy.get_current_venue(zone_id)
                    if venue_tuning_id is None:
                        pass
                    else:
                        venue_tuning = venue_manager.get(venue_tuning_id)
                        if venue_tuning is None:
                            pass
                        elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                            pass
                        else:
                            region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                            if region_tests is not None:
                                resolver = SingleSimResolver(actor.sim_info)
                                if region_tests.run_tests(resolver):
                                    results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_tuning in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_tuning in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_tuning in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_tuning in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
            else:
                venue_tuning_id = build_buy.get_current_venue(zone_id)
                if venue_tuning_id is None:
                    pass
                else:
                    venue_tuning = venue_manager.get(venue_tuning_id)
                    if venue_tuning is None:
                        pass
                    elif inst_or_cls.exclude_rented_zones and venue_tuning.is_vacation_venue and not travel_group_manager.is_zone_rentable(zone_id, venue_tuning):
                        pass
                    else:
                        region_tests = inst_or_cls.testable_region_inclusion.get(venue_tuning)
                        if region_tests is not None:
                            resolver = SingleSimResolver(actor.sim_info)
                            if region_tests.run_tests(resolver):
                                results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_tuning in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_tuning in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
                        else:
                            default_inclusion = inst_or_cls.default_inclusion
                            if inst_or_cls.default_inclusion.include_all_by_default:
                                if venue_tuning in default_inclusion.exclude_venues:
                                    pass
                                elif any(venue_tuning in venue_list for venue_list in default_inclusion.exclude_lists):
                                    pass
                                else:
                                    results.append(zone_data)
                            elif venue_tuning in default_inclusion.include_venues:
                                results.append(zone_data)
                            elif any(venue_tuning in venue_list for venue_list in default_inclusion.include_lists):
                                results.append(zone_data)
        return results

class MapViewPickerInteraction(LotPickerMixin, PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The object picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.MAP_VIEW, tuning_group=GroupNames.PICKERTUNING, dialog_locked_args={'text_cancel': None, 'text_ok': None, 'title': None, 'text': None, 'text_tokens': DEFAULT, 'icon': None, 'secondary_icon': None, 'phone_ring_type': PhoneRingType.NO_RING}), 'actor_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the actor when a picker \n            selection has been made.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'target_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the sim targetted', tuning_group=GroupNames.PICKERTUNING), 'bypass_picker_on_single_choice': Tunable(description='\n            If this is checked, bypass the picker if only one option is available.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    def _push_continuations(self, zone_datas):
        if not self.target_continuation:
            insert_strategy = QueueInsertStrategy.LAST
        else:
            insert_strategy = QueueInsertStrategy.NEXT
        try:
            picked_zone_set = {zone_data.zone_id for zone_data in zone_datas if zone_data is not None}
        except TypeError:
            picked_zone_set = {zone_datas.zone_id}
        self.interaction_parameters['picked_zone_ids'] = frozenset(picked_zone_set)
        if self.actor_continuation:
            self.push_tunable_continuation(self.actor_continuation, insert_strategy=insert_strategy, picked_zone_ids=picked_zone_set)
        if self.target_continuation:
            self.push_tunable_continuation(self.target_continuation, insert_strategy=insert_strategy, actor=self.target, picked_zone_ids=picked_zone_set)

    def _create_dialog(self, owner, target_sim=None, target=None, **kwargs):
        traveling_sims = []
        picked_sims = self.get_participants(ParticipantType.PickedSim)
        if picked_sims:
            traveling_sims = list(picked_sims)
        elif target is not None and target.is_sim and target is not self.sim:
            traveling_sims.append(target)
        dialog = self.picker_dialog(owner, title=lambda *_, **__: self.get_name(), resolver=self.get_resolver(), traveling_sims=traveling_sims)
        self._setup_dialog(dialog, **kwargs)
        dialog.set_target_sim(target_sim)
        dialog.set_target(target)
        dialog.add_listener(self._on_picker_selected)
        return dialog

    def _run_interaction_gen(self, timeline):
        choices = self._get_valid_lot_choices(self.target, self.context)
        if self.bypass_picker_on_single_choice and len(choices) == 1:
            self._push_continuations(choices[0])
            return True
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        return True

    @flexmethod
    def create_row(cls, inst, tag):
        return LotPickerRow(zone_data=tag, option_id=tag.zone_id, tag=tag)

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if cls._get_valid_lot_choices(target, context):
            return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for filter_result in inst_or_cls._get_valid_lot_choices(target, context):
            logger.info('LotPicker: add zone_data:{}', filter_result)
            yield LotPickerRow(zone_data=filter_result, option_id=filter_result.zone_id, tag=filter_result)

    def _on_picker_selected(self, dialog):
        results = dialog.get_result_tags()
        if results:
            self._push_continuations(results)

    def on_choice_selected(self, choice_tag, **kwargs):
        result = choice_tag
        if result is not None:
            self._push_continuations(result)
