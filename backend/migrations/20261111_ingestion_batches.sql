-- ============================================================================
-- Migration: 20261111_ingestion_batches.sql
-- Ingestion Batches & Git-Commit Style Ledger Schema
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ingestion_batches (
    id TEXT PRIMARY KEY,
    commit_hash VARCHAR(16) NOT NULL UNIQUE,
    message TEXT NOT NULL,
    career_title TEXT,
    skill_name TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'approved',
    author TEXT DEFAULT 'Admin / Ingestion Worker',
    sources JSONB DEFAULT '[]'::jsonb,
    lesson_ids JSONB DEFAULT '[]'::jsonb,
    lesson_count INT DEFAULT 0,
    quiz_count INT DEFAULT 0,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_batches_hash ON public.ingestion_batches(commit_hash);
CREATE INDEX IF NOT EXISTS idx_ingestion_batches_status ON public.ingestion_batches(status);

