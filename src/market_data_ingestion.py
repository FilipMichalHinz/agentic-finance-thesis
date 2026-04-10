import argparse
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yfinance as yf
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest daily market prices into Supabase")
    parser.add_argument("--tickers", default=",".join(DOW_30_TICKERS))
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--end-date", default="2026-01-01")
    parser.add_argument("--history-years", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    return parser.parse_args()


def shift_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # Handle leap-day edge cases by falling back to Feb 28.
        return value.replace(month=2, day=28, year=value.year + years)


# load env variables
print(" Loading environment variables...")
load_dotenv() 

# set up supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("❌ Error: SUPABASE_URL is missing. Check your .env file.")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def process_ticker(ticker, start_date, end_date):
    print(f" Downloading {ticker} data...")
    
    try:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(start=start_date, end=end_date, interval="1d", auto_adjust=True)
        
        if df.empty:
            print(f"   ⚠️ No data found for {ticker}")
            return

        # Reset index to make the Timestamp a column we can access
        df = df.reset_index()

        
        if 'Date' in df.columns:
            df = df.rename(columns={'Date': 'Datetime'})
            
        # Ensure we actually have a Datetime column
        if 'Datetime' not in df.columns:
            print(f"   ⚠️ Could not find timestamp column for {ticker}. Columns: {df.columns}")
            return

        # Treat daily bars as available at the regular market close.
        df['Datetime'] = pd.to_datetime(df['Datetime']).dt.date
        df['Datetime'] = pd.to_datetime(df['Datetime']) + pd.Timedelta(hours=16)
        df['Datetime'] = df['Datetime'].dt.tz_localize('America/New_York').dt.tz_convert('UTC')

        rows_to_insert = []
        
        for index, row in df.iterrows():
            # Robust check for NaN values
            if pd.isna(row['Open']) or pd.isna(row['Close']):
                continue

            data_point = {
                "ticker": ticker,
                "event_timestamp": row['Datetime'].isoformat(),
                "price_open": round(float(row['Open']), 4),
                "price_high": round(float(row['High']), 4),
                "price_low": round(float(row['Low']), 4),
                "price_close": round(float(row['Close']), 4),
                "volume": int(row['Volume'])
            }
            rows_to_insert.append(data_point)

        # Batch Insert
        print(f"   Writing {len(rows_to_insert)} rows to Supabase...")
        batch_size = 1000
        for i in range(0, len(rows_to_insert), batch_size):
            batch = rows_to_insert[i : i + batch_size]
            try:
                # Upsert based on the composite index (ticker + timestamp)
                supabase.table("market_prices_daily").upsert(batch, on_conflict="ticker, event_timestamp").execute()
            except Exception as e:
                print(f"   ❌ DB Error: {e}")
                
        print(f"   ✅ {ticker} Done.")
        
    except Exception as e:
        print(f"   ❌ Processing Error: {e}")

# Run
if __name__ == "__main__":
    args = parse_args()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    if args.history_years < 0:
        raise SystemExit("--history-years must be >= 0")
    target_start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    fetch_start_date = shift_years(target_start_date, -args.history_years)
    fetch_start = fetch_start_date.isoformat()

    print("🚀 Starting Ingestion Job...")
    print(
        f" Tracking {len(tickers)} tickers from {fetch_start} to {args.end_date} "
        f"(target window {args.start_date} to {args.end_date}, lookback {args.history_years} year(s))..."
    )
    
    for ticker in tickers:
        process_ticker(ticker, fetch_start, args.end_date)
        time.sleep(args.sleep_seconds) # Slight pause for API politeness
        
    print("🏁 Ingestion Complete.")
