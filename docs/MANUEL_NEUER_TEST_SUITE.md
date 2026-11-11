# The Manuel Neuer Master Blitz Test Suite
Comprehensive Quality Assurance and Sweeper-Keeper Runbook for Career Beacon

This test suite embodies the "Manuel Neuer" sweeper-keeper philosophy: active anticipation, fail-closed boundaries, impermeable validation gates, and zero tolerance for fake numbers, synthetic mocks, or ungrounded opinions.

---

## Architecture Overview

```
                                [ Learner Onboarding / Search ]
                                               |
                                 check_kinesthetic_redirect()
                                     /                   \
        [ Purely Kinesthetic Occupations ]             [ Eligible Occupations ]
        (Bus Driver, Bricklayer, Footballer)                      |
                        |                               classify_career_field()
         Redirect to Analytical / Supervisory                     |
              Counterpart Pathways                      7 Canonical Career Fields:
                                                        1. tech
                                                        2. engineering
                                                        3. healthcare
                                                        4. science
                                                        5. finance
                                                        6. business_ops
                                                        7. trades_safety
                                                                  |
                                                   [ Modular Ingestion Pipeline ]
                                                   12 Domain-Aware Source Adapters
                                                                  |
                                                  [ Dual Semantic Vector Gate ]
                                                Topical >= 0.56 & Skill >= 0.53
                                               Instructional vs Opinion Centroid
                                                                  |
                                                    [ 5-Lesson Daily Drop Engine ]
                                                 5 Primary + 5 Reserve (Mulligan)
                                                 Alternating Video & Written Sources
                                                                  |
                                                  [ 5-Question Checkpoint Quiz ]
                                                 Lexical Grounding & Shuffled MCQs
```

---

## 1. Pre-Flight Environment Checklist

Before executing any tests, verify your environment:

1. **Working Directory:** Ensure you are in the project root:
   ```powershell
   cd "c:\Users\PC\OneDrive\Desktop\Nota Bene\career-mentor"
   ```

2. **Backend Virtual Environment:**
   ```powershell
   & "backend\.venv\Scripts\python.exe" -V
   ```
   *Expected:* Python 3.10+ or 3.11+.

3. **Backend API Daemon (for live API & UI testing):**
   ```powershell
   cd backend
   & ".\.venv\Scripts\uvicorn.exe" app.main:app --reload --host 127.0.0.1 --port 8000
   ```

4. **Frontend Dev Server:**
   ```powershell
   cd frontend
   npm run dev
   ```
   *Expected:* Vite server running at `http://localhost:5173`.

---

## 2. Phase 1: Kinesthetic Redirection Barrier Tests

**Objective:** Verify that purely manual, athletic, or kinesthetic-motor occupations cannot bypass cognitive micro-learning and are intercepted with redirection to analytical, clinical, or supervisory alternatives.

### Test 1.1: Automated Redirection Verification
Run the following in PowerShell:
```powershell
& "backend\.venv\Scripts\python.exe" -c "
import sys; sys.path.insert(0, 'backend')
from app.core.career_fields import check_kinesthetic_redirect

cases = ['Bus Driver', 'Bricklayer', 'Professional Footballer', 'Software Developer']
for title in cases:
    res = check_kinesthetic_redirect(title)
    if res:
        print(f'[REDIRECTED] {title} -> Alternatives: {len(res.get(\"target_titles\", []))} options')
    else:
        print(f'[PASSED THROUGH] {title}')
"
```

**Expected Output:**
- `Bus Driver` -> `[REDIRECTED]` to `Transportation, Storage, and Distribution Manager`, `Logistician`, etc.
- `Bricklayer` -> `[REDIRECTED]` to `Construction Manager`, `Occupational Health and Safety Specialist`, etc.
- `Professional Footballer` -> `[REDIRECTED]` to `Athletic Trainer`, `Exercise Physiologist`, etc.
- `Software Developer` -> `[PASSED THROUGH]`

### Test 1.2: UI Visual Banner Verification
1. Open `http://localhost:5173/onboarding`.
2. In the career search input, type `Bus Driver` and submit.
3. **Expected UI Outcome:**
   - A matte editorial callout banner appears (`var(--surface-elevated)` background, `var(--border)` border).
   - Message explains that vehicle operation requires kinesthetic and behind-the-wheel certification.
   - Displays selectable alternative cards: *Logistics Coordinator*, *Fleet Operations Manager*, *Transportation Supervisor*.
   - Clicking an alternative card calibrates onboarding for that analytical role.

