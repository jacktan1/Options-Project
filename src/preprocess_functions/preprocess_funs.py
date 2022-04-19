import datetime
import multiprocessing
from multiprocessing.pool import Pool
import numpy as np
import os
from pathlib import Path
from .preprocess_funs_multithread import read_and_format_multi, remove_split_error_options_multi
import time


def read_and_format(ticker, option_data_path, logger):
    """
    Read raw options file, filter for ticker, and format option features as necessary. (multithread)
    Append date options DataFrame into a single dictionary.

    :param ticker: ticker symbol (string)
    :param option_data_path: path where option data files are stored (string)
    :param logger: logger to record system outputs
    :return: options_dict: dictionary with all date options
    """

    # Bookkeeping variables
    input_list = []
    my_pool = Pool(multiprocessing.cpu_count())
    options_dict = dict()
    start_time = time.time()

    # Get all date files we need to read
    my_years = os.listdir(option_data_path)
    for year in my_years:
        logger.info(f"Reading {year}")
        my_months = os.listdir(os.path.join(option_data_path, year))
        for month in my_months:
            my_days = os.listdir(os.path.join(option_data_path, year, month))
            for day in my_days:
                input_list.append({"ticker": ticker, "data_path": option_data_path,
                                   "ymd": [year, month, day]})

    # Multithread read and format options
    ticker_options_list = my_pool.map(read_and_format_multi, input_list)

    for n in ticker_options_list:
        # Log message if any
        [logger.info(my_message) for my_message in n["messages"]]

        # Aggregate options into dictionary
        if n["date"] not in options_dict.keys():
            options_dict[n["date"]] = n["df"]
        else:
            options_dict[n["date"]] = options_dict[n["date"]].append(n["df"], ignore_index=True)

    # Remove dates with no options
    option_data_dates = list(options_dict.keys())

    for date in option_data_dates:
        if options_dict[date].shape[0] == 0:
            options_dict.pop(date)

    logger.info(f"Reading and formatting - {round(time.time() - start_time, 2)} seconds")

    return options_dict


def remove_split_error_options(options_dict, hist_closing_df, logger):
    """
    Identify pre-split and split dates (if any). Calculate the split factor of each split.
    Take snapshot of option spreads on the pre-split dates. Adjust strikes by split factor.
    Group date options by which split "section" they belong in. Pass on each section to have
    error options removed, and append cleaned date options into dict.

    Assumes that data date is continuous in options dict. (Aka. not just a few months from
    various years)

    :param hist_closing_df: historical end of day prices (DataFrame)
    :param options_dict: dictionary of date options (dict)
    :param logger: logger to record system outputs
    :return: clean_options_dict: dictionary of cleaned date options (dict)
    """

    # Bookkeeping variables
    clean_options_dict = dict()
    input_list = []
    presplit_options_dict = dict()
    split_agg_dict = dict()
    start_time = time.time()

    # Option data dates
    option_dates = sorted(options_dict.keys())
    min_date = np.min(option_dates)
    max_date = np.max(option_dates)

    # Dates to obtain pre-split spreads. Remove last entry (it is not a pre-split date)
    presplit_df = hist_closing_df[~hist_closing_df.duplicated(subset="adjustment factor", keep="last")]
    presplit_df = presplit_df.iloc[:-1, ]

    # Dates to remove and section data. Remove first entry (it is not a split date)
    split_df = hist_closing_df[~hist_closing_df.duplicated(subset="adjustment factor", keep="first")]
    split_df = split_df.iloc[1:, ]

    # Filter for splits within option data range (assumes input data is continuous)
    split_df = split_df[(split_df["date"] >= min_date) &
                        (split_df["date"] <= max_date)][
        ["date", "adjustment factor"]].reset_index(drop=True)

    presplit_df = presplit_df[(presplit_df["date"] >= min_date) &
                              (presplit_df["date"] <= max_date)][
        ["date", "adjustment factor"]].reset_index(drop=True)

    # Edge case: When split happens on last date, drop because there would be nothing to adjust using it
    if max_date in split_df["date"]:
        split_df = split_df.iloc[:-1]
        presplit_df = presplit_df.iloc[:-1]

    # If no split occurred, return raw options. (Could lead to flaws if split occurs just before "first date")
    if split_df.shape[0] == 0:
        logger.info(f"No stock splits detected in [{min_date}, {max_date})")
        clean_options_dict = options_dict
        return clean_options_dict
    else:
        logger.info(f"Detected split dates: {list(split_df['date'])}")

    # Create split ratios df, use pre-split dates to adjust presplit spreads
    split_ratios_df = presplit_df[["adjustment factor"]] / split_df[["adjustment factor"]]
    split_ratios_df["date"] = presplit_df["date"]
    split_ratios_df.rename(columns={"adjustment factor": "split ratio"}, inplace=True)

    # Capture pre split date spreads into dict
    for my_date in presplit_df["date"]:
        # Get presplit option spread
        presplit_options = options_dict[my_date][["expiration date", "tag", "strike price"]].copy()
        split_ratio = float(split_ratios_df[split_ratios_df["date"] == my_date]["split ratio"])

        # Add expected strike prices after adjustment
        presplit_options["adj strike price"] = (presplit_options["strike price"] / split_ratio).round(2)
        # Rename original column
        presplit_options.rename(columns={"strike price": "raw strike price"}, inplace=True)
        # Add to dict
        presplit_options_dict[my_date] = presplit_options

    # Bin option data by split dates
    for my_date in option_dates:
        # Drop split date options - too inconsistent to use
        if my_date not in list(split_df["date"]):
            # Get the most recent pre-split date
            presplit_date = np.max(split_ratios_df[split_ratios_df["date"] < my_date]["date"])

            # If no pre-split date, return original
            if not isinstance(presplit_date, datetime.date):
                clean_options_dict[my_date] = options_dict[my_date]
            # If pre-split date found, add {date: options_df} dictionary to pre-split dictionary
            else:
                if presplit_date in split_agg_dict.keys():
                    split_agg_dict[presplit_date].update({my_date: options_dict[my_date]})
                else:
                    split_agg_dict[presplit_date] = {my_date: options_dict[my_date]}

    # Convert pre-split dictionary into list for each section to be processed in parallel
    for my_date in split_agg_dict.keys():
        input_list.append({"options dict": split_agg_dict[my_date],
                           "pre-split date": my_date,
                           "pre-split df": presplit_options_dict[my_date]})

    # Create as many threads as splits
    my_pool = Pool(len(split_agg_dict.keys()))

    # Multithread options cleaning
    clean_options_dict_list = my_pool.map(remove_split_error_options_multi, input_list)

    for n in clean_options_dict_list:
        # Log message if any
        [logger.info(my_message) for my_message in n["messages"]]

        # Aggregate "sections" into one dictionary
        clean_options_dict.update(n["dict"])

    logger.info(f"Removing error options - {round(time.time() - start_time, 2)} seconds")

    return clean_options_dict


