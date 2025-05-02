from __future__ import annotationsimport servicesimport sims4from event_testing.test_events import TestEventfrom objects.components import Component, componentmethod_with_fallbackfrom objects.components.stored_sim_info_component import StoredSimInfoComponentfrom objects.components.types import UNIQUE_OBJECT_COMPONENTfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, HasTunableSingletonFactory, TunableVariantfrom typing import TYPE_CHECKINGimport build_buyif TYPE_CHECKING:
    from objects.script_object import ScriptObject
    from sims.sim_info import SimInfo
    from typing import Optionallogger = sims4.log.Logger('UniqueObject', default_owner='cparrish')
class _DeathObjectBehavior(HasTunableSingletonFactory, AutoFactoryInit):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = None

    def on_add(self, owner):
        self.owner = owner
        services.get_event_manager().register(self, (TestEvent.StoredSimInfoComponentAdded, TestEvent.StoredSimInfoComponentLoaded))

    def handle_event(self, _, event:'TestEvent', resolver):
        obj = resolver.get_resolved_arg('obj')
        if obj != self.owner:
            return
        if event == TestEvent.StoredSimInfoComponentAdded:
            from_load = resolver.get_resolved_arg('from_load')
            if not from_load:
                sim_info = obj.get_stored_sim_info()
                sim_info.death_tracker.death_object_id = obj.id
                services.unique_object_service().mark_household_inventory_for_enforcement()
        elif event == TestEvent.StoredSimInfoComponentLoaded:
            self.enforce_uniqueness(obj=obj)

    @staticmethod
    def _get_stored_sim_info(obj:'Optional[ScriptObject]'=None, object_id:'Optional[int]'=None, household_id:'Optional[int]'=None) -> 'Optional[SimInfo]':
        if obj is not None:
            stored_sim_info = obj.get_stored_sim_info()
        else:
            object_data = build_buy.get_object_data_from_household_inventory(object_id, household_id)
            if object_data is None:
                logger.error('The object_data for {} is None', object_id)
                return
            stored_sim_id = StoredSimInfoComponent.get_stored_sim_id_from_object_data(object_data)
            stored_sim_info = services.sim_info_manager().get(stored_sim_id)
        return stored_sim_info

    def enforce_uniqueness(self, obj:'Optional[ScriptObject]'=None, object_id:'Optional[int]'=None, household_id:'Optional[int]'=None) -> 'bool':
        stored_sim_info = self._get_stored_sim_info(obj=obj, object_id=object_id, household_id=household_id)
        object_id = obj.id if obj is not None else object_id
        if stored_sim_info is not None:
            death_tracker = stored_sim_info.death_tracker
            if death_tracker.death_object_id == 0:
                death_tracker.death_object_id = object_id
            elif death_tracker.death_object_id != object_id:
                if obj is not None:
                    obj.destroy(source=self, cause='This is a duplicate Death Object.')
                else:
                    household = services.household_manager().get(household_id)
                    build_buy.remove_object_from_household_inventory(object_id, household)
                return False
        return True

class UniqueObjectComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=UNIQUE_OBJECT_COMPONENT):
    FACTORY_TUNABLES = {'unique_type': TunableVariant(description='\n            This is used to determine the behavior to use to measure and handle\n            uniqueness in this type of object.\n            ', default='invalid_type', locked_args={'invalid_type': None}, death_object=_DeathObjectBehavior.TunableFactory())}

    def on_add(self):
        self.unique_type.on_add(self.owner)

    @componentmethod_with_fallback(lambda : None)
    def enforce_uniqueness(self):
        self.unique_type.enforce_uniqueness(self.owner)
