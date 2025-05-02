from protocolbuffers.ResourceKey_pb2 import ResourceKeyimport sims4import string
class RelationshipLabelData:
    __slots__ = ('_label', '_icon')

    def __init__(self):
        self._label = None
        self._icon = None

    @property
    def label(self) -> string:
        return self._label

    @property
    def icon(self) -> ResourceKey:
        return self._icon

    def set_data(self, label, icon) -> None:
        if label is '':
            label = None
        self._label = label
        self._icon = icon

    def destroy(self) -> None:
        self._label = None
        self._icon = None

    def save_data(self, relationship_label_data_msg) -> None:
        if self.icon is not None:
            relationship_label_data_msg.label = self.label
            relationship_label_data_msg.icon = sims4.resources.get_protobuff_for_key(self.icon)

    def load_data(self, relationship_label_data_msg) -> None:
        self.set_data(relationship_label_data_msg.label, relationship_label_data_msg.icon)
