from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfo
    from event_testing.resolver import Resolverfrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableEnumEntry, Tunable
class ShowCheckTattooNotification(BaseLootOperation):
    DESIGN_FROM_CATALOG = 0
    DESIGN_FROM_PARTICIPANT = 1
    NONE = 2
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will equip the tattoo\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'allow_autonomous': Tunable(description='\n            If checked, then this notification will be displayed even if its\n            owning interaction was initiated by autonomy. If unchecked, then the\n            notification is suppressed if the interaction is autonomous.\n            ', tunable_type=bool, default=False)}

    def __init__(self, subject:'SimInfo', allow_autonomous:'bool', **kwargs):
        super().__init__(**kwargs)
        self._subject = subject
        self._allow_autonomous = allow_autonomous

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver') -> 'None':
        if not self._allow_autonomous:
            interaction = resolver.interaction
            if interaction is not None and interaction.is_autonomous:
                return
        subject.sim_info.tattoo_tracker.show_check_tattoo_notification()
