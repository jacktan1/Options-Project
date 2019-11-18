import numpy as np
import datetime as dt
import re
import pandas as pd
from questrade_api import Questrade
import urllib
import math
from numba import njit, prange

q = Questrade()

### --- Start of Functions --- ###


def get_current_price(stock_of_interest, stock_Id, API_key):
    price = q.markets_quote(stock_Id)['quotes'][0]['lastTradePrice']
    if (price == None):
        price = pd.read_csv(str('https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=' +
                                stock_of_interest + '&apikey=' + API_key + '&datatype=csv'))
        price = float(price['price'])
    return price

### -------- ###


def get_expiry_dates(all_options_data):
    expiry_dates = []
    for n in range(0, len(all_options_data)):
        expiry_dates.append(all_options_data[n]['expiryDate'])
    return expiry_dates

### -------- ###

# After obtaining 'q.time' or 'expiry_dates',
# We can plug it into the following to get correct date formating


def date_convert(dates):
    actual_dates = []
    # This is for convering the current date (q.time)
    if len(dates) == 1:
        dates = dates['time']
        date_decomp = re.findall('([\d]{4})[-]([\d]{2})[-]([\d]{2})[T]', dates)
        actual_dates.append(dt.date(int(date_decomp[0][0]), int(
            date_decomp[0][1]), int(date_decomp[0][2])))
        # There's no point keeping a list if there's only one date
        actual_dates = actual_dates[0]
    # This is converting all the expiry dates
    else:
        for n in range(0, len(dates)):
            date_decomp = re.findall(
                '([\d]{4})[-]([\d]{2})[-]([\d]{2})[T]', dates[n])
            actual_dates.append(dt.date(int(date_decomp[0][0]), int(
                date_decomp[0][1]), int(date_decomp[0][2])))
    return actual_dates

### -------- ###

# Extracts the historical daily closing price of a given stock from AlphaVantage API


def extract_price_history_v2(stock_of_interest, API_key):
    # Returns matrix with columns: date of price, closing price and
    # Getting data link
    data_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=' \
        + stock_of_interest + '&outputsize=full&apikey=' + API_key
    # Extracting the json information from the site
    history_data = pd.read_json(data_url)
    # Actual data starts at row 5
    history_data = history_data['Time Series (Daily)'].iloc[5:].reset_index()
    history_data['index'] = pd.to_datetime(history_data['index'])
    my_history_price = np.zeros((len(history_data), 3))
    # Extracting information we need
    for n in range(len(history_data)):
        my_history_price[n] = [history_data.iloc[n, 0].timestamp() / 86400, history_data.iloc[n, 1]['4. close'],
                               history_data.iloc[n, 1]['7. dividend amount']]
    my_history_price = my_history_price[::-1]
    return my_history_price

### -------- ###

# Scale historical prices to remove role played by dividends


@njit(parallel=True)
def get_naked_prices(my_history_price, current_price, num_days_a_year):
    naked_history = my_history_price.copy()
    adjust_matrix = np.zeros((len(my_history_price), 1))
    last_div_index = 0
    last_div = 0
    num_days_quarter = num_days_a_year / 4
    # Below loop fills out all dividend data up to (and including) the last dividend date
    for n in range(len(my_history_price)):
        if my_history_price[n, 2] != 0:
            last_div = my_history_price[n, 2]
            if last_div_index == 0:
                for m in range(n + 1):
                    adjust_matrix[m] = -((num_days_quarter -
                                          n + m) / num_days_quarter) * last_div
                last_div_index = n
            elif last_div_index != 0:
                div_length = n - last_div_index
                for m in range(div_length):
                    adjust_matrix[last_div_index + 1 + m] = - \
                        ((m + 1) / div_length) * last_div
                last_div_index = n
    num_days_empty = (len(my_history_price) - 1) - last_div_index
    for n in range(num_days_empty):
        adjust_matrix[last_div_index + 1 + n] = - \
            ((n + 1) / num_days_quarter) * last_div
        if (n == num_days_empty - 1):
            naked_current_price = current_price - \
                ((n + 2) / num_days_quarter) * last_div
    naked_history[:, 1] = my_history_price[:, 1] + adjust_matrix[:, 0]
    return naked_history, naked_current_price, last_div_index

### -------- ###

