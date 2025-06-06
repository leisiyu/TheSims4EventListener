import servicesimport sims4.logfrom buffs.buff_ops import BuffOpfrom interactions.utils.loot_basic_op import BaseTargetedLootOperationfrom interactions.utils.loot_ops import DialogLootOpfrom sims4.tuning.instances import TunedInstanceMetaclass, TuningClassMixinfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableListfrom tag import TunableTaglogger = sims4.log.Logger('AnimalLootOps')
class _AnimalLootOpBase(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, animal_service, subject, target, resolver):
        raise NotImplementedError

class _AssignToHome(_AnimalLootOpBase):

    def __call__(self, animal_serivce, subject, target, resolver):
        if target is None:
            return
        animal_serivce.assign_animal(subject.id, target)

class _UnassignFromHome(_AnimalLootOpBase):

    def __call__(self, animal_serivce, subject, target, resolver):
        animal_serivce.assign_animal(subject.id, None)

class AnimalLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'operation': TunableVariant(description='\n            Animal related operation to perform.\n            ', assign_to_home=_AssignToHome.TunableFactory(), unassign_from_home=_UnassignFromHome.TunableFactory(), default='assign_to_home')}

    def __init__(self, operation, **kwargs):
        super().__init__(**kwargs)
        self.operation = operation

    def _apply_to_subject_and_target(self, subject, target, resolver):
        animal_service = services.animal_service()
        if animal_service is None:
            return
        self.operation(animal_service, subject, target, resolver)

class UpdateAnimalPreferenceKnowledgeLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'tag_to_test': TunableTag(description='\n            The tag that the subject should now have knowledge of\n            ', filter_prefixes=('Func',)), 'should_trigger_cooldown': Tunable(description="\n            Whether or not the op should trigger a cooldown once it's rewarded\n            ", tunable_type=bool, default=True)}

    def __init__(self, tag_to_test, should_trigger_cooldown, **kwargs):
        super().__init__(**kwargs)
        self.tag_to_test = tag_to_test
        self.should_trigger_cooldown = should_trigger_cooldown

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None or target is None:
            logger.error('The subject / target is None, fix in tuning', self)
            return
        if target.is_sim:
            target = target.get_sim_instance()
            if target is None:
                logger.error("Target {} is a sim but couldn't get instance", target)
                return
        household_id = subject.sim_info.household_id
        preference_component = target.animalpreference_component
        if preference_component is None:
            logger.error("Target {} didn't have an AnimalPreferenceComponent", target)
            return
        if not preference_component.test_is_preference_known(subject.household_id, self.tag_to_test):
            preference_component.add_preference_knowledge(household_id, self.tag_to_test)
        if self.should_trigger_cooldown:
            preference_component.trigger_gifting_cooldown(household_id, self.tag_to_test)

class AnimalDeathLootActions(AutoFactoryInit, TuningClassMixin, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ACTION)):
    INSTANCE_TUNABLES = {'loot_actions': TunableList(description='\n            Loots that we can run.\n            ', tunable=TunableVariant(buff=BuffOp.TunableFactory(), notification_and_dialog=DialogLootOp.TunableFactory()))}

    def __iter__(self):
        return iter(self.loot_actions)
