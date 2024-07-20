import ta

def calculate_rsi(data, period=14):
    data['rsi'] = ta.momentum.RSIIndicator(data['close'], window=period).rsi()
    return data
