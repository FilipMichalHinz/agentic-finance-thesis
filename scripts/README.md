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

## Script: `scripts/ingest_sec_filing_events.py`

Loads the already-downloaded SEC manifest into `sec_filing_events`, which is the right
table for building the fundamental analyst's daily event package.

### Required
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- Apply `supabase/migrations/20260410124500_add_sec_filing_events.sql`

### Example
```bash
python scripts/ingest_sec_filing_events.py
```

### Optional flags
- `--manifest sec_bulk_filings/filings_manifest.jsonl`
- `--db-batch-size 500`
- `--limit 100`

### Stored Fields
- `ticker`, `cik`, `company_name`
- `form`, `filing_date`, `acceptance_datetime`
- `accession_number`, `source_url`
- local file references: `filename`, `submission_path`, `document_path`

### Note
- If `knowledge_base` is already populated with filing metadata, you can also derive `sec_filing_events` in SQL via a `SELECT DISTINCT ON (accession_number)` projection instead of reading the manifest again. The script is just the simplest standalone path.

## FMP Ratios Table

For deeper fundamental analysis, use `fundamental_ratios` rather than any daily Yahoo snapshot table.
The table is created by:

- `supabase/migrations/20260410113000_add_fundamental_ratios.sql`

It stores one row per reported period from the FMP `ratios` endpoint:

- identity fields: `provider`, `ticker`, `company_name`, `source_period_key`
- timing fields: `period_type`, `period_end_date`, `filing_date`, `available_at`
- period labels: `fiscal_year`, `fiscal_quarter`, `calendar_year`, `calendar_quarter`
- ratio fields: `current_ratio`, `quick_ratio`, `cash_ratio`, `debt_ratio`, `debt_to_equity`, `interest_coverage`, `gross_margin`, `operating_margin`, `pretax_margin`, `net_margin`, `return_on_assets`, `return_on_equity`, `return_on_capital_employed`, `asset_turnover`, `inventory_turnover`, `receivables_turnover`, `price_to_earnings`, `price_to_book`, `price_to_sales`, `price_to_cash_flow`, `price_to_free_cash_flow`, `price_earnings_to_growth`, `enterprise_value_multiple`, `dividend_yield`
- `raw_payload` for provider-specific extras

This table is the correct base for periodic FMP ratio ingestion and deeper per-ticker analysis. Daily agent packages should instead be built from:

- `market_prices_daily`
- `sec_filing_events`

## Script: `scripts/ingest_fundamentals_fmp.py`

Loads periodic financial ratios from FMP into `fundamental_ratios`.

### Required
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- `FMP_API_KEY` or `FINANCIAL_MODELING_PREP_API_KEY`
- Apply `supabase/migrations/20260410113000_add_fundamental_ratios.sql`

### Example
```bash
python scripts/ingest_fundamentals_fmp.py
```

### Optional flags
- `--tickers AAPL,MSFT`
- `--periods quarter,annual`
- `--limit 12`
- `--sleep-seconds 0.2`
- `--timeout-seconds 30`
- `--max-retries 5`
- `--retry-backoff-seconds 2.0`
- `--db-batch-size 200`
- `--api-key ...`

### What It Stores
- period identity and timing: `period_type`, `period_end_date`, `filing_date`, `available_at`
- liquidity and leverage: `current_ratio`, `quick_ratio`, `cash_ratio`, `debt_ratio`, `debt_to_equity`, `interest_coverage`
- profitability and efficiency: `gross_margin`, `operating_margin`, `pretax_margin`, `net_margin`, `return_on_assets`, `return_on_equity`, `return_on_capital_employed`, `asset_turnover`, `inventory_turnover`, `receivables_turnover`
- valuation: `price_to_earnings`, `price_to_book`, `price_to_sales`, `price_to_cash_flow`, `price_to_free_cash_flow`, `price_earnings_to_growth`, `enterprise_value_multiple`, `dividend_yield`
- `raw_payload` containing the original FMP ratio row

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
