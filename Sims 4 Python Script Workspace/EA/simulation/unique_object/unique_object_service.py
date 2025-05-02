from __future__ import annotationsfrom objects.components import typesimport build_buyimport servicesfrom sims4.service_manager import Service
class UniqueObjectService(Service):

    def __init__(self):
        self._household_inventory_check_requested = False

    def mark_household_inventory_for_enforcement(self) -> 'None':
        self._household_inventory_check_requested = True

    def on_all_households_and_sim_infos_loaded(self, *_) -> 'None':
        self._enforce_uniqueness_on_household_inventory_objects()
        self._enforce_uniqueness_on_lot_objects()

    def on_build_buy_enter(self) -> 'None':
        if self._household_inventory_check_requested:
            self._enforce_uniqueness_on_household_inventory_objects()

    def _enforce_uniqueness_on_household_inventory_objects(self) -> 'None':
        try:
            household_id = services.active_household_id()
            if services.current_zone().lot.zone_owner_household_id != household_id or not build_buy.is_household_inventory_available(household_id):
                return
            object_ids = build_buy.get_object_ids_in_household_inventory(household_id)
            for object_id in object_ids:
                object_data = build_buy.get_object_data_from_household_inventory(object_id, household_id)
                if object_data is None:
                    pass
                else:
                    definition_id = build_buy.get_vetted_object_defn_guid(object_id, object_data.guid)
                    if definition_id is None:
                        pass
                    else:
                        definition = services.definition_manager().get(definition_id, obj_state=object_data.state_index)
                        if definition is None:
                            pass
                        else:
                            tuned_unique_object_component = definition.cls.tuned_components.unique_object_component
                            if tuned_unique_object_component is not None:
                                tuned_unique_object_component._tuned_values.unique_type.enforce_uniqueness(object_id=object_id, household_id=household_id)
        finally:
            self._household_inventory_check_requested = False

    def _enforce_uniqueness_on_lot_objects(self):
        for obj in services.object_manager().get_objects_with_component(types.UNIQUE_OBJECT_COMPONENT):
            obj.enforce_uniqueness()
        for obj in services.inventory_manager().get_objects_with_component(types.UNIQUE_OBJECT_COMPONENT):
            obj.enforce_uniqueness()
