# Options_Analysis

## Description
This package aims to use historical option and stock prices to evaluate the performance of various models. Historical and current stock prices for a given ticker are pulled from [Alphavantage](https://www.alphavantage.co/) and [Questrade API](https://www.questrade.com/api), respectively. Current option prices also come from the Questrade API. Historical option prices, due to their lesser availability, were obtained from [Discount Option Data]( https://discountoptiondata.com/). Currently, I am only using option data from 2016, as most options go out for a maximum of 4 years.

This package is currently only concerned with the selling of options. In other words, it is trying to deduce which thetas are worth the risk for tickers of low volatility. The scope of this package can easily be expanded to include all combinations of option strategies.

## Folders
- **data**:
  - *questrade*: Data obtained from the Questrade API. Files are snapshots of option data of a specific ticker symbol for a given day. Note that prices are updated in real time once scraping script is executed. Therefore, recorded prices may not represent "end of day" prices.
  - *discount*: Data obtained from Discount Option Data. Prices are end of day as indicated on their website.

- **results**: This folder contains analyzed performance of different call and put option pairs for a given ticker on a given date.


## Dependencies
- python
  - numpy
  - pandas
  - plotly
  - numba
  - questrade_api
