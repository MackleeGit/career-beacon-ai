# Career Beacon — Supervisor Defense & Presentation Master Guide

---

## 1. Executive Presentation Agenda & Stage Management (10–12 Minutes)

| Timeline | Presentation Phase | What You Show On Screen | Key Defense Message to Verbalize |
| :--- | :--- | :--- | :--- |
| **00:00 – 01:30** | **Problem & Architecture** | Slide / Landing Page | Traditional career counseling is fragmented; static job boards don't bridge skill deficits. Career Beacon is an autonomous, dual-plane cognitive mentorship engine with 4 integrated modules. |
| **01:30 – 04:00** | **Module 1: Onboarding Triad** | Fresh Account (`live.learner@presentation.com`) | Split-pane 7-branch catalog explorer with live per-keystroke filter across 857 O*NET careers + real-time AI Career Inducer for novel titles. 60-second baseline proficiency calibration. |
| **04:00 – 06:30** | **Modules 2 & 3: Daily Drop & Mastery** | Dashboard (`Recommendations.jsx`) | Stage 1 pgvector recall + Stage 2 RRF ranking. 3 daily focus cards with editorial skeleton loader. Interactive 5-question mastery checkpoint with server-side validation. 1-shot reshuffle with 0 duplicate lessons. |
| **06:30 – 08:30** | **Module 4: Mentorship Ecosystem** | Mentorship Tab (`LearnerMentorship.jsx`) | Gold-verified industry mentors, bidirectional discovery, real-time threaded direct messaging, and UTC-synchronized 1:1 session scheduling. |
| **08:30 – 10:30** | **Administration & Ingestion Worker** | Admin Portal (`/admin`) | Git-commit style Ingestion Ledger, audited source transparency, in-place curriculum editor, live ingestion probe, and career taxonomy governance. |
| **10:30 – 12:00** | **Supervisor Q&A & Technical Defense** | Architecture & Database Schema | Defense of vector embeddings, fail-closed quality gates, deduplication, and production deployment on Render and Netlify. |

---

## 2. Pre-Configured Live Demo Credentials

Use these verified accounts during the presentation. All accounts exist in Supabase Auth and database with active relationships:

| Role | Name & Title | Email | Password | Pre-Configured State |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | System Administrator | `admin@careerbeacon.internal` | `AdminPassword123!` | Full access to KPI Health, Taxonomy Governance, Ingestion Ledger, Mentor Verification, and Moderation. |
| **Fresh Presentation Learner** | Leo Sterling (New User) | `live.learner@presentation.com` | `Presentation2026!` | Clean slate. Use to demonstrate the live Onboarding experience from scratch. |
| **Fresh Presentation Mentor** | Sarah Jenkins (Staff Bioinformatician) | `live.mentor@presentation.com` | `Presentation2026!` | Fresh mentor profile ready to calibrate domains and verify credentials. |
| **Active Demo Learner 1** | Jordan Blake (Full-Stack Engineer) | `jordan.learner@demo.com` | `DemoPassword123!` | 5-day streak, 12 enrolled skills, active daily drop, 4 DMs with Alex Vance, scheduled session tomorrow at 14:00 UTC. |
| **Active Demo Learner 2** | Maya Lin (Internal Medicine Physician) | `maya.learner@demo.com` | `DemoPassword123!` | 3-day streak, healthcare curriculum, 9 clinical skills, passed checkpoint history. |
| **Active Demo Mentor 1** | Dr. Evelyn Harper (ENT Surgeon) | `evelyn.mentor@demo.com` | `DemoPassword123!` | Gold Verified badge, 5 active mentees, 4.9 rating, clinical advisory portfolio. |
| **Active Demo Mentor 2** | Alex Vance (Distributed Systems Architect) | `alex.mentor@demo.com` | `DemoPassword123!` | Gold Verified badge, 12 years experience, active chat with Jordan Blake. |

---

## 3. Master Test Cases & Defensive Scripts

