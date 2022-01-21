from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import warnings


def calculate_dividends(ticker: str, api_key: str, hist_closing_df: pd.DataFrame,
                        num_days_future: int):
    """
    Creates 2 DataFrames
        1. Aggregates past dividend events. Finds the start date and amount of each dividend period.
           Infers future dividend start dates up to a certain user defined threshold.
        2. Infers a time series (freq=daily) from the dividend events. Method of inference used
           can be modified by user (linear method used here).

    Built in logic also handles edge cases such as:
        - Tickers who have never paid dividends before
        - Tickers who paid dividends in the past, but no longer do so

    :param ticker: ticker of interest (str)
    :param api_key: Alpha Vantage API token (str)
    :param hist_closing_df: Split adjusted historical ex-dates and amounts (pd.DataFrame)
    :param num_days_future: Number of days to infer past the last date of `hist_closing_df` (int)
    :return: {iv_events_df, div_ts_df} (dict)
    """

    my_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    company_info = pd.read_json(my_url, typ="series")
    next_div_date = company_info["ExDividendDate"]

    # Check next dividend date, fill with nonsense if invalid
    if next_div_date != "None":
        next_div_date = datetime.strptime(next_div_date, '%Y-%m-%d').date()
    else:
        next_div_date = datetime(1970, 1, 1).date()

    # Current annualized dividend ($) per share, not always accurate
    annual_div = company_info["DividendPerShare"]
    if annual_div == "None":
        annual_div = 0
    else:
        annual_div = float(annual_div)

    # Historical dividend events
    div_events_df = hist_closing_df[hist_closing_df["dividend"] != 0][["date", "dividend"]]
    div_events_df.reset_index(drop=True, inplace=True)
    div_events_df.rename(columns={"date": "div start"}, inplace=True)

    # Tickers without dividend history
    if div_events_df.shape[0] == 0:
        # Sanity check
        if (annual_div > 0) & (next_div_date < datetime.now().date()):
            raise Exception("Conflict between dividend history and next dividend date!")

        if next_div_date > np.max(hist_closing_df["date"]):
            print(f"'{ticker}' has never paid dividends before! It's first ex-date will be on: {next_div_date}")
        else:
            print(f"'{ticker}' does not pay dividends and it never has!")

        # Assume that ticker will not pay dividends in the future
        div_events_df = div_events_df.append(
            pd.DataFrame([[np.min(hist_closing_df["date"]), 0],
                          [(datetime.now().date() + timedelta(days=num_days_future)), np.nan]],
                         columns=["div start", "dividend"]))

    # Tickers with dividend history
    else:
        # Shift up 1 period (Alpha Vantage posts dividends on ex-date). A bit hacky
        div_events_df["div start"].index = div_events_df["div start"].index + 1
        div_events_df = pd.concat([div_events_df["div start"], div_events_df["dividend"]], axis=1)

        # Calculate upcoming dividend dates
        next_divs_df = get_next_divs(div_events_df, next_div_date, annual_div, hist_closing_df, num_days_future)

        # Combine past ex-dates with future ex-dates
        div_events_df = div_events_df.iloc[:-1, ].append(next_divs_df, ignore_index=True)

        # Calculate div start date
        first_div_start = get_first_div_start(div_events_df)

        div_events_df.loc[0, "div start"] = first_div_start

    # Create dividend time series from dividend events
    div_ts_df = create_ts(div_events_df, hist_closing_df)

    return {"events": div_events_df, "ts": div_ts_df}


def get_next_divs(div_events_df, next_div_date, annual_div, hist_closing_df, num_days_future):
    """
    Get dividend start dates (ex-dates) up to a user defined end date. Upcoming ex-date will be taken from
    Alpha Vantage if available, otherwise inferred. Additional ex-dates are always inferred.
    """

    # Start of previous ex-date
    start_date = div_events_df["div start"].iloc[-1]
    # Date to infer up to
    end_date = np.max(hist_closing_df["date"]) + timedelta(days=num_days_future)

    # Sanity check
    assert (div_events_df.shape[0] >= 2), "Should be at least 2 rows due to shifts!"

    # Case: ticker has paid dividends before, but it is no longer paying dividends
    if next_div_date == datetime(1970, 1, 1).date():
        print(f"Ticker no longer pays dividends")

        next_divs_df = pd.DataFrame([[start_date, 0], [end_date, np.nan]],
                                    columns=["div start", "dividend"])

    else:
        # Case: next dividend date is announced and hasn't passed yet
        if next_div_date > np.max(hist_closing_df["date"]):
            div_freq_year = infer_div_freq(ex_div_1=np.max(div_events_df["div start"]),
                                           ex_div_2=next_div_date)

            # Dividends hardly ever decrease, take max of the two
            if (annual_div / div_freq_year) < div_events_df["dividend"].iloc[-2]:
                warnings.warn(
                    f"Dividend decreased from {div_events_df['dividend'].iloc[-2]} to {(annual_div / div_freq_year)}!")
                print(f"Using higher value ({div_events_df['dividend'].iloc[-2]}) instead!")
                div_amount = div_events_df["dividend"].iloc[-2]
            else:
                div_amount = annual_div / div_freq_year

            # Length of dividend period
            div_offset = np.busday_count(begindates=start_date, enddates=next_div_date)

        # Case: infer next dividend date based off the last two
        else:
            div_amount = div_events_df['dividend'].iloc[-2]

            # Subcase: if only one previous dividend payout, there is nothing to infer from.
            # Can be a bit hacky when calculating first `div start`
            if div_events_df.shape[0] == 2:
                div_offset = np.busday_count(begindates=start_date, enddates=end_date)

            # Subcase: There are at least two ex-dates recorded, something to infer from
            else:
                div_offset = np.busday_count(begindates=div_events_df['div start'].iloc[-2], enddates=start_date)

        temp_div_date = start_date
        temp_div_date_list = [start_date]
        temp_div_amount_list = []

        # Find future dividend dates with offset and values inferred from above
        while temp_div_date < end_date:
            temp_div_date = np.busday_offset(dates=temp_div_date,
                                             offsets=div_offset,
                                             roll="forward")

            temp_div_date_list.append(temp_div_date)
            temp_div_amount_list.append(div_amount)

        # Add a np.nan to match length
        temp_div_amount_list.append(np.nan)

        next_divs_df = pd.DataFrame({"div start": temp_div_date_list,
                                     "dividend": temp_div_amount_list})

        # Convert div_start from datetime64 to datetime.date
        next_divs_df["div start"] = pd.to_datetime(next_divs_df["div start"]).dt.date

    return next_divs_df


