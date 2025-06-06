import enumimport sims4.reloadwith sims4.reload.protected(globals()):
    _log_arb_contents = FalseAUTO_EXIT_REF_TAG = 'auto_exit'MAX_ZERO_LENGTH_ASM_CALLS_FOR_RESET = 50ASM_INITIAL_TRANSLATION = 'InitialTranslation'ASM_INITIAL_ORIENTATION = 'InitialOrientation'ASM_TARGET_TRANSLATION = 'TargetTranslation'ASM_TARGET_ORIENTATION = 'TargetOrientation'ASM_SCRIPT_EVENT_ID = 'scriptEventID'ASM_SCRIPT_EVENT_PLACEMENT = 'scriptEventPlacement'ASM_LANDING_SURFACE = 'LandingSurface'ASM_THROW_ANGLE = 'ThrowAngle'ASM_HIT_ANGLE = 'hitAngle'ASM_LADDER_PORTAL_ALIGNMENT = 'ladderPortal'ASM_LADDER_PORTAL_ALIGNMENT_FRONT = 'front'ASM_LADDER_PORTAL_ALIGNMENT_LEFT = 'left'ASM_LADDER_PORTAL_ALIGNMENT_RIGHT = 'right'
class ActorType(enum.Int, export=False):
    Sim = int(149264255)
    Object = int(200706046)
    Door = int(2935391323)
    ProceduralObject = int(1054400919)
    Creature = int(2661483290)

class CreatureType(enum.Int):
    Invalid = 0
    Rabbit = int(2689485353)
    Hen = int(915067390)
    Chick = int(4176957319)
    Rooster = int(3987889111)
    Cow = int(1083682102)
    Llama = int(2978855956)
    Goat = int(567967128)
    Sheep = int(2935967122)
    Crow = int(4237424144)

class InteractionAsmType(enum.IntFlags, export=False):
    Unknown = 0
    Interaction = 1
    Outcome = 2
    Response = 4
    Reactionlet = 8
    Canonical = 16

class ProceduralControlType(enum.Int, export=False):
    UNKNOWN = 0
    WHEEL = 1
    SPHERE_WHEEL = 2
    SKATE = 3
    LIP_SYNC = 4
