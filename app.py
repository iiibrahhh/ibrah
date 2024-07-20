from flask import Flask, jsonify, request, render_template
import requests
import ccxt
import pandas as pd
import ta

app = Flask(__name__)

API_KEY = '5e54e977-66f6-43ac-8d1d-9b25e3a1f78f'
BASE_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'

exchange = ccxt.binance()

def get_historical_data(symbol, timeframe):
    since = exchange.parse8601('2023-01-01T00:00:00Z')
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # تحويل القيم إلى أرقام
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    return df

def calculate_technical_indicators(data):
    data['rsi'] = ta.momentum.RSIIndicator(data['close'], window=14).rsi()
    data['ema'] = ta.trend.EMAIndicator(data['close'], window=14).ema_indicator()
    macd = ta.trend.MACD(data['close'])
    data['macd'] = macd.macd()
    data['macd_signal'] = macd.macd_signal()
    data['sma'] = ta.trend.SMAIndicator(data['close'], window=14).sma_indicator()
    data['adx'] = ta.trend.ADXIndicator(data['high'], data['low'], data['close']).adx()
    data['cci'] = ta.trend.CCIIndicator(data['high'], data['low'], data['close']).cci()
    data['obv'] = ta.volume.OnBalanceVolumeIndicator(data['close'], data['volume']).on_balance_volume()
    data['bband_mavg'] = ta.volatility.BollingerBands(data['close']).bollinger_mavg()
    data['bband_hband'] = ta.volatility.BollingerBands(data['close']).bollinger_hband()
    data['bband_lband'] = ta.volatility.BollingerBands(data['close']).bollinger_lband()
    data['atr'] = ta.volatility.AverageTrueRange(data['high'], data['low'], data['close']).average_true_range()
    data['fi'] = ta.volume.ForceIndex(data['close'], data['volume']).force_index()
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_data', methods=['GET'])
def update_data():
    interval = request.args.get('interval', '15m')
    headers = {'X-CMC_PRO_API_KEY': API_KEY}
    params = {
        'start': '1',
        'limit': '50',
        'sort': 'market_cap',
        'convert': 'USDT'
    }
    response = requests.get(BASE_URL, headers=headers, params=params)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch data from CoinMarketCap'}), 500
    
    data = response.json().get('data', [])
    crypto_data = []
    
    for coin in data:
        symbol = coin['symbol'] + 'USDT'
        try:
            historical_data = get_historical_data(symbol, interval)
            historical_data = calculate_technical_indicators(historical_data)
            last_row = historical_data.iloc[-1]
            
            crypto_info = {
                'symbol': coin['symbol'],
                'price': coin['quote']['USDT']['price'],
                'RSI': last_row['rsi'],
                'RSI_signal': 'Buy' if last_row['rsi'] < 30 else 'Sell' if last_row['rsi'] > 70 else 'Hold',
                'MACD': last_row['macd'],
                'MACD_signal': 'Buy' if last_row['macd'] > last_row['macd_signal'] else 'Sell',
                'SMA': last_row['sma'],
                'SMA_signal': 'Buy' if last_row['close'] > last_row['sma'] else 'Sell',
                'EMA': last_row['ema'],
                'EMA_signal': 'Buy' if last_row['close'] > last_row['ema'] else 'Sell',
                'ADX': last_row['adx'],
                'ADX_signal': 'Buy' if last_row['adx'] > 25 else 'Sell',
                'CCI': last_row['cci'],
                'CCI_signal': 'Buy' if last_row['cci'] < -100 else 'Sell' if last_row['cci'] > 100 else 'Hold',
                'OBV': last_row['obv'],
                'OBV_signal': 'Buy' if last_row['obv'] > last_row['obv'].shift(1) else 'Sell',
                'BBand_mavg': last_row['bband_mavg'],
                'BBand_hband': last_row['bband_hband'],
                'BBand_lband': last_row['bband_lband'],
                'ATR': last_row['atr'],
                'FI': last_row['fi']
            }
            crypto_data.append(crypto_info)
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
            continue
    
    if not crypto_data:
        return jsonify([])  # تأكد من أن الكود يعيد قائمة فارغة إذا لم توجد بيانات
    
    return jsonify(crypto_data)

if __name__ == '__main__':
    app.run(debug=True)
