from __future__ import annotationsfrom pivotal_moments.pivotal_moment import PivotalMoment, PivotalMomentActivationStatusfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemafrom situations.situation_types import SituationDisplayStyleimport servicesimport date_and_timefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *pivotal_moment_schema = GsiGridSchema(label='Pivotal Moments Manager')pivotal_moment_schema.add_field('piv_moment_id', label='Pivotal Moment Id')pivotal_moment_schema.add_field('piv_moment_name', label='Pivotal Moment Name')pivotal_moment_schema.add_field('activation_status', label='Activation Status')pivotal_moment_schema.add_field('drama_node_id', label='Drama Node Id')pivotal_moment_schema.add_field('drama_node_time', label='Drama Node Time Left (sim mins/hours)')pivotal_moment_schema.add_field('time_left', label='Cooldown Time left (sim mins/hours)')pivotal_moment_schema.add_field('situation', label='Situation Name')pivotal_moment_schema.add_field('trigger_reason', label='Trigger Reason')pivotal_moment_schema.add_field('situation_display_style', label='Style')with pivotal_moment_schema.add_has_many('conditional_actions', GsiGridSchema, label='Conditional Actions') as sub_schema:
    sub_schema.add_field('name', label='Name', width=3)
    sub_schema.add_field('satisfied', label='Satisfied', width=1)
    sub_schema.add_field('satisfied_conditions', label='Satisfied Conditions', width=4)
    sub_schema.add_field('unsatisfied_conditions', label='Unsatisfied Conditions', width=4)
@GsiHandler('pivotal_moments', pivotal_moment_schema)
def generate_pivotal_moments_data() -> 'List':
    tutorial_service = services.get_tutorial_service()
    situation_manager = services.get_zone_situation_manager()
    all_pivotal_moments = []
    if tutorial_service is None:
        return all_pivotal_moments
    pivotal_moment_list = tutorial_service._pivotal_moments
    if pivotal_moment_list is None:
        return all_pivotal_moments
    for (key, piv_moment_inst) in pivotal_moment_list.items():
        piv_moments_data = {}
        piv_moments_data['piv_moment_id'] = key
        piv_moments_data['piv_moment_name'] = piv_moment_inst.__class__.__name__
        piv_moments_data['activation_status'] = PivotalMomentActivationStatus(piv_moment_inst._activation_status).name
        piv_moments_data['drama_node_id'] = piv_moment_inst._drama_node_id
        piv_moments_data['drama_node_time'] = get_drama_node_time_remaining(piv_moment_inst)
        piv_moments_data['time_left'] = get_cooldown_time(piv_moment_inst)
        piv_moments_data['situation'] = str(situation_manager.try_get_situation_by_id(piv_moment_inst._situation_id))
        piv_moments_data['trigger_reason'] = get_trigger_reason(piv_moment_inst)
        piv_moments_data['situation_display_style'] = SituationDisplayStyle(piv_moment_inst.situation_to_start.display_style).name
        all_pivotal_moments.append(piv_moments_data)
        if piv_moment_inst._condition_manager is not None:
            piv_moments_data['conditional_actions'] = []
            for group in piv_moment_inst._condition_manager:
                group_entry = {}
                group_entry['name'] = str(group.conditional_action)
                group_entry['satisfied'] = group.satisfied
                group_entry['satisfied_conditions'] = ',\n'.join(str(c) for c in group if c.satisfied)
                group_entry['unsatisfied_conditions'] = ',\n'.join(str(c) for c in group if not c.satisfied)
                piv_moments_data['conditional_actions'].append(group_entry)
    return all_pivotal_moments

def get_drama_node_time_remaining(pivotal_moment:'PivotalMoment') -> 'str':
    if pivotal_moment._activation_status == PivotalMomentActivationStatus.SCHEDULED:
        drama_scheduler = services.drama_scheduler_service()
        drama_node = drama_scheduler.get_scheduled_node_by_uid(pivotal_moment._drama_node_id)
        if drama_node is not None:
            return str(drama_node.get_time_remaining())

def get_cooldown_time(pivotal_moment:'PivotalMoment') -> 'str':
    if pivotal_moment.cooldown is None:
        return
    elif pivotal_moment._activation_status == PivotalMomentActivationStatus.ON_COOLDOWN and pivotal_moment._cooldown_alarm_handle is not None:
        now = services.game_clock_service().now()
        return str(pivotal_moment._cooldown_alarm_handle.finishing_time - now)

def get_trigger_reason(pivotal_moment:'PivotalMoment') -> 'str':
    return str(pivotal_moment._triggering_condition_group)
