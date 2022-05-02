import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from scipy.stats import gaussian_kde
from sklearn.model_selection import train_test_split


class BaselineModel:
    def __init__(self, sub_model_lags, train_test_ratio, kernel_resolution):

        # User defined
        self.sub_model_lags = sub_model_lags
        self.train_test_ratio = train_test_ratio
        self.num_bins = kernel_resolution

        # Used in class methods
        self.sub_models = dict()

        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None

        self.pred_train = None
        self.pred_test = None
        self.pred_test_pdf = None

    def train_test_split(self, input_df):

        # Independent variable is only EOD price
        input_df = input_df[["date", "adj_close"]].copy()

        # Generate dependent variables (y)
        for n in self.sub_model_lags:
            input_df[f"{n}_actual"] = input_df["adj_close"].shift(periods=-n)

        input_df.dropna(inplace=True)

        # Date duplicated in both train and test for easier indexing
        self.X_train, self.X_test, self.y_train, self.y_test = \
            train_test_split(input_df[["date", "adj_close"]],
                             input_df[(["date"] + [f"{lag}_actual" for lag in self.sub_model_lags])],
                             train_size=self.train_test_ratio,
                             shuffle=False)

    def train_models(self):
        """
        Naive model predicts the same regardless sub model

        :return: None
        """
        self.pred_train = self.X_train.copy()

        # Naive predictor is just the EOD price
        self.pred_train.rename(columns={"adj_close": "prediction"}, inplace=True)

    def generate_kdes(self):
        """
        Generate KDEs for all sub-models.

        Stores min / max of training dependent variable to establish range of prediction
        for given sub model.

        :return: None
        """

        for n in self.sub_model_lags:
            # Naive predictor predicts the same regardless sub model
            pred_df = self.pred_train.copy()

            pred_df["actual"] = self.y_train[f"{n}_actual"]

            my_kernel = gaussian_kde(np.transpose(pred_df[["prediction", "actual"]].to_numpy()))

            # Min / max of prediction range
            kernel_min = np.min(pred_df["actual"])
            kernel_max = np.max(pred_df["actual"])

            # Range when predicting with this KDE
            pred_range = np.linspace(kernel_min, kernel_max, num=self.num_bins)
            # Width of each PDF block
            bin_width = (kernel_max - kernel_min) / (self.num_bins - 1)

            self.sub_models[n] = {"kernel": my_kernel,
                                  "min": kernel_min,
                                  "max": kernel_max,
                                  "pred_range": pred_range,
                                  "bin_width": bin_width}

    def plot_kde_heatmaps(self):
        """
        Create heatmaps from KDEs of all sub-models

        :return: fig (Figure)
        """
        # Variables
        all_model_keys = list(self.sub_models.keys())
        max_cols = 3
        max_rows = int(np.ceil(len(all_model_keys) / max_cols))
        row = 1
        col = 1

        fig = make_subplots(rows=max_rows, cols=max_cols,
                            vertical_spacing=0.05,
                            horizontal_spacing=0.05,
                            x_title="predict",
                            y_title="actual (target)",
                            subplot_titles=[f"sub model lag: {n}" for n in all_model_keys])

        for n in all_model_keys:
            subplot_pdfs = []

            # Prediction same regardless of sub model in this case
            x_axis = np.linspace(np.min(self.pred_train["prediction"]),
                                 np.max(self.pred_train["prediction"]), num=self.num_bins)

            y_axis = np.linspace(self.sub_models[n]["min"],
                                 self.sub_models[n]["max"], num=self.num_bins)

            for y in y_axis:
                constant_y_list = [[x, y] for x in x_axis]

                pdf_list = self.sub_models[n]["kernel"].evaluate(np.transpose(constant_y_list))

                subplot_pdfs.append(list(pdf_list))

            fig.add_trace(go.Heatmap(
                x=x_axis,
                y=y_axis,
                z=subplot_pdfs,
                colorscale='Viridis'),
                row=row, col=col)

            if not col == max_cols:
                col += 1
            else:
                row += 1
                col = 1

        return fig

    def predict_test(self):
        """
        Naive model predicts the same regardless sub model

        :return: None
        """
        # Naive predictor is just the EOD price
        self.pred_test = self.X_test.copy()

        self.pred_test.rename(columns={"adj_close": "prediction"}, inplace=True)

    def generate_test_pdf(self, options_df):
        """
        Linearly interpolate PDFs of sub-models for actual expiration dates

        TODO: Log all data dates where predictions can't be generated

        :param options_df: EOD option snapshots of test dates
        :return: None
        """

        test_pdf_list = []

        all_model_keys = list(self.sub_models.keys())

        # Date
        for date in self.pred_test["date"]:
            date_df = options_df[options_df["date"] == date]

            # All valid models for date
            date_model_keys = all_model_keys.copy()

            # Inplace filter
            date_model_keys[:] = [model_key for model_key in date_model_keys if
                                  self.test_pdf(model_key=model_key, date=date)]

            # If there are enough valid sub-models left
            if len(date_model_keys) >= 2:
                # Expiration date
                for exp_date in pd.unique(date_df["expiration date"]):
                    # Time till expiry is 0. Delta should be step function. Skip
                    if date == exp_date:
                        continue

                    days_to_exp = np.busday_count(date, exp_date)

                    # Ascending (default)
                    model_keys_order = sorted(date_model_keys, key=lambda x: np.abs(x - days_to_exp))

                    # Two closest models
                    closest_model_keys = model_keys_order[0:2]

                    pred_dict = self.interpolate_pdf(model_keys=closest_model_keys,
                                                     date=date,
                                                     days_to_exp=days_to_exp)

                    test_pdf_list.append({"date": date, "expiration date": exp_date, "days to exp": days_to_exp,
                                          **pred_dict})

        self.pred_test_pdf = pd.DataFrame(test_pdf_list)

    def test_pdf(self, model_key, date):
        """
        Test if sub-model can produce a valid PDF on date

        :param model_key: specified sub-model
        :param date: date to test
        :return: True (if can produce PDF) / False
        """

        model = self.sub_models[model_key]

        # Prediction is the same regardless of model in this case
        pred = float(self.pred_test[self.pred_test["date"] == date]["prediction"])

        pred_list = [[pred, y] for y in model["pred_range"]]

        pred_2d_pdf = model["kernel"].evaluate(np.transpose(pred_list))

        pdf_sum = np.sum(pred_2d_pdf)

        # Unable to produce PDF
        if np.isclose(pdf_sum, 0):
            return False
        else:
            return True

    def interpolate_pdf(self, model_keys, date, days_to_exp):
        """
        Linearly interpolate PDF on expiration date (days_to_exp, DOE) using the two models in model_keys

        TODO: Interpolation may result in negative pdf value (if prediction DOE is too far from the 2 model DOEs)

        :param model_keys: the two sub-models closest to expiration date
        :param date: data date
        :param days_to_exp: days until expiration date
        :return: dict {"pred": raw prediction, "pdf": PDF of prediction,
                       "range": range of PDF, "bin_width": bin width of each bar in PDF}
        """

        c_pdf = np.zeros(self.num_bins)

        key_0 = min(model_keys)
        key_1 = max(model_keys)

        # Sanity check
        assert key_1 > key_0

        model_0 = self.sub_models[key_0]
        model_1 = self.sub_models[key_1]

        # Prediction is the same regardless of model in this case
        pred_0 = float(self.pred_test[self.pred_test["date"] == date]["prediction"])
        pred_1 = float(self.pred_test[self.pred_test["date"] == date]["prediction"])

        model_0_ratio = (key_1 - days_to_exp) / (key_1 - key_0)
        model_1_ratio = (days_to_exp - key_0) / (key_1 - key_0)

        c_min = min(model_0["min"], model_1["min"])
        c_max = max(model_0["max"], model_1["max"])

        c_pred_range = np.linspace(c_min, c_max, num=self.num_bins)
        # Width of each PDF block
        c_bin_width = (c_max - c_min) / (self.num_bins - 1)

        c_pred = model_0_ratio * pred_0 + model_1_ratio * pred_1

        for n in [{"pred": pred_0, "model": model_0, "ratio": model_0_ratio},
                  {"pred": pred_1, "model": model_1, "ratio": model_1_ratio}]:
            pred_list = [[n["pred"], y] for y in c_pred_range]

            pred_2d_pdf = n["model"]["kernel"].evaluate(np.transpose(pred_list))

            # Need to scale the pdf from 2-dimensional to 1-dimensional for slice
            scale_factor = 1 / (c_bin_width * np.sum(pred_2d_pdf))

            # scaling and contribution ratio
            pred_1d_pdf = pred_2d_pdf * scale_factor * n["ratio"]

            c_pdf = c_pdf + pred_1d_pdf

        return {"prediction": c_pred, "pdf": c_pdf, "range": c_pred_range, "bin width": c_bin_width}
