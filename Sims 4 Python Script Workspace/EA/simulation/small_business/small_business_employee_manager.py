import itertoolsfrom business.business_enums import BusinessEmployeeTypefrom business.business_employee import BusinessEmployeeDatafrom business.business_employee_manager import BusinessEmployeeManagerfrom sims.sim_info import SimInfofrom small_business.small_business_tuning import SmallBusinessTunablesfrom collections import namedtuplefrom clubs.club_tuning import TunableClubRuleSnippetfrom statistics.static_commodity import StaticCommodity, SituationStaticCommodityDataimport servicesimport sims4.logimport mathlogger = sims4.log.Logger('SmallBusinessEmployees', default_owner='mmikolajczyk')EmployeeAssignment = namedtuple('EmployeeAssignment', ['sim_id', 'encouragement', 'rules'])
class SmallBusinessEmployeeManager(BusinessEmployeeManager):

    def __init__(self, business_manager):
        super().__init__(business_manager)
        self._owner_id = business_manager._owner_sim_id
        self._employee_assignments = []
        self._had_employee_once = False
        self.employee_encouragement_name = 'SmallBusinessEmployeeEncouragement_'

    @property
    def had_employee_once(self) -> bool:
        return self._had_employee_once

    @property
    def has_employee_assignments(self) -> bool:
        return len(self._employee_assignments) > 0

    def force_had_employee_once(self, had_employee_once):
        self._had_employee_once = had_employee_once

    def on_zone_load(self):
        sim_info_manager = services.sim_info_manager()
        for (employee_type, employee_id_list) in self._employee_sim_ids.items():
            for employee_id in employee_id_list:
                sim_info = sim_info_manager.get(employee_id)
                if sim_info is not None:
                    self._employees[sim_info.sim_id] = BusinessEmployeeData(self, sim_info, employee_type)
        self._employee_sim_ids.clear()
        self.update_employees(add_career_remove_callback=True)
        for employee_assignment in self.get_employee_assignments_gen():
            rules_to_update = employee_assignment.rules.copy()
            self.update_employee_rules(employee_assignment.sim_id, rules_to_update)
        for employee_uniform in itertools.chain(self._employee_uniform_data_male.values(), self._employee_uniform_data_female.values()):
            self._send_employee_uniform_data(employee_uniform)
        if not self._business_manager.is_active_household_and_zone():
            return
        if self._business_manager.is_open:
            for sim_info in self.get_employees_on_payroll():
                career = self.get_employee_career(sim_info)
                if career is None:
                    self.on_employee_clock_out(sim_info)
                elif not any(owner_id == self._owner_id for owner_id in career._levels_per_owner.keys()):
                    self.on_employee_clock_out(sim_info)
                (clock_in_time, _) = self._employee_payroll[sim_info.sim_id]
                if clock_in_time is not None:
                    self._register_employee_callbacks(sim_info)
                    employee_data = self.get_employee_data(sim_info)
                    employee_data.add_career_buff()

    def transfer(self, new_owner_id:int):
        self._owner_id = new_owner_id
        self.add_employee_assignment(new_owner_id, replace_at_index=0)

    def add_employee_assignment(self, employee_id:int, replace_at_index=None):
        if any(employee_id == employee.sim_id for employee in self._employee_assignments):
            return
        if self._owner_id != employee_id:
            self._had_employee_once = True
        employee_encouragement_commodity = type(self.employee_encouragement_name + str(employee_id), (StaticCommodity, object), {'ad_data': 0})
        if replace_at_index is None:
            self._employee_assignments.append(EmployeeAssignment(sim_id=employee_id, encouragement=employee_encouragement_commodity, rules=[]))
        else:
            if len(self._employee_assignments) > 0:
                del self._employee_assignments[0]
            self._employee_assignments.insert(0, EmployeeAssignment(sim_id=employee_id, encouragement=employee_encouragement_commodity, rules=[]))

    def remove_employee_assignment(self, employee_id:int):
        for employee_assignment in self._employee_assignments:
            if employee_assignment.sim_id == employee_id:
                self._employee_assignments.remove(employee_assignment)
                return

    def add_employee_rule(self, employee_id:int, rule:TunableClubRuleSnippet):
        for employee in self._employee_assignments:
            if employee.sim_id == employee_id:
                self._add_employee_rule(employee, rule)
                return
        logger.error('Setting a rule for employee {} while they are not in employee data list', employee_id)

    def _add_employee_rule(self, employee_assignment, rule:TunableClubRuleSnippet):
        if rule.action is None:
            return
        static_commodity_data = SituationStaticCommodityData(employee_assignment.encouragement, 1)
        for affordance in rule.action():
            affordance.add_additional_static_commodity_data(static_commodity_data)
            self._business_manager.dirty_affordance(affordance)
        employee_assignment.rules.append(rule)

    def remove_employee_rule_affordance_data(self, rule, encouragment_commodity):
        static_commodity_data = SituationStaticCommodityData(encouragment_commodity, 1)
        for affordance in rule.action():
            affordance.remove_additional_static_commodity_data(static_commodity_data)
            self._business_manager.dirty_affordance(affordance)

    def update_employee_rules(self, employee_id:int, new_rules):
        employee_assignment = self.get_employee_assignment(employee_id)
        if employee_assignment is not None:
            for rule in employee_assignment.rules:
                self.remove_employee_rule_affordance_data(rule, employee_assignment.encouragement)
            employee_assignment.rules.clear()
            for rule in new_rules:
                self._add_employee_rule(employee_assignment, rule)
            self._business_manager.update_affordance_cache()

    def get_employee_rules_gen(self, employee_id:int):
        employee_assignment = self.get_employee_assignment(employee_id)
        if employee_assignment is not None:
            for rule in employee_assignment.rules:
                yield rule

    def get_employee_assignments_gen(self):
        for employee_assigment in self._employee_assignments:
            yield employee_assigment

    def get_employee_assignment(self, employee_id:int):
        for employee in self._employee_assignments:
            if employee_id == employee.sim_id:
                return employee

    def handle_event(self, sim_info, event, resolver):
        pass

    def get_employee_career_level(self, employee_sim_info):
        career = self.get_employee_career(employee_sim_info)
        if career is None:
            return
        elif self._owner_id in career._levels_per_owner.keys():
            return career.start_track.career_levels[career._levels_per_owner[self._owner_id]]

    def get_desired_career_level(self, sim_info, employee_type):
        return 0

    def _check_career_validity(self, career):
        return any(owner_id == self._owner_id for owner_id in career._levels_per_owner.keys())

    def add_employee(self, sim_info:SimInfo, employee_type:BusinessEmployeeType, is_npc_employee:bool=False):
        self.add_employee_assignment(sim_info.sim_id)
        super().add_employee(sim_info, employee_type, is_npc_employee)
        sim_info.relationship_tracker.add_relationship_bit(self._owner_id, SmallBusinessTunables.EMPLOYEE_RELBIT, force_add=True)

    def remove_employee(self, employee_info:SimInfo, is_quitting:bool=True):
        employee_assignment = self.get_employee_assignment(employee_info.sim_id)
        if employee_assignment is None:
            logger.error("Trying to remove an employee from a business but the employee doesn't belong to this business. {}", employee_info)
        self.remove_employee_assignment(employee_info.sim_id)
        super().remove_employee(employee_info, is_quitting=is_quitting)
        employee_info.relationship_tracker.remove_relationship_bit(self._owner_id, SmallBusinessTunables.EMPLOYEE_RELBIT)

    def remove_invalid_employee(self, sim_id):
        self.remove_employee_assignment(sim_id)
        super().remove_invalid_employee(sim_id)
        employee_info = services.sim_info_manager().get(sim_id)
        if employee_info is not None:
            employee_info.relationship_tracker.remove_relationship_bit(self._owner_id, SmallBusinessTunables.EMPLOYEE_RELBIT)

    def on_employee_career_promotion(self, sim_info):
        pass

    def on_employee_career_demotion(self, sim_info):
        pass

    def set_pay_level(self, sim_info, pay_level):
        career = self.get_employee_career(sim_info)
        if len(career.start_track.career_levels) > pay_level and pay_level >= 0:
            prev_pay_level = career.start_track.career_levels[career.get_career_level_for_owner(self._owner_id)]
            career.set_career_level(self._owner_id, pay_level)
            if self._business_manager.is_open:
                self.on_employee_clock_out(sim_info, career_level=prev_pay_level)
                self.on_employee_clock_in(sim_info)

    def get_outfit_index_for_employee(self, employee_sim_info) -> int:
        career = self.get_employee_career(employee_sim_info)
        if career is None:
            return -1
        return career.get_career_index(self._owner_id)

    def get_employee_wages(self, employee_sim_info):
        fake_salary_payment_relbit = SmallBusinessTunables.PERK_SETTINGS.fake_employee_payment
        employee_owner_rel_bits = services.relationship_service().get_all_bits(employee_sim_info.id, self._owner_id)
        if fake_salary_payment_relbit is not None and fake_salary_payment_relbit in employee_owner_rel_bits:
            return 0
        return super().get_employee_wages(employee_sim_info)
