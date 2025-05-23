import enum
class RelationshipBitCullingPrevention(enum.Int):
    ALLOW_ALL = ...
    PLAYED_ONLY = ...
    PLAYED_AND_UNPLAYED = ...

class RelationshipDecayMetricKeys(enum.Int, export=False):
    RELS = ...
    RELS_WITH_DECAY = ...
    LONG_TERM_TRACKS = ...
    LONG_TERM_TRACKS_DECAYING = ...
    LONG_TERM_TRACKS_AT_CONVERGENCE = ...
    SHORT_TERM_TRACKS = ...
    SHORT_TERM_TRACKS_DECAYING = ...
    SHORT_TERM_TRACKS_AT_CONVERGENCE = ...

class RelationshipDirection(enum.Int):
    BIDIRECTIONAL = 0
    UNIDIRECTIONAL = 1

class SentimentSignType(enum.Int):
    INVALID = 0
    POSITIVE = 1
    NEGATIVE = 2

class SentimentDurationType(enum.Int):
    INVALID = 0
    LONG = 1
    SHORT = 2

class RelationshipTrackType(enum.Int, export=False):
    RELATIONSHIP = 0
    SENTIMENT = 1
    UNIDIRECTIONAL = 2

class RelationshipType(enum.Int):
    NONE = 6
    PARENT = 7
    SIBLING = 8
    SPOUSE = 9
    FIANCE = 10
    STEADY = 11
    DESCENDANT = 12
    GRANDPARENT = 13
    GRANDCHILD = 14
    SIBLINGS_CHILD = 15
    PARENTS_SIBLING = 16
    COUSIN = 17
    STEP_PARENT = 18
    STEP_SIBLING = 19
    STEP_CHILD = 21
    PARENT_IN_LAW = 22
    CHILD_IN_LAW = 23
    SIBLING_IN_LAW = 24
