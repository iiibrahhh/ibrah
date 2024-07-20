# BollingerBands.py

import ccxt
import pandas as pd
from ta.volatility import BollingerBands
import pyodbc

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
    'okx',  # Use 'okex' instead of 'okx'
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

def calculate_bollinger_bands(data, window=20, window_dev=2):
    # Convert data to DataFrame
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    print("Converted data to DataFrame.")

    # Calculate Bollinger Bands using ta library
    indicator_bb = BollingerBands(close=df['close'], window=window, window_dev=window_dev)
    df['bb_upperband'] = indicator_bb.bollinger_hband()
    df['bb_lowerband'] = indicator_bb.bollinger_lband()
    df['bb_middleband'] = indicator_bb.bollinger_mavg()
    print("Calculated Bollinger Bands.")

    return df

def analyze_and_store_bollinger_bands_data():
    print("Starting to analyze and store Bollinger Bands data.")
    cursor.execute("SELECT CoinID, CoinSymbol FROM Cryptocurrencies")
    coins = cursor.fetchall()
    print(f"Fetched {len(coins)} coins from the database.")

    for coin in coins:
        coin_id, symbol = coin
        print(f"Processing {symbol} (CoinID: {coin_id})")

        if symbol == 'USDT':
            print(f"Skipping {symbol} as per request.")
            continue

        # Create a dictionary to store Bollinger Bands data for each timeframe
        bb_data = {timeframe: [] for timeframe in timeframes}

        for timeframe in timeframes:
            ohlcv = fetch_historical_data(exchanges, symbol + '/USDT', timeframe)
            if ohlcv:
                df = calculate_bollinger_bands(ohlcv)
                df.set_index('timestamp', inplace=True)
                print(f"Fetched and processed data for {symbol} with timeframe {timeframe}.")
                bb_data[timeframe].append(df)  # Append dataframe to the list

        # After processing all timeframes, insert/update data in the database
        for timeframe, dataframes in bb_data.items():
            for df in dataframes:
                for index, row in df.iterrows():
                    try:
                        # Determine recommendation based on Bollinger Bands values
                        if row['close'] < row['bb_lowerband']:
                            recommendation = 'Buy'
                        elif row['close'] > row['bb_upperband']:
                            recommendation = 'Sell'
                        else:
                            recommendation = 'Hold'

                        cursor.execute("""
                            IF NOT EXISTS (SELECT 1 FROM BollingerBands WHERE CoinID = ? AND Timestamp = ? AND Timeframe = ?)
                            BEGIN
                                INSERT INTO BollingerBands (CoinID, Timestamp, Timeframe, BBUpperBand, BBLowerBand, BBMiddleBand, CoinSymbol, Recommendation)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            END
                            ELSE
                            BEGIN
                                UPDATE BollingerBands SET BBUpperBand = ?, BBLowerBand = ?, BBMiddleBand = ?, CoinSymbol = ?, Recommendation = ?
                                WHERE CoinID = ? AND Timestamp = ? AND Timeframe = ?
                            END
                            """, (
                            coin_id, index, timeframe,  # For SELECT and INSERT: CoinID, Timestamp, Timeframe
                            coin_id, index, timeframe, row['bb_upperband'], row['bb_lowerband'], row['bb_middleband'], symbol, recommendation,
                            # For INSERT: Corresponding values
                            row['bb_upperband'], row['bb_lowerband'], row['bb_middleband'], symbol, recommendation,  # For UPDATE: Corresponding values
                            coin_id, index, timeframe  # For UPDATE: CoinID, Timestamp, Timeframe
                        ))

                        connection.commit()
                        print(f"Inserted/Updated Bollinger Bands for {symbol} at {index} with timeframe {timeframe}.")
                    except Exception as e:
                        print(f"Error inserting/updating data for CoinID {coin_id} at {index} with timeframe {timeframe}: {e}")

    print("Completed analysis and storage of Bollinger Bands data.")

# Start the analysis and storage process
analyze_and_store_bollinger_bands_data()
