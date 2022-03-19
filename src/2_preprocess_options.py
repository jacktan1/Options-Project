from logger import initialize_logger
import os
import pandas as pd
from pathlib import Path
from preprocess_functions import read_and_format, remove_split_error_options, adjust_options, \
    attach_dividends, attach_eod_prices, save_by_year
import time

# For a given ticker, this script does:
#   1. Read & filter all data for relevant options, remove duplicates if present.
#   2. Remove error options propagated by splits.
#   3. Adjust features by cumulative split (e.g. strike price, open interest, etc.)
#   4. Attach priced in dividends for data & expiration dates. Correct error expiration dates.
#   5. Attach end of day price for data & expiration dates. Group options into complete & incomplete.
#   6. Aggregate complete, incomplete, and error options by year and write to disk.


if __name__ == "__main__":
    # Ensure working directory path is correct
    while os.path.split(os.getcwd())[-1] != "Options-Project":
        os.chdir(os.path.dirname(os.getcwd()))

    # User defined parameters
    ticker = str(input("Ticker to aggregate option data: ")).upper()
    print(f"Selected: {ticker}")

    option_data_path = "data/options_data/"
    stock_data_path = f"data/adj_close/{ticker}/{ticker}.csv"
    dividends_data_path = f"data/dividends/{ticker}/{ticker}_ts.csv"
    save_path = f"data/adj_options/{ticker}/"

    # Create save directory if not present
    Path(save_path).mkdir(parents=True, exist_ok=True)

    # Time script
    start_time = time.time()

    # Set up logger
    logger = initialize_logger(logger_name="preprocess", save_path=save_path,
                               file_name="process.log")

    # Load end of day prices
    try:
        hist_closing_df = pd.read_csv(os.path.abspath(stock_data_path))
        hist_closing_df["date"] = pd.to_datetime(hist_closing_df["date"]).dt.date
    except FileNotFoundError:
        raise SystemExit(f"Security history for {ticker} not found in path: {os.path.abspath(stock_data_path)}")

    # Load dividend data
    try:
        dividends_df = pd.read_csv(os.path.abspath(dividends_data_path))
        dividends_df["date"] = pd.to_datetime(dividends_df["date"]).dt.date
    except FileNotFoundError:
        raise SystemExit(f"Dividend data for {ticker} not found in path: {os.path.abspath(dividends_data_path)}")

    # 1
    options_dict_1 = read_and_format(ticker=ticker,
                                     option_data_path=option_data_path,
                                     logger=logger)

    # 2
    options_dict_2 = remove_split_error_options(options_dict=options_dict_1,
                                                hist_closing_df=hist_closing_df,
                                                logger=logger)

    # 3
    adjust_options_dict = adjust_options(options_dict=options_dict_2,
                                         hist_closing_df=hist_closing_df,
                                         logger=logger)

    options_dict_3 = adjust_options_dict["adj dict"]

    errors_dict = adjust_options_dict["errors dict"]

    # 4
    options_dict_4 = attach_dividends(options_dict=options_dict_3,
                                      dividends_df=dividends_df,
                                      logger=logger)

    # 5
    options_dict_5 = attach_eod_prices(options_dict=options_dict_4,
                                       hist_closing_df=hist_closing_df,
                                       logger=logger)

    complete_options_dict = options_dict_5["complete dict"]

    incomplete_options_dict = options_dict_5["incomplete dict"]

    # 6
    save_by_year(complete_dict=complete_options_dict,
                 incomplete_dict=incomplete_options_dict,
                 errors_dict=errors_dict,
                 ticker=ticker,
                 save_path=save_path,
                 logger=logger)

    logger.info(f"Processed {ticker} options data! - Took {round(time.time() - start_time, 2)} seconds!")
