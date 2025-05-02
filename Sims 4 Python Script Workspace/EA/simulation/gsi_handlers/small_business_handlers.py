import servicesfrom business.business_enums import BusinessType, SmallBusinessAttendanceSaleModefrom clubs.club_tuning import ClubRuleCriteriaAge, ClubRuleCriteriaRelationship, ClubCriteriaCategory, MaritalStatus, ClubRuleCriteriaCareer, ClubRuleCriteriaHouseholdValue, HouseholdValueCategory, ClubRuleCriteriaTrait, ClubRuleCriteriaSkill, ClubRuleCriteriaCareSimTypeSupervised, CareSimType, ClubRuleCriteriaFameRank, FameRankfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom objects import ALL_HIDDEN_REASONSfrom sims.sim_info_types import Agefrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom small_business.small_business_tuning import SmallBusinessTunablessmall_business_managers_schema = GsiGridSchema(label='Small Business Managers')small_business_managers_schema.add_field('sim_id', label='Sim Id', width=0.5, unique_field=True)small_business_managers_schema.add_field('sim_name', label='Sim Name', width=0.5)small_business_managers_schema.add_field('small_business_name', label='Small Business Name', width=0.5)small_business_managers_schema.add_field('zone_id', label='ZoneID', width=0.5)small_business_managers_schema.add_field('is_open', label='Open', width=0.25)small_business_managers_schema.add_field('time_since_open', label='Time Since Open', width=0.5)small_business_managers_schema.add_field('star_rating_value', label='Star Value', type=GsiFieldVisualizers.FLOAT, width=0.25)small_business_managers_schema.add_field('star_rating', label='Star', type=GsiFieldVisualizers.INT, width=0.25)small_business_managers_schema.add_field('funds', label='Funds', type=GsiFieldVisualizers.FLOAT, width=0.25)small_business_managers_schema.add_field('daily_revenue', label='Daily Revenue', type=GsiFieldVisualizers.FLOAT, width=0.25)small_business_managers_schema.add_field('attendance_sale_mode', label='Attendance Sale Mode', width=0.5)small_business_managers_schema.add_field('is_light_retail_enabled', label='Light Retail Enabled', width=0.5)small_business_managers_schema.add_field('hourly_fee', label='Hourly Fee', width=0.25)small_business_managers_schema.add_field('entry_fee', label='Entry Fee', width=0.25)small_business_managers_schema.add_field('lifetime_revenue', label='Lifetime Revenue', width=0.25)with small_business_managers_schema.add_has_many('business_activities', GsiGridSchema, label='Business Rules') as sub_schema:
    sub_schema.add_field('group', label='Group', width=0.5)
    sub_schema.add_field('affordances', label='Affordances')with small_business_managers_schema.add_has_many('target_customer_rules', GsiGridSchema, label='Target Customers') as sub_schema:
    sub_schema.add_field('category', label='Category', width=0.5)
    sub_schema.add_field('restriction', label='Restriction')
    sub_schema.add_field('required', label='Required?', width=0.25)
    sub_schema.add_field('supervised', label='Supervised?', width=0.25)with small_business_managers_schema.add_has_many('customer_data', GsiGridSchema, label='Customers') as sub_schema:
    sub_schema.add_field('sim_id', label='SimID', width=0.5)
    sub_schema.add_field('sim_name', label='SimName', width=0.5)
    sub_schema.add_field('sim_age', label='SimAge', width=0.5)
    sub_schema.add_field('star_rating_value', label='StarValue', type=GsiFieldVisualizers.FLOAT, width=0.5)
    sub_schema.add_field('star_rating', label='Stars', type=GsiFieldVisualizers.INT, width=0.5)
    sub_schema.add_field('buff_bucket_totals', label='Buff Bucket', width=1.5)
    sub_schema.add_field('jobs', label='Jobs', width=1)
    sub_schema.add_field('roles', label='Roles', width=1)
    sub_schema.add_field('remaining_time', label='Remaining Time', width=0.5)
    sub_schema.add_field('time_passed', label='Time Passed', width=0.5)with small_business_managers_schema.add_has_many('employee_data', GsiGridSchema, label='Employees') as sub_schema:
    sub_schema.add_field('sim_id', label='SimID', width=0.5)
    sub_schema.add_field('sim_name', label='SimName', width=0.5)
    sub_schema.add_field('sim_age', label='SimAge', width=0.5)
    sub_schema.add_field('careers', label='Careers', width=1.5)with small_business_managers_schema.add_has_many('boons_and_bumps', GsiGridSchema, label='Boons & Bumps') as sub_schema:
    sub_schema.add_field('event_name', label='Name', width=1)
    sub_schema.add_field('event_default_cooldown', label='Default Cooldown (hours)', width=0.5)
    sub_schema.add_field('event_fired', label='Fired?', width=0.25)
    sub_schema.add_field('event_remaining_cooldown', label='Remaining Cooldown (hours)', width=0.5)with small_business_managers_schema.add_has_many('other_data', GsiGridSchema, label='Misc') as sub_schema:
    sub_schema.add_field('key', label='Data Name', width=0.5)
    sub_schema.add_field('value', label='Data Value')with small_business_managers_schema.add_view_cheat('business.set_open_small_business true', label='Open', dbl_click=True) as cheat:
    cheat.add_token_param('sim_id')with small_business_managers_schema.add_view_cheat('business.set_open_small_business false', label='Close', dbl_click=True) as cheat:
    cheat.add_token_param('sim_id')with small_business_managers_schema.add_view_cheat('business.sell_small_business', label='Sell', dbl_click=True) as cheat:
    cheat.add_token_param('sim_id')
