from dividends_fun import calculate_dividends
from eod_price_fun import get_current_price, get_price_history
import os
from pathlib import Path
from questrade_api import Questrade


# For a given ticker, this script does the following:
#   1. Get current price of ticker from Questrade / Alpha Vantage
#   2. Get historical end of day prices from Alpha Vantage
#   3. Obtain dividend data from Alpha Vantage and infer priced in dividend time series


# Ensure working directory path is correct
if os.getcwd()[-3:] == "src":
    os.chdir(os.path.dirname(os.getcwd()))
else:
    pass

# User defined parameters
ticker = str(input("Ticker to scrape: ")).upper()
print(f"Selected: {ticker}")

alphaVan_token = os.environ["ALPHAVANTAGE_KEY"]
# Number of days NYSE is open per year
num_days_year = 252
# How many days into future to predict dividends
num_days_future = 3 * 365
adjusted_closing_save_path = "data/adjusted_daily_closing/"
dividend_save_path = "data/dividends/"
q = Questrade()

# Initializing Questrade Connection
try:
    current_time = q.time
    print("Questrade API working successfully!")
except AttributeError:
    my_token = str(input("Login key has expired! New refresh token from Questrade: "))
    q = Questrade(refresh_token=my_token)
    current_time = q.time
    if not current_time:
        raise Exception("Questrade API not working properly!")
    else:
        print("New Questrade token saved to home directory!")

# Get current price
price = get_current_price(ticker=ticker,
                          questrade_instance=q,
                          api_key=alphaVan_token)

# Get historical closing prices
hist_closing_df = get_price_history(ticker=ticker,
                                    api_key=alphaVan_token,
                                    save_path=adjusted_closing_save_path)

div_dict = calculate_dividends(ticker=ticker,
                               api_key=alphaVan_token,
                               hist_closing_df=hist_closing_df,
                               num_days_future=num_days_future)

# Save dividend events and time series
Path(dividend_save_path).mkdir(exist_ok=True)

div_dict["events"].to_csv(path_or_buf=os.path.join(dividend_save_path, f"{ticker}.csv"), index=False)
div_dict["ts"].to_csv(path_or_buf=os.path.join(dividend_save_path, f"{ticker}_ts.csv"), index=False)

print('Done!')
