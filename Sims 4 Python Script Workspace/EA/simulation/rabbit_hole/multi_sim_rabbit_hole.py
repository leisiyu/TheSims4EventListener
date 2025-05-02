from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfo
    from GameplaySaveData_pb2 import RabbitHoleData
    from event_testing.resolver import Resolverfrom event_testing.resolver import DoubleSimResolverfrom interactions import ParticipantTypefrom rabbit_hole.rabbit_hole import RabbitHolefrom sims4.utils import flexmethodimport servicesimport sims4.logfrom sims4.tuning.tunable import TunableSet, TunableEnumEntrylogger = sims4.log.Logger('Multi Sim Rabbit Hole', default_owner='mjuskelis')
class MultiSimRabbitHoleBase(RabbitHole):
    INSTANCE_SUBCLASSES_ONLY = True

    def __init__(self, *args, participant_sim_ids:'Set[int]'=None, **kwargs) -> 'None':
        self._participant_sim_ids = participant_sim_ids
        logger.assert_raise(len(participant_sim_ids) > 0, 'Not enough sims to initialize multi sim rabbit hole.')
        super().__init__(*args, sim_id=self._participant_sim_ids[0], **kwargs)

    def get_participant_index(self, participant_type:'ParticipantType') -> 'Optional[int]':
        raise NotImplementedError

    def get_loot_resolver(self) -> 'Resolver':
        raise NotImplementedError

    def get_all_sim_ids_registered_for_rabbit_hole(self) -> 'Set[int]':
        return self._participant_sim_ids

    def _get_sim_infos_by_participant_type(self, participant_type:'ParticipantType') -> 'Optional[Tuple[SimInfo]]':
        if participant_type == ParticipantType.All:
            return tuple(services.sim_info_manager().get(sim_id) for sim_id in self._participant_sim_ids)
        possible_index = self.get_participant_index(participant_type)
        if possible_index is None:
            return
        return (services.sim_info_manager().get(self._participant_sim_ids[possible_index]),)

    def contains_sim_id(self, sim_id:'int') -> 'bool':
        return sim_id in self._participant_sim_ids

    @flexmethod
    def get_participants(cls, inst, participant_type:'ParticipantType', *args, **kwargs) -> 'Optional[Tuple[SimInfo]]':
        parent_result = super(__class__, inst if inst is not None else cls).get_participants(participant_type, *args, **kwargs)
        if parent_result:
            return parent_result
        elif inst:
            return inst._get_sim_infos_by_participant_type(participant_type)

    def save(self, rabbit_hole_data:'RabbitHoleData') -> 'None':
        super().save(rabbit_hole_data)
        for sim_id in self._participant_sim_ids:
            rabbit_hole_data.all_participant_sim_ids.append(sim_id)

    @classmethod
    def init_from_load(cls, rabbit_hole_data:'RabbitHoleData'):
        return cls(participant_sim_ids=rabbit_hole_data.all_participant_sim_ids, rabbit_hole_id=rabbit_hole_data.rabbit_hole_instance_id)

class TwoSimRabbitHole(MultiSimRabbitHoleBase):
    INSTANCE_TUNABLES = {'first_participant_types': TunableSet(description='\n            The participant types that should map to the first sim.\n            \n            Note: The first participant will always map to actor, so it is not needed here.\n            ', tunable=TunableEnumEntry(description='\n                A participant type that should map to the first sim.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor)), 'second_participant_types': TunableSet(description='\n            The participant types that should map to the second sim.\n            ', tunable=TunableEnumEntry(description='\n                A participant type that should map to the second sim.\n                ', tunable_type=ParticipantType, default=ParticipantType.TargetSim))}

    def get_loot_resolver(self) -> 'Resolver':
        return DoubleSimResolver(services.sim_info_manager().get(self._participant_sim_ids[0]), services.sim_info_manager().get(self._participant_sim_ids[1]))

    def get_participant_index(self, participant_type:'ParticipantType') -> 'Optional[int]':
        if participant_type in self.first_participant_types:
            return 0
        elif participant_type in self.second_participant_types:
            return 1
