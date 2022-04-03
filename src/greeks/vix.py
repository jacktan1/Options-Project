from base import GreeksBase
import numpy as np
import pandas as pd


class CalcVix(GreeksBase):
    def __init__(self, input_dict):
        super().__init__()
        self.name = "VIX"
        self.rates_dict = input_dict["rates_dict"]
        self.parameters = ["vix"]
        self.cols_input = ["date", "expiration date", "years to exp", "tag",
                           "strike price", "ask price", "date close"]
        self.cols_output_full = ["date", "expiration date", "tag",
                                 "strike midpoint", "delta strike", "ask midpoint", "vix"]

    def run(self, input_dict):
        """
        TODO: Make function parallel at date level rather than year. Option spread size increased ~10x from 2005 to 2021

        :param input_dict: {year_df, year}
        :return: dict {name, year, param df, full df, output_msg}
        """

        # Unpack
        year_df = input_dict["df"][self.cols_input]
        year = input_dict["year"]

        # Housekeeping
        full_vix_list = []
        param_vix_list = []

        # Flush output messages if class object is reused
        self.output_msg = []

        for date in list(set(year_df["date"])):
            # date
            self.date = date
            df1 = year_df[year_df["date"] == date]
            self.date_close = float(np.unique(df1["date close"]))
            # Housekeeping
            date_param_list = []

            for exp_date in list(set(df1["expiration date"])):
                # VIX undefined if time till expiry is 0. Skip
                if date == exp_date:
                    continue

                # date + exp date
                self.exp_date = exp_date
                df2 = df1[df1["expiration date"] == exp_date]
                self.years_to_exp = float(np.unique(df2["years to exp"]))

                exp_interest_rate = self.get_interest_rate()

                for tag in ["call", "put"]:
                    # date + exp date + tag
                    self.tag = tag
                    df3 = df2[df2["tag"] == tag].copy()

                    df3["moneyness"] = df3["date close"] - df3["strike price"]

                    if self.tag == "put":
                        df3["moneyness"] = -df3["moneyness"]

                    # Get min ITM strike
                    min_itm = np.min(df3[df3["moneyness"] >= 0]["moneyness"])

                    # Get all OTM & the smallest ITM option
                    df4 = df3[df3["moneyness"] <= min_itm].copy()

                    # Set upper bound of ITM strike price to ATM (closing price). Partial contribution
                    df4.loc[(df4["moneyness"] == min_itm), "strike price"] = self.date_close

                    df4["delta strike"] = df4["strike price"] - df4["strike price"].shift(periods=1)

                    df4["ask midpoint"] = (df4["ask price"] + df4["ask price"].shift(periods=1)) / 2

                    df4["vix"] = ((df4["delta strike"] * df4["ask midpoint"] *
                                   np.exp(exp_interest_rate * self.years_to_exp)) / self.date_close ** 2)

                    # Only for full df
                    df4["strike midpoint"] = (df4["strike price"] + df4["strike price"].shift(periods=1)) / 2

                    # Drop empty row from "shift" operation
                    df4.dropna(inplace=True)

                    full_vix_list.append(df4[self.cols_output_full])

                    # Sum of all VIX components to get final VIX value
                    vix_sum = np.sum(df4["vix"].dropna()) / self.years_to_exp

                    date_param_list.append([self.date, self.exp_date, self.years_to_exp, self.tag, vix_sum])

            # All VIX params for data date
            date_df = pd.DataFrame(date_param_list,
                                   columns=["date", "expiration date", "years to exp", "tag", "vix"])

            # Interpolate VIX at set intervals (1 month, 2 months, etc.)
            date_vix_df = self.interpolate_intervals(date_df=date_df,
                                                     parameters=self.parameters,
                                                     date=self.date)

            param_vix_list.append(date_vix_df)

        # Create parameter / full DataFrames
        param_vix_df = pd.concat(param_vix_list)
        full_vix_df = pd.concat(full_vix_list)

        # Sort
        param_vix_df.sort_values(by=["date", "interval", "tag"], inplace=True, ignore_index=True)
        full_vix_df.sort_values(by=["date", "expiration date", "strike midpoint", "tag"],
                                inplace=True, ignore_index=True)

        return {"name": self.name, "year": year,
                "param df": param_vix_df, "full df": full_vix_df, "output_msg": self.output_msg}

    def get_interest_rate(self):
        """
        If the interest rate on dates t_0 and t_1 are f(t_0) and f(t_1), respectively.
        The linear interpolation of interest rate on date t is:

        f(t) = f(t_0) * ((t_1 - t)/(t_1 - t_0)) + f(t_1) * ((t - t_0)/(t_1 - t_0))
        """
        rate_keys = list(self.rates_dict.keys())
        # For exp dates that expire within 1 month (a.k.a. no lower bound)
        rate_keys.append(0)

        t0 = np.max([n for n in rate_keys if n <= self.years_to_exp])
        t1 = np.min([n for n in rate_keys if n > self.years_to_exp])

        if pd.isna([t0, t1]).any():
            raise Exception(f"Unable to interpolate interest rate! Lower bound: {t0} Upper bound: {t1}")

        # Housekeeping
        interest_rate = 0

        for t in [t0, t1]:
            if t != 0:
                # Interest rate DataFrame of time period chosen
                df = self.rates_dict[t]
                dates = list(df["date"])

                # If unable to find rate for data date, interpolate
                if self.date not in dates:
                    # Get dates before and after data date
                    date_0 = self.date
                    date_1 = self.date

                    while date_0 not in dates:
                        date_0 = pd.to_datetime(np.busday_offset(date_0, -1)).date()

                    while date_1 not in dates:
                        date_1 = pd.to_datetime(np.busday_offset(date_1, 1)).date()

                    rate_t = (float(df[df["date"] == date_0]["continuous rate"]) +
                              float(df[df["date"] == date_1]["continuous rate"])) / 2
                else:
                    rate_t = float(df[df["date"] == self.date]["continuous rate"])
            # If lower bound is 0
            else:
                rate_t = 0

            # Add component contribution to total
            if t == t0:
                interest_rate = interest_rate + rate_t * ((t1 - self.years_to_exp) / (t1 - t0))
            elif t == t1:
                interest_rate = interest_rate + rate_t * ((self.years_to_exp - t0) / (t1 - t0))

        return interest_rate
