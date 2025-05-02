from _weakrefset import WeakSetfrom collections import OrderedDictimport itertoolsfrom objects.object_enums import ResetReasonfrom services.reset_and_delete_service import ResetRecordfrom sims4.repr_utils import standard_reprfrom singletons import EMPTY_SETfrom typing import Callable, NamedTuplefrom uid import UniqueIdGeneratorimport element_utilsimport elementsimport gsi_handlers.master_controller_handlersimport gsi_handlers.sim_timeline_handlersimport resetimport servicesimport sims4.logimport sims4.service_managerlogger = sims4.log.Logger('MasterController')
class _RunWorkGenElement(elements.SubclassableGeneratorElement):

    def __init__(self, work_entry, work_element, master_controller):
        super().__init__()
        self._work_entry = work_entry
        self._work_element = work_element
        self._master_controller = master_controller
        self.canceled = False

    def __repr__(self):
        return '{} {}'.format(super().__repr__(), self._work_element)

    def _run_gen(self, timeline):
        if self.canceled:
            return
        self._work_entry.running = True
        try:
            logger.debug('STARTING WORK: {}', self._work_entry)
            self._master_controller._gsi_add_sim_time_line_entry(self._work_entry, 'Run', 'Calling work')
            yield from element_utils.run_child(timeline, self._work_element)
        finally:
            logger.debug('FINISHED WORK: {}', self._work_entry)
            self._work_entry.remove_from_master_controller()
            self._work_entry.running = False
        self._master_controller._process(*self._work_entry.resources)
