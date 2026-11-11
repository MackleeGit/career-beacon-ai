-- =============================================================================
-- CAREER BEACON: COMPLETE CURRENT DATABASE SCHEMA
-- Target Environment: Supabase PostgreSQL 15 + pgvector Extension
-- Date / State: Current Active Database Schema (Post V2/V3 Combined Migration)
-- Description: Unified, single-file DDL script reflecting the exact active
--              state of the database, including vector(384) HNSW indexes,
--              external taxonomy identifiers (O*NET & ESCO), DAG prerequisites,
--              AI quarantine tables, relational constraints, and pgvector RPCs.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. EXTENSIONS & ENUMS
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('learner', 'mentor', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- -----------------------------------------------------------------------------
-- 2. CORE RELATIONAL & PROVENANCE CATALOGUE TABLES
-- -----------------------------------------------------------------------------

-- Profiles Table (Users authenticated via Supabase Auth)
CREATE TABLE IF NOT EXISTS public.profiles (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email                text NOT NULL UNIQUE,
    full_name            text,
    first_name           text,
    last_name            text,
    role                 text DEFAULT 'learner' CHECK (role IN ('learner', 'mentor', 'admin')),
    status               text,
    headline             text,
    avatar_url           text,
    bio                  text,
    weekly_hours         int DEFAULT 5,
    linkedin_url         text,
    is_linkedin_verified boolean DEFAULT false,
    target_career_id     uuid, -- foreign key constraint added after careers table creation
    created_at           timestamp with time zone DEFAULT now(),
    updated_at           timestamp with time zone DEFAULT now()
);

-- Careers Table (with 384-dimensional dense vector embeddings & provenance)
CREATE TABLE IF NOT EXISTS public.careers (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title               text NOT NULL UNIQUE,
    description         text,
    career_vector       vector(384),
    is_curated          boolean DEFAULT false,
    proposing_user_id   uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    source_origin       text DEFAULT 'llm'
                        CHECK (source_origin IN ('onet', 'esco', 'dual_sourced', 'curated_list', 'manual', 'llm')),
    review_status       text DEFAULT 'unreviewed'
                        CHECK (review_status IN ('unreviewed', 'in_review', 'curated', 'rejected')),
    onet_soc_code       text,
    esco_occupation_uri text,
    created_at          timestamp with time zone DEFAULT now(),
    updated_at          timestamp with time zone DEFAULT now()
);

-- Deferred foreign key link from profiles to careers
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_profiles_target_career'
    ) THEN
        ALTER TABLE public.profiles 
            ADD CONSTRAINT fk_profiles_target_career 
            FOREIGN KEY (target_career_id) REFERENCES public.careers(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Skills Table (Master taxonomy of normalized industry skills & standard identifiers)
CREATE TABLE IF NOT EXISTS public.skills (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,
    category        text,
    onet_element_id text,
    esco_skill_uri  text,
    created_at      timestamp with time zone DEFAULT now(),
    updated_at      timestamp with time zone DEFAULT now()
);

-- Career Skills Junction (Career-to-skill mappings with provenance, targets & tiers)
CREATE TABLE IF NOT EXISTS public.career_skills (
    career_id            uuid REFERENCES public.careers(id) ON DELETE CASCADE,
    skill_id             uuid REFERENCES public.skills(id) ON DELETE CASCADE,
    rank                 int NOT NULL DEFAULT 0,
    source_origin        text DEFAULT 'llm'
                         CHECK (source_origin IN ('onet', 'esco', 'dual_sourced', 'curated_list', 'manual', 'llm')),
    review_status        text DEFAULT 'unreviewed'
                         CHECK (review_status IN ('unreviewed', 'curated', 'rejected')),
    importance_score     numeric(4,3)
                         CHECK (importance_score BETWEEN 0.000 AND 1.000),
    importance           text
                         CHECK (importance IN ('essential', 'optional', 'differentiator')),
    tier                 int
                         CHECK (tier IN (1, 2, 3)),
    expected_proficiency int
                         CHECK (expected_proficiency BETWEEN 0 AND 100),
    career_level         text
                         CHECK (career_level IN ('entry', 'mid', 'senior', 'lead')),
    PRIMARY KEY (career_id, skill_id),
    CONSTRAINT chk_career_skills_target_level_pair CHECK (
        (expected_proficiency IS NULL AND career_level IS NULL) OR
        (expected_proficiency IS NOT NULL AND career_level IS NOT NULL)
    )
);

-- User Skills Junction (Learner proficiency tracking & assessment evidence source)
CREATE TABLE IF NOT EXISTS public.user_skills (
    user_id         uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill_id        uuid REFERENCES public.skills(id) ON DELETE CASCADE,
    proficiency     int NOT NULL CHECK (proficiency BETWEEN 0 AND 100),
    evidence_source text DEFAULT 'self_reported'
                    CHECK (evidence_source IN ('self_reported', 'quiz_verified', 'diagnostic_assessment')),
    last_used       timestamp with time zone DEFAULT now(),
    PRIMARY KEY (user_id, skill_id)
);

-- Skill Dependencies Table (Typed Directed Acyclic Graph of Skill Relationships)
CREATE TABLE IF NOT EXISTS public.skill_dependencies (
    skill_id          uuid REFERENCES public.skills(id) ON DELETE CASCADE,
    prerequisite_id   uuid REFERENCES public.skills(id) ON DELETE CASCADE,
    relationship_type text DEFAULT 'requires'
                      CHECK (relationship_type IN ('requires', 'supports', 'related_to', 'alternative_to')),
    rationale         text,
    created_at        timestamp with time zone DEFAULT now(),
    PRIMARY KEY (skill_id, prerequisite_id, relationship_type),
    CONSTRAINT chk_skill_deps_no_self_link CHECK (skill_id <> prerequisite_id)
);

-- Pending Careers Table (Quarantine table for AI-suggested or unreviewed career proposals)
CREATE TABLE IF NOT EXISTS public.pending_careers (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proposed_by        uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    title              text NOT NULL,
    description        text,
    provisional_skills jsonb DEFAULT '[]'::jsonb,
    status             text DEFAULT 'pending'
                       CHECK (status IN ('pending', 'promoted', 'rejected')),
    promoted_career_id uuid REFERENCES public.careers(id) ON DELETE SET NULL,
    reviewer_notes     text,
    created_at         timestamp with time zone DEFAULT now(),
    reviewed_at        timestamp with time zone
);

-- -----------------------------------------------------------------------------
-- 3. MICRO-LEARNING CONTENT & QUIZZES
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.micro_content (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    associated_skill_id uuid REFERENCES public.skills(id) ON DELETE SET NULL,
    title               text NOT NULL,
    summary_bullets     text,
    content             text,
    difficulty_level    int CHECK (difficulty_level BETWEEN 1 AND 5) DEFAULT 1,
    source_trust_score  numeric(3,2) CHECK (source_trust_score BETWEEN 0.00 AND 1.00) DEFAULT 1.00,
    quizzes             jsonb DEFAULT '[]'::jsonb,
    embedding           vector(384),
    source_url          text UNIQUE,
    created_at          timestamp with time zone DEFAULT now(),
    updated_at          timestamp with time zone DEFAULT now()
);

-- Assessment Attempts Table (Durable attempt history, retakes, and audit trail)
CREATE TABLE IF NOT EXISTS public.assessment_attempts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    lesson_id       uuid REFERENCES public.micro_content(id) ON DELETE CASCADE,
    skill_id        uuid REFERENCES public.skills(id) ON DELETE SET NULL,
    attempt_number  int NOT NULL DEFAULT 1,
    answers         jsonb DEFAULT '{}'::jsonb,
    score           int NOT NULL,
    total           int NOT NULL,
    percentage      numeric(4,1) NOT NULL,
    passed          boolean NOT NULL,
    created_at      timestamp with time zone DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user_lesson ON public.assessment_attempts (user_id, lesson_id, attempt_number);

-- User Content Activity Table (Interaction tracking: impressions, opens, completions)
CREATE TABLE IF NOT EXISTS public.user_content_activity (
    user_id           uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    content_id        uuid REFERENCES public.micro_content(id) ON DELETE CASCADE,
    first_seen_at     timestamp with time zone DEFAULT now(),
    last_seen_at      timestamp with time zone DEFAULT now(),
    opened_at         timestamp with time zone,
    completed_at      timestamp with time zone,
    times_recommended int NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, content_id)
);

