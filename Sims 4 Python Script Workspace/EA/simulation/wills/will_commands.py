from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target, TunableInstanceParam, RequiredTargetParamimport servicesimport sims4.commands
@sims4.commands.Command('wills.create_will', command_type=sims4.commands.CommandType.DebugOnly)
def create_will(opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    will_service = services.get_will_service()
    if will_service is not None:
        if will_service.get_sim_will(sim_info.id) is None:
            will_service.create_will(sim_info)
            sims4.commands.output('SimWill created for {}.'.format(sim_info), _connection)
            return True
        sims4.commands.output('SimWill already created for {}.'.format(sim_info), _connection)
    return False

@sims4.commands.Command('wills.set_sim_will_burial', command_type=sims4.commands.CommandType.DebugOnly)
def set_sim_will_burial(burial_obj_def_id:int, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                sim_will.set_burial_preference(burial_obj_def_id)
                return True
    return False

@sims4.commands.Command('wills.set_sim_will_funeral', command_type=sims4.commands.CommandType.DebugOnly)
def set_sim_will_funeral(activity:TunableInstanceParam(sims4.resources.Types.HOLIDAY_TRADITION), opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                sim_will.set_funeral_activity_preference(activity.guid64)
                return True
    return False

@sims4.commands.Command('wills.set_sim_will_heirloom', command_type=sims4.commands.CommandType.DebugOnly)
def set_sim_will_heirloom(object_id:int, recipient_sim_id:int, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                sim_will.set_heirloom_recipient(object_id, recipient_sim_id)
                return True
    return False

@sims4.commands.Command('wills.set_sim_will_note', command_type=sims4.commands.CommandType.DebugOnly)
def set_sim_will_note(note_text:str, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                note = will_service.SIM_WILL_NOTE_TEXT(note_text)
                sim_will.set_note(note)
                return True
    return False

@sims4.commands.Command('wills.set_sim_will_emotion', command_type=sims4.commands.CommandType.DebugOnly)
def set_sim_will_emotion(mood:TunableInstanceParam(sims4.resources.Types.MOOD), opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                sim_will.set_emotion(mood)
                return True
    return False

@sims4.commands.Command('wills.set_hh_will_dependent', command_type=sims4.commands.CommandType.DebugOnly)
def set_hh_will_dependent(dependent_sim_id:int, destination_hh_id:int, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            household_will = will_service.get_household_will(sim_info.household_id)
            if household_will is not None:
                household_will.set_dependent_distribution(dependent_sim_id, destination_hh_id)
                return True
    return False

@sims4.commands.Command('wills.set_hh_will_simoleon', command_type=sims4.commands.CommandType.DebugOnly)
def set_hh_will_simoleon(recipient_hh_id:int, percentage:float, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            household_will = will_service.get_household_will(sim_info.household_id)
            if household_will is not None:
                household_will.set_simoleon_distribution(recipient_hh_id, percentage)
                return True
    return False

@sims4.commands.Command('wills.set_hh_will_charity', command_type=sims4.commands.CommandType.DebugOnly)
def set_hh_will_charity(percentage:float, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            household_will = will_service.get_household_will(sim_info.household_id)
            if household_will is not None:
                household_will.set_charity_distribution(percentage)
                return True
    return False

@sims4.commands.Command('wills.clear_sim_will', command_type=sims4.commands.CommandType.DebugOnly)
def clear_sim_will(opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                sim_will.clear_burial_preference()
                sim_will.clear_funeral_activity_preferences()
                sim_will.clear_heirloom_distributions()
                sim_will.clear_note_and_emotion()
                return True
    return False

@sims4.commands.Command('wills.clear_hh_will', command_type=sims4.commands.CommandType.DebugOnly)
def clear_hh_will(opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            household_will = will_service.get_household_will(sim_info.household_id)
            if household_will is not None:
                household_will.clear_dependent_distributions()
                household_will.clear_simoleon_distributions()
                return True
    return False

@sims4.commands.Command('wills.claim_will', command_type=sims4.commands.CommandType.DebugOnly)
def claim_will(deceased_sim_id:int, opt_recipient_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    deceased_sim_info = services.sim_info_manager().get(deceased_sim_id)
    if deceased_sim_info is None or not deceased_sim_info.death_type:
        return False
    recipient_sim_info = get_optional_target(opt_recipient_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if recipient_sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            will_service.show_will_contents_notification(deceased_sim_info)
            will_service.claim_inheritance(deceased_sim_info, recipient_sim_info)
            return True
    return False

@sims4.commands.Command('wills.print_will', command_type=sims4.commands.CommandType.DebugOnly)
def print_will(opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        sim_info_manager = services.sim_info_manager()
        will_service = services.get_will_service()
        if will_service is not None:
            sim_will = will_service.get_sim_will(sim_info.id)
            if sim_will is not None:
                will_service.show_will_contents_notification(sim_info)
                sims4.commands.output("{}'s Final Wishes:\n".format(sim_info.full_name), _connection)
                note = sim_will.get_note()
                if note is not None:
                    sims4.commands.output('Note: <LocalizedString>\n', _connection)
                emotion = sim_will.get_emotion()
                if emotion is not None:
                    sims4.commands.output('Emotion: {}\n'.format(emotion), _connection)
                burial_obj_def_id = sim_will.get_burial_preference()
                if burial_obj_def_id:
                    burial_obj_def = services.definition_manager().get(burial_obj_def_id)
                    sims4.commands.output('Burial preference: {}\n'.format(burial_obj_def.name), _connection)
                funeral_preferences = sim_will.get_funeral_activity_preferences()
                if funeral_preferences:
                    holiday_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION)
                    activities = []
                    for activity_id in funeral_preferences:
                        activity = holiday_manager.get(activity_id)
                        activities.append(activity.__name__)
                    sims4.commands.output('Funeral activity preferences: {}\n'.format(activities), _connection)
                heirloom_distribution = sim_will.get_heirloom_distributions()
                if heirloom_distribution:
                    obj_manager = services.object_manager()
                    sims4.commands.output('Heirloom distribution:', _connection)
                    for (object_id, recipient_sim_id) in heirloom_distribution.items():
                        obj = obj_manager.get(object_id)
                        recipient_sim_info = sim_info_manager.get(recipient_sim_id)
                        sims4.commands.output('{}: {}'.format(obj.definition.name, recipient_sim_info.full_name), _connection)
                household_will = will_service.get_household_will(sim_info.household_id)
                if household_will is not None:
                    household_manager = services.household_manager()
                    dependent_dist = household_will.get_dependent_distributions()
                    if dependent_dist:
                        sims4.commands.output('\nDependent distribution:', _connection)
                        for (dependent_sim_id, destination_hh_id) in dependent_dist.items():
                            dependent_sim_info = sim_info_manager.get(dependent_sim_id)
                            destination_hh = household_manager.get(destination_hh_id)
                            sims4.commands.output('{}: {} Household'.format(dependent_sim_info.full_name, destination_hh.name), _connection)
                    simoleon_dist = household_will.get_simoleon_distributions()
                    charity_dist = household_will.get_charity_distribution()
                    if simoleon_dist or charity_dist:
                        sims4.commands.output('\nSimoleon distribution:', _connection)
                        for (recipient_hh_id, percentage) in simoleon_dist.items():
                            recipient_hh = household_manager.get(recipient_hh_id)
                            sims4.commands.output('{} Household: {}%'.format(recipient_hh.name, percentage*100), _connection)
                        sims4.commands.output('Charity: {}%'.format(charity_dist*100), _connection)
                return True
    return False

@sims4.commands.Command('wills.destroy_wills', command_type=sims4.commands.CommandType.Live)
def destroy_wills(opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            will_service.destroy_sim_will(sim_info.id)
            will_service.destroy_household_will(sim_info.household_id)
            sims4.commands.output('Wills destroyed for {}.'.format(sim_info), _connection)
            return True
    return False

@sims4.commands.Command('wills.create_shady_merchant_will', command_type=sims4.commands.CommandType.Live)
def create_shady_merchant_will(target_sim:RequiredTargetParam, opt_sim:OptionalSimInfoParam=None, _connection=None) -> bool:
    target_sim_info = target_sim.get_target(manager=services.sim_info_manager())
    if target_sim_info is None:
        sims4.commands.output('Target Sim {} is invalid.'.format(target_sim), _connection)
        return False
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('Actor Sim {} is invalid.'.format(opt_sim), _connection)
        return False
    if sim_info == target_sim_info:
        sims4.commands.output('Target and Actor Sim cannot be the same', _connection)
        return False
    else:
        will_service = services.get_will_service()
        if will_service is not None:
            will_service.generate_shady_merchant_will(sim_info, target_sim_info)
            sims4.commands.output('Wills created for {}.'.format(sim_info), _connection)
            return True
    return False
