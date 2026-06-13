import os
from schwab import auth

API_KEY = os.environ.get("SCHWAB_API_KEY")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET")
CALLBACK_URL = os.environ.get("SCHWAB_CALLBACK_URL")
TOKEN_PATH = "/etc/secrets/token.json"

def get_client():
    if not API_KEY:
        raise RuntimeError("Missing SCHWAB_API_KEY")
    if not APP_SECRET:
        raise RuntimeError("Missing SCHWAB_APP_SECRET")
    if not CALLBACK_URL:
        raise RuntimeError("Missing SCHWAB_CALLBACK_URL")
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(f"Missing token file at {TOKEN_PATH}")

    client = auth.easy_client(
        api_key=API_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=TOKEN_PATH,
        interactive=False,
    )

    if client is None:
        raise RuntimeError("Schwab client returned None. Token is probably invalid for Render.")

    return client
