from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.household import Household
    from statistics.mood import Moodfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolver, SingleActorAndObjectResolverfrom interactions.utils.death import DeathTypefrom objects import HiddenReasonFlagfrom protocolbuffers import Consts_pb2, FileSerialization_pb2, GameplaySaveData_pb2from protocolbuffers.Localization_pb2 import LocalizedStringfrom sims.household_enums import HouseholdChangeOriginimport build_buyimport enumimport objects.systemimport servicesimport sims4.loglogger = sims4.log.Logger('Wills', default_owner='madang')
class WillSectionType(enum.Int):
    BURIAL = 1
    FUNERAL = 2
    EMOTION = 3
    NOTE = 4
    HEIRLOOM = 5
    DEPENDENT = 6
    SIMOLEON = 7
    CHARITY = 8
    EMOTION_AND_NOTE = 9

class Will:

    def __init__(self) -> 'None':
        self._active = True
        self._claimants = None

    def is_finalized(self) -> 'bool':
        return not self._active

    def finalize_will(self) -> 'None':
        self._active = False
        self._refresh_recipients()

    def get_claimants(self) -> 'Set[int]':
        return self._claimants

    def _refresh_recipients(self) -> 'None':
        pass

class SimWill(Will):

    def __init__(self, sim_id:'int') -> 'None':
        super().__init__()
        self._sim_id = sim_id
        self._household_id = None
        self._heirloom_distribution = {}
        self._heirloom_object_data = {}
        self._burial_preference = None
        self._funeral_activity_preferences = []
        self._emotion = None
        self._note = None

    def get_will_owner_id(self):
        return self._sim_id

    def get_household_id(self):
        return self._household_id

    def get_heirloom_distributions(self) -> 'Dict[int, int]':
        return self._heirloom_distribution

    def get_heirloom_object_data(self) -> 'Dict[int, FileSerialization_pb2.ObjectData]':
        return self._heirloom_object_data

    def get_burial_preference(self) -> 'int':
        return self._burial_preference

    def get_funeral_activity_preferences(self) -> 'List[int]':
        return self._funeral_activity_preferences

    def get_note(self) -> 'LocalizedString':
        return self._note

    def get_emotion(self) -> 'Mood':
        return self._emotion

    def set_heirloom_recipient(self, object_id:'int', sim_id:'int') -> 'None':
        if object_id and sim_id:
            self._heirloom_distribution[object_id] = sim_id
            self._update_heirloom_object_data(object_id)

    def set_burial_preference(self, object_definition_id:'int') -> 'None':
        self._burial_preference = object_definition_id

    def set_funeral_activity_preference(self, activity_tuning_id:'int') -> 'None':
        if activity_tuning_id and len(self._funeral_activity_preferences) < services.get_will_service().SIM_WILL_FUNERAL_ACTIVITY_PREFERENCE_MAX:
            self._funeral_activity_preferences.append(activity_tuning_id)

    def set_emotion(self, mood:'Mood') -> 'None':
        self._emotion = mood

    def set_note(self, note_text:'LocalizedString') -> 'None':
        self._note = note_text

    def clear_heirloom_distributions(self) -> 'None':
        self._heirloom_distribution.clear()
        self._heirloom_object_data.clear()

    def clear_burial_preference(self) -> 'None':
        self._burial_preference = None

    def clear_funeral_activity_preferences(self) -> 'None':
        self._funeral_activity_preferences.clear()

    def clear_note_and_emotion(self) -> 'None':
        self._note = None
        self._emotion = None

    def remove_heirloom(self, object_id:'int') -> 'None':
        if object_id in self._heirloom_distribution:
            del self._heirloom_distribution[object_id]
        if object_id in self._heirloom_object_data:
            del self._heirloom_object_data[object_id]

    def finalize_will(self) -> 'None':
        super().finalize_will()
        self._claimants = self.get_sim_recipients()
        sim_info = services.sim_info_manager().get(self._sim_id)
        if sim_info is not None:
            self._household_id = sim_info.household_id
        for object_id in self._heirloom_distribution.keys():
            self._update_heirloom_object_data(object_id, destroy_object=True)

    def _refresh_recipients(self) -> 'None':
        sim_info_manager = services.sim_info_manager()
        for (object_id, sim_id) in list(self._heirloom_distribution.items()):
            sim_info = sim_info_manager.get(sim_id)
            if not sim_info.death_type != DeathType.NONE:
                if sim_info.household.hidden:
                    self.remove_heirloom(object_id)
            self.remove_heirloom(object_id)

    def get_sim_recipients(self) -> 'Set[int]':
        recipients = set()
        for sim_id in self._heirloom_distribution.values():
            recipients.add(sim_id)
        return recipients

    def is_sim_recipient(self, sim_id:'int') -> 'bool':
        return sim_id in self.get_sim_recipients()

    def apply_inheritance(self, recipient_sim_id:'int') -> 'None':
        if recipient_sim_id not in self._claimants:
            return
        recipient_sim_info = services.sim_info_manager().get(recipient_sim_id)
        recipient_sim = recipient_sim_info.get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE)
        for (object_id, sim_id) in self._heirloom_distribution.items():
            if sim_id == recipient_sim_id:
                if object_id not in self._heirloom_object_data.keys():
                    pass
                else:
                    obj = self._create_object_from_heirloom_obj_data(self._heirloom_object_data[object_id])
                    if obj is None:
                        logger.warn('Could not instantiate heirloom object from data for sim {}', recipient_sim_info)
                    else:
                        resolver = SingleActorAndObjectResolver(recipient_sim_info, obj, source=self)
                        services.get_will_service().HEIRLOOM_INHERITANCE_LOOT.apply_to_resolver(resolver)
                        obj.update_ownership(recipient_sim_info)
                        if recipient_sim is not None and recipient_sim.inventory_component.can_add(obj):
                            object_added = recipient_sim.inventory_component.player_try_add_object(obj)
                            if not object_added:
                                logger.warn('Could not add the heirloom object {} to inventory for sim {}', obj, recipient_sim)
                        else:
                            object_added = build_buy.move_object_to_household_inventory(obj)
                            if not object_added:
                                logger.warn('Could not add the heirloom object {} to household inventory for sim {}', obj, recipient_sim_info)
                                obj.destroy()
                                return
        self._claimants.remove(recipient_sim_id)

    def _update_heirloom_object_data(self, object_id:'int', destroy_object:'bool'=False) -> 'None':
        household = services.sim_info_manager().get(self._sim_id).household
        obj = services.object_manager().get(object_id)
        object_data = None
        if obj is not None:
            object_data = build_buy.c_api_buildbuy_get_save_object_data(obj.zone_id, object_id)
            if object_data is not None and destroy_object:
                for child in tuple(obj.children):
                    build_buy.move_object_to_household_inventory(child)
                obj.destroy()
        if object_data is None:
            object_data = build_buy.get_object_data_from_household_inventory(object_id, household.id)
            if object_data is not None and destroy_object:
                build_buy.remove_object_from_household_inventory(object_id, household, update_funds=False)
        if object_data is None:
            sim = services.sim_info_manager().get(self._sim_id).get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE)
            if sim is not None:
                obj = sim.inventory_component.get_item_with_id(object_id)
                if obj is not None:
                    sim_msg = services.get_persistence_service().get_sim_proto_buff(self._sim_id)
                    if sim_msg is not None:
                        inventory_obj_data = obj.save_object(sim_msg.inventory.objects)
                        hh_obj_added = build_buy.copy_objectdata_to_household_inventory(inventory_obj_data, household)
                        if hh_obj_added:
                            object_data = build_buy.get_object_data_from_household_inventory(object_id, household.id)
                            if object_data is not None:
                                build_buy.remove_object_from_household_inventory(object_id, household, update_funds=False)
                            if destroy_object:
                                obj.destroy()
        if object_data is not None:
            self._heirloom_object_data[object_id] = object_data

    def _create_object_from_heirloom_obj_data(self, object_data:'FileSerialization_pb2.ObjectData'):
        post_add_callback = lambda o: o.load_object(object_data, inline_finalize=True)
        obj = objects.system.create_object(object_data.guid, obj_state=object_data.state_index, post_add=post_add_callback)
        return obj

    def get_persistable_will_data_proto(self) -> 'GameplaySaveData_pb2.SimWillData':
        proto = GameplaySaveData_pb2.SimWillData()
        proto.sim_id = self._sim_id
        proto.active = self._active
        proto.funeral_activity_preferences.extend(self._funeral_activity_preferences)
        if self._household_id:
            proto.household_id = self._household_id
        if self._claimants:
            proto.claimant_sim_ids.extend(self._claimants)
        if self._burial_preference is not None:
            proto.burial_preference_id = self._burial_preference
        if self._emotion is not None:
            proto.emotion_mood_id = self._emotion.guid64
        if self._note is not None:
            proto.note = self._note
        for (object_id, recipient_sim_id) in self._heirloom_distribution.items():
            with ProtocolBufferRollback(proto.heirloom_distribution) as heirloom_data:
                heirloom_data.object_id = object_id
                heirloom_data.recipient_sim_id = recipient_sim_id
        if self._active:
            for object_id in self._heirloom_object_data.keys():
                self._update_heirloom_object_data(object_id)
        for (object_id, object_data) in self._heirloom_object_data.items():
            with ProtocolBufferRollback(proto.heirloom_obj_data) as heirloom_obj_data:
                heirloom_obj_data.object_id = object_id
                heirloom_obj_data.object_data = object_data.SerializeToString()
        return proto

    def load_from_persistable_will_data_proto(self, proto) -> 'None':
        self._active = proto.active
        if proto.household_id:
            self._household_id = proto.household_id
        if proto.claimant_sim_ids:
            self._claimants = list(proto.claimant_sim_ids)
        elif not self._active:
            self._claimants = set()
        self._burial_preference = proto.burial_preference_id
        self._funeral_activity_preferences = list(proto.funeral_activity_preferences)
        mood_manager = services.get_instance_manager(sims4.resources.Types.MOOD)
        self._emotion = mood_manager.get(proto.emotion_mood_id)
        if proto.note.hash:
            self._note = LocalizedString()
            self._note.MergeFrom(proto.note)
        for heirloom_data in proto.heirloom_distribution:
            self._heirloom_distribution[heirloom_data.object_id] = heirloom_data.recipient_sim_id
        for heirloom_obj_data in proto.heirloom_obj_data:
            object_data = FileSerialization_pb2.ObjectData()
            object_data.ParseFromString(heirloom_obj_data.object_data)
            self._heirloom_object_data[heirloom_obj_data.object_id] = object_data

