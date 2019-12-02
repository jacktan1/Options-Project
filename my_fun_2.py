import numpy as np
from numba import jit, njit, prange


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
        call_size = sorted_prices[n, 2]
        # The columns represent put prices
        for m in range(0, len(sorted_prices)):
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 5]
            put_size = sorted_prices[m, 6]
            # Same no matter what
            call_base = np.minimum(
                call_strike_price - final_prices, 0) + call_premium
            put_base = np.minimum(
                final_prices - put_strike_price, 0) + put_premium
            # Determine which line we are calculating for
            for my_type in ['diff_calls', 'diff_puts']:
                if my_type == 'diff_calls':
                    # Calls
                    call_num_matrix = np.arange(
                        0.0, call_sell_max + 1, 1.0).reshape(1, call_sell_max + 1)
                    call_comm_matrix = \
                        (call_num_matrix * contract_commission + fixed_commission) * 2
                    call_comm_matrix[0][0] = 0
                    call_return = np.dot(
                        call_base, call_num_matrix) * 100 - call_comm_matrix
                    # Puts
                    put_num_matrix = np.ones(
                        (1, put_sell_max + 1)) * put_sell_max
                    put_comm_matrix = \
                        (put_num_matrix * contract_commission + fixed_commission) * 2
                    put_return = np.dot(
                        put_base, put_num_matrix) * 100 - put_comm_matrix
                    # Calculations
                    for aa in range(call_sell_max + 1):
                        num_in_money = 0
                        risk_money_sum = 0
                        total_call_put = call_return[:, aa] + \
                            put_return[:, aa] / (aa + put_sell_max)
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
                    # Calls
                    call_num_matrix = np.ones(
                        (1, call_sell_max)) * call_sell_max
                    call_comm_matrix = \
                        (call_num_matrix * contract_commission + fixed_commission) * 2
                    call_return = np.dot(
                        call_base, call_num_matrix) * 100 - call_comm_matrix
                    # Puts
                    # Backwards since we want 1 then 0 puts for page ordering
                    put_num_matrix = np.arange(
                        put_sell_max - 1, -1., -1.0).reshape(1, put_sell_max)
                    put_comm_matrix = \
                        (put_num_matrix * contract_commission + fixed_commission) * 2
                    put_comm_matrix[0][put_sell_max - 1] = 0
                    put_return = np.dot(
                        put_base, put_num_matrix) * 100 - put_comm_matrix
                    # Calculations
                    for aa in range(put_sell_max):
                        num_in_money = 0
                        risk_money_sum = 0
                        total_call_put = call_return[:, aa] + \
                            put_return[:, aa] / (aa + call_sell_max)
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
                        percent_in_money[aa + call_sell_max + 1, n, m] = \
                            (num_in_money / len(total_call_put)) * 100
                        hist_return_avg[aa + call_sell_max + 1, n, m] = \
                            np.sum(total_call_put) / len(total_call_put)
                        risk_money[aa + call_sell_max + 1, n, m] = \
                            risk_money_avg

    return [percent_in_money, hist_return_avg, risk_money]


# numba slow as fuck for some reason
# @jit(parallel = False, fastmath=True, nopython = True)
def find_best_v2(list_len, percent_in_money, historical_return_avg, sorted_prices,
                 strike_date_index, days_till_expiry):
    [npages, nrows, ncols] = percent_in_money.shape
    best_returns_final = np.zeros((list_len, 9))
    best_returns_big = np.zeros((list_len * npages, 9))
    for aa in range(npages):
        if aa <= int(npages / 2):
            num_calls = aa
            num_puts = int(npages / 2)
        else:
            num_calls = int(npages / 2)
            num_puts = npages - aa - 1
        # Method below takes into account th e percent chance of being in money, (avg return * percent) / day
        daily_info = percent_in_money[aa, :, :] * historical_return_avg[aa, :, :] * 0.01 * \
            (1 / days_till_expiry)
        # Method below does not take into account the percent chance of being in money, only avg return / day
        # daily_info = historical_return_avg[n, m] * (1 / days_till_expiry)
        # Find the values of the top 'daily info's
        top_positions = sorted(np.partition(daily_info.flatten(), -list_len)[-list_len:],
                               reverse=True)
        for n in range(list_len):
            best_returns = np.zeros((list_len, 9))
            if top_positions[n] == 0:
                break
            position_holder = np.where(daily_info == top_positions[n])[0][0]
            call_row = int(position_holder / ncols)
            put_col = int(np.mod(position_holder, ncols))
            # Filling put the best returns matrix
            best_returns[n, :] = np.array([top_positions[n], strike_date_index,
                                           sorted_prices[call_row, 0],
                                           sorted_prices[call_row,
                                                         1], num_calls,
                                           sorted_prices[put_col, 0],
                                           sorted_prices[put_col, 5], num_puts,
                                           percent_in_money[aa, call_row, put_col]])
        # Inserting this into the bigger 'best_returns' matrix
        best_returns_big[aa * list_len:(aa + 1) * list_len, :] = best_returns
    # Finding the top 10 in terms of best avg return per day
    index_holder = int(list_len / 2)
    top_avg_returns = sorted(np.partition(best_returns_big[:, 0], -index_holder)[-index_holder:],
                             reverse=True)
    top_chance_in_money = sorted(np.partition(best_returns_big[:, 8],  -index_holder)[-index_holder:],
                                 reverse=True)
    for n in range(index_holder):
        holder_avg = np.where(
            best_returns_big[:, 0] == top_avg_returns[n])[0][0]
        holder_chance = np.where(
            best_returns_big[:, 8] == top_chance_in_money[n])[0][0]
        best_returns_final[n, :] = best_returns_big[holder_avg, :]
        best_returns_final[n + index_holder,
                           :] = best_returns_big[holder_chance, :]
    return best_returns_final


# def find_best_outer()
