import os
import time
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

load_dotenv()

API_KEY = os.environ.get("ICICI_API_KEY")
SECRET_KEY = os.environ.get("ICICI_SECRET_KEY")
SESSION_TOKEN = os.environ.get("ICICI_SESSION_TOKEN")

def on_ticks(tick):
    print(f"DEBUG TICK: {tick}")

breeze = BreezeConnect(api_key=API_KEY)
breeze.generate_session(api_secret=SECRET_KEY, session_token=SESSION_TOKEN)

breeze.on_ticks = on_ticks
print("Connecting to WebSocket...")
breeze.ws_connect()

print("Subscribing to BSESEN:BCE...")
# Try both BSE and NSE just in case, though Sensex is BSE
breeze.subscribe_feeds(exchange_code="BSE", stock_code="BSESEN")

print("Waiting 30 seconds for ticks...")
try:
    for i in range(30):
        time.sleep(1)
        if i % 5 == 0:
            print(f"Heartbeat {i}...")
except KeyboardInterrupt:
    pass

breeze.ws_disconnect()
print("Disconnected.")
