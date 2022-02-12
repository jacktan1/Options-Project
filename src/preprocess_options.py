import logging
import os
import pandas as pd
from pathlib import Path
from src import preprocess_fun as pre
import sys
import time

# For a given ticker, this script does:
#   1. Read & filter all data for relevant options, remove duplicates if present.
#   2. Remove error options propagated by splits.
#   3. Adjust features by cumulative split (e.g. strike price, open interest, etc.)
#   4. Attach priced in dividends for data & expiration dates. Correct error expiration dates.
#   5. Attach end of day price for data & expiration dates. Group options into complete & incomplete.
#   6. Aggregate complete, incomplete, and error options by year and write to disk.


if __name__ == '__main__':
    # Ensure working directory path is correct
    if os.getcwd()[-3:] == "src":
        os.chdir(os.path.dirname(os.getcwd()))
    else:
        pass

    # User defined parameters
    ticker = str(input("Ticker to aggregate option data: ")).upper()
    print(f"Selected: {ticker}")

    option_data_path = "data/options_data/"
    stock_data_path = f"data/adjusted_daily_closing/{ticker}.csv"
    dividends_data_path = f"data/dividends/{ticker}_ts.csv"
    save_path = f"data/adjusted_options/{ticker}/"

    # Create save directory if not present
    Path(save_path).mkdir(parents=True, exist_ok=True)

    # Time script
    start_time = time.time()

    # Set up logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(filename=os.path.join(save_path, "preprocess.log"), mode="w")
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.INFO)
    log_format = logging.Formatter("%(levelname)s - %(message)s")

    fh.setFormatter(log_format)
    ch.setFormatter(log_format)

    logger.addHandler(fh)
    logger.addHandler(ch)

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
    options_dict_1 = pre.read_and_format(ticker=ticker,
                                         option_data_path=option_data_path,
                                         logger=logger)

    # 2
    options_dict_2 = pre.remove_split_error_options(options_dict=options_dict_1,
                                                    hist_closing_df=hist_closing_df,
                                                    logger=logger)

    # 3
    adjust_options_dict = pre.adjust_options(options_dict=options_dict_2,
                                             hist_closing_df=hist_closing_df,
                                             logger=logger)

    options_dict_3 = adjust_options_dict["adj dict"]

    errors_dict = adjust_options_dict["errors dict"]

    # 4
    options_dict_4 = pre.attach_dividends(options_dict=options_dict_3,
                                          dividends_df=dividends_df,
                                          logger=logger)

    # 5
    options_dict_5 = pre.attach_eod_prices(options_dict=options_dict_4,
                                           hist_closing_df=hist_closing_df,
                                           logger=logger)

    complete_options_dict = options_dict_5["complete dict"]

    incomplete_options_dict = options_dict_5["incomplete dict"]

    # 6
    pre.save_by_year(complete_dict=complete_options_dict,
                     incomplete_dict=incomplete_options_dict,
                     errors_dict=errors_dict,
                     ticker=ticker,
                     save_path=save_path,
                     logger=logger)

    logger.info(f"Processed {ticker} options data! - {round(time.time() - start_time, 2)} seconds total!")
