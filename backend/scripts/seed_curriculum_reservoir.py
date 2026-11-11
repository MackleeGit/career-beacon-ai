"""
backend/scripts/seed_curriculum_reservoir.py
--------------------------------------------
Seeds high-quality, verified educational micro-lessons with 5-question checkpoints
and dense vector embeddings across 6 major careers:
1. Full-Stack Engineer (Tech)
2. Registered Nurse (Healthcare)
3. Data Scientist (Science / Tech)
4. Civil Engineer (Engineering)
5. Financial Analyst (Finance)
6. Operations Research Analyst (Business Ops)

Ensures that Daily Drops, Reshuffling, and Category exploration have deep reserve pools.
Compatible with Supabase micro_content schema and 5-question mastery checkpoint contracts.
"""

import sys
import os
import json
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService
from app.core.career_fields import classify_career_field

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

CURRICULUM_SEEDS = [
    # ── 1. Full-Stack Engineer (Tech) ──
    {
        "career_title": "Full-Stack Engineer",
        "skill_name": "React.js State Architecture",
        "category": "Frontend",
        "title": "Mastering React 18 State Architecture: Context, Zustand, and Immutability",
        "source_type": "youtube",
        "source_adapter": "youtube",
        "source_url": "https://www.youtube.com/watch?v=0ZJgIjIuY7U",
        "author_institution": "React Architecture Team",
        "reading_time_minutes": 15,
        "difficulty_level": 3,
        "summary": "Comprehensive architectural guide to state management in React 18 applications. Covers unidirectional data flow, component re-render boundaries, immutability, selectors, and separating server cache state from client UI state.",
        "takeaways": [
            "Server cache state should not be duplicated in global client stores.",
            "Zustand provides a lightweight, selector-based alternative to boilerplate-heavy Redux.",
            "React 18 Concurrent Mode features like useTransition allow non-blocking UI updates."
        ],
        "concept_overview": "State architecture in modern React applications requires a clear separation between client state and server state. Managing asynchronous server data within global stores causes stale-data anomalies and unnecessary re-renders. By isolating server-cached state with specialized hooks and keeping UI state localized or managed via atomic selector-based stores like Zustand, applications maintain predictable unidirectional data flows and high responsiveness.",
        "practice_scenario": "You are refactoring an enterprise dashboard where updating a filter triggers unnecessary re-renders across charts and tables. You extract filter state into a Zustand store using granular selectors and wrap table recalculations in useTransition, restoring smooth 60fps frame rates.",
        "quizzes": [
            {
                "question": "What is the primary architectural purpose of using selectors with global state in React?",
                "options": [
                    "To prevent unnecessary re-renders of components when unrelated state slices change",
                    "To serialize component state to localStorage automatically",
                    "To bypass the virtual DOM and mutate physical DOM elements directly",
                    "To replace React's synthetic event dispatcher"
                ],
                "answer": "To prevent unnecessary re-renders of components when unrelated state slices change",
                "explanation": "Selectors allow components to subscribe exclusively to the specific slice of state they consume, avoiding re-renders when other slices mutate."
            },
            {
                "question": "Which React hook should be used to mark a state update as non-urgent in React 18?",
                "options": [
                    "useEffect",
                    "useTransition",
                    "useImperativeHandle",
                    "useLayoutEffect"
                ],
                "answer": "useTransition",
                "explanation": "useTransition allows developers to mark state transitions as non-blocking, maintaining UI responsiveness during heavy rendering."
            },
            {
                "question": "Why is duplicating server-side cache data into global Redux or Zustand state considered an anti-pattern?",
                "options": [
                    "It creates dual sources of truth and causes stale cache synchronization bugs",
                    "It prevents HTTP requests from using TLS encryption",
                    "It forces JavaScript to run in strict single-threaded execution",
                    "It breaks the browser history stack"
                ],
                "answer": "It creates dual sources of truth and causes stale cache synchronization bugs",
                "explanation": "Duplicating server response data into client stores leads to cache invalidation headaches and out-of-sync UI states."
            },
            {
                "question": "In React 18, what mechanism ensures that parent state updates do not mutate existing child component props in-place?",
                "options": [
                    "Object.freeze at the runtime level",
                    "Immutability conventions and pure rendering functions",
                    "Web Workers memory isolation",
                    "CSS stylesheet isolation"
                ],
                "answer": "Immutability conventions and pure rendering functions",
                "explanation": "React relies on immutability conventions so shallow reference comparisons determine whether child components need to re-render."
            },
            {
                "question": "When should React Context be preferred over external store managers like Zustand?",
                "options": [
                    "For high-frequency tabular real-time ticker data",
                    "For low-frequency, app-wide values like themes, localization, and current authenticated user",
                    "For managing multi-gigabyte client binary buffers",
                    "Whenever WebSocket connections are established"
                ],
                "answer": "For low-frequency, app-wide values like themes, localization, and current authenticated user",
                "explanation": "Context is optimal for infrequently updated values. High-frequency changes trigger re-renders in all consuming subtrees without granular selector optimization."
            }
        ]
    },
    {
        "career_title": "Full-Stack Engineer",
        "skill_name": "PostgreSQL Query Optimization",
        "category": "Databases",
        "title": "PostgreSQL Indexing Internals: B-Tree vs. GIN Indexes and EXPLAIN ANALYZE",
        "source_type": "article",
        "source_adapter": "structured_tutorial",
        "source_url": "https://www.postgresql.org/docs/current/indexes.html",
        "author_institution": "PostgreSQL Global Development Group",
        "reading_time_minutes": 12,
        "difficulty_level": 3,
        "summary": "Deep dive into PostgreSQL relational query optimization. Explains cost-based query planners, reading EXPLAIN ANALYZE execution trees, index-only scans, avoiding sequential scans on large tables, and composite index ordering.",
        "takeaways": [
            "B-Tree indexes are ideal for equality and range queries on scalar data types.",
            "GIN is optimized for array and JSONB containment queries.",
            "Index columns must be ordered by query filter selectivity."
        ],
        "concept_overview": "Effective database optimization requires understanding how the PostgreSQL query planner evaluates data access paths. The cost model compares sequential table scans against index scans. When querying JSONB columns or full-text documents, standard B-Trees only index exact matches. Generalized Inverted Indexes (GIN) deconstruct complex composite documents into individual keys and values, enabling logarithmic lookups for containment operators.",
        "practice_scenario": "An API endpoint searching user profiles by tags and metadata takes 1400ms under load. By profiling with EXPLAIN (ANALYZE, BUFFERS), you identify a sequential scan on a 500,000-row table. You replace the scalar B-tree with a GIN index on the tags JSONB column, reducing query time to 8ms.",
        "quizzes": [
            {
                "question": "In PostgreSQL, which index type is most appropriate for searching inside JSONB columns containing document arrays?",
                "options": [
                    "B-Tree",
                    "GIN (Generalized Inverted Index)",
                    "BRIN (Block Range Index)",
                    "Hash Index"
                ],
                "answer": "GIN (Generalized Inverted Index)",
                "explanation": "GIN indexes are specifically designed for composite items where individual elements or key-value pairs need to be queried independently."
            },
            {
                "question": "What is the key difference between EXPLAIN and EXPLAIN ANALYZE in PostgreSQL?",
                "options": [
                    "EXPLAIN executes the query and returns actual execution times, while EXPLAIN ANALYZE only estimates cost",
                    "EXPLAIN only generates estimated execution plans; EXPLAIN ANALYZE actually runs the query and outputs actual runtime metrics",
                    "EXPLAIN deletes rows from the table, while EXPLAIN ANALYZE rolls back transactions",
                    "EXPLAIN only works on SQLite databases"
                ],
                "answer": "EXPLAIN only generates estimated execution plans; EXPLAIN ANALYZE actually runs the query and outputs actual runtime metrics",
                "explanation": "EXPLAIN ANALYZE executes the statement, measuring real CPU time and buffer read counts alongside planner estimates."
            },
            {
                "question": "In a composite B-Tree index on (tenant_id, created_at), which query can fully exploit the index?",
                "options": [
                    "WHERE created_at > '2026-01-01'",
                    "WHERE tenant_id = 'org_123' AND created_at > '2026-01-01'",
                    "WHERE status = 'active'",
                    "ORDER BY updated_at DESC"
                ],
                "answer": "WHERE tenant_id = 'org_123' AND created_at > '2026-01-01'",
                "explanation": "B-Tree composite indexes must be matched starting from the leading left column; filtering on tenant_id allows efficient range traversal on created_at."
            },
            {
                "question": "What indicates an Index-Only Scan has succeeded in PostgreSQL?",
                "options": [
                    "The query planner avoided visiting heap table pages because all requested columns were present in the index and marked visible",
                    "The database bypassed all locking mechanisms",
                    "The index completely replaced the primary key table",
                    "No memory buffer was allocated"
                ],
                "answer": "The query planner avoided visiting heap table pages because all requested columns were present in the index and marked visible",
                "explanation": "An index-only scan retrieves all projected columns directly from the index structure without reading physical heap pages."
            },
            {
                "question": "Why might the PostgreSQL query planner choose a sequential scan over an available index?",
                "options": [
                    "The table is small enough that sequential reading into shared buffers is faster than random index block lookups",
                    "The planner is corrupt and must be restarted",
                    "Indexes are only utilized during midnight cron runs",
                    "PostgreSQL disables indexes on primary keys"
                ],
                "answer": "The table is small enough that sequential reading into shared buffers is faster than random index block lookups",
                "explanation": "For small tables or queries selecting a large percentage of total rows, sequential block I/O is cheaper than random index traversal."
            }
        ]
    },
    {
        "career_title": "Full-Stack Engineer",
        "skill_name": "Docker & Container Orchestration",
        "category": "DevOps",
        "title": "Multi-Stage Docker Builds & Container Security Best Practices",
        "source_type": "article",
        "source_adapter": "structured_tutorial",
        "source_url": "https://docs.docker.com/build/building/multi-stage/",
        "author_institution": "Docker Documentation / CNCF",
        "reading_time_minutes": 10,
        "difficulty_level": 3,
        "summary": "Standardization of production containerization using multi-stage Dockerfiles. Separates build toolchains from minimal runtime environments, minimizing attack surfaces.",
        "takeaways": [
            "Multi-stage builds eliminate compiler toolchains from final production images.",
            "Never run production containers as the root user.",
            "Use non-caching secret mounts for credential injection."
        ],
        "concept_overview": "Containerizing modern applications requires balancing developer ergonomics with production security. Shipping images containing compilers, package managers, and development dependencies inflates image size and exposes vulnerable CVE surfaces. Multi-stage Dockerfiles enable building binaries in a heavyweight stage while copying strictly the compiled executable into a minimal distroless or alpine base image.",
        "practice_scenario": "A legacy Node.js container is 1.4 GB and flags 38 high-severity CVEs in security scanning. You implement a multi-stage Docker build separating node_modules pruning from runtime execution, reducing image size to 85 MB and eliminating compiler-level vulnerabilities.",
        "quizzes": [
            {
                "question": "What is the primary security advantage of using multi-stage Docker builds?",
                "options": [
                    "It automatically signs the image with a verified TLS certificate",
                    "It prevents build tools, compilers, and source artifacts from remaining in the final runtime image",
                    "It isolates container network namespaces from the host bridge",
                    "It encrypts environment variables at runtime"
                ],
                "answer": "It prevents build tools, compilers, and source artifacts from remaining in the final runtime image",
                "explanation": "Multi-stage builds allow compiling in an ephemeral stage and copying only the compiled artifacts into a lightweight, secure runtime base."
            },
            {
                "question": "Why is running container processes as the default 'root' user dangerous in production?",
                "options": [
                    "Root users consume double the CPU quota in cgroups",
                    "If a container escape vulnerability occurs, the attacker gains root privileges on the underlying host kernel",
                    "Root users cannot write files to mounted volumes",
                    "Kubernetes refuses to schedule containers with user ID 0"
                ],
                "answer": "If a container escape vulnerability occurs, the attacker gains root privileges on the underlying host kernel",
                "explanation": "Container root is host root unless user namespaces are configured; dropping privileges to a dedicated non-root user mitigates escape risks."
            },
            {
                "question": "Which Dockerfile instruction creates a persistent layer that should be optimized to leverage caching?",
                "options": [
                    "EXPOSE",
                    "RUN",
                    "LABEL",
                    "ENTRYPOINT"
                ],
                "answer": "RUN",
                "explanation": "RUN commands generate image layers on disk; placing static dependency installations before dynamic application code preserves build cache."
            },
            {
                "question": "What is a 'distroless' container image?",
                "options": [
                    "An image that contains only your application and its runtime dependencies, omitting package managers and shells",
                    "An image that runs without a Linux kernel",
                    "An image that cannot be pushed to container registries",
                    "An image configured without IP networking"
                ],
                "answer": "An image that contains only your application and its runtime dependencies, omitting package managers and shells",
                "explanation": "Distroless images contain no shell, package manager, or standard OS utilities, minimizing vulnerability attack surface."
            },
            {
                "question": "How should sensitive build secrets like private npm tokens be passed during Docker image builds?",
                "options": [
                    "Hardcoded in the Dockerfile ARG instruction",
                    "Committed to the git repository inside .env",
                    "Using BuildKit secret mounts (--mount=type=secret)",
                    "Passed as public environment variables via docker build -e"
                ],
                "answer": "Using BuildKit secret mounts (--mount=type=secret)",
                "explanation": "BuildKit secret mounts expose credentials during command execution without baking them into final image layer metadata."
            }
        ]
    },

    # ── 2. Registered Nurse (Healthcare) ──
    {
        "career_title": "Registered Nurse",
        "skill_name": "NCLEX Pharmacology & Dosage Calculations",
        "category": "Clinical",
        "title": "Clinical Pharmacology for NCLEX: Safe Medication Administration & High-Alert Drugs",
        "source_type": "youtube",
        "source_adapter": "youtube",
        "source_url": "https://www.youtube.com/watch?v=0kF6z8lR0pY",
        "author_institution": "RegisteredNurseRN / NCLEX Review",
        "reading_time_minutes": 14,
        "difficulty_level": 3,
        "summary": "Clinical protocol for pediatric and adult drug calculation, therapeutic index monitoring, and nursing interventions for high-alert medications including anticoagulants, insulins, and cardiac glycosides.",
        "takeaways": [
            "Verify the 5 Rights of Medication Administration prior to dispensing.",
            "Digoxin toxicity is precipitated by hypokalemia; assess apical pulse for 60 seconds.",
            "Heparin therapeutic efficacy is monitored via aPTT; Warfarin via PT/INR."
        ],
        "concept_overview": "Safe pharmacological administration is a primary nursing responsibility requiring precise physiological assessment and mathematical accuracy. High-alert medications like IV heparin, insulin, and cardiac glycosides possess narrow therapeutic windows where minor dosage errors cause life-threatening adverse reactions. Nurses must systematically verify patient identification, allergy history, laboratory parameters, and apical pulse before dispensing.",
        "practice_scenario": "You are preparing to administer morning medications to a patient with heart failure. The MAR lists Digoxin 0.25 mg orally. You auscultate the apical pulse at the mitral area for a full 60 seconds and count 52 beats per minute. You immediately hold the medication, check the serum potassium level, and document the assessment.",
        "quizzes": [
            {
                "question": "A patient scheduled to receive Digoxin has an apical heart rate of 54 bpm. What is the nurse's priority action?",
                "options": [
                    "Administer the dose with a full glass of water",
                    "Withhold the medication and notify the prescribing physician",
                    "Administer half the prescribed dose and re-check pulse in 2 hours",
                    "Administer an immediate potassium bolus"
                ],
                "answer": "Withhold the medication and notify the prescribing physician",
                "explanation": "Digoxin should be withheld if the adult apical pulse is below 60 bpm due to the danger of severe bradycardia and digitalis toxicity."
            },
            {
                "question": "Which laboratory value must be monitored to evaluate the therapeutic efficacy of IV unfractionated Heparin therapy?",
                "options": [
                    "Activated Partial Thromboplastin Time (aPTT)",
                    "International Normalized Ratio (INR)",
                    "Serum Creatinine",
                    "Erythrocyte Sedimentation Rate (ESR)"
                ],
                "answer": "Activated Partial Thromboplastin Time (aPTT)",
                "explanation": "Unfractionated heparin is monitored using aPTT, whereas warfarin is monitored using PT/INR."
            },
            {
                "question": "What is the primary reversal antidote for severe benzodiazepine overdose causing respiratory depression?",
                "options": [
                    "Naloxone",
                    "Flumazenil",
                    "Protamine Sulfate",
                    "Vitamin K"
                ],
                "answer": "Flumazenil",
                "explanation": "Flumazenil is the competitive antagonist for benzodiazepines, while Naloxone reverses opioids and Protamine sulfate reverses heparin."
            },
            {
                "question": "When administering regular insulin via continuous IV infusion, what electrolyte disturbance is the nurse monitoring for?",
                "options": [
                    "Hypercalcemia",
                    "Hypokalemia",
                    "Hypernatremia",
                    "Hypermagnesemia"
                ],
                "answer": "Hypokalemia",
                "explanation": "Insulin shifts potassium from the extracellular space into cells, potentially causing rapid hypokalemia and cardiac dysrhythmias."
            },
            {
                "question": "What is the standard nurse action before administering potassium chloride (KCl) IV piggyback?",
                "options": [
                    "Verify urine output is adequate (at least 30 mL/hr)",
                    "Administer via rapid IV push over 30 seconds",
                    "Mix with dextrose 50% without physician order",
                    "Warm the bag to 45 degrees Celsius"
                ],
                "answer": "Verify urine output is adequate (at least 30 mL/hr)",
                "explanation": "Potassium is cleared renally; administering IV potassium in oliguric patients causes lethal hyperkalemia. IV potassium must never be given IV push."
            }
        ]
    },
    {
        "career_title": "Registered Nurse",
        "skill_name": "Emergency Triage & Patient Assessment",
        "category": "Clinical",
        "title": "Emergency Severity Index (ESI): 5-Level Triage Acuity Assessment",
        "source_type": "article",
        "source_adapter": "clinical_science",
        "source_url": "https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html",
        "author_institution": "Agency for Healthcare Research and Quality (AHRQ)",
        "reading_time_minutes": 12,
        "difficulty_level": 3,
        "summary": "Standard operational guidelines for the Emergency Severity Index 5-level triage protocol. Establishes rapid clinical judgment for immediate resuscitation, high-risk situations, and resource consumption.",
        "takeaways": [
            "ESI Level 1 requires immediate life-saving intervention.",
            "ESI Level 2 identifies high-risk situations, severe distress, or altered mental status.",
            "ESI Levels 3 through 5 are stratified based on projected clinical resource consumption."
        ],
        "concept_overview": "Emergency Severity Index (ESI) is a validated 5-level triage algorithm used in emergency medicine to rapidly prioritize patients based on acuity and resource needs. Rather than relying on simple first-come first-served principles, ESI asks systematic questions regarding immediate life-saving needs, potential high-risk physiological decompensation, and projected diagnostic interventions.",
        "practice_scenario": "In a crowded ED waiting room, a 58-year-old patient presents with diaphoresis, substernal crushing chest pressure radiating to the left jaw, and oxygen saturation of 94%. You immediately assign ESI Level 2, expedite an urgent 12-lead ECG within 10 minutes, and transfer directly to an acute monitored bed.",
        "quizzes": [
            {
                "question": "Under the ESI protocol, which patient meets criteria for immediate Level 1 categorization?",
                "options": [
                    "A 45-year-old with sudden onset severe flank pain and hematuria",
                    "A 62-year-old presenting with unresponsive agonal breathing and no palpable carotid pulse",
                    "A 28-year-old with a 4cm scalp laceration and stable vital signs",
                    "A 19-year-old with suspected acute appendicitis and a fever of 38.5C"
                ],
                "answer": "A 62-year-old presenting with unresponsive agonal breathing and no palpable carotid pulse",
                "explanation": "ESI Level 1 is reserved exclusively for patients with impending or immediate cardiac/respiratory arrest requiring immediate life-saving resuscitation."
            },
            {
                "question": "What distinguishes an ESI Level 2 patient from an ESI Level 3 patient?",
                "options": [
                    "Level 2 is a high-risk situation, altered mental state, severe pain/distress, or danger zone vital signs",
                    "Level 2 requires zero hospital resources",
                    "Level 2 patients can safely wait up to 4 hours in the waiting room",
                    "Level 2 is determined solely by age over 65"
                ],
                "answer": "Level 2 is a high-risk situation, altered mental state, severe pain/distress, or danger zone vital signs",
                "explanation": "Level 2 identifies patients who should not wait because their clinical condition could deteriorate rapidly without prompt intervention."
            },
            {
                "question": "How are ESI Levels 3, 4, and 5 differentiated once high-risk criteria are ruled out?",
                "options": [
                    "By health insurance coverage status",
                    "By the number of projected diagnostic or therapeutic resources required (2+ for Level 3, 1 for Level 4, 0 for Level 5)",
                    "By patient body mass index",
                    "By distance traveled to the hospital"
                ],
                "answer": "By the number of projected diagnostic or therapeutic resources required (2+ for Level 3, 1 for Level 4, 0 for Level 5)",
                "explanation": "Resource anticipation stratifies lower-acuity patients: 2 or more resources assign Level 3; one resource assigns Level 4; zero assigns Level 5."
            },
            {
                "question": "Which of the following is counted as a 'resource' under ESI triage definitions?",
                "options": [
                    "Routine oral medication administration",
                    "Saline lock insertion alone without IV fluids",
                    "IV antibiotics and chest CT with contrast",
                    "Crutches fitting without X-rays"
                ],
                "answer": "IV antibiotics and chest CT with contrast",
                "explanation": "Diagnostic lab work, CT/X-ray imaging, IV medications, and specialist consults count as distinct ESI resources."
            },
            {
                "question": "A 7-month-old infant arrives with a rectal temperature of 39.2C, heart rate of 190 bpm, and lethargy. What is the appropriate triage classification?",
                "options": [
                    "ESI Level 5 (Non-urgent)",
                    "ESI Level 2 (High Risk / Danger Zone Vitals)",
                    "ESI Level 4 (Fast Track)",
                    "Discharge with oral rehydration instructions"
                ],
                "answer": "ESI Level 2 (High Risk / Danger Zone Vitals)",
                "explanation": "Lethargy combined with extreme pediatric tachycardia and high fever flags pediatric danger zone vitals, warranting immediate ESI Level 2 placement."
            }
        ]
    },
    {
        "career_title": "Registered Nurse",
        "skill_name": "Infection Control & Sterile Technique",
        "category": "Safety",
        "title": "CDC Transmission-Based Precautions: Airborne, Droplet, and Contact Isolation",
        "source_type": "article",
        "source_adapter": "clinical_science",
        "source_url": "https://www.cdc.gov/infection-control/hcp/isolation-precautions/",
        "author_institution": "Centers for Disease Control and Prevention (CDC)",
        "reading_time_minutes": 10,
        "difficulty_level": 2,
        "summary": "Evidence-based hospital infection prevention procedures. Differentiates standard precautions from transmission-based isolation, PPE donning/doffing sequences, and negative-pressure airflow standards.",
        "takeaways": [
            "Airborne precautions (Tuberculosis, Measles) require N95 respirator and negative-pressure room.",
            "Donning PPE order: Gown, Mask/Respirator, Goggles/Shield, Gloves.",
            "Doffing PPE order: Gloves, Goggles, Gown, Mask/Respirator."
        ],
        "concept_overview": "Infection control in clinical healthcare centers on breaking the epidemiological chain of transmission. Beyond universal standard precautions applied to all patient encounters, transmission-based precautions add tailored barrier defenses against specific modes of spread: Contact (C. difficile, MRSA), Droplet (Influenza, Pertussis), and Airborne (Mycobacterium tuberculosis, Varicella). Strict sequencing of PPE donning and doffing prevents self-contamination.",
        "practice_scenario": "A patient with suspected pulmonary tuberculosis is admitted to your medical-surgical floor. You immediately place the patient in an Airborne Infection Isolation Room (AIIR) with negative pressure, verify 12 air changes per hour, don a fit-tested N95 respirator before entering, and ensure the patient wears a surgical mask if transported.",
        "quizzes": [
            {
                "question": "Which personal protective equipment (PPE) item should be removed FIRST according to CDC doffing guidelines?",
                "options": [
                    "Respirator / Mask",
                    "Isolation Gown",
                    "Gloves",
                    "Face Shield"
                ],
                "answer": "Gloves",
                "explanation": "Gloves are the most heavily contaminated PPE item and must be removed first to prevent contaminating the face and neck during subsequent steps."
            },
            {
                "question": "For a patient infected with Clostridioides difficile, which hand hygiene method is mandatory?",
                "options": [
                    "Alcohol-based hand rub for 20 seconds",
                    "Washing with antimicrobial soap and warm water",
                    "Chlorhexidine wipes",
                    "Sterile saline rinse"
                ],
                "answer": "Washing with antimicrobial soap and warm water",
                "explanation": "C. difficile produces bacterial spores that are resistant to alcohol; mechanical friction with soap and running water is required to remove them."
            },
            {
                "question": "Which infectious pathogen requires an Airborne Infection Isolation Room (AIIR) with negative-pressure airflow?",
                "options": [
                    "Norovirus",
                    "Mycobacterium tuberculosis",
                    "Pseudomonas aeruginosa",
                    "Staphylococcus aureus"
                ],
                "answer": "Mycobacterium tuberculosis",
                "explanation": "Tuberculosis droplet nuclei remain suspended in the air over long distances, mandating negative-pressure isolation and N95 respirators."
            },
            {
                "question": "When donning PPE, what is the proper sequential order of application?",
                "options": [
                    "Gloves, Mask, Gown, Goggles",
                    "Gown, Mask/Respirator, Goggles/Face Shield, Gloves",
                    "Mask, Gloves, Gown, Goggles",
                    "Goggles, Gown, Gloves, Mask"
                ],
                "answer": "Gown, Mask/Respirator, Goggles/Face Shield, Gloves",
                "explanation": "Standard CDC donning sequence starts with the gown, followed by respiratory protection, eye protection, and finally gloves pulled over gown cuffs."
            },
            {
                "question": "During a sterile urinary catheterization procedure, the sterile glove accidentally brushes against the side rail of the patient bed. What must the nurse do?",
                "options": [
                    "Wipe the glove with an alcohol swab and continue",
                    "Discard the contaminated glove and don a fresh sterile glove",
                    "Complete the catheter insertion quickly to minimize exposure",
                    "Irrigate the catheter with sterile water"
                ],
                "answer": "Discard the contaminated glove and don a fresh sterile glove",
                "explanation": "Any contact between a sterile barrier and an unsterile surface constitutes contamination; sterile technique demands immediate replacement."
            }
        ]
    },

    # ── 3. Data Scientist (Science / Tech) ──
    {
        "career_title": "Data Scientist",
        "skill_name": "Machine Learning Pipeline Engineering",
        "category": "AI/ML",
        "title": "Production Scikit-Learn Pipelines: Feature Scaling, Encoders, and Leakage Prevention",
        "source_type": "article",
        "source_adapter": "structured_tutorial",
        "source_url": "https://scikit-learn.org/stable/modules/compose.html",
        "author_institution": "Scikit-Learn Core Contributors",
        "reading_time_minutes": 14,
        "difficulty_level": 3,
        "summary": "Engineering robust machine learning workflows using ColumnTransformer and Pipeline. Focuses on strictly preventing train-test data leakage during imputation, one-hot encoding, and numerical scaling across cross-validation folds.",
        "takeaways": [
            "Fitting scalers or imputers before train-test splitting introduces catastrophic target leakage.",
            "Pipelines encapsulate preprocessing and estimator into a unified serialization artifact.",
            "ColumnTransformer routes specific columns to distinct numerical or categorical transformers."
        ],
        "concept_overview": "Production machine learning pipelines combine data transformation and predictive modeling into atomic, repeatable components. Performing data preprocessing such as mean imputation or standard scaling on an entire dataset prior to cross-validation causes statistical information from holdout validation sets to leak into model parameters. Encapsulating transformations within scikit-learn Pipelines guarantees that transformations are fit strictly on training folds.",
        "practice_scenario": "A churn prediction model showed 96% ROC-AUC in local validation but collapsed to 68% in production. You discover that target encoding was performed globally before k-fold cross-validation. Refactoring into a ColumnTransformer inside a scikit-learn Pipeline eliminates data leakage and restores genuine model generalizability.",
        "quizzes": [
            {
                "question": "Why must StandardScaler.fit() only be called on the training split, never on the combined dataset?",
                "options": [
                    "To conserve RAM memory buffers during NumPy array serialization",
                    "To prevent data leakage by keeping mean and variance information of the test set completely unseen",
                    "Because StandardScaler only supports integer data types",
                    "To ensure gradient descent converges in exactly one epoch"
                ],
                "answer": "To prevent data leakage by keeping mean and variance information of the test set completely unseen",
                "explanation": "Fitting preprocessing transformers on test data exposes distributional parameters to the model prior to evaluation, artificially inflating performance metrics."
            },
            {
                "question": "In scikit-learn, what is the primary role of ColumnTransformer?",
                "options": [
                    "To rotate 2D pandas DataFrames into 3D tensors",
                    "To apply different transformation pipelines to distinct subsets of features (e.g. numeric vs categorical)",
                    "To automatically generate SQL CREATE TABLE statements",
                    "To deploy Docker containers to cloud endpoints"
                ],
                "answer": "To apply different transformation pipelines to distinct subsets of features (e.g. numeric vs categorical)",
                "explanation": "ColumnTransformer routes specified columns to tailored transformation sub-pipelines before concatenating their output arrays."
            },
            {
                "question": "When evaluating an imbalanced classification problem where positive cases represent 1% of samples, which metric is most informative?",
                "options": [
                    "Accuracy",
                    "Precision-Recall AUC (PR-AUC)",
                    "Mean Absolute Error (MAE)",
                    "R-Squared"
                ],
                "answer": "Precision-Recall AUC (PR-AUC)",
                "explanation": "When classes are heavily skewed, high accuracy is trivially obtained by predicting the majority class; PR-AUC focuses directly on positive class performance."
            },
            {
                "question": "What is the purpose of using K-Fold cross-validation instead of a single train-test split?",
                "options": [
                    "To ensure the model gets trained on test data",
                    "To obtain a lower-variance estimate of model generalization performance across diverse data partitions",
                    "To eliminate the need for hyperparameter tuning",
                    "To convert supervised models into unsupervised clusterers"
                ],
                "answer": "To obtain a lower-variance estimate of model generalization performance across diverse data partitions",
                "explanation": "K-fold cross-validation averages validation scores across K disjoint splits, minimizing sample bias from a single lucky or unlucky split."
            },
            {
                "question": "What is the principal symptom of severe overfitting in a supervised learning model?",
                "options": [
                    "High training error and high validation error",
                    "Extremely low training error accompanied by high validation error",
                    "Low CPU utilization during backpropagation",
                    "High sparsity in input features"
                ],
                "answer": "Extremely low training error accompanied by high validation error",
                "explanation": "Overfitting occurs when a model memorizes idiosyncrasies and noise in the training data, leading to poor generalization on unseen validation data."
            }
        ]
    },

    # ── 4. Financial Analyst (Finance) ──
    {
        "career_title": "Financial Analyst",
        "skill_name": "Discounted Cash Flow (DCF) Valuation",
        "category": "Finance",
        "title": "Corporate Valuation: Unlevered Free Cash Flow (UFCF) and WACC Calculation",
        "source_type": "article",
        "source_adapter": "finance",
        "source_url": "https://corporatefinanceinstitute.com/resources/valuation/dcf-formula-guide/",
        "author_institution": "Corporate Finance Institute (CFI)",
        "reading_time_minutes": 15,
        "difficulty_level": 3,
        "summary": "Core corporate financial modeling of intrinsic company value. Detailed calculation of Unlevered Free Cash Flow, Capital Asset Pricing Model for cost of equity, and Weighted Average Cost of Capital.",
        "takeaways": [
            "Unlevered FCF represents cash available to all capital providers.",
            "WACC weights cost of debt by the after-tax marginal corporate rate.",
            "Terminal value is modeled using Gordon Growth or Exit Multiple."
        ],
        "concept_overview": "Discounted Cash Flow (DCF) valuation models the intrinsic economic value of an enterprise by discounting projected future cash flows to their present value using an appropriate risk-adjusted discount rate. By utilizing Unlevered Free Cash Flow (UFCF)—cash generated after capital expenditures and operating working capital but before debt interest—the valuation remains independent of capital structure.",
        "practice_scenario": "You are building a 5-year valuation model for an acquisition candidate. Using historical financials, you forecast NOPAT, add back depreciation, subtract planned CapEx, and project changes in net working capital. Discounting cash flows at a calculated WACC of 8.5% reveals the target is undervalued by 18% compared to current public market multiples.",
        "quizzes": [
            {
                "question": "In the Weighted Average Cost of Capital (WACC) formula, why is the cost of debt multiplied by (1 - Tax Rate)?",
                "options": [
                    "Because debt interest payments are tax-deductible expenses (the interest tax shield)",
                    "To account for inflation risk premiums on sovereign bonds",
                    "Because dividend payouts are taxed at corporate capital gains rates",
                    "To discount preferred stock dividends"
                ],
                "answer": "Because debt interest payments are tax-deductible expenses (the interest tax shield)",
                "explanation": "Interest expense reduces taxable income, creating an interest tax shield that lowers the effective after-tax cost of debt for corporations."
            },
            {
                "question": "What is the formula for Unlevered Free Cash Flow (Free Cash Flow to Firm)?",
                "options": [
                    "Net Income - Dividends Paid",
                    "EBIT * (1 - Tax Rate) + D&A - Capital Expenditures - Change in Net Working Capital",
                    "Revenue - Total Operating Costs",
                    "Gross Profit + Cash From Financing Activities"
                ],
                "answer": "EBIT * (1 - Tax Rate) + D&A - Capital Expenditures - Change in Net Working Capital",
                "explanation": "UFCF begins with NOPAT (EBIT after taxes), adds back non-cash depreciation & amortization, and deducts reinvestment in Capex and working capital."
            },
            {
                "question": "Under the Capital Asset Pricing Model (CAPM), what does Beta represent?",
                "options": [
                    "The company's historical annual dividend yield",
                    "The sensitivity of the asset's returns relative to the overall market portfolio's returns",
                    "The ratio of book value to market value of debt",
                    "The probability of corporate bankruptcy within 12 months"
                ],
                "answer": "The sensitivity of the asset's returns relative to the overall market portfolio's returns",
                "explanation": "Beta measures systematic non-diversifiable risk; a Beta of 1.2 indicates the stock is expected to be 20% more volatile than the market."
            },
            {
                "question": "In the Gordon Growth Model for Terminal Value, what condition must hold regarding the perpetual growth rate (g) and WACC?",
                "options": [
                    "Growth rate must be strictly equal to inflation",
                    "Growth rate must be strictly less than WACC",
                    "Growth rate must exceed 10% per annum",
                    "Growth rate must be greater than WACC"
                ],
                "answer": "Growth rate must be strictly less than WACC",
                "explanation": "If the perpetual growth rate g equals or exceeds WACC, the denominator (WACC - g) becomes zero or negative, resulting in mathematically nonsensical infinite valuation."
            },
            {
                "question": "How does an increase in working capital (e.g. higher inventory holding) affect Free Cash Flow in a given year?",
                "options": [
                    "Increases Free Cash Flow because inventory is an asset",
                    "Decreases Free Cash Flow because cash is tied up in operating assets",
                    "Has zero impact on Free Cash Flow",
                    "Directly increases corporate taxable earnings"
                ],
                "answer": "Decreases Free Cash Flow because cash is tied up in operating assets",
                "explanation": "An increase in net working capital represents a cash outflow (reinvestment into receivables/inventory), reducing the net cash available to investors."
            }
        ]
    },

    # ── 5. Civil Engineer (Engineering) ──
    {
        "career_title": "Civil Engineer",
        "skill_name": "Structural Load & Beam Analysis",
        "category": "Engineering",
        "title": "Structural Mechanics: Shear Force and Bending Moment Diagrams in Reinforced Concrete",
        "source_type": "article",
        "source_adapter": "open_textbook",
        "source_url": "https://openstax.org/details/books/university-physics-volume-1",
        "author_institution": "OpenStax / ASCE",
        "reading_time_minutes": 14,
        "difficulty_level": 3,
        "summary": "Principles of structural equilibrium and internal load calculation for civil infrastructure. Construction of shear force and bending moment diagrams under distributed loads, and calculation of section modulus.",
        "takeaways": [
            "Bending moment reaches its local maximum where shear force crosses zero.",
            "Reinforced concrete places rebar at tension zones because concrete is weak in tension.",
            "Factor of safety scales ultimate load over allowable working stress."
        ],
        "concept_overview": "Structural analysis is the fundamental discipline that ensures built infrastructure safely resists external dead, live, wind, and seismic loads without failure. By applying static equilibrium equations, engineers compute internal shear forces and bending moments along beam spans. Because concrete possesses high compressive strength but poor tensile capacity, longitudinal steel rebar must be positioned precisely in tension zones identified on bending moment diagrams.",
        "practice_scenario": "You are designing a continuous reinforced concrete bridge girder subject to vehicle live loading. You plot shear force and bending moment diagrams. At midspan where positive bending moment induces tension on the bottom fiber, you specify tensile rebar; over piers where negative moment causes top fiber tension, you detail top steel reinforcement.",
        "quizzes": [
            {
                "question": "For a simply supported beam with a uniformly distributed load (UDL), at what point along the span does the bending moment reach its maximum?",
                "options": [
                    "At the left support",
                    "At the exact center of the span where shear force is zero",
                    "At the point of load application closest to the right support",
                    "At both support reactions simultaneously"
                ],
                "answer": "At the exact center of the span where shear force is zero",
                "explanation": "By calculus relationship (dM/dx = V), maximum bending moment occurs where shear force equals zero, which is at the midspan for symmetrical UDL."
            },
            {
                "question": "Why is steel reinforcement placed specifically in the lower zone of a simply supported concrete beam under downward loading?",
                "options": [
                    "To insulate the concrete from thermal conductivity",
                    "Because concrete is strong in compression but weak in tension, and downward loading creates tension in the lower fibers",
                    "To reduce the overall weight of the structure",
                    "To increase electrical grounding throughout the building"
                ],
                "answer": "Because concrete is strong in compression but weak in tension, and downward loading creates tension in the lower fibers",
                "explanation": "Concrete has high compressive strength but only 10% tensile capacity; steel carries the tensile forces developing in the bottom fibers."
            },
            {
                "question": "What is the mathematical relationship between distributed load (w), shear force (V), and bending moment (M)?",
                "options": [
                    "dV/dx = -w and dM/dx = V",
                    "dM/dx = -w and dV/dx = M",
                    "V = w * M",
                    "M = dV/dx + w"
                ],
                "answer": "dV/dx = -w and dM/dx = V",
                "explanation": "The rate of change of shear force is equal to the negative distributed load, and the rate of change of bending moment is equal to the shear force."
            },
            {
                "question": "What type of stress do stirrups (transverse rebar) primarily resist in a reinforced concrete beam?",
                "options": [
                    "Diagonal tensile stresses caused by shear forces",
                    "Direct compressive stresses",
                    "Longitudinal shrinkage cracking",
                    "Creep deflection"
                ],
                "answer": "Diagonal tensile stresses caused by shear forces",
                "explanation": "Stirrups cross diagonal shear cracks at near 90-degree angles, resisting diagonal tension induced by shear loads near supports."
            },
            {
                "question": "In limit state structural design, what is a 'load factor'?",
                "options": [
                    "A multiplier greater than 1 applied to service loads to account for uncertainties in load estimation",
                    "A reduction factor applied to material strength",
                    "The ratio of dead load to live load",
                    "The seismic response acceleration coefficient"
                ],
                "answer": "A multiplier greater than 1 applied to service loads to account for uncertainties in load estimation",
                "explanation": "Load factors (e.g. 1.2 Dead Load + 1.6 Live Load) amplify anticipated forces to establish an adequate margin of structural safety."
            }
        ]
    },

    # ── 6. Operations Research Analyst (Business Ops) ──
    {
        "career_title": "Operations Research Analyst",
        "skill_name": "Linear Programming & Optimization Modeling",
        "category": "Operations",
        "title": "Mathematical Optimization: Simplex Algorithm and Duality in Supply Chain Planning",
        "source_type": "article",
        "source_adapter": "structured_tutorial",
        "source_url": "https://scipy-lectures.org/advanced/optimizing/",
        "author_institution": "INFORMS / SciPy Optimization",
        "reading_time_minutes": 14,
        "difficulty_level": 3,
        "summary": "Formulation and algorithmic solution of linear programming problems. Definition of decision variables, linear objective functions, constraints, and interpreting dual shadow prices.",
        "takeaways": [
            "The Simplex algorithm traverses vertices of the convex feasible polytope.",
            "Dual variables measure the marginal value of relaxing a binding constraint.",
            "Non-binding constraints have a shadow price of zero."
        ],
        "concept_overview": "Operations research leverages mathematical programming to determine optimal allocations of scarce organizational resources. A linear program defines continuous decision variables bounded by linear inequalities representing physical or economic constraints. The fundamental theorem of linear programming proves that optimal solutions exist at extreme corner vertices of the feasible convex polytope, which the Simplex algorithm systematically evaluates.",
        "practice_scenario": "A nationwide logistics network must minimize transportation costs across 4 distribution hubs and 28 fulfillment centers. You formulate the network flow as a linear program in Python using SciPy/PuLP, establishing warehouse capacities and demand requirements. Solving the LP yields a routing schedule that reduces annual freight expenses by $2.3 million.",
        "quizzes": [
            {
                "question": "In linear programming duality, what does a non-zero shadow price for a capacity constraint indicate?",
                "options": [
                    "The constraint is currently binding and relaxing it increases the objective value",
                    "The algorithm has failed to find a feasible solution",
                    "The model has redundant decision variables that must be dropped",
                    "The objective function is unconstrained"
                ],
                "answer": "The constraint is currently binding and relaxing it increases the objective value",
                "explanation": "A shadow price represents the rate of improvement in the objective function per unit increase in the constraint's right-hand side. Non-zero shadow prices occur only on binding constraints."
            },
            {
                "question": "How does the Simplex algorithm locate the optimal solution to a linear program?",
                "options": [
                    "By random Monte Carlo sampling inside the feasible space",
                    "By traversing adjacent extreme vertices along the edges of the convex feasible polytope until no improving edge exists",
                    "By computing continuous gradients through neural networks",
                    "By inverting a non-linear Hessian matrix"
                ],
                "answer": "By traversing adjacent extreme vertices along the edges of the convex feasible polytope until no improving edge exists",
                "explanation": "Because optimal linear solutions occur at vertices, Simplex moves from vertex to adjacent vertex along edges that improve objective value."
            },
            {
                "question": "What mathematical property characterizes a 'binding constraint' at optimality?",
                "options": [
                    "The slack or surplus variable associated with the constraint is exactly zero",
                    "The constraint coefficients are all negative",
                    "The constraint was deleted from the model",
                    "The constraint is non-linear"
                ],
                "answer": "The slack or surplus variable associated with the constraint is exactly zero",
                "explanation": "A constraint is binding when it holds with strict equality at the optimal solution point, meaning zero slack remains."
            },
            {
                "question": "What is the relationship between the optimal objective value of a primal linear program and its dual linear program according to the Strong Duality Theorem?",
                "options": [
                    "Primal optimal value is always double the dual optimal value",
                    "Primal optimal value equals dual optimal value if a finite optimal solution exists",
                    "The dual is always unbounded whenever the primal is bounded",
                    "Dual optimal value is the negative reciprocal of primal value"
                ],
                "answer": "Primal optimal value equals dual optimal value if a finite optimal solution exists",
                "explanation": "The Strong Duality theorem guarantees that if either the primal or dual problem has an optimal solution, both have optimal solutions and their objective values are equal."
            },
            {
                "question": "In Mixed-Integer Linear Programming (MILP), which algorithmic technique is standardly used to solve for discrete integer variables?",
                "options": [
                    "Branch and Bound",
                    "Principal Component Analysis",
                    "K-Means Clustering",
                    "QuickSort"
                ],
                "answer": "Branch and Bound",
                "explanation": "Branch and Bound solves continuous LP relaxations and recursively branches on fractional integer variables to prune suboptimal search subtrees."
            }
        ]
    }
]

