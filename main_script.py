import numpy as np
import datetime as dt
from questrade_api import Questrade
import my_fun
import time

### --- Initialization --- ###
q = Questrade()
#np.set_printoptions(threshold=np.inf)

stock_of_interest = 'JNJ'
stock_data = q.symbols_search(prefix = stock_of_interest)
stock_Id = stock_data['symbols'][0]['symbolId']
alphaVan_API = 'U4G0AXZ62E77Z161'
num_days_a_year = 252
fixed_commission = 9.95
contract_commission = 1

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


#Should be: range(0,len(all_options_data))
for n in range(0,len(all_options_data)):
    # Gets the strike date and calculates the number of days till expiry
    # COULD ADD EXTRA 1 FOR THE WEEKEND!
    strike_date = expiry_dates_new[n]
    days_till_expiry = np.busday_count(current_date, strike_date)
    # takes historical prices, obtains the percent change over a certain time gap
    # and annualizes it
    price_change_percent_annual = my_fun.price_change_annualized(price_history, days_till_expiry, num_days_a_year)
    # Taking the percent change and applying to the current price
    hist_final_price = my_fun.historical_final_price(price_history, current_price, days_till_expiry)
    # extracting options data
    daily_option_data = all_options_data[n]['chainPerRoot'][0]['chainPerStrikePrice']
    # sorted prices of options based on cost, call price and put price (in that order)
    sorted_prices = my_fun.price_sorting_new(daily_option_data, strike_date, stock_of_interest)
    # calculates the max gain and loss bearable
    [max_increase_decrease, hist_return_avg] = \
    my_fun.risk_analysis(sorted_prices, current_price, fixed_commission, contract_commission, hist_final_price, \
    num_call_buy = 1, num_put_buy = 1)
    # annualizes the risk based on the number of days till expiry
    max_per_annualized = my_fun.norm_percentage_annualized(max_increase_decrease, days_till_expiry, num_days_a_year)
    winning = my_fun.percent_chance_win(price_change_percent_annual, max_per_annualized)
    #my_fun.plot_heatmap(winning, sorted_prices, strike_date)
    my_fun.plot_heatmap_v2(winning, sorted_prices, str(str(stock_of_interest) + '/' + str(strike_date) + '_risk_prob'))
    my_fun.plot_heatmap_v2(hist_return_avg, sorted_prices, str(str(stock_of_interest) + '/' + str(strike_date) + '_returns'))
    print(time.time() - t)
