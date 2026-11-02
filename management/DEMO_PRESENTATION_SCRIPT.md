# Career Beacon: System Defense & Live Demonstration Runbook

## Executive Demonstration Overview

This document provides the turnkey, step-by-step presentation script for the final project defense of **Career Beacon: Semantic Micro-Learning & Mentorship Acceleration Platform**.

The demonstration proves the system's end-to-end functionality across its four core technical modules:
1. **Module 1: Diagnostic Onboarding & Taxonomic Calibration** (O*NET 855-career catalog, 23 BLS Major Group vector gating, interactive proficiency self-rubrics).
2. **Module 2: Dashboard Analytics & Adaptive Skill Graph** (Visual competency deficit scoring, priority ranking).
3. **Module 3: Daily Focus Drop Engine** (The Brilliant/Wordle 3-lesson micro-learning habit loop, 1-shot mulligan/re-roll, and real-time Just-In-Time dynamic curriculum generation).
4. **Module 4: Two-Stage Semantic Mentorship Ecosystem** (Cosine similarity matching, anti-desperation thresholding, 1-on-1 session booking with ICS calendar exports, direct messaging, and real-time notification alerts).

---

## 1. Demo Baseline Configuration

The platform is pre-configured with two persistent baseline accounts:

| Role | Name | Email | Password | Career / Specialization | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Learner** | Jordan Blake | `softdev.learner@demo.com` | `DemoPassword123!` | Software Developer | Pre-seeded with 5 enrolled skills, active 3-lesson daily drop ready for immediate review. |
| **Mentor** | Dr. Evelyn Harper | `ent.mentor@demo.com` | `DemoPassword123!` | ENT Surgeon (Otolaryngology) | Gold Verified Mentor, rating 5.0 (14 sessions), availability pre-configured on Mon/Wed/Fri. |

### Live Accounts Created Live During the Defense
* **Live Learner:** Maya Lin (`ent.learner@demo.com` / `DemoPassword123!`) — Targets ENT Surgeon. Demonstrates live onboarding, rubric calibration, and Just-In-Time daily drop generation.
* **Live Mentor:** Alex Vance (`softdev.mentor@demo.com` / `DemoPassword123!`) — Targets Software Development. Demonstrates mentor onboarding, availability setup, semantic ranking match to Jordan Blake, 1-on-1 booking, DM exchange, and notification bell alerts.

---

## 2. Recommended Screen & Environment Setup

* **Left Screen (or Left Half):** Browser open to `http://localhost:5173/login`.
* **Right Screen (or Right Half):** Terminal running FastAPI server (`powershell -Command "backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --port 8000 --reload"`) showing live structured request logs and vector embedding metrics.

---

## 3. Step-by-Step Live Demonstration Script

### Act 1: The Daily Focus Drop & Habit Loop (Jordan Blake, Existing Learner)
**Estimated Time:** 2 Minutes  
**Goal:** Prove sub-50ms high-throughput retrieval, curated daily drop structure, checkpoint quiz validation, and the 1-shot mulligan mechanic.

1. **Log In:**
   * Navigate to `http://localhost:5173/login`.
   * Enter email `softdev.learner@demo.com` and password `DemoPassword123!`. Click **Sign In**.
2. **Review Dashboard & Daily Drop:**
   * Point out the clean Daily Focus Drop banner at the top of the dashboard.
   * Note the focus skill: *"Computers and Electronics / Software Engineering"*.
   * Explain that exactly 3 bite-sized lessons are delivered every 24 hours to prevent cognitive overload.
   * Point out the source badges: authoritative documentation from **MDN Web Docs** and open academic textbooks.
3. **Inspect Lesson & Checkpoint Quiz:**
   * Click the first lesson card (*"Key values for keyboard events"*).
   * Highlight the structured layout:
     * Structured Instructional Mini-Lesson (150–220 words).
     * Applied Workplace Scenario for a Software Developer.
     * 3 Technical Takeaway Bullets.
     * Interactive 5-Question Knowledge Check.
   * Answer a quiz question; show instant visual feedback (green for correct, red explanation for incorrect).
4. **Demonstrate 1-Shot Mulligan (Re-Roll):**
   * Return to the Daily Drop view and point to the **Re-Roll Drop** button.
   * Click **Re-Roll Drop**.
   * Note that the drop instantly shuffles to the pre-warmed reserve lessons for the same skill deficit in 0ms without re-querying or invoking external APIs.
   * Point out that the Re-Roll button is now disabled (enforcing the strict 1-shot daily rule).
   * **Spoken Script:**
     > *"Rather than drowning students in endless course directories, Career Beacon adopts a Wordle-inspired daily drop model: three focused lessons per day targeting the learner's greatest skill deficit. If the learner wants alternative practice today, they receive a single 1-shot mulligan, swapping instantly to pre-loaded reserve material while maintaining strict occupational boundaries."*

