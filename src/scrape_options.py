import scrape_fun
import os
import pandas as pd

# Ensure working directory path is correct
if os.getcwd()[-3:] == "src":
    os.chdir(os.path.dirname(os.getcwd()))
else:
    pass

# User defined parameters
option_data_path = "data/discount_data/"
stock_data_path = "data/adjusted_daily_closing/"
dividend_data_path = "data/dividends/"
adjusted_options_path = "data/adjusted_options/"

my_ticker = str(input("Ticker you want to aggregate option data for: ")).upper()
print("You have selected stock ticker: '" + my_ticker + "'")

# Loading in historical ticker data
try:
    history_df = pd.read_csv(os.path.abspath(os.path.join(stock_data_path, my_ticker)) + ".csv")
    history_df["date"] = pd.to_datetime(history_df["date"]).dt.date
except FileNotFoundError:
    raise SystemExit("Security history for " + my_ticker + " not found in path: " +
                     os.path.abspath(os.path.join(stock_data_path, my_ticker)) + ".csv")

# Aggregating options data for specified ticker
my_options_df = scrape_fun.hist_option_data(stock_of_interest=my_ticker,
                                            option_data_path=option_data_path,
                                            history_df=history_df)

# Fill in dividend info
scrape_fun.add_dividends(stock_of_interest=my_ticker,
                         options_df=my_options_df,
                         history_df=history_df,
                         dividends_data_path=dividend_data_path,
                         save_path=adjusted_options_path)

print("Done!")
