from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from DistributorOps_pb2 import Operation
    from sims.sim_info import SimInfo
    from horse_competitions.hc_service import HorseCompetition
    from matchmaking.matchmaking_profiles import MatchmakingProfileimport weakreffrom event_testing.resolver import DoubleSimResolverfrom protocolbuffers import Animation_pb2, DistributorOps_pb2, Routing_pb2, Sims_pb2, UI_pb2, Area_pb2, InteractionOps_pb2, Commodities_pb2, UI_pb2 as ui_ops, Clubs_pb2, Situations_pb2from protocolbuffers.Consts_pb2 import MGR_UNMANAGEDimport protocolbuffers.Audio_pb2import protocolbuffers.VFX_pb2from distributor.rollback import ProtocolBufferRollbackfrom sims4.collections import ListSetfrom sims4.repr_utils import standard_repr, standard_float_tuple_repr, standard_brief_id_repr, standard_angle_reprfrom sims4.resources import get_protobuff_for_keyfrom singletons import EMPTY_SETimport distributor.fieldsimport distributor.systemimport enumimport routingimport servicesimport sims4.colorimport sims4.hash_utilimport sims4.log__unittest__ = 'test.distributor.ops_test'protocol_constants = DistributorOps_pb2.Operation
def record(obj, op):
    if not obj.valid_for_distribution:
        return
    distributor_instance = distributor.system.Distributor.instance()
    distributor_instance.add_op(obj, op)

class DistributionSet(weakref.WeakSet):
    __slots__ = ('obj',)
    DEFAULT_SET = ListSet

    def __init__(self, obj):
        super().__init__()
        self.obj = obj

    def __repr__(self):
        return standard_repr(self, set(self))

    def add(self, item):
        super().add(item)
        obj = self.obj
        if getattr(obj, 'valid_for_distribution', True):
            master = item.master
            if master is None or master is obj:
                from distributor.system import Distributor
                distributor = Distributor.instance()
                distributor.add_op(obj, item)

class Op:

    def __init__(self, immediate=False, **kwargs):
        super().__init__(**kwargs)
        self._additional_channels = set()
        self._force_execution_on_tag = False
        if immediate:
            self._primary_channel_mask_override = 0
        else:
            self._primary_channel_mask_override = None

    def __repr__(self):
        return standard_repr(self)

    @property
    def is_create_op(self):
        return False

    def add_additional_channel(self, manager_id, object_id, mask=None):
        if mask is None:
            mask = 4294967295
        channel = (manager_id, object_id, 0 if self._force_execution_on_tag and manager_id != MGR_UNMANAGED else mask)
        self._additional_channels.add(channel)

    def block_tag(self, tag):
        self.add_additional_channel(MGR_UNMANAGED, tag)

    def block_on_tag(self, tag, force_execute_on_tag=True):
        _prev_tag_execution_state = self._force_execution_on_tag
        self._force_execution_on_tag = self._force_execution_on_tag or force_execute_on_tag
        self.add_additional_channel(MGR_UNMANAGED, tag)
        if self._force_execution_on_tag != _prev_tag_execution_state:
            old_channels = self._additional_channels
            self._additional_channels = set()
            for channel in old_channels:
                self._additional_channels.add((channel[0], channel[1], 0 if self._force_execution_on_tag and channel[0] != MGR_UNMANAGED else channel[2]))

    def serialize_op(self, msg, op, op_type):
        msg.type = op_type
        msg.data = op.SerializeToString()

    @property
    def payload_type(self):
        pass

    @property
    def block_on_task_owner(self):
        return True

    def write(self, msg):
        raise NotImplementedError

class ElementDistributionOpMixin(Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._master_ref = None
        self._attached = False

    @property
    def master(self):
        master = self._master_ref
        master = master() if master is not None else None
        return master

    @master.setter
    def master(self, value):
        self._master_ref = value.ref() if value is not None else None

    @property
    def is_attached(self):
        return self._attached

    def attach(self, *objects, master=None):
        self._attached = True
        if master:
            self.master = master
        elif self.master is None:
            self.master = objects[0]
        for obj in objects:
            if obj.primitives is not None:
                obj.primitives.add(self)

    def detach(self, *objects):
        master = self.master
        self._attached = False
        for obj in objects:
            if obj.primitives is not None:
                obj.primitives.discard(self)
            if obj is master:
                self.master = None

class GenericCreate(Op):

    @property
    def is_create_op(self):
        return True

    def __init__(self, obj, op, *args, additional_ops=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._fill_in_operation_list(obj, op)
        for additional_op in additional_ops:
            with ProtocolBufferRollback(op.operation_list.operations) as op_msg:
                additional_op.write(op_msg)
        self.data = op.SerializeToString()

    def _fill_in_operation_list(self, obj, create_op):
        operations = create_op.operation_list.operations
        distributor.fields.Field.fill_in_operation_list(obj, operations, for_create=True)
        for primitive in obj.primitives:
            if obj is primitive.master:
                with ProtocolBufferRollback(operations) as op_msg:
                    primitive.write(op_msg)

class SparseMessageOp(Op):
    TYPE = None

    def __init__(self, value, immediate=False):
        super().__init__(immediate=immediate)
        self.value = value

    def write(self, msg):
        self.serialize_op(msg, self.value, self.TYPE)

class GenericProtocolBufferOp(Op):

    def __init__(self, type_constant, protocol_buffer, block_on_task_owner=True):
        super().__init__()
        self.type_constant = type_constant
        self.protocol_buffer = protocol_buffer
        self._block_on_task_owner = block_on_task_owner

    def write(self, msg):
        self.serialize_op(msg, self.protocol_buffer, self.type_constant)

    @property
    def block_on_task_owner(self):
        return self._block_on_task_owner

class ObjectCreate(GenericCreate):

    def __init__(self, obj, *args, **kwargs):
        op = DistributorOps_pb2.ObjectCreate()
        op.def_id = obj.definition.id
        op.visible_to_automation = obj.VISIBLE_TO_AUTOMATION
        for component in obj.definition.components:
            op.components.append(component)
        super().__init__(obj, op, *args, **kwargs)
        self.data = op.SerializeToString()

    def write(self, msg):
        msg.type = protocol_constants.OBJECT_CREATE
        msg.data = self.data

class ObjectReplace(Op):

    def __init__(self, replacement_obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._replacement_obj = replacement_obj

    def write(self, msg):
        op = DistributorOps_pb2.ObjectReplace()
        op.replacement_id = self._replacement_obj.id
        self.serialize_op(msg, op, protocol_constants.OBJECT_REPLACE)

class ObjectDelete(Op):

    def __init__(self, *args, fade_duration=0, **kwargs):
        super().__init__(*args, **kwargs)
        self._fade_duration = fade_duration

    def write(self, msg):
        op = DistributorOps_pb2.ObjectDelete()
        op.fade_duration = self._fade_duration
        self.serialize_op(msg, op, protocol_constants.OBJECT_DELETE)

class SocialGroupCreate(GenericCreate):

    def __init__(self, obj, *args, **kwargs):
        op = DistributorOps_pb2.SocialGroupCreate()
        super().__init__(obj, op, *args, **kwargs)

    def write(self, msg):
        msg.type = protocol_constants.SOCIAL_GROUP_CREATE
        msg.data = self.data

class SocialGroupUpdate(Op):

    def __init__(self, social_group_members):
        super().__init__()
        self._social_group_members = social_group_members

    def write(self, msg):
        op = DistributorOps_pb2.SocialGroupUpdate()
        for social_group_member in self._social_group_members:
            social_group_member_msg = op.members.add()
            social_group_member_msg.sim_id = social_group_member.sim_id
            social_context_bit = social_group_member.social_context_bit
            if social_context_bit is not None:
                social_group_member_msg.social_context_bit_id = social_context_bit.guid64
        self.serialize_op(msg, op, protocol_constants.SOCIAL_GROUP_UPDATE)

class SocialGroupTargetUpdate(Op):

    def __init__(self, sim, target):
        super().__init__()
        self._sim_id = sim.sim_id
        self._target_id = target.sim_id

    def write(self, msg):
        op = DistributorOps_pb2.SocialGroupTargetUpdate()
        op.sim_id = self._sim_id
        op.target_id = self._target_id
        self.serialize_op(msg, op, protocol_constants.SOCIAL_GROUP_TARGET_UPDATE)

class SocialGroupDelete(Op):

    def write(self, msg):
        msg.type = protocol_constants.SOCIAL_GROUP_DELETE

class SimInfoCreate(GenericCreate):

    def __init__(self, obj, *args, **kwargs):
        op = DistributorOps_pb2.SimInfoCreate()
        super().__init__(obj, op, *args, **kwargs)

    def write(self, msg):
        msg.type = protocol_constants.SIM_INFO_CREATE
        msg.data = self.data

class SimInfoDelete(Op):

    def write(self, msg):
        msg.type = protocol_constants.SIM_INFO_DELETE

class ClientCreate(GenericCreate):

    def __init__(self, obj, *args, is_active=False, **kwargs):
        op = DistributorOps_pb2.ClientCreate()
        op.account_id = obj.account.id
        op.household_id = obj.household_id
        op.is_active = is_active
        super().__init__(obj, op, *args, **kwargs)

    def write(self, msg):
        msg.type = protocol_constants.CLIENT_CREATE
        msg.data = self.data

class ClientDelete(Op):

    def write(self, msg):
        msg.type = protocol_constants.CLIENT_DELETE

class SetAudioEffects(Op):

    def __init__(self, audio_effects):
        super().__init__()
        self.op = DistributorOps_pb2.SetAudioEffects()
        if audio_effects is not None:
            for (key, audio_effect_data) in audio_effects.items():
                audio_effect_msg = self.op.audio_effects.add()
                audio_effect_msg.key = key
                audio_effect_msg.effect_id = audio_effect_data.effect_id
                if audio_effect_data.track_flags is not None:
                    audio_effect_msg.track_flags = audio_effect_data.track_flags

    def __repr__(self):
        output = 'SetAudioEffects(Op):\n'
        for audio_effect_msg in self.op.audio_effects:
            output += '   Effect Key: {}, Effect Id: {}\n'.format(audio_effect_msg.key, audio_effect_msg.effect_id)
        return output

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_AUDIO_EFFECTS)

class SetOverrideDialogPitch(Op):

    def __init__(self, voice_pitch_override):
        super().__init__()
        self.op = DistributorOps_pb2.SetOverrideDialogPitch()
        if voice_pitch_override is not None:
            self.op.pitch = voice_pitch_override[0]
            try:
                self.op.override_fast_speed = voice_pitch_override[1]
            except:
                pass

    def __repr__(self):
        output = 'SetOverrideDialogPitch(Op): {}, override fast speed {}'.format(self.op.pitch, self.op.override_fast_speed)
        return output

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_OVERRIDE_DIALOG_PITCH)

class SetLocation(Op):

    def __init__(self, location_owner):
        super().__init__()
        self.op = DistributorOps_pb2.SetLocation()
        if isinstance(location_owner, sims4.math.Location):
            location = location_owner
            is_sim = False
        else:
            location = location_owner._location
            is_sim = location_owner.is_sim
        if location.transform is not None:
            self.op.transform.translation.x = location.transform.translation.x
            self.op.transform.translation.y = location.transform.translation.y
            self.op.transform.translation.z = location.transform.translation.z
            self.op.transform.orientation.x = location.transform.orientation.x
            self.op.transform.orientation.y = location.transform.orientation.y
            self.op.transform.orientation.z = location.transform.orientation.z
            self.op.transform.orientation.w = location.transform.orientation.w
        routing_surface = location.routing_surface
        if routing_surface is not None:
            self.op.surface_id.primary_id = location.routing_surface.primary_id
            self.op.surface_id.secondary_id = location.routing_surface.secondary_id
            self.op.surface_id.type = location.routing_surface.type
        if location.parent is not None:
            self.op.parent_id = location.parent.id
        self.op.slot_hash = location.slot_hash
        if location.joint_name_or_hash is not None:
            self.op.joint_name_hash = location.joint_name_hash
        surface_object_id = None
        if is_sim:
            posture = location_owner.posture
            if posture is not None:
                surface_object = posture.get_locomotion_surface()
                if surface_object is not None:
                    surface_object_id = surface_object.id
        if routing_surface.type == routing.SurfaceType.SURFACETYPE_OBJECT:
            result = services.terrain_service.terrain_object().get_routing_surface_height_and_surface_object_at(location.transform.translation.x, location.transform.translation.z, routing_surface)
            if result is not None:
                (_, surface_object_id) = result
        if surface_object_id is None and routing_surface is not None and surface_object_id is not None:
            self.op.surface_object_id = surface_object_id

    def __repr__(self):
        return standard_repr(self, parent=standard_brief_id_repr(self.op.parent_id), slot_hash=hex(self.op.slot_hash), surface_object_id=hex(self.op.surface_object_id), joint_name_hash=hex(self.op.joint_name_hash), translation=standard_float_tuple_repr(self.op.transform.translation.x, self.op.transform.translation.y, self.op.transform.translation.z), orientation=standard_float_tuple_repr(self.op.transform.orientation.x, self.op.transform.orientation.y, self.op.transform.orientation.z, self.op.transform.orientation.w), level=self.op.level)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_LOCATION)

def create_route_msg_src(route_id, actor, path, start_time, wait_time, track_override=None, mask_override=None):
    route_pb = Routing_pb2.Route(id=route_id)
    last_routing_surface_id = None
    for n in path.nodes:
        node_pb = route_pb.nodes.add()
        node_loc = node_pb.location
        (node_loc.translation.x, node_loc.translation.y, node_loc.translation.z) = n.position
        (node_loc.orientation.x, node_loc.orientation.y, node_loc.orientation.z, node_loc.orientation.w) = n.orientation
        node_pb.action = n.action
        node_pb.time = n.time
        node_pb.walkstyle = n.walkstyle
        node_pb.surface_object_id = n.surface_object_id
        node_pb.is_procedural = n.is_procedural
        if n.portal_object_id != 0:
            object_manager = services.object_manager(actor.zone_id)
            if object_manager is not None:
                portal_object = object_manager.get(n.portal_object_id)
                if portal_object is not None:
                    node_pb.portal_object_id = n.portal_object_id
                    portal_object.add_portal_events(n.portal_id, actor, n.time, route_pb)
                    node_data = portal_object.add_portal_data(n.portal_id, actor, n.walkstyle)
                    if node_data is not None:
                        node_pb.node_data.type = node_data.type
                        node_pb.node_data.data = node_data.data
                        node_pb.node_data.do_start_transition = node_data.do_start_transition
                        node_pb.node_data.do_stop_transition = node_data.do_stop_transition
        if not last_routing_surface_id is None:
            if last_routing_surface_id != n.routing_surface_id:
                node_pb.routing_surface_id.primary_id = n.routing_surface_id.primary_id
                node_pb.routing_surface_id.secondary_id = n.routing_surface_id.secondary_id
                node_pb.routing_surface_id.type = n.routing_surface_id.type
                last_routing_surface_id = n.routing_surface_id
        node_pb.routing_surface_id.primary_id = n.routing_surface_id.primary_id
        node_pb.routing_surface_id.secondary_id = n.routing_surface_id.secondary_id
        node_pb.routing_surface_id.type = n.routing_surface_id.type
        last_routing_surface_id = n.routing_surface_id
    for polys in path.nodes.obstacles():
        obstacle_polys_pb = route_pb.obstacle_polygons.add()
        for data in polys:
            poly_pb = obstacle_polys_pb.polygons.add()
            routing_surface_id = data[1]
            poly_pb.routing_surface_id.primary_id = routing_surface_id.primary_id
            poly_pb.routing_surface_id.secondary_id = routing_surface_id.secondary_id
            poly_pb.routing_surface_id.type = routing_surface_id.type
            for p in data[0]:
                point_pb = poly_pb.points.add()
                point_pb.pos.x = p.x
                point_pb.pos.y = p.y
    monotonic_time = services.game_clock_service().monotonic_time()
    route_time = monotonic_time - start_time
    route_pb.time = route_time.in_real_world_seconds()
    ROUTING_TIME_BUFFER_MS = 100
    route_pb.absolute_time_ms = int(monotonic_time.absolute_ticks() + ROUTING_TIME_BUFFER_MS + wait_time*1000.0)
    if track_override is not None:
        route_pb.track = track_override
    if mask_override is not None:
        route_pb.mask = mask_override
    actor.write_slave_data_msg(route_pb, path=path)
    return route_pb

