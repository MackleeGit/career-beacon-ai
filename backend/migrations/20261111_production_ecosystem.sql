-- ============================================================================
-- Career Beacon: Production Ecosystem Migration
-- Moves dynamic transactional data from local JSON to native Supabase PostgreSQL
-- ============================================================================

-- 1. Mentorship Connections
CREATE TABLE IF NOT EXISTS public.mentor_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentor_id UUID NOT NULL REFERENCES public.mentors(id) ON DELETE CASCADE,
    learner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'accepted', -- 'pending', 'accepted', 'declined', 'archived'
    initial_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(mentor_id, learner_id)
);
CREATE INDEX IF NOT EXISTS idx_mentor_connections_learner ON public.mentor_connections(learner_id);
CREATE INDEX IF NOT EXISTS idx_mentor_connections_mentor ON public.mentor_connections(mentor_id);

-- 2. Direct Messages (Real-time Mentorship Chat)
CREATE TABLE IF NOT EXISTS public.mentor_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES public.mentor_connections(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL,
    recipient_id UUID NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mentor_messages_connection ON public.mentor_messages(connection_id, created_at);
CREATE INDEX IF NOT EXISTS idx_mentor_messages_unread ON public.mentor_messages(recipient_id, is_read);

-- 3. Mentorship 1-on-1 Scheduled Sessions
CREATE TABLE IF NOT EXISTS public.mentor_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES public.mentor_connections(id) ON DELETE SET NULL,
    mentor_id UUID NOT NULL REFERENCES public.mentors(id) ON DELETE CASCADE,
    learner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    slot_start_iso TIMESTAMPTZ NOT NULL,
    slot_end_iso TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed', -- 'confirmed', 'completed', 'cancelled'
    meet_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mentor_sessions_proximity ON public.mentor_sessions(slot_start_iso, status);
CREATE INDEX IF NOT EXISTS idx_mentor_sessions_mentor ON public.mentor_sessions(mentor_id, status);
CREATE INDEX IF NOT EXISTS idx_mentor_sessions_learner ON public.mentor_sessions(learner_id, status);

-- 4. Learner Activity Streaks
CREATE TABLE IF NOT EXISTS public.user_streaks (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    current_streak INT NOT NULL DEFAULT 0,
    longest_streak INT NOT NULL DEFAULT 0,
    last_activity_date DATE,
    freeze_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Daily Drop Bundles (3-Lesson Cognitive Microlearning)
CREATE TABLE IF NOT EXISTS public.daily_drops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    drop_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'completed'
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, drop_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_drops_user_date ON public.daily_drops(user_id, drop_date);

-- 6. Assessment Attempts (Diagnostic Quizzes)
CREATE TABLE IF NOT EXISTS public.assessment_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES public.skills(id) ON DELETE SET NULL,
    score INT NOT NULL,
    total INT NOT NULL DEFAULT 5,
    percentage NUMERIC(4,1) NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    answers JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user_skill ON public.assessment_attempts(user_id, skill_id);

-- 7. User Content Reading / Video Activity
CREATE TABLE IF NOT EXISTS public.user_content_activity (
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content_id TEXT NOT NULL,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    times_recommended INT NOT NULL DEFAULT 1,
    PRIMARY KEY(user_id, content_id)
);

