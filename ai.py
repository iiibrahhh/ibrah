import pyodbc
import ccxt
import pandas as pd
from datetime import datetime

# Server and database connection details
server = 'ABU-RONZA\\SQLEXPRESS'
database = 'AAcrypto'
username = 'sa'
password = ''  # Replace with your actual password

# Connect to SQL Server
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

try:
    # Define table schema and create table if not exists
    create_table_sql = '''
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CryptocurrencyData]') AND type in (N'U'))
    BEGIN
        CREATE TABLE CryptocurrencyData (
            Id INT IDENTITY(1,1) PRIMARY KEY,
            Timestamp DATETIME,
            Symbol NVARCHAR(50),
            OpeningPrice FLOAT,
            High FLOAT,
            Low FLOAT,
            ClosingPrice FLOAT,
            Volume FLOAT
        )
    END
    '''
    cursor.execute(create_table_sql)
    conn.commit()
    print("Table 'CryptocurrencyData' created successfully.")

    # Establish connection to Binance exchange
    exchange = ccxt.binance()

    # Fetch top 100 cryptocurrencies by market cap
    markets = exchange.fetch_markets()
    top_symbols = [market['symbol'] for market in markets[:100]]

    # Fetch historical data for each symbol and store in SQL Server
    for symbol in top_symbols:
        try:
            timeframes = ['15m', '30m', '1h', '1d']
            for timeframe in timeframes:
                historical_data = exchange.fetch_ohlcv(symbol, timeframe)
                columns = ['Timestamp', 'OpeningPrice', 'High', 'Low', 'ClosingPrice', 'Volume']
                df = pd.DataFrame(historical_data, columns=columns)

                # Format Timestamp column
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')  # Convert Unix timestamp to datetime

                # Insert data into SQL Server table
                for index, row in df.iterrows():
                    insert_sql = '''
                    INSERT INTO CryptocurrencyData (Timestamp, Symbol, OpeningPrice, High, Low, ClosingPrice, Volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    '''
                    values = (row['Timestamp'], symbol, row['OpeningPrice'], row['High'], row['Low'], row['ClosingPrice'], row['Volume'])
                    cursor.execute(insert_sql, values)
                    conn.commit()

                print(f"Data for symbol {symbol} and timeframe {timeframe} inserted successfully.")

        except Exception as e:
            print(f"Error fetching data for symbol {symbol} and timeframe {timeframe}: {e}")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Close connection
    cursor.close()
    conn.close()
    print("Connection closed.")
