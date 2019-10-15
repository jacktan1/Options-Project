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
