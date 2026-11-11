# CHAPTER 4: SYSTEM ANALYSIS AND DESIGN

**Project Title:** Career Beacon: AI-Powered Micro-Learning and Mentorship Marketplace  
**Student:** Gitonga Macklee Nderitu (168000)  
**Supervisor:** Dr. Tiberias Tabulu  
**Department:** School of Computing and Engineering Sciences, Strathmore University  

---

## 4.1 Introduction
This chapter presents the comprehensive analysis and architectural design of **Career Beacon**, an AI-powered micro-learning recommendation and mentorship marketplace. In alignment with the approved project proposal and the development guidelines of Sprints I and II, this chapter formalises the system's operational requirements, structural models, data definitions, and dynamic behavioural sequences guiding the technical implementation.

---

## 4.2 Requirements Analysis

### 4.2.1 Functional Requirements (FR)
1. **FR1: User Authentication & Role Separation:** The system shall authenticate users using email and secure token-based sessions (Supabase Auth) with distinct role configurations (`student`, `mentor`, `admin`).
2. **FR2: Target Career Interrogation:** The system shall provide an intuitive free-text input interface allowing learners to specify their career ambitions in natural language.
3. **FR3: Semantic Vector Career Matching:** The backend shall transform user career inputs into 384-dimensional dense vectors using a pre-trained transformer model (`all-MiniLM-L6-v2`) and query the database using cosine distance. If similarity $\ge 0.85$, pre-seeded career taxonomy and associated skills are retrieved.
4. **FR4: Dynamic AI Taxonomy Fallback:** When no pre-seeded career satisfies the semantic threshold ($< 0.85$), the system shall route the request to a large language model to standardise the job title and dynamically synthesise 8 high-relevance technical skills.
5. **FR5: Self-Declared Skill Baseline Initialisation:** The interface shall allow the learner to declare their baseline proficiency across skills using calibrated tiers: Novice ($20\%$), Intermediate ($50\%$), and Advanced ($80\%$).
6. **FR6: Skill Graph Persistence:** The system shall atomically commit the selected career and proficiency data to relational tables (`profiles.target_career_id`, `user_skills`) only upon explicit confirmation by the learner.
7. **FR7: Real-Time Learner Dashboard:** The system shall render an adaptive visual dashboard displaying aggregate progress, skill status tiers (`Not Started`, `Learning`, `Mastered`), and individual proficiency progress bars.

### 4.2.2 Non-Functional Requirements (NFR)
1. **NFR1: Performance & Latency:** Semantic vector generation and database similarity retrieval shall execute in under $1.5$ seconds under standard network conditions.
2. **NFR2: High Availability & Resilience:** The AI engine shall provide multi-provider fallback (Groq primary, Google Gemini secondary) with exponential backoff on transient HTTP 429/503 errors to guarantee $99.5\%$ operational uptime.
3. **NFR3: Memory Efficiency:** Vector inference modules running on backend servers must operate within constrained memory boundaries ($< 512$ MB RAM) to support cost-effective cloud container deployments.
4. **NFR4: Security & Data Privacy:** API keys, database service credentials, and sensitive tokens must remain decoupled from client bundles, managed via environment variables and Row-Level Security (RLS) policies.

---

## 4.3 System Architecture

Career Beacon adopts a decoupled **Client-Server-BaaS (Backend-as-a-Service)** architectural pattern consisting of three primary tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION TIER (Frontend)                    │
│   • Technology: React.js (Vite), Vanilla Modular CSS                   │
│   • Responsibilities: Auth state machine, semantic search input,       │
│     proficiency slider controls, reactive dashboard visualisation      │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ RESTful HTTPS                   │ WebSocket (Realtime)
                   ▼                                 ▼
