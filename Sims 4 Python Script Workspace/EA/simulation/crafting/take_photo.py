from _math import Vector3import itertoolsfrom protocolbuffers import DistributorOps_pb2, ResourceKey_pb2from crafting.photography import Photographyfrom crafting.photography_enums import CameraMode, PhotoSize, ZoomCapability, CameraQuality, PhotoOrientationfrom crafting.photography_loots import DefaultTakePhotoLoot, RotateTargetPhotoLootfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.success_chance import SuccessChancefrom interactions.utils.tunable_icon import TunableIconAllPacksfrom objects.components.stored_actor_location_component import add_stored_sim_locationfrom sims.sim_info_types import SpeciesExtendedfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.resources import get_protobuff_for_keyfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, Tunable, OptionalTunable, TunableMapping, TunableVariant, TunableList, TunableSet, TunableReference, TunableTuple, TunableFactoryimport servicesimport sims4logger = sims4.log.Logger('Photography', default_owner='rrodgers')
class _BasePhotoMode(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'zoom_capability': TunableEnumEntry(description='\n            The zoom capability of the camera.\n            ', tunable_type=ZoomCapability, default=ZoomCapability.NO_ZOOM), 'camera_quality': TunableEnumEntry(description='\n            The quality of the camera.\n            ', tunable_type=CameraQuality, default=CameraQuality.CHEAP), 'hide_photographer': Tunable(description='\n            Whether or not to hide the photographer during the photo session.\n            ', tunable_type=bool, default=False), 'success_chance': SuccessChance.TunableFactory(description='\n            Percent chance that a photo will be successful.\n            '), 'camera_position_bone_name': Tunable(description='\n            Which bone on the photographer to use for the camera position.\n            ', tunable_type=str, default='', allow_empty=True), 'camera_position_bone_object': TunableEnumEntry(description='\n            The object that has the bone from which the camera position is\n            obtained. This is usually the photographer sim.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'objects_to_hide_tags': OptionalTunable(description='\n            If enabled, objects that match any of these tags will be hidden in the photo\n            session.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TAG_SET), class_restrictions=('TunableTagSet',))), 'number_of_photos_override': OptionalTunable(description='\n            If tuned, the number of photos that the player can take in this photo session.\n            ', tunable=Tunable(tunable_type=int, default=5)), 'filters_disabled': Tunable(description='\n            Whether or not to disable photo filters.\n            ', tunable_type=bool, default=False), 'single_shot_mode': Tunable(description='\n            Whether or not to only allow the photographer to take one photo\n            per session.\n            ', tunable_type=bool, default=False), 'orientation': TunableEnumEntry(description='\n            The orientation of the camera.\n            ', tunable_type=PhotoOrientation, default=PhotoOrientation.LANDSCAPE), 'allow_change_orientation': Tunable(description='\n            Whether to allow players to toggle between landscape and portrait mode freely.\n            ', tunable_type=bool, default=True), 'allow_change_size': Tunable(description='\n            Whether to allow players to change the photo size between small/medium/large or not.\n            ', tunable_type=bool, default=True), 'photo_pose': TunableReference(description='\n            The pose the sims in the photo will use.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ANIMATION), class_restrictions=('ObjectPose',)), 'photographer_sim': TunableEnumEntry(description='\n            The participant Sim that is the photographer.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'order_photo_target_sims': Tunable(description='\n            If checked, the targets of this TakePhoto will be assigned actors in\n            the asm based on tags on the interactions they are running. If\n            unchecked, they will be assigned in an arbitrary manner (which may\n            not be random).\n            ', tunable_type=bool, default=True), 'photo_target_sims_participants': TunableList(description='\n            The participants whose Sims are the target of the photograph.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.TargetSim)), 'photo_target_sims_from_situation': OptionalTunable(description='\n            Tuning to add a group of situation sims as targets of this photo\n            session.\n            ', tunable=TunableTuple(situation=TunableReference(description='\n                    The situation in which to look for sims.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), photographer_job=OptionalTunable(description='\n                    If enabled, the job the photographer sim must have in the tuned\n                    situation in order for that situation to be used. Use this\n                    tuning to ensure we are using the correct situation instance.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), target_jobs=TunableSet(description='\n                    The chosen sims must have one of the following jobs.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)))))}

    def create_take_photo_op(self, sims, interaction):
        take_photo_proto = DistributorOps_pb2.TakePhoto()
        self._populate_take_photo_op(sims, interaction, take_photo_proto)
        take_photo_op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.TAKE_PHOTO, take_photo_proto)
        return take_photo_op

    def _populate_take_photo_op(self, sims, interaction, take_photo_proto):
        take_photo_proto.camera_mode = self._get_camera_mode()
        take_photo_proto.zoom_capability = self.zoom_capability
        take_photo_proto.camera_quality = self.camera_quality
        take_photo_proto.orientation = self.orientation
        take_photo_proto.allow_change_orientation = self.allow_change_orientation
        if hasattr(take_photo_proto, 'allow_change_size'):
            take_photo_proto.allow_change_size = self.allow_change_size
        take_photo_proto.hide_photographer = self.hide_photographer
        take_photo_proto.success_chance = self.success_chance.get_chance(interaction.get_resolver())
        take_photo_proto.camera_position_bone_name = self.camera_position_bone_name
        offset = self._get_offset(interaction)
        take_photo_proto.camera_position_offset.x = offset.x
        take_photo_proto.camera_position_offset.y = offset.y
        take_photo_proto.camera_position_offset.z = offset.z
        take_photo_proto.rotate_target = self.enable_rotate_target(interaction)
        take_photo_proto.filters_disabled = self.filters_disabled
        take_photo_proto.single_shot_mode = self.single_shot_mode
        take_photo_proto.painting_size = self._get_photo_size()
        take_photo_proto.num_photos_per_session = self.number_of_photos_override if self.number_of_photos_override is not None else Photography.NUM_PHOTOS_PER_SESSION
        take_photo_proto.sim_mood_asm_param_name = sims[0].get_mood_animation_param_name()
        if self.objects_to_hide_tags is not None:
            objects_to_hide = list(obj.id for obj in services.object_manager().get_objects_with_tags_gen(*self.objects_to_hide_tags.tags))
            take_photo_proto.objects_to_hide.extend(objects_to_hide)
        bone_object = interaction.get_participant(self.camera_position_bone_object)
        if bone_object is not None:
            take_photo_proto.camera_position_bone_object = bone_object.id
        for (index, sim) in enumerate(sims):
            with ProtocolBufferRollback(take_photo_proto.sim_photo_infos) as entry:
                entry.participant_sim_id = sim.sim_id
                entry.participant_sim_position.x = sim.position.x
                entry.participant_sim_position.y = sim.position.y
                entry.participant_sim_position.z = sim.position.z
                if self.photo_pose.asm is not None:
                    entry.animation_pose.asm = get_protobuff_for_key(self.photo_pose.asm)
                    entry.animation_pose.state_name = self.photo_pose.state_name
                    actor_name = self._get_actor_name(index)
                    if actor_name is not None:
                        entry.animation_pose.actor_name = actor_name

    def _get_camera_mode(self):
        raise NotImplementedError('Attempting to call _get_camera_mode() on the base class, use sub-classes instead.')

    def _get_actor_name(self, index):
        return 'x'

    def _get_photo_size(self):
        return PhotoSize.LARGE

    def _get_offset(self, interaction):
        return Vector3.ZERO()

    def enable_rotate_target(self, interaction):
        return True

    def get_callbacks(self):
        pass

