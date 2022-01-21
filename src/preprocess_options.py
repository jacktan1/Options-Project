import os
import pandas as pd
from src.preprocess_fun import adjust_option_data, add_dividends
import time


# For a given ticker, this script does the following:
#   1. Filter all data for relevant options
#   2. Adjusts relevant features for splits (e.g. strike price, open interest, etc.)
#   3. Split data into two groups
#       - options whose expiry has passed
#       - ongoing options
#   4. Attach closing prices for every option's data date (and expiry date if applicable)
#   5. Attach priced-in dividend amount for every option's data and expiry dates
#   6. Group options by year and save to separate files


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

    start_time = time.time()

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

    # Aggregate, separate and add closing prices
    options_df_list = adjust_option_data(stock_of_interest=ticker,
                                         hist_closing_df=hist_closing_df,
                                         option_data_path=option_data_path,
                                         save_path=save_path)

    # Add data and exp date dividends
    add_dividends(stock_of_interest=ticker,
                  options_df_list=options_df_list,
                  dividends_df=dividends_df,
                  save_path=save_path)

    end_time = time.time()
    print(f"Finished processing {ticker} options data! Took {round(end_time - start_time, 2)} seconds!")
