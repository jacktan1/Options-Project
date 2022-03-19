import pandas as pd


def calc_gamma(input_dict):
    # Unpack
    year_df = input_dict["df"]
    year = input_dict["year"]

    # Initialize variables
    gamma_list = []
    my_cols = ["date", "expiration date", "tag", "strike midpoint", "Gamma", "moneyness", "adj moneyness",
               "date div", "exp date div", "date close"]

    for date in list(set(year_df["date"])):
        # date
        df1 = year_df[year_df["date"] == date]
        for exp_date in list(set(df1["expiration date"])):
            # date + exp date
            df2 = df1[df1["expiration date"] == exp_date]
            for tag in ["call", "put"]:
                # date + exp date + tag
                df3 = df2[df2["tag"] == tag].copy()

                df3.rename(columns={"strike midpoint": "strike"}, inplace=True)
                df3.drop(columns=["moneyness", "adj moneyness"], inplace=True)

                df3["strike midpoint"] = ((df3["strike"] +
                                           df3["strike"].shift(periods=1)) / 2).round(6)

                df3["Gamma"] = ((df3["Delta"] - df3["Delta"].shift(periods=1)) /
                                -(df3["strike"] - df3["strike"].shift(periods=1))).round(6)

                df3["moneyness"] = df3["date close"] - df3["strike midpoint"]
                df3["adj moneyness"] = ((df3["date close"] - df3["date div"]) -
                                        (df3["strike midpoint"] - df3["exp date div"]))

                if tag == "put":
                    df3["moneyness"] = -df3["moneyness"]
                    df3["adj moneyness"] = -df3["adj moneyness"]

                gamma_list.append(df3.dropna()[my_cols])

    gamma_df = pd.concat(gamma_list)

    gamma_df.sort_values(by=["date", "expiration date", "strike midpoint", "tag"], inplace=True, ignore_index=True)

    return {"df": gamma_df, "year": year}
