-- =============================================================================
-- Migration: Dual-Vector Semantic Search for Careers
-- Purpose: Adds title_vector and skills_vector to public.careers
--          Replaces match_careers() RPC with GREATEST(sim_title, sim_skills)
-- =============================================================================

-- 1. Add dual-vector columns to careers table
ALTER TABLE public.careers
    ADD COLUMN IF NOT EXISTS title_vector vector(384),
    ADD COLUMN IF NOT EXISTS skills_vector vector(384);

-- 2. Create HNSW indexes for high-speed cosine distance search (<=>)
CREATE INDEX IF NOT EXISTS idx_careers_title_vector 
    ON public.careers USING hnsw (title_vector vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_careers_skills_vector 
    ON public.careers USING hnsw (skills_vector vector_cosine_ops);

-- 3. Replace match_careers RPC with HNSW-index-backed UNION ALL dual-vector scoring
-- Uses each HNSW index independently via ORDER BY (<=>) LIMIT before taking MAX(similarity),
-- avoiding a full-table sequential scan caused by GREATEST(...) in ORDER BY.
CREATE OR REPLACE FUNCTION public.match_careers (
    query_embedding  vector(384),
    match_threshold  float DEFAULT 0.60,
    match_count      int DEFAULT 8
)
RETURNS TABLE (
    id          uuid,
    title       text,
    description text,
    similarity  float
)
LANGUAGE plpgsql
AS $$
DECLARE
    pool_limit int := GREATEST(match_count * 3, 24);
BEGIN
    RETURN QUERY
    WITH raw_hits AS (
        (
            SELECT c.id, c.title, c.description,
                   (1 - (c.title_vector <=> query_embedding))::float AS sim
            FROM public.careers c
            WHERE c.title_vector IS NOT NULL
            ORDER BY c.title_vector <=> query_embedding
            LIMIT pool_limit
        )
        UNION ALL
        (
            SELECT c.id, c.title, c.description,
                   (1 - (c.skills_vector <=> query_embedding))::float AS sim
            FROM public.careers c
            WHERE c.skills_vector IS NOT NULL
            ORDER BY c.skills_vector <=> query_embedding
            LIMIT pool_limit
        )
        UNION ALL
        (
            SELECT c.id, c.title, c.description,
                   (1 - (c.career_vector <=> query_embedding))::float AS sim
            FROM public.careers c
            WHERE c.career_vector IS NOT NULL
              AND c.title_vector IS NULL
            ORDER BY c.career_vector <=> query_embedding
            LIMIT pool_limit
        )
    ),
    deduped AS (
        SELECT
            r.id,
            r.title,
            r.description,
            MAX(r.sim)::float AS similarity
        FROM raw_hits r
        GROUP BY r.id, r.title, r.description
    )
    SELECT d.id, d.title, d.description, d.similarity
    FROM deduped d
    WHERE d.similarity > match_threshold
    ORDER BY d.similarity DESC
    LIMIT match_count;
END;
$$;

