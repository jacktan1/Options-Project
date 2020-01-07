import numpy as np
import pandas as pd
import datetime
import os
import time
import my_fun
import my_fun_2
import my_fun_bt
import plotly.express as px

stock_symbol = 'BP'
# API tokens
alphaVan_token = 'U4G0AXZ62E77Z161'
IEX_token = 'pk_8ae91e6a0b11401b88e3d2b71aae39a7'
# Parameters for model
num_days_year = 252
# We use 0 for these because we only care about accuracy of our model
fixed_commission = 10
assignment_fee = 25
contract_commission = 1
# Percent in-money threshold needed for a order to be listed
in_money_thres = 65
# Range of each segment
segment_range = 10
# Number of items in each range
list_len = 10
# Scores will be stored here
final_scores = pd.DataFrame({'Date': [], 'Score': []})

### --- Tunable Parameters --- ###
# Parameters associated with price history weights, base should stay as 1
base_weight = 1
# cosine function; 0 means no gain (flat)
weight_gain = 0

# Date we want to test
data_path = 'backtest_data'
first_dir = os.listdir(data_path)

t = time.time()

# Getting historical price of stock
price_history_all = my_fun.extract_price_history_v2(stock_of_interest=stock_symbol,
                                                    api_key=alphaVan_token)
# Creating weights
[weights, cumsum_weights, phase_line, freq_line, amp_line] = \
    my_fun_bt.sine_meshgrid(gain_max=1,
                            gain_min=1,
                            freq_max_log=1,
                            freq_min_log=-3,
                            price_history=price_history_all,
                            num_days_year=num_days_year,
                            base_weight=base_weight,
                            gain_density=2,
                            freq_num=200,
                            phase_density=(np.pi / 16))
# Matrix to score the cumulative scores
cumsum_scores = np.zeros((weights.shape[0], weights.shape[1], weights.shape[2]))
cumsum_scores_p = np.zeros((weights.shape[0], weights.shape[1], weights.shape[2]))
day_best_combo = np.zeros((1, 3))
day_best_combo_p = np.zeros((1, 3))
for season in first_dir:
    second_dir = my_fun_bt.listdir_nohidden(str(data_path + '/' + season))
    for month_name in second_dir:
        daily_files = my_fun_bt.listfile_nohidden(str(data_path + '/' + season + '/' + month_name))
        for file_name in daily_files:
            year = int(file_name[0:4])
            month = int(file_name[5:7])
            day = int(file_name[8:10])
            test_date = datetime.date(year, month, day)

            print(time.time() - t)

            # Resetting the best returns matrix
            best_returns_total = np.zeros((1, 9))

            ### --- Wrangling the options data --- ###
            # Location of price history file
            file_path = str(data_path + '/' + season + '/' + month_name + '/' + file_name)
            option_data_all = pd.read_csv(file_path)
            option_data = option_data_all[option_data_all.Symbol == stock_symbol]
            # Getting end of day price for given stock
            for n in range(len(price_history_all)):
                stock_price = 0
                if price_history_all[n, 0] == (test_date - datetime.date(1970, 1, 1)).days:
                    stock_price = price_history_all[n, 1]
                    end_index = n
                    break
                if n == len(price_history_all):
                    assert stock_price != 0, 'Could not find closing price for that day!'
            # Getting price history available on day we are testing
            price_history = price_history_all[:end_index, :]
            [naked_history, naked_current_price, last_div_index, last_div_length] = \
                my_fun.get_naked_prices(my_history_price=price_history,
                                        current_price=stock_price,
                                        num_days_year=num_days_year)
            # Reading options data
            expiry_dates = list(option_data.ExpirationDate.unique())
            # Convert str to datetime and then to datetime.date
            for n in range(len(expiry_dates)):
                holder = datetime.datetime.strptime(expiry_dates[n], '%Y-%m-%d')
                expiry_dates[n] = holder.date()
            adjusted_test_price = my_fun_bt.adjust_prices_bt(expiry_dates=expiry_dates,
                                                             naked_current_price=naked_current_price,
                                                             price_history=price_history_all,
                                                             last_div_index=last_div_index)
            # Scoring all option expiry dates for given test date
            for n in range(0, len(expiry_dates)):
                print(time.time() - t)
                strike_date = expiry_dates[n]
                test_price_at_exp = adjusted_test_price.get(strike_date)
                days_till_expiry = np.busday_count(test_date, strike_date)
                # Getting the actual price on expiry date. Have to first convert date to datetime
                holder = datetime.datetime.combine(strike_date, datetime.time())
                int_strike_date = int(holder.timestamp() / 86400)
                exp_date_price = price_history_all[price_history_all[:, 0] == int_strike_date][0, 1]
                if days_till_expiry == 0:
                    continue
                assert days_till_expiry > 0, 'Wut?!'
                # Taking the percent change and applying to the current price
                hist_final_price = my_fun.historical_final_price(naked_price_history=naked_history,
                                                                 current_price=test_price_at_exp,
                                                                 days_till_expiry=days_till_expiry)
                sorted_prices = my_fun_bt.price_sorting_bt(option_data=option_data,
                                                           strike_date=strike_date,
                                                           stock_symbol=stock_symbol)
                # Truncating weights matrix to appropriate size
                temp_weights = weights[:, :, :, :len(hist_final_price)]
                temp_sum = cumsum_weights[:, :, :, len(hist_final_price) - 1]
                # Simulation based off our data
                [percent_in_money, hist_return_avg] = \
                    my_fun_bt.risk_analysis_v5_bt(sorted_prices=sorted_prices,
                                                  final_prices=hist_final_price,
                                                  temp_weights=temp_weights,
                                                  temp_sum=temp_sum,
                                                  fixed_commission=fixed_commission,
                                                  contract_commission=contract_commission)
                # Calculate daily return avg based off days till expiry
                daily_return_avg = hist_return_avg / days_till_expiry
                [return_scores, percent_scores] = \
                    my_fun_bt.actual_score(return_avg=daily_return_avg,
                                           percent_in_money=percent_in_money,
                                           exp_date_price=exp_date_price,
                                           days_till_expiry=days_till_expiry,
                                           sorted_prices=sorted_prices,
                                           fixed_commission=fixed_commission,
                                           contract_commission=contract_commission)
                # Summing over the first two axis
                daily_scores = np.sum(np.sum(return_scores, axis=0), axis=0)
                daily_scores_p = np.sum(np.sum(percent_scores, axis=0), axis=0)
                # Adding it to the cumulative score holder (return avg and percent in money)
                cumsum_scores += daily_scores
                cumsum_scores_p += daily_scores_p
                # Storing the best of a certain option expiry date for a given test date data
                [holder, holder_index] = my_fun_bt.find_index(scores=daily_scores,
                                                              phase_line=phase_line,
                                                              freq_line=freq_line,
                                                              amp_line=amp_line)
                [holder_p, holder_p_index] = my_fun_bt.find_index(scores=daily_scores_p,
                                                                  phase_line=phase_line,
                                                                  freq_line=freq_line,
                                                                  amp_line=amp_line)
                day_best_combo = np.append(day_best_combo, holder, axis=0)
                day_best_combo_p = np.append(day_best_combo_p, holder_p, axis=0)
