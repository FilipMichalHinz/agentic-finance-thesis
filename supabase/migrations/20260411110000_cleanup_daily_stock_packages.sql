ALTER TABLE public.daily_stock_packages
DROP CONSTRAINT IF EXISTS daily_stock_packages_unique;

DROP INDEX IF EXISTS idx_daily_stock_packages_variant;

ALTER TABLE public.daily_stock_packages
DROP COLUMN IF EXISTS scenario_id,
DROP COLUMN IF EXISTS manipulation_mode,
DROP COLUMN IF EXISTS technical_trigger_flag,
DROP COLUMN IF EXISTS technical_trigger_reason,
DROP COLUMN IF EXISTS return_on_assets,
DROP COLUMN IF EXISTS return_on_equity,
DROP COLUMN IF EXISTS fundamental_trigger_flag,
DROP COLUMN IF EXISTS fundamental_trigger_reason,
DROP COLUMN IF EXISTS news_trigger_flag,
DROP COLUMN IF EXISTS news_trigger_reason,
DROP COLUMN IF EXISTS latest_macro_indicator_name,
DROP COLUMN IF EXISTS latest_macro_indicator_value;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_news_id'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_news_id TO latest_news_id;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_news_title'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_news_title TO latest_news_title;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_news_content'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_news_content TO latest_news_content;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_news_published_at'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_news_published_at TO latest_news_published_at;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_general_news_id'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_general_news_id TO latest_general_news_id;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_general_news_title'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_general_news_title TO latest_general_news_title;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_general_news_content'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_general_news_content TO latest_general_news_content;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_stock_packages'
          AND column_name = 'selected_general_news_published_at'
    ) THEN
        ALTER TABLE public.daily_stock_packages
        RENAME COLUMN selected_general_news_published_at TO latest_general_news_published_at;
    END IF;
END $$;

ALTER TABLE public.daily_stock_packages
ADD COLUMN IF NOT EXISTS chg_wma numeric,
ADD COLUMN IF NOT EXISTS chg_dema numeric,
ADD COLUMN IF NOT EXISTS chg_tema numeric,
ADD COLUMN IF NOT EXISTS chg_standarddeviation numeric,
ADD COLUMN IF NOT EXISTS inflation_rate numeric;

ALTER TABLE public.daily_stock_packages
ADD CONSTRAINT daily_stock_packages_unique
UNIQUE (package_date, ticker, dataset_version);

CREATE INDEX IF NOT EXISTS idx_daily_stock_packages_dataset_version
ON public.daily_stock_packages (dataset_version, package_date);
