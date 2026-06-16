import os
import json
from schwab import auth

API_KEY = os.environ["SCHWAB_API_KEY"]
APP_SECRET = os.environ["SCHWAB_APP_SECRET"]
CALLBACK_URL = os.environ["SCHWAB_CALLBACK_URL"]

TOKEN_PATH = "/tmp/token.json"

def get_client():
    token_json = os.environ.get("SCHWAB_TOKEN_JSON")

    if token_json:
        with open(TOKEN_PATH, "w") as f:
            json.dump(json.loads(token_json), f)

    return auth.client_from_token_file(
        token_path=TOKEN_PATH,
        api_key=API_KEY,
        app_secret=APP_SECRET,
    )
