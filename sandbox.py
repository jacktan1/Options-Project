import numpy as np
import datetime as dt
from questrade_api import Questrade
import my_fun
import time
import pandas as pd
import copy
from numba import njit, prange, jit

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
strike_date = expiry_dates_new[0]
print(strike_date)

my_list = ['Strike Date', 'Sold Date', 'Type',
           'Strike Price', 'Sold Price', 'Sold Quantity']

my_list_2 = ['Transaction Date', 'Strike Date', 'Buy / Sell', 'Type', 'Strike Price', 'Premium Price',
             'Quantity', 'Change in Cash (USD)']

df = pd.DataFrame({'year': [2019],
                   'month': [11],
                   'day': [29]})
my_dates = pd.to_datetime(df, format='%Y%m%d')
date_1 = my_dates.iloc[0].asm8.astype('<M8[D]')

purchase_time = pd.to_datetime('2019-11-20 12:49:00')
purchase_time

my_data = np.array([[date_1, purchase_time, 'Call', 129.0, 6.4, 3],
                    [date_1, purchase_time, 'Put', 140.0, 5.4, 3]])

my_data_2 = np.array([[purchase_time, date_1, 'Sell', 'Call', 129.0, 6.4, 3, 1907],
                      [purchase_time, date_1, 'Sell', 'Put', 140.0, 5.4, 3, 1607]])

live_purchases = pd.DataFrame(columns=my_list, data=my_data)

transactions = pd.DataFrame(columns=my_list_2, data=my_data_2)

live_purchases.to_csv('live_options.csv', encoding='utf-8', index=True)

transactions.to_csv('transaction_history.csv', encoding='utf-8', index=True)


@jit(parallel=True, nopython=False)
def risk_analysis_v4(call_sell_max=2, put_sell_max=2):

    sorted_prices = np.zeros((3, 1))

    for n in range(call_sell_max + 1):
        globals()['hist_return_avg_' + str(n) + str(put_sell_max)] = \
            np.zeros((len(sorted_prices), len(sorted_prices)))
        globals()['percent_in_money' + str(n) + str(put_sell_max)] = \
            np.zeros((len(sorted_prices), len(sorted_prices)))
        globals()['risk_money' + str(n) + str(put_sell_max)] = \
            np.zeros((len(sorted_prices), len(sorted_prices)))
    for n in range(put_sell_max):
        globals()['hist_return_avg_' + str(call_sell_max) + str(n)] = \
            np.zeros((len(sorted_prices), len(sorted_prices)))
        globals()['percent_in_money' + str(call_sell_max) + str(n)] = \
            np.zeros((len(sorted_prices), len(sorted_prices)))
        globals()['risk_money' + str(call_sell_max) + str(n)] = \
            np.zeros((len(sorted_prices), len(sorted_prices)))

    return(hist_return_avg_21)

a = np.array([5])
a.all()
b = c = d = copy.deepcopy(a)
b += 4

qwe = np.ones((5,1)) * 2
asd = np.ones((1,2)) *3
np.multiply(qwe, asd)

qwe.shape

isinstance(qwe[0,0], np.float64)

np.array([[]]) == [[]]

aaa[0, :, :]
aass = np.array([[74, 74, 3], [75, 80, 74], [1, 2, 3]])
print(aass[:,0])
asdasd = np.argpartition(aass.flatten(), -9)
asdasd
lmao = np.where(aass == asdasd[3])[0][0]
lmao

aass
np.where(aass == 75)[0][0]

aaa = np.array([[74, 74, 3], [4, 5, 6]])
aaa
asa = np.zeros((1,3))
np.append(asa, aass, axis = 0)

aass.flatten()

bbb = np.append(aaa, aass, axis = 0)
bbb

np.flip(bbb, axis = 0)

aaa[aaa[:,1] > 700][:,1]

np.arange(1, -1, -1.0)

@jit()
def fuck_numba():
    qwe = np.array([[1, 2, 3], [2, 3, 4]])
    asd = np.array([[1, 2, 3], [2, 3, 4]])
    fff = qwe * asd
    a = sorted(np.argpartition(fff.flatten(), -3)[-3:], reverse = True)
    return a

print(fuck_numba())


t = time.time()
def fun():
    asdf = np.ones((2,500000))
    for n in range(500000):
        for m in range(2):
            asdf[n, m] = 5
    return asdf
print(time.time() - t)
