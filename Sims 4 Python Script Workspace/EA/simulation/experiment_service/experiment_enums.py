from sims4.tuning.dynamic_enum import DynamicEnum
class ExperimentName(DynamicEnum):
    DEFAULT = 0

    def value_as_string(self) -> str:
        return str(self).split('.')[1]
