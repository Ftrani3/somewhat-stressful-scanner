import os
import json
import streamlit as st
from schwab import auth

API_KEY = st.secrets["SCHWAB_API_KEY"]
APP_SECRET = st.secrets["SCHWAB_APP_SECRET"]
CALLBACK_URL = st.secrets["SCHWAB_CALLBACK_URL"]
TOKEN_PATH = "token.json"

def get_client():
    if "SCHWAB_TOKEN_JSON" in st.secrets:
        with open(TOKEN_PATH, "w") as f:
            f.write(st.secrets["SCHWAB_TOKEN_JSON"])

    return auth.easy_client(
        api_key=API_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=TOKEN_PATH,
        interactive=False,
    )
