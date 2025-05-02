from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.object_manager import GameObjectManagerMixin
    from objects.game_object import GameObjectfrom sims4.tuning.tunable import AutoFactoryInit, TunableVariant, TunableList, TunableReference, TunableEnumEntry, TunableSet, HasTunableSingletonFactoryimport servicesimport tagOBJECT_DEFINITION_FILTER = 0OBJECT_TAG_FILTER = 1OBJECT_ID_SPECIFIED = 2
class TunableObjectFilter(HasTunableSingletonFactory, AutoFactoryInit):

    def get_filter_type(self):
        raise NotImplementedError

    def _intersect_similar(self, other):
        raise NotImplementedError

    def _intersect_dissimilar(self, other):
        raise NotImplementedError

    def matches(self, obj):
        raise NotImplementedError

    def get_objects_that_match(self, manager:'GameObjectManagerMixin') -> 'Set[GameObject]':
        raise NotImplementedError

    def intersect(self, other):
        if self.get_filter_type() == other.get_filter_type():
            return self._intersect_similar(other)
        return self._intersect_dissimilar(other)

    @staticmethod
    def intersect_definitions_with_flags(definitions, tags):
        intersected_items = []
        for definition in definitions:
            for tag in tags:
                if definition.has_build_buy_tag(tag):
                    intersected_items.append(definition)
                    break
        return intersected_items

class ObjectDefinitionsFilter(TunableObjectFilter):
    FACTORY_TUNABLES = {'items_to_check': TunableList(description='\n             A List of the definitions that can be matched to fulfill the filter.\n             This list is considered a Match Any requirement.\n             ', tunable=TunableReference(description='\n                 A reference to a definiton that can be matched as part of the \n                 filter.\n                 ', manager=services.definition_manager()))}

    def get_filter_type(self):
        return OBJECT_DEFINITION_FILTER

    def get_item_set(self):
        return set(self.items_to_check)

    def _intersect_similar(self, other):
        return ObjectDefinitionsFilter(items_to_check=self.get_item_set().intersection(other.get_item_set()))

    def _intersect_dissimilar(self, other):
        new_set = self.intersect_definitions_with_flags(self.items_to_check, other.tag_set)
        return ObjectDefinitionsFilter(items_to_check=new_set)

    def matches(self, obj):
        return obj.definition in self.items_to_check

    def get_objects_that_match(self, manager):
        results = set()
        for obj in manager.values():
            if self.matches(obj):
                results.add(obj)
        return results

class ObjectTagsFilter(TunableObjectFilter):
    FACTORY_TUNABLES = {'tag_set': TunableSet(description='\n            A Set of tags that can be matched to fulfill the filter. The set\n            is considered a Match Any requirement.\n            ', tunable=TunableEnumEntry(description='\n                A reference to a tag that can be matched as part of the filter.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID))}

    def get_filter_type(self):
        return OBJECT_TAG_FILTER

    def get_item_set(self):
        return self.tag_set

    def _intersect_similar(self, other):
        return ObjectTagsFilter(tag_set=self.get_item_set().intersection(other.get_item_set()))

    def _intersect_dissimilar(self, other):
        new_set = self.intersect_definitions_with_flags(other.items_to_check, self.tag_set)
        return ObjectDefinitionsFilter(items_to_check=new_set)

    def matches(self, obj:'GameObject') -> 'bool':
        return obj.has_any_tag(self.tag_set)

    def get_objects_that_match(self, manager):
        return manager.get_objects_matching_tags(self.tag_set, match_any=True)

class SpecificObjectFilter(TunableObjectFilter):
    FACTORY_TUNABLES = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.object = None

    def get_item_set(self):
        return {self.object}

    def get_filter_type(self):
        return OBJECT_ID_SPECIFIED

    def _intersect_similar(self, other):
        return other.matches(self.object)

    def _intersect_dissimilar(self, other):
        return self._intersect_similar(other)

    def matches(self, obj):
        return obj == self.object

    def get_objects_that_match(self, manager:'GameObjectManagerMixin') -> 'Set[GameObject]':
        results = set()
        if self.object is not None and self.object in manager.values():
            results.add(self.object)
        return results

class ObjectDefinitonsOrTagsVariant(TunableVariant):
    __slots__ = ()

    def __init__(self, **kwargs):
        super().__init__(object_definitions=ObjectDefinitionsFilter.TunableFactory(), object_tags=ObjectTagsFilter.TunableFactory(), default='object_tags', **kwargs)

class SituationObjectDefinitionsVariant(TunableVariant):
    __slots__ = ()

    def __init__(self, **kwargs):
        super().__init__(object_definitions=ObjectDefinitionsFilter.TunableFactory(), object_tags=ObjectTagsFilter.TunableFactory(), object_id_from_situation=SpecificObjectFilter.TunableFactory(), default='object_tags', **kwargs)