def adjust_options(options_dict, hist_closing_df, logger):
    """
    Remove data dates without historical closing prices. Check if sum
    of volume is 0 on any data date. Adjust option features based on
    cumulative split factor.

    :param options_dict: dictionary of date options (dict)
    :param hist_closing_df: historical end of day prices (DataFrame)
    :param logger: logger to record system outputs
    :return: {options_dict (valid date options, dict), errors_dict (invalid date options, dict)}
    """

    # Housekeeping variables
    errors_dict = dict()
    start_time = time.time()

    # All dates
    data_dates = options_dict.keys()
    hist_closing_dates = list(hist_closing_df["date"])

    error_dates = [n for n in data_dates if n not in hist_closing_dates]

    for date in error_dates:
        logger.info(f"Data date {date} is not in historical closing! Saving to errors")

        # Add to errors
        errors_dict[date] = options_dict[date]

        # Remove key-value pair from dict
        options_dict.pop(date)

    for date in options_dict.keys():
        # Sanity check
        if options_dict[date]["volume"].sum() == 0:
            logger.warning(f"Cumulative sum of volume on {date} is 0!")

        cumulative_adj_ratio = float(hist_closing_df[hist_closing_df["date"] == date]["adjustment factor"])

        options_dict[date][["strike price", "ask price", "bid price", "last price"]] = \
            options_dict[date][["strike price", "ask price", "bid price", "last price"]] / cumulative_adj_ratio

        options_dict[date][["ask size", "bid size", "volume", "open interest"]] = \
            options_dict[date][["ask size", "bid size", "volume", "open interest"]] * cumulative_adj_ratio

    logger.info(f"Applying split adjustment factor - {round(time.time() - start_time, 2)} seconds")

    return {"adj dict": options_dict, "errors dict": errors_dict}


