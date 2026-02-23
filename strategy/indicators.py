import pandas as pd
# [cite_start]Source: [cite: 8-11]

class IndicatorEngine:
    def calculate(self, df):
        """Calculates EMA9, EMA21, and VWAP on 1-min data."""
        df = df.copy()
        
        # [cite_start]EMA Calculations [cite: 9, 10]
        df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        # [cite_start]VWAP Calculation (Intraday) [cite: 11]
        df['cum_vol'] = df['volume'].cumsum()
        df['cum_vol_price'] = (df['close'] * df['volume']).cumsum()
        df['VWAP'] = df['cum_vol_price'] / df['cum_vol']
        
        return df.iloc[-1] # Return latest row