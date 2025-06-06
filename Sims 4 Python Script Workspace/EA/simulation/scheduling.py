from __future__ import annotationsimport heapqimport inspectimport operatorimport timefrom performance.sim_debt_simulator import SimDebtSimulatorfrom sims4.callback_utils import CallableListConsumingExceptionsimport pathsimport sims4.logfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from elements import Element
    from typing import *MAX_GARBAGE_FACTOR = 0.5ACCEPTABLE_GARBAGE = 100MAX_ELEMENTS = 10000logger = sims4.log.Logger('Scheduling')
class HardStopError(BaseException):
    pass

def raise_exception(timeline, element, exception, message):
    raise exception

class Timeline:

    def __init__(self, now, debugger=None, exception_reporter=raise_exception):
        self.heap = []
        self.now = now
        self.future = now
        self._ix = 0
        self._garbage = 0
        self._active = None
        self._child = None
        self._pending_hard_stop = False
        self._exception_reporter = exception_reporter
        self.per_simulate_callbacks = CallableListConsumingExceptions()
        self.on_time_advanced = CallableListConsumingExceptions()
        self.debugger = debugger
        if debugger is not None:
            debugger.set_timeline(self)

    @property
    def is_frozen(self):
        return False

    def teardown(self):
        heap = self.heap
        self.heap = None
        while heap:
            handle = heap.pop()
            self._teardown_handle(handle)
        self._active = None
        self._child = None
        self._garbage = 0
        self.per_simulate_callbacks = None
        self.debugger = None
        self.now = None

    def simulate(self, until, max_elements=MAX_ELEMENTS, max_time_ms=None):
        if until < self.future:
            logger.error('Simulating past time. until: {}, future: {}', until, self.future)
            return True
        else:
            count = 0
            self.future = until
            self.per_simulate_callbacks()
            if max_time_ms is not None:
                start_time = time.monotonic()
                end_time = start_time + max_time_ms/1000
            else:
                end_time = None
            if False or paths.AUTOMATION_MODE:
                SimDebtSimulator.try_simulate_sim_debt()
            early_exit = False
            while self.heap and self.heap[0].when <= until:
                count += 1
                handle = heapq.heappop(self.heap)
                if handle.element is None:
                    self._garbage -= 1
                else:
                    (when, _, _t, _s, e) = handle
                    if self.now != when:
                        self.now = when
                        self.on_time_advanced()
                    calling = True
                    result = None
                    try:
                        while e is not None:
                            handle._set_when(None)
                            handle._set_scheduled(False)
                            self._active = (e, handle)
                            try:
                                if calling:
                                    result = e._run(self)
                                else:
                                    result = e._resume(self, result)
                                if self._pending_hard_stop:
                                    raise HardStopError('Hard stop exception was consumed by {}'.format(e))
                            except BaseException as exc:
                                self._pending_hard_stop = False
                                self._active = None
                                try:
                                    if not isinstance(exc, HardStopError):
                                        self._report_exception(e, exc, 'Exception {} Element'.format('running' if calling else 'resuming'))
                                finally:
                                    if e._parent_handle is not None:
                                        self.hard_stop(e._parent_handle)
                            if inspect.isgenerator(result):
                                raise RuntimeError('Element {} returned a generator {}'.format(e, result))
                            if self._active is None:
                                break
                            if self._child is not None:
                                handle = self._child
                                self._child = None
                                e = handle.element
                                calling = True
                                count += 1
                            else:
                                if handle.is_scheduled:
                                    break
                                e._element_handle = None
                                handle = e._parent_handle
                                e._parent_handle = None
                                if handle is None:
                                    e._teardown()
                                    break
                                child = e
                                e = handle.element
                                will_reschedule = e._child_returned(child)
                                if not will_reschedule:
                                    child._teardown()
                                del child
                                calling = False
                    finally:
                        self._active = None
                        self._child = None
                    if count >= max_elements:
                        early_exit = True
                        break
                    if end_time is not None and time.monotonic() > end_time:
                        early_exit = True
                        break
            if self._garbage > ACCEPTABLE_GARBAGE and self._garbage > len(self.heap)*MAX_GARBAGE_FACTOR:
                self._clear_garbage()
            if not early_exit:
                if self.now != until:
                    self.now = until
                    self.on_time_advanced()
                return True
        return False

    def schedule(self, element, when=None):
        return self._schedule(element, when)

    def schedule_asap(self, element):
        return self._schedule(element, when=None, asap=True)

    def _schedule(self, element, when=None, asap=False):
        self._ix += 1
        ix = self._ix
        if asap:
            ix = -ix
        if when is None:
            when = self.now
        elif when < self.now:
            logger.error('Scheduling element {} in the past.  Now: {} Element Time: {}', element, self.now, when)
        if self._active is not None and self._active[0] is element:
            handle = self._active[1]
            handle._assign(when, ix, self, True, element)
        else:
            handle = ElementHandle(when, ix, self, True, element)
            element._element_handle = handle
        heapq.heappush(self.heap, handle)
        return handle

    def run_child(self, element):
        parent = self._active[0]
        if self._pending_hard_stop:
            raise HardStopError('Attempting to run a child element {} while a hard stop is pending for {}'.format(element, parent))
        self._ix = self._ix + 1
        handle = ElementHandle(None, self._ix, self, True, element)
        element._element_handle = handle
        parent._child_scheduled(self, handle)
        self._child = handle
        return handle

    def schedule_child(self, element, when):
        parent = self._active[0]
        if self._pending_hard_stop:
            raise HardStopError('Attempting to schedule a child element {} while a hard stop is pending for {}'.format(element, parent))
        self._ix += 1
        handle = ElementHandle(when, self._ix, self, True, element)
        element._element_handle = handle
        parent._child_scheduled(self, handle)
        heapq.heappush(self.heap, handle)
        return handle

    def reschedule(self, handle, when):
        if self._pending_hard_stop:
            raise HardStopError('Attempting to reschedule the active element {} while a hard stop is pending'.format(handle.element))
        if handle.when == when:
            return
        index = self.heap.index(handle)
        dummy = ElementHandle(handle.when, handle.ix, self, False, None)
        self.heap[index] = dummy
        self._garbage += 1
        self._ix += 1
        handle._set_when(when)
        handle._set_ix(self._ix)
        heapq.heappush(self.heap, handle)

    def soft_stop(self, handle):
        visited = {}
        pending = [handle]
        while pending:
            handle = pending.pop(-1)
            element = handle.element
            if not element is None:
                if id(element) in visited:
                    pass
                else:
                    visited[id(element)] = element
                    if not element._soft_stop():
                        pending.extend(element._get_child_handles())

    def hard_stop(self, handle):
        element = handle.element
        if element is None:
            if not handle.canceled:
                handle._clear_element()
            return
        self._stop_element_tree(handle)

    def get_sub_timeline(self):
        sub_timeline = Timeline(self.now, exception_reporter=self._exception_reporter)
        return sub_timeline

    def get_current_element(self):
        if self._active is not None:
            return self._active[0]

    def filter_handles(self, predicate):
        old_heap = self.heap
        new_heap = []
        while old_heap:
            handle = old_heap[0]
            if handle.element is None:
                heapq.heappop(old_heap)
            elif not predicate(handle):
                self.hard_stop(handle)
            else:
                heapq.heappop(old_heap)
                new_heap.append(handle)
        heapq.heapify(new_heap)
        self.heap = new_heap
        self._garbage = 0

    def _teardown_handle(self, handle):
        handles = self._collect_element_tree(handle)
        elements = [handle.element for handle in handles]
        for handle in handles:
            handle._clear_element()
        for element in elements:
            try:
                element._teardown()
            except BaseException as exc:
                self._report_exception(element, exc, 'Exception during element teardown.')
            finally:
                element._element_handle = None

    def _stop_element_tree(self, handle):
        to_stop_handles = self._collect_element_tree(handle)
        if self._active is not None:
            active_handle = self._active[1]
            for handle in to_stop_handles:
                if handle is active_handle:
                    self._pending_hard_stop = True
                    raise HardStopError('Attempting to stop active handle to element {}'.format(handle.element))
        elements = [handle.element for handle in to_stop_handles]
        for handle in to_stop_handles:
            handle._clear_element()
        self._garbage += len(to_stop_handles)
        for element in elements:
            if not self._active[1] is element._element_handle:
                if self._active[0] is element:
                    self._active = None
            self._active = None
        exceptions = []
        for element in elements:
            try:
                element._hard_stop()
            except BaseException as exc:
                exceptions.append(exc)
            finally:
                element._element_handle = None
        for exc in exceptions:
            if not isinstance(exc, HardStopError):
                self._report_exception(element, exc, 'Exception hard-stopping element')

    def _collect_element_tree(self, handle):
        root = handle
        while root.element is not None and root.element._parent_handle is not None:
            root = root.element._parent_handle
        visited = {}
        pending = [root]
        all_handles = []
        while pending:
            handle = pending.pop(-1)
            element = handle.element
            if not element is None:
                if id(element) in visited:
                    pass
                else:
                    visited[id(element)] = element
                    all_handles.append(handle)
                    pending.extend(element._get_child_handles())
        return list(reversed(all_handles))

    def _mark_scheduled(self, element):
        element_handle = self._active[1]
        element_handle._set_scheduled(True)

    def _clear_garbage(self):
        old_queue = self.heap
        self.heap = [handle for handle in old_queue if handle.element is not None]
        heapq.heapify(self.heap)
        self._garbage = 0

    def _report_exception(self, element, exception, message):
        if self._exception_reporter is not None:
            self._exception_reporter(self, element, exception, message)

