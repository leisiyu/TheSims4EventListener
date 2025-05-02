import sims4from server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParamfrom traits.preference_enums import GameplayObjectPreferenceTypesfrom traits.trait_type import TraitType
@sims4.commands.Command('traits.equip_gameplay_object_preference', command_type=sims4.commands.CommandType.Live)
def equip_gameplay_object_preference(trait_object:TunableInstanceParam(sims4.resources.Types.TRAIT), preference_type:GameplayObjectPreferenceTypes=GameplayObjectPreferenceTypes.NONE, opt_sim:OptionalTargetParam=None, _connection=None):
    if trait_object.trait_type is TraitType.GAMEPLAY_OBJECT_PREFERENCE:
        sim = get_optional_target(opt_sim, _connection)
        if sim is not None:
            trait_tracker = sim.sim_info.trait_tracker
            if trait_tracker is None:
                sims4.commands.output("Sim {} doesn't have trait tracker".format(sim), _connection)
                return False
            else:
                sim.sim_info.trait_tracker.add_gameplay_object_preference(trait_object, preference_type)
                return True
    return False

@sims4.commands.Command('traits.remove_gameplay_object_preference', command_type=sims4.commands.CommandType.Live)
def remove_gameplay_object_preference(trait_object:TunableInstanceParam(sims4.resources.Types.TRAIT), opt_sim:OptionalTargetParam=None, _connection=None):
    if trait_object.trait_type is TraitType.GAMEPLAY_OBJECT_PREFERENCE:
        sim = get_optional_target(opt_sim, _connection)
        if sim is not None:
            trait_tracker = sim.sim_info.trait_tracker
            if trait_tracker is None:
                sims4.commands.output("Sim {} doesn't have trait tracker".format(sim), _connection)
            sim.sim_info.trait_tracker.remove_gameplay_object_preference(trait_object)
            return True
    return False

@sims4.commands.Command('traits.clear_gameplay_object_preferences', command_type=sims4.commands.CommandType.Automation)
def clear_gameplay_object_preferences(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        trait_tracker = sim.sim_info.trait_tracker
        if trait_tracker is None:
            sims4.commands.output("Sim {} doesn't have trait tracker".format(sim), _connection)
            return False
        else:
            trait_tracker.remove_all_gameplay_object_preferences()
            return True
    return False
