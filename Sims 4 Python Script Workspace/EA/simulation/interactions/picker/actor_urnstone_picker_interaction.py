from interactions.base.picker_interaction import ObjectPickerInteractionfrom sims.ghost import Ghostfrom sims4.utils import flexmethod
class ActorsUrnstonePickerMixin:

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        yield Ghost.get_urnstone_for_sim_id(context.sim.sim_id)

class ActorUrnstonePickerInteraction(ActorsUrnstonePickerMixin, ObjectPickerInteraction):
    pass
