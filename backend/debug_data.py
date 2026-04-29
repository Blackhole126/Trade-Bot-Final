import pandas as pd
import json

# Load the data
with open('data/cache/TCS.NS_all_data.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['price_history'])
print('Columns:', df.columns.tolist())
print('\nSample data:')
print(df.head())
print('\nData types:')
print(df.dtypes)