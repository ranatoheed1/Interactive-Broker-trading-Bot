import yfinance as yf

# Define stock ticker and time interval
ticker_symbol = "AMD"  # Change this to your desired stock ticker
interval = "1h"         # Hourly data
period = "1y"           # Last 1 year

# Download data
data = yf.download(ticker_symbol, interval=interval, period=period)

# Save to CSV
csv_filename = f"{ticker_symbol}_1y_hourly.csv"
data.to_csv(csv_filename)

print(f"Data saved to {csv_filename}")
