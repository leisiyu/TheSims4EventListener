from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.context import InteractionContext
    from objects.script_object import ScriptObject
    from objects.components.state import ObjectStateValuefrom event_testing.results import TestResultfrom interactions.base.picker_interaction import AutonomousPickerSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom objects.components.state_references import TunableStateTypeReferencefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunableimport sims4.loglogger = sims4.log.Logger('PickChannel')
class PickChannelAutonomouslySuperInteraction(AutonomousPickerSuperInteraction):
    INSTANCE_TUNABLES = {'state': TunableStateTypeReference(description='\n            The state used in the interaction.\n            '), 'push_additional_affordances': Tunable(description="\n            Whether to push affordances specified by the channel. This is used\n            for stereo's turn on and listen to... interaction.\n            ", tunable_type=bool, default=True)}

    @classmethod
    def _get_state_choices_gen(cls, target:'ScriptObject', context:'InteractionContext') -> 'ObjectStateValue':
        for client_state in target.get_client_states(cls.state):
            if client_state.show_in_picker and client_state.test_channel(target, context):
                yield client_state

    @classmethod
    def _test(cls, target, context, **kwargs):
        test_result = super()._test(target, context, **kwargs)
        if not test_result:
            return test_result
        for _ in cls._get_state_choices_gen(target, context):
            return TestResult.TRUE
        return TestResult(False, 'No valid choice for state:{}', cls.state)

    def _run_interaction_gen(self, timeline):
        weights = []
        sim = self.sim
        for client_state in self._get_state_choices_gen(self.target, self.context):
            weight = client_state.calculate_autonomy_weight(sim)
            weights.append((weight, client_state))
        logger.assert_log(weights, 'Failed to find choice in autonomous recipe picker')
        chosen_state = sims4.random.pop_weighted(weights)
        if chosen_state is None:
            logger.error('{} fail to find a valid chosen state value for state {}'.format(self.__class__.__name__, self.state))
            return False
        chosen_state.activate_channel(interaction=self, push_affordances=self.push_additional_affordances)
        return True

class WatchCurrentChannelAutonomouslySuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'state': TunableStateTypeReference(description='\n            The state to use to determine what to autonomously watch.\n            ')}

    def _run_interaction_gen(self, timeline):
        current_state = self.target.get_state(self.state)
        current_state.activate_channel(interaction=self, push_affordances=True)
        return True
lock_instance_tunables(AutonomousPickerSuperInteraction, allow_user_directed=False, basic_reserve_object=None, disable_transitions=True)