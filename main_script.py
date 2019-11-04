import numpy as np
import datetime as dt
from questrade_api import Questrade
import my_fun
import time

### --- Initialization --- ###
q = Questrade()
#np.set_printoptions(threshold=np.inf)

stock_of_interest = 'CVX'
stock_data = q.symbols_search(prefix = stock_of_interest)
stock_Id = stock_data['symbols'][0]['symbolId']
alphaVan_API = 'U4G0AXZ62E77Z161'
num_days_a_year = 252
fixed_commission = 9.95
contract_commission = 1
call_sell_max = 10
put_sell_max = 10

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
for n in range(3, 4):
    # Gets the strike date and calculates the number of days till expiry
    # COULD ADD EXTRA 1 FOR THE WEEKEND!
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
    call_sell_max = 3, put_sell_max = 3)
    # my_fun.plot_heatmap_v2(percent_chance_in_money, sorted_prices, \
    #     str(str(stock_of_interest) + '/' + str(strike_date) + '_percent_chance_in_money'))
    # my_fun.plot_heatmap_v2(historical_return_avg, sorted_prices, \
    #     str(str(stock_of_interest) + '/' + str(strike_date) + '_avg_returns'))
    # my_fun.plot_heatmap_v2(risk_money, sorted_prices, \
    #     str(str(stock_of_interest) + '/' + str(strike_date) + '_safety_money'))
    print(time.time() - t)
