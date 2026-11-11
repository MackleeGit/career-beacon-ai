-- =============================================================================
-- CAREER BEACON: V3 PROVENANCE & EXTERNAL SOURCE SCHEMA UPGRADE
-- Extends v2_onboarding_triad_upgrade.sql
--
-- Purpose:
--   Establishes a provenance boundary between trusted external career-skill
--   knowledge (O*NET, ESCO) and provisional AI-generated or unreviewed content.
--
-- Design principles applied:
--   1. Learner personal edits (user_skills) must never mutate career_skills.
--   2. LLM-generated careers are quarantined until explicitly promoted.
--   3. Source provenance is stored separately from review/approval status.
--   4. O*NET and ESCO use different skill identifiers; both are preserved.
--
-- Run order: v1 schema → v2_onboarding_triad_upgrade.sql → THIS FILE
-- =============================================================================


-- -----------------------------------------------------------------------------
-- SECTION 1: CAREERS TABLE — Provenance & External Source Identity
-- -----------------------------------------------------------------------------

-- Where did this career profile originate?
ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS provenance TEXT
    DEFAULT 'llm_provisional'
    CHECK (provenance IN ('onet', 'esco', 'human_reviewed', 'llm_provisional'));

-- O*NET Standard Occupational Classification code (e.g. "15-2051.00")
ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS onet_soc_code TEXT;

-- ESCO occupation concept URI
ALTER TABLE public.careers
  ADD COLUMN IF NOT EXISTS esco_occupation_uri TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_careers_onet_soc_code
  ON public.careers (onet_soc_code)
  WHERE onet_soc_code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_careers_esco_uri
  ON public.careers (esco_occupation_uri)
  WHERE esco_occupation_uri IS NOT NULL;


-- -----------------------------------------------------------------------------
-- SECTION 2: SKILLS TABLE — Cross-Source External References
-- -----------------------------------------------------------------------------

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


-- -----------------------------------------------------------------------------
-- SECTION 3: CAREER_SKILLS TABLE — Per-Mapping Provenance & Importance Score
-- NOTE: 'learner_added' excluded. Learner customisations belong in user_skills.
-- -----------------------------------------------------------------------------

ALTER TABLE public.career_skills
  ADD COLUMN IF NOT EXISTS skill_source TEXT
    DEFAULT 'llm_provisional'
    CHECK (skill_source IN ('onet', 'esco', 'human_reviewed', 'llm_provisional'));

-- Normalised importance:
-- O*NET importance rating (1–5) → (value - 1) / 4.0 → 0.00–1.00
-- ESCO essential → 1.00, optional → 0.50
ALTER TABLE public.career_skills
  ADD COLUMN IF NOT EXISTS importance_score NUMERIC(4,3)
    CHECK (importance_score BETWEEN 0.000 AND 1.000);


-- -----------------------------------------------------------------------------
-- SECTION 4: USER_SKILLS TABLE — Evidence Confidence
-- Separates "did they attempt?" from "did they pass?"
-- -----------------------------------------------------------------------------

ALTER TABLE public.user_skills
  ADD COLUMN IF NOT EXISTS evidence_confidence TEXT
    DEFAULT 'self_reported'
    CHECK (evidence_confidence IN ('self_reported', 'quiz_attempted', 'quiz_verified'));


-- -----------------------------------------------------------------------------
-- SECTION 5: PENDING CAREERS — LLM Quarantine Table
-- LLM-generated career profiles isolated from the shared careers table.
-- Promotion requires explicit admin action.
-- -----------------------------------------------------------------------------

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


-- -----------------------------------------------------------------------------
-- SECTION 6: MIGRATE EXISTING DATA
-- Sync provenance for careers already marked is_curated in v2.
-- -----------------------------------------------------------------------------

UPDATE public.careers
  SET provenance = 'human_reviewed'
  WHERE is_curated = TRUE AND provenance = 'llm_provisional';

UPDATE public.careers
  SET provenance = 'llm_provisional'
  WHERE is_curated = FALSE AND provenance IS NULL;

UPDATE public.career_skills cs
  SET skill_source = 'human_reviewed'
  FROM public.careers c
  WHERE cs.career_id = c.id
    AND c.provenance = 'human_reviewed'
    AND cs.skill_source = 'llm_provisional';


-- =============================================================================
-- END OF V3 MIGRATION
-- =============================================================================
