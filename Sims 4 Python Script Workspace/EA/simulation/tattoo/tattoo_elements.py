from interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims.outfits.outfit_enums import BodyTypefrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, TunableListfrom tattoo.tattoo_tuning import TattooQuality, TattooSentimentType
class TattooTrackElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will equip the tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'quality': TunableEnumEntry(description='\n            Quality of the tattoo\n            ', tunable_type=TattooQuality, default=TattooQuality.NONE), 'sentiment_type': TunableEnumEntry(description='\n            Sentiment type for the tattoo\n            ', tunable_type=TattooSentimentType, default=TattooSentimentType.NONE), 'sentimental_target': OptionalTunable(description='\n            The sentimental target for the tattoo.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.SavedActor1)), 'design_participant': OptionalTunable(description='\n            If defined, participant where the design (cas_part) is stored \n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.PickedItemId)), 'unlock_design_participant': OptionalTunable(description='\n            If enabled, defined participant will unlock the tattoo design\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor))}

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.subject)
        caspart_id = None
        sentimental_participant_id = 0
        unlock_design_participant = None
        if self.design_participant is not None:
            caspart_id = self.interaction.get_participant(ParticipantType.PickedItemId)
        if self.sentimental_target is not None:
            sentimental_participant = self.interaction.get_participant(self.sentimental_target)
            if sentimental_participant:
                sentimental_participant_id = sentimental_participant.id
        if self.unlock_design_participant is not None:
            unlock_design_participant = self.interaction.get_participant(self.unlock_design_participant)
        target.sim_info.tattoo_tracker.track_tattoo(quality=self.quality, cas_part=caspart_id, sentimental_type=self.sentiment_type, sentimental_target=sentimental_participant_id, unlock_design_participant=unlock_design_participant)

class TattooRemoveElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The participant that will unequip the tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'body_types': TunableList(description='\n            Body parts to remove. If empty, will remove all tattoos\n            ', tunable=TunableEnumEntry(tunable_type=BodyType, default=BodyType.TATTOO_ARM_LOWER_LEFT))}

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.target)
        target.sim_info.tattoo_tracker.remove_tattoo(body_types=self.body_types)

class CheckTattooDataNotificationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will equip the tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.subject)
        target.sim_info.tattoo_tracker.show_check_tattoo_notification()

class StorePickedTattoo(XevtTriggeredElement):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description="\n            The participant's tracker where we will store the picked tattoo\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor), 'picked_tattoo_participant': TunableEnumEntry(description='\n            The participant where we currently have the picked tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId)}

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.target)
        picked_tattoo_id = self.interaction.get_participant(self.picked_tattoo_participant)
        target.sim_info.tattoo_tracker.store_picked_tattoo(picked_tattoo_id)
