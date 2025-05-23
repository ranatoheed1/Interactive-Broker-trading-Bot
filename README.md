# 📈 Bracket Order Backtesting Strategy

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Backtest a time-shifted moving average strategy with bracket orders (entry, take-profit, stop-loss) on historical stock data using Python and pandas.

---

## 🗂️ Table of Contents

- [Features](#-features)
- [Strategy Overview](#-strategy-overview)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Output](#-output)
- [Example Trade Log](#-example-trade-log)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

- Backtests bracket orders for multiple stocks.
- Uses moving average with 26-bar lag for confirmation.
- Simulates take-profit (10%) and stop-loss (12%) exits.
- Position sizing based on a fixed budget or 1-share fallback.
- Generates trade logs and terminal summary statistics.

---

## 🧠 Strategy Overview

**Buy Signal**:

- `Close price > 200-period MA (shifted back 26 bars)`
- Enough cash available.

**Bracket Order Logic**:

- **Stop Loss**: 8% below entry price.
- **Take Profit**: 6% above entry price.
- Commission: $1 per trade.

**End of Data Handling**:
- Open positions are closed at the final candle's price.

---

## 🔧 Installation

Clone the repository:

```bash
git clone https://github.com/your-username/bracket-order-backtest.git
cd bracket-order-backtest