class RouteUpdate(Op):
    __slots__ = ('id', 'actor', 'path', 'start_time', 'wait_time', 'track_override')

    def __init__(self, route_id, actor, path, start_time, wait_time, track_override=None):
        super().__init__()
        self.id = route_id
        self.actor = actor
        self.path = path
        self.start_time = start_time
        self.track_override = track_override
        self.wait_time = wait_time

    def __repr__(self):
        return standard_repr(self, self.id)

    def write(self, msg):
        op = create_route_msg_src(self.id, self.actor, self.path, self.start_time, self.wait_time, track_override=self.track_override)
        self.actor.routing_component.append_route_events_to_route_msg(op)
        self.serialize_op(msg, op, protocol_constants.ROUTE_UPDATE)

class FocusEventAdd(Op):

    def __init__(self, event_id, layer, score, source, target, bone, offset, blocking, distance_curve=None, facing_curve=None, flags=0):
        super().__init__()
        self.id = event_id
        self.source = source
        self.target = target
        self.bone = bone
        self.offset = offset
        self.layer = layer
        self.score = score
        self.blocking = blocking
        self.distance_curve = distance_curve
        self.facing_curve = facing_curve
        self.flags = flags

    def __repr__(self):
        return standard_repr(self, self.id)

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.id = self.id
        op.type = Animation_pb2.FocusEvent.FOCUS_ADD
        op.source_id = self.source
        op.target_id = self.target
        op.joint_name_hash = self.bone
        (op.offset.x, op.offset.y, op.offset.z) = self.offset
        op.layer = self.layer
        op.score = self.score
        if self.distance_curve is not None:
            for c in self.distance_curve:
                curve_data = op.distance_curve.add()
                curve_data.input_value = c[0]
                curve_data.output_value = c[1]
        if self.facing_curve is not None:
            for c in self.facing_curve:
                curve_data = op.facing_curve.add()
                curve_data.input_value = c[0]
                curve_data.output_value = c[1]
        if self.blocking:
            msg_type = protocol_constants.FOCUS
        else:
            msg_type = protocol_constants.FOCUS_NON_BLOCKING
        if self.flags != 0:
            op.flags = self.flags
        self.serialize_op(msg, op, msg_type)

class FocusEventDelete(Op):

    def __init__(self, source_id, event_id, blocking):
        super().__init__()
        self.source_id = source_id
        self.id = event_id
        self.blocking = blocking

    def __repr__(self):
        return standard_repr(self, self.id)

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.source_id = self.source_id
        op.id = self.id
        op.type = Animation_pb2.FocusEvent.FOCUS_DELETE
        if self.blocking:
            msg_type = protocol_constants.FOCUS
        else:
            msg_type = protocol_constants.FOCUS_NON_BLOCKING
        self.serialize_op(msg, op, msg_type)

class FocusEventClear(Op):

    def __init__(self, source_id, blocking):
        super().__init__()
        self.source_id = source_id
        self.blocking = blocking

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.source_id = self.source_id
        op.type = Animation_pb2.FocusEvent.FOCUS_CLEAR
        if self.blocking:
            msg_type = protocol_constants.FOCUS
        else:
            msg_type = protocol_constants.FOCUS_NON_BLOCKING
        self.serialize_op(msg, op, msg_type)

class FocusEventModifyScore(Op):

    def __init__(self, source_id, event_id, score, blocking):
        super().__init__()
        self.source_id = source_id
        self.id = event_id
        self.score = score
        self.blocking = blocking

    def __repr__(self):
        return standard_repr(self, self.id)

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.source_id = self.source_id
        op.id = self.id
        op.score = self.score
        op.type = Animation_pb2.FocusEvent.FOCUS_MODIFY_SCORE
        if self.blocking:
            msg_type = protocol_constants.FOCUS
        else:
            msg_type = protocol_constants.FOCUS_NON_BLOCKING
        self.serialize_op(msg, op, msg_type)

class FocusEventForceUpdate(Op):

    def __init__(self, source_id, blocking):
        super().__init__()
        self.source_id = source_id
        self.blocking = blocking

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.source_id = self.source_id
        op.type = Animation_pb2.FocusEvent.FOCUS_FORCE_UPDATE
        if self.blocking:
            msg_type = protocol_constants.FOCUS
        else:
            msg_type = protocol_constants.FOCUS_NON_BLOCKING
        self.serialize_op(msg, op, msg_type)

class FocusEventDisable(Op):

    def __init__(self, source_id, disable, blocking):
        super().__init__()
        self.source_id = source_id
        self.disable = disable
        self.blocking = blocking

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.source_id = self.source_id
        op.flags = self.disable
        op.type = Animation_pb2.FocusEvent.FOCUS_DISABLE
        if self.blocking:
            msg_type = protocol_constants.FOCUS
        else:
            msg_type = protocol_constants.FOCUS_NON_BLOCKING
        self.serialize_op(msg, op, msg_type)

class FocusEventPrint(Op):

    def __init__(self, source_id):
        super().__init__()
        self.source_id = source_id

    def write(self, msg):
        op = Animation_pb2.FocusEvent()
        op.source_id = self.source_id
        op.type = Animation_pb2.FocusEvent.FOCUS_PRINT
        self.serialize_op(msg, op, protocol_constants.FOCUS_NON_BLOCKING)

class RequestLiveEvents(Op):

    def write(self, msg):
        msg.type = protocol_constants.REQUEST_LIVE_EVENTS

class OpenTutorial(Op):

    def __init__(self, tutorial_id=None, source=None):
        super().__init__()
        self.op = DistributorOps_pb2.OpenTutorial()
        if tutorial_id is not None:
            self.op.tutorial_id = tutorial_id
        if source is not None:
            self.op.source = source

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.OPEN_TUTORIAL)

class RouteCancel(Op):

    def __init__(self, route_id, time, orientation):
        super().__init__()
        self.id = route_id
        self.time = time
        self.orientation = orientation

    def __repr__(self):
        return standard_repr(self, self.id)

    def write(self, msg):
        op = DistributorOps_pb2.RouteCancel()
        op.id = self.id
        op.time = self.time
        op.orientation.x = self.orientation.x
        op.orientation.y = self.orientation.y
        op.orientation.z = self.orientation.z
        op.orientation.w = self.orientation.w
        self.serialize_op(msg, op, protocol_constants.ROUTE_CANCEL)

class SetModel(Op):

    def __init__(self, model_with_material_variant):
        super().__init__()
        (self.key, self.variant_id) = model_with_material_variant

    def __repr__(self):
        return standard_repr(self, self.key, self.variant_id)

    def write(self, msg):
        op = DistributorOps_pb2.SetModel()
        op.key.type = self.key.type
        op.key.instance = self.key.instance
        op.key.group = self.key.group
        if self.variant_id is not None:
            op.variant_id = self.variant_id
        else:
            op.variant_id = 0
        self.serialize_op(msg, op, protocol_constants.SET_MODEL)

class SetRig(Op):

    def __init__(self, key):
        super().__init__()
        self.key = key

    def __repr__(self):
        return standard_repr(self, self.key)

    def write(self, msg):
        op = DistributorOps_pb2.SetRig()
        op.key.type = self.key.type
        op.key.instance = self.key.instance
        op.key.group = self.key.group
        self.serialize_op(msg, op, protocol_constants.SET_RIG)

class SetCanLiveDrag(Op):

    def __init__(self, can_live_drag):
        super().__init__()
        self.can_live_drag = can_live_drag

    def __repr__(self):
        return standard_repr(self, self.can_live_drag)

    def write(self, msg):
        op = DistributorOps_pb2.SetCanLiveDrag()
        op.can_live_drag = self.can_live_drag
        self.serialize_op(msg, op, protocol_constants.SET_CAN_LIVE_DRAG)

class LiveDragStart(Op):

    def __init__(self, live_drag_object_id, start_system, valid_drop_target_ids, valid_stack_id, sell_value, icon_info):
        super().__init__()
        self.live_drag_object_id = live_drag_object_id
        self.start_system = start_system
        self.valid_drop_target_ids = valid_drop_target_ids
        self.valid_stack_id = valid_stack_id
        self.sell_value = sell_value
        self.icon_info = icon_info

    def __repr__(self):
        return 'Live Drag Start: live_drag_object: {}, valid targets: {}'.format(self.live_drag_object_id, standard_repr(self.valid_drop_target_ids))

    def write(self, msg):
        op = DistributorOps_pb2.LiveDragStart()
        op.live_drag_object_id = self.live_drag_object_id
        op.drag_start_system = int(self.start_system)
        op.drop_object_ids.extend(self.valid_drop_target_ids)
        op.sell_value = self.sell_value
        if self.valid_stack_id is not None:
            op.stack_id = self.valid_stack_id
        if self.icon_info is not None:
            op.icon_info = self.icon_info
        self.serialize_op(msg, op, protocol_constants.LIVE_DRAG_START)

class LiveDragEnd(Op):

    def __init__(self, live_drag_object_id, start_system, end_system, next_stack_object_id):
        super().__init__()
        self.live_drag_object_id = live_drag_object_id
        self.start_system = start_system
        self.end_system = end_system
        self.next_stack_object_id = next_stack_object_id

    def __repr__(self):
        return 'Live Drag End: live_drag_object: {}'.format(self.live_drag_object_id)

    def write(self, msg):
        op = DistributorOps_pb2.LiveDragEnd()
        op.live_drag_object_id = self.live_drag_object_id
        op.drag_start_system = int(self.start_system)
        op.drag_end_system = int(self.end_system)
        if self.next_stack_object_id is not None:
            op.next_drag_object_id = self.next_stack_object_id
        self.serialize_op(msg, op, protocol_constants.LIVE_DRAG_END)

class LiveDragCancel(Op):

    def __init__(self, live_drag_object_id, start_system, end_system):
        super().__init__()
        self.live_drag_object_id = live_drag_object_id
        self.start_system = start_system
        self.end_system = end_system

    def __repr__(self):
        return 'Live Drag Cancel: live_drag_object: {}'.format(self.live_drag_object_id)

    def write(self, msg):
        op = DistributorOps_pb2.LiveDragCancel()
        op.live_drag_object_id = self.live_drag_object_id
        op.drag_start_system = int(self.start_system)
        op.drag_end_system = int(self.end_system)
        self.serialize_op(msg, op, protocol_constants.LIVE_DRAG_CANCEL)

class SetRelativeLotLocation(Op):

    def __init__(self, sim_id, on_active_lot, is_at_home, is_in_travel_group):
        super().__init__()
        self.sim_id = sim_id
        self.on_active_lot = on_active_lot
        self.is_at_home = is_at_home
        self.is_in_travel_group = is_in_travel_group

    def write(self, msg):
        op = ui_ops.SimRelativeLotLocation()
        op.sim_id = self.sim_id
        op.on_active_lot = self.on_active_lot
        op.home_zone_active = self.is_at_home
        op.is_on_vacation = self.is_in_travel_group
        self.serialize_op(msg, op, protocol_constants.SIM_RELATIVE_LOT_LOCATION)

class SetFootprint(Op):

    def __init__(self, key):
        super().__init__()
        self.key = key

    def __repr__(self):
        return standard_repr(self, self.key)

    def write(self, msg):
        op = DistributorOps_pb2.SetFootprint()
        op.key.type = self.key.type
        op.key.instance = self.key.instance
        op.key.group = self.key.group
        self.serialize_op(msg, op, protocol_constants.SET_FOOTPRINT)

class ResetObject(Op):

    def __init__(self, object_id):
        super().__init__()
        self._object_id = object_id

    def __repr__(self):
        return standard_repr(self, self._object_id)

    def write(self, msg):
        op = DistributorOps_pb2.ObjectReset()
        op.object_id = self._object_id
        self.serialize_op(msg, op, protocol_constants.OBJECT_RESET)

class SetRelatedObjects(Op):

    def __init__(self, related_object_ids=None, target_id=None):
        super().__init__()
        self._related_object_ids = related_object_ids
        self._target_id = target_id

    def __repr__(self):
        return standard_repr(self, self._related_object_ids)

    def write(self, msg):
        op = DistributorOps_pb2.SetRelatedObjects()
        for obj_id in self._related_object_ids:
            op.related_object_ids.append(obj_id)
        op.target_sim_id = self._target_id
        self.serialize_op(msg, op, protocol_constants.SET_RELATED_OBJECTS)

class UpdateFootprintStatus(Op):

    def __init__(self, value):
        super().__init__()
        self.key = value[0]
        self.enabled = value[1]

    def __repr__(self):
        return standard_repr(self, self.key)

    def write(self, msg):
        op = DistributorOps_pb2.UpdateFootprintStatus()
        op.key.type = self.key.type
        op.key.instance = self.key.instance
        op.key.group = self.key.group
        op.enabled = self.enabled
        self.serialize_op(msg, op, protocol_constants.UPDATE_FOOTPRINT_STATUS)

class SetSlot(Op):

    def __init__(self, key):
        super().__init__()
        self.key = key

    def __repr__(self):
        return standard_repr(self, self.key)

    def write(self, msg):
        op = DistributorOps_pb2.SetSlot()
        if self.key is not None:
            op.key.type = self.key.type
            op.key.instance = self.key.instance
            op.key.group = self.key.group
        else:
            op.key.type = 0
            op.key.instance = 0
            op.key.group = 0
        self.serialize_op(msg, op, protocol_constants.SET_SLOT)

class SetDisabledSlots(Op):

    def __init__(self, disabled_slots):
        super().__init__()
        self._disabled_slots = disabled_slots or set()

    def __repr__(self):
        return standard_repr(self, self._disabled_slots)

    def write(self, msg):
        op = DistributorOps_pb2.SetDisabledSlots()
        for slot_hash in self._disabled_slots:
            op.slots.append(slot_hash)
        self.serialize_op(msg, op, protocol_constants.SET_DISABLED_SLOTS)

class SetParentType(Op):

    def __init__(self, value):
        super().__init__()
        if value is not None:
            self.parent_type = value[0]
            self.parent_location = value[1]
        else:
            self.parent_type = 0
            self.parent_location = 0

    def __repr__(self):
        return standard_repr(self, self.parent_type, self.parent_location)

    def write(self, msg):
        op = DistributorOps_pb2.SetParentType()
        op.parent_type = self.parent_type
        op.parent_location = self.parent_location
        self.serialize_op(msg, op, protocol_constants.SET_PARENT_TYPE)

class SetScale(Op):

    def __init__(self, scale):
        super().__init__()
        self.scale = scale

    def __repr__(self):
        return standard_repr(self, self.scale)

    def write(self, msg):
        op = DistributorOps_pb2.SetScale()
        op.scale = self.scale
        self.serialize_op(msg, op, protocol_constants.SET_SCALE)

class SetTint(Op):

    def __init__(self, value):
        super().__init__()
        self.tint = value

    def __repr__(self):
        return standard_repr(self, self.tint)

    def write(self, msg):
        op = DistributorOps_pb2.SetTint()
        if self.tint is not None:
            (op.tint.x, op.tint.y, op.tint.z, _) = sims4.color.to_rgba(self.tint)
        else:
            op.tint.x = op.tint.y = op.tint.z = 1.0
        self.serialize_op(msg, op, protocol_constants.SET_TINT)

