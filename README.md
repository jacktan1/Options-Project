# Options_Analysis

## Description
This package aims to use historical option and stock prices to evaluate the performance of various models. Historical and current stock prices for a given ticker are pulled from [Alpha Vantage](https://www.alphavantage.co/) and [Questrade API](https://www.questrade.com/api), respectively. Current option prices also come from the Questrade API. Historical option prices, due to their lesser availability, were obtained from [Discount Option Data]( https://discountoptiondata.com/). Currently, I am only using option data from 2016, as most options go out for a maximum of 4 years.

This package is currently only concerned with the selling of options. In other words, it is trying to deduce which thetas are worth the risk for tickers of low volatility. The scope of this package can easily be expanded to include all combinations of option strategies.


## Folders
- **data**:
  - *EDA*: Data saved as intermediary steps between various data explorations to benefit from modularity.
    - "ticker_(calls/puts)_EDA1.csv" tracks change in open interest of call/put options. Filters out newly created and expired options.
  
  - *adjusted_daily_closing*: Daily closing prices of various stock tickers obtained from Alpha Vantage. The "close" column prices have already been forward/reverse split adjusted. The "adjustment factor" column indicates the factor by which the raw unadjusted price was *divided* by.
  
  - *adjusted_options*: Adjusted historical option data obtained from Discount Option Data and used for training of model. Prices are end of day as indicated on their website.
  
  - *dividends*: For each ticker symbol, there are two files. All dividends have been split adjusted, they can be subtracted directly from the adjusted daily closing prices.
      - "ticker.csv" contains the start and end dates of each dividend period, as well as amount paid. Note that "div_start" is the ex-dividend date for the previous dividend.
      - "ticker_ts.csv" contains the contribution to total price due to dividends as a time series. For each day on record, a dividend contribution is calculated.
      
  - *questrade_data*: Unadjusted option data scraped from Questrade API. Recorded prices may not represent "end of day" prices as snapshots are taken upon execution of scraping script.


- **src**: 
    - [*scrape_and_preprocess*](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_and_preprocess.py): 
        - Retrieves historical closing prices using Alpha Vantage.
        - Adjusts for splits and estimates dividend contribution to closing price.
    - [*scrape_options*](https://github.com/thejacktan/Options_Analysis/blob/master/src/scrape_options.py):
        - Filter options data for specified ticker.
        - Appends dividend contribution data.
    - Exploratory Data Analysis
      - [*EDA pt. 1*](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb) ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_1.ipynb) if github is unable to load):
        - Wrangling, filtering, processing, and visualization of adjusted options data. Tracks daily change in open interest.
      - [*EDA pt. 2*](https://github.com/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb) / ([here](https://nbviewer.jupyter.org/github/thejacktan/Options_Analysis/blob/master/src/EDA_2.ipynb))
        - Creation of novel features based off cleaned data, exploring predictive capabilities of such features.
