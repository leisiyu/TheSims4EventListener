import servicesfrom date_and_time import create_time_spanfrom sims.sim_info import SimInfofrom sims4.resources import Typesfrom event_testing.test_events import TestEventfrom sims4.tuning.tunable import TunableReferencefrom sims4.tuning.instances import lock_instance_tunablesfrom situations.custom_states.custom_states_situation_states import CustomStatesSituationStatefrom situations.custom_states.temporary_clone_situation import TemporaryCloneSituationfrom situations.situation import Situationfrom situations.situation_time_jump import SituationTimeJumpSimulatefrom objects.components.types import STORED_SIM_INFO_COMPONENTORIGINAL_SIM_ID_TOKEN = 'original_sim_id'SKILLS_GAINED_TOKEN = 'skills_gained'
class SemiPermanentCloneSituation(TemporaryCloneSituation):
    INSTANCE_TUNABLES = {'bit_between_clone_and_original': TunableReference(description='\n            The relationship bit given to the original sim and their clone.\n            ', manager=services.get_instance_manager(Types.RELATIONSHIP_BIT), pack_safe=True)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._skills_gained = set()
        self._original = None
        self._register_test_event(TestEvent.SkillValueChange)
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            original_sim_id = reader.read_uint64(ORIGINAL_SIM_ID_TOKEN, 0)
            if original_sim_id != 0:
                self._original = services.sim_info_manager().get(original_sim_id)
            skills_guids = reader.read_uint64s(SKILLS_GAINED_TOKEN, list())
            for skill_guid in skills_guids:
                skill = services.get_instance_manager(Types.STATISTIC).get(skill_guid)
                if skill is not None:
                    self.add_skill_gained(skill)

    @classmethod
    def should_load_after_time_jump(cls, seed):
        elapsed_time = create_time_span(minutes=services.current_zone().time_elapsed_since_last_save().in_minutes())
        if seed.duration_override is not None:
            if elapsed_time > seed.duration_override:
                return False
            seed.duration_override -= elapsed_time
        return True

    def start_situation(self):
        sim = self.get_clone()
        for relationship in services.relationship_service().get_all_sim_relationships(sim.id):
            if relationship.has_bit(sim.id, self.bit_between_clone_and_original):
                self._original = relationship.get_other_sim(sim.id)
        sim.allow_fame = False
        sim.allow_reputation = False
        self.store_clone_info_in_original()
        super().start_situation()

    def load_situation(self):
        return super().load_situation()

    def _save_custom_situation(self, writer):
        writer.write_uint64(ORIGINAL_SIM_ID_TOKEN, self._original.id)
        skills_guids = list()
        for skill_gained in self._skills_gained:
            skills_guids.append(skill_gained.guid64)
        writer.write_uint64s(SKILLS_GAINED_TOKEN, skills_guids)

    def _destroy(self):
        if self._original is not None:
            for skill_gained in self._skills_gained:
                clone_skill_value = self.get_clone().commodity_tracker.get_value(skill_gained)
                skill_diff = clone_skill_value - self._original.commodity_tracker.get_value(skill_gained)
                if skill_diff > 0:
                    self._original.commodity_tracker.set_value(skill_gained, clone_skill_value)
        super()._destroy()

    def get_clone(self) -> SimInfo:
        return self.initiating_sim_info

    def get_original(self) -> SimInfo:
        return self._original

    def store_clone_info_in_original(self):
        originals_stored_sim_info = self._original.get_component(STORED_SIM_INFO_COMPONENT)
        if originals_stored_sim_info is not None:
            originals_stored_sim_info.overwrite_sim_id(sim_id=self.get_clone().id)
        else:
            self._original.add_dynamic_component(STORED_SIM_INFO_COMPONENT, sim_id=self.get_clone().id)

    def add_skill_gained(self, skill_stat):
        self._skills_gained.add(skill_stat)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SkillValueChange:
            if not self.is_sim_info_in_situation(sim_info):
                return
            skill_gained = resolver.event_kwargs.get('skill')
            if skill_gained is not None:
                self.add_skill_gained(skill_gained.skill_type)
            return
        super().handle_event(sim_info, event, resolver)
lock_instance_tunables(SemiPermanentCloneSituation, time_jump=SituationTimeJumpSimulate())