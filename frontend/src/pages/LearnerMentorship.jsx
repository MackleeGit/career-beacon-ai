// src/pages/LearnerMentorship.jsx
import { useState, useEffect, useRef } from 'react';
import {
  getMentorMatches,
  requestMentorConnection,
  getMentorshipConnections,
  getConnectionMessages,
  sendConnectionMessage,
  getMentorPulseFeed,
  toggleLikePulsePost,
  getMentorshipQuestions,
  preflightMentorshipQuestion,
  askMentorshipQuestion,
  upvoteMentorshipAnswer,
  getMentorAvailableSlots,
  bookMentorshipSession,
  getMentorshipSessions,
  cancelMentorshipSession,
  getSessionIcsDownloadUrl,
  flagContentItem,
} from '../lib/api';
import Toast from '../components/Toast';
import { MentorCardSkeleton } from '../components/Skeleton';
import {
  Compass,
  Radio,
  HelpCircle,
  MessageSquare,
  ShieldCheck,
  Target,
  Calendar,
  Clock,
  UserCheck,
  Sparkles,
  ThumbsUp,
  ExternalLink,
  BookOpen,
  Video,
  Download,
  Send,
  Search,
  Plus,
  X,
  Star,
  Check,
  Flag,
  ArrowLeft,
} from '../components/Icons';

