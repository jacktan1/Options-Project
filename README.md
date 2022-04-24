# Options Project

## Description

**Goal:** Use Greeks and sentiment features derived from end-of-day (EOD) option snapshots to predict payout of
different vertical spread option strategies.

[Alpha Vantage](https://www.alphavantage.co), [Questrade API](https://www.questrade.com/api),
and [FRED](https://fred.stlouisfed.org/categories/115) are used to retrieve historical stock prices, current stock
prices, and treasury yields (respectively).

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
    - **[4.1 - Greeks](https://github.com/jacktan1/Options-Project/tree/master/src/greeks)**
        - Calculate Greeks from clean option spread
        - **[Delta](https://github.com/jacktan1/Options-Project/blob/master/src/greeks/delta.py)**
            - For each of call & put, we parameterize: "skew", in-the-money (ITM) spread, out-of-the-money (OTM) spread
            - Interpolation at 1, 2, 3, 6 and 12 months constant maturity
        - **[VIX](https://github.com/jacktan1/Options-Project/blob/master/src/greeks/vix.py)**
            - Modified stock-specific VIX calculation based
              on [CBOE VIX](https://cdn.cboe.com/resources/vix/vixwhite.pdf#page=4)
            - Parameterization
                - Call & put VIXs
                - Interpolation at 1, 2, 3, 6 and 12 months constant maturity
        - **[Gamma](https://github.com/jacktan1/Options-Project/blob/master/src/greeks/gamma.py)**
            - No parameterization yet (future)
        - **Theta** (future)

    - **[4.2 - Custom Input Features](https://github.com/jacktan1/Options-Project/blob/master/src/custom_features/custom_inputs.py)**
        - Use daily change in open
          interest ([methodology - EDA](https://github.com/jacktan1/Options-Project/blob/master/EDA/EDA_1.ipynb)) and
          volume to parameterize options via linear regression
            - Years until expiry vs. adjusted moneyness ratio (7 variations on sample weights)
            - Call, put slopes and intercepts (2 parameters per variation)


- **[Step 5: Fit & Predict Models](https://github.com/jacktan1/Options-Project/blob/master/src/models)**
    - **Fit** - For each model type:
        - Fit separate sub-models that predict EOD price `[1, 5, 10, 15, 20, 40, 65, 90, 130, 260, 390, 520]` days out
        - Generate 2-dimensional probability density kernels (1 per sub-model) using multi-variate kernel density
          estimates
    - **Predict** - For each expiry date in test options data date:
        - Use the two nearest sub-model kernels and their discrete predictions to linearly interpolate a 1-dimensional
          density plot
    - **Model Types**:
        - **[Baseline model](https://github.com/jacktan1/Options-Project/blob/master/src/4-0_baseline_model.ipynb)**
            - Simply uses previous day's EOD price as predictor for target
        - Baseline model with target standardization and autoregression
        - **[XGBoost model - in progress](https://github.com/jacktan1/Options-Project/blob/master/src/4-2_xgboost_model.ipynb)**
            - De-trend target variable to be stationary (ARIMA, Augmented Dickey-Fuller)
            - XGBoost
