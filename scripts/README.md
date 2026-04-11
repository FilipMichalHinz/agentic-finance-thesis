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

By default, the script skips filings whose `accession_number` already exists in
`knowledge_base`, so reruns only process newly downloaded filings.

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
- `--db-batch-size 50`
- `--limit 10` (debug)
- `--rechunk-existing` (force reprocess filings already chunked)

## Script: `scripts/embed_chunks.py`

Embeds rows in `knowledge_base` where `embedding IS NULL`. This is resumable
and safe to rerun. You can use Gemini (default) or a local model.

### Required
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- For Gemini Developer API: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- For Vertex AI: `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, optional `GOOGLE_CLOUD_LOCATION`, and either ADC (recommended) or `VERTEX_API_KEY`
- For local: `sentence-transformers` installed (model downloads on first run)

### Example
```bash
python scripts/embed_chunks.py --ticker MSFT --limit 50
```

### Vertex AI example
```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
gcloud auth application-default login
python scripts/embed_chunks.py --ticker MSFT --limit 50
```

### Vertex AI with explicit API key
```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export VERTEX_API_KEY="your-vertex-api-key"
python scripts/embed_chunks.py --ticker MSFT --limit 50
```

### Optional flags
- `--provider gemini|local`
- `--gemini-model gemini-embedding-001`
- `--local-model intfloat/e5-base-v2`
- `--device cpu`
- `--normalize`
- `--embed-batch-size 1`
- `--db-batch-size 25`
- `--sleep-seconds 0.2`
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

It stores one row per reported period from the FMP `ratios` endpoint, enriched with filing timing from FMP income statements:

- identity fields: `provider`, `ticker`, `source_period_key`
- timing fields: `period_type`, `period_end_date`, `filing_date`
- period labels: `fiscal_year`, `calendar_year`
- reported metadata: `reported_currency`
- core ratio fields: `current_ratio`, `quick_ratio`, `gross_margin`, `operating_margin`, `net_margin`, `return_on_assets`, `return_on_equity`, `debt_to_assets_ratio`, `debt_to_equity`, `interest_coverage_ratio`, `asset_turnover`, `inventory_turnover`, `receivables_turnover`, `price_to_earnings`, `price_to_book`, `price_to_sales`, `price_to_free_cash_flow`, `enterprise_value_multiple`, `dividend_yield`
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
- Apply `supabase/migrations/20260410160000_expand_fundamental_ratios_columns.sql`
- Apply `supabase/migrations/20260410163000_refine_metric_tables.sql`
- On FMP Starter, use annual ratios. Quarterly ratios require a higher tier.

### Example
```bash
python scripts/ingest_fundamentals_fmp.py
```

### Optional flags
- `--tickers AAPL,MSFT`
- `--periods annual`
- `--periods annual,quarter`
- `--limit 12`
- `--sleep-seconds 0.2`
- `--timeout-seconds 30`
- `--max-retries 5`
- `--retry-backoff-seconds 2.0`
- `--db-batch-size 200`
- `--api-key ...`

### What It Stores
- period identity and timing: `period_type`, `period_end_date`, `filing_date`
- reported metadata: `reported_currency`
- liquidity and leverage: `current_ratio`, `quick_ratio`, `debt_to_assets_ratio`, `debt_to_equity`, `interest_coverage_ratio`
- profitability and efficiency: `gross_margin`, `operating_margin`, `net_margin`, `return_on_assets`, `return_on_equity`, `asset_turnover`, `inventory_turnover`, `receivables_turnover`
- valuation: `price_to_earnings`, `price_to_book`, `price_to_sales`, `price_to_free_cash_flow`, `enterprise_value_multiple`, `dividend_yield`
- stored numeric values are rounded to 2 decimal places
- `raw_payload` containing the original FMP ratio row

### Point-in-time note
- The daily package builder should only surface a fundamental period after its `filing_date`.
- `period_end_date` describes what period the metrics belong to, but `filing_date` is the gate for when that period becomes visible in backtests.

## FMP Technical Indicators Table

For technical-analysis data, use `technical_indicators_daily`.
The table is created by:

- `supabase/migrations/20260410161000_add_technical_indicators_daily.sql`

It stores one row per:

- `ticker`
- `timeframe`
- `period_length`
- `event_date`

This wide daily shape keeps the row count down and avoids repeating metadata for each indicator value.

## Script: `scripts/ingest_technical_indicators_fmp.py`

Loads FMP technical indicator time series into `technical_indicators_daily`.

### Required
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- `FMP_API_KEY` or `FINANCIAL_MODELING_PREP_API_KEY`
- Apply `supabase/migrations/20260410161000_add_technical_indicators_daily.sql`

### Plan Note
- A live dry run on April 10, 2026 succeeded on your Starter plan for the `1day` timeframe across `sma, ema, wma, dema, tema, rsi, standarddeviation, williams, adx`.

### Supported Indicators
- `sma`
- `ema`
- `wma`
- `dema`
- `tema`
- `rsi`
- `standarddeviation`
- `williams`
- `adx`

### Example
```bash
python scripts/ingest_technical_indicators_fmp.py
```

### Example: small smoke test
```bash
python scripts/ingest_technical_indicators_fmp.py \
  --tickers AAPL \
  --indicators sma,rsi \
  --period-lengths 10,14 \
  --timeframe 1day \
  --start-date 2025-01-01 \
  --end-date 2025-01-31
