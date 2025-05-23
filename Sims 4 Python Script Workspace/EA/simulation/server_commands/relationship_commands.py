from _collections import defaultdictimport itertoolsimport randomfrom distributor.system import Distributorfrom interactions.cheats.force_marriage_interaction import ForceMarriageInteractionfrom protocolbuffers import UI_pb2, Consts_pb2from relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.relationship_enums import RelationshipTrackTypefrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParam, RequiredTargetParam, SimInfoParam, OptionalSimInfoParamfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_spawner import SimSpawnerfrom sims4.commands import CommandTypefrom sims4.tuning.tunable import TunableReference, Tunablefrom relationships.relationship_track import RelationshipTrackimport relationships.relationship_trackimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Relationship', default_owner='msantander')
class RelationshipCommandTuning:
    INTRODUCE_BIT = TunableReference(description='\n        Relationship bit to add to all Sims when running the introduce command.\n        ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT))
    INTRODUCE_TRACK = TunableReference(description='\n        Relationship track for friendship used by cheats to introduce sims. \n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=relationships.relationship_track.RelationshipTrack)
    INTRODUCE_VALUE = Tunable(description='\n        The value to add to the relationship to introduce the sims.\n        ', tunable_type=int, default=0)
    CREATE_FRIENDS_COMMAND_QUANTITY = Tunable(description='\n        The number of friendly sims to generate \n        using command |relationships.create_friends_for_sim.\n        ', tunable_type=int, default=1)
    CREATE_FRIENDS_COMMAND_FILTER = TunableReference(description='\n        The sim-filter for generating friendly sims.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=('TunableSimFilter',))

@sims4.commands.Command('relationship.create')
def create_relationship(source_sim_id:int, *sim_id_list, _connection=None):
    if not source_sim_id:
        return False
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    sim_id_list = _get_sim_ids_from_string_list(sim_id_list, _connection)
    if sim_id_list is None:
        return False
    sim_info_set = {services.sim_info_manager().get(sim_id) for sim_id in sim_id_list}
    for sim_info in sim_info_set:
        source_sim_info.relationship_tracker.create_relationship(sim_info.sim_id)
    return True

@sims4.commands.Command('relationship.destroy', command_type=sims4.commands.CommandType.Automation)
def destroy_relationship(source_sim_id:int, *sim_id_list, _connection=None):
    if not source_sim_id:
        sims4.commands.automation_output('DestroyRelationshipResponse; Success:False', _connection)
        return False
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        sims4.commands.automation_output('DestroyRelationshipResponse; Success:False', _connection)
        return False
    sim_id_list = _get_sim_ids_from_string_list(sim_id_list, _connection)
    if sim_id_list is None:
        sims4.commands.automation_output('DestroyRelationshipResponse; Success:False', _connection)
        return False
    sim_info_set = {services.sim_info_manager().get(sim_id) for sim_id in sim_id_list}
    for sim_info in sim_info_set:
        source_sim_info.relationship_tracker.destroy_relationship(sim_info.sim_id)
    sims4.commands.automation_output('DestroyRelationshipResponse; Success:True', _connection)
    return True

@sims4.commands.Command('relationship.introduce_all_sims')
def introduce_all_sims_command():
    introduce_all_sims()

def introduce_all_sims():
    all_sims = [sim_info for sim_info in services.sim_info_manager().objects]
    num_sims = len(all_sims)
    bit = RelationshipCommandTuning.INTRODUCE_BIT
    for sim_a_index in range(num_sims - 1):
        for sim_b_index in range(sim_a_index + 1, num_sims):
            sim_info_a = all_sims[sim_a_index]
            sim_info_b = all_sims[sim_b_index]
            if sim_info_a.relationship_tracker.has_bit(sim_info_b.sim_id, bit):
                pass
            else:
                sim_info_a.relationship_tracker.add_relationship_score(sim_info_b.sim_id, RelationshipCommandTuning.INTRODUCE_VALUE, RelationshipCommandTuning.INTRODUCE_TRACK)
                sim_info_a.relationship_tracker.add_relationship_bit(sim_info_b.sim_id, bit)

@sims4.commands.Command('relationship.make_all_sims_friends', command_type=sims4.commands.CommandType.Cheat)
def make_all_sims_friends(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No valid target for relationship.make_all_sims_friends', _connection)
        return
    friends = 0
    for target_sim in services.sim_info_manager().objects:
        if target_sim.id != sim.id:
            sim.relationship_tracker.set_default_tracks(target_sim, update_romance=False)
            target_sim.relationship_tracker.set_default_tracks(sim, update_romance=False)
            friends += 1
    sims4.commands.output('Set {} default friendships for {}'.format(friends, sim.full_name), _connection)

@sims4.commands.Command('relationships.create_friends_for_sim', command_type=sims4.commands.CommandType.Cheat)
def create_friends_for_sim(opt_sim:OptionalTargetParam=None, _connection=None):

    def callback_spawn_sims(filter_results, callback_data):
        sim_infos = [result.sim_info for result in filter_results]
        for sim_info in sim_infos:
            services.get_zone_situation_manager().add_debug_sim_id(sim_info.id)
            SimSpawner.spawn_sim(sim_info)

    quantity = 1
    if RelationshipCommandTuning.CREATE_FRIENDS_COMMAND_QUANTITY is not None:
        quantity = RelationshipCommandTuning.CREATE_FRIENDS_COMMAND_QUANTITY
    friend_filter = RelationshipCommandTuning.CREATE_FRIENDS_COMMAND_FILTER
    active_sim_info = None
    tgt_client = services.client_manager().get(_connection)
    if tgt_client is not None:
        active_sim_info = services.client_manager().get(_connection).active_sim
    else:
        logger.error("tgt_client is None-- can't get active SimInfo")
    if active_sim_info is None:
        sims4.commands.output('error: A valid sim is needed to carry out this command.', _connection)

    def get_sim_filter_gsi_name():
        return 'Relationship Command: Create Friend for {}'.format(active_sim_info)

    sims4.commands.output('Generating friends for active sim...', _connection)
    services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=quantity, sim_filter=friend_filter, callback=callback_spawn_sims, requesting_sim_info=active_sim_info, continue_if_constraints_fail=True, gsi_source_fn=get_sim_filter_gsi_name)

@sims4.commands.Command('relationship.introduce_sim_to_all_others', command_type=sims4.commands.CommandType.Cheat)
def introduce_sim_to_all_others(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No valid target for relationship.introduce_sim_to_all_others', _connection)
        return
    for target_sim in services.sim_info_manager().objects:
        if target_sim.id == sim.id:
            pass
        else:
            sim.relationship_tracker.add_relationship_score(target_sim.sim_id, RelationshipCommandTuning.INTRODUCE_VALUE, RelationshipCommandTuning.INTRODUCE_TRACK)

@sims4.commands.Command('relationship.clear')
def clear_relationships(source_sim_id:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(source_sim_id, _connection)
    if sim is not None:
        source_sim_info = sim.sim_info
    else:
        if not source_sim_id:
            sims4.commands.output('No sim_info id specified for relationship.clear', _connection)
            return False
        source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        sims4.commands.output('Invalid sim_info id: {}'.format(source_sim_id), _connection)
        return False
    tracker = source_sim_info.relationship_tracker
    if tracker:
        rel_list = list(tracker)
        for relationship in rel_list:
            tracker.destroy_relationship(relationship.get_other_sim_id(source_sim_id))
        sims4.commands.output('Removed {} relationships from {}'.format(len(rel_list), sim), _connection)
    else:
        logger.error("Sim {} doesn't have a RelationshipTracker", source_sim_info)
    return True

@sims4.commands.Command('relationships.set_object_relationship')
def set_object_relationship(sim_id:int, obj_inst_id:int, value:float, obj_def_id:int=None, _connection=None):
    obj = services.object_manager().get(obj_inst_id)
    if obj is None:
        obj = services.inventory_manager().get(obj_inst_id)
    if obj_def_id is None:
        obj_def_id = obj.definition.id
    obj_tag_set = services.relationship_service().get_mapped_tag_set_of_id(obj_def_id)
    if obj is not None and obj_tag_set is not None:
        obj_relationship = services.relationship_service()._find_object_relationship(sim_id, obj_tag_set, obj_def_id, create=True)
        if obj_relationship is None:
            logger.error('Relationship creation failed for Sim {} on object with catalog id {}.', sim_id, obj_def_id)
            sims4.commands.output('Object relationship creation failed for Sim {} on object {}'.format(sim_id, obj_def_id), _connection)
            return False
        stat_type = services.relationship_service().get_mapped_track_of_tag_set(obj_tag_set)
        obj_relationship.bidirectional_track_tracker.set_value(stat_type, value)
    else:
        if obj is None:
            logger.error('Retrieving Object Relationship with Sim {} failed: Target object {} does not exist.', sim_id, obj_inst_id)
            sims4.commands.output('Could not find target object {} relationship with Sim {}.'.format(obj_inst_id, sim_id), _connection)
            return False
        obj_rel = obj.objectrelationship_component
        if obj_rel is None:
            logger.error('Object {} has no valid relationship track or component.', obj_inst_id)
            sims4.commands.output('Object relationship for Sim {} on object {} is not valid.'.format(sim_id, obj_inst_id), _connection)
            return False
        obj_rel.modify_relationship(sim_id, value, set_value=True)
    return True

@sims4.commands.Command('relationships.print_object_relationship')
def print_object_relationship(sim_id:int, obj_def_id:int, _connection=None):
    obj_tag_set = services.relationship_service().get_mapped_tag_set_of_id(obj_def_id)
    if obj_tag_set is None:
        sims4.commands.output('No rel exists', _connection)
        return False
    obj_relationship = services.relationship_service()._find_object_relationship(sim_id, obj_tag_set, obj_def_id, create=False).bidirectional_track_tracker
    if obj_relationship is None:
        sims4.commands.output('No rel exists', _connection)
        return False
    stat_type = services.relationship_service().get_mapped_track_of_tag_set(obj_tag_set)
    sims4.commands.output('{} : Object Relationship Type Value between sim with sim id {} and object of def id {}.'.format(obj_relationship._rel_data.bidirectional_track_tracker.get_value(stat_type), sim_id, obj_def_id), _connection)

@sims4.commands.Command('relationships.set_object_relationship_name', command_type=sims4.commands.CommandType.Live)
def set_object_relationship_track_name(sim_id:int, obj_def_id:int, name:str, _connection=None):
    relationship_service = services.relationship_service()
    obj_tag_set = relationship_service.get_mapped_tag_set_of_id(obj_def_id)
    if obj_tag_set is None:
        sims4.commands.output('No rel exists', _connection)
        return
    obj_relationship = relationship_service.get_object_relationship(sim_id, obj_tag_set)
    if obj_relationship is None:
        sims4.commands.output('No rel exists', _connection)
        return
    obj_relationship.set_object_rel_name(name)

@sims4.commands.Command('relationship.hide_relationship')
def hide_relationship(sim_id:int, target_id:int, value:bool, _connection=None):
    services.relationship_service().hide_relationship(sim_id, target_id, value)

@sims4.commands.Command('relationship.print_hidden_relationships')
def print_hidden_relationships(sim_id:int, _connection=None):
    hidden_relationships = services.relationship_service().get_hidden_relationships(sim_id)
    print_string = 'Hidden Relationship Sim Ids: '
    if not hidden_relationships:
        print_string = print_string + 'None'
    for relationship in hidden_relationships:
        print_string = print_string + str(relationship.get_other_sim_id(sim_id)) + ', '
    sims4.commands.output(print_string, _connection)

@sims4.commands.Command('relationship.bulk_add_reltrack', command_type=sims4.commands.CommandType.Automation)
def bulk_add_reltrack(track:TunableInstanceParam(sims4.resources.Types.STATISTIC), max_sims:int=0, _connection=None):
    if max_sims <= 0:
        logger.error('You must provide some > 0 for the number of sims to attach reltracks between')
        return False
    all_sims = list(services.sim_info_manager().get_all())
    all_sim_count = len(all_sims)
    if all_sim_count < max_sims:
        logger.error('{} sims requested, but only {} exist in the sim_info_manager. Command will only target {} sims', max_sims, all_sim_count, all_sim_count)
    for sim_a in services.active_household():
        cur_count = 0
        for sim_b in all_sims:
            if sim_a.id == sim_b.id:
                pass
            else:
                if track.track_type != RelationshipTrackType.RELATIONSHIP:
                    sim_a.sim_info.relationship_tracker.set_track_to_max(sim_b.sim_id, track)
                    sim_b.sim_info.relationship_tracker.set_track_to_max(sim_a.sim_id, track)
                else:
                    sim_a.sim_info.relationship_tracker.set_track_to_max(sim_b.sim_id, track)
                cur_count += 1
                if cur_count == max_sims:
                    break
    logger.info('Done running relationship.bulk_add_reltrack')
    return True

@sims4.commands.Command('relationship.bulk_remove_reltrack', command_type=sims4.commands.CommandType.Automation)
def bulk_remove_reltrack(track_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), _connection=None):
    all_sims = list(services.sim_info_manager().get_all())
    for sim_a in services.active_household():
        for sim_b in all_sims:
            if sim_a.id == sim_b.id:
                pass
            else:
                sim_a.sim_info.relationship_tracker.remove_relationship_track(sim_b.sim_id, track_type)
                sim_b.sim_info.relationship_tracker.remove_relationship_track(sim_a.sim_id, track_type)
    logger.info('Done running relationship.bulk_remove_reltrack')
    return True

@sims4.commands.Command('relationship.add_score', command_type=sims4.commands.CommandType.Automation)
def add_score(source_sim_id:int, target_sim_id:int, score_delta:float, track_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    if score_delta != score_delta:
        logger.error('Sim {} trying to set {} to NaN', source_sim_info, track_type)
        return False
    source_sim_info.relationship_tracker.add_relationship_score(target_sim_id, score_delta, track_type)
    return True

@sims4.commands.Command('relationship.set_can_add_reltrack', command_type=sims4.commands.CommandType.Automation)
def set_can_add_reltrack(source_sim_id:int, target_sim_id:int, can_add:bool):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.set_can_add_reltrack(target_sim_id, can_add)
    return True

@sims4.commands.Command('relationship.add_track', command_type=sims4.commands.CommandType.Automation)
def add_track(source_sim_id:int, target_sim_id:int, track_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.set_track_to_max(target_sim_id, track_type)
    return True

@sims4.commands.Command('relationship.remove_track', command_type=sims4.commands.CommandType.Automation)
def remove_track(source_sim_id:int, target_sim_id:int, track_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.remove_relationship_track(target_sim_id, track_type)
    return True

@sims4.commands.Command('relationship.set_score', command_type=sims4.commands.CommandType.Automation)
def set_score(source_sim_id:int, target_sim_id:int, score:float, track_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), bidirectional:bool=True, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        sims4.commands.output("Source sim info doesn't exist in relationship.set_score", _connection)
        return False
    source_sim_info.relationship_tracker.set_relationship_score(target_sim_id, score, track_type)
    return True

@sims4.commands.Command('modifyrelationship', command_type=sims4.commands.CommandType.Cheat)
def modify_relationship(info1:SimInfoParam, info2:SimInfoParam, amount:float=0, track_type:TunableInstanceParam(sims4.resources.Types.STATISTIC)=None, _connection=None):
    if info1 is not None and info2 is not None:
        info1.relationship_tracker.add_relationship_score(info2.id, amount, track_type)
        return True
    return False

@sims4.commands.Command('relationship.print_score')
def print_relationship_score(source_sim_id:int, target_sim_id:int, track_name, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    track_type = services.get_instance_manager(sims4.resources.Types.STATISTIC).get(track_name)
    if track_type is None:
        sims4.commands.output('Invalid relationship track: {0}'.format(track_name), _connection)
        return False
    score = source_sim_info.relationship_tracker.get_relationship_score(target_sim_id, track_type)
    sims4.commands.output('Relationship Score: {0}'.format(score), _connection)
    return True

@sims4.commands.Command('relationships.change_ab_group', command_type=CommandType.Live)
def change_ab_group(ab_group_id:int, is_valid_value:bool=False, _connection:int=None) -> None:
    satisfaction_service = services.get_satisfaction_service()
    if satisfaction_service is None:
        return
    if is_valid_value:
        satisfaction_service._set_ab_test_group(ab_group_id)
    else:
        satisfaction_service._set_invalid_test_group()

@sims4.commands.Command('relationships.clear_ab_group', command_type=CommandType.Live)
def clear_ab_group(_connection:int=None) -> None:
    satisfaction_service = services.get_satisfaction_service()
    if satisfaction_service is None:
        return
    satisfaction_service._clear_ab_test_group()

@sims4.commands.Command('relationship.add_bit', command_type=sims4.commands.CommandType.Automation)
def add_bit(source_sim_id:int, target_sim_id:int, rel_bit:TunableInstanceParam(sims4.resources.Types.RELATIONSHIP_BIT), _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.add_relationship_bit(target_sim_id, rel_bit, force_add=True)
    return True

@sims4.commands.Command('relationship.remove_bit')
def remove_bit(source_sim_id:int, target_sim_id:int, rel_bit:TunableInstanceParam(sims4.resources.Types.RELATIONSHIP_BIT), _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.remove_relationship_bit(target_sim_id, rel_bit)
    return True

@sims4.commands.Command('relationship.print_depth')
def print_relationship_depth(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    depth = source_sim_info.relationship_tracker.get_relationship_depth(target_sim_id)
    sims4.commands.output('Relationship Depth: {0}'.format(depth), _connection)
    return True

@sims4.commands.Command('relationship.add_knows_career')
def add_knows_career(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.add_knows_career(target_sim_id)

@sims4.commands.Command('relationship.remove_knows_career')
def remove_knows_career(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.remove_knows_career(target_sim_id)

@sims4.commands.Command('relationship.add_knows_sexuality')
def add_knows_sexuality(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.add_knows_romantic_preference(target_sim_id, notify_client=False)
    source_sim_info.relationship_tracker.add_knows_woohoo_preference(target_sim_id)

@sims4.commands.Command('relationship.remove_knows_sexuality')
def remove_knows_sexuality(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.remove_knows_romantic_preference(target_sim_id, notify_client=False)
    source_sim_info.relationship_tracker.remove_knows_woohoo_preference(target_sim_id)

@sims4.commands.Command('relationship.add_knows_relationship_expectations')
def add_knows_relationship_expectations(source_sim_id:int, target_sim_id:int, _connection=None):
    services.relationship_service().add_knows_relationship_expectations(source_sim_id, target_sim_id)

@sims4.commands.Command('relationship.remove_knows_relationship_expectations')
def remove_knows_relationship_expectations(source_sim_id:int, target_sim_id:int, _connection=None):
    services.relationship_service().remove_knows_relationship_expectations(source_sim_id, target_sim_id)

@sims4.commands.Command('relationship.print_info')
def print_relationship_info(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.print_relationship_info(target_sim_id, _connection)

@sims4.commands.Command('qa.relationship.print_info', command_type=sims4.commands.CommandType.Automation)
def qa_print_relationship_info(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        sims4.commands.automation_output('SimRelationshipInfo; Error:COULD_NOT_FIND_SIM', _connection)
        return False
    relationship_tracker = source_sim_info.relationship_tracker
    out_str = 'SimRelationshipInfo; Sim1:{}, Sim2:{}, Depth:{}'.format(relationship_tracker._sim_info.sim_id, target_sim_id, relationship_tracker.get_relationship_depth(target_sim_id))
    relationship_service = services.relationship_service()
    if not relationship_service.has_relationship(source_sim_id, target_sim_id):
        out_str += ', Exists:No, NumBits:0, NumTracks:0'
    else:
        relationship_bits = relationship_service.get_all_bits(source_sim_id, target_sim_id=target_sim_id)
        relationship_tracks = list(relationship_service.relationship_tracks_gen(source_sim_id, target_sim_id))
        out_str += ', Exists:Yes, NumBits:{}, NumTracks:{}'.format(len(relationship_bits), len(relationship_tracks))
        for (idx, relationship_bit) in enumerate(relationship_bits):
            out_str += ', Bit{}:{}'.format(idx, relationship_bit.__name__)
        for (idx, relationship_track) in enumerate(relationship_tracks):
            out_str += ', Track{}_Name:{}, Track{}_Value:{}'.format(idx, relationship_track.__class__.__name__, idx, relationship_track.get_value())
    sims4.commands.automation_output(out_str, _connection)

def _get_spouses():
    spouses = defaultdict(set)
    for si in services.sim_info_manager().values():
        spouse = si.relationship_tracker.spouse_sim_id
        if spouse is not None:
            spouses[spouse].add(si.id)
        all_relationship_sim_infos = si.relationship_tracker.get_target_sim_infos()
        for sim_info in all_relationship_sim_infos:
            if si.relationship_tracker.has_bit(sim_info.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT):
                spouses[sim_info.id].add(si.id)
    return spouses

@sims4.commands.Command('relationship.test_marriage', command_type=CommandType.Cheat)
def test_marriage(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    spouses = _get_spouses()
    polygamies = False
    mgr = services.sim_info_manager()

    def get_name(sim_id):
        si = mgr.get(sim_id)
        if si is None:
            return 'Invalid'
        return '{} {}'.format(si.first_name, si.last_name)

    for (x, illegals) in spouses.items():
        if len(illegals) <= 1:
            pass
        else:
            polygamies = True
            output('{} with sim id: ({}) is married to the following sims: '.format(get_name(x), x))
            for illegal in illegals:
                illegal_spouses = spouses.get(illegal)
                if illegal_spouses is None:
                    illegal_spouses = 'None'
                else:
                    illegal_spouses = ', '.join('{} with sim id: ({})'.format(get_name(i), i) for i in illegal_spouses)
                illegal_name = get_name(illegal)
                output('\t{} with sim id: ({}). \n \t \t {} is married to {}'.format(illegal_name, illegal, illegal_name, illegal_spouses))
    if not polygamies:
        output('There are no inappropriate marriages in this save.')

@sims4.commands.Command('relationship.enforce_marriage', command_type=CommandType.Automation)
def enforce_marriage(x:RequiredTargetParam, y:RequiredTargetParam, _connection=None):
    mgr = services.sim_info_manager()
    source = x.get_target(manager=mgr)
    target = y.get_target(manager=mgr)
    ForceMarriageInteraction.enforce_marriage(source, target)

@sims4.commands.Command('relationship.print_non_reciprocal')
def print_non_reciprocal(_connection=None):
    num_rels = 0
    num_no_target = 0
    num_non_reciprocal = 0
    for sim_info in services.sim_info_manager().values():
        sim_id = sim_info.sim_id
        for rel in sim_info.relationship_tracker:
            num_rels += 1
            target_sim_info = rel.get_other_sim_info(sim_id)
            if target_sim_info is None:
                num_no_target += 1
                sims4.commands.output('Missing target: {} -> {}\n{}\n{}'.format(sim_info, rel.get_other_sim_id(sim_id), rel.build_printable_string_of_bits(sim_id), rel.build_printable_string_of_tracks()), _connection)
    sims4.commands.output('Number of Relationships: {}\nNumber missing target: {}\nNumber non reciprocal: {}'.format(num_rels, num_no_target, num_non_reciprocal), _connection)

@sims4.commands.Command('relationship.set_average_relationships', command_type=sims4.commands.CommandType.Automation)
def set_average_relationships(avg_relationships:float, _connection=None):
    relationship_service = services.relationship_service()
    relationship_count = len(relationship_service)
    sim_info_manager = services.sim_info_manager()
    sim_count = len(sim_info_manager)
    target_relationships = sim_count*avg_relationships
    needed_relationships = target_relationships - relationship_count
    modified_relationship_count = 0
    if needed_relationships > 0:
        sim_info_combinations = list(itertools.combinations(sim_info_manager, 2))
        random.shuffle(sim_info_combinations)
        for (sim_info_id_a, sim_info_id_b) in sim_info_combinations:
            sim_info_a = sim_info_manager.get(sim_info_id_a)
            sim_info_b = sim_info_manager.get(sim_info_id_b)
            if sim_info_a.is_npc and (sim_info_a.lod != SimInfoLODLevel.MINIMUM and (sim_info_b.is_npc and sim_info_b.lod != SimInfoLODLevel.MINIMUM)) and not sim_info_a.relationship_tracker.has_relationship(sim_info_b.sim_id):
                sim_info_a.relationship_tracker.set_default_tracks(sim_info_b, update_romance=False)
                sim_info_b.relationship_tracker.set_default_tracks(sim_info_a, update_romance=False)
                needed_relationships -= 1
                modified_relationship_count += 1
                if needed_relationships <= 0:
                    break
    elif needed_relationships < 0:
        relationships = list(relationship_service)
        random.shuffle(relationships)
        for relationship in relationships:
            if relationship.can_cull_relationship(consider_convergence=False):
                relationship_service.destroy_relationship(relationship.sim_id_a, relationship.sim_id_b)
                modified_relationship_count -= 1
                needed_relationships += 1
                if needed_relationships >= 0:
                    break
    sims4.commands.output('Number of Target Relationships: {}\nNumber of Initial Relationships: {}\nRelationship count delta:{} '.format(target_relationships, relationship_count, modified_relationship_count), _connection)

@sims4.commands.Command('relationship.check_culling_alarms')
def check_culling_alarms(_connection=None):
    num_rels_that_should_be_culled = 0
    num_of_culling_alarms = 0
    for relationship in services.relationship_service():
        if not relationship.find_sim_info_a().is_player_sim:
            pass
        if relationship.can_cull_relationship():
            num_rels_that_should_be_culled += 1
            if relationship._culling_alarm_handle is not None:
                num_of_culling_alarms += 1
    sims4.commands.output('Number of Relationships that should be culled: {}\nNumber of culling alarms: {}'.format(num_rels_that_should_be_culled, num_of_culling_alarms), _connection)

@sims4.commands.Command('relationship.open_sim_profile_ui', command_type=sims4.commands.CommandType.Live)
def open_sim_profile_ui(profile_sim:OptionalSimInfoParam=None, actor_sim:OptionalSimInfoParam=None, _connection=None):
    msg = UI_pb2.ShowSimProfile()
    if profile_sim is not None:
        sim_info = get_optional_target(profile_sim, target_type=OptionalSimInfoParam, _connection=_connection)
        msg.target_sim_id = sim_info.id
    if actor_sim is not None:
        sim_info = get_optional_target(actor_sim, target_type=OptionalSimInfoParam, _connection=_connection)
        msg.actor_sim_id = sim_info.id
        if not sim_info.is_selectable:
            services.relationship_service().send_relationship_info(msg.actor_sim_id, allow_sending_npc_info=True)
    Distributor.instance().add_event(Consts_pb2.MSG_SHOW_SIM_PROFILE, msg)

@sims4.commands.Command('relationship.update_compatibilities')
def update_compatibilities(source_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    if source_sim_info is None:
        return False
    source_sim_info.relationship_tracker.update_compatibilities()

@sims4.commands.Command('relationship.print_compatibility')
def print_compatibility(source_sim_id:int, target_sim_id:int, _connection=None):
    source_sim_info = services.sim_info_manager().get(source_sim_id)
    target_sim_info = services.sim_info_manager().get(target_sim_id)
    if source_sim_info is None or target_sim_info is None:
        return False
    score = source_sim_info.relationship_tracker.get_compatibility_score(target_sim_id)
    level = source_sim_info.relationship_tracker.get_compatibility_level(target_sim_id)
    if score is None or level is None:
        sims4.commands.output('No Compatibility found for sim ids {} and {}.'.format(source_sim_id, target_sim_id), _connection)
    else:
        sims4.commands.output('Compatibility Score: {}\nCompatibility Level: {}'.format(score, level), _connection)

def _get_sim_ids_from_string_list(sim_id_list, _connection):
    if not sim_id_list:
        return
    else:
        output_list = {int(x) for x in sim_id_list}
        if not output_list:
            sims4.commands.output('No valid sim ids in _get_sim_ids_from_string_list() command.', _connection)
            return
    return output_list
