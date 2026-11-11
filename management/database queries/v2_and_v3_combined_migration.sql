-- =============================================================================
-- CAREER BEACON: REVISED V2 & V3 ONBOARDING SCHEMA MIGRATION
-- Run in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/suagljghrticmonbrdrc/sql/new
--
-- Design Principles Applied:
-- 1. Source origin ('onet', 'esco', 'dual_sourced', 'llm') separated from review status ('unreviewed', 'curated').
-- 2. is_curated defaults to FALSE (neither new proposals nor raw imports are automatically curated).
-- 3. expected_proficiency (0-100) and career_level are constrained as a pair (both null or both present).
-- 4. skill_dependencies prevents self-links (skill_id <> prerequisite_id).
-- 5. No fabricated prerequisite edges inserted during migration.
-- 6. No arbitrary defaults on importance; unevidenced fields remain NULL.
-- 7. No unsafe retroactive backfills.
-- =============================================================================

-- =============================================================================
-- SECTION 1: CAREERS TABLE — Catalogue Integrity & Provenance
-- =============================================================================

-- Distinguishes internally curated careers from unreviewed/imported careers
ALTER TABLE public.careers 
  ADD COLUMN IF NOT EXISTS is_curated BOOLEAN DEFAULT false;

-- Tracks user proposal origin if created during onboarding
ALTER TABLE public.careers 
  ADD COLUMN IF NOT EXISTS proposing_user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;

-- Where this career originated
ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS source_origin TEXT
    DEFAULT 'llm'
    CHECK (source_origin IN ('onet', 'esco', 'dual_sourced', 'curated_list', 'manual', 'llm'));

-- Internal review / curation lifecycle state
ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS review_status TEXT
    DEFAULT 'unreviewed'
    CHECK (review_status IN ('unreviewed', 'in_review', 'curated', 'rejected'));

-- Explicitly mark pre-existing legacy rows as unreviewed starter data
UPDATE public.careers
  SET source_origin = 'curated_list', review_status = 'unreviewed', is_curated = false
  WHERE source_origin IS NULL;

-- External identifiers (both preserved independently)
ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS onet_soc_code TEXT;

ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS esco_occupation_uri TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_careers_onet_soc_code
  ON public.careers (onet_soc_code)
  WHERE onet_soc_code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_careers_esco_uri
  ON public.careers (esco_occupation_uri)
  WHERE esco_occupation_uri IS NOT NULL;


-- =============================================================================
-- SECTION 2: SKILLS TABLE — Canonical Cross-Source Identifiers
-- =============================================================================

ALTER TABLE public.skills
  ADD COLUMN IF NOT EXISTS onet_element_id TEXT;

ALTER TABLE public.skills
  ADD COLUMN IF NOT EXISTS esco_skill_uri TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_onet_element_id
  ON public.skills (onet_element_id)
  WHERE onet_element_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_esco_skill_uri
  ON public.skills (esco_skill_uri)
  WHERE esco_skill_uri IS NOT NULL;


-- =============================================================================
-- SECTION 3: CAREER_SKILLS TABLE — Career-Specific Relevance & Targets
-- =============================================================================

-- Where this career-skill connection came from
ALTER TABLE public.career_skills
  ADD COLUMN IF NOT EXISTS source_origin TEXT
    DEFAULT 'llm'
    CHECK (source_origin IN ('onet', 'esco', 'dual_sourced', 'curated_list', 'manual', 'llm'));

-- Verification status of this specific skill mapping
ALTER TABLE public.career_skills
  ADD COLUMN IF NOT EXISTS review_status TEXT
    DEFAULT 'unreviewed'
    CHECK (review_status IN ('unreviewed', 'curated', 'rejected'));

-- Explicitly mark pre-existing legacy mappings as unreviewed starter data
UPDATE public.career_skills
  SET source_origin = 'curated_list', review_status = 'unreviewed'
  WHERE source_origin IS NULL;

-- Derived normalized importance score (0.000 to 1.000)
-- Documented project scale: O*NET (Data_Value - 1) / 4; ESCO essential=1.0, optional=0.5
ALTER TABLE public.career_skills
  ADD COLUMN IF NOT EXISTS importance_score NUMERIC(4,3)
    CHECK (importance_score BETWEEN 0.000 AND 1.000);

