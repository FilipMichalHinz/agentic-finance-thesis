DROP VIEW IF EXISTS public.daily_stock_packages_analyst_view;
DROP VIEW IF EXISTS public.daily_stock_packages_price_view;
DROP VIEW IF EXISTS public.daily_stock_packages_technical_view;
DROP VIEW IF EXISTS public.daily_stock_packages_fundamental_view;
DROP VIEW IF EXISTS public.daily_stock_packages_news_view;

ALTER TABLE public.daily_stock_packages
DROP CONSTRAINT IF EXISTS daily_stock_packages_unique;

DROP INDEX IF EXISTS idx_daily_stock_packages_dataset_version;

ALTER TABLE public.daily_stock_packages
DROP COLUMN IF EXISTS dataset_version;

ALTER TABLE public.daily_stock_packages
ADD CONSTRAINT daily_stock_packages_unique
UNIQUE (package_date, ticker);

CREATE OR REPLACE VIEW public.daily_stock_packages_analyst_view AS
SELECT
    id,
    package_date,
    ticker,

    price_open,
    price_high,
    price_low,
    price_close,
    volume,
    prev_price_close,
    chg_open_vs_prev_close,
    chg_open_vs_prev_close_pct,
    chg_close_vs_open,
    chg_close_vs_open_pct,
    chg_close_vs_prev_close,
    chg_close_vs_prev_close_pct,
    sma,
    ema,
    wma,
    dema,
    tema,
    rsi,
    standarddeviation,
    williams,
    adx,
    chg_sma,
    chg_ema,
    chg_wma,
    chg_dema,
    chg_tema,
    chg_rsi,
    chg_standarddeviation,
    chg_williams,
    chg_adx,

    fundamental_period_end_date,
    current_ratio,
    quick_ratio,
    gross_margin,
    operating_margin,
    net_margin,
    debt_to_assets_ratio,
    debt_to_equity,
    interest_coverage_ratio,
    asset_turnover,
    inventory_turnover,
    receivables_turnover,
    price_to_earnings,
    price_to_book,
    price_to_sales,
    price_to_free_cash_flow,
    enterprise_value_multiple,
    dividend_yield,
    prev_current_ratio,
    chg_current_ratio,
    prev_gross_margin,
    chg_gross_margin,
    prev_operating_margin,
    chg_operating_margin,
    prev_net_margin,
    chg_net_margin,
    prev_debt_to_equity,
    chg_debt_to_equity,
    filing_flag,
    filing_form,
    inflation_rate,

    latest_news_id,
    latest_news_title,
    latest_news_content,
    latest_news_published_at,
    daily_news_count,
    latest_general_news_id,
    latest_general_news_title,
    latest_general_news_content,
    latest_general_news_published_at,
    daily_general_news_count,

    source_refs,
    created_at,
    updated_at
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_stock_packages_price_view AS
SELECT
    package_date,
    ticker,
    volume,
    prev_price_close,
    chg_open_vs_prev_close_pct,
    chg_close_vs_open_pct,
    chg_close_vs_prev_close_pct
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_stock_packages_technical_view AS
SELECT
    package_date,
    ticker,
    chg_sma,
    chg_ema,
    chg_wma,
    chg_dema,
    chg_tema,
    chg_rsi,
    chg_standarddeviation,
    chg_williams,
    chg_adx
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_stock_packages_fundamental_view AS
SELECT
    package_date,
    ticker,
    fundamental_period_end_date,
    current_ratio,
    gross_margin,
    operating_margin,
    net_margin,
    debt_to_equity,
    filing_flag,
    filing_form,
    inflation_rate
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_stock_packages_news_view AS
SELECT
    package_date,
    ticker,
    latest_news_id,
    latest_news_title,
    latest_news_content,
    latest_news_published_at,
    daily_news_count,
    latest_general_news_id,
    latest_general_news_title,
    latest_general_news_content,
    latest_general_news_published_at,
    daily_general_news_count
FROM public.daily_stock_packages;