### Test Case 1: Standard Onboarding via the 7-Branch Catalog
- **Goal**: Prove that 857 standardized O*NET careers are organized hierarchically and instantly searchable.
- **Action**:
  1. Log in as `live.learner@presentation.com` (or click "Get Started" from Landing).
  2. Click on the **Technology & Software** or **Health & Medicine** branch card.
  3. Type 2 characters (e.g. `da` or `nu`) in the live filter.
  4. Notice the instant split-pane preview on the right showing the full O*NET description and activation button.
  5. Click **"Select Career Pathway"**.
- **What to Say**:
  > *"Instead of an overwhelming flat dropdown or an ungrounded text prompt, Career Beacon organizes the complete Department of Labor O*NET 29.0 taxonomy into 7 cognitive fields. Selecting a career loads its standardized competencies into a lightweight 60-second baseline self-calibration."*

---

### Test Case 2: Novel / Niche Career Induction (The Lecturer's Trap)
- **Goal**: When the examiner says: *"What if I enter a job that does not exist in your database?"*
- **Action**:
  1. In the Career Search input, type a completely novel title: `Autonomous Drone Fleet Coordinator` or `Quantum Cryogenics Technician`.
  2. Press Enter or click Continue.
  3. Show the brief 2-second calibration pulse.
  4. Point out the resulting screen: The AI Career Inducer classified it into *Engineering & Mechanics*, synthesized 10 technical competencies, and assigned baseline proficiencies.
- **What to Say**:
  > *"Because real-world industry evolves faster than government taxonomies, our AI Career Inducer maps arbitrary titles into our 7-field cognitive ontology, induces essential competencies, and marks the career as `unreviewed` for administrator governance. It participates in vector search immediately without breaking."*

---

### Test Case 3: 5-Question Mastery Checkpoint & Anti-Farming Guard
- **Goal**: Show that learning is measurable and strictly grounded.
- **Action**:
  1. On the Recommendations page, click on any Daily Drop card to expand it (notice 150-word overview, practice scenario, and source citation).
  2. Click **"Take Quiz (5 questions)"**.
  3. Answer the 5 questions (score at least 3/5 to pass, or deliberately fail one to show feedback).
  4. Submit answers: Show the instant evaluation, explanation callouts, and the proficiency increase banner (`+8%`).
  5. Try to retake the passed quiz: Show that repeated-pass score farming is strictly prevented (`proficiency remains at current level`).
- **What to Say**:
  > *"Our micro-learning is not passive reading. Every lesson is bound to a 5-question mastery checkpoint. Quizzes are validated server-side against stored answer keys. Passing with 60% or higher durably updates the learner's skill proficiency in Supabase."*

---

### Test Case 4: Daily Drop 1-Shot Reshuffle (Zero Duplicates)
- **Goal**: Prove that Daily Drops rotate dynamically and reshuffling provides completely distinct content.
- **Action**:
  1. Note the 3 titles currently displayed on the Daily Drop feed.
  2. Click **"Shuffle Sprint"** / **"Re-roll"**.
  3. Show that the feed instantly replaces all 3 cards with completely unique reserve lessons.
  4. Attempt to click shuffle a second time: Show the defensive guardrail toast: *"You have already used your daily shuffle. Complete today's drop to unlock tomorrow's sprint."*
- **What to Say**:
  > *"Our Daily Drop utilizes an active-reserve pool pattern. Reshuffling pulls from secondary deficit skills or compatible domain siblings while strictly excluding already served cards, guaranteeing zero duplicate fatigue within the same 24-hour cycle."*

---

