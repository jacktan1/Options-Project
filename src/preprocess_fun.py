import multiprocessing
from multiprocessing.pool import Pool
import os
import pandas as pd
from pathlib import Path
from src.preprocess_fun_parallel import attach_eod_prices, attach_dividends


def adjust_option_data(stock_of_interest, hist_closing_df, option_data_path, save_path):
    """
    Aggregate and adjust all option data for a given ticker.
    2 types of adjustments are done:
        - Strike price, ask/bid/last price, ask/bid size, volume and open interest are
          adjusted for historical splits.
        - End of day prices are added for both data and expiry dates. Options that expire
          on holiday Fridays are also moved according to historical closing data.

    :param stock_of_interest: ticker symbol (string)
    :param hist_closing_df: historical end of day prices for ticker (DataFrame)
    :param option_data_path: path where all the option data files are stored (string)
    :param save_path: path to save annual error options (string)
    :return: options_df_list: list of [complete, incomplete] annual options for given ticker ([[DataFrame, DataFrame]])
    """

    options_df_list = []
    my_pool = Pool(multiprocessing.cpu_count())

    my_years = os.listdir(option_data_path)
    for year in my_years:
        print(f"Currently processing: {year}")
        # Initialize DataFrames to aggregates option data for a given year
        complete_df = pd.DataFrame()
        incomplete_df = pd.DataFrame()
        error_df = pd.DataFrame()
        # Input to be parallelized
        day_input = []
        my_months = os.listdir(os.path.join(option_data_path, year))
        for month in my_months:
            my_days = os.listdir(os.path.join(option_data_path, year, month))
            for day in my_days:
                day_input.append({"ticker": stock_of_interest, "closing_df": hist_closing_df,
                                  "data_path": option_data_path, "ymd": [year, month, day]})

        # Entire year of data has been aggregated
        year_results = my_pool.map(attach_eod_prices, day_input)
        # Append to appropriate DataFrame
        for my_result in year_results:
            complete_df = complete_df.append(my_result["complete"], ignore_index=True)
            incomplete_df = incomplete_df.append(my_result["incomplete"], ignore_index=True)
            error_df = error_df.append(my_result["error"], ignore_index=True)

        # Sort
        for temp_df in [complete_df, incomplete_df, error_df]:
            if temp_df.shape[0] > 0:
                temp_df.sort_values(by=["date", "expiration date", "strike price"], inplace=True)
                temp_df.reset_index(drop=True, inplace=True)

        # Save error df
        if error_df.shape[0] > 0:
            Path(os.path.join(save_path, year)).mkdir(parents=True, exist_ok=True)
            error_df.to_csv(
                path_or_buf=os.path.join(save_path, year, f"{stock_of_interest}_{year}_error.csv"),
                index=False)

        options_df_list.append({"complete": complete_df, "incomplete": incomplete_df, "year": year})

    return options_df_list


def add_dividends(stock_of_interest, options_df_list, dividends_df, save_path):
    """
    Appends priced in dividends for both "data date" and "expiration date".
    Dividends should exist for all future expiration dates. This is because
    upstream dividend inference does not take into account for holidays, and
    weekend expiry dates have already been fixed.

    :param stock_of_interest: ticker symbol (string)
    :param options_df_list: list of [complete, incomplete] annual options for given ticker ([[DataFrame, DataFrame]])
    :param dividends_df: dividends data for said ticker (DataFrame)
    :param save_path: path to save annual complete and incomplete options (string)
    :return: None
    """

    input_list = []

    for year_df_list in options_df_list:
        complete_df = year_df_list["complete"]
        incomplete_df = year_df_list["incomplete"]
        year = year_df_list["year"]

        if complete_df.shape[0] > 0:
            input_list.append({"options_df": complete_df, "dividends_df": dividends_df, "year": year,
                               "save_path": save_path, "ticker": stock_of_interest, "tag": "complete"})

        if incomplete_df.shape[0] > 0:
            input_list.append({"options_df": incomplete_df, "dividends_df": dividends_df, "year": year,
                               "save_path": save_path, "ticker": stock_of_interest,  "tag": "incomplete"})

    my_pool = Pool(multiprocessing.cpu_count())
    my_pool.map(attach_dividends, input_list)

    return
