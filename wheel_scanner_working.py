import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from schwab_connect import get_client

USE_EXTENDED_HOURS = True

#st.markdown(
#    "<h2>Available Capital ($)</h2>",
#    unsafe_allow_html=True
#)

EARNINGS_DATES = {
        # example:
        # "HAL": datetime(2026, 7, 22).date(),
        # "DVN": datetime(2026, 8, 5).date(),
    }

def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except:
        return None
    
#st.write("File loaded. run_scan =", run_scan)

def main():
    
    with st.form("scan_form"):
        CAPITAL = st.number_input(
            "Available Capital",
            min_value=500.0,
            value=10000.0,
            step=500.0,
            format="%.0f"
        )

        run_scan = st.form_submit_button("Refresh Scan")

    if not run_scan:
        st.stop()

    st.write("Capital used: $" + format(CAPITAL, ",.0f"))
    
    client = get_client()
        if client is None:
                st.error("Schwab client is None. Render is not authenticating with Schwab.")
                st.stop()

    TICKERS = pd.read_csv("tickers.csv")["Ticker"].dropna().unique().tolist()
    TICKERS = sorted(set(TICKERS))

    print(f"Loaded {len(TICKERS)} tickers from CSV")

    results = []
    bakup_results = []
    today = datetime.today().date()

    days_until_friday = (4 - today.weekday()) % 7
    
    if days_until_friday == 0:
        days_until_friday = 7

    nearest_friday = today + timedelta(days=days_until_friday)
    nearest_friday_str = nearest_friday.strftime("%Y-%m-%d")

    print("Nearest Friday:", nearest_friday_str)

    checked = 0
    skipped_capital = 0
    skipped_bid = 0
    skipped_iv = 0
    skipped_delta = 0
    skipped_oi = 0
    skipped_volume = 0
    skipped_yield = 0

    for ticker in TICKERS:
        
        above_150ma = False

        history_url = f"https://api.schwabapi.com/marketdata/v1/pricehistory"

        history_params = {
            "symbol": ticker,
            "periodType": "year",
            "period": 1,
            "frequencyType": "daily",
            "frequency": 1,
            "needExtendedHoursData": str(USE_EXTENDED_HOURS).lower()
    }

        history_response = client.session.get(
            history_url, 
            params=history_params
        )

        try:
            history_data = history_response.json()
        except:
            continue

        candles = history_data.get("candles", [])
        closes = [c["close"] for c in candles if "close" in c]

        rsi = None
        bb_pct = None
        above_150ma = False

        if len(closes) >= 20:
            series = pd.Series(closes)

            delta_prices = series.diff()
            gains = delta_prices.clip(lower=0)
            losses = -delta_prices.clip(upper=0)

            avg_gain = gains.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = losses.ewm(alpha=1/14, adjust=False).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi = round(rsi.iloc[-1], 2)

            sma = series.rolling(20).mean()
            std = series.rolling(20).std()

            upper_band = sma + (2 * std)
            lower_band = sma - (2 * std)

            bb_pct = ((series.iloc[-1] - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])) * 100
            bb_pct = round(bb_pct, 2)

            # 150-day moving average
            sma150 = series.rolling(150).mean()

            above_150ma = False

            if len(series) >= 150:
                above_150ma = series.iloc[-1] > sma150.iloc[-1]

        # quote = client.PriceHistory(
        #    ticker,
        #    period_type="month",
        #    period=3,
        #    frequency_type="daily",
        #    frequency=1
        # )
        url = "https://api.schwabapi.com/marketdata/v1/chains"

        today_str = datetime.now().strftime("%Y-%m-%d")
        six_days_str = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d")

        params = {
            "symbol": ticker,
            "contractType": "PUT",
            "strategy": "SINGLE",
            "strikeCount": 20,
            "includeQuotes": "TRUE",
            "fromDate": today_str,
            "toDate": six_days_str,
        }

        try:
            response = client.session.get(url, params=params)
            data = response.json()
            print("DATA KEYS:", data.keys())
            print("PUT MAP SIZE:", len(data.get("putExpDateMap", {})))
            print("CALL MAP SIZE:", len(data.get("callExpDateMap", {})))
            stock_price = data.get("underlyingPrice")
            
            if stock_price is None:
                continue

            #if stock_price is not None and (stock_price < 5 or stock_price > 150):
            #    continue

