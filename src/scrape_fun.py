import numpy as np
import pandas as pd
import sys
from pathlib import Path
import os
from tqdm import tqdm


def get_current_price(stock_of_interest, questrade_instance, api_key):
    """
    Retrieves the current price of a stock using the questrade_api package.
    If questrade server is down, Alphavantage is used as backup. Note that Alphavantage
    prices are less accurate and do not track pre and post market.

    :param stock_of_interest: ticker symbol (string)
    :param questrade_instance: Questrade instance from 'questrade_api'
    :param api_key: API key used to access the Alphavantage server (string)
    :return: current price of the ticker (float)
    """
    try:
        stock_id = questrade_instance.symbols_search(prefix=stock_of_interest)['symbols'][0]['symbolId']
        price = questrade_instance.markets_quote(stock_id)['quotes'][0]['lastTradePrice']
        if price is None:
            raise Exception
    except:
        print("Could not retrieve price from Questrade API, attempting Alphavantage instead!")
        try:
            price = float(pd.read_json("https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=" +
                                       stock_of_interest + '&apikey=' + api_key).loc["05. price"])
        except:
            print('Could not retrieve price from Alphavantage. Please ensure ticker symbol exists!')
            sys.exit(1)
    return price


def retrieve_price_history(stock_of_interest, api_key, save_path):
    """
    Retrieves historical daily closing price of a given ticker from the Alphavantage API.
    Adjusts ticker price and dividend payout accordingly to forward/reverse splits.
    Returns matrix with: date, adjusted closing price, adjusted dividend payout, and split factor
    Checks and appends the prices to local version of ticker history is present.

    :param stock_of_interest: ticker symbol (string)
    :param api_key: API key used to access the Alphavantage server (string)
    :param save_path: Path used to save data (string)
    :return: adjusted daily closing price and dividend payouts of the ticker (DataFrame)
    """

    # Default parameters
    split_multiplier = 1
    data_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=' \
               + stock_of_interest + '&outputsize=full&apikey=' + api_key

    # Actual data starts at row 5
    history_data = pd.read_json(data_url)['Time Series (Daily)'].iloc[5:].reset_index()
    # Reset index to be datetime format
    history_data['index'] = pd.to_datetime(history_data['index'])
    # Create DataFrame to store data
    my_history = np.zeros((len(history_data), 4), dtype=object)
    # Extracting information we need
    for n in range(len(history_data)):
        # Check if stock forward/reverse split happened the following day (data is present -> past)
        # n > 0 since we are calling 'n - 1'
        if n > 0:
            temp_multiplier = float(history_data.iloc[n - 1, 1]['8. split coefficient'])
            if temp_multiplier != 1:
                split_multiplier = split_multiplier * temp_multiplier
        # Update DataFrame
        my_history[n] = [history_data.iloc[n, 0],
                         round((float(history_data.iloc[n, 1]['4. close']) / split_multiplier), 3),
                         round((float(history_data.iloc[n, 1]['7. dividend amount']) / split_multiplier), 3),
                         round(split_multiplier, 3)]
    # Reverse list such that the oldest price is first
    my_history = my_history[::-1]
    # Removes the last row if that is the current date
    if my_history[-1, 0].date() == pd.to_datetime("today").date():
        my_history = my_history[:-1, :]

    # Convert to DataFrame and store
    my_history_df = pd.DataFrame(data=my_history,
                                 columns=["date", "close", "dividend amount", "adjustment factor"])

    # Create data directory if it doesn't exist
    Path(save_path).mkdir(exist_ok=True)

    try:
        old_data = pd.read_csv(os.path.abspath(os.path.join(save_path, stock_of_interest)) + ".csv")
        old_data["date"] = pd.to_datetime(old_data["date"])
        # Sometimes there are rounding errors when using "read_csv"
        old_data["close"] = round(old_data["close"], 3)
        old_data["dividend amount"] = round(old_data["dividend amount"], 3)
        old_data["adjustment factor"] = round(old_data["adjustment factor"], 3)
        my_history_df = pd.concat([old_data, my_history_df], ignore_index=True).drop_duplicates().reset_index(drop=True)
        if len(my_history_df['date']) != len(set(my_history_df['date'])):
            # Discrepancies are appended to the end of the concatenation
            print(my_history_df.tail())
            raise Exception("Discrepancies between old and new files. This could be due to forward/reverse splits."
                            "Data not updated, please manually fix!")
        else:
            my_history_df.to_csv(path_or_buf=(save_path + stock_of_interest + '.csv'),
                                 index=False)
    except FileNotFoundError:
        print("Local history of ticker '" + stock_of_interest + "' does not exist, created new file.")
        my_history_df.to_csv(path_or_buf=(os.path.abspath(os.path.join(save_path, stock_of_interest)) + ".csv"),
                             index=False)

    return my_history_df


