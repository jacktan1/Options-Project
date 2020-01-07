import numpy as np
from questrade_api import Questrade
import time
import os
import my_fun
import my_fun_2

### --- Initialization --- ###
# Questrade Initialization
q = Questrade()
stock_of_interest = 'BP'
stock_data = q.symbols_search(prefix=stock_of_interest)
stock_id = stock_data['symbols'][0]['symbolId']
# API tokens
alphaVan_token = 'U4G0AXZ62E77Z161'
IEX_token = 'pk_8ae91e6a0b11401b88e3d2b71aae39a7'
# Parameters for model
num_days_year = 252
fixed_commission = 9.95
assignment_fee = 24.95
contract_commission = 1.
call_sell_max = 3
put_sell_max = 3
# Percent in-money threshold needed for a order to be listed
in_money_thres = 65
# Range of each segment
segment_range = 10
# Number of items in each range
list_len = 10
best_returns_total = np.zeros((1, 9))
# Parameters associated with price history weights
base_weight = 1
weight_gain = 0.5

### --- Main Script --- ###

t = time.time()
current_date = my_fun.date_convert(dates=q.time)
current_price = my_fun.get_current_price(stock_of_interest=stock_of_interest,
                                         stock_id=stock_id,
                                         api_key=alphaVan_token)
price_history = my_fun.extract_price_history_v2(stock_of_interest=stock_of_interest,
                                                api_key=alphaVan_token)
[naked_history, naked_current_price, last_div_index, last_div_length] = \
    my_fun.get_naked_prices(my_history_price=price_history,
                            current_price=current_price,
                            num_days_year=num_days_year)
all_options_data = q.symbol_options(stock_id)['optionChain']
expiry_dates = my_fun.date_convert(dates=my_fun.get_expiry_dates(all_options_data=all_options_data))
adjusted_current_price = my_fun.adjust_prices(expiry_dates=expiry_dates,
                                              naked_current_price=naked_current_price,
                                              naked_history=naked_history,
                                              api_key=IEX_token,
                                              stock_of_interest=stock_of_interest,
                                              last_div_index=last_div_index,
                                              last_div_length=last_div_length)
print(time.time() - t)

# Should be: range(0, len(expiry_dates))
for n in range(0, len(expiry_dates)):
    strike_date = expiry_dates[n]
    current_price_at_exp = adjusted_current_price.get(strike_date)
    # COULD ADD EXTRA 1 FOR THE WEEKEND! Or if early in the day / market hasn't opened
    days_till_expiry = np.busday_count(current_date, strike_date)
    # When we are not interested in options that expire the day of (or expired)
    if days_till_expiry <= 0:
        continue
    # Taking the percent change and applying to the current price
    hist_final_price = my_fun.historical_final_price(naked_price_history=naked_history,
                                                     current_price=current_price_at_exp,
                                                     days_till_expiry=days_till_expiry)
    # Extracting options data
    daily_option_data = all_options_data[n]['chainPerRoot'][0]['chainPerStrikePrice']
    # Sorted prices of options based on cost, call price and put price (in that order)
    sorted_prices = my_fun.price_sorting_v2(option_data=daily_option_data,
                                            strike_date=strike_date,
                                            stock_name=stock_of_interest)
    # Simulation based off our data
    [percent_chance_in_money, historical_return_avg, risk_money] = \
        my_fun_2.risk_analysis_v4(price_history=price_history,
                                  sorted_prices=sorted_prices,
                                  final_prices=hist_final_price,
                                  current_price=current_price_at_exp,
                                  fixed_commission=fixed_commission,
                                  contract_commission=contract_commission,
                                  assignment_fee=assignment_fee,
                                  base_weight=base_weight,
                                  weight_gain=weight_gain,
                                  num_days_year=num_days_year,
                                  call_sell_max=call_sell_max,
                                  put_sell_max=put_sell_max)
    best_returns_day = my_fun_2.find_best_v2(percent_in_money=percent_chance_in_money,
                                             historical_return_avg=historical_return_avg,
                                             sorted_prices=sorted_prices,
                                             in_money_thres=in_money_thres,
                                             strike_date_index=n,
                                             days_till_expiry=days_till_expiry,
                                             segment_range=segment_range,
                                             list_len=list_len,
                                             call_sell_max=call_sell_max,
                                             put_sell_max=put_sell_max)
    best_returns_total = np.append(
        best_returns_total, best_returns_day, axis=0)
    print(time.time() - t)

# Removing all the 0 rows
best_returns_total = best_returns_total[best_returns_total[:, 0] > 0]

my_results = my_fun.beautify_to_df(best_returns=best_returns_total,
                                   expiry_dates=expiry_dates)
if not os.path.exists('results/' + stock_of_interest):
    os.makedirs('results/' + stock_of_interest)
my_results.to_csv('results/' + stock_of_interest + '/' + stock_of_interest + '_' +
                  current_date.strftime('%Y-%m-%d') + '.csv', encoding='utf-8', index=True)
# my_fun.user_interaction(best_returns_total, my_results)
