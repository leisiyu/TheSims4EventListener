import collectionsimport randomimport weakreffrom animation.procedural_animation_helpers import control_rotation_lookat, ProceduralAnimationRotationMixinfrom distributor.ops import SwitchActiveHouseholdControlfrom distributor.system import Distributorfrom element_utils import CleanupType, build_element, build_critical_section, build_critical_section_with_finally, build_delayed_elementfrom interactions import ParticipantType, ParticipantTypeSingleSim, ParticipantTypeSingle, ParticipantTypeSavedActorfrom interactions.utils.common import InteractionUtilsfrom interactions.utils.destruction_liability import DeleteObjectLiability, DELETE_OBJECT_LIABILITYfrom interactions.utils.success_chance import SuccessChancefrom objects import VisibilityStatefrom objects.client_object_mixin import ClientObjectMixinfrom sims.household_enums import HouseholdChangeOriginfrom sims.sim_dialogs import SimPersonalityAssignmentDialogfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.tuning.tunable import HasTunableFactory, TunableVariant, TunableTuple, TunableEnumEntry, Tunable, TunableReference, TunableRealSecond, OptionalTunable, TunableRange, TunableSimMinute, AutoFactoryInit, TunableSetfrom tag import Tagfrom ui.ui_dialog import PhoneRingTypefrom ui.ui_dialog_generic import TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAMEfrom ui.ui_dialog_rename import RenameDialogElementimport build_buyimport clockimport elementsimport objectsimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Interaction_Elements')
class XevtTriggeredElement(elements.ParentElement, HasTunableFactory, AutoFactoryInit):
    AT_BEGINNING = 'at_beginning'
    AT_END = 'at_end'
    ON_XEVT = 'on_xevt'
    TIMING_DESCRIPTION = '\n        Determines the exact timing of the behavior, either at the beginning\n        of an interaction, the end, or when an xevt occurs in an animation\n        played as part of the interaction.\n        '
    FakeTiming = collections.namedtuple('FakeTiming', ('timing', 'offset_time', 'criticality', 'xevt_id', 'supports_failsafe'))
    LOCKED_AT_BEGINNING = FakeTiming(AT_BEGINNING, None, None, None, None)
    LOCKED_AT_END = FakeTiming(AT_END, None, None, None, None)
    LOCKED_ON_XEVT = FakeTiming(ON_XEVT, None, None, None, None)
    FACTORY_TUNABLES = {'timing': TunableVariant(description=TIMING_DESCRIPTION, default=AT_END, at_beginning=TunableTuple(description="\n                The behavior should occur at the very beginning of the\n                interaction.  It will not be tightly synchronized visually with\n                animation.  This isn't a very common use case and would most\n                likely be used in an immediate interaction or to change hidden\n                state that is used for bookkeeping rather than visual\n                appearance.\n                ", offset_time=OptionalTunable(description='\n                    If enabled, the interaction will wait this amount of time\n                    after the beginning before running the element.\n                    \n                    Only use this if absolutely necessary. Better alternatives\n                    include using xevts, time based conditional action with\n                    loot ops, and using outcomes.\n                    ', tunable=TunableSimMinute(description='The interaction will wait this amount of time after the beginning before running the element', default=2), deprecated=True), locked_args={'timing': AT_BEGINNING, 'criticality': CleanupType.NotCritical, 'xevt_id': None, 'supports_failsafe': None}), at_end=TunableTuple(description='\n                The behavior should occur at the end of the interaction.  It\n                will not be tightly synchronized visually with animation.  An\n                example might be an object that gets dirty every time a Sim uses\n                it (so using a commodity change is overkill) but no precise\n                synchronization with animation is desired, as might be the case\n                with vomiting in the toilet.\n                ', locked_args={'timing': AT_END, 'xevt_id': None, 'offset_time': None, 'supports_failsafe': None}, criticality=TunableEnumEntry(CleanupType, CleanupType.OnCancel)), on_xevt=TunableTuple(description="\n                The behavior should occur synchronized visually with an xevt in\n                an animation played as part of the interaction.  If for some\n                reason such an event doesn't occur, the behavior will occur at\n                the end of the interaction unless supports failsafe is False. \n                \n                This is by far the most common use case, as when a Sim flushes \n                a toilet and the water level should change when the actual \n                flush animation and effects fire.\n                ", locked_args={'timing': ON_XEVT, 'offset_time': None}, criticality=TunableEnumEntry(CleanupType, CleanupType.OnCancel), xevt_id=Tunable(int, 100), supports_failsafe=Tunable(description='\n                    If checked and the x-event does not fire,\n                    the basic extra will still run at the end of\n                    the interaction as a fail-safe.\n                    ', tunable_type=bool, default=True))), 'success_chance': SuccessChance.TunableFactory(description='\n            The percentage chance that this action will be applied.\n            ')}

    def __init__(self, interaction, *, timing, sequence=(), **kwargs):
        super().__init__(timing=None, **kwargs)
        self.interaction = interaction
        self.sequence = sequence
        self.timing = timing.timing
        self.criticality = timing.criticality
        self.xevt_id = timing.xevt_id
        self.supports_failsafe = timing.supports_failsafe
        self.result = None
        self.triggered = False
        self.offset_time = timing.offset_time
        self._XevtTriggeredElement__event_handler_handle = None
        success_chance = self.success_chance.get_chance(interaction.get_resolver())
        self._should_do_behavior = random.random() <= success_chance

    def _register_event_handler(self, element):
        self._XevtTriggeredElement__event_handler_handle = self.interaction.animation_context.register_event_handler(self._behavior_event_handler, handler_id=self.xevt_id)

    def _release_event_handler(self, element):
        self._XevtTriggeredElement__event_handler_handle.release()
        self._XevtTriggeredElement__event_handler_handle = None

    def _behavior_element(self, timeline):
        if not self.triggered:
            self.triggered = True
            if self._should_do_behavior:
                self.result = self._do_behavior()
            else:
                self.result = None
        return self.result

    def _behavior_event_handler(self, *_, **__):
        if not self.triggered:
            self.triggered = True
            if self._should_do_behavior:
                self.result = self._do_behavior()
            else:
                self.result = None

    def _run(self, timeline):
        if not self._should_do_behavior:
            return timeline.run_child(build_element(self.sequence))
        if self.timing == self.AT_BEGINNING:
            if self.offset_time is None:
                sequence = [self._behavior_element, self.sequence]
            else:
                sequence = build_delayed_element(self.sequence, clock.interval_in_sim_minutes(self.offset_time), self._behavior_element, soft_sleep=True)
            child_element = build_element(sequence, critical=self.criticality)
        elif self.timing == self.AT_END:
            sequence = [self.sequence, self._behavior_element]
            child_element = build_element(sequence, critical=self.criticality)
        elif self.timing == self.ON_XEVT:
            child_element = build_critical_section([self._register_event_handler, self.sequence, self._release_event_handler])
            if self.supports_failsafe:
                child_element = build_element([child_element, self._behavior_element], critical=self.criticality)
        child_element = self._build_outer_elements(child_element)
        return timeline.run_child(child_element)

    def _build_outer_elements(self, sequence):
        return sequence

    def _do_behavior(self):
        raise NotImplementedError

    @classmethod
    def validate_tuning_interaction(cls, interaction, basic_extra):
        if basic_extra._tuned_values.timing.timing != XevtTriggeredElement.ON_XEVT:
            return
        if interaction.one_shot and interaction.basic_content.animation_ref is None:
            logger.error('The interaction ({}) has a tuned basic extra ({}) that occurs on an xevt but has no animation content.', interaction, basic_extra.factory, owner='shipark')
        elif interaction.staging:
            staging_content = interaction.basic_content.content.content_set._tuned_values
            if staging_content.affordance_links is None and staging_content.phase_tuning is None and interaction.basic_content.animation_ref is None:
                if interaction.provided_posture_type is None:
                    logger.error('The interaction ({}) has a tuned basic extra ({}) that occurs on an xevt tuned on a staging interaction without any staging content.', interaction, basic_extra.factory, owner='shipark')
                elif interaction.provided_posture_type._animation_data is None:
                    logger.error('The posture-providing interaction ({}) has a tuned basic extra ({}) that occurs on an xevt but has no animation content in the posture.', interaction, basic_extra.factory, owner='shipark')
        elif interaction.looping and interaction.basic_content.animation_ref is None:
            logger.error('The interaction ({}) has a tuned basic extra ({}) that occurs on an xevt but has no animation content.', interaction, basic_extra.factory, owner='shipark')

    @classmethod
    def validate_tuning_outcome(cls, outcome, basic_extra, interaction_name):
        if outcome.animation_ref is None and outcome.response is None and outcome.social_animation is None:
            logger.error('The interaction ({}) has an outcome with a tuned basic extra ({}) that occurs on an xevt, but has no animation content.', interaction_name, basic_extra, owner='shipark')

