import numpy as np
import source.const as const

""" Grid Configuration """


class ConfigurationMixin:
    def __init__(self):
        """ Configuration of the grid Mixin Class"""

        """ Simulation environment """
        self.auction_type = const.auction_type
        self.num_days = const.num_steps * const.market_interval / 60 / 24
        self.market_interval = const.market_interval  # minutes
        self.num_steps = const.num_steps

        """ Households basic configuration """
        self.consumers = 3
        self.prosumers_with_only_pv = 0
        self.prosumers_with_ess = 0
        self.prosumers_with_pv_and_ess = 0

        self.num_households = self.consumers + self.prosumers_with_only_pv + self.prosumers_with_ess + \
            self.prosumers_with_pv_and_ess

        self.classification_array = []

        """ consumers"""
        for agent in range(self.consumers):
            self.classification_array.append([True, False, False])

        """ prosumers with only PV """
        for agent in range(self.prosumers_with_only_pv):
            self.classification_array.append([True, True, False])

        """ prosumers with only ESS"""
        for agent in range(self.prosumers_with_ess):
            self.classification_array.append([True, False, True])

        """ prosumers with both PV and ESS"""
        for agent in range(self.prosumers_with_pv_and_ess):
            self.classification_array.append([True, True, True])

        """ Electrolyzer """
        self.fuel_station_load = 'ts_h2load_kg_15min_classverysmall_2015.csv'

        """ Utility presence """
        self.utility_presence = True
        self.negative_pricing = True
        self.dynamical_pricing = False
        self.utility_profile = 'ts_intradayPlusEeg_EURperkWh_15min_2015.csv'

        """ Household loads """
        self.household_loads_folder = 'household_load_profiles_SMART'
        self.num_households_with_consumption = self.num_households

        """ PV """
        self.num_pv_panels = self.prosumers_with_only_pv + self.prosumers_with_pv_and_ess
        self.pv_output_profile = 'ts_pv_kWperkWinstalled_15min_2015.csv'

        """ ESS """
        self.num_households_with_ess = self.prosumers_with_ess + self.prosumers_with_pv_and_ess
        max_capacity_list = np.full(self.num_households_with_ess, 3)
        initial_capacity_list = np.full(self.num_households_with_ess, 3)
        self.ess_characteristics_list = []

        for battery in range(self.num_households_with_ess):
            max_capacity = max_capacity_list[battery]
            initial_soc = initial_capacity_list[battery]
            self.ess_characteristics_list.append([initial_soc, max_capacity])
        self.total_ess_capacity = sum(max_capacity_list)

        print(self.ess_characteristics_list)


if __name__ == "__main__":
    config = ConfigurationMixin()
    print('fuel station load: ', config.fuel_station_load)
    print('utility prices data: ', config.utility_profile)
    print('household load dataset: ', config.household_loads_folder)
    print('total ess storage capacity: ', config.total_ess_capacity)
