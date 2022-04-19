import numpy as np
import pandas as pd
from sklearn import linear_model


class CalcCustomInputs:
    def __init__(self):
        self.name = "custom"
        self.output_msg = []
        self.cols_input = ["date", "expiration date", "years to exp", "tag",
                           "strike price", "adj moneyness ratio", "ask price",
                           "open interest", "volume"]

        # Linear models to fit
        self.models = ["baseline", "sign",
                       "doi", "volume", "price",
                       "doi*price", "volume*price"]

        # Model param column names
        self.param_names = []
        for m in self.models:
            self.param_names.extend([f"{m}_slope", f"{m}_intercept"])

        self.cols_output = ["date", "tag"] + self.param_names

    def group_date_pairs(self, input_list):
        """
        TODO: Make function parallel, deal with edge cases (last date of year) separately

        :param input_list: list of aggregated option spreads for given year
        :return: [{joined_df, date_0, date_1}, {joined_df, date_1, date_2} etc.] (list)
        """
        # Unpack
        year_list = sorted([n["year"] for n in input_list])

        output_list = []

        for year in year_list:
            year_df = [n["df"] for n in input_list if n["year"] == year][0].copy()

            year_df = self.get_input_cols(year_df)

            dates = sorted(set(year_df["date"]))

            for date_0 in dates:
                # Find the following date
                try:
                    date_1 = np.min([n for n in dates if n > date_0])

                    # Option spread of date_0 + date_1
                    output_df = year_df[year_df["date"].isin([date_0, date_1])].reset_index(drop=True)

                except ValueError:
                    # If next year is available
                    if year < np.max(year_list):
                        next_year_df = [n["df"] for n in input_list if n["year"] == (year + 1)][0]

                        next_year_df = self.get_input_cols(next_year_df)

                        # Get first date of next year
                        date_1 = np.min(next_year_df["date"])

                        # Option spreads of date_0 + date_1
                        output_df = year_df[year_df["date"] == date_0].append(
                            next_year_df[next_year_df["date"] == date_1], ignore_index=True)

                    # If no next year, skip
                    else:
                        continue

                output_list.append({"df": output_df, "former date": date_0, "latter date": date_1})

        # Done for all data dates in all years
        return output_list

    def get_input_cols(self, year_df):
        # Compute additional columns
        year_df["adj moneyness"] = ((year_df["date close"] - year_df["date div"]) -
                                    (year_df["strike price"] - year_df["exp date div"]))

        # Opposite for put options
        year_df.loc[year_df["tag"] == "put", "adj moneyness"] = \
            -year_df.loc[year_df["tag"] == "put", "adj moneyness"]

        year_df["adj moneyness ratio"] = year_df["adj moneyness"] / year_df["date close"]

        year_df = year_df[self.cols_input]

        return year_df

    def run(self, input_dict):
        """
        - Calculate change in open interest (OI) between two dates. Remove options that expire day of.

        - Fit linear regression models of "years till expiry" vs. various metrics.
            1. years until expiry (YTE) vs. adjusted moneyness ratio - (baseline)
            2. YTE vs. adj. moneyness ratio * delta OI sign
            3. YTE vs. adj. moneyness ratio * delta OI sign weighted by |delta interest|
            4. YTE vs. adj. moneyness ratio * delta OI sign weighted by volume
            5. YTE vs. adj. moneyness ratio * delta OI sign weighted by ask price
            6. YTE vs. adj. moneyness ratio * delta OI sign weighted by |delta interest * ask price|
            7. YTE vs. adj. moneyness ratio * delta OI sign weighted by volume * ask price

        Note: Open interest is recorded at start of date (proven in EDA).

        :param input_dict: {options_df, date_0, date_1} (dict)
        :return: {df, output_msg}
        """

        # Unpack
        options_df = input_dict["df"]
        t_0 = input_dict["former date"]
        t_1 = input_dict["latter date"]

        # Flush output messages if class object is reused
        self.output_msg = []

        # Sanity check
        if np.busday_count(t_0, t_1) > 2:
            self.output_msg.append(f"{self.name} - time between data dates [{t_0}, {t_1}] > 2 business days!")

        #
        # Calculate change in open interest
        #

        # Filter for data date_0 and exp date >= date_1
        df_0 = options_df[(options_df["date"] == t_0) &
                          (options_df["expiration date"] >= t_1)].copy()
        df_0.rename(columns={"open interest": "open interest 0"}, inplace=True)
        exp_dates_0 = set(np.unique(df_0["expiration date"]))

        # Filter for data date_1 & select needed columns
        df_1 = options_df[options_df["date"] == t_1].copy()
        df_1 = df_1[["expiration date", "tag", "strike price", "open interest"]]
        df_1.rename(columns={"open interest": "open interest 1"}, inplace=True)
        exp_dates_1 = set(np.unique(df_1["expiration date"]))

        # Sanity check
        missing_exp_dates = exp_dates_0 - exp_dates_1
        if missing_exp_dates:
            self.output_msg.append(f"{self.name} - "
                                   f"(date: {t_0}) - "
                                   f"Exp dates: {missing_exp_dates} missing from {t_1}")

        # Not right join because we need "ask price" of date_0
        # Not left join because dropped exp dates are usually errors
        df = df_0.merge(right=df_1,
                        on=["expiration date", "tag", "strike price"],
                        how="inner")

        # Get change in open interest
        df["delta interest"] = df["open interest 1"] - df["open interest 0"]
        df["oi sign"] = np.sign(df["delta interest"])

        # Get EOD open interest
        df.rename(columns={"open interest 1": "EOD open interest"}, inplace=True)

        # Drop unneeded columns
        df.drop(columns=["expiration date", "strike price", "open interest 0"], inplace=True)

        # Sanity check
        assert df[df.isna().any(axis=1)].empty, "There are NaNs present in joined DataFrame!"

        #
        # Fit Models
        #

        output_list = []

        # Fit separate models for call and put spreads
        for tag in ["call", "put"]:

            # Filter for volume or delta open interest != 0 & tag
            df_model = df[(df["tag"] == tag) & ((df["delta interest"] != 0) | (df["volume"] != 0))]
            model_params = []

            # Edge case 1
            if df_model.empty:
                self.output_msg.append(f"{self.name} - "
                                       f"(date: {t_0}, tag: {tag}) - "
                                       f"No options with 'delta interest' or 'volume' != 0")

                model_params = [np.nan] * len(self.param_names)

            # Edge case 2
            elif all(df_model["delta interest"] == 0):
                self.output_msg.append(f"{self.name} - "
                                       f"(date: {t_0}, tag: {tag}) - "
                                       f"No options with 'delta interest' != 0")

                for m in self.models:
                    if m == "baseline":
                        model = linear_model.LinearRegression().fit(X=df_model[["years to exp"]],
                                                                    y=df_model["adj moneyness ratio"])

                        model_params.extend([float(model.coef_), float(model.intercept_)])
                    else:
                        model_params.extend([np.nan, np.nan])

            # Ideal
            else:
                for m in self.models:
                    if m == "baseline":
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"]
                        )
                    elif m == "sign":
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"] * df_model["oi sign"]
                        )
                    elif m == "doi":
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"] * df_model["oi sign"],
                            sample_weight=np.abs(df_model["delta interest"])
                        )
                    elif m == "volume":
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"] * df_model["oi sign"],
                            sample_weight=df_model["volume"]
                        )
                    elif m == "price":
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"] * df_model["oi sign"],
                            sample_weight=df_model["ask price"]
                        )
                    elif m == "doi*price":
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"] * df_model["oi sign"],
                            sample_weight=np.abs(df_model["delta interest"] * df_model["ask price"])
                        )
                    # volume*price
                    else:
                        model = linear_model.LinearRegression().fit(
                            X=df_model[["years to exp"]],
                            y=df_model["adj moneyness ratio"] * df_model["oi sign"],
                            sample_weight=df_model["volume"] * df_model["ask price"]
                        )

                    model_params.extend([float(model.coef_), float(model.intercept_)])

            output_list.append([t_0, tag] + [round(n, 6) for n in model_params])

        output_df = pd.DataFrame(output_list, columns=(["date", "tag"] + self.param_names))

        return {"df": output_df, "output_msg": self.output_msg}

    def group_by_year(self, input_list):

        # Housekeeping
        output_list = []

        # Group all date dfs into single df
        df_combined = pd.concat(input_list)

        df_combined["year"] = pd.to_datetime(df_combined["date"]).dt.year

        years = np.unique(df_combined["year"])

        for year in years:
            df_year = df_combined[df_combined["year"] == year].copy()

            output_list.append({"name": self.name, "year": year,
                                "param df": df_year[self.cols_output]})

        return output_list