class SetMulticolor(Op):

    def __init__(self, color_list):
        super().__init__()
        self.color_list = color_list

    def __repr__(self):
        return standard_repr(self, self.color_list)

    def write(self, msg):
        op = DistributorOps_pb2.SetMulticolor()
        for color in self.color_list:
            color = getattr(color, 'value', color)
            (r, g, b, _) = sims4.color.to_rgba(color)
            color_message = op.color.add()
            color_message.x = r
            color_message.y = g
            color_message.z = b
        self.serialize_op(msg, op, protocol_constants.SET_MULTICOLOR)

class SetVFXMask(Op):

    def __init__(self, vfx_mask):
        super().__init__()
        self.vfx_mask = vfx_mask

    def __repr__(self):
        return standard_repr(self, self.vfx_mask)

    def write(self, msg):
        op = DistributorOps_pb2.SetVFXMask()
        op.vfx_mask = self.vfx_mask
        self.serialize_op(msg, op, protocol_constants.SET_VFX_MASK)

class SetExcludeVFXMask(Op):

    def __init__(self, exclude_vfx_mask):
        super().__init__()
        self.exclude_vfx_mask = exclude_vfx_mask

    def __repr__(self):
        return standard_repr(self, self.exclude_vfx_mask)

    def write(self, msg):
        op = DistributorOps_pb2.SetExcludeVFXMask()
        op.exclude_vfx_mask = self.exclude_vfx_mask
        self.serialize_op(msg, op, protocol_constants.SET_EXCLUDE_VFX_MASK)

class SetDisplayNumber(Op):

    def __init__(self, number_list):
        super().__init__()
        self.number_list = number_list

    def __repr__(self):
        return standard_repr(self, self.number_list)

    def write(self, msg):
        op = DistributorOps_pb2.SetDisplayNumber()
        if self.number_list is not None:
            op.number.extend(self.number_list)
        self.serialize_op(msg, op, protocol_constants.SET_DISPLAY_NUMBER)

class SetOpacity(Op):

    def __init__(self, opacity):
        super().__init__()
        self.opacity = opacity

    def __repr__(self):
        return standard_repr(self, self.opacity)

    def write(self, msg):
        op = DistributorOps_pb2.SetOpacity()
        if self.opacity is not None:
            op.opacity = self.opacity
        else:
            op.opacity = 1.0
        self.serialize_op(msg, op, protocol_constants.SET_OPACITY)

class SetPregnancyProgress(Op):

    def __init__(self, pregnancy_progress):
        super().__init__()
        self.pregnancy_progress = pregnancy_progress

    def __repr__(self):
        return standard_repr(self, self.pregnancy_progress)

    def write(self, msg):
        op = DistributorOps_pb2.SetPregnancyProgress()
        if self.pregnancy_progress is not None:
            op.pregnancy_progress = self.pregnancy_progress
        else:
            op.pregnancy_progress = 0.0
        self.serialize_op(msg, op, protocol_constants.SET_PREGNANCY_PROGRESS)

class SetSinged(Op):

    def __init__(self, is_singed):
        super().__init__()
        self.is_singed = is_singed

    def __repr__(self):
        return standard_repr(self, self.is_singed)

    def write(self, msg):
        op = DistributorOps_pb2.SetSinged()
        if self.is_singed is not None:
            op.is_singed = self.is_singed
        else:
            op.is_singed = False
        self.serialize_op(msg, op, protocol_constants.SET_SINGED)

class SetGrubby(Op):

    def __init__(self, is_grubby):
        super().__init__()
        self.is_grubby = is_grubby

    def __repr__(self):
        return standard_repr(self, self.is_grubby)

    def write(self, msg):
        op = DistributorOps_pb2.SetGrubby()
        if self.is_grubby is not None:
            op.is_grubby = self.is_grubby
        else:
            op.is_grubby = False
        self.serialize_op(msg, op, protocol_constants.SET_GRUBBY)

class SetDyed(Op):

    def __init__(self, is_dyed):
        super().__init__()
        self.is_dyed = is_dyed

    def __repr__(self):
        return standard_repr(self, self.is_dyed)

    def write(self, msg):
        op = DistributorOps_pb2.SetDyed()
        if self.is_dyed is not None:
            op.is_dyed = self.is_dyed
        else:
            op.is_dyed = False
        self.serialize_op(msg, op, protocol_constants.SET_DYED)

class SetMessy(Op):

    def __init__(self, is_messy):
        super().__init__()
        self.is_messy = is_messy

    def __repr__(self):
        return standard_repr(self, self.is_messy)

    def write(self, msg):
        op = DistributorOps_pb2.SetMessy()
        if self.is_messy is not None:
            op.is_messy = self.is_messy
        else:
            op.is_messy = False
        self.serialize_op(msg, op, protocol_constants.SET_MESSY)

class SetObjectDefStateIndex(Op):

    def __init__(self, obj_def_state_index):
        super().__init__()
        self.obj_def_state_index = obj_def_state_index

    def __repr__(self):
        return standard_repr(self, self.obj_def_state_index)

    def write(self, msg):
        op = DistributorOps_pb2.SetObjectDefStateIndex()
        op.object_def_state_index = self.obj_def_state_index
        self.serialize_op(msg, op, protocol_constants.SET_OBJECT_DEF_STATE_INDEX)

class FadeOpacity(Op):

    def __init__(self, opacity, duration, immediate=False):
        super().__init__(immediate=immediate)
        self.opacity = opacity
        self.duration = duration

    def __repr__(self):
        return '<FadeOpacity {0}, {1}>'.format(self.opacity, self.duration)

    def write(self, msg):
        op = DistributorOps_pb2.FadeOpacity()
        if self.opacity is None:
            op.target_value = 1
        else:
            op.target_value = self.opacity
        op.duration = self.duration
        self.serialize_op(msg, op, protocol_constants.FADE_OPACITY)

class SetPaintingState(Op):

    def __init__(self, canvas_state):
        super().__init__()
        self.canvas_state = canvas_state
        self.is_painting = None

    def __repr__(self):
        return '<Set{0}State {1}>'.format('Painting' if self.is_painting else 'Puzzle', self.canvas_state)

    def write(self, msg):
        self.is_painting = not hasattr(self.canvas_state, 'reveal_texture_id_b')
        if self.is_painting:
            op = DistributorOps_pb2.SetPainting()
        else:
            op = DistributorOps_pb2.SetPuzzle()
        if self.canvas_state is None:
            if self.is_painting:
                op.painting = 0
            else:
                op.puzzle = 0
            op.reveal_level = 0
            op.use_overlay = False
        else:
            if self.canvas_state.texture_id is not None:
                if self.is_painting:
                    op.painting = self.canvas_state.texture_id
                else:
                    op.puzzle = self.canvas_state.texture_id
            if self.canvas_state.overlay_texture_id is not None:
                op.overlay_texture_id = self.canvas_state.overlay_texture_id
            op.reveal_level = self.canvas_state.reveal_level
            op.effect = self.canvas_state.effect
            if self.is_painting:
                op.use_overlay = self.canvas_state.use_overlay
                if self.canvas_state.stage_texture_id is not None:
                    op.stage_texture_id = self.canvas_state.stage_texture_id
                if self.canvas_state.reveal_texture_id is not None:
                    op.reveal_texture_id = self.canvas_state.reveal_texture_id
            else:
                if self.canvas_state.reveal_texture_id is not None:
                    op.reveal_texture_id_A = self.canvas_state.reveal_texture_id
                if self.canvas_state.reveal_texture_id_b is not None:
                    op.reveal_texture_id_B = self.canvas_state.reveal_texture_id_b
        self.serialize_op(msg, op, protocol_constants.SET_PAINTING if self.is_painting else protocol_constants.SET_PUZZLE)

class SetLightDimmer(Op):

    def __init__(self, dimmer):
        super().__init__()
        self.dimmer = dimmer

    def __repr__(self):
        return standard_repr(self, self.dimmer)

    def write(self, msg):
        op = DistributorOps_pb2.SetLightDimmer()
        if self.dimmer is not None:
            op.dimmer = self.dimmer
        else:
            op.dimmer = 1.0
        self.serialize_op(msg, op, protocol_constants.SET_LIGHT_DIMMER)

class SetWindSpeedEffect(Op):

    def __init__(self, value):
        super().__init__()
        self._wind_speed_effect = value

    def __repr__(self):
        return standard_repr(self, self._wind_speed_effect)

    def write(self, msg):
        op = DistributorOps_pb2.SetPinWheelSpinSpeed()
        if self._wind_speed_effect is not None:
            op.spin_speed = self._wind_speed_effect.spin_speed
            op.transition_speed = self._wind_speed_effect.transition_speed
            self.serialize_op(msg, op, protocol_constants.SET_PINWHEEL_SPIN_SPEED)

class SetLightMaterialStates(Op):

    def __init__(self, material_states):
        super().__init__()
        self._material_state_on = material_states[0]
        self._material_state_off = material_states[1]

    def write(self, msg):
        op = DistributorOps_pb2.SetLightMaterialStates()
        if self._material_state_on:
            op.material_state_on = sims4.hash_util.hash32(self._material_state_on)
        if self._material_state_off:
            op.material_state_off = sims4.hash_util.hash32(self._material_state_off)
        self.serialize_op(msg, op, protocol_constants.SET_LIGHT_MATERIAl_STATES)

class SetLightColor(Op):

    def __init__(self, color):
        super().__init__()
        self._color = color

    def __repr__(self):
        return standard_repr(self, self._color)

    def write(self, msg):
        op = DistributorOps_pb2.SetLightColor()
        if self._color is not None:
            (op.color.x, op.color.y, op.color.z, _) = sims4.color.to_rgba(self._color)
        self.serialize_op(msg, op, protocol_constants.SET_LIGHT_COLOR)

class SetHauntedLight(Op):

    def __init__(self, start):
        super().__init__()
        self._start = start

    def __repr__(self):
        return standard_repr(self, self._start)

    def write(self, msg):
        op = DistributorOps_pb2.SetHauntedLight()
        if self._start is not None:
            op.start = self._start
        else:
            op.start = False
        self.serialize_op(msg, op, protocol_constants.SET_HAUNTED_LIGHT)

class SetSimSleepState(Op):

    def __init__(self, sleep):
        super().__init__()
        self.sleep = sleep

    def __repr__(self):
        return standard_repr(self, self.sleep)

    def write(self, msg):
        op = DistributorOps_pb2.SetSimSleep()
        if self.sleep is not None:
            op.sleep = self.sleep
        else:
            op.sleep = False
        self.serialize_op(msg, op, protocol_constants.SET_SIM_SLEEP)

class SetCensorState(Op):

    def __init__(self, censor_state):
        super().__init__()
        self.censor_state = censor_state

    def __repr__(self):
        return standard_repr(self, self.censor_state)

    def write(self, msg):
        op = DistributorOps_pb2.SetCensorState()
        op.censor_state = self.censor_state
        self.serialize_op(msg, op, protocol_constants.SET_CENSOR_STATE)

class SetGeometryState(Op):

    def __init__(self, state_name_hash):
        super().__init__()
        self.state_name_hash = state_name_hash

    def __repr__(self):
        return standard_repr(self, self.state_name_hash)

    def write(self, msg):
        op = DistributorOps_pb2.SetGeometryState()
        if self.state_name_hash is not None:
            op.state_name_hash = self.state_name_hash
        else:
            op.state_name_hash = 0
        self.serialize_op(msg, op, protocol_constants.SET_GEOMETRY_STATE)

class SetStandInModel(Op):

    def __init__(self, model):
        super().__init__()
        self.model = model

    def __repr__(self):
        return standard_repr(self, self.model)

    def write(self, msg):
        op = DistributorOps_pb2.SetStandInModel()
        if self.model is None:
            resource_key = protocolbuffers.ResourceKey_pb2.ResourceKey()
            resource_key.type = 0
            resource_key.group = 0
            resource_key.instance = 0
            op.model_key = resource_key
        else:
            op.model_key = get_protobuff_for_key(self.model)
        self.serialize_op(msg, op, protocol_constants.SET_STANDIN_MODEL)

class SetVisibility(Op):

    def __init__(self, value):
        super().__init__()
        if value is not None:
            self.visibility = value.visibility
            self.inherits = value.inherits
            self.enable_drop_shadow = value.enable_drop_shadow
        else:
            self.visibility = True
            self.inherits = None
            self.enable_drop_shadow = False

    def __repr__(self):
        return standard_repr(self, self.visibility, self.inherits, self.enable_drop_shadow)

    def write(self, msg):
        op = DistributorOps_pb2.SetVisibility()
        if self.visibility is not None:
            op.visibility = self.visibility
        else:
            op.visibility = True
        if self.inherits is not None:
            op.inherits = self.inherits
        if self.enable_drop_shadow is not None:
            op.enable_drop_shadow = self.enable_drop_shadow
        else:
            op.enable_drop_shadow = False
        self.serialize_op(msg, op, protocol_constants.SET_VISIBILITY)

class SetVisibilityFlags(Op):

    def __init__(self, value):
        super().__init__()
        self.visibility_flags = value

    def write(self, msg):
        op = DistributorOps_pb2.SetVisibilityFlags()
        if self.visibility_flags is not None:
            op.visibility_flags = self.visibility_flags
        else:
            op.visibility_flags = 255
        self.serialize_op(msg, op, protocol_constants.SET_VISIBILITY_FLAGS)

class SetMaterialState(Op):

    def __init__(self, value):
        super().__init__()
        if value is not None:
            self.state_name_hash = value.state_name_hash
            self.opacity = value.opacity
            self.transition = value.transition
        else:
            self.state_name_hash = 0
            self.opacity = None
            self.transition = None

    def __repr__(self):
        return standard_repr(self, self.state_name_hash)

    def write(self, msg):
        op = DistributorOps_pb2.SetMaterialState()
        if self.state_name_hash is not None:
            op.state_name_hash = self.state_name_hash
        else:
            op.state_name_hash = 0
        if self.opacity is not None:
            op.opacity = self.opacity
        if self.transition is not None:
            op.transition = self.transition
        self.serialize_op(msg, op, protocol_constants.SET_MATERIAL_STATE)

class SetSortOrder(Op):

    def __init__(self, sort_order):
        super().__init__()
        self.sort_order = sort_order

    def __repr__(self):
        return standard_repr(self, self.sort_order)

    def write(self, msg):
        op = DistributorOps_pb2.SetSortOrder()
        op.sort_order = self.sort_order
        self.serialize_op(msg, op, protocol_constants.SET_SORT_ORDER)

class SetMoney(Op):

    def __init__(self, amount, vfx_amount, reason):
        super().__init__()
        self.amount = amount
        self.vfx_amount = vfx_amount
        self.reason = reason

    def __repr__(self):
        return standard_repr(self, self.amount)

    def write(self, msg):
        op = DistributorOps_pb2.SetMoney()
        op.money = self.amount
        op.reason = self.reason
        op.vfx_amount = self.vfx_amount
        self.serialize_op(msg, op, protocol_constants.SET_MONEY)

class InitializeCollection(Op):

    def __init__(self, collection_data):
        super().__init__()
        self._collection_data = collection_data

    def __repr__(self):
        return standard_repr(self, self._collection_data)

    def write(self, msg):
        op = DistributorOps_pb2.InitializeCollection()
        for (key, value) in self._collection_data.items():
            with ProtocolBufferRollback(op.household_collections) as collection_data_msg:
                collection_data_msg.collectible_def_id = key
                collection_data_msg.collection_id = value.collection_id
                collection_data_msg.new = value.new
                collection_data_msg.quality = value.quality
                if value.icon_info is not None:
                    collection_data_msg.icon_info = value.icon_info
        self.serialize_op(msg, op, protocol_constants.COLLECTION_HOUSEHOLD_UPDATE)

