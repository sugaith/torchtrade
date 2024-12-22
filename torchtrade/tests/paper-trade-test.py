import os
from pybit import market, _websocket_stream, _v5_market
import pandas as pd
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")
SYMBOL = "BTCUSDT"  # Example symbol
TIMEFRAME = "240"  # 4-hour in minutes
SHORT_WINDOW = 10  # Short-term moving average period
LONG_WINDOW = 30   # Long-term moving average period
TRADE_AMOUNT = 0.01  # Amount to trade (in quote currency for USDT Perpetual)

# --- Initialize Bybit Client ---

rest_linear = _v5_market.MarketHTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET,
)

# --- Global Variables for Tracking State ---
position = "NONE"  # NONE, LONG, SHORT
entry_price = 0.0


def fetch_historical_data(symbol, interval, limit=100):
    """Fetches historical kline data from Bybit based on the v5 API."""
    try:
        params = {
            "category": "linear",  # Assuming USDT perpetual futures
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = rest_linear.get_kline(**params)
        if response['retCode'] == 0:
            raw_data = response['result']['list']
            df = pd.DataFrame(raw_data, columns=['start_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df['start_time'] = pd.to_datetime(df['start_time'], unit='ms')
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            df['turnover'] = pd.to_numeric(df['turnover'])
            return df
        else:
            print(f"Error fetching data: {response}")
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def calculate_moving_averages(df, short_window, long_window):
    """Calculates short and long-term moving averages."""
    df['SMA_short'] = df['close'].rolling(window=short_window).mean()
    df['SMA_long'] = df['close'].rolling(window=long_window).mean()
    return df


def place_market_order(side, symbol, qty):
    """Simulates placing a market order (paper trading)."""
    global position, entry_price
    try:
        print(f"Paper Trading: Placing Market {side} order for {qty} {symbol}")
        current_price = get_current_price(symbol)
        if current_price is None:
            print("Could not get current price, not placing order.")
            return

        if side == "Buy":
            if position == "SHORT":
                print(f"Paper Trading: Closing SHORT position at {current_price}")
                position = "NONE"
                entry_price = 0.0
            print(f"Paper Trading: Opening LONG position at {current_price}")
            position = "LONG"
            entry_price = current_price
        elif side == "Sell":
            if position == "LONG":
                print(f"Paper Trading: Closing LONG position at {current_price}")
                position = "NONE"
                entry_price = 0.0
            print(f"Paper Trading: Opening SHORT position at {current_price}")
            position = "SHORT"
            entry_price = current_price
        print(f"Current Position: {position}, Entry Price: {entry_price}")

    except Exception as e:
        print(f"Error placing order: {e}")


def get_current_price(symbol):
    """Gets the current price of a symbol."""
    try:
        data = rest_linear.get_tickers(category='linear', symbol=symbol)['result']
        if data:
            return float(data['list'][0]['lastPrice'])
        return None
    except Exception as e:
        print(f"Error getting current price: {e}")
        return None


def trading_logic():
    """Executes the trading logic based on moving averages."""
    global position, entry_price
    print(f"--- Running Trading Logic at {datetime.now()} ---")

    df = fetch_historical_data(SYMBOL, TIMEFRAME, limit=LONG_WINDOW + 5)
    if df is None or len(df) < LONG_WINDOW:
        print("Not enough data to calculate moving averages.")
        return

    df = calculate_moving_averages(df, SHORT_WINDOW, LONG_WINDOW)

    current_price = get_current_price(SYMBOL)
    if current_price is None:
        return

    last_row = df.iloc[-1]
    previous_row = df.iloc[-2]

    # Buy Condition: Short MA crosses above Long MA
    if (previous_row['SMA_short'] <= previous_row['SMA_long']) and (last_row['SMA_short'] > last_row['SMA_long']):
        if position != "LONG":
            place_market_order("Buy", SYMBOL, TRADE_AMOUNT)

    # Sell Condition: Short MA crosses below Long MA
    elif (previous_row['SMA_short'] >= previous_row['SMA_long']) and (last_row['SMA_short'] < last_row['SMA_long']):
        if position != "SHORT":
            place_market_order("Sell", SYMBOL, TRADE_AMOUNT)

    print(f"Current Price: {current_price}, Position: {position}")


def main():
    """Main function to run the paper trading bot."""
    print("Starting Bybit Paper Trading Bot...")
    while True:
        trading_logic()

        time.sleep(4 * 60 * 60)  # Run every 4 hours


if __name__ == "__main__":
    if not API_KEY or not API_SECRET:
        print("Error: BYBIT_API_KEY and BYBIT_API_SECRET environment variables must be set.")
    else:
        main()