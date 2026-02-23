import os
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

load_dotenv()

API_KEY = os.environ.get("ICICI_API_KEY")
SECRET_KEY = os.environ.get("ICICI_SECRET_KEY")
SESSION_TOKEN = os.environ.get("ICICI_SESSION_TOKEN")

try:
    breeze = BreezeConnect(api_key=API_KEY)
    breeze.generate_session(api_secret=SECRET_KEY, session_token=SESSION_TOKEN)
    print("Methods:", [m for m in dir(breeze) if 'connect' in m.lower() or 'ws' in m.lower()])
except Exception as e:
    print(f"Error: {e}")
