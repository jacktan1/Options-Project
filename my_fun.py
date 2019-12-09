import numpy as np
import datetime as dt
import re
import pandas as pd
from questrade_api import Questrade
import urllib
import math
import os
from numba import prange, jit

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


# @jit(parallel=False, nopython=True)
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


@jit(parallel=False, nopython=True)
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
    # Returns a matrix with column order: strike price, call bid price, call bid size, call ask price, call ask size
    # put bid price, put bid size, put ask price, put ask size
    price_holder = np.zeros((len(option_data), 9))
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
        bid_call_price = call_put_data[2 * n]['bidPrice']
        if bid_call_price == None:
            bid_call_price = 0
        ask_call_price = call_put_data[2 * n]['askPrice']
        if ask_call_price == None:
            ask_call_price = 0
        bid_call_size = call_put_data[2 * n]['bidSize']
        ask_call_size = call_put_data[2 * n]['askSize']
        bid_put_price = call_put_data[2 * n + 1]['bidPrice']
        if bid_put_price == None:
            bid_put_price = 0
        ask_put_price = call_put_data[2 * n + 1]['askPrice']
        if ask_put_price == None:
            ask_put_price = 0
        bid_put_size = call_put_data[2 * n + 1]['bidSize']
        ask_put_size = call_put_data[2 * n + 1]['askSize']
        price_holder[n, 1:] = [bid_call_price, bid_call_size, ask_call_price, ask_call_size,
                               bid_put_price, bid_put_size, ask_put_price, ask_put_size]
    print('Done pulling data from Questrade API!')
    data_down = 0
    # Using this to see if data has been pulled successfully. Since bid_call_size is all
    # 0 when API data is down.
    for n in range(0, len(price_holder)):
        if price_holder[n, 2] == 0:
            data_down = data_down + 1
    # If data is down, we try to load it locally
    if data_down == len(price_holder):
        print('Questrade data is down! Trying to pull most recent data...')
        try:
            price_holder = pd.read_csv(
                str('bid_history/' + stock_name + '/' + str(strike_date) + '.csv')).iloc[:, 1:].to_numpy()
            print('Loaded local data!')
        except:
            print('Most recent data not found!')
            pass
    # If data is not down, then we save it locally
    if data_down < len(price_holder):
        col_names = ['Strike Price', 'Call bid price', 'Call bid size', 'Call ask price', 'Call ask size',
                     'Put bid price', 'Put bid size', 'Put ask price', 'Put ask size']
        if (os.path.exists('bid_history/' + stock_name) == False):
            os.makedirs('bid_history/' + stock_name)
        pd.DataFrame(columns=col_names, data=price_holder).to_csv('bid_history/' + stock_name + '/' +
                                                                  str(strike_date) +
                                                                  '.csv', encoding='utf-8', index=True)
        print('Questrade data saved locally!')
    return price_holder

### -------- ###


def beautify_to_df(best_returns, expiry_dates):
    my_results = pd.DataFrame(data=best_returns, columns=['(Percent * Avg Return)/(Contract * Day)',
                                                          'Strike Date', 'Call Strike', 'Call Bid Price',
                                                          'Call Size', 'Put Strike', 'Put Bid Price',
                                                          'Put Size', 'Percent Chance In Money'])
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
