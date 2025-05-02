import enumimport servicesimport sims4from sims.sim_info_types import Age, Gender, SpeciesExtendedfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableList, TunableTuple, Tunable, TunableReferencefrom traits.traits import Traitlogger = sims4.log.Logger('_AdoptionSimData', default_owner='tythompson')
class AdoptionType(enum.Int):
    NONE = 0
    ADOPT_RESCUE = 1
    BUY = 2

class _AdoptionSimData(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def _verify_tunable_trait_callback(instance_class, tunable_name, source, weight, trait):
        if not trait.is_personality_trait:
            logger.error('{} is not a personality trait. Only personality traits should be entered in {}.', trait, source)

    FACTORY_TUNABLES = {'age': TunableEnumEntry(description="\n            The adopted Sim's age.\n            ", tunable_type=Age, default=Age.BABY), 'gender': TunableEnumEntry(description="\n            The adopted Sim's gender.\n            ", tunable_type=Gender, default=Gender.FEMALE), 'species': TunableEnumEntry(description="\n            The adopted Sim's species.\n            ", tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,)), 'traits': TunableList(description="\n            The adopted Sim's possible traits based on the tuned weights.\n            ", tunable=TunableTuple(description='\n                A weighted trait that might be applied to the adopted Sim.\n                ', weight=Tunable(description='\n                    The relative weight of this trait.\n                    ', tunable_type=float, default=1), trait=TunableReference(description='\n                    A trait that might be applied to the adopted Sim.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), class_restrictions=('Trait',), pack_safe=True), verify_tunable_callback=_verify_tunable_trait_callback)), 'adoption_type': TunableEnumEntry(description='\n            The type of adoption this Sim will be considered for.\n            ', tunable_type=AdoptionType, default=AdoptionType.ADOPT_RESCUE)}
