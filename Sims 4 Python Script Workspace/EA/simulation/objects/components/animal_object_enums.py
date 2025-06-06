import servicesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom protocolbuffers import Animation_pb2, DistributorOps_pb2from animation.animation_constants import CreatureTypefrom animation.animation_controls import ProceduralControlSkatefrom distributor.ops import GenericProtocolBufferOpimport sims4.logfrom sims4.tuning.tunable import AutoFactoryInit, TunableTuple, HasTunableSingletonFactory, OptionalTunable, TunableReferencefrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import classpropertyfrom tag import TunableTagslogger = sims4.log.Logger('Animal Object Enums', default_owner='amwu')
class AnimalTypeBase(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'move_to_spawn_point_state_value': TunableReference(description='\n            State value to move the animal to the spawn point. Primary use \n            case is to get the animal out of the way when they are homeless\n            and invisible.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)), 'move_to_spawn_point_tags': OptionalTunable(description='\n            Spawn point tags to determine which spawn points to move the animal to. \n            ', tunable=TunableTags(filter_prefixes=('Spawn',)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classproperty
    def creature_type(cls):
        raise NotImplementedError

    def setup(self, owner):
        pass

class RabbitAnimalType(AnimalTypeBase):

    @classproperty
    def creature_type(cls):
        return CreatureType.Rabbit

class ChickenAnimalType(AnimalTypeBase):
    FACTORY_TUNABLES = {'terrain_control': TunableTuple(description='\n            Procedural control to send to client to allow chickens to align with terrain.\n            ', control_id=TunableStringHash32(description='\n                The control id. This string will be converted to a hash number and sent to client.\n                '), control=ProceduralControlSkate.TunableFactory(description='\n                Chickens will skate along terrain on defined platform.\n                ', locked_args={'terrain_alignment': True}))}

    def setup(self, owner):
        animation_data_msg = Animation_pb2.ProceduralAnimationData()
        terrain_ctrl = self.terrain_control
        with ProtocolBufferRollback(animation_data_msg.controls) as control_msg:
            control_msg.control_id = terrain_ctrl.control_id
            skate = terrain_ctrl.control()
            skate.build_control_msg(control_msg)
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SET_PROCEDURAL_ANIMATION_DATA, animation_data_msg)
        distributor.add_op(owner, op)

class RanchAnimalType(AnimalTypeBase):
    FACTORY_TUNABLES = {'terrain_control': TunableTuple(description='\n            Procedural control to send to client to allow ranch animals to align with terrain.\n            ', control_id=TunableStringHash32(description='\n                The control id. This string will be converted to a hash number and sent to client.\n                '), control=ProceduralControlSkate.TunableFactory(description='\n                Ranch animals will skate along terrain on defined platform.\n                ', locked_args={'terrain_alignment': True}))}

    def setup(self, owner):
        animation_data_msg = Animation_pb2.ProceduralAnimationData()
        terrain_ctrl = self.terrain_control
        with ProtocolBufferRollback(animation_data_msg.controls) as control_msg:
            control_msg.control_id = terrain_ctrl.control_id
            skate = terrain_ctrl.control()
            skate.build_control_msg(control_msg)
        distributor = Distributor.instance()
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.SET_PROCEDURAL_ANIMATION_DATA, animation_data_msg)
        distributor.add_op(owner, op)

class PenAnimalType(AnimalTypeBase):
    FACTORY_TUNABLES = {'locked_args': {'move_to_spawn_point_state_value': None, 'move_to_spawn_point_tags': None}}

class ChickAnimalType(ChickenAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Chick

class HenAnimalType(ChickenAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Hen

class RoosterAnimalType(ChickenAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Rooster

class CowAnimalType(PenAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Cow

class LlamaAnimalType(PenAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Llama

class GoatAnimalType(RanchAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Goat

class SheepAnimalType(RanchAnimalType):

    @classproperty
    def creature_type(cls):
        return CreatureType.Sheep

class CrowAnimalType(AnimalTypeBase):

    @classproperty
    def creature_type(cls):
        return CreatureType.Crow

    FACTORY_TUNABLES = {'locked_args': {'move_to_spawn_point_state_value': None, 'move_to_spawn_point_tags': None}}
