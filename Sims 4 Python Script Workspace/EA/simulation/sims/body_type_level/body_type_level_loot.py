import sims4from interactions import ParticipantTypeSingleSimfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims.body_type_level.body_type_level_commodity import BODY_TYPE_TO_LEVEL_COMMODITYfrom sims.outfits.outfit_enums import BodyTypefrom sims4.tuning.tunable import TunableEnumEntry, TunableFactorylogger = sims4.log.Logger('BodyTypeLevelLoot', default_owner='skorman')
class SetBodyTypeToPreferredLevel(BaseLootOperation):
    FACTORY_TUNABLES = {'body_type': TunableEnumEntry(description='\n            The body type to set to the preferred level.\n            ', tunable_type=BodyType, default=BodyType.NONE, invalid_enums=(BodyType.NONE,))}

    @TunableFactory.factory_option
    def subject_participant_type_options(**kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, default_participant=ParticipantTypeSingleSim.Actor, **kwargs)

    def __init__(self, body_type, **kwargs):
        super().__init__(**kwargs)
        self._body_type = body_type

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Failed to set {} to preferred level. Subject is None.', self._body_type)
            return
        if self._body_type not in BODY_TYPE_TO_LEVEL_COMMODITY:
            logger.error('Failed to set {} to preferred level. The BodyType does not have an associated BodyTypeLevelCommodity.', self._body_type)
            return
        commodity_type = BODY_TYPE_TO_LEVEL_COMMODITY[self._body_type]
        commodity = subject.get_statistic(commodity_type)
        if commodity is None:
            return
        level = subject.base.get_preferred_growth_level(self._body_type)
        commodity.set_level(level)
