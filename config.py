import http.server
import socketserver
import threading
import webbrowser
import urllib.parse
import requests
import os
from dotenv import load_dotenv, set_key

# LOAD ENV VARIABLES
load_dotenv()
ENV_PATH = ".env"

AUTH_URL = os.getenv("AUTH_URL")
TOKEN_URL = os.getenv("TOKEN_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE ="invoices.read contacts.read"

auth_code_holder = {"code": None}

# 1. Build authorization URL
def build_authorization_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


# 2. Small server to listen on /callback
class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            qs = urllib.parse.parse_qs(parsed.query)
            code = qs.get("code", [None])[0]
            if code:
                auth_code_holder["code"] = code
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Auth received. You can close this tab.</h2>")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>No code found.</h2>")
        else:
            self.send_response(404)
            self.end_headers()


def start_callback_server():
    with socketserver.TCPServer(("localhost", 3000), OAuthCallbackHandler) as httpd:
        while auth_code_holder["code"] is None:
            httpd.handle_request()


# 3. Exchange code for token
def exchange_code_for_token(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()




# 4. Save tokens to .env
def save_tokens_to_env(code: str, access_token: str, refresh_token: str | None):
    set_key(ENV_PATH, "AUTH_CODE", code)
    set_key(ENV_PATH, "ACCESS_TOKEN", access_token)
    if refresh_token:
        set_key(ENV_PATH, "REFRESH_TOKEN", refresh_token)
    print("[APP] tokens saved to .env")


def main():
    server_thread = threading.Thread(target=start_callback_server, daemon=True)
    server_thread.start()
    auth_url = build_authorization_url()
    print("[APP] open:", auth_url)
    webbrowser.open(auth_url)

    server_thread.join()

    code = auth_code_holder["code"]
    print(f"[APP] got code: {code}")

    token_data = exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    print("[APP] access_token :", access_token)
    print("[APP] refresh_token:", refresh_token)

    save_tokens_to_env(code, access_token, refresh_token)


if __name__ == "__main__":
    main()
