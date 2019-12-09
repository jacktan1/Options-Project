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


def find_best_v2(percent_in_money, historical_return_avg, sorted_prices,
                 in_money_thres, strike_date_index, days_till_expiry,
                 call_sell_max, put_sell_max):
    density = 10
    list_len = 10
    num_groups = int((100 - in_money_thres) / density)
    best_returns_final = np.zeros((1, 9))
    [npages, nrows, ncols] = percent_in_money.shape
    num_to_take_ratio = 0.25
    # Number of entries every day that we want to extract, arbitrary value
    best_returns_big = np.zeros((1, 9))
    for aa in range(npages):
        if aa <= call_sell_max:
            num_calls = aa
            num_puts = put_sell_max
        else:
            num_calls = call_sell_max
            num_puts = npages - aa - 1
        # For pages with 0 calls and 0 puts, we only look at one column/row
        if aa == 0:
            holder1 = percent_in_money[aa, 0:1, :]  # 0:1 preserves 2-D shape
            holder2 = historical_return_avg[aa, 0:1, :]
            # Since we have one row in a 2-D ndarray
            num_to_take = holder1.shape[1]
        elif aa == call_sell_max + put_sell_max:
            holder1 = percent_in_money[aa, :, 0:1]
            holder2 = historical_return_avg[aa, :, 0:1]
            # Since we have one column in a 2-D ndarray
            num_to_take = holder1.shape[0]
        else:
            holder1 = percent_in_money[aa, :, :]
            holder2 = historical_return_avg[aa, :, :]
            num_to_take = int(num_to_take_ratio * nrows * ncols)
        # Method below takes into account th e percent chance of being in money, (avg return * percent) / day
        daily_info = holder1 * holder2 * 0.01 * \
            (1 / days_till_expiry)
        # Find the values of the top 'daily info's
        top_positions = sorted(np.argpartition(daily_info.flatten(), -num_to_take)[-num_to_take:],
                               reverse=True)
        # Converting matrix into rows with readible information
        best_returns = np.zeros((num_to_take, 9))
        for n in range(num_to_take):
            if aa == 0:
                call_row = 0
                put_col = top_positions[n]
            elif aa == call_sell_max + put_sell_max:
                call_row = top_positions[n]
                put_col = 0
            else:
                call_row = int(top_positions[n] / ncols)
                put_col = int(np.mod(top_positions[n], ncols))
            # There's no point filling out rest of the rows once we hit a 0 'expect return'
            if daily_info[call_row, put_col] == 0:
                break
            # Filling put the best returns matrix
            best_returns[n, :] = np.array([daily_info[call_row, put_col], strike_date_index,
                                           sorted_prices[call_row, 0],
                                           sorted_prices[call_row,
                                                         1], num_calls,
                                           sorted_prices[put_col, 0],
                                           sorted_prices[put_col, 5], num_puts,
                                           percent_in_money[aa, call_row, put_col]])
        # Inserting this into the bigger 'best_returns' matrix
        best_returns_big = np.append(best_returns_big, best_returns, axis=0)
    # Filtering our results
    # Only want positive avg returns
    best_returns_big = best_returns_big[best_returns_big[:, 0] > 0]
    # Only want percent chance in money over thres
    best_returns_big = best_returns_big[best_returns_big[:, 8]
                                        > in_money_thres]
    # Sorting our results into groups
    for n in range(num_groups):
        if n == num_groups - 1:
            filtered = best_returns_big[best_returns_big[:, 8]
                                        >= in_money_thres + density * n]
        else:
            filtered = best_returns_big[best_returns_big[:, 8]
                                        >= in_money_thres + density * n]
            filtered = filtered[filtered[:, 8] <
                                in_money_thres + density * (n + 1)]
        # Sorting the filtered results
        if len(filtered) == 0:
            da_best = np.zeros((1, 9))
        else:
            da_best = np.flip(filtered[np.argsort(filtered[:, 0])], axis=0)
            if len(da_best) > list_len:
                da_best = da_best[:list_len]
        best_returns_final = np.append(best_returns_final, da_best, axis=0)

    return best_returns_final
