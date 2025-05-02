from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from careers.career_gig import Gig
    from interactions.context import InteractionContext
    from objects.game_object import GameObject
    from scheduling import Timeline
    from sims.sim_info import SimInfo
    from ui.ui_dialog_picker import UiObjectPickerfrom collections import defaultdictfrom careers.career_enums import GigScoringBucketfrom careers.decorator_gig_picker_interaction import UiDecoratorPickerfrom event_testing.resolver import SingleSimResolverfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.loot import LootActionsfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunableEnumEntry, TunableList, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import UiOddJobPickerimport servicesimport sims4.log
class GigPickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'gig_career': TunableReference(description='\n            The Gig Career associated with this interaction.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'buckets': OptionalTunable(description='\n            If enabled, we only return Gigs from these buckets.\n            Gigs with no buckets are rejected. The order in which\n            buckets are tuned here will determine the order in which buckets\n            are shown in the picker. Gigs from the first bucket will appear\n            at the top of the picker and so on.\n            ', tunable=TunableList(tunable=TunableEnumEntry(description='\n                    Bucket to test against.\n                    ', tunable_type=GigScoringBucket, default=GigScoringBucket.DEFAULT), unique_entries=True)), 'loot_when_empty': OptionalTunable(description="\n            If enabled, we run this loot when picker is empty and don't display the empty \n            picker.\n            If disabled, picker will appear empty.\n            ", tunable=TunableList(description='\n                Loot applied if the picker is going to be empty.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))), 'disable_row_if_visibility_tests_fail': Tunable(description="\n            If checked, we will grey out any row if the corresponding gig failed its \n            visibility testing. If not checked, the row won't be shown.\n            ", tunable_type=bool, default=False), 'run_visibility_tests': Tunable(description='\n            If checked, This picker will run visibility tests on a gig to decide whether\n            it should be shown. Otherwise, all gigs will be available.\n            ', tunable_type=bool, default=True)}

    def _run_interaction_gen(self, timeline:'Timeline') -> 'bool':
        self._show_picker_dialog(self.target, target_sim=self.target)
        return True

    def _show_picker_dialog(self, owner:'SimInfo', **kwargs) -> 'None':
        if self.use_pie_menu():
            return
        dialog = self._create_dialog(owner, **kwargs)
        if self.loot_when_empty is not None and len(dialog.picker_rows) == 0:
            resolver = SingleSimResolver(owner.sim_info)
            for loot in self.loot_when_empty:
                loot.apply_to_resolver(resolver)
        else:
            dialog.show_dialog()

    @flexmethod
    def picker_rows_gen(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'None':
        inst_or_cls = inst if inst is not None else cls
        gigs = services.get_instance_manager(sims4.resources.Types.CAREER_GIG).types.values()
        if inst_or_cls.buckets:
            picker_rows_by_bucket = defaultdict(list)
        else:
            picker_rows = list()
        for gig in gigs:
            if gig.career == inst_or_cls.gig_career and not (inst_or_cls.buckets and gig.picker_scheduling_behavior is None or gig.picker_scoring is None):
                if gig.picker_scoring.bucket not in inst_or_cls.buckets:
                    pass
                else:
                    result = gig.picker_row_result(owner=target, run_visibility_tests=inst_or_cls.run_visibility_tests, disable_row_if_visibility_tests_fail=inst_or_cls.disable_row_if_visibility_tests_fail)
                    if result is not None:
                        if inst_or_cls.buckets:
                            picker_rows_by_bucket[gig.picker_scoring.bucket].append(result)
                        else:
                            picker_rows.append(result)
        if inst_or_cls.buckets:
            for bucket in inst_or_cls.buckets:
                yield from picker_rows_by_bucket[bucket]
        else:
            yield from picker_rows

    def on_choice_selected(self, choice_tag:'Gig', **kwargs) -> 'None':
        if choice_tag is None:
            return
        choice_tag.on_picker_choice(owner=self.sim.sim_info)

class OddJobGigPickerInteraction(GigPickerInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiOddJobPicker.TunableFactory(description='\n            The odd job picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING)}

    def _setup_dialog(self, dialog:'UiObjectPicker', **kwargs) -> 'None':
        super()._setup_dialog(dialog, **kwargs)
        gig_career = self.sim.career_tracker.get_career_by_uid(self.gig_career.guid64)
        if gig_career is not None:
            dialog.star_ranking = gig_career.level

    def on_multi_choice_selected(self, choice_tags, **kwargs) -> 'None':
        for choice_tag in choice_tags:
            self.on_choice_selected(choice_tag, **kwargs)

    def _get_current_selected_count(self) -> 'int':
        gig_career = self.sim.career_tracker.get_career_by_uid(self.gig_career.guid64)
        if gig_career is not None and gig_career.current_gig_limit > 1:
            return len(gig_career.get_current_gigs())
        else:
            return super()._get_current_selected_count()

class DecoratorCareerGigPickerInteraction(GigPickerInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiDecoratorPicker.TunableFactory(description='\n            The odd job picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING)}