class HouseholdWill(Will):

    def __init__(self, household_id:'int') -> 'None':
        super().__init__()
        self._household_id = household_id
        self._dependent_distribution = {}
        self._simoleon_distribution = {}
        self._charity_allocation = 0.0
        self._simoleon_amount = None

    def get_dependent_distributions(self) -> 'Dict[int, int]':
        return self._dependent_distribution

    def get_simoleon_distributions(self) -> 'Dict[int, float]':
        return self._simoleon_distribution

    def get_charity_distribution(self) -> 'float':
        return self._charity_allocation

    def set_dependent_distribution(self, dependent_sim_id:'int', destination_hh_id:'int') -> 'None':
        self._dependent_distribution[dependent_sim_id] = destination_hh_id

    def set_simoleon_distribution(self, recipient_hh_id:'int', percentage:'float') -> 'None':
        self._simoleon_distribution[recipient_hh_id] = percentage

    def set_charity_distribution(self, percentage:'float') -> 'None':
        self._charity_allocation = percentage

    def clear_dependent_distributions(self) -> 'None':
        self._dependent_distribution.clear()

    def clear_simoleon_distributions(self) -> 'None':
        self._simoleon_distribution.clear()
        self._charity_allocation = 0

    def finalize_will(self) -> 'None':
        super().finalize_will()
        self._update_will_dependents()
        self._claimants = self.get_household_recipients()
        household = services.household_manager().get(self._household_id)
        if household is not None:
            self._simoleon_amount = household.funds.money
            if self._simoleon_amount:
                inheritance_amount = self._simoleon_amount*(1.0 - self.remaining_simoleon_allocation_percentage())
                if inheritance_amount > 0:
                    household.funds.try_remove(inheritance_amount, Consts_pb2.FUNDS_INTERACTION_COST)

    def _update_will_dependents(self) -> 'None':
        sim_info_manager = services.sim_info_manager()
        for dependent_sim_id in list(self._dependent_distribution.keys()):
            dependent_sim_info = sim_info_manager.get(dependent_sim_id)
            if not dependent_sim_info.is_dead:
                if dependent_sim_info.can_live_alone:
                    del self._dependent_distribution[dependent_sim_id]
            del self._dependent_distribution[dependent_sim_id]

    def _refresh_recipients(self) -> 'None':
        household_manager = services.household_manager()
        for (sim_id, household_id) in list(self._dependent_distribution.items()):
            household = household_manager.get(household_id)
            if not household.is_dependent_household:
                if household.hidden:
                    del self._dependent_distribution[sim_id]
            del self._dependent_distribution[sim_id]
        for household_id in list(self._simoleon_distribution.keys()):
            household = household_manager.get(household_id)
            if not household.is_dependent_household:
                if household.hidden:
                    del self._simoleon_distribution[household_id]
            del self._simoleon_distribution[household_id]

    def get_household_recipients(self) -> 'Set[int]':
        dependent_recipients = set(self._dependent_distribution.values())
        simoleon_recipients = set(self._simoleon_distribution.keys())
        return dependent_recipients.union(simoleon_recipients)

    def is_household_recipient(self, household_id:'int') -> 'bool':
        return household_id in self.get_household_recipients()

    def remaining_simoleon_allocation_percentage(self) -> 'float':
        total_allocation = 0.0
        for amount in self._simoleon_distribution.values():
            total_allocation += amount
        return round(1.0 - (total_allocation + self._charity_allocation), 1)

    def _try_apply_dependent_inheritance(self, recipient_household:'Household') -> 'bool':
        self._update_will_dependents()
        dependent_sim_infos = []
        sim_info_manager = services.sim_info_manager()
        for (dependent_sim_id, hh_id) in self._dependent_distribution.items():
            if hh_id == recipient_household.id:
                dependent_sim_info = sim_info_manager.get(dependent_sim_id)
                if dependent_sim_info is not None and dependent_sim_info.household_id == self._household_id:
                    dependent_sim_infos.append(dependent_sim_info)
        if dependent_sim_infos:
            dependent_count = len(dependent_sim_infos)
            for sim_info in dependent_sim_infos:
                if sim_info.pregnancy_tracker is not None:
                    pregnancy_tracker = sim_info.pregnancy_tracker
                    if pregnancy_tracker.is_pregnant:
                        dependent_count += pregnancy_tracker.offspring_count
            household_manager = services.household_manager()
            if dependent_count <= recipient_household.free_slot_count:
                spawn = services.current_zone_id() == recipient_household.home_zone_id
                for dependent_sim_info in dependent_sim_infos:
                    household_manager.switch_sim_household(dependent_sim_info, reason=HouseholdChangeOrigin.WILL_INHERITANCE)
                    recipient_household.refresh_sim_data(dependent_sim_info.id, spawn=spawn, selectable=True)
            else:
                active_sim = services.active_sim_info()
                resolver = SingleSimResolver(active_sim)
                will_household = household_manager.get(self._household_id)
                transfer_fail_dialog = services.get_will_service().DEPENDENT_INHERITANCE_FAIL_NOTIFICATION(active_sim, resolver)
                transfer_fail_dialog.show_dialog(additional_tokens=(will_household.name, recipient_household.name))

    def apply_inheritance(self, recipient_household_id:'int') -> 'None':
        if recipient_household_id not in self._claimants:
            return
        recipient_household = services.household_manager().get(recipient_household_id)
        if recipient_household is None:
            return
        self._try_apply_dependent_inheritance(recipient_household)
        if recipient_household_id in self._simoleon_distribution and self._simoleon_amount is not None:
            inheritance_amount = self._simoleon_distribution[recipient_household_id]*self._simoleon_amount
            recipient_household.funds.add(inheritance_amount, Consts_pb2.FUNDS_INTERACTION_REWARD)
        self._claimants.remove(recipient_household_id)

    def get_persistable_will_data_proto(self) -> 'GameplaySaveData_pb2.HouseholdWillData':
        proto = GameplaySaveData_pb2.HouseholdWillData()
        proto.household_id = self._household_id
        proto.active = self._active
        if self._claimants:
            proto.claimant_hh_ids.extend(self._claimants)
        if self._charity_allocation is not None:
            proto.charity_percentage = self._charity_allocation
        if self._simoleon_amount:
            proto.simoleon_amount = self._simoleon_amount
        for (dependent_sim_id, recipient_hh_id) in self._dependent_distribution.items():
            with ProtocolBufferRollback(proto.dependent_distribution) as dependent_data:
                dependent_data.dependent_sim_id = dependent_sim_id
                dependent_data.recipient_hh_id = recipient_hh_id
        for (recipient_hh_id, percentage) in self._simoleon_distribution.items():
            with ProtocolBufferRollback(proto.simoleon_distribution) as simoleon_data:
                simoleon_data.recipient_hh_id = recipient_hh_id
                simoleon_data.percentage = percentage
        return proto

    def load_from_persistable_will_data_proto(self, proto) -> 'None':
        self._active = proto.active
        if proto.claimant_hh_ids:
            self._claimants = list(proto.claimant_hh_ids)
        elif not self._active:
            self._claimants = set()
        self._charity_allocation = proto.charity_percentage
        self._simoleon_amount = proto.simoleon_amount if proto.simoleon_amount else None
        for dependent_data in proto.dependent_distribution:
            self._dependent_distribution[dependent_data.dependent_sim_id] = dependent_data.recipient_hh_id
        for simoleon_data in proto.simoleon_distribution:
            self._simoleon_distribution[simoleon_data.recipient_hh_id] = simoleon_data.percentage
