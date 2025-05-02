import servicesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import send_relationship_op, build_icon_info_msg, IconInfoDatafrom protocolbuffers import Commodities_pb2 as commodity_protocolfrom relationships.relationship_objects.relationship import Relationship, loggerfrom sims4.localization import LocalizationHelperTuningfrom sims4.utils import classproperty
class ObjectRelationship(Relationship):
    __slots__ = ('_target_object_id', '_target_object_manager_id', '_target_object_instance_id', '_object_relationship_name')

    def __init__(self, sim_id:int, obj_def_id:int):
        self._sim_id_a = sim_id
        self._sim_id_b = obj_def_id
        self._target_object_id = 0
        self._target_object_manager_id = 0
        self._target_object_instance_id = 0
        self._object_relationship_name = None
        super().__init__()

    @classproperty
    def is_object_rel(cls):
        return True

    def save_relationship(self, relationship_msg):
        super().save_relationship(relationship_msg)
        relationship_msg.target_object_id = self._target_object_id
        relationship_msg.target_object_manager_id = self._target_object_manager_id
        relationship_msg.target_object_instance_id = self._target_object_instance_id
        if self._object_relationship_name is not None:
            relationship_msg.object_relationship_name = self._object_relationship_name

    def load_relationship(self, relationship_msg):
        super().load_relationship(relationship_msg)
        self._target_object_id = relationship_msg.target_object_id
        self._target_object_manager_id = relationship_msg.target_object_manager_id
        self._target_object_instance_id = relationship_msg.target_object_instance_id
        if relationship_msg.object_relationship_name:
            self._object_relationship_name = relationship_msg.object_relationship_name

    def get_object_rel_name(self):
        return self._object_relationship_name

    def set_object_rel_name(self, name):
        self._object_relationship_name = name

    def send_relationship_info(self, deltas=None, headline_icon_modifier=None, send_npc_relationship=False):
        if self.suppress_client_updates:
            return
        sim_info_a = self.find_sim_info_a()
        if sim_info_a is not None and sim_info_a.is_npc:
            return
        if sim_info_a is not None:
            op = self._build_object_relationship_update_proto(sim_info_a, self._sim_id_b, deltas=deltas, name_override=self.get_object_rel_name())
            if op is not None:
                send_relationship_op(sim_info_a, op)

    def _build_object_relationship_update_proto(self, actor_sim_info, member_obj_def_id, deltas=None, name_override=None):
        msg = commodity_protocol.RelationshipUpdate()
        actor_sim_id = actor_sim_info.sim_id
        msg.actor_sim_id = actor_sim_id
        msg.hidden = self.is_hidden
        if name_override is not None:
            loc_custom_name = LocalizationHelperTuning.get_raw_text(name_override)
            build_icon_info_msg(IconInfoData(), loc_custom_name, msg.target_icon_override)
        if self._target_object_id == 0:
            target_object = None
            tag_set = services.relationship_service().get_mapped_tag_set_of_id(member_obj_def_id)
            definition_ids = services.relationship_service().get_ids_of_tag_set(tag_set)
            for definition_id in definition_ids:
                for obj in services.object_manager().objects:
                    if definition_id == obj.definition.id:
                        target_object = obj
                        break
            if target_object is None:
                logger.error('Failed to find an object with requested object tag set in the world,                             so the initial object type relationship creation for sim {} will not complete.', actor_sim_info)
                return
            (msg.target_id.object_id, msg.target_id.manager_id) = target_object.icon_info
            msg.target_instance_id = target_object.id
            self._target_object_id = msg.target_id.object_id
            self._target_object_manager_id = msg.target_id.manager_id
            self._target_object_instance_id = msg.target_instance_id
        else:
            msg.target_id.object_id = self._target_object_id
            msg.target_id.manager_id = self._target_object_manager_id
            msg.target_instance_id = self._target_object_instance_id
        msg.last_update_time = self._last_update_time
        track_bits = self._build_relationship_track_proto(actor_sim_id, msg)
        self._build_relationship_bit_proto(actor_sim_id, track_bits, msg)
        return msg

    def _build_relationship_bit_proto(self, actor_sim_id, track_bits, msg):
        for bit in self.get_bit_instances(actor_sim_id):
            if bit.visible or not bit.invisible_filterable:
                pass
            elif bit.guid64 in track_bits:
                pass
            else:
                with ProtocolBufferRollback(msg.bit_updates) as bit_update:
                    bit_update.bit_id = bit.guid64
