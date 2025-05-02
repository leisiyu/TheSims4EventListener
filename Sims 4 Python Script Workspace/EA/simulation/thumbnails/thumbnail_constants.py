from objects.components.canvas_component_enums import *
def memorial_dedication_to_char(dedication_type:DedicationType) -> str:
    if dedication_type is DedicationType.UNDEDICATED:
        return 'u'
    if dedication_type is DedicationType.HUMAN:
        return 'm'
    if dedication_type is DedicationType.FAMILY:
        return 'f'
    if dedication_type is DedicationType.DOG:
        return 'l'
    if dedication_type is DedicationType.CAT:
        return 'x'
    if dedication_type is DedicationType.HORSE:
        return 'h'
    elif dedication_type is DedicationType.OTHER:
        return 'r'
    return 'r'
MEMORIAL_SINGLE_SIM_URL = 'img://thumbs/sims/a_0x{:016x}_l_{}'MEMORIAL_GENERIC_SIM_URL = 'img://thumbs/sims/a_mem_{}'FAMILY_PORTRAIT_URL = 'img://thumbs/sims/h_0x{:016x}_x_{:d}'AUTOGRAPH_PORTRAIT_URL = 'img://thumbs/sims/b_0x{:016x}_x_{:d}'UNIVERSITY_GRADUATION_URL = 'img://thumbs/sims/d_0x{:016x}_x_{:s}'HS_GRADUATION_URL = 'img://thumbs/sims/d_0x{:016x}_x_h'PHOTOBOOTH_BASE_URL = 'img://thumbs/sims/multi/p_{}_'