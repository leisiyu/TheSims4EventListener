from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from drama_scheduler.drama_node_types import DramaNodeTypefrom drama_scheduler.multi_unit_drama_node import MultiUnitEventDramaNodefrom sims4.utils import classpropertyfrom situations.custom_states.custom_states_situation import CustomStatesSituationimport services
class MultiUnitEventSituation(CustomStatesSituation):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drama_node_id = self._seed.extra_kwargs.get('drama_node_id', None)
        self._start_time = self._seed.extra_kwargs.get('start_time_override', None)

    @classproperty
    def allow_non_prestige_events(cls) -> 'bool':
        return True
