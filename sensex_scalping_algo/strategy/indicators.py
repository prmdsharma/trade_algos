import pandas as pd
# [cite_start]Source: [cite: 8-11]

class IndicatorEngine:
    def calculate(self, df):
        """Calculates EMA9 and EMA21 on 1-min data."""
        df = df.copy()
        
        # [cite_start]EMA Calculations [cite: 9, 10]
        df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        
        return df