# Plot showing distribution of scores
def make_plot(final_scores):
    my_fig = go.Figure()
    my_fig.add_trace(go.Histogram(x=final_scores.Score,
                                  histnorm='percent',
                                  xbins=dict(
                                      start=np.min(final_scores.Score),
                                      end=np.max(final_scores.Score),
                                      size=(np.max(final_scores.Score) - np.min(final_scores.Score)) / 100
                                  )))
    my_fig.show()
    return


# jit version using parallel cpu
@jit(parallel=True, fastmath=True, nopython=True)
def risk_analysis_v5_bt(sorted_prices, final_prices, temp_weights, temp_sum,
                        fixed_commission, contract_commission, assignment_fee):
    # Initializing the empty matrices. Ordering are as follows:
    # 0 Calls & 1 Puts
    # 1 Calls & 0 Puts
    # We use dimensional order of: type, call, put, phase, freq, amplitude
    hist_return_avg = np.zeros((2, len(sorted_prices), len(sorted_prices),
                                temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    percent_in_money = np.zeros((2, len(sorted_prices), len(sorted_prices),
                                 temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    for n in prange(0, len(sorted_prices)):
        call_strike_price = sorted_prices[n, 0]
        call_premium = sorted_prices[n, 1]
        # Same no matter what
        call_base = (np.minimum(call_strike_price - final_prices, 0) + call_premium)[:, 0]
        for m in prange(0, len(sorted_prices)):
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 5]
            # Same no matter what
            put_base = (np.minimum(final_prices - put_strike_price, 0) + put_premium)[:, 0]
            # Determine which combo we are calculating for
            for my_type in ['0c_1p', '1c_0p']:
                if my_type == '0c_1p':
                    # Put
                    put_comm_matrix = (contract_commission + fixed_commission) * 2
                    total_call_put = put_base * 100 - put_comm_matrix
                    ### ----- ###
                    # Creating the matrices for storing results
                    holder_in_money = np.zeros(len(total_call_put))
                    for aa in prange(len(total_call_put)):
                        if total_call_put[aa] > 0:
                            holder_in_money[aa] = 1
                    ### ----- ###
                    percent = np.zeros((temp_weights.shape[0],
                                        temp_weights.shape[1],
                                        temp_weights.shape[2]))
                    avg = np.zeros((temp_weights.shape[0],
                                    temp_weights.shape[1],
                                    temp_weights.shape[2]))
                    for cc in prange(temp_weights.shape[0]):
                        for dd in prange(temp_weights.shape[1]):
                            for ee in prange(temp_weights.shape[2]):
                                percent[cc, dd, ee] = \
                                    (np.sum(temp_weights[cc, dd, ee, :] * holder_in_money)) / temp_sum[cc, dd, ee]
                                avg[cc, dd, ee] = \
                                    (np.sum(temp_weights[cc, dd, ee, :] * total_call_put)) / temp_sum[cc, dd, ee]
                    ### ----- ###
                    percent_in_money[0, n, m] = percent
                    hist_return_avg[0, n, m] = avg
                elif my_type == '1c_0p':
                    # Call
                    call_comm_matrix = (contract_commission + fixed_commission) * 2
                    total_call_put = call_base * 100 - call_comm_matrix
                    ### ----- ###
                    # Creating the matrices for storing results
                    holder_in_money = np.zeros(len(total_call_put))
                    for aa in prange(len(total_call_put)):
                        if total_call_put[aa] > 0:
                            holder_in_money[aa] = 1
                    ### ----- ###
                    percent = np.zeros((temp_weights.shape[0],
                                        temp_weights.shape[1],
                                        temp_weights.shape[2]))
                    avg = np.zeros((temp_weights.shape[0],
                                    temp_weights.shape[1],
                                    temp_weights.shape[2]))
                    for cc in prange(temp_weights.shape[0]):
                        for dd in prange(temp_weights.shape[1]):
                            for ee in prange(temp_weights.shape[2]):
                                percent[cc, dd, ee] = \
                                    (np.sum(temp_weights[cc, dd, ee, :] * holder_in_money)) / temp_sum[cc, dd, ee]
                                avg[cc, dd, ee] = \
                                    (np.sum(temp_weights[cc, dd, ee, :] * total_call_put)) / temp_sum[cc, dd, ee]
                    ### ----- ###
                    percent_in_money[1, n, m] = percent
                    hist_return_avg[1, n, m] = avg
    return [percent_in_money, hist_return_avg]


################### Still working on cupy implmentation


def risk_analysis_v5_bt(sorted_prices_np, final_prices_np, temp_weights_np, temp_sum_np,
                        fixed_commission, contract_commission):
    sorted_prices = cp.array(sorted_prices_np)
    final_prices = cp.array(final_prices_np)
    temp_weights = cp.array(temp_weights_np)
    temp_sum = cp.array(temp_sum_np)
    # Initializing the empty matrices. Ordering are as follows:
    # 0 Calls & 1 Puts
    # 1 Calls & 0 Puts
    # We use dimensional order of: type, call, put, phase, freq, amplitude
    hist_return_avg = cp.zeros((2, len(sorted_prices), len(sorted_prices),
                                temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    percent_in_money = cp.zeros((2, len(sorted_prices), len(sorted_prices),
                                 temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    for n in range(0, len(sorted_prices)):
        call_strike_price = sorted_prices[n, 0]
        call_premium = sorted_prices[n, 1]
        # Same no matter what
        call_base = cp.add(cp.minimum(call_strike_price - final_prices, 0), call_premium)[:, 0]
        for m in range(0, len(sorted_prices)):
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 5]
            # Same no matter what
            put_base = cp.add(cp.minimum(final_prices - put_strike_price, 0), put_premium)[:, 0]
            # Determine which combo we are calculating for
            for my_type in ['0c_1p', '1c_0p']:
                if my_type == '0c_1p':
                    # Put
                    put_comm_matrix = cp.add(contract_commission, fixed_commission)
                    total_call_put = cp.subtract(cp.multiply(put_base, 100), put_comm_matrix)
                    ### ----- ###
                    # Creating the matrices for storing results
                    holder_in_money = cp.zeros(len(total_call_put))
                    for aa in range(len(total_call_put)):
                        if total_call_put[aa] > 0:
                            holder_in_money[aa] = 1
                    percent = cp.sum(cp.multiply(temp_weights, holder_in_money), axis=3)
                    percent = cp.divide(percent, temp_sum)
                    avg = cp.sum(cp.multiply(temp_weights, total_call_put), axis=3)
                    avg = cp.divide(avg, temp_sum)
                    ### ----- ###
                    # percent = cp.zeros((temp_weights.shape[0],
                    #                     temp_weights.shape[1],
                    #                     temp_weights.shape[2]))
                    # avg = cp.zeros((temp_weights.shape[0],
                    #                 temp_weights.shape[1],
                    #                 temp_weights.shape[2]))
                    # for cc in range(temp_weights.shape[0]):
                    #     for dd in range(temp_weights.shape[1]):
                    #         for ee in range(temp_weights.shape[2]):
                    #             percent[cc, dd, ee] = \
                    #                 (cp.sum(temp_weights[cc, dd, ee, :] * holder_in_money)) / temp_sum[cc, dd, ee]
                    #             avg[cc, dd, ee] = \
                    #                 (cp.sum(temp_weights[cc, dd, ee, :] * total_call_put)) / temp_sum[cc, dd, ee]
                    #             temp1 = np.ascontiguousarray(temp_weights[cc, dd, ee, :])
                    #             temp2 = np.ascontiguousarray(total_call_put)
                    #             percent = (inner_cuda(temp1, temp2))[0] / temp_sum[cc, dd, ee]
                    #             avg = (inner_cuda(temp1, temp2))[0] / temp_sum[cc, dd, ee]
                    ### ----- ###
                    percent_in_money[0, n, m] = percent
                    hist_return_avg[0, n, m] = avg
                elif my_type == '1c_0p':
                    # Call
                    call_comm_matrix = cp.add(contract_commission, fixed_commission)
                    total_call_put = cp.subtract(cp.multiply(call_base, 100), call_comm_matrix)
                    ### ----- ###
                    # Creating the matrices for storing results
                    holder_in_money = cp.zeros(len(total_call_put))
                    for aa in range(len(total_call_put)):
                        if total_call_put[aa] > 0:
                            holder_in_money[aa] = 1
                    percent = cp.sum(cp.multiply(temp_weights, holder_in_money), axis=3)
                    percent = cp.divide(percent, temp_sum)
                    avg = cp.sum(cp.multiply(temp_weights, total_call_put), axis=3)
                    avg = cp.divide(avg, temp_sum)
                    ### ----- ###
                    # percent = cp.zeros((temp_weights.shape[0],
                    #                     temp_weights.shape[1],
                    #                     temp_weights.shape[2]))
                    # avg = cp.zeros((temp_weights.shape[0],
                    #                 temp_weights.shape[1],
                    #                 temp_weights.shape[2]))
                    # for cc in range(temp_weights.shape[0]):
                    #     for dd in range(temp_weights.shape[1]):
                    #         for ee in range(temp_weights.shape[2]):
                    #             percent[cc, dd, ee] = \
                    #                 (cp.sum(temp_weights[cc, dd, ee, :] * holder_in_money)) / temp_sum[cc, dd, ee]
                    #             avg[cc, dd, ee] = \
                    #                 (cp.sum(temp_weights[cc, dd, ee, :] * total_call_put)) / temp_sum[cc, dd, ee]
                    #             temp1 = np.ascontiguousarray(temp_weights[cc, dd, ee, :])
                    #             temp2 = np.ascontiguousarray(total_call_put)
                    #             percent = (inner_cuda(temp1, temp2))[0] / temp_sum[cc, dd, ee]
                    #             avg = (inner_cuda(temp1, temp2))[0] / temp_sum[cc, dd, ee]
                    ### ----- ###
                    percent_in_money[1, n, m] = percent
                    hist_return_avg[1, n, m] = avg
    return [percent_in_money, hist_return_avg]

##################

@jit(parallel=False, fastmath=True, nopython=True)
def risk_analysis_v5_bt(sorted_prices, final_prices, temp_weights, temp_sum,
                        fixed_commission, contract_commission, assignment_fee,
                        call_sell_max=1, put_sell_max=1):
    # Initializing the empty matrices. Ordering are as follows (page 1 - 3):
    # 0 Calls & 1 Puts
    # 1 Calls & 1 Puts
    # 1 Calls & 0 Puts
    # We use dimensional order of: type, call, put, phase, freq, amplitude
    hist_return_avg = np.zeros((call_sell_max + put_sell_max + 1, len(sorted_prices), len(sorted_prices),
                                temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    percent_in_money = np.zeros((call_sell_max + put_sell_max + 1, len(sorted_prices), len(sorted_prices),
                                 temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    # len(sorted_prices)
    for n in range(0, len(sorted_prices)):
        call_strike_price = sorted_prices[n, 0]
        call_premium = sorted_prices[n, 1]
        for m in range(0, len(sorted_prices)):
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 5]
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
                        (1, call_sell_max + 1)) * put_sell_max
                    put_comm_matrix = \
                        (put_num_matrix * contract_commission + fixed_commission) * 2
                    put_return = np.dot(
                        put_base, put_num_matrix) * 100 - put_comm_matrix
                    # Calculations
                    for aa in range(call_sell_max + 1):
                        total_call_put = (call_return[:, aa] + put_return[:, aa]) / (aa + put_sell_max)
                        ### ----- ###
                        # Creating the matrices for storing results
                        holder_in_money = np.zeros(len(total_call_put))
                        for bb in range(len(total_call_put)):
                            if total_call_put[bb] > 0:
                                holder_in_money[bb] = 1
                        ### ----- ###
                        # percent = np.zeros((temp_weights.shape[0],
                        #                     temp_weights.shape[1],
                        #                     temp_weights.shape[2]))
                        avg = np.zeros((temp_weights.shape[0],
                                        temp_weights.shape[1],
                                        temp_weights.shape[2]))
                        for cc in range(temp_weights.shape[0]):
                            for dd in range(temp_weights.shape[1]):
                                for ee in range(temp_weights.shape[2]):
                                    # for ff in range(temp_weights.shape[3]):
                                    #     avg[cc, dd, ee] += temp_weights[cc, dd, ee, ff] * total_call_put[ff]
                                    # avg[cc, dd, ee] = avg[cc, dd, ee] / temp_sum[cc, dd, ee]
                                    # percent[cc, dd, ee] = \
                                    #     (np.sum(temp_weights[cc, dd, ee, :] * holder_in_money)) / temp_sum[cc, dd, ee]
                                    avg[cc, dd, ee] = \
                                        (np.sum(temp_weights[cc, dd, ee, :] * total_call_put)) / temp_sum[cc, dd, ee]
                        ### ----- ###
                        percent = 1
                        percent_in_money[aa, n, m] = percent
                        hist_return_avg[aa, n, m] = avg
                elif my_type == 'diff_puts':
                    # Calls
                    call_num_matrix = np.ones(
                        (1, put_sell_max)) * call_sell_max
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
                    put_comm_matrix[0][-1] = 0
                    put_return = np.dot(
                        put_base, put_num_matrix) * 100 - put_comm_matrix
                    # Calculations
                    for aa in range(put_sell_max):
                        total_call_put = (call_return[:, aa] + put_return[:, aa]) / \
                                         (put_sell_max - aa - 1 + call_sell_max)
                        ### ----- ###
                        # Creating the matrices for storing results
                        holder_in_money = np.zeros(len(total_call_put))
                        for bb in range(len(total_call_put)):
                            if total_call_put[bb] > 0:
                                holder_in_money[bb] = 1
                        ### ----- ###
                        # percent = np.zeros((temp_weights.shape[0],
                        #                     temp_weights.shape[1],
                        #                     temp_weights.shape[2]))
                        avg = np.zeros((temp_weights.shape[0],
                                        temp_weights.shape[1],
                                        temp_weights.shape[2]))
                        for cc in range(temp_weights.shape[0]):
                            for dd in range(temp_weights.shape[1]):
                                for ee in range(temp_weights.shape[2]):
                                    # for ff in range(temp_weights.shape[3]):
                                    #     avg[cc, dd, ee] += temp_weights[cc, dd, ee, ff] * total_call_put[ff]
                                    # avg[cc, dd, ee] = avg[cc, dd, ee] / temp_sum[cc, dd, ee]
                                    # percent[cc, dd, ee] = \
                                    #     (np.sum(temp_weights[cc, dd, ee, :] * holder_in_money)) / temp_sum[cc, dd, ee]
                                    avg[cc, dd, ee] = \
                                        (np.sum(temp_weights[cc, dd, ee, :] * total_call_put)) / temp_sum[cc, dd, ee]
                        ### ----- ###
                        percent = 1
                        percent_in_money[-(aa + 1), n, m] = percent
                        hist_return_avg[-(aa + 1), n, m] = avg
    return [percent_in_money, hist_return_avg]


# @jit(parallel=True, fastmath=True, nopython=True)
def sine_weights(phase, freq, amplitude,
                 price_history, total_call_put, base_weight):
    time_series = np.arange(0, len(price_history), 1)
    # numpy.meshgrid doesn't work in numba so have to manually do this shit
    # np.meshgrid(len(phase), len(freq), len(amplitude), len(time_series), indexing = 'ij')
    phase_mesh = np.zeros((len(phase), len(freq), len(amplitude), len(time_series)))
    freq_mesh = np.zeros((len(phase), len(freq), len(amplitude), len(time_series)))
    amplitude_mesh = np.zeros((len(phase), len(freq), len(amplitude), len(time_series)))
    time_series_mesh = np.zeros((len(phase), len(freq), len(amplitude), len(time_series)))
    for nn in range(len(phase)):
        phase_mesh[nn, :, :, :] = phase[nn]
        for mm in range(len(freq)):
            freq_mesh[nn, mm, :, :] = freq[mm]
            for pp in range(len(amplitude)):
                amplitude_mesh[nn, mm, pp, :] = amplitude[pp]
                for qq in range(len(time_series)):
                    time_series_mesh[nn, mm, pp, qq] = time_series[qq]
    # Creating the cosine weight function. We do freq * time_series since the freq already has
    # the other things factored into it
    weights = (amplitude_mesh / 2) * np.cos(freq_mesh * time_series_mesh + phase_mesh) + \
              (amplitude_mesh / 2) + base_weight
    # Flipping against the time_series axis so we have the weight for the oldest day first
    # Manually do this cuz numpy.flip is not supported
    # weights = np.flip(weights, axis=3)
    for nn in range(len(phase)):
        for mm in range(len(freq)):
            for pp in range(len(amplitude)):
                weights[nn, mm, pp, :] = weights[nn, mm, pp, ::-1]
    weights = weights[:, :, :, :len(total_call_put)]
    # Sum weights along the day axis
    sum_weights = np.sum(weights, axis=3)
    # Creating the matrices for storing results
    holder_in_money = np.zeros(len(total_call_put))
    for nn in range(len(total_call_put)):
        if total_call_put[nn] > 0:
            holder_in_money[nn] = 1
    num_in_money_w = np.sum(weights * holder_in_money, axis=3)
    # Calculating percent in money
    percent = num_in_money_w / sum_weights
    # Calculating total return avg
    avg = np.sum(weights * total_call_put, axis=3) / sum_weights
    return [percent, avg]


def backtest_score(best_returns_total, test_date, expiry_dates, price_history_all,
                   fixed_commission, contract_commission):
    unique_days = np.array(np.unique(best_returns_total[:, 1]), dtype=int)
    # unique_days
    for n in unique_days:
        days_till_expiry = np.busday_count(test_date, expiry_dates[n])
        # Converting datetime to epoch days
        final_date = datetime.datetime.combine(expiry_dates[n], datetime.time())
        final_date = int(final_date.timestamp() / 86400)
        # Getting the expiry date price
        expiry_date_price = price_history_all[price_history_all[:, 0] == final_date][0, 1]
        # Getting the results for that day
        day_return = best_returns_total[best_returns_total[:, 1] == n]
        # Calculating returns, this takes into account 2 transaction fees
        call_base = (np.minimum(day_return[:, 2] - expiry_date_price, 0) + day_return[:, 3]) * 100 * day_return[:, 4]
        put_base = (np.minimum(expiry_date_price - day_return[:, 5], 0) + day_return[:, 6]) * 100 * day_return[:, 7]
        call_comm = np.zeros(len(day_return))
        put_comm = np.zeros(len(day_return))
        for m in range(len(day_return)):
            if day_return[m, 4] == 0:
                call_comm[m] = 0
            else:
                call_comm[m] = (fixed_commission + contract_commission * day_return[m, 4]) * 2
            if day_return[m, 7] == 0:
                put_comm[m] = 0
            else:
                put_comm[m] = (fixed_commission + contract_commission * day_return[m, 7]) * 2
        total_return = (call_base + put_base - call_comm - put_comm) / (day_return[:, 4] + day_return[:, 7])
        total_return_day = total_return / days_till_expiry
        # Scoring method used to see if our prediction is good
        scores_day = total_return_day - day_return[:, 0]
        # Adding the scores to our matrix
        day_return[:, 9] = scores_day
        best_returns_total[best_returns_total[:, 1] == n] = day_return
    # Multiplying the scores by the percent confidence we had in it
    score = best_returns_total[:, 8] * best_returns_total[:, 9] * 0.01
    return score



def actual_score(return_avg, percent_in_money,
                 exp_date_price, sorted_prices,
                 fixed_commission, contract_commission):
    # Creating scores array
    return_avg_cp = cp.array(return_avg)
    percent_in_money_cp = cp.array(percent_in_money)
    for a in range(2):
        # When a == 0, we are doing 0 calls, 1 put
        # When a == 1, we are doing 1 call, 0 puts
        if a == 0:
            put_strike_price = sorted_prices[:, 0]
            put_premium = sorted_prices[:, 5]
            put_base = (np.minimum(exp_date_price - put_strike_price, 0) + put_premium)
            put_comm = contract_commission + fixed_commission
            total_return = cp.array(put_base * 100 - put_comm)
            for m in range(len(total_return)):
                put_scores = cp.multiply(cp.subtract(total_return[m], return_avg_cp[a, m, :, :, :]),
                                         percent_in_money_cp[a, m, :, :, :])
                # for n in range(return_avg.shape[2]):
                #     for p in range(return_avg.shape[3]):
                #         for q in range(return_avg.shape[4]):
                #             if put_scores[n, p, q] > 0:
                #                 put_scores[n, p, q] = 0
        if a == 1:
            call_strike_price = sorted_prices[:, 0]
            call_premium = sorted_prices[:, 1]
            call_base = (np.minimum(call_strike_price - exp_date_price, 0) + call_premium)
            call_comm = contract_commission + fixed_commission
            total_return = cp.array(call_base * 100 - call_comm)
            for m in range(len(total_return)):
                call_scores = cp.multiply(cp.subtract(total_return[m], return_avg_cp[a, m, :, :, :]),
                                          percent_in_money_cp[a, m, :, :, :])
                # for n in range(return_avg.shape[2]):
                #     for p in range(return_avg.shape[3]):
                #         for q in range(return_avg.shape[4]):
                #             if call_scores[n, p, q] > 0:
                #                 call_scores[n, p, q] = 0
    scores = put_scores + call_scores
    return scores