class FadeChildrenElement(elements.ParentElement, HasTunableFactory):
    FACTORY_TUNABLES = {'opacity': TunableRange(description='\n            The target opacity for the children.\n            ', tunable_type=float, default=0, minimum=0, maximum=1), '_parent_object': TunableEnumEntry(description='\n            The participant of an interaction whose children should be hidden.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'fade_duration': OptionalTunable(TunableRealSecond(description='\n                The number of seconds it should take for objects to fade out and\n                in.\n                ', default=0.25), disabled_name='use_default_fade_duration', enabled_name='use_custom_fade_duration'), 'fade_objects_on_ground': Tunable(description='\n            If checked, objects at height zero will fade. By default, objects \n            at ground level (like stools slotted into counters) will not fade.\n            ', tunable_type=bool, default=False)}

    def __init__(self, interaction, *, opacity, _parent_object, fade_duration, fade_objects_on_ground, sequence=()):
        super().__init__()
        self.interaction = interaction
        self.opacity = opacity
        self.parent_object = interaction.get_participant(_parent_object)
        if fade_duration is None:
            self.fade_duration = ClientObjectMixin.FADE_DURATION
        else:
            self.fade_duration = fade_duration
        self.fade_objects_on_ground = fade_objects_on_ground
        self.sequence = sequence
        self.hidden_objects = weakref.WeakKeyDictionary()

    def _run(self, timeline):

        def begin(_):
            for obj in self.parent_object.children_recursive_gen():
                if self.fade_objects_on_ground or obj.position.y == self.parent_object.position.y:
                    pass
                else:
                    opacity = obj.opacity
                    self.hidden_objects[obj] = opacity
                    obj.fade_opacity(self.opacity, self.fade_duration)

        def end(_):
            for (obj, opacity) in self.hidden_objects.items():
                obj.fade_opacity(opacity, self.fade_duration)

        return timeline.run_child(build_critical_section_with_finally(begin, self.sequence, end))

class SetVisibilityStateElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant of this interaction that will change the visibility.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'visibility': Tunable(description='\n            If checked, the subject will become visible. If unchecked, the\n            subject will become invisible.\n            ', tunable_type=bool, default=True), 'fade': Tunable(description='\n            If checked, the subject will fade in or fade out to match the\n            desired visibility.\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        if subject is not None:
            if self.fade:
                if self.visibility:
                    subject.fade_in()
                else:
                    subject.fade_out()
            else:
                subject.visibility = VisibilityState(self.visibility)

class SetRoutingInfoAndState(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant of this interaction whose routing behavior we want to change.\n            ', tunable_type=ParticipantType, default=ParticipantType.RoutingSlaves), 'routing_target': OptionalTunable(description='\n            The routing target we want to set for the subject, we expect this subject to route\n            to this target.\n            If disabled, we are not setting routing target for the subject.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantType.Object), enabled_by_default=True), 'routing_owner': OptionalTunable(description='\n            The routing owner we want to set for the subject, so the subject can have ability\n            to route back to the owner.\n            If disabled, we are not setting routing owner for the subject.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), enabled_by_default=True), 'routing_state_to_change': OptionalTunable(description='\n            The routing state we are setting on the subject. So its routing component will use\n            state-behavior map to change routing behavior.\n            If disabled, we are not setting routing state on the subject.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), enabled_by_default=True)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        target = self.interaction.get_participant(self.routing_target)
        owner = self.interaction.get_participant(self.routing_owner)
        if subject is not None:
            routing_component = subject.routing_component
            if routing_component is not None:
                if target:
                    routing_component.set_routing_target(target)
                if owner:
                    routing_component.set_routing_owner(owner)
                if self.routing_state_to_change:
                    subject.set_state(self.routing_state_to_change.state, self.routing_state_to_change)
                    logger.error("Trying to run a SetRoutingBehavior basic extra with a subject that doesn't have routing component.\nInteraction: {}\nSubject: {}", self.interaction, self.subject, owner='yozhang')
            else:
                logger.error("Trying to run a SetRoutingBehavior basic extra with a subject that doesn't have routing component.\nInteraction: {}\nSubject: {}", self.interaction, self.subject, owner='yozhang')
        else:
            logger.error('Trying to run a SetRoutingBehavior basic extra with a None subject.\nInteraction: {}', self.interaction, owner='yozhang')

class ProceduralAnimationRotationElement(XevtTriggeredElement, ProceduralAnimationRotationMixin):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The participant of this interaction whose procedural animation we're gonna control.\n            ", tunable_type=ParticipantTypeSingle, default=ParticipantType.Object), 'target': TunableEnumEntry(description='\n            The target we want the procedural animation to face to.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        target = self.interaction.get_participant(self.target)
        control_rotation_lookat(subject, self.procedural_animation_control_name, target, self.target_joint, self.duration, self.rotation_around_facing)

class UpdatePhysique(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': "\n            Basic extra to trigger a visual update of the specified Sims'\n            physiques.\n            ", 'targets': TunableEnumEntry(description='\n            The targets of this physique update.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def _do_behavior(self):
        targets = self.interaction.get_participants(self.targets)
        for target in targets:
            target.sim_info.update_fitness_state()

class UpdateDisplayNumber(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            The targets of this game score update\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def _do_behavior(self):
        targets = self.interaction.get_participants(self.targets)
        for target in targets:
            target.update_display_number()

class ReplaceObject(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that is the object that is to be replaced\n            Note: Please do not try to use this on Sims.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Object), 'tags': TunableSet(description='\n            A set of tags that an object must have in order to be considered a\n            valid replacement.\n            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID)), 'exclude_tags': TunableSet(description='\n            A set of tags that an object must NOT have in order to be\n            considered a valid replacement.\n            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID)), 'margin_of_error': Tunable(description='\n            The margin of error in bounding box size when considering a\n            replacement object. The larger the value, the more variety you will\n            see in potential replacement objects, both in larger and smaller\n            objects compared to the original.\n            ', tunable_type=int, default=50), 'number_replacement_attempts': Tunable(description='\n            This is the number of tries to find a replacement object that will\n            be attempted before giving up. The server team recommends this be set\n            to 0, to signify finding all available objects to pick from randomly.\n            However, in the interest of safety, I am making this tunable so that\n            we can easily change this for certain object types where this may \n            cause an issue. Please talk to a GPE if you think you need to change this.\n            ', tunable_type=int, default=0)}

    def _replace_object(self, resolver):
        original_obj = resolver.get_participant(self.participant)
        if original_obj is None or original_obj.is_sim:
            return
        new_obj_def = build_buy.get_replacement_object(services.current_zone_id(), original_obj.id, self.number_replacement_attempts, self.margin_of_error, tags=self.tags, exclude_tags=self.exclude_tags)
        if new_obj_def is not None:
            new_obj = objects.system.create_object(new_obj_def)
            if new_obj is not None:
                household_owner_id = original_obj.household_owner_id
                parent_slot = original_obj.parent_slot
                new_obj.move_to(routing_surface=original_obj.routing_surface, translation=original_obj.position, orientation=original_obj.orientation)
                new_obj.set_household_owner_id(household_owner_id)
                if parent_slot is not None:
                    original_obj.set_parent(None)
                    parent_slot.add_child(new_obj)
                delete_liability = DeleteObjectLiability([original_obj])
                self.interaction.add_liability(DELETE_OBJECT_LIABILITY, delete_liability)
            else:
                logger.warn('Sim Ray could not create an object from the returned definition: {}.', new_obj_def, owner='jwilkinson')
        else:
            logger.warn('Sim Ray server call did not return a replacement object definition. Try adjusting the tuning to use a larger margin of error.', owner='jwilkinson')

    def _do_behavior(self):
        self._replace_object(self.interaction.get_resolver())

class PutNearElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will get moved.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The participant that the subject will get moved near.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'fallback_to_spawn_point': Tunable(description='\n            If enabled, a spawn point will be used as a fallback if FGL fails. \n            If disabled, the Subject will stay wherever they are.\n            ', tunable_type=bool, default=True), 'use_fgl': Tunable(description="\n            If enabled, use fgl to place the subject near the target. Otherwise,\n            try to place the object directly at the target's location. \n            ", tunable_type=bool, default=True), 'use_world_routing': Tunable(description="\n            If enabled, use the target's parent object to place the subject on the world routing surface.\n            Useful if the target may be slotted on another object.\n            ", tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs) -> None:
        subject = self.interaction.get_participant(self.subject)
        target = self.interaction.get_participant(self.target)
        if target is not None:
            while target.parent is not None and target.parent is not target:
                target = target.parent
        InteractionUtils.do_put_near(subject, target, self.fallback_to_spawn_point, self.use_fgl)

class AddToHouseholdElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who to add to the active household.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim), 'rename_dialog': OptionalTunable(description='\n            If enabled, the dialog that is displayed (and asks for the player \n            to enter a first name and last name) before assigning the Sim to \n            their household.\n            ', tunable=SimPersonalityAssignmentDialog.TunableFactory(text_inputs=(TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAME), locked_args={'phone_ring_type': PhoneRingType.NO_RING}))}

    @staticmethod
    def run_behavior(sim_info):
        household_manager = services.household_manager()
        return household_manager.switch_sim_household(sim_info, reason=HouseholdChangeOrigin.ADD_BASIC_EXTRA)

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.target)
        if target is None:
            logger.error('Trying to run AddToHousehold basic extra with a None target.')
            return False
        return self.run_behavior(target.sim_info)

    def _build_outer_elements(self, sequence):
        if self.rename_dialog is None:
            return sequence
        target = self.interaction.get_participant(self.target)
        if target is None:
            return sequence
        rename_dialog = self.rename_dialog(target, resolver=self.interaction.get_resolver())
        rename_element = RenameDialogElement(rename_dialog, target.sim_info)
        return build_element((rename_element, sequence))

class RemoveDependentFromHouseholdElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who to remove from the active household and into a dependent \n            household.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim)}

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.target)
        if target is None:
            logger.error('Trying to run RemoveDependentFromHousehold basic extra with a None target.')
            return False
        household_manager = services.household_manager()
        household = target.household
        sim_info = target.sim_info
        dependent_household = household_manager.create_household(sim_info.account)
        dependent_household.set_to_dependent()
        household_manager.switch_sim_from_household_to_target_household(sim_info, household, dependent_household, reason=HouseholdChangeOrigin.DEPENDENT)
        sim_info.request_lod(SimInfoLODLevel.BACKGROUND)
        services.hidden_sim_service().hide_sim(sim_info.id)
        client = sim_info.client
        if client is not None:
            client.set_next_sim_or_none(only_if_this_active_sim_info=sim_info)

class SwitcActivehHouseholdElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Sim whose household should become the active household.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim)}

    def _do_behavior(self, *args, **kwargs) -> bool:
        target = self.interaction.get_participant(self.target)
        if target is None:
            logger.error('Trying to run SwitchActiveHousehold basic extra with a None target.')
            return False
        if target.household.home_zone_id == 0:
            logger.error('Trying to switch to {} household, but they are homeless.', target.household)
            return False
        persistence_service = services.get_persistence_service()
        if persistence_service.is_save_locked():
            logger.warn('Failed to run a SwitchActiveHousehold basic extra due to save lock.')
            return False
        household_name = persistence_service.get_sim_proto_buff(target.sim_id).household_name
        op = SwitchActiveHouseholdControl(sim_id=target.sim_id, zone_id=target.zone_id, household_id=target.household_id, household_name=household_name)
        Distributor.instance().add_op_with_no_owner(op)
        return True

class SaveParticipantElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that will be saved as the saved_participant specified.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'saved_participant': TunableEnumEntry(description='\n            The saved participant slot that participant will be saved as.\n            ', tunable_type=ParticipantTypeSavedActor, default=ParticipantTypeSavedActor.SavedActor1), 'use_sim_info': Tunable(description='\n            If the participant is a sim, and we do not need the object (just the data), we can enable this\n            Can be useful in cases where the sim object might not exist for the whole interaction, but we want\n            to run tests against their data\n            (such as death)\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs):
        participant = self.interaction.get_participant(self.participant)
        if participant is None:
            logger.error('Trying to save a participant in SaveParticipantElement that cannot be resolved by get_participant.\n  Interaction: {}\n  Participant:{}', self.interaction, self.participant)
        for (index, flag) in enumerate(list(ParticipantTypeSavedActor)):
            if self.saved_participant == flag:
                break
        if self.use_sim_info and participant is not None and participant.is_sim:
            self.interaction.set_saved_participant(index, participant.sim_info)
        else:
            self.interaction.set_saved_participant(index, participant)
