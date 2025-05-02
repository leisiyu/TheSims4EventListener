import servicesimport sims4from interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom interactions.utils.animation_reference import TunableAnimationReferencefrom protocolbuffers import Routing_pb2from routing.formation.formation_type_base import FormationTypeBase, FormationRoutingTypefrom sims4.tuning.tunable import OptionalTunable, TunableTuple, TunableReferencefrom sims4.utils import classproperty
class FormationTypePaired(FormationTypeBase):

    @classproperty
    def routing_type(cls):
        return FormationRoutingType.PAIRED

    @property
    def slave_attachment_type(self):
        return Routing_pb2.SlaveData.SLAVE_PAIRED_CHILD

class FormationTypePairedHorse(FormationTypePaired):
    FACTORY_TUNABLES = {'reins_animation_tuning': OptionalTunable(description='\n            If tuned, provide animations that may play ahead of a transition or\n            an interaction marked with require_reins_for_formation.\n            The formation keeps track of which animation should be playing, but\n            interactions will request a change in state and play the corresponding\n            animation as needed.\n            \n            e.g. use with rider Sims who may need to put down or pick up reins ahead of a social.\n            ', tunable=TunableTuple(description='\n                The pickup and putdown animations.\n                ', pickup_affordance=TunableReference(description='\n                    The affordance the master will play when entering locomotion or a\n                    marked interaction.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True), pickup_animation=TunableAnimationReference(description='\n                    The animation that will play when entering locomotion or a\n                    marked interaction.\n                    ', callback=None, class_restrictions=('AnimationElement', 'AnimationElementSet'), pack_safe=True), putdown_animation=TunableAnimationReference(description='\n                    The animation that will play when exiting locomotion or a\n                    marked interaction.\n                    ', callback=None, class_restrictions=('AnimationElement', 'AnimationElementSet'), pack_safe=True)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reins_state = True if self.reins_animation_tuning is not None else None

    @classproperty
    def routing_type(cls):
        return FormationRoutingType.PAIRED_HORSE

    @property
    def reins_state(self):
        return self._reins_state

    @reins_state.setter
    def reins_state(self, value):
        self._reins_state = value

    def on_release(self, sim):
        if self.reins_state is False:
            pickup_affordance = self.reins_animation_tuning.pickup_affordance
            for interaction in sim.get_all_running_and_queued_interactions():
                if interaction.affordance.is_putdown:
                    interaction.reins_anim_aop = pickup_affordance