class SetInteractable(Op):

    def __init__(self, interactable):
        super().__init__()
        self.interactable = interactable

    def __repr__(self):
        return standard_repr(self, self.interactable)

    def write(self, msg):
        op = DistributorOps_pb2.SetInteractable()
        op.interactable = self.interactable
        self.serialize_op(msg, op, protocol_constants.SET_INTERACTABLE)

class SetSkinTone(Op):

    def __init__(self, skin_tone):
        super().__init__()
        self.skin_tone = skin_tone

    def __repr__(self):
        return standard_repr(self, self.skin_tone)

    def write(self, msg):
        op = DistributorOps_pb2.SetSkinTone()
        op.skin_tone = self.skin_tone
        self.serialize_op(msg, op, protocol_constants.SET_SKIN_TONE)

class SetSkinToneValShift(Op):

    def __init__(self, skin_tone_val_shift):
        super().__init__()
        self.skin_tone_val_shift = skin_tone_val_shift

    def __repr__(self):
        return standard_repr(self, self.skin_tone_val_shift)

    def write(self, msg):
        op = DistributorOps_pb2.SetSkinToneValShift()
        op.skin_tone_val_shift = self.skin_tone_val_shift
        self.serialize_op(msg, op, protocol_constants.SET_SKIN_TONE_VAL_SHIFT)

class SetBabySkinTone(Op):

    def __init__(self, cloth_and_id):
        super().__init__()
        self.cloth_file_name = cloth_and_id[0]
        self.bassinet_id = cloth_and_id[1]

    def __repr__(self):
        return standard_repr(self)

    def write(self, msg):
        op = DistributorOps_pb2.SetBabySkinTone()
        if self.cloth_file_name is not None:
            op.cloth_file_name = self.cloth_file_name
        if self.bassinet_id is not None:
            op.bassinet_id = self.bassinet_id
        self.serialize_op(msg, op, protocol_constants.SET_BABY_SKIN_TONE)

class SetSimAttachment(Op):
    ATTACH = DistributorOps_pb2.SetSimAttachment.ATTACH
    DETACH = DistributorOps_pb2.SetSimAttachment.DETACH
    PREBUILD = DistributorOps_pb2.SetSimAttachment.PREBUILD

    def __init__(self, attachment_id, attach_option=0, infant_id=0):
        super().__init__()
        self.attachment_id = attachment_id if attachment_id is not None else 0
        self.attach_option = attach_option
        self.infant_id = infant_id

    def __repr__(self):
        return standard_repr(self, self.attachment_id, self.attach_option, self.infant_id)

    def write(self, msg):
        op = DistributorOps_pb2.SetSimAttachment()
        op.attachment_id = self.attachment_id
        op.attach_option = self.attach_option
        op.infant_id = self.infant_id
        self.serialize_op(msg, op, protocol_constants.SET_SIM_ATTACHMENT)

class SetPeltLayers(Op):

    def __init__(self, pelt_layers):
        super().__init__()
        self.pelt_layers = pelt_layers

    def __repr__(self):
        return standard_repr(self, self.pelt_layers)

    def write(self, msg):
        op = DistributorOps_pb2.SetPeltLayers()
        op.pelt_layers.MergeFromString(self.pelt_layers)
        self.serialize_op(msg, op, protocol_constants.SET_PELT_LAYERS)

class SetCustomTexture(Op):

    def __init__(self, custom_texture):
        super().__init__()
        self.custom_texture = custom_texture

    def __repr__(self):
        return standard_repr(self, self.custom_texture)

    def write(self, msg):
        op = DistributorOps_pb2.SetCustomTexture()
        op.custom_texture = self.custom_texture
        self.serialize_op(msg, op, protocol_constants.SET_CUSTOM_TEXTURE)

class SetVoicePitch(Op):

    def __init__(self, voice_pitch):
        super().__init__()
        self.voice_pitch = voice_pitch

    def __repr__(self):
        return standard_repr(self, self.voice_pitch)

    def write(self, msg):
        op = DistributorOps_pb2.SetVoicePitch()
        op.voice_pitch = self.voice_pitch
        self.serialize_op(msg, op, protocol_constants.SET_VOICE_PITCH)

class SetVoiceActor(Op):

    def __init__(self, voice_actor):
        super().__init__()
        self.voice_actor = voice_actor

    def __repr__(self):
        return standard_repr(self, self.voice_actor)

    def write(self, msg):
        op = DistributorOps_pb2.SetVoiceActor()
        op.voice_actor = self.voice_actor
        self.serialize_op(msg, op, protocol_constants.SET_VOICE_ACTOR)

class SetVoiceSuffixOverrides(Op):

    def __init__(self, new_overrides):
        super().__init__()
        self.overrides = new_overrides or {}

    def __repr__(self):
        return standard_repr(self, self.overrides)

    def write(self, msg):
        op = DistributorOps_pb2.SetVoiceSuffixOverrides()
        for (key, value) in self.overrides.items():
            with ProtocolBufferRollback(op.suffix_overrides) as override_msg:
                override_msg.suffix_type = key
                override_msg.suffix_override = value
        self.serialize_op(msg, op, protocol_constants.SET_VOICE_SUFFIX_OVERRIDES)

class SetVoiceEffect(Op):

    def __init__(self, voice_effect):
        super().__init__()
        self.voice_effect = voice_effect

    def __repr__(self):
        return standard_repr(self.voice_effect)

    def write(self, msg):
        op = DistributorOps_pb2.SetVoiceEffect()
        op.voice_effect = self.voice_effect
        self.serialize_op(msg, op, protocol_constants.SET_VOICE_EFFECT)

class OverridePlumbbob(Op):
    PLUMBOB_STATE_ACTIVE_SIM = 0
    PLUMBOB_STATE_CLUB_LEADER = 2

    def __init__(self, plumbbob_models):
        super().__init__()
        self.plumbbob_models = plumbbob_models

    def __repr__(self):
        return standard_repr(self, self.plumbbob_models)

    def write(self, msg):
        op = Sims_pb2.PlumbbobSetPlumbbobOverrideModelKey()
        if self.plumbbob_models:
            (active_sim_model, club_leader_model) = self.plumbbob_models
            override_key = Sims_pb2.PlumbbobOverrideModelKey()
            override_key.state = OverridePlumbbob.PLUMBOB_STATE_ACTIVE_SIM
            override_key.key = active_sim_model
            op.overrides.append(override_key)
            override_key = Sims_pb2.PlumbbobOverrideModelKey()
            override_key.state = OverridePlumbbob.PLUMBOB_STATE_CLUB_LEADER
            override_key.key = club_leader_model
            op.overrides.append(override_key)
        self.serialize_op(msg, op, protocol_constants.PLUMBBOB_OVERRIDE_KEY)

class SetPhysique(Op):

    def __init__(self, physique):
        super().__init__()
        self.physique = physique

    def __repr__(self):
        return standard_repr(self, self.physique)

    def write(self, msg):
        op = DistributorOps_pb2.SetPhysique()
        op.physique = self.physique
        self.serialize_op(msg, op, protocol_constants.SET_PHYSIQUE)

class SetFacialAttributes(Op):

    def __init__(self, facial_attributes):
        super().__init__()
        self.facial_attributes = facial_attributes

    def __repr__(self):
        return standard_repr(self, self.facial_attributes)

    def write(self, msg):
        msg.type = protocol_constants.SET_FACIAL_ATTRIBUTES
        msg.data = self.facial_attributes or b''

class SetGeneticData(Op):

    def __init__(self, genetic_data):
        super().__init__()
        self.genetic_data = genetic_data

    def __repr__(self):
        return standard_repr(self, self.genetic_data)

    def write(self, msg):
        msg.type = protocol_constants.SET_SIM_GENETIC_DATA
        msg.data = self.genetic_data or b''

class SetThumbnail(Op):

    def __init__(self, key):
        super().__init__()
        self.key = key

    def __repr__(self):
        return standard_repr(self, self.key)

    def write(self, msg):
        op = DistributorOps_pb2.SetThumbnail()
        op.key.type = self.key.type
        op.key.instance = self.key.instance
        op.key.group = self.key.group
        self.serialize_op(msg, op, protocol_constants.SET_THUMBNAIL)

class SetSimOutfits(Op):

    def __init__(self, outfits):
        super().__init__()
        self.outfits = outfits

    def __repr__(self):
        return standard_repr(self, self.outfits)

    def write(self, msg):
        op = DistributorOps_pb2.SetSimOutfits()
        op.outfits = self.outfits.save_outfits()
        self.serialize_op(msg, op, protocol_constants.SET_SIM_OUTFIT)

class ChangeSimOutfit(Op):

    def __init__(self, outfitcategory_and_index):
        super().__init__()
        self.outfit_category = outfitcategory_and_index[0]
        self.outfit_index = outfitcategory_and_index[1]

    def __repr__(self):
        return standard_repr(self, self.outfit_category)

    def write(self, msg):
        op = DistributorOps_pb2.ChangeSimOutfit()
        op.type = self.outfit_category
        op.index = self.outfit_index
        self.serialize_op(msg, op, protocol_constants.CHANGE_SIM_OUTFIT)

class UpdateClientActiveSim(Op):

    def __init__(self, active_sim):
        super().__init__()
        if active_sim is not None:
            self._active_sim_id = active_sim.id
        else:
            self._active_sim_id = 0

    def __repr__(self):
        return standard_repr(self, self._active_sim_id)

    def write(self, msg):
        op = Sims_pb2.UpdateClientActiveSim()
        op.active_sim_id = self._active_sim_id
        self.serialize_op(msg, op, protocol_constants.SET_SIM_ACTIVE)

class TravelSwitchToZone(Op):

    def __init__(self, travel_info):
        super().__init__()
        self.travel_info = travel_info

    def __repr__(self):
        return standard_repr(self, self.travel_info)

    def write(self, msg):
        op = DistributorOps_pb2.TravelSwitchToZone()
        op.sim_to_visit_id = self.travel_info[0]
        op.household_to_control_id = self.travel_info[1]
        op.zone_id = self.travel_info[2]
        op.world_id = self.travel_info[3]
        self.serialize_op(msg, op, protocol_constants.TRAVEL_SWITCH_TO_ZONE)

class TravelLiveToNhdToLive(Op):

    def __init__(self, sim_to_control_id, household_to_control_id):
        super().__init__()
        self.sim_to_control_id = sim_to_control_id
        self.household_to_control_id = household_to_control_id

    def write(self, msg):
        op = DistributorOps_pb2.TravelLiveToNhdToLive()
        op.sim_to_control_id = self.sim_to_control_id
        op.household_to_control_id = self.household_to_control_id
        self.serialize_op(msg, op, protocol_constants.TRAVEL_LIVE_TO_NHD_TO_LIVE)

class TravelBringToZone(Op):

    def __init__(self, summon_info):
        super().__init__()
        self.summon_info = summon_info

    def __repr__(self):
        return standard_repr(self, self.summon_info)

    def write(self, msg):
        op = DistributorOps_pb2.TravelBringToZone()
        op.sim_to_bring_id = self.summon_info[0]
        op.household_id = self.summon_info[1]
        op.zone_id = self.summon_info[2]
        op.world_id = self.summon_info[3]
        self.serialize_op(msg, op, protocol_constants.TRAVEL_BRING_TO_ZONE)

class SetBuildBuyUseFlags(Op):

    def __init__(self, build_buy_use_flags):
        super().__init__()
        self._build_buy_use_flags = build_buy_use_flags

    def write(self, msg):
        op = DistributorOps_pb2.SetBuildBuyUseFlags()
        op.use_flags = self._build_buy_use_flags
        self.serialize_op(msg, op, protocol_constants.SET_BUILDBUY_USE_FLAGS)

class SetOwnerId(Op):

    def __init__(self, owner_household_id):
        super().__init__()
        self._owner_household_id = owner_household_id if owner_household_id is not None else 0

    def write(self, msg):
        op = DistributorOps_pb2.SetId()
        op.id = self._owner_household_id
        self.serialize_op(msg, op, protocol_constants.SET_OWNER_ID)

class SetFocusCompatibility(Op):
    OP_TYPE = sims4.hash_util.hash32('focus_compatibility')

    def __init__(self, focus_compatibility):
        super().__init__()
        self.op = DistributorOps_pb2.SetActorData()
        self.op.type = self.OP_TYPE
        if focus_compatibility is not None:
            self.op.data.append(focus_compatibility)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACTOR_DATA)

class StopVFX(Op):

    def __init__(self, target_id, actor_id, stop_type=None, **kwargs):
        super().__init__(**kwargs)
        self._target_id = target_id
        self._actor_id = actor_id
        self._stop_type = stop_type

    def write(self, msg):
        op = protocolbuffers.VFX_pb2.VFXStop()
        op.object_id = self._target_id
        op.actor_id = self._actor_id
        op.transition_type = self._stop_type
        self.serialize_op(msg, op, protocol_constants.VFX_STOP)

class SetVFXState(Op):

    def __init__(self, target_id, actor_id, state_index):
        super().__init__()
        self._target_id = target_id
        self._actor_id = actor_id
        self._state_index = state_index

    def write(self, msg):
        op = protocolbuffers.VFX_pb2.VFXSetState()
        op.object_id = self._target_id
        op.actor_id = self._actor_id
        op.state_index = self._state_index
        self.serialize_op(msg, op, protocol_constants.VFX_SET_STATE)

class StopSound(Op):

    def __init__(self, target_id, channel, immediate=False):
        super().__init__(immediate=immediate)
        self._target_id = target_id
        self._channel = channel

    def __repr__(self):
        return standard_angle_repr(self, self._channel)

    def write(self, msg):
        op = protocolbuffers.Audio_pb2.SoundStop()
        op.object_id = self._target_id
        op.channel = self._channel
        self.serialize_op(msg, op, protocol_constants.SOUND_STOP)

class StartArb(Op):

    def __init__(self, arb):
        super().__init__()
        if arb is not None:
            self._arb_bytes = arb._bytes()
            self._is_interruptible = arb._is_interruptible()
            self._should_analyze = arb._should_analyze()
        else:
            self._arb_bytes = None
            self._is_interruptible = False
            self._should_analyze = False
            sims4.log.error('Animation', 'Creating an empty ARB.')

    def write(self, msg):
        op = Animation_pb2.AnimationRequestBlock()
        if self._arb_bytes is not None:
            op.arb_data = self._arb_bytes
        op.is_interruptible = self._is_interruptible
        op.should_analyze = self._should_analyze
        self.serialize_op(msg, op, protocol_constants.ARB_INITIAL_UPDATE)

class SetActorType(Op):
    OP_TYPE = sims4.hash_util.hash32('actortype')

    def __init__(self, actor_type):
        super().__init__()
        self.op = DistributorOps_pb2.SetActorData()
        self.op.type = self.OP_TYPE
        self.op.data.append(actor_type)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACTOR_DATA)

class SetCreatureType(Op):
    OP_TYPE = sims4.hash_util.hash32('creaturetype')

    def __init__(self, creature_type):
        super().__init__()
        self.op = DistributorOps_pb2.SetActorData()
        self.op.type = self.OP_TYPE
        self.op.data.append(creature_type)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACTOR_DATA)

class SetActorStateMachine(Op):
    OP_TYPE = sims4.hash_util.hash32('statemachine')

    def __init__(self, str_name):
        super().__init__()
        self.op = DistributorOps_pb2.SetActorData()
        self.op.type = self.OP_TYPE
        hash_key = str_name.instance
        self.op.data.append(hash_key & 4294967295)
        self.op.data.append(hash_key >> 32)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACTOR_DATA)

