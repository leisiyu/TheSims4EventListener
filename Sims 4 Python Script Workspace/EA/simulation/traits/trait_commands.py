import servicesimport sims4import tagfrom distributor import shared_messagesfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom protocolbuffers import UI_pb2, Consts_pb2from server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParam, RequiredTargetParam, OptionalSimInfoParamfrom sims.relationship_expectations_tuning import RelationshipExpectationTypefrom singletons import DEFAULTfrom statistics.lifestyle_service import LifestyleServicefrom traits.trait_type import TraitTypefrom sims4.utils import create_csvfrom sims4.resources import Types
@sims4.commands.Command('traits.show_traits', command_type=sims4.commands.CommandType.Automation)
def show_traits(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        trait_tracker = sim.sim_info.trait_tracker
        if trait_tracker is None:
            sims4.commands.output("Sim {} doesn't have trait tracker".format(sim), _connection)
            return
        sims4.commands.output('Sim {} has {} traits equipped, {} slots left'.format(sim, len(trait_tracker), trait_tracker.empty_slot_number), _connection)
        sims4.commands.automation_output('TraitsList; Status:Begin', _connection)
        for trait in trait_tracker.equipped_traits:
            s = 'Equipped: {}'.format(trait.__name__)
            sims4.commands.output(s, _connection)
            sims4.commands.automation_output('TraitsList; Status:Data, Trait:{}'.format(trait.__name__), _connection)
        sims4.commands.automation_output('TraitsList; Status:End', _connection)

@sims4.commands.Command('traits.equip_trait', command_type=sims4.commands.CommandType.Live)
def equip_trait(trait_type:TunableInstanceParam(sims4.resources.Types.TRAIT), opt_sim:OptionalTargetParam=None, index_in_personality_list:int=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and services.is_granted_or_non_account_reward_item(trait_type.guid64):
        sim.sim_info.add_trait(trait_type, index_in_personality_list=index_in_personality_list)
        return True
    return False

@sims4.commands.Command('traits.remove_trait', command_type=sims4.commands.CommandType.Live)
def remove_trait(trait_type:TunableInstanceParam(sims4.resources.Types.TRAIT), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sim.sim_info.remove_trait(trait_type)
        return True
    return False

@sims4.commands.Command('traits.clear_traits', command_type=sims4.commands.CommandType.Automation)
def clear_traits(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        trait_tracker = sim.sim_info.trait_tracker
        if trait_tracker is None:
            sims4.commands.output("Sim {} doesn't have trait tracker".format(sim), _connection)
            return False
        else:
            trait_tracker.clear_traits()
            return True
    return False

@sims4.commands.Command('traits.clear_personality_traits', command_type=sims4.commands.CommandType.Live)
def clear_personality_traits(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        trait_tracker = sim.sim_info.trait_tracker
        if trait_tracker is None:
            sims4.commands.output("Sim {} doesn't have trait tracker".format(sim), _connection)
            return False
        else:
            trait_tracker.clear_personality_traits()
            return True
    return False

@sims4.commands.Command('traits.show_inherited_traits')
def show_inherited_traits(sim_a:RequiredTargetParam=None, sim_b:OptionalTargetParam=None, _connection=None):
    sim_a = sim_a.get_target()
    sim_b = get_optional_target(sim_b, _connection)
    output = sims4.commands.Output(_connection)
    if sim_a is None or sim_b is None:
        output('Must specify two valid Sims.')
        return False
    output('Potential inherited traits between {} and {}:'.format(sim_a, sim_b))
    for (index, inherited_trait_entries) in enumerate(sim_a.trait_tracker.get_inherited_traits(sim_b)):
        output('Entry {}:'.format(index))
        total_weight = sum(entry[0] for entry in inherited_trait_entries)
        for inherited_trait_entry in inherited_trait_entries:
            output('    {:24} {:.2%}'.format(inherited_trait_entry[1].__name__, inherited_trait_entry[0]/total_weight if total_weight else 0))
    output('End')
    return True

@sims4.commands.Command('traits.show_traits_of_type')
def show_traits_of_type(trait_type:TraitType, sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(sim, _connection)
    output = sims4.commands.Output(_connection)
    if sim is None:
        output('No valid Sim found. Try specifying a SimID as the second argument.')
        return
    trait_tracker = sim.sim_info.trait_tracker
    if trait_tracker is None:
        output("Sim {} doesn't have trait tracker".format(sim))
        return
    traits = trait_tracker.get_traits_of_type(trait_type)
    if len(traits) == 0:
        output('Sim {} has no traits of type {}.'.format(sim, trait_type))
        return
    for trait in traits:
        output(trait.__name__)

@sims4.commands.Command('lifestyles.generate_dialog.ui', command_type=sims4.commands.CommandType.Live)
def generate_lifestyles_dialog_ui(lifestyle_dialog_id:int, sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    lifestyle_service = services.lifestyle_service()
    dialog = lifestyle_service.LIFESTYLES_DIALOG(sim_info, SingleSimResolver(sim_info))
    dialog.dialog_id = lifestyle_dialog_id
    dialog_subtitle = DEFAULT
    reached_max_lifestyles = len(sim_info.trait_tracker.get_traits_of_type(TraitType.LIFESTYLE)) >= lifestyle_service.MAX_ACTIVE_LIFESTYLES
    if reached_max_lifestyles:
        dialog_subtitle = dialog.max_lifestyles_active_subtitle
    dialog.show_dialog(text_override=dialog_subtitle)

@sims4.commands.Command('lifestyles.reset_all', command_type=sims4.commands.CommandType.Cheat)
def reset_all_lifestyles(sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    sim_info.trait_statistic_tracker.reset_all_statistics_by_group(LifestyleService.TRAIT_STATISTIC_GROUP)

@sims4.commands.Command('traits.dump_traits_with_commodities', command_type=sims4.commands.CommandType.DebugOnly)
def dump_traits_with_commodities():

    def trait_callback(file):
        instance_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        for trait in instance_manager.types.values():
            commodities_to_add = trait.get_all_initial_commodities()
            if len(commodities_to_add) != 0:
                for com in commodities_to_add:
                    file.write('{},{}\n'.format(trait.__name__, com.__name__))

    create_csv('TraitReport.txt', callback=trait_callback)

@sims4.commands.Command('traits.change_relationship_expectation_outlook_for_type')
def change_relationship_expectation_outlook_for_type(relationship_expectation_type:RelationshipExpectationType, sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    return sim_info.change_relationship_expectation_outlook_for_type(relationship_expectation_type)

@sims4.commands.Command('traits.equip_all_traits_with_tag', command_type=sims4.commands.CommandType.Live)
def equip_all_traits_with_tag(tag:tag.Tag, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    trait_to_equip = set()
    if sim is not None:
        all_traits = services.get_instance_manager(Types.TRAIT).types.values()
        for trait in all_traits:
            if trait.has_any_tag([tag]):
                trait_to_equip.add(trait)
        for trait in trait_to_equip:
            sim.sim_info.add_trait(trait)
        return True
    return False

@sims4.commands.Command('traits.generate_skill_list_from_trait_tag', command_type=sims4.commands.CommandType.Live)
def generate_skill_list_from_trait_tag(tag_id:int, mastery_perk_id:int, _connection=None):
    msg = UI_pb2.SkillsAffectedByMasteryPerk()
    msg.mastery_perk_id = mastery_perk_id
    all_skills = services.get_instance_manager(sims4.resources.Types.STATISTIC).all_skills_gen()
    if tag_id is not None:
        for skill in all_skills:
            if tag_id in skill.tags:
                msg.skill_names.append(skill.stat_name)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_SKILLS_AFFECTED_BY_MASTERY_PERK)
    Distributor.instance().add_op_with_no_owner(op)