def attach_dividends(options_dict, dividends_df, logger):
    """
    Fix options with error expiry dates. Attach amount of priced-in dividends
    on data & expiration dates for all options.

    :param options_dict: dictionary of date options (dict)
    :param dividends_df: historical and future enf of day priced-in dividends (DataFrame)
    :param logger: logger to record system outputs
    :return: options_dict: dictionary of date options (dict)
    """

    # Housekeeping variables
    start_time = time.time()

    for date in options_dict.keys():

        date_options = options_dict[date].copy()

        exp_dates = set(date_options["expiration date"])

        error_exp_dates = [n for n in exp_dates if (n not in list(dividends_df["date"]))]

        # Fix error exp dates
        for exp_date in error_exp_dates:
            logger.info(f"Exp date {exp_date} is not in historical closing! Trying the day before...")
            new_exp_date = exp_date + datetime.timedelta(days=-1)
            # Sanity check
            assert (new_exp_date in list(dividends_df["date"])), f"{new_exp_date} still does not have closing price!"
            # replace exp date in options
            date_options.loc[date_options["expiration date"] == exp_date, "expiration date"] = new_exp_date

        # Add data date dividends
        date_options = date_options.merge(dividends_df, how="left",
                                          on="date")

        date_options.rename(columns={"dividend": "date div"}, inplace=True)

        # Add exp date dividends
        date_options = date_options.merge(dividends_df, how="left",
                                          left_on="expiration date", right_on="date")

        # Drop extra column from merge
        date_options.drop(columns="date_y", inplace=True)

        date_options.rename(columns={"dividend": "exp date div",
                                     "date_x": "date"}, inplace=True)

        # Sanity check
        assert not (date_options.isna().any(axis=1)).any(), f"Some data / exp dates in {date} don't have dividends!"

        # Cast back into dictionary
        options_dict[date] = date_options

    logger.info(f"Attaching dividends - {round(time.time() - start_time, 2)} seconds")

    return options_dict


def attach_eod_prices(options_dict, hist_closing_df, logger):
    """
    Split options into those which are complete (expiration date has passed),
    and those who are incomplete (expiration date is in the future).
    Attach end of day closing prices as appropriate.

    :param options_dict: dictionary of date options (dict)
    :param hist_closing_df: historical end of day prices (DataFrame)
    :param logger: logger to record system outputs
    :return: {complete_dict (complete options, dict), incomplete_dict (ongoing options, dict)}
    """

    # Housekeeping variables
    complete_dict = dict()
    incomplete_dict = dict()
    start_time = time.time()

    for date in options_dict.keys():
        date_options = options_dict[date].copy()

        # Add date close
        date_options["date close"] = float(hist_closing_df[hist_closing_df["date"] == date]["close"])

        # Add exp date close
        date_options = date_options.merge(hist_closing_df[["date", "close"]], how="left",
                                          left_on="expiration date", right_on="date",
                                          validate="m:1")

        # Drop extra column from merge
        date_options.drop(columns="date_y", inplace=True)

        date_options.rename(columns={"close": "exp date close",
                                     "date_x": "date"}, inplace=True)

        na_filter = date_options.isna().any(axis=1)

        complete_df = date_options[~na_filter]

        incomplete_df = date_options[na_filter].drop(columns=["exp date close"])

        # Sanity check
        assert complete_df.shape[0] + incomplete_df.shape[0] == date_options.shape[0]

        if complete_df.shape[0] > 0:
            complete_dict[date] = complete_df

        if incomplete_df.shape[0] > 0:
            incomplete_dict[date] = incomplete_df

    logger.info(f"Attaching end of day prices - {round(time.time() - start_time, 2)} seconds")

    return {"complete dict": complete_dict, "incomplete dict": incomplete_dict}


def save_by_year(complete_dict, incomplete_dict, errors_dict, ticker, save_dir, logger):
    """
    For each of "complete", "incomplete", and "error" options, aggregate by
    year and save to appropriate directory.

    :param complete_dict: dictionary of complete options (dict)
    :param incomplete_dict: dictionary of incomplete options (dict)
    :param errors_dict: dictionary of error options (dict)
    :param ticker: ticker symbol (str)
    :param save_dir: path to save aggregated DataFrame (str)
    :param logger: logger to record system outputs
    :return: None
    """
    # Housekeeping variables
    start_time = time.time()

    for n in [{"data": complete_dict, "type": "complete"},
              {"data": incomplete_dict, "type": "incomplete"},
              {"data": errors_dict, "type": "errors"}]:

        year_dict = dict()

        for date in n["data"].keys():
            year = str(date.year)
            if year not in year_dict.keys():
                year_dict[year] = n["data"][date]
            else:
                year_dict[year] = year_dict[year].append(n["data"][date], ignore_index=True)

        for year in year_dict.keys():
            year_dict[year].sort_values(by=["date", "expiration date", "strike price"], inplace=True)

            Path(os.path.join(save_dir, year)).mkdir(exist_ok=True)
            year_dict[year].to_csv(
                path_or_buf=os.path.join(save_dir, year, f"{ticker}_{year}_{n['type']}.csv"),
                index=False)

    logger.info(f"Aggregating and saving data - {round(time.time() - start_time, 2)} seconds")
