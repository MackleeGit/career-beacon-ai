// src/lib/api.js
// Thin wrapper around fetch for the FastAPI AI Engine backend.

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || JSON.stringify(err);
    } catch { /* ignore parse errors */ }
    throw new Error(detail);
  }

  return res.json();
}

/**
 * Search for a career by natural language query.
 * Returns { status: 'matched'|'generated', career, skills }
 */
export async function searchCareer(query) {
  return request('/api/onboarding/career-search', {
    method: 'POST',
    body: JSON.stringify({ career_query: query }),
  });
}

/**
 * Save the user's career + skill proficiency graph.
 * Handles two cases:
 *  - Matched career: pass careerId + skills with real UUIDs.
 *  - Pending (AI-generated) career: pass pendingCareer + pendingSkills + ordered proficiency list.
 *
 * @param {string} userId
 * @param {{ id: string|null, title: string, description: string, _pending?: boolean }} career
 * @param {{ id: string, name: string, category: string }[]} allSkills  - full skill objects
 * @param {{ [skillId: string]: number }} proficiencyMap - skillId → proficiency value
 */
export async function saveSkills(userId, career, allSkills, proficiencyMap) {
  const isPending = career._pending || !career.id;

  if (isPending) {
    // Career hasn't been saved to DB yet — send everything for the backend to persist
    return request('/api/onboarding/save-skills', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        pending_career_title: career.title,
        pending_career_description: career.description,
        pending_skills: allSkills.map((s) => ({ name: s.name, category: s.category })),
        // Skills ordered to match pending_skills — backend uses index position
        skills: allSkills.map((s) => ({ skill_id: s.id, proficiency: proficiencyMap[s.id] ?? 20 })),
      }),
    });
  }

  // Matched career — skills already have real DB UUIDs
  return request('/api/onboarding/save-skills', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      career_id: career.id,
      skills: allSkills.map((s) => ({ skill_id: s.id, proficiency: proficiencyMap[s.id] ?? 20 })),
    }),
  });
}

/**
 * Fetch onboarding status for a user.
 * Returns { onboarding_complete: bool, career, skills }
 */
export async function getOnboardingStatus(userId) {
  return request(`/api/onboarding/status/${userId}`);
}
