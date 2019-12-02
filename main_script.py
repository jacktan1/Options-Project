import numpy as np
from questrade_api import Questrade
import time
import os
import my_fun
import my_fun_2

### --- Initialization --- ###
q = Questrade()

stock_of_interest = 'JNJ'
stock_data = q.symbols_search(prefix=stock_of_interest)
stock_Id = stock_data['symbols'][0]['symbolId']
alphaVan_token = 'U4G0AXZ62E77Z161'
IEX_token = 'pk_8ae91e6a0b11401b88e3d2b71aae39a7'
num_days_a_year = 252
fixed_commission = 9.95
assignment_fee = 24.95
contract_commission = 1.
list_len = 20 # This value has to be even
best_returns = np.zeros((list_len, 9))
# We don't want to set the number of days we want to calculate, since a lot of testing
best_returns_mass = np.zeros((1, 9))

### --- Main Script --- ###

t = time.time()

current_date = my_fun.date_convert(q.time)
current_price = my_fun.get_current_price(
    stock_of_interest, stock_Id, alphaVan_token)
price_history = my_fun.extract_price_history_v2(
    stock_of_interest, alphaVan_token)
[naked_history, naked_current_price, last_div_index] = my_fun.get_naked_prices(
    price_history, current_price, num_days_a_year)
all_options_data = q.symbol_options(stock_Id)['optionChain']
expiry_dates = my_fun.get_expiry_dates(all_options_data)
expiry_dates_new = my_fun.date_convert(expiry_dates)
adjusted_current_price = my_fun.adjust_prices(
    expiry_dates_new, naked_current_price, naked_history, IEX_token, stock_of_interest, last_div_index)

print(time.time() - t)

# Should be: range(0,len(all_options_data))
for n in range(0, len(all_options_data)):
    strike_date_index = n
    strike_date = expiry_dates_new[n]
    current_price_at_exp = adjusted_current_price.get(strike_date)
    # COULD ADD EXTRA 1 FOR THE WEEKEND! Or if early in the day / market hasn't opened
    days_till_expiry = np.busday_count(current_date, strike_date)
    # When we are not interested in options that expire the day of (or expired)
    if days_till_expiry <= 0:
        continue
    # Taking the percent change and applying to the current price
    hist_final_price = my_fun.historical_final_price(
        naked_history, current_price_at_exp, days_till_expiry)
    # extracting options data
    daily_option_data = all_options_data[n]['chainPerRoot'][0]['chainPerStrikePrice']
    # sorted prices of options based on cost, call price and put price (in that order)
    print(time.time() - t)
    sorted_prices = my_fun.price_sorting_v2(
        daily_option_data, strike_date, stock_of_interest)
    print(time.time() - t)
    # Simulation based off our data
    [percent_chance_in_money, historical_return_avg, risk_money] = \
    my_fun_2.risk_analysis_v4(sorted_prices, current_price_at_exp, fixed_commission,
                                  contract_commission, assignment_fee, hist_final_price,
                                  call_sell_max=3, put_sell_max=3)
    # [percent_chance_in_money, historical_return_avg, risk_money] = \
    # my_fun.risk_analysis_v3(sorted_prices, current_price_at_exp, fixed_commission,
    #                         contract_commission, assignment_fee, hist_final_price,
    #                         call_sell_max=3, put_sell_max=3)
    print(time.time() - t)
    # best_returns = my_fun.find_best(best_returns, percent_chance_in_money, historical_return_avg,
    #                                 sorted_prices, strike_date_index, days_till_expiry)
    best_returns_day = my_fun_2.find_best_v2(list_len, percent_chance_in_money, historical_return_avg,
                                     sorted_prices, strike_date_index, days_till_expiry)
    best_returns_mass = np.append(best_returns_mass, best_returns_day, axis = 0)

print(best_returns_mass.shape)

my_results = my_fun.beautify_to_df(best_returns, expiry_dates_new)
if (os.path.exists('results/' + stock_of_interest) == False):
    os.makedirs('results/' + stock_of_interest)
my_results.to_csv('results/' + stock_of_interest + '/' + stock_of_interest + '_' +
                  current_date.strftime('%Y-%m-%d') + '.csv', encoding='utf-8', index=True)
# my_fun.user_interaction(best_returns, my_results)
