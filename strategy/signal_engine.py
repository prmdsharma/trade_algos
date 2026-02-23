# [cite_start]Source: [cite: 12-22]

class SignalEngine:
    def analyze(self, candle):
        ema9 = candle['EMA9']
        ema21 = candle['EMA21']
        vwap = candle['VWAP']
        close = candle['close']
        open_price = candle['open']
        low = candle['low']
        high = candle['high']
        
        # [cite_start]CALL Conditions [cite: 13-17]
        # EMA9 > EMA21 | Price > VWAP | Bullish Candle | Pullback near EMA9
        is_bullish = close > open_price
        pullback_bull = (low <= ema9 * 1.0005) and (close > ema9)
        
        if (ema9 > ema21) and pullback_bull and is_bullish:
            return "CE"

        # [cite_start]PUT Conditions [cite: 18-22]
        # EMA9 < EMA21 | Bearish Candle | Pullback near EMA9
        is_bearish = close < open_price
        pullback_bear = (high >= ema9 * 0.9995) and (close < ema9)

        if (ema9 < ema21) and pullback_bear and is_bearish:
            return "PE"
            
        return None