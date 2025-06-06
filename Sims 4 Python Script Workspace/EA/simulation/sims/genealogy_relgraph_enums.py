import enum
class SimRelBitShift(enum.Int, export=False):
    SIMRELEBITSHIFT_MOTHER = 0
    SIMRELEBITSHIFT_FATHER = 1
    SIMRELEBITSHIFT_DAUGHTER = 2
    SIMRELEBITSHIFT_SON = 3
    SIMRELEBITSHIFT_WIFE = 4
    SIMRELEBITSHIFT_HUSBAND = 5
    SIMRELEBITSHIFT_FIANCEE = 6
    SIMRELEBITSHIFT_FIANCE = 7
    SIMRELEBITSHIFT_GIRLFRIEND = 8
    SIMRELEBITSHIFT_BOYFRIEND = 9
    SIMRELEBITSHIFT_MAX = 9
    SIMRELEBITSHIFT_PREEXISTING = 31

class SimRelBitFlags(enum.IntFlags, export=False):
    SIMRELBITFLAG_NONE = 0
    SIMRELBITFLAG_MOTHER = 1 << SimRelBitShift.SIMRELEBITSHIFT_MOTHER
    SIMRELBITFLAG_FATHER = 1 << SimRelBitShift.SIMRELEBITSHIFT_FATHER
    SIMRELBITFLAG_DAUGHTER = 1 << SimRelBitShift.SIMRELEBITSHIFT_DAUGHTER
    SIMRELBITFLAG_SON = 1 << SimRelBitShift.SIMRELEBITSHIFT_SON
    SIMRELBITFLAG_WIFE = 1 << SimRelBitShift.SIMRELEBITSHIFT_WIFE
    SIMRELBITFLAG_HUSBAND = 1 << SimRelBitShift.SIMRELEBITSHIFT_HUSBAND
    SIMRELEBIFLAG_FIANCEE = 1 << SimRelBitShift.SIMRELEBITSHIFT_FIANCEE
    SIMRELEBIFLAG_FIANCE = 1 << SimRelBitShift.SIMRELEBITSHIFT_FIANCE
    SIMRELEBIFLAG_GIRLFRIEND = 1 << SimRelBitShift.SIMRELEBITSHIFT_GIRLFRIEND
    SIMRELEBIFLAG_BOYFRIEND = 1 << SimRelBitShift.SIMRELEBITSHIFT_BOYFRIEND
    SIMRELBITFLAG_PREEXISTING = 1 << SimRelBitShift.SIMRELEBITSHIFT_PREEXISTING
    SIMRELBITS_MALE = SIMRELBITFLAG_FATHER | SIMRELBITFLAG_SON | SIMRELBITFLAG_HUSBAND | SIMRELEBIFLAG_FIANCE | SIMRELEBIFLAG_BOYFRIEND
    SIMRELBITS_FEMALE = SIMRELBITFLAG_MOTHER | SIMRELBITFLAG_DAUGHTER | SIMRELBITFLAG_WIFE | SIMRELEBIFLAG_FIANCEE | SIMRELEBIFLAG_GIRLFRIEND
    SIMRELBITS_CHILD = SIMRELBITFLAG_DAUGHTER | SIMRELBITFLAG_SON
    SIMRELBITS_PARENT = SIMRELBITFLAG_MOTHER | SIMRELBITFLAG_FATHER
    SIMRELBITS_SPOUSE = SIMRELBITFLAG_WIFE | SIMRELBITFLAG_HUSBAND
    SIMRELBITS_FIANCE = SIMRELEBIFLAG_FIANCEE | SIMRELEBIFLAG_FIANCE
    SIMRELBITS_STEADY = SIMRELEBIFLAG_GIRLFRIEND | SIMRELEBIFLAG_BOYFRIEND
    SIMRELBITS_ALL = SIMRELBITS_CHILD | SIMRELBITS_PARENT | SIMRELBITS_SPOUSE | SIMRELBITS_FIANCE | SIMRELBITS_STEADY | SIMRELBITFLAG_PREEXISTING