---

## 3. Phase 2: Canonical 7-Field Classification Matrix

**Objective:** Verify that any candidate occupation maps accurately to one of the 7 canonical career fields.

### Test 2.1: Automated Classification Sweep
Run the following script:
```powershell
& "backend\.venv\Scripts\python.exe" -c "
import sys; sys.path.insert(0, 'backend')
from app.core.career_fields import classify_career_field

test_matrix = [
    ('Backend Developer', 'tech'),
    ('Mechanical Engineer', 'engineering'),
    ('Clinical Pharmacist', 'healthcare'),
    ('Biochemist', 'science'),
    ('Financial Analyst', 'finance'),
    ('Supply Chain Operations Manager', 'business_ops'),
    ('Safety and Compliance Coordinator', 'trades_safety')
]

for title, expected in test_matrix:
    info = classify_career_field(title)
    field_id = info['field_id']
    match = (field_id == expected)
    status = 'PASS' if match else 'FAIL'
    print(f'[{status}] {title:<36} -> {field_id} (Expected: {expected})')
    assert match, f'Mismatch for {title}'
print('\nAll 7 Career Fields classified with 100% accuracy.')
"
```

**Verification Checklist:**
- [PASS] Tech (Software, Data & Cybersecurity)
- [PASS] Engineering (Applied Physical Systems & CAD/Control)
- [PASS] Healthcare (Biomedical & Clinical Practice)
- [PASS] Science (Life, Physical & Analytical Sciences)
- [PASS] Finance (Accounting & Quantitative Valuation)
- [PASS] Business Ops (Management, Supply Chain & Legal)
- [PASS] Trades Safety (Licensing, Code Compliance & OSHA/eCFR)

---

## 4. Phase 3: Modular Live Ingestion and Vector Gate Sweep

**Objective:** Verify that live source adapters fetch authoritative pedagogical material and that the semantic vector gate eliminates personal blogs, fluff, and cross-domain noise.

### Source Adapter Matrix

| Field ID | Primary Adapters | Secondary Adapters | Fallback Adapter |
| :--- | :--- | :--- | :--- |
| `tech` | `youtube`, `mdn` | `owasp`, `structured_tutorial` | `open_textbook` |
| `engineering` | `open_textbook` (Wikibooks) | `youtube`, `osha`, `ecfr` | `arxiv`, `openalex` |
| `healthcare` | `clinical_science` (Europe PMC / NCBI) | `youtube`, `open_textbook` | `openalex` |
| `science` | `clinical_science`, `arxiv` | `youtube`, `openalex` | `open_textbook` |
| `finance` | `finance` (Accounting/GAAP Standards) | `youtube`, `open_textbook`, `ecfr` | `openalex` |
| `business_ops` | `youtube`, `open_textbook` | `structured_tutorial`, `openalex` | `wikipedia` (last resort) |
| `trades_safety` | `osha` (29 CFR), `ecfr` | `youtube`, `open_textbook` | `openalex` |

### Test 3.1: Pedagogical Substance Vector Gate Test
The dual vector gate enforces:
1. `topical_sim >= 0.56` against `{career_title}: {distilled_skill}`
2. `skill_sim >= 0.53` against `{distilled_skill} core principles`
3. Cosine distance to `instructional` anchor must exceed distance to `opinion_showcase` anchor by at least `+0.012`.

Run the vector gate check directly:
```powershell
& "backend\.venv\Scripts\python.exe" -c "
import asyncio, sys; sys.path.insert(0, 'backend')
from app.services.content_service import ContentService

async def check():
    svc = ContentService()
    # Case 1: Instructional text
    good_text = '''REST is an architectural style for distributed hypermedia systems.
    An API conforming to REST constraints must provide stateless client-server communication,
    cacheable responses, and a uniform interface using standard HTTP verbs like GET, POST, PUT, DELETE.'''
    
    # Case 2: Personal blog / opinion text
    fluff_text = '''Why I stopped using REST in my side project. Here is my personal journey
    and why GraphQL is way cooler for my personal portfolio website and why you should switch today.'''
    
    res_good = await svc.verify_pedagogical_substance('REST API Architecture', good_text, 'REST APIs', 'Backend Developer')
    res_fluff = await svc.verify_pedagogical_substance('Why I Ditched REST', fluff_text, 'REST APIs', 'Backend Developer')
    
    print(f'Instructional Text Passed: {res_good} (Expected: True)')
    print(f'Opinion Blog Rejected:    {not res_fluff} (Expected: True)')

asyncio.run(check())
"
```

