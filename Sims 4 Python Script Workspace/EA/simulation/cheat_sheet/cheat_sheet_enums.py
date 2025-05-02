import enum
class CheatSheetMode(enum.IntFlags):
    IN_LIVE_MODE = 0
    IN_BB_MODE = 1
    TS3_CAMERA_ACTIVE = 2
    TS4_CAMERA_ACTIVE = 3
    INVALID = 4294967295
