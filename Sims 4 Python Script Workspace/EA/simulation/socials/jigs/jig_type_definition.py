from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.game_object import GameObject
    from routing import SurfaceIdentifier
    from sims.sim import Simfrom interactions import ParticipantTypeSinglefrom interactions.utils.routing import fgl_and_get_two_person_transforms_for_jig, fgl_and_get_two_person_transforms_for_jig_with_objfrom routing import FootprintTypefrom sims4.geometry import PolygonFootprintfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableReference, OptionalTunable, TunableRange, TunableTuple, Tunable, TunableEnumEntryfrom socials.jigs.jig_utils import JigPositioningimport placementimport servicesimport sims4.loglogger = sims4.log.Logger('Jigs')
class SocialJigFromDefinition(AutoFactoryInit, HasTunableSingletonFactory):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value, **kwargs):
        if value.jig_positioning_type == JigPositioning.RelativeToSingleParticipant and not value.jig_positioning_single_participant:
            logger.error('{} has Jig Positioning Type = Relative to Single Participant but has no Jig Positioning Single Participant set', instance_class)
        elif value.jig_positioning_single_participant is not None and value.jig_positioning_type != JigPositioning.RelativeToSingleParticipant:
            logger.error('{} has specified a Jig Positioning Single Participant, but has Jig Positioning Type= {}', instance_class, value.jig_positioning_type)

    FACTORY_TUNABLES = {'jig_definition': TunableReference(description='\n            The jig to use for finding a place to do the social.\n            ', manager=services.definition_manager()), 'override_polygon_and_cost': OptionalTunable(description='\n            If disabled, uses a CompoundPolygon of the object as footprint polygon. \n            If enabled, uses the largest placement polygon of the object as footprint\n            polygon. Then we will be able to add footprint cost to the polygon. This \n            can be used to discourage other sims from entering this area.\n            ', tunable=TunableTuple(footprint_cost=TunableRange(description='\n                    Footprint cost of the jig, this can be used to discourage/block other\n                    sims from entering this area.\n                    ', tunable_type=int, default=20, minimum=1))), 'jig_positioning_type': TunableEnumEntry(description='\n            Determines the type of positioning used for this Jig. The other sim will come over to the relative sim.\n            If both sims need to route to something else, like an object participant, choose RelativeToSingleParticipant\n            and specify the third participant using Jig Positioning Single Participant (Jig will be positioned near the \n            single participant, and relative to Sim A.)\n            ', tunable_type=JigPositioning, default=JigPositioning.RelativeToSimB), 'jig_positioning_single_participant': OptionalTunable(description='\n            This should only be enabled if Jig Positioning Type is set to Relative To Single Participant. \n            Specify the single participant that should influence jig position, e.g. Object. \n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)), 'jig_positioning_max_distance': OptionalTunable(description='\n            This should only be enabled if Jig Positioning Type is set to Relative To Single Participant. \n            Specify the maximum distance the jig can be positioned away from the single participant. Corresponds to FGL\n            parameter "max_distance". \n            ', tunable=Tunable(tunable_type=int, default=2)), 'verify_tunable_callback': _verify_tunable_callback}

    def get_transforms_gen(self, actor:'Sim', target:'GameObject', actor_slot_index:'int'=0, target_slot_index:'int'=1, fallback_routing_surface:'SurfaceIdentifier'=None, jig_positioning_participant:'GameObject'=None, fgl_kwargs=None) -> 'Iterator':
        fgl_kwargs = fgl_kwargs if fgl_kwargs is not None else {}
        actor = target
        target = actor
        actor_slot_index = target_slot_index
        target_slot_index = actor_slot_index
        if (self.jig_positioning_type == JigPositioning.RelativeToSimA or self.jig_positioning_type == JigPositioning.RelativeToSingleParticipant) and self.jig_positioning_type == JigPositioning.RelativeToSingleParticipant and jig_positioning_participant is not None:
            fgl_kwargs['max_dist'] = self.jig_positioning_max_distance
            (actor_transform, target_transform, routing_surface) = fgl_and_get_two_person_transforms_for_jig_with_obj(self.jig_definition, actor, target, jig_positioning_participant, actor_slot_index, target_slot_index, **fgl_kwargs)
        else:
            (actor_transform, target_transform, routing_surface) = fgl_and_get_two_person_transforms_for_jig(self.jig_definition, actor, actor_slot_index, target, target_slot_index, fallback_routing_surface=fallback_routing_surface, **fgl_kwargs)
        yield (actor_transform, target_transform, routing_surface, ())

    def get_footprint_polygon(self, sim_a, sim_b, sim_a_transform, sim_b_transform, routing_surface):
        if self.jig_positioning_type == JigPositioning.RelativeToSimA or self.jig_positioning_type == JigPositioning.RelativeToSingleParticipant:
            footprint_translation = sim_a_transform.translation
            footprint_orientation = sim_a_transform.orientation
        else:
            footprint_translation = sim_b_transform.translation
            footprint_orientation = sim_b_transform.orientation
        if self.override_polygon_and_cost is not None:
            polygon = placement.get_placement_footprint_polygon(footprint_translation, footprint_orientation, routing_surface, self.jig_definition.get_footprint(0))
            return PolygonFootprint(polygon, routing_surface=routing_surface, cost=self.override_polygon_and_cost.footprint_cost, footprint_type=FootprintType.FOOTPRINT_TYPE_PATH, enabled=True)
        return placement.get_placement_footprint_compound_polygon(footprint_translation, footprint_orientation, routing_surface, self.jig_definition.get_footprint(0))
