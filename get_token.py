"""
Kite Connect Token Generator

Automates the access token generation flow:
1. Opens the Kite login page in your browser.
2. Starts a local server to capture the redirect with the request_token.
3. Exchanges the request_token for an access_token.
4. Prints the access_token (and optionally writes it to .env).

Usage:
    python get_token.py

Prerequisites:
    pip install kiteconnect

Configuration:
    Set API_KEY and API_SECRET below, or use environment variables:
        export KITE_API_KEY="your_api_key"
        export KITE_API_SECRET="your_api_secret"
"""

import os
import sys
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("ERROR: kiteconnect not installed. Run: pip install kiteconnect")
    sys.exit(1)

# ---- Configuration ----
API_KEY = os.environ.get("KITE_API_KEY", "")
API_SECRET = os.environ.get("KITE_API_SECRET", "")

# Local server to capture the redirect
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 8000

# ---- Globals ----
_captured_token = None


class TokenCaptureHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the request_token from Kite's redirect."""

    def do_GET(self):
        global _captured_token

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "request_token" in params:
            _captured_token = params["request_token"][0]
            # Send a success page back to the browser
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;text-align:center;padding:50px'>"
                b"<h1>&#9989; Token Captured!</h1>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>No request_token found.</h1></body></html>")

        # Shut down the server after handling the request
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


def main():
    global _captured_token

    if not API_KEY:
        print("ERROR: KITE_API_KEY not set.")
        print("  export KITE_API_KEY='your_api_key'")
        sys.exit(1)

    if not API_SECRET:
        print("ERROR: KITE_API_SECRET not set.")
        print("  export KITE_API_SECRET='your_api_secret'")
        sys.exit(1)

    kite = KiteConnect(api_key=API_KEY)

    # Build login URL with our local redirect
    login_url = kite.login_url()
    print(f"\n{'='*50}")
    print("KITE TOKEN GENERATOR")
    print(f"{'='*50}\n")

    # Start local server to capture the redirect
    server = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), TokenCaptureHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    print(f"  Local server listening on http://{REDIRECT_HOST}:{REDIRECT_PORT}")
    print(f"  Opening Kite login in your browser...\n")

    webbrowser.open(login_url)

    print("  Waiting for you to log in at Zerodha...")
    print("  (If the browser didn't open, visit this URL manually:)")
    print(f"  {login_url}\n")

    # Wait for the server to capture the token
    server_thread.join(timeout=120)

    if not _captured_token:
        print("ERROR: Timed out waiting for login (120s). Try again.")
        server.shutdown()
        sys.exit(1)

    print(f"  Request token captured: {_captured_token[:8]}...")

    # Exchange request_token for access_token
    try:
        session = kite.generate_session(_captured_token, api_secret=API_SECRET)
        access_token = session["access_token"]
    except Exception as e:
        print(f"\nERROR: Failed to generate session: {e}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print("  ACCESS TOKEN GENERATED SUCCESSFULLY")
    print(f"{'='*50}\n")
    print(f"  Access Token: {access_token}\n")
    print("  To use it, run:\n")
    print(f'  export KITE_ACCESS_TOKEN="{access_token}"')
    print(f"\n  Then start paper trading:")
    print(f"  python paper_trade.py\n")

    # Optionally write to .env file
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, "w") as f:
            f.write(f'KITE_API_KEY="{API_KEY}"\n')
            f.write(f'KITE_API_SECRET="{API_SECRET}"\n')
            f.write(f'KITE_ACCESS_TOKEN="{access_token}"\n')
        print(f"  Credentials also saved to: {env_path}")
        print(f"  (Access token expires daily — re-run this script each morning)\n")
    except Exception:
        pass  # Non-critical


if __name__ == "__main__":
    main()
