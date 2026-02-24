import sqlite3
import pandas as pd
import os

def export_trades(db_path="database/trades.db", output_csv="backtest_report.csv", report_date=None):
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    try:
        query = "SELECT * FROM trades"
        if report_date:
            # report_date should be "YYYY-MM-DD" string or datetime.date
            date_str = str(report_date)
            query += f" WHERE date(entry_time) = '{date_str}'"
            print(f"Filtering report for date: {date_str}")
            
        df_raw = pd.read_sql_query(query, conn)
        if df_raw.empty:
            print(f"No trades found {'for ' + str(report_date) if report_date else ''} in the database.")
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
                'Spot': trade['entry_spot_close'],
                'EMA9': trade['entry_ema9'],
                'EMA21': trade['entry_ema21'],
                'P/L': None,
                'Exit_Reason': None
            }
            all_records.append(entry_rec)

            # 2. Exit Record
            exit_ts = pd.to_datetime(trade['exit_time']) if trade['exit_time'] else None
            exit_rec = {
                'Index': f"{trade['id']}.1",
                'Date': exit_ts.strftime('%Y-%m-%d') if pd.notnull(exit_ts) else None,
                'Time': exit_ts.strftime('%H:%M:%S') if pd.notnull(exit_ts) else "OPEN",
                'Type': trade['signal_type'],
                'B/S': 'Sell',
                'Strike': trade['strike'],
                'Qty': trade['qty'],
                'Price': trade['exit_price'] if trade['exit_price'] else "OPEN",
                'Event': 'EXIT',
                'Spot': trade['exit_spot_close'] if trade['exit_spot_close'] else "OPEN",
                'EMA9': trade['exit_ema9'],
                'EMA21': trade['exit_ema21'],
                'P/L': trade['pnl'] if trade['pnl'] is not None else "OPEN",
                'Exit_Reason': trade['exit_reason'] if trade['exit_reason'] else "OPEN"
            }
            all_records.append(exit_rec)

        df_final = pd.DataFrame(all_records)
        
        # Save to CSV
        df_final.to_csv(output_csv, index=False)
        print(f"Successfully exported {len(df_raw)} trades ({len(df_final)} records) to {output_csv}")
        
        # Print a concise summary report
        print("\n=== ENHANCED TRADE REPORT ===")
        cols = ["Index", "Time", "Event", "Type", "Price", "Spot", "EMA9", "EMA21", "P/L", "Exit_Reason"]
        print(df_final[cols].to_string(index=False))
        print(f"\nTotal Net P&L: ₹{df_raw['pnl'].sum():.2f}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    # Usage: python export_report.py [output_csv] [date YYYY-MM-DD]
    output = sys.argv[1] if len(sys.argv) > 1 else "backtest_report.csv"
    date_filter = sys.argv[2] if len(sys.argv) > 2 else None
    
    if date_filter == "today":
        date_filter = datetime.now().strftime("%Y-%m-%d")
        
    export_trades(output_csv=output, report_date=date_filter)
