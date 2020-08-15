import numpy as np
import datetime as dt
import re
import pandas as pd
from questrade_api import Questrade
import sys
from numba import jit
from pathlib import Path

q = Questrade()


def get_current_price(stock_of_interest, api_key):
    """
    Retrieves the current price of a stock using the questrade_api package.
    If questrade server is down, Alphavantage is used as backup. Note that Alphavantage
    prices are less accurate and do not track pre and post market.

    :param stock_of_interest: ticker symbol (string)
    :param api_key: API key used to access the Alphavantage server
    :return: current price of the stock is returned as a double
    """

    try:
        stock_id = q.symbols_search(prefix=stock_of_interest)['symbols'][0]['symbolId']
        price = q.markets_quote(stock_id)['quotes'][0]['lastTradePrice']
        if price is None:
            raise Exception
    except:
        print("Could not retrieve price from Questrade API, attempting Alphavantage instead!")
        try:
            price = float(pd.read_csv('https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=' +
                                      stock_of_interest + '&apikey=' + api_key + '&datatype=csv')['price'])
        except:
            print('Could not retrieve price from Alphavantage. Please ensure ticker symbol exists!')
            sys.exit(1)
    return price


def retrieve_price_history(stock_of_interest, api_key):
    """
    Retrieves daily closing price of a given ticker from the Alphavantage API.
    Checks and appends the prices to local version of ticker history is present.

    :param stock_of_interest: ticker symbol (string)
    :param api_key: API key used to access the Alphavantage server
    :return: daily closing price of stock ticker as a .csv
    """

    # Default parameters
    default_path = "data/daily_closing/"
    split_multiplier = 1
    data_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=' \
               + stock_of_interest + '&outputsize=full&apikey=' + api_key

    # Returns matrix with columns: date of price, closing price and dividend amount

    # Actual data starts at row 5
    history_data = pd.read_json(data_url)['Time Series (Daily)'].iloc[5:].reset_index()
    # Reset index to be datetime format
    history_data['index'] = pd.to_datetime(history_data['index'])
    # Create DataFrame to store data
    my_history = np.zeros((len(history_data), 3), dtype=object)
    # Extracting information we need
    for n in range(len(history_data)):
        # Check if stock forward/reverse split happened the following day (data is present -> past)
        if n > 0:
            temp_multiplier = float(history_data.iloc[n - 1, 1]['8. split coefficient'])
            if temp_multiplier != 1:
                split_multiplier = split_multiplier * temp_multiplier
        # Update DataFrame
        my_history[n] = [history_data.iloc[n, 0].strftime("%Y-%m-%d"),
                         round((float(history_data.iloc[n, 1]['4. close']) / split_multiplier), 3),
                         float(history_data.iloc[n, 1]['7. dividend amount'])]
    # Reverse list such that the oldest price is first
    my_history = my_history[::-1]
    # Removes the last element, since that is the current price, not history
    my_history = my_history[:-1, :]

    # Convert to DataFrame and store
    my_history_df = pd.DataFrame(data=my_history,
                                 columns=["date", "close", "dividend amount"])

    # Create data directory if it doesn't exist
    Path(default_path).mkdir(exist_ok=True)

    try:
        old_data = pd.read_csv(default_path + stock_of_interest + '.csv')
        my_history_df = pd.concat([old_data, my_history_df], ignore_index=True).drop_duplicates()
        if len(my_history_df['date']) != len(set(my_history_df['date'])):
            print(my_history_df)
            raise Exception("There are discrepancies in price between old and new files. Local version not updated!")
        else:
            my_history_df.to_csv(path_or_buf=(default_path + stock_of_interest + '.csv'),
                                 index=False)
    except FileNotFoundError:
        print("Local history of ticker '" + stock_of_interest + "' does not exist, created new file.")
        my_history_df.to_csv(path_or_buf=(default_path + stock_of_interest + '.csv'),
                             index=False)

    return my_history_df
