// src/lib/api.js
// Thin wrapper around fetch for the FastAPI AI Engine backend.
// Automatically injects the Supabase JWT as a Bearer token.

import { supabase } from './SupabaseClient';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  // Check online status immediately before attempting request
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    throw new Error('You appear to be offline. Please check your internet connection.');
  }

  // Retrieve current session token (if user is logged in)
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  // Guard against hanging requests when connection drops mid-flight
  const timeoutMs = options.timeoutMs || 75000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers,
      signal: controller.signal,
      ...options,
    });
  } catch (err) {
    if (options.signal?.aborted) {
      const abortErr = new Error('Request aborted');
      abortErr.name = 'AbortError';
      throw abortErr;
    }
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. The server took too long to respond or your connection was interrupted.');
    }
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      throw new Error('Network connection lost. Please check your internet connection.');
    }
    throw new Error('Unable to reach the backend service. Please verify your connection.');
  } finally {
    clearTimeout(timeoutId);
  }

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
export async function searchCareer(query, isStructuredAi = false, alwaysShowCandidates = true) {
  return request('/api/onboarding/career-search', {
    method: 'POST',
    body: JSON.stringify({
      career_query: query,
      is_structured_ai: isStructuredAi,
      always_show_candidates: alwaysShowCandidates,
    }),
  });
}

/**
 * Fetch a specific career and its taxonomy skills directly by ID.
 */
export async function getCareerById(careerId) {
  return request(`/api/onboarding/career/${careerId}`);
}

/**
 * Save the user's career and skill proficiency graph.
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
 */
export async function getRecommendations(userId, limit = 10, offset = 0, excludeIds = [], options = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  for (const id of excludeIds || []) {
    if (id) params.append('exclude_ids', id);
  }
  return request(`/api/recommendations/${userId}?${params.toString()}`, { timeoutMs: 75000, ...options });
}

/**
 * Submit quiz answers and update skill graph proficiency.
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

/**
 * Retrieve today's 3-lesson Daily Focus Drop with streak metadata.
 */
export async function getCurrentDailyDrop(options = {}) {
  return request('/api/recommendations/daily-drop/current', { timeoutMs: 75000, ...options });
}

/**
 * 1-Shot Daily Re-Roll: shuffle sprint to secondary priority deficit.
 */
export async function rerollDailyDrop() {
  return request('/api/recommendations/daily-drop/reroll', { method: 'POST', timeoutMs: 30000 });
}

// ===========================================================================
// Module 4: Mentorship Ecosystem API Helpers
// ===========================================================================

