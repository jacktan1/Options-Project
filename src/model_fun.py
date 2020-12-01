import numpy as np


def dividend_pricing(num_days, amount, completeness, position):
    """
    Function is used to calculate "priced in" dividends in
    daily historical prices. As no strict model is established
    for dividend pricing, this is my own interpretation on how the
    dividend becomes priced in over the course of a quarter/year

    :param num_days: the number of days in this dividend period (int)
    :param amount: amount paid for this dividend period (float)
    :param completeness: what ratio of the dividend amount is covered (float)
    :param position: where does this dividend lie (str)
    :return: numpy series containing all dividend contributions for time period
    """
    max_div = amount * completeness

    if max_div == 0:
        dividend_df = np.zeros(num_days)
    else:
        dividend_df = np.arange(start=float(max_div / num_days),
                                stop=float(max_div + (max_div / num_days) * 0.1),
                                step=float(max_div / num_days))

    if position == "head":
        dividend_df = amount - dividend_df + float(max_div / num_days)
        dividend_df = dividend_df[::-1]

    return dividend_df


def div_freq(ex_div_1, ex_div_2, num_days_year):
    """
    Function is used to detect the frequency of dividend payouts
    based off the time gap between two ex-dividend dates. As the
    number of days between each ex-dividend date varies slightly,
    upper and lower boundary values are used.

    :param ex_div_1: start date (datetime.datetime)
    :param ex_div_2: end date (datetime.datetime)
    :param num_days_year:number of business days in a year (int)
    :return: the multiplier value to be used against forward annual dividend rate (float)
    """
    time_gap = np.busday_count(begindates=ex_div_1.date(),
                               enddates=ex_div_2.date())
    # Quarterly dividends
    if (time_gap > 55) & (time_gap < 75):
        div_multiplier = 0.25
    # Annual dividends
    elif (time_gap > 240) & (time_gap < 260):
        div_multiplier = 1
    else:
        div_multiplier = float(time_gap / num_days_year)
    return div_multiplier
