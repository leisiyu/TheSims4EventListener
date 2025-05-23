import collectionsimport weakreffrom alarms import add_alarmfrom native.animation import get_mirrored_joint_name_hashfrom native.animation.arb import ClipEventType, ArbEventDatafrom objects import VisibilityState, MaterialStatefrom objects.components.censor_grid_component import CensorStatefrom objects.system import create_prop, create_object, create_prop_with_footprintfrom sims4.repr_utils import standard_angle_reprfrom singletons import DEFAULTfrom uid import unique_id, UniqueIdGeneratorimport audioimport clockimport native.animation.arbimport servicesimport sims4.hash_utilimport sims4.logimport vfxlogger = sims4.log.Logger('Animation')ClipEventType = native.animation.arb.ClipEventTypewith sims4.reload.protected(globals()):
    GLOBAL_SINGLE_PART_CONDITION_CACHE = {}
    GLOBAL_MULTI_PART_CONDITION_CACHE = {}
def get_animation_object_by_id(obj_id, allow_obj=True, allow_prop=True):
    zone = services.current_zone()
    if allow_obj:
        obj = zone.find_object(obj_id)
        if obj is not None:
            return obj
    if allow_prop:
        obj = zone.prop_manager.get(obj_id)
        if obj is not None:
            return obj
    if allow_obj and allow_prop:
        logger.warn('Animation object not found in prop or object manager: 0x{:016x}', obj_id)

def get_event_handler_error_for_missing_object(name, object_id):
    if object_id:
        return '{} (id: 0x{:016x}) not found in object manager. It was probably deleted.'.format(name, object_id)
    else:
        return "Missing {0}. Either the {0}'s namespace wasn't set in Maya, wasn't found in the namespace map, or wasn't set as an actor on the ASM.".format(name, object_id)

def get_animation_object_for_event(event_data, attr_name, error_name, asms=None, **kwargs):
    obj_id = event_data.event_data[attr_name]
    if obj_id == 0:
        asm_names = ', '.join(set(asm.name for asm in asms))
        clip_name = event_data.event_data.get('clip_name', 'unknown clip')
        logger.warn('\n            ANIMATION: The game is unable to resolve the {} ({}) \n            variable of {} event {}. The specific clip is {}, \n            and is found in one of these ASMs:\n             {}\n             \n            Please check the clip event data in Sage first. If everything looks\n            correct, check it out in Maya before asking Tech Design whether or\n            not all the actors are properly set. That should be verifiable by\n            looking at the GSI animation archive.\n            ', attr_name, error_name, ClipEventType(event_data.event_type).name, event_data.event_id, clip_name, asm_names)
        error = get_event_handler_error_for_missing_object(error_name, obj_id)
        return (error, None)
    obj = get_animation_object_by_id(obj_id, **kwargs)
    if obj is None:
        error = get_event_handler_error_for_missing_object(error_name, obj_id)
        return (error, None)
    return (None, obj)

class EventHandle:

    def __init__(self, manager, tag=None):
        self._manager_ref = weakref.ref(manager)
        self._tag = tag

    @property
    def _manager(self):
        if self._manager_ref is not None:
            return self._manager_ref()

    @property
    def tag(self):
        return self._tag

    def release(self):
        if self._manager is not None:
            self._manager._release_handle(self)

    def __hash__(self):
        if self.tag is not None:
            return hash(self.tag)
        return super().__hash__()

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        if self.tag is not None and self.tag == other.tag:
            return True
        return self is other
