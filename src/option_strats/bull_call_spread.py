import itertools
import multiprocessing
from multiprocessing.pool import Pool
import numpy as np
import pandas as pd


class BullCallSpread:
    def __init__(self, dates, threshold=0, max_num_scores=10):
        self.data_dates = dates
        self.threshold = threshold
        self.max_num_scores = max_num_scores

    def run(self, options_df, pred_pdf_df):
        """
        Uses parallel processing to calculate the best option pairs for bull call spread.
        Score is determined by multiplying PDF with profit-loss function (element-wise), and integrating
        over entire range of predictions
        Takes top `self.max_num_scores` scores per [data date, expiration date], if they are > `self.threshold`

        :param options_df: Adj. options for all [data dates, expiration dates]
        :param pred_pdf_df: Model prediction PDFs for all [data dates, expiration dates]
        :return: scores_df
        """
        # Local to function
        input_list = []
        my_pool = Pool(multiprocessing.cpu_count())
        options_df = options_df[options_df["tag"] == "call"].copy()

        # Get inputs
        for date in self.data_dates:
            options_df0 = options_df[options_df["date"] == date]

            pred_pdf_df0 = pred_pdf_df[pred_pdf_df["date"] == date]

            # No prediction for data date
            if pred_pdf_df0.shape[0] == 0:
                continue

            for exp_date in sorted(set(options_df0["expiration date"]), reverse=False):
                # Time till expiry is 0
                if date == exp_date:
                    continue

                options_df1 = options_df0[options_df0["expiration date"] == exp_date].reset_index(drop=True)

                pred_pdf_df1 = pred_pdf_df0[pred_pdf_df0["expiration date"] == exp_date].reset_index(drop=True)

                assert pred_pdf_df1.shape[0] == 1, "Multiple prediction PDFs?!"

                input_list.append({"date": date,
                                   "exp_date": exp_date,
                                   "df": options_df1[["strike price", "ask price", "bid price"]],
                                   "pdf_x": pred_pdf_df1.loc[0, "range"],
                                   "pdf_y": pred_pdf_df1.loc[0, "pdf"],
                                   "bin_width": pred_pdf_df1.loc[0, "bin width"]})

        # Calculate strategy scores
        scores_list = my_pool.map(self.calc_option_pair, input_list)
        scores_df = pd.concat(scores_list, ignore_index=True)

        return scores_df

    def calc_option_pair(self, input_dict):
        """
        Calculate scores of all option pairs in [data date, expiration date]
        Takes top `self.max_num_scores` scores per [data date, expiration date], if they are > `self.threshold`

        :param input_dict: {"date", "exp_date", "df", "pdf_x", "pdf_y", "bin_width"}
        :return: output_df
        """
        # Local to function
        df = input_dict["df"]
        is_complete = False
        option_pairs = itertools.combinations(df.index, 2)
        output_list = []

        while not is_complete:
            try:
                [n1, n2] = next(option_pairs)

                strike_1 = df.loc[n1, "strike price"]
                strike_2 = df.loc[n2, "strike price"]

                assert strike_2 > strike_1

                ask_1 = df.loc[n1, "ask price"]
                bid_2 = df.loc[n2, "bid price"]

            except StopIteration:
                is_complete = True
                continue

            min_pl = bid_2 - ask_1
            max_pl = (strike_2 - strike_1) + min_pl

            pl_x = np.array([self.calc_pl(strike_1, strike_2, min_pl, max_pl, n) for n in input_dict["pdf_x"]])

            weighted_integral = np.sum(pl_x * input_dict["pdf_y"] * input_dict["bin_width"])

            if weighted_integral >= self.threshold:
                output_list.append([input_dict["date"], input_dict["exp_date"], strike_1, strike_2,
                                    round(-min_pl, 5), round(weighted_integral, 6)])

        # All combinations exhausted
        output_df = pd.DataFrame(output_list, columns=["date", "expiration date", "strike 1", "strike 2",
                                                       "investment cost", "score"])

        # Filter for best `max_num_scores` scores
        output_df = output_df.sort_values(by=["score", "investment cost"],
                                          ascending=[False, True]).reset_index(drop=True).iloc[:self.max_num_scores]

        return output_df

    @staticmethod
    def calc_pl(strike_1, strike_2, min_pl, max_pl, x):
        """
        Calculate the profit / loss of price `x` at option expiry

        :param strike_1: Lower strike price
        :param strike_2: Higher strike price
        :param min_pl: maximum loss of option pair (min profit / loss)
        :param max_pl: maximum gain of option pair
        :param x: final closing price
        :return: pl_x: profit / loss at x
        """

        if x <= strike_1:
            pl_x = min_pl
        elif x >= strike_2:
            pl_x = max_pl
        else:
            pl_x = x - strike_1 + min_pl

        return pl_x
