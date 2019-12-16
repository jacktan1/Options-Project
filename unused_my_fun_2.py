# This version of risk analysis actually looks at whether there are people buying enough contracts
# as we are selling. And I believe it successfully does so (in a hacky way). However it became a whole
# different story when it came to the `find best`, and I would have to completely rewrite that code.

# As a result, I abandoned this code here, since so much effort needed to complete this for minimal benefits
# If there's no one buying, then bid price is 0 (code innately will disregard it), but if not enough contracts
# being bought, the flat trading fees shouldn't make THAT much of a difference.

@jit(parallel=False, fastmath=True, nopython=True)
def risk_analysis_v4(sorted_prices, current_price, fixed_commission, contract_commission,
                     assignment_fee, final_prices, call_sell_max=3, put_sell_max=3):
    # Initializing the empty matrices. Ordering are as follows (page 1 - 7):
    # 0 Calls & 3 Puts
    # 1 Calls & 3 Puts
    # 2 Calls & 3 Puts
    # 3 Calls & 3 Puts
    # 3 Calls & 2 Puts
    # 3 Calls & 1 Puts
    # 3 Calls & 0 Puts
    hist_return_avg = np.zeros(
        (call_sell_max + put_sell_max + 1, len(sorted_prices), len(sorted_prices)))
    percent_in_money = np.zeros(
        (call_sell_max + put_sell_max + 1, len(sorted_prices), len(sorted_prices)))
    risk_money = np.zeros(
        (call_sell_max + put_sell_max + 1, len(sorted_prices), len(sorted_prices)))

    # The rows represent call prices
    for n in range(0, len(sorted_prices)):
        call_strike_price = sorted_prices[n, 0]
        call_premium = sorted_prices[n, 1]
        call_lim = int(sorted_prices[n, 2])
        # The columns represent put prices
        for m in range(0, len(sorted_prices)):
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 5]
            put_lim = int(sorted_prices[m, 6])
            # Same no matter what
            call_base = np.minimum(
                call_strike_price - final_prices, 0) + call_premium
            put_base = np.minimum(
                final_prices - put_strike_price, 0) + put_premium
            # Determine which line we are calculating for
            for my_type in ['diff_calls', 'diff_puts']:
                if my_type == 'diff_calls':
                    # Seeing if there's even that many buy orders
                    if call_lim < call_sell_max:
                        call_max = call_lim
                    else:
                        call_max = call_sell_max
                    if put_lim < put_sell_max:
                        put_max = put_lim
                    else:
                        put_max = put_sell_max
                    ### --- ###
                    # Calls
                    call_num_matrix = np.arange(
                        0.0, call_max + 1, 1.0).reshape(1, call_max + 1)
                    call_comm_matrix = \
                        (call_num_matrix * contract_commission + fixed_commission) * 2
                    call_comm_matrix[0][0] = 0
                    call_return = np.dot(
                        call_base, call_num_matrix) * 100 - call_comm_matrix
                    # Puts
                    put_num_matrix = np.ones(
                        (1, call_max + 1)) * put_max
                    if put_max == 0:
                        put_comm_matrix = put_num_matrix
                    else:
                        put_comm_matrix = \
                            (put_num_matrix * contract_commission + fixed_commission) * 2
                    put_return = np.dot(
                        put_base, put_num_matrix) * 100 - put_comm_matrix
                    # Calculations
                    for aa in range(call_max + 1):
                        num_in_money = 0
                        risk_money_sum = 0
                        if aa + put_max != 0:
                            total_call_put = call_return[:, aa] + \
                                             put_return[:, aa] / (aa + put_max)
                        else:
                            total_call_put = (call_return[:, aa] + put_return[:, aa]) * 0
                        # Seeing how many are 'in the money' and gathering risk money
                        for cc in range(0, len(total_call_put)):
                            if total_call_put[cc] > 0:
                                num_in_money += 1
                            else:
                                risk_money_sum += total_call_put[cc]
                        # Calculating the 'average' risk money
                        if (len(total_call_put) - num_in_money) == 0:
                            risk_money_avg = 0
                        else:
                            risk_money_avg = risk_money_sum / \
                                             (len(total_call_put) - num_in_money)
                        # Saving information into our matrices
                        percent_in_money[aa, n, m] = \
                            (num_in_money / len(total_call_put)) * 100
                        hist_return_avg[aa, n, m] = \
                            np.sum(total_call_put) / len(total_call_put)
                        risk_money[aa, n, m] = \
                            risk_money_avg
                elif my_type == 'diff_puts':
                    if put_max != 0:
                        # Calls
                        call_num_matrix = np.ones(
                            (1, put_max)) * call_max
                        call_comm_matrix = \
                            (call_num_matrix * contract_commission + fixed_commission) * 2
                        call_return = np.dot(
                            call_base, call_num_matrix) * 100 - call_comm_matrix
                        # Puts
                        # Backwards since we want 1 then 0 puts for page ordering
                        put_num_matrix = np.arange(
                            put_max - 1, -1., -1.0).reshape(1, put_max)
                        put_comm_matrix = \
                            (put_num_matrix * contract_commission + fixed_commission) * 2
                        put_comm_matrix[0][put_max - 1] = 0
                        put_return = np.dot(
                            put_base, put_num_matrix) * 100 - put_comm_matrix
                        # Calculations
                        for aa in range(put_max):
                            num_in_money = 0
                            risk_money_sum = 0
                            if aa + call_max != 0:
                                total_call_put = call_return[:, aa] + \
                                                 put_return[:, aa] / (aa + call_max)
                            else:
                                total_call_put = (call_return[:, aa] + put_return[:, aa]) * 0
                            # Seeing how many are 'in the money' and gathering risk money
                            for cc in range(0, len(total_call_put)):
                                if total_call_put[cc] > 0:
                                    num_in_money += 1
                                else:
                                    risk_money_sum += total_call_put[cc]
                            # Calculating the 'average' risk money
                            if (len(total_call_put) - num_in_money) == 0:
                                risk_money_avg = 0
                            else:
                                risk_money_avg = risk_money_sum / \
                                                 (len(total_call_put) - num_in_money)
                            # Saving information into our matrices
                            percent_in_money[-(aa + 1), n, m] = \
                                (num_in_money / len(total_call_put)) * 100
                            hist_return_avg[-(aa + 1), n, m] = \
                                np.sum(total_call_put) / len(total_call_put)
                            risk_money[-(aa + 1), n, m] = \
                                risk_money_avg
    return [percent_in_money, hist_return_avg, risk_money]
