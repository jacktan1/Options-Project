import numpy as np
from numba import njit, prange


@njit(parallel=True)
def risk_analysis_v4(sorted_prices, current_price, fixed_commission, contract_commission, final_prices):

    call_sell_max = 2
    put_sell_max = 2

    # Initializing the empty matrices ... absolute cancer wtf
    hist_return_avg_02 = np.zeros((len(sorted_prices), len(sorted_prices)))
    hist_return_avg_12 = np.zeros((len(sorted_prices), len(sorted_prices)))
    hist_return_avg_22 = np.zeros((len(sorted_prices), len(sorted_prices)))
    hist_return_avg_21 = np.zeros((len(sorted_prices), len(sorted_prices)))
    hist_return_avg_20 = np.zeros((len(sorted_prices), len(sorted_prices)))
    percent_in_money_02 = np.zeros((len(sorted_prices), len(sorted_prices)))
    percent_in_money_12 = np.zeros((len(sorted_prices), len(sorted_prices)))
    percent_in_money_22 = np.zeros((len(sorted_prices), len(sorted_prices)))
    percent_in_money_21 = np.zeros((len(sorted_prices), len(sorted_prices)))
    percent_in_money_20 = np.zeros((len(sorted_prices), len(sorted_prices)))
    risk_money_02 = np.zeros((len(sorted_prices), len(sorted_prices)))
    risk_money_12 = np.zeros((len(sorted_prices), len(sorted_prices)))
    risk_money_22 = np.zeros((len(sorted_prices), len(sorted_prices)))
    risk_money_21 = np.zeros((len(sorted_prices), len(sorted_prices)))
    risk_money_20 = np.zeros((len(sorted_prices), len(sorted_prices)))

    # The rows represent call prices
    for n in range(0, 1):
        call_strike_price = sorted_prices[n, 0]
        call_premium = sorted_prices[n, 1]
        call_size = sorted_prices[n, 2]
        # The columns represent put prices
        for m in range(0, 1):
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 5]
            put_size = sorted_prices[m, 6]
            # Determine which line we are calculating for
            for my_type in ['diff_calls']:
                if my_type == 'diff_calls':
                    call_num_matrix = np.arange(
                        0.0, call_sell_max + 1, 1.0).reshape(1, call_sell_max + 1)
                    put_num_matrix = np.ones((1, put_sell_max)) * put_sell_max
                    # Calculation
                    call_base = np.minimum(
                        call_strike_price - final_prices, 0) + call_premium
                    call_comm_matrix = fixed_commission + call_num_matrix * contract_commission
                    call_comm_matrix[0][0] = 0
                    
                    #call_return = call_base * call_num_matrix * 100 - call_comm_matrix
                    #put_comm_matrix = fixed_commission + put_num_matrix * contract_commission
                # elif my_type == 'diff_puts':
                #     call_num_matrix = np.ones((1, call_sell_max + 1)) * call_sell_max
                #     put_num_matrix = np.arange(
                #         0.0, put_sell_max, 1.0).reshape(1, put_sell_max)

                # Get historical return matrices for calls and puts
                # Calls
                # call_base = np.minimum(
                #     call_strike_price - final_prices, 0) + call_premium
                # call_comm_matrix[0][0] = 0
                # call_return = call_base * call_num_matrix * 100 - call_comm_matrix
                # Puts
                # put_base = np.minimum(
                #     final_prices - put_strike_price, 0) + put_premium
                # put_comm_matrix[0][0] = 0
                # put_return = put_base * put_num_matrix * 100 - put_comm_matrix

    #            if my_type == 'diff_calls':
    #                 num_in_money = 0
    #                 risk_money_holder = 0
    #                 for aa in range(call_sell_max + 1):
    #                     total_call_put = call_return[:, aa] + \
    #                         put_return[:, 1] / (aa + put_sell_max)
    #                     for cc in range(0, len(total_call_put)):
    #                         if total_call_put[cc] > 0:
    #                             num_in_money += 1
    #                         else:
    #                             risk_money_holder += total_call_put[cc]
    #
    #                     if (len(total_call_put) - num_in_money) == 0:
    #                         risk_money = 0
    #                     else:
    #                         risk_money = risk_money_holder / \
    #                             (len(total_call_put) - num_in_money)
    #
    #                     if aa == 0:
    #                         hist_return_avg_02[n, m] = np.sum(
    #                             total_call_put) / len(total_call_put)
    #                         percent_in_money_02[n, m] = (
    #                             num_in_money / len(total_call_put)) * 100
    #                         risk_money_02[n, m] = risk_money
    #
    #                     if aa == 1:
    #                         hist_return_avg_12[n, m] = np.sum(
    #                             total_call_put) / len(total_call_put)
    #                         percent_in_money_12[n, m] = (
    #                             num_in_money / len(total_call_put)) * 100
    #                         risk_money_12[n, m] = risk_money
    #
    #                     if aa == 2:
    #                         hist_return_avg_22[n, m] = np.sum(
    #                             total_call_put) / len(total_call_put)
    #                         percent_in_money_22[n, m] = (
    #                             num_in_money / len(total_call_put)) * 100
    #                         risk_money_22[n, m] = risk_money
    #
    #             if my_type == 'diff_puts':
    #                 num_in_money = 0
    #                 risk_money_holder = 0
    #                 for bb in range(put_sell_max):
    #                     total_call_put = call_return + \
    #                         put_return[:, bb] / (call_sell_max + bb)
    #                     for cc in range(0, len(total_call_put)):
    #                         if total_call_put[cc] > 0:
    #                             num_in_money += 1
    #                         else:
    #                             risk_money_holder += total_call_put[cc]
    #
    #                     if (len(total_call_put) - num_in_money) == 0:
    #                         risk_money = 0
    #                     else:
    #                         risk_money = risk_money_holder / \
    #                             (len(total_call_put) - num_in_money)
    #
    #                     if bb == 0:
    #                         hist_return_avg_20[n, m] = np.sum(
    #                             total_call_put) / len(total_call_put)
    #                         percent_in_money_20[n, m] = (
    #                             num_in_money / len(total_call_put)) * 100
    #                         risk_money_20[n, m] = risk_money
    #
    #                     if bb == 1:
    #                         hist_return_avg_21[n, m] = np.sum(
    #                             total_call_put) / len(total_call_put)
    #                         percent_in_money_21[n, m] = (
    #                             num_in_money / len(total_call_put)) * 100
    #                         risk_money_21[n, m] = risk_money
    #
    # hist_return_avg = np.zeros((5, len(sorted_prices), len(sorted_prices)))
    # percent_in_money = np.zeros((5, len(sorted_prices), len(sorted_prices)))
    # risk_money = np.zeros((5, len(sorted_prices), len(sorted_prices)))
    # hist_return_avg[:, :, :] = [hist_return_avg_02, hist_return_avg_12, hist_return_avg_22,
    #                             hist_return_avg_21, hist_return_avg_20]
    # percent_in_money[:, :, :] = [percent_in_money_02, percent_in_money_12, percent_in_money_22,
    #                              percent_in_money_21, percent_in_money_20, ]
    # risk_money[:, :, :] = [risk_money_02, risk_money_12,
    #                        risk_money_22, risk_money_21, risk_money_20]
    # return [hist_return_avg, percent_in_money, risk_money]
    return 1