# This function takes the current naked stock price, the expiry dates of all options and calculates the scaled current
# price at the expiry date.


def adjust_prices(expiry_dates_new, naked_current_price, naked_history, IEX_token, stock_of_interest, last_div_index):
    data_url = 'https://cloud.iexapis.com/stable/stock/' + stock_of_interest + '/dividends/next?token=' \
        + IEX_token + '&format=csv'
    last_div_date = pd.to_datetime(
        naked_history[last_div_index, 0], unit='D').asm8.astype('<M8[D]')
    exp_dates_adjusted_current_price = {}
    try:
        next_div_data = pd.read_csv(data_url)
        next_ex_date = pd.to_datetime(
            next_div_data.iloc[0, 0]).asm8.astype('<M8[D]')
        div_price = next_div_data.iloc[0, 4]
        # Gotta subtract one since the next ex Dividend Date is 1 day after the max
        num_days_div = np.busday_count(last_div_date, next_ex_date) - 1
    except:
        next_ex_date_int = naked_history[last_div_index, 0] + int(365 / 4)
        next_ex_date = pd.to_datetime(
            next_ex_date_int, unit='D').asm8.astype('<M8[D]')
        div_price = naked_history[last_div_index, 2]
        num_days_div = np.busday_count(last_div_date, next_ex_date)
    for n in range(len(expiry_dates_new)):
        expiry_date = expiry_dates_new[n]
        num_days = np.busday_count(last_div_date, expiry_date) % num_days_div
        if num_days == 0:
            scaled_current_price = naked_current_price + div_price
        else:
            inflated_at_expiry = (num_days / num_days_div) * div_price
            scaled_current_price = naked_current_price + inflated_at_expiry
        exp_dates_adjusted_current_price.update(
            {expiry_date: scaled_current_price})
    return exp_dates_adjusted_current_price

### -------- ###

# This function calculates the theoretical end prices of the stock at the expiry date


def historical_final_price(naked_price_history, current_price, days_till_expiry):
    final_prices = np.zeros(
        (int(len(naked_price_history) - days_till_expiry), 1))
    for n in range(0, len(final_prices)):
        holder = (naked_price_history[n + days_till_expiry, 1] -
                  naked_price_history[n, 1]) / naked_price_history[n, 1]
        final_prices[n] = current_price * (1 + holder)
    return final_prices

### -------- ###

# When given the options data from a certain date, we use this function to arrange the data into
# a "n by 5" array.


def price_sorting_v2(option_data, strike_date, stock_name):
    # Returns a matrix with column order: strike price, call price, call size, put price, put size
    price_holder = np.zeros((len(option_data), 5))
    id_holder = [0] * (2 * len(option_data))
    for n in range(0, len(option_data)):
        strike_price = option_data[n]['strikePrice']
        price_holder[n, 0] = strike_price
        call_ID = option_data[n]['callSymbolId']
        put_ID = option_data[n]['putSymbolId']
        id_holder[2 * n] = call_ID
        id_holder[2 * n + 1] = put_ID
    # Stupid Questrade API has max request length of 100...
    if len(id_holder) > 100:
        call_put_data = q.markets_options(
            optionIds=list(id_holder[0:100]))['optionQuotes']
        call_put_data = call_put_data + \
            q.markets_options(optionIds=list(id_holder[100:len(id_holder)]))[
                'optionQuotes']
    else:
        call_put_data = q.markets_options(
            optionIds=list(id_holder))['optionQuotes']
    for n in range(0, len(option_data)):
        bid_call_price = call_put_data[int(2 * n)]['bidPrice']
        bid_call_size = call_put_data[2 * n]['bidSize']
        bid_put_price = call_put_data[2 * n + 1]['bidPrice']
        bid_put_size = call_put_data[2 * n + 1]['bidSize']
        price_holder[n, 1] = bid_call_price
        price_holder[n, 2] = bid_call_size
        price_holder[n, 3] = bid_put_price
        price_holder[n, 4] = bid_put_size
    print('Done pulling data from Questrade API!')
    data_down = 0
    # Using this to see if data has been pulled successfully. Since bid_call_size is all
    # 0 when API data is down.
    for n in range(0, len(price_holder)):
        if price_holder[n, 2] == 0:
            data_down = data_down + 1
    if data_down == len(price_holder):
        print('Questrade data is down! Trying to pull most recent data...')
        try:
            price_holder = np.loadtxt(str('bid_history/' + str(stock_name) + '/' + str(str(strike_date) + '.csv')),
                                      delimiter=',')
            print('Loaded local data!')
        except:
            print('Most recent data not found!')
            pass
    if data_down < len(price_holder):
        print('Questrade data saved locally!')
        np.savetxt('bid_history/' + str(stock_name) + '/' +
                   str(str(strike_date) + '.csv'), price_holder, delimiter=",")
    return price_holder


