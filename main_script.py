import numpy as np
import datetime as dt
from questrade_api import Questrade
import my_fun
import time

### --- Initialization --- ###
q = Questrade()
finished = False
#np.set_printoptions(threshold=np.inf)

stock_of_interest = 'JNJ'
stock_data = q.symbols_search(prefix = stock_of_interest)
stock_Id = stock_data['symbols'][0]['symbolId']
alphaVan_API = 'U4G0AXZ62E77Z161'
num_days_a_year = 252
fixed_commission = 9.95
contract_commission = 1
call_sell_max = 10
put_sell_max = 10
list_len = 50

### --- Main Script --- ###

t = time.time()

current_date = my_fun.date_convert(q.time)
current_price = my_fun.get_current_price(stock_of_interest, stock_Id)
price_history = my_fun.extract_price_history(stock_of_interest, alphaVan_API)

all_options_data = q.symbol_options(stock_Id)['optionChain']
expiry_dates = []
for n in range (0,len(all_options_data)):
    expiry_dates.append(all_options_data[n]['expiryDate'])
expiry_dates_new = my_fun.date_convert(expiry_dates)
best_returns = np.zeros((list_len, 7))


#Should be: range(0,len(all_options_data))
for n in range(8, 9):
    # Gets the strike date and calculates the number of days till expiry
    # COULD ADD EXTRA 1 FOR THE WEEKEND!
    strike_date_index = n
    strike_date = expiry_dates_new[n]
    days_till_expiry = np.busday_count(current_date, strike_date)
    # Taking the percent change and applying to the current price
    hist_final_price = my_fun.historical_final_price(price_history, current_price, days_till_expiry)
    # extracting options data
    daily_option_data = all_options_data[n]['chainPerRoot'][0]['chainPerStrikePrice']
    # sorted prices of options based on cost, call price and put price (in that order)
    sorted_prices = my_fun.price_sorting_v2(daily_option_data, strike_date, stock_of_interest)
    # calculates the max gain and loss bearable
    [percent_chance_in_money, historical_return_avg, risk_money] = \
    my_fun.risk_analysis_v3(sorted_prices, current_price, fixed_commission, contract_commission, hist_final_price, \
    call_sell_max = 2, put_sell_max = 2)
    best_returns = my_fun.find_best(best_returns, percent_chance_in_money, historical_return_avg, \
    sorted_prices, strike_date_index, days_till_expiry)
    print(time.time() - t)

my_results = my_fun.beautify_dataframe(best_returns, expiry_dates_new)
while (finished == False):
    print(my_results)
    my_select = input('Which option would you like to exercise? (input index number(s) as a consecutive string e.g. 12345)')
    try:
        my_select = np.array(my_select, dtype = int)
    except:
        finished = True
        continue
    selected_pretty = my_results.loc[my_select]
    print('You have selected the following option(s):')
    print(selected_pretty)
    my_confirm = input('Are you sure you want to sell these options? (y/n)')
    if (my_confirm == 'y'):
        selected = best_returns[my_select]
        finished = True
    elif (my_confirm == 'n'):
        my_confirm = input('Order cancelled. Do you want to reselect(1) or terminate process(2)? (1/2)')
        if (my_confirm == '1'):
            continue
        elif (my_confirm == '2'):
            finished = True
            continue
        else:
            print('Input not understood, taking you back to results.')
    else:
        print('Input not understood, taking you back to results.')