def hist_option_data(stock_of_interest, stock_data_path, option_data_path):
    """
    This function aims to aggregate and adjust all option data for a given ticker.
    Adjustment is made based on historical splits. For example, had a stock undergone
    a forward split of factor 2, all previous strike price, ask/bid price ...etc are
    divided by 2. On the flip side, ask/bid size, volume ...etc are multiplied by 2.
    Function has to be modified depending on structure of options data.

    :param stock_of_interest: ticker symbol (string)
    :param stock_data_path: path where daily closing stock prices are saved (string)
    :param option_data_path: path where all the option data files are stored (string)
    :return: my_options_data: DataFrame containing all ticker specific options data
    """
    my_options_data = pd.DataFrame()
    try:
        my_history_df = pd.read_csv(os.path.abspath(os.path.join(stock_data_path, stock_of_interest)) + ".csv")
        my_history_df["date"] = pd.to_datetime(my_history_df["date"]).dt.date
    except FileNotFoundError:
        raise SystemExit("Security history for " + stock_of_interest + " not found in path: " +
                         os.path.abspath(os.path.join(stock_data_path, stock_of_interest)) + ".csv")

    # Nested loading of options data
    my_years = [year for year in os.listdir(option_data_path) if not year.startswith(".")]
    for year in tqdm(my_years, desc="year"):
        my_months = [month for month in os.listdir(os.path.join(option_data_path, year)) if not month.startswith(".")]
        for month in tqdm(my_months, desc="month"):
            my_days = [day for day in os.listdir(os.path.join(option_data_path, year, month)) if
                       not day.startswith(".")]
            for day in tqdm(my_days, desc="day"):
                try:
                    daily_option_data = pd.read_csv(os.path.abspath(os.path.join(option_data_path, year, month, day)))
                except FileNotFoundError:
                    raise SystemExit("Option data for " + stock_of_interest + " not found in path:" +
                                     os.path.abspath(os.path.join(option_data_path, year, month, day)))
                # Filtering for the right symbol
                temp_data = daily_option_data[daily_option_data["Symbol"] == stock_of_interest]
                # Dropping columns are reordering others
                temp_data = temp_data.drop(columns=["optionkey", "Symbol", "UnderlyingPrice"])[[
                    "DataDate", "ExpirationDate", "PutCall", "StrikePrice", "AskPrice",
                    "AskSize", "BidPrice", "BidSize", "LastPrice", "Volume", "openinterest"]]
                # Change to datetime
                temp_data["DataDate"] = pd.to_datetime(temp_data["DataDate"]).dt.date
                temp_data["ExpirationDate"] = pd.to_datetime(temp_data["ExpirationDate"]).dt.date
                if len(np.unique(temp_data["DataDate"])) == 1:
                    temp_day = np.unique(temp_data["DataDate"])[0]
                else:
                    raise SystemExit("More than one unique day in each file! Discount Options Data seriously bugged :/")
                # Retrieve adjustment factor and closing price
                temp_df = my_history_df[my_history_df["date"] == temp_day][["adjustment factor", "close"]]
                temp_adjustment_factor = float(temp_df["adjustment factor"])
                temp_closing_price = float(temp_df["close"])
                # Adjusting option data as needed
                temp_data[["StrikePrice", "AskPrice", "BidPrice", "LastPrice"]] = \
                    temp_data[[
                        "StrikePrice", "AskPrice", "BidPrice", "LastPrice"]] / temp_adjustment_factor
                temp_data[["AskSize", "BidSize", "Volume", "openinterest"]] = \
                    temp_data[["AskSize", "BidSize", "Volume", "openinterest"]] * temp_adjustment_factor
                temp_data["closing price"] = temp_closing_price
                # Append to DataFrame
                my_options_data = my_options_data.append(temp_data).reset_index(drop=True)

    # Renaming columns
    my_options_data = my_options_data.rename(columns={"DataDate": "date",
                                                      "ExpirationDate": "expiration date",
                                                      "PutCall": "type",
                                                      "StrikePrice": "strike price",
                                                      "AskPrice": "ask price",
                                                      "AskSize": "ask size",
                                                      "BidPrice": "bid price",
                                                      "BidSize": "bid size",
                                                      "LastPrice": "last price",
                                                      "openinterest": "open interest",
                                                      "Volume": "volume"})

    my_options_data = my_options_data.sort_values(by=["date", "expiration date", "strike price"]).reset_index(drop=True)
    return my_options_data


