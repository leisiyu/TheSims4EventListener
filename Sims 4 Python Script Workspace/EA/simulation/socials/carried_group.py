from interactions.constraint_variants import TunableConstraintVariantfrom interactions.constraints import Anywhere, Nowherefrom interactions.interaction_finisher import FinishingTypefrom sims.sim_info_types import Speciesfrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import TunableListfrom socials.side_group import SideGroupfrom _math import Vector3
class CarriedGroup(SideGroup):
    HORSE_SOCIAL_CONSTRAINT_OFFSET = TunableVector3(description="\n        When generating constraints around a horse for CarriedGroups, offset \n        the position of the horse who is the focus of this group by this \n        much. This will prevent geometric constraints from clipping through \n        the horse's head since their root bone is at the base of their neck. \n        ", default=Vector3(0, 0, 1.5))
    INSTANCE_TUNABLES = {'group_constraints': TunableList(description='\n            A list of constraints non-carrying sims must satisfy to meet the needs of the social group.\n            The target of these constraints is the carrying sim.\n            ', tunable=TunableConstraintVariant())}

    def __init__(self, *args, **kwargs):
        self._carried_sim = None
        self._carrying_sim = None
        super().__init__(*args, **kwargs)

    def _set_carried_sim(self):
        if self._target_sim is not None:
            if self._initiating_sim.parent is not None and self._initiating_sim.parent.is_sim:
                self._carried_sim = self._initiating_sim
                self._carrying_sim = self._initiating_sim.parent
            elif self._target_sim.parent.is_sim:
                self._carried_sim = self._target_sim
                self._carrying_sim = self._target_sim.parent
            if self._carrying_sim is not None:
                self._carrying_sim.register_on_location_changed(self._carrying_sim_location_changed)

    def _make_constraint(self, position, *args, **kwargs):
        self._set_carried_sim()
        if self._carried_sim is None:
            return Nowhere('No carried sim set for the carried sim social group.')
        target_position = self._carrying_sim.intended_position
        if self._carrying_sim.species == Species.HORSE:
            offset = self._carrying_sim.intended_location.transform.orientation.transform_vector(self.HORSE_SOCIAL_CONSTRAINT_OFFSET)
            target_position = self._carrying_sim.intended_position + offset
        constraint_total = Anywhere()
        for constraint_factory in self.group_constraints:
            constraint = constraint_factory.create_constraint(self._initiating_sim, target=self._carrying_sim, target_position=target_position)
            constraint_total = constraint_total.intersect(constraint)
        constraint_total = constraint_total.intersect(self._los_constraint)
        return constraint_total

    def _get_constraint(self, sim):
        if self._carried_sim is None:
            return Nowhere('No carried sim set for the carried sim social group.')
        if sim is self._carried_sim or sim is self._carrying_sim:
            return Anywhere()
        return self._constraint

    def _carrying_sim_location_changed(self, obj, *_, **__):
        if obj is self._carrying_sim:
            if obj is not None and obj.species == Species.HORSE:
                interactions_to_cancel = []
                for interaction in self.get_all_interactions_gen():
                    if interaction.running:
                        interactions_to_cancel.append(interaction)
                for interaction in interactions_to_cancel:
                    interaction.cancel(FinishingType.SOCIALS, cancel_reason_msg='Carrying Sim location changed.')
                self.regenerate_constraint_and_validate_members()
                return
            if len(self) == 2 and self._carrying_sim in self and self._carried_sim in self:
                return
            self.shutdown(FinishingType.SOCIALS)

    def _get_focus(self):
        self._set_carried_sim()
        if self._carrying_sim is not None and self._carrying_sim.species == Species.HORSE:
            return self._carried_sim
        else:
            return super()._get_focus()

    def shutdown(self, finishing_type):
        if self._carried_sim:
            self._carrying_sim.unregister_on_location_changed(self._carrying_sim_location_changed)
            self._carrying_sim = None
            self._carried_sim = None
        super().shutdown(finishing_type)
