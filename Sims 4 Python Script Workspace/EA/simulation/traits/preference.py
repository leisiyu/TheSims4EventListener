from sims4.tuning.tunable import TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import constproperty, blueprintproperty, blueprintmethodfrom traits.base_preference import BasePreferencefrom traits.preference_enums import PreferenceSubjectfrom traits.preference_tuning import PreferenceTuningimport sims4.logimport serviceslogger = sims4.log.Logger('Trait', default_owner='micfisher')
class Preference(BasePreference):
    INSTANCE_TUNABLES = {'preference_item': TunableReference(description='\n            The item marked by the preference of the owner.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CAS_PREFERENCE_ITEM), tuning_group=GroupNames.SPECIAL_CASES)}

    @constproperty
    def is_preference_trait():
        return True

    @blueprintproperty
    def preference_category(self):
        return self.preference_item.cas_preference_category

    @blueprintproperty
    def decorator_preference(self):
        if self.disallow_from_decorator_gigs:
            return False
        return self.preference_category in PreferenceTuning.DECORATOR_CAREER_PREFERENCE_CATEGORIES

    @blueprintproperty
    def is_object_preference(self):
        return self.preference_item.preference_subject == PreferenceSubject.OBJECT

    @blueprintmethod
    def is_preference_subject(self, subject):
        return self.preference_item.preference_subject == subject

    @blueprintmethod
    def is_preference_subject_in_subject_set(self, subject_set):
        return self.preference_item.preference_subject in subject_set

    @blueprintmethod
    def _verify_tuning_callback(self):
        super()._verify_tuning_callback()
        if self.decorator_preference:
            preference_item = self.preference_item
            if hasattr(preference_item, 'object_item_def'):
                preference_item_object = preference_item.object_item_def
                if hasattr(preference_item_object, 'tag_set'):
                    tag_set = preference_item_object.tag_set
                    if not tag_set:
                        logger.error('Preference {}: For Decorator Preferences, Object Item Def must be tuned to use tags', self)
                    test_type = preference_item_object.test_type
                    if test_type != test_type.CONTAINS_ANY_TAG_IN_SET:
                        logger.error('Preference {} is set up to use tags, but is not using test type CONTAINS_ANY_TAG_IN_SET', self)
                else:
                    logger.error('Preference {} For Decorator Preferences, Object Item Def be tuned to use tags', self)
