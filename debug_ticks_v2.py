import os
import time
import logging
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

# Configure logging to see internal Breeze logs
logging.basicConfig(level=logging.DEBUG)
load_dotenv()

API_KEY = os.environ.get("ICICI_API_KEY")
SECRET_KEY = os.environ.get("ICICI_SECRET_KEY")
SESSION_TOKEN = os.environ.get("ICICI_SESSION_TOKEN")

def on_ticks(tick):
    print(f"!!! TICK RECEIVED: {tick}")

def on_error(err):
    print(f"!!! ERROR: {err}")

breeze = BreezeConnect(api_key=API_KEY)
try:
    print("Generating session...")
    breeze.generate_session(api_secret=SECRET_KEY, session_token=SESSION_TOKEN)
except Exception as e:
    print(f"Session generation failed: {e}")
    exit(1)

breeze.on_ticks = on_ticks
# breeze.on_error = on_error # Not sure if this exists but good to try

print("Connecting to WebSocket...")
breeze.ws_connect()
time.sleep(5)  # Give it time to connect

print("Subscribing to BSESEN:BSE...")
try:
    # Most common for Sensex spot
    res = breeze.subscribe_feeds(exchange_code="BSE", stock_code="BSESEN")
    print(f"Subscribe BSESEN:BSE result: {res}")
except Exception as e:
    print(f"Subscribe BSESEN:BSE failed: {e}")

print("Waiting for ticks (60s)...")
start_time = time.time()
while time.time() - start_time < 60:
    time.sleep(5)
    print(f"Still waiting... {int(time.time() - start_time)}s")

breeze.ws_disconnect()
print("Test complete.")
