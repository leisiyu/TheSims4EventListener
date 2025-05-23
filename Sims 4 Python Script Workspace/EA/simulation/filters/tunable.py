from __future__ import annotationsfrom __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.household import Household
    from sims.sim_info import SimInfo
    from sims.sim_spawner import SimCreatorimport mathfrom services.prom_service import PromRelationshipBitTypefrom sims.global_gender_preference_tuning import GlobalGenderPreferenceTuningimport build_buyimport itertoolsimport operatorimport randomfrom bucks.bucks_utils import BucksUtilsfrom caches import cachedfrom careers.career_enums import CareerCategory, GigResultfrom cas.cas import get_tags_from_outfitfrom cas.cas_enums import RandomizationModefrom clans.clan_service import ClanServicefrom date_and_time import DateAndTimefrom filters.demographics_filter_term_mixin import DemographicsFilterTermMixinfrom sims.genealogy_tracker import FamilyRelationshipIndexfrom sims.occult.occult_enums import OccultTypefrom sims.pets.breed_tuning import get_random_breed_tagfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_types import Age, Gender, Species, SpeciesExtendedfrom sims.sim_info_utils import sim_info_auto_finderfrom sims.sim_spawner_enums import SimNameTypefrom sims.university.university_enums import EnrollmentStatusfrom sims.university.university_tuning import Universityfrom sims4.resources import Typesfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableList, TunableVariant, HasTunableSingletonFactory, TunableSet, OptionalTunable, AutoFactoryInit, TunableReference, TunablePackSafeReference, TunableTuple, TunableRange, TunableInterval, TunableEnumSet, TunableWorldDescription, TunableFactory, TunableThresholdfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom venues.venue_enums import VenueTypesfrom world import regionimport filters.household_templateimport servicesimport simsimport sims4.logimport sims4.resourcesimport tagfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.sim_info import SimInfo
    from relationships.relationship_objects.relationship import Relationship
    from typing import *logger = sims4.log.Logger('SimFilter')
class FilterTermTag(DynamicEnumLocked):
    NO_TAG = 0

class FilterResult:
    TRUE = None
    FALSE = None

    def __init__(self, *args, score=1, sim_info=None, conflicting_career_track_id=None, tag=FilterTermTag.NO_TAG):
        if args:
            self._reason = args[0]
            self._format_args = args[1:]
        else:
            (self._reason, self._format_args) = (None, ())
        self.score = score
        self.sim_info = sim_info
        self.conflicting_career_track_id = conflicting_career_track_id
        self.tag = tag

    @property
    def reason(self):
        if self._reason:
            self._reason = self._reason.format(*self._format_args)
            self._format_args = ()
        return self._reason

    def __repr__(self):
        if self.reason:
            return '<FilterResult: sim_info: {0} score: {1} reason: {2}>'.format(self.sim_info, self.score, self.reason)
        return '<FilterResult: sim_info: {0} score: {1}>'.format(self.sim_info, self.score)

    def __bool__(self):
        return self.score != 0

    def combine_with_other_filter_result(self, other):
        if self.sim_info is not None:
            if self.sim_info != other.sim_info:
                raise AssertionError('Attempting to combine filter results between 2 different sim infos: {} and {}'.format(self.sim_info, other.sim_info))
        else:
            self.sim_info = other.sim_info
        self.score *= other.score
        if self._reason is None:
            self._reason = other._reason
            self._format_args = other._format_args
        if self.conflicting_career_track_id is None:
            self.conflicting_career_track_id = other.conflicting_career_track_id
FilterResult.TRUE = FilterResult()FilterResult.FALSE = FilterResult(score=0)
class BaseFilterTerm(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'minimum_filter_score': Tunable(description="\n            The minimum score that this filter term is allowed to have. The\n            purpose of this is to allow 'relaxed filters' that don't prevent\n            sims from being chosen.\n            ", tunable_type=float, default=0), 'force_filter_term': Tunable(description='\n            If checked, any Sim found via template will have this filter term \n            applied when conforming it.  If unchecked, this filter term will \n            not be applied.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, conform_optional=False, force_filter_term=True, **kwargs):
        self.conform_optional = conform_optional
        super().__init__(*args, force_filter_term=force_filter_term, **kwargs)

    @TunableFactory.factory_option
    def conform_optional(enable=False):
        kwargs = {}
        if enable:
            kwargs['conform_optional'] = Tunable(description='\n                If enabled, failing to conform this filter will not stop Sim\n                creation.\n                ', tunable_type=bool, default=False)
        return kwargs

    def can_repurpose_sim_info(self, sim_info):
        return self.is_sim_info_conformable

    @property
    def is_sim_info_conformable(self):
        raise NotImplementedError

    def calculate_score(self, sim_info, **kwargs):
        raise NotImplementedError

    def conform_sim_creator_to_filter_term(self, **kwargs):
        return FilterResult.TRUE

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        return self.calculate_score(created_sim_info, **kwargs)

    def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
        pass

    def is_compatible(self, other:'BaseFilterTerm') -> 'bool':
        return True

    def _is_comparable(self, other:'BaseFilterTerm') -> 'bool':
        if type(other) != type(self):
            return False
        if self is other:
            return True
        elif not (self.force_filter_term and other.force_filter_term):
            return False
        return True

class InvertibleFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'invert_score': Tunable(description='\n            Invert the score so that the filter term will score is the opposite\n            of what the score would be.\n            \n            For example, if sim is busy, normally would return 1, but if checked\n            value would return 0 and would not be chosen by filter system.\n            ', tunable_type=bool, default=False)}

    def invert_score_if_necessary(self, score):
        if self.invert_score:
            return 1 - score
        return score

def calculate_score_from_value(value, min_value, max_value, ideal_value, use_padding=True):
    if ideal_value == value:
        return 1
    if use_padding:
        min_value -= 1
        max_value += 1
    score = 0
    if value < ideal_value:
        score = (value - min_value)/(ideal_value - min_value)
    else:
        score = (max_value - value)/(max_value - ideal_value)
    return max(0, min(1, score))

class StatisticFilterTerm(InvertibleFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.statistic is None:
            logger.error('TunableStatisticFilterTerm {} has a filter term {} with invalid Statistic.', source, tunable_name)
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('TunableStatisticFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].', source, tunable_name, value.ideal_value, value.min_value, value.max_value)

    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            The statistic the range applies to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Statistic',)), 'min_value': Tunable(description='\n            Minimum value of the statistic that we are filtering against.\n            ', tunable_type=float, default=0.0), 'max_value': Tunable(description='\n            Maximum value of the statistic that we are filtering against.\n            ', tunable_type=float, default=10.0), 'ideal_value': Tunable(description='\n            Ideal value of the statistic that we are filtering against.\n            ', tunable_type=float, default=5.0), 'score_spread_override': OptionalTunable(description='\n            If enabled this interval modifies the spread over which the score\n            should return.\n            \n            A score is typically between 0 and 1.  A score of 0 means\n            the sim will never be selected, the higher a score is the more\n            likely that sim is to be selected.\n            \n            The score for statistic scoring is based on how close to the "ideal" value\n            the value for the specified statistic for a sim is.  It\'s a 1 if it\'s\n            that exact score.  It\'s *near* 0  (though not exactly, because the\n            general idea behind this filter to make it a weight not elimination)\n            as it gets farther from the ideal value and closer to the min or max value.\n            (Note: it uses min_value -1 and max_value + 1 as the min/max values to avoid\n            hitting 0.  However the min/max values don\'t have to be accurate,\n            so you can hit 0 by adjusting the tuned min/max values here as desired.)\n            \n            So if you have it tuned as:\n            min value: 0\n            max value: 5\n            ideal value: 5\n            The resulting score for each integer will be:\n            0 gives you: 0.17\n            1 gives you: 0.33\n            2 gives you: 0.5\n            3 gives you: 0.66\n            4 gives you: 0.83\n            5 gives you: 1\n            \n            The minimum filter score tuning is simply a floor.  Regardless of how low\n            the calculated score is, if it\'s lower than the minimum filter score\n            the result will simply be replaced with the minimum filter score.\n            \n            So adding a minimum filter score of 0.5 simply results in:\n            0 gives you: 0.5\n            1 gives you: 0.5\n            2 gives you: 0.5\n            3 gives you: 0.66\n            4 gives you: 0.83\n            5 gives you: 1\n            \n            This optional tunable modifies the spread over which the score\n            is returned (and gets rid of the -1/+1 padding as you can specify\n            the padding in the actual range.)  So instead of returning from 0 to 1, \n            where 0 is as far away from the ideal as possible, and 1 is at the \n            ideal value, it\'ll return the lower value when the statistic is as \n            far away from the ideal value as possible, and the closer you get to the \n            ideal value, the closer the return value will be to the maximum value.\n            \n            So adding a score spread override of 0.5 to 1.0, (instead of a\n            minimum filter score) results in:\n            0 gives you: 0.5\n            1 gives you: 0.6\n            2 gives you: 0.7\n            3 gives you: 0.8\n            4 gives you: 0.9\n            5 gives you: 1\n            \n            Note:  Since, as stated, it\'s perfectly possible to lie about the\n            min/max value, this result is also possible to achieve with clever\n            tuning:\n            min value of -4\n            max value of 5\n            ideal value of 5\n            ', tunable=TunableInterval(tunable_type=float, default_lower=0.0, default_upper=1.0, minimum=0)), 'only_check_statistic_owned': Tunable(description="\n            Only require that the statistic is actually owned by the sim,\n            ignoring the statistic's level.\n            ", tunable_type=bool, default=False), 'verify_tunable_callback': _verify_tunable_callback}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, tag=FilterTermTag.NO_TAG, **kwargs):
        return self._calculate_score(sim_info, self.statistic, tag, **kwargs)

    def _calculate_score(self, sim_info, statistic, tag=FilterTermTag.NO_TAG, use_rank=False, **kwargs):
        tracker = sim_info.get_tracker(statistic)
        if self.only_check_statistic_owned:
            if tracker is not None and tracker.has_statistic(statistic):
                return FilterResult(score=self.invert_score_if_necessary(1), sim_info=sim_info, tag=tag)
            return FilterResult(score=self.invert_score_if_necessary(0), sim_info=sim_info, tag=tag)
        if tracker is not None:
            if use_rank:
                ranked_stat = tracker.get_statistic(statistic)
                value = ranked_stat.rank_level if ranked_stat is not None else 0
            else:
                value = tracker.get_user_value(statistic)
        else:
            logger.error('Failed to get tracker. Sim: {}, Statistic: {}', sim_info, statistic)
            value = statistic.get_user_value()
        score = calculate_score_from_value(value, self.min_value, self.max_value, self.ideal_value, use_padding=self.score_spread_override is None)
        score = self.invert_score_if_necessary(score)
        if self.score_spread_override is not None:
            score = self.score_spread_override.value_at(score)
        return FilterResult(score=score, sim_info=sim_info, tag=tag)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        return self._conform_sim_info_to_filter_term(created_sim_info, self.statistic, **kwargs)

    def _conform_sim_info_to_filter_term(self, created_sim_info, statistic, use_rank=False, **kwargs):
        if not statistic.can_add(created_sim_info):
            return FilterResult('Failed to add skill/statistic, possibly due to age or gender restrictions: {}', statistic.__name__, score=0, sim_info=created_sim_info)
        if use_rank:
            tracker = created_sim_info.get_tracker(statistic)
            created_sim_stat = tracker.get_statistic(statistic, add=True)
            if hasattr(created_sim_stat, 'refresh_threshold_callback'):
                created_sim_stat.refresh_threshold_callback()
            stat_value = None if created_sim_stat is None else created_sim_stat.rank_level
        else:
            stat_value = created_sim_info.get_stat_value(statistic)
        if stat_value is None:
            current_user_value = statistic.convert_to_user_value(statistic.initial_value)
        else:
            current_user_value = stat_value if use_rank else statistic.convert_to_user_value(stat_value)
        if self.invert_score != self.min_value <= current_user_value <= self.max_value:
            return FilterResult.TRUE
        if self.invert_score:
            if use_rank:
                conform_min_value = statistic.initial_value
                conform_max_value = statistic.max_rank
            else:
                conform_min_value = statistic.min_value
                conform_max_value = statistic.max_value
            min_range = self.min_value - conform_min_value
            max_range = conform_max_value - self.max_value
            if min_range <= 0 and max_range > 0:
                statistic_user_value = random.randint(self.max_value, conform_max_value)
            elif min_range > 0 and max_range <= 0:
                statistic_user_value = random.randint(conform_min_value, self.min_value)
            elif min_range > 0 and max_range > 0:
                chosen_level = random.randint(0, min_range + max_range)
                if chosen_level > min_range:
                    statistic_user_value = chosen_level - min_range + self.max_value
                else:
                    statistic_user_value = chosen_level + conform_min_value
            else:
                FilterResult('Failed to add proper skill/statistic level to sim.', sim_info=created_sim_info, score=0)
        elif self.min_value == self.max_value:
            statistic_user_value = self.ideal_value
        else:
            statistic_user_value = round(random.triangular(self.min_value, self.max_value, self.ideal_value))
        if use_rank:
            if created_sim_stat is not None:
                created_sim_stat.set_value(created_sim_stat.points_to_rank(statistic_user_value))
        else:
            stat_value = statistic.convert_from_user_value(statistic_user_value)
            created_sim_info.add_statistic(statistic, stat_value)
        return FilterResult.TRUE

class SkillFilterTerm(StatisticFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.skill is None:
            logger.error('TunableSkillFilterTerm {} has a filter term {} with invalid Skill.', source, tunable_name)
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('TunableSkillFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].', source, tunable_name, value.ideal_value, value.min_value, value.max_value)

    FACTORY_TUNABLES = {'skill': TunableReference(description='\n            The skill the range applies to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Skill',)), 'min_value': Tunable(description='\n            Minimum value of the skill that we are filtering against.\n            ', tunable_type=int, default=0), 'max_value': Tunable(description='\n            Maximum value of the skill that we are filtering against.\n            ', tunable_type=int, default=10), 'ideal_value': Tunable(description='\n            Ideal value of the skill that we are filtering against.\n            ', tunable_type=int, default=5), 'verify_tunable_callback': _verify_tunable_callback, 'locked_args': {'statistic': None}}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, tag=FilterTermTag.NO_TAG, **kwargs):
        return self._calculate_score(sim_info, self.skill, tag, **kwargs)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        return self._conform_sim_info_to_filter_term(created_sim_info, self.skill, **kwargs)