export async function submitMentorOnboarding(payload) {
  return request('/api/mentor/onboarding', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function searchMentorCareers(query = '') {
  const cleanQ = query.trim();
  if (!cleanQ || cleanQ.length < 2) {
    return { direct_matches: [], vector_matches: [] };
  }

  // 1. Attempt the FastAPI backend endpoint first
  try {
    const q = encodeURIComponent(cleanQ);
    const res = await request(`/api/mentor/career-search?q=${q}`);
    if (res && (res.direct_matches || res.vector_matches)) {
      return res;
    }
  } catch (err) {
    console.warn('[searchMentorCareers] Backend endpoint unavailable, executing direct Supabase lookup:', err);
  }

  // 2. High-reliability direct Supabase database fallback
  try {
    const { data: directMatches, error } = await supabase
      .from('careers')
      .select('id, title, description, source_origin')
      .ilike('title', `%${cleanQ}%`)
      .limit(8);

    if (error) throw error;

    return {
      direct_matches: directMatches || [],
      vector_matches: [],
    };
  } catch (dbErr) {
    console.error('[searchMentorCareers] Direct Supabase fallback error:', dbErr);
    return { direct_matches: [], vector_matches: [] };
  }
}

export async function fetchMentorSkills(query = '', limit = 30) {
  const q = encodeURIComponent(query.trim());
  return request(`/api/mentor/skills?q=${q}&limit=${limit}`);
}

export async function getMyMentorProfile() {
  return request('/api/mentor/profile/me');
}

export async function updateMyMentorProfile(payload) {
  return request('/api/mentor/profile/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function getMentorMatches(includeBelowThreshold = false) {
  return request(`/api/mentor/matches?include_below_threshold=${includeBelowThreshold}`);
}

export async function getMentorshipConnections(role = 'learner') {
  return request(`/api/mentor/connections?role=${encodeURIComponent(role)}`);
}

export async function requestMentorConnection(mentorId, goalNote = '', autoAcceptDemo = false) {
  return request('/api/mentor/connections/request', {
    method: 'POST',
    body: JSON.stringify({
      mentor_id: mentorId,
      goal_note: goalNote,
      auto_accept_demo: autoAcceptDemo,
    }),
  });
}

export async function respondToConnectionRequest(connectionId, action) {
  return request(`/api/mentor/connections/${encodeURIComponent(connectionId)}/respond`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

export async function getConnectionMessages(connectionId) {
  return request(`/api/mentor/messages/${encodeURIComponent(connectionId)}`);
}

export async function sendConnectionMessage(connectionId, text, senderRole = 'learner') {
  return request('/api/mentor/messages', {
    method: 'POST',
    body: JSON.stringify({
      connection_id: connectionId,
      text,
      sender_role: senderRole,
    }),
  });
}

export async function getMentorPulseFeed(postType = '') {
  const qs = postType ? `?post_type=${encodeURIComponent(postType)}` : '';
  return request(`/api/mentor/pulse${qs}`);
}

export async function publishMentorPulsePost(payload) {
  return request('/api/mentor/pulse', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function toggleLikePulsePost(postId) {
  return request(`/api/mentor/pulse/${encodeURIComponent(postId)}/like`, {
    method: 'POST',
  });
}

export async function getMentorshipQuestions({ q = '', skillTag = '', forMentor = false } = {}) {
  const params = new URLSearchParams();
  if (q && q.trim()) params.set('q', q.trim());
  if (skillTag && skillTag.trim()) params.set('skill_tag', skillTag.trim());
  if (forMentor) params.set('for_mentor', 'true');
  return request(`/api/mentor/questions?${params.toString()}`);
}

export async function askMentorshipQuestion(payload) {
  return request('/api/mentor/questions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function answerMentorshipQuestion(questionId, body) {
  return request(`/api/mentor/questions/${encodeURIComponent(questionId)}/answer`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });
}

export async function upvoteMentorshipAnswer(questionId, answerId) {
  return request(
    `/api/mentor/questions/${encodeURIComponent(questionId)}/answers/${encodeURIComponent(answerId)}/upvote`,
    { method: 'POST' }
  );
}

export async function getMentorAvailableSlots(mentorId, daysAhead = 10) {
  return request(`/api/mentor/${encodeURIComponent(mentorId)}/slots?days_ahead=${daysAhead}`);
}

export async function bookMentorshipSession(payload) {
  return request('/api/mentor/sessions/book', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getMentorshipSessions(role = 'learner') {
  return request(`/api/mentor/sessions?role=${encodeURIComponent(role)}`);
}

export async function cancelMentorshipSession(sessionId) {
  return request(`/api/mentor/sessions/${encodeURIComponent(sessionId)}/cancel`, {
    method: 'POST',
  });
}

export async function completeMentorshipSession(sessionId, endorseSkillName = null, feedbackNote = '') {
  return request(`/api/mentor/sessions/${encodeURIComponent(sessionId)}/complete`, {
    method: 'POST',
    body: JSON.stringify({
      endorse_skill_name: endorseSkillName,
      feedback_note: feedbackNote,
    }),
  });
}

export function getSessionIcsDownloadUrl(sessionId) {
  return `${BASE_URL}/api/mentor/sessions/${encodeURIComponent(sessionId)}/calendar.ics`;
}


export async function resetLearnerAccount() {
  return request('/api/onboarding/reset', { method: 'POST' });
}

export async function resetMentorAccount() {
  return request('/api/mentor/reset', { method: 'POST' });
}

// ===========================================================================
// Admin Command Center API Helpers
// ===========================================================================

export async function getAdminStats() {
  return request('/api/admin/stats');
}

export async function getAdminPendingCareers() {
  return request('/api/admin/careers/pending');
}

export async function reviewAdminCareer(careerId, action, customTitle = null) {
  return request(`/api/admin/careers/${encodeURIComponent(careerId)}/review`, {
    method: 'POST',
    body: JSON.stringify({ action, custom_title: customTitle }),
  });
}

export async function getAdminMentors() {
  return request('/api/admin/mentors');
}

export async function verifyAdminMentor(mentorId, verified) {
  return request(`/api/admin/mentors/${encodeURIComponent(mentorId)}/verify`, {
    method: 'POST',
    body: JSON.stringify({ verified }),
  });
}

export async function getAdminFlaggedContent() {
  return request('/api/admin/moderation/flagged');
}

export async function takeAdminModerationAction(action, itemId, itemType) {
  return request('/api/admin/moderation/action', {
    method: 'POST',
    body: JSON.stringify({ action, item_id: itemId, item_type: itemType }),
  });
}

export async function submitLessonFeedback(lessonId, feedback, lessonTitle = null, reason = null) {
  return request('/api/recommendations/feedback', {
    method: 'POST',
    body: JSON.stringify({
      lesson_id: lessonId,
      feedback,
      lesson_title: lessonTitle,
      reason,
    }),
  });
}

export async function flagContentItem(itemType, itemId, contentSnippet, targetContext = 'Community Content', reason = 'Reported by user') {
  return request('/api/admin/moderation/flag', {
    method: 'POST',
    body: JSON.stringify({
      item_type: itemType,
      item_id: itemId,
      content_snippet: contentSnippet,
      target_context: targetContext,
      reason,
    }),
  });
}
