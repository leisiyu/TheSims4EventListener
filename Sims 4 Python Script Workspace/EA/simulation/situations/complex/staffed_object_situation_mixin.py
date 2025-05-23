from event_testing.test_events import TestEventfrom interactions.utils.object_definition_or_tags import SituationObjectDefinitionsVariant, OBJECT_ID_SPECIFIEDfrom sims4.tuning.tunable import Tunableimport servicesimport sims4logger = sims4.log.Logger('Situations')
class StaffedObjectSituationMixin:
    INSTANCE_TUNABLES = {'_object_to_staff_filter': SituationObjectDefinitionsVariant(description='\n            Either a list of object definitions or tags that identify the type\n            of object the Sim in this situation will be staffing.\n            '), '_unowned_objects_only': Tunable(description="\n            If checked, objects are only valid if they are unowned.  For example,\n            if your Sim places down a yoga instruction mat, yoga instructors at a spa\n            venue can have this checked so they don't try to staff your instruction mat.\n            ", tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._staff_member = None
        self._staffed_object_id = None
        if self._seed.extra_kwargs is not None:
            self._object_to_staff_filter.object = self._seed.extra_kwargs.get('object_to_staff')
        self._registered_test_events = set()

    def start_situation(self):
        super().start_situation()
        self._register_test_event(TestEvent.ObjectDestroyed)

    def load_situation(self):
        if not super().load_situation():
            return False
        self._register_test_event(TestEvent.ObjectDestroyed)
        return True

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._staff_member = sim
        if not self.claim_object_to_staff():
            self._self_destruct()

    def get_employee_sim_info(self):
        if self._staff_member is not None:
            return self._staff_member.sim_info

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self._staffed_object)

    def _register_test_event(self, test_event):
        custom_key_tuple = (test_event, None)
        if custom_key_tuple in self._registered_test_events:
            return
        self._registered_test_events.add(custom_key_tuple)
        services.get_event_manager().register_single_event(self, test_event)

    def _test_event_unregister(self, test_event):
        custom_key_tuple = (test_event, None)
        if custom_key_tuple in self._registered_test_events:
            self._registered_test_events.remove(custom_key_tuple)
            services.get_event_manager().unregister_single_event(self, test_event)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj = resolver.get_resolved_arg('obj')
            staffed_object = self._staffed_object
            if staffed_object is not None and staffed_object.id == destroyed_obj.id:
                if services.current_zone().is_in_build_buy:
                    self._register_test_event(TestEvent.OnExitBuildBuy)
                else:
                    self._self_destruct()
                    self._staffed_object = None
        elif event == TestEvent.OnExitBuildBuy:
            self._test_event_unregister(TestEvent.OnExitBuildBuy)
            staffed_object = self._staffed_object
            if self._staffed_object_id is not None and staffed_object is None:
                self._staffed_object = None
                if not self.claim_object_to_staff():
                    self._self_destruct()
        super().handle_event(sim_info, event, resolver)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if sim is self._staff_member:
            self.release_claimed_staffed_object()
            self._staff_member = None

    def on_remove(self):
        self._test_event_unregister(TestEvent.ObjectDestroyed)
        super().on_remove()

    def _attempt_to_claim_object(self, obj):
        if self._unowned_objects_only and obj.household_owner_id:
            return False
        elif obj.objectrelationship_component.has_relationship(self._staff_member.id) or obj.objectrelationship_component.add_relationship(self._staff_member.id):
            self._staffed_object = obj
            return True
        return False

    def claim_object_to_staff(self):
        filter_item_set = self._object_to_staff_filter.get_item_set()
        staffed_object = self._staffed_object
        if staffed_object is not None and (filter_item_set and self._object_to_staff_filter.matches(staffed_object)) and self._attempt_to_claim_object(staffed_object):
            return True
        if not filter_item_set:
            return True
        for obj in services.object_manager().get_objects_with_filter_gen(self._object_to_staff_filter):
            if self._attempt_to_claim_object(obj):
                return True
        return False

    def get_staff_member(self):
        return self._staff_member

    @property
    def _staffed_object(self):
        if self._staffed_object_id is None:
            return
        return services.object_manager().get(self._staffed_object_id)

    @_staffed_object.setter
    def _staffed_object(self, obj):
        self._staffed_object_id = None if obj is None else obj.id

    def get_staffed_object(self):
        return self._staffed_object

    def release_claimed_staffed_object(self):
        staffed_object = self._staffed_object
        if staffed_object is not None and staffed_object.objectrelationship_component is not None:
            staffed_object.objectrelationship_component.remove_relationship(self._staff_member.id)
        self._staffed_object = None

    @classmethod
    def situation_meets_starting_requirements(cls, reserved_object_relationships=0, object_to_staff=None):
        if object_to_staff is not None and cls._object_to_staff_filter.get_filter_type() == OBJECT_ID_SPECIFIED:
            available_object_list = [object_to_staff]
        else:
            if not cls._object_to_staff_filter.get_item_set():
                return True
            available_object_list = list(services.object_manager().get_objects_with_filter_gen(cls._object_to_staff_filter))
        for obj in available_object_list:
            if obj.objectrelationship_component is None:
                logger.error("{} required object {} to staff but it doesn't have objectrelationship_component tuned", cls, obj)
            elif cls._unowned_objects_only and obj.household_owner_id:
                pass
            else:
                number_of_allowed_relationships = obj.objectrelationship_component.get_number_of_allowed_relationships()
                if number_of_allowed_relationships is None:
                    return True
                num_rels = len(obj.objectrelationship_component.relationships)
                available_relationships = number_of_allowed_relationships - num_rels
                if available_relationships > 0:
                    if available_relationships - reserved_object_relationships > 0:
                        return True
                    reserved_object_relationships -= available_relationships
        return False

    def sim_of_interest(self, sim_info):
        if self._staff_member is not None and self._staff_member.sim_info is sim_info:
            return True
        return False