class ElementHandle(list):
    __slots__ = ()

    def __init__(self, when:'Optional[int]', ix:'int', timeline:'Timeline', scheduled:'bool', element:'Optional[Element]') -> 'None':
        super().__init__((when, ix, timeline, scheduled, element))

    when = property(operator.itemgetter(0), doc='When the Element is scheduled.  None if not in the Timeline.')
    ix = property(operator.itemgetter(1), doc='"A unique serial number for this handle.')
    timeline = property(operator.itemgetter(2), doc='The Timeline on which this handle is scheduled.')
    is_scheduled = property(operator.itemgetter(3), doc='True if the handle is scheduled in the Timeline.')

    @property
    def is_active(self):
        timeline = self[2]
        if timeline is not None and timeline._active is not None:
            return timeline._active[1] is self
        return False

    @property
    def element(self):
        if len(self) == 5:
            return self[4]

    @property
    def canceled(self):
        return len(self) < 5

    def trigger_hard_stop(self):
        if self.timeline is not None:
            self.timeline.hard_stop(self)

    def _assign(self, when, ix, timeline, scheduled, element):
        self[0] = when
        self[1] = ix
        self[2] = timeline
        self[3] = scheduled
        self[4] = element

    def _set_when(self, when):
        self[0] = when

    def _set_ix(self, ix):
        self[1] = ix

    def _set_scheduled(self, scheduled):
        self[3] = scheduled

    def _clear_element(self):
        self[3] = False
        del self[4]
