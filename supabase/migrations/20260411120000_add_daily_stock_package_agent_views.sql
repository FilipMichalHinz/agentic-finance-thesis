CREATE OR REPLACE VIEW public.daily_stock_packages_price_view AS
SELECT
    package_date,
    ticker,
    dataset_version,
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
    dataset_version,
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
    dataset_version,
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
    dataset_version,
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
