from autonomy.autonomy_modes import FullAutonomyfrom autonomy.autonomy_request import AutonomyRequestfrom event_testing.resolver import SingleSimResolverfrom interactions.aop import AffordanceObjectPairfrom interactions.base.super_interaction import RallySourcefrom interactions.context import QueueInsertStrategy, InteractionContextfrom interactions.priority import Priorityfrom objects.base_interactions import ProxyInteractionfrom sims.party import Partyfrom sims4.utils import classproperty, flexmethodfrom singletons import DEFAULTimport servicesimport sims4.logimport singletonslogger = sims4.log.Logger('RallyInteraction', default_owner='jdimailig')
class RallyInteraction(ProxyInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classproperty
    def proxy_name(cls):
        return '[Rally]'

    def __init__(self, *args, from_rally_interaction=None, push_social=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._rally_targets = None
        self._from_rally_interaction = from_rally_interaction
        self._push_social = push_social
        self.preferred_carrying_sims = set()
        self._eligible_carryable_sims = set()
        self._eligible_carrying_sims = set()

    @classmethod
    def generate(cls, proxied_affordance, rally_tag, rally_level, rally_data, rally_push_social=None, rally_constraint=None, rally_sources=(), rally_pie_menu_icon=None, rally_allow_forward=False, rally_carry_rule=None):
        rally_affordance = proxied_affordance
        result = super().generate(rally_affordance)
        result.rally_tag = rally_tag
        result.rally_level = rally_level
        result.rally_data = rally_data
        result.rally_push_social = rally_push_social
        result.rally_constraint = rally_constraint
        result.rally_sources = rally_sources
        if rally_pie_menu_icon is not None:
            result.pie_menu_icon = rally_pie_menu_icon
        result.rally_allow_forward = rally_allow_forward
        result.rally_carry_rule = rally_carry_rule
        return result

    @classproperty
    def is_rally_interaction(cls):
        return True

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        yield AffordanceObjectPair(cls, target, cls, None, **kwargs)

    @classmethod
    def generate_continuation_affordance(cls, affordance, **kwargs):
        return RallyInteraction.generate(affordance, rally_tag=cls.rally_tag, rally_level=cls.rally_level + 1, rally_data=None, rally_sources=cls.rally_sources, **kwargs)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        if inst is not None or cls.rally_data is None:
            return super(ProxyInteraction, inst)._get_name(target=target, context=context, **kwargs)
        original_name = super(ProxyInteraction, cls)._get_name(target=target, context=context, **kwargs)
        return cls.rally_data.get_display_name(original_name)

    @classmethod
    def autonomy_ads_gen(cls, *args, **kwargs):
        for op in Party.RALLY_FALSE_ADS:
            cls._add_autonomy_ad(op, overwrite=False)
        for ad in super().autonomy_ads_gen(*args, **kwargs):
            yield ad
        for op in Party.RALLY_FALSE_ADS:
            cls._remove_autonomy_ad(op)

    @flexmethod
    def _constraint_gen(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for constraint in super(__class__, inst_or_cls)._constraint_gen(*args, **kwargs):
            yield constraint
        if cls.rally_constraint is not None:
            yield cls.rally_constraint

    def _run_interaction_gen(self, timeline):
        main_group = self.sim.get_visible_group()
        if self._push_social is not None and main_group is None:
            context = InteractionContext(self.sim, InteractionContext.SOURCE_SCRIPT, self.context.priority)
            self.sim.push_super_affordance(self._push_social, self._from_rally_interaction.sim, context)
        yield from super()._run_interaction_gen(timeline)

    def disable_displace(self, other):
        if isinstance(other, RallyInteraction):
            return self._from_rally_interaction is other or other._from_rally_interaction is self
        return False

    def excluded_posture_destination_objects(self):
        excluded = set()
        if self._from_rally_interaction is None or self._from_rally_interaction.transition is None:
            return excluded
        for dest in self._from_rally_interaction.transition.final_destinations_gen():
            if dest.body_target is not None:
                excluded.add(dest.body_target)
        return excluded

    def _get_rally_affordance_target(self):
        affordance_target_type = self.rally_data.affordance_target
        if affordance_target_type is not None:
            return self.get_participant(affordance_target_type)
        return affordance_target_type

    def _do_rally_behavior(self, sim, constraint):
        if sim is self.sim:
            return False
        if sim in self.preferred_carrying_sims:
            return False
        preferred_carrying_sim = None
        if sim in self._eligible_carryable_sims:
            preferred_carrying_sim = self._get_preferred_carrying_sim()
        if self.rally_data is None:
            return False
        if self.rally_constraint is not None:
            constraint = self.rally_constraint
        context = self.context.clone_for_sim(sim, insert_strategy=QueueInsertStrategy.NEXT, preferred_carrying_sim=preferred_carrying_sim)
        self.rally_data.do_behavior(rally_interaction=self, sim=sim, preferred_carrying_sim=preferred_carrying_sim, constraint=constraint, context=context)

    def _process_for_carry(self, group_sims_list):
        if self.rally_carry_rule is None:
            return
        carryable_sim_eligibility_tests = self.rally_carry_rule.carryable_sim_eligibility_tests
        carrying_sim_eligibility_tests = self.rally_carry_rule.carrying_sim_eligibility_tests
        for sim in group_sims_list:
            resolver = SingleSimResolver(sim.sim_info)
            if carryable_sim_eligibility_tests.run_tests(resolver):
                self._eligible_carryable_sims.add(sim)
            elif carrying_sim_eligibility_tests.run_tests(resolver):
                self._eligible_carrying_sims.add(sim)
        if self.sim in self._eligible_carryable_sims and self.context.preferred_carrying_sim is None:
            preferred_carrying_sim = self._get_preferred_carrying_sim()
            if preferred_carrying_sim is not None:
                self.context.preferred_carrying_sim = preferred_carrying_sim
                self.preferred_carrying_sims.add(preferred_carrying_sim)
        group_sims_list.sort(key=lambda s: s in self._eligible_carryable_sims, reverse=True)

    def _get_preferred_carrying_sim(self):
        carrying_sim_list = list(self._eligible_carrying_sims)
        preferred_carrying_sim = next(iter(sim for sim in carrying_sim_list if sim not in self.preferred_carrying_sims), None)
        if preferred_carrying_sim is None:
            return next(iter(carrying_sim_list), None)
        return preferred_carrying_sim

    def maybe_bring_group_along(self, **kwargs):
        if not self.should_rally:
            return
        anchor_object = self.target
        if anchor_object.is_part:
            anchor_object = anchor_object.part_owner
        if anchor_object is not None and RallySource.SOCIAL_GROUP in self.rally_sources:
            main_group = self.sim.get_visible_group()
            if main_group:
                main_group.try_relocate_around_focus(self.sim, priority=self.priority)
                main_group_sims_list = list(main_group)
                self._process_for_carry(main_group_sims_list)
                for sim in main_group_sims_list:
                    self._do_rally_behavior(sim, main_group.get_constraint(sim))
        else:
            main_group = None
        if RallySource.ENSEMBLE in self.rally_sources:
            ensemble_sims = services.ensemble_service().get_ensemble_sims_for_rally(self.sim)
            if ensemble_sims:
                main_group_sims = set(main_group) if main_group else singletons.EMPTY_SET
                ensemble_sims -= main_group_sims
                ensemble_sims_list = list(ensemble_sims)
                self._process_for_carry(ensemble_sims_list)
                for sim in ensemble_sims_list:
                    self._do_rally_behavior(sim, None)

    @property
    def should_rally(self):
        if self._pushed_waiting_line:
            return False
        if self._from_rally_interaction is None:
            if RallySource.SOCIAL_GROUP in self.rally_sources:
                main_group = self.sim.get_visible_group()
                if main_group is not None and not main_group.is_solo:
                    return True
                elif RallySource.ENSEMBLE in self.rally_sources:
                    ensemble_sims = services.ensemble_service().get_ensemble_sims_for_rally(self.sim)
                    if ensemble_sims:
                        return True
            elif RallySource.ENSEMBLE in self.rally_sources:
                ensemble_sims = services.ensemble_service().get_ensemble_sims_for_rally(self.sim)
                if ensemble_sims:
                    return True
        return False
