import os
from schwab import auth

API_KEY = os.environ.get("SCHWAB_API_KEY")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET")
CALLBACK_URL = os.environ.get("SCHWAB_CALLBACK_URL")
TOKEN_PATH = "/etc/secrets/token.json"

def get_client():
    return auth.easy_client(
        api_key=API_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=TOKEN_PATH,
        interactive=False,
    )
