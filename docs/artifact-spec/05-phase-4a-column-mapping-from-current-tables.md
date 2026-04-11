**PHASE 4A — COLUMN MAPPING FROM CURRENT TABLES**

1. **market\_prices\_daily**

This is your core daily market price table.

Current columns:

* `id`  
* `ticker`  
* `event_timestamp`  
* `price_open`  
* `price_high`  
* `price_low`  
* `price_close`  
* `volume`

Conceptual mapping:

* ticker → `ticker`  
* market event timestamp / trading-day timestamp → `event_timestamp`  
* daily open price → `price_open`  
* daily high price → `price_high`  
* daily low price → `price_low`  
* daily close price → `price_close`  
* daily trading volume → `volume`

Fields mentioned in Phase 4 that are not stored yet and should be derived or precomputed from this table:

* previous close  
* close vs open percentage change  
* close vs previous close percentage change

Suggested technical names for prepared package fields:

* `chg_close_vs_open_pct`  
* `chg_close_vs_prev_close_pct`

This table is used by:

* Technical Analyst  
* News Analyst  
* Fundamental Analyst

2. **technical\_indicators\_daily**

This is your stored daily technical-indicator table.

Current columns:

* `id`  
* `provider`  
* `ticker`  
* `timeframe`  
* `period_length`  
* `event_date`  
* `sma`  
* `ema`  
* `wma`  
* `dema`  
* `tema`  
* `rsi`  
* `standarddeviation`  
* `williams`  
* `adx`  
* `raw_payload`

Conceptual mapping:

* data provider → `provider`  
* ticker → `ticker`  
* timeframe → `timeframe`  
* lookback length / indicator period → `period_length`  
* technical event date → `event_date`  
* simple moving average → `sma`  
* exponential moving average → `ema`  
* weighted moving average → `wma`  
* double exponential moving average → `dema`  
* triple exponential moving average → `tema`  
* relative strength index → `rsi`  
* standard deviation → `standarddeviation`  
* Williams %R → `williams`  
* average directional index → `adx`  
* raw vendor payload → `raw_payload`

Fields mentioned in Phase 4 that are not stored yet and should be derived or precomputed:

* day-to-day change in EMA  
* day-to-day change in RSI  
* day-to-day change in ADX  
* day-to-day change in standard deviation

Suggested technical names for prepared package fields:

* `chg_ema`  
* `chg_rsi`  
* `chg_adx`  
* `chg_standarddeviation`

This table is used by:

* Technical Analyst


3. **fundamental\_ratios**

This is your normalized fundamental-ratio table from FMP.

Current columns:

* `id`  
* `provider`  
* `ticker`  
* `source_period_key`  
* `period_type`  
* `period_end_date`  
* `fiscal_year`  
* `calendar_year`  
* `current_ratio`  
* `quick_ratio`  
* `gross_margin`  
* `operating_margin`  
* `net_margin`  
* `debt_to_equity`  
* `asset_turnover`  
* `inventory_turnover`  
* `receivables_turnover`  
* `price_to_earnings`  
* `price_to_book`  
* `price_to_sales`  
* `price_to_free_cash_flow`  
* `enterprise_value_multiple`  
* `dividend_yield`  
* `raw_payload`  
* `reported_currency`  
* `debt_to_assets_ratio`  
* `interest_coverage_ratio`  
* `filing_date`

Conceptual mapping:

* data provider → `provider`  
* ticker → `ticker`  
* source period key → `source_period_key`  
* reporting period type → `period_type`  
* reporting period end date → `period_end_date`  
* fiscal year → `fiscal_year`  
* calendar year → `calendar_year`  
* current ratio → `current_ratio`  
* quick ratio → `quick_ratio`  
* gross margin → `gross_margin`  
* operating margin → `operating_margin`  
* net margin → `net_margin`  
* debt to equity → `debt_to_equity`  
* debt to assets → `debt_to_assets_ratio`  
* interest coverage → `interest_coverage_ratio`  
* asset turnover → `asset_turnover`  
* inventory turnover → `inventory_turnover`  
* receivables turnover → `receivables_turnover`  
* price to earnings → `price_to_earnings`  
* price to book → `price_to_book`  
* price to sales → `price_to_sales`  
* price to free cash flow → `price_to_free_cash_flow`  
* enterprise value multiple → `enterprise_value_multiple`  
* dividend yield → `dividend_yield`  
* reported currency → `reported_currency`  
* raw vendor payload → `raw_payload`  
* filing date used for point-in-time visibility → `filing_date`

Fields mentioned in Phase 4 that are not stored yet and should be derived or precomputed carefully:

* filing-related event flags for the package day  
* the selected visible period metadata for the daily package row

Suggested technical names for prepared package fields:

* `fundamental_period_end_date`  
* `fundamental_filing_date`  
* `filing_flag`  
* `filing_form`

