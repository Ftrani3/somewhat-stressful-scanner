import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from io import BytesIO

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def bb_percent(series):
    sma = series.rolling(20).mean()
    std = series.rolling(20).std()
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    return ((series.iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])) * 100

def main():
    st.title("Somewhat Stressful Mobile Scanner")

    capital = st.number_input("Available Capital", min_value=500, value=100000, step=500)
    run_scan = st.button("Refresh Scan")

    if not run_scan:
        st.stop()

    tickers = pd.read_csv("tickers.csv")["Ticker"].dropna().unique().tolist()
    results = []

    progress = st.progress(0)

    for i, ticker in enumerate(tickers):
        progress.progress((i + 1) / len(tickers))

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")

            if hist.empty or len(hist) < 150:
                continue

            close = hist["Close"]
            price = float(close.iloc[-1])
            current_rsi = round(float(rsi(close).iloc[-1]), 2)
            current_bb = round(float(bb_percent(close)), 2)
            sma150 = close.rolling(150).mean().iloc[-1]
            above_150 = price > sma150

            if current_rsi > 60:
                continue

            if current_bb > 70:
                continue

            #if not above_150:
            #    continue

            expirations = stock.options
            if not expirations:
                continue

            exp = expirations[0]
            chain = stock.option_chain(exp)
            puts = chain.puts

            if puts.empty:
                continue

            puts = puts[puts["strike"] * 100 <= capital]
            puts = puts[puts["strike"] < price]

            if puts.empty:
                continue

            puts["premium"] = puts["bid"]
            puts = puts[puts["premium"] > 0]

            if puts.empty:
                continue

            puts["yield_pct"] = (puts["premium"] / puts["strike"]) * 100
            puts = puts.sort_values("yield_pct", ascending=False)

            best = puts.iloc[0]
            strike = float(best["strike"])
            premium = float(best["premium"])
            capital_required = strike * 100
            pct_otm = ((price - strike) / price) * 100

            results.append({
                "Ticker": ticker,
                "Expiration": exp,
                "Stock Price": round(price, 2),
                "Strike": round(strike, 2),
                "% OTM": round(pct_otm, 1),
                "Bid": round(premium, 2),
                "Premium": round(premium * 100, 2),
                "Yield %": round((premium / strike) * 100, 2),
                "Capital Required": round(capital_required, 2),
                "RSI": current_rsi,
                "BB%": current_bb,
                "Open Interest": int(best.get("openInterest", 0) or 0),
                "Volume": int(best.get("volume", 0) or 0),
            })

        except Exception:
            continue

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("No matches found.")
        return

    df = df.sort_values("Yield %", ascending=False)
    st.dataframe(df, use_container_width=True)

    output = BytesIO()
    df.to_excel(output, index=False)
    st.download_button(
        "Download Excel Results",
        data=output.getvalue(),
        file_name="mobile_scanner_results.xlsx",
    )

if __name__ == "__main__":
    main()