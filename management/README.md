# Project Management & Academic Thesis Artifacts

This directory contains research documentation, thesis draft chapters, system architecture specifications, and archived engineering scripts supporting **Career Beacon: AI-Powered Micro-Learning and Mentorship Marketplace**.

---

## Directory Layout

```
management/
├── CHAPTER_4_SYSTEM_ANALYSIS_AND_DESIGN.md        # Chapter 4 thesis draft (Methodology & Design)
├── CHAPTER_5_SYSTEM_IMPLEMENTATION_AND_TESTING.md # Chapter 5 thesis draft (Implementation & Validation)
├── CHAPTER_5_SECTION_5_4.md                       # Supplementary Chapter 5 implementation notes
├── CHAPTER_5_SECTIONS_5_5_AND_5_6.md              # Supplementary testing and evaluation draft
├── ADMIN_GOVERNANCE_AND_LIFECYCLE_SPEC.md         # Occupational governance & review lifecycle specification
├── VECTOR_ARCHITECTURE_SPEC.md                    # Dual-vector semantic embedding specification
├── onboarding_architecture_reimagined.md          # Architectural decisions on learner/mentor onboarding
├── goal.txt                                       # Technical specifications & project concept note
├── task.txt                                       # Interval roadmap linked to approved research objectives
├── MackleeNderituGitonga_168000_Dr.Tiberias.Tabulu (3).pdf # Approved proposal submission
├── README.md                                      # This reference guide
│
├── database queries/                              # Supabase PostgreSQL schema snapshots and migrations
│
├── diagrams/                                      # Interactive system architecture diagrams
│   ├── erd_clean.html                             # Entity-Relationship diagram
│   ├── sequence.html                              # Authentication & recommendation sequence diagrams
│   ├── usecase_clean.html                         # System actor use-case model
│   └── wireframes.html                            # UI/UX wireframe specifications
│
├── Doc Refs/                                      # University academic guidelines & reference guides
│   ├── Macklee_Nderitu_Gitonga_168000 (6).pdf
│   ├── REFERENCE GUIDE - Elvis Makara 2025.pdf
│   └── Sweeney Mbuvi.pdf
│
├── onet_data/                                     # Cached O*NET 31.0 official CSV releases
│   ├── occupation_data.csv                        # 1,016 standardized occupational classifications
│   ├── essential_skills.csv                       # Foundational competencies
│   ├── knowledge.csv                              # Knowledge domain taxonomies
│   ├── abilities.csv                              # Cognitive and psychomotor abilities
│   └── work_activities.csv                        # Generalized work activities
│
├── data_pipeline/                                 # Career normalization preview and batch scripts
└── archive/                                       # Shelved historical development artifacts
```

---

## System documentation map

- `CHAPTER_4_SYSTEM_ANALYSIS_AND_DESIGN.md` describes requirements and design models.
- `CHAPTER_5_SYSTEM_IMPLEMENTATION_AND_TESTING.md` is the primary implementation chapter and should be treated as the current technical narrative.
- `ADMIN_GOVERNANCE_AND_LIFECYCLE_SPEC.md` and `VECTOR_ARCHITECTURE_SPEC.md` describe the governance and embedding designs.
- The standalone Chapter 5 section files are supplementary drafts; check the primary Chapter 5 file for the latest integrated implementation description.

The application currently includes learner onboarding and skill progression, a career-aware paged recommendation feed, the Daily Focus Drop and streak flow, a completed-lesson library, mentor discovery and session workflows, and an administrator command center for career review, mentor verification, and moderation. The API route families are registered in `backend/app/main.py`; live request schemas are available from FastAPI's `/docs` endpoint.

## Operational scripts

Operational and maintenance utilities are located in `backend/scripts/`. The main repeatable workflows include:
- `ingest_content.py` — imports and processes learning material.
- `sync_embeddings.py`, `backfill_career_embeddings.py`, and `backfill_dual_career_vectors.py` — synchronize career embeddings.
- `clean_and_normalize_career_skills.py` — normalize occupational skill mappings.

Other files in that directory are audit, inspection, seed, validation, or legacy support utilities; review their purpose before using them against a configured database.
