# Career Beacon: AI-Powered Micro-Learning & Mentorship Marketplace

> **Student:** Gitonga Macklee Nderitu (168000)  
> **Degree:** Bachelor of Science in Informatics and Computer Science (ICS 4B)  
> **Course:** ICS Project II - Capstone Project  
> **Supervisor:** Dr. Tiberias Tabulu — School of Computing & Engineering Sciences, Strathmore University  
> **Live Production Client:** [https://careerbeacon.netlify.app](https://careerbeacon.netlify.app)  
> **Cloud API Target:** Render ASGI FastAPI Production Service (`render.yaml`)  

---

## 1. Project Overview & Architecture

**Career Beacon** is an AI-powered career enablement and mentorship platform designed to eliminate information overload and bridge the digital skills gap for emerging market learners. Rather than relying on generic course catalogs or ungrounded generative opinions, Career Beacon unifies four core academic subsystems and an administrative command center powered by dense vector retrieval, standardized labor market taxonomies, and human-in-the-loop validation.

```
┌────────────────────────────────────────────────────────────────────────┐
│               PRESENTATION TIER (React 19 + Vite 6 SPA)                │
│  Learner Dashboard • Daily Focus Drop • Quiz Modals • Mentor Portal    │
│  Mentor Pulse Feed • Community Q&A • Admin Governance Command Center   │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ HTTPS REST / WebSockets + Supabase Auth JWT
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│            APPLICATION & ORCHESTRATION TIER (FastAPI ASGI)             │
│  Role-Based JWT Middleware • CORS Whitelisting • Exception Interceptor │
│  FastEmbed (ONNX) Vector Inference • 7-Adapter Ingestion Pipeline      │
│  Two-Stage Hybrid Re-Ranker • Two-Stage Anti-Desperation Matcher       │
│  Multi-Provider LLM Fallback (Groq gpt-oss-120b → Gemini 2.5-flash)    │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ Asynchronous Supabase Client / Service Role
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│           DATA PERSISTENCE & VECTOR TIER (Supabase PostgreSQL 15)      │
│  Row-Level Security (RLS) • pgvector 384-dim HNSW Vector Indexes       │
│  O*NET 28.0 Taxonomy • Micro-Content Corpus • Ingestion Batch Ledger   │
│  Mentor Sessions & DMs • Learner Streaks • Assessment Attempts Table   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Functional Modules

### Module 1: Diagnostic Onboarding & Baseline Calibration
* **Semantic Career Search:** Translates free-text career queries into dense 384-dimensional embeddings via `all-MiniLM-L6-v2` (FastEmbed ONNX) and executes cosine distance retrieval against 855 canonical occupations from the U.S. Bureau of Labor Statistics O\*NET 28.0 catalog.
* **Dual-Threshold Decision Gate:** Automatically auto-enrolls queries clearing $\ge 0.85$ cosine similarity; displays a multi-card disambiguation grid for intermediate scores ($0.75 - 0.84$); and routes frontier/unindexed queries ($< 0.75$) to the multi-provider LLM fallback pipeline.
* **Behavioral Competency Rubric:** Calibrates baseline skill proficiencies across four discrete operational tiers: **Not Yet (0%)**, **Novice (20%)**, **Intermediate (50%)**, and **Advanced (80%)**, reserving 100% for quiz-verified mastery.

### Module 2: Learner Analytical Dashboard & Skill Graph
* **Career Readiness Meter:** Visualizes aggregate career preparedness as a weighted percentage based on target career competency pillars.
* **Competency Visualizer:** Breaks down active proficiencies across foundational, technical, and workplace categories.
* **Skill Deficit Prioritization:** Highlights critical skill gaps requiring immediate remediation and drives subsequent recommendations.

### Module 3: Daily Focus Drop Engine & Content Ingestion
* **High-Retention Daily Drop:** Delivers exactly three curated micro-lessons per 24 hours focused on the learner's single highest competency gap, accompanied by an active streak habit loop (`user_streaks`).
* **Controlled One-Shot Mulligan Re-Roll:** Allows learners to shuffle active cards once per day with reserve lessons targeting the same skill without external latency.
* **7 Pluggable Instructional Adapters:** Ingests authoritative learning materials from YouTube (transcripts/lectures), Structured Tutorials (GeeksforGeeks, Tutorialspoint, W3Schools), Open Textbooks (Wikibooks, Wikiversity), Clinical Science (NCBI StatPearls, Europe PMC), MDN Web Docs, OpenAlex academic literature, and Wikipedia (strict fallback).
* **3-Gate Ingestion Barrier:** Screens out personal blog fluff, enforces a $\ge 200$ character substance floor, and validates instructional vs. opinionated orientation via a dual-centroid semantic vector gate.
* **NLP Atomization & Dynamic 5-Question Quizzes:** Condenses source text into a 150–220 word concept overview, authentic workplace scenario, and 3 summary takeaways, paired with 5 applied MCQs evaluated server-side against a **60% passing threshold**.

### Module 4: Mentorship Marketplace & Collaboration Ecosystem
* **Two-Stage Anti-Desperation Matcher:** First applies a hard availability and mentee capacity filter (`active_mentees < max_mentees`). Then computes a hybrid composite score:
  $$\text{MatchScore} = 0.55 \cdot \text{CosineSim}(v_{\text{learner}}, v_{\text{mentor}}) + 0.30 \cdot \text{GapOverlapRatio} + 0.15 \cdot \text{DomainBonus}$$
  Enforces a strict $0.45$ anti-desperation threshold to block irrelevant pairings.
* **Conflict-Free Session Scheduling:** Dynamically generates 45-minute booking slots across a 14-day window, double-booking prevention locks, and automated dedicated Jitsi Meet video conferencing URLs (`mentor_sessions`).
* **RFC 5545 Standardized Calendar Sync:** Exports `.ics` calendar invitation files with dual `VALARM` notifications (24h and 15m lead times) alongside direct Google Calendar deep-links.
* **Mentor Pulse Feed:** Micro-publication stream (`/mentor/pulse`) for mentors to publish industry insights, architectural case studies, and career guidance.
* **Bidirectional Q&A Knowledge Base:** Contextual inquiry routing on repeated quiz difficulties (`/mentor/questions`), mentor answers, and community upvoting.
* **Post-Session Competency Endorsements:** Verified mentors issue formal skill endorsements, awarding a $+15\%$ proficiency boost to the learner's `user_skills` record.

### Module 5: Administrative Governance & Ingestion Ledger
* **Human-by-Exception Governance:** Automates ingestion and curriculum approval for verified sources while routing edge-cases and disputed skills to administrator review queues.
* **Git-Commit Style Ingestion Ledger:** Persists immutable batch records in `ingestion_batches` with a unique commit hash, adapter sources, lesson IDs, and quiz counts.
* **Atomic Batch Rollback:** Enables one-click purge of flawed or outdated third-party content batches without corrupting learner progression histories.
* **Soft Deprecation & Forward Aliasing:** Deprecates outdated competencies gracefully by mapping forward aliases (`successor_skill_id`), protecting learner skill graphs from cascading deletion.
* **Live System Health Telemetry:** Tracks real-time API latency, LLM failovers, database pool saturation, and ingestion filter pass rates.

---

## 3. Technology Stack

| Layer | Technology | Operational Justification |
|---|---|---|
| **Workstation OS** | Windows 11 Professional (64-Bit) | Host OS for local developer toolchain and virtual environments |
| **Backend Runtime** | Python 3.11.9 / 3.12 | Asynchronous ASGI runtime optimized for ML libraries and high-throughput I/O |
| **Web Framework** | FastAPI 0.115.8 + Uvicorn 0.34.0 | High-performance asynchronous REST API framework with native OpenAPI docs |
| **Frontend Framework** | React 19 + Vite 6 | Reactive Single Page Application (SPA) with Hot Module Replacement (HMR) |
| **Database & Vector Store**| Supabase Managed PostgreSQL 15 | Relational persistence, Row-Level Security (RLS), and `pgvector` HNSW indexes |
| **Neural Embeddings** | FastEmbed ONNX 0.2.7 (`all-MiniLM-L6-v2`)| 384-dimensional CPU vector inference (11.4 ms latency, 125 MB RAM overhead) |
| **LLM Inference** | Groq Cloud (`gpt-oss-120b`) & Gemini (`2.5-flash`)| Multi-provider fallback for edge-case taxonomy synthesis and quiz generation |
| **HTTP Client** | HTTPX 0.27.2 | Asynchronous HTTP requests executing external ingestion pipelines |
| **Video Conferencing** | Jitsi Meet API | Zero-install, encrypted peer-to-peer browser video rooms for mentorship |
| **Cloud Hosting** | Netlify (Client) & Render (Backend API) | Decoupled continuous deployment driven by GitHub repository triggers |

---

## 4. Directory Layout

```
career-mentor/
├── backend/
│   ├── app/
│   │   ├── core/           # Configuration, database client, and 7-field career definitions
│   │   ├── middleware/     # Supabase JWT authentication and RBAC checks
│   │   ├── models/         # Pydantic schemas and serialization models
│   │   ├── routers/        # API route controllers (onboarding, recs, mentor, admin, test)
│   │   ├── services/       # Core business logic:
│   │   │   ├── ai_service.py              # Multi-provider Groq & Gemini fallback engine
│   │   │   ├── content_service.py         # 7-adapter ingestion worker & quiz generator
│   │   │   ├── daily_drop_service.py      # 3-lesson daily drop, streak & re-roll service
│   │   │   ├── embedding_service.py       # FastEmbed ONNX 384-dim embedding generator
│   │   │   ├── ingestion_batch_service.py # Git-commit style batch ledger & rollback
│   │   │   ├── learning_history_service.py# Quiz grading, attempt logging & tracking
│   │   │   ├── mentorship_service.py      # 2-Stage Anti-Desperation mentor matching & calendar
│   │   │   └── recommendation_service.py  # Two-stage pedagogical re-ranking engine
│   │   ├── workers/        # Asynchronous background job processors
│   │   └── main.py         # FastAPI application entrypoint, CORS & keep-alive ping
│   ├── data/               # Seed data, JSON fixtures, and offline taxonomies
│   ├── migrations/         # Supabase PostgreSQL schema migrations and DDL scripts
│   ├── scripts/            # Database initialization, vector backfilling, and ingestion tools
│   ├── tests/              # Automated unit, integration, and security test suites
│   └── requirements.txt    # Pinned Python package dependencies
├── frontend/
│   ├── public/             # Static web assets, favicon, and brand icons
│   ├── src/
│   │   ├── components/     # UI components (Toast, Skeleton, NotificationBell, Icons)
│   │   ├── context/        # React Context providers for authentication and session state
│   │   ├── lib/            # Axios API client and Supabase client configuration
│   │   ├── pages/          # Application views:
│   │   │   ├── AdminPortal.jsx            # Administrative Command Center & audit ledger
│   │   │   ├── Dashboard.jsx              # Learner analytical skill graph & readiness meter
│   │   │   ├── Landing.jsx                # Public product landing page
│   │   │   ├── LearnerMentorship.jsx      # Mentorship marketplace, DMs, Pulse & Q&A
│   │   │   ├── LearnerOnboarding.jsx      # Semantic career search & baseline calibration
│   │   │   ├── Login.jsx                  # Supabase authentication & OAuth entrypoint
│   │   │   ├── MentorDashboard.jsx        # Mentor session manager, capacity & endorsements
│   │   │   ├── MentorOnboarding.jsx       # Mentor credential verification & availability setup
│   │   │   └── Recommendations.jsx        # Daily Focus Drop feed, quiz modal & library
│   │   ├── App.jsx         # Application routing and role-based view orchestration
│   │   └── index.css       # Design tokens, color system, and layout styling
│   └── package.json        # Frontend npm dependencies and build scripts
├── docs/                   # Quality assurance runbooks and manual testing guides
├── management/             # Capstone thesis documentation, schema snapshots, and diagrams
├── netlify.toml            # Netlify CDN deployment and SPA routing rules
└── render.yaml             # Render infrastructure-as-code web service specification
```

---

## 5. Core API Endpoints

### System Health & Public Routes
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service status, runtime metadata, and API version |
| `GET` | `/health` | Uptime health check ping (polled by Render keep-alive worker) |

### Learner Onboarding & Skill Graph (`/api/onboarding`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/onboarding/career-search` | Semantic career discovery matching query to O\*NET catalog or LLM fallback |
| `GET` | `/api/onboarding/career/{career_id}` | Retrieve canonical career details and required competency pillars |
| `POST` | `/api/onboarding/save-skills` | Persist learner-calibrated proficiencies (`user_skills`) and bind career |
| `GET` | `/api/onboarding/status/{user_id}` | Retrieve learner onboarding completion state and skill graph proficiencies |
| `POST` | `/api/onboarding/reset` | Reset learner onboarding state for profile recalibration |

### Recommendations & Daily Drop (`/api/recommendations`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/recommendations/{user_id}` | Paginated exploration feed with pedagogical re-ranking and exclusions |
| `GET` | `/api/recommendations/daily-drop/current` | Retrieve or generate today's 3-lesson Daily Focus Drop and streak status |
| `POST` | `/api/recommendations/daily-drop/reroll` | Execute one-shot daily mulligan shuffle with reserve same-deficit lessons |
| `POST` | `/api/recommendations/daily-drop/trigger-worker`| On-demand manual ingestion run for learner's active skill deficits |
| `POST` | `/api/recommendations/submit-quiz` | Grade 5-question checkpoint server-side and atomically increment proficiency |
| `GET` | `/api/recommendations/library/completed` | Retrieve chronological archive of successfully passed micro-learning lessons |
| `POST` | `/api/recommendations/activity/open` | Record lesson open timestamp and update recommendation frequencies |
| `POST` | `/api/recommendations/feedback` | Ingest user pedagogical ratings and route flagged content for review |

### Mentorship Marketplace & Collaboration (`/api/mentor`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/mentor/onboarding` | Register mentor profile, domain expertise, LinkedIn verification, and weekly slots |
| `GET` | `/api/mentor/profile/me` | Fetch active mentor profile, capacity, and current availability settings |
| `PATCH`| `/api/mentor/profile/me` | Update mentor professional bio, hourly quotas, or availability windows |
| `GET` | `/api/mentor/matches` | Execute Two-Stage Anti-Desperation matchmaking against learner skill gaps |
| `GET` | `/api/mentor/connections` | List active, pending, or archived learner-mentor connections |
| `POST` | `/api/mentor/connections/request` | Initiate connection handshake with initial message and skill gap snapshot |
| `POST` | `/api/mentor/connections/{id}/respond` | Accept or decline incoming mentorship connection request |
| `GET` | `/api/mentor/messages/{connection_id}` | Fetch direct messaging chat history for an authenticated connection |
| `POST` | `/api/mentor/messages` | Dispatch new direct chat message and trigger unread notification badges |
| `GET` | `/api/mentor/pulse` | Retrieve public mentor pulse stream filtered by career domain |
| `POST` | `/api/mentor/pulse` | Publish new industry update, case study, or micro-article |
| `POST` | `/api/mentor/pulse/{id}/like` | Upvote a mentor pulse publication |
| `GET` | `/api/mentor/questions` | Browse community Q&A knowledge base with topic and status filters |
| `POST` | `/api/mentor/questions` | Post learner question triggered from quiz difficulty or manual inquiry |
| `POST` | `/api/mentor/questions/{id}/answer` | Submit mentor response to an open technical question |
| `GET` | `/api/mentor/{mentor_id}/slots` | Generate conflict-free 45-minute bookable slots across the next 14 days |
| `POST` | `/api/mentor/sessions/book` | Confirm 1-on-1 session, lock schedule, and generate Jitsi Meet video room |
| `GET` | `/api/mentor/sessions` | List upcoming, completed, and canceled mentorship sessions |
| `GET` | `/api/mentor/sessions/{id}/calendar.ics` | Download RFC 5545 `.ics` calendar invitation file with dual `VALARM` triggers |
| `POST` | `/api/mentor/sessions/{id}/complete` | Mark session completed and issue $+15\%$ mentor-verified skill endorsement |

### Administrative Governance & Telemetry (`/api/admin`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/metrics` | Retrieve live system health, API provider latency, and database pool metrics |
| `GET` | `/api/admin/ingestion-batches` | List all historical content ingestion batches with Git-commit style hashes |
| `POST` | `/api/admin/ingestion-batches/{hash}/rollback`| Purge all lessons, embeddings, and quizzes tied to a specific commit batch |
| `GET` | `/api/admin/careers/pending` | Fetch AI-synthesized frontier occupations awaiting administrative review |
| `POST` | `/api/admin/careers/{id}/review` | Formally approve, modify, or reject synthesized career taxonomies |
| `GET` | `/api/admin/mentors/pending` | Retrieve unverified mentor profiles awaiting credential review |
| `POST` | `/api/admin/mentors/{id}/verify` | Verify mentor credentials, grant verified badge, and activate matching |

---

## 6. Setup and Installation

### Prerequisites
* Python 3.11.9 or 3.12+
* Node.js v20.18.0+ and npm v10.8.2+
* Provisioned Supabase project with `pgvector` enabled

### Backend Installation
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate       # On Windows PowerShell
# source .venv/bin/activate    # On macOS/Linux

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Configure environment (.env)
# Create backend/.env:
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
GROQ_API_KEY=<your-groq-api-key>
GEMINI_API_KEY=<your-gemini-api-key>
ENVIRONMENT=development

# 5. Start development ASGI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive Swagger API documentation will be accessible at `http://127.0.0.1:8000/docs`.

### Frontend Installation
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install npm dependencies
npm install

# 3. Configure environment (.env)
# Create frontend/.env:
VITE_SUPABASE_URL=https://<your-project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-key>
VITE_API_URL=http://localhost:8000

# 4. Start Vite development server
npm run dev
```
The application will launch at `http://localhost:5173`.

---

## 7. Quality Assurance & Verification

The system includes automated verification scripts and runbooks to validate all four modules under simulated and live production workloads:
* `docs/MANUEL_NEUER_TEST_SUITE.md`: End-to-end sweeper-keeper verification runbook covering career classification, the 3-gate filter, and quiz grading.
* `docs/USER_MANUAL_TEST_GUIDE.md`: Step-by-step validation guide for all user roles (Learner, Mentor, Admin).
* `backend/tests/`: Pytest suite verifying JWT authentication middleware, recommendation ranking logic, and database vector similarity queries.
