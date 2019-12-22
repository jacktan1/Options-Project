import pandas as pd
import numpy as np


### --- Start of Functions --- ###

# This function takes the current naked stock price, the expiry dates of all options and calculates the scaled current
# price at each of the expiry dates. This is a special version of the original function to be used for backtesting


def adjust_prices_bt(expiry_dates, naked_current_price, price_history, last_div_index):
    # Getting the date one day before ex-dividend date

    last_div_date = pd.to_datetime(
        price_history[last_div_index, 0], unit='D').asm8.astype('<M8[D]')
    exp_dates_adjusted_current_price = {}
    next_ex_date = 0
    # Searching for the next dividend date, have to add 2 since our index is one day before ex
    for n in range(last_div_index + 2, len(price_history)):
        if price_history[n, 2] != 0:
            next_ex_date = pd.to_datetime(
                price_history[n, 0], unit='D').asm8.astype('<M8[D]')
            break
        if n == len(price_history) - 1:
            assert n != 0, 'Could not find the next dividend date! Probably should not testing on \
            history this close to current date.'
    # Gotta subtract one since the max is one day before the next ex-dividend date
    num_days_div = np.busday_count(last_div_date, next_ex_date) - 1
    assert num_days_div > 0, "That's fucked up..."
    # Assume we don't know the next div payout, so take it to be same as last
    # Add 1 since our index is one day before the ex-div (which contains the amount)
    div_price = price_history[last_div_index + 1, 2]
    assert div_price > 0
    for n in range(len(expiry_dates)):
        expiry_date = expiry_dates[n]
        num_days = np.busday_count(last_div_date, expiry_date) % num_days_div
        assert num_days > 0, "That's fucked up..."
        if num_days == 0:
            # If expiry date is one day before next ex-dividend date, then price has all dividend priced in
            scaled_current_price = naked_current_price + div_price
        else:
            scaled_current_price = (num_days / num_days_div) * div_price + naked_current_price
        exp_dates_adjusted_current_price.update(
            {expiry_date: scaled_current_price})
    return exp_dates_adjusted_current_price
