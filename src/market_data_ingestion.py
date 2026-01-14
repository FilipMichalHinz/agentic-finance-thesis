import yfinance as yf
import pandas as pd
from supabase import create_client, Client
import os
import time
from dotenv import load_dotenv

#load env variables
print(" Loading environment variables...")
load_dotenv() 

# set up supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("❌ Error: SUPABASE_URL is missing. Check your .env file.")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# CONFIG
START_DATE = "2025-09-01"
END_DATE = "2026-01-01"

# We can just include all of NASDaq later
TICKERS = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]

# ingestion
def process_ticker(ticker):
    print(f" Downloading {ticker} data...")
    
    try:
        # FIX: Use Ticker().history() instead of download()
        # This prevents the "MultiIndex" bug by ensuring we get a simple table
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(start=START_DATE, end=END_DATE, interval="1h", auto_adjust=True)
        
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

        # TIMEZONE HANDLING
        # 1. Convert to NY first (if not already)
        if df['Datetime'].dt.tz is None:
            df['Datetime'] = df['Datetime'].dt.tz_localize('America/New_York')
        else:
            df['Datetime'] = df['Datetime'].dt.tz_convert('America/New_York')
        
        # 2. Convert to UTC for Supabase storage
        df['Datetime'] = df['Datetime'].dt.tz_convert('UTC')

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
                supabase.table("market_prices_hourly").upsert(batch, on_conflict="ticker, event_timestamp").execute()
            except Exception as e:
                print(f"   ❌ DB Error: {e}")
                
        print(f"   ✅ {ticker} Done.")
        
    except Exception as e:
        print(f"   ❌ Processing Error: {e}")

# Run
if __name__ == "__main__":
    print("🚀 Starting Ingestion Job...")
    
    for ticker in TICKERS:
        process_ticker(ticker)
        time.sleep(1.5) # Slight pause for API politeness
        
    print("🏁 Ingestion Complete.")