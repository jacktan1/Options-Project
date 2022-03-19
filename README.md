# Options Project

## Description

**Goal:** Use Greeks and sentiment features derived from option spreads to predict a stock's future price range.

[Alpha Vantage](https://www.alphavantage.co), [Questrade API](https://www.questrade.com/api),
and [FRED](https://fred.stlouisfed.org/categories/115) are used to retrieve historical stock prices, current stock
prices, and treasury yields (respectively).

User needs to generate their own API keys. "Premium" Alpha Vantage key required to get split information.

## Overview

- [**Step 1: Closing price, splits and
  dividends**](https://github.com/jacktan1/Options-Project/blob/master/src/0_adj_close_and_dividends.py):
    - Retrieve historical closing prices
    - Adjust for splits
    - Estimate dividend time series


- [**Step 2: Treasury Yields**](https://github.com/jacktan1/Options-Project/blob/master/src/1_treasury_yields.py):
    - Retrieve market yields on constant maturity securities
    - Convert linearly interpolated interest rates to continuous rates


- [**Step 3: Preprocess Options**](https://github.com/jacktan1/Options-Project/blob/master/src/2_preprocess_options.py):
    - Filter options data for specified ticker
    - Remove errors caused by stock splits
    - Adjust options by split factors
    - Attach dividend and closing prices on data/exp date(s)


- [**Step 4: Greeks**](https://github.com/jacktan1/Options-Project/blob/master/src/3_greeks.py):
    - Calculate Delta, Gamma, and custom VIX from clean option spread
    - Theta (not done)


- [**Step 5: Additional Features**](https://github.com/jacktan1/Options-Project/blob/master/src/EDA_1.ipynb):
    - Comparison of change in open interest vs. volume
    - Features generated via fitting linear regression (not done)


- **Step 6: Fit Models**
    - Detrend target variable to be stationary (ARIMA, Augmented Dickey-Fuller)
    - XGBoost (not done)


- **Step 7: Create Strategies**
    - not done

