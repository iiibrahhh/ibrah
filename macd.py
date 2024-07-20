import ta

def calculate_macd(data, period_slow=26, period_fast=12, period_signal=9):
    macd = ta.trend.MACD(data['close'], window_slow=period_slow, window_fast=period_fast, window_sign=period_signal)
    data['macd'] = macd.macd()
    data['macd_signal'] = macd.macd_signal()
    data['macd_diff'] = macd.macd_diff()
    return data
