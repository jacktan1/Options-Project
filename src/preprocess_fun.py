import numpy as np
import pandas as pd
from datetime import datetime
import model_fun
from pathlib import Path


def extract_dividends(my_history, stock_of_interest, api_key, num_days_year):
    """
    Removes priced in dividend from historical and current stock prices.
    For upcoming ex-dividend dates, Alphavantage query is made to see if
    ex-div date has been announced. Otherwise, a rough estimate is made.

    :param my_history: historical stock prices (DataFrame)
    :param stock_of_interest: ticker symbol (string)
    :param api_key: API key used to access the Alphavantage server (string)
    :param num_days_year: number of business days in a year (int)
    :return:
        - adjust_df - dividend contributions for each day in "my_history" (DataFrame)
        - div_info - record of all real and simulated dividend periods (DataFrame)
    """
    adjust_df = pd.DataFrame()
    div_info = pd.DataFrame()
    data_url = "https://www.alphavantage.co/query?function=OVERVIEW&symbol="
    default_path = "data/dividends/"
    company_info = pd.read_json(data_url + stock_of_interest + "&apikey=" + api_key,
                                typ="series")
    alpha_next_div_date = company_info["ExDividendDate"]
    # Check next dividend date, fill with nonsense otherwise
    if alpha_next_div_date != "None":
        alpha_next_div_date = datetime.strptime(alpha_next_div_date, '%Y-%m-%d')
    else:
        alpha_next_div_date = my_history['date'].iloc[0]
    # Current annualized dividend payout
    annual_div_amount = float(company_info["ForwardAnnualDividendRate"])
    if annual_div_amount == "None":
        annual_div_amount = 0

    # Creating DataFrame of all past dividends
    for n in range(my_history.shape[0]):
        if my_history['dividend amount'][n] != 0:
            temp_df = my_history.iloc[n, :].copy(deep=True)
            div_info = div_info.append(temp_df, ignore_index=True)

    # Reshape matrix if stock does pay dividends
    try:
        div_info = div_info[['date', 'dividend amount']]
        div_info['div_start'] = div_info['date']
        div_info = div_info.drop(['date'], axis=1)
        div_info = div_info[['div_start', 'dividend amount']]
    except:
        if (alpha_next_div_date.date() < pd.to_datetime("today").date()) & (annual_div_amount > 0):
            raise Exception("No dividend payout but yet Alphavantage indicates Ex-Div date has passed?!")

    # Calculating the next upcoming dividend date
    # Case 1: next dividend date is announced and hasn't passed yet
    if (alpha_next_div_date.date() > my_history['date'].iloc[-1].date()) & (annual_div_amount > 0):
        div_multiplier = model_fun.div_freq(ex_div_1=div_info['div_start'].iloc[-1],
                                            ex_div_2=alpha_next_div_date,
                                            num_days_year=num_days_year)

        div_info = div_info.append(
            pd.DataFrame([[alpha_next_div_date, annual_div_amount * div_multiplier]],
                         columns=div_info.columns.tolist()),
            ignore_index=True)
    # Case 2: estimate the next dividend date based off history
    elif div_info.shape[0] > 1:
        assumed_end_date = np.busday_offset(dates=div_info['div_start'].iloc[-1].date(),
                                            offsets=np.busday_count(
                                                begindates=div_info['div_start'].iloc[-2].date(),
                                                enddates=div_info['div_start'].iloc[-1].date()))

        div_info = div_info.append(pd.DataFrame([[assumed_end_date, div_info['dividend amount'].iloc[-1]]],
                                                columns=div_info.columns.tolist()),
                                   ignore_index=True)
    # Case 3: when there isn't anything to base estimate on
    elif div_info.shape[0] == 1:
        print("Only one ex-dividend date recorded and next date not in sight. Effect of dividend not calculated!")
        # Reset DataFrame to be as if no dividend recorded
        div_info = pd.DataFrame()
    # Case 4: company has never paid dividends
    else:
        print("Ticker " + stock_of_interest + " does not pay dividends and it never has!")

    # Calculating start date of first dividend recorded
    if div_info.shape[0] > 1:
        assumed_start_date = np.busday_offset(dates=div_info['div_start'].iloc[0].date(),
                                              offsets=-np.busday_count(
                                                  begindates=div_info['div_start'].iloc[0].date(),
                                                  enddates=div_info['div_start'].iloc[1].date()))
        div_info = pd.DataFrame([[assumed_start_date, 0]],
                                columns=div_info.columns.tolist()).append(div_info, ignore_index=True)

    # Rudimentary method of finding dividend end dates. Works in most cases unless there
    # is a gap/break between dividends. For example, dividend paid for Q1 and Q3 but not Q2.
    # "div_start" are Ex-dividend dates
    temp_end_dates = np.empty(shape=div_info.shape[0], dtype=object)
    for n in range(div_info.shape[0] - 1):
        temp_end_dates[n] = np.busday_offset(dates=div_info['div_start'].iloc[n + 1].date(),
                                             offsets=-1)

    #  Convert np.datetime64 to datetime & rearrange column order (if applicable)
    try:
        div_info['div_end'] = pd.to_datetime(temp_end_dates)
        div_info = div_info[['div_start', 'div_end', 'dividend amount']]
    except:
        pass

    # Stocks with dividend history
    if div_info.shape[0] > 1:
        # Readjusting the dividend amount since it is shifted down 1 row by default
        div_info['dividend amount'] = div_info['dividend amount'].iloc[1:].reset_index(drop=True)
        div_info = div_info.iloc[:-1, ]
    # When no dividend has been recorded (empty div_info)
    else:
        div_info = pd.DataFrame(data=[[my_history['date'].iloc[0], my_history['date'].iloc[-1], 0]],
                                columns=['div_start', 'div_end', 'dividend amount'])

    # Initializes the adjustment matrix for days before dividends existed
    if div_info['div_start'].iloc[0] > my_history['date'].iloc[0]:
        start_index = my_history.loc[my_history['date'] == div_info['div_start'][0]].index.values.astype(int)[0]
        adjust_df = adjust_df.append(pd.DataFrame(np.zeros(start_index),
                                                  columns=['amount']))

    # Appends adjustment matrix for each dividend period by their respective dividend contributions
    for n in range(div_info.shape[0]):
        # Case 1: first dividend start date is before first day on record
        if div_info['div_start'].iloc[n] < my_history['date'].iloc[0]:
            start_date = my_history['date'].iloc[0]
            end_date = div_info['div_end'].iloc[n]
            ratio = 0
            position = "head"
        # Case 2: last dividend end date is on/past today
        # NOTE that because we use the CURRENT DATE we need the MOST UP TO DATE data history file as well.
        # Thus this function should not run by itself!
        elif div_info['div_end'].iloc[n].date() > pd.to_datetime("today").date():
            start_date = div_info['div_start'].iloc[n]
            end_date = datetime.combine(pd.to_datetime("today").date(), datetime.min.time())
            ratio = 0
            position = "tail"
        # Case 3: most common, everything in the middle
        else:
            start_date = div_info['div_start'].iloc[n]
            end_date = div_info['div_end'].iloc[n]
            ratio = 1
            position = "middle"

        # Grabbing indeces of start and end dates to plug into model
        start_index = my_history.loc[my_history['date'] == start_date].index.values.astype(int)[0]

        try:
            end_index = my_history.loc[my_history['date'] == end_date].index.values.astype(int)[0]
        except:
            if end_date.date() == pd.to_datetime("today").date():
                # Today should be 1 day after the most recent recorded history
                end_index = my_history.shape[0]
            else:
                print("The market was not open on " + str(end_date.date()) + "!  Using business day prior to this!")
                temp_date = np.busday_offset(dates=end_date.date(), offsets=-1)
                end_index = my_history.loc[my_history['date'] == temp_date].index.values.astype(int)[0]

        # Find the ratio of the entire dividend period that is covered
        if ratio == 0:
            # Very important to add 1!
            ratio = (end_index - start_index + 1) / (np.busday_count(div_info['div_start'][n].date(),
                                                                     div_info['div_end'][n].date()) + 1)
            if ratio >= 1:
                raise Exception("More days have passed than there exists between the two start and end dates!")

        div_amount = div_info['dividend amount'].iloc[n]

        temp_df = model_fun.dividend_pricing(num_days=(end_index - start_index + 1),
                                             amount=div_amount,
                                             completeness=ratio,
                                             position=position)
        temp_df = pd.DataFrame(temp_df, columns=['amount'])
        adjust_df = adjust_df.append(temp_df, sort=False).reset_index(drop=True)

    # When the last "div_end" comes before the last day on record (aka company stopped paying dividends a year ago)
    if adjust_df.shape[0] <= my_history.shape[0]:
        # adding the extra "1" for "today"
        temp_df = pd.DataFrame(data=np.zeros(my_history.shape[0] - adjust_df.shape[0] + 1),
                               columns=['amount'])
        adjust_df = adjust_df.append(temp_df, sort=False).reset_index(drop=True)

    # Filling the "date" column
    adjust_df['date'] = my_history['date'].append(
        pd.Series(datetime.combine(pd.to_datetime("today").date(), datetime.min.time())), ignore_index=True)

    # Saving DataFrame into csv
    # Create data directory if it doesn't exist
    Path(default_path).mkdir(exist_ok=True)

    adjust_df.to_csv(path_or_buf=(default_path + stock_of_interest + '_ts.csv'),
                     index=False)

    div_info.to_csv(path_or_buf=(default_path + stock_of_interest + '.csv'),
                    index=False)
    return
