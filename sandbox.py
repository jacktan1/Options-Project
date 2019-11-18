import numpy as np
import datetime as dt
from questrade_api import Questrade
import my_fun
import time
import pandas as pd

### --- Initialization --- ###
q = Questrade()
finished = False
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
list_len = 50

### --- Main Script --- ###

t = time.time()

current_date = my_fun.date_convert(q.time)
current_price = my_fun.get_current_price(
    stock_of_interest, stock_Id, alphaVan_token)
price_history = my_fun.extract_price_history_v2(
    stock_of_interest, alphaVan_token)
[naked_history, naked_current_price, last_div_index] = \
    my_fun.get_naked_prices(price_history, current_price, num_days_a_year)
all_options_data = q.symbol_options(stock_Id)['optionChain']
expiry_dates = my_fun.get_expiry_dates(all_options_data)
expiry_dates_new = my_fun.date_convert(expiry_dates)
exp_dates_adjusted_current_price = my_fun.adjust_prices(
    expiry_dates_new, naked_current_price, naked_history, IEX_token, stock_of_interest, last_div_index)
print(exp_dates_adjusted_current_price)
strike_date = expiry_dates_new[0]
print(exp_dates_adjusted_current_price.get(strike_date))
