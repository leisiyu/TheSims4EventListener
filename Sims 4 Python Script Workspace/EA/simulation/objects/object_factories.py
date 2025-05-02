from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunablePackSafeReference, TunableEnumEntry, TunableSetfrom singletons import EMPTY_SETimport enumimport servicesimport sims4import taglogger = sims4.log.Logger('ObjectFactories', default_owner='mbilello')
class TagTestType(enum.Int):
    CONTAINS_ANY_TAG_IN_SET = 1
    CONTAINS_ALL_TAGS_IN_SET = 2
    CONTAINS_NO_TAGS_IN_SET = 3

class ObjectTypeFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'actual_object': TunablePackSafeReference(description='\n            The object we want to test ownership of\n            ', manager=services.definition_manager())}

    def __call__(self, obj):
        if self.actual_object is None:
            return False
        return obj.definition.id == self.actual_object.id

    def get_all_objects(self, object_manager):
        if self.actual_object is None:
            return EMPTY_SET
        return frozenset(obj for obj in object_manager.values() if obj.definition.id == self.actual_object.id)

class ObjectTagFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tag_set': TunableSet(TunableEnumEntry(description='\n                What tag to test for.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)), 'test_type': TunableEnumEntry(description='\n            How to test the tags in the tag set against the objects on the lot.\n            ', tunable_type=TagTestType, default=TagTestType.CONTAINS_ANY_TAG_IN_SET)}

    def __call__(self, obj):
        if obj.is_sim:
            return False
        if obj.is_terrain:
            return False
        object_tags = set(obj.get_tags())
        if self.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
            return object_tags & self.tag_set
        if self.test_type == TagTestType.CONTAINS_ALL_TAGS_IN_SET:
            return object_tags & self.tag_set == self.tag_set
        if self.test_type == TagTestType.CONTAINS_NO_TAGS_IN_SET:
            return not object_tags & self.tag_set
        logger.error('ObjectTagFactory received unrecognized TagTestType {}, defaulting to False', self.test_type, owner='mbilello')
        return False

    def get_all_objects(self, object_manager):
        objects_matching_any_tag = set()
        if self.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
            for tag in self.tag_set:
                matching_objects = object_manager.get_objects_matching_tags((tag,))
                if matching_objects is None:
                    pass
                else:
                    objects_matching_any_tag.update(matching_objects)
        elif self.test_type == TagTestType.CONTAINS_ALL_TAGS_IN_SET:
            objects_matching_any_tag = object_manager.get_objects_matching_tags(self.tag_set)
            if objects_matching_any_tag is None:
                return EMPTY_SET
        else:
            if self.test_type == TagTestType.CONTAINS_NO_TAGS_IN_SET:
                return set(obj for obj in object_manager.values() if obj.is_sim or not set(obj.get_tags() & self.tag_set))
            logger.error('ObjectTagFactory recieved unrecognized TagTestType {}, defaulting to False', self.test_type, owner='msantander')
        objects_matching_any_tag = set(obj for obj in objects_matching_any_tag if not obj.is_sim)
        return objects_matching_any_tag