CREATE INDEX IF NOT EXISTS idx_user_content_activity_user_last_seen ON public.user_content_activity (user_id, last_seen_at);

-- -----------------------------------------------------------------------------
-- 4. MENTORSHIP & EXPERT MARKETPLACE
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.mentors (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id    uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    bio           text,
    expertise     text,
    rating_avg    numeric(3,2) DEFAULT 0.00,
    rating_count  int DEFAULT 0,
    mentor_vector vector(384),
    created_at    timestamp with time zone DEFAULT now(),
    updated_at    timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.mentor_qa (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mentor_id     uuid REFERENCES public.mentors(id) ON DELETE CASCADE,
    question      text NOT NULL,
    answer        text NOT NULL,
    embedding     vector(384),
    created_at    timestamp with time zone DEFAULT now(),
    updated_at    timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.bookings (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mentor_id     uuid REFERENCES public.mentors(id) ON DELETE SET NULL,
    user_id       uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    start_time    timestamp with time zone NOT NULL,
    end_time      timestamp with time zone NOT NULL,
    status        text NOT NULL CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    meeting_link  text,
    created_at    timestamp with time zone DEFAULT now(),
    updated_at    timestamp with time zone DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- 5. INDEXES (Relational, External Identifiers & HNSW Vector Indexes)
-- -----------------------------------------------------------------------------

-- Standard B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_target_career ON public.profiles(target_career_id);
CREATE INDEX IF NOT EXISTS idx_careers_title ON public.careers(title);
CREATE INDEX IF NOT EXISTS idx_careers_proposing_user ON public.careers(proposing_user_id);
CREATE INDEX IF NOT EXISTS idx_skills_name ON public.skills(name);
CREATE INDEX IF NOT EXISTS idx_micro_content_skill ON public.micro_content(associated_skill_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON public.bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_mentor_id ON public.bookings(mentor_id);
CREATE INDEX IF NOT EXISTS idx_skill_deps_prereq ON public.skill_dependencies(prerequisite_id);
CREATE INDEX IF NOT EXISTS idx_pending_careers_status ON public.pending_careers(status);
CREATE INDEX IF NOT EXISTS idx_pending_careers_proposed_by ON public.pending_careers(proposed_by);

-- Sparse Unique Indexes for External Taxonomy Identifiers
CREATE UNIQUE INDEX IF NOT EXISTS idx_careers_onet_soc_code 
    ON public.careers (onet_soc_code) 
    WHERE onet_soc_code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_careers_esco_uri 
    ON public.careers (esco_occupation_uri) 
    WHERE esco_occupation_uri IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_onet_element_id 
    ON public.skills (onet_element_id) 
    WHERE onet_element_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_esco_skill_uri 
    ON public.skills (esco_skill_uri) 
    WHERE esco_skill_uri IS NOT NULL;

-- High-Performance HNSW Vector Cosine Indexes (384-dimensional embeddings)
CREATE INDEX IF NOT EXISTS idx_careers_vector 
    ON public.careers USING hnsw (career_vector vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_micro_content_embedding 
    ON public.micro_content USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_mentor_qa_embedding 
    ON public.mentor_qa USING hnsw (embedding vector_cosine_ops);

-- -----------------------------------------------------------------------------
-- 6. STORED PROCEDURES (pgvector RPC Functions)
-- -----------------------------------------------------------------------------

-- RPC 1: Semantic Career Search
CREATE OR REPLACE FUNCTION public.match_careers (
    query_embedding  vector(384),
    match_threshold  float,
    match_count      int
)
RETURNS TABLE (
    id          uuid,
    title       text,
    description text,
    similarity  float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        careers.id,
        careers.title,
        careers.description,
        (1 - (careers.career_vector <=> query_embedding))::float AS similarity
    FROM public.careers
    WHERE careers.career_vector IS NOT NULL
      AND (1 - (careers.career_vector <=> query_embedding)) > match_threshold
    ORDER BY careers.career_vector <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- RPC 2: Stage 1 Semantic Recall for Micro-Learning Lessons
CREATE OR REPLACE FUNCTION public.match_micro_content (
    query_embedding     vector(384),
    match_threshold     float DEFAULT 0.0,
    match_count         int DEFAULT 30
)
RETURNS TABLE (
    id                  uuid,
    title               text,
    source_url          text,
    summary_bullets     text,
    associated_skill_id uuid,
    difficulty_level    int,
    source_trust_score  numeric,
    quizzes             jsonb,
    similarity          float
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
    FROM public.micro_content
    WHERE micro_content.embedding IS NOT NULL
      AND (1 - (micro_content.embedding <=> query_embedding)) >= match_threshold
    ORDER BY micro_content.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
