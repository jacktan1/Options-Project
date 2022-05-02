from adj_close_and_dividend_functions import get_current_price, get_price_history, calculate_dividends
from logger import initialize_logger
import os
from pathlib import Path
from questrade_api import Questrade
import sys
import time
import urllib

if __name__ == "__main__":
    # For a given ticker, this script does the following:
    #   1. Get current price of ticker from Questrade / Alpha Vantage
    #   2. Get historical end of day prices from Alpha Vantage
    #   3. Obtain dividend data from Alpha Vantage and infer priced in dividend time series

    # Ensure working directory path is correct
    while os.path.split(os.getcwd())[-1] != "Options-Project":
        os.chdir(os.path.dirname(os.getcwd()))

    # User defined parameters
    ticker = str(input("Ticker to scrape: ")).upper()
    print(f"Selected: {ticker}")
    # How many calendar days into future to predict dividends
    num_days_future = 3 * 365

    alphaVan_token = os.environ["ALPHAVANTAGE_KEY"]
    q = Questrade()

    adj_close_save_path = f"data/adj_close/{ticker}/"
    dividends_save_path = f"data/dividends/{ticker}/"

    # Create save directory if not present
    Path(adj_close_save_path).mkdir(parents=True, exist_ok=True)
    Path(dividends_save_path).mkdir(parents=True, exist_ok=True)

    # Time adj close prices
    start_time = time.time()
    adj_close_logger = initialize_logger(logger_name="adj_close",
                                         save_dir=adj_close_save_path,
                                         file_name="process.log")

    # Initializing Questrade Connection
    try:
        current_time = q.time
        adj_close_logger.info("Questrade API working successfully!")
    except (urllib.error.HTTPError, AttributeError):
        my_token = str(input("Login key has expired! New refresh token from Questrade: "))
        q = Questrade(refresh_token=my_token)
        current_time = q.time
        if not current_time:
            adj_close_logger.error("Questrade API not working properly!")
            sys.exit(1)
        else:
            adj_close_logger.info("New Questrade token saved to home directory!")

    # Get current price
    price = get_current_price(ticker=ticker,
                              questrade_instance=q,
                              api_key=alphaVan_token,
                              logger=adj_close_logger)

    # Get historical closing prices
    hist_closing_df = get_price_history(ticker=ticker,
                                        api_key=alphaVan_token,
                                        save_path=adj_close_save_path,
                                        logger=adj_close_logger)

    adj_close_logger.info(f"Processed {ticker} adjusted close - {round(time.time() - start_time, 2)} seconds")

    # Time dividends
    start_time = time.time()
    dividends_logger = initialize_logger(logger_name="dividends",
                                         save_dir=dividends_save_path,
                                         file_name="process.log")

    div_dict = calculate_dividends(ticker=ticker,
                                   api_key=alphaVan_token,
                                   hist_closing_df=hist_closing_df,
                                   num_days_future=num_days_future,
                                   save_path=dividends_save_path,
                                   logger=dividends_logger)

    dividends_logger.info(f"Processed {ticker} dividends - {round(time.time() - start_time, 2)} seconds")
