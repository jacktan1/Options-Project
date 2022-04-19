import numpy as np
import pandas as pd


class GreeksBase:
    def __init__(self):
        self.output_msg = []

        # Housekeeping for child class functions
        self.name = None
        self.date = None
        self.date_close = None
        self.exp_date = None
        self.years_to_exp = None
        self.tag = None

    def interpolate_intervals(self, date_df, parameters, date):
        """
        Interpolate metrics at standardized intervals from expiration dates present.
        Linear interpolation using two values closest to point of interest (x).

        f(n) = f(n_0) * ((n_1 - n)/(n_1 - n_0)) + f(n_1) * ((n - n_0)/(n_1 - n_0))

        thresholds used:
        - 1 month (1/12 year)
        - 2 months (1/6)
        - 3 months (1/4)
        - 6 months (1/2)
        - 1 year (1)
        """
        output_list = []

        for param in parameters:

            assert all(n in date_df.columns for n in ["date", "years to exp", "tag", param]), "Missing columns!"

            df1 = date_df[["date", "years to exp", "tag", param]].copy()

            df1.dropna(inplace=True)

            for tag in ["call", "put"]:

                df2 = df1[df1["tag"] == tag]

                for n in [1 / 12, 1 / 6, 1 / 4, 1 / 2, 1]:

                    n_0 = np.max(df2[df2["years to exp"] <= n]["years to exp"])
                    n_1 = np.min(df2[df2["years to exp"] > n]["years to exp"])

                    if pd.isna([n_0, n_1]).any():

                        self.output_msg.append(f"{self.name} - "
                                               f"(date: {date}, tag: {tag}, target: {round(n, 6)} year) - "
                                               f"cannot interpolate {param}")

                        param_weighted = np.nan
                    else:
                        param_0 = float(df2[df2["years to exp"] == n_0][param].values)
                        param_1 = float(df2[df2["years to exp"] == n_1][param].values)

                        param_weighted = round((param_0 * (n_1 - n) + param_1 * (n - n_0)) / (n_1 - n_0), 6)

                    # Add interpolated metric to list
                    output_list.append([date, param, round(n, 4), tag, param_weighted])

        # Interpolated for all parameters
        output_df = pd.DataFrame(output_list, columns=["date", "parameter", "interval", "tag", "value"])

        output_df = output_df.pivot(index=["date", "interval", "tag"],
                                    columns="parameter",
                                    values="value").reset_index(drop=False)

        return output_df
