import event_testingfrom cas import casfrom event_testing.resolver import SingleActorAndObjectResolverfrom interactions import ParticipantTypeSingle, ParticipantTypefrom interactions.base.picker_interaction import PickerSingleChoiceSuperInteraction, ObjectPickerMixinfrom interactions.payment.tunable_payment import TunablePaymentSnippetfrom interactions.utils.tunable import TunableContinuationfrom sims.outfits.outfit_enums import BodyTypefrom sims4.localization import _create_localized_stringfrom sims4.tuning.tunable import TunableEnumEntry, Tunable, OptionalTunable, TunableList, TunableMappingfrom sims4.tuning.tunable_base import GroupNamesfrom tag import TunableTags, TunableTagfrom ui.ui_dialog_picker import ObjectPickerRow
class CASCatalogPicker(PickerSingleChoiceSuperInteraction, ObjectPickerMixin):
    INSTANCE_TUNABLES = {'body_types': TunableList(description='\n            The body types to filter by\n            ', tunable=TunableEnumEntry(tunable_type=BodyType, default=BodyType.NONE, invalid_enums=BodyType.NONE, tuning_group=GroupNames.PICKERTUNING)), 'include_tags': TunableTags(description='\n            Only get object with these tags if defined\n            ', tuning_group=GroupNames.PICKERTUNING), 'exclude_tags': TunableTags(description='\n            Exclude objects with these tags if defined \n            ', tuning_group=GroupNames.PICKERTUNING), 'catalog_participant': TunableEnumEntry(description='\n            From which participant are we getting the catalog\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor, tuning_group=GroupNames.PICKERTUNING), 'thumbnail_participant': TunableEnumEntry(description='\n            From which participant are we getting the catalog\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor, tuning_group=GroupNames.PICKERTUNING), 'show_all_variants': Tunable(description='\n            If true, show all color variants\n            ', tunable_type=bool, default=False), 'continuation': OptionalTunable(description='\n            If enabled, you can tune a continuation to be pushed.\n            PickedObject will be the object that was selected\n            ', tunable=TunableContinuation(description='\n                If specified, a continuation to push on the chosen object.'), tuning_group=GroupNames.PICKERTUNING), 'single_push_continuation': Tunable(description='\n            If enabled, only the first continuation that can be successfully\n            pushed will run. Otherwise, all continuations are pushed such that\n            they run in order.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'fallback_continuation': OptionalTunable(description='\n            If enabled, you can tune a continuation to be pushed when all tests for \n            continuations fail.\n            ', tunable=TunableContinuation(description='\n                If specified, a fallback continuation to push on the chosen object.'), tuning_group=GroupNames.PICKERTUNING), 'cell_enabled_tests': OptionalTunable(description='\n            Test to see if the cell should be enabled or not.\n            If it does not pass, it will disable the cell and optionally\n            override the tooltip.\n            A string tuned for Tooltip here will use tokens from the interaction\'s\n            tuned Display Names Text Tokens. For example, a tooltip string containing\n            "{0.ObjectName}" would use the first entry tuned there.\n            ', tunable=event_testing.tests.TunableTestSetWithTooltip(), tuning_group=GroupNames.PICKERTUNING), 'body_type_tag_map': TunableMapping(description="\n            Map between body types and tags to be used in filters. \n            As Picker filters are using tags to filter but we don't want CAS artists to add the tag to all catalog files, \n            we added this correlation between tag and body type.\n            ", key_type=TunableEnumEntry(description='\n                Body type.\n                ', tunable_type=BodyType, default=BodyType.NONE, invalid_enums=(BodyType.NONE,)), value_type=TunableTag(description='\n                Tag.\n                '))}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True

    def picker_rows_gen(cls, target, context=None, **kwargs):
        participant = cls.get_resolver().get_participant(cls.catalog_participant)
        thumbnail_participant = cls.get_resolver().get_participant(cls.thumbnail_participant)
        sim_info = participant.get_sim_info()
        household = sim_info.household
        reward_parts = household._reward_inventory.reward_parts
        reward_parts_list = list()
        new_rewards = list()
        for reward_part in reward_parts:
            if reward_part.sim_id == 0 or reward_part.sim_id == sim_info.id:
                reward_parts_list.append(reward_part.part_id)
                if reward_part.is_new_reward:
                    new_rewards.append(reward_part.part_id)
        cas_parts = cas.get_catalog_casparts_by_bodytype(sim_info=thumbnail_participant._base, include_tags=list(cls.include_tags), exclude_tags=list(cls.exclude_tags), bodytypes=list(cls.body_types), show_all_variants=cls.show_all_variants, rewards_parts=reward_parts_list)
        if reward_parts is not None and cls:
            interaction_parameters = cls.interaction_parameters.copy()
        else:
            interaction_parameters = kwargs.copy()
        for (cas_part, (tags, locked_tooltip_id)) in cas_parts.items():
            body_type = cas.get_caspart_bodytype(cas_part)
            tag = None
            if body_type in cls.body_type_tag_map:
                tag = cls.body_type_tag_map[body_type]
                tags.add(tag)
            row = ObjectPickerRow(def_id=cas_part, tag=cas_part, tag_list=tags, use_catalog_product_thumbnails=False, use_cas_catalog_product_thumbnails=True, cas_catalog_gender=thumbnail_participant.gender, owner_sim_id=sim_info.id, is_new=cas_part in new_rewards, target_sim_id=thumbnail_participant.id)
            resolver = SingleActorAndObjectResolver(thumbnail_participant, cas_part, source=cls)
            if locked_tooltip_id != 0:
                loc_string = _create_localized_string(locked_tooltip_id)
                row.row_tooltip = lambda *_, loc=loc_string: loc
                row.is_enable = False
            else:
                result = cls.cell_enabled_tests.run_tests(resolver)
                row.is_enable = False
                localization_tokens = cls.get_localization_tokens(**interaction_parameters)
                row.row_tooltip = lambda *_, result_tooltip=result.tooltip, tokens=localization_tokens: result_tooltip(*tokens)
            yield row

    def _on_picker_selected(self, dialog):
        (ids, _) = dialog.get_result_definitions_and_counts()
        if dialog.multi_select:
            self.on_multi_choice_selected(ids, ingredient_check=dialog.ingredient_check)
        elif len(ids) == 1:
            tag_obj = ids[0]
            self.on_choice_selected(tag_obj, ingredient_check=dialog.ingredient_check, prepped_ingredient_check=dialog.prepped_ingredient_check)

    def on_choice_selected(self, choice_tag, **kwargs):
        body_type = choice_tag
        if body_type is not None:
            self._push_continuation(body_type)
        else:
            self._push_fallback_continuation()

class TattooDesignPicker(CASCatalogPicker):
    INSTANCE_TUNABLES = {'payment': TunablePaymentSnippet()}