### Test Case 5: The Ingestion Worker, Quality Gates & Git-Commit Ledger
- **Goal**: Prove the existence of an autonomous offline ingestion plane with full administrative oversight.
- **Action**:
  1. Log into `/admin` as `admin@careerbeacon.internal`.
  2. Click the **Content Ingestion & Reservoir** tab.
  3. Point out the **Ingestion Commit Ledger**: Monospace commit hashes (e.g. `#a91df42`), messages, target domains, and status badges.
  4. Click **"Inspect Sources"** on any commit: Show the exact audited URLs, adapter names (NCBI, MDN, OpenAlex, YouTube), and calibrated trust scores.
  5. Click **"Disapprove"** and then **"Approve"** on a batch to show instant status governance cascading to `micro_content`.
  6. Scroll down to the Reservoir Lessons table and click **"Edit"** on a lesson: Show the modal dialogue allowing an administrator to modify title, difficulty, summary, mini-lesson text, or questions.
  7. Optional live demo: In the Single-Skill Ingestion Probe, enter `Data Scientist` and `PyTorch Tensor Operations` and click **"Execute Live Ingestion Probe"** to watch the real-time telemetry stream poll adapters, validate Gate 1/2, synthesize MCQs, and commit `#commit-hash`.
- **What to Say**:
  > *"Content is not scraped during the learner's morning drop. Our offline Ingestion Worker operates autonomously like a Git repository: every ingestion sweep generates an auditable commit hash, verified source references, and quality metrics that administrators can inspect, approve, reject, or fine-tune."*

---

### Test Case 6: Mentorship Ecosystem (Module 4)
- **Goal**: Demonstrate verified human-in-the-loop mentorship.
- **Action**:
  1. In learner mode (`jordan.learner@demo.com`), navigate to the **Mentorship** tab.
  2. Show the mentor directory: Filters by Domain (*Tech*, *Healthcare*, *Business*) and Gold Verified badges.
  3. Open the active conversation with Alex Vance: Send a message (`"Looking forward to our architecture review tomorrow!"`) and show instant message delivery.
  4. Show the scheduled 1:1 session card with UTC countdown and "Join Session" readiness.
- **What to Say**:
  > *"When AI recommendations reach their limit, Module 4 connects learners to verified human experts. Mentors are credential-checked by administrators, and learners can engage in threaded discussions or schedule structured sessions."*

---

## 4. Tough Supervisor Questions & Bulletproof Answers

#### Q: "Why didn't you just call the OpenAI API directly from the frontend whenever a user clicks something?"
> **Answer**: *"Calling an LLM on every user click introduces 4 to 8 seconds of latency, produces ungrounded hallucinations, exposes API keys to client-side reverse-engineering, and incurs unpredictable API costs. Career Beacon decouples content ingestion from delivery: high-quality curriculum is ingested, vector-validated, and pre-seeded offline, allowing the learner interface to deliver personalized daily drops in under 50 milliseconds."*

#### Q: "How do you know the multiple-choice questions are correct and grounded?"
> **Answer**: *"We enforce a 3-gate fail-closed pipeline. Gate 1 requires at least 200 characters of substance and strips web boilerplate. Gate 2 calculates vector cosine similarity against the canonical skill centroid. Gate 3 feeds the validated source text into the prompt context as explicit ground truth, instructing the model to generate applied questions strictly answerable from that text, and verifies the response server-side before persisting."*

#### Q: "How does pgvector scale compared to standard relational queries?"
> **Answer**: *"In Career Beacon, we use a hybrid two-stage retrieval architecture: Stage 1 uses pgvector cosine similarity to recall the top candidate pool from high-dimensional embedding space, and Stage 2 applies Reciprocal Rank Fusion (RRF) with user proficiency deficit weighting and impression cooldown penalties. This combines the semantic flexibility of vectors with the deterministic speed of relational indexing."*

#### Q: "How does your system prevent cross-domain contamination?"
> **Answer**: *"Every career is classified into an authoritative Occupational Domain Standard (e.g. Healthcare SOC 29/31, Tech SOC 15, Engineering SOC 17). Sibling sharing is allowed only within matching domains. Even if a nursing student's search mentions a technical word, our domain barrier prevents engineering or tech lessons from ever appearing in their clinical feed."*
