import scrape_fun
import preprocess_fun

# Default parameters used for data scraping
alphaVan_token = 'U4G0AXZ62E77Z161'
num_days_year = 252

my_ticker = str(input("Ticker you want to scrape data for: "))
print("You have selected stock ticker: '" + my_ticker + "'")

price = scrape_fun.get_current_price(stock_of_interest=my_ticker,
                                     api_key=alphaVan_token)

my_history_df = scrape_fun.retrieve_price_history(stock_of_interest=my_ticker,
                                                  api_key=alphaVan_token)

preprocess_fun.extract_dividends(my_history=my_history_df,
                                 stock_of_interest=my_ticker,
                                 api_key=alphaVan_token,
                                 num_days_year=num_days_year)

print('Done!')
