import scrape_fun
import preprocess_fun
import urllib
from questrade_api import Questrade

# Default parameters used for data scraping
alphaVan_token = 'U4G0AXZ62E77Z161'
num_days_year = 252
q = Questrade()

# Initializing Questrade Connection
try:
    current_time = q.time
    print("Questrade API working successfully!")
except urllib.error.HTTPError:
    print("Login key has expired! Need to obtain new refresh token from 'questrade.com'!")
    my_token = str(input("Refresh token from Questrade: "))
    q = Questrade(refresh_token=my_token)
    current_time = q.time
    if not current_time:
        raise Exception("Time should not be empty!")
    else:
        print("New Questrade token successfully saved!")


my_ticker = str(input("Ticker you want to scrape data for: "))
print("You have selected stock ticker: '" + my_ticker + "'")

price = scrape_fun.get_current_price(stock_of_interest=my_ticker,
                                     questrade_instance = q,
                                     api_key=alphaVan_token)

my_history_df = scrape_fun.retrieve_price_history(stock_of_interest=my_ticker,
                                                  api_key=alphaVan_token)

preprocess_fun.extract_dividends(my_history=my_history_df,
                                 stock_of_interest=my_ticker,
                                 api_key=alphaVan_token,
                                 num_days_year=num_days_year)

print('Done!')
