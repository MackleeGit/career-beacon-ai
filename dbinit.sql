-- dbinit.sql – Full schema and seed data for Career Mentor project

-- Enable pgvector extension (run once)
create extension if not exists vector;

-- -------------------------------------------------------------------
-- Core tables
-- -------------------------------------------------------------------
create table profiles (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    full_name text,
    avatar_url text,
    bio text,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table careers (
    id uuid primary key default gen_random_uuid(),
    title text not null unique,
    description text,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table skills (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    category text,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table career_skills (
    career_id uuid references careers(id) on delete cascade,
    skill_id uuid references skills(id) on delete cascade,
    rank int not null default 0,
    primary key (career_id, skill_id)
);

create table user_skills (
    user_id uuid references profiles(id) on delete cascade,
    skill_id uuid references skills(id) on delete cascade,
    proficiency int not null check (proficiency between 0 and 100),
    last_used timestamp with time zone,
    primary key (user_id, skill_id)
);

create table micro_content (
    id uuid primary key default gen_random_uuid(),
    career_id uuid references careers(id) on delete cascade,
    title text not null,
    summary text,
    content text,
    embedding vector(1536),
    source_url text,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table mentors (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid references profiles(id) on delete set null,
    bio text,
    expertise text,
    rating_avg numeric(3,2) default 0,
    rating_count int default 0,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table mentor_qa (
    id uuid primary key default gen_random_uuid(),
    mentor_id uuid references mentors(id) on delete cascade,
    question text not null,
    answer text not null,
    embedding vector(1536),
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

create table bookings (
    id uuid primary key default gen_random_uuid(),
    mentor_id uuid references mentors(id) on delete set null,
    user_id uuid references profiles(id) on delete cascade,
    start_time timestamp with time zone not null,
    end_time timestamp with time zone not null,
    status text not null check (status in ('pending','confirmed','cancelled','completed')),
    meeting_link text,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- -------------------------------------------------------------------
-- Seed reference data
-- -------------------------------------------------------------------
insert into careers (title, description) values
('Data Scientist', 'Work with data to extract insights and build models.'),
('Product Manager', 'Define product vision, prioritize features, and coordinate teams.'),
('Full-Stack Engineer', 'Build end-to-end web applications using modern stacks.');

insert into skills (name, category) values
('Python', 'Programming'),
('SQL', 'Data'),
('JavaScript', 'Programming'),
('User Research', 'Design');

-- Link starter skills to careers (example mapping)
-- Data Scientist: Python, SQL
insert into career_skills (career_id, skill_id, rank)
select c.id, s.id, 1 from careers c, skills s
where c.title = 'Data Scientist' and s.name in ('Python', 'SQL');

-- Product Manager: User Research, SQL
insert into career_skills (career_id, skill_id, rank)
select c.id, s.id, 1 from careers c, skills s
where c.title = 'Product Manager' and s.name in ('User Research', 'SQL');

-- Full-Stack Engineer: JavaScript, Python
insert into career_skills (career_id, skill_id, rank)
select c.id, s.id, 1 from careers c, skills s
where c.title = 'Full-Stack Engineer' and s.name in ('JavaScript', 'Python');

-- -------------------------------------------------------------------
-- Indexes (optional for performance)
-- -------------------------------------------------------------------
create index idx_profiles_email on profiles(email);
create index idx_careers_title on careers(title);
create index idx_skills_name on skills(name);
create index idx_micro_content_career_id on micro_content(career_id);
create index idx_micro_content_embedding on micro_content using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_mentor_qa_embedding on mentor_qa using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_bookings_user_id on bookings(user_id);
create index idx_bookings_mentor_id on bookings(mentor_id);

-- -------------------------------------------------------------------
-- End of dbinit.sql
-- -------------------------------------------------------------------
