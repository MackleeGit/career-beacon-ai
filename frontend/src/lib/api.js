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
 * @param {string} userId
 * @param {string} careerId
 * @param {{ skill_id: string, proficiency: number }[]} skills
 */
export async function saveSkills(userId, careerId, skills) {
  return request('/api/onboarding/save-skills', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, career_id: careerId, skills }),
  });
}

/**
 * Fetch onboarding status for a user.
 * Returns { onboarding_complete: bool, career, skills }
 */
export async function getOnboardingStatus(userId) {
  return request(`/api/onboarding/status/${userId}`);
}
