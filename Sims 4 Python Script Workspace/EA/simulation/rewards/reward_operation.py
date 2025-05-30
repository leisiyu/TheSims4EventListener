from interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunablePackSafeReferenceimport servicesimport sims4.loglogger = sims4.log.Logger('RewardOperation', default_owner='rmccord')
class RewardOperation(BaseLootOperation):
    FACTORY_TUNABLES = {'reward': TunablePackSafeReference(description='\n            The reward given to the subject of the loot operation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.REWARD))}

    def __init__(self, *args, reward, **kwargs):
        super().__init__(*args, **kwargs)
        self.reward = reward

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('Attempting to apply Reward Loot Op to {} which is not a Sim.', subject)
            return False
        if self.reward is None:
            return False
        self.reward.give_reward(subject)
        return True