export default function LearnerMentorship({
  user,
  career,
  skills = [],
  initialSubTab = 'matches',
  initialConnectionId = null,
  prefillQuestion = null,
  onClearPrefillQuestion,
}) {
  const [subTab, setSubTab] = useState(initialSubTab); // 'matches' | 'pulse' | 'qa' | 'sessions'
  const [matchData, setMatchData] = useState({ matches: [], filtered_out_by_anti_desperation: 0 });

  const formatMsgTime = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (isToday) return timeStr;
    return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${timeStr}`;
  };

  const getTimeUntilBadge = (slotStartIso) => {
    if (!slotStartIso) return null;
    const diffMs = new Date(slotStartIso) - new Date();
    const diffHours = diffMs / (1000 * 60 * 60);
    if (diffHours < 0 && diffHours > -0.75) {
      return <span className="badge badge--danger" style={{ fontWeight: 650 }}>In Progress Now</span>;
    }
    if (diffHours < 0) {
      return <span className="badge badge--neutral">Past Session</span>;
    }
    if (diffHours <= 2) {
      const mins = Math.max(1, Math.round(diffMs / 60000));
      return <span className="badge badge--danger" style={{ fontWeight: 650 }}>Starts in {mins}m</span>;
    }
    if (diffHours <= 24) {
      return <span className="badge badge--accent">Starts in {Math.round(diffHours)}h</span>;
    }
    const days = Math.round(diffHours / 24);
    return <span className="badge badge--neutral">In {days} day{days === 1 ? '' : 's'}</span>;
  };

  // Google Account for Learner Booking
  const isGoogleProvider = user?.app_metadata?.providers?.includes('google') || user?.email?.endsWith('@gmail.com');
  const [learnerGoogleEmail, setLearnerGoogleEmail] = useState(
    user?.user_metadata?.google_email || (isGoogleProvider ? user?.email : '')
  );
  const [savingLearnerGoogle, setSavingLearnerGoogle] = useState(false);

  const handleSaveLearnerGoogle = async () => {
    if (!learnerGoogleEmail.trim()) return;
    setSavingLearnerGoogle(true);
    try {
      await supabase.auth.updateUser({
        data: { google_email: learnerGoogleEmail.trim() },
      });
      setToastMessage('Google Calendar email linked successfully.');
    } catch (err) {
      console.error('Failed to link Google email:', err);
      setToastMessage('Failed to save Google email.');
    } finally {
      setSavingLearnerGoogle(false);
    }
  };
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
  const [preflightMatches, setPreflightMatches] = useState([]);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [expandedPreflightId, setExpandedPreflightId] = useState(null);

  useEffect(() => {
    if (!showAskModal || qTitle.trim().length < 8) {
      setPreflightMatches([]);
      return;
    }
    const timer = setTimeout(async () => {
      setPreflightLoading(true);
      try {
        const res = await preflightMentorshipQuestion({ q: qTitle.trim(), skillTag: qSkillTag });
        setPreflightMatches(res.matches || []);
      } catch (err) {
        console.debug('Preflight lookup skipped:', err);
      } finally {
        setPreflightLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [showAskModal, qTitle, qSkillTag]);

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
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (initialSubTab) {
      setSubTab(initialSubTab);
    }
    if (initialConnectionId) {
      setSelectedConnId(initialConnectionId);
    }
  }, [initialSubTab, initialConnectionId]);

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
      if (initialConnectionId && conns.some((c) => c.id === initialConnectionId)) {
        setSelectedConnId(initialConnectionId);
      } else if (accepted.length > 0 && !selectedConnId) {
        setSelectedConnId(accepted[0].id);
      }
      setPulsePosts(pRes.posts || []);
      setQuestions(qRes.questions || []);
      const sessList = (sRes.sessions || []).sort(
        (a, b) => new Date(a.slot_start_iso) - new Date(b.slot_start_iso)
      );
      setSessions(sessList);
    } catch (err) {
      console.error('Failed to load learner mentorship hub:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEcosystem();
  }, []);

  const activeConnection = connections.find((c) => c.id === selectedConnId);

  useEffect(() => {
    if (!selectedConnId || !activeConnection) return;
    let isMounted = true;
    const fetchMsgs = () => {
      getConnectionMessages(selectedConnId)
        .then((res) => {
          if (isMounted) setMessages(res.messages || []);
        })
        .catch(() => {});
    };
    fetchMsgs();
    const interval = setInterval(fetchMsgs, 4000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedConnId, activeConnection?.id]);

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
          `Connected with ${connectingMentor.full_name}. Direct Messaging & 1-on-1 Calendar Booking are now unlocked.`
        );
      } else {
        setToastMessage(`Connection request sent to ${connectingMentor.full_name}.`);
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
      setPreflightMatches([]);
      setExpandedPreflightId(null);
      setToastMessage('Your question has been routed to domain-matched mentors and added to the Q&A Hub.');
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

  const handleReportContent = async (itemType, itemId, snippet, context) => {
    try {
      await flagContentItem(itemType, itemId, snippet, context, 'Flagged by learner for moderator review');
      setToastMessage('Report submitted. Content flagged for administrator review.');
    } catch {
      setToastMessage('Report submitted to moderation.');
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
    if (!activeConnection?.mentor_id || !selectedSlotIso) {
      setToastMessage('Please select an available 45-minute slot.');
      return;
    }
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
        `Session confirmed for ${res.session.display_label}. Meeting room & calendar invites generated.`
      );
      setSessionNotes('');
      const [sRes, slotsRes] = await Promise.all([
        getMentorshipSessions('learner'),
        getMentorAvailableSlots(activeConnection.mentor_id, 10),
      ]);
      setSessions(sRes.sessions || []);
      const newSlots = slotsRes.slots || [];
      setAvailableSlots(newSlots);
      setSelectedSlotIso(newSlots[0]?.slot_start_iso || '');
      setSessionsSubView('chat');
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
    <div style={{ maxWidth: '1040px', margin: '0 auto', textAlign: 'left' }}>
      {/* Sub-navigation bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '18px',
        }}
      >
        <div className="segmented-tabs" role="tablist" aria-label="Mentorship sections">
          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'matches'}
            className={`segmented-tab ${subTab === 'matches' ? 'segmented-tab--active' : ''}`}
            onClick={() => setSubTab('matches')}
          >
            <Compass size={14} />
            <span>Matched Mentors</span>
            <span className="segmented-tab__count">{matchData.matches?.length || 0}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'pulse'}
            className={`segmented-tab ${subTab === 'pulse' ? 'segmented-tab--active' : ''}`}
            onClick={() => setSubTab('pulse')}
          >
            <Radio size={14} />
            <span>Mentor Pulse</span>
            <span className="segmented-tab__count">{pulsePosts.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'qa'}
            className={`segmented-tab ${subTab === 'qa' ? 'segmented-tab--active' : ''}`}
            onClick={() => setSubTab('qa')}
          >
            <HelpCircle size={14} />
            <span>Q&amp;A Knowledge Base</span>
            <span className="segmented-tab__count">{questions.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'sessions'}
            className={`segmented-tab ${subTab === 'sessions' ? 'segmented-tab--active' : ''}`}
            onClick={() => setSubTab('sessions')}
          >
            <MessageSquare size={14} />
            <span>Messages &amp; 1:1 Sessions</span>
            <span className="segmented-tab__count">{acceptedConnections.length}</span>
          </button>
        </div>

        {subTab === 'qa' && (
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => {
              setShowAskModal(true);
            }}
          >
            <Plus size={14} />
            <span>Ask a Question</span>
          </button>
        )}
      </div>

      {loading ? (
        <MentorCardSkeleton count={3} />
      ) : (
        <>
          {/* SUB-TAB 1: MATCHED MENTORS */}
          {subTab === 'matches' && (
            <div>
              {/* Quiet, trustworthy explanation banner */}
              <div
                style={{
                  marginBottom: '18px',
                  padding: '13px 16px',
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  <ShieldCheck size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                  <span>
                    Showing mentors aligned with <strong style={{ color: 'var(--text-primary)' }}>{career?.title || matchData.learner_career}</strong> and your current skill gaps
                    {matchData.filtered_out_by_anti_desperation > 0
                      ? ` (${matchData.filtered_out_by_anti_desperation} unrelated profiles hidden)`
                      : ''}.
                  </span>
                </div>
                <span className="badge badge--neutral">
                  Min relevance: {Math.round((matchData.anti_desperation_threshold || 0.45) * 100)}%
                </span>
              </div>

              {matchData.matches?.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '44px 24px' }}>
                  <h3 style={{ marginBottom: '6px' }}>No direct mentor matches above threshold</h3>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '520px', margin: '0 auto 18px', fontSize: '0.88rem' }}>
                    {matchData.zero_match_reason ||
                      'We only recommend 1-on-1 mentors whose verified skills overlap with your career path.'}
                  </p>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => {
                      setSubTab('qa');
                      setShowAskModal(true);
                    }}
                  >
                    <HelpCircle size={14} />
                    <span>Ask a Question on the Q&amp;A Board Instead</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                  {matchData.matches.map((mentor) => {
                    const connStatus = mentor.connection_status;
                    return (
                      <div
                        key={mentor.mentor_id}
                        className="card"
                        style={{
                          padding: '20px 22px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '14px',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
                            <span
                              className={`badge ${
                                mentor.match_tier === 'strong' ? 'badge--success' : 'badge--accent'
                              }`}
                            >
                              {mentor.match_badge} · {mentor.match_percent}%
                            </span>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              <Star size={12} style={{ color: 'var(--status-warning)' }} />
                              <span>{mentor.avg_rating || 4.9} ({mentor.verified_sessions_count || 12} sessions)</span>
                            </span>
                          </div>

                          <h3 style={{ fontSize: '1.08rem', marginBottom: '2px' }}>{mentor.full_name}</h3>
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '8px' }}>
                            <span className="badge badge--success" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                              <ShieldCheck size={11} /> {mentor.is_verified ? 'Verified Advisor' : 'Industry Mentor'}
                            </span>
                            {mentor.trust_score && (
                              <span className="badge badge--accent" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                                {mentor.trust_score}% Trust Rating
                              </span>
                            )}
                            {mentor.has_google && (
                              <span className="badge badge--neutral" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                                Google Synced
                              </span>
                            )}
                            {mentor.has_linkedin && (
                              <span className="badge badge--neutral" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                                LinkedIn Verified
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.82rem', color: 'var(--accent)', fontWeight: 500, marginBottom: '8px' }}>
                            {mentor.headline}
                          </div>
                          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '12px' }}>
                            {mentor.bio}
                          </p>

                          <div
                            style={{
                              padding: '10px 12px',
                              background: 'var(--surface-subtle)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 'var(--r-sm)',
                              marginBottom: '12px',
                            }}
                          >
                            <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '3px' }}>
                              Why this mentor matches
                            </div>
                            <div style={{ fontSize: '0.81rem', color: 'var(--text-primary)' }}>
                              {mentor.match_explanation}
                            </div>
                            {mentor.shared_gap_skills?.length > 0 && (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '7px' }}>
                                {mentor.shared_gap_skills.map((sk) => (
                                  <span key={sk} className="badge badge--accent" style={{ fontSize: '0.69rem' }}>
                                    <Target size={10} /> {sk}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                            {(mentor.expertise_skills || []).slice(0, 6).map((sk) => (
                              <span key={sk} className="badge badge--neutral">
                                {sk}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <Calendar size={12} />
                            <span>
                              {(mentor.available_days || []).join(', ')} ({mentor.preferred_time_window}) ·{' '}
                              {mentor.active_mentees_count}/{mentor.max_mentees} mentees
                            </span>
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
                              <MessageSquare size={13} />
                              <span>Message &amp; Book 1:1</span>
                            </button>
                          ) : connStatus === 'pending' ? (
                            <span className="badge badge--warning">
                              <Clock size={11} /> Pending
                            </span>
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
                              <UserCheck size={13} />
                              <span>Connect</span>
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {connectingMentor && (
                <div className="modal-backdrop">
                  <form
                    className="modal-panel"
                    onSubmit={handleSendConnectionRequest}
                    style={{ maxWidth: '480px' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <h3>Connect with {connectingMentor.full_name}</h3>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setConnectingMentor(null)}
                        aria-label="Close modal"
                      >
                        <X size={16} />
                      </button>
                    </div>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Your mentor will see your target career and top skill gaps so they can tailor your 1-on-1 sessions.
                    </p>

                    <div className="form-group">
                      <label className="form-label">Introductory note</label>
                      <textarea
                        className="input"
                        rows={3}
                        value={goalNote}
                        onChange={(e) => setGoalNote(e.target.value)}
                        required
                      />
                    </div>

                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.81rem',
                        color: 'var(--accent)',
                        marginBottom: '18px',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={autoAcceptDemo}
                        onChange={(e) => setAutoAcceptDemo(e.target.checked)}
                      />
                      <Sparkles size={13} />
                      <span>Instant accept for testing (unlocks DMs &amp; calendar booking immediately)</span>
                    </label>

                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setConnectingMentor(null)}
                      >
                        Cancel
                      </button>
                      <button type="submit" className="btn btn--primary btn--sm" disabled={submittingConn}>
                        {submittingConn ? 'Sending...' : 'Send Request'}
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          )}

          {/* SUB-TAB 2: MENTOR PULSE FEED */}
          {subTab === 'pulse' && (
            <div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
                {['', 'Industry Insight', 'Event / Webinar', 'Career & Hiring Advice'].map((cat) => (
                  <button
                    key={cat || 'all'}
                    type="button"
                    className={`btn btn--sm ${pulseFilter === cat ? 'btn--primary' : 'btn--secondary'}`}
                    onClick={() => setPulseFilter(cat)}
                  >
                    {cat || 'All Posts'}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {displayedPulse.map((post) => (
                  <div key={post.id} className="card" style={{ padding: '20px 22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap', marginBottom: '8px' }}>
                      <div>
                        <span className="badge badge--accent" style={{ marginBottom: '6px' }}>
                          {post.post_type}
                        </span>
                        <h3 style={{ fontSize: '1.06rem', marginBottom: '2px' }}>{post.title}</h3>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          <strong style={{ color: 'var(--text-primary)' }}>{post.mentor_name}</strong> · {post.mentor_headline}
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          type="button"
                          className="btn btn--secondary btn--xs"
                          onClick={() => handleToggleLike(post.id)}
                        >
                          <ThumbsUp size={12} />
                          <span>{post.likes_count || 0} Helpful</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost btn--xs"
                          onClick={() => handleReportContent('pulse_post', post.id, post.title, 'Mentor Pulse Feed')}
                          title="Report post to administrator"
                          style={{ color: 'var(--text-muted)' }}
                        >
                          <Flag size={12} />
                          <span>Report</span>
                        </button>
                      </div>
                    </div>

                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.62, whiteSpace: 'pre-line', marginBottom: '12px' }}>
                      {post.body}
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                        {(post.skill_tags || []).map((tag) => (
                          <span key={tag} className="badge badge--neutral">
                            #{tag}
                          </span>
                        ))}
                      </div>

                      {post.external_url && (
                        <a
                          href={post.external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn--ghost btn--xs"
                          style={{ color: 'var(--accent)' }}
                        >
                          <span>Reference link</span>
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SUB-TAB 3: Q&A KNOWLEDGE BASE */}
          {subTab === 'qa' && (
            <div>
              <form
                className="card"
                onSubmit={handleSearchQuestions}
                style={{
                  padding: '14px 18px',
                  marginBottom: '16px',
                  display: 'flex',
                  gap: '10px',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <div style={{ position: 'relative', flex: 2, minWidth: '220px' }}>
                  <Search
                    size={14}
                    style={{ position: 'absolute', left: '11px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                  />
                  <input
                    type="text"
                    className="input"
                    placeholder="Search answered mentor questions..."
                    value={qaSearch}
                    onChange={(e) => setQaSearch(e.target.value)}
                    style={{ paddingLeft: '32px' }}
                  />
                </div>
                <input
                  type="text"
                  className="input"
                  placeholder="Filter by skill (e.g. SQL)"
                  value={qaSkillFilter}
                  onChange={(e) => setQaSkillFilter(e.target.value)}
                  style={{ flex: 1, minWidth: '160px' }}
                />
                <button type="submit" className="btn btn--primary btn--sm">
                  Search
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

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {questions.map((q) => (
                  <div key={q.id} className="card" style={{ padding: '20px 22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span className="badge badge--accent">
                          #{q.skill_tag}
                        </span>
                        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                          Asked by <strong style={{ color: 'var(--text-primary)' }}>{q.learner_name}</strong> · {q.career_title}
                        </span>
                      </div>
                      {q.source_lesson_title && (
                        <span className="badge badge--warning">
                          <BookOpen size={11} /> Lesson: {q.source_lesson_title}
                        </span>
                      )}
                    </div>

                    <h3 style={{ fontSize: '1.04rem', marginBottom: '4px' }}>{q.title}</h3>
                    <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                      {q.body}
                    </p>

                    {q.answers?.length === 0 ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 12px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        <Clock size={13} />
                        <span>Routed to domain mentors — awaiting response.</span>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {q.answers.map((ans) => (
                          <div
                            key={ans.id}
                            style={{
                              padding: '12px 14px',
                              background: 'var(--surface-subtle)',
                              borderLeft: '3px solid var(--accent)',
                              borderRadius: 'var(--r-sm)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '4px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', fontSize: '0.82rem' }}>
                                <strong>{ans.mentor_name}</strong>
                                <span style={{ color: 'var(--text-muted)' }}>
                                  ({ans.mentor_headline})
                                </span>
                                <span className="badge badge--success" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                                  <Check size={10} /> Verified Mentor
                                </span>
                              </div>

                              <button
                                type="button"
                                className="btn btn--secondary btn--xs"
                                onClick={() => handleUpvoteAnswer(q.id, ans.id)}
                              >
                                <ThumbsUp size={11} />
                                <span>Upvote ({ans.upvotes || 0})</span>
                              </button>
                            </div>
                            <div style={{ fontSize: '0.86rem', color: 'var(--text-primary)', lineHeight: 1.58 }}>
                              {ans.body}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {showAskModal && (
                <div className="modal-backdrop">
                  <form
                    className="modal-panel"
                    onSubmit={handleAskQuestion}
                    style={{ maxWidth: '520px' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <h3>Ask a Domain Mentor</h3>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setShowAskModal(false)}
                        aria-label="Close modal"
                      >
                        <X size={16} />
                      </button>
                    </div>
                    <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Your question is routed to mentors with matching skill expertise and saved in the Q&amp;A Knowledge Base.
                    </p>

                    {qSourceLesson && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px', padding: '8px 12px', background: 'var(--accent-soft)', borderRadius: 'var(--r-sm)', fontSize: '0.79rem', color: 'var(--accent)' }}>
                        <BookOpen size={13} />
                        <span>Linked lesson: <strong>{qSourceLesson}</strong></span>
                      </div>
                    )}

                    <div className="form-group">
                      <label className="form-label">Related Skill</label>
                      <input
                        type="text"
                        className="input"
                        value={qSkillTag}
                        onChange={(e) => setQSkillTag(e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Question Summary</label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. When should I use a window function over GROUP BY?"
                        value={qTitle}
                        onChange={(e) => setQTitle(e.target.value)}
                        required
                      />
                    </div>

                    {preflightMatches.length > 0 && (
                      <div
                        style={{
                          background: 'var(--surface-raised, #1f2937)',
                          border: '1px solid var(--border-color, #374151)',
                          borderRadius: 'var(--r-sm, 6px)',
                          padding: '12px',
                          marginBottom: '14px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent, #6366f1)' }}>
                            Similar verified answers found in knowledge base
                          </span>
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                            {preflightMatches.length} existing match{preflightMatches.length > 1 ? 'es' : ''}
                          </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {preflightMatches.map((match) => {
                            const topAns = match.answers && match.answers[0];
                            const isExpanded = expandedPreflightId === match.id;
                            return (
                              <div
                                key={match.id}
                                style={{
                                  padding: '8px 10px',
                                  borderRadius: 'var(--r-sm, 6px)',
                                  background: 'var(--surface-ground, #111827)',
                                  border: '1px solid var(--border-color, #2d3748)',
                                  fontSize: '0.8rem',
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                                  <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                    {match.title}
                                  </div>
                                  <span style={{ fontSize: '0.72rem', color: 'var(--accent)', whiteSpace: 'nowrap', fontWeight: 600 }}>
                                    {Math.round((match.similarity || 0) * 100)}% match
                                  </span>
                                </div>
                                {topAns && (
                                  <div style={{ marginTop: '6px' }}>
                                    <p
                                      style={{
                                        color: 'var(--text-secondary)',
                                        margin: 0,
                                        fontSize: '0.78rem',
                                        lineHeight: '1.4',
                                        display: isExpanded ? 'block' : '-webkit-box',
                                        WebkitLineClamp: isExpanded ? 'unset' : 2,
                                        WebkitBoxOrient: 'vertical',
                                        overflow: isExpanded ? 'visible' : 'hidden',
                                      }}
                                    >
                                      {topAns.body}
                                    </p>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                                      <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                                        Answered by {topAns.mentor_name || 'Verified Mentor'}
                                      </span>
                                      <button
                                        type="button"
                                        className="btn btn--ghost btn--xs"
                                        style={{ fontSize: '0.72rem', padding: '2px 6px' }}
                                        onClick={() => setExpandedPreflightId(isExpanded ? null : match.id)}
                                      >
                                        {isExpanded ? 'Collapse' : 'Expand answer'}
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <div className="form-group">
                      <label className="form-label">Context &amp; Details</label>
                      <textarea
                        className="input"
                        rows={4}
                        placeholder="Describe the scenario or concept you want clarified..."
                        value={qBody}
                        onChange={(e) => setQBody(e.target.value)}
                        required
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setShowAskModal(false)}
                      >
                        Cancel
                      </button>
                      <button type="submit" className="btn btn--primary btn--sm" disabled={submittingQ}>
                        {submittingQ ? 'Posting...' : 'Post Question'}
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          )}

          {/* SUB-TAB 4: DIRECT MESSAGES & 1-ON-1 BOOKING */}
          {subTab === 'sessions' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              {acceptedConnections.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '44px 24px' }}>
                  <h3 style={{ marginBottom: '6px' }}>Connect with a mentor first</h3>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto 16px', fontSize: '0.88rem' }}>
                    Direct messaging and 1-on-1 session booking unlock once a mentor accepts your connection request.
                  </p>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => setSubTab('matches')}
                  >
                    <Compass size={14} />
                    <span>Browse Matched Mentors</span>
                  </button>
                </div>
              ) : (
                /* Direct Messages & Scheduled Sessions (Sessions scheduled by mentors) */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                  <div className="card">
                    {/* Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Direct Messages</h3>
                        {acceptedConnections.length > 1 ? (
                          <select
                            className="input"
                            value={selectedConnId || ''}
                            onChange={(e) => setSelectedConnId(e.target.value)}
                            style={{ width: 'auto', padding: '4px 10px', fontSize: '0.82rem' }}
                          >
                            {acceptedConnections.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.mentor?.full_name || 'Connected Mentor'}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="badge badge--accent" style={{ fontSize: '0.78rem' }}>
                            {activeConnection?.mentor?.full_name || 'Connected Mentor'}
                          </span>
                        )}
                      </div>

                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        1-on-1 sessions are scheduled by mentors
                      </span>
                    </div>

                    {/* Messages Container */}
                    <div
                      style={{
                        height: '380px',
                        overflowY: 'auto',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                        padding: '14px',
                        background: 'var(--surface-subtle)',
                        borderRadius: 'var(--r-sm)',
                        border: '1px solid var(--border)',
                        marginBottom: '14px',
                      }}
                    >
                      {messages.length === 0 ? (
                        <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem', margin: 'auto', padding: '24px' }}>
                          No messages yet. Say hello to {activeConnection?.mentor?.full_name || 'your mentor'}!
                        </div>
                      ) : (
                        messages.map((m) => {
                          const isMe = m.sender_role === 'learner';
                          return (
                            <div
                              key={m.id}
                              style={{
                                alignSelf: isMe ? 'flex-end' : 'flex-start',
                                maxWidth: '78%',
                                padding: '9px 12px',
                                borderRadius: 'var(--r-sm)',
                                background: isMe ? 'var(--accent-soft)' : 'var(--surface)',
                                border: '1px solid',
                                borderColor: isMe ? 'var(--accent-border)' : 'var(--border)',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '3px' }}>
                                <span style={{ fontWeight: 600 }}>{isMe ? 'You' : activeConnection?.mentor?.full_name || 'Mentor'}</span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span style={{ fontSize: '0.67rem' }}>
                                    {formatMsgTime(m.created_at)}
                                  </span>
                                  {!isMe && (
                                    <button
                                      type="button"
                                      className="btn btn--ghost btn--xs"
                                      onClick={() => handleReportContent('message', m.id, m.text, 'Learner Direct Message')}
                                      title="Report message to admin"
                                      style={{ padding: '0 3px', color: 'var(--text-muted)' }}
                                    >
                                      <Flag size={10} />
                                    </button>
                                  )}
                                </div>
                              </div>
                              <div style={{ fontSize: '0.85rem', lineHeight: 1.48, color: 'var(--text-primary)' }}>{m.text}</div>
                            </div>
                          );
                        })
                      )}
                      <div ref={messagesEndRef} />
                    </div>

                    {/* Send input */}
                    <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="text"
                        className="input"
                        placeholder={`Write a message to ${activeConnection?.mentor?.full_name || 'your mentor'}...`}
                        value={msgInput}
                        onChange={(e) => setMsgInput(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <button type="submit" className="btn btn--primary btn--sm" disabled={sendingMsg || !msgInput.trim()}>
                        <Send size={13} />
                        <span>{sendingMsg ? 'Sending...' : 'Send'}</span>
                      </button>
                    </form>
                  </div>

                  {/* Scheduled Sessions List below chat (Ranked by proximity in time) */}
                  <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                      <div>
                        <h3 style={{ fontSize: '1.02rem', margin: 0 }}>
                          Scheduled 1-on-1 Sessions ({sessions.length})
                        </h3>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                          Sessions scheduled by your mentors, ranked by proximity in time.
                        </p>
                      </div>
                      <span className="badge badge--neutral" style={{ fontSize: '0.72rem' }}>
                        Ranked by proximity
                      </span>
                    </div>

                    {sessions.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '28px 16px', color: 'var(--text-secondary)' }}>
                        <Calendar size={28} style={{ color: 'var(--text-muted)', marginBottom: '8px', opacity: 0.7 }} />
                        <h4 style={{ margin: '0 0 4px', fontSize: '0.94rem', color: 'var(--text-primary)' }}>
                          No upcoming 1-on-1 sessions scheduled
                        </h4>
                        <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)', maxWidth: '440px', marginLeft: 'auto', marginRight: 'auto' }}>
                          Your mentor will schedule 1-on-1 review sessions with you based on your skill gaps. Message them above to coordinate availability.
                        </p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {sessions.map((sess) => (
                          <div
                            key={sess.id}
                            style={{
                              padding: '14px 16px',
                              background: 'var(--surface-subtle)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-sm)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                                  {sess.topic} · with <span style={{ color: 'var(--accent)' }}>{sess.mentor_name}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '3px', flexWrap: 'wrap' }}>
                                  <Clock size={12} />
                                  <span>{sess.display_label || new Date(sess.slot_start_iso).toLocaleString()}</span>
                                  <span>· ID:</span>
                                  <code>{sess.meeting_code}</code>
                                </div>
                                {sess.focus_skill && (
                                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                                    Focus skill: <strong>{sess.focus_skill}</strong>
                                    {sess.endorsed_skill && (
                                      <span style={{ color: 'var(--status-success)', marginLeft: '8px', fontWeight: 600 }}>
                                        Endorsed (+15% Proficiency)
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                              <div>
                                {getTimeUntilBadge(sess.slot_start_iso)}
                              </div>
                            </div>

                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
                              {sess.meeting_url && sess.status === 'confirmed' && (
                                <a
                                  href={sess.meeting_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn btn--primary btn--xs"
                                >
                                  <Video size={13} />
                                  <span>Join Video Room ({sess.meeting_code})</span>
                                </a>
                              )}
                              {sess.google_calendar_url && (
                                <a
                                  href={sess.google_calendar_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn btn--secondary btn--xs"
                                >
                                  <Calendar size={13} />
                                  <span>Google Calendar</span>
                                </a>
                              )}
                              <a
                                href={getSessionIcsDownloadUrl(sess.id)}
                                download
                                className="btn btn--secondary btn--xs"
                              >
                                <Download size={13} />
                                <span>Download .ics</span>
                              </a>
                              {sess.status === 'confirmed' && (
                                <button
                                  type="button"
                                  className="btn btn--ghost btn--xs"
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
