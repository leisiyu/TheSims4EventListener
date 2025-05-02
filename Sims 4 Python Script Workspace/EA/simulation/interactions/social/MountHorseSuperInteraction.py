from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *import servicesimport sims4from animation.asm import do_params_matchfrom carry.carry_tuning import CarryTuningfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import QueueInsertStrategyfrom interactions.constraints import ObjectJigConstraint, RequiredSlotSingle, Transform, Nowherefrom interactions.utils.user_cancelable_chain_liability import UserCancelableChainLiabilityfrom routing import Location, get_actor_pitch_roll_at_locationfrom sims.sim_info_types import Speciesfrom sims4.utils import flexmethod, classpropertyfrom _sims4_collections import frozendictfrom terrain import get_terrain_heightlogger = sims4.log.Logger('MountHorseSuperInteraction', default_owner='skorman')
class MountHorseSuperInteraction(SuperInteraction):

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, *args, **kwargs):
        if inst is not None:
            jig_liability = inst.get_liability(ObjectJigConstraint.JIG_CONSTRAINT_LIABILITY)
            if jig_liability is None:
                logger.error('{} has no jig liability. Make sure it is tuned as a continuation of an interaction with jig constraints.', inst)
                return
            jig_id = jig_liability.jig.id
            jig_liability.release_on_start_carry = True
            if inst.target.is_riding_horse:
                return Nowhere("Can't mount a horse if a sim is already riding one.")
            if sim.species == Species.HORSE:
                yield Transform(sim.intended_transform, routing_surface=sim.intended_routing_surface, objects_to_ignore=(jig_id,), debug_name='SimCurrentPosition')
                return
            for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, **kwargs):
                yield constraint
            animation_element = inst.canonical_animation
            if animation_element is None:
                logger.error('{} needs a canonical animation!', inst)
                return
            asm_key = animation_element.asm_key
            actor_name = animation_element.actor_name
            target_name = animation_element.target_name
            carry_target_name = animation_element.carry_target_name
            state_name = animation_element.begin_states[0]
            participant_name = actor_name if sim is inst.sim else target_name
            asm = inst.get_asm(asm_key, actor_name, target_name, carry_target_name)
            intended_location = inst.sim.intended_location
            location = Location(intended_location.transform.translation, intended_location.transform.orientation, intended_location.routing_surface)
            (pitch, _) = get_actor_pitch_roll_at_location('x', 0, services.active_lot_id() or 0, location)
            asm.set_parameter('pitch', pitch)
            all_parameters = asm.get_all_parameters()
            param_dict = {}
            for param_set in all_parameters:
                for param_set_key in param_set.keys():
                    if type(param_set_key) == str:
                        param_dict.update(param_set)
                    elif participant_name is param_set_key[1]:
                        param_dict.update({tuple(key[:-1]): value for (key, value) in param_set.items()})
                    break
            asm.dirty_boundary_conditions()
            boundary_conditions = asm.get_boundary_conditions_list(sim, state_name, locked_params=frozendict(param_dict), target=target)
            param_dict.update({(param, target_name): value for (param, value) in sim._anim_overrides_internal.params.items()})
            for (_, slots_to_params_entry) in boundary_conditions:
                if not slots_to_params_entry:
                    pass
                else:
                    slots_to_params_entry_absolute = []
                    for (boundary_condition_entry, param_sequences_entry) in slots_to_params_entry:
                        (routing_transform_entry, containment_transform, _, reference_joint_exit) = boundary_condition_entry.get_transforms(asm, target)
                        slots_to_params_entry_absolute.append((routing_transform_entry, reference_joint_exit, param_sequences_entry))
                        if not any(do_params_match(param_sequence, param_dict) for param_sequence in param_sequences_entry):
                            break
                    terrain_height = get_terrain_height(containment_transform.translation.x, containment_transform.translation.z, location.routing_surface)
                    heightDelta = terrain_height - containment_transform.translation.y
                    distance_between_sim_and_horse = (location.transform.translation - containment_transform.translation).magnitude()
                    uphill_angle = sims4.math.rad_to_deg(sims4.math.atan2(heightDelta, distance_between_sim_and_horse))
                    asm.set_parameter('uphillAngle', uphill_angle)
                    yield RequiredSlotSingle(sim, target, asm, asm_key, None, actor_name, target_name, state_name, containment_transform, None, tuple(slots_to_params_entry_absolute), None, asm_name=asm.name, objects_to_ignore=(jig_id,))

    @classproperty
    def use_constraint_cache(cls):
        return False

    def prepare_gen(self, timeline, cancel_incompatible_carry_interactions=False):
        if not self.try_link_interaction_to_target():
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        return super().prepare_gen(timeline, cancel_incompatible_carry_interactions)

    def try_link_interaction_to_target(self) -> 'bool':
        if self.target is not None and self.target.is_sim:
            carried_context = self.context.clone_for_sim(self.target, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True, target_sim_id=self.sim.id)
            result = self.target.push_super_affordance(CarryTuning.CARRIED_SIM_PROXY_AFFORDANCE, self.sim, carried_context, proxied_interaction=self)
            if not result:
                return False
            else:
                interaction_pushed = result.interaction
                self.attach_interaction(interaction_pushed)
                interaction_pushed.attach_interaction(self)
                user_cancel_chain = self.get_liability(UserCancelableChainLiability.LIABILITY_TOKEN)
                if user_cancel_chain is not None:
                    interaction_pushed.add_liability(UserCancelableChainLiability.LIABILITY_TOKEN, user_cancel_chain)
                return True
        return False
