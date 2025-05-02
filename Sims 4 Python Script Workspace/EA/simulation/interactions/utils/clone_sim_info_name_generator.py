from sims.sim_spawner import SimSpawnerfrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableVariantfrom sims4.tuning.tunable import AutoFactoryInit
class CloneSimInfoNameGeneratorBase(HasTunableSingletonFactory, AutoFactoryInit):

    def get_first_name(self, source_sim_info):
        pass

    def get_last_name(self, source_sim_info):
        pass

class CloneSimInfoFromSourceNameGenerator(CloneSimInfoNameGeneratorBase):

    def get_first_name(self, source_sim_info):
        return source_sim_info._base.first_name

    def get_last_name(self, source_sim_info):
        return source_sim_info._base.last_name

class CloneSimInfoRandomNameGenerator(CloneSimInfoNameGeneratorBase):

    def get_first_name(self, source_sim_info):
        return SimSpawner.get_random_first_name(source_sim_info.gender, source_sim_info.species)

    def get_last_name(self, source_sim_info):
        return SimSpawner.get_random_last_name(source_sim_info.gender, source_sim_info.species)

class TunableCloneSimInfoNameGeneratorVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, random=CloneSimInfoRandomNameGenerator.TunableFactory(), from_source=CloneSimInfoFromSourceNameGenerator.TunableFactory(), **kwargs)
