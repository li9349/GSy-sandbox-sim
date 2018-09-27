from source.data_methods import *
from plots import *
from grid_config import ConfigurationMixin
import numpy as np

import logging
data_log = logging.getLogger('data')


class Data(ConfigurationMixin, object):
    def __init__(self):
        super().__init__()
        """initialise data sets"""
        data_type = "data_set_time_series"  # random_1_step, custom_load_profiles, data_set_time_series

        if data_type == 'random_1_step':
            """ check whether the market platform can complete a full run, using random numbers of simplicity
                -> do not use for testing, since input is all random, just for bug finding"""

            self.load_list = 1.8*np.random.rand(self.num_households)
            self.pv_gen_list = np.random.rand(self.num_households)
            self.ess_list = [[np.random.randint(0, 1) for _ in range(2)] for _ in range(self.num_households)]
            self.electrolyzer_list = [None for _ in range(self.num_households)]
            assert len(self.load_list) == len(self.ess_list) == len(self.pv_gen_list)

            self.agent_data_array = [self.load_list, self.pv_gen_list, self.ess_list]

            print(self.agent_data_array)

            self.agent_data_array = np.asarray(self.agent_data_array)

        elif data_type == 'custom_load_profiles':
            """ create simple (non random) test-profiles, currently also 1 step only
                -> use for testing of simply grids and hypotheses, check whether strategies are behaving"""
            self.load_list = [0, 0, 100, 10]
            self.pv_gen_list = [3, None, 3, None]
            self.electrolyzer_list = [None, None, None, None]
            self.ess_list = [[0.5, 5], [0.5, 5], [0, 5], [0, 5]]
            assert len(self.load_list) == len(self.ess_list) == len(self.pv_gen_list)

        elif data_type == 'data_set_time_series':
            """ run model with real data, check if the strategies are performing, and for research results"""
            self.load_array = self.get_load_profiles()
            self.pv_gen_array = self.get_pv_gen_profiles()
            self.ess_list = self.ess_characteristics_list

            self.electrolyzer_list = self.get_electrolyzer_profiles()

            assert len(self.load_array) == self.num_households
            assert len(self.pv_gen_array) == self.num_pv_panels
            assert len(self.ess_list) == self.num_households_with_ess

            assert len(self.electrolyzer_list) == self.num_steps
            assert len(self.load_array[0]) == self.num_steps
            assert len(self.pv_gen_array[0]) == self.num_steps

            self.agent_data_array = self.fill_in_classification_array()

        else:
            data_log.error("data type not found")
            exit()

        if self.utility_presence is True:
            self.utility_pricing_profile = self.get_utility_profile()
            assert len(self.utility_pricing_profile) == self.num_steps
            self.utility_pricing_profile = np.asarray(self.utility_pricing_profile)

            if self.negative_pricing is False:
                self.utility_pricing_profile[self.utility_pricing_profile < 0] = 0

        """ post evaluation variables, used by plots """

        self.soc_list_over_time = np.zeros([self.num_households_with_ess, self.num_steps])
        self.soc_deficit_overflow_over_time = np.zeros([self.num_households_with_ess, self.num_steps, 2])

    def plots(self):
        soc_over_time(self.num_steps, self.soc_list_over_time)
        households_deficit_overflow(self.num_steps, self.soc_deficit_overflow_over_time)
        show()

    def get_load_profiles(self):
        """ loading in load profiles """
        load_list = csv_read_load_file(self.num_households, self.household_loads_folder)

        """ load is in minutes, now convert to intervals """
        for i in range(len(load_list)):
            load_list[i] = load_list[i][0::self.market_interval]
            # TODO: add all consumption in 15 to element instead of naive sampling

            assert len(load_list[i]) == self.num_steps

        """ manual tuning of data can happen here """
        load_array = np.array(load_list)
        load_array[np.isnan(load_array)] = 0
        # TODO: link to german consumption rates?
        for i in range(len(load_list)):
            max_element = np.amax(load_array[i])
            if max_element > 1:
                load_array[i] = load_array[i] / max_element
                print(max_element)

        load_array = load_array * 0.5
        return load_array

    def get_pv_gen_profiles(self):
        """ loading in load profiles """
        # TODO: currently, all agents get the same profile :( """
        pv_gen_list = csv_read_pv_output_file(self.num_pv_panels, self.pv_output_profile)
        pv_gen_array = np.array(pv_gen_list)

        """ manual tuning of data can happen here"""
        pv_gen_array = pv_gen_array * 1
        return pv_gen_array

    def get_utility_profile(self):
        """ loads in utility pricing profile """
        utility_profile_dict = csv_read_utility_file(self.utility_profile, self.num_steps)

        # utility_profile_dict = utility_profile_dict[0::self.market_interval]
        return utility_profile_dict

    def get_electrolyzer_profiles(self):
        """ loading in load profiles """
        electrolyzer_list = csv_read_electrolyzer_profile(self.fuel_station_load)

        electrolyzer_list = electrolyzer_list[0:self.num_steps]
        return electrolyzer_list

    def fill_in_classification_array(self):
        """ fill_in_classification_array according to configuration Mixin """
        agent_data_array = self.classification_array

        load = 0
        pv = 0
        ess = 0
        for agent in range(len(self.classification_array)):
            if self.classification_array[agent][0]:
                agent_data_array[agent][0] = self.load_array[load]
                load += 1
            else:
                agent_data_array[agent][0] = None

            if self.classification_array[agent][1]:
                agent_data_array[agent][1] = self.pv_gen_array[pv]
                pv += 1
            else:
                agent_data_array[agent][1] = None

            if self.classification_array[agent][2]:
                agent_data_array[agent][2] = self.ess_list[ess]
                ess += 1
            else:
                agent_data_array[agent][2] = None

        return agent_data_array



if __name__ == "__main__":
    data = Data()
    print('fuel station load: ', data.fuel_station_load)
    print('utility prices data: ', data.utility_profile)
    print('household load data set: ', data.household_loads_folder)
    print('total ess storage capacity: %d kWh' % data.total_ess_capacity)

    # plot_avg_load_profile(data.num_steps, data.load_array)
    # plot_avg_pv_profile(data.num_steps, data.pv_gen_array)
    # plot_fuel_station_profile(data.num_steps, data.electrolyzer_list)
    total_generation_vs_consumption(data.num_steps, data.pv_gen_array, data.load_array)
    show()