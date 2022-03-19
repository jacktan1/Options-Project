import numpy as np
import pandas as pd
import time


def calc_vix(input_dict, rates_dict, num_days_year):
    # Unpack
    year_df = input_dict["df"]
    year = input_dict["year"]

    # Housekeeping
    vix_list = []
    vix_full_list = []
    start_time = time.time()

    for date in list(set(year_df["date"])):
        # date
        df1 = year_df[year_df["date"] == date]
        date_close = np.unique(df1["date close"])

        vix_date = []

        for exp_date in list(set(df1["expiration date"])):
            # date + exp date
            if date == exp_date:
                continue

            df2 = df1[df1["expiration date"] == exp_date]

            years_to_exp = np.busday_count(date, exp_date) / num_days_year

            exp_interest_rate = get_interest_rate(rates_dict=rates_dict,
                                                  date=date,
                                                  years_to_exp=years_to_exp)

            for tag in ["call", "put"]:
                # date + exp date + tag
                df3 = df2[df2["tag"] == tag].copy()

                df3["moneyness"] = df3["date close"] - df3["strike price"]

                if tag == "put":
                    df3["moneyness"] = -df3["moneyness"]

                # Get min ITM strike
                min_itm = np.min(df3[df3["moneyness"] >= 0]["moneyness"])

                df4 = df3[df3["moneyness"] <= min_itm].copy()

                # Set upper bound of ITM strike price to ATM for calculation
                df4.loc[(df4["moneyness"] == min_itm), "strike price"] = date_close

                df4["delta strike"] = df4["strike price"] - df4["strike price"].shift(periods=1)

                df4["midpoint ask"] = (df4["ask price"] + df4["ask price"].shift(periods=1)) / 2

                df4["vix"] = ((df4["delta strike"] * df4["midpoint ask"] * np.exp(exp_interest_rate * years_to_exp)) /
                              date_close ** 2)

                vix_sum = np.sum(df4["vix"].dropna()) / years_to_exp

                vix_date.append([date, exp_date, tag, years_to_exp, vix_sum])

        # Accumulated for all exp dates on date
        vix_date_df = pd.DataFrame(vix_date, columns=["date", "expiration date", "tag", "years to exp", "vix"])

        vix_date_bins_df = bin_vix(vix_date_df=vix_date_df, date=date)

        vix_list.append(vix_date_bins_df)

        vix_full_list.append(vix_date_df)

    vix_df = pd.concat(vix_list)

    vix_df.sort_values(by=["date", "bin", "tag"], inplace=True, ignore_index=True)

    vix_full_df = pd.concat(vix_full_list)

    vix_full_df.sort_values(by=["date", "expiration date", "tag"], inplace=True, ignore_index=True)

    print(f"VIX - {round(time.time() - start_time, 2)} seconds")

    return vix_df


def bin_vix(vix_date_df, date):
    """
    Bin VIX values of different expiration dates into standardized milestones.
    Linear interpolation using two points closest to point of interest (x).

    weighted_vix = vix_0*((t1-x)/(t1-t0)) + rix_1*((x-t0)/(t1-t0))

    milestones used:
    - 1 month (1/12 year)
    - 2 months (1/6)
    - 3 months (1/4)
    - 6 months (1/2)
    - 1 year (1)
    """

    output_list = []

    for n in [1 / 12, 1 / 6, 1 / 4, 1 / 2, 1]:
        t0 = np.max(vix_date_df[vix_date_df["years to exp"] <= n]["years to exp"])
        t1 = np.min(vix_date_df[vix_date_df["years to exp"] > n]["years to exp"])

        if any(pd.isna([t0, t1])):
            print(f"{n} skipped on date {date}")
            output_list.extend([[date, n, "call", np.nan],
                                [date, n, "put", np.nan]])
            continue

        for tag in ["call", "put"]:
            vix_w = 0

            for t in [t0, t1]:
                vix_t = float(vix_date_df[(vix_date_df["years to exp"] == t) &
                                          (vix_date_df["tag"] == tag)]["vix"].values)

                if t == t0:
                    vix_w = vix_w + vix_t * ((t1 - n) / (t1 - t0))
                elif t == t1:
                    vix_w = vix_w + vix_t * ((n - t0) / (t1 - t0))

            output_list.append([date, n, tag, vix_w])

    output_df = pd.DataFrame(output_list, columns=["date", "bin", "tag", "vix"])

    return output_df


def get_interest_rate(rates_dict, date, years_to_exp):
    """
    If the interest rate on dates t1 and t2 are r1 and r2, respectively.
    The linear interpolation of interest rate on date x given that t1 <= x <= t2 is:

    interest rate = r0*((t1-x)/(t1-t0)) + r1*((x-t0)/(t1-t0))
    """
    rate_keys = list(rates_dict.keys())
    # For exp dates that expire within 1 month (a.k.a. no lower bound)
    rate_keys.append(0)

    t0 = np.max([n for n in rate_keys if n <= years_to_exp])
    t1 = np.min([n for n in rate_keys if n > years_to_exp])

    interest_rate = 0

    for t in [t0, t1]:
        if t != 0:
            df = rates_dict[t]
            dates = list(df["date"])

            if date not in dates:
                # Get dates before and after "date" to perform interpolation
                date_0 = date
                date_1 = date

                while date_0 not in dates:
                    date_0 = pd.to_datetime(np.busday_offset(date_0, -1)).date()

                while date_1 not in dates:
                    date_1 = pd.to_datetime(np.busday_offset(date_1, 1)).date()

                rate_t = (float(df[df["date"] == date_0]["continuous rate"]) +
                          float(df[df["date"] == date_1]["continuous rate"])) / 2
            else:
                rate_t = float(df[df["date"] == date]["continuous rate"])
        else:
            rate_t = 0

        if t == t0:
            interest_rate = interest_rate + rate_t * ((t1 - years_to_exp) / (t1 - t0))
        elif t == t1:
            interest_rate = interest_rate + rate_t * ((years_to_exp - t0) / (t1 - t0))

    return interest_rate
