import logging
import numpy as np
method_logger = logging.getLogger('run_microgrid.methods')


def check_demand_supply(sorted_bid_list_, sorted_offer_list_):

    if len(sorted_bid_list_) is not 0:

        total_demand_ = np.sum([x[0] for x in sorted_bid_list_])
    else:
        total_demand_ = 0
    if len(sorted_offer_list_) is not 0:
        total_supply_ = np.sum([x[0] for x in sorted_offer_list_])
    else:
        total_supply_ = 0

    if total_demand_ >= total_supply_:
        method_logger.info('more supply than demand')
    else:
        method_logger.info('more demand than supply')
    return total_demand_, total_supply_


def pac_pricing(sorted_x_y_y_pairs_list_, sorted_bid_list, sorted_offer_list):
    """ trade matching according pay-as-clear pricing rule """
    clearing_quantity, clearing_price = clearing_quantity_calc(sorted_x_y_y_pairs_list_)
    # Give some feedback to the found clearing price and quantity.
    print('~~~\nclearing calculated. Clearing price: {} EUR/kWh; clearing quantity: {} kWh.\n~~~'.format(
        clearing_price, clearing_quantity))
    """ some checks """
    trade_pairs_pac_ = []
    total_turnover_ = 0

    if clearing_quantity is None:
        method_logger.warning("No clearing quantity or price was found")
        return clearing_quantity, clearing_price, None, None

    # filter only on executed segments that have no Non types (meaning) bid/offer but not offer/bid
    # first check if None, if not, check whether under clearing quantity
    executed_segment = [segment for segment in sorted_x_y_y_pairs_list_ if segment[0] is not None
                        and segment[0] <= clearing_quantity]

    total_turnover_ = clearing_quantity * clearing_price
    assert total_turnover_ >= 0 and clearing_quantity >= 0

    total_turnover_internally = 0
    clearing_quantity_internally = 0
    trade_pairs = []
    prev_segment_quantity = 0
    for segment in executed_segment:
        # reading out values from the executed trade segments
        trade_quantity = segment[0] - prev_segment_quantity
        clearing_quantity_internally += trade_quantity
        buyer_price = segment[1]
        seller_price = segment[2]
        buyer_id = segment[3]
        seller_id = segment[4]

        """ Open to market design matching algorithm """
        trade_payment = trade_quantity * clearing_price
        # set up trade pairs
        trade_pair = [seller_id, buyer_id, trade_quantity, trade_payment]
        if trade_pair[1] is None or trade_pair[2] == 0:
            continue

        trade_pairs_pac_.append(trade_pair)
        # finalise
        total_turnover_internally += trade_payment
        prev_segment_quantity = segment[0]

    # this is me having fun I am sorry
    try:
        assert total_turnover_internally == total_turnover_
    except AssertionError:
        print(executed_segment)
        print(clearing_quantity)
        print(clearing_quantity_internally)
        print(total_turnover_internally)
        print(total_turnover_)
        if abs(total_turnover_ - total_turnover_internally) < 0.001:
            pass
        else:
            assert total_turnover_internally == total_turnover_

    for trade in trade_pairs_pac_:
        if any(element is None for element in trade):
            print('weird stuff is happening')
            exit('weird stuff is happening')

    method_logger.info('finished matching winning bids and offers')
    return clearing_quantity, clearing_price, total_turnover_, trade_pairs_pac_


def pab_pricing(sorted_x_y_y_pairs_list, sorted_bid_list, sorted_offer_list):
    """ trade matching according pay-as-bid pricing rule """
    clearing_quantity, clearing_price = clearing_quantity_calc(sorted_x_y_y_pairs_list)

    trade_pairs_pab_ = []
    total_turnover_ = 0

    if clearing_quantity is None:
        return clearing_quantity, clearing_price, None, None

    # filter only on executed segments that have no Non types (meaning) bid/offer but not offer/bid
    # first check if None, if not, check whether under clearing quantity
    executed_segment = [segment for segment in sorted_x_y_y_pairs_list if segment[0] is not None
                        and segment[0] <= clearing_quantity]
    """ this function should return a pairing of bids and offers for determined prices"""
    trade_pairs = []
    prev_segment_quantity = 0
    for segment in executed_segment:
        # reading out values from the executed trade segments
        trade_quantity = segment[0] - prev_segment_quantity

        buyer_price = segment[1]
        seller_price = segment[2]
        buyer_id = segment[3]
        seller_id = segment[4]

        """ Open to market design matching algorithm """
        trade_payment = trade_quantity * buyer_price
        # set up trade pairs
        trade_pair = [seller_id, buyer_id, trade_quantity, trade_payment]
        trade_pairs_pab_.append(trade_pair)
        # finalise
        total_turnover_ += trade_payment
        prev_segment_quantity = trade_quantity

    # lumping together reduces transparency since prices per trade deal are different, so this is omitted here
    return clearing_quantity, clearing_price, total_turnover_, trade_pairs_pab_


def clearing_quantity_calc(sorted_x_y_y_pairs_list):
    """ This can be used both for PaC as for PaB, returns clearing quantity and uniform clearing price"""
    clearing_quantity_ = None
    clearing_price_ = None

    """ filter out None values and remove these points for they don't add information """
    # for i in range(len(sorted_x_y_y_pairs_list)):
    #     if sorted_x_y_y_pairs_list[-i][1] is None or sorted_x_y_y_pairs_list[-i][2] is None:
    #

    sorted_x_y_y_pairs_list = [segment for segment in sorted_x_y_y_pairs_list if segment[1] is not None
                               and segment[2] is not None]


    # now I make range(len(sorted_x_y_y_pairs_list)-1), -1 because of the forwards-step bug (see TODO_above)
    # if all offers are affordable to bids, i.e all offers are lower price than bids, the market should

    # fully execute: all bid prices are higher than offer prices
    if all(sorted_x_y_y_pairs_list[i][1] >= sorted_x_y_y_pairs_list[i][2] for i in range(len(sorted_x_y_y_pairs_list))):
        # clearing quantity is simply last quantity point of aggregate demand and supply curve
        clearing_quantity_ = sorted_x_y_y_pairs_list[-1][0]
        # highest winning bid is simply last price point of aggregate demand curve
        clearing_price_ = sorted_x_y_y_pairs_list[-1][1]
        method_logger.info('fully executed')

    # execute nothing: all bids prices are lower than offer prices
    elif all(sorted_x_y_y_pairs_list[i][1] < sorted_x_y_y_pairs_list[i][2] for i in range(len(sorted_x_y_y_pairs_list))):
        clearing_quantity_ = None
        clearing_price_ = None
        method_logger.info('nothing executed')

    # execute partially: some bids prices are lower than some offer prices
    else:
        # search for the first point in sorted_x_x_y_pairs_list where the bid price is lower than the offer price.
        # this will be the point where clearing quantity depends on
        for i in range(len(sorted_x_y_y_pairs_list)):
            # if bid is still higher than offer, then save it as potential clearing quantity and next "losing?" bid
            # as clearing price
            if sorted_x_y_y_pairs_list[i][1] < sorted_x_y_y_pairs_list[i][2]:
                # clearing price is defined as the highest winning bid, sorted_x_x_y_pairs_list[i][1]
                clearing_quantity_ = sorted_x_y_y_pairs_list[i - 1][0]
                clearing_price_ = sorted_x_y_y_pairs_list[i - 1][1]
                method_logger.info('partially executed')
                break

    return clearing_quantity_, clearing_price_
