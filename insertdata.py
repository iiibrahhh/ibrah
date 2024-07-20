def analyze_and_store_data():
    logging.info("بدء تحليل وتخزين البيانات.")
    cursor.execute("SELECT CoinID, CoinSymbol FROM Cryptocurrencies")
    coins = cursor.fetchall()
    logging.info(f"تم جلب {len(coins)} عملة من قاعدة البيانات.")

    for coin in coins:
        coin_id, symbol = coin
        logging.info(f"معالجة {symbol} (CoinID: {coin_id})")

        for timeframe in timeframes:
            ohlcv = fetch_historical_data(symbol + '/USDT', timeframe)
            if ohlcv:
                df = calculate_rsi(ohlcv)
                if df.empty:
                    logging.warning(f"لا توجد بيانات كافية لحساب RSI لـ {symbol} بالإطار الزمني {timeframe}.")
                    continue

                df.set_index('timestamp', inplace=True)
                logging.info(f"تم جلب ومعالجة البيانات لـ {symbol} بالإطار الزمني {timeframe}.")

                df['recommendation'] = df['rsi'].apply(lambda x: 'شراء' if x < 30 else 'بيع' if x > 70 else 'احتفاظ')

                for index, row in df.iterrows():
                    try:
                        cursor.execute("""
                            IF NOT EXISTS (SELECT 1 FROM RSI WHERE CoinID = ? AND Timestamp = ? AND Timeframe = ?)
                            BEGIN
                                INSERT INTO RSI (CoinID, Timestamp, Timeframe, RSIValue, Recommendation, CoinSymbol)
                                VALUES (?, ?, ?, ?, ?, ?)
                            END
                            ELSE
                            BEGIN
                                UPDATE RSI SET RSIValue = ?, Recommendation = ?, CoinSymbol = ? WHERE CoinID = ? AND Timestamp = ? AND Timeframe = ?
                            END
                        """, (
                            coin_id, index, timeframe,  # CoinID, Timestamp, Timeframe
                            coin_id, index, timeframe,  # Insert: CoinID, Timestamp, Timeframe
                            row['rsi'], row['recommendation'], symbol,  # Insert: RSIValue, Recommendation, CoinSymbol
                            row['rsi'], row['recommendation'], symbol,  # Update: RSIValue, Recommendation, CoinSymbol
                            coin_id, index, timeframe  # Update: CoinID, Timestamp, Timeframe
                        ))

                        connection.commit()
                        logging.info(f"تم إدراج/تحديث RSI لـ {symbol} في {index} بالإطار الزمني {timeframe}.")
                    except Exception as e:
                        logging.error(
                            f"خطأ في إدراج/تحديث البيانات لـ CoinID {coin_id} في {index} بالإطار الزمني {timeframe}: {e}")

    logging.info("اكتمل تحليل وتخزين البيانات.")
