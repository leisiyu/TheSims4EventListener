from sims4.tuning.instance_manager import InstanceManagerfrom sims4.utils import classproperty
class InstancedClassManager(InstanceManager):

    @classproperty
    def is_instanced_class_tuning_manager(cls):
        return True
