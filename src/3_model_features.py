from custom_features import CalcCustomInputs
from greeks import CalcDelta, CalcGamma, CalcVix
from logger import initialize_logger
import multiprocessing
from multiprocessing.pool import Pool
import numpy as np
import os
import pandas as pd
from pathlib import Path
import time

# For a given ticker, this script does:
#   1. Calculate Deltas for all [data date, expiration date] call / put option spreads
#       - Parameterize each call / put Delta "curve" via 3 parameters & interpolate parameters based on
#      expiration dates at 1, 2, 3, 6 and 12 months constant maturity
#           - Skew (when Delta == 0.5)
#           - ITM spread (width of first ITM quartile)
#           - OTM spread (width of first OTM quartile)
#   2. Calculate Gammas based on Deltas (parameterization to be done)
#   3. Calculate VIX (modified version of https://cdn.cboe.com/resources/vix/vixwhite.pdf#page=4) for all
#      [data date, expiration date] call / put option spreads
#       - Interpolate each call / put VIX value based on expiration dates at 1, 2, 3, 6 and 12 months constant maturity
#   4. Calculate custom features using linear regression
#       - Years until expiry (YTE) vs. adjusted moneyness ratio (7 models using different weights etc.)


if __name__ == "__main__":
    # Ensure working directory path is correct
    while os.path.split(os.getcwd())[-1] != "Options-Project":
        os.chdir(os.path.dirname(os.getcwd()))

    # Select ticker
    ticker = str(input("Ticker to generate model input features: ")).upper()
    print(f"Selected: {ticker}")

    # User defined parameters
    num_days_year = 260
    # Delta thresholds used to characterize the Delta curve
    delta_abs_higher_threshold = 0.75
    delta_abs_lower_threshold = 0.25
    delta_abs_reference = 0.5

    adj_options_path = f"data/adj_options/{ticker}"
    interest_rate_path = f"data/treasury_yields"
    save_dir = f"data/model_params/"

    Path(save_dir).mkdir(parents=True, exist_ok=True)

    # Assert adj options exist
    assert len(os.listdir(adj_options_path)) > 0, \
        f"Adjusted (clean) options for {ticker} do not exist! Preprocess first!"

    # Setup
    logger = initialize_logger(logger_name="Greeks", save_dir=save_dir,
                               file_name=f"{ticker}.log")
    my_pool = Pool(multiprocessing.cpu_count())
    output_list = []

    #
    # Read options and interest rates
    #

    start_time = time.time()
    options_input_list = []
    rates_dict = dict()

    # Options
    for year in next(os.walk(adj_options_path))[1]:
        year_df = pd.DataFrame()
        for file in os.listdir(os.path.join(adj_options_path, year)):
            if file.split("_")[-1] in ["complete.csv", "incomplete.csv"]:
                # Load
                file_df = pd.read_csv(os.path.join(adj_options_path, year, file))

                # Convert columns to correct format
                file_df["date"] = pd.to_datetime(file_df["date"]).dt.date
                file_df["expiration date"] = pd.to_datetime(file_df["expiration date"]).dt.date

                year_df = pd.concat([year_df, file_df])

        # All options for given year
        year_df.sort_values(by=["date", "expiration date", "strike price", "tag"], inplace=True, ignore_index=True)

        # Required by all Greeks for constant maturity interpolation
        year_df["years to exp"] = np.busday_count(list(year_df["date"]),
                                                  list(year_df["expiration date"])) / num_days_year

        options_input_list.append({"df": year_df, "year": int(year)})

    # Interest rates
    for filename in next(os.walk(interest_rate_path))[2]:
        if filename.split(".")[-1] == "csv":

            filename_short = filename.split(".")[0]

            if filename_short == "1_Month":
                ratio = round(1 / 12, 8)
            elif filename_short == "3_Month":
                ratio = 1 / 4
            elif filename_short == "6_Month":
                ratio = 1 / 2
            elif filename_short == "1_Year":
                ratio = 1
            elif filename_short == "2_Year":
                ratio = 2
            elif filename_short == "3_Year":
                ratio = 3
            elif filename_short == "5_Year":
                ratio = 5
            else:
                continue

            rate_df = pd.read_csv(os.path.join(interest_rate_path, filename))

            # Convert columns to correct format
            rate_df["date"] = pd.to_datetime(rate_df["date"]).dt.date

            rates_dict[ratio] = rate_df

    logger.info(f"Read adj options & interest rates - {round(time.time() - start_time, 2)} seconds")

    #
    # Delta
    #

    start_time = time.time()
    delta_initialize_dict = {"abs_reference_threshold": delta_abs_reference,
                             "abs_lower_threshold": delta_abs_lower_threshold,
                             "abs_higher_threshold": delta_abs_higher_threshold}

    calculate_delta = CalcDelta(delta_initialize_dict)
    Delta_list = my_pool.map(calculate_delta.run, options_input_list)
    output_list.append(Delta_list)

    logger.info(f"Calculate Delta - {round(time.time() - start_time, 2)} seconds")

    #
    # Gamma
    #

    start_time = time.time()

    calculate_gamma = CalcGamma()
    Gamma_list = my_pool.map(calculate_gamma.run, Delta_list)
    output_list.append(Gamma_list)

    logger.info(f"Calculate Gamma - {round(time.time() - start_time, 2)} seconds")

    #
    # VIX
    #

    start_time = time.time()
    vix_initialize_dict = {"rates_dict": rates_dict}

    calculate_vix = CalcVix(vix_initialize_dict)
    vix_list = my_pool.map(calculate_vix.run, options_input_list)
    output_list.append(vix_list)

    logger.info(f"Calculate VIX - {round(time.time() - start_time, 2)} seconds")

    #
    # Custom features
    #

    start_time = time.time()

    calculate_custom = CalcCustomInputs()
    # Group options into (date_0, date_1), (date_1, date_2), ... (date_n-1, date_n)
    pairs_list = calculate_custom.group_date_pairs(options_input_list)
    # Calculate change in open interest & fit linear models
    custom_feat_list = my_pool.map(calculate_custom.run, pairs_list)
    # Group day into year
    output_list.append(calculate_custom.group_by_year([n["df"] for n in custom_feat_list]))

    logger.info(f"Calculate custom features - {round(time.time() - start_time, 2)} seconds")

    #
    # Log messages & save data
    #

    start_time = time.time()

    # Log messages
    for metric in output_list:
        for year_dict in metric:
            if "output_msg" in year_dict.keys():
                # Log messages if any
                [logger.info(my_message) for my_message in year_dict["output_msg"]]

    for date_dict in custom_feat_list:
        [logger.info(my_message) for my_message in date_dict["output_msg"]]

    # Save parameters
    for metric in output_list:
        for year_dict in metric:
            metric_type = year_dict["name"]

            Path(os.path.join(save_dir, metric_type, ticker)).mkdir(parents=True, exist_ok=True)

            for n in ["full df", "param df"]:
                if n in year_dict.keys():
                    year_dict[n].to_csv(
                        path_or_buf=os.path.join(save_dir, metric_type, ticker,
                                                 f"{ticker}_{year_dict['year']}_{metric_type}_{n.split()[0]}.csv"),
                        index=False)

    logger.info(f"Log messages & save data - {round(time.time() - start_time, 2)} seconds")
