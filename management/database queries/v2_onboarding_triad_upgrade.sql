-- =============================================================================
-- CAREER BEACON: V2 ONBOARDING & RECOMMENDATION TRIAD SCHEMA UPGRADE
-- Workstreams 1-5: Catalogue Integrity, Provenance, DAG Dependencies & Evidence
-- =============================================================================

-- 1. Catalogue Integrity: Distinguish Curated Careers from AI Proposals
ALTER TABLE public.careers 
ADD COLUMN IF NOT EXISTS is_curated BOOLEAN DEFAULT true;

ALTER TABLE public.careers 
ADD COLUMN IF NOT EXISTS proposing_user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;

-- 2. Career Skills Importance & 3-Tier Hierarchy
-- Tier 1: Foundational Prerequisites (HTML/CSS/Git/Syntax)
-- Tier 2: Core Domain Workhorses (React, SQL, State Management)
-- Tier 3: Specialized Extensions (Docker, Testing, Next.js)
ALTER TABLE public.career_skills 
ADD COLUMN IF NOT EXISTS tier INT DEFAULT 2 CHECK (tier IN (1, 2, 3));

ALTER TABLE public.career_skills 
ADD COLUMN IF NOT EXISTS importance TEXT DEFAULT 'essential' CHECK (importance IN ('essential', 'optional', 'differentiator'));

-- 3. Validated Skill Prerequisites Graph (DAG)
CREATE TABLE IF NOT EXISTS public.skill_dependencies (
    skill_id UUID REFERENCES public.skills(id) ON DELETE CASCADE,
    prerequisite_id UUID REFERENCES public.skills(id) ON DELETE CASCADE,
    rationale TEXT, -- e.g. "JavaScript DOM & Closures required before React State"
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (skill_id, prerequisite_id)
);

-- 4. Evidence-Aware Learner Profiling
-- Distinguish initial self-reported assessments from quiz-verified mastery
ALTER TABLE public.user_skills 
ADD COLUMN IF NOT EXISTS evidence_source TEXT DEFAULT 'self_reported' 
CHECK (evidence_source IN ('self_reported', 'quiz_verified', 'diagnostic_assessment'));

ALTER TABLE public.user_skills 
ADD COLUMN IF NOT EXISTS tier INT DEFAULT 2 CHECK (tier IN (1, 2, 3));

-- 5. Helpful sample dependencies for core web development track
DO $$
DECLARE
    git_id UUID;
    js_id UUID;
    react_id UUID;
BEGIN
    SELECT id INTO git_id FROM public.skills WHERE name ILIKE 'git%' LIMIT 1;
    SELECT id INTO js_id FROM public.skills WHERE name ILIKE 'javascript%' LIMIT 1;
    SELECT id INTO react_id FROM public.skills WHERE name ILIKE 'react%' LIMIT 1;

    IF js_id IS NOT NULL AND react_id IS NOT NULL THEN
        INSERT INTO public.skill_dependencies (skill_id, prerequisite_id, rationale)
        VALUES (react_id, js_id, 'JavaScript syntax, async/await, and closures are prerequisites for React.')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
