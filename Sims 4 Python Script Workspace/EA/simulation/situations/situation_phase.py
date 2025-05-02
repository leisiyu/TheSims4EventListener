from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from date_and_time import TimeSpan
    from typing import *from date_and_time import create_time_span
class SituationPhase:

    def __init__(self, job_list, exit_conditions, duration:'int') -> 'None':
        self._job_list = job_list
        self._exit_conditions = exit_conditions
        self._duration = create_time_span(minutes=duration)

    def jobs_gen(self):
        for (job, role) in self._job_list.items():
            yield (job, role)

    def exit_conditions_gen(self):
        for ec in self._exit_conditions:
            yield ec

    def get_duration(self) -> 'TimeSpan':
        return self._duration
