# Career Beacon: In-App User Interactive Manual Test Suite
A Click-by-Click Browser Runbook for Local QA (No Python Scripts Required)

This runbook is designed for you as a human tester sitting at your browser with the frontend running at `http://localhost:5173` and the backend at `http://127.0.0.1:8000`.

---

## Pre-Flight Check

Make sure both services are running in your terminal:
- **Frontend URL:** [http://localhost:5173](http://localhost:5173)
- **Backend API:** [http://127.0.0.1:8000](http://127.0.0.1:8000)

Open Chrome, Firefox, or Edge to `http://localhost:5173`.

---

## Scenario 1: New Learner Registration and Identity Calibration

### Step 1.1: Register a New Test Learner
1. In the browser, navigate to: `http://localhost:5173/register` (or click **Get Started** from the landing page).
2. Enter the following test credentials:
   - **First Name:** `Jordan`
   - **Last Name:** `Taylor`
   - **Username:** `jordan_t` (Notice the instant availability check turns green: *"Username available"*).
   - **Email:** `jordan.test@example.com`
   - **Password:** `Password123!`
3. Click the eye icon next to the password input to verify show/hide functionality.
4. Click **Create Account**.

**Expected Result:**
- Account is created.
- The browser automatically navigates to `http://localhost:5173/onboarding`.

---

## Scenario 2: The Kinesthetic Interception Guardrail

### Step 2.1: Test Intercepted Motor Occupations
1. In the target career search box, type: `Bus Driver`.
2. Click **Find Career Pathway** (or press Enter).

**Expected Result:**
- The system intercepts the search because vehicle driving requires hands-on motor/behind-the-wheel instruction.
- A matte editorial callout banner appears:
  - *Title:* Physical / Kinesthetic Occupation Detected.
  - *Explanation:* Explains that commercial vehicle operation relies on in-person kinesthetic licensing.
  - *Alternative Cards:* Displays analytical/supervisory pathways:
    - *Transportation, Storage, and Distribution Manager*
    - *Logistics Coordinator*
    - *Supply Chain Operations Manager*
- Try another one: search `Bricklayer` or `Professional Footballer` -> verify they are similarly intercepted and offered supervisory/clinical alternatives (*Construction Manager*, *Athletic Trainer*).

### Step 2.2: Select an Eligible Career Track
1. Clear the search and type: `Backend Developer`.
2. Click **Find Career Pathway**.
3. Select the canonical card **Backend Developer** (`tech` field).
4. Click **Continue to Skill Calibration**.

---

## Scenario 3: Behavioral Skill Calibration

### Step 3.1: Calibrate Skill Baselines
You are presented with the vocational competency matrix for Backend Developer.
1. Calibrate skills across the anchor scale:
   - Set **REST API Architecture** to `Not Yet (0%)` (Foundational priority).
   - Set **SQL & Database Indexing** to `Novice (20%)` (Understand basics; require guidance).
   - Set **Data Structures & Algorithms** to `Novice (20%)`.
   - Set **Docker & Container Tooling** to `Intermediate (50%)` (Apply independently).
   - Set **System Architecture & Microservices** to `Not Yet (0%)`.
2. Click **Save Profile & Launch Dashboard**.

**Expected Result:**
- Profile is saved to Supabase with your target career and calibrated skill deficits.
- You land on the Learner Dashboard (`http://localhost:5173/dashboard`).
- Your Readiness Score displays around `15% - 25%` based on your calibrated ratings.

---

## Scenario 4: The 5-Lesson Daily Drop and Format Diversity

### Step 4.1: Inspect Today's Curated Daily Drop
1. In the top navigation bar, click **Recommendations** (or click the **Daily Drop** banner on your Dashboard).
2. Inspect the **Daily Drop** view:
   - **Header:** Displays *"Daily Drop"* and *"5 Curated Lessons for Jordan Taylor (Backend Developer)"*.
   - **Countdown Timer:** Displays *"Next drop in [HH:MM:SS]"* counting down to midnight UTC.
   - **Streak Indicator:** Displays *"Streak: 0 Days"* and a progress counter: *"0 / 5 Completed"*.
   - **Lesson Count:** Exactly 5 primary lesson cards appear in the list.

### Step 4.2: Verify Media Diversity (Video vs. Written)
Examine the 5 lesson cards:
1. Confirm that lessons alternate between:
   - **Video Lectures:** YouTube lecture card with duration badge, channel attribution, and playable video player/modal.
   - **Technical Documentation & Textbooks:** Badges from verified pedagogical sources (`MDN`, `OWASP`, `Wikibooks`, `arXiv`, etc.).
2. Confirm that lessons target your lowest calibrated skills (`REST API Architecture`, `SQL`, `Data Structures`).

---

## Scenario 5: The 1-Shot Free Mulligan Reroll

### Step 5.1: Execute the Daily Reroll
1. Notice the button at the top-right of the drop header: **Reroll Drop (1 remaining today)**.
2. Take note of the titles of the current 5 primary lessons.
3. Click **Reroll Drop (1 remaining today)**.

**Expected Result:**
- The list refreshes instantly: 5 fresh reserve lessons take the place of the previous 5 lessons.
- The button updates to **Reroll Used (0 remaining today)** and becomes disabled.
- Attempting to click it again is prevented.

---

## Scenario 6: Taking 5-Question Checkpoint Quizzes and Skill Progression

### Step 6.1: Test Quiz Failure and Remedial Review (<60%)
1. On **Lesson 1**, click **Take 5-Q Checkpoint**.
2. A clean modal opens containing **exactly 5 multiple-choice questions**.
3. **Intentional Failure:** Deliberately select incorrect answers across the questions to score 1/5 or 2/5 (20% or 40%).
4. Click **Submit Checkpoint**.

**Expected Result:**
- A red alert banner appears: *"Score: 40% - Checkpoint Threshold is 60%"*.
- Each question reveals an explanation callout pointing out the correct concept.
- The modal provides an **Ask Mentor** button to request 1:1 guidance on the missed concept.
- Your skill proficiency on the Dashboard remains unchanged.

### Step 6.2: Test Quiz Pass (>=60%) and Skill Advancement
1. In the checkpoint modal, click **Retake Checkpoint**.
2. Answer at least 3 out of 5 questions correctly (e.g. 4/5 or 5/5).
3. Click **Submit Checkpoint**.

**Expected Result:**
- A green celebration banner appears: *"Checkpoint Passed! Score: 80%"*.
- The modal states: *"+10% proficiency advancement awarded"*.
- Close the modal.
- Notice the lesson card updates its state: displays a completed badge with your score.
- Notice the topbar sprint tracker increments: *"1 / 5 Completed"*.
- Navigate to your **Dashboard**: verify that your target skill proficiency increased from `0% -> 10%` (or `20% -> 30%`).

---

## Scenario 7: Sprint Completion and Streak Increment

### Step 7.1: Complete All 5 Lessons
1. Go through lessons 2, 3, 4, and 5 in today's drop.
2. Take and pass the 5-question checkpoint for each lesson (scoring >= 60%).

**Expected Result:**
- When the 5th lesson is passed, the sprint marks as complete.
- A completion banner appears: *"Today's Daily Drop Complete! You have mastered today's core sprint."*
- The streak indicator increments:
  - **Streak:** Updates from `0 Days` to `1 Day`.
  - **Status:** Marks *"Completed Today"*.
- Reload the page (`F5`) to confirm the completion state and streak persist.

---

## Scenario 8: "Ask Mentor" Deep Linking

### Step 8.1: Test Direct Mentor Escalation
1. On any lesson card in the Recommendations feed, look at the bottom card tray.
2. Click the **Ask Mentor** button.

**Expected Result:**
- Navigates directly to the **Find Mentors** tab.
- The search filter is pre-calibrated with the specific skill name of that lesson (e.g. *REST API Architecture*).
- Surfaced mentors have an alignment score specifically weighted toward that skill deficit.

---

## Scenario 9: Content Moderation & Irrelevance Reporting

### Step 9.1: Report an Irrelevant Lesson
1. On any lesson card, locate the action icons next to the Bookmark icon:
   - Thumbs Up (Helpful)
   - Thumbs Down (Unhelpful)
   - Flag icon (Report as Irrelevant)
2. Click the **Flag** icon.

**Expected Result:**
- A confirmation prompt appears: *"Report recommendation as irrelevant (flags for admin review)"*.
- Confirm the report.
- A confirmation toast appears: *"Report submitted. Lesson queued for administrative review."*
- Log in as `@admin` (`admin@careerbeacon.internal` / `AdminPassword123!`) and navigate to the Admin Command Center: verify the reported lesson is listed under content moderation.

