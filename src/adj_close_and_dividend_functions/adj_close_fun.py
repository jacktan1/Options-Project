import datetime
import os
import pandas as pd
import sys


def get_current_price(ticker: str, api_key: str, questrade_instance, logger):
    """
    Retrieves a ticker's current price using the questrade_api package.
    If questrade fails, Alphavantage is used. Note that Alphavantage
    prices are not snap quotes and do not track pre-/post-market.

    :param ticker: ticker of interest (str)
    :param api_key: API key used to access the Alphavantage server (str)
    :param questrade_instance: Questrade instance from 'questrade_api'
    :param logger: logger to record system outputs
    :return: current price of the ticker (float)
    """
    try:
        stock_id = questrade_instance.symbols_search(prefix=ticker)['symbols'][0]['symbolId']
        price = questrade_instance.markets_quote(stock_id)['quotes'][0]['lastTradePrice']
        if price is None:
            raise ValueError
    except (ValueError, IndexError):
        logger.warning(f"Could not retrieve {ticker} price from Questrade API, trying Alphavantage...")
        try:
            my_url = \
                f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
            price = float(pd.read_json(my_url).loc["05. price"])
        except KeyError:
            logger.error("Could not retrieve price from Alphavantage either. Ensure ticker symbol exists!")
            sys.exit(1)

    return price


def get_price_history(ticker: str, api_key: str, save_path: str, logger):
    """
    Retrieves historical daily closing price of a given ticker from Alpha Vantage
    Adjusts ticker price and dividend payout accordingly to forward/reverse splits.
    Returns DataFrame with features: [date, adjusted closing price, adjusted dividend payout, split factor]
    Checks and appends to local history if available.

    :param ticker: ticker symbol (string)
    :param api_key: API key used to access the Alphavantage server (string)
    :param save_path: Path used to save data (string)
    :param logger: logger to record system outputs
    :return: adjusted daily closing price and dividend payouts of the ticker (DataFrame)
    """

    # Default parameters
    history_df = []
    split_multiplier = 1
    my_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=" \
             f"{ticker}&outputsize=full&apikey={api_key}"

    resp_data = pd.read_json(my_url)

    # Sanity check
    if "Time Series (Daily)" not in resp_data.keys():
        logger.error("Error retreiving historical data from Alphavantage!")
        sys.exit(1)

    # Actual data starts at row 5
    history_data = resp_data['Time Series (Daily)'].iloc[5:].reset_index()

    # Rename and format
    history_data = history_data.rename(columns={"index": "date",
                                                "Time Series (Daily)": "data"})
    history_data["date"] = pd.to_datetime(history_data["date"]).dt.date

    for n in range(history_data.shape[0]):
        # Check if stock forward/reverse split happened the next day (data is present -> past)
        # n > 0 since we are calling 'n - 1'
        if n > 0:
            temp_multiplier = float(history_data.loc[n - 1, "data"]['8. split coefficient'])
            if temp_multiplier != 1:
                split_multiplier = split_multiplier * temp_multiplier

        my_day = history_data.loc[n, "date"]
        if my_day == datetime.date.today():
            continue
        else:
            temp_data = history_data.loc[n, "data"]
            # Add processed data for that date
            history_df.append([my_day,
                               round(float(temp_data["4. close"]) / split_multiplier, 5),
                               round(float(temp_data["7. dividend amount"]) / split_multiplier, 5),
                               round(split_multiplier, 8)])

    # Convert list to DataFrame
    history_df = pd.DataFrame(data=history_df,
                              columns=["date", "close", "dividend", "adjustment factor"])

    history_df.sort_values(by="date", ascending=True, inplace=True)

    try:
        old_data = pd.read_csv(os.path.abspath(os.path.join(save_path, f"{ticker}.csv")))
        logger.info(f"Found existing {ticker} data...")
        old_data["date"] = pd.to_datetime(old_data["date"]).dt.date
        # Sometimes there are rounding errors when using "read_csv"
        old_data["close"] = round(old_data["close"], 5)
        old_data["dividend"] = round(old_data["dividend"], 5)
        old_data["adjustment factor"] = round(old_data["adjustment factor"], 8)

        # Stitch the two together and remove duplicates
        history_df = pd.concat([old_data, history_df]).drop_duplicates().reset_index(drop=True)

        # See if there are any discrepancies
        if history_df.shape[0] != len(set(history_df["date"])):
            # Sort for easier manual comparison
            history_df.sort_values(by="date", inplace=True)
            logger.info(history_df[history_df.duplicated(subset=["date"], keep=False)])
            logger.error("Discrepancies between old and new data! Could be due to forward/reverse splits. \n"
                         "Data not updated, please manually fix!")
            sys.exit(1)
        else:
            history_df.to_csv(path_or_buf=os.path.join(save_path, f"{ticker}.csv"), index=False)
            logger.info(f"{ticker} adjusted close has been updated!")

    except FileNotFoundError:
        logger.info(f"No local `{ticker}` adjusted close data found! Creating new...")
        history_df.to_csv(path_or_buf=os.path.join(save_path, f"{ticker}.csv"), index=False)
        print(f"{ticker} adjusted close has been created!")

    return history_df
