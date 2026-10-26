-- Learning history tables used by LearningHistoryService.
-- Apply once to the intended Supabase project; service-role backend access bypasses RLS.
CREATE TABLE IF NOT EXISTS public.assessment_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    lesson_id uuid REFERENCES public.micro_content(id) ON DELETE CASCADE,
    skill_id uuid REFERENCES public.skills(id) ON DELETE SET NULL,
    attempt_number integer NOT NULL DEFAULT 1,
    answers jsonb NOT NULL DEFAULT '{}'::jsonb,
    score integer NOT NULL,
    total integer NOT NULL,
    percentage numeric(4,1) NOT NULL,
    passed boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user_lesson
    ON public.assessment_attempts (user_id, lesson_id, attempt_number);

CREATE TABLE IF NOT EXISTS public.user_content_activity (
    user_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    content_id uuid REFERENCES public.micro_content(id) ON DELETE CASCADE,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    opened_at timestamptz,
    completed_at timestamptz,
    times_recommended integer NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, content_id)
);
CREATE INDEX IF NOT EXISTS idx_user_content_activity_user_last_seen
    ON public.user_content_activity (user_id, last_seen_at);
