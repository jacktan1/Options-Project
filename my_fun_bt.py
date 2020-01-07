import pandas as pd
import numpy as np
import datetime
import os
import plotly.graph_objs as go
from numba import jit, guvectorize, float64, prange
import cupy as cp


# Check if numpy function is usable in numba:
# https://github.com/numba/numba/issues/4074

### --- Start of Functions --- ###

def listdir_nohidden(path):
    my_list = []
    for f in os.listdir(path):
        if not f.startswith('.'):
            my_list.append(f)
    return my_list


def listfile_nohidden(path):
    my_list = []
    for f in os.listdir(path):
        if not f.startswith('.'):
            if os.path.isfile(os.path.join(path, f)):
                my_list.append(f)
    return my_list


# This function takes the current naked stock price, the expiry dates of all options and calculates the scaled current
# price at each of the expiry dates. This is a special version of the original function to be used for backtesting


def adjust_prices_bt(expiry_dates, naked_current_price, price_history, last_div_index):
    # Getting the date one day before ex-dividend date

    last_div_date = pd.to_datetime(
        price_history[last_div_index, 0], unit='D').asm8.astype('<M8[D]')
    exp_dates_adjusted_current_price = {}
    next_ex_date = 0
    # Searching for the next dividend date, have to add 2 since our index is one day before ex
    for n in range(last_div_index + 2, len(price_history)):
        if price_history[n, 2] != 0:
            next_ex_date = pd.to_datetime(
                price_history[n, 0], unit='D').asm8.astype('<M8[D]')
            break
        if n == len(price_history) - 1:
            assert n != 0, 'Could not find the next dividend date! Probably should not testing on \
            history this close to current date.'
    # Gotta subtract one since the max is one day before the next ex-dividend date
    num_days_div = np.busday_count(last_div_date, next_ex_date) - 1
    assert num_days_div > 0, "That's fucked up..."
    # Assume we don't know the next div payout, so take it to be same as last
    # Add 1 since our index is one day before the ex-div (which contains the amount)
    div_price = price_history[last_div_index + 1, 2]
    assert div_price > 0
    for n in range(len(expiry_dates)):
        expiry_date = expiry_dates[n]
        num_days = np.busday_count(last_div_date, expiry_date) % num_days_div
        assert num_days > 0, "That's fucked up..."
        if num_days == 0:
            # If expiry date is one day before next ex-dividend date, then price has all dividend priced in
            scaled_current_price = naked_current_price + div_price
        else:
            scaled_current_price = (num_days / num_days_div) * div_price + naked_current_price
        exp_dates_adjusted_current_price.update(
            {expiry_date: scaled_current_price})
    return exp_dates_adjusted_current_price


### ------ ###

# This function wrangles the options data to the same format as that of our non-backtest fucntion

def price_sorting_bt(option_data, strike_date, stock_symbol):
    assert (option_data.Symbol == stock_symbol).all(), 'Filtering was not done properly!'
    raw_data = option_data[option_data.ExpirationDate == str(strike_date)]
    call_raw_data = raw_data[raw_data.PutCall == 'call'].reset_index()
    put_raw_data = raw_data[raw_data.PutCall == 'put'].reset_index()
    assert (call_raw_data.StrikePrice == put_raw_data.StrikePrice).all(), \
        'Call and put rows have different strike prices!'
    assert (len(raw_data) % 2) == 0, 'Number of call and put entries are not the same!'
    daily_data = np.zeros((int(len(raw_data) / 2), 9))
    daily_data[:, 0] = call_raw_data.StrikePrice
    daily_data[:, 1] = call_raw_data.BidPrice
    daily_data[:, 2] = call_raw_data.BidSize
    daily_data[:, 3] = call_raw_data.AskPrice
    daily_data[:, 4] = call_raw_data.AskSize
    daily_data[:, 5] = put_raw_data.BidPrice
    daily_data[:, 6] = put_raw_data.BidSize
    daily_data[:, 7] = put_raw_data.AskPrice
    daily_data[:, 8] = put_raw_data.AskSize
    return daily_data


### ------ ###

def sine_meshgrid(gain_min, gain_max, freq_min_log, freq_max_log,
                  price_history, num_days_year, base_weight,
                  gain_density, freq_num, phase_density):
    # Creating the ranges for our test parameters
    # Change to np.float32 if memory problem arises
    time_series = np.arange(0, len(price_history), 1)
    phase = np.arange(-np.pi, np.pi, phase_density)
    freq = np.logspace(freq_min_log, freq_max_log, num=freq_num) * ((2 * np.pi) / num_days_year)
    amplitude = np.arange(gain_min, gain_max + gain_density, gain_density)
    # assert ((freq_density * num_days_year) % 1) == 0, 'Can not test periods that are not whole days!'
    # We use: phase, freq, amplitude, time_series ordering
    my_mesh = np.meshgrid(phase, freq, amplitude, time_series, indexing='ij')
    # Creating the cosine weight function. We do freq * time_series since the freq already has
    # the other things factored into it
    weights = my_mesh[2] * np.cos(my_mesh[1] * my_mesh[3] + my_mesh[0]) + base_weight
    # Flipping against the time_series axis so we have the weight for the oldest day first
    weights = np.flip(weights, axis=3)
    # Creating a cumulative sum matrix for weights to save future computation time
    cumsum_weights = np.cumsum(weights, axis=3)
    return [weights, cumsum_weights, phase, freq, amplitude]


