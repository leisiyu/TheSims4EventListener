import operatorimport servicesfrom objects.components import Componentfrom sims4.tuning.tunable import TunableSet, TunableReferenceimport objects.components.typesimport sims4
class NewObjectTuning:
    NEW_OBJECT_COMMODITY = TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity',))
    NEW_OBJECT_AFFORDANCES = TunableSet(description='\n        Affordances available on an object as long as its considered as new.\n        ', tunable=TunableReference(description='\n            Affordance reference to add to new objects.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True))

class NewObjectComponent(Component, component_name=objects.components.types.NEW_OBJECT_COMPONENT, allow_dynamic=True):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialize_commodity()
        self.owner.is_new_object = True

    def _initialize_commodity(self):
        new_object_commodity = self.owner.commodity_tracker.add_statistic(NewObjectTuning.NEW_OBJECT_COMMODITY)
        threshold = sims4.math.Threshold(new_object_commodity.min_value, operator.le)
        self._commodity_listener = self.owner.commodity_tracker.create_and_add_listener(NewObjectTuning.NEW_OBJECT_COMMODITY.stat_type, threshold, self._new_object_expired)

    def component_super_affordances_gen(self, **kwargs):
        if not self.owner.is_new_object:
            return
        yield from NewObjectTuning.NEW_OBJECT_AFFORDANCES

    def _new_object_expired(self, stat):
        self.owner.is_new_object = False
        self.owner.commodity_tracker.remove_listener(self._commodity_listener)
        self.owner.remove_component(objects.components.types.NEW_OBJECT_COMPONENT)

    def on_add(self, *_, **__):
        self.owner.update_component_commodity_flags()

    def on_remove(self, *_, **__):
        self.owner.update_component_commodity_flags()
        if self._commodity_listener is None:
            return
        self.owner.commodity_tracker.remove_listener(self._commodity_listener)
        self._commodity_listener = None
