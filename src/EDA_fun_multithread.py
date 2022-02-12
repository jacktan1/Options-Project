import numpy as np
from scipy.stats import kendalltau
import pandas as pd

import time


def delta_open_interest(input_dict):
    # Unpack
    options_df = input_dict["df"]
    date_1 = input_dict["former date"]
    date_2 = input_dict["latter date"]
    year = input_dict["year"]
    # former_int = input_dict["former date"]
    # latter_int = input_dict["latter date"]
    # date_1 = input_dict["start date"]
    ###
    # start_time = input_dict["start time"]
    # logs = ""

    ###
    # logs += f"{date_1}: \n"
    # logs += f"unpacking took {time.time() - start_time} \n"
    # start_time = time.time()

    # Extract previous day's open interest & rename
    former_int = options_df[options_df["date"] == date_1][["date", "year", "tag", "expiration date",
                                                           "adj strike", "open interest", "volume"]]
    former_int = former_int.rename(columns={"open interest": "open interest 1",
                                            "volume": "volume 1"})

    # Remove options that expire day of
    former_int = former_int[former_int["expiration date"] > date_1]

    # Extract following day's open interest & rename
    latter_int = options_df[options_df["date"] == date_2][["tag", "expiration date", "adj strike",
                                                           "open interest", "volume"]]
    latter_int = latter_int.rename(columns={"open interest": "open interest 2",
                                            "volume": "volume 2"})
    ###
    # logs += f"filtering took {time.time() - start_time} \n"
    # start_time = time.time()

    # Outer join as some options were newly created and some disappear (all open contracts were exercised etc.)
    joined_df = former_int.merge(right=latter_int,
                                 on=["tag", "expiration date", "adj strike"],
                                 how="outer")

    # Fill NANs (occur when new options appear or existing options disappear)
    joined_df["date"].fillna(value=date_1, inplace=True)
    joined_df["year"].fillna(value=year, inplace=True)
    joined_df[["volume 1", "volume 2", "open interest 1", "open interest 2"]] = (
        joined_df[["volume 1", "volume 2", "open interest 1", "open interest 2"]].fillna(value=0))

    # Get change in open interest
    joined_df["delta interest"] = joined_df["open interest 2"] - joined_df["open interest 1"]

    joined_df["abs delta"] = np.abs(joined_df["delta interest"])

    ###
    # logs += f"calculating took {time.time() - start_time} \n"

    return joined_df[["date", "year", "tag", "expiration date", "adj strike",
                      "volume 1", "volume 2", "open interest 1", "open interest 2",
                      "delta interest", "abs delta"]]


# Function for calculating Kendall rank correlation
def kendall_rank(input_list):
    """
    Function used to calculate Kendall rank correlation. Added here
    so that it can be used for parallel processing.

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
