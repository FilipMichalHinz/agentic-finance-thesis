DROP VIEW IF EXISTS public.daily_shared_context_view;

CREATE OR REPLACE VIEW public.daily_news_shared_context_view AS
SELECT DISTINCT ON (package_date)
    package_date,
    latest_general_news_id,
    latest_general_news_title,
    latest_general_news_content,
    latest_general_news_published_at,
    daily_general_news_count
FROM public.daily_stock_packages
ORDER BY package_date, latest_general_news_published_at DESC NULLS LAST, latest_general_news_id DESC NULLS LAST;


CREATE OR REPLACE VIEW public.daily_fundamental_shared_context_view AS
SELECT DISTINCT ON (package_date)
    package_date,
    inflation_rate
FROM public.daily_stock_packages
ORDER BY package_date, inflation_rate DESC NULLS LAST;
