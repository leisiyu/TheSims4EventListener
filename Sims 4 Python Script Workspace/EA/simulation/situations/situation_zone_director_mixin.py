import servicesimport sims4from sims4.tuning.tunable import TunableReference
class SituationZoneDirectorMixin:
    INSTANCE_TUNABLES = {'_zone_director': TunableReference(description='\n            This zone director will automatically be requested by the situation\n            during zone spin up.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR), class_restrictions=('ZoneDirectorBase',))}

    @classmethod
    def get_zone_director_request(cls, host_sim_info=None, zone_id=None):
        return (cls._zone_director(), cls._get_zone_director_request_type())

    @classmethod
    def _get_zone_director_request_type(cls):
        raise NotImplementedError
