import servicesfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypeSinglefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunablefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonInteractionCompletedSituationState, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionCUSTOMER_TOKEN = 'customer_id'
class BrowseItemsState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.object_sold()

    def timer_expired(self):
        self.owner._self_destruct()

class ConsumeItemState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()
YARD_SALE_SITUATION_ID_STR = 'yard_sale_situation_id'
class YardSaleCustomerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'browse_items_state': BrowseItemsState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_browse_items_state'), 'consume_item_state': ConsumeItemState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_consume_item_state'), 'customer_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the customer who wants to check out the\n            craft sales table.\n            '), 'consume_object': Tunable(description='\n            Whether the npc should consume the object after purchasing it.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, tunable_type=bool, default=False)}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.customer = None

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.customer_job_and_role_state.job, cls.customer_job_and_role_state.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self.customer = sim

    @classmethod
    def _states(cls):
        return (SituationStateData(1, BrowseItemsState, factory=cls.browse_items_state), SituationStateData(2, ConsumeItemState, factory=cls.consume_item_state))

    def on_remove(self):
        super().on_remove()

    def start_situation(self):
        super().start_situation()
        self._change_state(self.browse_items_state())

    def object_sold(self):
        if self.consume_object:
            self._change_state(self.consume_item_state())
        else:
            self._self_destruct()
REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLESlock_instance_tunables(YardSaleCustomerSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)