---

### Act 2: Live Onboarding & Just-In-Time Curation (New ENT Learner)
**Estimated Time:** 3 Minutes  
**Goal:** Prove that when an unseeded learner enters a distinct discipline (e.g., Medicine / Surgery), the system dynamically determines domain compatibility and curates clinical literature without cross-discipline contamination.

1. **Sign Up New Learner:**
   * Log out of Jordan Blake's account.
   * Click **Create an Account**.
   * Enter Full Name: `Maya Lin`, Email: `ent.learner@demo.com`, Password: `DemoPassword123!`. Role: `Learner`. Click **Sign Up**.
2. **Career Selection & Skill Rubric Calibration:**
   * In the career search box, type `ENT Surgeon` or `Otolaryngologist`.
   * Select `ENT Surgeon`. Note how the system extracts the official O*NET competency hierarchy.
   * Advance to the diagnostic self-assessment step. Show the 5-point proficiency rubrics for surgical skills (*"Pediatric airway management"*, *"Endoscopic surgical procedures"*, *"Head and neck anatomy"*).
   * Rate initial proficiencies as beginner/intermediate (e.g., 20–30%). Click **Complete Calibration**.
3. **Observe Just-In-Time Live Curation:**
   * As Maya lands on the Dashboard, direct the panel's attention to the backend terminal.
   * Show that the system detects a novel learner with 0 pre-cached drops.
   * The terminal streams live:
     * `[content_service] Querying Europe PMC / Clinical Science repository for airway management...`
     * `[content_service] Enforcing closed healthcare domain gate (no MDN, no OWASP)...`
     * `[daily_drop_service] Synthesizing 3 calibrated medical lessons and 384-d vectors...`
   * Within seconds, Maya's dashboard populates with verified clinical surgical lessons (e.g., *Airway Decision-Making in Acute Epiglottitis*, *Endoscopic Anatomy*).
   * **Spoken Script:**
     > *"For existing learners, drops are pre-computed overnight. But when a brand-new professional enters an specialized field like Otolaryngology, our Just-In-Time pipeline triggers autonomously. Using our 23-group vector taxonomy, the system gates adapters to clinical repositories like Europe PMC and NCBI, rejecting incompatible sources like MDN or OWASP, and delivers calibrated surgical instruction on the fly."*

---

### Act 3: Live Mentor Onboarding & Semantic Profile Vectorization
**Estimated Time:** 2.5 Minutes  
**Goal:** Prove mentor profile indexing, symmetric embedding generation, and multi-day availability setup.

1. **Sign Up New Mentor:**
   * Log out of Maya Lin.
   * Click **Sign Up**.
   * Enter Full Name: `Alex Vance`, Email: `softdev.mentor@demo.com`, Password: `DemoPassword123!`. Role: `Mentor`. Click **Sign Up**.
2. **Complete Mentor Onboarding:**
   * Primary Domain: `Software Developer`.
   * Professional Headline: `Lead Full-Stack Engineer & Distributed Systems Architect`.
   * Bio: `Over 10 years architecting scalable web applications, microservices, and reactive frontends. Passionate about mentoring junior and mid-level software engineers.`
   * Weekly Commitment: `5 hours/week` | Max Mentees: `6`.
   * Available Days: Select `Tuesday`, `Thursday`, `Saturday`. Preferred Window: `Evening`.
   * Expertise Tags: Add `System Architecture`, `Software Engineering`, `Web Applications`, `Database Design`.
   * Click **Save & Vectorize Profile**.
   * Direct attention to the terminal:
     * `[mentorship_service] Vectorized Alex Vance profile using all-MiniLM-L6-v2 in 14ms.`
     * `[mentorship_service] Persisted mentor into ecosystem store with 18 available 45-min slots.`
   * **Spoken Script:**
     > *"Mentor onboarding does not simply dump text into a table. The system generates a high-dimensional vector capturing the mentor's occupational domain, bio, and technical expertise tags. It computes recurring 45-minute booking slots across the mentor's designated weekly schedule while enforcing strict capacity limits."*

---

