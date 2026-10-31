// src/pages/MentorDashboard.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';
import {
  getMyMentorProfile,
  updateMyMentorProfile,
  getMentorshipConnections,
  respondToConnectionRequest,
  getConnectionMessages,
  sendConnectionMessage,
  getMentorPulseFeed,
  publishMentorPulsePost,
  toggleLikePulsePost,
  getMentorshipQuestions,
  answerMentorshipQuestion,
  getMentorshipSessions,
  cancelMentorshipSession,
  completeMentorshipSession,
  getSessionIcsDownloadUrl,
} from '../lib/api';
import Toast from '../components/Toast';

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MentorDashboard({ user, userProfile }) {
  const [activeTab, setActiveTab] = useState('roster'); // 'roster' | 'qa' | 'pulse' | 'messages' | 'calendar'
  const [mentorProfile, setMentorProfile] = useState(null);
  const [connections, setConnections] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [pulsePosts, setPulsePosts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);

  // Direct Messaging state
  const [selectedConnId, setSelectedConnId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [msgText, setMsgText] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);

  // Q&A Answer state
  const [answeringQuestionId, setAnsweringQuestionId] = useState(null);
  const [answerDraft, setAnswerDraft] = useState('');
  const [submittingAnswer, setSubmittingAnswer] = useState(false);

  // Mentor Pulse composer state
  const [pulseTitle, setPulseTitle] = useState('');
  const [pulseType, setPulseType] = useState('Industry Insight');
  const [pulseBody, setPulseBody] = useState('');
  const [pulseTagsInput, setPulseTagsInput] = useState('');
  const [pulseUrl, setPulseUrl] = useState('');
  const [publishingPulse, setPublishingPulse] = useState(false);

  // Session completion & Skill Endorsement state
  const [completingSession, setCompletingSession] = useState(null);
  const [endorseSkill, setEndorseSkill] = useState('');
  const [endorseNote, setEndorseNote] = useState('');
  const [submittingEndorsement, setSubmittingEndorsement] = useState(false);

  // Availability editor state
  const [availDays, setAvailDays] = useState(['Tue', 'Thu']);
  const [availWindow, setAvailWindow] = useState('Evening');
  const [availHours, setAvailHours] = useState(4);
  const [availMaxMentees, setAvailMaxMentees] = useState(5);
  const [savingAvail, setSavingAvail] = useState(false);

  const loadWorkspace = async () => {
    setLoading(true);
    try {
      const [profRes, connRes, qRes, pulseRes, sessRes] = await Promise.all([
        getMyMentorProfile(),
        getMentorshipConnections('mentor'),
        getMentorshipQuestions({ forMentor: true }),
        getMentorPulseFeed(),
        getMentorshipSessions('mentor'),
      ]);

      const mp = profRes.mentor;
      setMentorProfile(mp);
      if (mp) {
        setAvailDays(mp.available_days || ['Tue', 'Thu']);
        setAvailWindow(mp.preferred_time_window || 'Evening');
        setAvailHours(mp.weekly_hours || 4);
        setAvailMaxMentees(mp.max_mentees || 5);
      }

      const conns = connRes.connections || [];
      setConnections(conns);
      const accepted = conns.filter((c) => c.status === 'accepted');
      if (accepted.length > 0 && !selectedConnId) {
        setSelectedConnId(accepted[0].id);
      }

      setQuestions(qRes.questions || []);
      setPulsePosts(pulseRes.posts || []);
      setSessions(sessRes.sessions || []);
    } catch (err) {
      console.error('Failed to load mentor dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedConnId) return;
    getConnectionMessages(selectedConnId)
      .then((res) => setMessages(res.messages || []))
      .catch((err) => console.error('Failed to load messages:', err));
  }, [selectedConnId]);

  const handleRespondConnection = async (connectionId, action) => {
    try {
      await respondToConnectionRequest(connectionId, action);
      setToastMessage(
        action === 'accept'
          ? 'Connection accepted! You can now message and schedule 1-on-1 sessions with this mentee.'
          : 'Connection request declined.'
      );
      await loadWorkspace();
    } catch (err) {
      setToastMessage(err.message || 'Failed to update connection.');
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!selectedConnId || !msgText.trim()) return;
    setSendingMsg(true);
    try {
      const res = await sendConnectionMessage(selectedConnId, msgText.trim(), 'mentor');
      setMessages((prev) => [...prev, res.message]);
      setMsgText('');
    } catch (err) {
      setToastMessage(err.message || 'Failed to send message.');
    } finally {
      setSendingMsg(false);
    }
  };

  const handleSubmitAnswer = async (questionId) => {
    if (!answerDraft.trim()) return;
    setSubmittingAnswer(true);
    try {
      await answerMentorshipQuestion(questionId, answerDraft.trim());
      setAnswerDraft('');
      setAnsweringQuestionId(null);
      setToastMessage('Verified Mentor Answer published to the Q&A Knowledge Base!');
      const qRes = await getMentorshipQuestions({ forMentor: true });
      setQuestions(qRes.questions || []);
    } catch (err) {
      setToastMessage(err.message || 'Failed to post answer.');
    } finally {
      setSubmittingAnswer(false);
    }
  };

  const handlePublishPulse = async (e) => {
    e.preventDefault();
    if (!pulseTitle.trim() || !pulseBody.trim()) return;
    setPublishingPulse(true);
    try {
      const tags = pulseTagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      await publishMentorPulsePost({
        title: pulseTitle.trim(),
        post_type: pulseType,
        body: pulseBody.trim(),
        skill_tags: tags.length ? tags : mentorProfile?.expertise_skills?.slice(0, 3) || ['Career Strategy'],
        external_url: pulseUrl.trim() || null,
      });
      setPulseTitle('');
      setPulseBody('');
      setPulseTagsInput('');
      setPulseUrl('');
      setToastMessage('Published to Mentor Pulse Feed!');
      const pulseRes = await getMentorPulseFeed();
      setPulsePosts(pulseRes.posts || []);
    } catch (err) {
      setToastMessage(err.message || 'Failed to publish post.');
    } finally {
      setPublishingPulse(false);
    }
  };

  const handleCompleteAndEndorse = async (e) => {
    e.preventDefault();
    if (!completingSession) return;
    setSubmittingEndorsement(true);
    try {
      await completeMentorshipSession(
        completingSession.id,
        endorseSkill.trim() || null,
        endorseNote.trim()
      );
      setToastMessage(
        endorseSkill.trim()
          ? `Session marked complete! Endorsed "${endorseSkill.trim()}" (+15% Mentor-Verified proficiency boost).`
          : 'Session marked complete!'
      );
      setCompletingSession(null);
      setEndorseSkill('');
      setEndorseNote('');
      await loadWorkspace();
    } catch (err) {
      setToastMessage(err.message || 'Failed to complete session.');
    } finally {
      setSubmittingEndorsement(false);
    }
  };

  const handleSaveAvailability = async () => {
    setSavingAvail(true);
    try {
      const res = await updateMyMentorProfile({
        available_days: availDays,
        preferred_time_window: availWindow,
        weekly_hours: Number(availHours),
        max_mentees: Number(availMaxMentees),
      });
      setMentorProfile(res.mentor);
      setToastMessage('Availability & capacity settings updated!');
    } catch (err) {
      setToastMessage(err.message || 'Failed to update settings.');
    } finally {
      setSavingAvail(false);
    }
  };

  const pendingConnections = connections.filter((c) => c.status === 'pending');
  const acceptedConnections = connections.filter((c) => c.status === 'accepted');
  const upcomingSessions = sessions.filter((s) => s.status === 'confirmed');

  return (
    <>
      <div className="bg-orb bg-orb--1" />
      <div className="bg-orb bg-orb--2" />

      <div style={{ minHeight: '100svh', padding: '24px', position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            maxWidth: '1040px',
            margin: '0 auto 28px',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="logo-mark">
              <div className="logo-mark__icon">CB</div>
              Career Beacon
            </div>
            <span
              style={{
                padding: '4px 10px',
                borderRadius: '999px',
                fontSize: '0.75rem',
                fontWeight: 700,
                background: 'hsla(174, 72%, 56%, 0.16)',
                color: 'var(--teal)',
                border: '1px solid hsla(174, 72%, 56%, 0.35)',
              }}
            >
              🎓 Mentor Workspace
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              {mentorProfile?.full_name || userProfile?.full_name || user?.email}
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setShowLogoutToast(true)}
            >
              Sign out
            </button>
          </div>
        </header>

        <main style={{ maxWidth: '1040px', margin: '0 auto' }}>
          {/* Mentor Executive Summary Banner */}
          <div className="card" style={{ marginBottom: '24px', padding: '22px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--teal)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {mentorProfile?.primary_domain || 'Industry Mentorship'}
                </div>
                <h2 style={{ margin: '4px 0 6px' }}>
                  {mentorProfile?.full_name || userProfile?.full_name || 'Mentor Workspace'}
                </h2>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>
                  {mentorProfile?.headline || userProfile?.headline || 'Verified Career Beacon Mentor'}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '10px 16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--teal)' }}>
                    {acceptedConnections.length} / {mentorProfile?.max_mentees || 5}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Active Mentees</div>
                </div>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '10px 16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--accent-light)' }}>
                    {pendingConnections.length}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Pending Requests</div>
                </div>
                <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '10px 16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.35rem', fontWeight: 800, color: 'hsl(38, 90%, 60%)' }}>
                    {upcomingSessions.length}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Upcoming 1:1s</div>
                </div>
              </div>
            </div>
          </div>

          {/* 5-Tab Mentor Navigation */}
          <nav
            style={{
              display: 'flex',
              gap: '8px',
              marginBottom: '24px',
              borderBottom: '1px solid var(--border)',
              paddingBottom: '12px',
              flexWrap: 'wrap',
            }}
          >
            <button
              type="button"
              className={`btn btn--sm ${activeTab === 'roster' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('roster')}
            >
              👥 Mentees &amp; Requests ({connections.length})
            </button>
            <button
              type="button"
              className={`btn btn--sm ${activeTab === 'qa' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('qa')}
            >
              💡 Learner Q&amp;A Inbox ({questions.length})
            </button>
            <button
              type="button"
              className={`btn btn--sm ${activeTab === 'pulse' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('pulse')}
            >
              📢 Publish to Mentor Pulse
            </button>
            <button
              type="button"
              className={`btn btn--sm ${activeTab === 'messages' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('messages')}
            >
              💬 Direct Messages
            </button>
            <button
              type="button"
              className={`btn btn--sm ${activeTab === 'calendar' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('calendar')}
            >
              📅 Calendar &amp; 1-on-1 Sessions ({upcomingSessions.length})
            </button>
          </nav>

          {loading ? (
            <div className="card" style={{ textAlign: 'center', padding: '48px' }}>
              <div className="spinner spinner--lg" style={{ margin: '0 auto 12px' }} />
              <p style={{ color: 'var(--text-muted)' }}>Loading Mentor Ecosystem...</p>
            </div>
          ) : (
            <>
              {/* TAB 1: MENTEE ROSTER & REQUESTS (WITH SKILL GAP SNAPSHOT) */}
              {activeTab === 'roster' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* Pending Requests */}
                  <div className="card">
                    <h3 style={{ marginBottom: '6px' }}>Incoming Connection Requests ({pendingConnections.length})</h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                      Review each learner&apos;s target career, goal note, and live Skill Gap Snapshot before accepting.
                    </p>

                    {pendingConnections.length === 0 ? (
                      <div style={{ padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-md)', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                        No pending connection requests right now.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {pendingConnections.map((conn) => (
                          <div
                            key={conn.id}
                            style={{
                              padding: '16px',
                              background: 'var(--bg-elevated)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-md)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                              <div>
                                <div style={{ fontWeight: 700, fontSize: '1rem' }}>
                                  {conn.learner_snapshot?.learner_name || 'Learner'}
                                </div>
                                <div style={{ fontSize: '0.82rem', color: 'var(--teal)', marginTop: '2px' }}>
                                  Target Career: <strong>{conn.learner_snapshot?.target_career || 'Career Switcher'}</strong> · Avg Readiness: {conn.learner_snapshot?.avg_proficiency || 0}%
                                </div>
                              </div>
                              <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                  type="button"
                                  className="btn btn--primary btn--sm"
                                  onClick={() => handleRespondConnection(conn.id, 'accept')}
                                >
                                  ✓ Accept Mentee
                                </button>
                                <button
                                  type="button"
                                  className="btn btn--ghost btn--sm"
                                  onClick={() => handleRespondConnection(conn.id, 'decline')}
                                >
                                  Decline
                                </button>
                              </div>
                            </div>

                            {conn.goal_note && (
                              <div style={{ marginTop: '10px', padding: '10px 12px', background: 'var(--bg-surface)', borderRadius: 'var(--r-sm)', fontSize: '0.86rem' }}>
                                <strong>Mentee Goal Note:</strong> &ldquo;{conn.goal_note}&rdquo;
                              </div>
                            )}

                            {/* Live Skill Gap Snapshot */}
                            {conn.learner_snapshot?.top_skill_gaps?.length > 0 && (
                              <div style={{ marginTop: '12px' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                                  LIVE SKILL GAP SNAPSHOT (TOP PRIORITY DEFICITS):
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                  {conn.learner_snapshot.top_skill_gaps.map((g) => (
                                    <span
                                      key={g.name}
                                      style={{
                                        padding: '4px 10px',
                                        borderRadius: '999px',
                                        fontSize: '0.78rem',
                                        background: 'hsla(38, 90%, 60%, 0.14)',
                                        color: 'hsl(38, 90%, 65%)',
                                        border: '1px solid hsla(38, 90%, 60%, 0.3)',
                                      }}
                                    >
                                      {g.name} ({g.proficiency}%)
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Active Connected Mentees */}
                  <div className="card">
                    <h3 style={{ marginBottom: '6px' }}>Connected Mentees ({acceptedConnections.length})</h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                      Active mentees who can message you directly and book 1-on-1 calendar sessions.
                    </p>

                    {acceptedConnections.length === 0 ? (
                      <div style={{ padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-md)', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                        No connected mentees yet. Accept a request above to unlock Direct Messaging and 1-on-1 Session Scheduling.
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '14px' }}>
                        {acceptedConnections.map((conn) => (
                          <div
                            key={conn.id}
                            style={{
                              padding: '16px',
                              background: 'var(--bg-elevated)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-md)',
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'space-between',
                              gap: '12px',
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <strong style={{ fontSize: '0.98rem' }}>
                                  {conn.learner_snapshot?.learner_name || 'Connected Learner'}
                                </strong>
                                <span className="badge badge--accent">Connected</span>
                              </div>
                              <div style={{ fontSize: '0.82rem', color: 'var(--teal)', marginTop: '4px' }}>
                                Target: {conn.learner_snapshot?.target_career || 'Career Track'} ({conn.learner_snapshot?.avg_proficiency || 0}% avg)
                              </div>

                              {conn.learner_snapshot?.top_skill_gaps?.length > 0 && (
                                <div style={{ marginTop: '10px' }}>
                                  <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                    Top Skill Deficits:
                                  </div>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                    {conn.learner_snapshot.top_skill_gaps.map((g) => (
                                      <span
                                        key={g.name}
                                        style={{
                                          padding: '2px 8px',
                                          borderRadius: '999px',
                                          fontSize: '0.74rem',
                                          background: 'var(--bg-surface)',
                                          border: '1px solid var(--border)',
                                        }}
                                      >
                                        {g.name}: {g.proficiency}%
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>

                            <button
                              type="button"
                              className="btn btn--ghost btn--sm"
                              onClick={() => {
                                setSelectedConnId(conn.id);
                                setActiveTab('messages');
                              }}
                            >
                              💬 Open Direct Messages →
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: MATCHED LEARNER Q&A INBOX */}
              {activeTab === 'qa' && (
                <div className="card">
                  <h3 style={{ marginBottom: '6px' }}>Matched Learner Q&amp;A Inbox</h3>
                  <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                    Questions asked by learners across Career Beacon, prioritized by overlap with your expertise skills. Your answers receive a <strong>✓ Verified Mentor Answer</strong> badge.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {questions.map((q) => (
                      <div
                        key={q.id}
                        style={{
                          padding: '18px',
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                        }}
                      >
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
                              Asked by <strong>{q.learner_name}</strong> ({q.career_title})
                            </span>
                            {q.mentor_skill_match && (
                              <span className="badge badge--accent">Matches Your Expertise</span>
                            )}
                          </div>
                          {q.source_lesson_title && (
                            <span style={{ fontSize: '0.74rem', color: 'hsl(38, 90%, 65%)' }}>
                              📚 Linked Lesson: {q.source_lesson_title}
                            </span>
                          )}
                        </div>

                        <h4 style={{ marginBottom: '6px', fontSize: '1.02rem' }}>{q.title}</h4>
                        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                          {q.body}
                        </p>

                        {/* Existing verified answers */}
                        {q.answers?.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                            {q.answers.map((ans) => (
                              <div
                                key={ans.id}
                                style={{
                                  padding: '12px 14px',
                                  background: 'var(--bg-surface)',
                                  borderLeft: '3px solid var(--teal)',
                                  borderRadius: 'var(--r-sm)',
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                                  <span>
                                    <strong>{ans.mentor_name}</strong> · <span style={{ color: 'var(--teal)' }}>✓ Verified Mentor Answer</span>
                                  </span>
                                  <span style={{ color: 'var(--text-muted)' }}>▲ {ans.upvotes || 0} upvotes</span>
                                </div>
                                <div style={{ fontSize: '0.86rem', color: 'var(--text-primary)', lineHeight: 1.55 }}>
                                  {ans.body}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {answeringQuestionId === q.id ? (
                          <div style={{ marginTop: '10px' }}>
                            <textarea
                              rows={3}
                              placeholder="Write your verified guidance, examples, or recommended workflow..."
                              value={answerDraft}
                              onChange={(e) => setAnswerDraft(e.target.value)}
                              style={{
                                width: '100%',
                                background: 'var(--bg-input)',
                                color: 'var(--text-primary)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--r-md)',
                                padding: '10px 12px',
                                fontSize: '0.88rem',
                                marginBottom: '8px',
                              }}
                            />
                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                              <button
                                type="button"
                                className="btn btn--ghost btn--sm"
                                onClick={() => {
                                  setAnsweringQuestionId(null);
                                  setAnswerDraft('');
                                }}
                              >
                                Cancel
                              </button>
                              <button
                                type="button"
                                className="btn btn--primary btn--sm"
                                onClick={() => handleSubmitAnswer(q.id)}
                                disabled={submittingAnswer || !answerDraft.trim()}
                              >
                                {submittingAnswer ? 'Publishing...' : 'Publish Verified Answer'}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => {
                              setAnsweringQuestionId(q.id);
                              setAnswerDraft('');
                            }}
                          >
                            ✍️ Write Verified Answer
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: PUBLISH TO MENTOR PULSE */}
              {activeTab === 'pulse' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '20px', alignItems: 'start' }}>
                  <form className="card" onSubmit={handlePublishPulse}>
                    <h3 style={{ marginBottom: '6px' }}>Publish to Mentor Pulse</h3>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
                      Share industry developments, upcoming webinars/events, or actionable career advice with learners targeting your domain.
                    </p>

                    <div className="form-group">
                      <label>Post Category</label>
                      <select
                        value={pulseType}
                        onChange={(e) => setPulseType(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          padding: '10px 12px',
                        }}
                      >
                        <option value="Industry Insight">💡 Industry Insight</option>
                        <option value="Event / Webinar">📅 Event / Live Workshop</option>
                        <option value="Career & Hiring Advice">🎯 Career &amp; Hiring Advice</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Headline / Post Title</label>
                      <input
                        type="text"
                        placeholder="e.g. What Hiring Managers Look For in System Design Interviews"
                        value={pulseTitle}
                        onChange={(e) => setPulseTitle(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div className="form-group">
                      <label>Post Content</label>
                      <textarea
                        rows={5}
                        placeholder="Share concrete advice, real-world mental models, or event details..."
                        value={pulseBody}
                        onChange={(e) => setPulseBody(e.target.value)}
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

                    <div className="form-group">
                      <label>Skill Tags (comma-separated)</label>
                      <input
                        type="text"
                        placeholder="e.g. SQL, System Design, Financial Modeling"
                        value={pulseTagsInput}
                        onChange={(e) => setPulseTagsInput(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div className="form-group">
                      <label>Optional Event / Reference Link</label>
                      <input
                        type="url"
                        placeholder="https://..."
                        value={pulseUrl}
                        onChange={(e) => setPulseUrl(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>

                    <button
                      type="submit"
                      className="btn btn--primary btn--full"
                      disabled={publishingPulse || !pulseTitle.trim() || !pulseBody.trim()}
                    >
                      {publishingPulse ? 'Publishing...' : '📢 Publish to Learner Pulse Feed'}
                    </button>
                  </form>

                  <div className="card">
                    <h3 style={{ marginBottom: '14px' }}>Live Mentor Pulse Feed ({pulsePosts.length})</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      {pulsePosts.map((post) => (
                        <div
                          key={post.id}
                          style={{
                            padding: '16px',
                            background: 'var(--bg-elevated)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--r-md)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--teal)' }}>
                              {post.post_type}
                            </span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              ♥ {post.likes_count || 0} likes
                            </span>
                          </div>
                          <h4 style={{ marginBottom: '4px', fontSize: '0.96rem' }}>{post.title}</h4>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                            {post.mentor_name} · {post.mentor_headline}
                          </div>
                          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', whiteSpace: 'pre-line', marginBottom: '10px' }}>
                            {post.body}
                          </p>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {(post.skill_tags || []).map((t) => (
                              <span
                                key={t}
                                style={{
                                  fontSize: '0.72rem',
                                  padding: '2px 8px',
                                  borderRadius: '999px',
                                  background: 'var(--bg-surface)',
                                  border: '1px solid var(--border)',
                                }}
                              >
                                #{t}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: DIRECT MESSAGES (DMs) */}
              {activeTab === 'messages' && (
                <div className="card" style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '20px', minHeight: '420px' }}>
                  <div style={{ borderRight: '1px solid var(--border)', paddingRight: '16px' }}>
                    <h4 style={{ marginBottom: '12px' }}>Connected Mentees</h4>
                    {acceptedConnections.length === 0 ? (
                      <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                        Accept a connection request first to unlock direct messaging.
                      </p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {acceptedConnections.map((c) => (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() => setSelectedConnId(c.id)}
                            style={{
                              textAlign: 'left',
                              padding: '10px 12px',
                              borderRadius: 'var(--r-md)',
                              border: '1px solid',
                              borderColor: selectedConnId === c.id ? 'var(--teal)' : 'var(--border)',
                              background: selectedConnId === c.id ? 'hsla(174, 72%, 56%, 0.14)' : 'var(--bg-elevated)',
                              color: 'var(--text-primary)',
                              cursor: 'pointer',
                            }}
                          >
                            <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>
                              {c.learner_snapshot?.learner_name || 'Learner'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {c.learner_snapshot?.target_career || 'Career Mentee'}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    {!selectedConnId ? (
                      <div style={{ margin: 'auto', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                        Select a connected mentee on the left to view or send messages.
                      </div>
                    ) : (
                      <>
                        <div style={{ maxHeight: '320px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingRight: '8px' }}>
                          {messages.map((m) => {
                            const isMe = m.sender_role === 'mentor';
                            return (
                              <div
                                key={m.id}
                                style={{
                                  alignSelf: isMe ? 'flex-end' : 'flex-start',
                                  maxWidth: '78%',
                                  padding: '10px 14px',
                                  borderRadius: 'var(--r-md)',
                                  background: isMe ? 'hsla(174, 72%, 56%, 0.2)' : 'var(--bg-elevated)',
                                  border: '1px solid',
                                  borderColor: isMe ? 'hsla(174, 72%, 56%, 0.4)' : 'var(--border)',
                                }}
                              >
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                  {isMe ? 'You (Mentor)' : 'Mentee'}
                                </div>
                                <div style={{ fontSize: '0.88rem', lineHeight: 1.5 }}>{m.text}</div>
                              </div>
                            );
                          })}
                        </div>

                        <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
                          <input
                            type="text"
                            placeholder="Write a message to your mentee..."
                            value={msgText}
                            onChange={(e) => setMsgText(e.target.value)}
                            style={{ flex: 1 }}
                          />
                          <button type="submit" className="btn btn--primary btn--sm" disabled={sendingMsg || !msgText.trim()}>
                            {sendingMsg ? 'Sending...' : 'Send'}
                          </button>
                        </form>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 5: CALENDAR, SESSIONS & POST-SESSION SKILL ENDORSEMENT */}
              {activeTab === 'calendar' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1.35fr 1fr', gap: '20px', alignItems: 'start' }}>
                  <div className="card">
                    <h3 style={{ marginBottom: '6px' }}>1-on-1 Mentorship Sessions ({sessions.length})</h3>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Every booked session includes a unique Jitsi Meet room, Google Calendar deep-link, and RFC 5545 <code>.ics</code> invite with 24h &amp; 15m reminders. After a session, you can endorse the mentee&apos;s practiced skill (+15% verified boost).
                    </p>

                    {sessions.length === 0 ? (
                      <div style={{ padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-md)', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                        No 1-on-1 sessions booked yet.
                      </div>
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
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', flexWrap: 'wrap' }}>
                              <div>
                                <div style={{ fontWeight: 700, fontSize: '0.96rem' }}>{sess.topic}</div>
                                <div style={{ fontSize: '0.82rem', color: 'var(--teal)', marginTop: '2px' }}>
                                  🕒 {new Date(sess.slot_start_iso).toLocaleString()} ({sess.duration_minutes} mins)
                                </div>
                                {sess.focus_skill && (
                                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                                    Focus Competency: <strong>{sess.focus_skill}</strong>
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
                                ⬇ Download .ics (24h &amp; 15m Reminders)
                              </a>
                              {sess.status === 'confirmed' && (
                                <button
                                  type="button"
                                  className="btn btn--ghost btn--sm"
                                  style={{ borderColor: 'var(--teal)', color: 'var(--teal)' }}
                                  onClick={() => {
                                    setCompletingSession(sess);
                                    setEndorseSkill(sess.focus_skill || '');
                                  }}
                                >
                                  🏅 Complete &amp; Endorse Skill (+15%)
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Post-Session Skill Endorsement Modal */}
                    {completingSession && (
                      <form
                        onSubmit={handleCompleteAndEndorse}
                        style={{
                          marginTop: '18px',
                          padding: '18px',
                          background: 'var(--bg-surface)',
                          border: '1px solid var(--teal)',
                          borderRadius: 'var(--r-md)',
                        }}
                      >
                        <h4 style={{ marginBottom: '6px' }}>
                          🏅 Post-Session Skill Endorsement
                        </h4>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                          Endorsing a skill upgrades the mentee&apos;s skill graph by <strong>+15% proficiency</strong> with a <code>✓ Mentor Verified</code> badge.
                        </p>
                        <div className="form-group">
                          <label>Skill to Endorse</label>
                          <input
                            type="text"
                            placeholder="e.g. SQL, System Design, Financial Accounting..."
                            value={endorseSkill}
                            onChange={(e) => setEndorseSkill(e.target.value)}
                            style={{ width: '100%' }}
                          />
                        </div>
                        <div className="form-group">
                          <label>Session Feedback Note</label>
                          <textarea
                            rows={2}
                            placeholder="Brief note on the mentee's demonstrated competency..."
                            value={endorseNote}
                            onChange={(e) => setEndorseNote(e.target.value)}
                            style={{
                              width: '100%',
                              background: 'var(--bg-input)',
                              color: 'var(--text-primary)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-md)',
                              padding: '8px 10px',
                            }}
                          />
                        </div>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => setCompletingSession(null)}
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            className="btn btn--primary btn--sm"
                            disabled={submittingEndorsement}
                          >
                            {submittingEndorsement ? 'Saving...' : 'Confirm Completion & Endorse'}
                          </button>
                        </div>
                      </form>
                    )}
                  </div>

                  {/* Availability & Anti-Double-Booking Settings */}
                  <div className="card">
                    <h3 style={{ marginBottom: '6px' }}>Availability &amp; Capacity Manager</h3>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Control your recurring weekly windows and mentee cap. Booked slots automatically lock across both your calendar and the learner&apos;s calendar to prevent double-booking.
                    </p>

                    <div className="form-group">
                      <label>Available Days</label>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                        {DAYS_OF_WEEK.map((day) => {
                          const active = availDays.includes(day);
                          return (
                            <button
                              key={day}
                              type="button"
                              onClick={() =>
                                setAvailDays((prev) =>
                                  prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
                                )
                              }
                              style={{
                                padding: '6px 12px',
                                borderRadius: 'var(--r-sm)',
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                border: '1px solid',
                                borderColor: active ? 'var(--teal)' : 'var(--border)',
                                background: active ? 'hsla(174, 72%, 56%, 0.2)' : 'var(--bg-elevated)',
                                color: active ? 'var(--teal)' : 'var(--text-secondary)',
                              }}
                            >
                              {day}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="form-group">
                      <label>Preferred Time Window</label>
                      <select
                        value={availWindow}
                        onChange={(e) => setAvailWindow(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--r-md)',
                          padding: '10px 12px',
                        }}
                      >
                        <option value="Morning">Morning (09:00 – 11:00 UTC)</option>
                        <option value="Afternoon">Afternoon (14:00 – 16:00 UTC)</option>
                        <option value="Evening">Evening (18:00 – 20:00 UTC)</option>
                        <option value="Flexible">Flexible (All Windows)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Weekly Hours ({availHours} hrs/wk)</label>
                      <input
                        type="range"
                        min="1"
                        max="20"
                        value={availHours}
                        onChange={(e) => setAvailHours(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div className="form-group">
                      <label>Max Active Mentees ({availMaxMentees})</label>
                      <input
                        type="range"
                        min="1"
                        max="15"
                        value={availMaxMentees}
                        onChange={(e) => setAvailMaxMentees(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>

                    <button
                      type="button"
                      className="btn btn--primary btn--full"
                      onClick={handleSaveAvailability}
                      disabled={savingAvail}
                    >
                      {savingAvail ? 'Saving...' : 'Save Availability Settings'}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {toastMessage && (
        <Toast
          message={toastMessage}
          confirmLabel="OK"
          onConfirm={() => setToastMessage(null)}
        />
      )}

      {showLogoutToast && (
        <Toast
          message="Are you sure you want to log out?"
          confirmLabel="Yes, log out"
          onConfirm={async () => {
            setShowLogoutToast(false);
            await supabase.auth.signOut();
          }}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </>
  );
}

