from __future__ import annotationsfrom event_testing.test_events import TestEventfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from protocolbuffers.FileSerialization_pb2 import ObjectData
    from sims.sim_info import SimInfo
    from typing import *import tagfrom event_testing.resolver import SingleActorAndObjectResolverfrom objects.object_enums import ResetReasonfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot_basic_op import BaseTargetedLootOperation, BaseLootOperationfrom interactions.utils.loot_ops import RemoveTraitLootOpfrom objects.components import Component, types, componentmethod_with_fallbackfrom sims.sim_info_name_data import SimInfoNameDatafrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableEnumEntry, OptionalTunable, Tunable, TunableList, TunableVariant, TunableMappingimport servicesimport sims4import zone_typeslogger = sims4.log.Logger('Stored Sim Info Component', default_owner='shipark')
class TransferStoredSimInfo(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'clear_stored_sim_on_subject': Tunable(description='\n            If set to False, the Stored Sim will remain on the subject object. If\n            set to True, the Store Sim will be removed from the subject object.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, clear_stored_sim_on_subject=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._clear_stored_sim_on_subject = clear_stored_sim_on_subject

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error("The Transfer Stored Sim Info loot tuned on: '{}' has a subject participant of None value.", self)
            return
        stored_sim_info = subject.get_component(types.STORED_SIM_INFO_COMPONENT)
        if stored_sim_info is None:
            logger.error("The Transfer Stored Sim Info loot tuned on interaction: '{}' has a subject with no Stored Sim Info Component.", self)
            return
        if target is None:
            logger.error("The Transfer Stored Sim Info loot tuned on interaction: '{}' has a target participant of None value.", self)
            return
        if target.has_component(types.STORED_SIM_INFO_COMPONENT):
            target.remove_component(types.STORED_SIM_INFO_COMPONENT)
        target.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=stored_sim_info.get_stored_sim_id())
        if self._clear_stored_sim_on_subject:
            subject.remove_component(types.STORED_SIM_INFO_COMPONENT)

class StoreSimInfoLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'replace_current': Tunable(description="\n            If there is a StoredSimInfoComponent on the subject, it will be replaced when this operation is called.\n            If the intent is to add an additional stored SimInfo, uncheck this box.\n            Note: If multiple SimInfo's are stored, you must use StoredSimOrNameDataList to access the data.\n            ", tunable_type=bool, default=True)}

    def __init__(self, replace_current, **kwargs):
        super().__init__(**kwargs)
        self._replace_current = replace_current

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None or target is None:
            logger.error('Trying to run Store Sim Info loot action with a None Subject and/or Target. subject:{}, target:{}', subject, target)
            return
        if not target.is_sim:
            logger.error('Trying to run Store Sim Info loot action on Subject {} with a non Sim Target {}', subject, target)
            return
        if subject.has_component(types.STORED_SIM_INFO_COMPONENT):
            if self._replace_current:
                subject.remove_component(types.STORED_SIM_INFO_COMPONENT)
                subject.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=target.sim_id)
            else:
                stored_sim_info_component = subject.get_component(types.STORED_SIM_INFO_COMPONENT)
                stored_sim_info_component.add_sim_id_to_list(target.sim_id)
        else:
            subject.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=target.sim_id)

class RemoveSimInfoLootOp(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Trying to run Remove Stored Sim Info loot action with a None Subject')
            return
        if subject.has_component(types.STORED_SIM_INFO_COMPONENT):
            subject.remove_component(types.STORED_SIM_INFO_COMPONENT)

class StoreSimElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            An element that retrieves an interaction participant and attaches\n            its information to another interaction participant using a dynamic\n            StoredSimInfoComponent.\n            ', 'source_participant': OptionalTunable(description='\n            Specify what participant to store on the destination participant.\n            ', tunable=TunableEnumEntry(description='\n                The participant of this interaction whose Sim Info is retrieved\n                to be stored as a component.\n                ', tunable_type=ParticipantType, default=ParticipantType.PickedObject, invalid_enums=(ParticipantType.StoredSimOrNameDataList,)), enabled_name='specific_participant', disabled_name='no_participant'), 'destination_participant': TunableEnumEntry(description='\n            The participant of this interaction to which a\n            StoredSimInfoComponent is added, with the Sim Info of\n            source_participant.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'replace_current': Tunable(description="\n            If there is a StoredSimInfoComponent on the subject, it will be replaced when this operation is called.\n            If the intent is to add an additional stored SimInfo, uncheck this box.\n            Note: If multiple SimInfo's are stored, you must use StoredSimOrNameDataList to access the data.\n            ", tunable_type=bool, default=True)}

    def _do_behavior(self):
        destination = self.interaction.get_participant(participant_type=self.destination_participant)
        if destination is not None:
            source = self.interaction.get_participant(participant_type=self.source_participant) if self.source_participant is not None else None
            if destination.has_component(types.STORED_SIM_INFO_COMPONENT):
                if self.source_participant is None:
                    destination.remove_component(types.STORED_SIM_INFO_COMPONENT)
                    return
                if self.replace_current:
                    destination.remove_component(types.STORED_SIM_INFO_COMPONENT)
                    if source is not None:
                        destination.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=source.id)
                        if source is not None:
                            stored_sim_info_component = destination.get_component(types.STORED_SIM_INFO_COMPONENT)
                            stored_sim_info_component.add_sim_id_to_list(source.id)
                elif source is not None:
                    stored_sim_info_component = destination.get_component(types.STORED_SIM_INFO_COMPONENT)
                    stored_sim_info_component.add_sim_id_to_list(source.id)
            elif source is not None:
                destination.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=source.id)

