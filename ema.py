import ta

def calculate_ema(data, period_short=12, period_long=26):
    data['ema_short'] = ta.trend.EMAIndicator(data['close'], window=period_short).ema_indicator()
    data['ema_long'] = ta.trend.EMAIndicator(data['close'], window=period_long).ema_indicator()
    return data
