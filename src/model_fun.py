from scipy.stats import kendalltau
import pandas as pd


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