class StoredSimInfoComponent(Component, component_name=types.STORED_SIM_INFO_COMPONENT, allow_dynamic=True, persistence_key=protocols.PersistenceMaster.PersistableData.StoredSimInfoComponent):
    LOOTS_ON_OBJECT_REMOVE = TunableMapping(description='\n        A mapping of object tag to loots. A list of loots will be apply to the object \n        that has the stored sim component when the object is removed.\n        ', key_type=TunableEnumEntry(description='\n            what object to run loots.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True), value_type=TunableList(description='\n            loots to apply to the object when object is removed.\n            ', tunable=TunableVariant(description='\n                A specific loot to apply.\n                ', remove_trait=RemoveTraitLootOp.TunableFactory())))

    def __init__(self, *args, sim_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim_id_list = []
        if sim_id is not None:
            self._sim_id_list.append(sim_id)
        self._sim_info_name_data_list = []

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.StoredSimInfoComponent
        stored_sim_info_component_data = persistable_data.Extensions[protocols.PersistableStoredSimInfoComponent.persistable_data]
        stored_sim_info_component_data.sim_id_list.extend(self._sim_id_list)
        stored_sim_info_component_data.sim_info_name_data_list.extend([SimInfoNameData.generate_sim_info_name_data_msg(sim_info_name_data, use_profanity_filter=False) for sim_info_name_data in self._sim_info_name_data_list])
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        stored_sim_info_component_data = persistable_data.Extensions[protocols.PersistableStoredSimInfoComponent.persistable_data]
        if stored_sim_info_component_data.sim_id_list:
            self._sim_id_list = [_id for _id in stored_sim_info_component_data.sim_id_list]
            if stored_sim_info_component_data.sim_info_name_data_list:
                for _name_data in stored_sim_info_component_data.sim_info_name_data_list:
                    self._sim_info_name_data_list.append(SimInfoNameData(_name_data.gender, _name_data.age_flags, _name_data.first_name, _name_data.last_name, _name_data.full_name_key))
        else:
            self._sim_id_list = [stored_sim_info_component_data.sim_id]
            self._sim_id_list.extend([sim_id for sim_id in stored_sim_info_component_data.sim_id_set if sim_id != stored_sim_info_component_data.sim_id])
            if stored_sim_info_component_data.sim_info_name_data:
                sim_info_data = stored_sim_info_component_data.sim_info_name_data
                self._sim_info_name_data_list = [SimInfoNameData(sim_info_data.gender, sim_info_data.age_flags, sim_info_data.first_name, sim_info_data.last_name, sim_info_data.full_name_key)]
            if stored_sim_info_component_data.sim_info_name_data_set:
                for sim_info_data in stored_sim_info_component_data.sim_info_name_data_set:
                    sim_info_namedata = SimInfoNameData(sim_info_data.gender, sim_info_data.age_flags, sim_info_data.first_name, sim_info_data.last_name, sim_info_data.full_name_key)
                    if self._sim_info_name_data_list[0] != sim_info_namedata:
                        self._sim_info_name_data_list.append(sim_info_namedata)
        services.get_event_manager().process_event(TestEvent.StoredSimInfoComponentLoaded, obj=self.owner)

    def on_add(self, *_, **__):
        services.current_zone().register_callback(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, self._on_households_loaded)
        services.get_event_manager().process_event(TestEvent.StoredSimInfoComponentAdded, obj=self.owner, from_load=not self.has_stored_ids())

    def _apply_loots_on_object_remove(self):
        if self.LOOTS_ON_OBJECT_REMOVE is None:
            return

        def _apply_loots(sim_id):
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is not None:
                resolver = SingleActorAndObjectResolver(sim_info, self.owner, source=self)
                owner_tags = self.owner.get_tags()
                for (tag, loots) in self.LOOTS_ON_OBJECT_REMOVE.items():
                    if tag in owner_tags:
                        for loot in loots:
                            loot.apply_to_resolver(resolver)

        for _id in self._sim_id_list:
            _apply_loots(_id)

    def add_sim_id_to_list(self, sim_id):
        if sim_id in self._sim_id_list:
            return
        self._sim_id_list.append(sim_id)

    def clear_all_stored_data(self) -> 'None':
        self._sim_id_list = []
        self._sim_info_name_data_list = []

    def overwrite_sim_id(self, sim_id:'Optional[int]') -> 'bool':
        if sim_id is None:
            if not self.has_stored_data():
                return False
            self.clear_all_stored_data()
            return True
        stored_sim_id = self.get_stored_sim_id()
        if stored_sim_id == sim_id:
            return False
        self._sim_id_list = [sim_id]
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is not None:
            sim_name_data = sim_info.get_name_data()
            self._sim_info_name_data_list = [sim_name_data]
        else:
            self._sim_info_name_data_list = []
        return True

    def on_reset_component_get_interdependent_reset_records(self, reset_reason, reset_records):
        if reset_reason == ResetReason.BEING_DESTROYED and services.current_zone().is_zone_running:
            self._apply_loots_on_object_remove()

    def _on_households_loaded(self, *_, **__):
        sim_info_manager = services.sim_info_manager()
        if len(self._sim_info_name_data_list) == 0:
            for _id in self._sim_id_list:
                sim_info = sim_info_manager.get(_id)
                if sim_info is not None:
                    self._sim_info_name_data_list.append(sim_info.get_name_data())
        self.owner.update_object_tooltip()

    @staticmethod
    def get_stored_sim_id_from_object_data(object_data:'ObjectData') -> 'Optional[int]':
        save_data = protocols.PersistenceMaster()
        save_data.ParseFromString(object_data.attributes)
        persist_data_protocol = protocols.PersistableStoredSimInfoComponent.persistable_data
        for persist_data in save_data.data:
            if persist_data.type != persist_data.StoredSimInfoComponent:
                pass
            else:
                item_data = persist_data.Extensions[persist_data_protocol]
                return item_data.sim_id_list[0]

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_id(self) -> 'Optional[int]':
        if len(self._sim_id_list) > 0:
            return self._sim_id_list[0]

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_info(self) -> 'Optional[SimInfo]':
        if len(self._sim_id_list) > 0:
            return services.sim_info_manager().get(self._sim_id_list[0])

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_info_or_name_data(self) -> 'Union[SimInfo, SimInfoNameData, None]':
        if len(self._sim_id_list) > 0:
            sim_info = services.sim_info_manager().get(self._sim_id_list[0])
            if sim_info is not None:
                return sim_info
            else:
                return self.get_stored_sim_name_data()

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_name_data(self) -> 'Optional[SimInfoNameData]':
        if len(self._sim_info_name_data_list) > 0:
            return self._sim_info_name_data_list[0]

    @componentmethod_with_fallback(lambda *_, **__: None)
    def get_secondary_stored_sim_info(self, suppress_error=False):
        if len(self._sim_id_list) > 1:
            return services.sim_info_manager().get(self._sim_id_list[1])
        if not suppress_error:
            logger.error('The StoredSimComponent on {} does not have a second stored sim id', self.owner)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def get_secondary_stored_sim_info_or_name_data(self, suppress_error:'bool'=False) -> 'Optional[Union[SimInfo, SimInfoNameData]]':
        if len(self._sim_id_list) > 1:
            sim_info = services.sim_info_manager().get(self._sim_id_list[1])
            if sim_info is not None:
                return sim_info
        if len(self._sim_info_name_data_list) > 1:
            return self._sim_info_name_data_list[1]
        if not suppress_error:
            logger.error('The StoredSimComponent on {} does not have a second stored sim id so no SimInfo or name data could be loaded.', self.owner)

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_id_list(self):
        return self._sim_id_list

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_info_or_name_data_list(self):
        sim_info_or_name_data_list = []
        sim_info_manager = services.sim_info_manager()
        for sim_id in self._sim_id_list:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is not None:
                sim_info_or_name_data_list.append(sim_info)
            else:
                return self._sim_info_name_data_list
        return sim_info_or_name_data_list

    @componentmethod_with_fallback(lambda : None)
    def get_stored_sim_name_data_list(self):
        return self._sim_info_name_data_list

    def has_stored_ids(self) -> 'bool':
        return len(self._sim_id_list) != 0

    def has_stored_data(self) -> 'bool':
        return len(self._sim_info_name_data_list) != 0

    def component_interactable_gen(self):
        yield self
