import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime
import pytz

# Configurable parameters
STRATEGY_CONFIG = {
    "TICKERS": ["META", "MSFT", "NFLX", "NVDA", "TSLA"],
    "MA_PERIOD": 200,
    "MA_SHIFT": 26,
    "STOP_LOSS_PCT": 0.12,  # 2%
    "TAKE_PROFIT_PCT": 0.10,  # 4%
    "INITIAL_CASH": 1000.0,
    "BASE_BUDGET": 200.0,
    "COMMISSION": 1.0  # $1 per trade (buy/sell)
}

# CSV file paths
CSV_FILES = [
    "/content/drive/MyDrive/datasets/META.csv",
    "/content/drive/MyDrive/datasets/MSFT.csv",
    "/content/drive/MyDrive/datasets/NFLX.csv",
    "/content/drive/MyDrive/datasets/NVDA.csv",
    "/content/drive/MyDrive/datasets/TSLA.csv"
]

# Set up logging
def setup_logging():
    logging.basicConfig(  # FIXED: Changed 'basicBasic' to 'basicConfig'
        filename='backtest_trading.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

# US market timezone
US_TZ = pytz.timezone('US/Eastern')

def convert_to_us_time(timestamp: pd.Timestamp) -> str:
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize('UTC')
    local_time = timestamp.astimezone(US_TZ)
    return local_time.strftime('%Y-%m-%d %H:%M:%S')

def load_and_process_data(csv_files):
    """Load and process CSV data for all stocks."""
    data = {}
    for file in csv_files:
        stock_name = file.split("/")[-1].split(".")[0]
        df = pd.read_csv(file)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], format='ISO8601')
        df.sort_values("Timestamp", inplace=True)
        df["MA_200"] = df["Close"].rolling(STRATEGY_CONFIG["MA_PERIOD"]).mean()
        df["Backlog_26"] = df["MA_200"].shift(STRATEGY_CONFIG["MA_SHIFT"])
        df["Buy_Signal"] = df["Close"] > df["Backlog_26"]
        df.set_index("Timestamp", inplace=True)
        data[stock_name] = df
    return data

def simulate_bracket_order(trade, df, start_time, commission=1.0, cash=0.0, total_profit=0.0):
    """Simulate SL/TP exit for a trade."""
    entry_price = trade['Entry Price']
    qty = trade['Quantity']
    sl = trade['SL']
    tp = trade['TP']
    entry_time = trade['Entry Time']
    symbol = trade['Symbol']

    for timestamp in df.index[df.index > start_time]:
        bar = df.loc[timestamp]
        low_price = float(bar['Low'])
        high_price = float(bar['High'])
        current_price = float(bar['Close'])
        backlog_26 = float(bar['Backlog_26']) if not pd.isna(bar['Backlog_26']) else None
        ma_200 = float(bar['MA_200']) if not pd.isna(bar['MA_200']) else None

        if low_price <= sl:
            exit_price = sl
            exit_type = 'SL'
            exit_time = timestamp
            break
        elif high_price >= tp:
            exit_price = tp
            exit_type = 'TP'
            exit_time = timestamp
            break
    else:
        exit_price = df.iloc[-1]['Close']
        exit_time = df.index[-1]
        exit_type = 'End'
        backlog_26 = float(df.iloc[-1]['Backlog_26']) if not pd.isna(df.iloc[-1]['Backlog_26']) else None
        ma_200 = float(df.iloc[-1]['MA_200']) if not pd.isna(df.iloc[-1]['MA_200']) else None
        logging.info(f"{symbol}: No SL/TP hit, exited at {exit_time} @ ${exit_price:.2f}")

    pnl = (exit_price - entry_price) * qty - 2 * commission
    cash_after = cash + (exit_price * qty - commission)
    total_profit += pnl

    logging.info(
        f"SELL {symbol}: Time={convert_to_us_time(exit_time)}, Quantity={qty}, "
        f"Exit Price=${exit_price:.2f}, Exit Type={exit_type}, PNL=${pnl:.2f}, "
        f"SL=${sl:.2f}, TP=${tp:.2f}, Cash=${cash_after:.2f}, "
        f"Total Profit=${total_profit:.2f}, "
        f"MA_200={'N/A' if ma_200 is None else f'${ma_200:.2f}'}, "
        f"Backlog_26={'N/A' if backlog_26 is None else f'${backlog_26:.2f}'}, "
        f"Current Price=${exit_price:.2f}"
    )

    print(
        f"SELL {symbol}: {convert_to_us_time(exit_time)}, Quantity={qty}, "
        f"Exit Price=${exit_price:.2f}, Exit Type={exit_type}, PNL=${pnl:.2f}, "
        f"SL=${sl:.2f}, TP=${tp:.2f}, Cash=${cash_after:.2f}, "
        f"Total Profit=${total_profit:.2f}"
    )

    return {
        'Stock': symbol,
        'Entry Date': convert_to_us_time(entry_time).split()[0],
        'Entry Hour': convert_to_us_time(entry_time).split()[1],
        'Entry Price': entry_price,
        'Quantity': qty,
        'Exit Date': convert_to_us_time(exit_time).split()[0],
        'Exit Hour': convert_to_us_time(exit_time).split()[1],
        'Exit Price': exit_price,
        'Exit Type': exit_type,
        'PNL': pnl,
        'Duration Hours': (exit_time - entry_time).total_seconds() / 3600
    }, total_profit