class _FreeFormPhotoMode(_BasePhotoMode):
    FACTORY_TUNABLES = {'locked_args': {'photo_target_sims_participants': None, 'photo_pose': None}}

    def _get_camera_mode(self):
        return CameraMode.FREE_FORM_PHOTO

class _SimPhotoMode(_BasePhotoMode):

    class _MoodCategory(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'icon_tuning': TunableTuple(description="\n                A set of icons to associate with this mood category. Different\n                icons are for different states of the mood category's button in\n                the UI.\n                ", up_icon=TunableIconAllPacks(), down_icon=TunableIconAllPacks(), over_icon=TunableIconAllPacks()), 'tooltip': TunableLocalizedStringFactory(description='\n                The tooltip for this category in the photography UI.\n                '), 'mood_param_values': TunableList(description='\n                A list of mood param values (strings). One of these will be\n                selected at random if a player selects this category in the UI.\n                ', tunable=Tunable(tunable_type=str, default=None), minlength=1), 'target_tests_pass_one': TunableTestSet(description='\n                A set of tests which will be run on every photo target. The\n                target will be the Target Participant and the photographer will\n                be the Actor participant. These tests must pass for at least\n                one target for this mood category to be included. These will\n                only run for multi-Sim photos.\n                '), 'target_tests_pass_all': TunableTestSet(description='\n                A set of tests which will be run on every photo target. The\n                target will be the Target Participant and the photographer will\n                be the Actor participant. These tests must pass for all targets\n                for this mood category to be included. These will only run for \n                multi-Sim photos.\n                '), 'test_for_incest': Tunable(description='\n                If checked, this mood category will be disabled if any pair of\n                targets fails the incest test.\n                ', tunable_type=bool, default=False), 'actor_tests_pass_all': TunableTestSet(description='\n                A set of tests which will be run on the actor when there are no \n                target Sims (such as 1 Sim selfies). \n                ')}

        def run_tests(self, photographer, targets):
            if not targets:
                resolver = SingleSimResolver(photographer)
                return self.actor_tests_pass_all.run_tests(resolver)
            if self.test_for_incest:
                target_combinations = itertools.combinations(targets, 2)
                for (sim_a, sim_b) in target_combinations:
                    if not sim_a.sim_info.incest_prevention_test(sim_b.sim_info):
                        return False
            passed_one = False
            for target in targets:
                resolver = DoubleSimResolver(photographer, target)
                if self.target_tests_pass_one.run_tests(resolver):
                    passed_one = True
                if not self.target_tests_pass_all.run_tests(resolver):
                    return False
            if not (len(targets) > 1 and passed_one):
                return False
            return True

    DEFAULT_MOOD_CATEGORIES = TunableList(description='\n        These mood categories will always be available for photography modes that support\n        mood categories. Additional mood categories can be specified in the \n        Take Photo tuning.\n        ', tunable=_MoodCategory.TunableFactory())
    FACTORY_TUNABLES = {'additional_mood_categories': TunableList(description='\n            Additional mood categories that should be added to the default mood\n            categories for this photography session. Mood categories are \n            selectable in the photography UI and will cause the sim to re-pose\n            as if they were in different moods.\n            ', tunable=_MoodCategory.TunableFactory()), 'randomize_actors_on_repose': Tunable(description='\n            If checked, the targets of this photo will be assigned to random\n            actors whenever we re-pose them.\n            ', tunable_type=bool, default=False), 'use_default_mood_categories': Tunable(description='\n            If enabled, mood categories will be shown in the photogrpahy UI. If\n            disabled, mood categories will not be shown although the re-pose\n            button should still be present.\n            ', tunable_type=bool, default=True)}

    def _populate_take_photo_op(self, sims, interaction, take_photo_proto):
        super()._populate_take_photo_op(sims, interaction, take_photo_proto)
        mood_target_sim = sims[1] if len(sims) > 1 else None
        if mood_target_sim is not None:
            take_photo_proto.sim_mood_asm_param_name = mood_target_sim.get_mood_animation_param_name()
        take_photo_proto.randomize_target_sim_order = self.randomize_actors_on_repose
        mood_categories = itertools.chain(self.DEFAULT_MOOD_CATEGORIES, self.additional_mood_categories) if self.use_default_mood_categories else self.additional_mood_categories
        for mood_category in mood_categories:
            if mood_category.run_tests(sims[0], sims[1:]):
                with ProtocolBufferRollback(take_photo_proto.mood_categories) as entry:
                    entry.mood_category_up_icon = create_icon_info_msg(IconInfoData(mood_category.icon_tuning.up_icon), tooltip=mood_category.tooltip())
                    entry.mood_category_down_icon = create_icon_info_msg(IconInfoData(mood_category.icon_tuning.down_icon))
                    entry.mood_category_over_icon = create_icon_info_msg(IconInfoData(mood_category.icon_tuning.over_icon))
                    entry.mood_param_values.extend(mood_category.mood_param_values)

    def _get_camera_mode(self):
        return CameraMode.SIM_PHOTO

