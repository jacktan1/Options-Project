import datetime
import numpy as np
import os
import pandas as pd
from pathlib import Path


def attach_eod_prices(input_dict):
    """
    1. Filters for ticker options from raw data
    2. Clean & rename columns
    3. Adjust features for splits (e.g. strike price, open interest, etc.)
    4. Group options into 'expired' and 'ongoing'
    5. Attach closing prices for every option's data date (and expiry date if applicable)

    :param input_dict: {stock_of_interest, hist_closing_df, option data_path, [year, month, day]} (dict)
    :return: {complete_df, incomplete_df, error_df} (dict)
    """
    # Input parameters
    ticker = input_dict["ticker"]
    hist_closing_df = input_dict["closing_df"]
    option_data_path = input_dict["data_path"]
    ymd = input_dict["ymd"]

    complete_df = pd.DataFrame()
    incomplete_df = pd.DataFrame()
    error_df = pd.DataFrame()

    # Load file
    daily_option_data = pd.read_csv(os.path.abspath(os.path.join(option_data_path, ymd[0], ymd[1], ymd[2])))

    # Filter for ticker
    temp_data = daily_option_data[daily_option_data["symbol"] == f"{ticker}"].copy()

    # Case: if no option data available, return empties
    if temp_data.shape[0] == 0:
        print(f"No {ticker} option data found in {ymd[2]}! Skipping...")
        return {"complete": complete_df, "incomplete": incomplete_df, "error": error_df}

    # Change to datetime
    temp_data["datadate"] = pd.to_datetime(temp_data["datadate"]).dt.date
    temp_data["expirationdate"] = pd.to_datetime(temp_data["expirationdate"]).dt.date

    # Check if data date is unique
    if len(np.unique(temp_data["datadate"])) == 1:
        temp_day = np.unique(temp_data["datadate"])[0]
    else:
        raise SystemExit("More than one unique day in each 'day' file! Options data bugged :/")

    # Drop columns
    temp_data.drop(columns=["optionkey", "symbol", "underlyingprice"], inplace=True)
    # Rename columns
    temp_data.rename(columns={"datadate": "date",
                              "expirationdate": "expiration date",
                              "putcall": "tag",
                              "strikeprice": "strike price",
                              "askprice": "ask price",
                              "asksize": "ask size",
                              "bidprice": "bid price",
                              "bidsize": "bid size",
                              "lastprice": "last price",
                              "openinterest": "open interest"},
                     inplace=True)
    # Reorder columns
    temp_data = temp_data[["date", "expiration date", "tag", "strike price", "ask price", "ask size", "bid price",
                           "bid size", "last price", "volume", "open interest"]]

    # Retrieve adjustment factor and closing price
    temp_ts = hist_closing_df[hist_closing_df["date"] == temp_day][["adjustment factor", "close"]]

    # Case: if no end of day price available
    if temp_ts.shape[0] == 0:
        print(f"Data date {temp_day} is not in historical closing! Saving to errors")
        error_df = temp_data
        return {"complete": complete_df, "incomplete": incomplete_df, "error": error_df}
    else:
        temp_adjustment_factor = float(temp_ts["adjustment factor"])
        temp_closing_price = float(temp_ts["close"])

    # Drop erroneous rows where 'expiration date' is before 'data date'
    temp_data = temp_data[temp_data["date"] <= temp_data["expiration date"]]

    # Adjusting option data for splits ...etc
    temp_data[["strike price", "ask price", "bid price", "last price"]] = \
        temp_data[["strike price", "ask price", "bid price", "last price"]] / temp_adjustment_factor
    temp_data[["ask size", "bid size", "volume", "open interest"]] = \
        temp_data[["ask size", "bid size", "volume", "open interest"]] * temp_adjustment_factor
    # Add data date closing price
    temp_data["closing price"] = temp_closing_price

    # Attempt to add closing prices for expiry dates
    close_days = set(hist_closing_df["date"])
    max_date = np.max(hist_closing_df["date"])
    for my_exp in list(set(temp_data["expiration date"])):
        exp_day_df = temp_data[temp_data["expiration date"] == my_exp].copy()
        # Case: closing price on expiry date can be found
        if my_exp in close_days:
            # Add exp date closing price
            exp_day_df["exp date closing price"] = float(hist_closing_df[hist_closing_df["date"] == my_exp]["close"])
            complete_df = complete_df.append(exp_day_df, ignore_index=True)
        # Case: expiry date is in the future
        elif my_exp > max_date:
            incomplete_df = incomplete_df.append(exp_day_df, ignore_index=True)
        # Case: expiry date is an error date
        else:
            print(f"Exp date {my_exp} is not in historical closing! Trying the day before...")
            new_exp = my_exp + datetime.timedelta(days=-1)
            # Sanity check
            assert (new_exp in close_days), f"{new_exp} still does not have closing price!"
            # Fix exp date and add its closing price
            exp_day_df[["expiration date", "exp date closing price"]] = \
                [new_exp, float(hist_closing_df[hist_closing_df["date"] == new_exp]["close"])]
            complete_df = complete_df.append(exp_day_df, ignore_index=True)

    # Sanity check
    assert (complete_df.shape[0] + incomplete_df.shape[0] == temp_data.shape[0]), \
        f"Complete options ({complete_df.shape[0]} rows) + incomplete options ({incomplete_df.shape[0]} rows) don't" \
        f"add up to total ({temp_data.shape[0]} rows)"
    assert error_df.shape[0] == 0, "`error_df` should be empty!"

    return {"complete": complete_df, "incomplete": incomplete_df, "error": error_df}


def attach_dividends(input_dict):
    """
    Attach value of priced-in dividends for every option's data and expiry dates.

    :param input_dict: {options_df, dividends_df, year, save_path, ticker, tag} (dict)
    :return: None
    """
    options_df = input_dict["options_df"]
    dividends_df = input_dict["dividends_df"]
    year = input_dict["year"]
    save_path = input_dict["save_path"]
    ticker = input_dict["ticker"]
    tag = input_dict["tag"]

    # Add data date dividends
    for my_date in list(set(options_df["date"])):
        # Data date div
        date_div_df = dividends_df[dividends_df["date"] == my_date]

        # Sanity check
        assert date_div_df.shape[0] > 0, f"Dividend data not found for: {my_date} (data date)"

        # Append data date dividends
        options_df.loc[options_df["date"] == my_date, "date div"] = float(date_div_df["dividend"])

        # Add exp date dividends
        for my_exp_date in list(set(options_df[options_df["date"] == my_date]["expiration date"])):
            # Exp date div
            exp_date_div_df = dividends_df[dividends_df["date"] == my_exp_date]

            # Sanity check
            assert exp_date_div_df.shape[0] > 0, f"Dividend data not found for: {my_exp_date} (exp date)"

            options_df.loc[(options_df["date"] == my_date) & (options_df["expiration date"] == my_exp_date),
                           "exp date div"] = float(exp_date_div_df["dividend"])

    # Sort
    options_df.sort_values(by=["date", "expiration date", "strike price"], inplace=True)

    # Save
    Path(os.path.join(save_path, year)).mkdir(parents=True, exist_ok=True)
    options_df.to_csv(
        path_or_buf=os.path.abspath(os.path.join(save_path, year, f"{ticker}_{year}_{tag}.csv")),
        index=False)

    print(f"{year} {ticker} {tag} adjusted options saved!")
