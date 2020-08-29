import scrape_fun
import preprocess_fun
import pandas as pd

stock_of_interest = 'CVX'
alphaVan_token = 'U4G0AXZ62E77Z161'
num_days_year = 252

price = scrape_fun.get_current_price(stock_of_interest=stock_of_interest,
                                     api_key=alphaVan_token)

my_history_df = scrape_fun.retrieve_price_history(stock_of_interest=stock_of_interest,
                                                  api_key=alphaVan_token)

preprocess_fun.extract_dividends(my_history=my_history_df,
                                 stock_of_interest=stock_of_interest,
                                 api_key=alphaVan_token,
                                 num_days_year=num_days_year)
