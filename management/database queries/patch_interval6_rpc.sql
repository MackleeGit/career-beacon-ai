-- =============================================================================
-- Interval 6 Stored Procedure: match_micro_content
-- Run in Supabase SQL Editor to enable Stage 1 pgvector coarse filtering
-- for the Two-Stage Hybrid Recommendation Engine.
-- =============================================================================

CREATE OR REPLACE FUNCTION match_micro_content (
  query_embedding vector(384),
  match_threshold float DEFAULT 0.0,
  match_count int DEFAULT 30
)
RETURNS TABLE (
  id uuid,
  title text,
  source_url text,
  summary_bullets text,
  associated_skill_id uuid,
  difficulty_level int,
  source_trust_score numeric,
  quizzes jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    micro_content.id,
    micro_content.title,
    micro_content.source_url,
    micro_content.summary_bullets,
    micro_content.associated_skill_id,
    micro_content.difficulty_level,
    micro_content.source_trust_score,
    micro_content.quizzes,
    (1 - (micro_content.embedding <=> query_embedding))::float AS similarity
  FROM micro_content
  WHERE micro_content.embedding IS NOT NULL
    AND (1 - (micro_content.embedding <=> query_embedding)) >= match_threshold
  ORDER BY micro_content.embedding <=> query_embedding ASC
  LIMIT match_count;
END;
$$;
