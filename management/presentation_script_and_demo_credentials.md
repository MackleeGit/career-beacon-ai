# Career Beacon: Presentation Script & Demo Credentials Guide

## 1. Clean Verified Accounts (Supabase Auth & Database)

All legacy test accounts have been purged. The database is primed with exactly 4 active demo accounts and 2 fresh presentation accounts:

| Account Type | Role | Name | Email | Password | Pre-Configured State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Admin** | Administrator | System Administrator | `admin@careerbeacon.internal` | `AdminPassword123!` | Full Admin Portal access (`/admin`) |
| **Demo Mentor 1** | Mentor | Dr. Evelyn Harper | `evelyn.mentor@demo.com` | `DemoPassword123!` | Healthcare Lead, 5.0 rating, 14 sessions, slots set |
| **Demo Mentor 2** | Mentor | Alex Vance | `alex.mentor@demo.com` | `DemoPassword123!` | Backend Architect, 4.95 rating, 18 sessions, slots set |
| **Demo Learner 1** | Learner | Jordan Blake | `jordan.learner@demo.com` | `DemoPassword123!` | Full-Stack Engineer, 5-day streak, connected to Alex Vance, 4 DMs, scheduled 1:1 session tomorrow |
| **Demo Learner 2** | Learner | Maya Lin | `maya.learner@demo.com` | `DemoPassword123!` | Medical Doctor, 3-day streak, connected to Dr. Evelyn Harper, DMs active |
| **LIVE Presentation Learner** | Fresh Learner | Leo Sterling | `live.learner@presentation.com` | `Presentation2026!` | **Fresh / Un-onboarded**. Use for live onboarding walkthrough during defense. |
| **LIVE Presentation Mentor** | Fresh Mentor | Sarah Jenkins | `live.mentor@presentation.com` | `Presentation2026!` | **Fresh / Un-onboarded**. Use for live mentor setup demo. |

---

## 2. Step-by-Step Presentation Script

### Act 1: The Cognitive Labor Framework (2 Minutes)
- **Presenter Hook**:
  *"Most career guidance apps feel like generic AI toys: you type a job title, an LLM hallucinates 8 buzzwords with percentage sliders, and you have no idea what to study next. Real vocational mastery requires labor economics, dependency graphs, and cognitive calibration."*
- **Key Talking Points**:
  - Show the 6 Cognitive Occupational Domains + Technical Licensing Companion Track.
  - Explain how kinesthetic/athletic trades are intercepted and guided toward analytical and supervisory tracks.

---

### Act 2: Live Learner Onboarding Walkthrough (4 Minutes)
- **Login Action**: Sign in as `live.learner@presentation.com` with password `Presentation2026!`.
- **Live Onboarding Steps**:
  1. **The 7 Occupational Branches**:
     - Point out the 7 domain chips with catalog counts: `Healthcare (111)`, `Software & Data (41)`, `Engineering (56)`, `Life Sciences (60)`, `Finance (24)`, `Operations (278)`, `Licensing (224)`.
     - Click `Software & Data (41)` or `Healthcare (111)`.
  2. **Instant Keystroke Filter**:
     - Type a character (e.g., *"d"*, *"data"*, *"cloud"*).
     - Show that the list updates on every single keystroke with 0ms network latency.
  3. **Full Detail Preview**:
     - Click on an occupation (e.g. *Full-Stack Engineer* or *Clinical Laboratory Technologist*).
     - Show the complete, unabridged labor description in the preview pane.
     - Click **Select Career Pathway**.
  4. **Behavioral Competency Calibration**:
     - Show the calibration spinner standardizing the vocational pillars.
     - Highlight the 4 behavioral levels: `Not Yet [0%]`, `Novice [20%]`, `Intermediate [50%]`, `Advanced [80%]`.
     - Point out that raw physical abilities (Near Vision, Finger Dexterity) have been suppressed.
     - Rate a few skills and click **Save Competency Profile**.

---

### Act 3: The Daily Drop & Microlearning Engine (3 Minutes)
- **Login Action**: Switch to `jordan.learner@demo.com` (`DemoPassword123!`).
- **Live Demonstration**:
  1. **Daily Drop Card**:
     - Show the "Today's Daily Drop" bundle (3 focused micro-lessons targeting gap skills).
     - Explain the "3 and 3" cognitive pacing (3 active lessons, 3 reserve).
  2. **Streak Mechanics**:
     - Point out the 5-day streak badge and freeze protection token.
  3. **Learning History**:
     - Show completed lessons and diagnostic quiz history.

---

### Act 4: Mentorship, Direct Messaging & Anti-Double-Booking (4 Minutes)
- **Live Demonstration**:
  1. **Learner Mentorship Tab**:
     - In Jordan Blake's view, navigate to **Messages & 1:1 Sessions**.
     - Open the conversation thread with **Alex Vance**. Show real-time message exchange and timestamps.
     - Point out the **Scheduled 1-on-1 Sessions** card ranked by proximity in time (`Tomorrow at 14:00 UTC`) with countdown badge and Google Meet link.
     - Highlight that learners cannot book sessions directly; only mentors can schedule sessions to prevent calendar chaos.
  2. **Switch to Mentor View**:
     - Log out and sign in as `alex.mentor@demo.com` (`DemoPassword123!`):
     - Open the **Mentor Dashboard**.
     - Show accepted connections, unread message badges in the notification bell, and session management.
     - Show the dual anti-double-booking safeguard: mentors and learners cannot have overlapping active sessions.

---

### Act 5: Governance & Production Architecture (2 Minutes)
- **Login Action**: Sign in as `admin@careerbeacon.internal` (`AdminPassword123!`).
- **Showcase**:
  - The Admin Governance Portal (`/admin`).
  - Catalog review queues for human-by-exception governance.
  - Native Supabase PostgreSQL architecture replacing local ephemeral files.

