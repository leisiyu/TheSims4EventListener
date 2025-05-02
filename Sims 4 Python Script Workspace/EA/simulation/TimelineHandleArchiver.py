from __future__ import annotationsimport tracebackfrom sims4.gsi.archive import BaseArchiverfrom sims4.log import Loggerfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from date_and_time import DateAndTime
    from scheduling import ElementHandle, Timeline
    from typing import *logger = Logger('TimelineGSI', default_owner='mjuskelis')
class TimelineHandleSnapshot:
    __slots__ = ('id', 'when', 'is_scheduled', 'element_snapshot', 'call_stack', 'parent_snapshot', 'child_snapshots')

    def __init__(self, handle:'ElementHandle', archive:'TimelineHandleArchive') -> 'None':
        self.id = handle.ix
        self.when = handle.when
        self.is_scheduled = handle.is_scheduled
        self.element_snapshot = repr(handle.element)
        stack = []
        for line in traceback.format_stack():
            stack.append(line.strip())
        stack.reverse()
        self.call_stack = '\n'.join(stack)
        self.parent_snapshot = None
        self.child_snapshots = []
        if handle.element is not None and handle.element._parent_handle is not None:
            parent_id = archive.get_handle_id(handle.element._parent_handle)
            if parent_id in archive.id_to_snapshot_archive:
                self.parent_snapshot = archive.id_to_snapshot_archive[parent_id][-1]
                self.parent_snapshot.child_snapshots.append(self)
            elif timeline_archiver.missing_data:
                logger.warn('Child snapshot {} missing parent snapshot. Skipping parent data.', self.id)
            else:
                logger.error('Added child snapshot {} before taking any parent snapshots!', self.id)

    def __repr__(self) -> 'str':
        return f'ID: {self.id}
When: {self.when}
Is Scheduled?: {self.is_scheduled}
Element Snapshot: {self.element_snapshot}
Parent ID: {self.parent_snapshot.id if self.parent_snapshot is not None else 'None'}
'

class TimelineHandleArchive:

    def __init__(self) -> 'None':
        self.id_to_snapshot_archive = {}
        self._id_transfers = {}
        self._dummy_ids = []

    def clear_archive(self) -> 'None':
        self.id_to_snapshot_archive.clear()
        self._id_transfers.clear()
        self._dummy_ids.clear()

    @staticmethod
    def get_handle_id(handle:'ElementHandle') -> 'int':
        return handle.ix

    def get_current_id(self, handle_id:'int') -> 'int':
        current_id = handle_id
        while current_id in self._id_transfers:
            current_id = self._id_transfers[current_id]
        return current_id

    def on_handle_created(self, handle:'ElementHandle') -> 'None':
        if not timeline_archiver.enabled:
            return
        handle_id = self.get_handle_id(handle)
        if handle_id in self.id_to_snapshot_archive:
            logger.error('Tried to create handle {} twice!', handle_id)
            return
        self.id_to_snapshot_archive[handle_id] = [TimelineHandleSnapshot(handle, self)]

    def on_dummy_handle_created(self, handle:'ElementHandle') -> 'None':
        if not timeline_archiver.enabled:
            return
        self._dummy_ids.append(self.get_handle_id(handle))

    def on_handle_id_changed(self, original_id:'int', new_id:'int') -> 'None':
        if not timeline_archiver.enabled:
            return
        if original_id in self.id_to_snapshot_archive:
            self._id_transfers[original_id] = new_id
            self.id_to_snapshot_archive[new_id] = list(self.id_to_snapshot_archive[original_id])
            del self.id_to_snapshot_archive[original_id]
        elif timeline_archiver.missing_data:
            logger.warn('Handle {} changed IDs without an existing entry.\nTreating this as a creation event, since the archiver has been disabled.', original_id)
            self._id_transfers[original_id] = new_id
            self.id_to_snapshot_archive[new_id] = list(self.id_to_snapshot_archive[original_id])
        else:
            logger.error('Handle {} was modified without being created first!', original_id)

    def on_handle_modified(self, handle:'ElementHandle') -> 'None':
        if not timeline_archiver.enabled:
            return
        handle_id = self.get_handle_id(handle)
        if handle_id in self.id_to_snapshot_archive:
            self.id_to_snapshot_archive[handle_id].append(TimelineHandleSnapshot(handle, self))
        elif timeline_archiver.missing_data:
            logger.warn('Handle {} was modified without an existing entry.\nTreating this as a creation event, since the archiver has been disabled.', handle_id)
            self.id_to_snapshot_archive[handle_id] = [TimelineHandleSnapshot(handle, self)]
        else:
            logger.error('Handle {} was modified without being created first!', handle_id)

class TimelineHandleArchiver(BaseArchiver):

    def __init__(self) -> 'None':
        super().__init__(type_name='timeline_handle_archiver', custom_enable_fn=self.set_enabled)
        self._archives = {}
        self.missing_data = False

    def clear_archive(self, sim_id:'int'=None) -> 'None':
        logger.warn('Clearing archive data will lead to missing data later on.Use subsequent data with caution and expect a lot of warnings.')
        self.missing_data = True
        for archive in self._archives.values():
            archive.clear_archive()

    def get_archive_for_timeline(self, timeline:'Timeline') -> 'TimelineHandleArchive':
        if timeline not in self._archives:
            self._archives[timeline] = TimelineHandleArchive()
        return self._archives[timeline]

    def set_enabled(self, *args, enable:'bool'=False, **kwargs) -> 'None':
        if enable and self.missing_data:
            logger.warn('Enabling the Timeline Handle Archiver after disabling it could lead to missing data,since we will not have consumed every event. Use archive data with caution and expecta lot of warnings.')
        if not enable:
            self.missing_data = True
timeline_archiver = TimelineHandleArchiver()