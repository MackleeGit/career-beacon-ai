-- =============================================================================
-- Interval 6 Schema Enhancements (micro_content)
-- Ran in Supabase SQL Editor to enable native column storage
-- for micro-learning lessons, 5-question MCQs, and trust/difficulty metadata.
-- =============================================================================

-- 1. Add dedicated skill junction and metadata columns
ALTER TABLE public.micro_content 
    ADD COLUMN IF NOT EXISTS associated_skill_id uuid REFERENCES public.skills(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS summary_bullets text,
    ADD COLUMN IF NOT EXISTS difficulty_level int CHECK (difficulty_level BETWEEN 1 AND 5) DEFAULT 1,
    ADD COLUMN IF NOT EXISTS source_trust_score numeric(3,2) CHECK (source_trust_score BETWEEN 0.00 AND 1.00) DEFAULT 1.00,
    ADD COLUMN IF NOT EXISTS quizzes jsonb DEFAULT '[]'::jsonb;

-- 2. Add unique constraint on source_url for deterministic upserts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'micro_content_source_url_key'
    ) THEN
        ALTER TABLE public.micro_content ADD CONSTRAINT micro_content_source_url_key UNIQUE (source_url);
    END IF;
END $$;

-- 3. Verify HNSW index on embeddings exists
CREATE INDEX IF NOT EXISTS idx_micro_content_embedding 
    ON public.micro_content USING hnsw (embedding vector_cosine_ops);
