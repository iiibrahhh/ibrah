import requests
import pyodbc
import subprocess
import os
import sys
import time

# Server and database connection details
server = 'ABU-RONZA\\SQLEXPRESS'
database = 'AAcrypto'
username = 'sa'
password = ''

# ODBC connection string
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Connection setup
try:
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()
except pyodbc.Error as e:
    print(f"Error connecting to SQL Server: {e}")
    exit(1)

# Fetch top 100 cryptocurrencies from CoinMarketCap
url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
parameters = {
    'start': '1',
    'limit': '150',
    'sort': 'market_cap',
    'convert': 'USDt'
}
headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': '5e54e977-66f6-43ac-8d1d-9b25e3a1f78f',  # Use your own API key here
}

try:
    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()

    if response.status_code == 200:
        # Insert data into database, avoiding duplicates
        for currency in data['data']:
            id = currency['id']
            name = currency['name']
            symbol = currency['symbol']
            rank = currency['cmc_rank']

            # Check if the currency already exists
            cursor.execute("SELECT COUNT(*) FROM Cryptocurrencies WHERE CoinID = ?", (id,))
            if cursor.fetchone()[0] == 0:
                # Insert new currency
                cursor.execute("INSERT INTO Cryptocurrencies (CoinID, CoinName, CoinSymbol, Rank) VALUES (?, ?, ?, ?)",
                               (id, name, symbol, rank))

        # Commit changes
        connection.commit()
        print("Data inserted successfully!")
    else:
        print(f"Failed to fetch data: {response.status_code}, {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data from CoinMarketCap: {e}")

finally:
    # Close cursor and connection
    cursor.close()
    connection.close()

# List of scripts to execute
scripts = [
    'rsi.py',
    'macd.py',
    'ailstm.py',
    'atr.py',
    'BollingerbandsBB.py',
    'cci.py',
    'ema.py',
    'sma.py',
    'stoch.py',
    'insertdata.py'
]

# Path to the directory containing the scripts
script_dir = 'C:\\Users\\iiibr\\OneDrive\\Desktop\\Crypto\\test'

# Function to run a script
def run_script(script_name):
    script_path = os.path.join(script_dir, script_name)
    if os.path.exists(script_path):
        print(f"Found {script_name} at {script_path}")
        python_executable = sys.executable  # Get full path of the current Python interpreter
        return subprocess.Popen([python_executable, script_path], shell=True, env=os.environ.copy())
    else:
        print(f"{script_name} not found at {script_path}")
        return None

# Start all scripts
processes = {script: run_script(script) for script in scripts}

# Monitor the scripts and restart if any of them stops
while True:
    for script, process in processes.items():
        if process.poll() is not None:  # Process has terminated
            print(f"{script} has stopped. Restarting...")
            processes[script] = run_script(script)
    time.sleep(10)
