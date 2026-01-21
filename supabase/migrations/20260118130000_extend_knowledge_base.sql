ALTER TABLE public.knowledge_base
  ADD COLUMN IF NOT EXISTS accession_number text,
  ADD COLUMN IF NOT EXISTS chunk_index integer,
  ADD COLUMN IF NOT EXISTS acceptance_datetime timestamp with time zone,
  ADD COLUMN IF NOT EXISTS filing_date date,
  ADD COLUMN IF NOT EXISTS source_url text;

-- Ensure published_at remains required for time-travel filtering
-- (No change; using acceptance_datetime to populate it in ingestion)

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'knowledge_base_accession_chunk_unique'
  ) THEN
    ALTER TABLE public.knowledge_base
      ADD CONSTRAINT knowledge_base_accession_chunk_unique
      UNIQUE (accession_number, chunk_index);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_kb_accession_number
  ON public.knowledge_base (accession_number);

CREATE INDEX IF NOT EXISTS idx_kb_acceptance_datetime
  ON public.knowledge_base (acceptance_datetime);