class SkillListFilterTerm(SkillFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if len(value.skill_list) == 0:
            logger.error('TunableSkillListFilterTerm {} has a filter term {} with no Skills in the list.', source, tunable_name)
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('TunableSkillListFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].', source, tunable_name, value.ideal_value, value.min_value, value.max_value)
        if len(value.skill_list) < value.minimum_valid_skills:
            logger.error('TunableSkillListFilterTerm {} has not enough skills in the list to be valid {} compared to the minimum_valid_skills', source, tunable_name)

    FACTORY_TUNABLES = {'skill_list': TunableList(description='\n            List of skills for the sims to be included in the group.\n            ', tunable=TunableReference(description='\n                The list of skills the range applies to.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Skill',), pack_safe=True)), 'minimum_valid_skills': Tunable(description='\n            Minimum number of skills that fit with the range\n            ', tunable_type=int, default=1), 'locked_args': {'skill': None, 'statistic': None}, 'verify_tunable_callback': _verify_tunable_callback}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, tag=FilterTermTag.NO_TAG, **kwargs):
        best_score = FilterResult(score=self.invert_score_if_necessary(0), sim_info=sim_info, tag=tag)
        number_valid_skills = 0
        for skill in self.skill_list:
            score_result = self._calculate_score(sim_info, skill, tag, **kwargs)
            score = score_result.score
            if score != self.invert_score_if_necessary(0):
                number_valid_skills += 1
            if score > best_score.score:
                best_score = score_result
        if number_valid_skills >= self.minimum_valid_skills:
            return best_score
        return FilterResult(score=self.invert_score_if_necessary(0), sim_info=sim_info, tag=tag)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        number_valid_skills = 0
        for skill in self.skill_list:
            if self._conform_sim_info_to_filter_term(created_sim_info, skill, **kwargs) == FilterResult.TRUE:
                number_valid_skills += 1
                if number_valid_skills >= self.minimum_valid_skills:
                    return FilterResult.TRUE
        return FilterResult('Failed to add required number of skills, possibly due to age or gender restrictions: {}', self.skill_list[0].__name__, score=0, sim_info=created_sim_info)

class RankedStatisticFilterTerm(StatisticFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('TunableRankedStatisticFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].', source, tunable_name, value.ideal_value, value.min_value, value.max_value)

    FACTORY_TUNABLES = {'ranked_statistic': TunablePackSafeReference(description='\n            The ranked statistic the range applies to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',)), 'min_value': Tunable(description='\n            Minimum value of the ranked statistic that we are filtering against.\n            ', tunable_type=int, default=0), 'max_value': Tunable(description='\n            Maximum value of the ranked statistic that we are filtering against.\n            ', tunable_type=int, default=5), 'ideal_value': Tunable(description='\n            Ideal value of the ranked statistic that we are filtering against.\n            ', tunable_type=int, default=2), 'use_rank': Tunable(description='\n            If checked then use the rank value instead of the point value for\n            our calculations.\n            ', tunable_type=bool, default=True), 'verify_tunable_callback': _verify_tunable_callback, 'locked_args': {'statistic': None}}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, tag=FilterTermTag.NO_TAG, **kwargs):
        if self.ranked_statistic is None:
            return FilterResult(score=self.invert_score_if_necessary(0), sim_info=sim_info)
        return self._calculate_score(sim_info, self.ranked_statistic, tag, use_rank=self.use_rank, **kwargs)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if self.ranked_statistic is None:
            if self.invert_score:
                return FilterResult.TRUE
            return FilterResult('Failed to conform sim creator to filter since Ranked Statistic is None in Ranked Statistic filter term.', score=0)
        return self._conform_sim_info_to_filter_term(created_sim_info, self.ranked_statistic, use_rank=self.use_rank, **kwargs)

    def set_ranked_statistic(self, ranked_statistic):
        self.ranked_statistic = ranked_statistic

