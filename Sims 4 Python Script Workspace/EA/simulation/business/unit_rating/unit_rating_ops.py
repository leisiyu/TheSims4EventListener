from __future__ import annotationsfrom business.business_enums import BusinessTypefrom business.unit_rating.unit_rating_enums import ModifyDynamicUnitRatingfrom business.unit_rating.unit_rating_tuning import DynamicUnitRatingTuningfrom interactions import ParticipantType, ParticipantTypeZoneIdfrom interactions.utils.loot_basic_op import BaseLootOperationfrom multi_unit.multi_unit_handler import unit_rating_change_archive, log_unit_rating_changefrom sims4.tuning.tunable import TunableEnumEntryimport servicesimport sims4import sysimport tracebackfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from business.business_manager import BusinessManagerlogger = sims4.log.Logger('Unit Rating', default_owner='micfisher')
class ModifyDynamicUnitRatingLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'description': '\n            This loot will modify the Dynamic (Trigger) unit rating by the specified Change Value.\n            ', 'change_value': TunableEnumEntry(description='\n            The enum corresponding to the amount to change the dynamic (trigger) unit rating.\n            ', tunable_type=ModifyDynamicUnitRating, default=ModifyDynamicUnitRating.SMALL_LOSS), 'receiver': TunableEnumEntry(description='\n            The recipient of the loot. This should never be set to anything other than PickedZoneId, RandomZoneId, \n            ActorZoneId, CurrentZoneId, or AllUnitZoneIds.\n            ', tunable_type=ParticipantTypeZoneId, default=ParticipantType.PickedZoneId)}

    def __init__(self, change_value:'ModifyDynamicUnitRating', receiver:'ParticipantType', **kwargs):
        super().__init__(**kwargs)
        self._change_value = change_value
        self._receiver = receiver

    @classmethod
    def _verify_tuning_callback(cls) -> 'None':
        valid_receiver_types = [ParticipantType.PickedZoneId, ParticipantType.RandomZoneId, ParticipantType.ActorZoneId, ParticipantType.CurrentZoneId, ParticipantType.AllUnitZoneIds]
        if cls._receiver not in valid_receiver_types:
            logger.error('Receiver {} is not a valid receiver type!', cls._receiver)

    def _apply_rating_change(self, business_manager:'BusinessManager') -> 'None':
        if business_manager is None:
            return
        if business_manager.business_type == BusinessType.RENTAL_UNIT:
            business_manager.dynamic_unit_rating += DynamicUnitRatingTuning.RATING_CHANGE[self._change_value]
            business_manager.on_dynamic_rating_change()
            business_manager.send_venue_business_data_update_message()

    def _apply_to_subject_and_target(self, subject, target, resolver) -> 'None':
        if resolver is None:
            return
        business_service = services.business_service()
        zone_id_or_zone_ids = resolver.get_participants(self._receiver)
        for zone_id in zone_id_or_zone_ids:
            self._apply_rating_change(business_service.get_business_manager_for_zone(zone_id))
        if unit_rating_change_archive.enabled:
            frame = sys._getframe(1)
            callstack_info = traceback.extract_stack(frame, limit=20)
            log_unit_rating_change(zone_id_or_zone_ids, self._change_value.name, resolver.__class__.__name__, self._receiver.name, callstack_info)
