// src/pages/LearnerMentorship.jsx
import { useState, useEffect } from 'react';
import {
  getMentorMatches,
  requestMentorConnection,
  getMentorshipConnections,
  getConnectionMessages,
  sendConnectionMessage,
  getMentorPulseFeed,
  toggleLikePulsePost,
  getMentorshipQuestions,
  askMentorshipQuestion,
  upvoteMentorshipAnswer,
  getMentorAvailableSlots,
  bookMentorshipSession,
  getMentorshipSessions,
  cancelMentorshipSession,
  getSessionIcsDownloadUrl,
} from '../lib/api';
import Toast from '../components/Toast';

export default function LearnerMentorship({
  user,
  career,
  skills = [],
  initialSubTab = 'matches',
  prefillQuestion = null,
  onClearPrefillQuestion,
}) {
  const [subTab, setSubTab] = useState(initialSubTab); // 'matches' | 'pulse' | 'qa' | 'sessions'
  const [matchData, setMatchData] = useState({ matches: [], filtered_out_by_anti_desperation: 0 });
  const [connections, setConnections] = useState([]);
  const [pulsePosts, setPulsePosts] = useState([]);
  const [pulseFilter, setPulseFilter] = useState('');
  const [questions, setQuestions] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);

  // Connection modal state
  const [connectingMentor, setConnectingMentor] = useState(null);
  const [goalNote, setGoalNote] = useState('');
  const [autoAcceptDemo, setAutoAcceptDemo] = useState(true);
  const [submittingConn, setSubmittingConn] = useState(false);

  // Q&A search & ask state
  const [qaSearch, setQaSearch] = useState('');
  const [qaSkillFilter, setQaSkillFilter] = useState('');
  const [showAskModal, setShowAskModal] = useState(false);
  const [qTitle, setQTitle] = useState('');
  const [qBody, setQBody] = useState('');
  const [qSkillTag, setQSkillTag] = useState(skills[0]?.name || 'General Career');
  const [qSourceLesson, setQSourceLesson] = useState('');
  const [submittingQ, setSubmittingQ] = useState(false);

  // DMs & Session Booking state
  const [selectedConnId, setSelectedConnId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [msgInput, setMsgInput] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);

  const [availableSlots, setAvailableSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [selectedSlotIso, setSelectedSlotIso] = useState('');
  const [sessionTopic, setSessionTopic] = useState('1-on-1 Skill Gap & Architecture Review');
  const [sessionFocusSkill, setSessionFocusSkill] = useState(skills[0]?.name || '');
  const [sessionNotes, setSessionNotes] = useState('');
  const [bookingSession, setBookingSession] = useState(false);

  // Handle prefillQuestion from Module 3 failed quiz
  useEffect(() => {
    if (prefillQuestion) {
      setSubTab('qa');
      setShowAskModal(true);
      setQTitle(prefillQuestion.title || '');
      setQBody(prefillQuestion.body || '');
      setQSkillTag(prefillQuestion.skill_tag || skills[0]?.name || 'General Career');
      setQSourceLesson(prefillQuestion.source_lesson_title || '');
      if (onClearPrefillQuestion) onClearPrefillQuestion();
    }
  }, [prefillQuestion]);

  const loadEcosystem = async () => {
    setLoading(true);
    try {
      const [mRes, cRes, pRes, qRes, sRes] = await Promise.all([
        getMentorMatches(false),
        getMentorshipConnections('learner'),
        getMentorPulseFeed(),
        getMentorshipQuestions(),
        getMentorshipSessions('learner'),
      ]);
      setMatchData(mRes);
      const conns = cRes.connections || [];
      setConnections(conns);
      const accepted = conns.filter((c) => c.status === 'accepted');
      if (accepted.length > 0 && !selectedConnId) {
        setSelectedConnId(accepted[0].id);
      }
      setPulsePosts(pRes.posts || []);
      setQuestions(qRes.questions || []);
      setSessions(sRes.sessions || []);
    } catch (err) {
      console.error('Failed to load learner mentorship hub:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEcosystem();
  }, []);

  // Load DMs + Available Slots whenever selectedConnId changes
  const activeConnection = connections.find((c) => c.id === selectedConnId);

  useEffect(() => {
    if (!selectedConnId || !activeConnection) return;
    getConnectionMessages(selectedConnId)
      .then((res) => setMessages(res.messages || []))
      .catch((err) => console.error('Failed to load messages:', err));

    if (activeConnection.mentor_id) {
      setSlotsLoading(true);
      getMentorAvailableSlots(activeConnection.mentor_id, 10)
        .then((res) => {
          const slots = res.slots || [];
          setAvailableSlots(slots);
          if (slots.length > 0) setSelectedSlotIso(slots[0].slot_start_iso);
        })
        .catch((err) => console.error('Failed to load slots:', err))
        .finally(() => setSlotsLoading(false));
    }
  }, [selectedConnId, activeConnection?.mentor_id]);

  const handleSendConnectionRequest = async (e) => {
    e.preventDefault();
    if (!connectingMentor) return;
    setSubmittingConn(true);
    try {
      const res = await requestMentorConnection(
        connectingMentor.mentor_id,
        goalNote.trim() || `Seeking guidance on ${career?.title || 'my career roadmap'}.`,
        autoAcceptDemo
      );
      setConnectingMentor(null);
      setGoalNote('');
      await loadEcosystem();
      if (res.connection?.status === 'accepted') {
        setSelectedConnId(res.connection.id);
        setToastMessage(
          `Connected with ${connectingMentor.full_name}! Direct Messaging & 1-on-1 Calendar Booking are now unlocked.`
        );
      } else {
        setToastMessage(`Connection request sent to ${connectingMentor.full_name}!`);
      }
    } catch (err) {
      setToastMessage(err.message || 'Failed to send connection request.');
    } finally {
      setSubmittingConn(false);
    }
  };

  const handleToggleLike = async (postId) => {
    try {
      const res = await toggleLikePulsePost(postId);
      setPulsePosts((prev) => prev.map((p) => (p.id === postId ? res.post : p)));
    } catch (err) {
      console.error('Like error:', err);
    }
  };

  const handleSearchQuestions = async (e) => {
    if (e) e.preventDefault();
    try {
      const res = await getMentorshipQuestions({ q: qaSearch, skillTag: qaSkillFilter });
      setQuestions(res.questions || []);
    } catch (err) {
      console.error('Search Q&A error:', err);
    }
  };

  const handleAskQuestion = async (e) => {
    e.preventDefault();
    if (!qTitle.trim() || !qBody.trim()) return;
    setSubmittingQ(true);
    try {
      await askMentorshipQuestion({
        title: qTitle.trim(),
        body: qBody.trim(),
        skill_tag: qSkillTag,
        career_title: career?.title || 'Learner',
        source_lesson_title: qSourceLesson || null,
      });
      setShowAskModal(false);
      setQTitle('');
      setQBody('');
      setQSourceLesson('');
      setToastMessage('Your question has been routed to domain-matched mentors and added to the Q&A Hub!');
      const res = await getMentorshipQuestions();
      setQuestions(res.questions || []);
    } catch (err) {
      setToastMessage(err.message || 'Failed to submit question.');
    } finally {
      setSubmittingQ(false);
    }
  };

  const handleUpvoteAnswer = async (questionId, answerId) => {
    try {
      await upvoteMentorshipAnswer(questionId, answerId);
      const res = await getMentorshipQuestions({ q: qaSearch, skillTag: qaSkillFilter });
      setQuestions(res.questions || []);
    } catch (err) {
      console.error('Upvote error:', err);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!selectedConnId || !msgInput.trim()) return;
    setSendingMsg(true);
    try {
      const res = await sendConnectionMessage(selectedConnId, msgInput.trim(), 'learner');
      setMessages((prev) => [...prev, res.message]);
      setMsgInput('');
    } catch (err) {
      setToastMessage(err.message || 'Failed to send message.');
    } finally {
      setSendingMsg(false);
    }
  };

  const handleBookSession = async (e) => {
    e.preventDefault();
    if (!activeConnection?.mentor_id || !selectedSlotIso) return;
    setBookingSession(true);
    try {
      const res = await bookMentorshipSession({
        mentor_id: activeConnection.mentor_id,
        slot_start_iso: selectedSlotIso,
        topic: sessionTopic.trim() || '1-on-1 Career Mentorship Session',
        focus_skill: sessionFocusSkill || null,
        notes: sessionNotes.trim(),
      });
      setToastMessage(
        `Session confirmed for ${res.session.display_label}! Meeting room & calendar invites generated.`
      );
      setSessionNotes('');
      // Refresh sessions and available slots (slot is now locked against double-booking)
      const [sRes, slotsRes] = await Promise.all([
        getMentorshipSessions('learner'),
        getMentorAvailableSlots(activeConnection.mentor_id, 10),
      ]);
      setSessions(sRes.sessions || []);
      const newSlots = slotsRes.slots || [];
      setAvailableSlots(newSlots);
      setSelectedSlotIso(newSlots[0]?.slot_start_iso || '');
    } catch (err) {
      setToastMessage(err.message || 'Failed to book session.');
    } finally {
      setBookingSession(false);
    }
  };

  const handleCancelSession = async (sessionId) => {
    try {
      await cancelMentorshipSession(sessionId);
      setToastMessage('Session cancelled and time slot released.');
      const sRes = await getMentorshipSessions('learner');
      setSessions(sRes.sessions || []);
      if (activeConnection?.mentor_id) {
        const slotsRes = await getMentorAvailableSlots(activeConnection.mentor_id, 10);
        setAvailableSlots(slotsRes.slots || []);
      }
    } catch (err) {
      setToastMessage(err.message || 'Failed to cancel session.');
    }
  };

  const acceptedConnections = connections.filter((c) => c.status === 'accepted');
  const displayedPulse = pulseFilter
    ? pulsePosts.filter((p) => p.post_type === pulseFilter)
    : pulsePosts;

  return (
    <div>
      {/* Sub-navigation bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '10px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className={`btn btn--sm ${subTab === 'matches' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSubTab('matches')}
          >
            🧭 Matched Mentors ({matchData.matches?.length || 0})
          </button>
          <button
            type="button"
            className={`btn btn--sm ${subTab === 'pulse' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSubTab('pulse')}
          >
            📢 Mentor Pulse Feed ({pulsePosts.length})
          </button>
          <button
            type="button"
            className={`btn btn--sm ${subTab === 'qa' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSubTab('qa')}
          >
            💡 Q&amp;A Knowledge Base ({questions.length})
          </button>
          <button
            type="button"
            className={`btn btn--sm ${subTab === 'sessions' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setSubTab('sessions')}
          >
            💬 Messages &amp; 1:1 Booking ({acceptedConnections.length})
          </button>
        </div>

        <button
          type="button"
          className="btn btn--ghost btn--sm"
          style={{ borderColor: 'var(--teal)', color: 'var(--teal)' }}
          onClick={() => {
            setSubTab('qa');
            setShowAskModal(true);
          }}
        >
          + Ask a Mentor Question
        </button>
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px' }}>
          <div className="spinner spinner--lg" style={{ margin: '0 auto 12px' }} />
          <p style={{ color: 'var(--text-muted)' }}>Running 2-Stage Anti-Desperation Mentor Matcher...</p>
        </div>
      ) : (
        <>
          {/* ================================================================= */}
          {/* SUB-TAB 1: MATCHED MENTORS & ANTI-DESPERATION GATE                */}
          {/* ================================================================= */}
          {subTab === 'matches' && (
            <div>
              {/* Anti-Desperation Architecture Callout */}
              <div
                className="card"
                style={{
                  marginBottom: '20px',
                  padding: '16px 20px',
                  background: 'linear-gradient(135deg, hsla(174, 72%, 56%, 0.1), hsla(252, 85%, 68%, 0.08))',
                  borderColor: 'hsla(174, 72%, 56%, 0.3)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--teal)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      🛡️ 2-Stage Anti-Desperation Semantic Matcher
                    </div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                      Target Career: <strong>{career?.title || matchData.learner_career}</strong> · Filtered out{' '}
                      <strong>{matchData.filtered_out_by_anti_desperation || 0}</strong> unaligned mentors to prevent irrelevant matches.
                    </div>
                  </div>
                  <span className="badge badge--accent">
                    Min Threshold: {Math.round((matchData.anti_desperation_threshold || 0.45) * 100)}%
                  </span>
                </div>
              </div>

              {matchData.matches?.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
                  <h3 style={{ marginBottom: '8px' }}>No Direct 1-on-1 Mentor Matches Above Threshold</h3>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '560px', margin: '0 auto 20px', fontSize: '0.92rem' }}>
                    {matchData.zero_match_reason ||
                      'Our Anti-Desperation Gate blocked low-relevance matches so you are never paired with an unaligned mentor.'}
                  </p>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => {
                      setSubTab('qa');
                      setShowAskModal(true);
                    }}
                  >
                    💡 Post a Question to the Community Q&amp;A Board Instead →
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
                  {matchData.matches.map((mentor) => {
                    const connStatus = mentor.connection_status;
                    return (
                      <div
                        key={mentor.mentor_id}
                        className="card"
                        style={{
                          padding: '22px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '14px',
                        }}
                      >
                        <div>
                          {/* Top Badges */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
                            <span
                              style={{
                                padding: '4px 10px',
                                borderRadius: '999px',
                                fontSize: '0.74rem',
                                fontWeight: 700,
                                background:
                                  mentor.match_tier === 'strong'
                                    ? 'hsla(174, 72%, 56%, 0.18)'
                                    : 'hsla(252, 85%, 68%, 0.18)',
                                color: mentor.match_tier === 'strong' ? 'var(--teal)' : 'var(--accent-light)',
                                border: '1px solid',
                                borderColor:
                                  mentor.match_tier === 'strong'
                                    ? 'hsla(174, 72%, 56%, 0.35)'
                                    : 'hsla(252, 85%, 68%, 0.35)',
                              }}
                            >
                              {mentor.match_badge} · {mentor.match_percent}% Match
                            </span>
                            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                              ★ {mentor.avg_rating || 4.9} ({mentor.verified_sessions_count || 12} sessions)
                            </span>
                          </div>

                          <h3 style={{ fontSize: '1.1rem', marginBottom: '4px' }}>{mentor.full_name}</h3>
                          <div style={{ fontSize: '0.84rem', color: 'var(--teal)', fontWeight: 600, marginBottom: '8px' }}>
                            {mentor.headline}
                          </div>
                          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '12px' }}>
                            {mentor.bio}
                          </p>

                          {/* Explainability Box: Why We Matched You */}
                          <div
                            style={{
                              padding: '10px 12px',
                              background: 'var(--bg-elevated)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-sm)',
                              marginBottom: '12px',
                            }}
                          >
                            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                              Why We Matched You
                            </div>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                              {mentor.match_explanation}
                            </div>
                            {mentor.shared_gap_skills?.length > 0 && (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                                {mentor.shared_gap_skills.map((sk) => (
                                  <span
                                    key={sk}
                                    style={{
                                      padding: '2px 8px',
                                      borderRadius: '999px',
                                      fontSize: '0.72rem',
                                      fontWeight: 600,
                                      background: 'hsla(174, 72%, 56%, 0.16)',
                                      color: 'var(--teal)',
                                    }}
                                  >
                                    🎯 Gap Skill: {sk}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Expertise Chips */}
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                            {(mentor.expertise_skills || []).slice(0, 6).map((sk) => (
                              <span
                                key={sk}
                                style={{
                                  padding: '3px 8px',
                                  borderRadius: 'var(--r-sm)',
                                  fontSize: '0.74rem',
                                  background: 'var(--bg-surface)',
                                  border: '1px solid var(--border)',
                                  color: 'var(--text-secondary)',
                                }}
                              >
                                {sk}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Footer: Availability & Connect CTA */}
                        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                            📅 {(mentor.available_days || []).join(', ')} ({mentor.preferred_time_window}) ·{' '}
                            {mentor.active_mentees_count}/{mentor.max_mentees} mentees
                          </div>

                          {connStatus === 'accepted' ? (
                            <button
                              type="button"
                              className="btn btn--primary btn--sm"
                              onClick={() => {
                                setSelectedConnId(mentor.connection_id);
                                setSubTab('sessions');
                              }}
                            >
                              💬 Message &amp; Book 1:1 →
                            </button>
                          ) : connStatus === 'pending' ? (
                            <span className="badge badge--accent">⏳ Request Pending</span>
                          ) : (
                            <button
                              type="button"
                              className="btn btn--primary btn--sm"
                              onClick={() => {
                                setConnectingMentor(mentor);
                                setGoalNote(
                                  `Hi ${mentor.full_name.split(' ')[0]}, I'm working toward ${
                                    career?.title || 'my target career'
                                  } and would love your guidance on ${
                                    mentor.shared_gap_skills?.[0] || mentor.expertise_skills?.[0] || 'key skills'
                                  }.`
                                );
                              }}
                            >
                              🤝 Request Connection
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Connection Request Modal */}
              {connectingMentor && (
                <div
                  style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0,0,0,0.68)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                    padding: '16px',
                  }}
                >
                  <form
                    className="card"
                    onSubmit={handleSendConnectionRequest}
                    style={{ maxWidth: '500px', width: '100%', padding: '24px' }}
                  >
                    <h3 style={{ marginBottom: '6px' }}>Connect with {connectingMentor.full_name}</h3>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Your mentor will receive a live snapshot of your top skill gaps so they can tailor your 1-on-1 sessions.
                    </p>

                    <div className="form-group">
                      <label>Your Mentorship Goal Note</label>
                      <textarea
                        rows={3}
                        value={goalNote}
                        onChange={(e) => setGoalNote(e.target.value)}
                        required
                        style={{
                          width: '100%',
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          padding: '10px 12px',
                          fontFamily: 'inherit',
                        }}
                      />
                    </div>

                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.83rem',
                        color: 'var(--teal)',
                        marginBottom: '18px',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={autoAcceptDemo}
                        onChange={(e) => setAutoAcceptDemo(e.target.checked)}
                      />
                      ⚡ Simulate Instant Mentor Acceptance (unlocks DMs &amp; 1:1 Calendar Booking immediately for demo)
                    </label>

                    <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setConnectingMentor(null)}
                      >
                        Cancel
                      </button>
                      <button type="submit" className="btn btn--primary btn--sm" disabled={submittingConn}>
                        {submittingConn ? 'Connecting...' : 'Send Connection Request'}
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          )}

          {/* ================================================================= */}
          {/* SUB-TAB 2: MENTOR PULSE FEED (LINKEDIN-STYLE INSIGHTS & EVENTS)   */}
          {/* ================================================================= */}
          {subTab === 'pulse' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '18px' }}>
                {['', 'Industry Insight', 'Event / Webinar', 'Career & Hiring Advice'].map((cat) => (
                  <button
                    key={cat || 'all'}
                    type="button"
                    className={`btn btn--sm ${pulseFilter === cat ? 'btn--primary' : 'btn--ghost'}`}
                    onClick={() => setPulseFilter(cat)}
                  >
                    {cat || 'All Pulse Posts'}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {displayedPulse.map((post) => (
                  <div key={post.id} className="card" style={{ padding: '22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap', marginBottom: '10px' }}>
                      <div>
                        <span
                          style={{
                            padding: '3px 10px',
                            borderRadius: '999px',
                            fontSize: '0.73rem',
                            fontWeight: 700,
                            background: 'hsla(174, 72%, 56%, 0.15)',
                            color: 'var(--teal)',
                          }}
                        >
                          {post.post_type}
                        </span>
                        <h3 style={{ fontSize: '1.08rem', marginTop: '8px', marginBottom: '2px' }}>{post.title}</h3>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                          By <strong>{post.mentor_name}</strong> · {post.mentor_headline}
                        </div>
                      </div>

                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => handleToggleLike(post.id)}
                      >
                        ♥ {post.likes_count || 0} Helpful
                      </button>
                    </div>

                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.65, whiteSpace: 'pre-line', marginBottom: '14px' }}>
                      {post.body}
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {(post.skill_tags || []).map((tag) => (
                          <span
                            key={tag}
                            style={{
                              padding: '3px 9px',
                              borderRadius: '999px',
                              fontSize: '0.74rem',
                              background: 'var(--bg-elevated)',
                              border: '1px solid var(--border)',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            #{tag}
                          </span>
                        ))}
                      </div>

                      {post.external_url && (
                        <a
                          href={post.external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn--ghost btn--sm"
                          style={{ textDecoration: 'none', color: 'var(--teal)' }}
                        >
                          🔗 Open Event / Reference Link ↗
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ================================================================= */}
          {/* SUB-TAB 3: SEARCHABLE Q&A KNOWLEDGE BASE                          */}
          {/* ================================================================= */}
          {subTab === 'qa' && (
            <div>
              {/* Search & Filter Bar */}
              <form
                className="card"
                onSubmit={handleSearchQuestions}
                style={{
                  padding: '16px 20px',
                  marginBottom: '20px',
                  display: 'flex',
                  gap: '10px',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <input
                  type="text"
                  placeholder="Search answered mentor questions by keyword, concept, or career..."
                  value={qaSearch}
                  onChange={(e) => setQaSearch(e.target.value)}
                  style={{ flex: 2, minWidth: '220px' }}
                />
                <input
                  type="text"
                  placeholder="Filter by skill tag (e.g. SQL, Financial Accounting)"
                  value={qaSkillFilter}
                  onChange={(e) => setQaSkillFilter(e.target.value)}
                  style={{ flex: 1, minWidth: '160px' }}
                />
                <button type="submit" className="btn btn--primary btn--sm">
                  Search Q&amp;A
                </button>
                {(qaSearch || qaSkillFilter) && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={async () => {
                      setQaSearch('');
                      setQaSkillFilter('');
                      const res = await getMentorshipQuestions();
                      setQuestions(res.questions || []);
                    }}
                  >
                    Clear
                  </button>
                )}
              </form>

              {/* Questions List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {questions.map((q) => (
                  <div key={q.id} className="card" style={{ padding: '22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span
                          style={{
                            padding: '3px 10px',
                            borderRadius: '999px',
                            fontSize: '0.74rem',
                            fontWeight: 700,
                            background: 'hsla(174, 72%, 56%, 0.15)',
                            color: 'var(--teal)',
                          }}
                        >
                          #{q.skill_tag}
                        </span>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          Asked by <strong>{q.learner_name}</strong> · Target: {q.career_title}
                        </span>
                      </div>
                      {q.source_lesson_title && (
                        <span style={{ fontSize: '0.75rem', color: 'hsl(38, 90%, 65%)' }}>
                          📚 From Lesson: {q.source_lesson_title}
                        </span>
                      )}
                    </div>

                    <h3 style={{ fontSize: '1.05rem', marginBottom: '6px' }}>{q.title}</h3>
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      {q.body}
                    </p>

                    {q.answers?.length === 0 ? (
                      <div style={{ padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-sm)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        ⏳ Routed to domain-matched mentors — awaiting verified response.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {q.answers.map((ans) => (
                          <div
                            key={ans.id}
                            style={{
                              padding: '14px 16px',
                              background: 'var(--bg-elevated)',
                              borderLeft: '3px solid var(--teal)',
                              borderRadius: 'var(--r-sm)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
                              <div>
                                <strong>{ans.mentor_name}</strong>{' '}
                                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                  ({ans.mentor_headline})
                                </span>{' '}
                                <span
                                  style={{
                                    padding: '2px 8px',
                                    borderRadius: '999px',
                                    fontSize: '0.7rem',
                                    fontWeight: 700,
                                    background: 'hsla(174, 72%, 56%, 0.18)',
                                    color: 'var(--teal)',
                                  }}
                                >
                                  ✓ Verified Mentor Answer
                                </span>
                              </div>

                              <button
                                type="button"
                                className="btn btn--ghost btn--sm"
                                style={{ padding: '3px 10px', fontSize: '0.76rem' }}
                                onClick={() => handleUpvoteAnswer(q.id, ans.id)}
                              >
                                ▲ Upvote ({ans.upvotes || 0})
                              </button>
                            </div>
                            <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
                              {ans.body}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Ask a Question Modal */}
              {showAskModal && (
                <div
                  style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0,0,0,0.68)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                    padding: '16px',
                  }}
                >
                  <form
                    className="card"
                    onSubmit={handleAskQuestion}
                    style={{ maxWidth: '540px', width: '100%', padding: '24px' }}
                  >
                    <h3 style={{ marginBottom: '6px' }}>💡 Ask a Domain Mentor</h3>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Your question is automatically routed to mentors whose verified skill stack matches your topic, and archived in the searchable Knowledge Base.
                    </p>

                    {qSourceLesson && (
                      <div style={{ marginBottom: '12px', padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-sm)', fontSize: '0.8rem', color: 'var(--teal)' }}>
                        📚 Linked Micro-Learning Lesson: <strong>{qSourceLesson}</strong>
                      </div>
                    )}

                    <div className="form-group">
                      <label>Related Skill / Competency</label>
                      <input
                        type="text"
                        value={qSkillTag}
                        onChange={(e) => setQSkillTag(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div className="form-group">
                      <label>Question Summary</label>
                      <input
                        type="text"
                        placeholder="e.g. How do I choose between composite B-tree indexes and covering indexes?"
                        value={qTitle}
                        onChange={(e) => setQTitle(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div className="form-group">
                      <label>Detailed Context / What You Tried</label>
                      <textarea
                        rows={4}
                        placeholder="Describe the scenario, trade-offs, or quiz concept you want a mentor to clarify..."
                        value={qBody}
                        onChange={(e) => setQBody(e.target.value)}
                        required
                        style={{
                          width: '100%',
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          padding: '10px 12px',
                          fontFamily: 'inherit',
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setShowAskModal(false)}
                      >
                        Cancel
                      </button>
                      <button type="submit" className="btn btn--primary btn--sm" disabled={submittingQ}>
                        {submittingQ ? 'Posting...' : 'Route Question to Mentors'}
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          )}

          {/* ================================================================= */}
          {/* SUB-TAB 4: DIRECT MESSAGES & 1-ON-1 CALENDAR SESSION BOOKING      */}
          {/* ================================================================= */}
          {subTab === 'sessions' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {acceptedConnections.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
                  <h3 style={{ marginBottom: '8px' }}>Connect with a Matched Mentor First</h3>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '520px', margin: '0 auto 18px', fontSize: '0.9rem' }}>
                    To prevent unsolicited spam and calendar squatting, Direct Messaging and 1-on-1 Session Booking unlock once you connect with a mentor.
                  </p>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => setSubTab('matches')}
                  >
                    🧭 Browse Matched Mentors →
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', alignItems: 'start' }}>
                  {/* Left Column: Direct Messages with Connected Mentor */}
                  <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                      <h3>💬 Direct Messages</h3>
                      <select
                        value={selectedConnId || ''}
                        onChange={(e) => setSelectedConnId(e.target.value)}
                        style={{
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          padding: '6px 10px',
                          fontSize: '0.84rem',
                        }}
                      >
                        {acceptedConnections.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.mentor?.full_name || 'Connected Mentor'}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div
                      style={{
                        height: '280px',
                        overflowY: 'auto',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                        padding: '12px',
                        background: 'var(--bg-elevated)',
                        borderRadius: 'var(--r-md)',
                        border: '1px solid var(--border)',
                        marginBottom: '12px',
                      }}
                    >
                      {messages.map((m) => {
                        const isMe = m.sender_role === 'learner';
                        return (
                          <div
                            key={m.id}
                            style={{
                              alignSelf: isMe ? 'flex-end' : 'flex-start',
                              maxWidth: '82%',
                              padding: '10px 14px',
                              borderRadius: 'var(--r-md)',
                              background: isMe ? 'hsla(174, 72%, 56%, 0.18)' : 'var(--bg-surface)',
                              border: '1px solid',
                              borderColor: isMe ? 'hsla(174, 72%, 56%, 0.35)' : 'var(--border)',
                            }}
                          >
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '3px' }}>
                              {isMe ? 'You' : activeConnection?.mentor?.full_name || 'Mentor'}
                            </div>
                            <div style={{ fontSize: '0.86rem', lineHeight: 1.5 }}>{m.text}</div>
                          </div>
                        );
                      })}
                    </div>

                    <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="text"
                        placeholder="Message your mentor..."
                        value={msgInput}
                        onChange={(e) => setMsgInput(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <button type="submit" className="btn btn--primary btn--sm" disabled={sendingMsg || !msgInput.trim()}>
                        Send
                      </button>
                    </form>
                  </div>

                  {/* Right Column: 1-on-1 Session Scheduler (with Anti-Double-Booking) */}
                  <form className="card" onSubmit={handleBookSession}>
                    <h3 style={{ marginBottom: '4px' }}>
                      📅 Book 1-on-1 Session with {activeConnection?.mentor?.full_name}
                    </h3>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      45-minute slots generated from your mentor&apos;s live availability. Booked slots are locked immediately to prevent double-booking.
                    </p>

                    <div className="form-group">
                      <label>Select Available 45-Minute Slot</label>
                      {slotsLoading ? (
                        <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>Checking calendar conflicts...</div>
                      ) : availableSlots.length === 0 ? (
                        <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>No open slots in the next 10 days.</div>
                      ) : (
                        <select
                          value={selectedSlotIso}
                          onChange={(e) => setSelectedSlotIso(e.target.value)}
                          style={{
                            width: '100%',
                            background: 'var(--bg-input)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--r-md)',
                            padding: '10px 12px',
                          }}
                        >
                          {availableSlots.map((sl) => (
                            <option key={sl.slot_start_iso} value={sl.slot_start_iso}>
                              {sl.display_label} ({sl.duration_minutes} mins)
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    <div className="form-group">
                      <label>Session Topic / Agenda</label>
                      <input
                        type="text"
                        value={sessionTopic}
                        onChange={(e) => setSessionTopic(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div className="form-group">
                      <label>Primary Skill to Practice (Eligible for +15% Mentor Endorsement)</label>
                      <select
                        value={sessionFocusSkill}
                        onChange={(e) => setSessionFocusSkill(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          padding: '10px 12px',
                        }}
                      >
                        {skills.map((s) => (
                          <option key={s.id || s.name} value={s.name}>
                            {s.name} (Current: {s.proficiency}%)
                          </option>
                        ))}
                        {skills.length === 0 && <option value="Career Strategy">Career Strategy</option>}
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Questions or Links for the Session</label>
                      <input
                        type="text"
                        placeholder="Optional agenda notes..."
                        value={sessionNotes}
                        onChange={(e) => setSessionNotes(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn--primary btn--full"
                      disabled={bookingSession || !selectedSlotIso}
                    >
                      {bookingSession ? 'Confirming Slot & Generating Meeting ID...' : 'Confirm 1-on-1 Session & Generate Meeting Link'}
                    </button>
                  </form>
                </div>
              )}

              {/* Upcoming & Completed Sessions List */}
              <div className="card">
                <h3 style={{ marginBottom: '12px' }}>Your Scheduled 1-on-1 Sessions ({sessions.length})</h3>
                {sessions.length === 0 ? (
                  <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>
                    No sessions booked yet. Select an available slot above to generate your meeting link and calendar invite.
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {sessions.map((sess) => (
                      <div
                        key={sess.id}
                        style={{
                          padding: '16px',
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '0.98rem' }}>
                              {sess.topic} · with <span style={{ color: 'var(--teal)' }}>{sess.mentor_name}</span>
                            </div>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '3px' }}>
                              🕒 {sess.display_label || new Date(sess.slot_start_iso).toLocaleString()} · Meeting ID:{' '}
                              <code>{sess.meeting_code}</code>
                            </div>
                            {sess.focus_skill && (
                              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                                Target Competency: <strong>{sess.focus_skill}</strong>
                                {sess.endorsed_skill && (
                                  <span style={{ color: 'var(--teal)', marginLeft: '8px', fontWeight: 700 }}>
                                    ✓ Endorsed (+15% Proficiency)
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          <span className="badge badge--accent" style={{ textTransform: 'capitalize' }}>
                            {sess.status}
                          </span>
                        </div>

                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
                          {sess.meeting_url && sess.status === 'confirmed' && (
                            <a
                              href={sess.meeting_url}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn--primary btn--sm"
                              style={{ textDecoration: 'none' }}
                            >
                              🎥 Join Video Room ({sess.meeting_code})
                            </a>
                          )}
                          {sess.google_calendar_url && (
                            <a
                              href={sess.google_calendar_url}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn--ghost btn--sm"
                              style={{ textDecoration: 'none' }}
                            >
                              📅 Add to Google Calendar
                            </a>
                          )}
                          <a
                            href={getSessionIcsDownloadUrl(sess.id)}
                            download
                            className="btn btn--ghost btn--sm"
                            style={{ textDecoration: 'none' }}
                          >
                            ⬇ Download .ics (with 24h &amp; 15m Reminders)
                          </a>
                          {sess.status === 'confirmed' && (
                            <button
                              type="button"
                              className="btn btn--ghost btn--sm"
                              onClick={() => handleCancelSession(sess.id)}
                            >
                              Cancel Slot
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {toastMessage && (
        <Toast
          message={toastMessage}
          confirmLabel="OK"
          onConfirm={() => setToastMessage(null)}
        />
      )}
    </div>
  );
}

