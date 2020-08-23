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
    alpha_next_div_date = datetime.strptime(company_info["ExDividendDate"], '%Y-%m-%d')
    annual_div_amount = float(company_info["ForwardAnnualDividendRate"])
    if annual_div_amount == "None":
        annual_div_amount = 0

    for n in range(my_history.shape[0]):
        if my_history['dividend amount'][n] != 0:
            temp_df = my_history.iloc[n, :].copy(deep=True)
            div_info = div_info.append(temp_df, ignore_index=True)

    # See if ticker pays dividends & reshape matrix if it does
    try:
        div_info = div_info[['date', 'dividend amount']]
        div_info['div_start'] = div_info['date']
        div_info['div_end'] = pd.Series()
        div_info = div_info.drop(['date'], axis=1)
        div_info = div_info[['div_start', 'div_end', 'dividend amount']]
    except:
        print("Ticker " + stock_of_interest + " does not pay dividends and it never has!")
        if (alpha_next_div_date.date() < pd.to_datetime("today").date()) & (annual_div_amount > 0):
            raise Exception("No dividend history but yet Alphavantage indicates Ex-Div date has passed?!")

    if div_info.shape[0] == 1:
        if (alpha_next_div_date.date() >= pd.to_datetime("today").date()) & (annual_div_amount > 0):
            div_multiplier = model_fun.div_freq(exdiv_date_1=div_info['date'].iloc[-1],
                                                exdiv_date_2=alpha_next_div_date,
                                                num_days_year=num_days_year)
            # Forward
            div_info = div_info.append(
                pd.DataFrame([[alpha_next_div_date, np.nan, annual_div_amount * div_multiplier]],
                             columns=div_info.columns.tolist()),
                ignore_index=True)

            assumed_start_date = np.busday_offset(dates=div_info['div_start'].iloc[0].date(),
                                                  offsets=-np.busday_count(
                                                      begindates=div_info['div_start'].iloc[0].date(),
                                                      enddates=div_info['div_start'].iloc[1].date()))
            # Backward
            div_info = pd.DataFrame([[assumed_start_date, np.nan, 0]],
                                    columns=div_info.columns.tolist()).append(div_info, ignore_index=True)
        else:
            print("Only one ex-dividend date recorded and next date not in sight. Effect of dividend not calculated!")
            # Reset DataFrame to be as if no dividend recorded
            div_info = pd.DataFrame()
    elif div_info.shape[0] > 1:
        assumed_start_date = np.busday_offset(dates=div_info['div_start'].iloc[0].date(),
                                              offsets=-np.busday_count(
                                                  begindates=div_info['div_start'].iloc[0].date(),
                                                  enddates=div_info['div_start'].iloc[1].date()))
        # Backward
        div_info = pd.DataFrame([[assumed_start_date, np.nan, 0]],
                                columns=div_info.columns.tolist()).append(div_info, ignore_index=True)

        # Forward
        # If listed ex-dividend date has already passed
        if alpha_next_div_date.date() < pd.to_datetime("today").date():
            assumed_end_date = np.busday_offset(dates=div_info['div_start'].iloc[-1].date(),
                                                offsets=np.busday_count(
                                                    begindates=div_info['div_start'].iloc[-2].date(),
                                                    enddates=div_info['div_start'].iloc[-1].date()))

            div_info = div_info.append(pd.DataFrame([[assumed_end_date, np.nan, div_info['dividend amount'].iloc[-1]]],
                                                    columns=div_info.columns.tolist()),
                                       ignore_index=True)
        # If dividend date hasn't passed yet
        else:
            div_multiplier = model_fun.div_freq(ex_div_1=div_info['div_start'].iloc[-1],
                                                ex_div_2=alpha_next_div_date,
                                                num_days_year=num_days_year)

            div_info = div_info.append(
                pd.DataFrame([[alpha_next_div_date, np.nan, annual_div_amount * div_multiplier]],
                             columns=div_info.columns.tolist()),
                ignore_index=True)

    # Rudimentary method of finding dividend end dates. Works in most cases unless there
    # is a gap/break between dividends. For example, dividend paid for Q1 and Q3 but not Q2.
    # "div_start" are Ex-dividend dates
    # Gives dumb warning
    for n in range(div_info.shape[0] - 1):
        div_info['div_end'].iloc[n] = np.busday_offset(dates=div_info['div_start'].iloc[n + 1].date(),
                                                       offsets=-1)

    # Convert np.datetime64 to datetime
    div_info['div_end'] = pd.to_datetime(div_info['div_end'])

    if div_info.shape[0] > 1:
        # Readjusting the dividend amount since it is shifted down 1 row by default
        div_info['dividend amount'] = div_info['dividend amount'].iloc[1:].reset_index(drop=True)
        div_info = div_info.iloc[:-1, ]
    else:
        # Cases when no dividend has been recorded
        div_info = pd.DataFrame(data=[[my_history['date'].iloc[0], my_history['date'].iloc[-1], 0]],
                                columns=['div_start', 'div_end', 'dividend amount'])

    # Initializes the adjustment matrix
    if div_info['div_start'].iloc[0] > my_history['date'].iloc[0]:
        start_index = my_history.loc[my_history['date'] == div_info['div_start'][0]].index.values.astype(int)[0]
        adjust_df = adjust_df.append(pd.DataFrame(my_history['date'].iloc[:start_index],
                                                  columns=['date']))
        adjust_df['amount'] = 0

    # Appends adjustment matrix for each dividend period by their respective dividend contributions
    for n in range(div_info.shape[0]):
        # When first dividend start date is before first day of recorded history
        if div_info['div_start'].iloc[n] < my_history['date'].iloc[0]:
            start_index = 0
            try:
                end_index = my_history.loc[my_history['date'] == div_info['div_end'].iloc[n]] \
                    .index.values.astype(int)[0]
            except:
                print("The market was not open on the business day before ex Dividend date! Using business day prior to"
                      " this")
                temp_date = np.busday_offset(dates=div_info['div_end'].iloc[n].date(),
                                             offsets=-1)
                end_index = my_history.loc[my_history['date'] == temp_date] \
                    .index.values.astype(int)[0]

            # Very important to add 1!
            ratio = (end_index - start_index + 1) / (np.busday_count(begindates=div_info['div_start'][n].date(),
                                                                     enddates=div_info['div_end'][n].date()) + 1)
            div_amount = div_info['dividend amount'].iloc[n]
        # When last dividend end date is past last day of recorded history
        elif div_info['div_end'].iloc[n] > my_history['date'].iloc[-1]:
            start_index = my_history.loc[my_history['date'] == div_info['div_start'].iloc[n]] \
                .index.values.astype(int)[0]
            end_index = my_history.shape[0] - 1
            # Very important to add 1!
            ratio = (end_index - start_index + 1) / (np.busday_count(begindates=div_info['div_start'][n].date(),
                                                                     enddates=div_info['div_end'][n].date()) + 1)
            div_amount = div_info['dividend amount'].iloc[n]
        else:
            start_index = my_history.loc[my_history['date'] == div_info['div_start'].iloc[n]] \
                .index.values.astype(int)[0]
            ratio = 1
            div_amount = div_info['dividend amount'].iloc[n]
            try:
                end_index = my_history.loc[my_history['date'] == div_info['div_end'].iloc[n]] \
                    .index.values.astype(int)[0]
            except:
                print("The market was not open on the business day before ex Dividend date! Using business day prior to"
                      " this")
                temp_date = np.busday_offset(dates=div_info['div_end'].iloc[n].date(),
                                             offsets=-1)
                end_index = my_history.loc[my_history['date'] == temp_date] \
                    .index.values.astype(int)[0]

        temp_df = model_fun.dividend_pricing(num_days=(end_index - start_index + 1),
                                             amount=div_amount,
                                             completeness=ratio)
        temp_df = pd.DataFrame(temp_df, columns=['amount'])
        temp_df['date'] = 0
        adjust_df = adjust_df.append(temp_df, sort=False).reset_index(drop=True)

    # When the last "div_end" comes before the last day in price history
    if adjust_df.shape[0] < my_history.shape[0]:
        temp_df = pd.DataFrame(data=np.zeros((my_history.shape[0] - adjust_df.shape[0], 2)),
                               columns=['date', 'amount'])
        adjust_df = adjust_df.append(temp_df, sort=False).reset_index(drop=True)

    # Filling the "date" column
    adjust_df['date'] = my_history['date']

    # Saving DataFrame into csv
    # Create data directory if it doesn't exist
    Path(default_path).mkdir(exist_ok=True)

    adjust_df.to_csv(path_or_buf=(default_path + stock_of_interest + '_ts.csv'),
                     index=False)

    div_info.to_csv(path_or_buf=(default_path + stock_of_interest + '.csv'),
                    index=False)

    return
