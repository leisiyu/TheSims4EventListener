from __future__ import annotationsfrom _collections import dequefrom collections import namedtupleimport operatorfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from objects.game_object import GameObject
    from sims.sim_info import SimInfo
    from role.role_state import RoleState
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from situations.situation_job import SituationJob
    from typing import *from build_buy import get_object_placement_flags, HouseholdInventoryFlags, PlacementFlagsfrom default_property_stream_reader import DefaultPropertyStreamReaderfrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom objects.object_enums import ItemLocationfrom objects.system import create_objectfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableList, TunableEnumEntry, TunableRangefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, CommonInteractionCompletedSituationState, SituationStateData, SituationStatefrom situations.effect_triggering_situation_state import CustomStatesSituationTriggerDataTestVariantfrom ui.ui_dialog_notification import UiDialogNotificationimport build_buyimport protocolbuffers.FileSerialization_pb2 as file_serializationimport servicesimport sims4.logimport randomimport telemetry_helperlogger = sims4.log.Logger('BurglarSituation', default_owner='mmikolajczyk')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_START_SITUATION = 'STAS'TELEMETRY_HOOK_STOP_SITUATION = 'STOS'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)
class _WaitForBurglarState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self._change_state(self.owner.find_object_state())

class _FindObjectState(CommonSituationState):

    def on_activate(self, reader:'DefaultPropertyStreamReader'=None) -> 'None':
        super().on_activate(reader=reader)
        current_object = None
        while self.owner.objects_to_steal:
            obj_count = len(self.owner.objects_to_steal)
            max_index = self.owner.max_best_object_to_randomize if self.owner.max_best_object_to_randomize < obj_count else obj_count - 1
            obj_id = self.owner.objects_to_steal.pop(random.randint(0, max_index))[0]
            obj = services.object_manager().get(obj_id)
            if obj is not None and obj.depreciated_value + self.owner.total_stolen_value > self.owner.max_money_amount:
                pass
            elif not obj.self_or_part_in_use:
                current_object = obj
                break
        if current_object is not None:
            self.owner.set_current_object(current_object)
            self._change_state(self.owner.idle_at_object_state())
        else:
            self._change_state(self.owner.leave_state())

    def timer_expired(self) -> 'None':
        self._change_state(self.owner.find_object_state())

class _IdleAtObjectState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        self._change_state(self.owner.steal_object_state())

    def timer_expired(self) -> 'None':
        self._change_state(self.owner.find_object_state())

class _StealObjectState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs) -> 'None':
        obj = services.object_manager(services.current_zone_id()).get(self.owner.current_object.id)
        object_list = file_serialization.ObjectList()
        object_data = obj.save_object(object_list.objects)
        name = obj.custom_name if obj.has_custom_name() else LocalizationHelperTuning.get_object_name(obj.definition)
        commodities = obj.commodity_tracker.get_all_commodities()
        for commodity in commodities:
            commodity.stop_regular_simulation()
        self.owner.stolen_objects_data.append(self.owner.stolen_object_data(object_name=name, guid=object_data.guid, game_data=object_data, commodities=commodities))
        self.owner.total_stolen_value += self.owner.current_object.depreciated_value
        self.owner.clear_current_object()
        self.owner.on_object_stolen()

    def timer_expired(self) -> 'None':
        self._change_state(self.owner.find_object_state())

class _HoldingState(CommonSituationState):

    def timer_expired(self) -> 'None':
        self._change_state(self.owner.leave_state())

class _LeaveState(CommonSituationState):
    pass

class _SadLeaveState(CommonSituationState):
    pass

class BurglarSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'burglar_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the burglar.\n            ', tuning_group=GroupNames.ROLES), 'max_money_amount': Tunable(description='\n            Tuning that determines the simoleon amount the burglar might steal.\n            ', tunable_type=float, default=1000, tuning_group=GroupNames.SITUATION), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip to show when the player tries to save the game while\n            this situation is running. The save is locked when the situation\n            starts.\n            ', tuning_group=GroupNames.SITUATION), 'wait_for_burglar_state': _WaitForBurglarState.TunableFactory(description='\n            The state where the situation waits for burglar to spawn and finish spawning interaction.\n            ', display_name='1. Wait For Burglar Spawn', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'find_object_state': _FindObjectState.TunableFactory(description='\n            The state that picks an object for the burglar to steal.\n            ', display_name='2. Find Object State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'idle_at_object_state': _IdleAtObjectState.TunableFactory(description='\n            The state at which the burglar waits near the picked object\n            and can be interrupted.\n            ', display_name='3. Idle At Object State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'steal_object_state': _StealObjectState.TunableFactory(description='\n            The state at which the burglar will steal the picked object.\n            ', display_name='4. Steal Object State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'holding_state': _HoldingState.TunableFactory(description='\n            The state at which the burglar is waiting for action from outside influence.\n            ', display_name='5. Holding State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _LeaveState.TunableFactory(description='\n            The state at which the burglar leaves the lot with the stolen items.\n            ', display_name='6. Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'sad_leave_state': _SadLeaveState.TunableFactory(description='\n            The state at which the burglar leaves the lot after being stopped.\n            ', display_name='6b. Sad Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'valid_object_tests': TunableTestSet(description='\n            Test set that determines if an object on the lot is valid to be\n            stolen.\n            ', tuning_group=GroupNames.SITUATION), 'maximum_objects_to_steal': TunableRange(description='\n            The total maximum objects that the situation will take.\n            ', tunable_type=int, default=1, minimum=1, tuning_group=GroupNames.SITUATION), 'max_best_object_to_randomize': Tunable(description='\n            The amount of best objects to randomize the object to be stolen from.\n            ', tunable_type=int, default=5, tuning_group=GroupNames.SITUATION), 'return_objects_event': TunableEnumEntry(description='\n            The event that triggers the burglar returning stolen items to household inventory.\n            ', tunable_type=TestEvent, default=TestEvent.Invalid, invalid_enums=(TestEvent.Invalid,), tuning_group=GroupNames.SITUATION), 'objects_returned_tns': UiDialogNotification.TunableFactory(description='\n            TNS showing a list of returned items when burglar is not successful.\n            ', tuning_group=GroupNames.SITUATION), 'objects_stolen_tns': UiDialogNotification.TunableFactory(description='\n            TNS showing a list of stolen items when burglar is successful.\n            ', tuning_group=GroupNames.SITUATION), 'objects_returned_loot': TunableList(description='\n            A list of loot operations to apply when the objects are returned to the\n            owner.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), tuning_group=GroupNames.SITUATION), 'objects_stolen_loot': TunableList(description='\n            A list of loot operations to apply when the objects are stolen.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), tuning_group=GroupNames.SITUATION), 'situation_start_loot': TunableList(description='\n            A list of loot operations to apply at the start of the situation.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), tuning_group=GroupNames.SITUATION), 'situation_end_loot': TunableList(description='\n            A list of loot operations to apply at the end of the situation.\n            ', tunable=sims4.tuning.tunable.TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), tuning_group=GroupNames.SITUATION), 'triggers_holding': TunableList(description='\n            The events that will trigger a change to the holding state.\n            ', tunable=CustomStatesSituationTriggerDataTestVariant(), tuning_group=GroupNames.SITUATION), 'triggers_leave': TunableList(description='\n            The events that will trigger a change to the leave state.\n            ', tunable=CustomStatesSituationTriggerDataTestVariant(), tuning_group=GroupNames.SITUATION), 'triggers_sad_leave': TunableList(description='\n            The events that will trigger a change to the holding state.\n            ', tunable=CustomStatesSituationTriggerDataTestVariant(), tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self.objects_to_steal = []
        self.stolen_object_data = namedtuple('StolenObjectData', ['object_name', 'guid', 'game_data', 'commodities'])
        self.stolen_objects_data = []
        self.current_object = None
        self._reservation_handler = None
        self._objects_stolen = 0
        self.total_stolen_value = 0
        event_manager = services.get_event_manager()
        event_manager.register_single_event(self, self.return_objects_event)
        event_manager.register_tests(self, self.triggers_holding)
        event_manager.register_tests(self, self.triggers_leave)
        event_manager.register_tests(self, self.triggers_sad_leave)
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_START_SITUATION) as hook:
            hook.write_guid('type', self.guid64)

    @classmethod
    def _states(cls) -> 'Tuple[SituationStateData, ...]':
        return (SituationStateData(1, _WaitForBurglarState, factory=cls.wait_for_burglar_state), SituationStateData(2, _FindObjectState, factory=cls.find_object_state), SituationStateData(3, _IdleAtObjectState, factory=cls.idle_at_object_state), SituationStateData(4, _StealObjectState, factory=cls.steal_object_state), SituationStateData(5, _HoldingState, factory=cls.holding_state), SituationStateData(6, _LeaveState, factory=cls.leave_state), SituationStateData(7, _SadLeaveState, factory=cls.sad_leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls) -> 'List[Tuple[SituationJob, RoleState]]':
        return [(cls.burglar_job_and_role_state.job, cls.burglar_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls) -> 'Optional[SituationJob]':
        pass

    def burglar(self) -> 'Optional[Sim]':
        return next(self.all_sims_in_job_gen(self.burglar_job_and_role_state.job), None)

    def handle_event(self, sim_info:'SimInfo', event:'TestEvent', resolver:'Resolver') -> 'None':
        super().handle_event(sim_info, event, resolver)
        if event == self.return_objects_event:
            self.return_stolen_objects()
            return
        if any(resolver(test) for test in self.triggers_holding):
            self._change_state(self.holding_state())
            return
        if any(resolver(test) for test in self.triggers_leave):
            self._change_state(self.leave_state())
            return
        elif any(resolver(test) for test in self.triggers_sad_leave):
            self._change_state(self.sad_leave_state())
            return

    def return_stolen_objects(self) -> 'None':
        for stolen_object in self.stolen_objects_data:
            obj = create_object(stolen_object.guid, loc_type=ItemLocation.HOUSEHOLD_INVENTORY)
            if obj is not None:
                obj.current_value = obj.depreciated_value
                obj.scale = stolen_object.game_data.scale
                for commodity in stolen_object.commodities:
                    obj.commodity_tracker.set_value(commodity.stat_type, commodity.get_value())
                build_buy.move_object_to_household_inventory(obj, HouseholdInventoryFlags.FORCE_OWNERSHIP)
        if len(self.stolen_objects_data) > 0:
            stolen_objects_string = LocalizationHelperTuning.get_bulleted_list((None,), [data.object_name for data in self.stolen_objects_data])
            burglar_info = self.burglar().sim_info
            dialog = self.objects_returned_tns(burglar_info)
            dialog.show_dialog(additional_tokens=(stolen_objects_string,))
            resolver = SingleSimResolver(burglar_info)
            for loot in self.objects_returned_loot:
                loot.apply_to_resolver(resolver)
        self.stolen_objects_data.clear()

    def _cache_valid_objects(self) -> 'None':
        target_amount = self.max_money_amount
        unsorted = []
        plex_service = services.get_plex_service()
        check_common_area = plex_service.is_active_zone_a_plex()
        household_id = services.get_active_sim().household_id
        for obj in services.object_manager().valid_objects():
            if not obj.get_household_owner_id() == household_id:
                pass
            elif not obj.is_on_active_lot():
                pass
            elif check_common_area and plex_service.get_plex_zone_at_position(obj.position, obj.level) is None:
                pass
            elif not obj.is_connected(self.burglar()):
                pass
            elif obj.children:
                pass
            elif PlacementFlags.NON_INVENTORYABLE & get_object_placement_flags(obj.definition.id):
                pass
            else:
                resolver = SingleObjectResolver(obj)
                if self.valid_object_tests.run_tests(resolver):
                    unsorted.append((obj.id, obj.depreciated_value))
        self.objects_to_steal = sorted(unsorted, key=operator.itemgetter(1), reverse=True)

    def on_object_stolen(self) -> 'None':
        self._objects_stolen += 1
        if (self.maximum_objects_to_steal is None or self._objects_stolen < self.maximum_objects_to_steal) and self.total_stolen_value < self.max_money_amount:
            self._change_state(self.find_object_state())
            return
        self._change_state(self.leave_state())

    def _on_add_sim_to_situation(self, sim:'Sim', job_type:'SituationJob', role_state_type_override:'RoleState'=None) -> 'None':
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        if self.burglar() is not None:
            self._cache_valid_objects()

    def _on_remove_sim_from_situation(self, sim:'Sim') -> 'None':
        super()._on_remove_sim_from_situation(sim)
        resolver = SingleSimResolver(sim.sim_info)
        if len(self.stolen_objects_data) > 0:
            stolen_objects_string = LocalizationHelperTuning.get_bulleted_list((None,), [data.object_name for data in self.stolen_objects_data])
            dialog = self.objects_stolen_tns(sim.sim_info)
            dialog.show_dialog(additional_tokens=(stolen_objects_string,))
            for loot in self.objects_stolen_loot:
                loot.apply_to_resolver(resolver)
        for loot in self.situation_end_loot:
            loot.apply_to_resolver(resolver)
        self._self_destruct()

    def _destroy(self) -> 'None':
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_STOP_SITUATION) as hook:
            hook.write_guid('type', self.guid64)
        super()._destroy()
        event_manager = services.get_event_manager()
        event_manager.unregister_tests(self, self.triggers_holding)
        event_manager.unregister_tests(self, self.triggers_leave)
        event_manager.unregister_tests(self, self.triggers_sad_leave)
        event_manager.unregister_single_event(self, self.return_objects_event)
        self.clear_current_object()
        services.get_persistence_service().unlock_save(self)

    def start_situation(self) -> 'None':
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(self.wait_for_burglar_state())
        active_sim_info = services.active_sim_info()
        if active_sim_info is not None:
            resolver = SingleSimResolver(active_sim_info)
            for loot in self.situation_start_loot:
                loot.apply_to_resolver(resolver)

    def get_target_object(self) -> 'None':
        return self.current_object

    def get_lock_save_reason(self) -> 'TunableLocalizedString':
        return self.save_lock_tooltip

    def set_current_object(self, obj:'GameObject') -> 'None':
        self.current_object = obj
        if self._reservation_handler is not None:
            logger.error('Trying to reserve an object when an existing reservation already exists: {}', self._reservation_handler)
            self._reservation_handler.end_reservation()
        self._reservation_handler = self.current_object.get_reservation_handler(self.burglar())
        self._reservation_handler.begin_reservation()

    def clear_current_object(self) -> 'None':
        self.current_object = None
        if self._reservation_handler is not None:
            self._reservation_handler.end_reservation()
            self._reservation_handler = None
