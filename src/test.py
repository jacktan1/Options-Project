import sys
import scraping

stock_of_interest = 'AAPL'
alphaVan_token = 'U4G0AXZ62E77Z161'

# price = scraping.get_current_price(stock_of_interest=stock_of_interest,
#                                    api_key=alphaVan_token)

hist = scraping.retrieve_price_history(stock_of_interest=stock_of_interest,
                                       api_key=alphaVan_token)