@GsiHandler('small_business_managers', small_business_managers_schema)
def generate_small_business_service_data(zone_id:int=None):
    business_service = services.business_service()
    business_manager_data = []
    sim_info_manager = services.sim_info_manager()

    def _construct_small_business_manager_gsi_data(business_zone_id, small_business_manager, business_tracker=None):
        owner_sim_info = sim_info_manager.get(small_business_manager.owner_sim_id) if small_business_manager is not None else None
        income_data = small_business_manager.small_business_income_data
        sim_name = str(owner_sim_info) if owner_sim_info is not None and str(owner_sim_info) else '<Unnamed Sim>'
        sim_name = sim_name + ' (NPC)' if owner_sim_info.is_npc else sim_name
        small_business_manager_entry = {'sim_id': str(owner_sim_info.sim_id) if owner_sim_info.sim_id is not None else 'N/A', 'sim_name': sim_name, 'small_business_name': small_business_manager.name, 'zone_id': str(hex(business_zone_id)), 'is_open': 'x' if small_business_manager.is_open else '', 'time_since_open': str(small_business_manager.get_timespan_since_open()), 'star_rating_value': small_business_manager._star_rating_value, 'star_rating': small_business_manager.get_star_rating(), 'funds': str(small_business_manager.funds.money), 'daily_revenue': small_business_manager.daily_revenue, 'attendance_sale_mode': str(SmallBusinessAttendanceSaleMode(income_data.attendance_sale_mode)).split('.')[1], 'is_light_retail_enabled': 'Yes' if income_data.is_light_retail_enabled else 'No', 'hourly_fee': income_data.get_hourly_fee(), 'entry_fee': income_data.get_entry_fee(), 'lifetime_revenue': income_data.get_total_revenue()}
        other_data = [{'key': 'daily_items_sold', 'value': str(small_business_manager._daily_items_sold)}, {'key': 'markup_multiplier', 'value': str(small_business_manager._markup_multiplier)}, {'key': 'advertising_type', 'value': small_business_manager.get_advertising_type_for_gsi()}, {'key': 'quality_setting', 'value': small_business_manager.quality_setting.name}, {'key': 'session_customers_served', 'value': str(small_business_manager._customer_manager.session_customers_served)}, {'key': 'lifetime_customers_served', 'value': str(small_business_manager._customer_manager.lifetime_customers_served)}, {'key': 'funds_category_tracker', 'value': str(small_business_manager._funds_category_tracker)}, {'key': 'buff_bucket_totals', 'value': str(small_business_manager._buff_bucket_totals)}, {'key': 'open_time', 'value': str(small_business_manager._open_time)}, {'key': 'total_open_hours', 'value': str(small_business_manager.total_open_hours)}]
        if business_tracker is not None:
            other_data.append({'key': 'additional_employee_slots (tracker data)', 'value': str(business_tracker._additional_employee_slots)})
            other_data.append({'key': 'additional_markup_multiplier(tracker data)', 'value': business_tracker.additional_markup_multiplier})
            other_data.append({'key': 'additional_customer_count(tracker data)', 'value': business_tracker.addtitional_customer_count})
        small_business_manager_entry['other_data'] = other_data
        customer_data = []
        for (customer_sim_id, business_customer_data) in small_business_manager._customer_manager._customers.items():
            customer_sim_info = sim_info_manager.get(customer_sim_id)
            sim = customer_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            jobs = []
            roles = []
            remaining_times = []
            buff_buckets_totals = ''
            if small_business_manager.is_open:
                situation_manager = services.get_zone_situation_manager(zone_id=business_zone_id)
                for situation in situation_manager.get_situations_sim_is_in(sim):
                    roles.append(str(situation.get_current_role_state_for_sim(sim).__name__))
                    jobs.append(str(situation.get_current_job_for_sim(sim).__name__))
                    remaining_times.append(str(situation.get_remaining_time() if situation.get_remaining_time() else 'No Time Limit'))
                    buff_buckets_totals = 'None' if len(business_customer_data.buff_bucket_totals) == 0 else '\n'.join(['{}={}'.format(key, value) for (key, value) in business_customer_data.buff_bucket_totals.items()])
            entry = {'sim_id': str(customer_sim_id), 'sim_name': str(customer_sim_info.full_name), 'sim_age': str(customer_sim_info.age), 'star_rating_value': business_customer_data.get_star_rating_stat_value(), 'star_rating': business_customer_data.get_star_rating(), 'buff_bucket_totals': buff_buckets_totals, 'jobs': ','.join(jobs), 'roles': ','.join(roles), 'remaining_time': ','.join(remaining_times), 'time_passed': str(business_customer_data.time_passed)}
            customer_data.append(entry)
        small_business_manager_entry['customer_data'] = customer_data
        employee_data = []
        for (employee_sim_id, business_employee_data) in small_business_manager._employee_manager._employees.items():
            employee_sim_info = sim_info_manager.get(employee_sim_id)
            entry = {'sim_id': str(employee_sim_id), 'sim_name': str(employee_sim_info.full_name), 'sim_age': str(employee_sim_info.age), 'careers': str([type(career).__name__ for career in employee_sim_info.careers.values()])}
            employee_data.append(entry)
        small_business_manager_entry['employee_data'] = employee_data
        business_activities = []
        for rule in set(small_business_manager.customer_rules):
            business_activities.append({'group': rule.action.__name__, 'affordances': [affordance.__name__ for affordance in rule.action()]})
        small_business_manager_entry['business_activities'] = business_activities
        target_customer_rules = []
        for rule in small_business_manager.attendance_criteria:
            category = str(ClubCriteriaCategory(rule.CATEGORY).name)
            restriction = str(rule)
            if isinstance(rule, ClubRuleCriteriaAge):
                restriction = [Age(age).name for age in rule.ages]
            if isinstance(rule, ClubRuleCriteriaRelationship):
                restriction = MaritalStatus(rule.marital_status).name
            if isinstance(rule, ClubRuleCriteriaCareer):
                restriction = [career.__name__ for career in rule.careers]
            if isinstance(rule, ClubRuleCriteriaHouseholdValue):
                restriction = HouseholdValueCategory(rule.household_value).name
            if isinstance(rule, ClubRuleCriteriaTrait):
                restriction = [trait.__name__ for trait in rule.traits]
            if isinstance(rule, ClubRuleCriteriaSkill):
                restriction = [skill.__name__ for skill in rule.skills]
            if isinstance(rule, ClubRuleCriteriaCareSimTypeSupervised):
                restriction = [CareSimType(care_type).name for care_type in rule.care_sim_type_requirements]
            if isinstance(rule, ClubRuleCriteriaFameRank):
                restriction = [FameRank(rank).name for rank in rule.fame_rank_requirements]
            target_customer_rules.append({'category': category, 'restriction': str(restriction), 'required': 'Yes' if rule.required else 'No', 'supervised': 'Yes' if rule.supervised else 'No'})
        small_business_manager_entry['target_customer_rules'] = target_customer_rules
        events = []
        adventures_dict = SmallBusinessTunables.BUSINESS_EVENTS_INTERACTION.get_adventures()
        if owner_sim_info.adventure_tracker:
            moment_dict = owner_sim_info.adventure_tracker._adventure_cooldowns[SmallBusinessTunables.BUSINESS_EVENTS_INTERACTION.interaction.guid64]
            for (title, adventures) in adventures_dict.items():
                for adventure in adventures:
                    for (adventure_moment_key, adventure_moment_data) in adventure._tuned_values._adventure_moments.items():
                        did_event_fire = adventure_moment_key in moment_dict
                        entry = {'event_name': str(adventure_moment_key), 'event_default_cooldown': str(adventure_moment_data.sim_specific_cooldown), 'event_fired': str(did_event_fire), 'event_remaining_cooldown': str((moment_dict[adventure_moment_key] - services.time_service().sim_now).in_hours() if did_event_fire else '-')}
                        events.append(entry)
        small_business_manager_entry['boons_and_bumps'] = events
        return small_business_manager_entry

    for business_tracker in business_service.business_trackers_gen():
        for (sim_id, business_manager) in business_tracker.zoneless_business_managers.items():
            if business_manager.business_type == BusinessType.SMALL_BUSINESS:
                business_manager_data.append(_construct_small_business_manager_gsi_data(0, business_manager, business_tracker))
    for business_tracker in business_service.business_trackers_gen():
        for (zone_id, business_manager) in business_tracker.business_managers.items():
            if business_manager.business_type == BusinessType.SMALL_BUSINESS:
                business_manager_data.append(_construct_small_business_manager_gsi_data(zone_id, business_manager, business_tracker))
    return business_manager_data
small_business_archiver_schema = GsiGridSchema(label='Small Business Archive')small_business_archiver_schema.add_field('event_from', label='EventFrom', width=0.5)small_business_archiver_schema.add_field('sim_id', label='SimID', width=1)small_business_archiver_schema.add_field('sim_name', label='SimName', width=1)small_business_archiver_schema.add_field('event_description', label='Reason', width=2)small_business_archiver = GameplayArchiver('small_business_archiver', small_business_archiver_schema, add_to_archive_enable_functions=True)
def archive_small_business_event(event_from, sim, event_description, sim_id=None):
    entry = {'event_from': event_from, 'sim_id': str(sim.id) if sim is not None else str(sim_id), 'sim_name': sim.full_name if sim is not None else '', 'event_description': event_description}
    small_business_archiver.archive(data=entry)