#Earnings filter
            earnings_date = EARNINGS_DATES.get(ticker)

            if earnings_date is not None:
                days_to_earnings = (earnings_date - today) .days

                if 0 <= days_to_earnings <= 10:
                    continue
        
            put_map = data.get("putExpDateMap", {})

            if not put_map:
                continue

            available_expirations = sorted(
                [d.split(":")[0] for d in put_map.keys()]
            )

            nearest_available_exp = available_expirations[0]

            print("NEAREST AVAILABLE:", nearest_available_exp)

            for exp_date, strike_list in put_map.items():
                exp_clean = exp_date.split(":")[0]

                if exp_clean != nearest_available_exp:
                    continue

                for strike_key, options in strike_list.items():
                    for option in options:
                        checked += 1

                        strike = safe_float(option.get("strikePrice"))
                        bid = safe_float(option.get("bid"))
                        delta = safe_float(option.get("delta"))
                        iv = safe_float(option.get("volatility"))
                        open_interest = safe_float(option.get("openInterest")) or 0
                        volume = safe_float(option.get("totalVolume")) or 0
                        days_to_exp = safe_float(option.get("daysToExpiration"))

                        if days_to_exp is None or days_to_exp > 45:
                            continue

                        if strike is None:
                            continue

                        checked += 1

                        capital_required = strike * 100

                        if capital_required > CAPITAL:
                            skipped_capital += 1
                            continue

                        if bid is None or bid <= 0:
                            skipped_bid += 1
                            continue

                        premium = bid * 100
                        yield_pct = (premium / capital_required) * 100

                        # TEMP DEBUG FILTERS
                        # Keeping these loose so we can find matches first

                        if iv is not None and (iv < 10 or iv > 100):
                            skipped_iv += 1
                            continue

                        if delta is not None and not (-0.70 <= delta <= -0.1):
                            skipped_delta += 1
                            continue

                        if rsi is None or rsi > 45:
                            continue

                        if bb_pct is None or bb_pct > 45:
                            continue 

                        #if not above_150ma:
                        #    continue

                        if open_interest < 50:
                            skipped_oi += 1
                            continue

                        if volume < 25:
                            skipped_volume += 1
                            continue

                        if yield_pct < 0.50:
                            skipped_yield += 1
                            continue

                        score = 0

                        if rsi is not None and rsi <= 30:
                            score += 15
                        elif rsi is not None and rsi <= 45:
                            score += 10

                        if bb_pct is not None and bb_pct <= 25:
                            score += 15
                        elif bb_pct is not None and bb_pct <= 45:
                            score += 10

# Delta = 40 points
                        if delta is not None and -0.30 <= delta <= -0.20:
                           score += 40
                        elif delta is not None and -0.35 <= delta <= -0.15:
                           score += 25

# IV = 25 points
                        if iv is not None and 15 <= iv <= 75:
                            score += 25
                        elif iv is not None and 10 <= iv <= 100:
                            score += 15

# Technical score
                        if rsi is not None and rsi <= 45:
                            score += 15

                        if bb_pct is not None and bb_pct <= 45:
                            score += 15

                        if above_150ma:
                            score += 15

# Liquidity = 20 points
                        liquidity_score = 0

                        if open_interest >= 1000:
                            liquidity_score += 10
                        elif open_interest >= 500:
                            liquidity_score += 7
                        elif open_interest >= 100:
                            liquidity_score += 5

                        if volume >= 500:
                            liquidity_score += 10
                        elif volume >= 100:
                            liquidity_score += 7
                        elif volume >= 25:
                            liquidity_score += 5

                        score += liquidity_score

# DTE = 15 points
                        if days_to_exp is not None and 5 <= days_to_exp <= 10:
                            score += 20
                        elif days_to_exp is not None and 11 <= days_to_exp <= 17:
                            score += 10
                        elif days_to_exp is not None and days_to_exp <= 45:
                            score += 3

