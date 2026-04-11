ALTER TABLE public.daily_stock_packages
ADD COLUMN IF NOT EXISTS fundamental_filing_date date;

DROP VIEW IF EXISTS public.daily_fundamental_analyst_screening_view;

CREATE OR REPLACE VIEW public.daily_fundamental_analyst_screening_view AS
SELECT
    package_date,
    ticker,
    price_close,
    chg_close_vs_prev_close_pct,
    chg_close_vs_open_pct,
    fundamental_period_end_date,
    fundamental_filing_date,
    filing_flag,
    filing_form,
    price_to_earnings,
    price_to_sales
FROM public.daily_stock_packages;
