import servicesimport sims4from interactions import ParticipantTypefrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunablePackSafeReference, OptionalTunable, TunableInterval, TunableTuple, TunableVariant, TunableEnumEntryimport collectionslogger = sims4.log.Logger('Skills')
class SkillEffectiveness(DynamicEnum):
    STANDARD = 0
_SkillLootData = collections.namedtuple('_SkillLootData', ['level_range', 'stat', 'effectiveness'])EMPTY_SKILL_LOOT_DATA = _SkillLootData(None, None, None)
class TunableSkillLootData(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(level_range=OptionalTunable(TunableInterval(description="\n            Interval is used to clamp the sim's user facing\n            skill level to determine how many point to give. If\n            disabled, level passed to the dynamic skill loot\n            will always be the current user facing skill level\n            of sim. \n            Example: if sim is level 7 in fitness but\n            interaction skill level is only for 1 to 5 give the\n            dynamic skill amount as if sim is level 5.\n            ", tunable_type=int, default_lower=0, default_upper=1, minimum=0)), stat=TunablePackSafeReference(description='\n                The statistic we are operating on.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), allow_none=True, class_restrictions=('Skill',)), effectiveness=TunableEnumEntry(description='\n                Enum to determine which curve to use when giving\n                points to sim.\n                ', tunable_type=SkillEffectiveness, needs_tuning=True, default=None), **kwargs)

class CareerSkillLootData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'career': TunablePackSafeReference(description='\n            The career to reference a statistic from.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAREER), class_restrictions=('UniversityCourseCareerSlot',))}

    def __call__(self, sim_info, interaction):
        if sim_info is None:
            return
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            return
        course_data = degree_tracker.get_course_data(self.career.guid64)
        if course_data is None:
            return
        return course_data.course_skill_data.related_skill

class PickedStatReference(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, sim_info, interaction):
        if interaction is not None:
            stats = interaction.get_participants(ParticipantType.PickedStatistic)
            if len(stats) > 1:
                logger.error('PickedStatReference only supports one picked skill. The first found will be returned, the rest are ignored.')
            for stat in stats:
                return stat

class TunableVariantSkillLootData(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(level_range=OptionalTunable(TunableInterval(description="\n            Interval is used to clamp the sim's user facing\n            skill level to determine how many point to give. If\n            disabled, level passed to the dynamic skill loot\n            will always be the current user facing skill level\n            of sim. \n            Example: if sim is level 7 in fitness but\n            interaction skill level is only for 1 to 5 give the\n            dynamic skill amount as if sim is level 5.\n            ", tunable_type=int, default_lower=0, default_upper=1, minimum=0)), stat=TunableVariant(description='\n            Where to obtain the statistic we are operating on.\n            ', from_career=CareerSkillLootData.TunableFactory(), from_picked=PickedStatReference.TunableFactory(), default='from_career'), effectiveness=TunableEnumEntry(description='\n            Enum to determine which curve to use when giving\n            points to sim.\n            ', tunable_type=SkillEffectiveness, needs_tuning=True, default=None), **kwargs)
