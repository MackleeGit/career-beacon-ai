# Admin Governance, Taxonomy Distillation & Skill Lifecycle Specification
**Project:** Career Beacon — AI-Powered Micro-Learning & Mentorship Marketplace  
**Module Reference:** Module 2 (Onboarding) & Module 6 (Admin & Lifecycle Governance)  
**Author:** Gitonga Macklee Nderitu (ID: 168000)  
**Supervisor:** Dr. Tiberias Tabulu  

---

## 1. Autonomous Consensus & Human-by-Exception Governance

### Problem Statement
With 840 canonical occupations, requiring a human platform administrator to manually inspect, edit, and approve thousands of individual skill mappings is operationally intractable and violates scalable system design principles.

### The Governance Protocol
```
┌──────────────────────────────────────────────┐
│  Raw O*NET Duties + Raw ESCO Task Statements │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│       LLM Competency Distillation            │
│   (Clusters into 8-12 Actionable Pillars)    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│      Dual-Source Grounding Check             │
│ Cosine Similarity (all-MiniLM-L6-v2) >= 0.80 │
└───────────┬──────────────────────┬───────────┘
            │ YES                  │ NO / AMBIGUOUS
            ▼                      ▼
┌───────────────────────┐ ┌───────────────────────────┐
│  AUTO-PROMOTED        │ │  FLAGGED FOR REVIEW       │
│ review_status:        │ │ review_status:            │
│ 'auto_verified'       │ │ 'in_review'               │
│ (Active in Catalogue) │ │ (Requires Admin Decision) │
└───────────────────────┘ └───────────────────────────┘
```

1. **Dual-Source Grounding Heuristic**:
   - The LLM Distiller extracts 8–12 structured competency pillars from the raw text duties in O*NET and ESCO.
   - Each synthesized pillar is embedded using `all-MiniLM-L6-v2`.
   - A cosine similarity check is performed against the underlying authoritative task paragraphs.
   - If similarity $\ge 0.80$, the competency is verified as factually grounded in official labour data and auto-promoted to `auto_verified` (active in the live catalogue).
2. **Human-by-Exception Triggers**:
   - High-liability regulated professions (e.g., Surgery, Civil Engineering Structural Analysis, Legal Practice).
   - Low confidence matches ($< 0.80$).
   - User feedback flags: A learner or mentor clicks `"Report Inaccurate / Irrelevant Skill"`.

---

## 2. Soft Deprecation & Forward Aliasing Schema

### Problem Statement
If an administrator deletes or renames a redundant or poorly phrased skill (e.g. replacing ESCO's *"use markup languages"* with *"HTML5 & Semantic Markup"*), hard deletion (`DELETE FROM skills`) causes:
1. Catastrophic cascade deletion of learners' calibrated proficiencies in `user_skills`.
2. Orphaned quiz verifications and micro-learning progress in `user_learning_history`.
3. Vector distortion in the recommendation engine.

### The Forward Aliasing Pattern
```sql
ALTER TABLE public.skills
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS merged_into_id UUID REFERENCES public.skills(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS deprecated_at TIMESTAMPTZ;
```

```
[Learner Profile: Alice]
├── Skill: "use markup languages" (ID: aaa-111)
│   └── Proficiency: 80% (Advanced)
│   └── Verified: true
│
[Admin Action]
└── Skill "use markup languages" (ID: aaa-111) set to:
    ├── is_active: false
    └── merged_into_id: "HTML5" (ID: bbb-222)
│
[Recommendation Engine Lookup]
└── Resolves "aaa-111" -> Follows alias to "bbb-222" ("HTML5")
    └── Alice retains 80% Advanced rating in HTML5 seamlessly.
```

### Invariants:
1. **Zero Data Loss:** `user_skills` rows are immutable historical records of learner calibration. They are never hard-deleted during administrative catalogue refinement.
2. **Transparent Resolution:** The recommendation engine (`Module 3`) and diagnostic quiz engine (`Module 5`) resolve `COALESCE(s.merged_into_id, s.id)` dynamically.
3. **Audit Trail:** Every deprecation records `deprecated_at` and the administrator's ID for accreditation transparency.

