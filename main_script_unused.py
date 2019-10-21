# takes historical prices, obtains the percent change over a certain time gap
# and annualizes it
price_change_percent_annual = my_fun.price_change_annualized(price_history, days_till_expiry, num_days_a_year)
# annualizes the risk based on the number of days till expiry
max_per_annualized = my_fun.norm_percentage_annualized(max_increase_decrease, days_till_expiry, num_days_a_year)
winning = my_fun.percent_chance_win(price_change_percent_annual, max_per_annualized)
