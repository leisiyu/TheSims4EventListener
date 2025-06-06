from event_testing.resolver import DoubleSimResolverfrom interactions import ParticipantTypefrom interactions.base.picker_interaction import PickerSuperInteractionfrom social_media import SocialMediaPostTypefrom social_media.social_media_tuning import SocialMediaTunablesimport sims4.hash_utilfrom sims4.tuning.tunable import TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import TunablePickerDialogVariant, ObjectPickerRow, ObjectPickerTuningFlagsimport enumimport services
class SocialMediaPickerContentType(enum.Int):
    POST_TYPE = 0
    CONTEXT_POST = 1
    CONTEXT_NARRATIVE = 2

class SocialMediaPickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The type of post picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.OBJECT, tuning_group=GroupNames.PICKERTUNING), 'post_type': TunableEnumEntry(description='\n            A SocialMediaPostType enum entry.\n            ', tunable_type=SocialMediaPostType, default=SocialMediaPostType.DEFAULT, tuning_group=GroupNames.PICKERTUNING), 'picker_content_type': TunableEnumEntry(description='\n            A SocialMediaPickerContentType enum entry.\n            ', tunable_type=SocialMediaPickerContentType, default=SocialMediaPickerContentType.POST_TYPE, tuning_group=GroupNames.PICKERTUNING)}

    @property
    def _dialog_target(self):
        dialog_target = self.get_participant(ParticipantType.PickedSim)
        if dialog_target is None:
            return self.target
        return dialog_target

    def _run_interaction_gen(self, timeline):
        dialog_target = self._dialog_target
        self._show_picker_dialog(dialog_target, target_sim=dialog_target)
        return True

    def _show_picker_dialog(self, owner, **kwargs):
        if self.use_pie_menu():
            return
        dialog = self._create_dialog(owner, **kwargs)
        if len(dialog.picker_rows) > 0:
            dialog.show_dialog()

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, sim, **kwargs):
        social_media_service = services.get_social_media_service()
        if social_media_service is None:
            super().picker_rows_gen(cls, inst, target, context, **kwargs)
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.picker_content_type == SocialMediaPickerContentType.POST_TYPE:
            yield from inst_or_cls.get_post_picker_row_gen(False, sim, target)
        elif inst_or_cls.picker_content_type == SocialMediaPickerContentType.CONTEXT_NARRATIVE:
            yield from inst_or_cls.get_post_picker_row_gen(True, sim, target)
        elif inst_or_cls.picker_content_type == SocialMediaPickerContentType.CONTEXT_POST:
            yield from inst_or_cls.get_context_post_picker_row_gen(sim)

    @flexmethod
    def get_post_picker_row_gen(cls, inst, check_context_post=False, target=None, author=None):
        available_narratives = dict()
        inst_or_cls = inst if inst is not None else cls
        for post_type in SocialMediaTunables.TYPES_OF_POSTS:
            if post_type.post_type != inst_or_cls.post_type:
                pass
            elif post_type.context_post is None == check_context_post:
                pass
            else:
                available_narratives[post_type.narrative] = []
                if post_type.context_post is None or target is None or not target.sim_info.Buffs.has_buff(post_type.context_post.buff_type) or post_type.narrative not in available_narratives and post_type.context_post is not None:
                    available_narratives[post_type.narrative].append(post_type.context_post.buff_type)
        for narrative_type in SocialMediaTunables.SOCIAL_MEDIA_NARRATIVE_TUNING:
            if narrative_type.narrative not in available_narratives:
                pass
            elif author.relationship_tracker.has_any_bits(target.sim_id, narrative_type.blacklist_rel_bit):
                pass
            else:
                resolver = DoubleSimResolver(author.sim_info, target.sim_info)
                if not narrative_type.targeted_availability_tests.run_tests(resolver):
                    pass
                else:
                    if check_context_post:
                        second_tag_list = [x.buff_name().hash for x in available_narratives.get(narrative_type.narrative, [])]
                    else:
                        second_tag_list = list(item().guid64 for item in narrative_type.blacklist_rel_bit)
                    yield ObjectPickerRow(option_id=narrative_type.narrative, name=narrative_type.picker_name, icon_info=narrative_type.picker_icon(None), row_description=narrative_type.picker_description, tag=narrative_type, second_tag_list=second_tag_list)

    @flexmethod
    def get_context_post_picker_row_gen(cls, inst, target):
        buffs_serviced = []
        event_count = 0
        for event_type in SocialMediaTunables.TYPES_OF_POSTS:
            event_count = event_count + 1
            if event_type.post_type != SocialMediaPostType.DEFAULT or not event_type.context_post is None:
                if event_type.context_post in buffs_serviced:
                    pass
                elif target.sim_info.Buffs.has_buff(event_type.context_post.buff_type):
                    context_buff = event_type.context_post
                    buffs_serviced.append(context_buff)
                    yield ObjectPickerRow(option_id=event_count*100 + event_type.narrative.value, name=context_buff.buff_name(target.sim_info), icon=context_buff.icon, row_description=context_buff.buff_description, tag=event_type)

    def _setup_dialog(self, dialog, **kwargs):
        for row in self.picker_rows_gen(self._dialog_target, self.context, self.sim, **kwargs):
            dialog.add_row(row)

    def _on_picker_selected(self, dialog):
        selected_rows = dialog.get_result_rows()
        if selected_rows:
            self.on_choice_selected(selected_rows[0])

    def on_choice_selected(self, picked_choice, **kwargs):
        if picked_choice is None:
            return
        social_media_service = services.get_social_media_service()
        if social_media_service is None:
            return
        if self.picker_content_type == SocialMediaPickerContentType.POST_TYPE:
            narrative = picked_choice.option_id
            social_media_service.create_post(self.post_type, self.sim.sim_info.sim_id, self._dialog_target.sim_info.sim_id, narrative)
        elif self.picker_content_type == SocialMediaPickerContentType.CONTEXT_POST or self.picker_content_type == SocialMediaPickerContentType.CONTEXT_NARRATIVE:
            narrative = picked_choice.option_id
            dialog_target = self._dialog_target
            target_sim_id = dialog_target.sim_info.sim_id if dialog_target is not None else None
            social_media_service.create_post(SocialMediaPostType.DEFAULT, self.sim.sim_info.sim_id, target_sim_id, narrative)
