from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *import inspectimport sims4.hash_utilimport sims4.logimport typeslogger = sims4.log.Logger('Tuning')INSTANCE_TUNABLES = 'INSTANCE_TUNABLES'REMOVE_INSTANCE_TUNABLES = 'REMOVE_INSTANCE_TUNABLES'TUNING_FILE_MODULE_NAME = 'sims4.tuning.class.instances'BASE_GAME_ONLY_ATTR = 'base_game_only'TUNING_ATTRIBUTES_REGISTRY = {}TUNING_ATTRIBUTES_REGISTRY_DYNAMIC = {}
class TuningBlueprintBase:
    pass

class TuningClassMixin:
    __slots__ = ()
    is_blueprint = False
    tuning_name = None
    tuning_blueprint = None

    def __repr__(self):
        if self.tuning_name is not None:
            return self.tuning_name
        else:
            return self.__class__.__name__
tuning_blueprint_dict = {}
def is_tuning_blueprint_attr(cls, attr_name:'str') -> 'bool':
    attr = getattr(cls, attr_name, None)
    if attr is not None:
        if isinstance(attr, property):
            return False
        elif isinstance(attr, types.FunctionType):
            attr_inspect = inspect.getattr_static(cls, attr_name, None)
            if isinstance(attr_inspect, types.FunctionType):
                return False
    return True

def create_tuning_blueprint_class(base_class):
    if base_class not in tuning_blueprint_dict:

        class TuningBlueprint(TuningBlueprintBase, base_class):
            __slots__ = ('tuning_name', 'resource_key', 'guid64')
            is_blueprint = True

            def __init__(self, name, *args, **kwargs):
                self.tuning_name = name
                self.resource_key = None
                self.guid64 = None

            def __setattr__(self, key, value):
                super().__setattr__(key, value)
                object_id = id(self)
                if object_id not in TUNING_ATTRIBUTES_REGISTRY_DYNAMIC:
                    TUNING_ATTRIBUTES_REGISTRY_DYNAMIC[object_id] = set()
                TUNING_ATTRIBUTES_REGISTRY_DYNAMIC[object_id].add(key)

            @property
            def __name__(self):
                return self.tuning_name

            @classmethod
            def get_parents(cls):
                parents = cls.mro()
                for (i, c) in enumerate(parents[1:], 1):
                    if isinstance(c, TunedInstanceMetaclass):
                        parents = parents[:i]
                        break
                return parents

            @classmethod
            def get_tunables(cls, ignore_tuned_instance_metaclass_subclasses=False):
                parents = cls.__mro__
                if ignore_tuned_instance_metaclass_subclasses:
                    i = 0
                    for c in parents:
                        if TunedInstanceMetaclass in c.__class__.__mro__:
                            parents = parents[:i]
                            break
                        i += 1
                tuning = {}
                for base_cls in parents[::-1]:
                    cls_vars = base_cls.__dict__
                    if REMOVE_INSTANCE_TUNABLES in cls_vars:
                        for key in cls_vars[REMOVE_INSTANCE_TUNABLES]:
                            try:
                                del tuning[key]
                            except:
                                pass
                    if INSTANCE_TUNABLES in cls_vars:
                        tuning.update(cls_vars[INSTANCE_TUNABLES])
                return tuning

            def init_blueprint(self, inst):
                inst.tuning_blueprint = self
                inst.guid64 = self.guid64
                object_id = id(self)

                def set_tuning_instance_attrs(keys):
                    for key in keys:
                        value = getattr(self, key, None)
                        setattr(inst, key, value)

                if object_id in TUNING_ATTRIBUTES_REGISTRY:
                    set_tuning_instance_attrs(TUNING_ATTRIBUTES_REGISTRY[object_id])
                if object_id in TUNING_ATTRIBUTES_REGISTRY_DYNAMIC:
                    set_tuning_instance_attrs(TUNING_ATTRIBUTES_REGISTRY_DYNAMIC[object_id])

            def __call__(self, *args, **kwargs):
                instance = base_class(*args, init_blueprint_func=self.init_blueprint, **kwargs)
                return instance

            @staticmethod
            def mro(*args, **kwargs):
                return base_class.mro(*args, **kwargs)

        tuning_blueprint_dict[base_class] = TuningBlueprint
    return tuning_blueprint_dict[base_class]