class SetActorPosture(Op):
    OP_TYPE = sims4.hash_util.hash32('posture')

    class CarryInfo(enum.IntFlags, export=False):
        CARRY_NONE = 0
        CARRY_LEFT = 1
        CARRY_RIGHT = 2
        CARRY_BACK = 4
        CARRY_SIDE_MASK = CARRY_LEFT | CARRY_RIGHT

    def __init__(self, posture_state):
        super().__init__()
        self.op = DistributorOps_pb2.SetActorData()
        self.op.type = self.OP_TYPE
        if posture_state is not None:
            posture_state_spec_manifest = posture_state.body_posture_state_constraint.posture_state_spec[0]
            posture_state_spec_entry = tuple(posture_state_spec_manifest.in_best_order)[0]
            self.op.data.append(sims4.hash_util.hash32(posture_state_spec_entry[1]))
            self.op.data.append(sims4.hash_util.hash32(posture_state_spec_entry[2]))
            carry_info = SetActorPosture.CarryInfo.CARRY_NONE
            from carry.carry_utils import get_carried_objects_gen
            from animation.posture_manifest import Hand
            for (hand, _, carry_object) in get_carried_objects_gen(posture_state.sim):
                if carry_object.is_sim:
                    if hand is Hand.LEFT:
                        carry_info |= SetActorPosture.CarryInfo.CARRY_LEFT
                    elif hand is Hand.RIGHT:
                        carry_info |= SetActorPosture.CarryInfo.CARRY_RIGHT
                    elif hand is Hand.BACK:
                        carry_info |= SetActorPosture.CarryInfo.CARRY_BACK
            self.op.data.append(carry_info)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACTOR_DATA)

class SetActorStateMachineParams(Op):

    def __init__(self, params):
        super().__init__()
        self.params = params

    def write(self, msg):
        op = DistributorOps_pb2.SetActorStateMachineParams()
        for (key, value) in self.params.items():
            with ProtocolBufferRollback(op.asm_params) as param_data:
                param_data.param_key = key
                if isinstance(value, str):
                    param_data.param_value_string = value
                elif isinstance(value, int):
                    param_data.param_value_int = value
                elif isinstance(value, bool):
                    param_data.param_value_bool = value
        self.serialize_op(msg, op, protocol_constants.SET_ACTOR_STATE_MACHINE_PARAMS)

class DisablePendingHeadline(Op):

    def __init__(self, sim_id, group_id=None, was_canceled=False):
        super().__init__()
        self.sim_id = sim_id
        self.group_id = group_id
        self.was_canceled = was_canceled

    def write(self, msg):
        op = Sims_pb2.DisablePendingInteractionHeadline()
        op.sim_id = self.sim_id
        if self.group_id is not None:
            op.group_id = self.group_id
        op.canceled = self.was_canceled
        self.serialize_op(msg, op, protocol_constants.DISABLE_PENDING_HEADLINE)

class CancelPendingHeadline(Op):

    def __init__(self, sim_id):
        super().__init__()
        self.sim_id = sim_id

    def write(self, msg):
        op = Sims_pb2.EnablePendingInteractionHeadline()
        op.sim_id = self.sim_id
        self.serialize_op(msg, op, protocol_constants.ENABLE_PENDING_HEADLINE)

class SetUiObjectMetadata(SparseMessageOp):
    TYPE = protocol_constants.SET_UI_OBJECT_METADATA

class SetUiObjectMetadataImmediate(SparseMessageOp):
    TYPE = protocol_constants.SET_UI_OBJECT_METADATA

    def __init__(self, value):
        super().__init__(value, immediate=True)

class SituationStartOp(GenericCreate):

    def __init__(self, obj, protocol_msg, *args, **kwargs):
        super().__init__(obj, protocol_msg, *args, **kwargs)

    def write(self, msg):
        msg.type = protocol_constants.SITUATION_START
        msg.data = self.data

class SituationEndOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_END)

class SituationSimJoinedOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_SIM_JOINED)

class SituationSimLeftOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_SIM_LEFT)

class SituationScoreUpdateOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_SCORE_UPDATED)

class SituationGoalUpdateOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_GOALS_UPDATE)

class SituationTimeUpdate(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_TIME_UPDATE)

class SituationCallbackResponse(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_CALLBACK_RESPONSE)

class SituationMeterUpdateOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_METER_UPDATE)

class SituationIconUpdateOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SITUATION_ICON_UPDATE)

class VideoSetPlaylistOp(Op):

    def __init__(self, playlist):
        super().__init__()
        self.protocol_msg = playlist.get_protocol_msg()

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.VIDEO_SET_PLAYLIST)

class HouseholdCreate(GenericCreate):

    def __init__(self, obj, *args, is_active=False, **kwargs):
        op = DistributorOps_pb2.HouseholdCreate()
        additional_ops = (distributor.ops.SetMoney(obj.funds.money, False, 0),)
        if is_active:
            additional_ops += (distributor.ops.InitializeCollection(obj.get_household_collections()),)
        super().__init__(obj, op, *args, additional_ops=additional_ops, **kwargs)

    def write(self, msg):
        msg.type = protocol_constants.HOUSEHOLD_CREATE
        msg.data = self.data

class HouseholdDelete(Op):

    def write(self, msg):
        msg.type = protocol_constants.HOUSEHOLD_DELETE

class TravelGroupCreate(GenericCreate):

    def __init__(self, obj, *args, zone_id=0, group_type=0, **kwargs):
        op = DistributorOps_pb2.TravelGroupCreate()
        op.zone_id = zone_id
        op.group_type = group_type
        super().__init__(obj, op, *args, **kwargs)

    def write(self, msg):
        msg.type = protocol_constants.TRAVEL_GROUP_CREATE
        msg.data = self.data

class TravelGroupDelete(Op):

    def write(self, msg):
        msg.type = protocol_constants.TRAVEL_GROUP_DELETE

class SetValue(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetValue()
        self.op.value = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_VALUE)

class SetAge(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetSimAge()
        self.op.age = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_AGE)

class SetGender(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetGender()
        self.op.gender = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_GENDER)

class SetSpecies(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetSpecies()
        self.op.species = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SPECIES)

class SetPrimaryAspiration(Op):

    def __init__(self, aspiration):
        super().__init__()
        self.op = DistributorOps_pb2.SetPrimaryAspiration()
        self.op.aspiration_id = aspiration.guid64 if aspiration is not None else 0

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_PRIMARY_ASPIRATION)

class SetUnfinishedBusinessAspiration(Op):

    def __init__(self, aspiration):
        super().__init__()
        self.op = DistributorOps_pb2.SetUnfinishedBusinessAspiration()
        self.op.aspiration_id = aspiration.guid64 if aspiration is not None else 0

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_UNFINISHED_BUSINESS_ASPIRATION)

class SetWhimComplete(Op):

    def __init__(self, whim_guid):
        super().__init__()
        self.op = DistributorOps_pb2.SetWhimComplete()
        self.op.whim_guid64 = whim_guid

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_WHIM_COMPLETE)

class SetCurrentWhims(Op):

    def __init__(self, whim_goals):
        super().__init__()
        self.op = DistributorOps_pb2.SetCurrentWhims()
        if whim_goals:
            self.op.whim_goals.extend(whim_goals)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_CURRENT_WHIMS)

class SetWhimBucks(Op):

    def __init__(self, whim_bucks, reason):
        super().__init__()
        self.op = DistributorOps_pb2.SetWhimBucks()
        self.op.whim_bucks = whim_bucks
        self.op.reason = reason

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_WHIM_BUCKS)

class SetTraits(Op):

    def __init__(self, all_traits, traits_to_add=None, traits_to_remove=None):
        super().__init__()
        self.op = DistributorOps_pb2.SetTraits()
        if all_traits:
            self.op.trait_ids.extend(all_traits)
        if traits_to_add:
            self.op.traits_to_add.extend(traits_to_add)
        if traits_to_remove:
            self.op.traits_to_remove.extend(traits_to_remove)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_TRAITS)

class SetDeathType(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetDeathType()
        if value is not None:
            self.op.death_type = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_DEATH_TYPE)

class SetAgeProgress(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetSimAgeProgress()
        (progress, tooltip) = value
        self.op.progress = progress
        if tooltip is not None:
            self.op.aging_disabled_tooltip = tooltip

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_AGE_PROGRESS)

class SetSimAgeProgressTooltipData(Op):

    def __init__(self, current_day, ready_to_age_day, days_alive):
        super().__init__()
        self.op = DistributorOps_pb2.SetSimAgeProgressTooltipData()
        self.op.current_day = current_day
        self.op.ready_to_age_day = ready_to_age_day
        self.op.days_alive = days_alive

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_AGE_PROGRESS_TOOLTIP_DATA)

class SetCurrentSkillId(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetCurrentSkillId()
        self.op.current_skill_id = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_CURRENT_SKILL_ID)

class Heartbeat(Op):

    def write(self, msg):
        msg.type = protocol_constants.HEARTBEAT

class SetGameTime(Op):

    def __init__(self, server_time, monotonic_time, game_time, game_speed, clock_speed, initial_game_time, super_speed, serial_number):
        super().__init__()
        self.op = Area_pb2.GameTimeCommand()
        self.op.clock_speed = clock_speed
        self.op.game_speed = game_speed
        self.op.server_time = server_time
        self.op.sync_game_time = game_time + initial_game_time
        self.op.monotonic_time = monotonic_time
        self.op.super_speed = super_speed
        self.op.serial_number = serial_number

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_GAME_TIME)

class SetCareers(Op):

    def __init__(self, career_tracker):
        super().__init__()
        self.op = DistributorOps_pb2.SetCareers()
        if career_tracker is None:
            return
        (careers, multi_gig_careers) = career_tracker.get_multigig_and_standard_careers()
        custom_data = career_tracker.custom_career_data
        for career in careers:
            with ProtocolBufferRollback(self.op.careers) as career_op:
                career.populate_set_career_op(career_op)
        for career in multi_gig_careers:
            for gig in career.get_current_gigs():
                with ProtocolBufferRollback(self.op.careers) as career_op:
                    career.populate_set_career_op(career_op, gig=gig)
        if custom_data is not None:
            if custom_data._custom_name:
                self.op.custom_name = custom_data._custom_name
            if custom_data._custom_description:
                self.op.custom_description = custom_data._custom_description

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_CAREER)

class DisplayCareerTooltip(Op):

    def __init__(self, career_uid, sim_id, gig_uid, objective_uid):
        super().__init__()
        self.op = DistributorOps_pb2.DisplayCareerTooltip()
        self.op.career_uid = career_uid
        self.op.sim_id = sim_id
        if gig_uid:
            self.op.gig_uid = gig_uid
        if objective_uid:
            self.op.objective_uid = objective_uid

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.DISPLAY_CAREER_TOOLTIP)

class NotifyNotebookEntryDiscovered(Op):

    def __init__(self, subcategory_name):
        super().__init__()
        self.op = DistributorOps_pb2.NotifyNotebookEntryDiscovered()
        self.op.subcategory_name = subcategory_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.NOTIFY_NOTEBOOK_ENTRY_DISCOVERED)

class SetAtWorkInfos(Op):

    def __init__(self, at_work_infos):
        super().__init__()
        self.op = DistributorOps_pb2.SetAtWorkInfos()
        if at_work_infos:
            self.op.at_work_infos.extend(at_work_infos)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_AT_WORK_INFO)

class UpdateFindCareerInteractionAvailability(Op):

    def __init__(self, enable, tooltip):
        super().__init__()
        self.op = DistributorOps_pb2.UpdateFindCareerInteractionAvailability()
        self.op.enable = enable
        if tooltip is not None:
            self.op.tooltip = tooltip

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.UPDATE_FIND_CAREER_INTERACTION_AVAILABILITY)

class EndOfWorkday(Op):

    def __init__(self, career_uid, score_text, level_icon, money_earned, paid_time_off_earned):
        super().__init__()
        self.op = DistributorOps_pb2.EndOfWorkday()
        self.op.career_uid = career_uid
        self.op.score_text = score_text
        self.op.level_icon.type = level_icon.type
        self.op.level_icon.group = level_icon.group
        self.op.level_icon.instance = level_icon.instance
        self.op.money_earned = money_earned
        self.op.paid_time_off_earned = paid_time_off_earned

    def add_promotion_info(self, career, text):
        self.op.promotion.text = text
        career.populate_set_career_op(self.op.promotion.career)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.END_OF_WORKDAY)

class SetAccountId(Op):

    def __init__(self, account_id):
        super().__init__()
        self.op = DistributorOps_pb2.SetAccountId()
        self.op.account_id = account_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACCOUNT_ID)

class SetIsNpc(Op):

    def __init__(self, is_npc):
        super().__init__()
        self.op = DistributorOps_pb2.SetIsNpc()
        self.op.is_npc = is_npc

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_IS_NPC)

class SetPlayerProtectedStatus(Op):

    def __init__(self, is_player):
        super().__init__()
        self.op = DistributorOps_pb2.SetPlayerProtectedStatus()
        self.op.is_player_protected = is_player

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_PLAYER_PROTECTED_STATUS)

class SetPlayedStatus(Op):

    def __init__(self, is_played):
        super().__init__()
        self.op = DistributorOps_pb2.SetPlayedStatus()
        self.op.is_played = is_played

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_PLAYED_STATUS)

class SetHouseholdName(Op):

    def __init__(self, name):
        super().__init__()
        self.op = DistributorOps_pb2.SetHouseholdName()
        self.op.name = name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_HOUSEHOLD_NAME)

class SetHouseholdDescription(Op):

    def __init__(self, description):
        super().__init__()
        self.op = DistributorOps_pb2.SetHouseholdDescription()
        self.op.description = description

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_HOUSEHOLD_DESCRIPTION)

class SetHouseholdHidden(Op):

    def __init__(self, hidden):
        super().__init__()
        self.op = DistributorOps_pb2.SetHouseholdHidden()
        self.op.hidden = hidden

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_HOUSEHOLD_HIDDEN)

class SetHouseholdHomeZoneId(Op):

    def __init__(self, home_zone_id):
        super().__init__()
        self.op = DistributorOps_pb2.SetHouseholdHomeZoneId()
        self.op.home_zone_id = home_zone_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_HOUSEHOLD_HOME_ZONE_ID)

class SetHouseholdSims(Op):

    def __init__(self, sims):
        super().__init__()
        self.op = DistributorOps_pb2.SetHouseholdSims()
        self.op.sim_ids.extend(sim.sim_id for sim in sims)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_HOUSEHOLD_SIMS)

class SetFirstName(Op):

    def __init__(self, first_name):
        super().__init__()
        self.op = DistributorOps_pb2.SetFirstName()
        self.op.first_name = first_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_FIRST_NAME)

class SetLastName(Op):

    def __init__(self, last_name):
        super().__init__()
        self.op = DistributorOps_pb2.SetLastName()
        self.op.last_name = last_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_LAST_NAME)

class SetPackedPronouns(Op):

    def __init__(self, packed_pronouns):
        super().__init__()
        self.op = DistributorOps_pb2.SetPackedPronouns()
        self.op.packed_pronouns = packed_pronouns

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_PACKED_PRONOUNS)

class SetBusinessNameDescriptionKey(Op):

    def __init__(self, name_key, description_key, sim_id):
        super().__init__()
        self.op = DistributorOps_pb2.SetBusinessNameAndDescriptionKey()
        self.op.sim_id = sim_id
        self.op.name_key = name_key
        self.op.description_key = description_key

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_BUSINESS_NAME_DESCRIPTION_KEY)

class SetBreedName(Op):

    def __init__(self, breed_name):
        super().__init__()
        self.op = DistributorOps_pb2.SetBreedName()
        self.op.breed_name = breed_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_BREED_NAME)

class SetFullNameKey(Op):

    def __init__(self, full_name_key):
        super().__init__()
        self.op = DistributorOps_pb2.SetFullNameKey()
        self.op.full_name_key = full_name_key

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_FULL_NAME_KEY)

class SetFirstNameKey(Op):

    def __init__(self, first_name_key):
        super().__init__()
        self.op = DistributorOps_pb2.SetFirstNameKey()
        self.op.first_name_key = first_name_key

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_FIRST_NAME_KEY)

class SetLastNameKey(Op):

    def __init__(self, last_name_key):
        super().__init__()
        self.op = DistributorOps_pb2.SetLastNameKey()
        self.op.last_name_key = last_name_key

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_LAST_NAME_KEY)

