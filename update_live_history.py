import pandas as pd
import numpy as np

test_time = pd.to_datetime('2019-01-01 00:00:00')  # To be removed later
cols_inv = ['Strike Date', 'Sold Date', 'Type',
            'Strike Price', 'Sold Price', 'Sold Quantity']
cols_trans = ['Transaction Date', 'Strike Date', 'Buy / Sell', 'Type', 'Strike Price', 'Premium Price',
              'Quantity', 'Change in Cash (USD)']

# When buying back options, we have to look into our inventory and remove inventory as needed
# Also have to check if any options in inventory is expired - Throw warning

# def update_inventroy(strike_date, current_time, info ...etc)
inventory = pd.read_csv('live_options.csv').iloc[:, 1:]

inventory_len = inventory.shape[0]

new_data = pd.DataFrame(columns=cols_inv, data=np.array(
    [[test_time, test_time, 'Call', 0.0, 0.0, 0]]))
inventory = inventory.append(new_data).reset_index().iloc[:, 1:]
inventory.to_csv('live_options.csv', encoding='utf-8', index=True)


transactions = pd.read_csv('transaction_history.csv').iloc[:, 1:]
new_data = pd.DataFrame(columns=cols_trans,
                        data=np.array([[test_time, test_time, 'Sell', 'Put', 0.0, 0.0, 0, 0.0]]))
transactions = transactions.append(new_data).reset_index().iloc[:, 1:]
transactions.to_csv('transaction_history.csv', encoding='utf-8', index=True)
