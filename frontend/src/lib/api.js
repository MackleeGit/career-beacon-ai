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
 * Save the user's career and skill proficiency graph.
 * Handles two cases:
 *  1. Matched career: pass careerId and skills with real UUIDs.
 *  2. Pending (AI-generated) career: pass pendingCareer, pendingSkills, and proficiency list.
 *
 * @param {string} userId
 * @param {{ id: string|null, title: string, description: string, _pending?: boolean }} career
 * @param {{ id: string, name: string, category: string }[]} allSkills - full skill objects
 * @param {{ [skillId: string]: number }} proficiencyMap - skillId to proficiency value
 */
export async function saveSkills(userId, career, allSkills, proficiencyMap) {
  const isPending = career._pending || !career.id;

  if (isPending) {
    // Career has not been saved to DB yet; send payload for backend persistence
    return request('/api/onboarding/save-skills', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        pending_career_title: career.title,
        pending_career_description: career.description,
        pending_skills: allSkills.map((s) => ({ name: s.name, category: s.category })),
        // Skills ordered to match pending_skills; backend uses index position
        skills: allSkills.map((s) => ({ skill_id: s.id, proficiency: proficiencyMap[s.id] ?? 20 })),
      }),
    });
  }

  // Matched career: skills already have real DB UUIDs
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

/**
 * Fetch personalized micro-learning recommendations (Two-Stage Hybrid).
 * @param {string} userId
 * @param {number} limit
 */
export async function getRecommendations(userId, limit = 5) {
  return request(`/api/recommendations/${userId}?limit=${limit}`);
}

/**
 * Submit quiz answers and update skill graph proficiency.
 * @param {string} userId
 * @param {string} lessonId
 * @param {{ [questionIdx: number|string]: string }} answers
 */
export async function submitQuiz(userId, lessonId, answers) {
  return request('/api/recommendations/submit-quiz', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      lesson_id: lessonId,
      answers,
    }),
  });
}

