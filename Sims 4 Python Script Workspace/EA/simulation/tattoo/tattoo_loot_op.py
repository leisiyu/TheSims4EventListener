from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfo
    from event_testing.resolver import Resolverimport sims4from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims.outfits.outfit_enums import BodyTypefrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, TunableCasPart, TunableTuple, OptionalTunable, TunableListfrom tattoo.tattoo_tuning import TattooQuality, TattooSentimentTypelogger = sims4.log.Logger('Tattoo', default_owner='javier.canon')
class TrackTattooOp(BaseLootOperation):
    DESIGN_FROM_CATALOG = 0
    DESIGN_FROM_PARTICIPANT = 1
    NONE = 2
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will equip the tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'quality': TunableEnumEntry(description='\n            Quality of the tattoo\n            ', tunable_type=TattooQuality, default=TattooQuality.NONE), 'sentiment_type': TunableEnumEntry(description='\n            Sentiment type for the tattoo\n            ', tunable_type=TattooSentimentType, default=TattooSentimentType.NONE), 'sentimental_target': OptionalTunable(description='\n            The sentimental target for the tattoo.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor)), 'design': OptionalTunable(description='\n            If enabled, defines if the tattoo design will be retrieved from a participant or the defined cas part.\n            ', tunable=TunableVariant(from_participant=TunableTuple(locked_args={'design_type': DESIGN_FROM_PARTICIPANT}, participant=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.PickedItemId)), from_catalog=TunableTuple(locked_args={'design_type': DESIGN_FROM_CATALOG}, catalog_id=TunableCasPart()))), 'unlock_design_participant': OptionalTunable(description='\n            If enabled, defined participant will unlock the tattoo design\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Actor))}

    def __init__(self, subject:'SimInfo', quality:'TattooQuality', sentiment_type:'TattooSentimentType', design:'TunableVariant', sentimental_target:'ParticipantType', unlock_design_participant:'ParticipantType', **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._quality = quality
        self._sentiment_type = sentiment_type
        self._design = design
        self._sentimental_target = sentimental_target
        self._unlock_design_participant = unlock_design_participant

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver') -> 'None':
        caspart_id = None
        sentimental_participant_id = 0
        unlock_design_participant = None
        if self._design and self._design.design_type == self.DESIGN_FROM_PARTICIPANT:
            caspart_id = resolver.get_participant(self._design.participant)
        elif self._design.design_type == self.DESIGN_FROM_CATALOG:
            caspart_id = self._design.catalog_id
        if self._sentimental_target is not None:
            sentimental_participant = resolver.get_participant(self._sentimental_target)
            if sentimental_participant:
                sentimental_participant_id = sentimental_participant.id
        if self._unlock_design_participant is not None:
            unlock_design_participant = resolver.get_participant(self._unlock_design_participant)
        subject.sim_info.tattoo_tracker.track_tattoo(quality=self._quality, cas_part=caspart_id, sentimental_type=self._sentiment_type, sentimental_target=sentimental_participant_id, unlock_design_participant=unlock_design_participant)

class SetQualityTattooOp(BaseLootOperation):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who to apply the new quality\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'quality': TunableEnumEntry(description='\n            Quality of the tattoo\n            ', tunable_type=TattooQuality, default=TattooQuality.NONE), 'body_types': TunableList(description='\n            Body parts that will change their quality. If empty, it will applied to all body parts\n            ', tunable=TunableEnumEntry(tunable_type=BodyType, default=BodyType.TATTOO_ARM_LOWER_LEFT))}

    def __init__(self, subject:'SimInfo', quality:'TattooQuality', body_types:'List(BodyType)', **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._quality = quality
        self._body_types = body_types

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver') -> 'None':
        subject.sim_info.tattoo_tracker.set_quality(quality=self._quality, body_types=self._body_types)

class StorePickedTattooOp(BaseLootOperation):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The participant's tracker where we will store the picked tattoo\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor), 'picked_tattoo_participant': TunableEnumEntry(description='\n            The participant where we currently have the picked tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.PickedItemId)}

    def __init__(self, subject:'SimInfo', picked_tattoo_participant:'int', **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._picked_tattoo = picked_tattoo_participant

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver') -> 'None':
        caspart_id = resolver.get_participant(self._picked_tattoo)
        if caspart_id is None:
            return
        subject.sim_info.tattoo_tracker.store_picked_tattoo(caspart_id)
