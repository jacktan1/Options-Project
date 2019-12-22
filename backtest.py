import numpy as np
import pandas as pd
import datetime
import os
import my_fun
import my_fun_2
import my_fun_bt

stock_symbol = 'BP'
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
# Parameters associated with price history weights
base_weight = 1
weight_gain = 5
# Date we want to test
year = 2016
month = 1
day = 4
test_date = datetime.date(year, month, day)
# Location of price history file
file_path = str('backtest_data/' + str(test_date) + '_OData.csv')

option_data_all = pd.read_csv(file_path)
option_data = option_data_all[option_data_all.Symbol == stock_symbol]
price_history_all = my_fun.extract_price_history_v2(stock_of_interest=stock_symbol,
                                                    api_key=alphaVan_token)
# Getting end of day price for given stock
for n in range(len(price_history_all)):
    stock_price = 0
    if price_history_all[n, 0] == (test_date - datetime.date(1970, 1, 1)).days:
        stock_price = price_history_all[n, 1]
        end_index = n
        break
    if n == len(price_history_all):
        assert stock_price != 0, 'Could not find closing price for that day!'
# Getting price history available at that time
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
adjusted_current_price = my_fun_bt.adjust_prices_bt(expiry_dates=expiry_dates,
                                                    naked_current_price=naked_current_price,
                                                    price_history=price_history_all,
                                                    last_div_index=last_div_index)
print('nani')
