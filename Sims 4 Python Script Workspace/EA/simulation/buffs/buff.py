from routing import PathNodeTransitionfrom timeit import itertoolsimport operatorfrom animation.awareness.awareness_tuning import AwarenessModifiersfrom audio.voice.voice_pitch import VoicePitchModifierfrom broadcasters.broadcaster_request import BroadcasterRequestfrom buffs import BuffPolarity, Appropriatenessfrom buffs.appearance_modifier.appearance_modifier import AppearanceModifierfrom buffs.buff_display_type import BuffDisplayTypefrom buffs.buff_telemetry import write_buff_telemetry, TELEMETRY_HOOK_ADD_BUFF, TELEMETRY_HOOK_REMOVE_BUFFfrom buffs.tunable import BuffReference, TunableBuffReferencefrom clock import interval_in_sim_minutesfrom element_utils import build_critical_section_with_finallyfrom event_testing.resolver import SingleSimResolver, SingleObjectResolverfrom game_effect_modifier.game_effect_modifiers import GameEffectModifiersfrom interactions.utils.statistic_element import PeriodicStatisticChangeElementfrom interactions.utils.tunable import TunableAffordanceLinkListfrom objects import ALL_HIDDEN_REASONSfrom objects.mixins import MixerActorMixin, MixerProviderMixin, InstancedSuperAffordanceProviderMixin, TargetSuperAffordanceProviderMixinfrom routing.portals.portal_tuning import PortalFlagsfrom routing.route_enums import RouteEventType, RoutingStageEventfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom routing.walkstyle.walkstyle_behavior_override import WalkstyleBehaviorOverridefrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom sims.sim_info_utils import apply_super_affordance_commodity_flags, remove_super_affordance_commodity_flagsfrom sims.template_affordance_provider.tunable_provided_template_affordance import TunableProvidedTemplateAffordancefrom sims4.collections import frozendictfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryfrom sims4.tuning.instances import HashedTunedInstanceMetaclass, TuningClassMixinfrom sims4.tuning.tunable import Tunable, TunableList, TunableVariant, TunableResourceKey, OptionalTunable, TunableReference, TunableRange, TunableEnumEntry, TunableSet, TunableTuple, TunableMapping, TunableEnumWithFilter, TunableEnumFlags, TunablePercentfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import blueprintmethod, blueprintpropertyfrom singletons import DEFAULTfrom situations.tunable import TunableSituationStartfrom statistics.commodity import CommodityState, RuntimeCommodity, CommodityTimePassageFixupTypefrom statistics.statistic_categories import StatisticCategoryfrom statistics.statistic_ops import StatisticAddOpfrom tag import Tagfrom teleport.teleport_enums import TeleportStylefrom vfx import PlayEffect, PlayMultipleEffectsimport enumimport event_testing.testsimport interactions.base.mixer_interactionimport servicesimport sims4.logimport sims4.resourcesimport statistics.static_commodityimport tagimport topics.topiclogger = sims4.log.Logger('Buffs')
class BuffHandler:

    def __init__(self, sim, buff_type, buff_reason=None):
        self._sim = sim
        self._handle_id = None
        self._buff_type = buff_type
        self._buff_reason = buff_reason

    def begin(self, _):
        self._handle_id = self._sim.add_buff(self._buff_type, self._buff_reason)

    def end(self, _):
        if self._handle_id is not None:
            try:
                self._sim.remove_buff(self._handle_id, on_destroy=self._sim.is_being_destroyed)
            except AttributeError as exc:
                sim_info = self._sim.sim_info
                sim_lod = None
                if sim_info is not None:
                    sim_lod = sim_info.lod
                raise AttributeError('{} \n BuffType:{} \n BeingDestroyed:{} \n SimInfoLOD: {} '.format(exc, self._buff_type, self._sim.is_being_destroyed, str(sim_lod)))
NO_TIMEOUT = (0, 0)
class MotiveOverlayType(enum.Int):
    INVALID = 0
    POWER_WARNING = 1

