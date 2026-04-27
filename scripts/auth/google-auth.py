#!/usr/bin/env python3
"""Google Calendar OAuth2 — run on laptop, produces token.json.
Then SCP token.json to Pi: ~/.config/cyberdeck/google-token.json

Usage:
  python3 scripts/auth/google-auth.py --credentials /path/to/credentials.json
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Install: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Calendar OAuth2 flow")
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Path to credentials.json downloaded from Google Cloud Console",
    )
    parser.add_argument(
        "--output",
        default="google-token.json",
        help="Output path for the token file (default: google-token.json)",
    )
    args = parser.parse_args()

    creds_path = Path(args.credentials)
    if not creds_path.exists():
        print(f"Error: credentials file not found: {creds_path}")
        print("\nTo get credentials.json:")
        print("  1. Go to console.cloud.google.com")
        print("  2. Create a project → Enable Google Calendar API")
        print("  3. OAuth consent screen → External → add your email")
        print("  4. Credentials → Create OAuth client ID → Desktop app → Download JSON")
        sys.exit(1)

    print(f"Starting OAuth flow with {creds_path}...")
    print("A browser window will open. Grant access, then return here.")

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=8888, prompt="consent")

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(token_data, indent=2))

    print(f"\nToken saved to {output_path}")
    print("\nSCP to Pi:")
    print(f"  scp {output_path} pi@<pi-ip>:~/.config/cyberdeck/google-token.json")
    print("\nAlso SCP credentials.json:")
    print(f"  scp {creds_path} pi@<pi-ip>:~/.config/cyberdeck/google-credentials.json")
    print("\nThen update ~/.config/cyberdeck/.env on the Pi:")
    print("  GOOGLE_CALENDAR_CREDENTIALS_PATH=/home/pi/.config/cyberdeck/google-credentials.json")
    print("  GOOGLE_CALENDAR_TOKEN_PATH=/home/pi/.config/cyberdeck/google-token.json")


if __name__ == "__main__":
    main()
