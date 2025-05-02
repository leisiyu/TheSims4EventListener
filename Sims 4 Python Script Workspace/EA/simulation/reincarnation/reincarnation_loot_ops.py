import servicesimport sims4from interactions.utils.loot_basic_op import BaseLootOperationlogger = sims4.log.Logger('LootOperations')
class ReincarnationLootOp(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to reincarnate a None subject for participant {}. Loot: {}', self.subject, self)
            return
        if not subject.is_sim:
            logger.error('Attempting to reincarnate subject {} that is not a Sim. Loot: {}', self.subject, self)
            return
        services.get_reincarnation_service().reincarnation(subject.sim_info)
