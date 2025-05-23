from distributor.system import Distributorfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionSource, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims.aging.aging_element import ChangeAgeElementimport distributorimport distributor.opsimport servicesimport sims4.loglogger = sims4.log.Logger('Baby')
def baby_age_up(sim_info):
    bassinet = services.object_manager().get(sim_info.id)
    if bassinet is None:
        return
    middle_bassinet = bassinet.replace_for_age_up()
    if middle_bassinet is None:
        return
    baby_cloth_tuple = (middle_bassinet.baby_cloth, sim_info.sim_id)
    baby_skin_tone_op = distributor.ops.SetBabySkinTone(baby_cloth_tuple)
    Distributor.instance().add_op(middle_bassinet, baby_skin_tone_op)

    def _on_spawn(sim):
        affordance = bassinet.get_age_up_addordance()
        aop = AffordanceObjectPair(affordance, middle_bassinet, affordance, None, is_baby_age_up=True)
        context = InteractionContext(sim, InteractionSource.SCRIPT, Priority.Critical, insert_strategy=QueueInsertStrategy.NEXT)
        result = aop.test_and_execute(context)
        if not result:
            logger.error('Failed to run baby age up interaction: {}', result, owner='jjacobson')

    infant_initial_location = middle_bassinet.infant_initial_location
    ChangeAgeElement.spawn_for_age_up(sim_info, infant_initial_location.transform.translation, spawn_action=_on_spawn, sim_location=middle_bassinet.infant_initial_location)
