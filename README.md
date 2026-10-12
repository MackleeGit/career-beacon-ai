# Career Beacon: AI-Powered Micro-Learning & Mentorship Marketplace

> **Student:** Gitonga Macklee Nderitu (168000)  
> **Degree:** Bachelor of Science in Informatics and Computer Science (ICS 4B)  
> **Course:** ICS Project II - Capstone Project  
> **Supervisor:** Dr. Tiberias Tabulu - School of Computing & Engineering Sciences, Strathmore University  
> **Live Production Client:** [https://careerbeacon.netlify.app](https://careerbeacon.netlify.app)  
> **API Backend Target:** Render / Fly.io Containerised FastAPI Service  

---

## 1. Project Overview & Architecture

**Career Beacon** is an AI-driven career onboarding, micro-learning recommendation, and mentorship marketplace. It addresses information overload and skill misalignment in emerging markets by unifying a **Dual Semantic Recommendation Framework** driven by a shared learner skill profile.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        REACT.JS CLIENT (Vite SPA)                      │
│   • Semantic Career Search UI           • Proficiency Sliders (20/50/80) │
│   • Skill Graph Visualisation           • Auth & Session State Machine │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ HTTPS REST                      │ Supabase Realtime
                   ▼                                 ▼
┌────────────────────────────────────┐ ┌─────────────────────────────────┐
│     FASTAPI AI ENGINE (Python)     │ │   SUPABASE (PostgreSQL + pgvector)│
│ • FastEmbed (all-MiniLM-L6-v2)     │ │ • Relational Schema & Profiles  │
│   384-dimensional dense vectors    │ │ • pgvector Cosine Search (<=>)  │
│ • Multi-Provider LLM Fallback:     │ │ • HNSW Vector Indexes           │
│   1. Groq (gpt-oss-120b)           │ │ • Row-Level Security & Auth     │
│   2. Google Gemini (2.5-flash)     │ │ • match_careers() Stored Proc   │
│ • Exponential Backoff Retries      │ │                                 │
└────────────────────────────────────┘ └─────────────────────────────────┘
```

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
│   │   ├── core/           # Config & Supabase database client
│   │   ├── models/         # Pydantic request/response schemas
│   │   ├── routers/        # API route handlers (onboarding, test endpoints)
│   │   ├── services/       # FastEmbed EmbeddingService & Multi-provider AIService
│   │   └── main.py         # FastAPI application entrypoint & CORS setup
│   ├── scripts/
│   │   └── sync_embeddings.py # Repeatable DB vector synchronization script
│   ├── requirements.txt    # Frozen Python dependencies
│   └── .env.example        # Environment variable template
├── frontend/
│   ├── src/
│   │   ├── components/     # UI components (Toast, ErrorBoundary)
│   │   ├── lib/            # SupabaseClient and API client
│   │   ├── pages/          # Login, Onboarding, Dashboard views
│   │   ├── App.jsx         # Top-level auth state machine
│   │   └── index.css       # Design system tokens and styles
│   ├── package.json
│   └── vite.config.js
├── management/
│   ├── CHAPTER_4_SYSTEM_ANALYSIS_AND_DESIGN.md
│   ├── CHAPTER_5_IMPLEMENTATION_AND_TESTING.md
│   ├── SPRINT_I_AND_II_PRESENTATION_GUIDE.md
│   ├── diagrams/           # Use cases, ERD, sequence diagrams, wireframes
│   ├── goal.txt            # System technical specifications
│   └── task.txt            # Sprint task breakdown linked to thesis objectives
├── dbinit.sql              # Supabase initial schema DDL
├── patch_db.sql            # Vector(384) migration & match_careers RPC function
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
| `POST` | `/api/onboarding/career-search` | Semantic career match ($Cosine \ge 0.85$) or AI dynamic fallback |
| `POST` | `/api/onboarding/save-skills` | Persists user profile, career mapping, and skill graph weights |
| `GET` | `/api/onboarding/status/{user_id}` | Fetches user onboarding completion state and skill graph |
| `POST` | `/api/test/minilm-embedding` | Diagnostic test for FastEmbed 384-dimensional vector output |
| `POST` | `/api/test/ai-generate` | Diagnostic test for Groq/Gemini JSON generation |
| `GET` | `/api/test/supabase` | Diagnostic test for Supabase PostgreSQL connectivity |
