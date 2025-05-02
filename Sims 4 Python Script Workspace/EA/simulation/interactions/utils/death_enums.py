from sims4.tuning.dynamic_enum import DynamicEnumLockedimport random
class DeathType(DynamicEnumLocked, partitioned=True):
    NONE = 0

    @classmethod
    def get_random_death_type(cls):
        death_types = list(cls)[1:]
        return random.choice(death_types)