def add_dividends(stock_of_interest, my_options_data, dividends_data_path, save_path):
    """
    This function appends the price contribution due to dividends for the "posting" and
    "expiration" dates of each option. This allows us to be one step closer to working
    with the "true" price of the security on those dates.

    :param stock_of_interest: ticker symbol (string)
    :param my_options_data: DataFrame containing all option data for specified ticker (pd.DataFrame)
    :param dividends_data_path: path where dividend data is stored (str)
    :param save_path: path to save final options data (str)
    :return: None
    """
    # Load dividend data
    try:
        my_dividends_df = pd.read_csv(os.path.abspath(os.path.join(dividends_data_path, stock_of_interest)) + "_ts.csv")
        my_dividends_df["date"] = pd.to_datetime(my_dividends_df["date"]).dt.date
    except FileNotFoundError:
        raise SystemExit("Dividend data for " + stock_of_interest + " not found in path: " +
                         os.path.abspath(os.path.join(dividends_data_path, stock_of_interest)) + "_ts.csv")

    # Initialize empty containers
    my_date_div = pd.Series()
    my_exp_date_div = pd.Series()
    # adding dividend contribution info to DataFrame
    if all(my_dividends_df["amount"] == 0):
        my_date_div = pd.Series(np.zeros(my_options_data.shape[0]))
        my_exp_date_div = pd.Series(np.zeros(my_options_data.shape[0]))
    else:
        for my_date in sorted(my_options_data["date"].unique()):
            temp_options_df = my_options_data[my_options_data["date"] == my_date]
            date_div_price = float(my_dividends_df[my_dividends_df["date"] == my_date]["amount"])
            my_date_div = my_date_div.append(pd.Series(np.ones(temp_options_df.shape[0]) * date_div_price)).reset_index(
                drop=True)
            for my_exp_date in sorted(temp_options_df["expiration date"].unique()):
                exp_day_length = temp_options_df[temp_options_df["expiration date"] == my_exp_date].shape[0]
                ex_date_div_price = float(my_dividends_df[my_dividends_df["date"] == my_exp_date]["amount"])
                my_exp_date_div = my_exp_date_div.append(
                    pd.Series(np.ones(exp_day_length) * ex_date_div_price)).reset_index(drop=True)

    my_options_data["date div"] = my_date_div
    my_options_data["exp date div"] = my_exp_date_div

    # Save adjusted options data
    Path(save_path).mkdir(exist_ok=True)
    my_options_data.to_csv(path_or_buf=(os.path.abspath(os.path.join(save_path, stock_of_interest)) + ".csv"),
                           index=False)
    print("All adjusted option data for " + stock_of_interest + " has been aggregated and saved to path: " +
          os.path.abspath(os.path.join(save_path, stock_of_interest)) + ".csv")
    return
