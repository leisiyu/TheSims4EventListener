from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.context import InteractionContext
    from objects.game_object import GameObjectfrom event_testing.resolver import InteractionResolverfrom filters.tunable import FilterResultfrom interactions.base.picker_interaction import SimPickerInteraction, AutonomousSimPickerSuperInteraction, ObjectPickerInteractionfrom sims4.tuning.tunable import TunableList, TunableVariant, TunableReference, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom situations.complex.object_bound_situation_mixin import ObjectBoundSituationMixinfrom situations.situation_by_definition_or_tags import SituationSearchByDefinitionOrTagsVariantfrom vet.vet_clinic_handlers import log_vet_flow_entryfrom vet.vet_clinic_utils import get_vet_clinic_zone_directorimport servicesimport sims4logger = sims4.log.Logger('Situation Picker Interaction Tuning', default_owner='myakubek')
class SituationSimsPickerMixin:
    INSTANCE_TUNABLES = {'valid_situations': SituationSearchByDefinitionOrTagsVariant(description='\n            Situations where the guest list will be collected to populate the picker.\n            ', tuning_group=GroupNames.PICKERTUNING), 'job_filter': TunableList(description='\n            If provided, only looks for Sims with the specified jobs.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), pack_safe=True), tuning_group=GroupNames.PICKERTUNING)}
    REMOVE_INSTANCE_TUNABLES = ('sim_filter', 'sim_filter_household_override', 'sim_filter_requesting_sim', 'include_uninstantiated_sims', 'include_instantiated_sims', 'include_actor_sim', 'include_target_sim')

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for situation in cls.valid_situations.get_all_matching_situations():
            for sim in situation.all_sims_in_situation_gen():
                if not cls.job_filter or situation.get_current_job_for_sim(sim) not in cls.job_filter:
                    pass
                else:
                    target_id = target.sim_id if target.is_sim else target.id
                    if not sim is not None or not target is not None or services.relationship_service().is_hidden(sim.sim_id, target_id):
                        pass
                    elif inst_or_cls.sim_tests:
                        if inst:
                            interaction_parameters = inst.interaction_parameters.copy()
                        else:
                            interaction_parameters = kwargs.copy()
                        interaction_parameters['picked_item_ids'] = {sim.sim_id}
                        resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                        if inst_or_cls.sim_tests.run_tests(resolver):
                            yield FilterResult(sim_info=sim.sim_info)
                            yield FilterResult(sim_info=sim.sim_info)
                    else:
                        yield FilterResult(sim_info=sim.sim_info)

class SituationSimsPickerInteraction(SituationSimsPickerMixin, SimPickerInteraction):
    pass

class AutonomousSituationSimsPickerInteraction(SituationSimsPickerMixin, AutonomousSimPickerSuperInteraction):

    class _SimPickerStrategy(HasTunableSingletonFactory, AutoFactoryInit):

        def __call__(self, interaction, valid_sim_filter_results):
            return interaction.find_best_sim_id_base(valid_sim_filter_results)

    class _VetCustomerStrategy(HasTunableSingletonFactory, AutoFactoryInit):

        def __call__(self, interaction, valid_sim_filter_results):
            sim = interaction.sim
            actor_id = sim.sim_id
            vet_clinic_zone_director = get_vet_clinic_zone_director()
            if vet_clinic_zone_director is None:
                return
            waiting_sim_infos = tuple(result.sim_info for result in valid_sim_filter_results)
            for pet in vet_clinic_zone_director.waiting_sims_gen(actor_id):
                if pet.sim_info in waiting_sim_infos:
                    log_vet_flow_entry(repr(sim), type(interaction).__name__, '{} chose {}'.format(repr(interaction), repr(pet.sim_info)))
                    vet_clinic_zone_director.reserve_waiting_sim(pet.sim_id, actor_id)
                    return pet.sim_id

    INSTANCE_TUNABLES = {'choice_strategy': TunableVariant(description='\n            Strategy to use for picking a Sim.\n            ', default='default_sim_picker', default_sim_picker=_SimPickerStrategy.TunableFactory(), vet_customer_picker=_VetCustomerStrategy.TunableFactory(), tuning_group=GroupNames.PICKERTUNING)}
    REMOVE_INSTANCE_TUNABLES = ('test_compatibility',)

    def find_best_sim_id(self, valid_sim_filter_results):
        return self.choice_strategy(self, valid_sim_filter_results)

class SituationBoundObjectPickerMixin:
    INSTANCE_TUNABLES = {'valid_situations': SituationSearchByDefinitionOrTagsVariant(description='\n            Situations to pull bound objects from for the picker.\n            ', tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_objects_gen(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'Generator[GameObject]':
        for situation in cls.valid_situations.get_all_matching_situations():
            try:
                if situation.bound_object_id is not None:
                    yield services.object_manager().get(situation.bound_object_id)
            except AttributeError:
                logger.error('Tuning Error: Situation {} does not have bound object for Situation Bound Object Picker to use.', situation, owner='myakubek')
                yield None

class SituationBoundObjectPickerInteraction(SituationBoundObjectPickerMixin, ObjectPickerInteraction):

    def _get_fallback_object(cls, inst, target:'GameObject', context:'InteractionContext', **kwargs) -> 'Optional[GameObject]':
        pass