def run_backtest():
    setup_logging()
    logging.info("Backtest start")

    # Load data
    data = load_and_process_data(CSV_FILES)
    if not data:
        logging.error("No data loaded")
        return

    # Initialize portfolio
    cash = STRATEGY_CONFIG['INITIAL_CASH']
    total_profit = 0.0
    positions = {ticker: {'qty': 0, 'entry_time': None} for ticker in STRATEGY_CONFIG['TICKERS']}
    trades = []
    equity = []
    equity_timestamps = []

    # Get common timestamps
    common_index = data[STRATEGY_CONFIG['TICKERS'][0]].index
    for ticker in STRATEGY_CONFIG['TICKERS'][1:]:
        common_index = common_index.intersection(data[ticker].index)

    # Backtest loop
    for timestamp in common_index:
        # Get prices and sort tickers
        ticker_prices = []
        for ticker in STRATEGY_CONFIG['TICKERS']:
            if timestamp in data[ticker].index:
                price = data[ticker].loc[timestamp, 'Close']
                if not pd.isna(price):
                    ticker_prices.append((ticker, price))
                else:
                    logging.warning(f"No price for {ticker} at {timestamp}")

        ticker_prices.sort(key=lambda x: x[1])

        for ticker, price in ticker_prices:
            df = data[ticker]
            ma_200 = float(df.loc[timestamp, 'MA_200']) if not pd.isna(df.loc[timestamp, 'MA_200']) else None
            backlog_26 = float(df.loc[timestamp, 'Backlog_26']) if not pd.isna(df.loc[timestamp, 'Backlog_26']) else None
            logging.info(
                f"{ticker}: Time={convert_to_us_time(timestamp)}, "
                f"MA_200={'N/A' if ma_200 is None else f'${ma_200:.2f}'}, "
                f"Backlog_26={'N/A' if backlog_26 is None else f'${backlog_26:.2f}'}, "
                f"Current Price=${price:.2f}"
            )

        for ticker, price in ticker_prices:
            df = data[ticker]
            ma_200 = float(df.loc[timestamp, 'MA_200']) if not pd.isna(df.loc[timestamp, 'MA_200']) else None
            backlog_26 = float(df.loc[timestamp, 'Backlog_26']) if not pd.isna(df.loc[timestamp, 'Backlog_26']) else None

            if positions[ticker]['qty'] > 0:
                trade = {
                    'Symbol': ticker,
                    'Entry Time': positions[ticker]['entry_time'],
                    'Entry Price': positions[ticker]['entry_price'],
                    'Quantity': positions[ticker]['qty'],
                    'SL': positions[ticker]['sl'],
                    'TP': positions[ticker]['tp']
                }
                trade_result, total_profit = simulate_bracket_order(
                    trade, df, timestamp, STRATEGY_CONFIG['COMMISSION'], cash, total_profit
                )
                trades.append(trade_result)

                cash += trade_result['Exit Price'] * trade_result['Quantity'] - STRATEGY_CONFIG['COMMISSION']
                positions[ticker] = {'qty': 0, 'entry_time': None}
                logging.info(f"Closed position for {ticker}: Cash=${cash:.2f}, Total Profit=${total_profit:.2f}")

            if not df.loc[timestamp, 'Buy_Signal'] or pd.isna(df.loc[timestamp, 'Backlog_26']):
                continue

            if price <= STRATEGY_CONFIG['BASE_BUDGET']:
                budget = min(STRATEGY_CONFIG['BASE_BUDGET'], cash)
                qty = int(budget // price)
                logging.info(f"{ticker}: Price <= $200, Allocated=${budget:.2f}, Qty={qty}")
            else:
                qty = 1 if cash >= price else 0
                logging.info(f"{ticker}: Price > $200, Can buy 1 share={cash >= price}, Qty={qty}")

            if qty >= 1:
                cost = qty * price
                if cost > cash:
                    logging.info(f"Insufficient cash for {ticker}: Cost=${cost:.2f}, Cash=${cash:.2f}")
                    continue
                sl = round(price * (1 - STRATEGY_CONFIG['STOP_LOSS_PCT']), 2)
                tp = round(price * (1 + STRATEGY_CONFIG['TAKE_PROFIT_PCT']), 2)

                cash -= cost + STRATEGY_CONFIG['COMMISSION']
                positions[ticker] = {
                    'qty': qty,
                    'entry_time': timestamp,
                    'entry_price': price,
                    'sl': sl,
                    'tp': tp
                }

                logging.info(
                    f"BUY {ticker}: Time={convert_to_us_time(timestamp)}, Quantity={qty}, "
                    f"Entry Price=${price:.2f}, Total Cost=${cost:.2f}, SL=${sl:.2f}, "
                    f"TP=${tp:.2f}, Cash=${cash:.2f}, "
                    f"MA_200={'N/A' if ma_200 is None else f'${ma_200:.2f}'}, "
                    f"Backlog_26={'N/A' if backlog_26 is None else f'${backlog_26:.2f}'}, "
                    f"Current Price=${price:.2f}"
                )

                print(
                    f"BUY {ticker}: {convert_to_us_time(timestamp)}, Quantity={qty}, "
                    f"Entry Price=${price:.2f}, Total Cost=${cost:.2f}, SL=${sl:.2f}, "
                    f"TP=${tp:.2f}, Cash=${cash:.2f}"
                )

        portfolio_value = cash
        for ticker in STRATEGY_CONFIG['TICKERS']:
            if positions[ticker]['qty'] > 0 and timestamp in data[ticker].index:
                portfolio_value += positions[ticker]['qty'] * data[ticker].loc[timestamp, 'Close']
        equity.append(portfolio_value)
        equity_timestamps.append(timestamp)

    for ticker in STRATEGY_CONFIG['TICKERS']:
        if positions[ticker]['qty'] > 0:
            df = data[ticker]
            trade = {
                'Symbol': ticker,
                'Entry Time': positions[ticker]['entry_time'],
                'Entry Price': positions[ticker]['entry_price'],
                'Quantity': positions[ticker]['qty'],
                'SL': positions[ticker]['sl'],
                'TP': positions[ticker]['tp']
            }
            trade_result, total_profit = simulate_bracket_order(
                trade, df, df.index[-1], STRATEGY_CONFIG['COMMISSION'], cash, total_profit
            )
            trades.append(trade_result)
            cash += trade_result['Exit Price'] * trade_result['Quantity'] - STRATEGY_CONFIG['COMMISSION']
            positions[ticker] = {'qty': 0, 'entry_time': None}
            logging.info(
                f"Closed position for {ticker}: Cash=${cash:.2f}, Total Profit=${total_profit:.2f}"
            )

    trade_logs_df = pd.DataFrame(trades)
    trade_logs_df.to_csv("trade_logs.csv", index=False)

    total_return = (cash - STRATEGY_CONFIG['INITIAL_CASH']) / STRATEGY_CONFIG['INITIAL_CASH'] * 100
    win_rate = len([t for t in trades if t['PNL'] > 0]) / len(trades) * 100 if trades else 0

    logging.info(
        f"Backtest complete: Initial Cash=${STRATEGY_CONFIG['INITIAL_CASH']:.2f}, "
        f"Final Cash=${cash:.2f}, Total Return={total_return:.2f}%, "
        f"Win Rate={win_rate:.2f}%, Total Profit=${total_profit:.2f}"
    )
    print("\nTrade logs saved to 'trade_logs.csv'.")
    print(f"Initial Cash: ${STRATEGY_CONFIG['INITIAL_CASH']:.2f}")
    print(f"Final Cash: ${cash:.2f}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total Profit: ${total_profit:.2f}")

    return trade_logs_df, cash, total_return, win_rate, total_profit

if __name__ == '__main__':
    run_backtest()
