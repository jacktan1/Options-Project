import numpy as np
import os
import pandas as pd


def read_and_format_multi(input_dict):
    """
    1. Filter for ticker options in raw data
    2. Reformat columns
    3. Remove true duplicates & fix error duplicates
    4. Select and rename columns

    :param input_dict: {stock_of_interest, data_path, [year, month, day]} (dict)
    :return: {options_df, date, messages} (dict)
    """
    # Unpack
    option_data_path = input_dict["data_path"]
    ticker = input_dict["ticker"]
    ymd = input_dict["ymd"]

    output_msg = []

    # Load file
    day_options_df = pd.read_csv(os.path.abspath(os.path.join(option_data_path, ymd[0], ymd[1], ymd[2])))

    # Filter for ticker
    options_df = day_options_df[day_options_df["symbol"].str.upper() == ticker].copy()

    # Format ticker to uppercase
    options_df["symbol"] = options_df["symbol"].str.upper()

    # Change to datetime, option type to lowercase, negative volume to positive
    options_df["datadate"] = pd.to_datetime(options_df["datadate"]).dt.date
    options_df["expirationdate"] = pd.to_datetime(options_df["expirationdate"]).dt.date
    options_df["putcall"] = options_df["putcall"].str.lower()
    options_df["volume"] = np.abs(options_df["volume"])

    # Remove true duplicates (Normally, if `split adjusted strike`==`error raw strike`, open interest shouldn't be same)
    options_df.drop_duplicates(subset=["optionkey", "openinterest"], keep="first",
                               ignore_index=True, inplace=True)

    # Check if there are error duplicates
    dup_options_filter = options_df.duplicated(subset=["expirationdate", "putcall", "strikeprice"],
                                               keep=False)

    # Decide which of the duplicates to keep
    if dup_options_filter.any():
        output_msg.append(f"Duplicate {ticker} option data found in {ymd[2]}!")
        nodup_options = options_df[~dup_options_filter]
        dup_options = options_df[dup_options_filter]
        kept_dup = pd.DataFrame()

        for option_key in list(set(dup_options["optionkey"])):
            temp_dup = dup_options[dup_options["optionkey"] == option_key].copy()
            if (temp_dup["putcall"] == "call").all():
                temp_dup["moneyness"] = temp_dup["underlyingprice"] - temp_dup["askprice"] - temp_dup["strikeprice"]
            else:
                temp_dup["moneyness"] = temp_dup["strikeprice"] - temp_dup["askprice"] - temp_dup["underlyingprice"]

            # Keep the option with less "moneyness"
            kept_dup = kept_dup.append(
                temp_dup[temp_dup["moneyness"] == temp_dup["moneyness"].min()].drop(columns="moneyness"))

        # Add "selected" dup to non-dups
        options_df = nodup_options.append(kept_dup)

    # Drop erroneous options where "data date" > "expiration date"
    options_df = options_df[options_df["datadate"] <= options_df["expirationdate"]]

    # Drop columns
    options_df.drop(columns=["optionkey", "symbol", "underlyingprice"], inplace=True)

    # Rename columns
    options_df.rename(columns={"datadate": "date",
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
    options_df = options_df[["date", "expiration date", "tag", "strike price", "ask price", "ask size", "bid price",
                             "bid size", "last price", "volume", "open interest"]]

    # Sort
    options_df.sort_values(by=["expiration date", "strike price", "tag"], ignore_index=True, inplace=True)

    # Check if data date is unique & get data date
    data_date_list = np.unique(options_df["date"])
    if len(data_date_list) == 0:
        output_msg.append(f"No {ticker} option data found in {ymd[2]}!")
        # Get data date using options from other tickers in that file
        all_dates = pd.to_datetime(day_options_df["datadate"]).dt.date
        data_date_list = np.unique(all_dates)

    # Sanity check
    if len(data_date_list) != 1:
        raise SystemExit(f"Data dates: {data_date_list}. Should be unique!")
    else:
        data_date = data_date_list[0]

    return {"df": options_df, "date": data_date, "messages": output_msg}


def remove_split_error_options_multi(input_dict):
    """
    For every "date" in "batch" options_df_list, we have:

    Options filter process
        1. Filter for options that overlap in expiry dates as those in the presplit
            - KEEP options with "new" expiry dates (assume no errors)
        2. For the remaining, merge current date strikes with adjusted presplit strikes (correctly adjusted options)
            - KEEP options with successful merges
        3. For the remaining, merge with min/max raw and adjusted strikes per exp date
            - Define the following:
                - active: |volume + ask size + bid size| > 0
                - inactive: |volume + ask size + bid size| == 0
                - natural: option strike is closer to adj min/max strike than raw min/max strike
                - unnatural: option strike is closer to raw min/max strike than adj min/max strike
            - KEEP active OR natural options

    Track exp dates of error options (inactive AND unnatural), check that it is monotonically decreasing

    Only when a date yields no error options, will we stop checking in future dates (straight pipe to output
    via `is_complete`).

    :param input_dict: {options_dict, presplit_date, presplit_df} (dict)
    :return: {clean_options_dict, messages} (dict)
    """
    # Unpack
    options_dict = input_dict["options dict"]
    presplit_date = input_dict["pre-split date"]
    presplit_df = input_dict["pre-split df"].copy()

    # Bookkeeping variables
    clean_options_dict = dict()
    is_complete = False
    output_msg = []

    # Sorted data dates (for sequential processing)
    sorted_data_dates = sorted(options_dict.keys())

    # Get max and min raw/adj strike prices per expiration date
    presplit_max_min_strikes_df = presplit_df.groupby(by=["expiration date"]).agg(
        raw_strike_min=pd.NamedAgg(column="raw strike price", aggfunc=np.min),
        raw_strike_max=pd.NamedAgg(column="raw strike price", aggfunc=np.max),
        adj_strike_min=pd.NamedAgg(column="adj strike price", aggfunc=np.min),
        adj_strike_max=pd.NamedAgg(column="adj strike price", aggfunc=np.max),
    )
    presplit_max_min_strikes_df.reset_index(inplace=True)

    # Exp dates on presplit date
    presplit_exp_dates = list(np.unique(presplit_df["expiration date"]))

    # Exp dates that still contain erroneous options, bookkeeping
    error_exp_dates = presplit_exp_dates

    # Sequential processing of date options
    for data_date in sorted_data_dates:
        date_options_df = options_dict[data_date]

        # See if all error options have been removed already
        if is_complete:
            clean_options_dict[data_date] = date_options_df
            continue

        # To store all options to be kept in date, bookkeeping
        clean_df = pd.DataFrame()
        # columns to be kept
        base_cols = date_options_df.columns

        # Options with new exp dates, add to kept options (REF #1)
        overlap_filter = date_options_df["expiration date"].isin(presplit_exp_dates)
        exp_no_overlap_options_df = date_options_df[~overlap_filter].copy()
        clean_df = clean_df.append(exp_no_overlap_options_df[base_cols])

        # Otherwise, keep going
        exp_overlap_options_df = date_options_df[overlap_filter].copy()

        # Sanity check. There should be some overlap in expiry dates (here, `is_complete` == False still)
        assert exp_overlap_options_df.shape[0] > 0, \
            f"Data date: {data_date}, Pre-split date: {presplit_date} \n" \
            f"No overlap in exp dates occurred before all error options were removed! \n" \
            f"Likely incorrect identification of error options."

        # Merge strike and adj strike
        adj_merge_df = exp_overlap_options_df.merge(
            presplit_df[["expiration date", "tag", "adj strike price"]], how="left",
            left_on=["expiration date", "tag", "strike price"],
            right_on=["expiration date", "tag", "adj strike price"],
            validate="1:1")

        # Successful match, add to kept options (REF #2)
        adj_merge_filter = adj_merge_df.isna().any(axis=1)
        complete_adj_merge_df = adj_merge_df[~adj_merge_filter].copy()
        clean_df = clean_df.append(complete_adj_merge_df[base_cols])

        # Otherwise, keep going
        incomplete_adj_merge_df = adj_merge_df[adj_merge_filter].copy()
        incomplete_adj_merge_df = incomplete_adj_merge_df[base_cols]

        # Add on min/max adj/raw strikes
        max_min_strike_merge = incomplete_adj_merge_df.merge(presplit_max_min_strikes_df, how="left",
                                                             on="expiration date",
                                                             validate="m:1")

        # Feature to identify if option is natural
        max_min_strike_merge["raw strikes dist"] = np.minimum(
            np.abs(max_min_strike_merge["strike price"] - max_min_strike_merge["raw_strike_min"]),
            np.abs(max_min_strike_merge["strike price"] - max_min_strike_merge["raw_strike_max"])
        )

        max_min_strike_merge["adj strikes dist"] = np.minimum(
            np.abs(max_min_strike_merge["strike price"] - max_min_strike_merge["adj_strike_min"]),
            np.abs(max_min_strike_merge["strike price"] - max_min_strike_merge["adj_strike_max"])
        )

        # Filter for "active" AND/OR "natural" options, add to kept options (REF #3)
        new_df = max_min_strike_merge[
            (max_min_strike_merge["raw strikes dist"] > max_min_strike_merge["adj strikes dist"]) |
            (max_min_strike_merge[["volume", "ask size", "bid size"]].sum(axis=1) > 0)]
        clean_df = clean_df.append(new_df[base_cols])

        # Filter for "inactive" AND "unnatural" options
        errors_df = max_min_strike_merge[
            (max_min_strike_merge["raw strikes dist"] <= max_min_strike_merge["adj strikes dist"]) &
            (max_min_strike_merge[["volume", "ask size", "bid size"]].sum(axis=1) == 0)]

        # Check how many error options remain in the data
        if errors_df.shape[0] == 0:
            # All error options have now been removed
            is_complete = True
            output_msg.append(f"Error options from pre-split {presplit_date} were completely removed on {data_date}!")
        # Keep track of how many error dates left (not sure if needed, #???)
        else:
            new_error_exp_dates = list(np.unique(errors_df["expiration date"]))

            # Check that new error exp dates are a subset of the old ones
            if not all([n in error_exp_dates for n in new_error_exp_dates]):
                output_msg.append(f"Error options with new exp dates appeared on {data_date}! (Should NOT happen)")

            # update outstanding error exp dates
            error_exp_dates = new_error_exp_dates

        # Sort cleaned options and add to dict
        clean_df.sort_values(by=["expiration date", "strike price"], inplace=True, ignore_index=True)
        clean_options_dict[data_date] = clean_df

    return {"dict": clean_options_dict, "messages": output_msg}
