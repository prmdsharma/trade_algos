# [cite_start]Source: [cite: 12-22]

class SignalEngine:
    def analyze(self, df):
        """
        Analyzes candles for entry signals.
        Enforces 'Signal -> Wait -> Confirmation' by ensuring the trend was already 
        established on the previous candle before allowing an entry on a pullback.
        """
        if len(df) < 2:
            return None

        # Current candle (Confirmation candidates)
        curr = df.iloc[-1]
        ema9 = curr['EMA9']
        ema21 = curr['EMA21']
        close = curr['close']
        open_price = curr['open']
        low = curr['low']
        high = curr['high']

        # Previous candle (Signal/Trend check)
        prev = df.iloc[-2]
        prev_ema9 = prev['EMA9']
        prev_ema21 = prev['EMA21']

        # [cite_start]CALL Conditions [cite: 13-17]
        # EMA9 > EMA21 | Bullish Candle | Pullback near EMA9
        # NEW: Ensure trend was already bullish on prev candle
        is_bullish = close > open_price
        pullback_bull = (low <= ema9 * 1.0005) and (close > ema9)
        trend_stable_bull = (ema9 > ema21) and (prev_ema9 > prev_ema21)
        
        if trend_stable_bull and pullback_bull and is_bullish:
            return "CE"

        # [cite_start]PUT Conditions [cite: 18-22]
        # EMA9 < EMA21 | Bearish Candle | Pullback near EMA9
        # NEW: Ensure trend was already bearish on prev candle
        is_bearish = close < open_price
        pullback_bear = (high >= ema9 * 0.9995) and (close < ema9)
        trend_stable_bear = (ema9 < ema21) and (prev_ema9 < prev_ema21)

        if trend_stable_bear and pullback_bear and is_bearish:
            return "PE"
            
        return None