-- Raw source qualitative importance (no default; populated only from source evidence)
ALTER TABLE public.career_skills
  ADD COLUMN IF NOT EXISTS importance TEXT
    CHECK (importance IN ('essential', 'optional', 'differentiator'));

-- Optional high-level display tier (1=Foundational, 2=Core, 3=Specialized)
-- NULL on automated ingestion; populated only when an evidence-backed curriculum rule exists
ALTER TABLE public.career_skills 
  ADD COLUMN IF NOT EXISTS tier INT 
    CHECK (tier IN (1, 2, 3));

-- Target proficiency (0-100) and career level
-- Both must be NULL or both must be present (prevents orphaned targets without level context)
ALTER TABLE public.career_skills 
  ADD COLUMN IF NOT EXISTS expected_proficiency INT 
    CHECK (expected_proficiency BETWEEN 0 AND 100);

ALTER TABLE public.career_skills 
  ADD COLUMN IF NOT EXISTS career_level TEXT 
    CHECK (career_level IN ('entry', 'mid', 'senior', 'lead'));

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_career_skills_target_level_pair'
  ) THEN
    ALTER TABLE public.career_skills
      ADD CONSTRAINT chk_career_skills_target_level_pair
      CHECK (
        (expected_proficiency IS NULL AND career_level IS NULL) OR
        (expected_proficiency IS NOT NULL AND career_level IS NOT NULL)
      );
  END IF;
END $$;


-- =============================================================================
-- SECTION 4: SKILL_DEPENDENCIES TABLE — Typed Skill Relationships Graph
-- =============================================================================
-- Stores typed relationships between skills.
-- Note: 'requires' edges represent directed prerequisites (enforced acyclic by app logic).
-- 'related_to' (concept overlap) and 'alternative_to' (substitutes) may be symmetric or cyclic.
-- Zero edges are inserted during migration; populated only through validated review.

CREATE TABLE IF NOT EXISTS public.skill_dependencies (
    skill_id UUID REFERENCES public.skills(id) ON DELETE CASCADE,
    prerequisite_id UUID REFERENCES public.skills(id) ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'requires' 
        CHECK (relationship_type IN ('requires', 'supports', 'related_to', 'alternative_to')),
    rationale TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (skill_id, prerequisite_id, relationship_type),
    CONSTRAINT chk_skill_deps_no_self_link CHECK (skill_id <> prerequisite_id)
);

-- Ensure constraint exists even if skill_dependencies was created previously
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_skill_deps_no_self_link'
  ) THEN
    ALTER TABLE public.skill_dependencies
      ADD CONSTRAINT chk_skill_deps_no_self_link
      CHECK (skill_id <> prerequisite_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_skill_deps_prereq
  ON public.skill_dependencies (prerequisite_id);


-- =============================================================================
-- SECTION 5: USER_SKILLS TABLE — Learner Profile Evidence
-- =============================================================================

-- Tracks how the learner's score was obtained
ALTER TABLE public.user_skills 
  ADD COLUMN IF NOT EXISTS evidence_source TEXT DEFAULT 'self_reported' 
    CHECK (evidence_source IN ('self_reported', 'quiz_verified', 'diagnostic_assessment'));


-- =============================================================================
-- SECTION 6: PENDING_CAREERS TABLE — LLM Quarantine
-- =============================================================================
-- AI-generated career proposals are isolated here from the main careers table
-- until explicitly reviewed and promoted by an administrator.

CREATE TABLE IF NOT EXISTS public.pending_careers (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposed_by        UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  title              TEXT NOT NULL,
  description        TEXT,
  provisional_skills JSONB DEFAULT '[]'::JSONB,
  status             TEXT DEFAULT 'pending'
    CHECK (status IN ('pending', 'promoted', 'rejected')),
  promoted_career_id UUID REFERENCES public.careers(id) ON DELETE SET NULL,
  reviewer_notes     TEXT,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  reviewed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pending_careers_status
  ON public.pending_careers (status);

CREATE INDEX IF NOT EXISTS idx_pending_careers_proposed_by
  ON public.pending_careers (proposed_by);

-- =============================================================================
-- END OF REVISED MIGRATION
-- =============================================================================