class SetPackedPronounsKey(Op):

    def __init__(self, packed_pronouns_key):
        super().__init__()
        self.op = DistributorOps_pb2.SetPackedPronounsKey()
        self.op.packed_pronouns_key = packed_pronouns_key

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_PACKED_PRONOUNS_KEY)

class SetBreedNameKey(Op):

    def __init__(self, breed_name_key):
        super().__init__()
        self.op = DistributorOps_pb2.SetBreedNameKey()
        self.op.breed_name_key = breed_name_key

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_BREED_NAME_KEY)

class SetOccultTypes(Op):

    def __init__(self, occult_types):
        super().__init__()
        self.op = DistributorOps_pb2.SetOccultTypes()
        self.op.occult_types = occult_types

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_OCCULT_TYPES)

class SetCurrentOccultTypes(Op):

    def __init__(self, current_occult_types):
        super().__init__()
        self.op = DistributorOps_pb2.SetCurrentOccultTypes()
        self.op.current_occult_types = current_occult_types

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_CURRENT_OCCULT_TYPES)

class SetMannequinData(Op):

    def __init__(self, sim_info_data):
        super().__init__()
        self.op = DistributorOps_pb2.SetMannequinData()
        self.op.sim_info_data.mannequin_id = sim_info_data.sim_id
        self.op.sim_info_data.age = sim_info_data.age
        self.op.sim_info_data.gender = sim_info_data.gender
        self.op.sim_info_data.physique = sim_info_data.physique
        self.op.sim_info_data.facial_attributes = sim_info_data.facial_attributes
        self.op.sim_info_data.skin_tone = sim_info_data.skin_tone
        self.op.sim_info_data.skin_tone_val_shift = sim_info_data.skin_tone_val_shift
        self.op.sim_info_data.outfits = sim_info_data.save_outfits()

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_MANNEQUIN_DATA)

class SetMannequinPose(Op):

    def __init__(self, mannequin_pose):
        super().__init__()
        self.op = DistributorOps_pb2.SetMannequinPose()
        if mannequin_pose is not None:
            self.op.animation_pose.asm = get_protobuff_for_key(mannequin_pose.asm)
            self.op.animation_pose.state_name = mannequin_pose.state_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_MANNEQUIN_POSE)

class SetWallsUpOrDown(Op):

    def __init__(self, walls_up):
        super().__init__()
        self.op = DistributorOps_pb2.SetWallsUpOrDown()
        if services.get_plex_service().is_zone_an_apartment(services.current_zone_id(), consider_penthouse_an_apartment=False):
            self.op.walls_up = False
            self.op.hide_livable_plexes = walls_up
        else:
            self.op.walls_up = walls_up

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_WALLS_UP_OR_DOWN)

class OverrideWallsUp(Op):

    def __init__(self, override=True, lot_id=None):
        super().__init__()
        self.op = DistributorOps_pb2.OverrideWallsUp()
        self.op.enable_override = override
        if lot_id is not None:
            self.op.lot_id = lot_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.OVERRIDE_WALLS_UP)

class InteractionProgressUpdate(Op):

    def __init__(self, sim_id, percent, rate_change, interaction_id):
        super().__init__()
        self.op = InteractionOps_pb2.InteractionProgressUpdate()
        self.op.sim_id = sim_id
        self.op.percent = percent
        self.op.rate_change = rate_change
        self.op.interaction_id = interaction_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.INTERACTION_PROGRESS_UPDATE)

class PreloadSimOutfit(Op):

    def __init__(self, outfit_category_and_index_list):
        super().__init__()
        self.outfit_category_and_index_list = outfit_category_and_index_list

    def write(self, msg):
        op = DistributorOps_pb2.PreloadSimOutfit()
        for (outfit_category, outfit_index) in self.outfit_category_and_index_list:
            with ProtocolBufferRollback(op.outfits) as outfit:
                outfit.type = outfit_category
                outfit.index = outfit_index
        self.serialize_op(msg, op, protocol_constants.PRELOAD_SIM_OUTFIT)

class SkillProgressUpdate(Op):

    def __init__(self, skill_instance_id, change_rate, curr_points, hide_progress_bar):
        super().__init__()
        self.op = Commodities_pb2.SkillProgressUpdate()
        self.op.skill_id = skill_instance_id
        self.op.change_rate = change_rate
        self.op.curr_points = int(curr_points)
        self.op.hide_progress_bar = hide_progress_bar

    @property
    def block_on_task_owner(self):
        return False

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SIM_SKILL_PROGRESS)

class SocialContextUpdate(Op):

    def __init__(self, social_context_bit):
        super().__init__()
        self.op = Sims_pb2.SocialContextUpdate()
        if social_context_bit is not None:
            self.op.bit_id = social_context_bit.guid64

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SOCIAL_CONTEXT_UPDATE)

class RelationshipUpdate(Op):

    def __init__(self, protocol_buffer):
        super().__init__()
        self.protocol_buffer = protocol_buffer

    def write(self, msg):
        self.serialize_op(msg, self.protocol_buffer, protocol_constants.SIM_RELATIONSHIP_UPDATE)

class SetPhoneSilence(Op):

    def __init__(self, silence):
        super().__init__()
        self.op = DistributorOps_pb2.SetPhoneSilence()
        self.op.silence = silence

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_PHONE_SILENCE)

class SetAwayAction(Op):

    def __init__(self, away_action):
        super().__init__()
        self.op = DistributorOps_pb2.SetAwayAction()
        if away_action.icon_data is not None:
            self.op.icon.type = away_action.icon_data.icon.type
            self.op.icon.instance = away_action.icon_data.icon.instance
            self.op.icon.group = away_action.icon_data.icon.group
            self.op.tooltip = away_action.icon_data.tooltip()

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_AWAY_ACTION)

class SetObjectDefinitionId(Op):

    def __init__(self, def_id):
        super().__init__()
        self.def_id = def_id

    def __repr__(self):
        return standard_repr(self, self.def_id)

    def write(self, msg):
        op = DistributorOps_pb2.SetObjectDefinitionId()
        op.def_id = self.def_id
        self.serialize_op(msg, op, protocol_constants.SET_OBJECT_DEFINITION_ID)

class SetTutorialTipSatisfy(Op):

    def __init__(self, tutorial_tip_id):
        super().__init__()
        self.op = ui_ops.SatisfyTutorialTip()
        self.op.tutorial_tip_id = tutorial_tip_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.TUTORIAL_TIP_SATISFY)

class FocusCamera(Op):

    def __init__(self, id=None, follow_mode=None):
        super().__init__()
        self.op = DistributorOps_pb2.FocusCamera()
        if id is not None:
            self.op.id = id
        if follow_mode is not None:
            self.op.follow_mode = follow_mode

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.FOCUS_CAMERA)

    def set_location(self, location):
        self.op.location.x = location.x
        self.op.location.y = location.y
        self.op.location.z = location.z

    def set_position(self, position):
        self.op.position.x = position.x
        self.op.position.y = position.y
        self.op.position.z = position.z

class CancelFocusCamera(Op):

    def __init__(self, id=None):
        super().__init__()
        self.op = DistributorOps_pb2.CancelFocusCamera()
        if id is not None:
            self.op.id = id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.CANCEL_FOCUS_CAMERA)

class FocusCameraOnLot(Op):

    def __init__(self, lot_id=None, lerp_time=1.0):
        super().__init__()
        self.op = DistributorOps_pb2.FocusCameraOnLot()
        if lot_id is not None:
            self.op.lot_id = lot_id
        if lerp_time is not None:
            self.op.lerp_time = lerp_time

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.FOCUS_CAMERA_ON_LOT)

class ShakeCamera(Op):

    def __init__(self, duration, frequency=None, amplitude=None, octaves=None, fade_multiplier=None):
        super().__init__()
        self.op = DistributorOps_pb2.InitCameraShake()
        self.op.duration = duration
        if frequency is not None:
            self.op.frequency = frequency
        if amplitude is not None:
            self.op.amplitude = amplitude
        if octaves is not None:
            self.op.octaves = octaves
        if fade_multiplier is not None:
            self.op.fade_multiplier = fade_multiplier

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.INIT_CAMERA_SHAKE)

class SetCallToAction(Op):

    def __init__(self, color, speed, thickness, tutorial_text=None):
        super().__init__()
        self.op = DistributorOps_pb2.SetCallToAction()
        (r, g, b, a) = sims4.color.to_rgba(color)
        self.op.color.x = r
        self.op.color.y = g
        self.op.color.z = b
        self.op.opacity = a
        self.op.speed = speed
        self.op.thickness = thickness
        if tutorial_text is not None:
            self.op.tutorial_text = tutorial_text

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_CALL_TO_ACTION)

class MoveHouseholdIntoLotFromGallery(Op):

    def __init__(self, household_id=None, num_household_sims=None, plex_zone_ids=EMPTY_SET, zone_id=0):
        super().__init__()
        self._zone_id = zone_id
        self._household_id = household_id
        self._num_household_sims = num_household_sims
        self._zone_ids = plex_zone_ids

    def write(self, msg):
        op = DistributorOps_pb2.MoveHouseholdIntoLotFromGallery()
        op.zone_id = self._zone_id
        if self._household_id is not None:
            op.household_id = self._household_id
        if self._num_household_sims is not None:
            op.num_household_sims = self._num_household_sims
        op.zone_ids.extend(self._zone_ids)
        self.serialize_op(msg, op, protocol_constants.MOVE_HOUSEHOLD_INTO_LOT_FROM_GALLERY)

class CustomizableObjectDataList(Op):

    def __init__(self, objects):
        super().__init__()
        self.op = DistributorOps_pb2.CustomizableObjectDataList()
        saved_animal_slots = {}
        animal_service = services.animal_service()
        for obj in objects:
            attribute_data = obj.get_attribute_save_data()
            with ProtocolBufferRollback(self.op.object_data) as object_data:
                object_data.object_id = obj.id
                if attribute_data is not None:
                    object_data.attributes = attribute_data.SerializeToString()
                if obj.material_variant is not None:
                    object_data.material_variant = obj.material_variant
                texture_id = obj.get_canvas_texture_id()
                if texture_id is not None:
                    object_data.texture_id = texture_id
                texture_effect = obj.get_canvas_texture_effect()
                if texture_effect is not None:
                    object_data.texture_effect = texture_effect
                if animal_service is None:
                    continue
                animal_obj_component = obj.animalobject_component
                if animal_obj_component is not None:
                    home = animal_service.get_animal_home_id(obj.id)
                    if home is None:
                        continue
                    saved_slots = saved_animal_slots.get(home, [])
                    saved = animal_obj_component.save_animal_assignment_data(object_data, saved_slots)
                    if saved:
                        home = object_data.parent_id
                        saved_slots.append(object_data.slot_hash)
                        saved_animal_slots[home] = saved_slots

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.CUSTOMIZABLE_OBJECT_DATA_LIST)

class BreakThroughMessage(Op):

    def __init__(self, sim_id, progress, display_time):
        super().__init__()
        self.op = ui_ops.BreakThroughMessage()
        self.op.sim_id = sim_id
        self.op.progress = progress
        self.op.display_time = display_time

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.BREAK_THROUGH_MESSAGE)

class SetRetailFunds(Op):

    def __init__(self, funds):
        super().__init__()
        self.op = DistributorOps_pb2.SetRetailFunds()
        self.op.available_funds = funds

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_RETAIL_FUNDS)

class SetBuckFunds(Op):

    def __init__(self, bucks_type, available_funds, club_id=None, sim_id=None):
        super().__init__()
        self.op = DistributorOps_pb2.SetBuckFunds()
        self.op.bucks_type = bucks_type
        self.op.available_funds = available_funds
        if club_id is not None:
            self.op.club_id = club_id
        if sim_id is not None:
            self.op.sim_id = sim_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_BUCK_FUNDS)

class SetRetailDailyItemsSold(Op):

    def __init__(self, items_sold):
        super().__init__()
        self.op = DistributorOps_pb2.SetRetailDailyItemsSold()
        self.op.daily_retail_items_sold = items_sold

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_RETAIL_DAILY_ITEMS_SOLD)

class SetRetailDailyOutgoingCosts(Op):

    def __init__(self, outgoing_costs):
        super().__init__()
        self.op = DistributorOps_pb2.SetRetailDailyOutgoingCosts()
        self.op.daily_retail_outgoing_costs = outgoing_costs

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_RETAIL_DAILY_OUTGOING_COSTS)

class SetRetailDailyNetProfit(Op):

    def __init__(self, net_profit):
        super().__init__()
        self.op = DistributorOps_pb2.SetRetailDailyNetProfit()
        self.op.daily_retail_net_profit = net_profit

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_RETAIL_DAILY_NET_PROFIT)

class SetRetailStoreOpen(Op):

    def __init__(self, is_open, open_time):
        super().__init__()
        self.op = DistributorOps_pb2.SetRetailStoreOpen()
        self.op.is_open = is_open
        self.op.time_opened = open_time

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_RETAIL_STORE_OPEN)

class PurchaseIntentUpdate(Op):

    def __init__(self, sim_id, start_fill, end_fill, show_continuously=True):
        super().__init__()
        self.op = ui_ops.PurchaseIntentUpdate()
        self.op.sim_id = sim_id
        self.op.curr_value = int(100*start_fill)
        self.op.target_value = int(100*end_fill)
        self.op.show_continuously = show_continuously

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.PURCHASE_INTENT_UPDATE)

class SetSimHeadline(Op):

    def __init__(self, headline):
        super().__init__()
        self.op = DistributorOps_pb2.SetSimHeadline()
        if headline is not None:
            self.op.headline = headline

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_SIM_HEADLINE)

class SetLinkedSims(Op):

    def __init__(self, linked_sims):
        super().__init__()
        self.op = DistributorOps_pb2.SetLinkedSims()
        self.op.linked_sim_ids.extend(linked_sims)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_LINKED_SIMS)

class BuildBuyLockUnlock(Op):

    def __init__(self, build_buy_locked, reason=None):
        super().__init__()
        self.op = ui_ops.BuildBuyLockUnlock()
        self.op.build_buy_locked = build_buy_locked
        if reason is not None:
            self.op.reason = reason

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.BUILD_BUY_LOCK_UNLOCK)

class StartClubGathering(Op):

    def __init__(self, club_id):
        super().__init__()
        self.op = DistributorOps_pb2.StartClubGathering()
        self.op.club_id = club_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.START_CLUB_GATHERING)

class UpdateClubGathering(Op):

    def __init__(self, update_type, club_id, member_id):
        super().__init__()
        self.op = DistributorOps_pb2.UpdateClubGathering()
        self.op.club_update_type = update_type
        self.op.club_id = club_id
        self.op.member_id = member_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.UPDATE_CLUB_GATHERING)

class EndClubGathering(Op):

    def __init__(self, club_id):
        super().__init__()
        self.op = DistributorOps_pb2.EndClubGathering()
        self.op.club_id = club_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.END_CLUB_GATHERING)

class SendClubInfo(Op):

    def __init__(self, clubs, message_type):
        super().__init__()
        self.op = DistributorOps_pb2.ClubInfo()
        self.op.message_type = message_type
        for club in clubs:
            with ProtocolBufferRollback(self.op.clubs) as club_data:
                club.save(club_data)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_CLUB_INFO)

class SendClubBuildingInfo(Op):

    def __init__(self, criterias, available_lots):
        super().__init__()
        self.op = Clubs_pb2.ClubBuildingInfo()
        for criteria in criterias:
            self.op.criterias.append(criteria)
        for available_lot in available_lots:
            self.op.available_lots.append(available_lot)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_CLUB_BUILDING_INFO)

