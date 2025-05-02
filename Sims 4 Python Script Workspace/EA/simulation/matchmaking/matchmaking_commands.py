from google.protobuf import text_formatfrom protocolbuffers import Sims_pb2import servicesimport sims4import sysfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom matchmaking.matchmaking_enum import ProfileTypefrom server_commands.argument_helpers import RequiredTargetParam, OptionalTargetParam, OptionalSimInfoParamfrom server_commands.interaction_commands import push_targeting_sim_info, push_self_interaction, push_interactionfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Age, Genderfrom sims4.commands import CommandTypefrom sims4.common import Packlogger = sims4.log.Logger('Matchmaking Commands', default_owner='sucywang')
def _get_matchmaking_service(_connection:int=None):
    matchmaking_service = services.get_matchmaking_service()
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
    return matchmaking_service

@sims4.commands.Command('matchmaking.show_matchmaking_dialog', command_type=CommandType.Live)
def show_matchmaking_dialog(actor_param:RequiredTargetParam, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    matchmaking_service.show_matchmaking_dialog(actor_info.sim_id)

@sims4.commands.Command('matchmaking.update_matchmaking_dialog', command_type=CommandType.Live)
def update_matchmaking_dialog(actor_param:RequiredTargetParam, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    matchmaking_service.show_matchmaking_dialog(actor_info.sim_id, True)

@sims4.commands.Command('matchmaking.save_matchmaking_profile', command_type=CommandType.Live)
def save_matchmaking_profile(actor_param:RequiredTargetParam, candidate_id:int, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    if candidate_id is None:
        sims4.commands.output('Missing required argument candidate id.', _connection)
        return
    matchmaking_service.on_save_profile(actor_info.sim_id, candidate_id)

@sims4.commands.Command('matchmaking.delete_matchmaking_profile', command_type=CommandType.Live)
def delete_matchmaking_profile(actor_param:RequiredTargetParam, candidate_id:int, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    if candidate_id is None:
        sims4.commands.output('Missing required argument candidate id.', _connection)
        return
    matchmaking_service.on_delete_profile(actor_info.sim_id, candidate_id)

@sims4.commands.Command('matchmaking.report_matchmaking_gallery_profile', command_type=CommandType.Live)
def report_matchmaking_gallery_profile(actor_param:RequiredTargetParam, candidate_id:int, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    if candidate_id is None:
        sims4.commands.output('Missing required argument candidate id.', _connection)
        return
    matchmaking_service.on_report_gallery_profile(actor_info.sim_id, candidate_id)

@sims4.commands.Command('matchmaking.on_age_select', command_type=CommandType.Live)
def on_age_select(actor_param:RequiredTargetParam, age_selected:Age, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    matchmaking_service.select_age(actor_info.sim_id, age_selected)
    matchmaking_service.show_matchmaking_dialog(actor_info.sim_id, True)

@sims4.commands.Command('matchmaking.on_age_deselect', command_type=CommandType.Live)
def on_age_deselect(actor_param:RequiredTargetParam, age_deselected:Age, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    matchmaking_service.deselect_age(actor_info.sim_id, age_deselected)
    matchmaking_service.show_matchmaking_dialog(actor_info.sim_id, True)

@sims4.commands.Command('matchmaking.set_profile_traits', command_type=CommandType.Live)
def set_profile_traits(actor_param:RequiredTargetParam, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid actor SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    push_interaction(affordance=matchmaking_service.SET_TRAITS_AFFORDANCE, opt_sim=OptionalTargetParam(str(actor_info.sim_id)), opt_target=RequiredTargetParam(str(actor_info.sim_id)), priority=Priority.High, _connection=_connection)

@sims4.commands.Command('matchmaking.set_profile_thumbnail', command_type=CommandType.Live)
def set_profile_thumbnail(target_actor_sim_id:int, thumbnail_url:str, _connection:int=None):
    if target_actor_sim_id is None:
        sims4.commands.output('Not a valid target actor SimID.', _connection)
        return
    if thumbnail_url is None:
        sims4.commands.output('Not a valid thumbnail url.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    matchmaking_service.set_profile_thumbnail(target_actor_sim_id, thumbnail_url)

@sims4.commands.Command('matchmaking.ask_on_date', command_type=CommandType.Live)
def ask_on_date(actor_param:RequiredTargetParam, target_actor_sim_id:int, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid actor SimID or is NPC.', _connection)
        return
    if target_actor_sim_id is None:
        sims4.commands.output('Not a valid target actor SimID.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    target_actor_real_sim_id = matchmaking_service.contact_action_used(actor_info, target_actor_sim_id)
    matchmaking_service.show_matchmaking_dialog(actor_info.sim_id, True)
    if target_actor_real_sim_id is not None:
        push_targeting_sim_info(affordance=matchmaking_service.ASK_ON_DATE_AFFORDANCE, opt_target=OptionalSimInfoParam(str(target_actor_real_sim_id)), opt_sim=OptionalTargetParam(str(actor_info.sim_id)), priority=Priority.High, interaction_context=InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, _connection=_connection)

@sims4.commands.Command('matchmaking.open_camera', command_type=CommandType.Live)
def open_camera(actor_param:RequiredTargetParam, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid actor SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    push_self_interaction(affordance=matchmaking_service.OPEN_SELFIE_CAMERA_AFFORDANCE, opt_sim=OptionalTargetParam(str(actor_info.sim_id)), priority=Priority.High, _connection=_connection)
    matchmaking_service.register_photo_taken_event(actor_info)
    matchmaking_service.register_photo_mode_exited_event(actor_info)

@sims4.commands.Command('matchmaking.contact_action_used', command_type=sims4.commands.CommandType.Live)
def contact_action_used(actor_param:RequiredTargetParam, candidate_id:int, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.output('Matchmaking Service not loaded.', _connection)
        return
    if candidate_id is None:
        sims4.commands.output('Missing required argument candidate id.', _connection)
        return
    matchmaking_service.contact_action_used(actor_info, candidate_id)
    matchmaking_service.show_matchmaking_dialog(actor_info.sim_id, True)

@sims4.commands.Command('matchmaking.refresh_candidates', command_type=CommandType.Live)
def refresh_candidates(actor_param:RequiredTargetParam, replace_gallery_sims:bool=False, enable_gallery_kill_switch:bool=False, _connection:int=None):
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None or actor_info.is_npc:
        sims4.commands.output('Not a valid SimID or is NPC.', _connection)
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    matchmaking_service.set_gallery_kill_switch(enable_gallery_kill_switch)
    matchmaking_service.refresh_npcs_for_sim(actor_info, replace_gallery_sims)

@sims4.commands.Command('matchmaking.clean_up_gallery_sim', command_type=sims4.commands.CommandType.Live)
def clean_up_gallery_sim(sim_id:str, gallery_sim_id:str, family_info_pb_data, *gallery_siminfos, _connection:int=None):
    actor_info = services.sim_info_manager().get(int(sim_id))
    if actor_info is None:
        return
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    if gallery_siminfos:
        gallery_siminfo = gallery_siminfos[0]
        matchmaking_service.set_gallery_kill_switch(False)
        try:
            attraction_preferences = set(filter(lambda trait: trait.is_attraction_trait, actor_info.trait_tracker))
            trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
            (household_id, item_type, remote_id) = gallery_siminfo.split(',')
            num_gallery_sims = 0
            gallery_sim_profiles = []
            family_info_pb = Sims_pb2.AccountFamilyData()
            text_format.Merge(family_info_pb_data, family_info_pb)
            if sys.getsizeof(family_info_pb_data) > 1073741824:
                logger.debug('Gallery sim data too large.')
                matchmaking_service.refresh_npcs_for_sim(actor_info, True)
                return
            for sim_proto in family_info_pb.sim:
                if sim_proto.sim_id == int(gallery_sim_id):
                    gallery_sim_trait_ids = list(t for t in sim_proto.attributes.trait_tracker.trait_ids)
                    if set(gallery_sim_trait_ids).intersection(set(matchmaking_service.gallery_sims_trait_exclusions)):
                        break
                    else:
                        base_sim_info = SimInfoBaseWrapper(first_name=sim_proto.first_name, sim_id=sim_proto.sim_id)
                        base_sim_info.load_sim_info(sim_proto)
                        base_sim_info.manager = services.sim_info_manager()
                        base_sim_info.set_trait_ids_on_base(trait_ids_override=gallery_sim_trait_ids)
                        base_sim_profile = matchmaking_service.create_matchmaking_profile_from_sim_info(base_sim_info, ProfileType.GALLERY_NPC)
                        base_sim_profile.exchange_data_creator_name = family_info_pb.original_creator_string
                        base_sim_profile.exchange_data_household_id = int(household_id)
                        base_sim_profile.exchange_data_type = int(item_type)
                        base_sim_profile.exchange_data_remote_id = remote_id
                        base_sim_profile.family_data = family_info_pb
                        if remote_id in matchmaking_service.remote_id_to_sim_id.keys():
                            base_sim_profile.real_sim_id = matchmaking_service.remote_id_to_sim_id[remote_id]
                        for preference in attraction_preferences:
                            for trait_id in base_sim_profile.displayed_traits_map:
                                base_sim_profile.displayed_traits_map[trait_id] += int(matchmaking_service.calculate_preference_score_for_trait(preference, trait_manager.get(trait_id)))
                        num_gallery_sims += 1
                        gallery_sim_profiles.append(base_sim_profile)
                        break
            if len(gallery_sim_profiles) > 0:
                for profile in gallery_sim_profiles:
                    matchmaking_service.add_gallery_sim(profile)
                matchmaking_service.refresh_npcs_for_sim(actor_info, False, [profile.sim_id for profile in gallery_sim_profiles])
            else:
                matchmaking_service.refresh_npcs_for_sim(actor_info, True)
        except Exception:
            logger.info('Error encountered while parsing gallery sim data.')
            matchmaking_service.refresh_npcs_for_sim(actor_info, True)
            return

@sims4.commands.Command('matchmaking.toggle_gallery_sims_enabled', pack=Pack.EP16, command_type=sims4.commands.CommandType.Live)
def toggle_matchmaking_allow_gallery_sims(enable:bool, _connection:int=None) -> None:
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    matchmaking_service.gallery_sims_enabled = enable

@sims4.commands.Command('matchmaking.toggle_occult_sims_enabled', pack=Pack.EP16, command_type=sims4.commands.CommandType.Live)
def toggle_matchmaking_allow_occult_sims(enable:bool, _connection:int=None) -> None:
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    matchmaking_service.occult_sims_enabled = enable

@sims4.commands.Command('matchmaking.toggle_gallery_sims_favorites_only_enabled', pack=Pack.EP16, command_type=sims4.commands.CommandType.Live)
def toggle_gallery_sims_favorites_only_enabled(enable:bool, _connection:int=None) -> None:
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        return
    matchmaking_service.gallery_sims_favorites_only_enabled = enable

@sims4.commands.Command('matchmaking.save_all_candidates', pack=Pack.EP16, command_type=sims4.commands.CommandType.Automation)
def save_all_candidates(actor_param:RequiredTargetParam, _connection:int=None) -> None:
    matchmaking_service = _get_matchmaking_service(_connection)
    if matchmaking_service is None:
        sims4.commands.automation_output('CandidateIds; Ids:', _connection)
        return
    actor_info = actor_param.get_target(manager=services.sim_info_manager())
    if actor_info is None:
        sims4.commands.automation_output('CandidateIds; Ids:', _connection)
        return
    if actor_info.id in matchmaking_service.actor_id_to_matchmaking_data:
        candidate_ids = matchmaking_service.actor_id_to_matchmaking_data[actor_info.id].candidate_ids
        for candidate_id in candidate_ids:
            matchmaking_service.on_save_profile(actor_info.id, candidate_id)
        id_string = str(candidate_ids)
        id_string = id_string.translate({ord(','): None, ord('}'): None, ord('{'): None})
        sims4.commands.automation_output('CandidateIds; Ids:{}'.format(id_string), _connection)
        return
    sims4.commands.automation_output('CandidateIds; Ids:', _connection)
    sims4.commands.output('Actor ({}) not found in matchmaking data'.format(actor_info), _connection)
