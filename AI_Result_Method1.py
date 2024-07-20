import pyodbc
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.callbacks import EarlyStopping

# SQL Server connection details
server = 'ABU-RONZA\\SQLEXPRESS'
database = 'AAcrypto'
username = 'sa'
password = ''

connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Connect to the SQL Server database
try:
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()
    print("Connected to the database successfully!")
except pyodbc.Error as e:
    print(f"Error connecting to SQL Server: {e}")
    exit(1)

# Fetch data from all indicator tables and merge
query = """
SELECT
    r.Timestamp,
    r.RSIValue,
    a.ATRValue,
    b.BBUpperBand, b.BBLowerBand, b.BBMiddleBand,
    c.CCIValue,
    e.EMAValue,
    m.MACDValue, m.MACDSignal,
    s.SMAValue,
    st.StochasticK, st.StochasticD
FROM RSI r
JOIN ATR a ON r.CoinID = a.CoinID AND r.Timestamp = a.Timestamp
JOIN BollingerBands b ON r.CoinID = b.CoinID AND r.Timestamp = b.Timestamp
JOIN cci c ON r.CoinID = c.CoinID AND r.Timestamp = c.Timestamp
JOIN EMA e ON r.CoinID = e.CoinID AND r.Timestamp = e.Timestamp
JOIN MACD m ON r.CoinID = m.CoinID AND r.Timestamp = m.Timestamp
JOIN SMA s ON r.CoinID = s.CoinID AND r.Timestamp = s.Timestamp
JOIN stoch st ON r.CoinID = st.CoinID AND r.Timestamp = st.Timestamp
WHERE r.Timeframe = '5m' AND a.Timeframe = '5m' AND b.Timeframe = '5m' AND c.Timeframe = '5m' 
AND e.Timeframe = '5m' AND m.Timeframe = '5m' AND s.Timeframe = '5m' AND st.Timeframe = '5m'
"""
cursor.execute(query)
rows = cursor.fetchall()

# Convert fetched data to a DataFrame
columns = [
    'Timestamp', 'RSIValue', 'ATRValue', 'BBUpperBand', 'BBLowerBand', 'BBMiddleBand', 'CCIValue',
    'EMAValue', 'MACDValue', 'MACDSignal', 'SMAValue', 'StochasticK', 'StochasticD'
]
df = pd.DataFrame([tuple(row) for row in rows], columns=columns)

# Print fetched data to debug
print(f"Fetched {len(rows)} rows")
print(df.head())

# Feature selection and preprocessing
X = df.drop(columns=['Timestamp'])
y = np.where((df['RSIValue'] > 70), -1, np.where((df['RSIValue'] < 30), 1, 0))

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train/test split while keeping the original indices
X_train, X_test, y_train, y_test, train_idx, test_idx = train_test_split(X_scaled, y, df.index, test_size=0.2, random_state=42)

# Build ANN model
model = Sequential([
    Dense(64, input_dim=X_train.shape[1], activation='relu'),
    Dense(32, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Training with early stopping
early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=32, callbacks=[early_stopping])

# Evaluate the model
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Model accuracy: {accuracy * 100:.2f}%")

# Predict recommendations
predictions = model.predict(X_test)
recommendations = np.where(predictions > 0.5, 'Buy', 'Sell')

# Insert predictions into AI_Result_Method1 table
try:
    for idx, recommendation in zip(test_idx, recommendations):
        timestamp = df.loc[idx, 'Timestamp']
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM AI_Result_Method1 WHERE Timestamp = ?)
            BEGIN
                INSERT INTO AI_Result_Method1 (Timestamp, Recommendation)
                VALUES (?, ?)
            END
            ELSE
            BEGIN
                UPDATE AI_Result_Method1
                SET Recommendation = ?
                WHERE Timestamp = ?
            END
        """, (timestamp, timestamp, recommendation[0], recommendation[0], timestamp))
    connection.commit()
    print("Predictions inserted/updated successfully in AI_Result_Method1 table!")
except pyodbc.Error as e:
    print(f"Error inserting/updating predictions: {e}")
finally:
    cursor.close()
    connection.close()
