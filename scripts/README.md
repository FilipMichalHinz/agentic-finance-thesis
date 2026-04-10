# SEC Index Ingestion

This folder contains a script for downloading SEC filings via the official `master.idx`
files (free, complete coverage). It pulls filings, extracts the correct `<DOCUMENT>` body,
and writes metadata + raw text to local storage for later chunking and embeddings.

## Script: `scripts/ingest_sec_index.py`

### Required
- `SEC_USER_AGENT` (environment variable) or `--user-agent`
  - Format example: `YourName your_email@example.com`

### Defaults
- Tickers: Dow 30 (`AAPL,AMGN,AMZN,AXP,BA,CAT,CRM,CSCO,CVX,DIS,GS,HD,HON,IBM,JNJ,JPM,KO,MCD,MMM,MRK,MSFT,NKE,NVDA,PG,SHW,TRV,UNH,V,VZ,WMT`)
- Forms: `10-K,10-Q,8-K`
- Date window: `2025-01-01` to `2026-01-01` (end is exclusive)

### Example
```bash
export SEC_USER_AGENT="YourName your_email@example.com"
python scripts/ingest_sec_index.py
```

### Example: explicit Dow 30 run
```bash
python scripts/ingest_sec_index.py \
  --start-date 2025-01-01 \
  --end-date 2026-01-01 \
  --tickers AAPL,AMGN,AMZN,AXP,BA,CAT,CRM,CSCO,CVX,DIS,GS,HD,HON,IBM,JNJ,JPM,KO,MCD,MMM,MRK,MSFT,NKE,NVDA,PG,SHW,TRV,UNH,V,VZ,WMT
```

### Optional flags
- `--tickers AAPL,MSFT` (override tickers)
- `--forms 10-K,10-Q,8-K`
- `--start-date 2025-01-01`
- `--end-date 2026-01-01`
- `--cache-dir sec_bulk_index`
- `--filings-dir sec_bulk_filings`
- `--manifest sec_bulk_filings/filings_manifest.jsonl`
- `--sleep-seconds 0.2` (SEC-friendly rate limit)
- `--timeout-seconds 30`
- `--max-retries 5`
- `--retry-backoff-seconds 2.0`
- `--failed-log sec_bulk_filings/failed_downloads.jsonl`
- `--limit 25` (debug)
- `--overwrite` (re-download even if present)

## Script: `scripts/chunk_filings.py`

Chunks downloaded filings and stores them in `knowledge_base` with `embedding = NULL`
so you can run embeddings later as a separate job.

### Required
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` must be set.

### Example
```bash
python scripts/chunk_filings.py
```

### Optional flags
- `--manifest sec_bulk_filings/filings_manifest.jsonl`
- `--chunk-size 1000`
- `--chunk-overlap 200`
- `--db-batch-size 200`
- `--limit 10` (debug)

## Script: `scripts/embed_chunks.py`

Embeds rows in `knowledge_base` where `embedding IS NULL`. This is resumable
and safe to rerun. You can use Gemini (default) or a local model.

### Required
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- For Gemini: `GOOGLE_API_KEY`
- For local: `sentence-transformers` installed (model downloads on first run)

### Example
```bash
python scripts/embed_chunks.py --ticker MSFT --limit 50
```

### Optional flags
- `--provider gemini|local`
- `--gemini-model gemini-embedding-001`
- `--local-model intfloat/e5-base-v2`
- `--device cpu`
- `--normalize`
- `--embed-batch-size 1`
- `--db-batch-size 50`
- `--sleep-seconds 1.0`
- `--max-retries 5`
- `--timeout-seconds 300`
- `--limit 0` (no limit)
- `--ticker MSFT`
- `--log-file sec_bulk_filings/failed_embeddings.jsonl`

## Script: `src/news_data_ingestion.py`

Loads Financial Modeling Prep news into Supabase for daily portfolio context.
It writes into two separate tables:
- `stock_news_daily`
- `general_news_daily`

Schema note:
- `general_news_daily` does not store ticker or symbols

Daily caps:
- stock news: max `10` per ticker per day by default
- general news: max `10` per day by default

### Required
- `FMP_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Example: one-week NVDA test
```bash
python src/news_data_ingestion.py \
  --tickers NVDA \
  --start-date 2026-04-03 \
  --end-date 2026-04-10
```

### Example: dry run
```bash
python src/news_data_ingestion.py \
  --tickers NVDA \
  --start-date 2026-04-03 \
  --end-date 2026-04-10 \
  --dry-run
```

### Optional flags
- `--news-types stock_news,general_news`
- `--page-size 50`
- `--general-pages 5`
- `--max-stock-news-per-day 10`
- `--max-general-news-per-day 10`
- `--sleep-seconds 0.25`
