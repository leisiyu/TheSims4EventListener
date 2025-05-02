from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from services.reset_and_delete_service import ResetRecord
    from sims.sim_info import SimInfoimport profanityimport servicesimport sims4import zone_typesfrom event_testing.resolver import SingleActorAndObjectResolverfrom interactions.utils.loot_basic_op import BaseTargetedLootOperation, BaseLootOperationfrom objects.components import Component, types, componentmethod, componentmethod_with_fallbackfrom objects.hovertip import HovertipStylefrom objects.object_enums import ResetReasonfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims.sim_info_name_data import SimInfoNameDatafrom sims4.common import Packfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableList, TunableReferencefrom sims4.utils import classpropertylogger = sims4.log.Logger('Heirloom Component', default_owner='jmoline')
class HeirloomComponent(Component, allow_dynamic=True, component_name=types.HEIRLOOM_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.HeirloomComponent):
    LOOTS_ON_HEIRLOOM_REMOVE = TunableList(description='\n        A list of loots that will be applied when the heirloom component is\n        removed or object destroyed.\n        \n        The Actor is the sim that created the heirloom. If the Actor does\n        not exist, then loots will not be given.\n        \n        The Object is the heirloom object itself.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True))
    HEIRLOOM_TITLE = TunableLocalizedStringFactory(description='\n        This should provide the format for the title of an heirloom object hovertip.\n        Parameter 0 provides the name of sim that created the heirloom.\n        \n        e.g. "{0.SimName}\'s Heirloom" \n        ')
    HEIRLOOM_OWNER = TunableLocalizedStringFactory(description='\n        This should provide the format for the sim in posession of the heirloom\n        object. Parameter 0 provides the name of the sim that owns the heirloom.\n        \n        e.g. "In Possession Of: {0.SimName}"\n        ')

    @classproperty
    def required_packs(cls):
        return (Pack.EP17,)

    def __init__(self, *args, sim_id:'int'=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._creator_sim_id = sim_id
        self._creator_sim_info_name_data = None
        self._engraved_message = None
        self._ui_metadata_handles = []
        self._original_hover_tip_style = None
        self.hovertip_requested = False

    def save(self, persistence_master_message) -> 'None':
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.HeirloomComponent
        heirloom_component_data = persistable_data.Extensions[protocols.PersistableHeirloomComponent.persistable_data]
        if self._creator_sim_id is not None:
            heirloom_component_data.creator_sim_id = self._creator_sim_id
        if self._creator_sim_info_name_data is not None:
            heirloom_component_data.creator_sim_info_name_data = SimInfoNameData.generate_sim_info_name_data_msg(self._creator_sim_info_name_data, use_profanity_filter=False)
        if self._engraved_message is not None:
            heirloom_component_data.engraved_message = self._engraved_message
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data) -> 'None':
        heirloom_component_data = persistable_data.Extensions[protocols.PersistableHeirloomComponent.persistable_data]
        if heirloom_component_data.HasField('creator_sim_id'):
            self._creator_sim_id = heirloom_component_data.creator_sim_id
        if heirloom_component_data.HasField('creator_sim_info_name_data'):
            name_data = heirloom_component_data.creator_sim_info_name_data
            self._creator_sim_info_name_data = SimInfoNameData(name_data.gender, name_data.age_flags, name_data.first_name, name_data.last_name, name_data.full_name_key)
        if heirloom_component_data.HasField('engraved_message'):
            self.set_engraved_message(self._get_filtered_text(heirloom_component_data.engraved_message))
        self.owner.update_object_tooltip()

    def _get_filtered_text(self, text:'str') -> 'str':
        if self.owner.is_from_gallery:
            (_, filtered_text) = profanity.check(text)
            return filtered_text
        return text

    @componentmethod_with_fallback(lambda : None)
    def get_creator_sim_id(self) -> 'int':
        return self._creator_sim_id

    @componentmethod_with_fallback(lambda : None)
    def get_creator_sim_info(self) -> 'Optional[SimInfo]':
        if self._creator_sim_id is None:
            return
        return services.sim_info_manager().get(self._creator_sim_id)

    @componentmethod_with_fallback(lambda : None)
    def get_creator_sim_info_name_data(self) -> 'SimInfoNameData':
        return self._creator_sim_info_name_data

    @componentmethod_with_fallback(lambda : None)
    def get_engraved_message(self) -> 'str':
        return self._engraved_message

    @componentmethod
    def set_engraved_message(self, engraved_message:'str') -> 'None':
        self._engraved_message = engraved_message
        self.update_hovertip()

    def on_add(self, *_, **__) -> 'None':
        services.current_zone().register_callback(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, self._on_households_loaded)
        if self.owner.hover_tip == HovertipStyle.HOVER_TIP_GARDENING or self.owner.hover_tip == HovertipStyle.HOVER_TIP_ICON_TITLE_DESCRIPTION or self.owner.hover_tip == HovertipStyle.HOVER_TIP_OBJECT_RELATIONSHIP:
            logger.error("The object {} has {} as its HovertipStyle. The style has a custom hover tip UI that isn't supported by heirlooms.", self.owner, self.owner.hover_tip)
        tooltip_component = self.owner.tooltip_component
        if tooltip_component is not None:
            self.hovertip_requested = tooltip_component.hovertip_requested
        self.update_hovertip()

    def on_remove(self, *_, **__) -> 'None':
        zone = services.current_zone()
        if not zone.is_zone_shutting_down:
            self._apply_loots_on_object_remove()
        if self._ui_metadata_handles:
            for handle in self._ui_metadata_handles:
                self.owner.remove_ui_metadata(handle)
            self.owner.update_ui_metadata()
            self._ui_metadata_handles.clear()

    def on_reset_component_get_interdependent_reset_records(self, reset_reason:'ResetReason', reset_records:'List[ResetRecord]'):
        if reset_reason == ResetReason.BEING_DESTROYED and services.current_zone().is_zone_running:
            self._apply_loots_on_object_remove()

    def _apply_loots_on_object_remove(self) -> 'None':
        if not self.LOOTS_ON_HEIRLOOM_REMOVE:
            return
        sim_info_manager = services.sim_info_manager()
        creator_sim_info = sim_info_manager.get(self._creator_sim_id)
        if creator_sim_info is None:
            return
        resolver = SingleActorAndObjectResolver(actor_sim_info=creator_sim_info, obj=self.owner, source=self)
        for loot in self.LOOTS_ON_HEIRLOOM_REMOVE:
            loot.apply_to_resolver(resolver)

    def _on_households_loaded(self, *_, **__) -> 'None':
        sim_info_manager = services.sim_info_manager()
        if self._creator_sim_info_name_data is None:
            sim_info = sim_info_manager.get(self._creator_sim_id)
            if sim_info is not None:
                self._creator_sim_info_name_data = sim_info.get_name_data()
        self.owner.update_object_tooltip()

    def _ui_metadata_gen(self) -> 'Generator[str, Any]':
        sim_info_manager = services.sim_info_manager()
        yield ('hover_tip', HovertipStyle.HOVER_TIP_HEIRLOOM_OBJECT)
        creator_sim_info = sim_info_manager.get(self._creator_sim_id)
        if creator_sim_info is None:
            creator_sim_info = self._creator_sim_info_name_data
        else:
            yield ('heirloom_sim_id', self._creator_sim_id)
        yield ('heirloom_title', HeirloomComponent.HEIRLOOM_TITLE(creator_sim_info))
        owner_sim_id = self.owner.get_sim_owner_id()
        if owner_sim_id is not None:
            owner_sim_info = sim_info_manager.get(owner_sim_id)
            if owner_sim_info is not None:
                yield ('heirloom_owner', HeirloomComponent.HEIRLOOM_OWNER(owner_sim_info))
        if self._engraved_message is not None:
            yield ('engraved_message', LocalizationHelperTuning.get_raw_text(self._engraved_message))

    def update_hovertip(self) -> 'None':
        if self.hovertip_requested:
            old_handles = list(self._ui_metadata_handles)
            try:
                self._ui_metadata_handles = []
                for (name, value) in self._ui_metadata_gen():
                    handle = self.owner.add_ui_metadata(name, value)
                    self._ui_metadata_handles.append(handle)
            finally:
                for handle in old_handles:
                    self.owner.remove_ui_metadata(handle)
                self.owner.update_ui_metadata()

    def on_client_connect(self, client) -> 'None':
        self.update_hovertip()

    def on_hovertip_requested(self) -> 'bool':
        if not self.hovertip_requested:
            self.hovertip_requested = True
            self.update_hovertip()
            return True
        return False

    def has_ui_metadata_handles(self) -> 'bool':
        return bool(self._ui_metadata_handles)

class SetHeirloomObjectLootOp(BaseTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None or target is None:
            logger.error('Trying to run Store Heirloom Object loot action with a None Subject and/or Target. subject:{}, target:{}', subject, target)
            return
        if not target.is_sim:
            logger.error('Trying to run Store Heirloom Object loot action on Subject {} with a non Sim Target {}', subject, target)
            return
        if subject.has_component(types.HEIRLOOM_COMPONENT):
            subject.remove_component(types.HEIRLOOM_COMPONENT)
            will_service = services.get_will_service()
            if will_service is not None:
                will_service.remove_heirloom_from_will(subject.id)
        subject.add_dynamic_component(types.HEIRLOOM_COMPONENT, sim_id=target.sim_id)

class ClearHeirloomObjectLootOp(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Trying to run Remove Heirloom Object loot action with a None Subject')
            return
        if subject.has_component(types.HEIRLOOM_COMPONENT):
            subject.remove_component(types.HEIRLOOM_COMPONENT)
            will_service = services.get_will_service()
            if will_service is not None:
                will_service.remove_heirloom_from_will(subject.id)
