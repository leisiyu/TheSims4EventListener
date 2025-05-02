from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from sims.sim_info import SimInfo
    from typing import *from balloon.tunable_balloon import TunableBalloonfrom interactions.utils.loot_basic_op import BaseLootOperationimport sims4.resourceslogger = sims4.log.Logger('BalloonLootOps', default_owner='cseraphim')
class ShowBalloonOp(BaseLootOperation):
    FACTORY_TUNABLES = {'balloon': TunableBalloon(description='\n            The balloon to show when this loot op fires.\n            ')}

    def __init__(self, balloon, **kwargs):
        super().__init__(**kwargs)
        self.balloon = balloon

    def _apply_to_subject_and_target(self, subject:'SimInfo', target:'SimInfo', resolver:'Resolver'):
        requests = TunableBalloon.build_balloon_requests(resolver=resolver, balloon_target=self.balloon.balloon_target, balloon_choices=self.balloon.balloon_choices, balloon_delay=self.balloon.balloon_delay, balloon_delay_random_offset=self.balloon.balloon_delay_random_offset, balloon_chance=self.balloon.balloon_chance, balloon_view_offset=self.balloon.balloon_view_offset, source=resolver)
        for request in requests:
            request.distribute()
