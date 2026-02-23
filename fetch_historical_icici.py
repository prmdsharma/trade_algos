import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

# Load .env file
load_dotenv()

API_KEY = os.environ.get("ICICI_API_KEY")
SECRET_KEY = os.environ.get("ICICI_SECRET_KEY")
SESSION_TOKEN = os.environ.get("ICICI_SESSION_TOKEN")

def fetch_last_day_data():
    if not all([API_KEY, SECRET_KEY, SESSION_TOKEN]):
        print("Error: ICICI credentials missing in .env")
        return

    # Initialize Breeze
    breeze = BreezeConnect(api_key=API_KEY)
    breeze.generate_session(api_secret=SECRET_KEY, session_token=SESSION_TOKEN)

    # Determine last trading day (approximate: if today is Sun/Mon, go back to Friday)
    today = datetime.now()
    if today.weekday() == 0:  # Monday
        last_day = today - timedelta(days=3)
    elif today.weekday() == 6:  # Sunday
        last_day = today - timedelta(days=2)
    else:
        last_day = today - timedelta(days=1)
    
    date_str = last_day.strftime("%Y-%m-%d")
    print(f"Fetching data for: {date_str}")

    from_date = f"{date_str}T09:15:00.000Z"
    to_date = f"{date_str}T15:30:00.000Z"
    
    print(f"Date range: {from_date} to {to_date}")

    # Fetch data
    # SENSEX is a BSE index. Stock code is BSESEN as per user feedback.
    response = breeze.get_historical_data_v2(
        interval="1minute",
        from_date=from_date,
        to_date=to_date,
        stock_code="BSESEN",
        exchange_code="BSE",
        product_type="cash"
    )

    print(f"API Response Status: {response.get('Status')}")
    if response.get("Status") != 200:
        print(f"Error Details: {response.get('Error')}")

    if response.get("Status") != 200 or "Success" not in response:
        print(f"Error fetching data: {response}")
        return

    data = response["Success"]
    if not data:
        print("No data returned for the selected date.")
        return

    df = pd.DataFrame(data)
    
    # Rename columns to match KiteClientStub expectations
    # ICICI: datetime, open, high, low, close, volume, stock_code, exchange_code
    # Expected: time, open, high, low, close, volume
    df = df.rename(columns={"datetime": "time"})
    df = df[["time", "open", "high", "low", "close", "volume"]]
    
    # Sort by time to ensure chronological order for backtest
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    # Save Spot data to CSV
    output_path = "data/backtest_data/backtest_prices.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Successfully saved {len(df)} Spot candles to {output_path}")

    # --- Option Fetching Logic ---
    print("\n--- Fetching Option Data ---")
    min_spot = df["close"].min()
    max_spot = df["close"].max()
    
    # Strikes are every 100 points
    start_strike = int((min_spot // 100) * 100) - 200
    end_strike = int((max_spot // 100) * 100) + 200
    
    # VERIFIED: Use BSESEN and ISO format for historical options
    expiry_date_breeze = "2026-02-26T07:00:00.000Z"
    
    # Kite symbol parts
    # For Feb 26 monthly expiry, the code is 26FEB
    kite_expiry_code = "26FEB"
    
    options_dir = "data/backtest_data/options"
    os.makedirs(options_dir, exist_ok=True)
    
    for strike in range(start_strike, end_strike + 100, 100):
        for right in ["Call", "Put"]:
            suffix = "CE" if right == "Call" else "PE"
            
            print(f"Fetching {right} data for strike {strike}...")
            try:
                opt_res = breeze.get_historical_data_v2(
                    interval="1minute",
                    from_date=from_date,
                    to_date=to_date,
                    stock_code="BSESEN", # VERIFIED
                    exchange_code="BFO",
                    product_type="Options",
                    expiry_date=expiry_date_breeze, # VERIFIED
                    right=right,
                    strike_price=str(strike)
                )
                
                if opt_res.get("Status") == 200 and "Success" in opt_res and opt_res["Success"]:
                    opt_df = pd.DataFrame(opt_res["Success"])
                    # Convert Breeze "datetime" to "time" (Kite format)
                    opt_df = opt_df.rename(columns={"datetime": "time"})
                    
                    kite_symbol = f"SENSEX{kite_expiry_code}{strike}{suffix}"
                    save_path = f"{options_dir}/{kite_symbol}.csv"
                    opt_df.to_csv(save_path, index=False)
                    print(f"  Saved {len(opt_df)} rows to {kite_symbol}.csv")
                else:
                    print(f"  No data for {strike} {right} ({opt_res.get('Error', 'Unknown error')})")
            except Exception as e:
                print(f"  Error fetching {strike} {right}: {e}")

    print("Option data fetching complete.")

if __name__ == "__main__":
    fetch_last_day_data()