### --- ###
[wombo_combo, wombo_combo_index] = my_fun_bt.find_index(scores=cumsum_scores,
                                                        phase_line=phase_line,
                                                        freq_line=freq_line,
                                                        amp_line=amp_line)
[wombo_combo_p, wombo_combo_p_index] = my_fun_bt.find_index(scores=cumsum_scores_p,
                                                            phase_line=phase_line,
                                                            freq_line=freq_line,
                                                            amp_line=amp_line)
### --- ###
day_best_combo = day_best_combo[1:, :]
day_best_combo_p = day_best_combo_p[1:, :]
[unique_val, unique_count] = np.unique(day_best_combo, axis=0, return_counts=True)
holder2 = np.zeros((unique_val.shape[0], unique_val.shape[1] + 1))
holder2[:, :unique_val.shape[1]] = unique_val
holder2[:, unique_val.shape[1]] = unique_count
combo_df = pd.DataFrame(data=holder2,
                        columns=['phase', 'frequency', 'amplitude', 'count'])
### --- ###
[unique_val_p, unique_count_p] = np.unique(day_best_combo_p, axis=0, return_counts=True)
holder2_p = np.zeros((unique_val_p.shape[0], unique_val_p.shape[1] + 1))
holder2_p[:, :unique_val_p.shape[1]] = unique_val_p
holder2_p[:, unique_val_p.shape[1]] = unique_count_p
combo_df_p = pd.DataFrame(data=holder2_p,
                          columns=['phase', 'frequency', 'amplitude', 'count'])
# Making plotly diagram
fig = px.scatter_3d(combo_df, x='phase', y='frequency', z='count',
                    color='amplitude', opacity=0.8,
                    color_continuous_scale=px.colors.diverging.Tealrose)
fig.update_layout(
    title="Best Sets on Option Expiry Dates on Test Dates (Based on Return)"
)
fig.show()
###
fig1 = px.scatter_3d(combo_df_p, x='phase', y='frequency', z='count',
                     color='amplitude', opacity=0.8,
                     color_continuous_scale=px.colors.diverging.Tealrose)
fig1.update_layout(
    title="Best Sets on Option Expiry Dates on Test Dates (Based on Percent)"
)
fig1.show()
print('nani')
