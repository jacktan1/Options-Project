import numpy as np
import requests
import datetime as dt
import re
import pandas as pd
from questrade_api import Questrade
import urllib
import json
import math
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import chart_studio.plotly as py
import plotly.graph_objects as go
import plotly.figure_factory as ff

q = Questrade()

### --- Start of Functions --- ###

# After obtaining 'q.time' or
#
# expiry_date = []
# for n in range (0,len(options_data)):
#     expiry_date.append(options_data[n]['expiryDate'])
#
# We can plug it into the following to get correct date formating
def date_convert(dates):
    actual_dates = []
    # This is for convering the current date (q.time)
    if len(dates) == 1:
        dates = dates['time']
        date_decomp = re.findall('([\d]{4})[-]([\d]{2})[-]([\d]{2})[T]', dates)
        actual_dates.append(dt.date(int(date_decomp[0][0]), int(date_decomp[0][1]), int(date_decomp[0][2])))
    # This is converting all the expiry dates
    else:
        for n in range(0, len(dates)):
            date_decomp = re.findall('([\d]{4})[-]([\d]{2})[-]([\d]{2})[T]', dates[n])
            actual_dates.append(dt.date(int(date_decomp[0][0]), int(date_decomp[0][1]), int(date_decomp[0][2])))
    return actual_dates

### -------- ###

# Extracts the historical daily closing price of a given stock from AlphaVantage API
def extract_price_history(stock_of_interest, API_key):
        # Getting data link
    data_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=' \
        + stock_of_interest + '&outputsize=full&apikey=' + API_key
    # Extracting the json information from the site
    with urllib.request.urlopen(data_url) as url:
        history_data = json.load(url)
    # Treating the data since it had a lot of other crap
    history_data =  history_data['Time Series (Daily)']
    # Extracting the dates keys
    wanted_keys = history_data.keys()
    # Getting the stupid date keys out of there
    refined_history_data = list(history_data[k] for k in wanted_keys)

    history_closing_price = np.zeros((len(refined_history_data), 1))
    # Extracting the closing price info from all the prices
    for n in range(0, len(refined_history_data)):
        history_closing_price[n,0] = refined_history_data[n]['4. close']
    history_closing_price = history_closing_price[::-1]
    return history_closing_price

### -------- ###

def get_current_price(stock_symb, stock_Id):
    price = q.markets_quote(stock_Id)['quotes'][0]['lastTradePrice']
    return price

### -------- ###

# When given the options data from a certain date, we use this function to arrange the data into
# a "n by 5" array.
def price_sorting_v2(option_data, strike_date, stock_name):
    price_holder = np.zeros((len(option_data),5))
    #id_holder = np.zeros((2*len(option_data),1))
    id_holder = [0]*(2*len(option_data))
    for n in range(0, len(option_data)):
        strike_price = option_data[n]['strikePrice']
        price_holder[n,0] = strike_price
        call_ID = option_data[n]['callSymbolId']
        put_ID = option_data[n]['putSymbolId']
        id_holder[2*n] = call_ID
        id_holder[2*n+1] = put_ID
    # Stupid Questrade API has max request length of 100...
    if len(id_holder) > 100:
        call_put_data = q.markets_options(optionIds=list(id_holder[0:100]))['optionQuotes']
        call_put_data = call_put_data + q.markets_options(optionIds=list(id_holder[100:len(id_holder)]))['optionQuotes']
    else:
        call_put_data = q.markets_options(optionIds=list(id_holder))['optionQuotes']
    for n in range(0, len(option_data)):
        bid_call_price = call_put_data[int(2*n)]['bidPrice']
        bid_call_size = call_put_data[2*n]['bidSize']
        bid_put_price = call_put_data[2*n+1]['bidPrice']
        bid_put_size  = call_put_data[2*n+1]['bidSize']
        price_holder[n,1] = bid_call_price
        price_holder[n,2] = bid_call_size
        price_holder[n,3] = bid_put_price
        price_holder[n,4] = bid_put_size
    print('Done pulling data from Questrade API!')
    data_down = 0
    for n in range(0, len(price_holder)):
        if price_holder[n,2] == 0:
            data_down = data_down + 1
    if data_down == len(price_holder):
        print('Questrade data is down! Trying to pull most recent data...')
        try:
            price_holder = np.loadtxt(str('bid_history/' + str(stock_name) + '/'  + str(str(strike_date) + '.csv')), delimiter=',')
            print('Loaded local data!')
        except Exception as e:
            print('Most recent data not found!')
            pass
    if data_down < len(price_holder):
        print('Questrade data saved locally!')
        np.savetxt('bid_history/' + str(stock_name) + '/' + str(str(strike_date) + '.csv'), price_holder, delimiter=",")
    return price_holder


