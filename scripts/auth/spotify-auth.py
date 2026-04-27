#!/usr/bin/env python3
"""Spotify OAuth2 — run on laptop, prints refresh token.
Copy the refresh token into ~/.config/cyberdeck/.env on the Pi.

Usage:
  SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=xxx python3 scripts/auth/spotify-auth.py

Or pass as args:
  python3 scripts/auth/spotify-auth.py --client-id xxx --client-secret xxx
"""
import argparse
import os
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import requests
except ImportError:
    print("Install: pip install requests")
    sys.exit(1)

SCOPE = "user-read-currently-playing user-read-playback-state"
REDIRECT_URI = "http://127.0.0.1:8889/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

received_code: str | None = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        global received_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            received_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authorization complete. Return to terminal.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args: object) -> None:
        pass  # suppress request logs


def main() -> None:
    parser = argparse.ArgumentParser(description="Spotify OAuth2 flow")
    parser.add_argument("--client-id",     default=os.environ.get("SPOTIFY_CLIENT_ID", ""))
    parser.add_argument("--client-secret", default=os.environ.get("SPOTIFY_CLIENT_SECRET", ""))
    args = parser.parse_args()

    client_id     = args.client_id
    client_secret = args.client_secret

    if not client_id or not client_secret:
        print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required.")
        print("Set as env vars or pass --client-id / --client-secret.")
        print("\nTo get credentials:")
        print("  1. Go to developer.spotify.com/dashboard")
        print("  2. Create an app → Settings → Copy Client ID + Client Secret")
        print("  3. Add redirect URI: http://localhost:8889/callback")
        sys.exit(1)

    auth_params = {
        "client_id":     client_id,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("Opening browser for Spotify authorization...")
    webbrowser.open(auth_url)
    print(f"If browser didn't open, visit:\n  {auth_url}\n")

    server = HTTPServer(("localhost", 8889), CallbackHandler)
    print("Waiting for callback on localhost:8889...")
    server.handle_request()

    if received_code is None:
        print("Error: did not receive authorization code.")
        sys.exit(1)

    import base64
    creds_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type":   "authorization_code",
            "code":         received_code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Authorization": f"Basic {creds_b64}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    refresh_token = data.get("refresh_token", "")
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print(f"\nSpotify Refresh Token:\n  {refresh_token}")
    print("\nAdd these to ~/.config/cyberdeck/.env on the Pi:")
    print(f"  SPOTIFY_CLIENT_ID={client_id}")
    print(f"  SPOTIFY_CLIENT_SECRET={client_secret}")
    print(f"  SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