### Test 3.2: 7-Field Live Ingestion Sweep
Run the dedicated blitz script:
```powershell
& "backend\.venv\Scripts\python.exe" -u "scratch\manuel_neuer_7_career_blitz.py"
```

**Evaluation Thresholds:**
- At least 6 of 7 career fields must return a verified instructional source on the first attempt.
- No source raw text may be under 300 characters.
- YouTube lectures with short descriptions (<800 chars) must automatically merge a written companion text reference.

---

## 5. Phase 4: 5-Lesson Daily Drop Engine and Mulligan Reroll

**Objective:** Verify that the Daily Drop generates exactly 5 primary lessons + 5 reserve lessons across the learner's top 5 deficit skills (max 2 lessons per skill), alternating media formats, and supporting the 1-shot free Mulligan reroll.

### Test 4.1: Automated Multi-Career Daily Drop Generation
Execute the multi-career test suite:
```powershell
& "backend\.venv\Scripts\python.exe" backend/tests/test_daily_drop_multi_career.py
```

### Test 4.2: Manual API Verification via cURL / PowerShell
1. **Trigger Worker:**
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/daily-drop/trigger-worker" -Method Post -Headers @{"Content-Type"="application/json"} -Body '{"user_id": "test-learner-1"}'
   ```
2. **Fetch Daily Drop:**
   ```powershell
   $drop = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/daily-drop?user_id=test-learner-1" -Method Get
   Write-Host "Primary Lessons Count:" $drop.primary_lessons.Count
   Write-Host "Reserve Lessons Count:" $drop.reserve_lessons.Count
   Write-Host "Mulligan Remaining:" $drop.mulligan_available
   ```
   *Expected:* Primary count = 5, Reserve count = 5, Mulligan = true.

3. **Execute Mulligan Reroll:**
   ```powershell
   $reroll = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/daily-drop/reroll" -Method Post -Headers @{"Content-Type"="application/json"} -Body '{"user_id": "test-learner-1"}'
   Write-Host "New Primary Lessons Count:" $reroll.primary_lessons.Count
   Write-Host "Mulligan Available Post-Reroll:" $reroll.mulligan_available
   ```
   *Expected:* Primary count = 5 (swapped with reserve), Mulligan = false.

---

## 6. Phase 5: 5-Question Checkpoint Quiz Engine and Skill Advancement

**Objective:** Ensure that every micro-lesson has an associated 5-question multiple-choice checkpoint, answers are verified against source evidence, option positions are server-side shuffled, and passing modifies learner skill proficiency.

### Test 5.1: Quiz Structure and Shuffling Validation
Run the validator script:
```powershell
& "backend\.venv\Scripts\python.exe" -c "
import sys; sys.path.insert(0, 'backend')
from app.services.content_service import validate_quiz_structure

source_sample = '''
In thermodynamics, the Carnot cycle provides the theoretical upper limit for the efficiency of any classical thermodynamic engine during the conversion of heat into work. The efficiency depends solely on the temperatures of the hot and cold reservoirs, defined as 1 - (Tc / Th), where temperatures are expressed in Kelvin.
'''

