from sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableReference, TunableTuple, Tunableimport enumimport servicesimport sims4from traits.traits import Traitfrom typing import *
class RelationshipExpectationType(enum.Int):
    PHYSICAL = 0
    EMOTIONAL = 1
    OPEN_TO_CHANGE = 2
    WOOHOO = 3

class RelationshipExpectationsTuning:
    RELATIONSHIP_EXPECTATIONS = TunableMapping(description='\n        A mapping between the Relationship Expectation Type, Relationship Expectation Status and the corresponding \n        traits and weights for easy lookup.\n        ', key_type=TunableEnumEntry(description='\n            The Relationship Expectation Type to index the Relationship Expectation Status to.\n            ', tunable_type=RelationshipExpectationType, default=RelationshipExpectationType.PHYSICAL), value_type=TunableTuple(description='\n            A tuple of the corresponding trait and random weighted choice for generated sims, via sim\n            template, to exist with the corresponding trait.\n            ', yes_trait=TunableReference(description='\n                Reference to the trait that denotes that the Sim has this Relationship Expectation Type and Status.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), no_trait=TunableReference(description='\n                Reference to the trait that denotes that the Sim has this Relationship Expectation Type and Status.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), yes_trait_generation_chance=Tunable(description='\n                The chance to denote the percentage of generated sims, via sim template, we want to exist with the \n                yes trait.\n                ', tunable_type=int, default=100)))

    @classmethod
    def get_relationship_expectations_traits(cls) -> List[Trait]:
        relationship_expectations_traits = []
        for (relationship_expectation_type, relationship_expectation_type_mapping) in cls.RELATIONSHIP_EXPECTATIONS.items():
            relationship_expectations_traits.append(relationship_expectation_type_mapping.yes_trait)
            relationship_expectations_traits.append(relationship_expectation_type_mapping.no_trait)
        return relationship_expectations_traits

    @classmethod
    def get_relationship_expectation_outlook_for_trait(cls, relationship_expectation_trait:Trait) -> Optional[bool]:
        for (relationship_expectation_type, relationship_expectation_type_mapping) in cls.RELATIONSHIP_EXPECTATIONS.items():
            if relationship_expectation_trait is relationship_expectation_type_mapping.yes_trait:
                return True
            if relationship_expectation_trait is relationship_expectation_type_mapping.no_trait:
                return False

    @classmethod
    def get_relationship_expectation_trait_by_type_and_outlook(cls, relationship_expectation_type:RelationshipExpectationType, relationship_expectation_outlook:bool) -> Optional[Trait]:
        relationship_expectation_type_mapping = cls.RELATIONSHIP_EXPECTATIONS.get(relationship_expectation_type)
        if relationship_expectation_type_mapping is None:
            return
        if relationship_expectation_outlook:
            return relationship_expectation_type_mapping.yes_trait
        else:
            return relationship_expectation_type_mapping.no_trait
