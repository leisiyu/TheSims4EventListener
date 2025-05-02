from interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunablePackSafeReference, TunableEnumEntryimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('SmallBusinessCustomerLootOps', default_owner='mmikolajczyk')
class SmallBusinessCustomerStates(enum.Int):
    DELIBERATE = 1
    CHECK_IN = 2
    BUSINESS_VISIT = 3
    LEAVE = 4
    CHECK_OUT = 5
    DEFAULT = 6

class SmallBusinessCustomerSituationStateChange(BaseLootOperation):
    FACTORY_TUNABLES = {'customer_situation': TunablePackSafeReference(description="\n            The Situation who's state will change.\n            ", manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'situation_state': TunableEnumEntry(description='\n            Situation state to be set for the customer.\n            ', tunable_type=SmallBusinessCustomerStates, default=SmallBusinessCustomerStates.DEFAULT, invalid_enums=(SmallBusinessCustomerStates.DEFAULT,))}

    def __init__(self, *args, customer_situation, situation_state, **kwargs):
        super().__init__(*args, **kwargs)
        self._customer_situation = customer_situation
        self._situation_state = situation_state

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if self._customer_situation is None:
            return
        if subject is None:
            return
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_sim_is_in(subject.get_sim_instance()):
            if type(situation) is self._customer_situation:
                situation.set_small_business_customer_situation_state(self._situation_state)
                return
        logger.error('Sim {} trying to switch situation state {} while not running the small business customer situation', subject, self._situation_state)
