DROP INDEX IF EXISTS idx_fundamental_ratios_lookup;

ALTER TABLE public.fundamental_ratios
DROP COLUMN IF EXISTS company_name,
DROP COLUMN IF EXISTS filing_date,
DROP COLUMN IF EXISTS available_at,
DROP COLUMN IF EXISTS fiscal_quarter,
DROP COLUMN IF EXISTS calendar_quarter,
DROP COLUMN IF EXISTS cash_ratio,
DROP COLUMN IF EXISTS ebit_margin,
DROP COLUMN IF EXISTS ebitda_margin,
DROP COLUMN IF EXISTS pretax_margin,
DROP COLUMN IF EXISTS effective_tax_rate,
DROP COLUMN IF EXISTS return_on_capital_employed,
DROP COLUMN IF EXISTS debt_ratio,
DROP COLUMN IF EXISTS interest_coverage,
DROP COLUMN IF EXISTS price_to_cash_flow,
DROP COLUMN IF EXISTS price_earnings_to_growth,
DROP COLUMN IF EXISTS continuous_operations_profit_margin,
DROP COLUMN IF EXISTS bottom_line_profit_margin,
DROP COLUMN IF EXISTS payables_turnover,
DROP COLUMN IF EXISTS fixed_asset_turnover,
DROP COLUMN IF EXISTS solvency_ratio,
DROP COLUMN IF EXISTS price_to_earnings_growth_ratio,
DROP COLUMN IF EXISTS forward_price_to_earnings_growth_ratio,
DROP COLUMN IF EXISTS price_to_operating_cash_flow,
DROP COLUMN IF EXISTS debt_to_capital_ratio,
DROP COLUMN IF EXISTS long_term_debt_to_capital_ratio,
DROP COLUMN IF EXISTS financial_leverage_ratio,
DROP COLUMN IF EXISTS working_capital_turnover_ratio,
DROP COLUMN IF EXISTS operating_cash_flow_ratio,
DROP COLUMN IF EXISTS operating_cash_flow_sales_ratio,
DROP COLUMN IF EXISTS free_cash_flow_operating_cash_flow_ratio,
DROP COLUMN IF EXISTS debt_service_coverage_ratio,
DROP COLUMN IF EXISTS short_term_operating_cash_flow_coverage_ratio,
DROP COLUMN IF EXISTS operating_cash_flow_coverage_ratio,
DROP COLUMN IF EXISTS capital_expenditure_coverage_ratio,
DROP COLUMN IF EXISTS dividend_paid_and_capex_coverage_ratio,
DROP COLUMN IF EXISTS dividend_payout_ratio,
DROP COLUMN IF EXISTS dividend_yield_percentage,
DROP COLUMN IF EXISTS revenue_per_share,
DROP COLUMN IF EXISTS net_income_per_share,
DROP COLUMN IF EXISTS interest_debt_per_share,
DROP COLUMN IF EXISTS cash_per_share,
DROP COLUMN IF EXISTS book_value_per_share,
DROP COLUMN IF EXISTS tangible_book_value_per_share,
DROP COLUMN IF EXISTS shareholders_equity_per_share,
DROP COLUMN IF EXISTS operating_cash_flow_per_share,
DROP COLUMN IF EXISTS capex_per_share,
DROP COLUMN IF EXISTS free_cash_flow_per_share,
DROP COLUMN IF EXISTS net_income_per_ebt,
DROP COLUMN IF EXISTS ebt_per_ebit,
DROP COLUMN IF EXISTS price_to_fair_value,
DROP COLUMN IF EXISTS debt_to_market_cap;

CREATE INDEX IF NOT EXISTS idx_fundamental_ratios_lookup
ON public.fundamental_ratios (ticker, period_end_date DESC);

DO $$
DECLARE
    target_column text;
    roundable_fundamental_columns text[] := ARRAY[
        'current_ratio',
        'quick_ratio',
        'gross_margin',
        'operating_margin',
        'net_margin',
        'return_on_assets',
        'return_on_equity',
        'debt_to_assets_ratio',
        'debt_to_equity',
        'interest_coverage_ratio',
        'asset_turnover',
        'inventory_turnover',
        'receivables_turnover',
        'price_to_earnings',
        'price_to_book',
        'price_to_sales',
        'price_to_free_cash_flow',
        'enterprise_value_multiple',
        'dividend_yield'
    ];
BEGIN
    FOREACH target_column IN ARRAY roundable_fundamental_columns LOOP
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns c
            WHERE table_schema = 'public'
              AND table_name = 'fundamental_ratios'
              AND c.column_name = target_column
        ) THEN
            EXECUTE format(
                'UPDATE public.fundamental_ratios SET %1$I = round(%1$I, 2) WHERE %1$I IS NOT NULL',
                target_column
            );
        END IF;
    END LOOP;
END $$;

DO $$
DECLARE
    target_column text;
    roundable_indicator_columns text[] := ARRAY[
        'sma',
        'ema',
        'wma',
        'dema',
        'tema',
        'rsi',
        'standarddeviation',
        'williams',
        'adx'
    ];
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'technical_indicators_daily'
    ) THEN
        FOREACH target_column IN ARRAY roundable_indicator_columns LOOP
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns c
                WHERE table_schema = 'public'
                  AND table_name = 'technical_indicators_daily'
                  AND c.column_name = target_column
            ) THEN
                EXECUTE format(
                    'UPDATE public.technical_indicators_daily SET %1$I = round(%1$I, 2) WHERE %1$I IS NOT NULL',
                    target_column
                );
            END IF;
        END LOOP;
    END IF;
END $$;
