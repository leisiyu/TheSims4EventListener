import enum
class ProfileType(enum.Int, export=False):
    WORLD_NPC = 0
    GENERATED_NPC = 1
    GALLERY_NPC = 2
