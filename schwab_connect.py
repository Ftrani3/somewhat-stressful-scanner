from schwab import auth

API_KEY = "fGMOA7h2JddxOAkwge4NQNwc8JZMjAyDdAxWcYG9K1c1X6pw"
APP_SECRET = "i0T3RAL3vdKQnAhl9EeEljgRh6aV6hotBemJaei9OIcpwKZFs4GWrS8BjnZASN1S"
CALLBACK_URL = "https://127.0.0.1:8182"
TOKEN_PATH = "token.json"

def get_client():
    client = auth.easy_client(
        api_key=API_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=TOKEN_PATH,
        interactive=True,
    )

    return client

    resp = client.get_quote("AAPL")
    print(resp.json())

if __name__ == "__main__":
    client = get_client()
    resp = client.get_quote("AAPL")
    print(resp.json())