### -------- ###

# Calculates the max increase or decrease in stock price while remaining in safe zone.
# call price is on rows, put price is on columns
# first sheet is max increase, second sheet is max decrease


def risk_analysis_v3(sorted_prices, current_price, fixed_commission, contract_commission, final_prices,
                     call_sell_max=1, put_sell_max=1):
    historical_return_avg = np.zeros(
        (len(sorted_prices), len(sorted_prices)), dtype=np.ndarray)
    percent_in_money = np.zeros(
        (len(sorted_prices), len(sorted_prices)), dtype=np.ndarray)
    risk_money = np.zeros(
        (len(sorted_prices), len(sorted_prices)), dtype=np.ndarray)
    # The rows represent call prices
    for n in range(0, len(sorted_prices)):
        # Progress indicator
        print(n)
        call_strike_price = sorted_prices[n, 0]
        call_premium = sorted_prices[n, 1]
        call_size = sorted_prices[n, 2]
        # The columns represent put prices
        for m in range(0, len(sorted_prices)):
            # reinitilaizing the max call and put matrix
            num_call_put_matrix = np.zeros((call_sell_max, put_sell_max))
            # reinitilaizing other matrices
            historical_return_avg_inner = np.zeros(
                (call_sell_max + 1, put_sell_max + 1))
            percent_in_money_inner = np.zeros(
                (call_sell_max + 1, put_sell_max + 1))
            risk_money_inner = np.zeros((call_sell_max + 1, put_sell_max + 1))
            ###
            put_strike_price = sorted_prices[m, 0]
            put_premium = sorted_prices[m, 3]
            put_size = sorted_prices[m, 4]
            ###
            # Seeing if these options actually exist
            if (call_premium == None) or (put_premium == None):
                percent_in_money[n, m] = None
                historical_return_avg[n, m] = None
            else:
                # Calls
                call_base = np.minimum(
                    call_strike_price - final_prices, 0) + call_premium
                call_num_matrix = np.arange(
                    0, call_sell_max + 1, 1).reshape(1, call_sell_max + 1)
                call_comm_matrix = fixed_commission + call_num_matrix * contract_commission
                call_comm_matrix[0][0] = 0
                call_return = call_base * call_num_matrix * 100 - call_comm_matrix

                # Puts
                put_base = np.minimum(
                    final_prices - put_strike_price, 0) + put_premium
                put_num_matrix = np.arange(
                    0, put_sell_max + 1, 1).reshape(1, put_sell_max + 1)
                put_comm_matrix = fixed_commission + put_num_matrix * contract_commission
                put_comm_matrix[0][0] = 0
                put_return = put_base * put_num_matrix * 100 - put_comm_matrix

                # The inner matrix rows will represent number of call contracts to sell
                for aa in range(0, call_sell_max + 1):
                    # The inner matrix columns will represent number of put contracts to sell
                    for bb in range(0, put_sell_max + 1):
                        # reinitialize parameter to calculate percentage chance to be in money
                        num_in_money = 0
                        risk_money_holder = 0
                        if (aa == 0) & (bb == 0):
                            historical_return_avg_inner[aa, bb] = 0
                            percent_in_money_inner[aa, bb] = 0
                            risk_money_inner[aa, bb] = 0
                        else:
                            total_call_put = (
                                call_return[:, aa] + put_return[:, bb]) / (aa + bb)
                            for cc in range(0, len(total_call_put)):
                                if total_call_put[cc] > 0:
                                    num_in_money += 1
                                else:
                                    risk_money_holder += total_call_put[cc]

                            historical_return_avg_inner[aa, bb] = np.sum(
                                total_call_put) / len(total_call_put)
                            percent_in_money_inner[aa, bb] = (
                                num_in_money / len(total_call_put)) * 100
                            if (len(total_call_put) - num_in_money) == 0:
                                risk_money_inner[aa, bb] = 0
                            else:
                                risk_money_inner[aa, bb] = risk_money_holder / \
                                    (len(total_call_put) - num_in_money)

                historical_return_avg[n, m] = historical_return_avg_inner
                percent_in_money[n, m] = percent_in_money_inner
                risk_money[n, m] = risk_money_inner

    return [percent_in_money, historical_return_avg, risk_money]

