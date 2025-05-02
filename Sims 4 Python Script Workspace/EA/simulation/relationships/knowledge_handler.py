import servicesfrom relationships.sim_knowledge import SimKnowledgefrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaknowledge_schema = GsiGridSchema(label='Knowledge', sim_specific=True)knowledge_schema.add_field('sim_name', label='Sim Name')knowledge_schema.add_field('target_sim_id', label='Sim Id', hidden=True)knowledge_schema.add_field('has_knowledge', label='Has Any Knowledge')with knowledge_schema.add_has_many('flags', GsiGridSchema, label='Flags') as sub_schema:
    sub_schema.add_field('question', label='Question')
    sub_schema.add_field('answer', label='Answer')with knowledge_schema.add_has_many('traits', GsiGridSchema, label='Known Traits') as sub_schema:
    sub_schema.add_field('trait_name', label='Name')with knowledge_schema.add_has_many('stats', GsiGridSchema, label='Known Stats') as sub_schema:
    sub_schema.add_field('stat_name', label='Stat Name')
    sub_schema.add_field('stat_id', label='Stat ID')with knowledge_schema.add_has_many('rel_tracks', GsiGridSchema, label='Known Relationship Tracks') as sub_schema:
    sub_schema.add_field('track_name', label='Track Name')
    sub_schema.add_field('track_id', label='Track ID')with knowledge_schema.add_has_many('romantic_preferences', GsiGridSchema, label='Known Romantic Preferences') as sub_schema:
    sub_schema.add_field('gender', label='Gender')with knowledge_schema.add_has_many('woohoo_preferences', GsiGridSchema, label='Known WooHoo Preferences') as sub_schema:
    sub_schema.add_field('gender', label='Gender')with knowledge_schema.add_has_many('sim_secrets', GsiGridSchema, label='Known Secrets') as sub_schema:
    sub_schema.add_field('sim_secret', label='Sim Secret')
    sub_schema.add_field('status', label='Status')with knowledge_schema.add_has_many('finance', GsiGridSchema, label='Known Finances') as sub_schema:
    sub_schema.add_field('finance_type', label='Finance Type')
    sub_schema.add_field('value', label='Value')with knowledge_schema.add_has_many('relationship_expectations', GsiGridSchema, label='Known Relationship Expectations') as sub_schema:
    sub_schema.add_field('relationship_expectation', label='Relationship Expectation')
@GsiHandler('knowledge_view', knowledge_schema)
def generate_knowledge_view_data(sim_id:int=None):
    knowledge_data = []
    sim_info_manager = services.sim_info_manager()
    relationship_service = services.relationship_service()
    if sim_info_manager is None or relationship_service is None:
        return knowledge_data
    for relationship in relationship_service.get_all_sim_relationships(sim_id):
        target_sim_id = relationship.get_other_sim_id(sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        knowledge = relationship.get_knowledge(sim_id, target_sim_id)
        entry = {'sim_name': str(target_sim_info.full_name) if target_sim_info is not None else 'None', 'target_sim_id': str(target_sim_id), 'has_knowledge': str(knowledge is not None), 'flags': [], 'traits': [], 'stats': [], 'rel_tracks': [], 'romantic_preferences': [], 'woohoo_preferences': [], 'sim_secrets': [], 'finance': [], 'relationship_expectations': []}
        if knowledge is None:
            knowledge_data.append(entry)
        else:
            entry['flags'].append({'question': 'Knows Career?', 'answer': str(knowledge.knows_career)})
            entry['flags'].append({'question': 'Knows Major?', 'answer': str(knowledge.knows_major)})
            entry['flags'].append({'question': 'Knows Romantic Preference?', 'answer': str(knowledge.knows_romantic_preference)})
            entry['flags'].append({'question': 'Knows WooHoo Preference?', 'answer': str(knowledge.knows_woohoo_preference)})
            entry['flags'].append({'question': 'Knows Relationship Status?', 'answer': str(knowledge.knows_relationship_status)})
            entry['flags'].append({'question': 'Knows Net Worth?', 'answer': str(knowledge.knows_net_worth)})
            entry['flags'].append({'question': 'Knows Relationship Expectations?', 'answer': str(len(knowledge.known_relationship_expectations) > 0)})
            entry['finance'].append({'finance_type': 'Net Worth', 'value': str(knowledge.known_net_worth) if knowledge.knows_net_worth else 'Unknown'})
            for trait in knowledge.known_traits or []:
                entry['traits'].append({'trait_name': str(trait.__name__)})
            for stat in knowledge.known_stats or []:
                entry['stats'].append({'stat_name': str(stat.__name__), 'stat_id': str(stat.guid64)})
            for track in knowledge.known_rel_tracks or []:
                entry['rel_tracks'].append({'track_name': str(track.__name__), 'track_id': str(track.guid64)})
            for gender in knowledge.known_romantic_genders or []:
                entry['romantic_preferences'].append({'gender': str(gender)})
            for gender in knowledge.known_woohoo_genders or []:
                entry['woohoo_preferences'].append({'gender': str(gender)})
            unconfronted_secret = knowledge.get_unconfronted_secret()
            if unconfronted_secret is not None:
                entry['sim_secrets'].append({'sim_secret': str(unconfronted_secret), 'status': 'Unconfronted'})
            for secret in knowledge.get_confronted_secrets():
                entry['sim_secrets'].append({'sim_secret': str(secret), 'status': 'Blackmailed' if secret.blackmailed else 'Kept Secret'})
            for expectation in knowledge.known_relationship_expectations:
                entry['relationship_expectations'].append({'relationship_expectation': str(expectation.__name__)})
            knowledge_data.append(entry)
    return knowledge_data
