# Career Beacon: AI-Powered Micro-Learning & Mentorship Marketplace

> **Student:** Gitonga Macklee Nderitu (168000)  
> **Degree:** Bachelor of Science in Informatics and Computer Science (ICS 4B)  
> **Course:** ICS Project II - Capstone Project  
> **Supervisor:** Dr. Tiberias Tabulu - School of Computing & Engineering Sciences, Strathmore University  
> **Live Production Client:** [https://careerbeacon.netlify.app](https://careerbeacon.netlify.app)  
> **API Backend Target:** Render / Fly.io Containerised FastAPI Service  

---

## 1. Project Overview & Architecture

**Career Beacon** is a career-learning and mentorship platform with separate learner, mentor, and administrator workflows. Learners select a career, assess their skills, and receive a career-aware learning feed and a daily three-lesson focus sprint. The system tracks lesson and quiz activity, updates skill progress, and connects learners to mentors. Administrators review career proposals, verify mentors, and handle reported content.

```
┌────────────────────────────────────────────────────────────────────────┐
│                  REACT CLIENT (Vite single-page app)                   │
│ Learner dashboard/feed • Mentor workspace • Admin command center       │
│ Authentication • Career onboarding • Skill graph • Daily Focus Drop   │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ HTTPS REST + Supabase Auth SDK
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION (Python)                       │
│ Career/skill onboarding • Recommendation and quiz services             │
│ Daily Focus Drop • Mentorship • Administration and moderation          │
│ FastEmbed semantic retrieval • External source adapters • AI services  │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ Supabase client / authenticated requests
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  SUPABASE AUTH + POSTGRESQL / pgvector                 │
│ Profiles • Careers and skills • Micro-content • Mentor records         │
│ Quiz/activity data • Career and content vector search                  │
└────────────────────────────────────────────────────────────────────────┘
```

The recommendation engine combines semantic retrieval with career-skill priorities, proficiency gaps, prerequisite relationships, lesson difficulty, calibrated source authority weights, and learner activity. The primary learning flow delivers a high-impact Daily Focus Drop of three curated lessons targeting the learner's highest skill deficit, accompanied by an optional one-shot re-roll, daily streak tracking, in-app concept overviews, and interactive 5-question checkpoints. Completed lessons are archived into a searchable completed library.

---

## 2. Sprint Milestones Status

### Sprint I: Data Preparation & Environment Setup [COMPLETED]
- [x] **Configured Local Environment**: Python 3.12/3.11 virtual environment, Node.js v20+, Vite tooling.
- [x] **Clean Repository Structure**: Decoupled `frontend/`, `backend/`, and `management/` documentation.
- [x] **Git Version Control**: Strict commit history, credentials protected via `.env` and `.gitignore`.
- [x] **Data & Database Preparation**: Supabase PostgreSQL initialized with `pgvector` extension and 384-dimension vector embeddings.
- [x] **Repeatable Automation**: Database sync script (`sync_embeddings.py`) and reproducible migration pipelines.
- [x] **Chapter 4 Documentation**: Formal System Analysis and Design documentation aligned with actual implementation.

### Sprint II: Core Functionality, Integration & Initial Testing [COMPLETED]
- [x] **Core Workflow**: Free-text career search $\rightarrow$ semantic vector matching $\rightarrow$ AI dynamic fallback $\rightarrow$ baseline proficiency sliders $\rightarrow$ skill graph persistence $\rightarrow$ learner dashboard.
- [x] **System Integration**: React Frontend + FastAPI AI Engine + Supabase PostgreSQL (`pgvector`) + FastEmbed ONNX + Groq/Gemini LLM.
- [x] **Initial Testing & Failure Handling**: Test matrix covering valid inputs, non-standard career strings, transient API timeouts (exponential backoff), and semantic score gating.
- [x] **AI/ML Baseline Evaluation**: Audited vector embedding space (384 dimensions), semantic similarity threshold calibration ($0.85$), and latency benchmarks.
- [x] **AI-Assisted Workflow Audit**: Audited and defended critical design decisions (FastEmbed ONNX replacing heavy PyTorch `sentence-transformers` to avoid 512MB RAM OOMs, deferred database writes to prevent DB pollution).
- [x] **Chapter 5 Documentation**: Implementation, integration decisions, testing records, and evaluation metrics documented.

---

## 3. Directory Layout

```
career-mentor/
├── backend/
│   ├── app/
│   │   ├── core/           # Runtime settings and Supabase client
│   │   ├── middleware/     # JWT authentication and request checks
│   │   ├── routers/        # Onboarding, recommendations, mentor, admin, diagnostics
│   │   ├── services/       # Retrieval, content, learning history, daily drop, mentorship
│   │   ├── workers/        # Background/operational worker modules
│   │   └── main.py         # FastAPI entry point, middleware, and router registration
│   ├── scripts/            # Content ingestion, sync, audit, and maintenance tools
│   ├── tests/              # Backend unit, integration, security, and workflow tests
│   └── requirements.txt
├── frontend/
│   ├── public/             # PWA manifest, service worker, and app icons
│   ├── src/
│   │   ├── components/     # Shared controls, notifications, and status UI
│   │   ├── context/        # Shared client state
│   │   ├── lib/            # Supabase and backend API clients
│   │   ├── pages/          # Learner, mentor, admin, and recommendation views
│   │   ├── App.jsx         # Authentication and role-based view selection
│   │   └── index.css       # Design system and responsive styles
│   └── package.json
├── management/
│   ├── CHAPTER_4_SYSTEM_ANALYSIS_AND_DESIGN.md
│   ├── CHAPTER_5_SYSTEM_IMPLEMENTATION_AND_TESTING.md
│   ├── CHAPTER_5_SECTION_5_4.md
│   ├── ADMIN_GOVERNANCE_AND_LIFECYCLE_SPEC.md
│   ├── VECTOR_ARCHITECTURE_SPEC.md
│   ├── database queries/   # Schema snapshots and migrations
│   └── diagrams/           # Architecture and workflow diagrams
├── netlify.toml            # Frontend deployment configuration
└── render.yaml             # Backend deployment configuration
```

---

## 4. Setup and Run Instructions

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- Active Supabase project with `vector` extension enabled

### Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate       # On Windows PowerShell
# source .venv/bin/activate    # On macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (.env)
# Create backend/.env with:
# SUPABASE_URL=https://<your-project>.supabase.co
# SUPABASE_SERVICE_KEY=<your-service-role-key>
# GROQ_API_KEY=<your-groq-key>
# GEMINI_API_KEY=<your-gemini-key>
# YOUTUBE_API_KEY=<optional-youtube-data-api-key>
# ENVIRONMENT=development

# 5. Run vector sync (first-time setup)
python scripts/sync_embeddings.py

# 6. Start API server
uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

### Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment (.env)
# Create frontend/.env with:
# VITE_SUPABASE_URL=https://<your-project>.supabase.co
# VITE_SUPABASE_ANON_KEY=<your-anon-key>
# VITE_API_URL=http://localhost:8000

# 4. Start Vite dev server
npm run dev
```
Client will be live at: `http://localhost:5173`

---

## 5. Core API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service health & metadata |
| `GET` | `/health` | Uptime healthcheck ping |
| `POST` | `/api/onboarding/career-search` | Search for a career and return matched or generated career/skill data |
| `GET` | `/api/onboarding/career/{career_id}` | Retrieve career and associated skill details |
| `POST` | `/api/onboarding/save-skills` | Save the learner's selected career and skill baselines |
| `GET` | `/api/onboarding/status/{user_id}` | Read onboarding completion and learner skill state |
| `POST` | `/api/onboarding/reset` | Reset learner onboarding state |
| `GET` | `/api/recommendations/{user_id}` | Career-aware paginated feed; accepts `limit`, `offset`, and repeated `exclude_ids`; includes completed-library data |
| `GET` | `/api/recommendations/daily-drop/current` | Get or create today's Daily Focus Drop and streak state |
| `POST` | `/api/recommendations/daily-drop/reroll` | Use the once-per-day same-focus-skill shuffle when available |
| `POST` | `/api/recommendations/submit-quiz` | Evaluate a lesson quiz and record learning progress |
| `POST` | `/api/recommendations/activity/open` | Record a lesson open |
| `POST` | `/api/recommendations/activity/complete` | Record a lesson completion |
| `POST` | `/api/recommendations/feedback` | Record feedback and route relevant reports for moderation |
| `/api/mentor/*` | Various | Mentor onboarding, matching, connections, messaging, community Q&A, and session scheduling |
| `/api/admin/*` | Various | Administration metrics, career review, mentor verification, and moderation actions |
| `/api/test/*` | Various | Embedding, AI, and database diagnostics |

Protected `/api` routes validate Supabase JWTs. See the generated FastAPI documentation at `http://localhost:8000/docs` for request schemas and the complete route list.