class Buff(RouteEventProviderMixin, InstancedSuperAffordanceProviderMixin, TargetSuperAffordanceProviderMixin, MixerActorMixin, MixerProviderMixin, TuningClassMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.BUFF)):
    INSTANCE_TUNABLES = {'buff_name': TunableLocalizedStringFactory(description='\n        Name of buff.\n        ', allow_none=True, tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'buff_description': TunableLocalizedString(description='\n        Tooltip description of the Buff Effect.\n        ', allow_none=True, tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'icon': TunableResourceKey(description='\n        Icon to be displayed for buff\n        ', default=None, resource_types=sims4.resources.CompoundTypes.IMAGE, tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'ui_sort_order': Tunable(description='\n        Order buff should be sorted in UI.\n        ', tunable_type=int, tuning_group=GroupNames.UI, default=1, export_modes=ExportModes.All), 'visible': Tunable(description='\n        Whether this buff should be visible in the UI.\n        ', tunable_type=bool, default=True, tuning_group=GroupNames.UI), 'audio_sting_on_remove': TunableResourceKey(description='\n        The sound to play when this buff is removed.\n        ', default=None, resource_types=(sims4.resources.Types.PROPX,), export_modes=ExportModes.All), 'is_npc_only': Tunable(description='\n        If checked, this buff will get removed from Sims that have a home when\n        the zone is loaded or whenever they switch to a household that has a\n        home zone.\n        ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'audio_sting_on_add': TunableResourceKey(description='\n        The sound to play when this buff is added.\n        ', default=None, resource_types=(sims4.resources.Types.PROPX,), export_modes=ExportModes.All), 'voice_pitch_modifier': OptionalTunable(description="\n        If enabled, this buff will apply a modifier to the Sim's voice pitch\n        for its duration.\n        ", tunable=VoicePitchModifier.TunableFactory(description="\n            A modifier for the Sim's voice pitch for the duration of this buff.\n            ")), 'broadcaster': OptionalTunable(description='\n        If enabled, this buff will apply a broadcaster to the Sim while the\n        buff is active.\n        ', tunable=BroadcasterRequest.TunableFactory(locked_args={'participant': None, 'offset_time': None})), 'show_timeout': Tunable(description='\n        Whether timeout should be shown in the UI.\n        ', tunable_type=bool, default=True, tuning_group=GroupNames.UI), 'success_modifier': Tunable(description='\n        Base chance delta for interaction success\n        ', tunable_type=int, default=0), 'interactions': OptionalTunable(TunableTuple(weight=Tunable(description='\n            The selection weight to apply to all interactions added by this\n            buff. This takes the place of the SI weight that would be used on\n            SuperInteractions.\n            ', tunable_type=float, default=1), scored_commodity=TunableReference(description="\n            The commodity that is scored when deciding whether or not to \n            perform these interactions.  This takes the place of the commodity\n            scoring for the SuperInteraction when Subaction Autonomy scores\n            all of the SI's in the SI State.  If this is None, the default \n            value of autonomy.autonomy_modes.SUBACTION_MOTIVE_UTILITY_FALLBACK_SCORE \n            will be used.\n            ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity',), allow_none=True), interaction_items=TunableAffordanceLinkList(description='\n            Mixer interactions to add to the Sim when this buff is active.\n            ', class_restrictions=(interactions.base.mixer_interaction.MixerInteraction,))), tuning_group=GroupNames.ANIMATION), 'topics': TunableList(description='\n        Topics that should be added to sim when buff is added.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TOPIC), class_restrictions=topics.topic.Topic)), 'game_effect_modifier': GameEffectModifiers.TunableFactory(description="\n        A list of effects that that can modify a Sim's behavior.\n        "), 'mood_type': TunableReference(description='\n        The mood that this buff pushes onto the owning Sim. If None, does\n        not affect mood.\n        ', manager=services.get_instance_manager(sims4.resources.Types.MOOD), allow_none=True, export_modes=ExportModes.All), 'mood_weight': TunableRange(description='\n        Weight for this mood. The active mood is determined by summing all\n        buffs and choosing the mood with the largest weight.\n        ', tunable_type=int, default=0, minimum=0, export_modes=ExportModes.All), 'buff_cost': Tunable(description='\n        The cost in simolean that the buff would have. \n        Ex. Create family recipes with buffs that have a cost.\n        ', tunable_type=int, default=0), 'buff_notification_info': OptionalTunable(TunableTuple(description="\n        If enabled, when Buff Notification is tuned the buff's text and \n        priority will be used to determine what will show in a TNS.\n        ", text=TunableLocalizedStringFactory(description='\n            Text to be displayed in the TNS. Text tokens for this text should be tuned in Buff Notification.\n            '), priority=TunableRange(description="\n            Buff priority to be displayed in the TNS. A higher numbered priority buff will be shown over \n            a lower one. If two buff's priorities are tied, the tied buff most recently added will show.\n            ", tunable_type=int, minimum=0, maximum=20, default=0))), 'proximity_detection_tests': OptionalTunable(description="\n        Whether or not this buff should be added because of a Sim's proximity\n        to an object with a Proximity Component with this buff in its buffs\n        list.\n        ", tunable=event_testing.tests.TunableTestSet(description="\n            A list of tests groups. At least one must pass all its sub-tests to\n            pass the TestSet.\n            \n            Actor is the one who receives the buff.\n            \n            If this buff is for two Sims in proximity to each other, only Actor\n            and TargetSim should be tuned as Participant Types. Example: A Neat\n            Sim is disgusted when around a Sim that has low hygiene. The test\n            will be for Actor having the Neat trait and for TargetSim with low\n            hygiene motive.\n\n            If this buff is for a Sim near an object, only use participant\n            types Actor and Object. Example: A Sim who likes classical music\n            should get a buff when near a stereo that's playing classical\n            music. The test will be for Actor liking classical music and for\n            Object in the state of playing classical music.\n            "), enabled_by_default=False, disabled_name='no_proximity_detection', enabled_name='proximity_tests'), 'proximity_buff_added_reason': OptionalTunable(tunable=TunableLocalizedString(description="\n            If this is a proximity buff, this field will be the reason for why\n            the Sim received this buff. Doesn't use tokens.\n            "), enabled_by_default=False, disabled_name='no_proximity_add_reason', enabled_name='proximity_add_reason'), '_add_test_set': OptionalTunable(description='\n        Whether or not this buff should be added.\n        ', tunable=event_testing.tests.TunableTestSet(description='\n            A list of tests groups. At least one must pass all its sub-tests to\n            pass the TestSet. Only Actor should be tuned as Participant\n            Types.The Actor is the Sim that will receive the buff if all tests\n            pass."\n            '), enabled_by_default=False, disabled_name='always_allowed', enabled_name='tests_set'), 'awareness_modifiers': AwarenessModifiers.TunableFactory(tuning_group=GroupNames.ANIMATION), 'walkstyle': OptionalTunable(description="\n        If enabled, specify a walkstyle override to apply to the Sim while this\n        buff is active.\n        \n        e.g.:\n         Sims with the 'bummed' buff walk in a sad fashion.\n        ", tunable=WalkStyleRequest.TunableFactory(), tuning_group=GroupNames.ANIMATION), 'walkstyle_behavior_override': OptionalTunable(description="\n        If enabled, define walkstyle behavior overrides to apply to the Sim\n        while this buff is active.\n        \n        e.g.:\n         * Sims who are Pregnant won't run. \n         * Sims who are Wild might run indoors, and for shorter distances.\n        ", tunable=WalkstyleBehaviorOverride.TunableFactory(), tuning_group=GroupNames.ANIMATION), 'teleport_style': OptionalTunable(description='\n        If enabled, instead of doing its default walkstyle, a Sim will use \n        the specified teleport style to move to its final goal.\n        ', tunable=TunableEnumEntry(description='\n            Teleport style to use.\n            ', tunable_type=TeleportStyle, default=TeleportStyle.NONE, invalid_enums=(TeleportStyle.NONE,), pack_safe=True), tuning_group=GroupNames.ANIMATION), 'portal_cost_override': TunableList(description="\n        Override the portal cost for the specific portal during the buff's period. If multiple buffs provide \n        different costs, the newer cost will override the old cost.\n        ", tunable=TunableTuple(description="\n            Override the portal cost for the specific portal during the buffs' period. If multiple buffs provide \n            different costs, the newer cost will override the old cost.\n            ", object_tag=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID), new_cost=TunableRange(description="\n                a float indicating the new cost of the portal. Cost can't be \n                negative otherwise routing failure could happen.\n                ", tunable_type=float, default=0.0, minimum=0.0)), tuning_group=GroupNames.SPECIAL_CASES), 'portal_flags_override': TunableTuple(description="\n            Override PortalFlags bits on a Sim's routing context,\n            which are used to allow sims to traverse portals that also have\n            these flags tuned on them, via the portal's Required Portal Flags\n            tuning.\n            ", set_flags=OptionalTunable(TunableTuple(description="\n                Tuple of allowance, discouragement, and exclusion flags that will be set\n                on the Sim's routing context for the duration of this buff.\n                ", portal_allowance_flags=TunableEnumFlags(description='\n                    When this buff is present, bits tuned here will be set on \n                    the Sim allowed portal flags.\n                    \n                    When the buff is removed, the tuned bits will be unset.\n                    \n                    NOTE: This functionality does not care what the existing \n                    value of the bits are, and this will do exactly what it \n                    says, overwriting any previous value.\n                    ', enum_type=PortalFlags, allow_no_flags=True), portal_discouragement_flags=TunableEnumFlags(description='\n                    When this buff is present, bits tuned here will be set on \n                    the Sim discouragement portal flags.\n                    \n                    When the buff is removed, the tuned bits will be unset.\n                    \n                    NOTE: This functionality does not care what the existing \n                    value of the bits are, and this will do exactly what it \n                    says, overwriting any previous value.\n                    ', enum_type=PortalFlags, allow_no_flags=True), portal_exclusion_flags=TunableEnumFlags(description='\n                    When this buff is present, bits tuned here will be set on \n                    the Sim exclusion portal flags.\n\n                    When the buff is removed, the tuned bits will be unset.\n\n                    NOTE: This functionality does not care what the existing \n                    value of the bits are, and this will do exactly what it \n                    says, overwriting any previous value.\n                    ', enum_type=PortalFlags, allow_no_flags=True))), unset_flags=OptionalTunable(TunableTuple(description="\n                Tuple of allowance, discouragement, and exclusion flags to be removed \n                from the Sim's routing context for the duration of this buff.\n                ", portal_allowance_flags=TunableEnumFlags(description='\n                    When this buff is present, bits tuned here will be unset on \n                    the Sim allowed portal flags.\n                    \n                    When the buff is removed, the tuned bits will be set.\n                    \n                    NOTE: This functionality does not care what the existing \n                    value of the bits are, and this will do exactly what it \n                    says, overwriting any previous value.\n                    ', enum_type=PortalFlags, allow_no_flags=True), portal_discouragement_flags=TunableEnumFlags(description='\n                    When this buff is present, bits tuned here will be unset on \n                    the Sim discouragement portal flags.\n                    \n                    When the buff is removed, the tuned bits will be set.\n                    \n                    NOTE: This functionality does not care what the existing \n                    value of the bits are, and this will do exactly what it \n                    says, overwriting any previous value.\n                    ', enum_type=PortalFlags, allow_no_flags=True), portal_exclusion_flags=TunableEnumFlags(description='\n                    When this buff is present, bits tuned here will be unset on \n                    the Sim exclusion portal flags.\n\n                    When the buff is removed, the tuned bits will be set.\n\n                    NOTE: This functionality does not care what the existing \n                    value of the bits are, and this will do exactly what it \n                    says, overwriting any previous value.\n                    ', enum_type=PortalFlags, allow_no_flags=True))), tuning_group=GroupNames.SPECIAL_CASES), 'teleport_cost_multiplier': OptionalTunable(description='\n        If enabled, cost of the teleport will be affected by the multiplier.\n        ', tunable=Tunable(description='\n            Float value to multiply the teleport cost whenever a teleport\n            action is triggered.\n            ', tunable_type=float, default=1.0), tuning_group=GroupNames.SPECIAL_CASES), 'vfx': TunableVariant(description='\n        vfx to play on the sim when buff is added.\n        ', play_effect=PlayEffect.TunableFactory(), play_multiple_effects=PlayMultipleEffects.TunableFactory(), locked_args={'no_effect': None}, default='no_effect', tuning_group=GroupNames.ANIMATION), 'static_commodity_to_add': TunableSet(description='\n        Static commodity that is added to the sim when buff is added to sim.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY), class_restrictions=statistics.static_commodity.StaticCommodity, pack_safe=True)), '_operating_commodity': TunableReference(description='\n        This is the commodity that is considered the owning commodity of the\n        buff.  Multiple commodities can reference the same buff.  This field\n        is used to determine which commodity is considered the authoritative\n        commodity.  This only needs to be filled if there are more than one\n        commodity referencing this buff.\n        \n        For example, motive_hunger and starvation_commodity both reference\n        the same buff.  Starvation commodity is marked as the operating\n        commodity.  If outcome action asks the buff what commodity it should\n        apply changes to it will modify the starvation commodity.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity',), allow_none=True), '_temporary_commodity_info': OptionalTunable(TunableTuple(description='\n        Tunables relating to the generation of a temporary commodity to control\n        the lifetime of this buff.  If enabled, this buff has no associated\n        commodities and will create its own to manage its lifetime.\n        ', max_duration=Tunable(description='\n            The maximum time buff can last for.  Example if set to 100, buff\n            only last at max 100 sim minutes.  If washing hands gives +10 sim\n            minutes for buff. Trying to run interaction for more than 10 times,\n            buff time will not increase\n            ', tunable_type=int, default=100), categories=TunableSet(description='\n            List of categories that this commodity is part of. Used for buff\n            removal by category.\n            ', tunable=StatisticCategory, needs_tuning=True), persists=Tunable(description='\n            If enabled, the temporary commodity will persist.\n            ', tunable_type=bool, default=True))), '_appropriateness_tags': TunableSet(description='\n            A set of tags that define the appropriateness of the\n            interactions allowed by this buff.  All SIs are allowed by\n            default, so adding this tag generally implies that it is always\n            allowed even if another buff has said that it is\n            inappropriate.\n            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID)), '_inappropriateness_tags': TunableSet(description="\n            A set of tags that define the inappropriateness of the\n            interactions allowed by this buff.  All SIs are allowed by\n            default, so adding this tag generally implies that it's not\n            allowed.\n            ", tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID)), '_add_buff_on_remove': OptionalTunable(tunable=TunableTuple(description='\n            A buff and its associated tests to apply when the current buff is removed.\n            ', tests=event_testing.tests.TunableTestSet(description='\n                A list of tests groups. At least one must pass all its sub-tests to\n                pass the TestSet. Only Actor should be tuned as Participant\n                Types.The Actor is the Sim that will receive the buff if all tests\n                pass."\n                '), buff=TunableBuffReference())), '_loot_on_addition': TunableList(description='\n        Loot that will be applied when buff is added to sim.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), '_loot_on_instance': TunableList(description='\n        Loot that will be applied when a sim with this buff is instanced.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), '_loot_on_removal': TunableList(description='\n        Loot that will be applied when buff is removed from sim.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), 'refresh_on_add': Tunable(description='\n        This buff will have its duration refreshed if it gets added to a Sim\n        who already has the same buff.\n        ', tunable_type=bool, default=True), 'reloot_on_add': Tunable(description="\n        This buff will regive it's loots if it gets added to a Sim\n        who already has the same buff.\n        ", tunable_type=bool, default=False), 'flip_arrow_for_progress_update': Tunable(description='\n        This only for visible buffs with an owning commodity.\n        \n        If unchecked and owning commodity is increasing an up arrow will\n        appear on the buff and if owning commodity is decreasing a down arrow\n        will appear.\n        \n        If checked and owning commodity is increasing then a down arrow will\n        appear on the buff and if owning commodity is decreasing an up arrow\n        will appear.\n        \n        Example of being checked is motive failing buffs, when the commodity is\n        increasing we need to show down arrows for the buff.\n        ', tunable_type=bool, default=False, tuning_group=GroupNames.UI), 'timeout_string': TunableLocalizedStringFactory(description='\n        String to override the the timeout text. The first token (0.TimeSpan)\n        will be the timeout time and the second token will (1.String) will be\n        the  buff this buff is transitioning to.\n        \n        If this buff is not transitioning to another buff the only token valid\n        in string is 0.Timespan\n        \n        Example: If this is the hungry buff, then the commodity is decaying to\n        starving buff. Normally timeout in tooltip will say \'5 hours\'. With\n        this set it will pass in the next buff name as the first token into\n        this localized string.  So if string provided is \'Becomes {1.String}\n        in: {0.TimeSpan}. Timeout tooltip for buff now says \'Becomes Starving\n        in: 5 hours\'.\n        \n        Example: If buff is NOT transitioning into another buff. Localized\n        string could be "Great time for :{0.Timespan}". Buff will now say\n        "Great time for : 5 hours"\n        ', allow_none=True, tuning_group=GroupNames.UI, export_modes=(ExportModes.ClientBinary,)), 'timeout_string_no_next_buff': TunableLocalizedStringFactory(description="\n        String to override the the timeout text. The first token (0.TimeSpan)\n        will be the timeout time.  \n        \n        If this is not None it will be used instead of the timeout_string if \n        there is no next buff.  The issue is that it's possible for the \n        convergence point to change so where normally there is a next buff \n        (and the timeout string expects it) under certain conditions there won't\n        be (and thus you get an error because the timeout string expects it.)\n        \n        Ideally there would have simply been a string with the buff and one\n        without, and buffs would have specified one and/or both as appropriate,\n        but that changing now is unrealistic.\n        ", allow_none=True, tuning_group=GroupNames.UI, export_modes=(ExportModes.ClientBinary,)), 'appearance_modifier': OptionalTunable(AppearanceModifier.TunableFactory()), 'suppress_social_front_page_when_targeted': Tunable(description='\n        If set to true, then the owner of this buff will not show the socials\n        top list when targeted by the player for socials.\n        ', tunable_type=bool, default=False), 'discourage_route_to_join_social_group': Tunable(description='\n        If True, then this Sim will not route to join a social group unless\n        the social group has a specific anchor object or group leader.\n        \n        If False then this Sim will route to join an already established social\n        group, even if they are the target of the Social. In that case the Actor\n        will stay put and the target sim will route to where the group is.\n        ', tunable_type=bool, default=False), 'additional_posture_costs': TunableMapping(description='\n        For any posture in this mapping, its cost is modified by the\n        specified value for the purpose of transitioning for this\n        interaction.\n        \n        The values tuned here will be added to the values tuned on the \n        interaction as well as other autonomy modifiers on the Sim.\n        \n        For example, Sit is a generally cheap posture. However, some\n        interactions (such as Nap), would want to penalize Sit in favor\n        of something more targeted (such as the two-seated version of\n        nap).\n        ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.POSTURE), pack_safe=True), value_type=Tunable(description='\n            The cost override for the specified posture.\n            ', tunable_type=int, default=0)), 'tags': TunableSet(description='\n        A list of tags associated with this buff.\n        ', tunable=TunableEnumWithFilter(description='\n            A tag associated with this buff.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,), filter_prefixes=('buff',), pack_safe=True)), 'motive_panel_overlays': TunableMapping(description='\n        Allows tuning an overlay on the motives panel.\n        ', key_name='Overlay Type', key_type=MotiveOverlayType, value_name='Linked Motive', value_type=TunableReference(description='\n            A commodity on the motives panel to which the overlay will be\n            applied.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity',), pack_safe=True), tuning_group=GroupNames.SPECIAL_CASES), 'routing_periodic_stat_change': OptionalTunable(description='\n        If enabled, Sims with this buff will gain/lose certain statistics for\n        the duration of routes.\n        \n        e.g. Sims with the "Toddler" buff gain Movement skill while routing.\n        ', tunable=PeriodicStatisticChangeElement.TunableFactory(operation_overrides={'locked_args': {'advertise': False, 'exclusive_to_owning_si': False}}), tuning_group=GroupNames.ROUTING), 'route_events': OptionalTunable(description='\n        If enabled, Sims can play route events on routes while this buff is\n        active.\n        ', tuning_group=GroupNames.ROUTING, tunable=TunableTuple(description='\n            There are two kinds of route events for buffs. One is an idle\n            that has a chance to play every route at a low priority. One is\n            repeating and gets dispersed throughout the route at a very low\n            priority.\n            ', single_events=TunableList(description='\n                Single Route Events to possibly play once on a route while the\n                Sim has this buff active.\n                ', tunable=TunableReference(description='\n                    A single route event that may happen once when a Sim is\n                    routing with this buff on them.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RouteEvent',), pack_safe=True)), repeating_events=TunableList(description='\n                Repeating Route Events which can occur multiple times over the\n                course of a route while this buff is active.\n                ', tunable=TunableReference(description="\n                    A repeating route event which will be dispersed throughout\n                    a Sim's route while they have this buff on them.\n                    ", manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RouteEvent',), pack_safe=True)), first_indoor=TunableList(description='\n                Route events that will be scheduled right after a sim enters an\n                indoor area. Only 1 will be able to play.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RouteEvent',), pack_safe=True)), last_indoor=TunableList(description='\n                Route events that will be scheduled right before a sim enters \n                an outdoor area.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RouteEvent',), pack_safe=True)), on_level_change_indoors=TunableList(description='\n                Route events that will be scheduled right after a sim changes\n                level indoors.\n                \n                These route events will only be scheduled for\n                the final level transition indoors. For example, if a sim\n                routes from the ground floor to the fourth floor, the only\n                route event that will be scheduled is when the sim transitions\n                from the third floor to the fourth floor.\n                ', tunable=TunableTuple(lot_level_tests=event_testing.tests.TunableTestSet(description='\n                        Tests that will run on the LotLevel. If these tests pass,\n                        the corresponding route event can be scheduled.\n                        '), route_event=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RouteEvent',), pack_safe=True), apply_loot_actions_at_end_of_route=Tunable(description='\n                        If checked, we will apply the loot actions tuned on\n                        the Route Event field when the sim completes the route.\n                        This ensures that even in the case where a route is\n                        canceled and the sim does not get to play the route\n                        event, its loot will still get pushed.\n                        ', tunable_type=bool, default=True))))), 'auto_situation': OptionalTunable(description='\n        If enabled, instantiated Sims with this buff will host the tuned\n        situation. Unlike situations started via the buff\'s loot actions, this\n        situation is automatically destroyed when the Sim loses the buff.\n        \n        e.g. Toddlers are automatically made hosts of a "Caregiver" situation.\n        ', tunable=TunableSituationStart(locked_args={'invite_participants': frozendict(), 'invite_picked_sims': False, 'invite_target_sim': False}), tuning_group=GroupNames.SITUATION), 'provided_template_affordances': OptionalTunable(description='\n        If enabled, allows the owner of the buff to provide a suite of\n        interactions that have template data.\n        ', tunable=TunableProvidedTemplateAffordance(description='\n            Sims will provide the tuned list of affordances for the\n            specified duration.\n            ')), '_ignore_weather': Tunable(description='\n        If True, any sim under the affects of this buff is no longer weather\n        aware for the duration of the buff, and is immune to temperature.\n        \n        Will receive "end" loots for any weather currently affecting the sim.\n        Will not receive start loots until the buff is removed, at which time\n        the sim will receive start loots for the current weather.\n        \n        Note:  Since weather awareness doesn\'t persist, (reapplied on load)\n        Buffs that ignore weather can\'t either.\n        ', tunable_type=bool, default=False), 'report_telemetry': Tunable(description='\n        If True, this buff will report when it is added to or removed from an instanced active household member Sim.\n        ', tunable_type=bool, default=False, tuning_group=GroupNames.TELEMETRY), 'line_of_sight_distance_multiplier': OptionalTunable(description='\n        Multiplied by the default line-of-sight distance via the Line of Sight component.\n        Used to limit (or enhance) line of sight distance for Sims with this buff.\n        ', tunable=TunablePercent(description='\n            Percentage multiplier to use.\n            ', default=100))}
    is_mood_buff = False
    exclusive_index = None
    exclusive_weight = None
    trait_replacement_buffs = None
    _owning_commodity = None
    refresh_lock = False
    needs_temporary_commodity_generation = False

    @blueprintmethod
    def _verify_tuning_callback(self):
        if self.visible and not self.mood_type:
            logger.error('No mood type set for visible buff: {}.  Either provide a mood or make buff invisible.', self, owner='Tuning')
        if self._ignore_weather and self._temporary_commodity_info and self._temporary_commodity_info.persists:
            logger.error('Buff {} that ignores weather can not persist.', self, owner='Tuning')

    @blueprintmethod
    def _tuning_loaded_callback(self):
        if self._temporary_commodity_info is None:
            self.needs_temporary_commodity_generation = False
        else:
            self.needs_temporary_commodity_generation = True
            temp_commodity_res_key = RuntimeCommodity.get_resource_key(self.tuning_name)
            statistic_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            statistic_manager.temp_commodity_buff_mapping[temp_commodity_res_key.instance] = self

    def __init__(self, owner, commodity_guid, replacing_buff_type, transition_into_buff_id, additional_static_commodities_to_add=None, remove_on_zone_unload=True, init_blueprint_func=None):
        if init_blueprint_func is not None:
            tuning_blueprint = init_blueprint_func.__self__
            if tuning_blueprint.needs_temporary_commodity_generation:
                tuning_blueprint.try_generate_temp_commodity_on_demand()
            init_blueprint_func(self)
        self._owner = owner
        self.commodity_guid = commodity_guid
        self.effect_modification = self.game_effect_modifier(owner)
        self.buff_reason = None
        self.handle_ids = []
        self._static_commodites_added = None
        self._replacing_buff_type = replacing_buff_type
        self._mood_override = None
        self._vfx = None
        self.transition_into_buff_id = transition_into_buff_id
        self._walkstyle_request = None
        self._additional_static_commodities_to_add = additional_static_commodities_to_add
        self._broadcaster_request = None
        self._voice_pitch_modifier = None
        if self.appearance_modifier is not None:
            owner.register_for_outfit_changed_callback(self._on_sim_outfit_changed)
        self._auto_situation_id = None
        self._remove_on_zone_unload = remove_on_zone_unload
        if self._ignore_weather and not self._remove_on_zone_unload:
            logger.error('Buff {} that ignores weather that was added via trait or other game service can not persist', self, owner='Tuning')

    @blueprintmethod
    def can_add(self, owner):
        if self._add_test_set is not None:
            resolver = SingleSimResolver(owner)
            result = self._add_test_set.run_tests(resolver)
            if not result:
                return False
        return True

    @blueprintproperty
    def polarity(self):
        if self.mood_type is not None:
            return self.mood_type.buff_polarity
        return BuffPolarity.NEUTRAL

    @blueprintproperty
    def buff_type(self):
        if self.is_blueprint:
            return self
        return self.tuning_blueprint

    @property
    def display_type(self):
        return BuffDisplayType.DEFAULT

    @blueprintproperty
    def get_success_modifier(self):
        return self.success_modifier/100

    @blueprintproperty
    def is_changeable(self):
        if self.mood_type is not None:
            return self.mood_type.is_changeable
        return False

    @blueprintproperty
    def has_temporary_commodity(self):
        return self._temporary_commodity_info is not None

    @blueprintproperty
    def add_test_set(self):
        return self._add_test_set

    @blueprintmethod
    def add_owning_commodity(self, commodity):
        if self._owning_commodity is None:
            self._owning_commodity = commodity
        elif self._operating_commodity is None and self._owning_commodity is not commodity:
            logger.error('Please fix tuning: Multiple commodities reference {} : commodity:{},  commodity:{}, Set _operating_commodity to authoratative commodity', self, self._owning_commodity, commodity)

    @blueprintmethod
    def try_generate_temp_commodity_on_demand(self):
        if self._owning_commodity is None:
            self._create_temporary_commodity()
        elif issubclass(self._owning_commodity, RuntimeCommodity):
            self._create_temporary_commodity(proxied_commodity=self._owning_commodity)
        self.needs_temporary_commodity_generation = False

    @blueprintproperty
    def commodity(self):
        if self.is_blueprint and self.needs_temporary_commodity_generation:
            self.try_generate_temp_commodity_on_demand()
        if self.is_blueprint or self._replacing_buff_type is not None:
            return self._replacing_buff_type.commodity
        return self._operating_commodity or self._owning_commodity

    @blueprintmethod
    def build_critical_section(self, sim, buff_reason, *sequence):
        buff_handler = BuffHandler(sim, self, buff_reason=buff_reason)
        return build_critical_section_with_finally(buff_handler.begin, sequence, buff_handler.end)

    @blueprintmethod
    def _create_temporary_commodity(self, proxied_commodity=None, create_buff_state=True, initial_value=DEFAULT):
        if proxied_commodity is None:
            proxied_commodity = RuntimeCommodity.generate(self.tuning_name)
        proxied_commodity.decay_rate = 1
        proxied_commodity.convergence_value = 0
        proxied_commodity.remove_on_convergence = True
        proxied_commodity.visible = False
        proxied_commodity.max_value_tuning = self._temporary_commodity_info.max_duration
        proxied_commodity.min_value_tuning = 0
        proxied_commodity.initial_value = initial_value if initial_value is not DEFAULT else self._temporary_commodity_info.max_duration
        proxied_commodity._categories = self._temporary_commodity_info.categories
        proxied_commodity._time_passage_fixup_type = CommodityTimePassageFixupType.FIXUP_USING_TIME_ELAPSED
        proxied_commodity.persisted_tuning = self._temporary_commodity_info.persists
        if create_buff_state:
            buff_to_add = BuffReference(buff_type=self)
            new_state_add_buff = CommodityState(value=0.1, buff=buff_to_add)
            new_state_remove_buff = CommodityState(value=0, buff=BuffReference())
            proxied_commodity.commodity_states = [new_state_remove_buff, new_state_add_buff]
        self.add_owning_commodity(proxied_commodity)

    @blueprintmethod
    def get_appropriateness(self, tags):
        if self._appropriateness_tags & tags:
            return Appropriateness.ALLOWED
        if self._inappropriateness_tags & tags:
            return Appropriateness.NOT_ALLOWED
        return Appropriateness.DONT_CARE

    @blueprintmethod
    def appropriateness_tags(self):
        return self._appropriateness_tags

    @blueprintmethod
    def inappropriate_tags(self):
        return self._inappropriateness_tags

    @blueprintmethod
    def has_tag(self, tag):
        if self.tags and tag is None:
            return False
        return tag in self.tags

    @blueprintmethod
    def has_any_tag(self, tags):
        if not (self.tags and tags):
            return False
        return any(tag in self.tags for tag in tags)

    @property
    def mood_override(self):
        return self._mood_override

    @mood_override.setter
    def mood_override(self, value):
        if not self.is_changeable:
            logger.error('Trying to override mood for buff:{}, but mood for this is not considered changeable.', self, owner='msantander')
        self._mood_override = value

    def on_add(self, from_load=False, apply_buff_loot=True):
        self.effect_modification.on_add()
        for topic_type in self.topics:
            self._owner.add_topic(topic_type)
        if self._additional_static_commodities_to_add:
            static_commodity_iter = itertools.chain(self.static_commodity_to_add, self._additional_static_commodities_to_add)
        else:
            static_commodity_iter = self.static_commodity_to_add
        tracker = self._owner.static_commodity_tracker
        for static_commodity_type in static_commodity_iter:
            tracker.add_statistic(static_commodity_type)
            if self._static_commodites_added is None:
                self._static_commodites_added = []
            self._static_commodites_added.append(static_commodity_type)
        self.apply_interaction_lockout_to_owner()
        sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            if self._ignore_weather:
                weather_aware_component = sim.weather_aware_component
                if weather_aware_component is not None:
                    weather_aware_component.enable(False)
            if not from_load:
                self._start_vfx()
                self._start_auto_situation()
                self._apply_portal_flag_overrides(sim)
                self._apply_portal_cost_overrides(sim)
                if apply_buff_loot and self._loot_on_addition:
                    self.apply_all_loot_actions()
                if self.line_of_sight_distance_multiplier is not None:
                    sim.on_line_of_sight_changed()
                self._apply_walkstyle(sim)
                apply_super_affordance_commodity_flags(sim, self, self.super_affordances)
                if self.route_events is not None:
                    if self.route_events.first_indoor or self.route_events.on_level_change_indoors:
                        sim.set_should_track_path_transition(PathNodeTransition.PATH_NODE_TRANSITION_FIRST_INDOOR, True)
                    if self.route_events.last_indoor:
                        sim.set_should_track_path_transition(PathNodeTransition.PATH_NODE_TRANSITION_LAST_INDOOR, True)
                    if self.route_events.on_level_change_indoors:
                        sim.routing_component.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_route_ended_level_changed)
                if self.buff_type.report_telemetry:
                    write_buff_telemetry(TELEMETRY_HOOK_ADD_BUFF, self, sim)
        if self.appearance_modifier is not None:
            self._owner.appearance_tracker.add_appearance_modifiers(self.appearance_modifier.appearance_modifiers, self.buff_type.guid, self.appearance_modifier.priority, self.appearance_modifier.apply_to_all_outfits, self.appearance_modifier.additional_flags, source=self.buff_type.tuning_name)
        self._apply_voice_pitch_modifier(sim)
        self._start_providing_template_affordances()
        if self.teleport_style is not None:
            self._owner.add_teleport_style(self.buff_type.guid, self.teleport_style)
        self._apply_broadcaster(sim)
        self._apply_awareness(sim)

    def apply_all_loot_actions(self):
        sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            resolver = sim.get_resolver()
            for loot_action in self._loot_on_addition:
                loot_action.apply_to_resolver(resolver)

    def on_remove(self, apply_loot_on_remove=True):
        self.effect_modification.on_remove()
        for topic_type in self.topics:
            self._owner.remove_topic(topic_type)
        if self._static_commodites_added is not None:
            tracker = self._owner.static_commodity_tracker
            for static_commodity_type in self._static_commodites_added:
                tracker.remove_statistic(static_commodity_type)
        if self._add_buff_on_remove is not None:
            resolver = SingleSimResolver(self._owner)
            if self._add_buff_on_remove.tests.run_tests(resolver):
                self._owner.add_buff_from_op(self._add_buff_on_remove.buff.buff_type, self._add_buff_on_remove.buff.buff_reason)
        sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        self._remove_voice_pitch_modifier()
        self._release_walkstyle()
        self._release_broadcaster()
        self._release_awareness(sim)
        self._stop_providing_template_affordances()
        self.on_sim_removed()
        if sim is not None:
            if self._ignore_weather:
                weather_aware_component = sim.weather_aware_component
                if weather_aware_component is not None:
                    weather_aware_component.enable(True)
            if apply_loot_on_remove:
                resolver = sim.get_resolver()
                for loot_action in self._loot_on_removal:
                    loot_action.apply_to_resolver(resolver)
            if self.line_of_sight_distance_multiplier is not None:
                sim.on_line_of_sight_changed()
            remove_super_affordance_commodity_flags(sim, self)
            if self.route_events is not None:
                if self.route_events.first_indoor or self.route_events.on_level_change_indoors:
                    sim.set_should_track_path_transition(PathNodeTransition.PATH_NODE_TRANSITION_FIRST_INDOOR, False)
                if self.route_events.last_indoor:
                    sim.set_should_track_path_transition(PathNodeTransition.PATH_NODE_TRANSITION_LAST_INDOOR, False)
                if self.route_events.on_level_change_indoors:
                    sim.routing_component.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_route_ended_level_changed)
            if self.buff_type.report_telemetry:
                write_buff_telemetry(TELEMETRY_HOOK_REMOVE_BUFF, self, sim)
        if self.appearance_modifier is not None:
            self._owner.appearance_tracker.remove_appearance_modifiers(self.buff_type.guid, source=self.buff_type.tuning_name)
            self._owner.unregister_for_outfit_changed_callback(self._on_sim_outfit_changed)
        if self.teleport_style is not None:
            self._owner.remove_teleport_style(self.buff_type.guid, self.teleport_style)
        if self._owner.trait_tracker is not None:
            self._owner.trait_tracker.update_day_night_buffs_on_buff_removal(self)
        if sim is not None:
            if self.portal_flags_override.set_flags:
                sim.routing_component.clear_portal_mask_flag(self.portal_flags_override.set_flags.portal_allowance_flags)
                sim.routing_component.clear_portal_discouragement_mask_flag(self.portal_flags_override.set_flags.portal_discouragement_flags)
                sim.routing_component.clear_portal_exclusion_mask_flag(self.portal_flags_override.set_flags.portal_exclusion_flags)
            if self.portal_flags_override.unset_flags:
                sim.routing_component.set_portal_mask_flag(self.portal_flags_override.unset_flags.portal_allowance_flags)
                sim.routing_component.set_portal_discouragement_mask_flag(self.portal_flags_override.unset_flags.portal_discouragement_flags)
                sim.routing_component.set_portal_exclusion_mask_flag(self.portal_flags_override.unset_flags.portal_exclusion_flags)
            if len(self.portal_cost_override) > 0:
                self._clear_portal_cost_overrides(sim)

    def _on_route_ended_level_changed(self, sim, *args, path, **kwargs):
        if len(path) <= 0:
            return
        start_level_index = path[0].routing_surface_id.secondary_id
        end_level_index = sim.level
        if start_level_index == end_level_index:
            return
        lot = services.active_lot()
        lot_level_instance = lot.get_lot_level_instance(end_level_index)
        if lot_level_instance is None:
            return
        lot_level_resolver = SingleObjectResolver(lot_level_instance)
        for route_event_data in self.route_events.on_level_change_indoors:
            if not route_event_data.lot_level_tests.run_tests(lot_level_resolver):
                pass
            else:
                if not route_event_data.apply_loot_actions_at_end_of_route:
                    break
                sim_resolver = SingleSimResolver(sim)
                for loot_action in route_event_data.route_event.loot_actions:
                    loot_action.apply_to_resolver(sim_resolver)
                break

    def on_lod_increase(self, sim, old_lod, new_lod):
        if self._static_commodites_added:
            for static_commodity_type in self._static_commodites_added:
                tracker = sim.get_tracker(static_commodity_type)
                if tracker is not None and not tracker.has_statistic(static_commodity_type):
                    tracker.add_statistic(static_commodity_type)
        resolver = sim.get_resolver()
        for loot_actions in list(itertools.chain(self._loot_on_instance, self._loot_on_addition)):
            for loot_action in loot_actions.loot_actions:
                if isinstance(loot_action, StatisticAddOp):
                    loot_action.apply_to_resolver(resolver)

    def clean_up(self):
        self.effect_modification.on_remove(on_destroy=True)
        self._release_walkstyle()
        self.on_sim_removed()
        if self._static_commodites_added:
            self._static_commodites_added.clear()
            self._static_commodites_added = None

    def on_sim_ready_to_simulate(self):
        for topic_type in self.topics:
            self._owner.add_topic(topic_type)
        self.apply_interaction_lockout_to_owner()
        self._start_vfx()
        self._start_auto_situation()
        sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        self._apply_broadcaster(sim)
        self._apply_awareness(sim)
        self._apply_walkstyle(sim)
        self._apply_portal_flag_overrides(sim)
        self._apply_portal_cost_overrides(sim)
        if self._static_commodites_added:
            tracker = self._owner.static_commodity_tracker
            for static_commodity in self._static_commodites_added:
                tracker.add_statistic(static_commodity)
        resolver = sim.get_resolver()
        for loot_action in self._loot_on_instance:
            loot_action.apply_to_resolver(resolver)
        apply_super_affordance_commodity_flags(sim, self, self.super_affordances)
        if self.route_events is not None:
            if self.route_events.first_indoor:
                sim.set_should_track_path_transition(PathNodeTransition.PATH_NODE_TRANSITION_FIRST_INDOOR, True)
            if self.route_events.last_indoor:
                sim.set_should_track_path_transition(PathNodeTransition.PATH_NODE_TRANSITION_LAST_INDOOR, True)
        if self._voice_pitch_modifier is None:
            self._apply_voice_pitch_modifier(sim)

    def on_bassinet_ready_to_simulate(self):
        self._start_auto_situation()

    def _on_sim_outfit_changed(self, sim_info, outfit_category_and_index, old_outfit_category_and_index):
        if self.appearance_modifier is not None:
            for modifiers in self.appearance_modifier.appearance_modifiers:
                for entry in modifiers:
                    if not entry.modifier.is_compatible_with_outfit(outfit_category_and_index[0]):
                        self._owner.remove_buff_by_type(self.buff_type)
                        return

    def _apply_voice_pitch_modifier(self, sim):
        if self.voice_pitch_modifier is not None:
            self._voice_pitch_modifier = self.voice_pitch_modifier(sim)
            self._voice_pitch_modifier.start()

    def _remove_voice_pitch_modifier(self):
        if self._voice_pitch_modifier is not None:
            self._voice_pitch_modifier.stop()
            self._voice_pitch_modifier = None

    def _apply_broadcaster(self, sim):
        if self.broadcaster is not None and sim is not None:
            if self._broadcaster_request is None:
                self._broadcaster_request = self.broadcaster(sim)
            self._broadcaster_request.start()

    def _release_broadcaster(self):
        if self._broadcaster_request is not None:
            self._broadcaster_request.stop()
            self._broadcaster_request = None

    def _apply_walkstyle(self, sim):
        if self.walkstyle is None:
            return
        if self._walkstyle_request is not None:
            return
        self._walkstyle_request = self.walkstyle(sim)
        self._walkstyle_request.start()

    def _release_walkstyle(self):
        if self._walkstyle_request is not None:
            self._walkstyle_request.stop()
            self._walkstyle_request = None

    def _start_providing_template_affordances(self):
        template_affordance_tracker = self._owner.template_affordance_tracker
        provided_template_affordances = self.provided_template_affordances
        if template_affordance_tracker is not None and provided_template_affordances is not None:
            template_affordance_tracker.on_affordance_template_start(provided_template_affordances)

    def _stop_providing_template_affordances(self):
        template_affordance_tracker = self._owner.template_affordance_tracker
        provided_template_affordances = self.provided_template_affordances
        if template_affordance_tracker is not None and provided_template_affordances is not None:
            template_affordance_tracker.on_affordance_template_stop(provided_template_affordances)

    def _apply_awareness(self, sim):
        self.awareness_modifiers.apply_modifier(sim)

    def _release_awareness(self, sim):
        self.awareness_modifiers.remove_modifier(sim)

    def _apply_portal_flag_overrides(self, sim):
        if self.portal_flags_override.set_flags:
            sim.routing_component.set_portal_mask_flag(self.portal_flags_override.set_flags.portal_allowance_flags)
            sim.routing_component.set_portal_discouragement_mask_flag(self.portal_flags_override.set_flags.portal_discouragement_flags)
            sim.routing_component.set_portal_exclusion_mask_flag(self.portal_flags_override.set_flags.portal_exclusion_flags)
        if self.portal_flags_override.unset_flags:
            sim.routing_component.clear_portal_mask_flag(self.portal_flags_override.unset_flags.portal_allowance_flags)
            sim.routing_component.clear_portal_discouragement_mask_flag(self.portal_flags_override.unset_flags.portal_discouragement_flags)
            sim.routing_component.clear_portal_exclusion_mask_flag(self.portal_flags_override.unset_flags.portal_exclusion_flags)

    def _apply_portal_cost_overrides(self, sim):
        for portal_cost_override_item in self.portal_cost_override:
            object_tag = portal_cost_override_item.object_tag
            new_cost = portal_cost_override_item.new_cost
            sim.sim_info.set_portal_cost_override(self, object_tag, new_cost)

    def _clear_portal_cost_overrides(self, sim):
        if sim.sim_info.portal_cost_override_map(self):
            sim.sim_info.clear_portal_cost_override(self)

    def on_sim_removed(self, immediate=False):
        sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        self._release_broadcaster()
        self._release_awareness(sim)
        self._release_walkstyle()
        self._stop_auto_situation()
        if self._vfx is not None:
            self._vfx.stop(immediate=immediate)
            self._vfx = None
        self._remove_voice_pitch_modifier()

    def apply_interaction_lockout_to_owner(self):
        if self.interactions is not None:
            for mixer_affordance in self.interactions.interaction_items:
                if mixer_affordance.lock_out_time_initial is not None:
                    self._owner.set_sub_action_lockout(mixer_affordance, initial_lockout=True)

    def add_handle(self, handle_id, buff_reason=None):
        self.handle_ids.append(handle_id)
        self.buff_reason = buff_reason

    def remove_handle(self, handle_id):
        if handle_id not in self.handle_ids:
            return False
        else:
            self.handle_ids.remove(handle_id)
            if self.handle_ids:
                return False
        return True

    def provide_route_events(self, route_event_context, sim, path, failed_types=None, **kwargs):
        resolver = SingleSimResolver(sim.sim_info)
        for route_event_cls in self.route_events.single_events:
            if self.can_provide_route_event(route_event_cls, failed_types, resolver) and not (route_event_context.route_event_already_fully_considered(route_event_cls, self) or route_event_context.route_event_already_scheduled(route_event_cls)):
                route_event_context.add_route_event(RouteEventType.LOW_SINGLE, route_event_cls(provider=self, provider_required=True))
        for route_event_cls in self.route_events.repeating_events:
            if self.can_provide_route_event(route_event_cls, failed_types, resolver) and not route_event_context.route_event_already_fully_considered(route_event_cls, self):
                route_event_context.add_route_event(RouteEventType.LOW_REPEAT, route_event_cls(provider=self, provider_required=True))
        for route_event_cls in self.route_events.first_indoor:
            if self.can_provide_route_event(route_event_cls, failed_types, resolver) and not route_event_context.route_event_already_fully_considered(route_event_cls, self):
                route_event_context.add_route_event(RouteEventType.FIRST_INDOOR, route_event_cls(provider=self, provider_required=True))
        for route_event_cls in self.route_events.last_indoor:
            if self.can_provide_route_event(route_event_cls, failed_types, resolver) and not route_event_context.route_event_already_fully_considered(route_event_cls, self):
                route_event_context.add_route_event(RouteEventType.LAST_INDOOR, route_event_cls(provider=self, provider_required=True))
        if self.route_events.on_level_change_indoors:
            lot = services.active_lot()
            node = path.get_final_indoor_level_change_node()
            if node is not None:
                level_index = node.routing_surface_id.secondary_id
                lot_level = lot.get_lot_level_instance(level_index)
                if lot_level is not None:
                    lot_level_resolver = SingleObjectResolver(lot_level)
                    for route_event_data in self.route_events.on_level_change_indoors:
                        if not route_event_data.lot_level_tests.run_tests(lot_level_resolver):
                            pass
                        else:
                            route_event_cls = route_event_data.route_event
                            if self.can_provide_route_event(route_event_cls, failed_types, resolver) or not route_event_context.route_event_already_fully_considered(route_event_cls, self):
                                pass
                            else:
                                route_event_context.add_route_event(RouteEventType.ENTER_LOT_LEVEL_INDOOR, route_event_cls(time=node.time, provider=self, provider_required=True))
                                break

    def is_route_event_valid(self, route_event, time, sim, path):
        return True

    def _start_vfx(self):
        if self._vfx is None and self.vfx:
            sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            self._vfx = self.vfx(sim)
            self._vfx.start()

    def on_sim_reset(self):
        self._stop_vfx()
        self._start_vfx()

    def _stop_vfx(self):
        if self._vfx is not None:
            self._vfx.stop()
            self._vfx = None

    def _start_auto_situation(self):
        if self.auto_situation is None:
            return
        if self._auto_situation_id is not None:
            return

        def _on_situation_create(situation_id):
            self._auto_situation_id = situation_id
            situation_manager = services.get_zone_situation_manager()
            situation_manager.disable_save_to_situation_manager(situation_id)

        resolver = SingleSimResolver(self._owner)
        situation_create_fn = self.auto_situation(resolver, situation_created_callback=_on_situation_create)
        situation_create_fn()

    def _stop_auto_situation(self):
        if self._auto_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(self._auto_situation_id)
        self._auto_situation_id = None

    def _get_tracker(self):
        if self.commodity is not None:
            return self._owner.get_tracker(self.commodity)

    def get_highest_id(self):
        if self.handle_ids:
            return self.handle_ids[-1]
        return -1

    def get_commodity_instance(self):
        if self.commodity is None:
            return
        tracker = self._get_tracker()
        if tracker is None:
            return
        else:
            commodity_instance = tracker.get_statistic(self.commodity)
            if commodity_instance is None:
                return
        return commodity_instance

    def _get_absolute_timeout_time(self, commodity_instance, threshold):
        rate_multiplier = commodity_instance.get_decay_rate_modifier()
        if rate_multiplier < 1:
            time = commodity_instance.get_decay_time(threshold)
            rate_multiplier = 1
        else:
            time = commodity_instance.get_decay_time(threshold, use_decay_modifier=False)
        if time is not None and time != 0:
            time_now = services.time_service().sim_now
            time_stamp = time_now + interval_in_sim_minutes(time)
            return (time_stamp.absolute_ticks(), rate_multiplier)
        return NO_TIMEOUT

    def get_timeout_time(self):
        commodity_instance = self.get_commodity_instance()
        if commodity_instance is None:
            return NO_TIMEOUT
        buff_type = self.buff_type
        if self._replacing_buff_type is not None:
            buff_type = self._replacing_buff_type
        else:
            buff_type = self.buff_type
        state_index = commodity_instance.get_state_index_matches_buff_type(buff_type)
        if state_index is None:
            return NO_TIMEOUT
        state_lower_bound_value = commodity_instance.commodity_states[state_index].value
        if commodity_instance.convergence_value <= state_lower_bound_value:
            threshold_value = state_lower_bound_value
            comparison = operator.le
        else:
            comparison = operator.ge
            next_state_index = state_index + 1
            if next_state_index >= len(commodity_instance.commodity_states):
                threshold_value = commodity_instance.convergence_value
            else:
                threshold_value = commodity_instance.commodity_states[next_state_index].value
        threshold = sims4.math.Threshold(threshold_value, comparison)
        return self._get_absolute_timeout_time(commodity_instance, threshold)
