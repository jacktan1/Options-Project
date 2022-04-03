from base import GreeksBase
import numpy as np
import pandas as pd


class CalcDelta(GreeksBase):
    def __init__(self, input_dict):
        super().__init__()
        self.name = "Delta"
        self.abs_reference = input_dict["abs_reference_threshold"]
        self.abs_lower = input_dict["abs_lower_threshold"]
        self.abs_higher = input_dict["abs_higher_threshold"]
        self.parameters = ["delta_reference_point", "delta_itm_spread", "delta_otm_spread"]
        self.cols_input = ["date", "expiration date", "years to exp", "tag",
                           "strike price", "ask price", "date close",
                           "date div", "exp date div"]
        self.cols_output_full = ["date", "expiration date", "years to exp", "tag",
                                 "strike midpoint", "moneyness", "moneyness ratio", "adj moneyness", "Delta"]

        # Housekeeping for class functions
        self.moneyness_df = None

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
        full_delta_list = []
        param_delta_list = []

        # Flush output messages if class object is reused
        self.output_msg = []

        for date in list(set(year_df["date"])):
            # date
            self.date = date
            df1 = year_df[year_df["date"] == date]
            # Housekeeping
            date_param_list = []

            for exp_date in list(set(df1["expiration date"])):
                # Time till expiry is 0. Delta should be step function. Skip
                if date == exp_date:
                    continue

                # date + exp date
                self.exp_date = exp_date
                df2 = df1[df1["expiration date"] == exp_date]
                self.years_to_exp = float(np.unique(df2["years to exp"]))

                for tag in ["call", "put"]:
                    # date + exp date + tag
                    self.tag = tag
                    df3 = df2[df2["tag"] == tag].copy()

                    df3["Delta"] = ((df3["ask price"] - df3["ask price"].shift(periods=1)) /
                                    -(df3["strike price"] - df3["strike price"].shift(periods=1))).round(6)

                    df3["strike midpoint"] = ((df3["strike price"] +
                                               df3["strike price"].shift(periods=1)) / 2).round(6)

                    df3["moneyness"] = df3["date close"] - df3["strike midpoint"]
                    df3["adj moneyness"] = ((df3["date close"] - df3["date div"]) -
                                            (df3["strike midpoint"] - df3["exp date div"]))

                    if tag == "put":
                        df3["moneyness"] = -df3["moneyness"]
                        df3["adj moneyness"] = -df3["adj moneyness"]

                    df3["moneyness ratio"] = df3["moneyness"] / df3["date close"]

                    # Drop empty row from "shift" operation
                    df3.dropna(inplace=True)

                    full_delta_list.append(df3[self.cols_output_full])

                    # Get moneyness ratio at different Delta thresholds
                    threshold_moneyness_dict = self.get_moneyness_ratios(
                        df=df3,
                        abs_thresholds=[self.abs_lower, self.abs_reference, self.abs_higher])

                    # Derive parameters using the moneyness ratios at different thresholds
                    delta_parameters_dict = self.get_parameters(input_dict=threshold_moneyness_dict)

                    # Append to list
                    for key in delta_parameters_dict:
                        date_param_list.append([self.date, self.exp_date, self.years_to_exp, self.tag,
                                                key, delta_parameters_dict[key]])

            # All Delta params for data date
            date_df = pd.DataFrame(date_param_list,
                                   columns=["date", "expiration date", "years to exp", "tag",
                                            "parameter", "moneyness ratio"])

            date_df = date_df.pivot(index=["date", "expiration date", "years to exp", "tag"],
                                    columns="parameter",
                                    values="moneyness ratio").reset_index(drop=False)

            # Interpolate parameters to set intervals (1 month, 2 months, etc.)
            date_delta_df = self.interpolate_intervals(date_df=date_df,
                                                       parameters=self.parameters,
                                                       date=self.date)

            param_delta_list.append(date_delta_df)

        # Create parameter / full DataFrames
        param_delta_df = pd.concat(param_delta_list)
        full_delta_df = pd.concat(full_delta_list)

        # Sort
        param_delta_df.sort_values(by=["date", "interval", "tag"], inplace=True, ignore_index=True)
        full_delta_df.sort_values(by=["date", "expiration date", "strike midpoint", "tag"], inplace=True,
                                  ignore_index=True)

        return {"name": self.name, "year": year,
                "param df": param_delta_df, "full df": full_delta_df, "output_msg": self.output_msg}

    def get_moneyness_ratios(self, df, abs_thresholds):
        # Housekeeping
        cand_0 = pd.Series()
        cand_1 = pd.Series()
        necessary_columns = ["moneyness ratio", "Delta"]
        output_dict = dict()

        # Local copy
        self.moneyness_df = df[necessary_columns].copy()

        # Flip put curve to be monotonically increasing
        if self.tag == "put":
            self.moneyness_df["Delta"] = -self.moneyness_df["Delta"]

        # Max / min moneyness ratios
        max_moneyness = np.max(self.moneyness_df["moneyness ratio"])
        min_moneyness = np.min(self.moneyness_df["moneyness ratio"])

        for i in abs_thresholds:
            for j in ["pre", "post"]:

                cand = self.find_next_candidate(cand_type=j, threshold=i,
                                                min_moneyness=min_moneyness,
                                                max_moneyness=max_moneyness)

                # If no suitable option exists (spread is too narrow etc.), n is empty DataFrame
                if cand.empty:
                    if j == "pre":
                        cand_0 = np.nan
                    else:
                        cand_1 = np.nan

                # If suitable candidate exist, cand is a Series
                else:
                    # Find options neighbouring cand
                    n_0, n_1 = self.find_neighbours(poi=cand)

                    # n is considered valid if monotonically increasing with immediate neighbours
                    while not (cand["Delta"] >= n_0["Delta"]) & (n_1["Delta"] >= cand["Delta"]):
                        # Find next best candidate
                        if j == "pre":
                            cand = self.find_next_candidate(cand_type=j, threshold=i,
                                                            min_moneyness=min_moneyness,
                                                            max_moneyness=cand["moneyness ratio"])
                        else:
                            cand = self.find_next_candidate(cand_type=j, threshold=i,
                                                            min_moneyness=cand["moneyness ratio"],
                                                            max_moneyness=max_moneyness)

                        # No more valid candidates
                        if cand.empty:
                            cand = np.nan
                            break
                        else:
                            # New neighbours
                            n_0, n_1 = self.find_neighbours(poi=cand)

                    # Found appropriate options
                    if j == "pre":
                        cand_0 = cand
                    else:
                        cand_1 = cand

            # Obtained upper & lower bound for threshold
            if pd.isna([cand_0, cand_1]).any():
                self.output_msg.append(f"{self.name} - "
                                       f"(data date: {self.date}, exp date: {self.exp_date}, tag: {self.tag}) - "
                                       f"cannot interpolate |threshold|: {i} moneyness ratio")
                threshold_moneyness = np.nan

            # Ideal case
            else:
                # Linearly interpolate moneyness ratio at threshold
                delta_0 = cand_0["Delta"]
                moneyness_0 = cand_0["moneyness ratio"]

                delta_1 = cand_1["Delta"]
                moneyness_1 = cand_1["moneyness ratio"]

                threshold_moneyness = (moneyness_1 * (i - delta_0) + moneyness_0 * (delta_1 - i)) / (delta_1 - delta_0)

            # Add threshold moneyness ratio to output
            if self.tag == "put":
                actual_threshold = -i
            else:
                actual_threshold = i

            output_dict[actual_threshold] = round(threshold_moneyness, 8)

        return output_dict

    def find_next_candidate(self, cand_type, threshold, min_moneyness, max_moneyness):
        # Not on edges
        cand = self.moneyness_df[(self.moneyness_df["moneyness ratio"] > min_moneyness) &
                                 (self.moneyness_df["moneyness ratio"] < max_moneyness)].sort_values(
            by="moneyness ratio", ascending=True)

        if cand_type == "pre":
            cand = cand[cand["Delta"] <= threshold]
            if not cand.empty:
                # Max moneyness & below threshold & not on edges
                cand = cand.iloc[-1, :]
        else:
            cand = cand[(cand["Delta"] > threshold)]
            if not cand.empty:
                # Min moneyness & above threshold & not on edges
                cand = cand.iloc[0, :]

        return cand

    def find_neighbours(self, poi):
        n_0 = self.moneyness_df[self.moneyness_df["moneyness ratio"] < poi["moneyness ratio"]].sort_values(
            by="moneyness ratio", ascending=True).iloc[-1, :]

        n_1 = self.moneyness_df[self.moneyness_df["moneyness ratio"] > poi["moneyness ratio"]].sort_values(
            by="moneyness ratio", ascending=True).iloc[0, :]

        return n_0, n_1

    def get_parameters(self, input_dict):
        # Housekeeping
        output_dict = dict()

        if self.tag == "put":
            [reference, lower, higher] = [-self.abs_reference, -self.abs_lower, -self.abs_higher]
        else:
            [reference, lower, higher] = [self.abs_reference, self.abs_lower, self.abs_higher]

        # Sanity check
        assert all([n in input_dict.keys() for n in [reference, lower, higher]])

        # Calculate parameters
        if "delta_reference_point" in self.parameters:
            output_dict["delta_reference_point"] = input_dict[reference]

        if "delta_otm_spread" in self.parameters:
            output_dict["delta_otm_spread"] = input_dict[reference] - input_dict[lower]

        if "delta_itm_spread" in self.parameters:
            output_dict["delta_itm_spread"] = input_dict[higher] - input_dict[reference]

        return output_dict