### -------- ###

# Calculates the max increase or decrease in stock price while remaining in safe zone.
# call price is on rows, put price is on columns
# first sheet is max increase, second sheet is max decrease
def risk_analysis_v3(sorted_prices, current_price, fixed_commission, contract_commission, final_prices, \
call_sell_max = 1, put_sell_max = 1):
    historical_return_avg = np.zeros((len(sorted_prices), len(sorted_prices)), dtype = np.ndarray)
    percent_in_money = np.zeros((len(sorted_prices), len(sorted_prices)), dtype = np.ndarray)
    risk_money = np.zeros((len(sorted_prices), len(sorted_prices)), dtype = np.ndarray)
    # The rows represent call prices
    for n in range(0,len(sorted_prices)):
        # Progress indicator
        print(n)
        call_strike_price = sorted_prices[n,0]
        call_premium = sorted_prices[n,1]
        call_size = sorted_prices[n,2]
        # The columns represent put prices
        for m in range(0,len(sorted_prices)):
            # reinitilaizing the max call and put matrix
            num_call_put_matrix = np.zeros((call_sell_max, put_sell_max))
            # reinitilaizing other matrices
            historical_return_avg_inner = np.zeros((call_sell_max + 1, put_sell_max + 1))
            percent_in_money_inner = np.zeros((call_sell_max + 1, put_sell_max + 1))
            risk_money_inner = np.zeros((call_sell_max + 1, put_sell_max + 1))
            ###
            put_strike_price = sorted_prices[m,0]
            put_premium = sorted_prices[m,3]
            put_size = sorted_prices[m,4]
            ###
            # Seeing if these options actually exist
            if (call_premium == None) or (put_premium == None):
                percent_in_money[n,m] = None
                historical_return_avg[n,m] = None
            else:
                # Calls
                call_base = np.minimum(call_strike_price - final_prices, 0) + call_premium
                call_num_matrix = np.arange(0, call_sell_max + 1, 1).reshape(1, call_sell_max + 1)
                call_comm_matrix = fixed_commission + call_num_matrix * contract_commission
                call_comm_matrix[0][0] = 0
                call_return = call_base * call_num_matrix * 100 - call_comm_matrix

                # Puts
                put_base = np.minimum(final_prices - put_strike_price , 0) + put_premium
                put_num_matrix = np.arange(0, put_sell_max + 1, 1).reshape(1, put_sell_max + 1)
                put_comm_matrix = fixed_commission + put_num_matrix * contract_commission
                put_comm_matrix[0][0] = 0
                put_return = put_base * put_num_matrix * 100 - put_comm_matrix

                for aa in range(0, call_sell_max + 1):
                    for bb in range(0, put_sell_max + 1):
                        # reinitialize parameter to calculate percentage chance to be in money
                        num_in_money = 0
                        risk_money_holder = 0
                        if (aa == 0) & (bb == 0):
                            historical_return_avg_inner[aa, bb] = 0
                            percent_in_money_inner[aa, bb] = 0
                            risk_money_inner[aa, bb] = 0
                        else:
                            total_call_put = (call_return[:,aa] + put_return[:,bb])/(aa + bb)
                            for cc in range(0, len(total_call_put)):
                                if total_call_put[cc] > 0:
                                    num_in_money += 1
                                else:
                                    risk_money_holder += total_call_put[cc]

                            historical_return_avg_inner[aa, bb] = np.sum(total_call_put)/len(total_call_put)
                            percent_in_money_inner[aa, bb] = (num_in_money/len(total_call_put)) * 100
                            if (len(total_call_put) - num_in_money) == 0:
                                risk_money_inner[aa, bb] = 0
                            else:
                                risk_money_inner[aa, bb] = risk_money_holder/(len(total_call_put) - num_in_money)

                historical_return_avg[n, m] = historical_return_avg_inner
                percent_in_money[n, m] = percent_in_money_inner
                risk_money[n, m] = risk_money_inner

    return [percent_in_money, historical_return_avg, risk_money]

