import servicesimport sims4from interactions import ParticipantTypeSingle, ParticipantType, ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, TunablePackSafeReference, TunableList
class RabbitHoleElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'rabbit_holed_participant': TunableEnumEntry(description='\n            The participant to place in the rabbit hole.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'rabbit_hole': TunablePackSafeReference(description='\n            Rabbit hole to create\n            ', manager=services.get_instance_manager(sims4.resources.Types.RABBIT_HOLE))}

    def _do_behavior(self):
        if self.rabbit_hole is None:
            return
        sim_or_sim_info = self.interaction.get_participant(self.rabbit_holed_participant)
        picked_skill = self.interaction.get_participant(ParticipantType.PickedStatistic)
        services.get_rabbit_hole_service().put_sim_in_managed_rabbithole(sim_or_sim_info.sim_info, self.rabbit_hole, picked_skill=picked_skill)

class MultiRabbitHoleElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'rabbit_holed_participants': TunableList(description='\n            The set of all participants to place in the rabbit hole.\n            ', tunable=TunableEnumEntry(description='\n                The participant to place in the rabbit hole.\n                ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), unique_entries=True, minlength=1), 'rabbit_hole': TunablePackSafeReference(description='\n            Rabbit hole to create\n            ', manager=services.get_instance_manager(sims4.resources.Types.RABBIT_HOLE))}

    def _do_behavior(self):
        if self.rabbit_hole is None:
            return
        all_sims = []
        picked_skill = self.interaction.get_participant(ParticipantType.PickedStatistic)
        for participant in self.rabbit_holed_participants:
            sim_or_sim_info = self.interaction.get_participant(participant)
            all_sims.append(sim_or_sim_info.sim_info)
        services.get_rabbit_hole_service().put_sims_in_shared_rabbithole(all_sims, self.rabbit_hole, picked_skill=picked_skill)
