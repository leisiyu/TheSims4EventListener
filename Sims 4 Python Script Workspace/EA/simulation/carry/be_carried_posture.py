from postures.posture import Posturefrom postures.posture_animation_data import AnimationDataByActorAndTargetSpeciesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyimport sims4.loglogger = sims4.log.Logger('Carry', default_owner='amwu')
class BeCarriedPosture(Posture):
    INSTANCE_TUNABLES = {'_animation_data': AnimationDataByActorAndTargetSpecies.TunableFactory(tuning_group=GroupNames.ANIMATION)}

    @classmethod
    def get_animation_target_species(cls, species):
        return cls._animation_data.get_animation_target_species(species)

    @classproperty
    def is_be_carried_posture(cls):
        return True
lock_instance_tunables(BeCarriedPosture, _supports_carry=False)