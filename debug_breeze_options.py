import os
from breeze_connect import BreezeConnect
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ICICI_API_KEY")
SECRET_KEY = os.environ.get("ICICI_SECRET_KEY")
SESSION_TOKEN = os.environ.get("ICICI_SESSION_TOKEN")

breeze = BreezeConnect(api_key=API_KEY)
breeze.generate_session(api_secret=SECRET_KEY, session_token=SESSION_TOKEN)

# Find active contracts for Feb 20
print("\n--- Finding Active SENSEX Contracts for Feb 20 ---")
# BSE Sensex Weekly Expiry is Tuesday.
# Feb 20, 2026 is Friday.
# Previous Tuesday was Feb 17.
# Next Tuesday is Feb 24.
# Monthly Expiry is Feb 26 (Thursday).
likely_expiries = [
    "2026-02-17T07:00:00.000Z", # Already expired but might have historical data?
    "2026-02-20T07:00:00.000Z", # Maybe it was Friday?
    "2026-02-24T07:00:00.000Z", # Next weekly
    "2026-02-26T07:00:00.000Z", # Monthly
]

for exp in likely_expiries:
    print(f"\nTesting Expiry: {exp}")
    try:
        res = breeze.get_historical_data_v2(
            interval="1minute",
            from_date="2026-02-20T09:15:00.000Z",
            to_date="2026-02-20T09:20:00.000Z",
            exchange_code="BFO",
            stock_code="BSESEN",
            product_type="Options",
            expiry_date=exp,
            right="Call",
            strike_price="82500"
        )
        count = len(res.get("Success", [])) if res.get("Success") else 0
        print(f"  Result: {res.get('Status')} | Count: {count}")
        if count > 0:
            print(f"!!! SUCCESS with {exp} !!!")
    except Exception as e:
        print(f"  Error: {e}")