class TunedInstanceMetaclass(type):

    def __new__(cls, name, bases, *args, **kwargs):
        if 'manager' in kwargs:
            manager = kwargs.pop('manager')
        else:
            for base in bases:
                if isinstance(base, TunedInstanceMetaclass):
                    manager = base.tuning_manager
                    break
            manager = None
        if 'custom_module_name' in kwargs:
            cls.__module__ = kwargs.pop('custom_module_name')
        if BASE_GAME_ONLY_ATTR in kwargs:
            cls.base_game_only = kwargs.pop(BASE_GAME_ONLY_ATTR)
        tuned_instance = super().__new__(cls, name, bases, *args, **kwargs)
        tuned_instance.tuning_manager = manager
        if cls.__module__ != TUNING_FILE_MODULE_NAME:
            manager.register_class_template(tuned_instance)
        for (name, tunable) in tuned_instance.get_tunables(ignore_tuned_instance_metaclass_subclasses=True).items():
            setattr(tuned_instance, name, tunable.default)
        tuned_instance.reloadable = True
        return tuned_instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

    def get_parents(cls):
        parents = cls.mro()
        for (i, c) in enumerate(parents[1:], 1):
            if isinstance(c, TunedInstanceMetaclass):
                parents = parents[:i]
                break
        return parents

    def get_tunables(cls, ignore_tuned_instance_metaclass_subclasses=False):
        parents = cls.__mro__
        if ignore_tuned_instance_metaclass_subclasses:
            i = 0
            for c in parents:
                if TunedInstanceMetaclass in c.__class__.__mro__:
                    parents = parents[:i]
                    break
                i += 1
        tuning = {}
        for base_cls in parents[::-1]:
            cls_vars = base_cls.__dict__
            if REMOVE_INSTANCE_TUNABLES in cls_vars:
                for key in cls_vars[REMOVE_INSTANCE_TUNABLES]:
                    try:
                        del tuning[key]
                    except:
                        pass
            if INSTANCE_TUNABLES in cls_vars:
                tuning.update(cls_vars[INSTANCE_TUNABLES])
        return tuning

    def get_invalid_removals(cls):
        tuning = None
        parents = cls.mro()
        valid_remove = set()
        missing_remove = set()
        for base_cls in reversed(parents):
            cls_vars = vars(base_cls)
            if REMOVE_INSTANCE_TUNABLES in cls_vars:
                remove_instance_tunables = cls_vars[REMOVE_INSTANCE_TUNABLES]
                for key in remove_instance_tunables:
                    if key in tuning:
                        del tuning[key]
                        valid_remove.add(key)
                    elif tuning is not None:
                        missing_remove.add(key)
            if INSTANCE_TUNABLES in cls_vars:
                instance_tunables = cls_vars[INSTANCE_TUNABLES]
                if tuning is None:
                    tuning = {}
                tuning.update(instance_tunables)
        return missing_remove - valid_remove

    def get_removed_tunable_names(cls):
        removed_tuning = []
        for base_cls in cls.get_parents():
            cls_vars = vars(base_cls)
            if isinstance(base_cls, TunedInstanceMetaclass) and base_cls is not cls:
                return removed_tuning
            if REMOVE_INSTANCE_TUNABLES in cls_vars:
                remove_instance_tunables = cls_vars[REMOVE_INSTANCE_TUNABLES]
                for key in remove_instance_tunables:
                    removed_tuning.append(key)
        return removed_tuning

    def get_base_game_only(cls):
        base_game_only = getattr(cls, BASE_GAME_ONLY_ATTR, None)
        if base_game_only is None:
            base_game_only = cls.tuning_manager.base_game_only
        return base_game_only

    def add_tunable_to_instance(cls, tunable_name, tunable):
        cls_vars = vars(cls)
        if INSTANCE_TUNABLES in cls_vars:
            cls_vars[INSTANCE_TUNABLES][tunable_name] = tunable
        else:
            setattr(cls, INSTANCE_TUNABLES, {tunable_name: tunable})
        setattr(cls, tunable_name, tunable.default)

    def generate_tuned_type(cls, name, *args, **kwargs):
        tuning_class_instance = type(cls)(name, (cls,), {}, custom_module_name=TUNING_FILE_MODULE_NAME)
        return tuning_class_instance

    def generate_tuned_type_instanced_class(cls, name, *args, **kwargs):
        tuning_blueprint_class = create_tuning_blueprint_class(cls)
        tuning_blueprint = tuning_blueprint_class(name)
        for (name, tunable) in tuning_blueprint.get_tunables(ignore_tuned_instance_metaclass_subclasses=True).items():
            setattr(tuning_blueprint, name, tunable.default)
        tuning_blueprint.reloadable = True
        return tuning_blueprint

class HashedTunedInstanceMetaclass(TunedInstanceMetaclass):

    @staticmethod
    def assign_guid(tuning_inst, name):
        tuning_inst.guid = sims4.hash_util.hash32(name)
        if not tuning_inst.tuning_manager.use_guid_for_ref:
            tuning_inst.guid64 = sims4.hash_util.hash64(name)
        return tuning_inst

    def generate_tuned_type(cls, name, *args, **kwargs):
        inst = super().generate_tuned_type(name, *args, **kwargs)
        cls.assign_guid(inst, name)
        return inst

    def generate_tuned_type_instanced_class(cls, name, *args, **kwargs):
        inst = super().generate_tuned_type_instanced_class(name, *args, **kwargs)
        cls.assign_guid(inst, name)
        return inst

def lock_instance_tunables(cls, **kwargs):
    for (key, value) in kwargs.items():
        setattr(cls, key, value)
    remove_tunables = set(cls.__dict__.get(REMOVE_INSTANCE_TUNABLES, ()))
    remove_tunables.update(kwargs.keys())
    setattr(cls, REMOVE_INSTANCE_TUNABLES, remove_tunables)

def prohibits_instantiation(cls):
    return vars(cls).get('INSTANCE_SUBCLASSES_ONLY', False)
