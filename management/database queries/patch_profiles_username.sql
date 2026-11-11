-- Migration: Add Unique Username to Profiles
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS username text UNIQUE;

CREATE INDEX IF NOT EXISTS idx_profiles_username_lower 
    ON public.profiles (LOWER(username));

