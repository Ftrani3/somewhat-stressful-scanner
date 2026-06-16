import os
import shutil
from schwab import auth

API_KEY = os.environ["SCHWAB_API_KEY"]
APP_SECRET = os.environ["SCHWAB_APP_SECRET"]
CALLBACK_URL = os.environ["SCHWAB_CALLBACK_URL"]

SECRET_TOKEN_PATH = "/etc/secrets/token.json"
TOKEN_PATH = "/tmp/token.json"

def get_client():
    if not os.path.exists(SECRET_TOKEN_PATH):
        raise RuntimeError(f"Missing token file at {SECRET_TOKEN_PATH}")

    shutil.copyfile(SECRET_TOKEN_PATH, TOKEN_PATH)

    return auth.client_from_token_file(
        token_path=TOKEN_PATH,
        api_key=API_KEY,
        app_secret=APP_SECRET,
    )
