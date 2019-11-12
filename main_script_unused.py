# takes historical prices, obtains the percent change over a certain time gap
# and annualizes it
price_change_percent_annual = my_fun.price_change_annualized(price_history, days_till_expiry, num_days_a_year)
# annualizes the risk based on the number of days till expiry
max_per_annualized = my_fun.norm_percentage_annualized(max_increase_decrease, days_till_expiry, num_days_a_year)
winning = my_fun.percent_chance_win(price_change_percent_annual, max_per_annualized)

# Plotting heatmap of various things
my_fun.plot_heatmap_v2(percent_chance_in_money, sorted_prices, \
    str(str(stock_of_interest) + '/' + str(strike_date) + '_percent_chance_in_money'))
my_fun.plot_heatmap_v2(historical_return_avg, sorted_prices, \
    str(str(stock_of_interest) + '/' + str(strike_date) + '_avg_returns'))
my_fun.plot_heatmap_v2(risk_money, sorted_prices, \
    str(str(stock_of_interest) + '/' + str(strike_date) + '_safety_money'))


### Below for testing purposes only!

import numpy as np
aaa = np.zeros((3, 2), dtype = np.ndarray)
aaa[0,0] = np.ones((2, 2))
[nrows, nols] = aaa.shape
nrows
str('asd' + str(2))


aa = np.array([[12,12, 8],[3,4,7]])
bb = np.array([[2,1],[1,5]])
cc = np.append(list(np.ndarray.flatten(aa)), list(bb[:, 0]))
dd = sorted(cc[np.argpartition(cc, -4)][-4:],\
reverse = True)
print(dd)
[call_row, put_col] = np.where(aa == 12)
call_row


test = np.array([[10,12, 8],[3,4,7],[5,7,7],[6,2,7],[9,1,7]])
test[test[:, 0].argsort()[::-1]]

test = np.array([10,12,8,3,4,7])
test2 = np.array([1, 2, 3])
test[test2]

my_select = 0
(type(my_select) != list) & (type(my_select) != int)

print(str('aa: ' + str(new_best[aa])))
print(str('date: ' + str(strike_date_index)))
print(str('call price: ' + str(sorted_prices[n, 0])))
print(str('call num: ' + str(int(call_row))))
print(str('put price: ' + str(sorted_prices[m, 0])))
print(str('put num: ' + str(int(int(put_col)))))
