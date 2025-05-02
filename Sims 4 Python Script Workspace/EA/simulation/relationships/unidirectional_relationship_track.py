from __future__ import annotationsfrom relationships.relationship_enums import RelationshipTrackTypefrom relationships.relationship_track import RelationshipTrackfrom sims4.utils import classpropertyfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from protocolbuffers import Commodities_pb2
class UnidirectionalRelationshipTrack(RelationshipTrack):

    @classproperty
    def track_type(cls) -> 'RelationshipTrackType':
        return RelationshipTrackType.UNIDIRECTIONAL

    def build_single_relationship_track_proto(self, relationship_track_update:'Commodities_pb2.RelationshipTrack') -> 'None':
        super().build_single_relationship_track_proto(relationship_track_update)
        relationship_track_update.track_type = RelationshipTrackType.UNIDIRECTIONAL
