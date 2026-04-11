DROP VIEW IF EXISTS public.daily_technical_analyst_screening_view;
DROP VIEW IF EXISTS public.daily_fundamental_analyst_screening_view;
DROP VIEW IF EXISTS public.daily_news_analyst_screening_view;

CREATE OR REPLACE VIEW public.daily_technical_analyst_screening_view AS
SELECT
    package_date,
    ticker,
    price_close,
    volume,
    chg_close_vs_prev_close_pct,
    chg_close_vs_open_pct,
    chg_ema,
    chg_rsi,
    chg_adx,
    chg_standarddeviation
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_fundamental_analyst_screening_view AS
SELECT
    package_date,
    ticker,
    price_close,
    chg_close_vs_prev_close_pct,
    chg_close_vs_open_pct,
    fundamental_period_end_date,
    filing_flag,
    filing_form,
    price_to_earnings,
    price_to_sales
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_news_analyst_screening_view AS
SELECT
    package_date,
    ticker,
    price_close,
    chg_close_vs_prev_close_pct,
    chg_close_vs_open_pct,
    latest_news_id,
    latest_news_title,
    daily_news_count
FROM public.daily_stock_packages;


CREATE OR REPLACE VIEW public.daily_shared_context_view AS
SELECT DISTINCT ON (package_date)
    package_date,
    latest_general_news_id,
    latest_general_news_title,
    latest_general_news_content,
    latest_general_news_published_at,
    daily_general_news_count,
    inflation_rate
FROM public.daily_stock_packages
ORDER BY package_date, latest_general_news_published_at DESC NULLS LAST, latest_general_news_id DESC NULLS LAST;