# Yield = 10 points
                        if yield_pct >= 2:
                            score += 10
                        elif yield_pct >= 1:
                            score += 7
                        elif yield_pct >= 0.75:
                            score += 5  

                        stock_price = data.get("underlyingPrice") 

                        if stock_price is None:
                            continue

                        if stock_price < 5 or stock_price > 150:
                            continue

                        pct_otm = ((stock_price - strike) / stock_price) * 100

                        if pct_otm is not None and pct_otm < 0:
                            score -= 40
                        print(f"MATCH FOUND: {ticker} Strike={strike} Required={capital_required}")
                        results.append({
                            "Ticker": ticker,
                            "Expiration": exp_date,
                            "Stock Price": round(stock_price, 2) if stock_price else None,
                            "Strike": strike,
                            "% OTM": round(pct_otm, 1) if pct_otm is not None else None,
                            "Moneyness": "ITM" if pct_otm < 0 else "OTM",
                            "Bid": round(bid, 2),
                            "Premium": round(premium, 2),
                            "Yield %": round(yield_pct, 2),
                            "Capital Required": round(capital_required, 2),
                            "RSI": rsi,
                            "BB%": bb_pct,
                            "Delta": round(delta, 3) if delta is not None else None,
                            "IV": round(iv, 2) if iv is not None else None,
                            "Open Interest": int(open_interest),
                            "Volume": int(volume),
                            "Assignment Score": score,
                            "Days": int(days_to_exp) if days_to_exp is not None else None,
                        })

        except Exception as e:
            print(f"Error scanning {ticker}: {e}")

    print("Ticker count:", len(TICKERS))
    df = pd.DataFrame(results)

    print("\n--- DEBUG SUMMARY ---")
    print("Checked:", checked)
    print("Skipped capital:", skipped_capital)
    print("Skipped bid:", skipped_bid)
    print("Skipped IV:", skipped_iv)
    print("Skipped delta:", skipped_delta)
    print("Skipped OI:", skipped_oi)
    print("Skipped volume:", skipped_volume)
    print("Skipped yield:", skipped_yield)
    print("Matches:", len(results))

    if len(df) == 0:
        print("\nNo matches found.")
        return

    df["Wheel Rank Score"] = (
        df["Assignment Score"] * 1.0
        + df["Yield %"] * 20
        + (45 - df["RSI"]) * 1.5
        + (45 - df["BB%"]) * 1.5
        + df["% OTM"] * 3
    )
    df["Worthless Score"] = (
        df["% OTM"] * 5
        + (1 - df["Delta"].abs()) * 100
        + (45 - df["RSI"]) * 1.2
        + (45 - df["BB%"]) * 1.2
        - df["IV"] * 0.25
    )

    df.loc[df["Moneyness"] == "ITM", "Worthless Score"] -= 75
    
    df = df.sort_values(
        by=["Worthless Score", "Assignment Score", "Yield %"],
        ascending=[False, False, False]
    )

    df = df.reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))

    display_cols = [
        "Rank", "Ticker", "Stock Price", "Strike", "Worthless Score", "Wheel Rank Score", "% OTM",  
        "Premium", "Yield %", "Delta", "IV", "RSI", "BB%", "Capital Required", "Assignment Score"
        ]
    st.success(f"Scan complete: {len(df)} matches found.")
    st.write(f"Capital used: ${CAPITAL}")

    st.subheader("Top 20 Wheel Candidates")
    top_df = df[display_cols + ["Moneyness"]].head(20).copy()

    format_cols = {
        "Stock Price": "{:.2f}",
        "Strike": "{:.2f}",
        "% OTM": "{:.1f}",
        "Bid": "{:.2f}",
        "Premium": "{:.0f}",
        "Yield %": "{:.2f}",
        "Delta": "{:.3f}",
        "IV": "{:.1f}",
        "RSI": "{:.1f}",
        "BB%": "{:.1f}",
        "Capital Required": "{:.0f}",
        "Open Interest": "{:.0f}",
        "Volume": "{:.0f}",
        "Assignment Score": "{:.0f}",
        "Worthless Score": "{:.1f}",
        "Wheel Rank Score": "{:.1f}",
    }

    styled_df = top_df.style.format(format_cols).apply(
        lambda row: ["background-color: #ffe6e6" if row["Moneyness"] == "ITM" else "" for _ in row],
        axis=1
    )

    st.dataframe(styled_df.hide(axis="columns", subset=["Moneyness"]), width="stretch", hide_index=True)

    df.to_excel("wheel_scanner_results.xlsx", index=False)

    with open("wheel_scanner_results.xlsx", "rb") as f:
        excel_data = f.read()

    st.download_button(
        "Download Excel Results",
        excel_data,
        file_name="wheel_scanner_results.xlsx"
    )

    print("\nExported to wheel_scanner_results.xlsx")
