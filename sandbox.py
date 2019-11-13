import numpy as np
import datetime as dt
from questrade_api import Questrade
import my_fun
import time

### --- Initialization --- ###
q = Questrade()
finished = False
# np.set_printoptions(threshold=np.inf)

stock_of_interest = 'CVX'
stock_data = q.symbols_search(prefix=stock_of_interest)
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
current_price = my_fun.get_current_price(
    stock_of_interest, stock_Id, alphaVan_API)
price_history = my_fun.extract_price_history(stock_of_interest, alphaVan_API)
