from __future__ import annotationsimport servicesfrom event_testing.test_events import TestEventfrom sims4.tuning.tunable import TunableEnumEntryfrom situations.situation_goal import SituationGoalfrom tutorials.tutorial_tip_enums import TutorialTipUiElementfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import DataResolver
    from protocolbuffers import Situations_pb2
    from sims.sim_info import SimInfo
    from typing import *
class SituationGoalUiInteraction(SituationGoal):
    INSTANCE_TUNABLES = {'_ui_element': TunableEnumEntry(description='\n                The UI element that when clicked will satisfy this goal.\n                ', tunable_type=TutorialTipUiElement, default=TutorialTipUiElement.UI_INVALID, invalid_enums=(TutorialTipUiElement.UI_INVALID,))}

    def setup(self) -> 'None':
        super().setup()
        services.get_event_manager().register(self, (TestEvent.UiElementInteracted,))

    def _run_goal_completion_tests(self, sim_info:'SimInfo', event:'TestEvent', resolver:'DataResolver') -> 'bool':
        result = super()._run_goal_completion_tests(sim_info, event, resolver)
        if not result:
            return False
        if 'ui_element' not in resolver.event_kwargs:
            return False
        else:
            ui_element = resolver.event_kwargs.get('ui_element')
            if int(ui_element) == int(self._ui_element):
                return True
        return False

    def build_goal_message(self, goal_msg:'Situations_pb2.SituationGoal') -> 'None':
        super().build_goal_message(goal_msg)
        goal_msg.ui_element = self._ui_element

    def _decommision(self) -> 'None':
        services.get_event_manager().unregister(self, (TestEvent.UiElementInteracted,))
        super()._decommision()
