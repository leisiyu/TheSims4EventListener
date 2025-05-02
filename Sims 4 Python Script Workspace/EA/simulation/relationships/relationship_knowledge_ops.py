from __future__ import annotationsimport enumimport randomfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import DoubleSimResolverfrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom interactions.utils.notification import NotificationElementfrom sims.global_gender_preference_tuning import GenderPreferenceTypefrom sims4.localization import LocalizationHelperTuningfrom sims.relationship_expectations_tuning import RelationshipExpectationTypefrom sims4.tuning.tunable import TunableVariant, TunableTuple, TunableList, TunableRange, OptionalTunable, TunableSet, TunableReference, TunableEnumEntry, Tunablefrom traits.preference_tuning import PreferenceTuningfrom traits.trait_type import TraitTypeimport interactions.utilsimport servicesimport sims4.resourcesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from interactions.utils import LootType
    from relationships.relationship_track import RelationshipTrack
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from traits.traits import Trait
    from typing import *logger = sims4.log.Logger('KnowOtherSimTraitOp', default_owner='asantos')
class RelationshipTargetedLootOperation(BaseTargetedLootOperation):

    @property
    def loot_type(self) -> 'LootType':
        return interactions.utils.LootType.RELATIONSHIP

class RelationshipBitTargetedLootOperation(BaseTargetedLootOperation):

    @property
    def loot_type(self) -> 'LootType':
        return interactions.utils.LootType.RELATIONSHIP_BIT

