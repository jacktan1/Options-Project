import scrape_fun
import os

# Ensure working directory path is correct
if os.getcwd()[-3:] == "src":
    os.chdir(os.path.dirname(os.getcwd()))
else:
    pass

# User defined parameters
option_data_path = "data/discount_data/"
stock_data_path = "data/adjusted_daily_closing/"
adjusted_options_save_path = "data/adjusted_options/"

my_ticker = str(input("Ticker you want to aggregate option data for: ")).upper()
print("You have selected stock ticker: '" + my_ticker + "'")

scrape_fun.hist_option_data(stock_of_interest=my_ticker,
                            option_data_path=option_data_path,
                            stock_data_path=stock_data_path,
                            save_path=adjusted_options_save_path)

print("Done!")