class SendClubMembershipCriteriaValidation(Op):

    def __init__(self, failure_infos):
        super().__init__()
        self.op = DistributorOps_pb2.ClubMembershipCriteriaValidation()
        for (sim_id, criteria_ids) in failure_infos:
            with ProtocolBufferRollback(self.op.failure_infos) as failure_info:
                failure_info.failed_sim_id = sim_id
                for failed_criteria in criteria_ids:
                    failure_info.failed_criteria_ids.append(failed_criteria)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_CLUB_MEMBERSHIP_CRITERIA_VALIDATION)

class SendClubValdiation(Op):

    def __init__(self, sim_id, failed_club_ids):
        super().__init__()
        self.op = DistributorOps_pb2.ClubValidation()
        self.op.failed_sim_id = sim_id
        for club_id in failed_club_ids:
            self.op.failed_club_ids.append(club_id)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_CLUB_VALIDATION)

class AskAboutClubsDialog(Op):

    def __init__(self, sim_id, club_ids=(), show_orgs=False):
        super().__init__()
        self.op = DistributorOps_pb2.AskAboutClubsDialog()
        self.op.sim_id = sim_id
        self.op.show_orgs = show_orgs
        for club_id in club_ids:
            self.op.club_ids.append(club_id)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.ASK_ABOUT_CLUBS_DIALOG)

class ShowClubInfoUI(Op):

    def __init__(self, club_id):
        super().__init__()
        self.op = Clubs_pb2.ShowClubInfoUI()
        self.op.club_id = club_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SHOW_CLUB_INFO_UI)

class SendClubInteractionRuleUpdate(Op):

    def __init__(self, rule_status):
        super().__init__()
        self.op = Clubs_pb2.ClubInteractionRuleUpdate()
        self.op.rule_status = rule_status

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_CLUB_INTERACTION_RULE_STATUS)

class StartEnsemble(Op):

    def __init__(self, ensemble_id):
        super().__init__(self)
        self.op = DistributorOps_pb2.StartEnsemble()
        self.op.ensemble_id = ensemble_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.START_ENSEMBLE)

class UpdateEnsemble(Op):

    def __init__(self, ensemble_id, sim_id, is_add):
        super().__init__(self)
        self.op = DistributorOps_pb2.UpdateEnsemble()
        self.op.ensemble_id = ensemble_id
        self.op.sim_id = sim_id
        if is_add:
            self.op.update_type = DistributorOps_pb2.UpdateEnsemble.ADD_MEMBER
        else:
            self.op.update_type = DistributorOps_pb2.UpdateEnsemble.REMOVE_MEMBER

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.UPDATE_ENSEMBLE)

class EndEnsemble(Op):

    def __init__(self, ensemble_id):
        super().__init__(self)
        self.op = DistributorOps_pb2.EndEnsemble()
        self.op.ensemble_id = ensemble_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.END_ENSEMBLE)

class CompositeThumbnail(Op):

    def __init__(self, thumbnail_url_source, composite_target, target_object, no_op_version, is_modded=False, force_rebuild_thumb=False, additional_composite_operations=None):
        super().__init__(self)
        self.op = DistributorOps_pb2.CompositeThumbnail()
        self.op.thumbnail_url_source = thumbnail_url_source
        self.op.composite_target = composite_target
        self.op.target_object = target_object
        self.op.no_op_version = no_op_version
        self.op.is_modded = is_modded
        self.op.force_rebuild_thumb = force_rebuild_thumb
        if additional_composite_operations is not None:
            self.op.additional_composite_operations.extend(additional_composite_operations)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.COMPOSITE_THUMBNAIL)

class CompositeImages(Op):

    def __init__(self, composite_target, composite_target_effect, target_object):
        super().__init__(self)
        self.op = DistributorOps_pb2.CompositeImages()
        self.op.composite_target = composite_target
        self.op.composite_target_effect = composite_target_effect
        self.op.target_object = target_object

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.COMPOSITE_IMAGES)

class GenerateMemorialPhoto(Op):

    def __init__(self, sim_id:'int') -> 'None':
        super().__init__(self)
        self.op = DistributorOps_pb2.GenerateMemorialPhoto()
        self.op.sim_id = sim_id

    def write(self, msg:'Operation') -> 'None':
        self.serialize_op(msg, self.op, protocol_constants.GENERATE_MEMORIAL_PHOTO)

class FollowRoute(Op):
    __slots__ = ('actor', 'path', 'start_time', 'mask_override')

    def __init__(self, actor, path, start_time, mask_override):
        super().__init__()
        self.actor = actor
        self.path = path
        self.start_time = start_time
        self.mask_override = mask_override

    def __repr__(self):
        return standard_repr(self, self.path.id)

    def write(self, msg):
        msg_src = distributor.ops.create_route_msg_src(self.path.nodes.id, self.actor, self.path, self.start_time, 0, track_override=None, mask_override=self.mask_override)
        self.serialize_op(msg, msg_src, protocol_constants.FOLLOW_ROUTE)

class SetScratched(Op):

    def __init__(self, is_scratched):
        super().__init__()
        self.is_scratched = is_scratched

    def __repr__(self):
        return standard_repr(self, self.is_scratched)

    def write(self, msg):
        op = DistributorOps_pb2.SetScratchedOverlay()
        if self.is_scratched is not None:
            op.enabled = self.is_scratched
        else:
            op.enabled = False
        self.serialize_op(msg, op, protocol_constants.SET_SCRATCHED_OVERLAY)

class SetLotDecorations(Op):

    def __init__(self, zone_id, decoration_type_id=None, preset_id=None, fade_in_time=None, fade_in_delay=None, fade_in_delay_variation=None):
        super().__init__()
        self.op = DistributorOps_pb2.SetLotDecorations()
        self.op.zone_id = zone_id
        if decoration_type_id is not None:
            self.op.holiday_id = decoration_type_id
        if preset_id is not None:
            self.op.preset_id = preset_id
        self.op.fade_in_time = fade_in_time
        self.op.fade_in_delay = fade_in_delay
        self.op.fade_in_delay_variation = fade_in_delay_variation

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_LOT_DECORATIONS)

class SetAllowFame(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetAllowFame()
        self.op.allow_fame = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ALLOW_FAME)

class SetAllowReputation(Op):

    def __init__(self, value):
        super().__init__()
        self.op = DistributorOps_pb2.SetAllowReputation()
        self.op.allow_reputation = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ALLOW_REPUTATION)

class DisplayHeadline(Op):

    def __init__(self, sim_info, headline, value, icon_modifier):
        super().__init__()
        self.op = DistributorOps_pb2.DisplayHeadline()
        self.op.sim_id = sim_info.sim_id
        self.op.headline_type = headline.guid64
        self.op.value = value
        if icon_modifier is not None:
            self.op.icon_modifier.type = icon_modifier.type
            self.op.icon_modifier.group = icon_modifier.group
            self.op.icon_modifier.instance = icon_modifier.instance

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.DISPLAY_HEADLINE)

class OwnedUniversityHousingLoad(Op):

    def __init__(self, zone_id):
        super().__init__()
        self.op = DistributorOps_pb2.OwnedUniversityHousingLoad()
        self.op.zone_id = zone_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.OWNED_UNIVERSITY_HOUSING_LOAD)

class SplitHouseholdDialog(Op):

    def __init__(self, source_household_id, target_household_id=0, cancelable=True, allow_sim_transfer=True, selected_sim_ids=[], destination_zone_id=0, callback_command_name=None, lock_preselected_sims=True):
        super().__init__()
        self.op = DistributorOps_pb2.SplitHouseholdDialog()
        self.op.source_household_id = source_household_id
        self.op.target_household_id = target_household_id
        self.op.cancelable = cancelable
        self.op.allow_sim_transfer = allow_sim_transfer
        self.op.selected_sim_ids.extend(selected_sim_ids)
        self.op.destination_zone_id = destination_zone_id
        self.op.lock_preselected_sims = lock_preselected_sims
        if callback_command_name is not None:
            self.op.callback_command_name = callback_command_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SPLIT_HOUSEHOLD_DIALOG)

class CommunityBoardDialog(Op):

    def __init__(self, provider, sim_info, target_id):
        super().__init__()
        self.op = ui_ops.CommunityBoardShow()
        provider.populate_community_board_op(sim_info, self.op, target_id)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.COMMUNITY_POLICY_BOARD)

class CommunityBoardAddPolicy(Op):

    def __init__(self, policy_tuple, sim_id, new_policy_allowed):
        super().__init__()
        self.op = ui_ops.CommunityBoardAddPolicy()
        self.op.sim_id = sim_id
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for policy_id in policy_tuple:
            policy = snippet_manager.get(policy_id)
            if policy is not None:
                with ProtocolBufferRollback(self.op.policies) as added_policy:
                    added_policy.policy_id = policy_id
                    stat = policy.vote_count_statistic
                    added_policy.count = 0
                    if stat is not None:
                        added_policy.max_count = stat.max_value
        self.op.new_policy_allowed = new_policy_allowed

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.COMMUNITY_POLICY_ADD_POLICY)

class CivicPolicyPanelUpdate(Op):

    def __init__(self, voting_open, repeal_policy_id, repeal_policy_sigs, schedule_text):
        super().__init__()
        self.op = DistributorOps_pb2.CivicPolicyPanelData()
        self.op.voting_open = voting_open
        self.op.repeal_policy_id = repeal_policy_id
        self.op.repeal_policy_sigs = repeal_policy_sigs
        if hasattr(self.op, 'schedule_text'):
            self.op.schedule_text = schedule_text

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.CIVIC_POLICY_PANEL_UPDATE)

class SendUIMessage(Op):

    def __init__(self, message_name):
        super().__init__()
        self.op = DistributorOps_pb2.SendUIMessage()
        self.op.message_name = message_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_UI_MESSAGE)

class ShowBillsPanel(Op):

    def __init__(self, utility_infos, line_items, due_bills_line_items):
        super().__init__()
        self.op = ui_ops.ShowBillsDialog()
        for utility_info in utility_infos:
            with ProtocolBufferRollback(self.op.utility_info) as utility_info_msg:
                utility_info_msg.utility = utility_info.utility
                utility_info_msg.cost = int(utility_info.cost)
                utility_info_msg.max_value = int(utility_info.max_value)
                utility_info_msg.current_value = int(utility_info.current_value)
                utility_info_msg.utility_name = utility_info.utility_name
                utility_info_msg.utility_symbol = utility_info.utility_symbol
                utility_info_msg.rate_of_change = utility_info.rate_of_change
                utility_info_msg.selling = utility_info.selling
        for line_item in line_items:
            with ProtocolBufferRollback(self.op.line_items) as line_item_msg:
                line_item_msg.amount = int(line_item.amount)
                line_item_msg.label = line_item.label
                if line_item.tooltip is not None:
                    line_item_msg.tooltip = line_item.tooltip
        for line_item in due_bills_line_items:
            with ProtocolBufferRollback(self.op.due_bills_line_items) as due_bills_line_item_msg:
                due_bills_line_item_msg.amount = int(line_item.amount)
                due_bills_line_item_msg.label = line_item.label
                if line_item.tooltip is not None:
                    due_bills_line_item_msg.tooltip = line_item.tooltip

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SHOW_BILLS_DIALOG)

class ShowSocialMediaPanel(Op):

    def __init__(self, sim_id, followers_count, feed_items, messages_items, is_update=False, has_new_posts=False, has_new_messages=False, can_make_context_post=False, can_add_new_contacts=True):
        super().__init__()
        self.op = ui_ops.ShowSocialMediaDialog()
        self.op.sim_id = sim_id
        self.op.followers_count = followers_count
        self.op.is_update = is_update
        self.op.has_new_posts = has_new_posts
        self.op.has_new_messages = has_new_messages
        self.op.can_make_context_post = can_make_context_post
        self.op.can_add_contacts = can_add_new_contacts
        for feed_item in feed_items:
            with ProtocolBufferRollback(self.op.feed_items) as feed_items_msg:
                feed_items_msg.post_id = feed_item.post_id
                feed_items_msg.author_sim_id = feed_item.author_sim_id
                feed_items_msg.target_sim_id = feed_item.target_sim_id if feed_item.target_sim_id is not None and feed_item.target_sim_id >= 0 else 0
                feed_items_msg.post_type = feed_item.post_type
                feed_items_msg.post_time = feed_item.post_time
                feed_items_msg.post_text = feed_item.post_text
                feed_items_msg.has_author_reacted = False
                for reaction in feed_item.reactions:
                    with ProtocolBufferRollback(feed_items_msg.reactions) as post_reaction_msg:
                        post_reaction_msg.narrative_type = reaction.narrative
                        post_reaction_msg.polarity_type = reaction.polarity
                        post_reaction_msg.count = reaction.count if reaction.count >= 0 else 0
                        post_reaction_msg.reacted_sims.extend(reaction.reacted_sims)
        for message_item in messages_items:
            with ProtocolBufferRollback(self.op.messages_items) as messages_items_msg:
                messages_items_msg.message_id = message_item.message_id
                messages_items_msg.message_post = self.build_dm_message(message_item.message_post)
                if message_item.reply_post is not None:
                    messages_items_msg.reply_post = self.build_dm_message(message_item.reply_post)

    def build_dm_message(self, dm_item):
        ret_dm_msg = UI_pb2.SocialMediaFeedItem()
        ret_dm_msg.post_id = dm_item.post_id
        ret_dm_msg.author_sim_id = dm_item.author_sim_id
        ret_dm_msg.target_sim_id = dm_item.target_sim_id if dm_item.target_sim_id is not None else 0
        ret_dm_msg.post_type = dm_item.post_type
        ret_dm_msg.post_time = dm_item.post_time
        ret_dm_msg.post_text = dm_item.post_text
        ret_dm_msg.has_author_reacted = False
        for reaction in dm_item.reactions:
            with ProtocolBufferRollback(ret_dm_msg.reactions) as dm_reaction_msg:
                dm_reaction_msg.narrative_type = reaction.narrative
                dm_reaction_msg.polarity_type = reaction.polarity
                dm_reaction_msg.count = reaction.count
                dm_reaction_msg.reacted_sims.extend(reaction.reacted_sims)
        return ret_dm_msg

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SHOW_SOCIAL_MEDIA_DIALOG)

