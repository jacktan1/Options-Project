import pandas as pd
import numpy as np
import os

# Ensure working directory path is correct
if os.getcwd()[-3:] == "src":
    os.chdir(os.path.dirname(os.getcwd()))
else:
    pass

# User defined parameters
stock_of_interest = "CVX"
option_data_path = "data/adjusted_options/"
stock_data_path = "data/adjusted_daily_closing/"

# Loading necessary files
try:
    my_options_df = pd.read_csv(os.path.abspath(os.path.join(option_data_path, stock_of_interest)) + ".csv")
    my_options_df["date"] = pd.to_datetime(my_options_df["date"])
    my_options_df["expiration date"] = pd.to_datetime(my_options_df["expiration date"])
except FileNotFoundError:
    raise SystemExit("Option data for " + stock_of_interest + " not found in path: " +
                     os.path.abspath(os.path.join(option_data_path, stock_of_interest)) + ".csv")

try:
    my_stock_df = pd.read_csv(os.path.abspath(os.path.join(stock_data_path, stock_of_interest)) + ".csv")
    my_stock_df["date"] = pd.to_datetime(my_stock_df["date"])
except FileNotFoundError:
    raise SystemExit("Daily closing price data for " + stock_of_interest + " not found in path: " +
                     os.path.abspath(os.path.join(stock_data_path, stock_of_interest)) + ".csv")


# Bid price of 0 suggests no interest/price unknown
my_options_df = my_options_df[my_options_df["bid price"] != 0].reset_index(drop=True)


print("hello")
