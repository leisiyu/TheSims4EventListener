from __future__ import annotationsfrom event_testing.test_events import TestEventfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from careers.career_tuning import Career
    from careers.retirement import Retirement
    from relationships.relationship_track import RelationshipTrack
    from sims.secrets.tunable_sim_secret import SimSecret
    from sims.sim_info_types import Gender
    from sims.university.university_career_tuning import UniversityCourseCareerSlot
    from sims.university.university_tuning import UniversityMajor
    from statistics.statistic import Statistic
    from traits.traits import Trait
    from typing import *import singletonsfrom sims.global_gender_preference_tuning import GlobalGenderPreferenceTuningfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom careers.career_unemployment import CareerUnemploymentimport servicesimport sims4from traits.trait_tracker import TraitTrackerlogger = sims4.log.Logger('Relationship', default_owner='jjacobson')
class SimKnowledge:
    __slots__ = ('_rel_data', '_known_traits', '_knows_career', '_known_stats', '_known_rel_tracks', '_knows_major', '_knows_rel_status', '_knows_romantic_preference', '_knows_woohoo_preference', '_known_romantic_genders', '_known_woohoo_genders', '_known_exploring_sexuality', '_known_net_worth', '_knows_secrets', '_confronted_secrets', '_unconfronted_secret', '_known_relationship_expectations')

    def __init__(self, rel_data):
        self._rel_data = rel_data
        self._known_traits = None
        self._knows_career = False
        self._known_stats = None
        self._known_rel_tracks = None
        self._knows_major = False
        self._knows_rel_status = False
        self._knows_romantic_preference = False
        self._knows_woohoo_preference = False
        self._known_romantic_genders = None
        self._known_woohoo_genders = None
        self._known_exploring_sexuality = None
        self._known_net_worth = None
        self._confronted_secrets = []
        self._unconfronted_secret = None
        self._known_relationship_expectations = []

    def _on_change(self, notify_client:'bool'=True) -> 'None':
        services.get_event_manager().process_event(TestEvent.KnowledgeChanged, actor_sim_id=self._rel_data.sim_id_a, target_sim_id=self._rel_data.sim_id_b)
        if notify_client:
            self._rel_data.relationship.send_relationship_info()

    def add_known_trait(self, trait:'Trait', notify_client:'bool'=True) -> 'bool':
        return_value = False
        if trait.trait_type in TraitTracker.KNOWLEDGE_TRAIT_TYPES:
            if self._known_traits is None:
                self._known_traits = set()
            if trait not in self._known_traits:
                return_value = True
                self._known_traits.add(trait)
        else:
            logger.error("Try to add trait of a type not allowed for knowledge {} to Sim {}'s knowledge about to Sim {}", trait, self._rel_data.sim_id_a, self._rel_data.sim_id_b)
        if return_value:
            self._on_change(notify_client)
        return return_value

    def remove_known_trait(self, trait:'Trait', notify_client:'bool'=True) -> 'None':
        if trait.trait_type in TraitTracker.KNOWLEDGE_TRAIT_TYPES:
            if self._known_traits is None or trait not in self._known_traits:
                return
            self._known_traits.remove(trait)
            self._on_change(notify_client)
        else:
            logger.error("Try to remove trait of a type not allowed for knowledge {} from Sim {}'s knowledge about to Sim {}", trait, self._rel_data.sim_id_a, self._rel_data.sim_id_b)

    @property
    def known_traits(self) -> 'Set[Trait]':
        if self._known_traits is None:
            return ()
        return self._known_traits

    @property
    def knows_romantic_preference(self) -> 'bool':
        return self._knows_romantic_preference

    @property
    def known_romantic_genders(self) -> 'Set[Gender]':
        if self._known_romantic_genders is None:
            return singletons.EMPTY_SET
        return self._known_romantic_genders

    @property
    def get_known_exploring_sexuality(self) -> 'bool':
        return self._known_exploring_sexuality

    def add_knows_romantic_preference(self, notify_client:'bool'=True) -> 'bool':
        if self._knows_romantic_preference:
            return False
        target_sim_info = self._rel_data.find_target_sim_info()
        if target_sim_info is None:
            return False
        genders = set()
        for (gender, trait_pair) in GlobalGenderPreferenceTuning.ROMANTIC_PREFERENCE_TRAITS_MAPPING.items():
            attracted_trait = trait_pair.is_attracted_trait
            if attracted_trait is None:
                logger.error('Missing romantic preference trait tuning for {} gender.', gender, owner='amwu')
                return False
            if target_sim_info.has_trait(attracted_trait):
                genders.add(gender)
        self._knows_romantic_preference = True
        self._known_romantic_genders = frozenset(genders)
        self._known_exploring_sexuality = target_sim_info.is_exploring_sexuality
        self._on_change(notify_client)
        return True

    def remove_knows_romantic_preference(self, notify_client:'bool'=True):
        if not self._knows_romantic_preference:
            return
        self._knows_romantic_preference = False
        self._known_romantic_genders = None
        self._known_exploring_sexuality = None
        self._on_change(notify_client)

    @property
    def knows_woohoo_preference(self) -> 'bool':
        return self._knows_woohoo_preference

    @property
    def known_woohoo_genders(self) -> 'Set[Gender]':
        if self._known_woohoo_genders is None:
            return singletons.EMPTY_SET
        return self._known_woohoo_genders

    def add_knows_woohoo_preference(self, notify_client:'bool'=True) -> 'bool':
        if self._knows_woohoo_preference:
            return False
        target_sim_info = self._rel_data.find_target_sim_info()
        if target_sim_info is None:
            return False
        genders = set()
        for (gender, trait_pair) in GlobalGenderPreferenceTuning.WOOHOO_PREFERENCE_TRAITS_MAPPING.items():
            attracted_trait = trait_pair.is_attracted_trait
            if attracted_trait is None:
                logger.error('Missing woohoo preference trait tuning for {} gender.', gender, owner='amwu')
                return False
            if target_sim_info.has_trait(attracted_trait):
                genders.add(gender)
        self._knows_woohoo_preference = True
        self._known_woohoo_genders = frozenset(genders)
        self._on_change(notify_client)
        return True

    def remove_knows_woohoo_preference(self, notify_client:'bool'=True):
        if not self._knows_woohoo_preference:
            return
        self._knows_woohoo_preference = False
        self._known_woohoo_genders = None
        self._on_change(notify_client)

    @property
    def known_relationship_expectations(self) -> 'List[Trait]':
        return self._known_relationship_expectations

    def add_knows_relationship_expectations(self, notify_client:'bool'=True) -> 'bool':
        if self.known_relationship_expectations:
            return False
        target_sim_info = self._rel_data.find_target_sim_info()
        if target_sim_info is None:
            return False
        relationship_expectations = target_sim_info.get_relationship_expectations()
        if relationship_expectations is None:
            return False
        self._known_relationship_expectations = relationship_expectations.copy()
        self._on_change(notify_client)
        return True

    def remove_knows_relationship_expectations(self, notify_client:'bool'=True) -> 'None':
        if len(self._known_relationship_expectations) > 0:
            self._known_relationship_expectations = []
            self._on_change(notify_client)

    @property
    def knows_relationship_status(self) -> 'bool':
        return self._knows_rel_status

    def add_knows_relationship_status(self, notify_client:'bool'=True):
        value_changed = not self._knows_rel_status
        self._knows_rel_status = True
        if value_changed:
            self._on_change(notify_client)

    @property
    def knows_career(self) -> 'bool':
        return self._knows_career

    def add_knows_career(self, notify_client:'bool'=True) -> 'bool':
        value_changed = not self._knows_career
        self._knows_career = True
        if value_changed:
            self._on_change(notify_client)
        return value_changed

    def remove_knows_career(self, notify_client:'bool'=True):
        value_changed = self._knows_career
        self._knows_career = False
        if value_changed:
            self._on_change(notify_client)

    def get_known_careers(self) -> 'Set[Union[Career, CareerUnemployment, Retirement]]':
        if self._knows_career:
            target_sim_info = self._rel_data.find_target_sim_info()
            if target_sim_info is not None:
                if target_sim_info.career_tracker.has_career:
                    careers = tuple(career for career in target_sim_info.careers.values() if career.is_visible_career and not career.is_course_slot)
                    if careers:
                        return careers
                if target_sim_info.career_tracker.retirement is not None:
                    return (target_sim_info.career_tracker.retirement,)
                else:
                    return (CareerUnemployment(target_sim_info),)
        return ()

    def get_known_careertrack_ids(self) -> 'Set[int]':
        return (career_track.current_track_tuning.guid64 for career_track in self.get_known_careers())

    @property
    def knows_net_worth(self) -> 'bool':
        return self._known_net_worth is not None

    @property
    def known_net_worth(self) -> 'int':
        if self.knows_net_worth:
            return self._known_net_worth
        return -1

    def set_known_net_worth(self, net_worth:'int', notify_client:'bool'=True) -> 'bool':
        if self._known_net_worth is not None and self._known_net_worth == net_worth:
            return False
        self._known_net_worth = net_worth
        self._on_change(notify_client)
        return True

    def add_known_stat(self, stat, notify_client:'bool'=True):
        if self._known_stats is None:
            self._known_stats = set()
        if stat in self._known_stats:
            return
        self._known_stats.add(stat)
        self._on_change(notify_client)

    @property
    def known_stats(self) -> 'Set[Statistic]':
        if self._known_stats is None:
            return ()
        return self._known_stats

    @property
    def known_rel_tracks(self) -> 'Set[RelationshipTrack]':
        if self._known_rel_tracks is None:
            return ()
        return self._known_rel_tracks

    def add_known_rel_track(self, rel_track:'RelationshipTrack', notify_client:'bool'=True):
        if self._known_rel_tracks is None:
            self._known_rel_tracks = set()
        if rel_track not in self._known_rel_tracks:
            self._known_rel_tracks.add(rel_track)
            self._on_change(notify_client)

    @property
    def knows_major(self) -> 'bool':
        return self._knows_major

    def add_knows_major(self, notify_client:'bool'=True) -> 'bool':
        return_value = not self._knows_major
        self._knows_major = True
        self._on_change(notify_client)
        return return_value

    def remove_knows_major(self, notify_client:'bool'=True):
        if self._knows_major:
            self._knows_major = False
            self._on_change(notify_client)

    def get_known_major(self) -> 'Optional[UniversityMajor]':
        if self._knows_major:
            target_sim_info = self._rel_data.find_target_sim_info()
            if target_sim_info is not None and target_sim_info.degree_tracker:
                return target_sim_info.degree_tracker.get_major()

    def get_known_major_career(self) -> 'Set[UniversityCourseCareerSlot]':
        if self._knows_major:
            target_sim_info = self._rel_data.find_target_sim_info()
            if target_sim_info is not None and target_sim_info.career_tracker.has_career:
                careers = tuple(career for career in target_sim_info.careers.values() if career.is_visible_career and career.is_course_slot)
                if careers:
                    return careers
        return ()

    @property
    def knows_confronted_secrets(self) -> 'bool':
        return len(self._confronted_secrets) > 0

    @property
    def knows_unconfronted_secret(self) -> 'bool':
        return self._unconfronted_secret is not None

    def set_unconfronted_secret(self, secret:'SimSecret', notify_client:'bool'=True) -> 'bool':
        if secret in self.get_all_secrets():
            logger.error('Adding a secret that has already been discovered for this sim.', owner='cparrish')
            return False
        self._unconfronted_secret = secret
        self._on_change(notify_client)
        return True

    def get_confronted_secrets(self) -> 'List[SimSecret]':
        return self._confronted_secrets

    def get_unconfronted_secret(self) -> 'SimSecret':
        return self._unconfronted_secret

    def get_all_secrets(self) -> 'List[SimSecret]':
        all_secrets = [secret for secret in self._confronted_secrets]
        if self._unconfronted_secret is not None:
            all_secrets.append(self._unconfronted_secret)
        return all_secrets

    def make_secret_known(self, blackmailed:'bool'=False, notify_client:'bool'=True) -> 'None':
        if self._unconfronted_secret in self._confronted_secrets:
            return
        self._unconfronted_secret.blackmailed = blackmailed
        self._confronted_secrets.append(self._unconfronted_secret)
        self._unconfronted_secret = None
        self._on_change(notify_client)

    def get_save_data(self) -> 'protocols.SimKnowledge':
        save_data = protocols.SimKnowledge()
        for trait in self.known_traits:
            save_data.trait_ids.append(trait.guid64)
        save_data.knows_career = self._knows_career
        if self._known_stats is not None:
            for stat in self._known_stats:
                save_data.stats.append(stat.guid64)
        save_data.knows_major = self._knows_major
        save_data.knows_romantic_preference = self._knows_romantic_preference
        save_data.knows_woohoo_preference = self._knows_woohoo_preference
        if self._known_romantic_genders is not None:
            for gender in self._known_romantic_genders:
                save_data.known_romantic_genders.append(gender)
        if self._known_woohoo_genders is not None:
            for gender in self._known_woohoo_genders:
                save_data.known_woohoo_genders.append(gender)
        if self._known_exploring_sexuality is not None:
            save_data.known_exploring_sexuality = self._known_exploring_sexuality
        for secret in self._confronted_secrets:
            confronted_secret = protocols.ConfrontedSimSecret()
            confronted_secret.secret_id = secret.guid64
            confronted_secret.blackmailed = secret.blackmailed
            save_data.confronted_secrets.append(confronted_secret)
        if self._unconfronted_secret is not None:
            save_data.unconfronted_secret_id = self._unconfronted_secret.guid64
        for expectation in self._known_relationship_expectations:
            save_data.known_relationship_expectations_ids.append(expectation.guid64)
        for track in self.known_rel_tracks:
            save_data.known_rel_tracks.append(track.guid64)
        if self.knows_net_worth:
            save_data.known_net_worth = self.known_net_worth
        return save_data

    def load_knowledge(self, save_data:'protocols.SimKnowledge') -> 'None':
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        stat_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for trait_inst_id in save_data.trait_ids:
            trait = trait_manager.get(trait_inst_id)
            if trait is not None:
                if self._known_traits is None:
                    self._known_traits = set()
                self._known_traits.add(trait)
        for stat_id in save_data.stats:
            if self._known_stats is None:
                self._known_stats = set()
            stat = stat_manager.get(stat_id)
            if stat is not None:
                self._known_stats.add(stat)
        self._knows_career = save_data.knows_career
        if hasattr(save_data, 'knows_major'):
            self._knows_major = save_data.knows_major
        if hasattr(save_data, 'knows_romantic_preference'):
            self._knows_romantic_preference = save_data.knows_romantic_preference
        if hasattr(save_data, 'knows_woohoo_preference'):
            self._knows_woohoo_preference = save_data.knows_woohoo_preference
        if self._knows_romantic_preference:
            self._known_romantic_genders = frozenset(save_data.known_romantic_genders)
        if self._knows_woohoo_preference:
            self._known_woohoo_genders = frozenset(save_data.known_woohoo_genders)
        if hasattr(save_data, 'known_exploring_sexuality'):
            self._known_exploring_sexuality = save_data.known_exploring_sexuality
        if hasattr(save_data, 'unconfronted_secret_id'):
            unconfronted_secret = snippet_manager.get(save_data.unconfronted_secret_id)
            if unconfronted_secret:
                self._unconfronted_secret = unconfronted_secret()
        if hasattr(save_data, 'confronted_secrets'):
            for saved_secret in save_data.confronted_secrets:
                secret = snippet_manager.get(saved_secret.secret_id)
                if secret:
                    secret_instance = secret()
                    secret_instance.blackmailed = saved_secret.blackmailed
                    self._confronted_secrets.append(secret_instance)
        for trait_inst_id in save_data.known_relationship_expectations_ids:
            trait = trait_manager.get(trait_inst_id)
            if trait is not None:
                self._known_relationship_expectations.append(trait)
        if save_data.known_rel_tracks:
            if self._known_rel_tracks is None:
                self._known_rel_tracks = set()
            for track in self._rel_data.relationship.relationship_tracks_gen(self._rel_data.sim_id_a):
                if track.guid64 in save_data.known_rel_tracks:
                    self._known_rel_tracks.add(track)
        if hasattr(save_data, 'known_net_worth'):
            self._known_net_worth = save_data.known_net_worth
