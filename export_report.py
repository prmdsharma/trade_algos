import sqlite3
import pandas as pd
import os

def export_trades(db_path="trades.db", output_csv="backtest_report.csv"):
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    try:
        df_raw = pd.read_sql_query("SELECT * FROM trades", conn)
        if df_raw.empty:
            print("No trades found in the database.")
            return

        all_records = []
        for _, trade in df_raw.iterrows():
            # 1. Entry Record
            entry_ts = pd.to_datetime(trade['entry_time'])
            entry_rec = {
                'Index': str(trade['id']),
                'Date': entry_ts.strftime('%Y-%m-%d'),
                'Time': entry_ts.strftime('%H:%M:%S'),
                'Type': trade['signal_type'],
                'B/S': 'Buy',
                'Strike': trade['strike'],
                'Qty': trade['qty'],
                'Price': trade['entry_price'],
                'Event': 'ENTRY',
                'EMA9': trade['entry_ema9'],
                'EMA21': trade['entry_ema21'],
                'VWAP': trade['entry_vwap'],
                'Spot_High': trade['entry_spot_high'],
                'Spot_Low': trade['entry_spot_low'],
                'P/L': None,
                'Exit_Reason': None
            }
            all_records.append(entry_rec)

            # 2. Exit Record
            exit_ts = pd.to_datetime(trade['exit_time']) if trade['exit_time'] else None
            exit_rec = {
                'Index': f"{trade['id']}.1",
                'Date': exit_ts.strftime('%Y-%m-%d') if exit_ts else None,
                'Time': exit_ts.strftime('%H:%M:%S') if exit_ts else None,
                'Type': trade['signal_type'],
                'B/S': 'Sell',
                'Strike': trade['strike'],
                'Qty': trade['qty'],
                'Price': trade['exit_price'],
                'Event': 'EXIT',
                'EMA9': trade['exit_ema9'],
                'EMA21': trade['exit_ema21'],
                'VWAP': trade['exit_vwap'],
                'Spot_High': trade['exit_spot_high'],
                'Spot_Low': trade['exit_spot_low'],
                'P/L': trade['pnl'],
                'Exit_Reason': trade['exit_reason']
            }
            all_records.append(exit_rec)

        df_final = pd.DataFrame(all_records)
        
        # Save to CSV
        df_final.to_csv(output_csv, index=False)
        print(f"Successfully exported {len(df_raw)} trades ({len(df_final)} records) to {output_csv}")
        
        # Print a concise summary report
        print("\n=== ENHANCED TRADE REPORT ===")
        print(df_final[["Index", "Time", "Event", "Type", "Price", "P/L", "Exit_Reason"]].to_string(index=False))
        print(f"\nTotal Net P&L: ₹{df_raw['pnl'].sum():.2f}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    # Default to backtest_report.csv, allow overriding via command line
    output = sys.argv[1] if len(sys.argv) > 1 else "backtest_report.csv"
    export_trades(output_csv=output)
