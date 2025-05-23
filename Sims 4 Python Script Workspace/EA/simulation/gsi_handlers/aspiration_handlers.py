from aspirations.aspiration_tuning import Aspirationfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport aspirations.aspirationsimport servicesimport sims4.resourcesfrom gsi_handlers.gameplay_archiver import GameplayArchiveraspiration_schema = GsiGridSchema(label='Aspirations', sim_specific=True)aspiration_schema.add_field('aspiration_uid', label='UId', unique_field=True)aspiration_schema.add_field('aspiration', label='Aspiration', width=3)aspiration_schema.add_field('aspiration_complete', label='Done')aspiration_schema.add_field('aspiration_completion_count', label='Completion Count', width=1)aspiration_schema.add_field('display_name', label='DisplayStr', hidden=True)aspiration_schema.add_field('description', label='DescStr', hidden=True)aspiration_schema.add_field('auto_select', label='Auto Select', hidden=True)aspiration_schema.add_field('simId', label='SimId', hidden=True)with aspiration_schema.add_view_cheat('aspirations.complete_aspiration', label='Complete') as cheat:
    cheat.add_token_param('aspiration_uid')
    cheat.add_token_param('simId')with aspiration_schema.add_has_many('objectives', GsiGridSchema, label='Objectives') as sub_schema:
    sub_schema.add_field('objective', label='Objective')
    sub_schema.add_field('objective_iterations_complete', label='Iterations Complete')
    sub_schema.add_field('objective_iterations_required', label='Iterations Required')
    sub_schema.add_field('objective_complete', label='Completed')
@GsiHandler('aspiration_view', aspiration_schema)
def generate_aspiration_view_data(sim_id:int=None):
    sim_info = services.sim_info_manager().get(sim_id)
    aspiration_tracker = sim_info.aspiration_tracker
    all_aspirations = []
    if aspiration_tracker is None:
        return all_aspirations
    aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
    for aspiration_id in aspiration_manager.types:
        aspiration = aspiration_manager.get(aspiration_id)
        aspiration_data = {}
        aspiration_data['aspiration'] = str(aspiration)
        aspiration_data['aspiration_uid'] = int(aspiration.guid64)
        if issubclass(aspiration, Aspiration):
            aspiration_data['display_name'] = str(hex(aspiration.display_name.hash))
            aspiration_data['description'] = str(hex(aspiration.descriptive_text.hash))
            aspiration_data['auto_select'] = str(aspiration)
        aspiration_data['aspiration_complete'] = False
        aspiration_data['objectives'] = []
        aspiration_data['simId'] = str(sim_id)
        if aspiration_tracker.milestone_completed(aspiration):
            aspiration_data['aspiration_complete'] = True
        completion_count = aspiration_tracker.get_milestone_completion_count(aspiration)
        aspiration_data['aspiration_completion_count'] = completion_count if completion_count is not None else "Doesn't Track"
        for objective in aspiration_tracker.get_objectives(aspiration):
            objective_data = {}
            objective_data['objective'] = str(objective)
            objective_data['objective_iterations_complete'] = aspiration_tracker.get_last_updated_value_for_objective(objective)
            objective_data['objective_iterations_required'] = objective.goal_value()
            objective_data['objective_complete'] = aspiration_tracker.objective_completed(objective)
            aspiration_data['objectives'].append(objective_data)
        all_aspirations.append(aspiration_data)
    return all_aspirations
aspiration_event_schema = GsiGridSchema(label='Aspiration Events')aspiration_event_schema.add_field('sim', label='Sim', width=2)aspiration_event_schema.add_field('event', label='Event', width=2)with aspiration_event_schema.add_has_many('Objectives Processed', GsiGridSchema) as sub_schema:
    sub_schema.add_field('milestone', label='Aspiration', width=2)
    sub_schema.add_field('completed', label='Completed')
    sub_schema.add_field('test_type', label='Test', width=2)
    sub_schema.add_field('test_result', label='Result', width=3)archiver = GameplayArchiver('aspiration_events', aspiration_event_schema)
def archive_aspiration_event_set(event_data):
    archiver.archive(data=event_data)