### Act 4: Semantic Matching, 1-on-1 Booking, Messaging & Notifications
**Estimated Time:** 3.5 Minutes  
**Goal:** Prove the Two-Stage Anti-Desperation Matcher, conflict-free booking, Jitsi video generation, RFC 5545 ICS calendar export, Direct Messaging, and real-time Notification Bell alerts.

1. **Log In as Jordan Blake (Software Dev Learner):**
   * Log in to `softdev.learner@demo.com` / `DemoPassword123!`.
   * Click **Mentorship** in the top navigation.
2. **Observe Two-Stage Semantic Mentor Recommendations:**
   * Highlight the top recommended mentor: **Alex Vance**!
   * Point out the high match score (e.g., 88–94%), matched skills tags (`System Architecture`, `Software Engineering`), and availability badge (`Evening Slots · Tue, Thu, Sat`).
   * Contrast with Dr. Evelyn Harper: note that Dr. Harper (ENT Surgeon) is filtered out or ranked at the bottom by the Anti-Desperation gate because her cosine similarity score is well below the relevance threshold for a software developer.
   * **Spoken Script:**
     > *"Our Two-Stage Matcher computes cosine similarity between the learner's skill gap vector and candidate mentor vectors. Notice that Alex Vance—registered just moments ago—immediately ranks at the top with full skill overlap, while medical mentors like Dr. Harper are filtered out by our anti-desperation threshold."*
3. **Request Connection & Direct Messaging (DM):**
   * Click **Connect** on Alex Vance's card.
   * Click **Send Message** to open the Direct Messaging drawer.
   * Jordan types: *"Hi Alex! I reviewed the daily drop on distributed caching. Can we discuss Redis cache invalidation strategies?"* Click **Send**.
4. **Book a 1-on-1 Mentorship Session:**
   * In the Mentorship view, click **Book 1:1 Session** on Alex Vance's card.
   * Select an available slot from the calendar (e.g., Tuesday 6:00 PM - 6:45 PM).
   * Topic: `Distributed Caching & Redis Invalidation Patterns`.
   * Focus Skill: `System Architecture`.
   * Click **Confirm Booking**.
   * Point out the instant booking confirmation, unique Jitsi video meeting room URL, and the **Add to Calendar (.ics)** button.
   * Click **Add to Calendar (.ics)**: show that a standard RFC 5545 calendar file downloads with built-in 24-hour and 15-minute alarm reminders.
5. **Inspect Notification Bell (Learner Side):**
   * Look at the **Notification Bell** in the top navigation bar.
   * An unread badge indicates active notifications.
   * Click the bell: show the upcoming session reminder with direct **Join Video Call** link and the connection status alert.
6. **Log In as Alex Vance (Mentor Side) to Close the Loop:**
   * Switch to incognito window (or log out and log in as `softdev.mentor@demo.com`).
   * Navigate to `/mentor-dashboard`.
   * Point out the Notification Bell: Alex has notifications for:
     * *New Connection Request* from Jordan Blake.
     * *Upcoming 1-on-1 Session* on Distributed Caching.
   * Open the Roster/Messages tab: see Jordan's message and reply:
     * *"Hey Jordan! Absolutely. Let's cover cache-aside and write-through patterns during our call."*
   * Point out the **Join Video Call** button ready for the 1:1 session.
   * **Spoken Script:**
     > *"The mentorship module delivers a complete operational loop: verified semantic matching, clash-proof scheduling, automated video room provisioning, calendar file synchronization, and real-time notification alerts for both participants."*

---

### Act 5: Architectural Defense & Committee Q&A
**Estimated Time:** 2 Minutes  
**Goal:** Summarize the algorithmic rigor and academic contributions.

* **Key Points to Emphasize:**
  1. **Determinism vs Hallucination:** Taxonomy-backed O*NET 855-career ontology with BLS 23 Major Groups prevents hallucinations.
  2. **Pedagogical Purity:** Brilliant/Wordle micro-learning cadence (3 lessons/day) with 1-shot mulligan prevents cognitive fatigue.
  3. **Zero Token Waste:** Heavy pre-warming and database vector caching ensure sub-50ms retrieval under steady-state load.
  4. **Holistic Mentorship:** Anti-desperation semantic matching guarantees high-signal mentor discovery.

---

## 4. Resetting the Baseline for Future Demonstrations

To reset the database back to the pristine two-account state after a rehearsal or defense, run:
```bash
backend\.venv\Scripts\python.exe backend\scripts\prepare_demo_baseline.py
```
This automatically deletes `ent.learner@demo.com` and `softdev.mentor@demo.com` and confirms that `softdev.learner@demo.com` and `ent.mentor@demo.com` are clean and ready.
