-- =============================================================================
-- Migration: Add User Metadata & Automated Auth Trigger to Profiles
-- Date: 2026-10-30
-- Target: Supabase PostgreSQL 15
-- Description:
--   1. Adds first_name, last_name, role, status, headline, weekly_hours,
--      linkedin_url, and is_linkedin_verified to public.profiles.
--   2. Creates idempotent on_auth_user_created trigger so that OAuth (Google,
--      LinkedIn) and Email/Password sign-ups automatically populate profiles.
-- =============================================================================

-- 1. Ensure required columns exist on public.profiles
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS first_name text,
    ADD COLUMN IF NOT EXISTS last_name text,
    ADD COLUMN IF NOT EXISTS role text DEFAULT 'learner' CHECK (role IN ('learner', 'mentor', 'admin')),
    ADD COLUMN IF NOT EXISTS status text,
    ADD COLUMN IF NOT EXISTS headline text,
    ADD COLUMN IF NOT EXISTS weekly_hours int DEFAULT 5,
    ADD COLUMN IF NOT EXISTS linkedin_url text,
    ADD COLUMN IF NOT EXISTS is_linkedin_verified boolean DEFAULT false;

-- Create index on role for fast routing checks
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);

-- 2. Trigger function to synchronize auth.users -> public.profiles automatically
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_first_name text;
    v_last_name  text;
    v_full_name  text;
    v_role       text;
    v_status     text;
    v_headline   text;
    v_bio        text;
    v_avatar     text;
    v_linkedin   text;
    v_is_li_ver  boolean;
BEGIN
    v_first_name := new.raw_user_meta_data->>'first_name';
    v_last_name  := new.raw_user_meta_data->>'last_name';
    
    -- Fallback for full_name resolution from first/last or OAuth providers
    v_full_name  := COALESCE(
        new.raw_user_meta_data->>'full_name',
        new.raw_user_meta_data->>'name',
        NULLIF(TRIM(CONCAT_WS(' ', v_first_name, v_last_name)), '')
    );
    
    -- Fallback first/last extraction if OAuth only provided a combined full_name
    IF v_first_name IS NULL AND v_full_name IS NOT NULL THEN
        v_first_name := SPLIT_PART(v_full_name, ' ', 1);
        v_last_name  := NULLIF(SUBSTRING(v_full_name FROM LENGTH(v_first_name) + 2), '');
    END IF;

    v_role       := COALESCE(new.raw_user_meta_data->>'role', 'learner');
    v_status     := new.raw_user_meta_data->>'status';
    v_headline   := new.raw_user_meta_data->>'headline';
    v_bio        := new.raw_user_meta_data->>'bio';
    v_avatar     := COALESCE(new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture');
    v_linkedin   := new.raw_user_meta_data->>'linkedin_url';
    v_is_li_ver  := (new.raw_app_meta_data->>'provider' = 'linkedin' OR new.raw_app_meta_data->>'provider' = 'linkedin_oidc');

    INSERT INTO public.profiles (
        id,
        email,
        full_name,
        first_name,
        last_name,
        role,
        status,
        headline,
        bio,
        avatar_url,
        linkedin_url,
        is_linkedin_verified,
        created_at,
        updated_at
    )
    VALUES (
        new.id,
        new.email,
        v_full_name,
        v_first_name,
        v_last_name,
        v_role,
        v_status,
        v_headline,
        v_bio,
        v_avatar,
        v_linkedin,
        v_is_li_ver,
        NOW(),
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        email                 = EXCLUDED.email,
        full_name             = COALESCE(EXCLUDED.full_name, profiles.full_name),
        first_name            = COALESCE(EXCLUDED.first_name, profiles.first_name),
        last_name             = COALESCE(EXCLUDED.last_name, profiles.last_name),
        avatar_url            = COALESCE(EXCLUDED.avatar_url, profiles.avatar_url),
        role                  = COALESCE(profiles.role, EXCLUDED.role),
        status                = COALESCE(profiles.status, EXCLUDED.status),
        headline              = COALESCE(profiles.headline, EXCLUDED.headline),
        bio                   = COALESCE(profiles.bio, EXCLUDED.bio),
        linkedin_url          = COALESCE(profiles.linkedin_url, EXCLUDED.linkedin_url),
        is_linkedin_verified  = (profiles.is_linkedin_verified OR EXCLUDED.is_linkedin_verified),
        updated_at            = NOW();

    -- If registered as a mentor, automatically initialize placeholder mentor record if not present
    IF v_role = 'mentor' THEN
        INSERT INTO public.mentors (
            id,
            profile_id,
            bio,
            expertise,
            created_at,
            updated_at
        )
        VALUES (
            new.id,
            new.id,
            COALESCE(v_bio, 'Mentor profile pending initialization'),
            COALESCE(v_headline, 'General Mentorship'),
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
    END IF;

    RETURN new;
END;
$$;

-- 3. Attach trigger to auth.users (idempotent)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