class ShowMatchmakingDialog(Op):

    def __init__(self, sim_id:'int', trait_ids:'List[int]', selected_ages:'List[Age]', selected_traits_ids:'List[int]', cooldown_mins_left:'int', num_contact_actions:'int', list_mm_profiles:'List[MatchmakingProfile]', saved_profiles:'List[MatchmakingProfile]', max_save:'int', max_contact:'int', attracted_options:'List[Gender]', woohoo_options:'List[Gender]', res_key:'Key', min_download_count:'str', upload_time_range_start:'str', update_time_range_end:'str', bg_res_key:'Key', gallery_sims_enabled:'bool', gallery_sims_favorites_only_enabled:'bool', remote_ids_on_cooldown:'Set[str]', is_update:'bool'=False, is_traits_display_update:'bool'=False) -> 'None':
        super().__init__()
        self.op = ui_ops.ShowMatchmakingDialog()
        self.op.sim_id = sim_id
        self.op.trait_ids.extend(trait_ids)
        self.op.selected_ages.extend(selected_ages)
        self.op.selected_traits.extend(selected_traits_ids)
        self.op.cooldown_mins_left = cooldown_mins_left
        self.op.num_contact_actions = num_contact_actions
        self.op.max_save = max_save
        self.op.max_contact = max_contact
        self.op.is_update = is_update
        self.op.is_traits_display_update = is_traits_display_update
        self.op.attracted_options.extend(attracted_options)
        self.op.woohoo_options.extend(woohoo_options)
        self.op.min_download_count = min_download_count
        self.op.upload_time_range_start = upload_time_range_start
        self.op.update_time_range_end = update_time_range_end
        self.op.gallery_sims_enabled = gallery_sims_enabled
        self.op.gallery_sims_favorites_only_enabled = gallery_sims_favorites_only_enabled
        if hasattr(self.op, 'remote_ids_on_cooldown'):
            self.op.remote_ids_on_cooldown.extend(remote_ids_on_cooldown)
        if type(res_key) is sims4.resources.Key:
            proto_res_key = protocolbuffers.ResourceKey_pb2.ResourceKey()
            proto_res_key.type = res_key.type
            proto_res_key.group = res_key.group
            proto_res_key.instance = res_key.instance
            self.op.res_key = proto_res_key
        if res_key is not None and bg_res_key is not None:
            proto_res_key = protocolbuffers.ResourceKey_pb2.ResourceKey()
            proto_res_key.type = bg_res_key.type
            proto_res_key.group = bg_res_key.group
            proto_res_key.instance = bg_res_key.instance
            self.op.bg_res_key = proto_res_key
        for profile in list_mm_profiles:
            with ProtocolBufferRollback(self.op.profiles) as profiles_msg:
                profiles_msg.sim_id = profile.sim_id
                profiles_msg.region_name = profile.region_name
                profiles_msg.contacted = profile.contacted
                if hasattr(profiles_msg, 'rel_is_hidden'):
                    profiles_msg.rel_is_hidden = profile.rel_is_hidden
                profiles_msg.profile_type = profile.profile_type
                profiles_msg.thumbnail_url = profile.thumbnail_url
                profiles_msg.name = profile.first_name
                profiles_msg.real_sim_id = profile.real_sim_id
                profiles_msg.reported = profile.reported
                profiles_msg.pose_index = profile.pose_index
                if hasattr(profiles_msg, 'profile_bg_res_key'):
                    proto_res_key = protocolbuffers.ResourceKey_pb2.ResourceKey()
                    proto_res_key.type = profile.profile_bg_res_key.type
                    proto_res_key.group = profile.profile_bg_res_key.group
                    proto_res_key.instance = profile.profile_bg_res_key.instance
                    profiles_msg.profile_bg_res_key = proto_res_key
                for (trait_id, score) in profile.displayed_traits_map.items():
                    with ProtocolBufferRollback(profiles_msg.display_traits) as traits_score:
                        traits_score.trait_id = trait_id
                        traits_score.score = score
                if profile.profile_bg_res_key is not None and profile.is_gallery_profile:
                    profiles_msg.exchange_data_creator_name = profile.exchange_data_creator_name
                    profiles_msg.exchange_data_household_id = profile.exchange_data_household_id
                    profiles_msg.exchange_data_remote_id = profile.exchange_data_remote_id
                    profiles_msg.exchange_data_type = profile.exchange_data_type
        for profile in saved_profiles:
            with ProtocolBufferRollback(self.op.saved_profiles) as saved_profiles_msg:
                saved_profiles_msg.sim_id = profile.sim_id
                saved_profiles_msg.region_name = profile.region_name
                saved_profiles_msg.contacted = profile.contacted
                if hasattr(saved_profiles_msg, 'rel_is_hidden'):
                    saved_profiles_msg.rel_is_hidden = profile.rel_is_hidden
                saved_profiles_msg.profile_type = profile.profile_type
                saved_profiles_msg.thumbnail_url = profile.thumbnail_url
                saved_profiles_msg.name = profile.first_name
                saved_profiles_msg.real_sim_id = profile.real_sim_id
                saved_profiles_msg.reported = profile.reported
                saved_profiles_msg.pose_index = profile.pose_index
                if hasattr(saved_profiles_msg, 'profile_bg_res_key'):
                    proto_res_key = protocolbuffers.ResourceKey_pb2.ResourceKey()
                    proto_res_key.type = profile.profile_bg_res_key.type
                    proto_res_key.group = profile.profile_bg_res_key.group
                    proto_res_key.instance = profile.profile_bg_res_key.instance
                    saved_profiles_msg.profile_bg_res_key = proto_res_key
                for (trait_id, score) in profile.displayed_traits_map.items():
                    with ProtocolBufferRollback(saved_profiles_msg.display_traits) as traits_score:
                        traits_score.trait_id = trait_id
                        traits_score.score = score
                if profile.profile_bg_res_key is not None and profile.is_gallery_profile:
                    saved_profiles_msg.exchange_data_creator_name = profile.exchange_data_creator_name
                    saved_profiles_msg.exchange_data_household_id = profile.exchange_data_household_id
                    saved_profiles_msg.exchange_data_remote_id = profile.exchange_data_remote_id
                    saved_profiles_msg.exchange_data_type = profile.exchange_data_type

    def write(self, msg:'Operation'):
        self.serialize_op(msg, self.op, protocol_constants.SHOW_MATCHMAKING_DIALOG)

class ShowHorseCompetitionSelector(Op):

    def __init__(self, is_update:'bool', categories, mood_data, selected_sim_info:'SimInfo', selected_horse_sim_info:'SimInfo'):
        super().__init__()
        self.op = ui_ops.ShowHorseCompetitionSelector()
        self.op.is_update = is_update
        self.all_skills = set()
        self._build_skill_id_data(categories)
        self._build_competition_metadata(categories, selected_sim_info, selected_horse_sim_info)
        if selected_sim_info is not None:
            self.op.selected_sim = self._build_assignee_data(selected_sim_info, mood_data)
        if selected_horse_sim_info is not None:
            self.op.selected_horse = self._build_assignee_data(selected_horse_sim_info, mood_data)

    def _build_skill_id_data(self, categories):
        for category in categories:
            for competition in category.competitions:
                for sim_skill_requirement in competition.sim_skill_requirements:
                    self.all_skills.add(sim_skill_requirement.skill)
                for horse_skill_requirement in competition.horse_skill_requirements:
                    self.all_skills.add(horse_skill_requirement.skill)

    def _build_assignee_data(self, assignee:'SimInfo', mood_data):
        assignee_data = UI_pb2.HorseCompetitionAssigneeData()
        assignee_data.sim_id = assignee.sim_id
        assignee_data.mood_id = assignee.get_mood().guid64
        for (mood, loc) in mood_data.items():
            if mood.guid64 == assignee_data.mood_id:
                assignee_data.mood_tooltip = loc()
        assignee_data.mood_intensity = assignee.get_mood_intensity()
        for required_skill in self.all_skills:
            with ProtocolBufferRollback(assignee_data.skills) as skill:
                skill.skill_id = required_skill.guid64
                current_skill = assignee.get_stat_instance(required_skill)
                skill.level = current_skill.get_user_value() if current_skill is not None else 1
        return assignee_data

    def _build_competition_metadata(self, categories, sim:'SimInfo', horse:'SimInfo'):
        resolver = DoubleSimResolver(sim, horse)
        hc_service = services.get_horse_competition_service()
        horse_id = horse.sim_id if horse is not None else None
        for category in categories:
            for competition in category.competitions:
                competition_id = competition.guid64
                pretests = competition.prerequisite_tests
                tests = competition.availability_tests
                with ProtocolBufferRollback(self.op.competition_metadatas) as competition_metadata:
                    competition_metadata.competition_id = competition_id
                    competition_metadata.eligible_to_compete = True
                    if horse_id is None:
                        competition_metadata.has_placed_previously = False
                    else:
                        highest_placement = hc_service.try_get_highest_placement(horse_id, competition_id)
                        competition_metadata.has_placed_previously = hc_service.has_medaled(horse_id, competition_id)
                        if competition_metadata.has_placed_previously:
                            competition_metadata.highest_placement = highest_placement
                    if sim is None or horse is None:
                        continue
                    if pretests is not None:
                        result = pretests.run_tests(resolver, search_for_tooltip=True)
                        if tests is not None:
                            result = tests.run_tests(resolver, search_for_tooltip=True)
                        if not (result and result):
                            competition_metadata.eligible_to_compete = False
                            competition_metadata.not_eligible_reason = result.tooltip()

    def write(self, msg:'Operation'):
        self.serialize_op(msg, self.op, protocol_constants.SHOW_HORSE_COMPETITION_SELECTOR)

class ShowHorseCompetitionResults(Op):

    def __init__(self, sim:'SimInfo', horse:'SimInfo', competition:'HorseCompetition', placement:'int', unlocked_competition:'HorseCompetition'=None):
        super().__init__()
        self.op = ui_ops.ShowHorseCompetitionResults()
        self.op.sim_id = sim.sim_id
        self.op.horse_id = horse.sim_id
        self.op.competition_id = competition.guid64
        self.op.placement = placement
        self.op.unlocked_new_competition = unlocked_competition is not None
        if unlocked_competition is not None:
            self.op.unlocked_competition_id = unlocked_competition.guid64

    def write(self, msg:'Operation'):
        self.serialize_op(msg, self.op, protocol_constants.SHOW_HORSE_COMPETITION_RESULTS)

class TraitAtRiskUpdate(Op):

    def __init__(self, trait, at_risk):
        super().__init__()
        self.op = DistributorOps_pb2.SetTraitAtRiskState()
        self.op.trait_id = trait.guid64
        self.op.at_risk = at_risk

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_TRAIT_AT_RISK_STATE)

class ToggleSimInfoPanel(Op):

    def __init__(self, panel_type, stay_open):
        super().__init__()
        self.op = ui_ops.ToggleSimInfoPanel()
        self.op.panel_type = panel_type
        self.op.stay_open = stay_open

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.TOGGLE_SIM_INFO_PANEL)

class ScenarioGoalsUpdateOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SCENARIO_GOALS_UPDATE)

class ScenarioEndOp(Op):

    def __init__(self, protocol_msg):
        super().__init__()
        self.protocol_msg = protocol_msg

    def write(self, msg):
        self.serialize_op(msg, self.protocol_msg, protocol_constants.SCENARIO_END)

class PhoneNotificationOp(Op):

    def __init__(self, interaction_ids, sim_id):
        super().__init__()
        self.op = InteractionOps_pb2.PhoneNotificationUpdate()
        self.op.sim_id = sim_id
        if interaction_ids:
            self.op.interaction_ids.extend(interaction_ids)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SEND_PHONE_NOTIFICATION)

class TogglePhoneBadge(Op):

    def __init__(self, sim_id, has_notification):
        super().__init__()
        self.op = DistributorOps_pb2.TogglePhoneBadge()
        self.op.sim_id = sim_id
        self.op.has_notification = has_notification

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.TOGGLE_PHONE_BADGE)

class HorseValueUpdate(Op):

    def __init__(self, horse_sim_info, value):
        super().__init__()
        self.op = DistributorOps_pb2.HorseValueUpdate()
        self.op.sim_id = horse_sim_info.id
        self.op.value = value

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.HORSE_VALUE_UPDATE)

class RequestDaysPlayed(Op):

    def write(self, msg):
        msg.type = protocol_constants.REQUEST_DAYS_PLAYED

class PivotalMomentCompleted(Op):

    def __init__(self, pivotal_moment_id:'int', rewarded:'bool') -> 'None':
        super().__init__()
        self.op = DistributorOps_pb2.PivotalCompleted()
        self.op.pivotal_moment_id = pivotal_moment_id
        self.op.rewarded = rewarded

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.PIVOTAL_COMPLETED)

class RequestCompletedPivotalMoments(Op):

    def write(self, msg):
        msg.type = protocol_constants.REQUEST_COMPLETED_PIVOTAL_MOMENTS

class SwitchActiveHouseholdControl(Op):

    def __init__(self, sim_id:'int', zone_id:'int', household_id:'int', household_name:'str') -> 'None':
        super().__init__()
        self.op = DistributorOps_pb2.SwitchActiveHouseholdControl()
        self.op.sim_id = sim_id
        self.op.zone_id = zone_id
        self.op.household_id = household_id
        self.op.household_name = household_name

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SWITCH_ACTIVE_HOUSEHOLD_CONTROL)

class UpdateSkewerThumbnail(Op):

    def __init__(self, sim_id):
        super().__init__(self)
        self.op = DistributorOps_pb2.UpdateSkewerThumbnail()
        self.op.sim_id = sim_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.UPDATE_SKEWER_THUMBNAIL)

class RequestQuestEvents(Op):

    def write(self, msg):
        msg.type = protocol_constants.REQUEST_LIVE_QUEST_EVENTS_DATA

class QuestGoalComplete(Op):

    def __init__(self, quest_goal_id:'int', quest_id:'int', live_event_id:'int') -> 'None':
        super().__init__()
        self.op = Situations_pb2.QuestGoalUpdate()
        self.op.live_event_id = live_event_id
        self.op.situation_goal_id = quest_goal_id
        self.op.quest_id = quest_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.QUEST_GOAL_COMPLETE)

class QuestComplete(Op):

    def __init__(self, quest_id:'int', live_event_id:'int') -> 'None':
        super().__init__()
        self.op = Situations_pb2.QuestGoalUpdate()
        self.op.live_event_id = live_event_id
        self.op.quest_id = quest_id

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.QUEST_COMPLETE)

class ReincarnationCountUpdate(Op):

    def __init__(self, sim_id, reincarnation_count):
        super().__init__()
        self.op = DistributorOps_pb2.ReincarnationCountUpdate()
        self.op.sim_id = sim_id
        self.op.reincarnation_count = reincarnation_count

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.REINCARNATION_COUNT_UPDATE)

class GetAccountDataForCurrentUser(Op):

    def __init__(self, data_type:'int') -> 'None':
        super().__init__()
        self.op = DistributorOps_pb2.UserAccountData()
        self.op.data_type = data_type

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.GET_ACCOUNT_DATA_FOR_CURRENT_USER)

class SetAccountDataForCurrentUser(Op):

    def __init__(self, user_account_data) -> 'None':
        super().__init__()
        self.op = DistributorOps_pb2.UserAccountData()
        self.op.data_type = user_account_data.data_type
        self.op.data = user_account_data.data

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.SET_ACCOUNT_DATA_FOR_CURRENT_USER)

class TriggerUIFlyAway(Op):

    def __init__(self, sim_id, text, keyframeName, spawnPosition):
        super().__init__()
        self.op = DistributorOps_pb2.TriggerUIFlyAway()
        self.op.sim_id = sim_id
        self.op.localizedString = text
        self.op.keyframeName = keyframeName
        self.op.spawn_position = spawnPosition

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.TRIGGER_UI_FLYAWAY)

class TraitAppearanceUpdate(Op):

    def __init__(self, sim_id, trait_ids):
        super().__init__()
        self.op = DistributorOps_pb2.TraitAppearanceUpdate()
        self.op.sim_id = sim_id
        self.op.trait_ids.extend(trait_ids)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.TRAIT_APPEARANCE_UPDATE)

class GetGroupsForExperiments(Op):

    def __init__(self) -> 'None':
        super().__init__()
        self.op = DistributorOps_pb2.ExperimentNames()

    def add_experiment(self, experiment_name:'str') -> 'None':
        self.op.experiment_names.append(experiment_name)

    def write(self, msg):
        self.serialize_op(msg, self.op, protocol_constants.GET_GROUPS_FOR_EXPERIMENTS)

class SetPartsCustomTattoos(Op):

    def __init__(self, parts_custom_tattoos):
        super().__init__()
        self.parts_custom_tattoos = parts_custom_tattoos

    def write(self, msg):
        op = DistributorOps_pb2.SetPartsCustomTattoos()
        for (body_type, texture_id) in self.parts_custom_tattoos.items():
            part_custom_tattoo_data = op.parts_custom_tattoos.add()
            part_custom_tattoo_data.body_type = body_type
            part_custom_tattoo_data.texture_id = texture_id
        self.serialize_op(msg, op, protocol_constants.SET_PARTS_CUSTOM_TATTOOS)

class SetHouseholdInventoryRewards(Op):

    def __init__(self, reward_part_list):
        super().__init__()
        self.reward_part_list = reward_part_list

    def write(self, msg):
        op = DistributorOps_pb2.SetHouseholdInventoryRewards()
        op.reward_part_list.CopyFrom(self.reward_part_list)
        self.serialize_op(msg, op, protocol_constants.SET_HOUSEHOLD_INVENTORY_REWARDS)
