-- 1. First, drop the existing indexes since we are changing the vector dimension
DROP INDEX IF EXISTS idx_micro_content_embedding;
DROP INDEX IF EXISTS idx_mentor_qa_embedding;

-- 2. Delete existing seed data to prevent dimension mismatch errors
DELETE FROM career_skills;
DELETE FROM micro_content;
DELETE FROM mentor_qa;
DELETE FROM careers;
DELETE FROM skills;

-- 3. Alter columns to be vector(384) instead of vector(1536)
ALTER TABLE micro_content ALTER COLUMN embedding TYPE vector(384);
ALTER TABLE mentor_qa ALTER COLUMN embedding TYPE vector(384);

-- 4. Add the missing career_vector column to careers table and target_career_id to profiles
ALTER TABLE careers ADD COLUMN IF NOT EXISTS career_vector vector(384);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS target_career_id uuid REFERENCES careers(id) ON DELETE SET NULL;

-- 5. Re-create the indexes with the correct dimensions
CREATE INDEX idx_micro_content_embedding ON micro_content USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_mentor_qa_embedding ON mentor_qa USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_careers_vector ON careers USING hnsw (career_vector vector_cosine_ops);

-- 6. Create the Postgres function for semantic search of careers
CREATE OR REPLACE FUNCTION match_careers (
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  title text,
  description text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    careers.id,
    careers.title,
    careers.description,
    1 - (careers.career_vector <=> query_embedding) AS similarity
  FROM careers
  WHERE 1 - (careers.career_vector <=> query_embedding) > match_threshold
  ORDER BY careers.career_vector <=> query_embedding
  LIMIT match_count;
END;
$$;
