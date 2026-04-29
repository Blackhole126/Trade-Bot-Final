import json

# Load the TCS.NS data
with open('data/cache/TCS.NS_all_data.json', 'r') as f:
    data = json.load(f)

print("Data keys:", list(data.keys()))
print("\nMetadata:", data.get('metadata', 'No metadata found'))
print("\nPrice history type:", type(data.get('price_history', 'Not found')))

if 'price_history' in data:
    price_data = data['price_history']
    print(f"Price history length: {len(price_data)}")
    print("First few entries:")
    for i, entry in enumerate(price_data[:3]):
        print(f"  Entry {i}: {entry}")
else:
    print("No price_history found in data")