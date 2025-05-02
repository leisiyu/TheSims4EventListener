from _math import Vector2, Transform, Vector3from animation import get_throwaway_animation_contextfrom animation.animation_utils import StubActorfrom animation.asm import create_asm, do_params_matchfrom interactions.utils.animation_reference import TunableAnimationReferencefrom postures import PostureTrackfrom routing import FootprintTypefrom sims.sim_info_types import SpeciesExtendedfrom sims4.collections import frozendictfrom sims4.geometry import PolygonFootprintfrom sims4.math import yaw_quaternion_to_angle, vector3_rotate_axis_anglefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableEnumEntryfrom socials.jigs.jig_utils import get_default_reserve_space, generate_jig_polygon, _generate_poly_points, JigPositioning
class SocialJigAnimation(AutoFactoryInit, HasTunableSingletonFactory):

    @staticmethod
    def on_tunable_loaded_callback(instance_class, tunable_name, source, value):
        animation_element = value.canonical_animation
        asm_key = animation_element.asm_key
        actor_name = animation_element.actor_name
        target_name = animation_element.target_name
        state_name = animation_element.begin_states[0]
        actor = StubActor(1)
        target = StubActor(2)
        animation_context = get_throwaway_animation_context()
        asm = create_asm(asm_key, context=animation_context)
        asm.set_actor(actor_name, actor)
        asm.set_actor(target_name, target)
        for posture_manifest_entry in asm.get_supported_postures_for_actor(actor_name).get_constraint_version():
            for posture_type in posture_manifest_entry.posture_types:
                if posture_type.mobile:
                    break
            break
        posture_type = None
        available_transforms = []
        if posture_type is not None:
            posture = posture_type(actor, None, PostureTrack.BODY, animation_context=animation_context)
            boundary_conditions = asm.get_boundary_conditions_list(actor, state_name, posture=posture, target=target)
            for (_, slots_to_params_entry) in boundary_conditions:
                if not slots_to_params_entry:
                    pass
                else:
                    for (boundary_condition_entry, param_sequences_entry) in slots_to_params_entry:
                        (relative_transform, _, _, _) = boundary_condition_entry.get_transforms(asm, target)
                        available_transforms.append((param_sequences_entry, relative_transform))
        setattr(value, 'available_transforms', available_transforms)

    FACTORY_TUNABLES = {'canonical_animation': TunableAnimationReference(description="\n            The canonical animation element used to generate social positioning\n            for this group.\n            \n            The animation must include a target actor (such as 'y') whose\n            relative positioning from an actor, such as 'x' defines the\n            positioning.\n            ", callback=None), 'reverse_actor_sim_orientation': Tunable(description='\n            If checked then we will reverse the orientation of the actor Sim\n            when generating this jig. \n            ', tunable_type=bool, default=False), 'ignore_posture_jig': Tunable(description='\n            If checked, we will ignore the posture jigs of actor and target sims\n            on finding a good location for the social jig.\n            ', tunable_type=bool, default=False), 'jig_positioning_type': TunableEnumEntry(description='\n            Determines the type of positioning used for this Jig.\n            The other sim will come over to the relative sim.\n            ', tunable_type=JigPositioning, default=JigPositioning.RelativeToSimB, invalid_enums=(JigPositioning.RelativeToSingleParticipant,)), 'callback': on_tunable_loaded_callback}

    def _get_available_transforms_gen(self, actor, target):
        animation_element = self.canonical_animation
        actor_name = animation_element.actor_name
        target_name = animation_element.target_name
        actor_age = actor.age.age_for_animation_cache
        target_age = target.age.age_for_animation_cache
        locked_params = {('age', target_name): target_age.animation_age_param, ('species', target_name): SpeciesExtended.get_animation_species_param(target.extended_species), ('age', actor_name): actor_age.animation_age_param, ('species', actor_name): SpeciesExtended.get_animation_species_param(actor.extended_species)}
        for (param_sequences, transform) in self.available_transforms:
            for param_sequence in param_sequences:
                if not do_params_match(param_sequence, locked_params):
                    pass
                else:
                    jig_params = frozendict({param: value for (param, value) in param_sequence.items() if param not in locked_params})
                    yield (transform, jig_params)

    def get_transforms_gen(self, actor, target, fallback_routing_surface=None, fgl_kwargs=None, **kwargs):
        reserved_space_a = get_default_reserve_space(actor.species, actor.age)
        reserved_space_b = get_default_reserve_space(target.species, target.age)
        fgl_kwargs = fgl_kwargs if fgl_kwargs is not None else {}
        ignored_objects = {sim.id for sim in (actor, target)}
        ignored_ids = fgl_kwargs.get('ignored_object_ids')
        if actor.posture._jig_instance is not None:
            ignored_objects.add(actor.posture._jig_instance.id)
        if self.ignore_posture_jig and target.posture._jig_instance is not None:
            ignored_objects.add(target.posture._jig_instance.id)
        if ignored_ids is not None:
            ignored_objects.update(ignored_ids)
        fgl_kwargs['ignored_object_ids'] = ignored_objects
        for (transform, jig_params) in self._get_available_transforms_gen(actor, target):
            actor_angle = yaw_quaternion_to_angle(transform.orientation)
            if self.jig_positioning_type == JigPositioning.RelativeToSimA:
                pos_a = Vector2.ZERO()
                rot_a = 0
                pos_b = vector3_rotate_axis_angle(-1*transform.translation, -actor_angle, Vector3.Y_AXIS())
                rot_b = -actor_angle
            else:
                pos_a = transform.translation
                rot_a = actor_angle
                pos_b = Vector2.ZERO()
                rot_b = 0
            (translation_a, orientation_a, translation_b, orientation_b, routing_surface) = generate_jig_polygon(actor.location, pos_a, rot_a, target.location, pos_b, rot_b, reserved_space_a.left, reserved_space_a.right, reserved_space_a.front, reserved_space_a.back, reserved_space_b.left, reserved_space_b.right, reserved_space_b.front, reserved_space_b.back, fallback_routing_surface=fallback_routing_surface, reverse_nonreletive_sim_orientation=self.reverse_actor_sim_orientation, positioning_type=self.jig_positioning_type, **fgl_kwargs)
            if translation_a is None:
                pass
            else:
                yield (Transform(translation_a, orientation_a), Transform(translation_b, orientation_b), routing_surface, jig_params)

    def get_footprint_polygon(self, sim_a, sim_b, sim_a_transform, sim_b_transform, routing_surface):
        reserved_space_a = get_default_reserve_space(sim_a.species, sim_a.age)
        reserved_space_b = get_default_reserve_space(sim_b.species, sim_b.age)
        polygon = _generate_poly_points(sim_a_transform.translation, sim_a_transform.orientation.transform_vector(Vector3.Z_AXIS()), sim_b_transform.translation, sim_b_transform.orientation.transform_vector(Vector3.Z_AXIS()), reserved_space_a.left, reserved_space_a.right, reserved_space_a.front, reserved_space_a.back, reserved_space_b.left, reserved_space_b.right, reserved_space_b.front, reserved_space_b.back)
        return PolygonFootprint(polygon, routing_surface=sim_a.routing_surface, cost=25, footprint_type=FootprintType.FOOTPRINT_TYPE_OBJECT, enabled=True)
