import requests
import pyodbc
import subprocess
import os
import sys
import schedule
import time

# Server and database connection details
server = 'ABU-RONZA\\SQLEXPRESS'
database = 'AAcrypto'
username = 'sa'
password = ''

# ODBC connection string
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'


def update_data():
    try:
        # Connect to database
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Fetch top 100 cryptocurrencies from CoinMarketCap
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        parameters = {
            'start': '1',
            'limit': '100',
            'sort': 'market_cap',
            'convert': 'USDt'
        }
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': 'YOUR_API_KEY',  # Use your own API key here
        }

        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()

        if response.status_code == 200:
            # Clear the existing data in the table
            cursor.execute("DELETE FROM Cryptocurrencies")

            # Insert new data into database
            for currency in data['data']:
                id = currency['id']
                name = currency['name']
                symbol = currency['symbol']
                rank = currency['cmc_rank']
                cursor.execute("INSERT INTO Cryptocurrencies (CoinID, CoinName, CoinSymbol, Rank) VALUES (?, ?, ?, ?)",
                               (id, name, symbol, rank))

            # Commit changes
            connection.commit()
            print("All data updated successfully!")

        else:
            print(f"Failed to fetch data: {response.status_code}, {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinMarketCap: {e}")

    except pyodbc.Error as e:
        print(f"Error connecting to SQL Server: {e}")

    finally:
        # Close cursor and connection
        cursor.close()
        connection.close()


def execute_scripts():
    # List of exchanges to use (only exchange IDs)
    exchanges = [
        'binance',
        # Add more exchanges if needed
    ]

    # Paths to the scripts
    scripts = {
        'rsi': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\rsi.py',
        'macd': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\macd.py',
        'ailstm': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\ailstm.py',
        'atr': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\atr.py',
        'BollingerbandsBB': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\BollingerbandsBB.py',
        'cci': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\cci.py',
        'ema': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\ema.py',
        'sma': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\sma.py',
        'stoch': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\stoch.py',
        'insertdata': 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test\\insertdata.py'
    }

    # Execute each script if found
    python_executable = sys.executable  # Get full path of the current Python interpreter

    for name, path in scripts.items():
        if os.path.exists(path):
            print(f"Found {name}.py at {path}")
            subprocess.Popen([python_executable, path], shell=True, env=dict(EXCHANGES=",".join(exchanges)))
        else:
            print(f"{name}.py not found at {path}")


def job():
    update_data()
    execute_scripts()


# Schedule the job every hour
schedule.every().hour.do(job)

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)
