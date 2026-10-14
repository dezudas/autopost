#!/usr/bin/env python3
"""
Helper script to generate a permanent YouTube OAuth2 Refresh Token.
Run this locally whenever you need to obtain or refresh YOUTUBE_REFRESH_TOKEN.

Usage:
    python scripts/get_youtube_token.py
"""

import http.server
import json
import os
import socketserver
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

PORT = 8080
REDIRECT_URI = f"http://localhost:{PORT}"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f8fafc;">
                    <h1 style="color: #4ade80;">Authorization Successful!</h1>
                    <p>You can close this tab and return to your terminal.</p>
                </body>
                </html>
            """)
        elif "error" in params:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            err = params['error'][0]
            self.wfile.write(f"<h1>Authorization Failed</h1><p>{err}</p>".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence default HTTP server logging
        return


def get_tokens():
    print("=" * 60)
    print("   YouTube OAuth2 Refresh Token Generator")
    print("=" * 60)
    print()

    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()

    if not client_id:
        client_id = input("Enter your YOUTUBE_CLIENT_ID: ").strip()
    else:
        print(f"Using YOUTUBE_CLIENT_ID from environment ({client_id[:12]}...)")

    if not client_secret:
        client_secret = input("Enter your YOUTUBE_CLIENT_SECRET: ").strip()
    else:
        print("Using YOUTUBE_CLIENT_SECRET from environment (***)")

    if not client_id or not client_secret:
        print("\nError: Both Client ID and Client Secret are required.")
        sys.exit(1)

    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Ensures refresh token is always returned
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)

    print("\nStarting local server on http://localhost:8080...")
    try:
        server = socketserver.TCPServer(("localhost", PORT), OAuthCallbackHandler)
    except OSError:
        print(f"Port {PORT} is already in use. Please free port {PORT} and try again.")
        sys.exit(1)

    print(f"\nOpening browser for authorization:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for you to authorize in the browser...")
    while OAuthCallbackHandler.auth_code is None:
        server.handle_request()

    auth_code = OAuthCallbackHandler.auth_code
    server.server_close()

    print("\nAuthorization code received! Exchanging for tokens...")

    post_data = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=post_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            token_data = json.loads(error_body)
        except Exception:
            token_data = {"error": error_body}
    if "refresh_token" not in token_data:
        print(f"\nFailed to obtain refresh token. Response:\n{token_data}")
        print("\nNote: If 'refresh_token' was not returned, verify that you approved all scopes")
        print("and that prompt=consent was provided.")
        sys.exit(1)

    refresh_token = token_data["refresh_token"]

    print("\n" + "=" * 60)
    print("SUCCESS! Here is your new YOUTUBE_REFRESH_TOKEN:")
    print("=" * 60)
    print(f"\n{refresh_token}\n")
    print("=" * 60)
    print("NEXT STEPS:")
    print("1. Go to your GitHub repository -> Settings -> Secrets and variables -> Actions")
    print("2. Update the secret 'YOUTUBE_REFRESH_TOKEN' with the value above.")
    print("3. Ensure 'YOUTUBE_CLIENT_ID' and 'YOUTUBE_CLIENT_SECRET' match the credentials used.")
    print("\nCRITICAL - PREVENT 7-DAY EXPIRATION:")
    print("In Google Cloud Console (console.cloud.google.com):")
    print("  Go to APIs & Services -> OAuth consent screen.")
    print("  Make sure Publishing status is 'In production' (click 'Publish App').")
    print("  If left in 'Testing' status, Google expires refresh tokens every 7 days!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    get_tokens()
