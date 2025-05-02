import servicesimport sims4from event_testing.objective_enums import ObjectiveCategoryTypefrom sims4.tuning.tunable import TunableEnumSetfrom sims4.utils import classproperty
class UnfinishedBusiness:
    GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK = sims4.tuning.tunable.TunableReference(description='\n        The Aspiration within the track that is associated with this level.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK), class_restrictions='AspirationTrack', pack_safe=True)
    UNFINISHED_BUSINESS_CATEGORIES = TunableEnumSet(description='\n        A set of Category Types that are associated with Unfinished Business\n        ', enum_type=ObjectiveCategoryType, enum_default=ObjectiveCategoryType.NO_CATEGORY_TYPE)
    UNFINISHED_BUSINESS_STAT = sims4.tuning.tunable.TunableReference(description='\n        The statistic representing Unfinished Business progress.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',), pack_safe=True)

    @classproperty
    def global_unfinished_business_aspiration(cls):
        if cls.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK is None:
            return
        if cls.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK.aspirations is None:
            return
        return next(iter(cls.GLOBAL_UNFINISHED_BUSINESS_ASPIRATION_TRACK.aspirations.values()), None)