class _PhotoStudioPhotoMode(_SimPhotoMode):

    def _get_camera_mode(self):
        return CameraMode.PHOTO_STUDIO_PHOTO

    def _get_actor_name(self, index):
        if index == 0:
            return
        if index == 1:
            return 'x'
        elif index == 2:
            return 'y'

class _TripodPhotoMode(_SimPhotoMode):
    CLIP_INDEX_VALUES = TunableList(description="\n        When we pose sims during tripod photography sessions, we don't want two\n        sims to choose the same pose clip. To avoid this, client assigns a\n        unique value to each actor's ClipIndex parameter. This is a list of all\n        valid ClipIndex values from which a unique element will be assigned to\n        each actor being posed.\n        \n        Note: Gameplay needs to make sure this list is kept in-sync with the\n        ClipIndex animation parameter.\n        ", tunable=Tunable(tunable_type=str, default=None))
    FACTORY_TUNABLES = {'canvas_size': TunableEnumEntry(description='\n            The size of the canvas.\n            ', tunable_type=PhotoSize, default=PhotoSize.LARGE)}

    def _populate_take_photo_op(self, sims, interaction, take_photo_proto):
        super()._populate_take_photo_op(sims, interaction, take_photo_proto)
        take_photo_proto.clip_index_values.extend(self.CLIP_INDEX_VALUES)

    def _get_camera_mode(self):
        return CameraMode.TRIPOD

    def _get_actor_name(self, index):
        if index == 0:
            return
        if index == 1:
            return 'x'
        if index == 2:
            return 'y'
        elif index == 3:
            return 'z'

