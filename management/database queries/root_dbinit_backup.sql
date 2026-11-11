-- -------------------------------------------------
-- 1️⃣ Enable pgvector extension (run once)
-- -------------------------------------------------
create extension if not exists vector;   -- enables the `vector` data type

-- -------------------------------------------------
-- 2️⃣ Core tables
-- -------------------------------------------------
create type user_role as enum ('learner','mentor','admin');
-- Users / Profiles
create table profiles (
    id            uuid primary key default gen_random_uuid(),
    email         text not null unique,
    full_name     text,
    avatar_url    text,
    bio           text,
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- Careers (e.g., "Data Scientist", "Product Manager")
create table careers (
    id            uuid primary key default gen_random_uuid(),
    title         text not null unique,
    description   text,
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- Skills (e.g., "Python", "SQL", "User Research")
create table skills (
    id            uuid primary key default gen_random_uuid(),
    name          text not null unique,
    category      text,                     -- optional grouping (e.g., "Programming", "Soft")
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- Many‑to‑many: which skills belong to which career
create table career_skills (
    career_id uuid references careers(id) on delete cascade,
    skill_id  uuid references skills(id)  on delete cascade,
    rank      int not null default 0,          -- optional ranking / importance
    primary key (career_id, skill_id)
);

-- User‑specific skill levels / proficiency
create table user_skills (
    user_id   uuid references profiles(id) on delete cascade,
    skill_id  uuid references skills(id)    on delete cascade,
    proficiency int not null check (proficiency between 0 and 100), -- 0‑100%
    last_used timestamp with time zone,
    primary key (user_id, skill_id)
);

-- -------------------------------------------------
-- 3️⃣ Micro‑learning content
-- -------------------------------------------------
create table micro_content (
    id            uuid primary key default gen_random_uuid(),
    career_id     uuid references careers(id) on delete cascade,
    title         text not null,
    summary       text,                         -- 3‑bullet summary (≤150 words)
    content       text,                         -- full article / transcript
    embedding     vector(1536),                 -- vector of the summary or content
    source_url    text,                         -- optional original source
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- -------------------------------------------------
-- 4️⃣ Mentorship entities
-- -------------------------------------------------
create table mentors (
    id            uuid primary key default gen_random_uuid(),
    profile_id    uuid references profiles(id) on delete set null,
    bio           text,
    expertise     text,                         -- free‑form description
    rating_avg    numeric(3,2) default 0,       -- optional aggregate rating
    rating_count  int default 0,
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- Q&A pairs linked to a mentor (knowledge base)
create table mentor_qa (
    id            uuid primary key default gen_random_uuid(),
    mentor_id     uuid references mentors(id) on delete cascade,
    question      text not null,
    answer        text not null,
    embedding     vector(1536),                 -- for semantic search
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- -------------------------------------------------
-- 5️⃣ Booking / Session table
-- -------------------------------------------------
create table bookings (
    id            uuid primary key default gen_random_uuid(),
    mentor_id     uuid references mentors(id) on delete set null,
    user_id       uuid references profiles(id) on delete cascade,
    start_time    timestamp with time zone not null,
    end_time      timestamp with time zone not null,
    status        text not null check (status in ('pending','confirmed','cancelled','completed')),
    meeting_link  text,                         -- e.g., Google Meet / Calendly URL
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

-- -------------------------------------------------
-- 6️⃣ Indexes for fast lookup (optional but recommended)
-- -------------------------------------------------
create index idx_profiles_email on profiles(email);
create index idx_careers_title on careers(title);
create index idx_skills_name on skills(name);
create index idx_micro_content_career_id on micro_content(career_id);
create index idx_micro_content_embedding on micro_content using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_mentor_qa_embedding on mentor_qa using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_bookings_user_id on bookings(user_id);
create index idx_bookings_mentor_id on bookings(mentor_id);

-- -------------------------------------------------
-- End of schema
-- -------------------------------------------------
