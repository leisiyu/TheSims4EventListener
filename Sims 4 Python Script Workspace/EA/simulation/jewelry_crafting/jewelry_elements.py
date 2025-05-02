from interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom objects.components.types import JEWELRY_COMPONENTfrom sims4.tuning.tunable import TunableEnumEntry, Tunable
class JewelryWearElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will equip the jewel\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The jewel that will be equipped.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'apply_to_all_outfits': Tunable(description='\n            Bool to define if the jewel should be applied to all outfits or not\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        target = self.interaction.get_participant(self.target)
        subject.sim_info.jewelry_tracker.track_jewel(target, self.apply_to_all_outfits)

class JewelryRemoveElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant where the jewel will be removed.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The jewel that will be removed.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'apply_to_all_outfits': Tunable(description='\n            Bool to define if the jewel removal should be applied to all outfits or not\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        target = self.interaction.get_participant(self.target)
        subject.sim_info.jewelry_tracker.untrack_jewel(target, self.apply_to_all_outfits)