class _SelfiePhotoMode(_SimPhotoMode):
    CLIP_INDEX_VALUES = TunableList(description="\n        When we pose Sims during selfie photography sessions, we don't want the\n        Sim to choose the same pose clip in a row. To avoid this, client assigns a\n        unique value to each actor's ClipIndex parameter. This is a list of all\n        valid ClipIndex values from which a unique element will be assigned to\n        the actor being posed.\n\n        Note: Gameplay needs to make sure this list is kept in-sync with the\n        ClipIndex animation parameter.\n        ", tunable=Tunable(tunable_type=str, default=None))

    @TunableFactory.factory_option
    def locked_args_option(*args):
        return {'locked_args': {'photo_target_sims_participants': None}}

    def _populate_take_photo_op(self, sims, interaction, take_photo_proto):
        super()._populate_take_photo_op(sims, interaction, take_photo_proto)
        take_photo_proto.clip_index_values.extend(self.CLIP_INDEX_VALUES)

    def _get_camera_mode(self):
        return CameraMode.SELFIE_PHOTO

class _TwoSimSelfiePhotoMode(_SelfiePhotoMode):
    CLIP_INDEX_VALUES = TunableList(description="\n        When we pose Sims during selfie photography sessions, we don't want the\n        Sim to choose the same pose clip in a row. To avoid this, client assigns a\n        unique value to each actor's ClipIndex parameter. This is a list of all\n        valid ClipIndex values from which a unique element will be assigned to\n        the actor being posed.\n\n        Note: Gameplay needs to make sure this list is kept in-sync with the\n        ClipIndex animation parameter.\n        ", tunable=Tunable(tunable_type=str, default=None))

    @TunableFactory.factory_option
    def locked_args_option(*args):
        return {}

    def _get_camera_mode(self):
        return CameraMode.TWO_SIM_SELFIE_PHOTO

    def _get_actor_name(self, index):
        if index == 0:
            return 'x'
        elif index == 1:
            return 'y'

