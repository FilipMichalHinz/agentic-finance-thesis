CREATE INDEX IF NOT EXISTS idx_knowledge_base_unembedded_id
ON public.knowledge_base (id)
WHERE embedding IS NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_base_unembedded_ticker_id
ON public.knowledge_base (ticker, id)
WHERE embedding IS NULL;
