import sims4.logimport sims4.service_managerfrom singletons import DEFAULTlogger = sims4.log.Logger('InternService', default_owner='manus')
class InternService(sims4.service_manager.Service):

    def __init__(self):
        self._intern_dict = None
        self.started = False

    def intern(self, key, value=DEFAULT):
        if value is DEFAULT:
            value = key
        if self._intern_dict is None:
            return value
        if key in self._intern_dict:
            return self._intern_dict[key]
        self._intern_dict[key] = value
        return value

    def start(self):
        self.started = True

    def stop(self):
        self.started = False
        if self._intern_dict is not None:
            logger.error('InternService was not stopped using a service.')
            self.stop_interning()

    def _start_interning(self):
        if not self.started:
            logger.error('InternService was not started.')
        if self._intern_dict is not None:
            logger.error('InternService was double-started.')
        self._intern_dict = {}

    def _stop_interning(self):
        if self._intern_dict is None:
            logger.error('InternService was double-stopped.')
        self._intern_dict = None

    def get_start_interning(self):
        return _StartInterning(self)

    def get_stop_interning(self):
        return _StopInterning(self)

class _StartInterning(sims4.service_manager.Service):

    def __init__(self, intern_service):
        self.intern_service = intern_service

    def start(self):
        self.intern_service._start_interning()

class _StopInterning(sims4.service_manager.Service):

    def __init__(self, intern_service):
        self.intern_service = intern_service

    def start(self):
        self.intern_service._stop_interning()
