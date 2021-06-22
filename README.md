# Options Project

## Description
We aim to design and evaluate the performance of various option pricing models.  [Alpha Vantage](https://www.alphavantage.co) and [Questrade API](https://www.questrade.com/api) are used to retrieve historical and current stock prices (respectively). Latter also scrapes for real-time option spreads. [Discount Option Data](https://discountoptiondata.com) is used to obtain historical option spreads. [FRED](https://fred.stlouisfed.org/categories/115) is responsible for treasury yields.

No API keys stored inside repo files.

## Overview

- [**scrape_and_preprocess.py**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_and_preprocess.py): 
    - Retrieve historical closing prices using Alpha Vantage
    - Adjust for splits
    - Estimates dividend contribution to price

- [**scrape_options.py**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_options.py):
    - Filter options data for specified ticker and append dividend data

- [**scrape_treasury_yields.py**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_treasury_yields.py):
    - Retrieve treasury yields from Federal Reserve Economic Data (FRED)

- [**greeks.ipynb**](https://github.com/jacktan1/Options-Project/blob/master/src/greeks.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/greeks.ipynb) if GitHub is unable to load)
    - Derive Delta, Gamma and Theta using option spread and treasury yield data
    - Interpolate above greeks for strike prices in option spread

- **Exploratory Data Analysis**
    - [**EDA_1.ipynb**](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb))
        - Filter, process and create new features using option spread and dividend data
        - Visualization of open interest
    - [**EDA_2.ipynb**](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb))
        - Engineer novel features
        - De-trend target with ARIMA. Ensure stationary using Augmented Dickey-Fuller test
        - Baseline linear regression model
        - Principal component analysis (PCA) on features

## Data

  - [**EDA**](https://github.com/jacktan1/Options-Project/tree/master/data/EDA)
    - *Format*: `{ticker}_(calls/puts)_EDA1.csv` 
    - Open interest of call/put options. Filters out newly created and expired options
    
  - [**greeks**](https://github.com/jacktan1/Options-Project/tree/master/data/greeks)
    - *Format*: `{ticker}_(calls/puts)_(delta/gamma/theta).csv` 
    - greek values for calls/puts derived from option spread. See [greeks](https://github.com/jacktan1/Options-Project/blob/master/src/greeks.ipynb) for details
  
  - [**adjusted_daily_closing**](https://github.com/jacktan1/Options-Project/tree/master/data/adjusted_daily_closing)
    - *Format*: `{ticker}.csv`
    - End-of-day prices from Alpha Vantage. "close" column prices have been forward/reverse split adjusted. "adjustment factor" column is the factor by which the raw unadjusted price was *divided* by
  
  - [**adjusted_options**](https://github.com/jacktan1/Options-Project/tree/master/data/adjusted_options)
    - *Format*: `{ticker}.csv`
    - Adjusted end-of-day option spreads from Discount Option Data
  
  - [**dividends**](https://github.com/jacktan1/Options-Project/tree/master/data/dividends)
    - *Format*:
      - `{ticker}.csv`: The start/end dates of each dividend period, and amount paid. Note that "div_start" is the ex-dividend date for the previous dividend
      - `{ticker}_ts.csv`: Priced-in dividends as a time series (daily).  Function ["dividend_pricing"](https://github.com/jacktan1/Options-Project/blob/master/src/model_fun.py) uses a linear pricing model
    - For each ticker, there are two files. All dividends have been split adjusted, and can be subtracted from data in "adjusted_daily_closing" to obtain true equity price
      
  - [**questrade**](https://github.com/jacktan1/Options-Project/tree/master/data/questrade)
    - *Format*: `{ticker}/(date).csv`
    - Unadjusted option data scraped from Questrade API in real-time. Thus, recorded prices may not represent end-of-day
    - Each ticker has its own folder containing options spreads expiring on different days 
    - TODO: record date of scrape, wrangle into same format as training data
    
  - [**treasury_yields**](https://github.com/jacktan1/Options-Project/tree/master/data/treasury_yields)
    - *Format*: `{time_to_maturity}.csv`
    - US treasury yield (return ratio **per day**). Unit of day rather than year to match greeks (e.g. Theta)
        - daily rate by linear interpolation
        - daily rate by exponential interpolation (continuous compounding)