UserDataKey = collections.namedtuple('UserDataKey', ['event_type', 'actor_id', 'id'])
@unique_id('_context_uid')
class AnimationContext:
    _get_next_asm_event_uid = UniqueIdGenerator()
    _CENSOR_MAPPING = {native.animation.arb.CENSOREVENT_STATE_FACE: CensorState.FACE, native.animation.arb.CENSOREVENT_STATE_LHAND: CensorState.LHAND, native.animation.arb.CENSOREVENT_STATE_RHAND: CensorState.RHAND, native.animation.arb.CENSOREVENT_STATE_FULLBODY: CensorState.FULLBODY, native.animation.arb.CENSOREVENT_STATE_TODDLERPELVIS: CensorState.TODDLER_PELVIS, native.animation.arb.CENSOREVENT_STATE_PELVIS: CensorState.PELVIS, native.animation.arb.CENSOREVENT_STATE_TORSOPELVIS: CensorState.TORSO_PELVIS, native.animation.arb.CENSOREVENT_STATE_TORSO: CensorState.TORSO, native.animation.arb.CENSOREVENT_STATE_OFF: CensorState.OFF}

    def __init__(self, *args, is_throwaway=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_data = {}
        self._props = {}
        self._placeholders = {}
        self._posture_owners = None if is_throwaway else set()
        self._vfx_overrides = None
        self._sound_overrides = None
        self._custom_event_handlers = {}
        self._event_handlers = {}
        self._asms = []
        self._alarm_handles = []
        self.include_object_children_in_fade = False
        if not is_throwaway:
            self.reset_for_new_interaction()
        self.apply_carry_interaction_mask = []
        self._ref_count = []

    def __repr__(self):
        kwargs = {}
        if self._props:
            kwargs['props'] = list(sorted(self._props))
        if self._placeholders:
            kwargs['placeholders'] = list(sorted(str(e) for e in self._placeholders.values()))
        if self._asms:
            kwargs['asms'] = list(sorted({e.name for e in self._asms}))
        if self._ref_count:
            kwargs['refs'] = self._ref_count
        return standard_angle_repr(self, request_id=self.request_id, **kwargs)

    def add_asm(self, asm):
        self._asms.append(asm)

    def get_asms_gen(self):
        return iter(self._asms)

    @property
    def user_data(self):
        return self._user_data

    def add_posture_owner(self, posture):
        if self._posture_owners is not None:
            self._posture_owners.add(posture)
            self.add_ref(posture)

    def remove_posture_owner(self, posture):
        if self._posture_owners is not None:
            self._posture_owners.discard(posture)
            self.release_ref(posture)
            if self._posture_owners or self._ref_count:
                logger.error('{} release all the postures but still have {} ref count. This is invalid.', self, self._ref_count)

    def reset_for_new_interaction(self):
        self._vfx_overrides = None
        self._sound_overrides = None
        self._alarm_handles = [alarm_handle for alarm_handle in self._alarm_handles if alarm_handle is not None]
        self._custom_event_handlers = {}
        self._event_handlers = {}
        self.register_event_handler(self._event_handler_effect_start, ClipEventType.Effect)
        self.register_event_handler(self._event_handler_effect_stop, ClipEventType.StopEffect)
        self.register_event_handler(self._event_handler_sound_start, ClipEventType.ServerSoundStart)
        self.register_event_handler(self._event_handler_sound_stop, ClipEventType.ServerSoundStop)
        self.register_event_handler(self._event_handler_censor_grid, ClipEventType.Censor)
        self.register_event_handler(self._event_handler_material_state, ClipEventType.MaterialState)
        self.register_event_handler(self._event_handler_geometry_state, ClipEventType.GeometryState)
        self.register_event_handler(self._event_handler_fade_object, ClipEventType.FadeObject)

    def get_placeholder_objects(self):
        return tuple(reservation_and_object[1] for reservation_and_object in self._placeholders.values())

    def _reset_throwaway_context(self):
        self._stop()
        self.reset_for_new_interaction()
        del self._asms[:]

    def add_ref(self, tag):
        self._ref_count.append(tag)

    def release_ref(self, tag):
        if tag in self._ref_count:
            self._ref_count.remove(tag)
        else:
            logger.error('Unexpected tag in release_ref: {} (remaining refs: {})', tag, self._ref_count)
        if not self._ref_count:
            self._stop()

    def release_alarms(self):
        for alarm_handle in self._alarm_handles:
            if alarm_handle is not None:
                alarm_handle.cancel()
        self._alarm_handles.clear()

    def _all_props_gen(self, held_only):
        for (name, prop) in self._props.items():
            if prop.id not in prop.manager:
                pass
            elif held_only:
                parent = prop.parent
                if not parent is None:
                    if not parent.is_sim:
                        pass
                    else:
                        yield name
            else:
                yield name

    def destroy_all_props(self, held_only=False):
        names = []
        for name in self._all_props_gen(held_only):
            names.append(name)
        for name in names:
            prop_manager = services.prop_manager()
            prop_manager.destroy_prop(self._props.pop(name), source=self, cause='Animation destroying all props.')

    def set_all_prop_visibility(self, visible, held_only=False):
        for name in self._all_props_gen(held_only):
            self._props[name].visibility = VisibilityState(visible)

    def _stop(self):
        for key in self._user_data:
            data = self._user_data[key]
            if hasattr(data, 'stop'):
                if key.event_type == ClipEventType.Effect:
                    data.stop(immediate=False)
                else:
                    data.stop()
            if key.event_type == ClipEventType.Censor:
                censor_object = get_animation_object_by_id(key.actor_id)
                if censor_object is not None:
                    censor_object.censorgrid_component.remove_censor(data)
        self._user_data.clear()
        self.destroy_all_props()
        self.clear_reserved_slots()
        self.release_alarms()
        self._event_handlers.clear()

    @property
    def request_id(self):
        return self._context_uid

    def _override_prop_states(self, actor, prop, states):
        if actor is None or actor.state_component is None:
            return
        if prop is None or prop.state_component is None:
            return
        for state in states:
            state_value = actor.get_state(state)
            if state_value is not None:
                prop.set_state(state, state_value)

    def _get_prop(self, asm, prop_name, definition_id, interaction=None):
        props = self._props
        prop = props.get(prop_name)
        (from_actor, states_to_override) = asm.get_prop_state_override(prop_name, interaction=interaction)
        if not definition_id:
            self._override_prop_states(from_actor, prop, states_to_override)
            return prop
        if prop.definition.id != definition_id:
            asm.set_actor(prop_name, None)
            prop.destroy(source=self, cause='Replacing prop.')
            del props[prop_name]
            prop = None
        if prop is not None and prop is None:
            share_key = asm.get_prop_share_key(prop_name)
            if share_key is None:
                prop = create_prop(definition_id)
            else:
                prop_manager = services.prop_manager()
                prop = prop_manager.create_shared_prop(share_key, definition_id)
            if prop is not None:
                props[prop_name] = prop
            else:
                logger.error("{}: Failed to create prop '{}' with definition id {:#x}", asm.name, prop_name, definition_id)
        if prop is not None:
            asm.set_prop_state_values(prop_name, prop)
            self._override_prop_states(from_actor, prop, states_to_override)
            asm.set_prop_as_asm_actor(prop_name, prop)
            asm.apply_special_case_overrides(prop_name, prop)
        return prop

    def clear_reserved_slots(self):
        for (slot_manifest_entry, placeholder_info) in list(self._placeholders.items()):
            (reservation_handler, placeholder_obj) = placeholder_info
            logger.debug('Slot Reservation: Release: {} for {}', placeholder_obj, slot_manifest_entry)
            reservation_handler.end_reservation()
            placeholder_obj.destroy(source=self, cause='Clearing reserved slots')
        self._placeholders.clear()

    @staticmethod
    def init_placeholder_obj(obj):
        obj.visibility = VisibilityState(False)

    def update_reserved_slots(self, slot_manifest_entry, reserve_sim, objects_to_ignore=DEFAULT):
        runtime_slot = slot_manifest_entry.runtime_slot
        if runtime_slot is None:
            raise RuntimeError('Attempt to reserve slots without a valid runtime slot: {}'.format(slot_manifest_entry))
        if slot_manifest_entry.actor in runtime_slot.children or slot_manifest_entry in self._placeholders:
            return sims4.utils.Result.TRUE
        definition = slot_manifest_entry.actor.definition
        result = sims4.utils.Result.TRUE

        def post_add(obj):
            nonlocal result
            try:
                result = runtime_slot.is_valid_for_placement(obj=obj, objects_to_ignore=objects_to_ignore)
                if result:
                    runtime_slot.add_child(obj)
                    reservation_handler = obj.get_reservation_handler(reserve_sim)
                    reservation_handler.begin_reservation()
                    self._placeholders[slot_manifest_entry] = (reservation_handler, obj)
                    logger.debug('Slot Reservation: Reserve: {} for {}', obj, slot_manifest_entry)
            except:
                logger.exception('Exception reserving slot: {} for {}', obj, slot_manifest_entry)
                result = sims4.utils.Result(False, 'Exception reserving slot.')
            finally:
                if not result:
                    logger.debug('Slot Reservation: Fail:    {} for {} - {}', obj, slot_manifest_entry, result)
                    obj.destroy(source=self, cause='updating reserved slots')

        create_prop_with_footprint(definition, init=self.init_placeholder_obj, post_add=post_add)
        return result

    def register_event_handler(self, callback, handler_type=ClipEventType.Script, handler_id=None, tag=None):
        handle = EventHandle(self, tag=tag)
        for existing_handle in list(self._event_handlers):
            if existing_handle == handle:
                existing_handle.release()
        uid = AnimationContext._get_next_asm_event_uid()
        self._event_handlers[handle] = (uid, callback, handler_type, handler_id)
        return handle

    def register_custom_event_handler(self, callback, actor, time, allow_stub_creation=False, optional=False):
        handler_id = services.current_zone().arb_accumulator_service.claim_xevt_id()
        handle = EventHandle(self)
        uid = AnimationContext._get_next_asm_event_uid()
        self._custom_event_handlers[handle] = (uid, callback, handler_id, actor.id if actor is not None else None, time, allow_stub_creation, optional)
        return handle

    def _release_handle(self, handle):
        if handle in self._event_handlers:
            del self._event_handlers[handle]
        if handle in self._custom_event_handlers:
            del self._custom_event_handlers[handle]

    def _pre_request(self, asm, arb, state, interaction=None):
        arb.add_request_info(self, asm, state)
        for (uid, callback, event_type, event_id) in self._event_handlers.values():
            if not hasattr(arb, '_context_uids'):
                arb._context_uids = set()
            if uid not in arb._context_uids:
                arb.register_event_handler(callback, event_type, event_id)
                arb._context_uids.add(uid)
        props = asm.get_props_in_traversal(asm.current_state, state)
        for (prop_name, definition_id) in props.items():
            prop = self._get_prop(asm, prop_name, definition_id, interaction)
            if prop is not None and not asm.set_actor(prop_name, prop):
                logger.warn('{}: Failed to set actor: {} to {}', asm, prop_name, prop)
        self._vfx_overrides = asm.vfx_overrides
        self._sound_overrides = asm.sound_overrides
        for actor_name in self.apply_carry_interaction_mask:
            asm._set_actor_trackmask_override(actor_name, 50000, 'Trackmask_CarryInteraction')

    def _post_request(self, asm, arb, state):
        asm_actors = None
        for (uid, callback, event_id, actor_id, time, allow_stub_creation, optional) in self._custom_event_handlers.values():
            if actor_id is not None:
                actors = arb._actors()
                if actors and actor_id not in actors:
                    if optional:
                        pass
                    else:
                        logger.error("Failed to schedule custom x-event {} from {} on {} which didn't have the requested actor: {}, callback: {}", event_id, asm, arb, actor_id, callback)
                        scheduled_event = False
                        if actor_id is None:
                            actors = arb._actors()
                            if actors:
                                for arb_actor_id in actors:
                                    if arb.add_custom_event(arb_actor_id, time, event_id):
                                        scheduled_event = True
                                        break
                        elif arb.add_custom_event(actor_id, time, event_id):
                            scheduled_event = True
                        if scheduled_event:
                            if not hasattr(arb, '_context_uids'):
                                arb._context_uids = set()
                            if uid not in arb._context_uids:
                                arb.register_event_handler(callback, ClipEventType.Script, event_id)
                                arb._context_uids.add(uid)
                        elif allow_stub_creation:
                            asm_actors = list(asm.actors_gen()) if asm_actors is None else asm_actors
                            for actor in asm_actors:
                                if actor.id == actor_id:
                                    actors = {actor_id}
                                    event_data = {}
                                    data = ArbEventData(ClipEventType.Script, event_id, event_data, actors)

                                    def custom_event_alarm_callback(timeline):
                                        callback(data)

                                    alarm_handle = add_alarm(self, clock.interval_in_sim_minutes(time), custom_event_alarm_callback)
                                    self._alarm_handles.append(alarm_handle)
                                    break
            scheduled_event = False
            if actor_id is None:
                actors = arb._actors()
                if actors:
                    for arb_actor_id in actors:
                        if arb.add_custom_event(arb_actor_id, time, event_id):
                            scheduled_event = True
                            break
            elif arb.add_custom_event(actor_id, time, event_id):
                scheduled_event = True
            if scheduled_event:
                if not hasattr(arb, '_context_uids'):
                    arb._context_uids = set()
                if uid not in arb._context_uids:
                    arb.register_event_handler(callback, ClipEventType.Script, event_id)
                    arb._context_uids.add(uid)
            elif allow_stub_creation:
                asm_actors = list(asm.actors_gen()) if asm_actors is None else asm_actors
                for actor in asm_actors:
                    if actor.id == actor_id:
                        actors = {actor_id}
                        event_data = {}
                        data = ArbEventData(ClipEventType.Script, event_id, event_data, actors)

                        def custom_event_alarm_callback(timeline):
                            callback(data)

                        alarm_handle = add_alarm(self, clock.interval_in_sim_minutes(time), custom_event_alarm_callback)
                        self._alarm_handles.append(alarm_handle)
                        break
        for actor_name in self.apply_carry_interaction_mask:
            asm._clear_actor_trackmask_override(actor_name)
        self._custom_event_handlers = {}

    def _event_handler_discard_prop(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        prop_id = event_data.event_data['prop_actor_id']
        self.destroy_prop_from_id(prop_id)

    def destroy_prop_from_actor_id(self, prop_id):
        props = self._props
        for (prop_name, prop) in props.items():
            if prop.id == prop_id:
                prop_manager = services.prop_manager()
                prop_manager.destroy_prop(prop, source=self, cause='Discarding props.')
                del props[prop_name]
                return

    def _event_handler_effect_start(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        (early_out, effect_parent_obj) = get_animation_object_for_event(event_data, 'effect_parent_id', 'parent', asms=self._asms)
        if early_out is not None:
            return
        target_parent_id = event_data.event_data['effect_target_parent_id']
        if target_parent_id == 0:
            target_parent_obj = None
        else:
            (early_out, target_parent_obj) = get_animation_object_for_event(event_data, 'effect_target_parent_id', 'parent', asms=self._asms)
            if early_out is not None:
                return
        event_actor_id = event_data.event_data['event_actor_id']
        effect_actor_id = event_data.event_data['effect_actor_id']
        effect_name = None
        target_joint_offset = None
        callback_event_id = None
        mirrored_effect_name = None
        effect_joint_name_hash = event_data.event_data['effect_joint_name_hash']
        target_joint_name_hash = event_data.event_data['effect_target_joint_name_hash']
        if self._vfx_overrides and effect_actor_id in self._vfx_overrides:
            effect_overrides = self._vfx_overrides[effect_actor_id]
            if effect_overrides.effect is not None:
                effect_name = effect_overrides.effect
            if effect_overrides.effect_joint is not None:
                effect_joint_name_hash = effect_overrides.effect_joint
            if effect_overrides.target_joint is not None:
                target_joint_name_hash = effect_overrides.target_joint
            if effect_overrides.target_joint_offset is not None:
                target_joint_offset = effect_overrides.target_joint_offset()
            if effect_overrides.callback_event_id is not None:
                callback_event_id = effect_overrides.callback_event_id
            if effect_overrides.mirrored_effect is not None:
                mirrored_effect_name = effect_overrides.mirrored_effect
        else:
            effect_name = event_data.event_data['effect_name']
        key = UserDataKey(ClipEventType.Effect, event_actor_id, effect_actor_id)
        if key in self._user_data:
            self._user_data[key].stop()
            del self._user_data[key]
        mirrored = event_data.event_data['clip_is_mirrored']
        if mirrored_effect_name is not None:
            effect_name = mirrored_effect_name
            mirrored = False
        if not (mirrored and effect_name):
            return
        if mirrored:
            try:
                if effect_parent_obj is not None:
                    effect_joint_name_hash = get_mirrored_joint_name_hash(effect_parent_obj.rig, effect_joint_name_hash)
                if target_parent_obj is not None:
                    target_joint_name_hash = get_mirrored_joint_name_hash(target_parent_obj.rig, target_joint_name_hash)
            except Exception as e:
                logger.error('Failed to look up mirrored joint name...\nException: {}\nEventData: {}', e, event_data.event_data)
        effect = vfx.PlayEffect(effect_parent_obj, effect_name, effect_joint_name_hash, target_parent_id, target_joint_name_hash, target_joint_offset=target_joint_offset, callback_event_id=callback_event_id, mirror_effect=mirrored)
        self._user_data[key] = effect
        effect.start()

    def _event_handler_effect_stop(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        event_actor_id = event_data.event_data['event_actor_id']
        effect_actor_id = event_data.event_data['effect_actor_id']
        key = UserDataKey(ClipEventType.Effect, event_actor_id, effect_actor_id)
        if key in self._user_data:
            self._user_data[key].stop(immediate=event_data.event_data['effect_hard_stop'])
            del self._user_data[key]

    def _event_handler_sound_start(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        (early_out, obj) = get_animation_object_for_event(event_data, 'target_actor_id', 'parent', asms=self._asms)
        if early_out is not None:
            return
        sound_name = event_data.event_data['sound_name']
        sound_id = sims4.hash_util.hash64(sound_name)
        sound_id_overridden = False
        if sound_id in self._sound_overrides:
            sound_id = self._sound_overrides[sound_id]
            sound_id_overridden = True
        key = UserDataKey(ClipEventType.ServerSoundStart, obj.id, sound_name)
        if self._sound_overrides and key in self._user_data:
            self._user_data[key].stop()
            del self._user_data[key]
        if sound_id is None:
            return
        is_vox = sound_name.startswith('vo')
        if is_vox and not sound_id_overridden:
            sound = audio.primitive.PlaySound(obj, sound_id, is_vox=is_vox)
        elif not sound_id_overridden:
            sound = audio.primitive.PlaySound(obj, sound_id, sound_name=sound_name)
        else:
            sound = audio.primitive.PlaySound(obj, sound_id)
        self._user_data[key] = sound
        sound.start()

    def _event_handler_sound_stop(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        sound_parent_id = event_data.event_data['target_actor_id']
        sound_name = event_data.event_data['sound_name']
        key = UserDataKey(ClipEventType.ServerSoundStart, sound_parent_id, sound_name)
        if key in self._user_data:
            self._user_data[key].stop()
            del self._user_data[key]

    def _event_handler_censor_grid(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        event_actor_id = event_data.event_data['event_actor_id']
        censor_state = event_data.event_data['censor_state']
        key = UserDataKey(ClipEventType.Censor, event_actor_id, None)
        censor_state = self._CENSOR_MAPPING[censor_state]
        actor = get_animation_object_by_id(event_actor_id)
        if key in self._user_data:
            actor.censorgrid_component.remove_censor(self._user_data[key])
            del self._user_data[key]
        if censor_state != CensorState.OFF:
            self._user_data[key] = actor.censorgrid_component.add_censor(censor_state)

    def _event_handler_material_state(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        target_actor_id = event_data.event_data['target_actor_id']
        material_state = event_data.event_data['material_state_name']
        target = get_animation_object_by_id(target_actor_id)
        if target is None:
            logger.error('Failed to handle material state clip event in ASMs: {}, Clip: {} because Target is None. Target ID: {}, Material State: {}', self._asms, event_data.event_data.get('clip_name', 'unknown clip'), target_actor_id, material_state, owner='shouse')
            return
        material_state = MaterialState(material_state)
        target.material_state = material_state

    def _event_handler_geometry_state(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        target_actor_id = event_data.event_data['target_actor_id']
        geometry_state = event_data.event_data['geometry_state_name']
        target = get_animation_object_by_id(target_actor_id)
        if target is None:
            logger.error('Failed to handle geometry state clip event in ASMs: {}, Clip: {} because Target is None. Target ID: {}, Geometry State: {}', self._asms, event_data.event_data.get('clip_name', 'unknown clip'), target_actor_id, geometry_state, owner='rmccord')
            return
        target.geometry_state = geometry_state

    def _event_handler_fade_object(self, event_data):
        request_id = event_data.event_data['request_id']
        if request_id != self.request_id:
            return
        target_actor_id = event_data.event_data['target_actor_id']
        opacity = event_data.event_data['target_opacity']
        duration = event_data.event_data['duration']
        target = get_animation_object_by_id(target_actor_id)
        if target is None:
            logger.error('Failed to handle fade clip event in ASMs: {}, Clip: {} because Target is None. Target ID: {}', self._asms, event_data.event_data.get('clip_name', 'unknown clip'), target_actor_id, owner='rmccord')
            return
        target.fade_opacity(opacity, duration)
        if self.include_object_children_in_fade:
            for obj in target.children_recursive_gen():
                obj.fade_opacity(opacity, duration)

    def add_user_data_from_anim_context(self, anim_context):
        self._user_data.update(anim_context.user_data)
_GLOBAL_ANIMATION_CONTEXT_SINGLETON = AnimationContext(is_throwaway=True)
def get_throwaway_animation_context():
    _GLOBAL_ANIMATION_CONTEXT_SINGLETON._reset_throwaway_context()
    return _GLOBAL_ANIMATION_CONTEXT_SINGLETON
