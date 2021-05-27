# Options Project

## Description
We aim to use historical option and stock prices to create and evaluate the performance of various models. Historical and current stock prices for a given ticker are pulled from [Alpha Vantage](https://www.alphavantage.co/) and [Questrade API](https://www.questrade.com/api), respectively. Current option prices also come from the Questrade API. Historical option prices, were obtained from [Discount Option Data]( https://discountoptiondata.com/). Currently, I am only using option data from 2016, as most options go out for a maximum of 4 years.


## Overview

- **src**: 
    - [**scrape_and_preprocess**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_and_preprocess.py): 
        - Retrieve historical closing prices using Alpha Vantage.
        - Adjust for splits and estimates dividend contribution.
    - [**scrape_options**](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_options.py):
        - Filter options data for specified ticker and append dividend data.
    - **Exploratory Data Analysis**
      - [**EDA pt. 1**](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb) if GitHub is unable to load)
        - Wrangle, filter, process, and visualize adjusted options data. Visualization of open interest.
      - [**greeks**](https://github.com/jacktan1/Options-Project/blob/master/src/greeks.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/greeks.ipynb))
        - Derive Delta, Gamma and Theta using option spread data. 
      - [**EDA pt. 2**](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb) / ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb))
        - Create features.
        - De-trend target with ARIMA. Ensure stationary using Augmented Dickey-Fuller test.
        - Baseline linear regression model.
        - Principal component analysis (PCA) on features.

- **data**:
  - **EDA**: Data saved as intermediary steps between notebooks.
    - "{ticker}_(calls/puts)_EDA1.csv": Open interest of call/put options. Filters out newly created and expired options.
    - "{ticker)_(calls/puts)_delta.csv": Delta values for calls/puts derived using data from option spread. See [greeks.ipynb](https://github.com/jacktan1/Options-Project/blob/master/src/greeks.ipynb) for detailed methods.
  
  - **adjusted_daily_closing**: Daily closing prices of tickers obtained from Alpha Vantage. The "close" column prices have already been forward/reverse split adjusted. The "adjustment factor" column indicates the factor by which the raw unadjusted price was *divided* by.
  
  - **adjusted_options**: Adjusted historical option data from Discount Option Data. Recorded prices are end-of-day.
  
  - **dividends**: For each ticker, there are two files. All dividends have been split adjusted, they can be subtracted directly from the adjusted daily closing prices.
      - "{ticker}.csv": The start and end dates of each dividend period, as well as amount paid. Note that "div_start" is the ex-dividend date for the previous dividend.
      - "{ticker}_ts.csv": Priced in dividends as a time series. Pricing model as defined in function "dividend_pricing" [here](https://github.com/jacktan1/Options-Project/blob/master/src/model_fun.py). Calculated for all days with an end-of-day price.
      
  - **questrade_data**: Unadjusted option data scraped from Questrade API. Recorded prices may not represent end-of-day, as data is scraped in real time.