class _PaintByReferenceMode(_BasePhotoMode):
    FACTORY_TUNABLES = {'canvas_size': TunableEnumEntry(description='\n            The size of the canvas.\n            ', tunable_type=PhotoSize, default=PhotoSize.LARGE), 'locked_args': {'photo_target_sims_participants': None, 'photo_pose': None}}

    def _populate_take_photo_op(self, sims, interaction, take_photo_proto):
        super()._populate_take_photo_op(sims, interaction, take_photo_proto)
        painting = interaction.get_participant(ParticipantType.CreatedObject)
        if painting is not None:
            take_photo_proto.target_object = painting.id

    def _get_camera_mode(self):
        return CameraMode.PAINT_BY_REFERENCE

    def _get_photo_size(self):
        return self.canvas_size

class _CrossStitchByReferenceMode(_PaintByReferenceMode):

    def _get_camera_mode(self):
        return CameraMode.CROSSSTITCH_BY_REFERENCE

class _RotateTargetSelfieMode(_BasePhotoMode):
    FACTORY_TUNABLES = {'rotate_target_sim': TunableEnumEntry(description='\n            The participant used as the rotate selfie subject.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.TargetSim), 'forward_distance_multiplier_map': TunableMapping(description='\n            Mapping between species and forward distance the camera will be\n            set from the rotate selfie subject. \n            ', key_type=TunableEnumEntry(description='\n                Species these values are intended for.\n                ', tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,)), value_type=Tunable(description='\n                The the forward distance from the rotation target that the\n                camera will be placed. \n                ', tunable_type=float, default=1.2)), 'locked_args': {'photo_target_sims_participants': None, 'photo_pose': None}}

    def _get_camera_mode(self):
        return CameraMode.SELFIE_PHOTO

    def _get_offset(self, interaction):
        rotate_target = interaction.get_participant(self.rotate_target_sim)
        multiplier = self.forward_distance_multiplier_map.get(rotate_target.extended_species)
        offset = rotate_target.forward*multiplier
        return offset

    def enable_rotate_target(self, interaction):
        rotate_target = interaction.get_participant(self.rotate_target_sim)
        if rotate_target is None:
            logger.error('Got a None Sim {} trying to run interaction {}.', self.rotate_target_sim, interaction, owner='shipark')
            return True
        return False

class _DecoratorPhotoMode(_BasePhotoMode):
    FACTORY_TUNABLES = {'stored_location': Tunable(description='\n            If True, store the location of the photographer on\n            the photo object. The photo object will provide\n            an interaction to return to the location.\n            ', tunable_type=bool, default=True), 'gig_career': TunableReference(description='\n            The career expected on the active sim. This will be used to get\n            the active gig and before and after photos will be stored on the gig \n            history.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'before_or_after_photo': Tunable(description='\n            If True, store the photo as a before photo on the Gig History. If False,\n            store the photo as an after photo on the Gig History.\n            ', tunable_type=bool, default=True), 'states_to_set_on_photo': TunableSet(description='\n            A set of states to set on the created photo object.\n            ', tunable=TunableReference(description='\n                An object state to set on the photo object.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))), 'locked_args': {'filters_disabled': False, 'order_photo_target_sims': False, 'photo_target_sims_from_situation': None, 'photo_target_sims_participants': None, 'photo_pose': None}}

    def _get_camera_mode(self):
        return CameraMode.DECORATOR_MODE

    def add_photo_to_gig_history(self, photo_object, sim=None, photo_resource_key=None, second_photo_resource_key=None):
        sim_info = sim.sim_info
        career_tracker = sim_info.career_tracker
        gig_career = career_tracker.get_career_by_uid(self.gig_career.guid64)
        if gig_career is None:
            logger.error('Attempting to add gig-photo but the active sim {} does not have career {}', sim_info, self.gig_career)
            return
        current_gig = gig_career.get_current_gig()
        if current_gig is None:
            logger.error('Attempting to add gig-photo but, but the active sim {} has no active gig for career {}', sim_info, self.gig_career)
            return
        self.set_photo_description(current_gig, photo_object)
        gig_history_key = current_gig.get_gig_history_key()
        has_gig_history = career_tracker.has_gig_history_with_key(gig_history_key)
        if not has_gig_history:
            career_tracker.add_gig_history(current_gig)
        key = ResourceKey_pb2.ResourceKey()
        if type(second_photo_resource_key) is sims4.resources.Key:
            key.type = second_photo_resource_key.type
            key.group = second_photo_resource_key.group
            key.instance = second_photo_resource_key.instance
        key_low_res = ResourceKey_pb2.ResourceKey()
        if type(photo_resource_key) is sims4.resources.Key:
            key_low_res.type = photo_resource_key.type
            key_low_res.group = photo_resource_key.group
            key_low_res.instance = photo_resource_key.instance
        result = career_tracker.set_before_after_photo(gig_history_key, key, key_low_res, before=self.before_or_after_photo)
        if not result:
            logger.warn('Failed to add photo to the gig history of sim: {}', sim_info)

    def set_photo_description(self, current_gig, photo_object):
        zone = services.get_zone(current_gig.get_customer_lot_id())
        if zone is None:
            return
        lot_name = zone.lot.get_lot_name()
        if lot_name is None:
            return
        photo_object.name_component.set_custom_description(lot_name, force_set=True, update_tooltip=False)

    def _add_states_to_photo(self, photo_object, **kwargs):
        for state_value in self.states_to_set_on_photo:
            photo_object.set_state(state_value.state, state_value)

    def _add_stored_location_callback(self, callbacks):
        if self.stored_location:
            callbacks.register(add_stored_sim_location)
        return callbacks

    def get_callbacks(self):
        callbacks = super().get_callbacks()
        callbacks = CallableList() if callbacks is None else callbacks
        callbacks = self._add_stored_location_callback(callbacks)
        if self.states_to_set_on_photo:
            callbacks.register(self._add_states_to_photo)
        callbacks.register(self.add_photo_to_gig_history)
        return callbacks

