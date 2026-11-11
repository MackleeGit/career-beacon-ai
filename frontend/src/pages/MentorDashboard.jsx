// src/pages/MentorDashboard.jsx
import { useState, useEffect, useRef } from 'react';
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
  getMentorshipQuestions,
  answerMentorshipQuestion,
  upvoteMentorshipAnswer,
  getMentorshipSessions,
  bookMentorshipSession,
  completeMentorshipSession,
  getSessionIcsDownloadUrl,
  resetMentorAccount,
  flagContentItem,
} from '../lib/api';
import Toast from '../components/Toast';
import ThemeSelector from '../components/ThemeSelector';
import NotificationBell from '../components/NotificationBell';
import { MentorCardSkeleton } from '../components/Skeleton';
import {
  Compass,
  Users,
  HelpCircle,
  Radio,
  MessageSquare,
  Calendar,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  X,
  LogOut,
  Check,
  CheckCircle2,
  Award,
  Clock,
  Video,
  Download,
  Send,
  ThumbsUp,
  BookOpen,
  Settings,
  AlertTriangle,
  RotateCcw,
  Plus,
  User,
  ShieldCheck,
  Flag,
} from '../components/Icons';

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MentorDashboard({ user, userProfile, onRecalibrateCareer }) {
  const [activeTab, setActiveTab] = useState('roster'); // 'roster' | 'qa' | 'pulse' | 'messages' | 'calendar' | 'account'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true); // Closed / compact by default on load
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mentorProfile, setMentorProfile] = useState(null);
  const [connections, setConnections] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [pulsePosts, setPulsePosts] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);

  // Sub-tab toggles
  const [pulseSubTab, setPulseSubTab] = useState('feed'); // 'feed' | 'publish'
  const [pulseDomainFilter, setPulseDomainFilter] = useState('all'); // 'all' | 'mine'
  const [qaSubTab, setQaSubTab] = useState('answer'); // 'answer' | 'explore'
  const [calendarSubTab, setCalendarSubTab] = useState('upcoming'); // 'upcoming' | 'schedule' | 'history' | 'availability'

  // Direct Messaging state
  const [selectedConnId, setSelectedConnId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [msgText, setMsgText] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

  // Mentor-Initiated Session Booking state
  const [bookingMenteeId, setBookingMenteeId] = useState('');
  const [bookingTopic, setBookingTopic] = useState('1-on-1 Career & Technical Guidance');
  const [bookingDate, setBookingDate] = useState('');
  const [bookingTime, setBookingTime] = useState('17:00');
  const [bookingSkill, setBookingSkill] = useState('');
  const [bookingNotes, setBookingNotes] = useState('');
  const [submittingBooking, setSubmittingBooking] = useState(false);

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

  // Account Space state
  const [accountName, setAccountName] = useState('');
  const [accountHeadline, setAccountHeadline] = useState('');
  const [accountBio, setAccountBio] = useState('');
  const [accountDomain, setAccountDomain] = useState('');
  const [savingAccount, setSavingAccount] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [resettingAccount, setResettingAccount] = useState(false);

  // Connected Accounts / Integrations
  const isGoogleProvider = user?.app_metadata?.providers?.includes('google') || user?.email?.endsWith('@gmail.com');
  const [googleEmail, setGoogleEmail] = useState(
    user?.user_metadata?.google_email || (isGoogleProvider ? user?.email : '')
  );
  const [linkedinUrl, setLinkedinUrl] = useState(user?.user_metadata?.linkedin_url || '');
  const [githubHandle, setGithubHandle] = useState(user?.user_metadata?.github_username || '');
  const [savingIntegrations, setSavingIntegrations] = useState(false);

  const handleSaveIntegrations = async (e) => {
    e?.preventDefault();
    setSavingIntegrations(true);
    try {
      await supabase.auth.updateUser({
        data: {
          google_email: googleEmail.trim(),
          linkedin_url: linkedinUrl.trim(),
          github_username: githubHandle.trim(),
        },
      });
      setToastMessage('Connected accounts updated successfully.');
    } catch (err) {
      console.error('Failed to update integrations:', err);
      setToastMessage('Failed to update connected accounts.');
    } finally {
      setSavingIntegrations(false);
    }
  };

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
        setAccountName(mp.full_name || userProfile?.full_name || '');
        setAccountHeadline(mp.headline || userProfile?.headline || '');
        setAccountBio(mp.bio || userProfile?.bio || '');
        setAccountDomain(mp.primary_domain || '');
      }

      const conns = connRes.connections || [];
      setConnections(conns);
      const accepted = conns.filter((c) => c.status === 'accepted');
      if (accepted.length > 0 && !selectedConnId) {
        setSelectedConnId(accepted[0].id);
      }
      if (accepted.length > 0 && !bookingMenteeId) {
        setBookingMenteeId(accepted[0].learner_id);
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
    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const [connRes, sessRes] = await Promise.all([
          getMentorshipConnections('mentor'),
          getMentorshipSessions('mentor'),
        ]);
        if (isMounted) {
          setConnections(connRes.connections || []);
          setSessions(sessRes.sessions || []);
        }
      } catch {}
    }, 8000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!selectedConnId) return;
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
  }, [selectedConnId]);

  const activeConnection = connections.find((c) => c.id === selectedConnId);

  const handleRespondConnection = async (connectionId, action) => {
    try {
      await respondToConnectionRequest(connectionId, action);
      setToastMessage(
        action === 'accept'
          ? 'Connection accepted. You can now message and schedule 1-on-1 sessions with this mentee.'
          : 'Connection request declined.'
      );
      await loadWorkspace();
    } catch (err) {
      setToastMessage(err.message || 'Failed to update connection.');
    }
  };

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

  const handleReportContent = async (itemType, itemId, snippet, context) => {
    try {
      await flagContentItem(itemType, itemId, snippet, context, 'Flagged by mentor for moderator review');
      setToastMessage('Report submitted. Content flagged for administrator review.');
    } catch {
      setToastMessage('Report submitted to moderation.');
    }
  };

  const handleSubmitAnswer = async (questionId) => {
    if (!answerDraft.trim()) return;
    setSubmittingAnswer(true);
    try {
      await answerMentorshipQuestion(questionId, answerDraft.trim());
      setAnswerDraft('');
      setAnsweringQuestionId(null);
      setToastMessage('Verified Mentor Answer published to the Q&A Knowledge Base.');
      const qRes = await getMentorshipQuestions({ forMentor: true });
      setQuestions(qRes.questions || []);
    } catch (err) {
      setToastMessage(err.message || 'Failed to post answer.');
    } finally {
      setSubmittingAnswer(false);
    }
  };

  const handleUpvoteAnswer = async (questionId, answerId) => {
    try {
      await upvoteMentorshipAnswer(questionId, answerId);
      const qRes = await getMentorshipQuestions({ forMentor: true });
      setQuestions(qRes.questions || []);
      setToastMessage('Upvote recorded.');
    } catch (err) {
      setToastMessage(err.message || 'Failed to upvote.');
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
      setToastMessage('Published to Mentor Pulse Feed.');
      const pulseRes = await getMentorPulseFeed();
      setPulsePosts(pulseRes.posts || []);
      setPulseSubTab('feed');
    } catch (err) {
      setToastMessage(err.message || 'Failed to publish post.');
    } finally {
      setPublishingPulse(false);
    }
  };

  const handleMentorBookSession = async (e) => {
    e.preventDefault();
    if (!bookingMenteeId || !bookingDate || !bookingTime) {
      setToastMessage('Please select a mentee, date, and time.');
      return;
    }
    setSubmittingBooking(true);
    try {
      const slotIso = new Date(`${bookingDate}T${bookingTime}:00`).toISOString();
      await bookMentorshipSession({
        mentor_id: user?.id,
        learner_id: bookingMenteeId,
        slot_start_iso: slotIso,
        topic: bookingTopic.trim() || '1-on-1 Mentorship Guidance Session',
        focus_skill: bookingSkill.trim() || undefined,
        notes: bookingNotes.trim() || undefined,
      });
      setToastMessage('Session scheduled successfully. Calendar invite and Jitsi room generated.');
      setCalendarSubTab('upcoming');
      const sessRes = await getMentorshipSessions('mentor');
      setSessions(sessRes.sessions || []);
    } catch (err) {
      setToastMessage(err.message || 'Failed to schedule session.');
    } finally {
      setSubmittingBooking(false);
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
          ? `Session marked complete. Endorsed "${endorseSkill.trim()}" with qualitative mentor review.`
          : 'Session marked complete.'
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
      setToastMessage('Availability & capacity settings updated.');
    } catch (err) {
      setToastMessage(err.message || 'Failed to update settings.');
    } finally {
      setSavingAvail(false);
    }
  };

  const handleSaveAccountProfile = async (e) => {
    e.preventDefault();
    setSavingAccount(true);
    try {
      const res = await updateMyMentorProfile({
        headline: accountHeadline.trim(),
        bio: accountBio.trim(),
        primary_domain: accountDomain.trim(),
      });
      if (accountName.trim() && user?.id) {
        await supabase.from('profiles').update({ full_name: accountName.trim() }).eq('id', user.id);
      }
      setMentorProfile(res.mentor);
      setToastMessage('Account profile updated successfully.');
    } catch (err) {
      setToastMessage(err.message || 'Failed to update account.');
    } finally {
      setSavingAccount(false);
    }
  };

  const handleConfirmResetMentorAccount = async () => {
    setResettingAccount(true);
    try {
      await resetMentorAccount();
      setToastMessage('Mentor profile reset. Restarting onboarding...');
      setShowResetModal(false);
      if (onRecalibrateCareer) {
        onRecalibrateCareer();
      } else {
        window.location.reload();
      }
    } catch (err) {
      setToastMessage(err.message || 'Failed to reset account.');
      setResettingAccount(false);
    }
  };

  const pendingConnections = connections.filter((c) => c.status === 'pending');
  const acceptedConnections = connections.filter((c) => c.status === 'accepted');
  const upcomingSessions = sessions.filter((s) => s.status === 'confirmed');
  const pastSessions = sessions.filter((s) => s.status === 'completed' || s.status === 'cancelled');
  const displayName = mentorProfile?.full_name || userProfile?.full_name || user?.email || 'Mentor';

  // Pulse posts filtered by mentor domain if toggled
  const filteredPulsePosts = pulseDomainFilter === 'mine' && mentorProfile?.primary_domain
    ? pulsePosts.filter((p) => {
        const matchesDomain = p.primary_domain?.toLowerCase() === mentorProfile.primary_domain?.toLowerCase();
        const matchesSkill = (p.skill_tags || []).some((tag) =>
          (mentorProfile.expertise_skills || []).some((esk) => esk.toLowerCase() === tag.toLowerCase())
        );
        return matchesDomain || matchesSkill;
      })
    : pulsePosts;

  const navItems = [
    { id: 'roster', label: 'Mentees & Requests', Icon: Users, badge: connections.length },
    { id: 'qa', label: 'Learner Q&A Inbox', Icon: HelpCircle, badge: questions.length },
    { id: 'pulse', label: 'Mentor Pulse', Icon: Radio },
    { id: 'messages', label: 'Direct Messages', Icon: MessageSquare, badge: acceptedConnections.length },
    { id: 'calendar', label: 'Calendar & 1:1s', Icon: Calendar, badge: upcomingSessions.length },
    { id: 'account', label: 'Account & Settings', Icon: Settings },
  ];

  const activeNavMeta = navItems.find((i) => i.id === activeTab) || navItems[0];

  const handleToggleSidebar = () => {
    if (window.innerWidth <= 900) {
      setMobileMenuOpen((o) => !o);
    } else {
      setSidebarCollapsed((c) => !c);
    }
  };

  return (
    <div className="app-shell">
      {mobileMenuOpen && (
        <div
          className="app-sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Persistent Sidebar (starts collapsed by default) */}
      <aside
        className={`app-sidebar ${sidebarCollapsed ? 'app-sidebar--collapsed' : ''} ${
          mobileMenuOpen ? 'app-sidebar--mobile-open' : ''
        }`}
        aria-label="Mentor Sidebar Navigation"
      >
        <div className="app-sidebar__header">
          <div className="logo-mark" style={{ overflow: 'hidden' }}>
            <div className="logo-mark__icon">
              <Compass size={16} />
            </div>
            {!sidebarCollapsed && <span>Career Beacon</span>}
          </div>

          <button
            type="button"
            className="btn btn--ghost btn--sm desktop-collapse-btn"
            onClick={() => setSidebarCollapsed((c) => !c)}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{ padding: '5px' }}
          >
            {sidebarCollapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </button>
        </div>

        {!sidebarCollapsed && (
          <div
            style={{
              margin: '12px 10px 4px',
              padding: '11px 12px',
              borderRadius: 'var(--r-sm)',
              background: 'var(--surface-subtle)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
              Mentorship Domain
            </div>
            <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.3, marginBottom: '6px' }}>
              {mentorProfile?.primary_domain || 'Industry Mentorship'}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              <span>Capacity</span>
              <strong className="mono" style={{ color: 'var(--accent)' }}>
                {acceptedConnections.length} / {mentorProfile?.max_mentees || 5} mentees
              </strong>
            </div>
          </div>
        )}

        <nav className="app-sidebar__nav" aria-label="Mentor Workspace Sections">
          {!sidebarCollapsed && <div className="app-sidebar__section-label">Workspace</div>}
          {navItems.map(({ id, label, Icon, badge }) => {
            const isActive = activeTab === id;
            return (
              <button
                key={id}
                type="button"
                className={`nav-item ${isActive ? 'nav-item--active' : ''}`}
                onClick={() => {
                  setActiveTab(id);
                  if (mobileMenuOpen) setMobileMenuOpen(false);
                }}
                title={sidebarCollapsed ? label : undefined}
              >
                <Icon size={17} className="nav-item__icon" />
                {!sidebarCollapsed && <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>}
                {!sidebarCollapsed && badge !== undefined && badge > 0 && (
                  <span className="nav-item__badge">{badge}</span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="app-sidebar__footer">
          {!sidebarCollapsed && (
            <div style={{ padding: '4px 8px', marginBottom: '2px' }}>
              <div style={{ fontSize: '0.81rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {displayName}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.email}
              </div>
            </div>
          )}
          <button
            id="sign-out-btn"
            type="button"
            className="nav-item"
            onClick={() => setShowLogoutToast(true)}
            style={{ color: 'var(--text-secondary)' }}
            title="Sign out"
          >
            <LogOut size={16} className="nav-item__icon" />
            {!sidebarCollapsed && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="app-topbar__left">
            <button
              type="button"
              className="topbar-sidebar-toggle"
              onClick={handleToggleSidebar}
              aria-label="Toggle navigation sidebar"
              title="Toggle sidebar"
            >
              <Menu size={18} />
            </button>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: 650, color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>
                {activeNavMeta.label}
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                · Mentor Workspace
              </span>
            </div>
          </div>

          <div className="app-topbar__right">
            <NotificationBell
              role="mentor"
              sessions={sessions}
              connections={connections}
              activeTab={activeTab}
              activeConnectionId={selectedConnId}
              onNavigate={(tab, subTab, connId) => {
                setActiveTab(tab);
                if (connId) setSelectedConnId(connId);
                if (mobileMenuOpen) setMobileMenuOpen(false);
              }}
              onNotifyToast={setToastMessage}
            />
            <ThemeSelector />
          </div>
        </header>

        <main className="app-content">
          {/* Header Summary Banner */}
          {activeTab !== 'account' && (
            <div className="card" style={{ marginBottom: '20px', padding: '18px 22px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '2px' }}>
                    {mentorProfile?.primary_domain || 'Industry Mentorship'}
                  </div>
                  <h1 style={{ fontSize: '1.35rem', marginBottom: '3px' }}>
                    {displayName}
                  </h1>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                    {mentorProfile?.headline || userProfile?.headline || 'Verified Career Beacon Mentor'}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn--secondary btn--xs"
                  onClick={() => setActiveTab('account')}
                  style={{ gap: '5px' }}
                >
                  <Settings size={13} />
                  <span>Account Settings</span>
                </button>
              </div>

              {mentorProfile?.expertise_skills?.length > 0 && (
                <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {mentorProfile.expertise_skills.map((sk) => (
                    <span key={sk} className="badge badge--accent" style={{ fontSize: '0.72rem' }}>
                      <Check size={11} /> {sk}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Identity & Integration Alert if Google / LinkedIn missing */}
          {(!googleEmail || !linkedinUrl) && activeTab !== 'account' && (
            <div
              style={{
                marginBottom: '20px',
                padding: '12px 18px',
                background: 'var(--surface-subtle)',
                border: '1px solid var(--accent-border)',
                borderRadius: 'var(--r-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
                flexWrap: 'wrap',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldCheck size={20} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Increase Your Mentor Trust Score &amp; Enable 1:1 Calendar Bookings
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Mentors with verified Google Calendar and LinkedIn integrations earn verified badges and higher placement in learner matches.
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="btn btn--secondary btn--xs"
                onClick={() => setActiveTab('account')}
              >
                Connect in Settings
              </button>
            </div>
          )}

          {loading ? (
            <MentorCardSkeleton />
          ) : (
            <>
              {/* TAB 1: ROSTER & REQUESTS */}
              {activeTab === 'roster' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div className="card">
                    <h3 style={{ fontSize: '1.05rem', marginBottom: '4px' }}>
                      Pending Mentorship Requests ({pendingConnections.length})
                    </h3>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      Learners seeking your guidance on their career roadmap and technical skill gaps.
                    </p>

                    {pendingConnections.length === 0 ? (
                      <div style={{ padding: '18px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', color: 'var(--text-muted)', fontSize: '0.86rem' }}>
                        No pending requests. Incoming mentee connection requests will appear here.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {pendingConnections.map((conn) => (
                          <div
                            key={conn.id}
                            style={{
                              padding: '16px 18px',
                              background: 'var(--surface-subtle)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-md)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                              <div>
                                <h4 style={{ margin: 0, fontSize: '0.98rem' }}>
                                  {conn.learner_snapshot?.learner_name || 'Aspiring Professional'}
                                </h4>
                                <div style={{ fontSize: '0.8rem', color: 'var(--accent)', marginTop: '2px', fontWeight: 500 }}>
                                  Target Career: {conn.learner_snapshot?.target_career || 'Career Track'} ({conn.learner_snapshot?.avg_proficiency || 0}% current readiness)
                                </div>
                              </div>

                              <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                  type="button"
                                  className="btn btn--primary btn--sm"
                                  onClick={() => handleRespondConnection(conn.id, 'accept')}
                                >
                                  Accept Request
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
                              <div style={{ marginTop: '10px', padding: '9px 12px', background: 'var(--surface)', borderRadius: 'var(--r-sm)', fontSize: '0.84rem', border: '1px solid var(--border-subtle)' }}>
                                <strong>Goal note:</strong> &ldquo;{conn.goal_note}&rdquo;
                              </div>
                            )}

                            {conn.learner_snapshot?.top_skill_gaps?.length > 0 && (
                              <div style={{ marginTop: '10px' }}>
                                <div style={{ fontSize: '0.73rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '5px' }}>
                                  Priority skill gaps
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                  {conn.learner_snapshot.top_skill_gaps.map((g) => (
                                    <span key={g.name} className="badge badge--warning">
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

                  <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <h3 style={{ fontSize: '1.05rem', margin: 0 }}>
                        Connected Mentees ({acceptedConnections.length})
                      </h3>
                      <button
                        type="button"
                        className="btn btn--secondary btn--xs"
                        onClick={() => {
                          setCalendarSubTab('schedule');
                          setActiveTab('calendar');
                        }}
                      >
                        <Calendar size={12} />
                        <span>Schedule 1:1 Session</span>
                      </button>
                    </div>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
                      Active mentees who can message you directly and attend scheduled 1-on-1 calendar sessions.
                    </p>

                    {acceptedConnections.length === 0 ? (
                      <div style={{ padding: '18px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', color: 'var(--text-muted)', fontSize: '0.86rem' }}>
                        No connected mentees yet. Accept a request above to unlock Direct Messaging and 1-on-1 Session Scheduling.
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: '12px' }}>
                        {acceptedConnections.map((conn) => (
                          <div
                            key={conn.id}
                            style={{
                              padding: '15px 16px',
                              background: 'var(--surface-subtle)',
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
                                <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                                  {conn.learner_snapshot?.learner_name || 'Connected Learner'}
                                </strong>
                                <span className="badge badge--success">Connected</span>
                              </div>
                              <div style={{ fontSize: '0.8rem', color: 'var(--accent)', marginTop: '3px', fontWeight: 500 }}>
                                {conn.learner_snapshot?.target_career || 'Career Track'} ({conn.learner_snapshot?.avg_proficiency || 0}% readiness)
                              </div>

                              {conn.learner_snapshot?.top_skill_gaps?.length > 0 && (
                                <div style={{ marginTop: '8px' }}>
                                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                    Current gaps:
                                  </div>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                                    {conn.learner_snapshot.top_skill_gaps.map((g) => (
                                      <span key={g.name} className="badge badge--neutral">
                                        {g.name}: {g.proficiency}%
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>

                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                type="button"
                                className="btn btn--secondary btn--sm"
                                style={{ flex: 1 }}
                                onClick={() => {
                                  setSelectedConnId(conn.id);
                                  setActiveTab('messages');
                                }}
                              >
                                <MessageSquare size={13} />
                                <span>Message</span>
                              </button>
                              <button
                                type="button"
                                className="btn btn--ghost btn--sm"
                                onClick={() => {
                                  setBookingMenteeId(conn.learner_id);
                                  setCalendarSubTab('schedule');
                                  setActiveTab('calendar');
                                }}
                                title="Schedule 1:1"
                              >
                                <Calendar size={13} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: LEARNER Q&A INBOX (Togglable) */}
              {activeTab === 'qa' && (
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Learner Q&amp;A Knowledge Exchange</h3>
                      <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', margin: '2px 0 0' }}>
                        Answer mentee challenges or explore community discussions in your domain.
                      </p>
                    </div>

                    <div className="segmented-tabs" style={{ width: 'auto' }}>
                      <button
                        type="button"
                        className={`segmented-tab ${qaSubTab === 'answer' ? 'segmented-tab--active' : ''}`}
                        onClick={() => setQaSubTab('answer')}
                      >
                        Answer Questions ({questions.length})
                      </button>
                      <button
                        type="button"
                        className={`segmented-tab ${qaSubTab === 'explore' ? 'segmented-tab--active' : ''}`}
                        onClick={() => setQaSubTab('explore')}
                      >
                        Explore Domain Posts
                      </button>
                    </div>
                  </div>

                  {qaSubTab === 'answer' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      {questions.length === 0 ? (
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', padding: '16px 0' }}>
                          No mentee questions currently pending in your domain.
                        </p>
                      ) : (
                        questions.map((q) => (
                          <div
                            key={q.id}
                            style={{
                              padding: '16px 18px',
                              background: 'var(--surface-subtle)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--r-md)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                                <span className="badge badge--accent">#{q.skill_tag}</span>
                                <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                                  Asked by <strong style={{ color: 'var(--text-primary)' }}>{q.learner_name}</strong> ({q.career_title})
                                </span>
                                {q.mentor_skill_match && (
                                  <span className="badge badge--success">Matches your stack</span>
                                )}
                              </div>
                              {q.source_lesson_title && (
                                <span className="badge badge--warning">
                                  <BookOpen size={11} /> Lesson: {q.source_lesson_title}
                                </span>
                              )}
                            </div>

                            <h4 style={{ marginBottom: '4px', fontSize: '0.98rem' }}>{q.title}</h4>
                            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                              {q.body}
                            </p>

                            {q.answers?.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                                {q.answers.map((ans) => (
                                  <div
                                    key={ans.id}
                                    style={{
                                      padding: '11px 14px',
                                      background: 'var(--surface)',
                                      borderLeft: '3px solid var(--accent)',
                                      borderRadius: 'var(--r-sm)',
                                    }}
                                  >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '3px' }}>
                                      <span>
                                        <strong>{ans.mentor_name}</strong> · <span style={{ color: 'var(--status-success)', fontWeight: 600 }}>Verified Mentor</span>
                                      </span>
                                      <button
                                        type="button"
                                        className="btn btn--ghost btn--xs"
                                        onClick={() => handleUpvoteAnswer(q.id, ans.id)}
                                        style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                      >
                                        <ThumbsUp size={11} /> {ans.upvotes || 0}
                                      </button>
                                    </div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.55 }}>
                                      {ans.body}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {answeringQuestionId === q.id ? (
                              <div style={{ marginTop: '10px' }}>
                                <textarea
                                  className="input"
                                  rows={3}
                                  placeholder="Write your verified practical guidance or code solution..."
                                  value={answerDraft}
                                  onChange={(e) => setAnswerDraft(e.target.value)}
                                  style={{ marginBottom: '8px' }}
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
                                    {submittingAnswer ? 'Publishing...' : 'Publish Answer'}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button
                                type="button"
                                className="btn btn--secondary btn--xs"
                                onClick={() => {
                                  setAnsweringQuestionId(q.id);
                                  setAnswerDraft('');
                                }}
                              >
                                Write Answer
                              </button>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {questions.filter((q) => q.answers && q.answers.length > 0).length === 0 ? (
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem', padding: '16px 0' }}>
                          No answered domain discussions recorded yet.
                        </p>
                      ) : (
                        questions
                          .filter((q) => q.answers && q.answers.length > 0)
                          .map((q) => (
                            <div
                              key={q.id}
                              style={{
                                padding: '15px 16px',
                                background: 'var(--surface-subtle)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--r-md)',
                              }}
                            >
                              <div style={{ display: 'flex', gap: '6px', marginBottom: '4px' }}>
                                <span className="badge badge--accent">#{q.skill_tag}</span>
                                <span className="badge badge--neutral">{q.career_title}</span>
                              </div>
                              <h4 style={{ fontSize: '0.94rem', margin: '0 0 6px' }}>{q.title}</h4>
                              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '0 0 10px' }}>
                                {q.body}
                              </p>
                              {q.answers.map((ans) => (
                                <div
                                  key={ans.id}
                                  style={{
                                    padding: '10px 12px',
                                    background: 'var(--surface)',
                                    borderRadius: 'var(--r-sm)',
                                    borderLeft: '3px solid var(--accent)',
                                    marginBottom: '6px',
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                                    <strong style={{ color: 'var(--text-primary)' }}>{ans.mentor_name}</strong>
                                    <button
                                      type="button"
                                      className="btn btn--ghost btn--xs"
                                      onClick={() => handleUpvoteAnswer(q.id, ans.id)}
                                      style={{ color: 'var(--text-muted)', gap: '4px' }}
                                    >
                                      <ThumbsUp size={11} /> {ans.upvotes || 0}
                                    </button>
                                  </div>
                                  <div style={{ fontSize: '0.83rem', color: 'var(--text-secondary)' }}>
                                    {ans.body}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ))
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: MENTOR PULSE (Togglable Between Feed and Upload) */}
              {activeTab === 'pulse' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="card" style={{ padding: '14px 20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                      <div>
                        <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Mentor Pulse Feed</h3>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '2px 0 0' }}>
                          Discover industry insights, workshop announcements, and technical paradigms.
                        </p>
                      </div>

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <div className="segmented-tabs" style={{ width: 'auto' }}>
                          <button
                            type="button"
                            className={`segmented-tab ${pulseSubTab === 'feed' ? 'segmented-tab--active' : ''}`}
                            onClick={() => setPulseSubTab('feed')}
                          >
                            Browse Feed ({filteredPulsePosts.length})
                          </button>
                          <button
                            type="button"
                            className={`segmented-tab ${pulseSubTab === 'publish' ? 'segmented-tab--active' : ''}`}
                            onClick={() => setPulseSubTab('publish')}
                          >
                            <Plus size={12} /> Post Insight
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {pulseSubTab === 'publish' ? (
                    <form className="card" onSubmit={handlePublishPulse} style={{ maxWidth: '780px' }}>
                      <h3 style={{ fontSize: '1.05rem', marginBottom: '4px' }}>Publish to Mentor Pulse</h3>
                      <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                        Broadcast technical insights, architecture lessons, or upcoming live sessions to learners across Career Beacon.
                      </p>

                      <div className="form-group">
                        <label className="form-label">Category</label>
                        <select
                          className="input"
                          value={pulseType}
                          onChange={(e) => setPulseType(e.target.value)}
                        >
                          <option value="Industry Insight">Industry Insight</option>
                          <option value="Event / Webinar">Event / Workshop</option>
                          <option value="Career & Hiring Advice">Career &amp; Hiring Advice</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Headline / Title</label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. Critical Failure Modes in Distributed Systems / Clinical Case Prep"
                          value={pulseTitle}
                          onChange={(e) => setPulseTitle(e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Insight Body</label>
                        <textarea
                          className="input"
                          rows={5}
                          placeholder="Share actionable knowledge, case studies, or operational takeaways..."
                          value={pulseBody}
                          onChange={(e) => setPulseBody(e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Skill Tags (comma-separated)</label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. PostgreSQL, Distributed Systems, System Design"
                          value={pulseTagsInput}
                          onChange={(e) => setPulseTagsInput(e.target.value)}
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">External Resource Link (Optional)</label>
                        <input
                          type="url"
                          className="input"
                          placeholder="https://..."
                          value={pulseUrl}
                          onChange={(e) => setPulseUrl(e.target.value)}
                        />
                      </div>

                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '12px' }}>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={() => setPulseSubTab('feed')}
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="btn btn--primary btn--sm"
                          disabled={publishingPulse || !pulseTitle.trim() || !pulseBody.trim()}
                        >
                          <Radio size={13} />
                          <span>{publishingPulse ? 'Publishing...' : 'Publish to Feed'}</span>
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {/* Domain Filter Pills */}
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Filter feed:</span>
                        <button
                          type="button"
                          className={`btn btn--xs ${pulseDomainFilter === 'all' ? 'btn--primary' : 'btn--ghost'}`}
                          onClick={() => setPulseDomainFilter('all')}
                        >
                          All Communities
                        </button>
                        {mentorProfile?.primary_domain && (
                          <button
                            type="button"
                            className={`btn btn--xs ${pulseDomainFilter === 'mine' ? 'btn--primary' : 'btn--ghost'}`}
                            onClick={() => setPulseDomainFilter('mine')}
                          >
                            My Field ({mentorProfile.primary_domain})
                          </button>
                        )}
                      </div>

                      {filteredPulsePosts.length === 0 ? (
                        <div className="card" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No posts found for the selected filter. Switch to &ldquo;All Communities&rdquo; or publish an insight!
                        </div>
                      ) : (
                        filteredPulsePosts.map((post) => (
                          <div
                            key={post.id}
                            className="card"
                            style={{
                              padding: '16px 20px',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className="badge badge--accent">{post.post_type}</span>
                                {post.primary_domain && (
                                  <span className="badge badge--neutral" style={{ fontSize: '0.7rem' }}>
                                    {post.primary_domain}
                                  </span>
                                )}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                  <ThumbsUp size={11} /> {post.likes_count || 0}
                                </span>
                                <button
                                  type="button"
                                  className="btn btn--ghost btn--xs"
                                  onClick={() => handleReportContent('pulse_post', post.id, post.title, 'Mentor Pulse Feed')}
                                  title="Report post to administrator"
                                  style={{ padding: '2px 4px', color: 'var(--text-muted)' }}
                                >
                                  <Flag size={11} />
                                </button>
                              </div>
                            </div>

                            <h4 style={{ marginBottom: '4px', fontSize: '1.02rem', color: 'var(--text-primary)' }}>
                              {post.title}
                            </h4>
                            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                              {post.mentor_name} · {post.mentor_headline}
                            </div>
                            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', whiteSpace: 'pre-line', marginBottom: '10px', lineHeight: 1.55 }}>
                              {post.body}
                            </p>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                                {(post.skill_tags || []).map((t) => (
                                  <span key={t} className="badge badge--neutral">
                                    #{t}
                                  </span>
                                ))}
                              </div>

                              {post.external_url && (
                                <a
                                  href={post.external_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn btn--ghost btn--xs"
                                  style={{ color: 'var(--accent)', textDecoration: 'none' }}
                                >
                                  Reference Link &rarr;
                                </a>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: DIRECT MESSAGES */}
              {activeTab === 'messages' && (
                <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '18px', minHeight: '400px' }}>
                  <div style={{ borderRight: '1px solid var(--border-subtle)', paddingRight: '14px' }}>
                    <h4 style={{ marginBottom: '10px' }}>Connected Mentees</h4>
                    {acceptedConnections.length === 0 ? (
                      <p style={{ fontSize: '0.83rem', color: 'var(--text-muted)' }}>
                        Accept a connection request first to unlock direct messaging.
                      </p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {acceptedConnections.map((c) => (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() => setSelectedConnId(c.id)}
                            style={{
                              textAlign: 'left',
                              padding: '9px 11px',
                              borderRadius: 'var(--r-sm)',
                              border: '1px solid',
                              borderColor: selectedConnId === c.id ? 'var(--accent-border)' : 'var(--border)',
                              background: selectedConnId === c.id ? 'var(--accent-soft)' : 'var(--surface-subtle)',
                              color: 'var(--text-primary)',
                              cursor: 'pointer',
                            }}
                          >
                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                              {c.learner_snapshot?.learner_name || 'Learner'}
                            </div>
                            <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>
                              {c.learner_snapshot?.target_career || 'Career Mentee'}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    {!selectedConnId ? (
                      <div style={{ margin: 'auto', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                        Select a connected mentee on the left to view or send messages.
                      </div>
                    ) : (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: '8px' }}>
                          <div>
                            <span style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                              {activeConnection?.learner_snapshot?.learner_name || 'Mentee'}
                            </span>
                            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginLeft: '8px' }}>
                              · {activeConnection?.learner_snapshot?.target_career || 'Career Track'}
                            </span>
                          </div>
                          <button
                            type="button"
                            className="btn btn--secondary btn--xs"
                            onClick={() => {
                              if (activeConnection?.learner_id) {
                                setBookingMenteeId(activeConnection.learner_id);
                              }
                              setActiveTab('calendar');
                              setCalendarSubTab('schedule');
                            }}
                            style={{ gap: '5px' }}
                          >
                            <Calendar size={12} />
                            <span>Schedule 1:1 Session</span>
                          </button>
                        </div>

                        <div style={{ maxHeight: '310px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', paddingRight: '6px' }}>
                          {messages.length === 0 ? (
                            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem', margin: 'auto', padding: '24px 0' }}>
                              No messages yet. Send a note to start the conversation with your mentee.
                            </div>
                          ) : (
                            messages.map((m) => {
                              const isMe = m.sender_role === 'mentor';
                              return (
                                <div
                                  key={m.id}
                                  style={{
                                    alignSelf: isMe ? 'flex-end' : 'flex-start',
                                    maxWidth: '78%',
                                    padding: '9px 12px',
                                    borderRadius: 'var(--r-sm)',
                                    background: isMe ? 'var(--accent-soft)' : 'var(--surface-subtle)',
                                    border: '1px solid',
                                    borderColor: isMe ? 'var(--accent-border)' : 'var(--border)',
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '3px' }}>
                                    <span style={{ fontWeight: 600 }}>{isMe ? 'You (Mentor)' : 'Mentee'}</span>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <span style={{ fontSize: '0.67rem' }}>
                                        {formatMsgTime(m.created_at)}
                                      </span>
                                      {!isMe && (
                                        <button
                                          type="button"
                                          className="btn btn--ghost btn--xs"
                                          onClick={() => handleReportContent('message', m.id, m.text, 'Mentor Direct Message')}
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

                        <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                          <input
                            type="text"
                            className="input"
                            placeholder="Write a message..."
                            value={msgText}
                            onChange={(e) => setMsgText(e.target.value)}
                            style={{ flex: 1 }}
                          />
                          <button type="submit" className="btn btn--primary btn--sm" disabled={sendingMsg || !msgText.trim()}>
                            <Send size={13} />
                            <span>{sendingMsg ? 'Sending...' : 'Send'}</span>
                          </button>
                        </form>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 5: CALENDAR & 1:1 SESSIONS (Togglable: Upcoming, Schedule, History, Availability) */}
              {activeTab === 'calendar' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="card" style={{ padding: '14px 20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                      <div>
                        <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Calendar &amp; 1-on-1 Sessions</h3>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '2px 0 0' }}>
                          Manage appointments, initiate session bookings with mentees, and tune availability slots.
                        </p>
                      </div>

                      <div className="segmented-tabs" style={{ width: 'auto' }}>
                        <button
                          type="button"
                          className={`segmented-tab ${calendarSubTab === 'upcoming' ? 'segmented-tab--active' : ''}`}
                          onClick={() => setCalendarSubTab('upcoming')}
                        >
                          Upcoming ({upcomingSessions.length})
                        </button>
                        <button
                          type="button"
                          className={`segmented-tab ${calendarSubTab === 'schedule' ? 'segmented-tab--active' : ''}`}
                          onClick={() => setCalendarSubTab('schedule')}
                        >
                          <Plus size={12} /> Schedule 1:1
                        </button>
                        <button
                          type="button"
                          className={`segmented-tab ${calendarSubTab === 'history' ? 'segmented-tab--active' : ''}`}
                          onClick={() => setCalendarSubTab('history')}
                        >
                          History ({pastSessions.length})
                        </button>
                        <button
                          type="button"
                          className={`segmented-tab ${calendarSubTab === 'availability' ? 'segmented-tab--active' : ''}`}
                          onClick={() => setCalendarSubTab('availability')}
                        >
                          Availability
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Sub-View 1: Upcoming Sessions */}
                  {calendarSubTab === 'upcoming' && (
                    <div className="card">
                      <h4 style={{ fontSize: '0.98rem', marginBottom: '12px' }}>Confirmed Upcoming Sessions</h4>
                      {upcomingSessions.length === 0 ? (
                        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)' }}>
                          No upcoming sessions booked. Click &ldquo;Schedule 1:1&rdquo; to invite an accepted mentee or wait for a mentee booking.
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          {upcomingSessions.map((sess) => (
                            <div
                              key={sess.id}
                              style={{
                                padding: '16px',
                                background: 'var(--surface-subtle)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--r-md)',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', flexWrap: 'wrap' }}>
                                <div>
                                  <div style={{ fontWeight: 600, fontSize: '0.94rem', color: 'var(--text-primary)' }}>{sess.topic}</div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--accent)', marginTop: '4px' }}>
                                    <Clock size={12} />
                                    <span>{new Date(sess.slot_start_iso).toLocaleString()} ({sess.duration_minutes} mins)</span>
                                  </div>
                                  {sess.focus_skill && (
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                                      Focus Skill: <strong style={{ color: 'var(--text-primary)' }}>{sess.focus_skill}</strong>
                                    </div>
                                  )}
                                </div>
                                <span className="badge badge--success">Confirmed</span>
                              </div>

                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
                                {sess.meeting_url && (
                                  <a
                                    href={sess.meeting_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="btn btn--primary btn--xs"
                                  >
                                    <Video size={13} />
                                    <span>Join Jitsi Video Room</span>
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
                                <button
                                  type="button"
                                  className="btn btn--secondary btn--xs"
                                  style={{ borderColor: 'var(--accent-border)', color: 'var(--accent)' }}
                                  onClick={() => {
                                    setCompletingSession(sess);
                                    setEndorseSkill(sess.focus_skill || '');
                                  }}
                                >
                                  <Award size={13} />
                                  <span>Complete &amp; Endorse</span>
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Modal for Post-Session Skill Endorsement */}
                      {completingSession && (
                        <form
                          onSubmit={handleCompleteAndEndorse}
                          style={{
                            marginTop: '16px',
                            padding: '18px',
                            background: 'var(--surface)',
                            border: '1px solid var(--accent-border)',
                            borderRadius: 'var(--r-md)',
                          }}
                        >
                          <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                            <Award size={16} style={{ color: 'var(--accent)' }} />
                            <span>Qualitative Skill Endorsement &amp; Session Review</span>
                          </h4>
                          <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                            Record qualitative feedback and endorse competency for session: <strong>{completingSession.topic}</strong>.
                          </p>

                          <div className="form-group">
                            <label className="form-label">Endorsed Skill</label>
                            <input
                              type="text"
                              className="input"
                              placeholder="e.g. System Design, Differential Diagnosis, SQL Optimization"
                              value={endorseSkill}
                              onChange={(e) => setEndorseSkill(e.target.value)}
                            />
                          </div>

                          <div className="form-group">
                            <label className="form-label">Qualitative Notes &amp; Observations</label>
                            <textarea
                              className="input"
                              rows={3}
                              placeholder="Key strengths demonstrated, architecture critique, homework assignments..."
                              value={endorseNote}
                              onChange={(e) => setEndorseNote(e.target.value)}
                            />
                          </div>

                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '10px' }}>
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
                              {submittingEndorsement ? 'Saving...' : 'Finalize & Endorse'}
                            </button>
                          </div>
                        </form>
                      )}
                    </div>
                  )}

                  {/* Sub-View 2: Schedule Session with Mentee (Direct Mentor Booking) */}
                  {calendarSubTab === 'schedule' && (
                    <form className="card" onSubmit={handleMentorBookSession} style={{ maxWidth: '680px' }}>
                      <h4 style={{ fontSize: '1rem', marginBottom: '4px' }}>Schedule a 1-on-1 Session with Mentee</h4>
                      <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                        Invite an accepted mentee to a dedicated guidance slot. Jitsi video room and .ics invites are generated automatically.
                      </p>

                      {!googleEmail && (
                        <div
                          style={{
                            padding: '12px 14px',
                            background: 'var(--surface-subtle)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--r-sm)',
                            marginBottom: '16px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent)', fontWeight: 600, fontSize: '0.86rem', marginBottom: '4px' }}>
                            <Calendar size={15} />
                            <span>Google Calendar Synchronization (Optional)</span>
                          </div>
                          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '0 0 8px', lineHeight: 1.4 }}>
                            Jitsi video rooms and .ics calendar invites are created automatically for every session. If you wish to also sync directly to Google Calendar, enter your address:
                          </p>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                              type="email"
                              className="input"
                              placeholder="your.email@gmail.com"
                              value={googleEmail}
                              onChange={(e) => setGoogleEmail(e.target.value)}
                              style={{ height: '34px', fontSize: '0.84rem' }}
                            />
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm"
                              onClick={handleSaveIntegrations}
                              disabled={!googleEmail.trim()}
                            >
                              Save Google Email
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="form-group">
                        <label className="form-label">Select Mentee</label>
                        {acceptedConnections.length === 0 ? (
                          <div style={{ padding: '10px', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            No connected mentees yet. Accept a connection request first.
                          </div>
                        ) : (
                          <select
                            className="input"
                            value={bookingMenteeId}
                            onChange={(e) => setBookingMenteeId(e.target.value)}
                            required
                          >
                            {acceptedConnections.map((c) => (
                              <option key={c.learner_id} value={c.learner_id}>
                                {c.learner_snapshot?.learner_name || 'Learner'} ({c.learner_snapshot?.target_career || 'Mentee'})
                              </option>
                            ))}
                          </select>
                        )}
                      </div>

                      <div className="form-group">
                        <label className="form-label">Session Topic</label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. Portfolio Architecture Review, Clinical Case Preparation"
                          value={bookingTopic}
                          onChange={(e) => setBookingTopic(e.target.value)}
                          required
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div className="form-group">
                          <label className="form-label">Date</label>
                          <input
                            type="date"
                            className="input"
                            value={bookingDate}
                            onChange={(e) => setBookingDate(e.target.value)}
                            required
                          />
                        </div>
                        <div className="form-group">
                          <label className="form-label">Time</label>
                          <input
                            type="time"
                            className="input"
                            value={bookingTime}
                            onChange={(e) => setBookingTime(e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Focus Skill (Optional)</label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. System Design, Diagnostic Strategy"
                          value={bookingSkill}
                          onChange={(e) => setBookingSkill(e.target.value)}
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Prep Notes / Prerequisites</label>
                        <textarea
                          className="input"
                          rows={2}
                          placeholder="Items mentee should have ready before the call..."
                          value={bookingNotes}
                          onChange={(e) => setBookingNotes(e.target.value)}
                        />
                      </div>

                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '12px' }}>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={() => setCalendarSubTab('upcoming')}
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="btn btn--primary btn--sm"
                          disabled={submittingBooking || acceptedConnections.length === 0}
                        >
                          {submittingBooking ? 'Scheduling...' : 'Confirm Appointment'}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* Sub-View 3: Session History */}
                  {calendarSubTab === 'history' && (
                    <div className="card">
                      <h4 style={{ fontSize: '0.98rem', marginBottom: '12px' }}>Session History &amp; Completed Reviews</h4>
                      {pastSessions.length === 0 ? (
                        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--surface-subtle)', borderRadius: 'var(--r-sm)' }}>
                          No completed or past sessions on record yet.
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          {pastSessions.map((sess) => (
                            <div
                              key={sess.id}
                              style={{
                                padding: '14px 16px',
                                background: 'var(--surface-subtle)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--r-md)',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <strong style={{ fontSize: '0.92rem' }}>{sess.topic}</strong>
                                <span className={`badge ${sess.status === 'completed' ? 'badge--success' : 'badge--neutral'}`} style={{ textTransform: 'capitalize' }}>
                                  {sess.status}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                {new Date(sess.slot_start_iso).toLocaleDateString()} · {sess.duration_minutes} mins
                              </div>
                              {sess.endorsed_skill && (
                                <div style={{ marginTop: '6px', fontSize: '0.82rem', color: 'var(--accent)' }}>
                                  <ShieldCheck size={12} /> Endorsed Skill: <strong>{sess.endorsed_skill}</strong>
                                </div>
                              )}
                              {sess.feedback_note && (
                                <div style={{ marginTop: '6px', padding: '8px 10px', background: 'var(--surface)', borderRadius: 'var(--r-sm)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                  &ldquo;{sess.feedback_note}&rdquo;
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Sub-View 4: Weekly Availability Settings */}
                  {calendarSubTab === 'availability' && (
                    <div className="card" style={{ maxWidth: '640px' }}>
                      <h4 style={{ fontSize: '1rem', marginBottom: '4px' }}>Weekly Availability &amp; Booking Window</h4>
                      <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                        Define standard open windows so learners can reserve double-booking-filtered 45-minute slots.
                      </p>

                      <div className="form-group">
                        <label className="form-label">Available Days</label>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {DAYS_OF_WEEK.map((day) => {
                            const isSelected = availDays.includes(day);
                            return (
                              <button
                                key={day}
                                type="button"
                                className={`btn btn--xs ${isSelected ? 'btn--primary' : 'btn--secondary'}`}
                                onClick={() => {
                                  setAvailDays((prev) =>
                                    isSelected ? prev.filter((d) => d !== day) : [...prev, day]
                                  );
                                }}
                              >
                                {day}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Preferred Time Window</label>
                        <select
                          className="input"
                          value={availWindow}
                          onChange={(e) => setAvailWindow(e.target.value)}
                        >
                          <option value="Morning">Morning (09:00 &ndash; 12:00)</option>
                          <option value="Afternoon">Afternoon (13:00 &ndash; 17:00)</option>
                          <option value="Evening">Evening (18:00 &ndash; 21:00)</option>
                        </select>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        <div className="form-group">
                          <label className="form-label">Hours / Week ({availHours}h)</label>
                          <input
                            type="range"
                            min={1}
                            max={20}
                            value={availHours}
                            onChange={(e) => setAvailHours(e.target.value)}
                            style={{ width: '100%' }}
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label">Max Active Mentees ({availMaxMentees})</label>
                          <input
                            type="range"
                            min={1}
                            max={15}
                            value={availMaxMentees}
                            onChange={(e) => setAvailMaxMentees(e.target.value)}
                            style={{ width: '100%' }}
                          />
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
                        <button
                          type="button"
                          className="btn btn--primary btn--sm"
                          onClick={handleSaveAvailability}
                          disabled={savingAvail || availDays.length === 0}
                        >
                          {savingAvail ? 'Saving...' : 'Save Availability'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: ACCOUNT & SETTINGS SPACE */}
              {activeTab === 'account' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '780px' }}>
                  <form className="card" onSubmit={handleSaveAccountProfile}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                      <div
                        style={{
                          width: '44px',
                          height: '44px',
                          borderRadius: '50%',
                          background: 'var(--accent-soft)',
                          color: 'var(--accent)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '1.2rem',
                          fontWeight: 700,
                        }}
                      >
                        {displayName.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h3 style={{ fontSize: '1.1rem', margin: 0 }}>Mentor Profile &amp; Account Settings</h3>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {user?.email} · Registered Industry Mentor
                        </div>
                      </div>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Full Name</label>
                      <input
                        type="text"
                        className="input"
                        value={accountName}
                        onChange={(e) => setAccountName(e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Professional Headline</label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. Principal Systems Architect | Cloud Strategy"
                        value={accountHeadline}
                        onChange={(e) => setAccountHeadline(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Primary Occupational Domain</label>
                      <input
                        type="text"
                        className="input"
                        placeholder="e.g. Software Architecture, Family Care Medicine"
                        value={accountDomain}
                        onChange={(e) => setAccountDomain(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Biography &amp; Coaching Philosophy</label>
                      <textarea
                        className="input"
                        rows={4}
                        placeholder="Share your technical background, guidance methodology, and mentee expectations..."
                        value={accountBio}
                        onChange={(e) => setAccountBio(e.target.value)}
                      />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
                      <button
                        type="submit"
                        className="btn btn--primary btn--sm"
                        disabled={savingAccount || !accountName.trim()}
                      >
                        {savingAccount ? 'Saving Changes...' : 'Save Profile Changes'}
                      </button>
                    </div>
                  </form>

                  {/* Connected Accounts & External Identity */}
                  <form className="card" onSubmit={handleSaveIntegrations}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                      <div>
                        <h3 style={{ fontSize: '1.05rem', margin: '0 0 4px' }}>Connected Accounts &amp; Verified Identity</h3>
                        <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', margin: 0 }}>
                          Connect your professional accounts to enable Google Calendar synchronization, verified mentor badges, and portfolio validation.
                        </p>
                      </div>
                      <span className="badge badge--success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={12} /> Jitsi Video Ready
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
                      <div className="form-group" style={{ margin: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                          <label className="form-label" style={{ margin: 0 }}>
                            Google Account (Optional Calendar Sync)
                          </label>
                          <span style={{ fontSize: '0.74rem', color: googleEmail ? 'var(--status-success)' : 'var(--text-muted)', fontWeight: 600 }}>
                            {googleEmail ? 'Active for Invites' : 'Optional'}
                          </span>
                        </div>
                        <input
                          type="email"
                          className="input"
                          placeholder="your.mentor.email@gmail.com"
                          value={googleEmail}
                          onChange={(e) => setGoogleEmail(e.target.value)}
                        />
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                          Mentorship session invites, Jitsi meeting reminders, and attendee notifications will synchronize to this Google address.
                        </div>
                      </div>

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ marginBottom: '4px' }}>
                          LinkedIn Profile URL (Verified Mentor Credential)
                        </label>
                        <input
                          type="url"
                          className="input"
                          placeholder="https://linkedin.com/in/yourprofile"
                          value={linkedinUrl}
                          onChange={(e) => setLinkedinUrl(e.target.value)}
                        />
                      </div>

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ marginBottom: '4px' }}>
                          GitHub Username (Technical Background &amp; Open Source Proof)
                        </label>
                        <input
                          type="text"
                          className="input"
                          placeholder="e.g. octocat"
                          value={githubHandle}
                          onChange={(e) => setGithubHandle(e.target.value)}
                        />
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                      <button
                        type="submit"
                        className="btn btn--primary btn--sm"
                        disabled={savingIntegrations}
                      >
                        {savingIntegrations ? 'Saving Integrations...' : 'Save Connected Accounts'}
                      </button>
                    </div>
                  </form>

                  {/* DANGER ZONE: RESTART ONBOARDING */}
                  <div className="danger-zone-card">
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                      <div style={{ color: 'var(--status-danger)', marginTop: '2px' }}>
                        <AlertTriangle size={24} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ color: 'var(--status-danger)', fontSize: '1.02rem', margin: '0 0 4px' }}>
                          Danger Zone &ndash; Restart Mentor Onboarding
                        </h4>
                        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '0 0 14px', lineHeight: 1.5 }}>
                          Restarting your onboarding will permanently erase your mentor profile, declared expertise competencies, active mentee connections, published pulse posts, and all scheduled calendar sessions. This action is irreversible.
                        </p>
                        <button
                          type="button"
                          className="btn btn--danger btn--sm"
                          onClick={() => setShowResetModal(true)}
                        >
                          <RotateCcw size={13} />
                          <span>Restart Mentor Onboarding</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* RESTART ONBOARDING CONFIRMATION MODAL */}
      {showResetModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.72)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            zIndex: 100,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '520px',
              width: '100%',
              padding: '24px',
              border: '1px solid var(--status-danger-bd)',
              boxShadow: 'var(--shadow-xl)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px', color: 'var(--status-danger)' }}>
              <AlertTriangle size={22} />
              <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Restart Onboarding &amp; Wipe Progress?</h3>
            </div>

            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '14px' }}>
              Are you sure you want to restart onboarding? You will <strong>lose all active mentee connections, message history, scheduled sessions, and published insights</strong>.
            </p>

            <div
              style={{
                padding: '12px',
                background: 'var(--status-danger-bg)',
                borderRadius: 'var(--r-sm)',
                border: '1px solid var(--status-danger-bd)',
                fontSize: '0.82rem',
                color: 'var(--status-danger)',
                marginBottom: '18px',
              }}
            >
              This action cannot be undone. You will immediately be routed back to Step 1 of Mentor Onboarding.
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setShowResetModal(false)}
                disabled={resettingAccount}
              >
                Keep My Profile
              </button>
              <button
                type="button"
                className="btn btn--danger btn--sm"
                onClick={handleConfirmResetMentorAccount}
                disabled={resettingAccount}
              >
                {resettingAccount ? 'Resetting...' : 'Yes, Delete Everything & Restart'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* LOGOUT CONFIRMATION TOAST */}
      {showLogoutToast && (
        <div
          role="dialog"
          aria-label="Sign out confirmation"
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 9999,
            background: 'var(--surface-elevated)',
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--r-md)',
            boxShadow: 'var(--shadow-lg)',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            maxWidth: '380px',
          }}
        >
          <span style={{ fontSize: '0.88rem', color: 'var(--text-primary)' }}>
            Are you sure you want to sign out?
          </span>
          <button
            type="button"
            className="btn btn--ghost btn--xs"
            onClick={() => setShowLogoutToast(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--primary btn--xs"
            onClick={async () => {
              await supabase.auth.signOut();
              window.location.reload();
            }}
          >
            Sign out
          </button>
        </div>
      )}

      {toastMessage && (
        <Toast
          message={toastMessage}
          onClose={() => setToastMessage(null)}
        />
      )}
    </div>
  );
}