class CareerFilterTerm(InvertibleFilterTerm):

    class _CareerTypeExplicit(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'career_type': TunableReference(description='\n                The career that this term applies to. Sims that are conformed to the\n                filter will enter the career at its entry level.\n                ', manager=services.get_instance_manager(sims4.resources.Types.CAREER))}

        def get_careers_for_conformation_gen(self, sim_info, filter_term):
            yield self.career_type

        def get_careers_for_score_gen(self, sim_info):
            career_tracker = sim_info.career_tracker
            if career_tracker is not None:
                career = career_tracker.get_career_by_uid(self.career_type.guid64)
                if career:
                    yield career

    class _CareerTypeFromCategory(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'career_category': TunableEnumEntry(description='\n                The career category that this filter term applies to. Sims may\n                be conformed if we want to remove the career, i.e. the term is\n                inverted, but may not be conformed to join a career.\n                ', tunable_type=CareerCategory, default=CareerCategory.Work)}

        def get_careers_for_conformation_gen(self, sim_info, filter_term):
            if filter_term.career_level is not None and filter_term.career_level.specifies_careers:
                yield from filter_term.career_level.get_unique_careers(self.career_category)
            elif filter_term.invert_score:
                yield from self.get_careers_for_score_gen(sim_info)
            else:
                yield from services.get_career_service().get_careers_by_category_gen(self.career_category)

        def get_careers_for_score_gen(self, sim_info):
            career_tracker = sim_info.career_tracker
            if career_tracker is not None:
                yield from career_tracker.get_careers_by_category_gen(self.career_category)

    class _CareerLocationFilterActiveLot(HasTunableSingletonFactory):

        def calculate_career_score(self, career):
            career_location = career.get_career_location()
            if career_location.get_zone_id() != services.current_zone_id():
                return 0
            return 1

        def conform_career(self, career):
            career_location = career.get_career_location()
            career_location.set_zone_id(services.current_zone_id())

    class _CareerScheduleFilterAvailableNow(HasTunableSingletonFactory):

        def calculate_career_score(self, career):
            if career.is_time_during_shift():
                return 1
            return 0

        def conform_career(self, career):
            pass

    class _CareerUserLevelFilter(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'career_user_level': TunableRange(description='\n                A user level. If this level cooresponds to an advanced branch\n                and we conform or generate a sim with this filter and the career \n                has branches a branch will be chosen at random. If this behavior\n                is not desired, use Career Level Reference instead.\n                ', tunable_type=int, default=1, minimum=1)}

        def calculate_career_score(self, career):
            if self.career_user_level == career.user_level:
                return 1
            return 0

        def user_level_override(self):
            return self.career_user_level

        def career_level_override(self, career):
            pass

        @property
        def specifies_careers(self):
            return False

    class _CareerLevelReferenceFilter(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'career_level_references': TunableList(description='\n                A list of CareerLevels. One will be randomly chosen\n                when conforming sims.\n                ', tunable=TunableReference(description='\n                    A reference to a CareerLevel to join the career at.\n                    The CareerLevel must belong to the career tuned above.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_LEVEL), pack_safe=True))}

        def user_level_override(self):
            pass

        def calculate_career_score(self, career):
            if career.current_level_tuning in self.career_level_references:
                return 1
            return 0

        def career_level_override(self, career):
            career_guid = career.guid64
            potential_level_references = [level_reference for level_reference in self.career_level_references if level_reference.career.guid64 is career_guid]
            if potential_level_references:
                return random.choice(potential_level_references)

        @property
        def specifies_careers(self):
            return True

        def get_unique_careers(self, career_category):
            careers = set()
            for career_level_reference in self.career_level_references:
                if career_level_reference.career.career_category == career_category:
                    careers.add(career_level_reference.career)
            return careers

    FACTORY_TUNABLES = {'career': TunableVariant(description='\n            Define the career that this filter term applies to.\n            ', from_explicit_type=_CareerTypeExplicit.TunableFactory(), from_category=_CareerTypeFromCategory.TunableFactory(), default='from_explicit_type'), 'career_location': TunableVariant(description='\n            Define how important career location is for this filter. Leave None\n            if location is not important.\n            ', on_active_lot=_CareerLocationFilterActiveLot.TunableFactory(), default=None), 'career_schedule': TunableVariant(description='\n            Define how scheduling affects this filter. Leave None if schedule is\n            not important.\n            ', available_now=_CareerScheduleFilterAvailableNow.TunableFactory(), default=None), 'career_seniority': Tunable(description='\n            If enabled, Sims that have been in the career for longer will score\n            higher than Sims that have been in the career for less time.\n            ', tunable_type=bool, default=True), 'career_level': OptionalTunable(description='\n            If enabled we add an additional requirement of the user level of\n            the career to the requirements.\n            ', tunable=TunableVariant(career_user_level=_CareerUserLevelFilter.TunableFactory(), career_level_reference=_CareerLevelReferenceFilter.TunableFactory(), default='career_level_reference')), 'only_requesting_sim_careers': Tunable(description="\n            If enabled, after generating careers that the sim can conform to, \n            filter out careers that the requesting sim doesn't have.\n            \n            Ex. Requesting sim has the detective career, no sim was found that fit the filter terms,\n            so we want to create a new sim that is in the same career as the requesting sim. \n            ", tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return True

    def can_repurpose_sim_info(self, sim_info):
        for career in self.career.get_careers_for_conformation_gen(sim_info, self):
            if career.is_valid_career(sim_info):
                return True
        return False

    def calculate_score(self, sim_info, **kwargs):
        max_score = 0
        reason = None
        for career in self.career.get_careers_for_score_gen(sim_info):
            score = 1
            reason = ''
            if self.career_location is not None:
                score *= self.career_location.calculate_career_score(career)
                if score == 0:
                    reason = 'Career Location returned score of 0'
                elif self.career_schedule is not None:
                    score *= self.career_schedule.calculate_career_score(career)
                    if score == 0 and not reason:
                        reason = 'Career Schedule returned score of 0'
                    elif self.career_seniority:
                        score *= career.get_career_seniority()
                        if score == 0 and not reason:
                            reason = 'Career Seniority returned score of 0'
                        elif self.career_level is not None:
                            score *= self.career_level.calculate_career_score(career)
                            if score == 0 and not reason:
                                reason = 'Career level does not match actual career level.'
                            elif score > max_score:
                                max_score = score
                        elif score > max_score:
                            max_score = score
                    elif self.career_level is not None:
                        score *= self.career_level.calculate_career_score(career)
                        if score == 0 and not reason:
                            reason = 'Career level does not match actual career level.'
                        elif score > max_score:
                            max_score = score
                    elif score > max_score:
                        max_score = score
                elif self.career_seniority:
                    score *= career.get_career_seniority()
                    if score == 0 and not reason:
                        reason = 'Career Seniority returned score of 0'
                    elif self.career_level is not None:
                        score *= self.career_level.calculate_career_score(career)
                        if score == 0 and not reason:
                            reason = 'Career level does not match actual career level.'
                        elif score > max_score:
                            max_score = score
                    elif score > max_score:
                        max_score = score
                elif self.career_level is not None:
                    score *= self.career_level.calculate_career_score(career)
                    if score == 0 and not reason:
                        reason = 'Career level does not match actual career level.'
                    elif score > max_score:
                        max_score = score
                elif score > max_score:
                    max_score = score
            elif self.career_schedule is not None:
                score *= self.career_schedule.calculate_career_score(career)
                if score == 0 and not reason:
                    reason = 'Career Schedule returned score of 0'
                elif self.career_seniority:
                    score *= career.get_career_seniority()
                    if score == 0 and not reason:
                        reason = 'Career Seniority returned score of 0'
                    elif self.career_level is not None:
                        score *= self.career_level.calculate_career_score(career)
                        if score == 0 and not reason:
                            reason = 'Career level does not match actual career level.'
                        elif score > max_score:
                            max_score = score
                    elif score > max_score:
                        max_score = score
                elif self.career_level is not None:
                    score *= self.career_level.calculate_career_score(career)
                    if score == 0 and not reason:
                        reason = 'Career level does not match actual career level.'
                    elif score > max_score:
                        max_score = score
                elif score > max_score:
                    max_score = score
            elif self.career_seniority:
                score *= career.get_career_seniority()
                if score == 0 and not reason:
                    reason = 'Career Seniority returned score of 0'
                elif self.career_level is not None:
                    score *= self.career_level.calculate_career_score(career)
                    if score == 0 and not reason:
                        reason = 'Career level does not match actual career level.'
                    elif score > max_score:
                        max_score = score
                elif score > max_score:
                    max_score = score
            elif self.career_level is not None:
                score *= self.career_level.calculate_career_score(career)
                if score == 0 and not reason:
                    reason = 'Career level does not match actual career level.'
                elif score > max_score:
                    max_score = score
            elif score > max_score:
                max_score = score
        if max_score == 0:
            reason = 'Career is None'
        return FilterResult(reason, score=self.invert_score_if_necessary(max_score), sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, requesting_sim_info=None, **kwargs):
        career_tracker = created_sim_info.career_tracker
        careers = list(self.career.get_careers_for_conformation_gen(created_sim_info, self))
        (requesting_career_tracker, reason) = self._get_requesting_sim_career_tracker(requesting_sim_info)
        if reason is not None:
            return FilterResult(reason, score=self.invert_score_if_necessary(0), sim_info=created_sim_info)
        random.shuffle(careers)
        for career in careers:
            if requesting_career_tracker is not None and requesting_career_tracker.get_career_by_uid(career.guid64) is None:
                pass
            elif self.invert_score:
                career_tracker.remove_career(career.guid64)
            elif career.is_valid_career(created_sim_info):
                career = career(created_sim_info)
                if self.career_location is not None:
                    self.career_location.conform_career(career)
                if self.career_schedule is not None:
                    self.career_schedule.conform_career(career)
                if self.career_level is not None:
                    career_tracker.add_career(career, user_level_override=self.career_level.user_level_override(), career_level_override=self.career_level.career_level_override(career))
                else:
                    career_tracker.add_career(career)
                break
        return self.calculate_score(created_sim_info)

    def _get_requesting_sim_career_tracker(self, requesting_sim_info):
        reason = None
        if not self.only_requesting_sim_careers:
            return (None, reason)
        if requesting_sim_info is None:
            reason = "Only use requesting sim's careers is enabled, but no sim info was found."
            return (None, reason)
        career_tracker = requesting_sim_info.career_tracker
        if career_tracker is None:
            reason = 'Requesting sim career tracker is None.'
        elif not career_tracker.careers:
            reason = 'Requesting sim does not have any careers.'
        return (career_tracker, reason)

class UniversityMajorFilterTerm(InvertibleFilterTerm):
    TOP_SKILLS_NUMBER = 3

    class _SpecificMajors(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'_majors': TunableList(description='\n                Sim must be currently enrolled in one of the specified majors.\n                ', tunable=TunableReference(description='\n                    ', manager=services.get_instance_manager(sims4.resources.Types.UNIVERSITY_MAJOR)), minlength=1)}

        def get_major_for_conformation(self, created_sim_info):
            return random.choice(self._majors)

        def get_score(self, sim_info):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                return 0
            else:
                major = degree_tracker.get_enrolled_major()
                if major in self._majors:
                    return 1
            return 0

    class _AnyMajors(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'conform_using_skills': Tunable(description='\n                If checked then when we conform a Sim using this filter term\n                we will use the Sims skills to choose which Major to enroll \n                them in. If unchecked we will pick one randomly.\n                ', tunable_type=bool, default=False)}

        def get_major_for_conformation(self, created_sim_info):
            if self.conform_using_skills:
                skill_values = set()
                commodity_tracker = created_sim_info.commodity_tracker
                for skill in University.SKILL_TO_MAJOR_TUNING.keys():
                    skill_value = commodity_tracker.get_value(skill)
                    skill_values.add((skill, skill_value))
                skill_values = sorted(skill_values, key=operator.itemgetter(1), reverse=True)
                skill_values = skill_values[:UniversityMajorFilterTerm.TOP_SKILLS_NUMBER]
                skill_to_use = random.choice(skill_values)[0]
                major_list = University.SKILL_TO_MAJOR_TUNING[skill_to_use]
                return random.choice(major_list)
            return University.choose_random_major()

        def get_score(self, sim_info):
            degree_tracker = sim_info.degree_tracker
            if degree_tracker is None:
                return 0
            elif degree_tracker.get_enrolled_major() is not None:
                return 1
            return 0

    FACTORY_TUNABLES = {'major': TunableVariant(description='\n            Which major(s) the sim must be pursuing.\n            ', any_majors=_AnyMajors.TunableFactory(), specific_majors=_SpecificMajors.TunableFactory(), default='any_majors'), 'university': OptionalTunable(description='\n            University in which the sim must be enrolled.\n            If Disabled, sim can be in any university.\n            ', tunable=TunableReference(description='\n                The university to filter for.\n                ', manager=services.get_instance_manager(Types.UNIVERSITY)))}

    @property
    def is_sim_info_conformable(self):
        return True

    def can_repurpose_sim_info(self, sim_info):
        degree_tracker = sim_info.degree_tracker
        if degree_tracker is None:
            return False
        return degree_tracker.get_enrolled_major() is None

    def calculate_score(self, sim_info, **kwargs):
        score = self.major.get_score(sim_info)
        reason = ''
        if score == 0:
            reason = 'not enrolled in specified major(s)'
        elif self.university is not None:
            current_university = sim_info.degree_tracker.get_university()
            if current_university is None or current_university.guid64 != self.university.guid64:
                score = 0
                reason = 'not enrolled in specified university'
        return FilterResult(reason, score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def get_random_university(self):
        all_universities = list(services.get_instance_manager(sims4.resources.Types.UNIVERSITY).types.values())
        if not all_universities:
            return
        return random.choice(all_universities)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if not self.invert_score:
            degree_tracker = created_sim_info.degree_tracker
            if degree_tracker is not None and degree_tracker.get_enrollment_status() != EnrollmentStatus.ENROLLED:
                major = self.major.get_major_for_conformation(created_sim_info)
                if major is not None:
                    if self.university is None:
                        university = self.get_random_university()
                    else:
                        university = self.university
                    degree_tracker.process_acceptance(send_telemetry=False)
                    if not degree_tracker.is_accepted_degree(university, major):
                        degree_tracker.set_accepted_degree(university, major)
                    degree_tracker.enroll(major, university, 3, [])
        return self.calculate_score(created_sim_info)

    def set_university(self, university):
        self.university = university

class SickSimFilterTerm(InvertibleFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.difficulty_range is not None and value.invert_score:
            logger.error('SickSimFilterTerm: {} has a filter term {} that setsa difficulty range but inverts score.This is ambiguous and not supported.', source, tunable_name)

    FACTORY_TUNABLES = {'difficulty_range': OptionalTunable(description="\n            Optionally define the difficulty rating range that is required\n            for the Sim's sickness.\n            ", tunable=TunableInterval(description="\n                The difficulty rating range, this maps to 'difficulty_rating'\n                values in Sickness tuning.\n                ", tunable_type=float, default_lower=0, default_upper=10, minimum=0, maximum=10)), 'verify_tunable_callback': _verify_tunable_callback}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        if self.difficulty_range is None:
            score = 1 if sim_info.is_sick() else 0
        else:
            score = 1 if sim_info.is_sick() and sim_info.current_sickness.difficulty_rating in self.difficulty_range else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def can_repurpose_sim_info(self, sim_info):
        if self.invert_score:
            return not sim_info.is_sick()
        elif self.difficulty_range is not None and sim_info.is_sick():
            return self.calculate_score(sim_info)
        return True

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if self.invert_score:
            if created_sim_info.is_sick():
                return FilterResult('Cannot conform a sick Sim to be non-sick.', score=0)
        elif not created_sim_info.is_sick():
            sickness_criteria = None if self.difficulty_range is None else lambda s: s.difficulty_rating in self.difficulty_range
            services.get_sickness_service().make_sick(created_sim_info, criteria_func=sickness_criteria)
        return super().conform_sim_info_to_filter_term(created_sim_info, **kwargs)

class TraitFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'trait': TunablePackSafeReference(description='\n            The trait to filter against.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), 'ignore_if_wrong_pack': Tunable(description="\n            If checked then we will ignore this filter term if the specified\n            trait isn't found.  (.e.g. trait is from uninstalled pack.)\n            For example we'd *like* to pick sims that use umbrellas.  But if \n            Seasons isn't installed it's ok to use sims that don't.\n            ", tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        score = 0
        if self.trait is None:
            if self.ignore_if_wrong_pack:
                return FilterResult(score=1, sim_info=sim_info)
        elif sim_info.trait_tracker.has_trait(self.trait):
            score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        if self.trait is None:
            if self.invert_score or self.ignore_if_wrong_pack:
                return FilterResult.TRUE
            return FilterResult('Failed to conform sim creator to filter since trait is None in trait filter term.', score=0)
        else:
            if not self.invert_score:
                sim_creator.traits.add(self.trait)
            return FilterResult.TRUE

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if self.trait is None and (self.invert_score or self.ignore_if_wrong_pack):
            return FilterResult.TRUE
        if self.invert_score != created_sim_info.trait_tracker.has_trait(self.trait):
            return FilterResult.TRUE
        if self.invert_score:
            if not created_sim_info.remove_trait(self.trait):
                return FilterResult('Failed conform sim to filter by removing trait {}', self.trait, sim_info=created_sim_info, score=0)
        elif not created_sim_info.add_trait(self.trait):
            return FilterResult('Failed conform sim to filter by adding trait {}', self.trait, sim_info=created_sim_info, score=0)
        return FilterResult.TRUE

class TraitBlacklistFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'traits': TunableSet(description='\n            The traits to filter against.\n            ', tunable=TunableReference(description='\n                A trait the Sim should NOT have\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True))}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        if self.traits and set(sim_info.trait_tracker) & self.traits:
            return FilterResult(score=0, sim_info=sim_info)
        return FilterResult(score=1, sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if not self.traits:
            return FilterResult.TRUE
        created_sim_traits_to_remove = set(created_sim_info.trait_tracker) & self.traits
        if created_sim_traits_to_remove:
            for trait in created_sim_traits_to_remove:
                if not created_sim_info.remove_trait(trait):
                    return FilterResult('Failed conform sim to filter by removing trait {}', trait, sim_info=created_sim_info, score=0)
        return FilterResult.TRUE

class SpeciesFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'species': TunableEnumEntry(description='\n            The species to filter for.\n            ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), 'additional_species': TunableEnumSet(description='\n            A set of additional species to filter for.\n            ', enum_type=Species, enum_default=Species.HUMAN, invalid_enums=Species.INVALID, allow_empty_set=True)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 1 if sim_info.species in {self.species} | self.additional_species else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        all_species = {self.species} | self.additional_species
        if SpeciesExtended.get_species(sim_creator.species) not in all_species:
            sim_creator.species = random.choice(list(itertools.chain.from_iterable(SpeciesExtended.get_species_extended(species) for species in all_species)))
        return FilterResult.TRUE

class AgeFilterTerm(InvertibleFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('TunableAgeFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].'.format(source, tunable_name, value.ideal_value, value.min_value, value.max_value))

    FACTORY_TUNABLES = {'min_value': TunableEnumEntry(description='\n            The minimum age of the sim we are filtering for.\n            ', tunable_type=Age, default=Age.BABY), 'max_value': TunableEnumEntry(description='\n            The maximum age of the sim we are filtering for.\n            ', tunable_type=Age, default=Age.ELDER), 'ideal_value': TunableEnumEntry(description='\n            The ideal age of the sim we are filtering for.\n            ', tunable_type=Age, default=Age.ADULT), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._min_value_int = self.min_value.sequential_value
        self._max_value_int = self.max_value.sequential_value
        self._ideal_value_int = self.ideal_value.sequential_value

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        value = sim_info.age.sequential_value
        score = calculate_score_from_value(value, self._min_value_int, self._max_value_int, self._ideal_value_int)
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        if self.invert_score and sim_creator.age != self.ideal_value != self.min_value <= sim_creator.age <= self.max_value:
            return FilterResult.TRUE
        if self.invert_score:
            if self.min_value == sim_creator.age and sim_creator.age == self.max_value:
                return FilterResult('Cannot find valid age in order to conform sim to age filter term.', score=0)
            if self.min_value == sim_creator.age:
                sim_creator.age = self.max_value
            elif self.max_value == sim_creator.age:
                sim_creator.age = self.min_value
            else:
                sim_creator.age = random.choice([self.min_value, self.max_value])
        else:
            sim_creator.age = self.ideal_value
        return FilterResult.TRUE

    def is_compatible(self, other:'BaseFilterTerm') -> 'bool':
        if not self._is_comparable(other):
            return True
        self_min = self._min_value_int
        self_max = self._max_value_int
        comp_min = other.min_value.sequential_value
        comp_max = other.max_value.sequential_value
        if self.invert_score or not other.invert_score:
            if comp_max < self_min:
                return False
            if self_max < comp_min:
                return False
        elif self.invert_score and other.invert_score:
            window1 = max(min(self_min, comp_min) - Age.BABY.sequential_value, 0)
            window2 = max(max(self_min, comp_min) - min(self_max, comp_max), 0)
            window3 = max(Age.ELDER.sequential_value - max(self_max, comp_max), 0)
            if window1 + window2 + window3 < 1:
                return False
        elif self.invert_score and not other.invert_score:
            if self_min < comp_min and self_max > comp_max:
                return False
        elif self.invert_score or other.invert_score and comp_min < self_min and comp_max > self_max:
            return False
        return True

class AgeVariationFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'allowed_ages': TunableEnumSet(description="\n            The allowed ages we're filtering for.\n            ", enum_type=sims.sim_info_types.Age, enum_default=sims.sim_info_types.Age.ADULT)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        if sim_info.age in self.allowed_ages:
            return FilterResult(score=1, sim_info=sim_info)
        return FilterResult(score=0, sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        if sim_creator.age not in self.allowed_ages:
            chosen_age = random.choice(tuple(self.allowed_ages))
            sim_creator.age = chosen_age
        return FilterResult.TRUE

class GenderFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'gender': TunableEnumEntry(description='\n            The required gender of the sim we are filtering for.\n            ', tunable_type=Gender, default=Gender.MALE)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        if sim_info.gender is self.gender:
            return FilterResult(score=1, sim_info=sim_info)
        return FilterResult(score=0, sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        sim_creator.gender = self.gender
        return FilterResult.TRUE

    def set_gender(self, gender):
        self.gender = gender

    def is_compatible(self, other:'BaseFilterTerm') -> 'bool':
        if not self._is_comparable(other):
            return True
        elif other.gender == self.gender:
            return True
        return False

class GenderRelativeFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'same': Tunable(description='\n            If checked then we will make sure that the sim is the same gender\n            as the target sim.  Otherwise the opposite gender\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if sim_info.gender is self._get_target_gender(requesting_sim_info):
            return FilterResult(score=1, sim_info=sim_info)
        return FilterResult(score=0, sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, requesting_sim_info=None, **kwargs):
        sim_creator.gender = self._get_target_gender(requesting_sim_info)
        return FilterResult.TRUE

    def _get_target_gender(self, requesting_sim_info):
        if self.same:
            return requesting_sim_info.gender
        return Gender.get_opposite(requesting_sim_info.gender)

class HouseholdValueFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'household_value': TunableInterval(description="\n            An interval the Sim's household value must be between in order to\n            conform to this filter term.\n            ", tunable_type=int, default_lower=0, default_upper=1000, minimum=0)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        if self.household_value.lower_bound <= sim_info.household.household_net_worth() and sim_info.household.household_net_worth() <= self.household_value.upper_bound:
            return FilterResult(score=1, sim_info=sim_info)
        return FilterResult(score=0, sim_info=sim_info)

class HouseholdCompositionFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'age': OptionalTunable(description='\n            Define an age condition for Sims in the household.\n            ', tunable=AgeFilterTerm.TunableFactory(), disabled_name='Dont_Care'), 'gender': OptionalTunable(description='\n            Define a gender condition for Sims in the household.\n            ', tunable=GenderFilterTerm.TunableFactory(), disabled_name='Dont_Care'), 'species': OptionalTunable(description='\n            Define a species condition for Sims in the household.\n            ', tunable=SpeciesFilterTerm.TunableFactory(), disabled_name='Dont_Care'), 'statistic': OptionalTunable(description='\n            Define a statistic condition for Sims in the household.\n            ', tunable=StatisticFilterTerm.TunableFactory(), disabled_name='Dont_Care'), 'ranked_statistic': OptionalTunable(description='\n            Define a ranked statistic condition for Sims in the household.\n            ', tunable=RankedStatisticFilterTerm.TunableFactory(), disabled_name='Dont_Care'), 'trait': OptionalTunable(description='\n            Define a trait condition for Sims in the household.\n            ', tunable=TraitFilterTerm.TunableFactory(), disabled_name='Dont_Care'), 'threshold': TunableThreshold(description='\n            Define the required number of Sims required in order to satisfy the\n            term.\n            ')}

    @property
    def is_sim_info_conformable(self):
        return False

    def _sim_matches_composition_requirements(self, sim_info):
        if self.age is not None and not self.age.calculate_score(sim_info):
            return False
        if self.gender is not None and not self.gender.calculate_score(sim_info):
            return False
        if self.species is not None and not self.species.calculate_score(sim_info):
            return False
        if self.statistic is not None and not self.statistic.calculate_score(sim_info):
            return False
        if self.ranked_statistic is not None and not self.ranked_statistic.calculate_score(sim_info):
            return False
        elif self.trait is not None and not self.trait.calculate_score(sim_info):
            return False
        return True

    def calculate_score(self, sim_info, **kwargs):
        match_count = sum(1 for household_sim_info in sim_info.household if self._sim_matches_composition_requirements(household_sim_info))
        if not self.threshold.compare(match_count):
            return FilterResult(score=0, sim_info=sim_info)
        return FilterResult(score=1, sim_info=sim_info)

class ClubMembershipFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        club_service = services.get_club_service()
        if club_service is None:
            logger.error('Attempting to run a ClubMembershipFilterTerm but the Club Service does not exist.', owner='tastle')
            return FilterResult(score=0, sim_info=sim_info)
        if club_service.can_sim_info_join_more_clubs(sim_info):
            score = 1
        else:
            score = 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class InClubFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'check_if_requesting_sim_can_join': Tunable(description='\n            If checked then we will make sure that the requesting Sim can join\n            one of the clubs of this Sim.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        self._specific_club_id = kwargs.get('specific_club_id', None)
        super().__init__(*args, **kwargs)

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        score = 0
        club_service = services.get_club_service()
        if club_service is None:
            logger.error('Attempting to run a InClubFilterTerm but the Club Service does not exist.', owner='tastle')
            return FilterResult(score=score, sim_info=sim_info)
        clubs = club_service.get_clubs_for_sim_info(sim_info)
        if self.check_if_requesting_sim_can_join:
            if requesting_sim_info is None:
                return FilterResult('Trying to make sure that the requesting sim info could join a club, but no requesting sim info was given.', score=score, sim_info=sim_info)
            for club in clubs:
                if club.can_sim_info_join(requesting_sim_info):
                    score = 1
                    break
        elif clubs:
            if self._specific_club_id is None:
                score = 1
            else:
                for club in clubs:
                    if club is not None and club.club_id == self._specific_club_id:
                        score = 1
                        break
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def set_specific_club_id(self, club_id):
        self._specific_club_id = club_id

class InSameClubFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'check_supplied_club': Tunable(description='\n            If checked then we will check if the Sim is in a specific supplied\n            club.  Check with your GPE before using this option because it will\n            only work when the data is properly supplied by gameplay.\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, club=None, **kwargs):
        club_service = services.get_club_service()
        if club_service is None:
            logger.error('Attempting to run a InSameClubFilterTerm but the Club Service does not exist.', owner='tastle')
            return FilterResult(score=0, sim_info=sim_info)
        if self.check_supplied_club:
            if club is None:
                return FilterResult('Trying to check if Sims are in the same club, but no club was supplied.', score=0, sim_info=sim_info)
            requesting_clubs = {club}
        else:
            if requesting_sim_info is None:
                return FilterResult('Trying to check if Sims are in the same club, but there is no requesting sim info.', score=0, sim_info=sim_info)
            requesting_clubs = club_service.get_clubs_for_sim_info(requesting_sim_info)
        sim_info_clubs = club_service.get_clubs_for_sim_info(sim_info)
        score = 1 if sim_info_clubs & requesting_clubs else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class CasTagsFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'cas_tags': TunableSet(description='\n            Sims must have at least one of these tags on their parts for the\n            filter to pass.\n            ', tunable=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID)), 'creation_cas_tags': OptionalTunable(description='\n            The tags to use when creating a new Sim with this filter term.\n            \n            This should be same_as_cas_tags for almost all cases. Note that\n            custom cas tags are supplied, the Sim must still have Cas Tags\n            for sim creation to succeed.\n            ', tunable=tag.TunableTags(minlength=1, pack_safe=False), disabled_name='same_as_cas_tags', enabled_name='custom')}

    @property
    def is_sim_info_conformable(self):
        return False

    def _get_sim_creator_cas_tags(self):
        if self.creation_cas_tags is not None:
            return self.creation_cas_tags
        return self.cas_tags

    def _get_scoring_cas_tags(self):
        return self.cas_tags

    def calculate_score(self, sim_info, **kwargs):
        cas_tags = self._get_scoring_cas_tags()
        try:
            tags = get_tags_from_outfit(sim_info._base, sim_info.get_current_outfit())
        except Exception as exc:
            logger.error('Failed to calculate CAS Filter Tag Term for Sim {} with current outfit: {}\nException: {}', sim_info, sim_info.get_current_outfit(), exc, owner='bhill', trigger_breakpoint=True)
            return FilterResult(score=0, sim_info=sim_info)
        if cas_tags & set().union(*tags.values()):
            return FilterResult(score=1, sim_info=sim_info)
        return FilterResult(score=0, sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        cas_tags = self._get_sim_creator_cas_tags()
        sim_creator.tag_set.update(cas_tags)
        return FilterResult.TRUE

class IsBusyFilterTerm(InvertibleFilterTerm):
    OVERRIDE_SELECTABLE = 1
    OVERRIDE_NPC = 2
    FACTORY_TUNABLES = {'override': TunableVariant(description='\n            Determine a set of Sims that is never considered busy.\n            ', locked_args={'no_override': None, 'selectable_sims': OVERRIDE_SELECTABLE, 'npc_sims': OVERRIDE_NPC}, default='no_override')}

    @property
    def is_sim_info_conformable(self):
        return False

    def _is_sim_overriden(self, sim_info):
        if self.override == self.OVERRIDE_SELECTABLE:
            return sim_info.is_selectable
        elif self.override == self.OVERRIDE_NPC:
            return not sim_info.is_selectable
        return False

    def calculate_score(self, sim_info, start_time_ticks=None, end_time_ticks=None, **kwargs):
        (is_busy, career) = sim_info.is_busy(start_time_ticks=start_time_ticks, end_time_ticks=end_time_ticks)
        is_busy_score = 1 if is_busy else 0
        score = self.invert_score_if_necessary(is_busy_score)
        if is_busy_score and self._is_sim_overriden(sim_info):
            return FilterResult(sim_info=sim_info, conflicting_career_track_id=None if career is None else career.current_track_tuning.guid64)
        return FilterResult(score=score, sim_info=sim_info)

class IsHiddenFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 1 if services.hidden_sim_service().is_hidden(sim_info.id) else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class IsHiddenRelationshipFilerTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    @staticmethod
    def _is_hidden_relationship(sim_info, requesting_sim_info) -> 'bool':
        if requesting_sim_info is None:
            return False
        return services.relationship_service().is_hidden(sim_info.id, requesting_sim_info.id)

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        score = 1 if self._is_hidden_relationship(sim_info, requesting_sim_info) else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class IsNeighborFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def _is_neighbor(self, sim_info, requesting_sim_info):
        if sim_info.household is None or requesting_sim_info is None or requesting_sim_info.household is None:
            return False
        home_zone_id = sim_info.household.home_zone_id
        target_home_zone_id = requesting_sim_info.household.home_zone_id
        if home_zone_id == target_home_zone_id:
            return False
        if home_zone_id == 0 or target_home_zone_id == 0:
            return False
        sim_home_zone_proto_buffer = services.get_persistence_service().get_zone_proto_buff(home_zone_id)
        target_sim_home_zone_proto_buffer = services.get_persistence_service().get_zone_proto_buff(target_home_zone_id)
        if sim_home_zone_proto_buffer is None or target_sim_home_zone_proto_buffer is None:
            return False
        elif sim_home_zone_proto_buffer.world_id != target_sim_home_zone_proto_buffer.world_id:
            return False
        return True

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        is_neighbor = 0
        if self._is_neighbor(sim_info, requesting_sim_info):
            is_neighbor = 1
        score = self.invert_score_if_necessary(is_neighbor)
        return FilterResult(score=score, sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a neighbor sim', score=0)
        return FilterResult.TRUE

class LivesOnApartmentFloor(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        home_zone_id = sim_info.household.home_zone_id
        if not home_zone_id:
            home_zone_id = sim_info.roommate_zone_id
        current_zone_id = services.current_zone_id()
        plex_service = services.get_plex_service()
        plex_zones = plex_service.get_plex_zones_in_group(current_zone_id)
        score = 1 if home_zone_id in plex_zones else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a sim on the current apartment floor.', score=0)
        return FilterResult.TRUE

class LivesInCurrentZone(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self) -> 'bool':
        return False

    def calculate_score(self, sim_info:'SimInfo', **kwargs) -> 'float':
        home_zone_id = sim_info.household.home_zone_id
        if not home_zone_id:
            home_zone_id = sim_info.roommate_zone_id
        current_zone_id = services.current_zone_id()
        score = 1 if home_zone_id == current_zone_id else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs) -> 'FilterResult':
        if not self.invert_score:
            return FilterResult('Unable to create a sim that lives in current zone', score=0)
        return FilterResult.TRUE

class LivesOnStreetFilterTerm(DemographicsFilterTermMixin, InvertibleFilterTerm):

    class MustMatch(HasTunableSingletonFactory):

        @property
        def allow_if_world_meets_townie_population_cap(self):
            return False

    class MatchTargetPopulation(HasTunableSingletonFactory):

        @property
        def allow_if_world_meets_townie_population_cap(self):
            return True

    FACTORY_TUNABLES = {'street': OptionalTunable(description='\n            The street the Sim must live on.\n            ', tunable=TunableWorldDescription(), disabled_name='current_street', enabled_name='specific_street'), 'match_criteria': TunableVariant(description="\n            Criteria for a Sim to match this filter. This tunable is ignored if\n            the filter is inverted. If inverted, the filter passes if the Sim\n            doesn't live on the street and fails if so.\n            \n            Match Target Population: If the number of townies living on the\n            tuned street meets or exceeds the street's tuned townie threshold,\n            then this filter term will be considered met.\n            \n            Must Match: The Sim chosen or created must live on the street.\n            ", match_target_population=MatchTargetPopulation.TunableFactory(), must_match=MustMatch.TunableFactory(), default='match_target_population')}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        target_world_id = self._get_world_id_for_tuned_street()
        home_world_id = sim_info.household.get_home_world_id()
        if not sim_info.household.home_zone_id:
            zone_id = sim_info.roommate_zone_id
            if zone_id != 0:
                zone = services.get_zone_manager().get(zone_id)
                if zone is not None:
                    home_world_id = zone.open_street_id
        score = 1 if home_world_id == target_world_id else 0
        if self.match_criteria.allow_if_world_meets_townie_population_cap:
            score = 1 if services.get_demographics_service().world_meets_townie_population_cap(target_world_id) else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def _get_world_id_for_tuned_street(self):
        if self.street is not None:
            return services.get_world_id(self.street)
        return services.current_zone().open_street_id

    def get_valid_world_ids(self):
        world_id = self._get_world_id_for_tuned_street()
        if self.invert_score:
            return (None, {world_id})
        return ({world_id}, None)

class LivesTogetherFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'consider_household': Tunable(description='\n            If enabled, this will succeed if the Sim is in the same household as\n            the requesting Sim.\n            ', tunable_type=bool, default=True), 'consider_travel_group': Tunable(description='\n            If enabled, this will succeed if the Sim is in the same travel group as\n            the requesting Sim.\n            ', tunable_type=bool, default=True), 'consider_hosted_travel_group': Tunable(description='\n            If enabled, this will succeed if the Sim is in a travel group staying at \n            the requesting sims home zone.\n            ', tunable_type=bool, default=False), 'exclude_sims_in_both': Tunable(description="\n            If enabled, this will fail if the Sim is in both the same household\n            and travel group. If false, it doesn't care.\n            ", tunable_type=bool, default=False), 'include_roommates_as_household': Tunable(description='\n            If enabled, roommates will be considered part of the same household.\n            ', tunable_type=bool, default=True)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult(score=0, sim_info=sim_info)
        in_household = self.consider_household and sim_info.household_id == requesting_sim_info.household_id
        if self.include_roommates_as_household:
            roommate_service = services.get_roommate_service()
            if roommate_service is not None:
                home_zone_id_a = sim_info.household.home_zone_id if sim_info.household.home_zone_id else sim_info.roommate_zone_id
                home_zone_id_b = requesting_sim_info.household.home_zone_id if requesting_sim_info.household.home_zone_id else requesting_sim_info.roommate_zone_id
                if home_zone_id_a:
                    in_household = home_zone_id_a == home_zone_id_b
        in_travel_group = (in_household or self.consider_travel_group) and (sim_info.travel_group_id == requesting_sim_info.travel_group_id and sim_info.travel_group_id != 0)
        if self.consider_hosted_travel_group:
            travel_group = services.travel_group_manager().get_travel_group_by_zone_id(requesting_sim_info.household.home_zone_id)
            in_travel_group = travel_group is not None and sim_info in travel_group
        if not (in_travel_group or in_household):
            pass
        score = not (self.exclude_sims_in_both and (in_travel_group and in_household))
        return FilterResult(score=self.invert_score_if_necessary(int(score)), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a sim in the household or travel group.', score=0)
        return FilterResult.TRUE

class LivesInRegion(DemographicsFilterTermMixin, InvertibleFilterTerm):
    FACTORY_TUNABLES = {'region': OptionalTunable(description='\n            Which region to test against.\n            ', tunable=TunableList(description='\n                The list of valid regions.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.REGION), class_restrictions=('Region',), pack_safe=True), unique_entries=True, minlength=1), disabled_name='current_region', enabled_name='specific_regions'), 'street_for_creation': OptionalTunable(description='\n            By default, Sims can only be created with this filter term if this\n            term is inverted (that is, the resulting Sim is a townie that lives\n            nowhere). Otherwise, the conform fails.\n            \n            If this is enabled and the term is not inverted, the Sim will\n            instead be assigned as townie living on the street.\n            ', tunable=TunableWorldDescription(pack_safe=True))}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        home_region = sim_info.household.get_home_region()
        if not sim_info.household.home_zone_id:
            roommate_service = services.get_roommate_service()
            if roommate_service is not None:
                zone_id = sim_info.roommate_zone_id
                if zone_id != 0:
                    home_region = region.get_region_instance_from_zone_id(zone_id)
        if home_region is None:
            score = 0
        elif self.region is None:
            current_region = region.get_region_instance_from_zone_id(services.current_zone_id())
            score = 1 if home_region is current_region else 0
        else:
            score = 1 if home_region in self.region else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def get_valid_world_ids(self):
        if self.street_for_creation is not None:
            world_id = services.get_world_id(self.street_for_creation)
            if self.invert_score:
                return (None, (world_id,))
            else:
                return ((world_id,), None)
        return (None, None)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            if self.street_for_creation is not None:
                return FilterResult.TRUE
            return FilterResult('Unable to create a sim who lives in a specific region.', score=0)
        return FilterResult.TRUE

class InFamilyFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, household_id=0, **kwargs):
        score = 1 if sim_info.household_id == household_id else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a sim in a household.', score=0)
        return FilterResult.TRUE

class IsRoommateFilterTerm(InvertibleFilterTerm):
    ANY = 0
    SPECIFIED_HOUSEHOLD = 1
    REQUESTING_SIM_HOUSEHOLD = 2
    ACTIVE_HOUSEHOLD = 3
    FACTORY_TUNABLES = {'target_household': TunableVariant(description='\n            Which household must the sim be a roommate of.\n            ', locked_args={'any': ANY, 'specified_household': SPECIFIED_HOUSEHOLD, 'requesting_sim_household': REQUESTING_SIM_HOUSEHOLD, 'active_household': ACTIVE_HOUSEHOLD}, default='any')}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, household_id=0, requesting_sim_info=None, **kwargs):
        roommate_service = services.get_roommate_service()
        score = 0
        if roommate_service:
            if self.household == self.ANY:
                household_id = None
            elif self.household == self.REQUESTING_SIM_HOUSEHOLD:
                if requesting_sim_info is None:
                    household_id = -1
                else:
                    household_id = requesting_sim_info.household_id
            elif self.household == self.ACTIVE_HOUSEHOLD:
                household_id = services.active_household_id()
                if household_id is None:
                    household_id = -1
            if roommate_service.is_sim_info_roommate(sim_info, household_id):
                score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to conform sim to be a roommate', score=0)
        return FilterResult.TRUE

class CullingScore(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self) -> 'bool':
        return False

    @cached
    def _get_household_culling_score(self, household:'Household') -> 'float':
        culling_service = services.get_culling_service()
        max_culling_score = max(culling_service.get_culling_score_for_sim_info(household_sim_info).score for household_sim_info in household)
        max_culling_score = max(1, max_culling_score)
        return max_culling_score

    def calculate_score(self, sim_info:'SimInfo', **kwargs) -> 'float':
        culling_score = self._get_household_culling_score(sim_info.household)
        return FilterResult(score=self.invert_score_if_necessary(1/culling_score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, **kwargs) -> 'FilterResult':
        return FilterResult('Unable to create a sim with specific culling score', score=0.1)

class IsGhostFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'require_npc': Tunable(description=' \n            If enabled, the Sim needs to be an NPC. If not enabled, any Sim that\n            is a ghost will pass the filter.\n            ', tunable_type=bool, default=True), 'always_pass_active_household_sims': Tunable(description='\n            If enabled then we will always pass sims in the active household,\n            whether they are a ghost or not.\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        if self.always_pass_active_household_sims and sim_info.is_selectable:
            return FilterResult.TRUE
        if sim_info.is_ghost:
            score = 0 if self.require_npc and not sim_info.is_npc else 1
        else:
            score = 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def is_compatible(self, other:'BaseFilterTerm') -> 'bool':
        if not self._is_comparable(other):
            return True
        elif self.invert_score != other.invert_score:
            if self.always_pass_active_household_sims and other.always_pass_active_household_sims:
                return True
            else:
                return False
        return False
        return True

class CanBeOutside(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'at_anytime': Tunable(description='\n            If enabled, the Sim needs to be able to go outside during day and night.\n            Otherwise, it needs to be able to go outside at current time or \n            during certain period of time.\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, start_time_ticks=None, end_time_ticks=None, **kwargs):
        score = 0
        vampire_trait = sim_info.occult_tracker.VAMPIRE_DAYWALKER_PERK.trait
        if not sim_info.trait_tracker.has_trait(vampire_trait):
            score = 1
        elif sim_info.age == Age.INFANT or sim_info.age == Age.TODDLER or sim_info.age == Age.CHILD:
            score = 1
        else:
            daywalker_perk = sim_info.occult_tracker.VAMPIRE_DAYWALKER_PERK.perk
            daywalker_perk_type = daywalker_perk.associated_bucks_type
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(daywalker_perk_type, sim_info.id)
            if bucks_tracker is None or not bucks_tracker.is_perk_unlocked(daywalker_perk):
                if not self.at_anytime:
                    if start_time_ticks is None or end_time_ticks is None:
                        if not services.time_service().is_day_time():
                            score = 1
                            start_time = DateAndTime(start_time_ticks)
                            end_time = DateAndTime(end_time_ticks)
                            if not services.time_service().is_day_time(end_time):
                                score = 1
                    else:
                        start_time = DateAndTime(start_time_ticks)
                        end_time = DateAndTime(end_time_ticks)
                        if not services.time_service().is_day_time(end_time):
                            score = 1
            else:
                score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        vampire_trait = created_sim_info.occult_tracker.VAMPIRE_DAYWALKER_PERK.trait
        if self.invert_score:
            return FilterResult.TRUE
        if not created_sim_info.trait_tracker.has_trait(vampire_trait):
            return FilterResult.TRUE
        daywalker_perk = created_sim_info.occult_tracker.VAMPIRE_DAYWALKER_PERK.perk
        daywalker_perk_type = daywalker_perk.associated_bucks_type
        bucks_tracker = BucksUtils.get_tracker_for_bucks_type(daywalker_perk_type, created_sim_info.id, add_if_none=True)
        bucks_tracker.unlock_perk(daywalker_perk)
        return FilterResult.TRUE

class OccultRankFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'occult_type': TunableEnumEntry(description='\n            The occult type that this entry applies to.\n            ', tunable_type=OccultType, default=OccultType.HUMAN), 'rank_values': TunableInterval(description='\n            An interval of the Sim rank. Rank must be between the interval \n            in order to pass the filter term. We set lower and upper rank interval \n            so then Sim that is too weak or too strong will not pass the filter.\n            ', tunable_type=int, default_lower=1, default_upper=1, minimum=1)}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        occult_data = sim_info.occult_tracker.OCCULT_DATA.get(self.occult_type, None)
        if occult_data is None:
            return FilterResult(score=0, sim_info=sim_info)
        xpranked_stat = occult_data.experience_statistic
        if xpranked_stat is None:
            return FilterResult(score=0, sim_info=sim_info)
        if not sim_info.commodity_tracker.has_statistic(xpranked_stat):
            return FilterResult(score=0, sim_info=sim_info)
        rank = sim_info.commodity_tracker.get_statistic(xpranked_stat).rank_level
        if rank < self.rank_values.lower_bound or rank > self.rank_values.upper_bound:
            return FilterResult(score=0, sim_info=sim_info)
        return FilterResult(score=1, sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        occult_data = created_sim_info.occult_tracker.OCCULT_DATA.get(self.occult_type, None)
        if occult_data is None:
            return FilterResult('Failed conform sim occult rank. {} does not have Occult Data', self.occult_type, sim_info=created_sim_info, score=0)
        xpranked_stat = occult_data.experience_statistic
        if xpranked_stat is None:
            return FilterResult('Failed conform sim occult rank. {} does not have Experience Statistic', occult_data, sim_info=created_sim_info, score=0)
        created_sim_info.desired_occult_rank[self.occult_type] = self.rank_values.random_int()
        return FilterResult.TRUE

class PerksFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'perks': TunableSet(description='\n            List of perks that a Sim should has.\n            ', tunable=TunableReference(description='\n                The perks that Sim should has.\n                ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True))}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        if not self.perks:
            return FilterResult(score=1, sim_info=sim_info)
        score = 1
        for perk in self.perks:
            bucks_type = perk.associated_bucks_type
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(bucks_type, sim_info.id)
            if not bucks_tracker is None:
                if not bucks_tracker.is_perk_unlocked(perk):
                    score = 0
                    break
            score = 0
            break
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        for perk in self.perks:
            bucks_type = perk.associated_bucks_type
            bucks_tracker = BucksUtils.get_tracker_for_bucks_type(bucks_type, created_sim_info.id, add_if_none=True)
            if not self.invert_score:
                if not bucks_tracker.is_perk_unlocked(perk):
                    bucks_tracker.unlock_perk(perk)
                    if bucks_tracker.is_perk_unlocked(perk):
                        bucks_tracker.lock_perk(perk)
            elif bucks_tracker.is_perk_unlocked(perk):
                bucks_tracker.lock_perk(perk)
        return FilterResult.TRUE

class InCompatibleRegionFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if self.invert_score:
            return FilterResult('Unable to create a sim in an incompatible region', score=0)
        return FilterResult.TRUE

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        score = 0
        if requesting_sim_info is not None:
            region_instance = region.get_region_instance_from_zone_id(requesting_sim_info.zone_id)
            if region_instance is not None:
                score = int(region_instance.is_sim_info_compatible(sim_info))
            else:
                score = 1
        else:
            current_region = services.current_region()
            score = int(current_region.is_sim_info_compatible(sim_info))
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class _RelationshipFilterTerm(InvertibleFilterTerm):

    class _BaseRelationshipSelector(HasTunableSingletonFactory):

        def get_relationships(self, sim_info:'SimInfo', requesting_sim_info:'SimInfo') -> 'List[Relationship]':
            raise NotImplementedError

        def get_pre_filtered_sim_ids(self, requesting_sim_info:'Optional[SimInfo]'=None) -> 'Optional[List[int]]':
            raise NotImplementedError

    class _RelationshipRequestingSim(_BaseRelationshipSelector):

        def get_relationships(self, sim_info, requesting_sim_info):
            if sim_info is None or requesting_sim_info is None:
                logger.error("Attempting to get relationships between a sim and None. This can be caused by tuning a rel bit filter term on a filter attached to something that doesn't specify a sim.\nOne fix for this is to add a filter_requesting_sim_id to the SituationGuestList that is being used here.", owner='bhill')
                return ()
            return ((requesting_sim_info, sim_info),)

        def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
            if requesting_sim_info is None:
                return
            return tuple(requesting_sim_info.relationship_tracker.target_sim_gen())

    class _RelationshipAllKnown(_BaseRelationshipSelector):

        def get_relationships(self, sim_info, _):
            valid_relationships = []
            for relationship in sim_info.relationship_tracker:
                target_sim_info = relationship.get_other_sim_info(sim_info.sim_id)
                if target_sim_info is not None:
                    valid_relationships.append((target_sim_info, sim_info))
            return valid_relationships

        def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
            pass

    class _RelationshipAllKnownPlayed(_BaseRelationshipSelector):

        def get_relationships(self, sim_info, _):
            valid_relationships = []
            for relationship in sim_info.relationship_tracker:
                target_sim_info = relationship.get_other_sim_info(sim_info.sim_id)
                if target_sim_info is not None and target_sim_info.is_played_sim:
                    valid_relationships.append((target_sim_info, sim_info))
            return valid_relationships

        def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
            pass

    class _RelationshipRequestingSimHouseholdMembers(_BaseRelationshipSelector):

        def get_relationships(self, sim_info, requesting_sim_info):
            valid_relationships = []
            for household_sim_info in requesting_sim_info.household:
                valid_relationships.append((sim_info, household_sim_info))
            return valid_relationships

        def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
            pass

    class _RelationshipHouseholdRequestingSim(_BaseRelationshipSelector):

        def get_relationships(self, sim_info, requesting_sim_info):
            valid_relationships = []
            for household_sim_info in sim_info.household:
                valid_relationships.append((requesting_sim_info, household_sim_info))
            return valid_relationships

        def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
            pass

    class _BaseScoreCombineStrategy(HasTunableSingletonFactory, AutoFactoryInit):

        def combine_scores(self, relationships:'List[Relationship]', filter_call:'Callable[[SimInfo, SimInfo], float]') -> 'float':
            raise NotImplementedError

    class _MatchAnyStrategy(_BaseScoreCombineStrategy):

        def combine_scores(self, relationships, filter_call):
            for relationship in relationships:
                score = filter_call(*relationship)
                if score > 0:
                    return 1
            return 0

    class _MatchAllStrategy(_BaseScoreCombineStrategy):

        def combine_scores(self, relationships, filter_call):
            for relationship in relationships:
                score = filter_call(*relationship)
                if score <= 0:
                    return 0
            return 1

    class _MultiplyScoresStrategy(_BaseScoreCombineStrategy):

        def combine_scores(self, relationships, filter_call):
            current_score = 1
            for relationship in relationships:
                score = filter_call(*relationship)
                current_score *= score
                if current_score == 0:
                    return 0
            return current_score

    FACTORY_TUNABLES = {'requesting_sim_override': Tunable(description='\n            If checked then the filter term will always return 1 if the\n            requesting sim info is the sim info we are looking at.\n            ', tunable_type=bool, default=False), 'relationship_selector': TunableVariant(description='\n            Define which relationships are to be considered.\n            ', use_requesting_sim=_RelationshipRequestingSim.TunableFactory(), use_all_sims=_RelationshipAllKnown.TunableFactory(), use_played_sims=_RelationshipAllKnownPlayed.TunableFactory(), use_household_with_requesting_sim=_RelationshipHouseholdRequestingSim.TunableFactory(), use_requesting_sim_household_members=_RelationshipRequestingSimHouseholdMembers.TunableFactory(), default='use_requesting_sim'), 'combine_strategy': TunableVariant(description='\n            RelationshipFilterTerms can look at multiple relationships at once,\n            and evaluate each one against the filter term. This strategy defines\n            how we want to "combine" all of those individual relationship\n            evaluations back together into one overall evaluation for the sim.\n            \n            Each strategy also contains an explanation in its tooltip, if you want\n            more details on an individual strategy. Here are some general examples\n            for choosing a strategy.\n            \n            For our first example, lets say we are looking at Bob, who has a\n            spouse and two children. Let\'s also say we have a filter that is\n            looking for any sims who are not married. When looking at Bob, our\n            RelationshipFilterTerm will evaluate the following for each\n            relationship:\n            Spouse: fail\n            Child 1: pass\n            Child 2: pass\n            \n            Since our intention is to filter sims that are not married, we would\n            want our Combine Strategy in this case to fail if any one of the\n            relationships fails. We could use the Match All strategy, since we\n            want to match only if all relationships match. Using the Match All\n            strategy, Bob would fail the filter, since his Spouse relationship\n            fails the filter.\n            \n            Here\'s another example. Let\'s say we have Bob again, but this time\n            we\'re looking for Sims with children. When looking at Bob, our\n            RelationshipFilterTerm will evaluate the following for each\n            relationship:\n            Spouse: fail (not Bob\'s child)\n            Child 1: pass\n            Child 2: pass\n            \n            Since our intention is to filter sims that have children, we would\n            want our Combine Strategy in this case to pass if any one of the\n            relationships passes. We could use the Match Any strategy, since we\n            want to match with any relationship that matches. Using the Match Any\n            strategy, Bob would pass the filter, since he has at least one\n            relationship that passes the filter.\n            \n            One final example. Let\'s say that we have Bob again, his spouse is his\n            best friend, but his relationship with Child 1 is not very good. His\n            relationship with Child 2 is neutral. Let\'s also say that we have a\n            filter that is looking for sims who have friends, and want to bias for\n            sims who have more friends than enemies. We do this by having a \'score\'\n            for the evaluation, where 0 is failure, anything non-zero is a\n            \'likelihood\' of being selected, where a higher score is better. The max\n            score is 1. With all of that in mind, let\'s finally say that for our\n            RelationshipFilterTerm evaluates friendship, where enemies would be 0\n            and best friends are 1. When looking at Bob, our RelationshipFilterTerm\n            will evaluate the following for each relationship:\n            Spouse: 1 (best friends is 1)\n            Child 1: 0.1 (Bob and Child 1 aren\'t enemies, but it isn\'t looking good)\n            Child 2: 0.5 (since neutral is halfway between enemies and best friends)\n            \n            Since our intention is to try and find the sim with the most friends and\n            least enemies, we can achieve this by using the Multiply Scores strategy,\n            which is an easy way to combine weights together. Using Multiply Scores,\n            Bob\'s score would evaluate to 1 * 0.1 * 0.5 = 0.05; a pretty low score!\n            \n            Note: all of the strategies actually work with scores, but the Match\n            strategies just return 0 or 1.\n            ', match_any=_MatchAnyStrategy.TunableFactory(), match_all=_MatchAllStrategy.TunableFactory(), multiply=_MultiplyScoresStrategy.TunableFactory(), default='match_any')}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if self.requesting_sim_override and sim_info is requesting_sim_info:
            return FilterResult(score=self.invert_score_if_necessary(1), sim_info=sim_info)
        relationships = self.relationship_selector.get_relationships(sim_info, requesting_sim_info)
        if not relationships:
            return FilterResult(score=self.invert_score_if_necessary(0), sim_info=sim_info)
        score = self.combine_strategy.combine_scores(relationships, self._calculate_relationship_score)
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, requesting_sim_info=None, **kwargs):
        result = self.calculate_score(created_sim_info, requesting_sim_info=requesting_sim_info, **kwargs)
        if result:
            return result
        for relationship in self.relationship_selector.get_relationships(created_sim_info, requesting_sim_info):
            self._conform_relationship(*relationship)
        return self.calculate_score(created_sim_info, requesting_sim_info=requesting_sim_info, **kwargs)

    def _calculate_relationship_score(self, sim_info, requesting_sim_info):
        raise NotImplementedError

    def _conform_relationship(self, sim_info, created_sim_info):
        raise NotImplementedError

    def get_pre_filtered_sim_ids(self, requesting_sim_info=None):
        return self.relationship_selector.get_pre_filtered_sim_ids(requesting_sim_info=requesting_sim_info)

class RelationshipBitFilterTerm(_RelationshipFilterTerm):
    FACTORY_TUNABLES = {'white_list': TunableSet(description='\n            A set of relationship bits that requires the requesting sim to have\n            at least one matching relationship bit with the sims we are scoring.\n            TIP: If it is required that the test fails if ANY of the relationships \n            have a specific rel bit, use whitelist for that bit and choose to invert \n            the result.\n            ', tunable=TunableReference(description="\n                A relationship bit that we will use to check if the requesting\n                sim has it with the sim we are scoring.\n                WARNING: If all elements are in a pack, then no sim will pass\n                the filter if the pack(s) aren't installed.\n                ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)), 'black_list': TunableSet(description="\n            A set of relationship bits that requires the requesting sim to not\n            have any one matching relationship bits with the sims we are\n            scoring. The black list is tested on all relationships that pass\n            the white list. WARNING: When used with Use All Sims relationship selector, \n            the test will pass as long as at least one relationship doesn't get \n            the black list bit. If it is required that it fails if ANY of the \n            relationships have a specific rel bit, use whitelist for that bit instead \n            and choose to invert the result.\n            ", tunable=TunableReference(description='\n                A relationship bit that we will use to check if the requesting\n                sim has it with the sim we are scoring.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)), 'reverse_bit_lookup': Tunable(description='\n            Look up the relationship bits for target to source sim,\n            instead of the default behavior of source to target relationship bits\n            ', tunable_type=bool, default=False)}

    def _calculate_relationship_score(self, sim_info, requesting_sim_info):
        if self.reverse_bit_lookup:
            relationship_bits = set(requesting_sim_info.relationship_tracker.get_all_bits(target_sim_id=sim_info.sim_id))
        else:
            relationship_bits = set(sim_info.relationship_tracker.get_all_bits(target_sim_id=requesting_sim_info.sim_id))
        if self.white_list and not relationship_bits & self.white_list:
            return 0
        elif self.black_list and relationship_bits & self.black_list:
            return 0
        return 1

    def _conform_relationship(self, sim_info, created_sim_info):
        for rel_bit in self.white_list:
            sim_info.relationship_tracker.add_relationship_bit(created_sim_info.sim_id, rel_bit, force_add=True)
        for rel_bit in self.black_list:
            sim_info.relationship_tracker.remove_relationship_bit(created_sim_info.sim_id, rel_bit)

class RelationshipBitCollectionFilterTerm(_RelationshipFilterTerm):
    FACTORY_TUNABLES = {'white_list': TunableSet(description='\n            A set of relationship bits or bit collections that requires the \n            requesting sim to have at least one matching relationship bit with \n            the sims we are scoring.\n            ', tunable=TunableReference(description="\n                A relationship bit or bit collection that we will use to check \n                if the requesting sim has it with the sim we are scoring.\n                WARNING: If all elements are in a pack, then no sim will pass\n                the filter if the pack(s) aren't installed.\n                ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)), 'black_list': TunableSet(description='\n            A set of relationship bits or bit collections that requires the \n            requesting sim to not have any one matching relationship bits with\n            the sims we are scoring.\n            ', tunable=TunableReference(description='\n                A relationship bit or bit collection that we will use to check \n                if the requesting sim has it with the sim we are scoring.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)), 'reverse_bit_lookup': Tunable(description='\n            Look up the relationship bits for target to source sim,\n            instead of the default behavior of source to target relationship bits\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def _calculate_relationship_score(self, sim_info, requesting_sim_info):
        if self.reverse_bit_lookup:
            relationship_bits = set(requesting_sim_info.relationship_tracker.get_all_bits(target_sim_id=sim_info.sim_id))
        else:
            relationship_bits = set(sim_info.relationship_tracker.get_all_bits(target_sim_id=requesting_sim_info.sim_id))
        if self.white_list:
            for bit in self.white_list:
                if any(bit.matches_bit(bit_type) for bit_type in relationship_bits):
                    break
            return 0
        if self.black_list:
            for bit in self.black_list:
                if any(bit.matches_bit(bit_type) for bit_type in relationship_bits):
                    return 0
        return 1

class RelationshipTrackFilterTerm(_RelationshipFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('RelationshipTrackFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].', source, tunable_name, value.ideal_value, value.min_value, value.max_value)

    FACTORY_TUNABLES = {'min_value': Tunable(description='\n            The minimum value of the relationship track that we are filtering\n            against.\n            ', tunable_type=int, default=-100), 'max_value': Tunable(description='\n            The maximum value of the relationship track that we are filtering\n            against.\n            ', tunable_type=int, default=100), 'ideal_value': Tunable(description='\n            Ideal value of the relationship track that we are filtering against.\n            ', tunable_type=int, default=0), 'relationship_track': TunableReference(description='\n            The relationship track that we are filtering against.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RelationshipTrack',)), 'verify_tunable_callback': _verify_tunable_callback}

    def _calculate_relationship_score(self, sim_info, requesting_sim_info):
        relationship_value = requesting_sim_info.relationship_tracker.get_relationship_score(sim_info.sim_id, self.relationship_track)
        return calculate_score_from_value(relationship_value, self.min_value, self.max_value, self.ideal_value)

    def _conform_relationship(self, sim_info, created_sim_info):
        if self.min_value == self.max_value:
            relationship_value = self.ideal_value
        else:
            relationship_value = round(random.triangular(self.min_value, self.max_value, self.ideal_value))
        sim_info.relationship_tracker.set_relationship_score(created_sim_info.sim_id, relationship_value, self.relationship_track)

class GenealogyFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'family_relationship': TunableEnumEntry(description='\n            This is the family relationship between the requesting sim and the\n            target sim.\n            ', tunable_type=FamilyRelationshipIndex, default=FamilyRelationshipIndex.MOTHER), 'swap_direction': Tunable(description='\n            This is the direction between the requesting sim and the target sim\n            so that the genealogy is checked between the sim info and the\n            requesting sim info.\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult(score=0, sim_info=sim_info)
        if self.swap_direction:
            score = 1 if sim_info.get_relation(self.family_relationship) == requesting_sim_info.id else 0
        else:
            score = 1 if requesting_sim_info.get_relation(self.family_relationship) == sim_info.id else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult('Unable to create sims with specific relationship-- requesting sim info is required', score=0)
        return FilterResult.TRUE

    def conform_sim_info_to_filter_term(self, created_sim_info, requesting_sim_info=None, **kwargs):
        if self.invert_score:
            return FilterResult.TRUE
        if self.swap_direction:
            created_sim_info.set_and_propagate_family_relation(self.family_relationship, requesting_sim_info)
            created_sim_info.set_default_relationships(reciprocal=True)
        else:
            requesting_sim_info.set_and_propagate_family_relation(self.family_relationship, created_sim_info)
            requesting_sim_info.set_default_relationships(reciprocal=True)
        return FilterResult.TRUE

class PregnancyFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'pregnancy_progress': OptionalTunable(description='\n            If enabled then we will check a specific \n            ', tunable=TunableTuple(description='\n                ', minimum_value=Tunable(description='\n                    The minimum commodity value that will pass.\n                    ', tunable_type=float, default=0.0), maximum_value=Tunable(description='\n                    The maximum commodity value that will pass.\n                    ', tunable_type=float, default=100.0), ideal_value=Tunable(description='\n                    The ideal commodity value for scoring.\n                    ', tunable_type=float, default=50.0))), 'pregnancy_partner_filter': OptionalTunable(description='\n            Specify how Sims are conformed to match this filter term.\n            ', tunable=TunableReference(description='\n                The filter that will be used to find a pregnancy partner for for\n                this Sim.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)), enabled_name='Use_Spouse_or_Filter', disabled_name='Use_Spouse_Exclusively')}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        if not sim_info.is_pregnant:
            return FilterResult('Sim Info has no pregnancy commodity.', score=0.0, sim_info=sim_info)
        if self.pregnancy_progress is None:
            return FilterResult(sim_info=sim_info)
        from sims.pregnancy.pregnancy_tracker import PregnancyTracker
        pregnancy_stat = sim_info.get_statistic(PregnancyTracker.PREGNANCY_COMMODITY_MAP.get(sim_info.species))
        pregnancy_value = pregnancy_stat.get_user_value()
        score = calculate_score_from_value(pregnancy_value, self.pregnancy_progress.minimum_value, self.pregnancy_progress.maximum_value, self.pregnancy_progress.ideal_value)
        return FilterResult(score=score, sim_info=sim_info)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        pregnancy_partner_sim_info = created_sim_info.get_significant_other_sim_info()
        if pregnancy_partner_sim_info is None or pregnancy_partner_sim_info.gender == created_sim_info.gender:
            if self.pregnancy_partner_filter is None:
                return FilterResult('Sim has no spouse or same-sex spouse, and no fallback filter', score=0)
            filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=self.pregnancy_partner_filter, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
            if not filter_results:
                return FilterResult('Cannot find sim to be pregnancy partner to make sim pregnant.', score=0)
            pregnancy_partner_sim_info = filter_results[0].sim_info
        created_sim_info.pregnancy_tracker.start_pregnancy(created_sim_info, pregnancy_partner_sim_info)
        if self.pregnancy_progress is not None:
            if self.pregnancy_progress.minimum_value == self.pregnancy_progress.maximum_value:
                pregnancy_value = self.pregnancy_progress.minimum_value
            else:
                pregnancy_value = random.triangular(self.pregnancy_progress.minimum_value, self.pregnancy_progress.maximum_value, self.pregnancy_progress.ideal_value)
            from sims.pregnancy.pregnancy_tracker import PregnancyTracker
            created_sim_info.set_stat_value(PregnancyTracker.PREGNANCY_COMMODITY_MAP.get(created_sim_info.species), pregnancy_value)
        return FilterResult.TRUE

class SimLODFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'sim_lod_value': TunableEnumEntry(description='\n            The Sim LOD value to check against.\n            ', tunable_type=SimInfoLODLevel, default=SimInfoLODLevel.BACKGROUND)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 1 if sim_info.lod >= self.sim_lod_value else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class AgeUpFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 1 if sim_info.can_age_up() else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a sim that is ready to age up.', score=0)
        return FilterResult.TRUE

class IsHomeZoneApartmentFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 1 if services.get_plex_service().is_zone_an_apartment(sim_info.household.home_zone_id) else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class IsHomeZoneUniversityHousingFilterTerm(InvertibleFilterTerm):
    UNIVERSITY_HOUSING_VENUE_TUNING = TunablePackSafeReference(description='\n        The university housing venue.  This should be kept in sync with the same tunable in university_housing_tuning.py\n        and we would ideally just reference the get_university_housing_zone_ids in there, but doing so causes a circular\n        import.\n        ', manager=services.get_instance_manager(sims4.resources.Types.VENUE))

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 0
        if IsHomeZoneUniversityHousingFilterTerm.UNIVERSITY_HOUSING_VENUE_TUNING is not None:
            home_zone_id = sim_info.household.home_zone_id
            if home_zone_id != 0:
                venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
                venue_type = venue_manager.get(build_buy.get_current_venue(home_zone_id))
                if venue_type is IsHomeZoneUniversityHousingFilterTerm.UNIVERSITY_HOUSING_VENUE_TUNING:
                    score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class HasHomeZoneFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'include_vacation_home': Tunable(description='\n            If enabled and the Sim is on a vacation at a zone, this will return\n            True.\n            ', tunable_type=bool, default=False), 'specific_venue_types': TunableEnumSet(description='\n            If tuned, home zone venue must match one of these venue types. This\n            option has no effect if include_vacation_home is True and the sim\n            is traveling.\n            ', enum_type=VenueTypes)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 0
        if self.include_vacation_home and sim_info.is_in_travel_group():
            score = 1
        else:
            home_zone_id = sim_info.household.home_zone_id
            if home_zone_id:
                home_venue = services.venue_service().get_venue_tuning(home_zone_id)
                if home_venue:
                    if not self.specific_venue_types:
                        score = 1
                    elif home_venue.venue_type in self.specific_venue_types:
                        score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a sim that has a home lot.', score=0)
        return FilterResult.TRUE

class HasHouseholdEverBeenPlayedFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        if sim_info.household is None:
            logger.error("{} has no household, so the test for whether or not their household has been played won't work. this shouldn't happen. Check GSI for information about how this state might have beeen achieved.", sim_info)
            score = 0
        else:
            score = 1 if sim_info.is_played_sim else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a sim that has a household that has been played by the player.', score=0)
        return FilterResult.TRUE

class HouseholdHomeZoneReservationFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        household = sim_info.household
        if household is None:
            score = 0
        elif services.get_zone_reservation_service().is_reserved(household.home_zone_id):
            score = 1
        else:
            score = 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class AgeProgressFilterTerm(BaseFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.ideal_value < value.min_value or value.ideal_value > value.max_value:
            logger.error('TunableAgeProgressFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the minimum and maximum bounds [{}, {}].'.format(source, tunable_name, value.ideal_value, value.min_value, value.max_value))

    FACTORY_TUNABLES = {'min_value': Tunable(description='\n            Minimum value of age progress.\n            ', tunable_type=float, default=0), 'max_value': Tunable(description='\n            Maximum value of age progress.\n            ', tunable_type=float, default=10), 'ideal_value': Tunable(description='\n            Ideal value of age progress.\n            ', tunable_type=float, default=5), 'verify_tunable_callback': _verify_tunable_callback}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        value = sim_info.age_progress
        score = calculate_score_from_value(value, self.min_value, self.max_value, self.ideal_value)
        return FilterResult(score=score, sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        current_value = created_sim_info.age_progress
        if self.min_value <= current_value and current_value <= self.max_value:
            return FilterResult.TRUE
        if self.min_value == self.max_value:
            new_age_progress_value = self.ideal_value
        else:
            new_age_progress_value = round(random.triangular(self.min_value, self.max_value, self.ideal_value))
        created_sim_info.age_progress = new_age_progress_value
        return FilterResult.TRUE

class AgeProgressPercentageFilterTerm(BaseFilterTerm):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.ideal_value < value.value_range.lower_bound or value.ideal_value > value.value_range.upper_bound:
            logger.error('AgeProgressPercentageFilterTerm {} has a filter term {} that is tuned with ideal_value {} outside of the lower_bound and upper_bound range [{}, {}].'.format(source, tunable_name, value.ideal_value, value.value_range.lower_bound, value.value_range.upper_bound))

    FACTORY_TUNABLES = {'value_range': TunableInterval(description='\n            The minimum and maximum age progress percentage.\n            ', tunable_type=int, default_lower=0, default_upper=100, minimum=0, maximum=100), 'ideal_value': Tunable(description='\n            Ideal value of age progress as a percentage.\n            ', tunable_type=int, default=50), 'verify_tunable_callback': _verify_tunable_callback}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        value = min(sim_info.age_progress_integer_percentage, 100)
        score = calculate_score_from_value(value, self.value_range.lower_bound, self.value_range.upper_bound, self.ideal_value)
        return FilterResult(score=score, sim_info=sim_info)

class IsNotIncestuousFilterTerm(BaseFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult('Trying to check against incest but there is no requesting sim info.', score=0, sim_info=sim_info)
        if requesting_sim_info.incest_prevention_test(sim_info):
            return FilterResult(score=1, sim_info=sim_info)
        else:
            return FilterResult('Incest prevention filter failed.', score=0, sim_info=sim_info)

class GenderPreferenceFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'consider_exploration': Tunable(description='\n            If checked, then we will allow sims who do not have matching attractions but are exploring.\n            If not, then we will strictly consider only their current romantic preference unless\n            the sim has no preference and a fallback is tuned.\n            Only applicable to human sims.\n            ', tunable_type=bool, default=False), 'fallback_if_no_preference_is_set': Tunable(description='\n            If checked then if no gender preference is set for the sim we will\n            fallback to a heterosexual connection. If this is set on human sims,\n            it will only work if the sim is exploring, but will do so even if\n            consider_exploration is unchecked.\n            ', tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info:'SimInfo', requesting_sim_info:'Optional[SimInfo]'=None, **kwargs) -> 'FilterResult':

        def _calculate_score_from_fallback():
            if requesting_sim_info.gender != sim_info.gender:
                return FilterResult(score=1, sim_info=sim_info)
            else:
                return FilterResult('Romantic preference filter failed with heterosexual fallback', score=0, sim_info=sim_info)

        if requesting_sim_info is None:
            return FilterResult('Trying to check romantic preference but there is no requesting sim info.', score=0, sim_info=sim_info)
        match_requesting_sim_preference = False
        match_filter_sim_preference = False
        has_any_attraction = False
        if sim_info.has_any_trait(GlobalGenderPreferenceTuning.ALWAYS_ATTRACTIVE_TRAITS):
            return FilterResult(score=1, sim_info=sim_info)
        for (gender, traits) in GlobalGenderPreferenceTuning.ROMANTIC_PREFERENCE_TRAITS_MAPPING.items():
            has_attraction = requesting_sim_info.has_trait(traits.is_attracted_trait)
            if has_attraction:
                has_any_attraction = True
                if gender == sim_info.gender:
                    return FilterResult(score=1, sim_info=sim_info)
        allow_fallback = True
        if requesting_sim_info.is_human:
            allow_fallback = requesting_sim_info.is_exploring_sexuality
            if self.consider_exploration and allow_fallback:
                return FilterResult(score=1, sim_info=sim_info)
        if has_any_attraction or self.fallback_if_no_preference_is_set and allow_fallback:
            return _calculate_score_from_fallback()
        return FilterResult('Romantic preference filter failed for sim due to gender preference.', score=0, sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, *, sim_creator, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult("Requesting sim info required to set sim info's gender.", score=0)
        sim_gender_preferences = list(requesting_sim_info.get_gender_preferences_gen())
        gender_pref_values = [0 if x[1] is None else x[1].get_value() for x in sim_gender_preferences]
        if not any(gender_pref_values):
            if requesting_sim_info.is_human:
                if not requesting_sim_info.is_exploring_sexuality:
                    return FilterResult('Requesting sim info is not interested in romance.', score=0)
                if self.fallback_if_no_preference_is_set:
                    target_gender = Gender.get_opposite(requesting_sim_info.gender)
                elif self.consider_exploration:
                    target_gender = random.choice(sim_gender_preferences)[0]
                else:
                    return FilterResult('Unable to create a sim with matching gender preference (should considerexploration be checked?).', score=0)
        else:
            target_gender = max(sim_gender_preferences, key=lambda x: 0 if x[1] is None else x[1].get_value())[0]
        sim_creator.gender = target_gender
        sim_creator.traits.add(GlobalGenderPreferenceTuning.ROMANTIC_PREFERENCE_TRAITS_MAPPING[target_gender].is_attracted_trait)
        return FilterResult.TRUE

class MatchmakingGenderPreferenceFilterTerm(GenderPreferenceFilterTerm):
    FACTORY_TUNABLES = {'consider_woohoo_preferences': Tunable(description='\n            If checked then woohoo preferences will also be considered along gender preferences.\n            If not, then we will strictly consider only their current romantic preference.\n            ', tunable_type=bool, default=True), 'pass_all_if_no_preference_is_set': Tunable(description='\n            If checked then if no gender preference is set for the sim and they are also not exploring,\n            we will let any sim pass the filter.\n            ', tunable_type=bool, default=True), 'locked_args': {'force_filter_term': True, 'consider_exploration': False, 'fallback_if_no_preference_is_set': False}}

    def conform_sim_creator_to_filter_term(self, *, sim_creator, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult("Requesting sim info required to set sim info's gender.", score=0)
        sim_gender_preferences = list(requesting_sim_info.get_gender_preferences_gen())
        gender_pref_values = [0 if x[1] is None else x[1].get_value() for x in sim_gender_preferences]
        if not any(gender_pref_values):
            target_gender = random.choice(sim_gender_preferences)[0]
        else:
            target_gender = max(sim_gender_preferences, key=lambda x: 0 if x[1] is None else x[1].get_value())[0]
        sim_creator.gender = target_gender
        sim_creator.traits.add(GlobalGenderPreferenceTuning.ROMANTIC_PREFERENCE_TRAITS_MAPPING[target_gender].is_attracted_trait)
        return FilterResult.TRUE

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult('Trying to check romantic preference but there is no requesting sim info.', score=0, sim_info=sim_info)
        match_requesting_sim_preference = False
        match_filter_sim_preference = False
        requesting_sim_has_any_attraction = False
        for (gender, traits) in GlobalGenderPreferenceTuning.ROMANTIC_PREFERENCE_TRAITS_MAPPING.items():
            requesting_sim_has_attraction = requesting_sim_info.has_trait(traits.is_attracted_trait)
            if requesting_sim_has_attraction:
                requesting_sim_has_any_attraction = True
                if gender == sim_info.gender:
                    match_requesting_sim_preference = True
            filter_sim_has_attraction = sim_info.has_trait(traits.is_attracted_trait)
            if filter_sim_has_attraction and gender == requesting_sim_info.gender:
                match_filter_sim_preference = True
        if self.consider_woohoo_preferences:
            for (gender, traits) in GlobalGenderPreferenceTuning.WOOHOO_PREFERENCE_TRAITS_MAPPING.items():
                requesting_sim_has_attraction = requesting_sim_info.has_trait(traits.is_attracted_trait)
                if requesting_sim_has_attraction:
                    requesting_sim_has_any_attraction = True
                    if gender == sim_info.gender:
                        match_requesting_sim_preference = True
                filter_sim_has_attraction = sim_info.has_trait(traits.is_attracted_trait)
                if filter_sim_has_attraction and gender == requesting_sim_info.gender:
                    match_filter_sim_preference = True
        if match_requesting_sim_preference and match_filter_sim_preference:
            return FilterResult(score=1, sim_info=sim_info)
        if self.pass_all_if_no_preference_is_set and not requesting_sim_has_any_attraction:
            return FilterResult(score=1, sim_info=sim_info)
        return FilterResult('Romantic preference filter failed for sim due to gender preference.', score=0, sim_info=sim_info)

class RequestingSimFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        score = 1 if sim_info is requesting_sim_info else 0
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_creator_to_filter_term(self, **kwargs):
        if not self.invert_score:
            return FilterResult('Unable to create a Sim that is the requesting Sim.', score=0)
        return FilterResult.TRUE

class SimInfoFixupFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'fixup': TunablePackSafeReference(description='\n            The sim info fixup to filter against.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_INFO_FIXUP))}

    @property
    def is_sim_info_conformable(self):
        return True

    def calculate_score(self, sim_info, **kwargs):
        score = 0
        if sim_info.fixup_tracker.has_fixup(self.fixup):
            score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if self.fixup is None and self.invert_score:
            return FilterResult.TRUE
        if self.invert_score != created_sim_info.fixup_tracker.has_fixup(self.fixup):
            return FilterResult.TRUE
        if self.invert_score:
            created_sim_info.fixup_tracker.remove_fixup(self.fixup)
        else:
            created_sim_info.fixup_tracker.add_fixup(self.fixup)
        return FilterResult.TRUE

class GigHistoryFilterTerm(BaseFilterTerm):
    FACTORY_TUNABLES = {'has_gig_history': Tunable(description="\n            If checked then sim must be in requesting sim's gig history.\n            ", tunable_type=bool, default=True), 'min_result': TunableEnumEntry(description="\n            The worst acceptable gig result we're filtering for.\n            ", tunable_type=GigResult, default=GigResult.CRITICAL_FAILURE), 'max_result': TunableEnumEntry(description="\n            The best acceptable gig result we're filtering for.\n            ", tunable_type=GigResult, default=GigResult.GREAT_SUCCESS), 'check_household': Tunable(description="\n            If checked then we check every one in the sim's household.\n            ", tunable_type=bool, default=False)}

    @property
    def is_sim_info_conformable(self):
        return False

    def _check_gig_history_for_sim_info(self, sim_info, requesting_sim_info):
        career_tracker = requesting_sim_info.career_tracker
        if career_tracker is None:
            return False
        gig_history = career_tracker.get_gig_history_by_customer(sim_info.id)
        if gig_history is None:
            return False
        return gig_history.gig_result <= self.min_result and gig_history.gig_result >= self.max_result

    def calculate_score(self, sim_info, requesting_sim_info=None, **kwargs):
        if requesting_sim_info is None:
            return FilterResult('Trying to check gig history but there is no requesting sim info.', score=0, sim_info=sim_info)
        if self.check_household:
            found_history = any(self._check_gig_history_for_sim_info(household_sim_info, requesting_sim_info) for household_sim_info in sim_info.household)
        else:
            found_history = self._check_gig_history_for_sim_info(sim_info, requesting_sim_info)
        score = 1 if found_history == self.has_gig_history else 0
        return FilterResult(score=score, sim_info=sim_info)

class DoesHouseholdHaveFreeSlotsFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 0
        if sim_info.household.free_slot_count > 0:
            score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class CanDieFilterTerm(InvertibleFilterTerm):

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 0 if sim_info.is_death_disabled() else 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class ClanFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'clan': TunablePackSafeReference(description='\n            The clan to filter against.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CLAN))}

    @property
    def is_sim_info_conformable(self):
        return True

    def can_repurpose_sim_info(self, sim_info):
        if self.clan is not None:
            clan_data = ClanService.CLAN_DATA.get(self.clan)
            if clan_data is not None:
                return not sim_info.has_trait(clan_data.rival_clan.clan_trait)
        return False

    def calculate_score(self, sim_info, **kwargs):
        score = 0
        if sim_info.trait_tracker.has_trait(self.clan.clan_trait):
            score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

    def conform_sim_info_to_filter_term(self, created_sim_info, **kwargs):
        if not self.invert_score:
            clan_service = services.clan_service()
            if clan_service is not None:
                clan_service.add_sim_to_clan(created_sim_info, self.clan)
        return self.calculate_score(created_sim_info)

class PromFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'bit_type': TunableEnumEntry(description='\n            The type of prom rel bit. \n            ', tunable_type=PromRelationshipBitType, default=PromRelationshipBitType.INVITED)}

    @property
    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        prom_service = services.get_prom_service()
        score = 0
        if prom_service is None:
            return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)
        if self.bit_type == PromRelationshipBitType.INVITED:
            score = int(sim_info.id in prom_service.get_prom_teen_attendee_ids())
        else:
            score = int(sim_info.id in prom_service.get_prom_pact_sim_ids())
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class HighSchoolGraduationFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'current_valedictorian': OptionalTunable(description="\n            If enabled, test for whether or not a sim is the current valedictorian or not. \n            If you don't care if the Sim is the current valedictorian or not just leave this option disabled.\n            ", tunable=Tunable(description='\n                Whether or not you are looking for the current valedictorian, or a non valedictorian.\n                ', tunable_type=bool, default=False))}

    def is_sim_info_conformable(self):
        return False

    def calculate_score(self, sim_info, **kwargs):
        graduation_service = services.get_graduation_service()
        if graduation_service is None:
            return FilterResult(score=self.invert_score_if_necessary(0), sim_info=sim_info)
        score = 0
        if self.current_valedictorian is None or self.current_valedictorian == graduation_service.is_current_valedictorian(sim_info):
            score = 1
        return FilterResult(score=self.invert_score_if_necessary(score), sim_info=sim_info)

class GallerySimFilterTerm(InvertibleFilterTerm):
    FACTORY_TUNABLES = {'locked_args': {'force_filter_term': False}}

    @property
    def is_sim_info_confromable(self):
        return False

    def calculate_score(self, sim_info, tag=FilterTermTag.NO_TAG, **kwargs):
        matchmaking_service = services.get_matchmaking_service()
        if matchmaking_service and sim_info.sim_id in matchmaking_service.remote_id_to_sim_id.values():
            return FilterResult(score=1, sim_info=sim_info, tag=tag)
        return FilterResult(score=0, sim_info=sim_info, tag=tag)

class FilterTermVariant(TunableVariant):

    def __init__(self, conform_optional=False, **kwargs):
        filter_kwargs = {}
        if conform_optional:
            filter_kwargs['conform_optional'] = True
        super().__init__(skill=SkillFilterTerm.TunableFactory(**filter_kwargs), skill_list=SkillListFilterTerm.TunableFactory(**filter_kwargs), statistic=StatisticFilterTerm.TunableFactory(**filter_kwargs), ranked_statistic=RankedStatisticFilterTerm.TunableFactory(**filter_kwargs), trait=TraitFilterTerm.TunableFactory(**filter_kwargs), trait_blacklist=TraitBlacklistFilterTerm.TunableFactory(**filter_kwargs), age=AgeFilterTerm.TunableFactory(**filter_kwargs), age_variant=AgeVariationFilterTerm.TunableFactory(**filter_kwargs), gender=GenderFilterTerm.TunableFactory(**filter_kwargs), gender_relative=GenderRelativeFilterTerm.TunableFactory(**filter_kwargs), species=SpeciesFilterTerm.TunableFactory(**filter_kwargs), cas_tags=CasTagsFilterTerm.TunableFactory(**filter_kwargs), is_busy=IsBusyFilterTerm.TunableFactory(**filter_kwargs), in_family=InFamilyFilterTerm.TunableFactory(**filter_kwargs), culling_score=CullingScore.TunableFactory(**filter_kwargs), is_ghost=IsGhostFilterTerm.TunableFactory(**filter_kwargs), is_roommate=IsRoommateFilterTerm.TunableFactory(**filter_kwargs), can_be_outside=CanBeOutside.TunableFactory(**filter_kwargs), occult_ranked=OccultRankFilterTerm.TunableFactory(**filter_kwargs), perks=PerksFilterTerm.TunableFactory(**filter_kwargs), is_not_incestuous=IsNotIncestuousFilterTerm.TunableFactory(**filter_kwargs), relationship_bit=RelationshipBitFilterTerm.TunableFactory(**filter_kwargs), prom=PromFilterTerm.TunableFactory(**filter_kwargs), relationship_bit_collection=RelationshipBitCollectionFilterTerm.TunableFactory(**filter_kwargs), relationship_track=RelationshipTrackFilterTerm.TunableFactory(**filter_kwargs), can_age_up=AgeUpFilterTerm.TunableFactory(**filter_kwargs), has_home_zone=HasHomeZoneFilterTerm.TunableFactory(**filter_kwargs), has_reserved_home_zone=HouseholdHomeZoneReservationFilterTerm.TunableFactory(**filter_kwargs), has_household_ever_been_played=HasHouseholdEverBeenPlayedFilterTerm.TunableFactory(**filter_kwargs), household_composition=HouseholdCompositionFilterTerm.TunableFactory(**filter_kwargs), age_progress=AgeProgressFilterTerm.TunableFactory(**filter_kwargs), age_progress_percentage=AgeProgressPercentageFilterTerm.TunableFactory(**filter_kwargs), is_neighbor=IsNeighborFilterTerm.TunableFactory(**filter_kwargs), in_compatible_region=InCompatibleRegionFilterTerm.TunableFactory(**filter_kwargs), lives_in_region=LivesInRegion.TunableFactory(**filter_kwargs), lives_together=LivesTogetherFilterTerm.TunableFactory(**filter_kwargs), genealogy=GenealogyFilterTerm.TunableFactory(**filter_kwargs), career=CareerFilterTerm.TunableFactory(**filter_kwargs), university=UniversityMajorFilterTerm.TunableFactory(**filter_kwargs), pregnancy=PregnancyFilterTerm.TunableFactory(**filter_kwargs), household_value=HouseholdValueFilterTerm.TunableFactory(**filter_kwargs), in_club=InClubFilterTerm.TunableFactory(**filter_kwargs), in_same_club=InSameClubFilterTerm.TunableFactory(**filter_kwargs), lives_on_apartment_floor=LivesOnApartmentFloor.TunableFactory(**filter_kwargs), lives_in_current_zone=LivesInCurrentZone.TunableFactory(**filter_kwargs), lives_on_street=LivesOnStreetFilterTerm.TunableFactory(**filter_kwargs), sim_info_lod=SimLODFilterTerm.TunableFactory(**filter_kwargs), is_sim_sick=SickSimFilterTerm.TunableFactory(**filter_kwargs), is_hidden=IsHiddenFilterTerm.TunableFactory(**filter_kwargs), is_hidden_relationship=IsHiddenRelationshipFilerTerm.TunableFactory(**filter_kwargs), gender_preference=GenderPreferenceFilterTerm.TunableFactory(**filter_kwargs), matchmaking_gender_preference=MatchmakingGenderPreferenceFilterTerm.TunableFactory(**filter_kwargs), requesting_sim=RequestingSimFilterTerm.TunableFactory(**filter_kwargs), sim_info_fixups=SimInfoFixupFilterTerm.TunableFactory(**filter_kwargs), gig_history=GigHistoryFilterTerm.TunableFactory(**filter_kwargs), is_home_zone_apartment=IsHomeZoneApartmentFilterTerm.TunableFactory(**filter_kwargs), is_home_zone_university_housing=IsHomeZoneUniversityHousingFilterTerm.TunableFactory(**filter_kwargs), does_household_have_free_slots=DoesHouseholdHaveFreeSlotsFilterTerm.TunableFactory(**filter_kwargs), can_die=CanDieFilterTerm.TunableFactory(**filter_kwargs), in_clan=ClanFilterTerm.TunableFactory(**filter_kwargs), is_graduating=HighSchoolGraduationFilterTerm.TunableFactory(**filter_kwargs), default='skill', **kwargs)

class TunableSimFilter(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)):
    USE_CONSTRAINED_SIMS = 2
    TOP_NUMBER_OF_SIMS_TO_LOOK_AT = Tunable(description='\n        When running a filter request and doing a weighted random, how many of\n        the top scorers will be used to get the results.\n        ', tunable_type=int, default=5)
    BLANK_FILTER = TunableReference(description='\n        A filter that is used when a filter of None is passed in.  This filter\n        should have no filter terms.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER))
    ANY_FILTER = TunableReference(description='\n        A filter used for creating debug sims in your neighborhood.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER))
    UNIMPORTANT_FILTER = TunableReference(description='\n        A filter used to find Sims that are considered unimportant. Unimportant\n        Sims can be used as a fallback before generating new SimInfos in the\n        case a filter request fails. This allows us to conserve SimInfos.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER))
    INSTANCE_TUNABLES = {'_filter_terms': TunableList(description='\n            A list of filter terms that will be used to query the townie pool\n            for sims.\n            ', tunable=FilterTermVariant()), '_template_chooser': TunableReference(description='\n            A reference to a template chooser.  In the case that the filter\n            fails to find any sims that match it, the template chooser will\n            select a template to use that will be used to create a sim.  After\n            that sim is created then the filter will fix up the sim further in\n            order to ensure that the template that the sim defines still meets\n            the criteria of the filter.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TEMPLATE_CHOOSER), allow_none=True), 'use_weighted_random': Tunable(description='\n            If checked will do a weighted random of top results rather than\n            just choosing the best ones.\n            \n            Note: Before doing weighted random, Sim filter caps top results by\n            TOP_NUMBER_OF_SIMS_TO_LOOK_AT. So do not completely rely on this \n            checkbox if you are looking for weighted randomization of all results.\n            ', tunable_type=bool, default=False), 'repurpose_terms': TunableVariant(description='\n            If specified, then Sims, should any be available, are conformed to\n            the filter terms. Unimportant Sims are defined by the\n            UNIMPORTANT_FILTER global tunable or a specified filter.\n            \n            The purpose of this is to conserve SimInfos when it is not necessary\n            to generate brand new Sims. For example, an unimportant Sim might\n            become the bartender at a venue.\n            ', use_specific_sims=TunableReference(description='\n                Use a specific filter to determine unimportant Sims.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)), locked_args={'use_constrained_sims': USE_CONSTRAINED_SIMS, 'use_unimportant_sims': DEFAULT, 'dont_repurpose': None}, default='dont_repurpose'), 'repurpose_game_breaker': Tunable(description='\n            If checked, then we can repurpose instanced sims for the results of\n            this filter.\n            \n            DO NOT TUNE THIS UNLESS YOU TALK TO A GPE.  IT WILL POTENTIALLY\n            CAUSE WEIRD SUBTLE BUGS.\n            ', tunable_type=bool, default=False), '_set_household_as_hidden': Tunable(description="\n            If checked, the household created for this template will be hidden.\n            Normally used with household_template_override. e.g. Death's\n            household.\n            ", tunable_type=bool, default=False), '_household_templates_override': OptionalTunable(description='\n            If enabled, when creating sim info use the household template\n            specified.\n            ', tunable=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE), class_restrictions=('HouseholdTemplate',)))), 'automatically_assign_as_street_townie': Tunable(description="\n            If set and this Sim is being created as a townie (i.e. as a Sim\n            whose household doesn't reside on a physical lot), allow the Sim to\n            still be automatically assigned to a street. It will be considered\n            as living on the street (e.g. they will pass the Lives On Street\n            filter term) and will pick up any characteristics appropriate for\n            that street (cas tags, skills, etc. Specific tuning can be found on\n            Street -> Townie Demographics).\n            \n            If disabled, this Sim will never be automatically set to be as\n            being part of a street. They will still be allowed to be assigned\n            to a street if this filter has a Lives On Street filter that allows\n            conforming.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.SPECIAL_CASES), 'specify_cas_randomization_mode': OptionalTunable(description='\n            If enabled, the CAS sim randomization mode to use for this filter.\n            \n            If disabled, the default client randomization mode logic will be used.\n            ', disabled_name='USE_CLIENT_DEFAULT', tunable=TunableEnumEntry(tunable_type=RandomizationMode, default=RandomizationMode.SELECTIVE_RANDOMIZATION)), 'additional_conform_terms': TunableList(description="\n            When a Sim is conformed to meet a filter (using repurpose terms),\n            the actions taken to conform a Sim may not also be the same as the\n            baseline requirements to meet the filter in the first place.  This\n            list is the list of filter actions that are ONLY used when a Sim\n            is being conformed to fit the filter.\n            \n            For example, when conforming Sims to the MagicUser (NPC) filter, \n            when they are first conformed (given the witch occult trait), we \n            want to put a one-time trait on them to fix them up if they are \n            ever made playable, but we don't want to re-apply this trait to a Sim\n            every time they should be a candidate for this filter.\n            ", tunable=FilterTermVariant())}

    @classmethod
    def _verify_tuning_callback(cls):
        repurpose_filter = cls.UNIMPORTANT_FILTER if cls.repurpose_terms is DEFAULT else cls.repurpose_terms
        if repurpose_filter != cls.USE_CONSTRAINED_SIMS:
            if cls is repurpose_filter:
                logger.error("{} specifies itself as a repurpose filter. That's not going to do anything useful.", cls)
            template_chooser = repurpose_filter._template_chooser
            if template_chooser is not None:
                logger.error("{} specifies {} as a repurpose filter, but that specifies {} as a template. Repurpose terms can't have templates.", cls, repurpose_filter, template_chooser)

    @flexmethod
    def get_filter_terms(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls._filter_terms

    @flexmethod
    def get_additional_conform_terms(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls.additional_conform_terms

    @classmethod
    def choose_template(cls):
        if cls._template_chooser is not None:
            return cls._template_chooser.choose_template()

    @classmethod
    def is_aggregate_filter(cls):
        return False

    @flexmethod
    def _repurpose_sim_info(cls, inst, sim_info, additional_filter_terms=(), **kwargs):
        inst_or_cls = inst if inst is not None else cls
        conformable_terms = []
        total_filter_terms = inst_or_cls.get_filter_terms() + additional_filter_terms + inst_or_cls.get_additional_conform_terms()
        for term in total_filter_terms:
            if term.can_repurpose_sim_info(sim_info):
                conformable_terms.append(term)
            else:
                result = term.calculate_score(sim_info, **kwargs)
                if not result:
                    return result
        for filter_term in conformable_terms:
            if filter_term.force_filter_term:
                result = filter_term.conform_sim_info_to_filter_term(created_sim_info=sim_info, **kwargs)
                if not result:
                    logger.error('Failed to repurpose {} to filter term {}. Sim Filter: {}, Reason: {}', sim_info, filter_term, cls.__name__, result)
                    return result
        return FilterResult.TRUE

    @flexmethod
    def get_sim_filter_gsi_name(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return str(inst_or_cls)

    @flexmethod
    def create_sim_info(cls, inst, zone_id, blacklist_sim_ids=(), additional_filter_terms=(), sim_constraints=(), **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.repurpose_terms is not None:
            if inst_or_cls.repurpose_terms is cls.USE_CONSTRAINED_SIMS:
                sim_info_manager = services.sim_info_manager()
                for sim_id in sim_constraints:
                    if sim_id in blacklist_sim_ids:
                        pass
                    else:
                        sim_info = sim_info_manager.get(sim_id)
                        if sim_info is None:
                            pass
                        else:
                            result = inst_or_cls._repurpose_sim_info(sim_info, additional_filter_terms=additional_filter_terms, **kwargs)
                            if result:
                                return FilterResult('Constrained SimInfo repurposed successfully', sim_info=sim_info)
            else:
                repurpose_terms = inst_or_cls.UNIMPORTANT_FILTER if inst_or_cls.repurpose_terms is DEFAULT else inst_or_cls.repurpose_terms
                for unimportant_result in services.sim_filter_service().submit_filter(repurpose_terms, None, blacklist_sim_ids=blacklist_sim_ids, allow_yielding=False, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name, **kwargs):
                    result = inst_or_cls._repurpose_sim_info(unimportant_result.sim_info, additional_filter_terms=additional_filter_terms, **kwargs)
                    if result:
                        return FilterResult('Unimportant SimInfo repurposed successfully', sim_info=unimportant_result.sim_info)
        template = cls.choose_template()
        if not template:
            return FilterResult('No template selected, template chooser might not be tuned properly.', score=0)
        sim_creator = template.sim_creator
        filter_terms = list(inst_or_cls.get_filter_terms())
        filter_terms.extend(additional_filter_terms)
        filter_terms.extend(inst_or_cls.get_additional_conform_terms())
        (world_id, sim_name_type) = services.get_demographics_service().choose_world_and_conform_filter(sim_creator, filter_terms, inst_or_cls.automatically_assign_as_street_townie)
        if sim_creator.sim_name_type != SimNameType.DEFAULT:
            sim_name_type = sim_creator.sim_name_type
        for filter_term in filter_terms:
            if filter_term.force_filter_term:
                result = filter_term.conform_sim_creator_to_filter_term(sim_creator=sim_creator, **kwargs)
                if not result:
                    return result
        if sim_creator.breed_name_key == 0:
            breed_tag = get_random_breed_tag(sim_creator.species)
            if breed_tag is not None:
                sim_creator.tag_set.add(breed_tag)
        if inst_or_cls.specify_cas_randomization_mode is not None:
            sim_creator.randomization_mode = inst_or_cls.specify_cas_randomization_mode
        household_template = cls.create_template_matching_sim_creator(sim_creator)
        if household_template is None:
            return FilterResult('No template selected, there is no household template with matching age, gender, and species', score=0)
        (household, created_sim_info) = household_template.create_household(zone_id, sim_creator=sim_creator, sim_name_type=sim_name_type, creation_source='filter: {}'.format(cls.__name__), sim_debug_name=template.__name__, template_override=template)
        if cls._set_household_as_hidden:
            household.set_to_hidden()
        if world_id is not None:
            created_sim_info.household.set_home_world_id(world_id)
        for filter_term in filter_terms:
            if filter_term.force_filter_term:
                result = filter_term.conform_sim_info_to_filter_term(created_sim_info=created_sim_info, **kwargs)
                if result or not filter_term.conform_optional:
                    logger.error('Failed to conform {} to filter term {}. Sim Filter: {}, Reason: {}', created_sim_info, filter_term, cls.__name__, result)
                    return result
        return FilterResult('SimInfo created successfully', sim_info=created_sim_info)

    @classmethod
    def create_template_matching_sim_creator(cls, sim_creator):
        valid_filter_templates = []
        if cls._household_templates_override:
            templates_to_iterate_over = cls._household_templates_override
        else:
            templates_to_iterate_over = services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE).types.values()
        for filter_template_type in templates_to_iterate_over:
            if filter_template_type.template_type != filters.sim_template.SimTemplateType.HOUSEHOLD:
                pass
            else:
                filter_template = filter_template_type()
                for sim_template in filter_template.get_household_member_templates():
                    if sim_template.matches_creation_data(sim_creator=sim_creator):
                        valid_filter_templates.append(filter_template)
                        break
        if valid_filter_templates:
            return random.choice(valid_filter_templates)

    @classmethod
    def get_pre_filtered_sim_ids(cls, requesting_sim_info=None):
        pre_filtered_sim_ids = None
        for filter_term in cls.get_filter_terms():
            term_pre_filtered_sim_ids = filter_term.get_pre_filtered_sim_ids(requesting_sim_info=requesting_sim_info)
            if term_pre_filtered_sim_ids is None:
                pass
            elif pre_filtered_sim_ids is None:
                pre_filtered_sim_ids = set(term_pre_filtered_sim_ids)
            else:
                pre_filtered_sim_ids &= set(term_pre_filtered_sim_ids)
        if pre_filtered_sim_ids is not None:
            return tuple(pre_filtered_sim_ids)

    @classmethod
    @sim_info_auto_finder
    def get_pre_filtered_sim_infos(cls, *args, **kwargs):
        return cls.get_pre_filtered_sim_ids(*args, **kwargs)

class TunableAggregateFilter(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)):
    INSTANCE_TUNABLES = {'leader_filter': TunableTuple(filter=TunableReference(description='\n                Sim filter that is used as the leader of the group. All\n                relationships will use this sim as the reference point.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',)), tag=TunableEnumEntry(description='\n                Tag associated with the filter which allows for specific filters\n                to be associated with specific things, like which job to apply\n                to the Sim with that filter.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG)), 'filters': TunableList(description='\n            List of filters for the sims to be included in the group.\n            ', tunable=TunableTuple(filter=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',)), tag=TunableEnumEntry(description='\n                    Tag associated with the filter which allows for specific filters\n                    to be associated with specific things, like which job to apply\n                    to the Sim with that filter.\n                    ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), optional=Tunable(description='\n                    Whether or not this filter is required for the filter to\n                    be considered successful.\n                    ', tunable_type=bool, default=True)))}

    @classmethod
    def is_aggregate_filter(cls):
        return True

    @classmethod
    def get_filter_count(cls):
        return len(cls.filters) + 1

class DynamicSimFilter(TunableSimFilter):
    INSTANCE_TUNABLES = {'_additional_filter_terms': TunableList(description='\n            A list of filter terms that are going to be used in conjunction with\n            the terms provided by the user of this filter.\n            ', tunable=FilterTermVariant())}
    REMOVE_INSTANCE_TUNABLES = ('_filter_terms',)

    def __init__(self, filter_terms=()):
        self._filter_terms = filter_terms + self._additional_filter_terms

class BlankFilter(TunableSimFilter):
    REMOVE_INSTANCE_TUNABLES = ('_filter_terms',)

    @classproperty
    def _filter_terms(cls):
        return ()
