from greek_functions import calc_delta, calc_gamma, calc_vix
from logger import initialize_logger
import multiprocessing
from multiprocessing.pool import Pool
import os
import pandas as pd
from pathlib import Path
import time

if __name__ == "__main__":
    # Ensure working directory path is correct
    while os.path.split(os.getcwd())[-1] != "Options-Project":
        os.chdir(os.path.dirname(os.getcwd()))

    # User defined parameters
    ticker = str(input("Ticker to calculate Greeks: ")).upper()
    print(f"Selected: {ticker}")
    num_days_year = 260

    adj_options_path = f"data/adj_options/{ticker}"
    interest_rate_path = f"data/treasury_yields"
    delta_save_path = f"data/Greeks/Delta/{ticker}"
    gamma_save_path = f"data/Greeks/Gamma/{ticker}"

    # Assert adj options exist
    assert len(os.listdir(adj_options_path)) > 0, f"Adjusted options for {ticker} do not exist! Preprocess first!"

    # Create save directories if not present
    Path(delta_save_path).mkdir(parents=True, exist_ok=True)
    Path(gamma_save_path).mkdir(parents=True, exist_ok=True)

    # Set up logger
    logger = initialize_logger(logger_name="Greeks", save_path=f"data/Greeks",
                               file_name=f"{ticker}.log")

    # Set up pool
    my_pool = Pool(multiprocessing.cpu_count())

    # Initialize Variables
    input_list = []
    rates_dict = dict()
    start_time = time.time()
    
    # Read options
    # next(os.walk(adj_options_path))[1]
    for year in ["2020"]:
        year_df = pd.DataFrame()
        for file in os.listdir(os.path.join(adj_options_path, year)):
            if file.split("_")[-1] in ["complete.csv", "incomplete.csv"]:
                # Load
                file_df = pd.read_csv(os.path.join(adj_options_path, year, file))

                # Convert columns to correct format
                file_df["date"] = pd.to_datetime(file_df["date"]).dt.date
                file_df["expiration date"] = pd.to_datetime(file_df["expiration date"]).dt.date

                year_df = pd.concat([year_df, file_df])

        # Concatenated all options for given year
        year_df.sort_values(by=["date", "expiration date", "strike price", "tag"], inplace=True, ignore_index=True)

        input_list.append({"df": year_df, "year": int(year)})

    # Read interest rates
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

            df2 = pd.read_csv(os.path.join(interest_rate_path, filename))

            # Convert columns to correct format
            df2["date"] = pd.to_datetime(df2["date"]).dt.date
            
            rates_dict[ratio] = df2

    logger.info(f"Read adj options / interest rates - {round(time.time() - start_time, 2)} seconds")
    start_time = time.time()

    vix_dict = calc_vix(input_dict=input_list[0], rates_dict=rates_dict, num_days_year=num_days_year)

    logger.info(f"Calculate call/put VIX - {round(time.time() - start_time, 2)} seconds")
    start_time = time.time()

    Delta_list = my_pool.map(calc_delta, input_list)

    logger.info(f"Calculate Deltas - {round(time.time() - start_time, 2)} seconds")
    start_time = time.time()

    Gamma_list = my_pool.map(calc_gamma, Delta_list)

    logger.info(f"Calculate Gammas - {round(time.time() - start_time, 2)} seconds")
    start_time = time.time()