### -------- ###

# This function multiplies the percentage of winning with the average profit per contract
# and returns the top choices. If better than current top choices, it will update.


def find_best(best_returns, percent_in_money, historical_return_avg, sorted_prices,
              strike_date_index, days_till_expiry):
    [list_len, list_width] = best_returns.shape
    [nrows, ncols] = percent_in_money.shape
    for n in range(nrows):
        for m in range(ncols):
            # Method below takes into account the percent chance of being in money, only (avg return * percent) / day
            # daily_info = percent_in_money[n, m] * \
            #     historical_return_avg[n, m] * 0.01 * (1 / days_till_expiry)
            # Method below does not take into account the percent chance of being in money, only avg return / day
            daily_info = historical_return_avg[n, m] * (1 / days_till_expiry)
            daily_returns = np.append(np.ndarray.flatten(
                daily_info), np.array(best_returns[:, 0]))
            daily_returns = np.array(
                [x for x in daily_returns if str(x) != 'nan'])
            new_best = sorted((daily_returns[np.argpartition(daily_returns, (-list_len))][(-list_len):]),
                              reverse=True)
            # See if there has been any changes to the best returns matrix
            if (new_best == list(best_returns[:, 0])):
                continue
            else:
                different_elements = list()
                for aa in range(list_len):
                    if ((new_best[aa] in best_returns) == False):
                        different_elements.append(new_best[aa])
                best_returns_holder = np.zeros((list_len, list_width))
                best_returns_holder[0:(list_len - len(different_elements))] = \
                    best_returns[0:(list_len - len(different_elements))]
                for bb in range(len(different_elements)):
                    [call_row, put_col] = np.where(
                        daily_info == different_elements[bb])
                    # Order is 'percent chance * avg return per contract per day', strike date,
                    # call price, number calls, put price, number puts, percent_in_money
                    best_returns_holder[(list_len - len(different_elements) + bb), :] = \
                        [different_elements[bb], strike_date_index, sorted_prices[n, 0],
                         int(call_row), sorted_prices[m, 0], int(put_col), percent_in_money[n, m][call_row, put_col]]
                best_returns = best_returns_holder[best_returns_holder[:, 0].argsort()[
                    ::-1]]
    return best_returns

### -------- ###


def beautify_dataframe(best_returns, expiry_dates):
    my_results = pd.DataFrame(data=best_returns, columns=['(Percent * Avg Return)/(Contract * Day)',
                                                          'Strike Date', 'Call Price', 'Call Amount',
                                                          'Put Price', 'Put Amount', 'Percent Chance In Money'])
    expiry_dates = np.array(expiry_dates)
    date_indices = np.array(my_results['Strike Date'], dtype=int)
    my_results['Strike Date'] = expiry_dates[date_indices]
    return my_results

### -------- ###


def user_interaction(best_returns, my_results):
    finished = False
    while (finished == False):
        print(my_results)
        my_select = input(
            'Which option would you like to exercise? (input index number(s) as a consecutive string e.g. 12345)')
        try:
            my_select = int(my_select)
        except:
            finished = True
            continue
        selected_pretty = my_results.loc[my_select]
        print('You have selected the following option(s):')
        print(selected_pretty)
        my_confirm = input(
            'Are you sure you want to sell these options? (y/n)')
        if (my_confirm == 'y'):
            selected = best_returns[my_select]
            finished = True
        elif (my_confirm == 'n'):
            my_confirm = input(
                'Order cancelled. Do you want to reselect(1) or terminate process(2)? (1/2)')
            if (my_confirm == '1'):
                continue
            elif (my_confirm == '2'):
                finished = True
                continue
            else:
                print('Input not understood, taking you back to results.')
        else:
            print('Input not understood, taking you back to results.')