class _PuzzleByReferenceMode(_PaintByReferenceMode):
    FACTORY_TUNABLES = {'locked_args': {'filters_disabled': False, 'order_photo_target_sims': False, 'photo_target_sims_from_situation': None, 'photo_target_sims_participants': None, 'photo_pose': None}}

    def _get_camera_mode(self):
        return CameraMode.PUZZLE_BY_REFERENCE

class TakePhoto(XevtTriggeredElement):
    FACTORY_TUNABLES = {'photo_mode': TunableVariant(description='\n            The photo mode to use for this photo session.\n            ', free_form_photo=_FreeFormPhotoMode.TunableFactory(), sim_photo=_SimPhotoMode.TunableFactory(), selfie_photo=_SelfiePhotoMode.TunableFactory(), two_sim_selfie_photo=_TwoSimSelfiePhotoMode.TunableFactory(), photo_studio_photo=_PhotoStudioPhotoMode.TunableFactory(), paint_by_reference=_PaintByReferenceMode.TunableFactory(), rotate_target_selfie=_RotateTargetSelfieMode.TunableFactory(), tripod=_TripodPhotoMode.TunableFactory(), decorator_mode=_DecoratorPhotoMode.TunableFactory(), cross_stitch_by_reference=_CrossStitchByReferenceMode.TunableFactory(), puzzle_by_reference=_PuzzleByReferenceMode.TunableFactory(), default='free_form_photo'), 'loot_to_apply': TunableList(description='\n            Loot defined here will be applied to the participants of the photography\n            interaction after the systems photography call is finished.\n            ', tunable=TunableVariant(description='\n            Select Default Take Photo Loot for most Camera Modes.\n            Select Rotate Target Photo Loot for Rotate Target Selfie Mode.\n            ', photoLoot=DefaultTakePhotoLoot.TunableFactory(), targetPhotoLoot=RotateTargetPhotoLoot.TunableFactory(), default='photoLoot'), set_default_as_first_entry=True)}

    def _find_sim_with_interaction_tag(self, photo_target_sims, interaction_tag):
        for sim in photo_target_sims:
            if sim.get_running_and_queued_interactions_by_tag({interaction_tag}):
                return sim

    def _order_group_photo_sims(self, photo_target_sims):
        ordered_sims = []
        tags = (Photography.GROUP_PHOTO_X_ACTOR_TAG, Photography.GROUP_PHOTO_Y_ACTOR_TAG, Photography.GROUP_PHOTO_Z_ACTOR_TAG)
        used_tags = tags[:len(photo_target_sims)]
        for tag in used_tags:
            sim = self._find_sim_with_interaction_tag(photo_target_sims, tag)
            if sim is None:
                logger.error("Couldn't find sim with tag: {}", tag)
                return
            ordered_sims.append(sim)
        return ordered_sims

    def _do_behavior(self):
        photographer_sim = self.interaction.get_participant(self.photo_mode.photographer_sim)
        if photographer_sim is None:
            logger.error('take_photo basic extra could not find a photographer {}')
            return False
        sims = []
        sims.append(photographer_sim)
        photo_target_sims = []
        if self.photo_mode.photo_target_sims_participants:
            for participant_type in self.photo_mode.photo_target_sims_participants:
                participant_sims = self.interaction.get_participants(participant_type)
                if participant_sims is not None:
                    photo_target_sims.extend(participant_sims)
        situation_target_tuning = self.photo_mode.photo_target_sims_from_situation
        if situation_target_tuning:
            photo_situations = services.get_zone_situation_manager().get_situations_by_type(situation_target_tuning.situation)
            for photo_situation in photo_situations:
                if not situation_target_tuning.photographer_job is None:
                    if photo_situation.get_current_job_for_sim(photographer_sim) is situation_target_tuning.photographer_job:
                        for job in situation_target_tuning.target_jobs:
                            sims_in_job = photo_situation.all_sims_in_job_gen(job)
                            photo_target_sims.extend(sims_in_job)
                        break
                for job in situation_target_tuning.target_jobs:
                    sims_in_job = photo_situation.all_sims_in_job_gen(job)
                    photo_target_sims.extend(sims_in_job)
                break
        if self.photo_mode.order_photo_target_sims:
            num_target_sims = len(photo_target_sims)
            if num_target_sims > 1:
                photo_target_sims = self._order_group_photo_sims(photo_target_sims)
                if photo_target_sims is None:
                    return False
        sims.extend(photo_target_sims)
        is_rotate_selfie_mode = self.photo_mode.enable_rotate_target(self.interaction)
        if not is_rotate_selfie_mode:
            sims = self.interaction.get_participants(self.photo_mode.rotate_target_sim)
        photography_service = services.get_photography_service()
        for photoloot in self.loot_to_apply:
            loot = photoloot(self.interaction.sim, self.interaction)
            photography_service.add_loot_for_next_photo_taken(loot)
        callbacks = self.photo_mode.get_callbacks()
        if callbacks is not None:
            photography_service.add_callbacks(callbacks)
        op = self.photo_mode.create_take_photo_op(sims, self.interaction)
        Distributor.instance().add_op(photographer_sim, op)
        return True
