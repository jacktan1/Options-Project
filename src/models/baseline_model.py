import numpy as np
from scipy.stats import gaussian_kde
from sklearn.model_selection import train_test_split


class BaselineModel:
    def __init__(self, sub_model_lags, train_test_ratio, kernel_resolution):

        self.sub_model_lags = sub_model_lags

        self.num_bins = kernel_resolution

        self.train_test_ratio = train_test_ratio

        self.sub_models = dict()

        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None

        self.pred_train = None
        self.pred_test = None

        self.test_na_count = dict()

        self.test_pdf = dict()
        self.test_na = dict()

    def train_test_split(self, input_df):

        input_df = input_df[["date", "adj_close"]].copy()

        # Generate dependent variables (y)
        for n in self.sub_model_lags:
            input_df[f"{n}_actual"] = input_df["adj_close"].shift(periods=-n)

        input_df.dropna(inplace=True)

        self.X_train, self.X_test, self.y_train, self.y_test = \
            train_test_split(input_df[["date", "adj_close"]],
                             input_df[[f"{lag}_actual" for lag in self.sub_model_lags]],
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

            self.sub_models[n] = {"kernel": my_kernel,
                                  "min": kernel_min,
                                  "max": kernel_max}

    def predict_test(self):
        """
        Naive model predicts the same regardless sub model

        :return: None
        """
        self.pred_test = self.X_test.copy()

        # Naive predictor is just the EOD price
        self.pred_test.rename(columns={"adj_close": "prediction"}, inplace=True)

    def generate_test_pdf(self):
        """
        Generate PDF given prediction for all sub models

        TODO: Allow for dynamic selection of prediction range instead of fixed at min/max of training dependent variable

        :return: None
        """

        for model in self.sub_models.keys():
            kde = self.sub_models[model]["kernel"]

            pred_min = self.sub_models[model]["min"]

            pred_max = self.sub_models[model]["max"]

            pred_range = np.linspace(pred_min, pred_max, num=self.num_bins)

            # Width of each PDF block
            bin_width = (pred_max - pred_min) / (len(pred_range) - 1)

            # Generate PDF for each test date
            for m in range(self.pred_test.shape[0]):

                date = self.pred_test.iloc[m]["date"]

                # Prediction is the same regardless of model in this case
                pred = self.pred_test.iloc[m]["prediction"]
                actual = self.y_test.iloc[m][f"{model}_actual"]

                pred_list = [[pred, y] for y in pred_range]

                pred_2d_pdf = kde.evaluate(np.transpose(pred_list))

                pdf_sum = np.sum(pred_2d_pdf)

                # This case to be removed
                if np.isclose(pdf_sum, 0):

                    if model not in self.test_na_count.keys():
                        self.test_na_count[model] = 0

                    self.test_na_count[model] += 1

                    # _________

                    if date not in self.test_na.keys():
                        self.test_na[date] = dict()

                    self.test_na[date][model] = {"prediction": pred, "actual": actual}

                else:
                    # Need to scale the pdf from 2-dimensional to 1-dimensional for slice
                    scale_factor = 1 / (bin_width * pdf_sum)

                    pred_1d_pdf = pred_2d_pdf * scale_factor

                    if date not in self.test_pdf.keys():
                        self.test_pdf[date] = dict()

                    self.test_pdf[date][model] = {"prediction": pred, "actual": actual,
                                                  "range": pred_range, "pdf": pred_1d_pdf}