async def seed_curriculum():
    print("=== SEEDING VERIFIED LESSONS ACROSS 6 KEY CAREERS ===")
    emb_service = EmbeddingService()

    # Pre-fetch skills mapping from Supabase
    s_res = supabase_client.table("skills").select("id, name").execute()
    s_map = {s["name"].lower().strip(): s["id"] for s in (s_res.data or [])}

    # Pre-fetch careers mapping from Supabase
    c_res = supabase_client.table("careers").select("id, title").execute()
    c_map = {c["title"].lower().strip(): c["id"] for c in (c_res.data or [])}

    seeded_count = 0
    for seed in CURRICULUM_SEEDS:
        sk_name = seed["skill_name"]
        sk_id = s_map.get(sk_name.lower().strip())
        
        # If skill doesn't exist, create it
        if not sk_id:
            ins = supabase_client.table("skills").insert({
                "name": sk_name,
                "category": seed["category"]
            }).execute()
            if ins.data:
                sk_id = ins.data[0]["id"]
                s_map[sk_name.lower().strip()] = sk_id

        # Match career_id
        c_title = seed["career_title"]
        career_id = c_map.get(c_title.lower().strip())

        # Classify field
        field_meta = classify_career_field(c_title)

        # Generate dense semantic vector
        embed_text = f"Title: {seed['title']}. Skill: {sk_name}. Career: {c_title}. Summary: {seed['summary']}"
        embedding = await emb_service.get_embedding(embed_text)

        # Content metadata container
        content_dict = {
            "summary": seed["summary"],
            "summary_bullets": seed["takeaways"],
            "concept_overview": seed["concept_overview"],
            "practice_scenario": seed["practice_scenario"],
            "quizzes": seed["quizzes"],
            "author_institution": seed["author_institution"],
            "reading_time_minutes": seed["reading_time_minutes"],
            "difficulty_level": seed["difficulty_level"],
            "source_trust_score": 0.95,
            "source_type": seed["source_type"],
            "source_adapter": seed["source_adapter"],
            "source_url": seed["source_url"],
            "source_name": seed["author_institution"],
            "career_title": c_title,
            "career_id": career_id,
            "skill_name": sk_name,
            "field_id": field_meta["field_id"],
            "field_label": field_meta["label"],
            "review_status": "approved",
            "ingested_at": utc_now_iso(),
        }

        # Exact micro_content schema row
        lesson_row = {
            "career_id": career_id,
            "associated_skill_id": sk_id,
            "title": seed["title"],
            "summary": seed["summary"],
            "summary_bullets": seed["takeaways"],
            "source_url": seed["source_url"],
            "difficulty_level": seed["difficulty_level"],
            "source_trust_score": 0.95,
            "content": json.dumps(content_dict),
            "quizzes": seed["quizzes"],
            "embedding": embedding,
            "updated_at": utc_now_iso(),
        }

        # Check if lesson with this title already exists
        check = supabase_client.table("micro_content").select("id").eq("title", seed["title"]).execute()
        if check.data:
            supabase_client.table("micro_content").update(lesson_row).eq("id", check.data[0]["id"]).execute()
            print(f"Updated verified lesson: {seed['title'][:55]}... [Skill: {sk_name}]")
        else:
            lesson_row["created_at"] = utc_now_iso()
            supabase_client.table("micro_content").insert(lesson_row).execute()
            print(f"Inserted verified lesson: {seed['title'][:55]}... [Skill: {sk_name}]")
        seeded_count += 1

    print(f"\nSuccessfully seeded {seeded_count} verified curriculum lessons with 5-question checkpoints into Supabase micro_content!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_curriculum())
