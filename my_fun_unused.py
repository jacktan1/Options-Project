from mpl_toolkits.mplot3d import Axes3D

# This function plots the winning probability data into a 3-D bar graph
def plot_3dbar(winning, sorted_prices, title_name):
    # The x-axis represent the put prices
    xpos = sorted_prices[:,0]
    # The y-axis represent the call prices
    ypos = sorted_prices[:,0]
    zaxis = np.zeros((len(ypos), len(xpos)))
    [xaxis, yaxis] = np.meshgrid(xpos, ypos)

    dx = np.ones((len(ypos), len(xpos)))*0.5
    dy = np.ones((len(ypos), len(xpos)))*0.5
    dz = winning

    x_f = xaxis.flatten()
    y_f = yaxis.flatten()
    z_f = zaxis.flatten()
    dx_f = dx.flatten()
    dy_f = dy.flatten()
    dz_f = dz.flatten()

    fig = plt.figure()
    ax1 = fig.add_subplot(111, projection='3d')
    ax1.bar3d(x_f, y_f, z_f, dx_f, dy_f, dz_f, color='#00ceaa')
    ax1.set_xlabel('Put Price', fontsize = 18)
    ax1.set_ylabel('Call Price', fontsize = 18)
    ax1.set_zlabel('Percent Chance of Winning', fontsize = 18)
    ax1.set_title(str(title_name))
    plt.show()

### -------- ###

# When given the options data from a certain date, we use this function to arrange the data into
# a "n by 5" array.
def price_sorting(option_data):
    price_holder = np.zeros((len(option_data),5))
    for n in range(0,len(option_data)):
        # Sanity check to make sure code is still running
        print(n)
        strike_price = option_data[n]['strikePrice']
        call_ID = option_data[n]['callSymbolId']
        put_ID = option_data[n]['putSymbolId']
        call_put_data = q.markets_options(optionIds=[call_ID, put_ID])['optionQuotes']
        bid_call_price = call_put_data[0]['bidPrice']
        bid_call_size = call_put_data[0]['bidSize']
        bid_put_price = call_put_data[1]['bidPrice']
        bid_put_size  = call_put_data[1]['bidSize']
        price_holder[n,0] = strike_price
        price_holder[n,1] = bid_call_price
        price_holder[n,2] = bid_call_size
        price_holder[n,3] = bid_put_price
        price_holder[n,4] = bid_put_size
    return price_holder


# Calculates the max increase or decrease in stock price while remaining in safe zone.
# call price is on rows, put price is on columns
# first sheet is max increase, second sheet is max decrease
def risk_analysis(sorted_prices, current_price, fixed_commission, contract_commission, final_prices, \
num_call_sell = 1, num_put_sell = 1):
    max_increase_break = np.zeros((len(sorted_prices), len(sorted_prices)))
    max_decrease_break = np.zeros((len(sorted_prices), len(sorted_prices)))
    historical_return_avg = np.zeros((len(sorted_prices), len(sorted_prices)))
    max_increase_decrease = np.zeros((2, len(sorted_prices), len(sorted_prices)))
    # The rows represent call prices
    for n in range(0,len(sorted_prices)):
        print(n)
        call_strike_price = sorted_prices[n,0]
        call_premium = sorted_prices[n,1]
        call_size = sorted_prices[n,2]
        if num_call_sell != 0:
            call_commission = fixed_commission + num_call_sell*contract_commission
        else:
            call_commission = 0
        # The columns represent put prices
        for m in range(0,len(sorted_prices)):
            put_strike_price = sorted_prices[m,0]
            put_premium = sorted_prices[m,3]
            put_size = sorted_prices[m,4]
            if num_put_sell != 0:
                put_commission = fixed_commission + num_put_sell*contract_commission
            else:
                put_commission = 0
            ###
            # Seeing if these options actually exist (first 2)
            # Seeing if the the combined premium price is enough to cover the call-put difference (3)
            # Seeing if the combined premium prices is enough to cover the commission fees
            if (call_premium == None) or (put_premium == None) or \
            (call_premium + put_premium) <= put_strike_price - call_strike_price or \
            (call_premium*num_call_sell + put_premium*num_put_sell)*100 <= put_commission + call_commission):
                max_increase_break[n,m] = None
                max_decrease_break[n,m] = None
                historical_return_avg[n,m] = None
            else:
                # Needs to be edited to express different sell amounts for calls and puts
                max_increase_break[n,m] = (call_strike_price + call_premium + put_premium - \
                                           current_price)/current_price
                max_decrease_break[n,m] = (put_strike_price - call_premium - put_premium - \
                                           current_price)/current_price
                for p in range(0,len(final_prices)):
                    historical_return_avg[n,m] = historical_return_avg[n,m] \
                    + (min(call_strike_price - final_prices[p], 0) + call_premium) * num_call_sell * 100 \
                    + (min(final_prices[p] - put_strike_price, 0) + put_premium) * num_put_sell * 100
                historical_return_avg[n,m] = (1/len(final_prices))*historical_return_avg[n,m] - call_commission - put_commission
                # The return avg is the average return per contract
                historical_return_avg[n,m] = historical_return_avg[n,m]/(num_call_sell+num_put_sell)
    max_increase_decrease[0,:,:] = max_increase_break
    max_increase_decrease[1,:,:] = max_decrease_break
    [percent_change, historical_return_avg] = [max_increase_decrease, historical_return_avg]
    return [percent_change, historical_return_avg]

### -------- ###

# Converts to percent and annualizes the risk.
def norm_percentage_annualized(max_increase_decrease, days_till_expiry, num_days_a_year):
    percent_max = 100*np.array(max_increase_decrease)
    max_in_de_annual = (num_days_a_year/int(days_till_expiry))*np.array(percent_max)
    return max_in_de_annual

### -------- ###

# This calculated the percentage chance of not exceeding the min and max limits of the stock.
# This is done by sorting the prices and finding the percentage of observations that lie in
# the middle
def percent_chance_win(price_change_percent_annualzed, max_per_annualized):
    winning = np.ones((len(max_per_annualized[0]),len(max_per_annualized[0])))
    prices_sorted = price_change_percent_annualzed[price_change_percent_annualzed[:,0].argsort()]
    for n in range (0, len(max_per_annualized[0])):
        for m in range (0, len(max_per_annualized[0])):
            max_increase = max_per_annualized[0,n,m]
            max_decrease = max_per_annualized[1,n,m]
            if (math.isnan(max_increase) == True) or (math.isnan(max_decrease) == True):
                winning[n,m] = 0
            else:
                winning_range = np.where((prices_sorted > max_decrease) & \
                                          (prices_sorted < max_increase))
                percentile = (len(winning_range[0]))*100/len(prices_sorted)
                winning[n,m] = percentile
    return winning

# Converts to percent and annualizes the risk.
def norm_percentage_annualized(max_increase_decrease, days_till_expiry, num_days_a_year):
    percent_max = 100*np.array(max_increase_decrease)
    max_in_de_annual = (num_days_a_year/int(days_till_expiry))*np.array(percent_max)
    return max_in_de_annual
