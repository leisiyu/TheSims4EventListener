import functoolsimport weakreffrom animation.animation_constants import CreatureTypefrom protocolbuffers import SimObjectAttributes_pb2from event_testing.test_events import TestEventfrom objects.components import Component, componentmethod, componentmethod_with_fallbackfrom objects.components.portal_lock_data import LockAllWithSimIdExceptionData, LockSimInfoData, LockAllWithClubException, LockResult, LockAllWithSituationJobExceptionData, IndividualSimDoorLockData, LockAllWithGenusException, LockRankedStatisticData, LockAllWithBuffExceptionData, LockCreatureData, UnlockForBuffDatafrom objects.components.portal_locking_enums import LockPriority, LockSide, LockType, ClearLockfrom objects.components.types import PORTAL_LOCKING_COMPONENT, OBJECT_LOCKING_COMPONENTfrom objects.mixins import SuperAffordanceProviderMixinfrom sims.sim_info_tests import MatchTypefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableList, TunableVariantimport servicesimport sims4logger = sims4.log.Logger('LockComponents', default_owner='cjiang')
class BaseLockingComponent(Component, HasTunableFactory, AutoFactoryInit):
    DEFAULT_LOCK = LockAllWithSimIdExceptionData(except_actor=False, except_household=False, lock_priority=LockPriority.SYSTEM_LOCK, lock_sides=LockSide.LOCK_BOTH, should_persist=True)
    FACTORY_TUNABLES = {'preset_lock_datas': TunableList(description='\n            The preset lock data on the component. If the priority is set to\n            SYSTEM_LOCK, the lock will always exist. If the priority is set to\n            PLAYER_LOCK, then upon load, any preset data is trumped by whatever\n            might have been set by the player.\n            ', tunable=TunableVariant(lock_siminfo=LockSimInfoData.TunableFactory(), lock_clubs=LockAllWithClubException.TunableFactory(), lock_situation_job=LockAllWithSituationJobExceptionData.TunableFactory(), lock_genus=LockAllWithGenusException.TunableFactory(), lock_ranked_statistic=LockRankedStatisticData.TunableFactory(), lock_buff=LockAllWithBuffExceptionData.TunableFactory(), unlock_buff=UnlockForBuffData.TunableFactory(), lock_creature=LockCreatureData.TunableFactory(), default='lock_siminfo'))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_datas = {}
        self._disallowed_objects = weakref.WeakKeyDictionary()
        self._lock_refresh_events = set()
        for preset_lock_data in self.preset_lock_datas:
            self.add_lock_data(preset_lock_data(), refresh=False, clear_existing_locks=ClearLock.CLEAR_NONE)

    def on_remove(self, *_, **__):
        services.get_event_manager().unregister(self, self._lock_refresh_events)

    def remove_disallowed_object(self, obj, disallower):
        raise NotImplementedError

    def add_disallowed_object(self, obj, disallower, lock_both=False):
        if obj not in self._disallowed_objects:
            self._disallowed_objects[obj] = dict()
        self._disallowed_objects[obj][disallower] = lock_both

    @componentmethod
    def add_lock_data(self, lock_data, replace_same_lock_type=True, refresh=True, clear_existing_locks=ClearLock.CLEAR_ALL):
        if clear_existing_locks != ClearLock.CLEAR_NONE:
            for existing_lock_data in list(self.lock_datas.values()):
                if existing_lock_data.lock_priority == LockPriority.PLAYER_LOCK:
                    clear_lock = True
                    if clear_existing_locks == ClearLock.CLEAR_OTHER_LOCK_TYPES:
                        clear_lock = existing_lock_data.lock_type != lock_data.lock_type
                    if clear_lock:
                        del self.lock_datas[existing_lock_data.lock_type]
        if not replace_same_lock_type:
            existing_data = self.lock_datas.get(lock_data.lock_type)
            if existing_data is not None:
                lock_data.update(existing_data)
        self.lock_datas[lock_data.lock_type] = lock_data
        if refresh:
            self.refresh_locks()
        self._lock_refresh_events.update(lock_data.REFRESH_EVENTS)
        services.get_event_manager().register(self, self._lock_refresh_events)

    @componentmethod_with_fallback(lambda : None)
    def refresh_locks(self, update_objects=True):
        self._clear_locks_on_all_sims(update_objects)
        self._lock_every_sim(update_objects)

    def _clear_locks_on_all_sims(self, update_objects=True):
        for target_sim in services.sim_info_manager().instanced_sims_gen():
            self.remove_disallowed_object(target_sim, self)
        if update_objects:
            for obj in services.get_object_routing_service().routable_objects_gen():
                self.remove_disallowed_object(obj, self)

    def _lock_every_sim(self, update_objects=True):
        for target_sim in services.sim_info_manager().instanced_sims_gen():
            self.lock_object(target_sim)
        if update_objects:
            for obj in services.get_object_routing_service().routable_objects_gen():
                self.lock_object(obj)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def lock_object(self, obj):
        lock_result = self.test_lock(obj)
        if lock_result:
            self.add_disallowed_object(obj, self, lock_both=lock_result.is_locking_both())

    @componentmethod
    def test_lock(self, obj):
        current_system_lock_result = LockResult.NONE
        current_player_lock_result = LockResult.NONE
        current_override_lock_result = LockResult.NONE
        for lock_data in self.lock_datas.values():
            if not lock_data.check_lock_permission(obj):
                pass
            else:
                lock_result = lock_data.test_lock(obj)
                if lock_result is None:
                    pass
                elif lock_result.is_player_lock():
                    if current_player_lock_result == LockResult.NONE:
                        current_player_lock_result = lock_result
                    elif current_player_lock_result.is_locked and not lock_result.is_locked:
                        current_player_lock_result = lock_result
                    elif lock_result.is_locking_both():
                        current_player_lock_result = lock_result
                elif lock_result.is_override_player_lock():
                    if current_override_lock_result == LockResult.NONE:
                        current_override_lock_result = lock_result
                    elif current_override_lock_result.is_locked or lock_result.is_locked:
                        current_override_lock_result = lock_result
                    elif lock_result.is_locking_both():
                        current_override_lock_result = lock_result
                elif current_system_lock_result == LockResult.NONE:
                    current_system_lock_result = lock_result
                elif current_system_lock_result.is_locked or lock_result.is_locked:
                    current_system_lock_result = lock_result
                elif current_system_lock_result.is_locked and lock_result.is_locked and lock_result.is_locking_both():
                    current_system_lock_result = lock_result
        if current_system_lock_result.is_locked:
            if current_player_lock_result.is_locked and current_player_lock_result.is_locking_both():
                return current_player_lock_result
            return current_system_lock_result
        else:
            if current_override_lock_result != LockResult.NONE:
                return current_override_lock_result
            if current_player_lock_result.is_locked:
                return current_player_lock_result
        return LockResult.NONE

    @componentmethod
    def get_disallowed_objects(self):
        return self._disallowed_objects

    def handle_event(self, sim_info, event_type, resolver):
        if event_type == TestEvent.BuffBeganEvent or event_type == TestEvent.BuffEndedEvent:
            buff = resolver.event_kwargs['buff']
            if buff is not None and buff.refresh_lock:
                self.refresh_locks(update_objects=False)

    @componentmethod_with_fallback(lambda : False)
    def has_locking_component(self):
        return True

    @componentmethod_with_fallback(lambda : None)
    def get_locking_component(self):
        return self

    @componentmethod_with_fallback(lambda : None)
    def lock(self):
        self.add_lock_data(BaseLockingComponent.DEFAULT_LOCK)

    @componentmethod_with_fallback(lambda : None)
    def unlock(self):
        if self.lock_datas:
            self._clear_locks_on_all_sims()
            self.lock_datas.clear()

    @componentmethod_with_fallback(lambda *_, **__: False)
    def has_lock_data(self, lock_priority=None, lock_types=None):
        for lock_data in self.lock_datas.values():
            if not lock_priority is None:
                pass
            if not lock_types is None:
                if lock_data.lock_type in lock_types:
                    return True
            return True
        return False

    @componentmethod
    def remove_locks(self, lock_type=None, lock_priority=None, creature_types=None):
        if not self.lock_datas:
            return
        self._clear_locks_on_all_sims()
        for lock_data in list(self.lock_datas.values()):
            if not lock_priority is None:
                pass
            if not lock_type is None:
                if lock_data.lock_type == lock_type:
                    if lock_data.lock_type == LockType.LOCK_CREATURE and creature_types is not None and hasattr(self.lock_datas[lock_data.lock_type], 'creature_types'):
                        creature_list = list(self.lock_datas[lock_data.lock_type].creature_types)
                        for remove_creature in creature_types:
                            if remove_creature in creature_list:
                                creature_list.remove(remove_creature)
                        if len(creature_list) > 0:
                            self.lock_datas[lock_data.lock_type].creature_types = tuple(creature_list)
                        else:
                            del self.lock_datas[lock_data.lock_type]
                            del self.lock_datas[lock_data.lock_type]
                    else:
                        del self.lock_datas[lock_data.lock_type]
            if lock_data.lock_type == LockType.LOCK_CREATURE and creature_types is not None and hasattr(self.lock_datas[lock_data.lock_type], 'creature_types'):
                creature_list = list(self.lock_datas[lock_data.lock_type].creature_types)
                for remove_creature in creature_types:
                    if remove_creature in creature_list:
                        creature_list.remove(remove_creature)
                if len(creature_list) > 0:
                    self.lock_datas[lock_data.lock_type].creature_types = tuple(creature_list)
                else:
                    del self.lock_datas[lock_data.lock_type]
                    del self.lock_datas[lock_data.lock_type]
            else:
                del self.lock_datas[lock_data.lock_type]
        self._lock_every_sim()

    def _save(self, persistence_master_message, cmp_lock_data, persistable_data):
        for lock_data in self.lock_datas.values():
            if not lock_data.should_persist:
                pass
            elif lock_data.lock_priority == LockPriority.PLAYER_LOCK:
                persist_lock_data = cmp_lock_data.lock_data.add()
                persist_lock_data.lock_type = lock_data.lock_type
                lock_data.save(persist_lock_data)
        persistence_master_message.data.extend([persistable_data])

    def _load(self, cmp_lock_data):
        self.remove_locks(lock_priority=LockPriority.PLAYER_LOCK)
        for persist_lock_data in cmp_lock_data.lock_data:
            if persist_lock_data.lock_type == LockType.LOCK_ALL_WITH_SIMID_EXCEPTION:
                create_lock_data = functools.partial(LockAllWithSimIdExceptionData, except_actor=persist_lock_data.except_actor, except_household=persist_lock_data.except_household)
            elif persist_lock_data.lock_type == LockType.LOCK_ALL_WITH_SITUATION_JOB_EXCEPTION:
                create_lock_data = functools.partial(LockAllWithSituationJobExceptionData, situation_job_test=None, except_business_employee=persist_lock_data.except_retail_employee)
            elif persist_lock_data.lock_type == LockType.LOCK_ALL_WITH_CLUBID_EXCEPTION:
                create_lock_data = functools.partial(LockAllWithClubException, except_club_seeds=())
            elif persist_lock_data.lock_type == LockType.INDIVIDUAL_SIM:
                create_lock_data = functools.partial(IndividualSimDoorLockData)
            elif persist_lock_data.lock_type == LockType.LOCK_ALL_WITH_GENUS_EXCEPTION:
                create_lock_data = functools.partial(LockAllWithGenusException, gender=0, ages=None, species=None, match_type=MatchType.MATCH_ALL)
            elif persist_lock_data.lock_type == LockType.LOCK_RANK_STATISTIC:
                create_lock_data = functools.partial(LockRankedStatisticData, ranked_stat=None, rank_threshold=None)
            elif persist_lock_data.lock_type == LockType.LOCK_ALL_WITH_BUFF_EXCEPTION:
                create_lock_data = functools.partial(LockAllWithBuffExceptionData, except_buffs=None)
            elif persist_lock_data.lock_type == LockType.UNLOCK_ALL_WITH_BUFF:
                create_lock_data = functools.partial(UnlockForBuffData, buffs=None)
            elif persist_lock_data.lock_type == LockType.LOCK_CREATURE:
                create_lock_data = functools.partial(LockCreatureData, creature_types=None)
                lock_data = create_lock_data(lock_priority=LockPriority(persist_lock_data.priority), lock_sides=LockSide(persist_lock_data.sides), should_persist=True)
                lock_data.load(persist_lock_data)
                self.add_lock_data(lock_data, clear_existing_locks=ClearLock.CLEAR_NONE)
            lock_data = create_lock_data(lock_priority=LockPriority(persist_lock_data.priority), lock_sides=LockSide(persist_lock_data.sides), should_persist=True)
            lock_data.load(persist_lock_data)
            self.add_lock_data(lock_data, clear_existing_locks=ClearLock.CLEAR_NONE)

class ObjectLockingComponent(BaseLockingComponent, HasTunableFactory, AutoFactoryInit, SuperAffordanceProviderMixin, component_name=OBJECT_LOCKING_COMPONENT, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.ObjectLockingComponent):

    def on_add(self, *_, **__):
        self.owner.update_component_commodity_flags()

    @componentmethod_with_fallback(lambda *_, **__: None)
    def remove_disallowed_object(self, obj, disallower):
        disallowing_objects = self._disallowed_objects.get(obj)
        if disallowing_objects is None:
            return
        if disallower not in disallowing_objects:
            return
        del disallowing_objects[disallower]
        if not disallowing_objects:
            del self._disallowed_objects[obj]

    def component_super_affordances_gen(self, context=None, **kwargs):
        if context is None:
            yield from self.super_affordances
        elif context.sim is not None and not self.test_lock(context.sim).is_locked:
            yield from self.super_affordances

    def save(self, persistence_master_message):
        persistable_data = SimObjectAttributes_pb2.PersistenceMaster.PersistableData()
        persistable_data.type = SimObjectAttributes_pb2.PersistenceMaster.PersistableData.ObjectLockingComponent
        lock_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableObjectLockingComponent.persistable_data]
        self._save(persistence_master_message, lock_data, persistable_data)

    def load(self, persistence_master_message):
        lock_data = persistence_master_message.Extensions[SimObjectAttributes_pb2.PersistableObjectLockingComponent.persistable_data]
        self._load(lock_data)

