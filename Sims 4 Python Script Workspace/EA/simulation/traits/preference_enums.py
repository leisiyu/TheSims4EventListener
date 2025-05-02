from traits.trait_type import TraitTypeimport enum
class PreferenceTypes(enum.Int):
    LIKE = TraitType.LIKE
    DISLIKE = TraitType.DISLIKE

class GameplayObjectPreferenceTypes(enum.Int):
    NONE = 0
    UNSURE = 1
    DISLIKE = 2
    LIKE = 3
    LOVE = 4

class PreferenceSubject(enum.Int):
    OBJECT = 0
    DECOR = 1
    CHARACTERISTIC = 2
    CONVERSATION = 3