### ------ ###


@guvectorize([(float64[:], float64[:], float64[:])],
             '(n),(n)->()',
             nopython=True,
             target='cuda')
def inner_cuda(a, b, wut):
    wut[0] = 1


### ------ ###


@jit(parallel=True, fastmath=True, nopython=True)
def risk_analysis_v5_bt(sorted_prices, final_prices, temp_weights, temp_sum,
                        fixed_commission, contract_commission):
    # Initializing the empty matrices. Ordering are as follows:
    # 0 Calls & 1 Puts
    # 1 Calls & 0 Puts
    # We use dimensional order of: type, call, put, phase, freq, amplitude
    hist_return_avg = np.zeros((2, len(sorted_prices),
                                temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    percent_in_money = np.zeros((2, len(sorted_prices),
                                 temp_weights.shape[0], temp_weights.shape[1], temp_weights.shape[2]))
    for a in prange(2):
        # When a == 0, we are doing 0 calls, 1 put
        # When a == 1, we are doing 1 call, 0 puts
        if a == 0:
            for n in prange(len(sorted_prices)):
                put_strike_price = sorted_prices[n, 0]
                put_premium = sorted_prices[n, 5]
                # Same no matter what
                put_base = (np.minimum(final_prices - put_strike_price, 0) + put_premium)[:, 0]
                put_comm_matrix = contract_commission + fixed_commission
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
                percent_in_money[a, n] = percent
                hist_return_avg[a, n] = avg
        elif a == 1:
            for n in prange(len(sorted_prices)):
                call_strike_price = sorted_prices[n, 0]
                call_premium = sorted_prices[n, 1]
                # Same no matter what
                call_base = (np.minimum(call_strike_price - final_prices, 0) + call_premium)[:, 0]
                call_comm_matrix = contract_commission + fixed_commission
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
                percent_in_money[a, n] = percent
                hist_return_avg[a, n] = avg
    return [percent_in_money, hist_return_avg]


### ------ ###


@jit(parallel=False, fastmath=True, nopython=True)
def actual_score(return_avg, percent_in_money,
                 exp_date_price, days_till_expiry, sorted_prices,
                 fixed_commission, contract_commission):
    return_scores = np.zeros(return_avg.shape)
    percent_scores = np.zeros(return_avg.shape)
    for a in prange(2):
        # When a == 0, we are doing 0 calls, 1 put
        # When a == 1, we are doing 1 call, 0 puts
        if a == 0:
            put_strike_price = sorted_prices[:, 0]
            put_premium = sorted_prices[:, 5]
            put_base = (np.minimum(exp_date_price - put_strike_price, 0) + put_premium)
            put_comm = contract_commission + fixed_commission
            # Get return per day
            total_return = (put_base * 100 - put_comm) / days_till_expiry
            for m in prange(len(total_return)):
                # Calculating score based off percentages
                if total_return[m] > 0:
                    percent_scores[a, m] = np.subtract(percent_in_money[a, m, :, :, :], 1)
                else:
                    percent_scores[a, m] = np.subtract(0, percent_in_money[a, m, :, :, :])
                # Calculating score based off returns
                put_scores = np.multiply(np.subtract(total_return[m], return_avg[a, m, :, :, :]),
                                         percent_in_money[a, m, :, :, :])
                for n in prange(return_avg.shape[2]):
                    for p in prange(return_avg.shape[3]):
                        for q in prange(return_avg.shape[4]):
                            if put_scores[n, p, q] > 0:
                                put_scores[n, p, q] = 0
                return_scores[a, m] = put_scores
        if a == 1:
            call_strike_price = sorted_prices[:, 0]
            call_premium = sorted_prices[:, 1]
            call_base = (np.minimum(call_strike_price - exp_date_price, 0) + call_premium)
            call_comm = contract_commission + fixed_commission
            # Get return per day
            total_return = (call_base * 100 - call_comm) / days_till_expiry
            for m in prange(len(total_return)):
                # Calculating score based off percentages
                if total_return[m] > 0:
                    percent_scores[a, m] = np.subtract(percent_in_money[a, m, :, :, :], 1)
                else:
                    percent_scores[a, m] = np.subtract(0, percent_in_money[a, m, :, :, :])
                # Calculating score based off returns
                call_scores = np.multiply(np.subtract(total_return[m], return_avg[a, m, :, :, :]),
                                          percent_in_money[a, m, :, :, :])
                for n in prange(return_avg.shape[2]):
                    for p in prange(return_avg.shape[3]):
                        for q in prange(return_avg.shape[4]):
                            if call_scores[n, p, q] > 0:
                                call_scores[n, p, q] = 0
                return_scores[a, m] = call_scores
    return [return_scores, percent_scores]


### ------ ###


def find_index(scores, phase_line, freq_line, amp_line):
    best_index = np.argmax(scores)
    phase_index = best_index // (scores.shape[1] * scores.shape[2])
    freq_index = np.remainder((best_index // scores.shape[2]), scores.shape[1])
    amp_index = np.remainder(best_index, scores.shape[2])
    phase_value = phase_line[phase_index]
    freq_value = freq_line[freq_index]
    amp_value = amp_line[amp_index]
    ideal_set = np.array([[phase_value, freq_value, amp_value]])
    ideal_index = np.array([[phase_index, freq_index, amp_index]])
    return [ideal_set, ideal_index]

