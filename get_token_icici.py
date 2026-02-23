"""
ICICI Direct Breeze Session Token Generator.

Opens the ICICI Direct login page, captures the session token,
and prints it for use.

Usage:
    export ICICI_API_KEY="your_api_key"
    export ICICI_SECRET_KEY="your_secret_key"
    python get_token_icici.py

Prerequisites:
    pip install breeze-connect
"""

import os
import sys
import webbrowser
from dotenv import load_dotenv

# Load .env file
load_dotenv()

try:
    from breeze_connect import BreezeConnect
except ImportError:
    print("ERROR: breeze-connect not installed. Run: pip install breeze-connect")
    sys.exit(1)

API_KEY = os.environ.get("ICICI_API_KEY", "")
SECRET_KEY = os.environ.get("ICICI_SECRET_KEY", "")


def main():
    if not API_KEY:
        print("ERROR: ICICI_API_KEY not set.")
        print("  export ICICI_API_KEY='your_api_key'")
        sys.exit(1)

    if not SECRET_KEY:
        print("ERROR: ICICI_SECRET_KEY not set.")
        print("  export ICICI_SECRET_KEY='your_secret_key'")
        sys.exit(1)

    print(f"\n{'='*50}")
    print("ICICI DIRECT — SESSION TOKEN GENERATOR")
    print(f"{'='*50}\n")

    # Step 1: Open the ICICI login URL
    login_url = f"https://api.icicidirect.com/apiuser/login?api_key={API_KEY}"

    print("  Opening ICICI Direct login in your browser...")
    print(f"  (If it doesn't open, visit this URL manually:)")
    print(f"  {login_url}\n")

    webbrowser.open(login_url)

    # Step 2: The user logs in and gets a session token from the redirect
    print("  After logging in, ICICI will redirect you to your")
    print("  configured redirect URL with a session token.\n")

    session_token = input("  Paste the session token here: ").strip()

    if not session_token:
        print("ERROR: No session token provided.")
        sys.exit(1)

    # Step 3: Verify by generating a session
    try:
        breeze = BreezeConnect(api_key=API_KEY)
        breeze.generate_session(
            api_secret=SECRET_KEY,
            session_token=session_token,
        )
        print(f"\n  ✅ Session generated successfully!")
    except Exception as e:
        print(f"\n  ❌ Failed to generate session: {e}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print("  SESSION TOKEN VERIFIED")
    print(f"{'='*50}\n")
    print(f"  Session Token: {session_token}\n")
    print("  To use it, run:\n")
    print(f'  export ICICI_SESSION_TOKEN="{session_token}"')
    print(f"\n  Then start paper trading:")
    print(f"  python paper_trade.py\n")

    # Save to .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, "w") as f:
            f.write(f'ICICI_API_KEY="{API_KEY}"\n')
            f.write(f'ICICI_SECRET_KEY="{SECRET_KEY}"\n')
            f.write(f'ICICI_SESSION_TOKEN="{session_token}"\n')
        print(f"  Credentials saved to: {env_path}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
