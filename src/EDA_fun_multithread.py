import numpy as np
from scipy.stats import kendalltau
from sklearn import linear_model
import pandas as pd


def delta_open_interest(input_dict):
    """
    Calculate change in open interest between two dates. Remove options
    that expire day of (they will not exist the next day, no "delta").
    Add new entries for new options (exist in latter date but not former).

    :param input_dict: {options_df, date_1, date_2, year} (dict)
    :return: joined_df (joined DataFrame between date_1 and date_2)
    """

    # Unpack
    options_df = input_dict["df"]
    date_1 = input_dict["former date"]
    date_2 = input_dict["latter date"]
    year = input_dict["year"]

    # Bookkeeping variables
    output_msg = []

    # Extract previous day's open interest & rename
    former_df = options_df[options_df["date"] == date_1].copy()
    former_df.rename(columns={"open interest": "open interest 1",
                              "volume": "volume 1"}, inplace=True)

    # Remove options that expire before the next data date
    former_df = former_df[former_df["expiration date"] >= date_2]

    # Extract following day's open interest & rename
    latter_df = options_df[options_df["date"] == date_2].copy()
    latter_df.drop(columns=["year", "date"], inplace=True)
    latter_df.rename(columns={"open interest": "open interest 2",
                              "volume": "volume 2"}, inplace=True)

    # Outer join as some options were newly created and some disappear (all open contracts were exercised etc.)
    joined_df = former_df.merge(right=latter_df,
                                on=["expiration date", "tag", "adj strike"],
                                how="outer")

    # See if there are entirely new / missing exp dates
    na_df = joined_df[joined_df.isna().any(axis=1)]
    na_exp_dates = np.unique(na_df["expiration date"])

    for exp_date in na_exp_dates:
        na_exp_date_df = na_df[na_df["expiration date"] == exp_date]
        if na_exp_date_df.shape[0] == joined_df[joined_df["expiration date"] == exp_date].shape[0]:
            if all(na_exp_date_df["volume 2"].isna()) & any(na_exp_date_df["volume 1"] != 0):
                output_msg.append(
                    f"WARNING: Exp date: {exp_date} options are missing from {date_2} (previously present on {date_1})")
            # elif any(na_exp_date_df["volume 2"] != 0):
            #     output_msg.append(
            #         f"Exp date: {exp_date} options are added on {date_2} (they were not present in {date_1})")

    # Fill NANs (occur when new options appear or existing options disappear)
    joined_df["date"].fillna(value=date_1, inplace=True)
    joined_df["year"] = joined_df["year"].fillna(value=year).astype(int)

    joined_df[["volume 1", "volume 2", "open interest 1", "open interest 2"]] = \
        joined_df[["volume 1", "volume 2", "open interest 1", "open interest 2"]].fillna(value=0)

    # Get change in open interest
    joined_df["delta interest"] = joined_df["open interest 2"] - joined_df["open interest 1"]

    joined_df["abs delta"] = np.abs(joined_df["delta interest"])

    # Sanity check
    assert joined_df[joined_df.isna().any(axis=1)].empty, "There are NANs present in joined DataFrame!"

    return {"df": joined_df, "messages": output_msg}


def fit_linear_model(input_dict):
    """
    Fit linear regression models of "days till expiry" vs. various metrics.
        1. Baseline linear regression between (days until expiry (DTE) vs. moneyness)
        2. DTE vs. moneyness * (+/- 1) depending on sign of delta interest / volume
        3. DTE vs. moneyness * (+/- 1) weighted by delta interest / volume
        4. DTE vs. moneyness * (+/- 1) weighted by adj. ask price
        5. DTE vs. moneyness * (+/- 1) weighted by delta interest / volume * ask price
    Return coefficient and intercept of these models

    :param input_dict: {year_df, date, n_1 ("delta interest"/"volume"), n_2 ("call"/"put")} (dict)
    :return: {date, n_1, n_2, (models), messages} (dict)
    """

    # Unpack variables
    year_df = input_dict["year_df"]
    date = input_dict["date"]
    n_1 = input_dict["n_1"]
    n_2 = input_dict["n_2"]

    # Bookkeeping variables
    output_msg = []

    # Filter for date
    date_df = year_df[year_df["date"] == date]

    # Filter for options with delta interest / volume & filter for call / put
    date_df = date_df[(date_df[n_1] != 0) & (date_df["tag"] == n_2)]

    # If filtered DataFrame is empty
    if date_df.empty:
        output_msg.append(f"{date}: No {n_2} options with {n_1} != 0")

        baseline = [np.nan, np.nan]
        sign = [np.nan, np.nan]
        tag = [np.nan, np.nan]
        price = [np.nan, np.nan]
        er = [np.nan, np.nan]

    # If "delta sign" are all 0 (caused by "delta interest" being all 0)
    elif all(date_df["delta sign"] == 0):
        # Doesn't use delta sign
        baseline_model = linear_model.LinearRegression().fit(X=date_df[["days till exp"]],
                                                             y=date_df["adj moneyness"])
        baseline = [float(baseline_model.coef_), float(baseline_model.intercept_)]
        sign = [np.nan, np.nan]
        tag = [np.nan, np.nan]
        price = [np.nan, np.nan]
        er = [np.nan, np.nan]

    # Normally
    else:
        # Fit models
        baseline_model = linear_model.LinearRegression().fit(X=date_df[["days till exp"]],
                                                             y=date_df["adj moneyness"])

        sign_model = linear_model.LinearRegression().fit(X=date_df[["days till exp"]],
                                                         y=date_df["adj moneyness"] * date_df["delta sign"])

        tag_model = linear_model.LinearRegression().fit(X=date_df[["days till exp"]],
                                                        y=date_df["adj moneyness"] * date_df["delta sign"],
                                                        sample_weight=np.abs(date_df[n_1]))

        price_model = linear_model.LinearRegression().fit(X=date_df[["days till exp"]],
                                                          y=date_df["adj moneyness"] * date_df["delta sign"],
                                                          sample_weight=date_df["ask price"])

        er_model = linear_model.LinearRegression().fit(X=date_df[["days till exp"]],
                                                       y=date_df["adj moneyness"] * date_df["delta sign"],
                                                       sample_weight=np.abs(
                                                           date_df[n_1] * date_df["ask price"]))

        baseline = [float(baseline_model.coef_), float(baseline_model.intercept_)]
        sign = [float(sign_model.coef_), float(sign_model.intercept_)]
        tag = [float(tag_model.coef_), float(tag_model.intercept_)]
        price = [float(price_model.coef_), float(price_model.intercept_)]
        er = [float(er_model.coef_), float(er_model.intercept_)]

    return {"date": date, "n_1": n_1, "n_2": n_2,
            "baseline": baseline,
            "sign": sign,
            "tag": tag,
            "price": price,
            "er": er,
            "messages": output_msg}


def kendall_rank(input_list):
    """
    Function used to calculate Kendall rank correlation.

    :param input_list: 2-column DataFrame to apply Kendall rank to
    :return: tau: correlation [-1, 1]
             pval: p-value of such correlation
    """

    if type(input_list[0]) == pd.core.frame.DataFrame:
        input_df = input_list[0]
        option_type = input_list[1]
    else:
        input_df = input_list[1]
        option_type = input_list[0]

    assert input_df.shape[1] == 2, "There are more than two columns in input!"
    my_cols = list(input_df.columns)

    [tau, pval] = kendalltau(input_df.iloc[:, 0], input_df.iloc[:, 1])
    return [tau, pval, my_cols[0], my_cols[1], option_type]
