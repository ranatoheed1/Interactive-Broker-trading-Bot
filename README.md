# 📈 Stock Trading Strategy Analyzer

This project implements a backtesting system that analyzes stock trading strategies using historical data from five major companies: AAPL, AMZN, GOOGL, MSFT, and TSLA. It utilizes a combination of technical indicators (200-period Moving Average and Ichimoku components) to generate buy signals and simulate trades with predefined stop-loss and take-profit thresholds.

## 🔧 Features

- Backtests a simple buy strategy across 5 stocks.
- Uses:
  - 200-period Moving Average (`MA_200`)
  - Ichimoku Kijun (Base Line)
  - Lagging Span (Chikou Span)
- Buy signal when current close > `MA_200` from 26 bars ago.
- Executes trades with:
  - 2% stop loss
  - 4% take profit
- Logs each trade (entry/exit price, duration, profit/loss).
- Generates interactive candlestick charts with trade markers using Plotly.
- Saves trade history to CSV.

## 📁 Dataset

CSV files used should contain the following columns:  
`Timestamp`, `Open`, `High`, `Low`, `Close`

Place them in your desired directory and update the paths accordingly:
```python
csv_files = [
    "path/to/AAPL.csv",
    "path/to/AMZN.csv",
    ...
]
