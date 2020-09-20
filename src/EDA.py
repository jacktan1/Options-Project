import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    options_df = pd.read_csv(os.path.abspath(os.path.join(option_data_path, stock_of_interest)) + ".csv")
    options_df["date"] = pd.to_datetime(options_df["date"]).dt.date
    options_df["expiration date"] = pd.to_datetime(options_df["expiration date"]).dt.date
except FileNotFoundError:
    raise SystemExit("Option data for " + stock_of_interest + " not found in path: " +
                     os.path.abspath(os.path.join(option_data_path, stock_of_interest)) + ".csv")

try:
    my_stock_df = pd.read_csv(os.path.abspath(os.path.join(stock_data_path, stock_of_interest)) + ".csv")
    my_stock_df["date"] = pd.to_datetime(my_stock_df["date"]).dt.date
except FileNotFoundError:
    raise SystemExit("Daily closing price data for " + stock_of_interest + " not found in path: " +
                     os.path.abspath(os.path.join(stock_data_path, stock_of_interest)) + ".csv")

# Bid price of 0 suggests no interest/price unknown
options_df = options_df[options_df["bid price"] != 0].reset_index(drop=True)

options_df["adj closing"] = options_df["closing price"] - options_df["date div"]
options_df["adj strike"] = options_df["strike price"] - options_df["exp date div"]
options_df["adj exp closing"] = options_df["exp date closing price"] - options_df["exp date div"]
options_df["days till exp"] = np.busday_count(begindates=options_df["date"],
                                              enddates=options_df["expiration date"])
options_df = options_df.drop(columns=["date div", "exp date div"])

# Splitting into call and put DataFrames
calls_df = options_df[options_df["type"] == "call"].copy()
puts_df = options_df[options_df["type"] == "put"].copy()

# Breakeven prices for call/put options
calls_df["adj exp breakeven"] = calls_df["adj strike"] + calls_df["bid price"]
puts_df["adj breakeven"] = puts_df["adj strike"] - puts_df["bid price"]

# Identify options that are inherently not plausible. (Ones where buyer can profit by exercising upon purchase)
calls_df1 = calls_df[(calls_df["strike price"] + calls_df["bid price"]) < calls_df["closing price"]]
puts_df1 = puts_df[(puts_df["strike price"] - puts_df["bid price"]) > puts_df["adj closing"]]

options_df = calls_df.append(puts_df).sort_values(by=["date", "expiration date"]).reset_index(
    drop=True)

fig = go.Figure(data=go.Scatter(x=options_df["normalized strike"],
                                y=options_df["normalized bid"],
                                mode="markers"))

fig.update_layout(
    title=dict(text="<b>Normalized Option Strike Vs. Normalized Bid<b>",
               font=dict(size=30)),
    xaxis_title=dict(text="<b>Normalized Strike<b>",
                     font=dict(size=30)),
    yaxis_title=dict(text="<b>Normalized Bid<b>",
                     font=dict(size=30)),
    font=dict(size=20)
)

fig.show()


print("hello")
