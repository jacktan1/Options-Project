import itertools
import multiprocessing
from multiprocessing.pool import Pool
import numpy as np
import pandas as pd


class BullCallSpread:
    def __init__(self, dates, threshold=0.00001, max_num_scores=3):
        self.data_dates = dates
        # Minimum score threshold for option pair to be considered
        self.threshold = threshold
        # Max number of contracts pairs to return for [data date, expiration date]
        self.max_num_scores = max_num_scores

        self.risk_scores_df = None
        self.no_risk_scores_df = None
        self.pl_df = None
        self.cumul_date_df = None
        self.exp_date_df = None

    def get_scores(self, options_df, pred_pdf_df):
        """
        1. Filter for option pairs for those with and without risk (min pl < 0 vs >= 0, respectively)
        2. Evaluate and select best `max_num_scores` "with risk" option pairs per [data date, expiration date]
        3. Calculate score ratio a given contract pair takes from the sum of all scores for that data date
        4. Calculate purchase ratio of that contract pair given score ratio and investment cost


        :param options_df: Adj. options for all [data dates, expiration dates]
        :param pred_pdf_df: Model prediction PDFs for all [data dates, expiration dates]
        :return: None
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

                # Sanity check
                assert pred_pdf_df1.shape[0] == 1, "Multiple prediction PDFs for a distinct [data, expiration] date"

                input_list.append({"date": date,
                                   "exp_date": exp_date,
                                   "days_to_exp": pred_pdf_df1.loc[0, "days to exp"],
                                   "df": options_df1[["strike price", "ask price", "bid price"]],
                                   "pdf_x": pred_pdf_df1.loc[0, "range"],
                                   "pdf_y": pred_pdf_df1.loc[0, "pdf"],
                                   "bin_width": pred_pdf_df1.loc[0, "bin width"]})

        # Calculate strategy scores
        results_list = my_pool.map(self.calc_option_pairs, input_list)

        # Option pairs with `min pl` < 0 (with risk)
        scores_df1 = pd.concat([n["with risk"] for n in results_list], ignore_index=True)

        # Option pairs with `min pl` > 0 (risk-free, likely mis-priced)
        scores_df2 = pd.concat([n["no risk"] for n in results_list], ignore_index=True)

        #
        # Process options pairs with risk
        #

        # Check that scores are valid
        assert all(scores_df1["score"] > 0), "There exist option pairs with score <= 0! Is threshold valid?"

        # Sum of date scores
        scores_date_df1 = scores_df1.groupby("date")["score"].sum().reset_index().rename(
            columns={"score": "score sum day"})

        scores_df1 = scores_df1.merge(scores_date_df1, on="date", how="inner", validate="m:1")

        # Get book cost for option pair on that day (assumes total investment of 1 unit of cash per day)
        scores_df1["book"] = scores_df1["score"] / scores_df1["score sum day"]

        # Purchase ratio (# of contract pairs to purchase)
        scores_df1["contract pairs"] = scores_df1["book"] / -scores_df1["min pl"]

        scores_df1.drop(columns="score sum day", inplace=True)

        # Add results to instance attribute
        self.risk_scores_df = scores_df1
        self.no_risk_scores_df = scores_df2

    def eval_model_strategy(self, date_close_df, num_days_year):
        """
        Evaluate the performance of model, given the vertical spread strategy

        1. Calculate raw return of contract pairs at expiration
        2. Calculate realized return, ROI for option pair, and annum ROI via simple compounding
            - Continuous compounding is not used due to some total losses (ln(0))
        3. Group by data date to calculate cumulative book, realized return and ROI
        4. Group by expiration date to get total book and weighted average annum ROI

        :param date_close_df: Historical close prices
        :param num_days_year: Number of days per year, used to get annualized return
        :return: None
        """

        #
        # Calculate ROI of option pairs that have capital risk
        #

        pl_df = self.risk_scores_df.merge(date_close_df[["date", "close"]],
                                          left_on="expiration date", right_on="date",
                                          how="left", validate="m:1")

        pl_df.drop(columns="date_y", inplace=True)

        pl_df.rename(columns={"date_x": "date",
                              "close": "exp close"}, inplace=True)

        # Gain from lower strike + loss from higher strike per option pair
        pl_df["raw return"] = (np.maximum(pl_df["exp close"] - pl_df["strike 1"], 0) +
                               np.minimum(pl_df["strike 2"] - pl_df["exp close"], 0))

        # Actual gain based on size of purchase
        pl_df["realized return"] = pl_df["raw return"] * pl_df["contract pairs"]

        # ROI for that option pair
        pl_df["ROI"] = (pl_df["realized return"] - pl_df["book"]) / pl_df["book"]

        # Annualized ROI
        pl_df["annum ROI"] = ((pl_df["realized return"] / pl_df["book"]) ** (num_days_year / pl_df["days to exp"])) - 1

        self.pl_df = pl_df

        #
        # Group by data date to calculate cumulative book, realized return and ROI
        #

        self.cumul_date_df = self.calc_cumul_date_roi()

        #
        # Group by expiration date to get total book and weighted average annum ROI
        #

        self.exp_date_df = self.calc_exp_date_roi()

    def calc_option_pairs(self, input_dict):
        """
        Calculate scores of all contract pairs in [data date, expiration date]
        Total score is determined by multiplying PDF with profit-loss function (element-wise), and integrating
        over entire range of predictions

        If min_pl < 0, pair has risk (potential to lose money). Otherwise, if min_pl >= 0, pair is "risk free".

        For risk option pairs:
            Divide raw integral by days to expiry, else heavily skewed towards distant exp dates due to large premiums:

            ```score = Total score / days to exp```

            TODO: instead of scaling parameter (1 / days to exp), use (a / days to exp) for some `a`

            If score > `self.threshold`, Take top `self.max_num_scores` scores per [data date, expiration date]

        For rik free option pairs:
            Take all

        :param input_dict: {"date", "exp_date", "df", "pdf_x", "pdf_y", "bin_width"}
        :return: output_dict
        """

        # Local to function
        df = input_dict["df"]
        is_complete = False
        option_pairs = itertools.combinations(df.index, 2)

        # Option pairs that are not risk-free (min_pl < 0)
        output_list1 = []
        # Option pairs that are risk-free (min_pl >= 0)
        output_list2 = []

        while not is_complete:
            try:
                # Get next pair of options
                [n1, n2] = next(option_pairs)

                strike_1 = df.loc[n1, "strike price"]
                strike_2 = df.loc[n2, "strike price"]

                assert strike_2 > strike_1

                ask_1 = df.loc[n1, "ask price"]
                bid_2 = df.loc[n2, "bid price"]

            # Exhausted all pairs
            except StopIteration:
                is_complete = True
                continue

            # Max loss (min_pl) and max gain (max_pl) from strategy
            min_pl = bid_2 - ask_1
            max_pl = (strike_2 - strike_1) + min_pl

            pl_x = np.array([self.calc_pair_pl(strike_1, strike_2, min_pl, max_pl, n) for n in input_dict["pdf_x"]])

            # Integrate
            weighted_integral = np.sum(pl_x * input_dict["pdf_y"] * input_dict["bin_width"])

            score = round(weighted_integral / input_dict["days_to_exp"], 6)

            temp_list = [input_dict["date"], input_dict["exp_date"], input_dict["days_to_exp"],
                         strike_1, strike_2,
                         round(min_pl, 5), score]

            # If option pair is risk-free
            if min_pl >= 0:
                output_list2.append(temp_list)
            # If not risk-free, only consider if profitability > threshold
            elif score >= self.threshold:
                output_list1.append(temp_list)

        # List to Dataframe
        col_names = ["date", "expiration date", "days to exp",
                     "strike 1", "strike 2", "min pl", "score"]

        output_df1 = pd.DataFrame(output_list1, columns=col_names)
        output_df2 = pd.DataFrame(output_list2, columns=col_names)

        # Top `self.max_num_scores` for non risk-free
        output_df1 = output_df1.sort_values(by=["score", "min pl"],
                                            ascending=False).reset_index(drop=True).iloc[:self.max_num_scores]
        # Take all for risk-free
        output_df2 = output_df2.sort_values(by=["score", "min pl"],
                                            ascending=False).reset_index(drop=True)

        return {"with risk": output_df1, "no risk": output_df2}

    @staticmethod
    def calc_pair_pl(strike_1, strike_2, min_pl, max_pl, x):
        """
        Calculate the profit / loss at expiry price `x`

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

    def calc_cumul_date_roi(self):
        """
        Group by data date to calculate cumulative book, realized return and ROI

        :return: metric_df
        """

        # Sum all realized returns for each exp date (i.e. the bulk payout dates)
        returns_df = self.pl_df.groupby("expiration date")["realized return"].sum().reset_index().rename(
            columns={"expiration date": "date"})

        # Book cost of 1 regardless of data date
        book_df = pd.DataFrame({"date": sorted(set(self.pl_df["date"])), "book": 1})

        metric_df = returns_df.merge(
            book_df, on="date", how="outer").sort_values(
            by="date", ignore_index=True).fillna(
            value=0
        )

        metric_df[["cumulative return", "cumulative book"]] = metric_df[["realized return", "book"]].cumsum()

        metric_df["cumulative ROI %"] = ((metric_df["cumulative return"] - metric_df["cumulative book"]) * 100 /
                                         metric_df["cumulative book"]).round(2)

        return metric_df

    def calc_exp_date_roi(self):
        """
        Group by expiration date to get total book and weighted average annum ROI

        :return: metric_df
        """

        temp_df = self.pl_df[["expiration date", "book", "annum ROI"]].copy()

        book_exp_date_df = self.pl_df.groupby("expiration date")["book"].sum().reset_index().rename(
            columns={"book": "book sum exp date"})

        temp_df = temp_df.merge(book_exp_date_df, on="expiration date", how="left", validate="m:1")

        # Weighted annualized ROI by book cost contribution
        temp_df["weighted annum ROI"] = (temp_df["book"] / temp_df["book sum exp date"]) * temp_df["annum ROI"]

        metric_df = temp_df.groupby("expiration date")["weighted annum ROI"].sum().reset_index().rename(
            columns={"weighted annum ROI": "average annum ROI"})

        metric_df = metric_df.merge(book_exp_date_df, on="expiration date", how="left", validate="1:1")

        return metric_df
