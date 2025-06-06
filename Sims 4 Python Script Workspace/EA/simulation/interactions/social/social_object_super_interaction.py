import sims4from interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import Transform, Nowherefrom objects.components import typesfrom objects.components.state import TunableStateValueVariantfrom postures import DerailReasonfrom sims4.tuning.tunable import OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import UNSETfrom socials.jigs.jig_variant import TunableJigVariantlogger = sims4.log.Logger('SocialObjectSuperInteraction', default_owner='bnguyen')
class SocialObjectSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'social_jig': OptionalTunable(description='\n            The jig used to position the sim and target for touching social interactions.\n            ', tunable=TunableJigVariant(), tuning_group=GroupNames.CORE), 'state_value_prepare': OptionalTunable(description="\n            The object state value to set on the target when the interaction is being prepared.  An interaction is\n            prepared when it enters the front of the queue, right before transitions/routes occur.\n\n            If a social_jig is tuned, this state value must map to an ObjectRoutingBehavior with a supported route type.\n            Please ask a GPE if you aren't sure which route types are supported.\n            ", tunable=TunableStateValueVariant(), tuning_group=GroupNames.CORE), 'state_value_exit': OptionalTunable(description='\n            The object state value to set on the target when the interaction is exited.  An interaction is exited when\n            it is removed from the queue for any reason.\n\n            If a social_jig is tuned, this state value must map to an ObjectRoutingBehavior.\n            ', tunable=TunableStateValueVariant(), tuning_group=GroupNames.CORE)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_value_prepare = self.state_value_prepare(self) if self.state_value_prepare is not None else None
        self._target_jig_transform_constraint = None
        self._target_start_position = None
        self._abort_preparation = False
        self._target_has_been_prepared = False
        self._behavior_run_result = None
        self._object_routing_behavior = None
        self.sim_jig_transform_constraint = None

    def _entered_pipeline(self):
        super()._entered_pipeline()
        if self._is_touching_social():
            if not self.target.has_component(types.OBJECT_ROUTING_COMPONENT):
                logger.error('Target has no ObjectRoutingComponent for <{}>', self)
                self._abort_preparation = True
                return
            self._target_start_position = self.target.position
            self._calculate_jig_transform_constraints()

    def prepare_gen(self, timeline, **kwargs):
        if self._abort_preparation:
            return InteractionQueuePreparationStatus.FAILURE
        controlling_id = self.target.get_controlling_social_interaction_id()
        if controlling_id is None:
            self.target.set_controlling_social_interaction_id(self.id)
        elif controlling_id is not self.id:
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        preparation_status = None
        if self._is_touching_social():
            preparation_status = self._prepare_touching_social()
        else:
            self._set_target_state(self._state_value_prepare)
        self._target_has_been_prepared = True
        if preparation_status is not None:
            return preparation_status
        result = yield from super().prepare_gen(timeline, **kwargs)
        return result

    def _prepare_touching_social(self):
        if not self._target_jig_transform_constraint.valid:
            return
        if not self._target_has_been_prepared:
            if self._target_start_position != self.target.position:
                self._calculate_jig_transform_constraints()
                self.transition.derail(DerailReason.CONSTRAINTS_CHANGED, self.sim)
            self._set_target_state(self._state_value_prepare)
            target_pos_constraint = Transform(self.target.intended_transform, routing_surface=self.target.routing_surface)
            intersection = self._target_jig_transform_constraint.intersect(target_pos_constraint)
            if intersection.valid:
                return
            self.target.set_social_transform_constraint(self._target_jig_transform_constraint)
            self._object_routing_behavior = self.target.get_object_routing_behavior()
            if self._object_routing_behavior is None:
                return InteractionQueuePreparationStatus.FAILURE
            self._object_routing_behavior.register_run_completed_callback(self._on_routing_behavior_run_completed)
        if self._behavior_run_result is None:
            if self._object_routing_behavior is not self.target.get_object_routing_behavior():
                self._object_routing_behavior = None
                return InteractionQueuePreparationStatus.FAILURE
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        elif self._behavior_run_result is False:
            return InteractionQueuePreparationStatus.FAILURE
        else:
            return
        return

    def _exited_pipeline(self, *args, **kwargs):
        if self.target.get_controlling_social_interaction_id() == self.id:
            self._state_value_exit = self.state_value_exit(self) if self.state_value_exit is not None else None
            self._set_target_state(self._state_value_exit)
            self.target.set_controlling_social_interaction_id(None)
        return super()._exited_pipeline(*args, **kwargs)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, **kwargs):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, **kwargs):
            yield constraint
        if inst is not None and inst.sim_jig_transform_constraint is not None:
            yield inst.sim_jig_transform_constraint

    def _calculate_jig_transform_constraints(self):
        if not self._is_touching_social():
            return
        for (actor_transform, target_transform, routing_surface, _) in self.social_jig.get_transforms_gen(self.sim, self.target):
            if actor_transform is not None and target_transform is not None and routing_surface is not None:
                self._target_jig_transform_constraint = Transform(actor_transform, routing_surface=routing_surface)
                self.sim_jig_transform_constraint = Transform(target_transform, routing_surface=routing_surface)
                self._constraint_cache.clear()
                if self.transition is not None:
                    self.transition.derail(DerailReason.CONSTRAINTS_CHANGED, self.sim)
                return
        self._target_jig_transform_constraint = Nowhere('Failed to get social jig transforms for {}', self)
        self.sim_jig_transform_constraint = Nowhere('Failed to get social jig transforms for {}', self)

    def _verify_state_value(self, state_value, check_routing_behavior=False):
        if state_value is None:
            return
        if state_value.state is None:
            logger.error('Object state value {} has no state for <{}>.', state_value, self)
            return
        if not self.target.has_state(state_value.state):
            logger.error('Target does not support object state {} for <{}>.', state_value.state, self)
            return
        if check_routing_behavior and self._is_touching_social():
            behavior = self.target.get_mapped_object_routing_behavior(state_value)
            if behavior is None:
                logger.error('Target does not have an ObjectRoutingBehavior mapped to object state value {} for <{}>.', state_value, self)
                return
            elif behavior is UNSET or not behavior(self.target).consumes_social_transform_constraint():
                logger.error('Target does not have an ObjectRoutingBehavior with a supported route type mapped to object state value {} for <{}>.', state_value, self)
                return

    def _is_touching_social(self):
        return self.social_jig is not None

    def _set_target_state(self, state_value):
        if state_value is not None:
            self.target.set_state(state_value.state, state_value)

    def _on_routing_behavior_run_completed(self, success):
        self._behavior_run_result = success
        self._object_routing_behavior = None
