from __future__ import annotationsfrom cas.cas import get_caspart_bodytype, get_caspart_gender_compatible, OutfitOverrideOptionFlagsfrom collections import namedtuplefrom sims4.localization import TunableLocalizedStringfrom tunable_multiplier import TunableMultiplierfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfoimport servicesfrom objects.components.state_change import StateChangefrom sims4.common import Packfrom sims4.utils import classpropertyfrom buffs.appearance_modifier.appearance_modifier import AppearanceModifier, AppearanceModifierPriorityfrom jewelry_crafting.jewelry_crafting_tuning import JewelryCraftingTuningfrom objects.components.state import ObjectState, ObjectStateValue, StateComponentfrom objects.components import Component, types, componentmethod_with_fallbackfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunablePackSafeReference, TunableMapping, TunableCasPart, TunableReference, HasTunableSingletonFactory, OptionalTunableimport sims4.logAppearanceModifierTuple = namedtuple('AppearanceModifier', ['modifier', 'weight'])
class JewelryComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.JEWELRY_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.PersistableJewelryComponent, allow_dynamic=True):
    FACTORY_TUNABLES = {'crystal_state_cas_map': TunableMapping(description='\n            Map that defines which cas_part should be equipped depending on the crystal state\n            Key: Crystal State\n            Value: Cas Part\n            ', key_name='crystal_state', value_name='cas_part', value_type=TunableCasPart(), key_type=TunablePackSafeReference(description='\n                The value to compare to.', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buff_handle = None
        self._current_body_part = None
        self._current_cas_part = None
        self._sim_info_id = None

    @classproperty
    def required_packs(cls):
        return (Pack.SP49,)

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.PersistableJewelryComponent
        jewelry_data = persistable_data.Extensions[protocols.PersistableJewelryComponent.persistable_data]
        if self._current_body_part is not None:
            jewelry_data.current_body_part = self._current_body_part
        if self._current_cas_part is not None:
            jewelry_data.current_cas_part = self._current_cas_part
        if self._buff_handle is not None:
            jewelry_data.buff_handle = self._buff_handle
        if self._sim_info_id is not None:
            jewelry_data.sim_id = self._sim_info_id
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        jewelry_data = persistable_data.Extensions[protocols.PersistableJewelryComponent.persistable_data]
        if jewelry_data.HasField('current_body_part'):
            self._current_body_part = jewelry_data.current_body_part
        if jewelry_data.HasField('current_cas_part'):
            self._current_cas_part = jewelry_data.current_cas_part
        if jewelry_data.HasField('buff_handle'):
            self._buff_handle = jewelry_data.buff_handle
        if jewelry_data.HasField('sim_id'):
            self._sim_info_id = jewelry_data.sim_id

    def get_buff(self):
        return self.buff

    def get_cas_part(self) -> 'int':
        return self._current_cas_part

    def _is_drained(self) -> 'bool':
        return self.owner.state_value_active(JewelryCraftingTuning.JEWELRY_DATA.drained_state_value)

    def refresh_sim_tense_buff(self) -> 'None':
        if self._sim_info_id is None:
            return
        sim_info_manager = services.sim_info_manager()
        sim_info = sim_info_manager.get(self._sim_info_id)
        if sim_info is not None and sim_info.jewelry_tracker is not None:
            sim_info.jewelry_tracker.refresh_tense_buff()

    def on_state_changed(self, state, old_value, new_value, from_init):
        if self._sim_info_id is not None:
            sim_info_manager = services.sim_info_manager()
            sim_info = sim_info_manager.get(self._sim_info_id)
            if new_value == JewelryCraftingTuning.JEWELRY_DATA.drained_state_value:
                self.remove_buff(sim_info=sim_info)
            sim_info.jewelry_tracker.refresh_tense_buff()

    def wear(self, owner_sim_info:'SimInfo', apply_to_all_outfits:'bool', call_appearance_modifier:'bool', sim_infos_to_apply) -> 'None':
        self._sim_info_id = owner_sim_info.id
        if call_appearance_modifier:
            state_component = self.owner.state_component
            metal_state = JewelryCraftingTuning.JEWELRY_DATA.metal_state
            metal_state_value = state_component.get_state(metal_state)
            cas_part = self.get_cas_part(owner_sim_info)
            self._current_body_part = get_caspart_bodytype(cas_part)
            hsv = None
            if StateChange.HSV_COLOR_SHIFT in metal_state_value.new_client_state.ops:
                hsv = metal_state_value.new_client_state.ops[StateChange.HSV_COLOR_SHIFT]
            self._current_cas_part = cas_part
            modifier = AppearanceModifier.SetCASPart(cas_part=cas_part, should_toggle=False, replace_with_random=False, update_genetics=True, _is_combinable_with_same_type=False, remove_conflicting=True, outfit_type_compatibility=None, appearance_modifier_tag=None, expect_invalid_parts=False, hsv_color_shift=hsv, object_id=self.owner.id, part_layer_index=-1, rgba_color_shift=0, should_refresh_thumbnail=False)
            element = AppearanceModifierTuple(modifier, TunableMultiplier.ONE)
            for sim_info in sim_infos_to_apply:
                sim_info.appearance_tracker.add_appearance_modifiers(((element,),), self.owner.id, AppearanceModifierPriority.INVALID, apply_to_all_outfits, OutfitOverrideOptionFlags.SKIP_BODY_MODIFICATIONS, source='JewelryComponent')
        self.set_worn_state(True, True, owner_sim_info)
        self.add_buff(owner_sim_info, True)

    def set_worn_state(self, is_worn_in_current_outfit:'bool', is_worn_in_other_outfit:'bool', sim_info:'SimInfo') -> 'None':
        state_component = self.owner.state_component
        new_state = None
        if is_worn_in_current_outfit:
            new_state = JewelryCraftingTuning.JEWELRY_DATA.wearing_states.worn_in_current_outfit
        elif is_worn_in_other_outfit:
            new_state = JewelryCraftingTuning.JEWELRY_DATA.wearing_states.worn_in_other_outfit
        else:
            new_state = JewelryCraftingTuning.JEWELRY_DATA.wearing_states.not_worn
        state_component.set_state(new_state.state, new_state)

    def unequip(self, owner_sim_info:'SimInfo', apply_to_all_outfits:'bool', is_worn_in_other_outfit:'bool', call_appearance_modifier:'bool', sim_infos_to_apply:'set()'):
        self.refresh_sim_tense_buff()
        self._sim_info_id = None
        if self._current_cas_part is not None:
            modifier = AppearanceModifier.RemoveCASPart(cas_part=self._current_cas_part, update_genetics=True, outfit_type_compatibility=None, appearance_modifier_tag=None, _is_combinable_with_same_type=False, object_id=self.owner.id)
            element = AppearanceModifierTuple(modifier, TunableMultiplier.ONE)
            for sim_info in sim_infos_to_apply:
                sim_info.appearance_tracker.add_appearance_modifiers(((element,),), self.owner.id, AppearanceModifierPriority.INVALID, apply_to_all_outfits, OutfitOverrideOptionFlags.SKIP_BODY_MODIFICATIONS, source='JewelryComponent')
        self.set_worn_state(False, is_worn_in_other_outfit, owner_sim_info)
        self.remove_buff(owner_sim_info)

    def get_cas_part(self, sim_info:'SimInfo') -> 'int':
        state_component = self.owner.state_component
        crystal_state = JewelryCraftingTuning.JEWELRY_DATA.crystal_state
        current_crystal_value = state_component.get_state(crystal_state)
        tuning_cas_part = self.crystal_state_cas_map[current_crystal_value]
        cas_part = get_caspart_gender_compatible(sim_info=sim_info._base, cas_part=tuning_cas_part)
        return cas_part

    def add_buff(self, sim_info:'SimInfo', force_add:'bool') -> 'None':
        if self._is_drained():
            return
        state_component = self.owner.state_component
        crystal_state = JewelryCraftingTuning.JEWELRY_DATA.crystal_state
        crystal_state_state_value = state_component.get_state(crystal_state)
        if crystal_state_state_value in JewelryCraftingTuning.JEWELRY_DATA.crystal_state_buff_map:
            buff = JewelryCraftingTuning.JEWELRY_DATA.crystal_state_buff_map[crystal_state_state_value]
        if self._buff_handle is None or force_add:
            self._buff_handle = sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason)

    def remove_buff(self, sim_info:'SimInfo') -> 'None':
        if self._buff_handle is not None:
            sim_info.remove_buff(self._buff_handle)
            self._buff_handle = None

    @componentmethod_with_fallback(lambda : None)
    def is_sell_disabled_from_component(self):
        if self.owner.state_value_active(JewelryCraftingTuning.JEWELRY_DATA.wearing_states.worn_in_current_outfit) or self.owner.state_value_active(JewelryCraftingTuning.JEWELRY_DATA.wearing_states.worn_in_other_outfit):
            return True
        return False
