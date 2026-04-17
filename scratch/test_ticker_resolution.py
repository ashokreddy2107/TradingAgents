import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tradingagents.dataflows.ticker_utils import resolve_yfinance_ticker

tickers_to_test = ["AAPL", "OLECTRA", "RELIANCE", "SPY"]

for t in tickers_to_test:
    print(f"Resolving '{t}'...")
    resolved = resolve_yfinance_ticker(t)
    print(f"Result: '{resolved}'")
    print("-" * 20)
