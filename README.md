# Options Project

## Description
We aim to use historical option and stock prices to create and evaluate the performance of various models. Historical and current stock prices for a given ticker are pulled from [Alpha Vantage](https://www.alphavantage.co/) and [Questrade API](https://www.questrade.com/api), respectively. Current option prices also come from Questrade. Historical option prices, were obtained from [Discount Option Data]( https://discountoptiondata.com/). Currently, I am only using option data from 2016, as most options from then have now expired (to maximize training data).

## Overview

- [**scrape_and_preprocess**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_and_preprocess.py): 
    - Retrieve historical closing prices using Alpha Vantage.
    - Adjust for splits and estimates dividend contribution.

- [**scrape_options**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_options.py):
    - Filter options data for specified ticker and append dividend data.

- [**greeks**](https://github.com/jacktan1/Options-Project/blob/master/src/greeks.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/greeks.ipynb) if GitHub is unable to load)
    - Derive Delta, Gamma and Theta using option spread data.
    - Interpolate above greeks for strike prices in option spread.

- **Exploratory Data Analysis**
  - [**EDA pt. 1**](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb))
    - Wrangle, filter, process, and visualize adjusted options data. Visualization of open interest.
  - [**EDA pt. 2**](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb))
    - Create features.
    - De-trend target with ARIMA. Ensure stationary using Augmented Dickey-Fuller test.
    - Baseline linear regression model.
    - Principal component analysis (PCA) on features.

## Data

  - [**EDA**](https://github.com/jacktan1/Options-Project/tree/master/data/EDA)
    - *Format*: "{ticker}_(calls/puts)_EDA1.csv" 
    - Open interest of call/put options. Filters out newly created and expired options.
    
  - [**greeks**](https://github.com/jacktan1/Options-Project/tree/master/data/greeks)
    - *Format*: "{ticker}_(calls/puts)_(delta/gamma/theta).csv" 
    - greek values for calls/puts derived from option spread. See [greeks](https://github.com/jacktan1/Options-Project/blob/master/src/greeks.ipynb) for details
  
  - [**adjusted_daily_closing**](https://github.com/jacktan1/Options-Project/tree/master/data/adjusted_daily_closing)
    - *Format*: "{ticker}.csv"
    - End-of-day prices from Alpha Vantage. "close" column prices have been forward/reverse split adjusted. "adjustment factor" column is the factor by which the raw unadjusted price was *divided* by.
  
  - [**adjusted_options**](https://github.com/jacktan1/Options-Project/tree/master/data/adjusted_options)
    - *Format*: "{ticker}.csv"
    - Adjusted end-of-day option spreads from Discount Option Data.
  
  - [**dividends**](https://github.com/jacktan1/Options-Project/tree/master/data/dividends)
    - *Format*:
      - "{ticker}.csv": The start/end dates of each dividend period, and amount paid. Note that "div_start" is the ex-dividend date for the previous dividend.
      - "{ticker}_ts.csv": Priced in dividends as a time series (daily). A linear model was used in function ["dividend_pricing"](https://github.com/jacktan1/Options-Project/blob/master/src/model_fun.py).
    - For each ticker, there are two files. All dividends have been split adjusted, they can be subtracted directly from `adjusted_daily_closing` prices to obtain true equity price.
      
  - [**questrade_data**](https://github.com/jacktan1/Options-Project/tree/master/data/questrade_data)
    - *Format*: "{ticker}/(date).csv"
    - Unadjusted option data scraped from Questrade API. Recorded prices may not represent end-of-day, as data is scraped in real time.
    - Each ticker has its own folder containing options spreads expiring on different days. 
    - TODO: record date options were scraped, wrangle into same format as training data.