class PortalLockingComponent(BaseLockingComponent, HasTunableFactory, AutoFactoryInit, component_name=PORTAL_LOCKING_COMPONENT, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.PortalLockingComponent):

    def on_add(self, *_, **__):
        services.object_manager().add_portal_to_cache(self.owner)

    @componentmethod
    def add_disallowed_object(self, obj, disallower, lock_both=False):
        super().add_disallowed_object(obj, disallower, lock_both)
        for portal_pair in self.owner.get_portal_pairs():
            obj.routing_component.routing_context.lock_portal(portal_pair.there)
            if lock_both and portal_pair.back is not None:
                obj.routing_component.routing_context.lock_portal(portal_pair.back)

    def has_bidirectional_lock(self, obj):
        return any(self._disallowed_objects[obj].values())

    @componentmethod_with_fallback(lambda *_, **__: None)
    def remove_disallowed_object(self, obj, disallower):
        disallowing_objects = self._disallowed_objects.get(obj)
        if disallowing_objects is None:
            return
        if disallower not in disallowing_objects:
            return
        del disallowing_objects[disallower]
        if not disallowing_objects:
            for portal_pair in self.owner.get_portal_pairs():
                obj.routing_component.routing_context.unlock_portal(portal_pair.there)
                if portal_pair.back is not None:
                    obj.routing_component.routing_context.unlock_portal(portal_pair.back)
            del self._disallowed_objects[obj]

    def save(self, persistence_master_message):
        persistable_data = SimObjectAttributes_pb2.PersistenceMaster.PersistableData()
        persistable_data.type = SimObjectAttributes_pb2.PersistenceMaster.PersistableData.PortalLockingComponent
        portal_lock_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistablePortalLockingComponent.persistable_data]
        self._save(persistence_master_message, portal_lock_data, persistable_data)

    def load(self, persistence_master_message):
        portal_lock_data = persistence_master_message.Extensions[SimObjectAttributes_pb2.PersistablePortalLockingComponent.persistable_data]
        self._load(portal_lock_data)
