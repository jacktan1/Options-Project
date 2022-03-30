from common_funs_multithread import GreeksBase
import pandas as pd


class CalcGamma(GreeksBase):
    def __init__(self):
        super().__init__()
        self.name = "Gamma"
        self.cols_input = ["date", "expiration date", "years to exp", "tag",
                           "strike midpoint", "moneyness", "moneyness ratio", "adj moneyness", "Delta"]
        self.cols_output_full = ["date", "expiration date", "tag",
                                 "strike midpoint", "moneyness", "moneyness ratio", "adj moneyness", "Gamma"]

    def run(self, input_dict):
        # Unpack
        year_df = input_dict["full df"][self.cols_input]
        year = input_dict["year"]

        # Housekeeping
        full_gamma_list = []

        for date in list(set(year_df["date"])):
            # date
            self.date = date
            df1 = year_df[year_df["date"] == date]

            for exp_date in list(set(df1["expiration date"])):
                # date + exp date
                self.exp_date = exp_date
                df2 = df1[df1["expiration date"] == exp_date]

                for tag in ["call", "put"]:
                    # date + exp date + tag
                    self.tag = tag
                    df3 = df2[df2["tag"] == tag].copy()

                    df3["Gamma"] = ((df3["Delta"] - df3["Delta"].shift(periods=1)) /
                                    -(df3["strike midpoint"] - df3["strike midpoint"].shift(periods=1))).round(6)

                    for metric in ["strike midpoint", "moneyness", "moneyness ratio", "adj moneyness"]:
                        df3[metric] = ((df3[metric] +
                                        df3[metric].shift(periods=1)) / 2).round(6)

                    # Drop empty row from "shift" operation
                    df3.dropna(inplace=True)

                    full_gamma_list.append(df3[self.cols_output_full])

        # Create parameter / full DataFrames
        full_gamma_df = pd.concat(full_gamma_list)

        # Sort
        full_gamma_df.sort_values(by=["date", "expiration date", "strike midpoint", "tag"], inplace=True,
                                  ignore_index=True)

        return {"name": self.name, "year": year,
                "full df": full_gamma_df, "output_msg": self.output_msg}
