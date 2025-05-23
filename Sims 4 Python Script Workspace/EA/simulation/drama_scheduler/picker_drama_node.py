from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from event_testing.resolver import Resolverimport elementsimport enumimport randomfrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeRunOutcomefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.tests import TunableTestSetWithTooltipfrom interactions import ParticipantTypefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableEnumEntry, TunableResourceKeyfrom sims4.utils import classpropertyimport id_generatorimport servicesimport sims4.loglogger = sims4.log.Logger('PickerDramaNode', default_owner='bosee')
class _PickerDramaNodeBehavior(HasTunableSingletonFactory, AutoFactoryInit):

    def _save_custom_data(self, writer):
        pass

    def _load_custom_data(self, reader):
        return True

    def create_picker_row(self, owner=None, **kwargs):
        raise NotImplementedError

    def on_picked(self, owner=None, associated_sim_info=None):
        raise NotImplementedError

class _ScheduleDramaNodePickerBehavior(_PickerDramaNodeBehavior):
    FACTORY_TUNABLES = {'drama_node': TunableReference(description='\n            Drama node to schedule.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_node = None

    def create_picker_row(self, owner, **kwargs):
        uid = id_generator.generate_object_id()
        self._saved_node = self.drama_node(uid)
        picker_row = self._saved_node.create_picker_row(owner=owner)
        return picker_row

    def on_picked(self, owner=None, associated_sim_info=None):
        services.drama_scheduler_service().schedule_node(self.drama_node, SingleSimResolver(owner), specific_time=self._saved_node.get_picker_schedule_time(), drama_inst=self._saved_node)

class _ScheduleCareerGigPickerBehavior(_PickerDramaNodeBehavior):
    FACTORY_TUNABLES = {'career_gig': TunableReference(description='\n            Career gig to schedule.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_GIG), class_restrictions=('Gig',)), 'allow_add_career': Tunable(description="\n            If tuned, picking this drama node will add the required career\n            if the sim doesn't already have it. If not tuned, trying to add a\n            gig for a career the sim doesn't have will throw an error.\n            ", tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduled_time = None

    def create_picker_row(self, owner, associated_sim_info=None, associated_sim_thumbnail_override=None, associated_sim_background=None, enabled=True, **kwargs):
        now = services.time_service().sim_now
        time_till_gig = self.career_gig.get_time_until_next_possible_gig(now)
        if time_till_gig is None:
            return
        self._scheduled_time = now + time_till_gig
        picker_row = self.career_gig.create_picker_row(scheduled_time=self._scheduled_time, owner=owner, gig_customer=associated_sim_info, customer_thumbnail_override=associated_sim_thumbnail_override, customer_background=associated_sim_background, enabled=enabled, **kwargs)
        return picker_row

    def on_picked(self, owner=None, associated_sim_info=None):
        sim_info = SingleSimResolver(owner).get_participant(ParticipantType.Actor)
        career = sim_info.career_tracker.get_career_by_uid(self.career_gig.career.guid64)
        if career is None:
            if self.allow_add_career:
                sim_info.career_tracker.add_career(self.career_gig.career(sim_info))
            else:
                logger.error('Tried to add gig {} to missing career {} on sim {}', self.career_gig, self.career_gig.career, sim_info)
                return
        self._set_gig(sim_info, associated_sim_info=associated_sim_info)

    def _set_gig(self, sim_info, associated_sim_info=None):
        sim_info.career_tracker.set_gig(self.career_gig, self._scheduled_time, gig_customer=associated_sim_info)

class _ScheduleDecoratorCareerGigPickerBehavior(_ScheduleCareerGigPickerBehavior):
    GIG_BUDGET_TOKEN = 'gig_budget'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gig_budget = None

    def _save_custom_data(self, writer):
        if self._gig_budget is not None:
            writer.write_uint64(self.GIG_BUDGET_TOKEN, self._gig_budget)

    def _load_custom_data(self, reader):
        self._gig_budget = reader.read_uint64(self.GIG_BUDGET_TOKEN, None)
        return True

    def create_picker_row(self, *args, **kwargs):
        if self._gig_budget is None:
            self._gig_budget = self.career_gig.create_gig_budget()
        return super().create_picker_row(*args, gig_budget=self._gig_budget, **kwargs)

    def _set_gig(self, sim_info, associated_sim_info=None):
        sim_info.career_tracker.set_gig(self.career_gig, self._scheduled_time, gig_customer=associated_sim_info, gig_budget=self._gig_budget)

class PickBehavior(enum.Int):
    DO_NOTHING = 0
    REMOVE = 1
    DISABLE_FOR_PICKING_SIM = 2
    DISABLE_FOR_ALL_SIMS = 3

class PickerDramaNode(BaseDramaNode, AutoFactoryInit):
    SIM_ID_TOKEN = 'associated_sim_id'
    DISABLE_SIM_IDS_TOKEN = 'disable_sim_ids'
    DISABLED_TOKEN = 'disabled'
    INSTANCE_TUNABLES = {'behavior': TunableVariant(schedule_drama_node=_ScheduleDramaNodePickerBehavior.TunableFactory(description='\n                Drama node to schedule should the player pick this to run.\n                '), schedule_career_gig=_ScheduleCareerGigPickerBehavior.TunableFactory(description='\n                A gig to schedule should the player pick this to run.\n                '), schedule_decorator_gig=_ScheduleDecoratorCareerGigPickerBehavior.TunableFactory(description='\n                A decorator gig to schedule should the player pick this to run.\n                ')), 'associated_sim_filter': OptionalTunable(description='\n            If tuned, will associate a sim with this drama node. Because they do\n            not have receivers or senders, picker drama nodes do not support the\n            normal flow for non-simless drama nodes.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER))), 'associated_sim_name_override': OptionalTunable(description='\n            If enabled and tuned, this string will be used for the name of the \n            associated Sim. \n            ', tunable=TunableLocalizedString(description="\n                The string to use in place of the associated Sim's name. This is\n                currently only supported by Mission Gigs.\n                ")), 'associated_sim_thumbnail_override': OptionalTunable(description='\n            If enabled, an override thumbnail can be used in place of the tuned Associated Sim Filter.\n            ', tunable=TunableResourceKey(description="\n                The image to use for the Associated Sim's thumbnail.\n                ", resource_types=sims4.resources.CompoundTypes.IMAGE)), 'associated_sim_thumbnail_background': OptionalTunable(description="\n            If enabled, the background behind the Associated Sim's thumbnail, or\n            the thumbnail override, will use this image.\n            ", tunable=TunableResourceKey(description="\n                The image to use for the Associated Sim's background.\n                ", resource_types=sims4.resources.CompoundTypes.IMAGE)), 'visibility_tests': TunableTestSetWithTooltip(description='\n            Tests that will be run on the picker owner of this PickerDramaNode\n            to determine if this node should appear in a picker.\n            '), 'disable_if_visibility_tests_fail_with_tooltip': Tunable(description='\n            If checked, when the Visibility Tests fail and a tooltip is provided, \n            this entry will show in the picker but be disabled. This tuning works  \n            independently of the Disable Row If Visibility Tests Fail tunable in \n            Drama Node Picker Interaction.\n            ', tunable_type=bool, default=False), 'on_pick_behavior': TunableEnumEntry(description='\n             Determines what happens to this PickerDramaNode if it is picked in\n             a picker. \n             ', tunable_type=PickBehavior, default=PickBehavior.DO_NOTHING), 'replace_if_removed': Tunable(description='\n            If True, whenever we remove this node because it was selected in a picker, we will replace it with a new\n            valid node from the same bucket.\n            ', tunable_type=bool, default=False)}

    def __init__(self, uid=None, **kwargs):
        super().__init__(uid=uid, **kwargs)
        self._associated_sim_info = None
        self._disable_sim_ids = set() if self.on_pick_behavior == PickBehavior.DISABLE_FOR_PICKING_SIM else None
        self._disabled = False

    @classproperty
    def persist_when_active(cls):
        return False

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.PICKER

    @classproperty
    def simless(cls):
        return True

    def _async_setup_associated_sim_info(self) -> 'bool':

        def _on_filter_request_complete(results, *_, **__):
            if self._associated_sim_info is not None:
                return
            if not results:
                return
            chosen_result = sims4.random.pop_weighted([(result.score, result) for result in results])
            self._associated_sim_info = chosen_result.sim_info

        if self.associated_sim_filter is not None:
            services.sim_filter_service().submit_filter(self.associated_sim_filter, callback=_on_filter_request_complete, allow_yielding=True, gsi_source_fn=self.get_sim_filter_gsi_name)

    def setup(self, resolver:'Resolver', for_scoring:'bool'=False, **kwargs) -> 'bool':
        if not for_scoring:
            self._async_setup_associated_sim_info()
        return super().setup(resolver, for_scoring=for_scoring, **kwargs)

    def finish_deferred_setup(self) -> 'None':
        self._async_setup_associated_sim_info()

    def _run(self):
        return DramaNodeRunOutcome.SUCCESS_NODE_COMPLETE

    def on_picker_choice(self, owner=None):
        if self.on_pick_behavior == PickBehavior.REMOVE:
            if self.replace_if_removed:
                selected_time = self.selected_time

                def schedule_new_node(timeline):
                    try:
                        nodes_in_bucket = []
                        for drama_node in services.get_instance_manager(sims4.resources.Types.DRAMA_NODE).types.values():
                            if drama_node.scoring and drama_node.scoring.bucket == self.scoring.bucket:
                                nodes_in_bucket.append(drama_node)
                        yield from services.drama_scheduler_service().score_and_schedule_nodes_gen(nodes_in_bucket, 1, specific_time=selected_time, zone_id=services.current_zone_id(), timeline=timeline)
                    except GeneratorExit:
                        raise
                    except Exception as exception:
                        logger.exception('Exception while replacing a drama node', exc=exception, level=sims4.log.LEVEL_ERROR)
                    finally:
                        self._element = None

                sim_timeline = services.time_service().sim_timeline
                self._element = sim_timeline.schedule(elements.GeneratorElement(schedule_new_node))
            if self._uid is not None:
                services.drama_scheduler_service().cancel_scheduled_node(self._uid)
        elif self.on_pick_behavior == PickBehavior.DISABLE_FOR_PICKING_SIM:
            self._disable_sim_ids.add(owner.id)
        elif self.on_pick_behavior == PickBehavior.DISABLE_FOR_ALL_SIMS:
            self._disabled = True
        self.behavior.on_picked(owner=owner, associated_sim_info=self._associated_sim_info)

    def _save_custom_data(self, writer):
        if self._disable_sim_ids:
            writer.write_uint64s(self.DISABLE_SIM_IDS_TOKEN, self._disable_sim_ids)
        if self._associated_sim_info is not None:
            writer.write_uint64(self.SIM_ID_TOKEN, self._associated_sim_info.id)
        if self.on_pick_behavior == PickBehavior.DISABLE_FOR_ALL_SIMS:
            writer.write_bool(self.DISABLED_TOKEN, self._disabled)
        self.behavior._save_custom_data(writer)

    def _load_custom_data(self, reader):
        if self.associated_sim_filter is not None:
            sim_info_id = reader.read_uint64(self.SIM_ID_TOKEN, None)
            if sim_info_id:
                self._associated_sim_info = services.sim_info_manager().get(sim_info_id)
                if self._associated_sim_info is None:
                    return False
        if self.on_pick_behavior == PickBehavior.DISABLE_FOR_PICKING_SIM:
            self._disable_sim_ids = reader.read_uint64s(self.DISABLE_SIM_IDS_TOKEN, set())
        if self.on_pick_behavior == PickBehavior.DISABLE_FOR_ALL_SIMS:
            self._disabled = reader.read_bool(self.DISABLED_TOKEN, False)
        return self.behavior._load_custom_data(reader)

    def create_picker_row(self, owner=None, run_visibility_tests=True, disable_row_if_visibily_tests_fail=False, **kwargs):
        enabled = True
        tooltip_override = None
        if self.associated_sim_filter is not None and self._associated_sim_info is None:
            results = services.sim_filter_service().submit_filter(self.associated_sim_filter, callback=None, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
            if results:
                self._associated_sim_info = random.choice(results).sim_info
            else:
                return
        if owner is not None:
            if self._associated_sim_info:
                resolver = DoubleSimResolver(owner, self._associated_sim_info)
            else:
                resolver = SingleSimResolver(owner)
            result = self.visibility_tests.run_tests(resolver)
            if not result:
                tooltip_override = result.tooltip
                if disable_row_if_visibily_tests_fail or self.disable_if_visibility_tests_fail_with_tooltip and tooltip_override:
                    enabled = False
                else:
                    return
        if run_visibility_tests and self._disable_sim_ids is not None and owner.id in self._disable_sim_ids:
            enabled = False
        elif self._disabled:
            enabled = False
        picker_row = self.behavior.create_picker_row(owner=owner, associated_sim_info=self._associated_sim_info, associated_sim_thumbnail_override=self.associated_sim_thumbnail_override, associated_sim_background=self.associated_sim_thumbnail_background, customer_name=self.associated_sim_name_override, enabled=enabled)
        if picker_row is not None:
            picker_row.tag = self
            if tooltip_override:
                picker_row.row_tooltip = lambda *_: tooltip_override(owner)
        return picker_row

    REMOVE_INSTANCE_TUNABLES = ('receiver_sim', 'sender_sim_info', 'picked_sim_info')
lock_instance_tunables(PickerDramaNode, allow_during_work_hours=True)