┌────────────────────────────────────┐ ┌─────────────────────────────────┐
│     APPLICATION TIER (AI Engine)   │ │      DATA TIER (BaaS & DB)      │
│ • Technology: Python FastAPI       │ │ • Technology: Supabase          │
│ • Embedding: FastEmbed ONNX        │ │   (PostgreSQL 15 + pgvector)    │
│   (all-MiniLM-L6-v2, 384-dim)      │ │ • Capabilities:                 │
│ • LLM: Groq (gpt-oss-120b) +       │ │   - HNSW Cosine Indexing (<=>)  │
│   Gemini (2.5-flash) Multi-fallback│ │   - Stored Procedure RPCs       │
│ • Middleware: Strict CORS, Pydantic│ │   - Row-Level Security (RLS)    │
└────────────────────────────────────┘ └─────────────────────────────────┘
```

1. **Presentation Tier:** A responsive Single Page Application (SPA) built with React and Vite, hosted on Netlify, ensuring fast load times and an app-level state machine handling session transitions seamlessly.
2. **Application Tier (AI Engine):** An asynchronous Python FastAPI service running in a lightweight container (Render/Fly.io), orchestrating dense vector generation and multi-provider generative fallback.
3. **Data Tier (Supabase / PostgreSQL):** A managed relational PostgreSQL engine equipped with `pgvector` and HNSW indexing for high-speed nearest-neighbor cosine similarity queries.

---

## 4.4 Conceptual Models and Diagrams

### 4.4.1 Use Case Model (Figure 4.3)
The system boundary encompasses interactions between three primary external actors: **Learner**, **Mentor**, and **System/AI Engine**.

```
                   Dual Semantic Recommendation Framework Boundary
                 ┌──────────────────────────────────────────────────┐
                 │  [UC1: Authenticate / Manage Account]            │
     Learner ───┼─►[UC2: Input Target Career & Search Pathway]    │
                 │         │                                        │
                 │         ▼ <<include>>                            │
                 │  [UC3: Execute Semantic Vector Search] ◄────────┼── AI Engine /
                 │         │                                        │   Supabase
                 │         ▼ <<extend>> (if similarity < 0.85)      │
                 │  [UC4: Synthesize Career & Skills Taxonomy] ────┼── LLM Service
                 │         │                                        │
                 │         ▼                                        │
                 │  [UC5: Declare Initial Skill Proficiency Tiers]  │
                 │  [UC6: View Personalized Skill Graph Dashboard]  │
                 │  [UC7: Complete Micro-Learning Quizzes]          │
                 │  [UC8: Match with Mentors & Book Sessions]       │
                 └──────────────────────────────────────────────────┘
```
*(Reference visual asset: `management/diagrams/usecase.html` — Figure 4.3)*

### 4.4.2 Database Schema & ERD (Figure 4.2)
The database structure combines normalized relational design with high-dimensional vector types:

- **`profiles`**: Stores user identity, roles, and current `target_career_id` (foreign key to `careers.id`).
- **`careers`**: Stores standardized career names, descriptions, and dense vector embeddings (`career_vector vector(384)`).
- **`skills`**: Catalog of normalized technical competency nodes.
- **`career_skills`**: Junction table establishing the mapping and curriculum order between careers and required skills.
- **`user_skills`**: Dynamic junction table recording each learner's proficiency score ($0-100\%$) and completion status.
- **`micro_content`**: Contains curated atomized resources, summary bullets, quizzes JSON, and 384-dimensional vector embeddings.
- **`mentors`**: Captures verified mentor bios, meeting links (Google Meet/Calendly), reputation ratings, and 384-dimensional mentor embeddings.
- **`mentor_qa`**: Public searchable repository of answered questions with semantic vector search support.
- **`bookings`**: Transactional table managing scheduled mentorship sessions.

*(Reference visual asset: `management/diagrams/schema.html` and `management/diagrams/erd.html` — Figure 4.2)*

### 4.4.3 System Sequence Model: Onboarding & Skill Graph (Figure 4.4)
The sequence diagram demonstrates data movement from user input through processing to database persistence:

```
Learner (React)            FastAPI AI Engine          Supabase (PostgreSQL)      LLM (Groq/Gemini)
      │                            │                           │                        │
      ├── 1. POST "Career Query" ─►│                           │                        │
      │                            ├── 2. Generate 384-dim vec │                        │
      │                            ├── 3. match_careers(vec) ─►│                        │
      │                            │◄─ 4. Similarity result ───┤                        │
      │                            │                           │                        │
      │                            │   [If similarity < 0.85 (AI Fallback)]:            │
      │                            ├── 5. POST prompt (normalize + 8 skills) ──────────►│
      │                            │◄─ 6. Valid JSON {title, skills} ───────────────────┤
      │                            │                           │                        │
      │◄─ 7. Return Career+Skills ─┤                           │                        │
      │                            │                           │                        │
      ├── 8. Adjust sliders &      │                           │                        │
      │      submit graph (Save) ─►│                           │                        │
      │                            ├── 9. Insert career, link skills, upsert user_skills│
      │                            │──────────────────────────►│                        │
      │                            │◄─ 10. Commit success ─────┤                        │
      │◄─ 11. Render Dashboard ───┤                           │                        │
```
*(Reference visual asset: `management/diagrams/sequence.html` — Figure 4.4)*

---

## 4.5 Design Changes & Adjustments from Proposal
In accordance with Agile development in Sprints I and II, the following architectural adjustments were made and approved:
1. **Model Dimension Standardization ($384$ vs $1536$):** The database vector columns and HNSW indexes were standardized to 384 dimensions to natively align with open-source sentence transformers (`all-MiniLM-L6-v2`), avoiding vendor lock-in to proprietary 1536-dimensional APIs.
2. **Inference Engine Optimization:** Migrated from PyTorch-dependent `sentence-transformers` to ONNX Runtime `FastEmbed`, reducing backend memory overhead by over $80\%$ and eliminating out-of-memory (OOM) failures on cloud instances.
3. **Deferred Persistence Pattern:** Career generation is maintained in an ephemeral pending state on the client until the user confirms their baseline proficiency sliders, preventing database clutter from abandoned queries.
