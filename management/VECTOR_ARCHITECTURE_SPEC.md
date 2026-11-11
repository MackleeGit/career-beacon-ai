# Career Beacon — Unified Vector Architecture & Isomorphism Specification

This document defines the mathematical foundation, structural contracts, and implementation rules for all vector operations across the Career Beacon platform.

---

## 1. Mathematical Ground Rules (`all-MiniLM-L6-v2`)

1. **Dimensionality & Normalization**:
   - Embeddings are 384-dimensional dense vectors produced by FastEmbed ONNX (`all-MiniLM-L6-v2`).
   - Every embedding vector is $L_2$-normalized to unit length ($\|u\|_2 = 1.0$) upon creation.
   - For unit vectors, Cosine Similarity is equivalent to the Euclidean Dot Product:
     $$\text{sim}(u, v) = u \cdot v = \sum_{i=1}^{384} u_i v_i$$
   - Cosine Distance is $1 - \text{sim}(u, v)$, matching PostgreSQL pgvector's `<=>` operator.

2. **The Length Dilution Law**:
   - Due to Transformer Mean Pooling, adding extraneous tokens (e.g. database codes, personal anecdotes, numeric percentages) directly dilutes the attention weights of the critical semantic concepts.
   - **Contract**: All embedded texts (both query and target documents) must stay strictly within the **15–40 word window** of high-density semantic tokens.

3. **Hybrid Search Separation Principle**:
   - **Relational First**: Identifiers (`skill_id`, `career_id`), discrete categorical states (`primary_domain`, `difficulty`, `is_curated`), and availability must **NEVER** be matched via vector similarity. They must be resolved via SQL `WHERE` clauses and B-tree indexes.
   - **Vectors Second**: Vectors are reserved exclusively for fuzzy conceptual matching, vocabulary mismatch resolution, and nuanced intent ranking within a relationally pre-filtered set.

---

## 2. Complete Platform Vector Map

| Module | Target Table | Relational Filter (SQL) | Vector Column(s) | Stored Document Embedding Text | Query Vector Embedding Text | Fusion / Scoring Math |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Career Onboarding** | `careers` | `is_curated = TRUE` | `title_vector` (384)<br>`skills_vector` (384) | **Title**: `"{title}. Role: {description}"`<br>**Skills**: `"Key technical competencies: {top_8_skills}"` | Cleaned user search string | $\max(s_{\text{title}}, s_{\text{skills}})$ |
| **2. Skill Deduplication** | `skills` | Optional `category` | `skill_vector` (384) | `"{name} in {category}"` | Candidate custom / AI skill string | $\text{sim}(q, v_{\text{skill}}) > 0.88$ $\to$ reuse ID |
| **3. Micro-Learning Feed** | `micro_content` | `skill_id = target_skill`<br>`difficulty = target_diff` | `embedding` (384) | `"{title}. Focus: {summary_bullets}"` | `"Objective: {skill_name} practical concepts."` | Cosine similarity within filtered skill pool |
| **4. Mentor Matching** | `mentors` | `primary_domain = ...`<br>`mentor_skills.skill_id = ...` | `specialties_vector` (384) | `"Technical specialties: {concrete_technical_topics}"` | Mentee technical problem / goal text | Cosine similarity within filtered mentor pool |
| **5. Mentor Q&A Board** | `mentor_qa` | `skill_id = ...` | `embedding` (384) | `"{question_text}"` | Student query or failed quiz question | Cosine similarity (Question-to-Question) |

---

## 3. Detailed Operational Contracts

### A. Career Discovery (Learner Onboarding)
- **Problem Solved**: Learner queries describe either a role title (*"Machine Learning Engineer"*) OR a technology stack (*"React, Node.js, and MongoDB"*).
- **Dual Vector Architecture**:
  - `title_vector`: Captures functional occupational identity.
  - `skills_vector`: Captures technical tooling and stack vocabulary.
- **SQL Execution**:
  ```sql
  SELECT 
      id, title, description,
      GREATEST(
          1 - (title_vector <=> query_embedding),
          1 - (skills_vector <=> query_embedding)
      ) AS similarity
  FROM public.careers
  WHERE is_curated = TRUE
  ORDER BY similarity DESC
  LIMIT 8;
  ```

### B. Micro-Learning Retrieval (`recommendation_service.py`)
- **Anti-Pattern Removed**: Removed 200-word composite query containing O\*NET codes, ESCO URIs, and multiple percentage weights.
- **Isomorphic Schema**:
  - Filter: `WHERE skill_id = user_frontier_skill_id AND difficulty = current_tier`
  - Re-rank: Lesson objective vs. Lesson summary bullets.

### C. Mentor Marketplace (`mentor.py`)
- **Anti-Pattern Removed**: Removed freeform biographical text (coffee, hobbies, personal stories) from the embedding vector.
- **Isomorphic Schema**:
  - Filter: `primary_domain` + `mentor_skills` junction.
  - Re-rank: Technical specialties list vs. mentee technical roadblock statement.

### D. Skill Deduplication
- When users or LLMs propose custom skills during onboarding, compute cosine similarity against canonical skills.
- If similarity $\ge 0.88$, map to existing canonical `skill_id`. Prevents database pollution from minor phrasing variations (e.g., "Postgres" vs. "PostgreSQL").

