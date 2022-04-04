# Options Project

## Description

**Goal:** Use Greeks and sentiment features derived from option spreads to predict a stock's future price range.

[Alpha Vantage](https://www.alphavantage.co), [Questrade API](https://www.questrade.com/api),
and [FRED](https://fred.stlouisfed.org/categories/115) are used to retrieve historical stock prices, current stock
prices, and treasury yields (respectively).

Users need to generate their own API keys. "Premium" Alpha Vantage key required to get split information.

## Overview

- **[Step 1: Closing price, splits and
  dividends](https://github.com/jacktan1/Options-Project/blob/master/src/0_adj_close_and_dividends.py)**
    - Retrieve historical closing prices
    - Adjust for splits
    - Estimate dividend time series


- **[Step 2: Treasury Yields](https://github.com/jacktan1/Options-Project/blob/master/src/1_treasury_yields.py)**
    - Retrieve market yields on constant maturity securities
    - Convert linearly interpolated interest rates to continuous rates


- **[Step 3: Preprocess Options](https://github.com/jacktan1/Options-Project/blob/master/src/2_preprocess_options.py)**
    - Filter options data for specified ticker
    - Remove errors caused by stock splits
    - Adjust options by split factors
    - Attach dividend and closing prices on data/exp date(s)


- **[Step 4: Engineer Features](https://github.com/jacktan1/Options-Project/blob/master/src/3_model_features.py)**
    - **4.1 - Greeks**
        - Calculate Greeks from clean option spread 
        - Parameterization of **[Delta](https://github.com/jacktan1/Options-Project/blob/master/src/greeks/delta.py)** curves 
            - For each of call and put, we have: "skew", in-the-money (ITM) spread, out-of-the-money (OTM) spread 
            - Interpolation at 1, 2, 3, 6 and 12 months constant maturity
        - **[VIX](https://github.com/jacktan1/Options-Project/blob/master/src/greeks/vix.py)**
            - Modified stock-specific VIX calculation based on [CBOE VIX](https://cdn.cboe.com/resources/vix/vixwhite.pdf#page=4)
            - Parameterization
                - Call VIX, put VIX
                - Interpolation at 1, 2, 3, 6 and 12 months constant maturity
        - **[Gamma](https://github.com/jacktan1/Options-Project/blob/master/src/greeks/gamma.py)**
            - No parameterization yet (future)
        - **Theta** (future)
    
    - **4.2 - [Custom Features](https://github.com/jacktan1/Options-Project/blob/master/src/custom_features/custom_features.py)**
      - Use daily change in open interest ([methodology - EDA](https://github.com/jacktan1/Options-Project/blob/master/src/EDA_1.ipynb)) and volume to parameterize option spreads via linear regression
        - Call spread, put spread
        - Years until expiry vs. adjusted moneyness ratio (7 models)

    
- **[Step 5: Fit Models](https://github.com/jacktan1/Options-Project/blob/master/src/4_train_model.ipynb)**
    - Detrend target variable to be stationary (ARIMA, Augmented Dickey-Fuller)
    - XGBoost (currently on this)


- **Step 6: Create Strategies**
    - not done

