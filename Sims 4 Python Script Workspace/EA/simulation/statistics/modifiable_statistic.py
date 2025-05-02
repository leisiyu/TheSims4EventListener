from caches import cachedfrom event_testing.resolver import SingleSimResolverfrom sims4.utils import flexmethodfrom statistics.statistic import Statisticfrom tunable_multiplier import TunableMultiplier, TestedSum
class ModifiableStatistic(Statistic):
    INSTANCE_TUNABLES = {'tunable_addends': TestedSum.TunableFactory(description="\n            List of modifiers that add to the Sim's base value. Applied before multipliers.\n            "), 'tunable_multipliers': TunableMultiplier.TunableFactory(description="\n            List of modifiers that multiply the total of the Sim's base and added values. Applied after addends.\n            ")}

    @flexmethod
    @cached
    def get_value(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        resolver = SingleSimResolver(inst_or_cls._tracker.owner)
        return (inst_or_cls.initial_value + inst_or_cls.tunable_addends.get_modified_value(resolver))*inst_or_cls.tunable_multipliers.get_multiplier(resolver)