### -------- ###

#This function calculates the theoretical end prices of the stock at the expiry date
def historical_final_price(price_history, current_price, days_till_expiry):
    final_prices = np.zeros((int(len(price_history)-days_till_expiry), 1))
    for n in range(0, len(final_prices)):
        holder = (price_history[n+days_till_expiry] - price_history[n])/price_history[n]
        final_prices[n] = current_price*(1 + holder)
    return final_prices

### -------- ###

# This map creates a heat map of the winning probabilities
def plot_heatmap(winning, sorted_prices, title_name):
    # x-axis are put prices
    x_axis = sorted_prices[:,0]
    # y-axis are call prices
    y_axis = sorted_prices[:,0]
    heatmap_data = winning

    fig, ax = plt.subplots(figsize = (13,9))
    im = ax.imshow(heatmap_data)

    # Create colorbar
    fig.colorbar(im, ax=ax)

    # We want to show all ticks
    ax.set_xticks(np.arange(len(x_axis)))
    ax.set_yticks(np.arange(len(y_axis)))
    # ... and label them with the respective list entries
    ax.set_xticklabels(x_axis)
    ax.set_yticklabels(y_axis)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=90, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    for n in range(len(y_axis)):
        for m in range(len(x_axis)):
            text = ax.text(m, n, round(winning[n, m],1), \
                           ha="center", va="center", color="w", fontsize = 5)

    ax.set_title(str(title_name))
    ax.set_xlabel('Put Price', fontsize = 16)
    ax.set_ylabel('Call Price', fontsize = 16)
    fig.tight_layout()
    plt.show()

### -------- ###

# This is a non-annotated heatmap using Plotly

def plot_heatmap(winning, sorted_prices, title_name):
    # x-axis are put prices
    # y-axis are call prices

    data = go.Heatmap(
        z = winning,
        x = list(sorted_prices[:,0]),
        y = list(sorted_prices[:,0]),
        xgap = 5,
        ygap = 5,
        text = np.matrix.round(winning, 1)
        )


    layout = go.Layout(
        title = (str(title_name)),
        font = dict(size = 20),
        xaxis = dict(showgrid=True, ticks="inside", dtick=1, title_text='Put Price', \
                title_font = dict(size=25)),
        yaxis = dict(showgrid=True, ticks="inside", dtick=1, title_text='Call Price', \
                title_font = dict(size=25)),
        width = 1500,
        height = 950
    )

    fig = go.Figure(data = data, layout = layout)
    fig.write_image(str(title_name) + '.png')

### -------- ###

# This is an annotated heatmap using Plotly

def plot_heatmap_v2(winning, sorted_prices, title_name):

    fig = ff.create_annotated_heatmap(
        z = winning,
        x = list(sorted_prices[:,0]),
        y = list(sorted_prices[:,0]),
        annotation_text = np.matrix.round(winning),
        showscale = True,
        xgap = 5,
        ygap = 5,
        )

    fig.layout.update(dict(height = 900, width = 1500, font = dict(size = 10), title_text = str(title_name), \
    title_font = dict(size = 25)))

    fig.layout.xaxis.update(dict(showgrid = True, ticks = 'inside', dtick = 5, title_text = 'Put Price', \
            title_font = dict(size = 25), side = 'bottom'))

    fig.layout.yaxis.update(dict(showgrid = True, ticks = "inside", dtick = 5, title_text = 'Call Price', \
            title_font = dict(size = 25), side = 'left'))

    fig.write_image('figs/' + str(title_name) + '.png')


### -------- ###
