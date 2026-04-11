ALTER TABLE public.fundamental_ratios
ADD COLUMN IF NOT EXISTS filing_date date;

CREATE INDEX IF NOT EXISTS idx_fundamental_ratios_ticker_filing_date
ON public.fundamental_ratios (ticker, filing_date DESC, period_end_date DESC);