```

### Optional flags
- `--tickers AAPL,MSFT`
- `--indicators sma,ema,rsi`
- `--period-lengths 10,14,20`
- `--timeframe 1day`
- `--start-date 2025-01-01`
- `--end-date 2026-04-10`
- `--sleep-seconds 0.2`
- `--timeout-seconds 30`
- `--db-batch-size 500`
- `--dry-run`
- `--api-key ...`

### What It Stores
- daily identity: `ticker`, `timeframe`, `period_length`, `event_date`
- one column per indicator: `sma`, `ema`, `wma`, `dema`, `tema`, `rsi`, `standarddeviation`, `williams`, `adx`
- stored indicator values are rounded to 2 decimal places
- `raw_payload` containing the source FMP records merged by indicator for that day

## FMP Economic Indicators Table

For macro data, use `economic_indicators`.
The table is created by:

- `supabase/migrations/20260410165000_add_economic_indicators.sql`

It stores one row per:

- `country`
- `indicator_name`
- `event_date`

This normalized shape fits macro series better than a wide table because GDP is quarterly while CPI, inflation, and unemployment are typically monthly.

## Script: `scripts/ingest_economic_indicators_fmp.py`

Loads FMP economic indicators into `economic_indicators`.

### Required
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- `FMP_API_KEY` or `FINANCIAL_MODELING_PREP_API_KEY`
- Apply `supabase/migrations/20260410165000_add_economic_indicators.sql`

### Defaults
- indicators: `GDP,CPI,inflationRate,unemploymentRate`
- country: `US`
- date window: `2024-01-01` to `2026-04-10`

### Example
```bash
python scripts/ingest_economic_indicators_fmp.py
```

### Example: dry run
```bash
python scripts/ingest_economic_indicators_fmp.py --dry-run
```

### Optional flags
- `--indicators GDP,CPI,inflationRate,unemploymentRate`
- `--country US`
- `--start-date 2024-01-01`
- `--end-date 2026-04-10`
- `--sleep-seconds 0.2`
- `--timeout-seconds 30`
- `--db-batch-size 200`
- `--dry-run`
- `--api-key ...`

### What It Stores
- identity: `country`, `indicator_name`, `event_date`
- normalized numeric value: `value`
- stored values are rounded to 2 decimal places
- `raw_payload` containing the source FMP record

### Indicator Name Notes
- FMP returns data for `inflationRate`, not `inflation`
- FMP returns data for `unemploymentRate`; the script also accepts `unemployment`
- the script accepts `inflation` and `unemployment` as aliases and stores the canonical FMP names

## Script: `src/news_data_ingestion.py`

Loads FMP news into Supabase for daily portfolio context via two scripts:
- `scripts/ingest_general_news_fmp.py` -> `general_news_daily`
- `scripts/ingest_stock_news_fmp.py` -> `stock_news_daily`

Schema note:
- `general_news_daily` does not store ticker or symbols

Daily caps:
- stock news: max `10` per ticker per day by default
- general news: max `10` per day by default

### Required
- `FMP_API_KEY` or `FINANCIAL_MODELING_PREP_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Example: one-week general news dry run
```bash
python scripts/ingest_general_news_fmp.py \
  --start-date 2025-04-11 \
  --end-date 2025-04-18 \
  --dry-run
```

### Example: one-week NVDA stock news dry run
```bash
python scripts/ingest_stock_news_fmp.py \
  --tickers NVDA \
  --start-date 2025-04-11 \
  --end-date 2025-04-18 \
  --dry-run
```

### Optional flags
- `--page-size 20`
- `--max-pages 5`
- `--sleep-seconds 0.25`
- `--timeout-seconds 30.0`
- `--max-retries 5`
- `--retry-backoff-seconds 2.0`
