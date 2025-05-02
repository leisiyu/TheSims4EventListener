import servicesimport sims4from objects.object_factories import ObjectTypeFactory, ObjectTagFactory, TagTestTypefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableReference, TunableVariant, TunableRange, TunableMapping, OptionalTunablefrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classpropertyfrom traits.preference_enums import PreferenceSubjectfrom traits.preference_tuning import PreferenceTuninglogger = sims4.log.Logger('CasPreferenceItem', default_owner='spark')
class CasPreferenceItem(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.CAS_PREFERENCE_ITEM)):
    INSTANCE_TUNABLES = {'cas_preference_category': TunableReference(description='\n            The category this Preference Item belongs to. (E.g. if the Preference\n            Item contains: Trait-Likes-Pink and Trait-Dislikes-Pink, then the category\n            would be Preference-Category-Color.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAS_PREFERENCE_CATEGORY), export_modes=ExportModes.All), 'like': TunableReference(description='\n            The like-trait for this Preference Item.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), export_modes=ExportModes.All), 'dislike': TunableReference(description='\n            The dislike-trait for this Preference Item.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), export_modes=ExportModes.All), 'tooltip': OptionalTunable(description='\n            If enabled, the tooltip description text for this item in the CAS Preferences\n            Panel.\n            ', tunable=TunableLocalizedString(), export_modes=ExportModes.All)}

    @classmethod
    def _verify_tuning_callback(cls):
        services.get_instance_manager(sims4.resources.Types.CAS_PREFERENCE_ITEM).add_on_load_complete(cls._verify_on_all_items_loaded)

    @classmethod
    def _verify_on_all_items_loaded(cls, manager):
        for item in manager.types.values():
            group = PreferenceTuning.try_get_preference_group_for_preference_item(item)
            if group is None:
                logger.error('Preference Item {} is not in any group! This is not allowed.', item)

    @classproperty
    def preference_subject(self):
        raise NotImplementedError

    def target_is_preferred(self, target):
        raise NotImplementedError

    @classmethod
    def get_any_tags(cls):
        pass

class ObjectPreferenceItem(CasPreferenceItem):
    INSTANCE_TUNABLES = {'object_item_def': TunableVariant(definition_id=ObjectTypeFactory.TunableFactory(), tags=ObjectTagFactory.TunableFactory(), default='tags')}

    @classproperty
    def preference_subject(self):
        return PreferenceSubject.OBJECT

    def target_is_preferred(self, target):
        return self.object_item_def(target)

    @classmethod
    def get_any_tags(cls):
        if hasattr(cls.object_item_def, 'tag_set'):
            if cls.object_item_def.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
                return cls.object_item_def.tag_set
            logger.error('You are trying to get tags from preference {} without using type CONTAINS_ANY_TAG_IN_SET', cls, owner='mbilello')

class StylePreferenceItem(CasPreferenceItem):
    INSTANCE_TUNABLES = {'style_tags': ObjectTagFactory.TunableFactory(description='\n            Validate the tags of the style of the target object against.\n            Style tags can be found in the catalog here: Styles-> Object\n             Styles-> Tags.\n            ')}

    @classproperty
    def preference_subject(self):
        return PreferenceSubject.DECOR

    def target_is_preferred(self, target):
        for style_tag in self.style_tags:
            if style_tag in target.get_style_tags():
                return True
        return False

    @classmethod
    def get_any_tags(cls):
        if cls.style_tags.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
            return cls.style_tags.tag_set
        logger.error('You are trying to get tags from preference {} without using type CONTAINS_ANY_TAG_IN_SET', cls, owner='mbilello')

class CharacteristicPreferenceItem(CasPreferenceItem):
    INSTANCE_TUNABLES = {'trait_map': TunableMapping(description='\n            A mapping of the desired traits associated with this PreferenceItem, and \n            the corresponding scores. \n            ', key_type=TunableReference(description='\n                The desired trait.  This could be a standard trait, an activity \n                like/dislike trait, or a lifestyle trait.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=TunableRange(description="\n                The score associated with this trait.  If there's a match, this value\n                gets added to the overall compatibility score.\n                ", tunable_type=float, default=1.0))}

    @classproperty
    def preference_subject(self):
        return PreferenceSubject.CHARACTERISTIC

    def target_is_preferred(self, target):
        return False

class AttractionPreferenceItem(CharacteristicPreferenceItem):
    pass

class ConversationPreferenceItem(CasPreferenceItem):

    @classproperty
    def preference_subject(self):
        return PreferenceSubject.CONVERSATION

    def target_is_preferred(self, target):
        return False
