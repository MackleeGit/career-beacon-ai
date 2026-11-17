-- ============================================================================
-- Migration: 20261117_moderation_flags.sql
-- Persists Safety & Moderation Reports in Supabase PostgreSQL
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.flagged_items (
    id              TEXT PRIMARY KEY,
    item_type       TEXT NOT NULL,
    original_item_id TEXT,
    sender_name     TEXT,
    target_context  TEXT,
    content_snippet TEXT NOT NULL,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'pending_review',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flagged_items_status ON public.flagged_items(status, created_at DESC);
