import pandas as pd
import json
import os

# Check if cache file exists
cache_file = 'data/cache/TCS.NS_all_data.json'
if not os.path.exists(cache_file):
    print(f"Cache file not found: {cache_file}")
    exit(1)

# Load the data
with open(cache_file, 'r') as f:
    data = json.load(f)

print("Data keys:", list(data.keys()))

if 'price_history' in data:
    df = pd.DataFrame(data['price_history'])
    print(f"DataFrame shape: {df.shape}")
    print(f"Index type: {type(df.index)}")
    print(f"Index dtype: {df.index.dtype}")
    print(f"First 5 index values: {df.index[:5].tolist()}")
    print(f"Last 5 index values: {df.index[-5:].tolist()}")
    print(f"Max index value: {df.index.max()}")
    print(f"Min index value: {df.index.min()}")
    
    # Check if we have a date column
    date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
    print(f"Date columns found: {date_columns}")
    
    if date_columns:
        date_col = date_columns[0]
        print(f"Sample {date_col} values: {df[date_col].head().tolist()}")
else:
    print("No price_history in data")