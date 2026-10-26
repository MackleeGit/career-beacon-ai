// src/lib/api.js
// Thin wrapper around fetch for the FastAPI AI Engine backend.
// Automatically injects the Supabase JWT as a Bearer token.

import { supabase } from './SupabaseClient';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  // Retrieve current session token (if user is logged in)
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
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
  const isPending = Boolean(career._pending || !career.id);

  // Unified atomic contract: every skill carries its own name, category, and proficiency
  const unifiedSkills = allSkills.map((s) => ({
    skill_id: s.id && !s.id.startsWith('temp-') && s.id.length === 36 ? s.id : null,
    name: s.name.trim(),
    category: s.category || 'General',
    proficiency: proficiencyMap[s.id] ?? 20,
    importance: s.importance || null,
  }));

  return request('/api/onboarding/save-skills', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      career_id: career.id || null,
      career_title: career.title,
      career_description: career.description || '',
      is_custom: isPending,
      skills: unifiedSkills,
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


/** Record that the learner opened a recommended source. */
export async function recordContentOpen(userId, contentId) {
  return request('/api/recommendations/activity/open', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, content_id: contentId }),
  });
}
