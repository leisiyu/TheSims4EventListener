import servicesimport sims4from sims4.tuning.tunable import TunableReference
class OccultTuning:
    NO_OCCULT_TRAIT = TunableReference(description='\n        The trait that indicates a sim has no occult type.\n        ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',))
