import os
import re
import glob
import time
import json
import random
import sys
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai
from google.genai import types
from sec_edgar_downloader import Downloader
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS

# --- 1. CONFIGURATION ---
load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"), http_options={"timeout": 300000})

DOWNLOAD_FOLDER = "sec_data_cache"
USER_AGENT_NAME = "AgenticFinanceThesis"
USER_AGENT_EMAIL = "nimy21ac@student.cbs.dk"

TICKERS = DOW_30_TICKERS
FORM_TYPES = ["10-K", "10-Q", "8-K"]
SEC_TIMEZONE = ZoneInfo("America/New_York")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "1"))
EMBED_SLEEP_SECONDS = float(os.getenv("EMBED_SLEEP_SECONDS", "2.0"))
EMBED_RETRY_LOG = os.getenv("EMBED_RETRY_LOG", os.path.join(DOWNLOAD_FOLDER, "failed_embeddings.jsonl"))

# --- 2. BATCH EMBEDDING FUNCTION (The Fix) ---

def get_batch_embeddings(texts):
    """
    Generates embeddings for a LIST of strings in one API call.
    Includes robust retry logic for SSL/Timeout errors.
    """
    if not texts: return []
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # New Gemini API supports list of contents for batching
            response = client.models.embed_content(
                model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=768,
                    task_type="RETRIEVAL_DOCUMENT",
                ),
            )
            # Extract list of vectors
            return [e.values for e in response.embeddings]
            
        except (httpx.ReadTimeout, httpx.TimeoutException, Exception) as e:
            wait_time = (attempt + 1) * 3 + random.uniform(0.5, 1.5)
            print(f"      ⚠️ API Error (Attempt {attempt+1}/{max_retries}): {e} - Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
            
    print(f"      ❌ Failed to embed batch after {max_retries} attempts.")
    return [None] * len(texts) # Return Nones so we preserve order

# --- 3. PARSING LOGIC ---

def parse_filing_date(header):
    patterns = [
        r'<FILING-DATE>\s*(\d{8})',
        r'FILED AS OF DATE:\s*(\d{8})',
        r'CONFORMED PERIOD OF REPORT:\s*(\d{8})',
    ]
    for pattern in patterns:
        match = re.search(pattern, header)
        if match:
            d = match.group(1)
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None

def parse_acceptance_datetime(header):
    match = re.search(r'<ACCEPTANCE-DATETIME>\s*(\d{14})', header)
    if not match:
        return None
    dt = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    return dt.replace(tzinfo=SEC_TIMEZONE)

def extract_document_text(content, target_type):
    documents = content.split("<DOCUMENT>")
    for doc in documents[1:]:
        type_match = re.search(r"<TYPE>\s*([^\n<]+)", doc)
        if not type_match:
            continue
        doc_type = type_match.group(1).strip()
        if doc_type != target_type and not doc_type.startswith(f"{target_type}/"):
            continue
        text_match = re.search(r"<TEXT>(.*)</TEXT>", doc, flags=re.DOTALL | re.IGNORECASE)
        if text_match:
            return text_match.group(1)
    return None

def extract_html_from_submission(file_path, target_type):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            header = f.read(20000)
            f.seek(0)
            content = f.read()
        acceptance_dt = parse_acceptance_datetime(header)
        filing_date = parse_filing_date(header)
        raw_text = extract_document_text(content, target_type)
        return acceptance_dt, filing_date, raw_text
    except Exception as e:
        print(f"      ⚠️ Extraction Error: {e}")
    return None, None, None

def read_metadata(metadata_path):
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        filing_date = data.get("filing_date")
        accession_number = data.get("accession_number")
        source_url = data.get("primary_doc_url") or data.get("accession_number_url")
        return {
            "filing_date": filing_date,
            "accession_number": accession_number,
            "source_url": source_url,
            "filing_type": data.get("filing_type"),
        }
    except Exception as e:
        print(f"      ⚠️ Metadata Error: {e}")
        return {}

def parse_html_to_chunks(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator="\n")
        text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        return splitter.split_text(text)
    except:
        return []

def infer_source_type(file_path):
    for form_type in FORM_TYPES:
        if f"{os.sep}{form_type}{os.sep}" in file_path:
            return form_type
    return None

def log_failed_embedding(payload):
    try:
        os.makedirs(os.path.dirname(EMBED_RETRY_LOG), exist_ok=True)
        with open(EMBED_RETRY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"      ⚠️ Failed to log embedding retry: {e}")

# --- 4. MAIN LOOP ---

def process_ticker(ticker):
    print(f"\n📂 Processing {ticker}...")
    
    # 1. DOWNLOAD (Skip if files exist)
    dl = Downloader(USER_AGENT_NAME, USER_AGENT_EMAIL, DOWNLOAD_FOLDER)
    try:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=365 * 2)
        for form_type in FORM_TYPES:
            dl.get(form_type, ticker, after=start_date.isoformat())
    except:
        pass 

    # 2. FIND RAW SUBMISSIONS
    base_path = os.path.join(DOWNLOAD_FOLDER, "sec-edgar-filings", ticker)
    submission_files = glob.glob(os.path.join(base_path, "**", "full-submission.txt"), recursive=True)

    if not submission_files:
        print(f"   ❌ No full-submission.txt files found in {base_path}")
        return

    print(f"   ✅ Found {len(submission_files)} raw submissions. Processing...")

    for file_path in submission_files:
        metadata_path = os.path.join(os.path.dirname(file_path), "metadata.json")
        metadata = read_metadata(metadata_path) if os.path.exists(metadata_path) else {}
        filing_date = metadata.get("filing_date")
        source_type = metadata.get("filing_type") or infer_source_type(file_path)
        if not source_type:
            print(f"      ⚠️ Unknown source_type for {file_path}")
            continue
        acceptance_dt, header_filing_date, raw_html = extract_html_from_submission(file_path, source_type)
        if not raw_html:
            continue
        if not filing_date:
            filing_date = header_filing_date
        if not filing_date and acceptance_dt:
            filing_date = acceptance_dt.date().isoformat()

        if filing_date:
            try:
                filing_date_obj = datetime.strptime(filing_date, "%Y-%m-%d").date()
                end_date = datetime.now(timezone.utc).date()
                start_date = end_date - timedelta(days=365 * 2)
                if not (start_date <= filing_date_obj <= end_date):
                    continue
            except ValueError:
                pass
        
        chunks = parse_html_to_chunks(raw_html)
        if not chunks: continue
        
        accession_number = metadata.get("accession_number") or os.path.basename(os.path.dirname(file_path))
        source_url = metadata.get("source_url")
        acceptance_utc = acceptance_dt.astimezone(timezone.utc) if acceptance_dt else None
        published_at = acceptance_utc or (f"{filing_date}T00:00:00Z" if filing_date else None)
        
        if not filing_date:
            print(f"      ⚠️ Missing filing_date in metadata: {metadata_path}")
        if not published_at:
            print(f"      ⚠️ Missing published_at for {file_path}; skipping")
            continue
        print(f"      📄 {filing_date} | {source_type} | {len(chunks)} chunks ...", end=" ")

        # --- BATCH PROCESSING START ---
        # Process in batches of 20 chunks to respect API limits but go fast
        BATCH_SIZE = EMBED_BATCH_SIZE
        total_uploaded = 0
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch_chunks = chunks[i : i + BATCH_SIZE]
            
            # 1. Get Embeddings for the whole batch at once
            vectors = get_batch_embeddings(batch_chunks)
            
            # 2. Prepare DB Rows
            db_rows = []
            for j, (chunk_text, vector) in enumerate(zip(batch_chunks, vectors)):
                if vector: # Only add if embedding succeeded
                    db_rows.append({
                        "ticker": ticker,
                        "title": f"{ticker} {source_type} ({filing_date}) Pt-{i+j}",
                        "content": chunk_text,
                        "embedding": vector,
                        "published_at": published_at,
                        "source_type": source_type,
                        "accession_number": accession_number,
                        "chunk_index": i + j,
                        "acceptance_datetime": acceptance_utc,
                        "filing_date": filing_date,
                        "source_url": source_url
                    })
                else:
                    log_failed_embedding({
                        "ticker": ticker,
                        "source_type": source_type,
                        "filing_date": filing_date,
                        "accession_number": accession_number,
                        "chunk_index": i + j,
                        "content": chunk_text,
                    })
            
            # 3. Upload Batch
            if db_rows:
                try:
                    supabase.table("knowledge_base").upsert(
                        db_rows,
                        on_conflict="accession_number,chunk_index"
                    ).execute()
                    total_uploaded += len(db_rows)
                    print(".", end="", flush=True)
                except Exception as e:
                    print("x", end="", flush=True)
            time.sleep(EMBED_SLEEP_SECONDS)

        print(f" Done ({total_uploaded}/{len(chunks)})")

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    print("🚀 Starting Batch RAG Ingestion...")
    for t in TICKERS:
        process_ticker(t)
