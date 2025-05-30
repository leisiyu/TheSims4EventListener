import operatorimport randomfrom _collections import defaultdictfrom contextlib import contextmanagerimport sims4from buffs.appearance_modifier import appearance_modifier_handlersfrom buffs.appearance_modifier.appearance_modifier_type import AppearanceModifierTypefrom cas.cas import apply_siminfo_override, OutfitOverrideOptionFlagsfrom distributor.ops import SetSimAttachment, UpdateSkewerThumbnailfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sims4.math import MAX_UINT32logger = sims4.log.Logger('Appearance')
class ModifierInfo:

    def __init__(self, modifier, guid, priority, apply_to_all_outfits, additional_flags, should_display):
        self.modifier = modifier
        self.guid = guid
        self.priority = priority
        self.apply_to_all_outfits = apply_to_all_outfits
        self.additional_flags = additional_flags
        self.should_display = should_display

class AppearanceTracker:

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._persisted_appearance_data = dict()
        self._current_appearance_override_sim_info = None
        self._no_overrides = False
        self._active_appearance_modifier_infos = None
        self._sim_info.on_outfit_generated.append(self._on_outfit_generated)
        self._active_sim_attachment_modifiers = None
        self._appearance_target_obj = None

    def add_appearance_modifier(self, modifier, guid, priority, apply_to_all_outfits, additional_flags=OutfitOverrideOptionFlags.DEFAULT, source=None, archive_single_entry=True):
        if self._active_appearance_modifier_infos is None:
            self._active_appearance_modifier_infos = defaultdict(list)
        modifier_info = ModifierInfo(modifier, guid, priority, apply_to_all_outfits, additional_flags, False)
        self._active_appearance_modifier_infos[modifier.modifier_type].append(modifier_info)
        if archive_single_entry and appearance_modifier_handlers.archiver.enabled:
            appearance_modifier_handlers.add_appearance_modifier_data(self._sim_info, (modifier,), priority, apply_to_all_outfits, source, modifier)

    def add_appearance_modifiers(self, appearance_modifiers_list, guid, priority, apply_to_all_outfits, additional_flags=OutfitOverrideOptionFlags.DEFAULT, source=None, target_obj=None):
        permanent_modifiers = []
        added_non_permanent_modifier = False
        self._appearance_target_obj = target_obj
        for appearance_modifiers in appearance_modifiers_list:
            modifier = self._choose_modifier(appearance_modifiers)
            if modifier is None:
                pass
            elif modifier.is_permanent_modification:
                permanent_modifiers.append(modifier)
            else:
                self.add_appearance_modifier(modifier, guid, priority, apply_to_all_outfits, additional_flags, archive_single_entry=False)
                added_non_permanent_modifier = True
                if appearance_modifier_handlers.archiver.enabled:
                    appearance_modifier_handlers.add_appearance_modifier_data(self._sim_info, (entry.modifier for entry in appearance_modifiers), priority, apply_to_all_outfits, source, modifier)
        self.apply_permanent_appearance_modifiers(permanent_modifiers, guid, priority, apply_to_all_outfits, additional_flags)
        if added_non_permanent_modifier:
            self.evaluate_appearance_modifiers()
        self._appearance_target_obj = None

    def apply_permanent_appearance_modifiers(self, permanent_modifiers, guid, priority, apply_to_all_outfits, additional_flags):
        for permanent_modifier in permanent_modifiers:
            modifier_info = ModifierInfo(permanent_modifier, guid, priority, apply_to_all_outfits, additional_flags, True)
            self.apply_appearance_modifiers([modifier_info], self._sim_info, is_permanent_modification=True)

    def make_active_appearance_modifier_permanent(self, tag):
        if not self._active_appearance_modifier_infos:
            return False
        appearance_modifier_made_permanent = False
        for appearance_modifier_info_list in self._active_appearance_modifier_infos.values():
            for modifier_info in appearance_modifier_info_list:
                if modifier_info.should_display and modifier_info.modifier.appearance_modifier_tag == tag:
                    self.apply_appearance_modifiers([modifier_info], self._sim_info, is_permanent_modification=True)
                    appearance_modifier_made_permanent = True
        return appearance_modifier_made_permanent

    def remove_appearance_modifiers(self, guid, source=None):
        if not self._active_appearance_modifier_infos:
            return
        keys_to_remove = []
        modifiers = []
        if appearance_modifier_handlers.archiver.enabled:
            archiver_enabled = True
        else:
            archiver_enabled = False
        for (mod_type, appearance_modifier_list) in self._active_appearance_modifier_infos.items():
            modifier_infos_to_remove = []
            for appearance_modifier_info in appearance_modifier_list:
                if appearance_modifier_info.guid == guid:
                    modifier_infos_to_remove.append(appearance_modifier_info)
            if archiver_enabled:
                for modifier_info in modifier_infos_to_remove:
                    modifiers.append(modifier_info.modifier)
            self._active_appearance_modifier_infos[mod_type] = [mod for mod in self._active_appearance_modifier_infos[mod_type] if mod not in modifier_infos_to_remove]
            if modifier_infos_to_remove and not self._active_appearance_modifier_infos[mod_type]:
                keys_to_remove.append(mod_type)
        if archiver_enabled:
            appearance_modifier_handlers.remove_appearance_modifier_data(self._sim_info, modifiers, source)
        for mod_type in keys_to_remove:
            self._active_appearance_modifier_infos.pop(mod_type, None)
        self.remove_persistent_appearance_modifier_data(guid)
        self.evaluate_appearance_modifiers()

    def evaluate_appearance_modifiers(self):
        modifiers_to_apply = []
        should_refresh_thumbnail = False
        if self._active_appearance_modifier_infos:
            for appearance_modifier_info_list in self._active_appearance_modifier_infos.values():
                appearance_modifier = appearance_modifier_info_list[0].modifier
                if appearance_modifier.is_combinable_with_same_type:
                    sorting_dict = defaultdict(list)
                    for modifier_info in appearance_modifier_info_list:
                        sorting_dict[modifier_info.modifier.combinable_sorting_key].append(modifier_info)
                    for appearance_modifier_info_list_for_sorting_key in sorting_dict.values():
                        appearance_modifier_info_list_for_sorting_key.sort(key=operator.attrgetter('priority'), reverse=True)
                        for (index, mod_info) in enumerate(appearance_modifier_info_list_for_sorting_key):
                            mod_info.should_display = True if index == 0 else False
                else:
                    appearance_modifier_info_list.sort(key=operator.attrgetter('priority'), reverse=True)
                    for (index, mod_info) in enumerate(appearance_modifier_info_list):
                        mod_info.should_display = True if index == 0 else False
                should_refresh_thumbnail = should_refresh_thumbnail or appearance_modifier.should_refresh_thumbnail
                modifiers_to_apply.extend(appearance_modifier_info_list)
        modifiers_to_apply.sort(key=lambda m: m.modifier.modifier_type == AppearanceModifierType.GENERATE_OUTFIT and m.modifier.apply_before_other_modifiers, reverse=True)
        regular_modifiers_to_apply = []
        attachment_modifiers_to_apply = []
        for m in modifiers_to_apply:
            if m.modifier.modifier_type == AppearanceModifierType.SET_ATTACHMENT:
                attachment_modifiers_to_apply.append(m)
            else:
                regular_modifiers_to_apply.append(m)
        self.apply_appearance_modifiers(regular_modifiers_to_apply, self._sim_info, should_refresh_thumbnail=should_refresh_thumbnail)
        self.apply_sim_attachment_modifiers(attachment_modifiers_to_apply)

    def active_displayed_appearance_modifiers(self):
        active_displayed_modifiers = set()
        if self._active_appearance_modifier_infos:
            for appearance_modifier_info_list in self._active_appearance_modifier_infos.values():
                active_displayed_modifiers.add(appearance_modifier_info_list[0].modifier)
        return active_displayed_modifiers

    @contextmanager
    def no_appearance_overrides(self):
        if not self._no_overrides:
            logger.error('Calling appearance_tracker.no_appearance_overrides\n                            after it has already been called in this context.\n                            Nested calls not supported.', owner='jwilkinson')
        self._no_overrides = True
        try:
            yield None
        finally:
            self._no_overrides = False

    @property
    def appearance_override_sim_info(self):
        if self._no_overrides:
            return
        return self._current_appearance_override_sim_info

    @appearance_override_sim_info.setter
    def appearance_override_sim_info(self, override_sim_info):
        self._current_appearance_override_sim_info = override_sim_info

    def add_persistent_appearance_modifier_data(self, key, persisted_data):
        if key not in self._persisted_appearance_data:
            self._persisted_appearance_data[key] = persisted_data

    def remove_persistent_appearance_modifier_data(self, key):
        if key in self._persisted_appearance_data:
            del self._persisted_appearance_data[key]

    def get_persistent_appearance_modifier_data(self, key):
        return self._persisted_appearance_data.get(key, None)

    def save_appearance_tracker(self):
        data = protocols.PersistableAppearanceTracker()
        for (guid, seed) in self._persisted_appearance_data.items():
            with ProtocolBufferRollback(data.appearance_modifiers) as entry:
                entry.guid = guid
                entry.seed = seed
        return data

    def load_appearance_tracker(self, data):
        for appearance_modifier in data.appearance_modifiers:
            self.add_persistent_appearance_modifier_data(appearance_modifier.guid, appearance_modifier.seed)

    def _on_outfit_generated(self, outfit_category, outfit_index, **kwargs):
        self.evaluate_appearance_modifiers()

    def _apply_sim_info_override(self, original_sim_info, modified_sim_info, resulting_sim_info, outfit_category, outfit_index, apply_to_all_outfits, additional_flags, body_type_flags_to_set, modified_ids):
        option_flags = additional_flags | OutfitOverrideOptionFlags.OVERRIDE_HAIR_MATCH_FLAGS
        if apply_to_all_outfits:
            option_flags |= OutfitOverrideOptionFlags.OVERRIDE_ALL_OUTFITS
        if body_type_flags_to_set:
            with modified_sim_info.set_temporary_outfit_flags(outfit_category, outfit_index, body_type_flags_to_set):
                if modified_ids is not None:
                    apply_siminfo_override(original_sim_info._base, modified_sim_info._base, resulting_sim_info._base, option_flags, filter_outfit_category_index_pair_dict=list(modified_ids))
                else:
                    apply_siminfo_override(original_sim_info._base, modified_sim_info._base, resulting_sim_info._base, option_flags)
        elif modified_ids is not None:
            apply_siminfo_override(original_sim_info._base, modified_sim_info._base, resulting_sim_info._base, option_flags, filter_outfit_category_index_pair_dict=list(modified_ids))
        else:
            apply_siminfo_override(original_sim_info._base, modified_sim_info._base, resulting_sim_info._base, option_flags)

    def apply_sim_attachment_modifiers(self, attachment_modifiers_to_apply):
        if self._active_sim_attachment_modifiers is None:
            self._active_sim_attachment_modifiers = defaultdict(list)
        should_be_attached_guids = set(m.guid for m in attachment_modifiers_to_apply)
        for (guid, attachment_ids) in self._active_sim_attachment_modifiers.items():
            if guid not in should_be_attached_guids:
                for attachment_id in attachment_ids:
                    distributor = Distributor.instance()
                    op = SetSimAttachment(attachment_id, SetSimAttachment.DETACH)
                    distributor.add_op(self._sim_info, op)
        keys_to_delete = set(self._active_sim_attachment_modifiers.keys()).difference(should_be_attached_guids)
        for k in keys_to_delete:
            del self._active_sim_attachment_modifiers[k]
        already_attached_guids = set(self._active_sim_attachment_modifiers.keys())
        for modifier_info in attachment_modifiers_to_apply:
            if modifier_info.guid not in already_attached_guids:
                attachment_id = modifier_info.modifier.get_attachment_id(sim_info=self._sim_info, appearance_target_obj=self._appearance_target_obj)
                if attachment_id is not None:
                    distributor = Distributor.instance()
                    op = SetSimAttachment(attachment_id, SetSimAttachment.ATTACH, self._appearance_target_obj.id if self._appearance_target_obj is not None else 0)
                    distributor.add_op(self._sim_info, op)
                    self._active_sim_attachment_modifiers[modifier_info.guid].append(attachment_id)

    def apply_appearance_modifiers(self, appearance_modifier_infos, original_sim_info, is_permanent_modification=False, should_refresh_thumbnail=False):
        if not appearance_modifier_infos:
            original_sim_info.appearance_tracker.appearance_override_sim_info = None
            original_sim_info.resend_physical_attributes()
            return
        from sims import sim_info_base_wrapper
        modified_sim_info = sim_info_base_wrapper.SimInfoBaseWrapper(gender=original_sim_info.gender, age=original_sim_info.age, species=original_sim_info.species, first_name=original_sim_info.first_name, last_name=original_sim_info.last_name, breed_name=original_sim_info.breed_name, full_name_key=original_sim_info.full_name_key, breed_name_key=original_sim_info.breed_name_key)
        body_type_flags_to_set = 0
        with original_sim_info.set_temporary_outfit_flags_on_all_outfits(0):
            apply_to_all_outfits = None
            additional_flags = None
            source_sim_info = original_sim_info
            for modifier_info in appearance_modifier_infos:
                if modifier_info.should_display is False:
                    pass
                else:
                    random_seed = original_sim_info.appearance_tracker.get_persistent_appearance_modifier_data(modifier_info.guid)
                    if random_seed is None:
                        random_seed = random.randint(0, MAX_UINT32)
                        if not is_permanent_modification:
                            original_sim_info.appearance_tracker.add_persistent_appearance_modifier_data(modifier_info.guid, random_seed)
                    if apply_to_all_outfits is None:
                        apply_to_all_outfits = modifier_info.apply_to_all_outfits
                    else:
                        apply_to_all_outfits |= modifier_info.apply_to_all_outfits
                        if apply_to_all_outfits != modifier_info.apply_to_all_outfits:
                            logger.error('Sim: {} has a mix of appearance modifiers that have Apply to All Outfits tuned to true and false.This is not supported, so all modifiers will be applied to all outfits as a fallback.', original_sim_info, owner='rrodgers')
                    if additional_flags is None:
                        additional_flags = modifier_info.additional_flags
                    else:
                        additional_flags |= modifier_info.additional_flags
                        if additional_flags != modifier_info.additional_flags:
                            logger.error('Sim: {} has multiple appearance modifiers with different flags set. This is not supported and all set flags will be applied for all appearance modifiers as a fallback.', original_sim_info, owner='rrodgers')
                    (body_type_flag, modified_ids) = modifier_info.modifier.modify_sim_info(source_sim_info, modified_sim_info, random_seed)
                    body_type_flags_to_set |= body_type_flag
                    source_sim_info = modified_sim_info
        (outfit_category, outfit_index) = original_sim_info.get_current_outfit()
        modified_sim_info.set_current_outfit(original_sim_info.get_current_outfit())
        if is_permanent_modification:
            stored_appearance_override_sim_info = original_sim_info.appearance_tracker.appearance_override_sim_info if original_sim_info.appearance_tracker else None
            self._apply_sim_info_override(original_sim_info, modified_sim_info, original_sim_info, outfit_category, outfit_index, apply_to_all_outfits, additional_flags, body_type_flags_to_set, modified_ids)
            if stored_appearance_override_sim_info is not None:
                self._apply_sim_info_override(stored_appearance_override_sim_info, modified_sim_info, stored_appearance_override_sim_info, outfit_category, outfit_index, apply_to_all_outfits, additional_flags, body_type_flags_to_set, modified_ids)
        else:
            appearance_override_sim_info = sim_info_base_wrapper.SimInfoBaseWrapper(sim_id=original_sim_info.sim_id)
            self._apply_sim_info_override(original_sim_info, modified_sim_info, appearance_override_sim_info, outfit_category, outfit_index, apply_to_all_outfits, additional_flags, body_type_flags_to_set, modified_ids)
            original_sim_info.appearance_tracker.appearance_override_sim_info = appearance_override_sim_info
        original_sim_info.resend_physical_attributes()
        if should_refresh_thumbnail and not (original_sim_info.is_npc or original_sim_info.is_selected):
            op = UpdateSkewerThumbnail(original_sim_info.id)
            Distributor.instance().add_op_with_no_owner(op)

    def _choose_modifier(self, modifiers):
        if not modifiers:
            return
        resolver = SingleSimResolver(self._sim_info)
        weighted_options = [(entry.weight.get_multiplier(resolver), entry.modifier) for entry in modifiers]
        modifier = sims4.random.weighted_random_item(weighted_options)
        return modifier
