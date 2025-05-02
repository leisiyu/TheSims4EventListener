from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *import servicesimport timeINCREASE_STEP = 0.01DECREASE_STEP = 0.005SIM_DEBT_LIST_MAX_LEN = 100SLEEP_UPPER_BOUND = 0.1
class SimDebtSimulator:
    sim_debt_target = 0.0
    last_avg_debt = 0.0
    sim_debt_list = list()
    sim_debt_cycle_counter = 0
    last_sleep_delta = 0.0

    @staticmethod
    def push_sim_debt(debt:'float') -> 'None':
        SimDebtSimulator.sim_debt_list.append(debt)
        if len(SimDebtSimulator.sim_debt_list) > SIM_DEBT_LIST_MAX_LEN:
            SimDebtSimulator.sim_debt_list.pop(0)
        SimDebtSimulator.sim_debt_cycle_counter += 1
        SimDebtSimulator.sim_debt_cycle_counter %= SIM_DEBT_LIST_MAX_LEN

    @staticmethod
    def sim_debt_average() -> 'float':
        sim_debt_list_len = len(SimDebtSimulator.sim_debt_list)
        if sim_debt_list_len > 0:
            return sum(SimDebtSimulator.sim_debt_list)/sim_debt_list_len
        return 0

    @staticmethod
    def try_simulate_sim_debt() -> 'None':
        if SimDebtSimulator.sim_debt_target > 0.0:
            time_service = services.time_service()
            current_sim_debt = time_service.get_simulator_debt() if time_service is not None else 0
            SimDebtSimulator.push_sim_debt(current_sim_debt)
            sleep_delta = SimDebtSimulator.last_sleep_delta
            if SimDebtSimulator.sim_debt_cycle_counter == 0:
                sim_debt_average = SimDebtSimulator.sim_debt_average()
                if sim_debt_average < SimDebtSimulator.sim_debt_target:
                    if sim_debt_average <= SimDebtSimulator.last_avg_debt:
                        sleep_delta += INCREASE_STEP
                elif sim_debt_average > SimDebtSimulator.last_avg_debt:
                    sleep_delta -= DECREASE_STEP
                SimDebtSimulator.last_avg_debt = sim_debt_average
            sleep_delta = min(max(sleep_delta, 0), SLEEP_UPPER_BOUND)
            SimDebtSimulator.last_sleep_delta = sleep_delta
            if sleep_delta > 0:
                time.sleep(sleep_delta)