Important note:  
 A fundamental period should only be visible in a daily package if `filing_date <= package_date`. The package should not surface a newer period before it was filed.

This table is used by:

* Fundamental Analyst


4. **stock\_news\_daily**

This is your stock-specific news table.

Current columns:

* `id`  
* `ticker`  
* `symbols`  
* `title`  
* `content`  
* `published_at`  
* `publisher`  
* `site`  
* `dedupe_key`  
* `created_at`

Conceptual mapping:

* source news row ID → `id`  
* primary stock ticker → `ticker`  
* mentioned symbols → `symbols`  
* stock-news headline → `title`  
* stock-news body/content/summary text → `content`  
* publication timestamp → `published_at`  
* publisher name → `publisher`  
* source website/domain → `site`  
* deduplication key → `dedupe_key`  
* ingestion/creation timestamp → `created_at`

Fields mentioned in Phase 4 that are not stored yet and should be derived or precomputed:

* latest news-of-the-day  
* daily news count per stock  

Suggested technical names for prepared package fields:

* `latest_news_id`  
* `latest_news_title`  
* `daily_news_count`

This table is used by:

* News Analyst

5. **general\_news\_daily**

This is your market-wide or general news table.

Current columns:

* `id`  
* `title`  
* `content`  
* `published_at`  
* `publisher`  
* `site`  
* `dedupe_key`  
* `created_at`

Conceptual mapping:

* general news row ID → `id`  
* market-wide headline → `title`  
* market-wide content/summary → `content`  
* publication timestamp → `published_at`  
* publisher → `publisher`  
* source site → `site`  
* dedupe key → `dedupe_key`  
* ingestion timestamp → `created_at`

Fields mentioned in Phase 4 that are not stored yet and should be derived or precomputed:

* latest general-news item for the day  
* daily general-news count

Suggested technical names for prepared package fields:

* `latest_general_news_id`  
* `latest_general_news_title`  
* `latest_general_news_content`  
* `latest_general_news_published_at`  
* `daily_general_news_count`

This table is used by:

* News Analyst  
* possibly Portfolio Manager later, if summarized

6. economic\_indicators

This is your macroeconomic indicator table.

Current columns:

* `id`  
* `provider`  
* `country`  
* `indicator_name`  
* `event_date`  
* `value`  
* `raw_payload`

Conceptual mapping:

* data provider → `provider`  
* country → `country`  
* economic indicator name → `indicator_name`  
* event date → `event_date`  
* indicator value → `value`  
* raw vendor payload → `raw_payload`

Current examples you mentioned:

* GDP  
* unemployment rate  
* CPI  
* inflation rate

Fields mentioned in Phase 4 that are not stored yet and should be derived or precomputed:

* previous value  
* change from previous value  
* macro event flag for the day

Suggested technical names for prepared package fields:

* `prev_value`  
* `chg_value`  
* `chg_value_pct`  
* `macro_event_flag`  
* `macro_event_reason`

This table is used by:

* Fundamental Analyst

7. **knowledge\_base**

This table should be treated as the SEC filing content layer, not as a general-purpose knowledge or memory table.

Its role in the system is to store filing-linked content and metadata that can be retrieved during deeper analysis by the Fundamental Analyst.

Current columns:

* `id`  
* `ticker`  
* `title`  
* `content`  
* `embedding`  
* `published_at`  
* `source_type`  
* `accession_number`  
* `chunk_index`  
* `acceptance_datetime`  
* `filing_date`  
* `source_url`

Conceptual mapping:

* filing content chunk ID → `id`  
* company ticker → `ticker`  
* filing or chunk title → `title`  
* filing-derived text chunk → `content`  
* vector embedding for retrieval → `embedding`  
* publication timestamp → `published_at`  
* filing or document type → `source_type`  
* SEC accession number → `accession_number`  
* chunk position within filing-derived content → `chunk_index`  
* SEC acceptance timestamp → `acceptance_datetime`  
* filing date → `filing_date`  
* original filing or source link → `source_url`

Correct interpretation in the architecture:

* this table is a filing-linked retrieval layer  
* it supports deeper analysis of SEC filings  
* it is a role-specific source for the Fundamental Analyst  
* it is not the same as the system’s agent memory layer

How it should be used:

* during the daily package stage, the Fundamental Analyst should receive only filing flags or filing-event indicators  
* during deeper analysis, the Fundamental Analyst may retrieve relevant filing-linked content from `knowledge_base`

What this table is not:

* it is not the general memory store for the whole system  
* it is not the same as analyst notes, weekly summaries, or portfolio history

Those memory and continuity artifacts should later live in separate artifact tables such as:

* analyst notes  
* weekly summaries  
* portfolio history  
* run logs

This table is used by:

* Fundamental Analyst during deeper analysis 

9. **Which current columns support which agent**

Technical Analyst can currently use:

