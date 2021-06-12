import pandas as pd
from fredapi import Fred
from pathlib import Path
import os
import numpy as np

# Assumes that API key has been saved to env variable `FRED_API_KEY`
fred = Fred()
save_path = "data/treasury_yields/"
num_days_year = 253

# Ensure working directory path is correct
if os.getcwd()[-3:] == "src":
    os.chdir(os.path.dirname(os.getcwd()))
else:
    pass
# Create data directory if it doesn't exist
Path(save_path).mkdir(exist_ok=True)

# Tickers
# 1 Year - `DGS1`
# 2 Year - `DGS2`
# 3 Year - `DGS3`
# 1 Month - `DGS1MO`
# 3 Months - `DGS3MO`
# 6 Months - `DGS6MO`
# 5 Year TIPS - `DFII5`
# 5 Year Breakeven - `T5YIE`

# Add/remove tickers as needed
tickers_dict = {"DGS1": ["1_Year", 1], "DGS2": ["2_Year", 1 / 2], "DGS3": ["3_Year", 1 / 3],
                "DGS1MO": ["1_Month", 12], "DGS3MO": ["3_Month", 4], "DGS6MO": ["6_Month", 2],
                "DFII5": ["TIPS_5_Year", 1 / 5]}

for my_ticker in tickers_dict:
    # Name and ratio for iteration
    my_name = tickers_dict.get(my_ticker)[0]
    my_ratio = tickers_dict.get(my_ticker)[1]
    # Scrape
    my_data = fred.get_series(my_ticker)
    # Wrangle
    my_data = pd.DataFrame(my_data).dropna(axis=0).reset_index()
    my_data.rename(columns={"index": "date",
                            0: "linear annual rate"},
                   inplace=True)
    my_data["date"] = pd.to_datetime(my_data["date"]).dt.date
    # From percent to ratio
    my_data["linear annual rate"] = (my_data["linear annual rate"] * 0.01).round(9)
    # daily rate by linear interpolation
    my_data["linear daily rate"] = (my_data["linear annual rate"] / num_days_year).round(9)
    # daily rate by continuous compounding
    my_data["continuous daily rate"] = ((my_ratio / num_days_year) *
                                        np.log(1 + (my_data["linear annual rate"] / my_ratio))).round(9)
    my_data.drop(columns=["linear annual rate"], inplace=True)

    # See if data already exists
    try:
        old_data = pd.read_csv(os.path.abspath(os.path.join(save_path, f"{my_name}.csv")))
        print(f"Older version of {my_name} data found!")
        old_data["date"] = pd.to_datetime(old_data["date"]).dt.date
        my_data = my_data.merge(old_data, how="outer",
                                on=["date", "linear daily rate", "continuous daily rate"])
        if my_data.shape[0] > len(np.unique(my_data["date"])):
            raise Exception("Inconsistency between old and new data!")
    except FileNotFoundError:
        print(f"No local copy of {my_name} data found!")

    # Save data
    my_data.to_csv(os.path.abspath(os.path.join(save_path, f"{my_name}.csv")),
                   index=False)
    print(f"{my_name} data saved!")

# Breakeven rates
my_ticker = "T5YIE"
my_name = "Breakeven_5_Year"
my_data = fred.get_series(my_ticker)
# Wrangle
my_data = pd.DataFrame(my_data).dropna(axis=0).reset_index()
my_data.rename(columns={"index": "date",
                        0: "annual breakeven rate"},
               inplace=True)
my_data["date"] = pd.to_datetime(my_data["date"]).dt.date
# From percent to ratio
my_data["annual breakeven rate"] = (my_data["annual breakeven rate"] * 0.01).round(9)

try:
    old_data = pd.read_csv(os.path.abspath(os.path.join(save_path, f"{my_name}.csv")))
    print(f"Older version of {my_name} data found!")
    old_data["date"] = pd.to_datetime(old_data["date"]).dt.date
    my_data = my_data.merge(old_data, how="outer",
                            on=["date", "annual breakeven rate"])
    if my_data.shape[0] > len(np.unique(my_data["date"])):
        raise Exception("Inconsistency between old and new data!")
except FileNotFoundError:
    print(f"No local copy of {my_name} data found!")

my_data.to_csv(os.path.abspath(os.path.join(save_path, f"{my_name}.csv")),
               index=False)
print(f"{my_name} data saved!")
