import numpy as np
from questrade_api import Questrade
import my_fun
import time
import os

### --- Initialization --- ###
q = Questrade()
# np.set_printoptions(threshold=np.inf)

stock_of_interest = 'JNJ'
stock_data = q.symbols_search(prefix=stock_of_interest)
stock_Id = stock_data['symbols'][0]['symbolId']
alphaVan_token = 'U4G0AXZ62E77Z161'
IEX_token = 'pk_8ae91e6a0b11401b88e3d2b71aae39a7'
num_days_a_year = 252
fixed_commission = 9.95
contract_commission = 1
call_sell_max = 10
put_sell_max = 10
list_len = 100
best_returns = np.zeros((list_len, 7))

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

# Should be: range(0,len(all_options_data))
for n in range(1, 2):
    strike_date_index = n
    strike_date = expiry_dates_new[n]
    current_price_at_exp = adjusted_current_price.get(strike_date)
    # COULD ADD EXTRA 1 FOR THE WEEKEND! Or if early in the day / market hasn't opened
    days_till_expiry = np.busday_count(current_date, strike_date)
    # print(days_till_expiry)
    # Taking the percent change and applying to the current price
    hist_final_price = my_fun.historical_final_price(
        naked_history, current_price_at_exp, days_till_expiry)
    # extracting options data
    daily_option_data = all_options_data[n]['chainPerRoot'][0]['chainPerStrikePrice']
    # sorted prices of options based on cost, call price and put price (in that order)
    sorted_prices = my_fun.price_sorting_v2(
        daily_option_data, strike_date, stock_of_interest)
    # Simulation based off our data
    # TODO: Currently we don't take into account the number of call/put contracts actually available
    # we are assuming that it is less than the call and put max we set
    [percent_chance_in_money, historical_return_avg, risk_money] = \
        my_fun.risk_analysis_v3(sorted_prices, current_price_at_exp, fixed_commission,
                                contract_commission, hist_final_price, call_sell_max=2, put_sell_max=2)
    best_returns = my_fun.find_best(best_returns, percent_chance_in_money, historical_return_avg,
                                    sorted_prices, strike_date_index, days_till_expiry)
    print(time.time() - t)


my_results = my_fun.beautify_to_df(best_returns, expiry_dates_new)
if (os.path.exists('results/' + stock_of_interest) == False):
    os.makedirs('results/' + stock_of_interest)
my_results.to_csv('results/' + stock_of_interest + '/' + stock_of_interest + '_' +
                  current_date.strftime('%Y-%m-%d') + '.csv', encoding='utf-8', index=True)
# my_fun.user_interaction(best_returns, my_results)
