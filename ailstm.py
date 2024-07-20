import ccxt
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine, text
import os

# Server and database connection details
server = 'ABU-RONZA\\SQLEXPRESS'
database = 'AAcrypto'
username = 'sa'
password = ''  # Replace with your actual password

# Create connection string for SQLAlchemy
connection_string = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server'
engine = create_engine(connection_string)

# Directory to save models
model_dir = 'saved_models'
os.makedirs(model_dir, exist_ok=True)

try:
    with engine.connect() as conn:
        # Check and create CryptocurrencyData table if not exists
        check_table_query = "SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CryptocurrencyData]') AND type in (N'U')"
        table_exists = conn.execute(text(check_table_query)).fetchone()

        if not table_exists:
            create_data_table_sql = '''
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
            '''
            conn.execute(text(create_data_table_sql))
            print("Table 'CryptocurrencyData' created successfully.")
        else:
            print("Table 'CryptocurrencyData' already exists.")

        # Check and create PredictedPrices table if not exists
        check_table_query = "SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PredictedPrices]') AND type in (N'U')"
        table_exists = conn.execute(text(check_table_query)).fetchone()

        if not table_exists:
            create_predictions_table_sql = '''
            CREATE TABLE PredictedPrices (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                Symbol NVARCHAR(50),
                Epoch INT,
                Loss FLOAT,
                LearningDetails NVARCHAR(MAX)
            )
            '''
            conn.execute(text(create_predictions_table_sql))
            print("Table 'PredictedPrices' created successfully.")
        else:
            print("Table 'PredictedPrices' already exists.")

        # Establish connection to Binance exchange
        exchange = ccxt.binance()

        # Fetch top 100 cryptocurrencies by market cap
        markets = exchange.fetch_markets()
        top_symbols = [market['symbol'] for market in markets[:100]]


        # Function to prepare data and train the model
        def prepare_and_train_model(symbol, df, conn):
            if len(df) < 2:
                print(f"Not enough data for symbol {symbol}")
                return

            # Normalize the data
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(df['ClosingPrice'].values.reshape(-1, 1))

            # Split the data into time windows
            sequence_length = 60
            x_data = []
            y_data = []

            for i in range(len(scaled_data) - sequence_length):
                x_data.append(scaled_data[i:i + sequence_length])
                y_data.append(scaled_data[i + sequence_length])

            x_data = np.array(x_data)
            y_data = np.array(y_data)

            # Split the data into training and testing sets
            x_train, x_test, y_train, y_test = train_test_split(x_data, y_data, test_size=0.2, shuffle=False)

            # Load existing model if exists, else build a new model
            model_path = os.path.join(model_dir, f'{symbol}_model.h5')
            if os.path.exists(model_path):
                model = load_model(model_path)
                print(f"Loaded existing model for symbol {symbol}")
            else:
                model = Sequential()
                model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
                model.add(LSTM(units=50))
                model.add(Dense(units=1))
                model.compile(optimizer='adam', loss='mean_squared_error')
                print(f"Built new model for symbol {symbol}")

            # Train the model and record details after each epoch
            learning_details = []
            initial_epoch = 0
            if 'initial_epoch' in conn.execute(
                    text(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'PredictedPrices' AND COLUMN_NAME = 'Epoch'")).fetchone():
                initial_epoch = conn.execute(
                    text(f"SELECT MAX(Epoch) FROM PredictedPrices WHERE Symbol = '{symbol}'")).scalar() or 0

            for epoch in range(initial_epoch + 1, initial_epoch + 11):  # 10 epochs
                model.fit(x_train, y_train, epochs=1, batch_size=32, verbose=0)
                loss = model.evaluate(x_train, y_train, verbose=0)
                learning_details.append(f"Epoch {epoch}: Loss - {loss}")

                # Store the details in the database after each epoch
                with engine.connect() as conn:
                    insert_prediction_sql = '''
                    INSERT INTO PredictedPrices (Symbol, Epoch, Loss, LearningDetails)
                    VALUES (:symbol, :epoch, :loss, :learning_details)
                    '''
                    conn.execute(text(insert_prediction_sql), {
                        'symbol': symbol,
                        'epoch': epoch,
                        'loss': float(loss),
                        'learning_details': learning_details[-1]
                    })

                # Save the model after each epoch
                model.save(model_path)
                print(f"Model saved for symbol {symbol} after epoch {epoch}")

            print(f"Model trained for symbol {symbol}. Final loss: {loss}")


        # Fetch historical data for each symbol and train the model
        for symbol in top_symbols:
            try:
                print(f"Fetching data for symbol: {symbol}")
                query = f"SELECT Timestamp, ClosingPrice FROM CryptocurrencyData WHERE Symbol='{symbol}' ORDER BY Timestamp"
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    df.set_index('Timestamp', inplace=True)
                    prepare_and_train_model(symbol, df, conn)
                else:
                    print(f"No data found for symbol {symbol}")
            except Exception as e:
                print(f"Error processing symbol {symbol}: {e}")

except Exception as e:
    print(f"Error: {e}")

finally:
    print("Connection closed.")