class KnowOtherSimTraitOp(RelationshipBitTargetedLootOperation):
    TRAIT_SPECIFIED = 0
    TRAIT_RANDOM = 1
    TRAIT_ALL = 2
    FACTORY_TUNABLES = {'traits': TunableVariant(description='\n            The traits that the subject may learn about the target.\n            ', specified=TunableTuple(description='\n                Specify individual traits that can be learned.\n                ', locked_args={'learned_type': TRAIT_SPECIFIED}, potential_traits=TunableList(description='\n                    A list of traits that the subject may learn about the target.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',)))), random=TunableTuple(description='\n                Specify a random number of traits to learn.\n                ', locked_args={'learned_type': TRAIT_RANDOM}, count=TunableRange(description='\n                    The number of potential traits the subject may learn about\n                    the target.\n                    ', tunable_type=int, default=1, minimum=1), trait_types=TunableList(description='\n                    The random traits are picked from the traits of these types.\n                    If this list is empty, pick only from Personality traits.\n                    ', tunable=TraitType, set_default_as_first_entry=True, unique_entries=True)), all=TunableTuple(description="\n                The subject Sim may learn all of the target's traits.\n                ", locked_args={'learned_type': TRAIT_ALL}, trait_types=TunableList(description='\n                    The subject will learn all the traits of these types.\n                    If this list is empty, sim learns all the Personality traits.\n                    ', tunable=TraitType, set_default_as_first_entry=True, unique_entries=True)), default='specified'), 'notification': OptionalTunable(description="\n            Specify a notification that will be displayed for every subject if\n            information is learned about each individual target_subject. This\n            should probably be used only if you can ensure that target_subject\n            does not return multiple participants. The first two additional\n            tokens are the Sim and target Sim, respectively. A third token\n            containing a string with a bulleted list of trait names will be a\n            String token in here. If you are learning multiple traits, you\n            should probably use it. If you're learning a single trait, you can\n            get away with writing specific text that does not use this token.\n            ", tunable=NotificationElement.TunableFactory(locked_args={'recipient_subject': None})), 'notification_no_more_traits': OptionalTunable(description='\n            Specify a notification that will be displayed when a Sim knows\n            all traits of another target Sim.\n            ', tunable=NotificationElement.TunableFactory(locked_args={'recipient_subject': None})), 'notification_limit_one_per_instance': Tunable(description='\n            If enabled, this will cause only one notification to be run per instance of this type. For example,\n            if there multiple recipient sims, all sims will learn the specified traits, but the notification\n            will only be displayed once.', tunable_type=bool, default=False), 'notification_group_preferences': Tunable(description='\n            If enabled, this will change how the trait list token works, so that\n            preference traits are grouped together in a more readable way.\n            \n            For example, if we are learning about the following traits:\n            - Good\n            - Bro\n            - Likes Blue\n            - Likes Outdoorsy\n            - Turned on by Music\n            - Turned on by Brown Hair\n            - Turned on by Blonde Hair\n            - Dislikes Green\n            - Dislikes Ambitious\n            - Turned off by White Hair\n            \n            We would get the following output for the trait list string:\n            \n            - Good\n            - Bro\n            Likes\n            - Likes Blue\n            - Likes Outdoorsy\n            Dislikes\n            - Dislikes Green\n            - Dislikes Ambitious\n            Turn Ons\n            - Turned on by Music\n            - Turned on by Brown Hair\n            - Turned on by Blonde Hair\n            Turn Offs\n            - Turned off by White Hair\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, traits, notification, notification_no_more_traits, notification_limit_one_per_instance, notification_group_preferences, **kwargs):
        super().__init__(*args, **kwargs)
        self.traits = traits
        self.notification = notification
        self.notification_no_more_traits = notification_no_more_traits
        self.notification_limit_one_per_instance = notification_limit_one_per_instance
        self.notification_group_preferences = notification_group_preferences
        self.notification_limit_target_sim = None
        self.notification_has_been_run_for_target_sim = False

    @staticmethod
    def _select_traits(knowledge, trait_tracker, trait_types, random_count=None):
        traits = set()
        for trait_type in trait_types:
            traits.update(trait for trait in trait_tracker.get_traits_of_type(trait_type) if trait not in knowledge.known_traits)
        if random_count is not None and traits:
            return random.sample(traits, min(random_count, len(traits)))
        return traits

    def verify_valid_knowledge_trait(self, trait_tracker, interaction):
        if self.traits.learned_type == KnowOtherSimTraitOp.TRAIT_SPECIFIED:
            for trait in self.traits.potential_traits:
                if trait.trait_type not in trait_tracker.KNOWLEDGE_TRAIT_TYPES:
                    logger.error("{}: Tuned to get knowledge of trait {}, whose type {} is not allowed. Look at 'Knowledge Trait Types' in trait_tracker for the valid types.", interaction.affordance.__name__, trait, trait.trait_type, owner='asantos')
        elif self.traits.learned_type == KnowOtherSimTraitOp.TRAIT_ALL or self.traits.learned_type == KnowOtherSimTraitOp.TRAIT_RANDOM:
            for trait_type in self.traits.trait_types:
                if trait_type not in trait_tracker.KNOWLEDGE_TRAIT_TYPES:
                    logger.error("{}: Tuned to get knowledge of trait of type {}, which is not allowed. Look at 'Knowledge Trait Types' in trait_tracker for the valid types.", interaction.affordance.__name__, trait_type.name, owner='asantos')

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        trait_tracker = target.trait_tracker
        if self.traits.learned_type == self.TRAIT_SPECIFIED:
            traits = tuple(trait for trait in self.traits.potential_traits if trait_tracker.has_trait(trait) and trait not in knowledge.known_traits)
        elif self.traits.learned_type == self.TRAIT_ALL:
            traits = self._select_traits(knowledge, trait_tracker, self.traits.trait_types)
        elif self.traits.learned_type == self.TRAIT_RANDOM:
            traits = self._select_traits(knowledge, trait_tracker, self.traits.trait_types, random_count=self.traits.count)
            if traits or self.notification_no_more_traits is not None:
                interaction = resolver.interaction
                if interaction is not None:
                    self.notification_no_more_traits(interaction).show_notification(additional_tokens=(subject, target), recipients=(subject,), icon_override=IconInfoData(obj_instance=target))
        for trait in traits:
            knowledge.add_known_trait(trait)
        if traits:
            interaction = resolver.interaction
            if self.notification_limit_target_sim is not target:
                self.notification_has_been_run_for_target_sim = False
            if self.notification_has_been_run_for_target_sim and interaction is not None and self.notification is not None and not self.notification_has_been_run_for_target_sim:
                trait_string = self._build_trait_list_string(traits, target)
                if subject.is_player_sim:
                    self.notification_limit_target_sim = target
                    self.notification_has_been_run_for_target_sim = True
                self.notification(interaction).show_notification(additional_tokens=(subject, target, trait_string), recipients=(subject,), icon_override=IconInfoData(obj_instance=target))

    def _build_trait_list_string(self, traits:'List[Trait]', target) -> 'str':

        def localize_list(trait_list:'List[Trait]') -> 'str':
            return LocalizationHelperTuning.get_bulleted_list((None,), (trait_item.display_name(target) for trait_item in trait_list))

        if not self.notification_group_preferences:
            return LocalizationHelperTuning.get_bulleted_list((None,), (trait.display_name(target) for trait in traits))
        default_traits = []
        traits_by_preference_group = {}
        for trait in traits:
            if not trait.is_preference_trait:
                default_traits.append(trait)
            else:
                group = PreferenceTuning.try_get_preference_group_for_trait(trait)
                if group is None:
                    logger.error('Unable to get group for trait {} when building knowledge notification', trait, owner='mjuskelis')
                else:
                    if group not in traits_by_preference_group:
                        traits_by_preference_group[group] = ([], [])
                    if trait.preference_item.like == trait:
                        traits_by_preference_group[group][0].append(trait)
                    else:
                        traits_by_preference_group[group][1].append(trait)
        strings = []
        if len(default_traits) > 0:
            strings.append(localize_list(default_traits))
            strings.append('')
        for group in PreferenceTuning.CAS_PREFERENCE_GROUPS:
            if group in traits_by_preference_group:
                positive_traits = [trait.display_name(target) for trait in traits_by_preference_group[group][0]]
                if len(positive_traits) > 0:
                    strings.append(LocalizationHelperTuning.get_bulleted_list(group.items_name_positive, positive_traits))
                    strings.append('')
                negative_traits = [trait.display_name(target) for trait in traits_by_preference_group[group][1]]
                if len(negative_traits) > 0:
                    strings.append(LocalizationHelperTuning.get_bulleted_list(group.items_name_negative, negative_traits))
                    strings.append('')
        if strings[-1] == '':
            strings.pop(-1)
        return LocalizationHelperTuning.get_new_line_separated_strings(*strings)

class KnowOtherSimCareerOp(RelationshipBitTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None or knowledge.knows_career:
            return
        knowledge.add_knows_career(target.sim_id)
        career_tracker = target.career_tracker
        if career_tracker.has_custom_career:
            career_tracker.custom_career_data.show_custom_career_knowledge_notification(subject, DoubleSimResolver(subject, target))
            return
        for career in knowledge.get_known_careers():
            career.show_knowledge_notification(subject, DoubleSimResolver(subject, target))

class KnowOtherSimSexualOrientationOp(RelationshipBitTargetedLootOperation):
    FACTORY_TUNABLES = {'gender_preference_types': TunableList(description='\n            Gender preference types that the actor may learn about the target.\n            ', tunable=TunableEnumEntry(description='\n                The orientation type of the Sim that we are adding knowledge for.\n                Romantic includes which genders the Sim is romantically attracted\n                to, as well as whether they are exploring. Woohoo refers to the\n                set of genders the Sim is interested in Woohoo with.\n                ', tunable_type=GenderPreferenceType, default=GenderPreferenceType.ROMANTIC))}

    def __init__(self, *args, gender_preference_types, **kwargs):
        super().__init__(*args, **kwargs)
        self.gender_preference_types = gender_preference_types

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        for orientation_type in self.gender_preference_types:
            if orientation_type == GenderPreferenceType.ROMANTIC:
                if knowledge.knows_romantic_preference:
                    pass
                else:
                    knowledge.add_knows_romantic_preference(target.sim_id)
                    if orientation_type == GenderPreferenceType.WOOHOO:
                        if knowledge.knows_woohoo_preference:
                            pass
                        else:
                            knowledge.add_knows_woohoo_preference(target.sim_id)
                            logger.error('Invalid orientation type tuned for Sexual Orientation knowledge.', owner='amwu')
                            return
                    else:
                        logger.error('Invalid orientation type tuned for Sexual Orientation knowledge.', owner='amwu')
                        return
            elif orientation_type == GenderPreferenceType.WOOHOO:
                if knowledge.knows_woohoo_preference:
                    pass
                else:
                    knowledge.add_knows_woohoo_preference(target.sim_id)
                    logger.error('Invalid orientation type tuned for Sexual Orientation knowledge.', owner='amwu')
                    return
            else:
                logger.error('Invalid orientation type tuned for Sexual Orientation knowledge.', owner='amwu')
                return

class RelationshipExpectationsOp(BaseTargetedLootOperation):
    CHANGE_OTHER_SIM_RELATIONSHiP_EXPECTATION_OUTLOOK = 0
    KNOW_OTHER_SIM_RELATIONSHIP_EXPECTATIONS = 1
    FACTORY_TUNABLES = {'relationship_expectations_op': TunableVariant(description='\n            The op to run.\n            ', change_other_sim_relationship_expectation_outlook=TunableTuple(description='\n                Change the relationship expectation outlook of the target sim for the passed in \n                relationship expectation type.\n                ', locked_args={'op_type': CHANGE_OTHER_SIM_RELATIONSHiP_EXPECTATION_OUTLOOK}, relationship_expectation_type=TunableEnumEntry(description='\n                    The relationship expectation type to change the outlook of.\n                    ', tunable_type=RelationshipExpectationType, default=RelationshipExpectationType.PHYSICAL)), know_other_sim_relationship_expectations=TunableTuple(description="\n                Add the target sim's relationship expectations to the actor sim's knowledge\n                of the target sim.\n                ", locked_args={'op_type': KNOW_OTHER_SIM_RELATIONSHIP_EXPECTATIONS}, enabled=Tunable(description='\n                    Whether or not to enable this op.\n                    ', tunable_type=bool, default=True)), default='change_other_sim_relationship_expectation_outlook')}

    def __init__(self, *args, relationship_expectations_op, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self.relationship_expectations_op = relationship_expectations_op

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver') -> 'None':
        if subject is None or target is None:
            return
        if self.relationship_expectations_op.op_type == self.KNOW_OTHER_SIM_RELATIONSHIP_EXPECTATIONS:
            if self.relationship_expectations_op.enabled:
                services.relationship_service().add_knows_relationship_expectations(subject.sim_id, target.sim_id)
        elif self.relationship_expectations_op.op_type == self.CHANGE_OTHER_SIM_RELATIONSHiP_EXPECTATION_OUTLOOK:
            result = target.sim_info.change_relationship_expectation_outlook_for_type(self.relationship_expectations_op.relationship_expectation_type)
            if result:
                services.relationship_service().add_knows_relationship_expectations(subject.sim_id, target.sim_id)

class KnowOtherSimsStat(RelationshipTargetedLootOperation):
    FACTORY_TUNABLES = {'statistics': TunableSet(description='\n            A list of all the Statistics that the Sim can learn from\n            this loot op.\n            ', tunable=TunableReference(description='\n                A tunable reference to a statistic that might be learned\n                from this op.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True)), 'notification': OptionalTunable(description="\n            Specify a notification that will be displayed for every subject if\n            information is learned about each individual target_subject. This\n            should probably be used only if you can ensure that target_subject\n            does not return multiple participants. The first two additional\n            tokens are the Sim and target Sim, respectively. A third token\n            containing a string with a bulleted list of stat names will be a\n            String token in here. If you are learning multiple traits, you\n            should probably use it. If you're learning a single trait, you can\n            get away with writing specific text that does not use this token.\n            ", tunable=NotificationElement.TunableFactory(locked_args={'recipient_subject': None}))}

    def __init__(self, *args, statistics=None, notification=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._statistics = statistics
        self._notification = notification

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        target_tracker = target.commodity_tracker
        learned_stats = set()
        for stat in self._statistics:
            if target_tracker.has_statistic(stat) and stat not in knowledge.known_stats:
                knowledge.add_known_stat(stat)
                learned_stats.add(stat)
        if learned_stats:
            interaction = resolver.interaction
            if interaction is not None and self._notification is not None:
                stat_string = LocalizationHelperTuning.get_bulleted_list((None,), (statistic.stat_name for statistic in learned_stats))
                self._notification(interaction).show_notification(additional_tokens=(stat_string,), recipients=(subject,), icon_override=IconInfoData(obj_instance=target))

class KnowOtherSimRelTrackOp(RelationshipTargetedLootOperation):
    FACTORY_TUNABLES = {'rel_tracks': TunableSet(description='\n        A list of all Relationship Tracks that the\n        Sim can learn from this op.\n        ', tunable=TunableReference(description='\n                A tunable reference to a Relationship\n                track that might be learned from this op.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack'))}

    def __init__(self, *args, rel_tracks:'Set[RelationshipTrack]'=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._rel_tracks = rel_tracks

    def _apply_to_subject_and_target(self, subject:'Sim', target:'Sim', resolver:'Resolver'):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        for rel_track in self._rel_tracks:
            track = target.relationship_tracker.get_relationship_track(subject.sim_id, rel_track)
            if track is not None:
                knowledge.add_known_rel_track(rel_track)

class KnowOtherSimMajorOp(RelationshipBitTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None or knowledge.knows_major:
            return
        knowledge.add_knows_major(target.sim_id)
        degree_tracker = target.degree_tracker
        degree_tracker.show_knowledge_notification(subject, DoubleSimResolver(subject, target))

class KnowOtherSimNetWorthOp(RelationshipTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver'):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        household = services.household_manager().get_by_sim_id(target.sim_id)
        if household is None:
            logger.error('No household data found for {}.', target)
            return
        knowledge.set_known_net_worth(household.household_net_worth())

class KnowOtherSimRelationshipStatusOp(RelationshipBitTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver'):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge is None:
            return
        knowledge.add_knows_relationship_status()

class ParticipantTypeSimSecrets(enum.LongFlags):
    TargetSim = ParticipantType.TargetSim
    LotOwnersOrRenters = ParticipantType.LotOwnersOrRenters

class KnowOtherSimSecretOp(RelationshipTargetedLootOperation):
    FACTORY_TUNABLES = {'success_notification': NotificationElement.TunableFactory(description='\n            The notification to display if a secret was successfully found.\n            ', locked_args={'recipient_subject': None}), 'failure_notification': NotificationElement.TunableFactory(description='\n            The notification to display if no secret could be found.\n            ')}

    def __init__(self, success_notification, failure_notification, **kwargs):
        super().__init__(**kwargs)
        self.success_notification = success_notification
        self.failure_notification = failure_notification

    def apply_to_resolver(self, resolver, skip_test=False):
        if self.target_participant_type != ParticipantTypeSimSecrets.TargetSim:
            target_household_id = services.get_persistence_service().get_household_id_from_zone_id(services.current_zone_id())
            for subject in self.resolve_participants(self.subject, resolver, self._subject_filter_tests):
                target = services.sim_secrets_service().determine_snooping_target(subject, target_household_id)
                if target is None:
                    self.failure_notification(resolver.interaction).show_notification(additional_tokens=(subject,), recipients=(subject,))
                else:
                    self._apply_to_subject_and_target(subject, target, resolver)
        else:
            super().apply_to_resolver(resolver, skip_test=skip_test)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        sim_secrets_service = services.sim_secrets_service()
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if knowledge.knows_unconfronted_secret:
            logger.error('Active sim {} must confront Target sim {} before finding more secrets.'.format(subject, target))
            return
        interaction = resolver.interaction
        secret = sim_secrets_service.generate_secret_for_target_sim(source_sim=subject, target_sim_id=target.sim_id)
        if secret is None:
            self.failure_notification(interaction).show_notification(additional_tokens=(subject,), recipients=(subject,))
            return
        relationship_tracker = subject.relationship_tracker
        if relationship_tracker.get_relationship_track(target.sim_id) is None:
            relationship_tracker.add_relationship_score(target.sim_id, -1)
        knowledge.set_unconfronted_secret(secret)
        interaction.set_saved_participant(0, target.sim_info)
        self.success_notification(interaction).show_notification(additional_tokens=(subject, target, secret.display_name()), recipients=(subject,))

class ConfrontOtherSimSecretOp(RelationshipTargetedLootOperation):
    FACTORY_TUNABLES = {'blackmail_secret': Tunable(description="\n            If checked, the unconfronted secret about the target sim will be set to 'BLACKMAILED'\n            ", tunable_type=bool, default=False)}

    def __init__(self, blackmail_secret, **kwargs):
        super().__init__(**kwargs)
        self.blackmail_secret = blackmail_secret

    @property
    def target_participant_type(self):
        return ParticipantType.TargetSim

    def _apply_to_subject_and_target(self, subject, target, resolver):
        knowledge = subject.relationship_tracker.get_knowledge(target.sim_id, initialize=True)
        if not knowledge.knows_unconfronted_secret:
            logger.error('{} cannot confront {} who does not have an unconfronted secret.'.format(subject, target))
            return
        knowledge.make_secret_known(blackmailed=self.blackmail_secret, notify_client=True)
