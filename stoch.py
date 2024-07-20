import ccxt
import pandas as pd
from ta.momentum import StochasticOscillator
import pyodbc
import schedule
import time

# Server and database connection details
server = 'ABU-RONZA\\SQLEXPRESS'
database = 'AAcrypto'
username = 'sa'
password = ''

# ODBC connection string
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Connect to SQL Server
try:
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()
    # Set transaction isolation level
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    print("Connected to SQL Server successfully.")
except pyodbc.Error as e:
    print(f"Error connecting to SQL Server: {e}")
    exit(1)

# List of exchanges to use (only exchange IDs)
exchanges = [
    'binance',
    'coinbase',
    'kraken',
    'bitfinex',
    'huobi',
    'okx',
    'gateio',
    'bybit',
    'bitflyer',
]

# List of timeframes to use
timeframes = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']

def fetch_historical_data(exchange_list, symbol, timeframe='30m', limit=500):
    for exchange_id in exchange_list:
        exchange = getattr(ccxt, exchange_id)()
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if ohlcv:
                print(f"Fetched data from {exchange.id} for {symbol}")
                return ohlcv
        except Exception as e:
            print(f"Error fetching data from {exchange.id} for {symbol}: {e}")
            continue

    print(f"No data available for {symbol} on the specified exchanges.")
    return []

def calculate_stoch(data):
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    print("Converted data to DataFrame.")

    stoch_indicator = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
    df['stoch_k'] = stoch_indicator.stoch()
    df['stoch_d'] = stoch_indicator.stoch_signal()
    print("Calculated Stochastic Oscillator.")

    # Add recommendation based on Stochastic Oscillator
    df['SignalValue'] = df.apply(lambda row: 'Buy' if row['stoch_k'] < 20 and row['stoch_d'] < 20 else 'Sell' if row['stoch_k'] > 80 and row['stoch_d'] > 80 else 'Hold', axis=1)
    print("Calculated SignalValue.")

    return df

def analyze_and_store_stoch_data():
    print("Starting to analyze and store Stochastic Oscillator data.")
    cursor.execute("SELECT CoinID, CoinSymbol FROM Cryptocurrencies")
    coins = cursor.fetchall()
    print(f"Fetched {len(coins)} coins from the database.")

    for coin in coins:
        coin_id, symbol = coin
        print(f"Processing {symbol} (CoinID: {coin_id})")

        if symbol == 'USDT':
            print(f"Skipping {symbol} as per request.")
            continue

        for timeframe in timeframes:
            ohlcv = fetch_historical_data(exchanges, symbol + '/USDT', timeframe)
            if ohlcv:
                df = calculate_stoch(ohlcv)
                df.set_index('timestamp', inplace=True)

                for index, row in df.iterrows():
                    try:
                        cursor.execute("""
                            IF NOT EXISTS (SELECT 1 FROM stoch WHERE CoinID = ? AND Timestamp = ? AND Timeframe = ?)
                            BEGIN
                                INSERT INTO stoch (CoinID, Timestamp, Timeframe, StochasticK, StochasticD, SignalValue, CoinSymbol)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            END
                            ELSE
                            BEGIN
                                UPDATE stoch SET StochasticK = ?, StochasticD = ?, SignalValue = ?, CoinSymbol = ?
                                WHERE CoinID = ? AND Timestamp = ? AND Timeframe = ?
                            END
                            """, (
                            coin_id, index, timeframe,  # For SELECT and INSERT: CoinID, Timestamp, Timeframe
                            coin_id, index, timeframe, row['stoch_k'], row['stoch_d'], row['SignalValue'], symbol,
                            # For INSERT: Corresponding values
                            row['stoch_k'], row['stoch_d'], row['SignalValue'], symbol,  # For UPDATE: Corresponding values
                            coin_id, index, timeframe  # For UPDATE: CoinID, Timestamp, Timeframe
                        ))

                        connection.commit()
                        print(f"Inserted/Updated Stochastic Oscillator for {symbol} at {index} with timeframe {timeframe}.")
                    except Exception as e:
                        print(f"Error inserting/updating data for CoinID {coin_id} at {index} with timeframe {timeframe}: {e}")

    print("Completed analysis and storage of Stochastic Oscillator data.")

# Schedule the analysis and storage to run every 5 seconds
schedule.every(5).seconds.do(analyze_and_store_stoch_data)

# Run the scheduled tasks
while True:
    schedule.run_pending()
    time.sleep(1)
