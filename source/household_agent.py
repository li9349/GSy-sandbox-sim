from source.devices import *
from source.wallet import Wallet
from source.strategies.simple_strategy import simple_strategy
from source.strategies.smart_ess_strategy import smart_ess_strategy

from mesa import Agent
import scipy.optimize as optimize
import logging
import numpy as np

house_log = logging.getLogger('run_microgrid.house')


class HouseholdAgent(Agent):
    """ Household agents are created through this class """
    def __init__(self, _unique_id, model):
        super().__init__(_unique_id, self)
        house_log.info('agent%d created', _unique_id)

        self.id = _unique_id
        self.model = model
        self.data = self.model.data

        """ Loading in data """
        self.load_data = self.model.data.agent_data_array[self.id][0]
        self.pv_data = self.model.data.agent_data_array[self.id][1]
        self.ess_data = self.model.data.agent_data_array[self.id][2]

        self.load_on_step = 0
        self.pv_production_on_step = 0
        self.ess_demand_on_step = 0

        """ Creation of device objects, depending what Data class assigns them """
        self.devices = {}
        self.has_load = False
        self.has_pv = False
        self.has_ess = False

        if self.load_data is not None:
            self.load = GeneralLoad(self, self.load_data)
            self.devices['GeneralLoad'] = self.load
            self.has_load = True

        if self.pv_data is not None:
            self.pv = PVPanel(self, self.pv_data)
            self.devices['PV'] = self.pv
            self.has_pv = True

        if self.ess_data is not None:
            self.ess = ESS(self, self.ess_data)
            self.devices['ESS'] = self.ess
            self.has_ess = True

        else:
            self.soc_actual = 0

        house_log.info(self.devices)

        """standard house attributes"""
        self.wallet = Wallet(_unique_id)

        """ trading """
        if self.has_ess is True:
            self.selected_strategy = 'smart_ess_strategy'

        if self.has_ess is False:
            self.selected_strategy = 'simple_strategy'

        self.bidding_method = "price_curve"
        # self.bidding_method = "utility_function"

        """ Initialise trade """
        self.trading_state = None
        self.bids = None
        self.offers = None
        self.energy_trade_flux = 0
        self.net_energy_in = None
        self.overflow = None
        self.deficit = None
        self.net_energy_in_simple_strategy = 0

    def state_update_from_devices(self):
        """ updates the household agent on state of devices """
        current_step = self.model.step_count

        if self.has_load is True:
            self.load_on_step = self.load.get_load(current_step)

        if self.has_pv is True:
            self.pv_production_on_step = self.pv.get_generation(current_step)

    def pre_auction_round(self):
        """ each agent makes a step here, before auction step"""

        self.state_update_from_devices()
        for device in self.devices:
            self.devices[device].uniform_call_to_device(self.model.step_count)

        """ 
            STRATEGIES 
            how to come up with price-quantity points on the auction platform (aka the market)
        """
        if self.has_ess is True and self.selected_strategy == 'smart_ess_strategy':
            smart_ess_strategy(self)

        elif self.selected_strategy == 'simple_strategy':
            simple_strategy(self)

        elif self.selected_strategy == 'no_trade':
            self.offers = None
            self.bids = None

        self.announce_bid_and_offers()

    def post_auction_round(self):
        """ after auctioneer gives clearing signal """

        self.energy_trade_flux = sum(self.model.auction.who_gets_what_dict[self.id])
        self.net_energy_in = self.pv_production_on_step + self.load_on_step + self.energy_trade_flux

        assert self.pv_production_on_step >= 0
        assert self.load_on_step <= 0

        """ update ESS and unmatched loads """
        if self.has_ess is True:
            self.overflow, self.deficit = self.ess.update_ess_state(self.net_energy_in)

        else:
            if self.net_energy_in > 0:
                self.overflow = abs(self.net_energy_in)
                self.deficit = 0
            else:
                self.overflow = 0
                self.deficit = abs(self.net_energy_in)

        """ data logging """
        self.data.overflow_over_time[self.id][self.model.step_count] = self.overflow
        self.data.deficit_over_time[self.id][self.model.step_count] = self.deficit


    def announce_bid_and_offers(self):
        """ announces bid to auction agent by appending to bid list """
        house_log.info('house%d is %s', self.id, self.trading_state)

        if self.trading_state == 'supplying':
            for offer in self.offers:
                self.model.auction.offer_list.append(offer)

        elif self.trading_state == 'buying':
            for bid in self.bids:
                self.model.auction.bid_list.append(bid)