* `market_prices_daily`  
  * `ticker`  
  * `event_timestamp`  
  * `price_open`  
  * `price_high`  
  * `price_low`  
  * `price_close`  
  * `volume`  
* `technical_indicators_daily`  
  * `ticker`  
  * `event_date`  
  * `sma`  
  * `ema`  
  * `wma`  
  * `dema`  
  * `tema`  
  * `rsi`  
  * `standarddeviation`  
  * `williams`  
  * `adx`

News Analyst can currently use:

* `market_prices_daily`  
  * `ticker`  
  * `event_timestamp`  
  * `price_open`  
  * `price_high`  
  * `price_low`  
  * `price_close`  
  * `volume`  
* `stock_news_daily`  
  * `ticker`  
  * `title`  
  * `content`  
  * `published_at`  
  * `publisher`  
  * `site`  
  * `dedupe_key`  
* `general_news_daily`  
  * `title`  
  * `content`  
  * `published_at`  
  * `publisher`  
  * `site`  
  * `dedupe_key`

Fundamental Analyst can currently use:

* `market_prices_daily`  
  * `ticker`  
  * `event_timestamp`  
  * `price_open`  
  * `price_high`  
  * `price_low`  
  * `price_close`  
  * `volume`  
* `fundamental_ratios`  
  * all normalized ratio columns  
* `economic_indicators`  
  * `country`  
  * `indicator_name`  
  * `event_date`  
  * `value`  
* `knowledge_base`  
  * `ticker`  
  * `title`  
  * `content`  
  * `source_type`  
  * `acceptance_datetime`  
  * `filing_date`  
  * `source_url`

Portfolio Manager will not mainly use raw source columns. It will mainly use:

* analyst outputs  
* portfolio state  
* notes and summaries  
* challenge outputs  
* debate outputs

Those belong more to later artifact tables than to the current ingestion tables.

10. **What still needs to be created or precomputed for the daily packages**

From the current tables, the biggest missing prepared-package fields are:

From market prices:

* previous close  
* close vs open percentage change  
* close vs previous close percentage change

From technicals:

* selected day-to-day indicator changes

From fundamentals:

* daily package selection gated by `filing_date`  
* package-level `fundamental_period_end_date`  
* package-level `fundamental_filing_date`  
* filing flags for the package day

From stock news:

* one-news-of-the-day selection  
* daily news count  

From general news:

* one selected general-news item for the day  
* general-news count if desired

From filings:

* simple daily filing-event flags in the package  
* deeper retrieval remains in the knowledge base


11. **Recommended naming convention for the prepared package layer**

To keep the technical names clean, I would recommend package-layer columns like:

Shared package keys:

* `package_date`  
* `ticker`

Price package fields:

* `price_close`  
* `volume`  
* `chg_close_vs_open_pct`  
* `chg_close_vs_prev_close_pct`

Technical package fields:

* `chg_ema`  
* `chg_rsi`  
* `chg_adx`  
* `chg_standarddeviation`

Fundamental package fields:

* `fundamental_period_end_date`  
* `fundamental_filing_date`  
* `filing_flag`  
* `filing_form`  
* `price_to_earnings`  
* `price_to_sales`

News package fields:

* `latest_news_id`  
* `latest_news_title`  
* `daily_news_count`  
* news shared-context fields kept outside the per-stock package:
  * `latest_general_news_id`
  * `latest_general_news_title`
  * `latest_general_news_content`
  * `latest_general_news_published_at`
  * `daily_general_news_count`

Fundamental shared-context fields kept outside the per-stock package:

* `inflation_rate`

12. **Current prepared-view mapping**

The current prepared package layer is best understood through the final analyst-facing views.

The Technical Analyst screening view should expose:

* `package_date`  
* `ticker`  
* `price_close`  
* `volume`  
* `chg_close_vs_prev_close_pct`  
* `chg_close_vs_open_pct`  
* `chg_ema`  
* `chg_rsi`  
* `chg_adx`  
* `chg_standarddeviation`

The Fundamental Analyst screening view should expose:

* `package_date`  
* `ticker`  
* `price_close`  
* `chg_close_vs_prev_close_pct`  
* `chg_close_vs_open_pct`  
* `fundamental_period_end_date`  
* `fundamental_filing_date`  
* `filing_flag`  
* `filing_form`  
* `price_to_earnings`  
* `price_to_sales`

The News Analyst screening view should expose:

* `package_date`  
* `ticker`  
* `price_close`  
* `chg_close_vs_prev_close_pct`  
* `chg_close_vs_open_pct`  
* `latest_news_id`  
* `latest_news_title`  
* `daily_news_count`

The News shared-context view should expose one row per day with:

* `package_date`  
* `latest_general_news_id`  
* `latest_general_news_title`  
* `latest_general_news_content`  
* `latest_general_news_published_at`  
* `daily_general_news_count`

The Fundamental shared-context view should expose one row per day with:

* `package_date`  
* `inflation_rate`