sample_quiz = [
    {
        'question': 'What determines the theoretical maximum efficiency of a Carnot engine?',
        'options': ['Reservoir temperatures in Kelvin', 'Working fluid viscosity', 'Piston chamber volume', 'Ambient atmospheric pressure'],
        'correct_answer': 0,
        'explanation': 'Carnot efficiency is defined strictly by the ratio of reservoir temperatures.'
    },
    {
        'question': 'What temperature unit must be used in the Carnot efficiency formula?',
        'options': ['Fahrenheit', 'Celsius', 'Rankine', 'Kelvin'],
        'correct_answer': 3,
        'explanation': 'Absolute temperature in Kelvin is mandatory.'
    },
    {
        'question': 'What is the efficiency formula for a Carnot engine?',
        'options': ['1 - (Tc / Th)', 'Tc / Th', '1 + (Th / Tc)', 'Th - Tc'],
        'correct_answer': 0,
        'explanation': 'The formula is 1 - (Tc / Th).'
    },
    {
        'question': 'Can any real classical heat engine exceed Carnot efficiency?',
        'options': ['Yes, with helium gas', 'No, Carnot is the theoretical upper limit', 'Yes, at high pressure', 'Only in space'],
        'correct_answer': 1,
        'explanation': 'Carnot cycle represents the upper bound.'
    },
    {
        'question': 'What energy conversion does a heat engine perform?',
        'options': ['Light to sound', 'Heat into work', 'Chemical into electrical', 'Nuclear into potential'],
        'correct_answer': 1,
        'explanation': 'Heat engines convert thermal energy into mechanical work.'
    }
]

validated = validate_quiz_structure(sample_quiz, source_sample)
print(f'Quiz Validation Passed: {len(validated) == 5}')
print(f'Correct Answer Indices (shuffled): {[q[\"correct_answer\"] for q in validated]}')
"
```

**Expected Result:**
- Returns exactly 5 validated questions.
- `correct_answer` positions are distributed (e.g. `[2, 0, 3, 1, 2]`), proving Option A bias is eliminated.

### Test 5.2: Quiz Scoring and Skill Boosting Check
1. In the frontend at `http://localhost:5173/recommendations`, select any lesson and click **Take Checkpoint**.
2. **Failure Run:** Select incorrect options to score 2/5 (40%). Click **Submit Checkpoint**.
   - Verify: Red alert *"Score: 40% - Threshold is 60%"*. Skill proficiency remains unchanged.
3. **Passing Run:** Click **Retake Checkpoint**, select correct options to score >= 3/5 (60%+).
   - Verify: Green alert *"Checkpoint Passed"*.
   - Verify: Target skill receives a `+10%` to `+15%` proficiency increase.
   - Lesson card updates to "Completed" with score recorded.

---

## 7. Phase 6: Frontend UI / UX Matte Editorial Check

**Objective:** Guarantee the UI adheres strictly to the Matte Editorial aesthetic with zero neon glow, zero AI sparkle clichés, and full responsive stability.

### Verification Checklist:
1. **Color Tokens:**
   - Card background: `var(--surface-elevated)` (#161922 or matte dark slate).
   - Borders: Subtle 1px solid `var(--border)` (#282c37).
   - Badges: Matte muted gray or monochromatic tint with `11px` typography and `font-weight: 500`.
   - No neon green or glowing cyan borders.
2. **5-Lesson Daily Drop View:**
   - Primary column displays exactly 5 lessons in active view.
   - Header shows "Daily Drop" with "5 Curated Lessons for [User's Career Title]".
   - Free Mulligan button appears: *"Reroll Drop (1 remaining today)"*.
3. **Card Content Details:**
   - Video lessons render YouTube thumbnail with duration badge and channel title.
   - Written lessons display source badge (`arXiv`, `eCFR`, `OSHA`, `Finance Standard`, `Europe PMC`, `MDN`, `OWASP`, `Wikibooks`).
   - Every card has an **Ask Mentor** button in the lower tray that deep-links directly to mentor matching for that specific skill.

---

## 8. Summary of Passing Criteria

| Test Suite Component | Manuel Neuer Standard | Minimum Passing Threshold |
| :--- | :--- | :--- |
| **Kinesthetic Interception** | 100% redirect of motor/athletic occupations | 3/3 test cases redirected |
| **Career Field Classification** | Exact mapping across 7 served tracks | 7/7 test cases matched |
| **Modular Ingestion Pipeline** | Authoritative, domain-governed instructional text | >= 6/7 careers return valid source |
| **Pedagogical Vector Gate** | Fail-closed rejection of blogs and fluff | 100% rejection of opinion text |
| **Daily Drop Sizing** | Exactly 5 primary + 5 reserve | Exactly 10 total lessons in pool |
| **Checkpoint Quiz** | Exactly 5 grounded MCQs with shuffled options | Exactly 5 valid questions per lesson |
| **Skill Advancement** | Strict 60% threshold for proficiency boost | Fail = 0% boost, Pass = +10-15% |