def infer_div_freq(ex_div_1, ex_div_2):
    """
    Infer frequency of dividends based on offset between two ex-dividend dates.
    Since offsets vary slightly (due to holidays etc.), ranges are used.
    """
    # Doesn't take holidays into account
    approx_day_diff = np.busday_count(begindates=ex_div_1,
                                      enddates=ex_div_2)
    # Quarterly dividends
    if (approx_day_diff > 55) & (approx_day_diff < 75):
        div_freq = 4
    # Annual dividends
    elif (approx_day_diff > 240) & (approx_day_diff < 260):
        div_freq = 1
    else:
        raise Exception("Dividend frequency not quarterly or annually!")

    return div_freq


def get_first_div_start(div_events_df):
    """
    Infer start of the first dividend period from 2nd and 3rd start dates
    """
    my_offset = np.busday_count(begindates=div_events_df["div start"].loc[1],
                                enddates=div_events_df["div start"].loc[2])

    start_date = np.busday_offset(div_events_df["div start"].loc[1], offsets=-my_offset)

    # datetime64 to datetime.date
    start_date = pd.to_datetime(start_date).date()

    return start_date


def create_ts(div_events_df, hist_closing_df):
    """
    Get start and end dates of each dividend period, pass into function to create time series.
    Range: [min(hist_closing_df["date"]), np.max(div_events_df["div start"])]
    """
    ts_df = pd.DataFrame()

    for n in range(div_events_df.shape[0] - 1):
        # Start and end dates for this dividend period
        temp_start = div_events_df.loc[n, "div start"]
        temp_end = div_events_df.loc[n + 1, "div start"]
        temp_div = div_events_df.loc[n, "dividend"]

        temp_ts_df = ts_model(hist_closing_df=hist_closing_df,
                              start_date=temp_start,
                              end_date=temp_end,
                              div_amount=temp_div)

        ts_df = ts_df.append(temp_ts_df, ignore_index=True)

    # Fill in dividend = 0 for all historical dates before first dividend period
    hist_no_div_df = hist_closing_df[hist_closing_df["date"] < div_events_df.loc[0, "div start"]][["date"]].copy()

    hist_no_div_df["dividend"] = 0

    ts_df = ts_df.append(hist_no_div_df)

    ts_df.sort_values(by="date", inplace=True)
    ts_df.reset_index(drop=True, inplace=True)

    return ts_df


def ts_model(hist_closing_df, start_date, end_date, div_amount):
    """
    Create dividend time series (freq = daily) given two neighbouring ex-dates.
    Takes into account situations where ex-date start or end outside `hist_closing_df["date"]` range.
    """
    hist_start = np.min(hist_closing_df["date"])
    hist_end = np.max(hist_closing_df["date"])

    dates_df = hist_closing_df[(hist_closing_df["date"] >= start_date) &
                               (hist_closing_df["date"] < end_date)][["date"]].copy()

    # Case: dividend start date is earlier than first recorded closing price date
    if start_date < hist_start:
        approx_num_days_total = np.busday_count(begindates=start_date,
                                                enddates=end_date)

        # Take dividends from the last `dates_df.shape[0]` dates
        my_div = (((np.arange(approx_num_days_total) + 1) / approx_num_days_total) * div_amount)[-dates_df.shape[0]:]

        # Dates are simply those with closing prices
        my_dates = list(dates_df["date"])

    # Case: dividend end date is later than the latest recorded closing price date
    elif end_date > hist_end:
        # If dividend period has overlap between past and future
        if start_date < hist_end:
            # Remove first date because it overlaps with hist_end in `dates_df`
            # Remove last date because it is ex-date (start of next dividend)
            dates_future = pd.date_range(start=hist_end, end=end_date,
                                         freq="B")[1:-1]

        # If dividend period is purely in the future
        else:
            # Only remove last date (see reason above)
            dates_future = pd.date_range(start=start_date, end=end_date,
                                         freq="B")[:-1]

        approx_num_days_total = dates_df.shape[0] + len(dates_future)

        my_div = ((np.arange(approx_num_days_total) + 1) / approx_num_days_total) * div_amount

        my_dates = list(dates_df["date"])
        my_dates.extend(dates_future)

    # Case:dDividend start and end dates are within range of `hist_closing_df`
    else:
        my_div = ((np.arange(dates_df.shape[0]) + 1) / dates_df.shape[0]) * div_amount

        my_dates = list(dates_df["date"])

    my_ts = pd.DataFrame({"date": my_dates, "dividend": my_div})
    my_ts["date"] = pd.to_datetime(my_ts["date"]).dt.date

    return my_ts
