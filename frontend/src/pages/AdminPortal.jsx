// src/pages/AdminPortal.jsx
import { Fragment, useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';
import {
  getAdminStats,
  getAdminPendingCareers,
  reviewAdminCareer,
  getAdminMentors,
  verifyAdminMentor,
  getAdminFlaggedContent,
  takeAdminModerationAction,
  getAdminIngestionOverview,
  getAdminIngestionLessons,
  triggerAdminIngestion,
  getAdminIngestionPriorities,
  runAdminNightlyBatch,
  runAdminDailyDropBatch,
  getAdminIngestionBatches,
  updateAdminBatchStatus,
  editAdminIngestionLesson,
} from '../lib/api';
import ThemeSelector from '../components/ThemeSelector';
import Toast from '../components/Toast';
import { Skeleton } from '../components/Skeleton';
import {
  ShieldCheck,
  LayoutDashboard,
  Layers,
  Users,
  AlertTriangle,
  CheckCircle2,
  Menu,
  X,
  LogOut,
  RefreshCw,
  Search,
  Check,
  Trash2,
  Award,
  GitCommit,
  Edit3,
  ExternalLink,
} from '../components/Icons';

export default function AdminPortal({ user, onSignOut }) {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'taxonomy' | 'mentors' | 'moderation'
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [pendingCareers, setPendingCareers] = useState([]);
  const [mentors, setMentors] = useState([]);
  const [flaggedItems, setFlaggedItems] = useState([]);
  const [toastMessage, setToastMessage] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Content Ingestion & Reservoir State
  const [ingestionSubTab, setIngestionSubTab] = useState('workers'); // 'workers' | 'batches' | 'skills' | 'lessons'
  const [loadingIngestion, setLoadingIngestion] = useState(true);
  const [ingestionOverview, setIngestionOverview] = useState(null);
  const [reservoirLessons, setReservoirLessons] = useState([]);
  const [skillPriorities, setSkillPriorities] = useState([]);
  const [ingestionBatches, setIngestionBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [editingLesson, setEditingLesson] = useState(null);
  const [editForm, setEditForm] = useState({
    title: '',
    summary: '',
    concept_overview: '',
    practice_scenario: '',
    difficulty_level: 2,
    quizzes: [],
  });
  const [savingLesson, setSavingLesson] = useState(false);
  const [selectedCareer, setSelectedCareer] = useState('Backend Software Engineer');
  const [selectedSkill, setSelectedSkill] = useState('RESTful API Design & Integration');
  const [ingestionLogs, setIngestionLogs] = useState([]);
  const [ingesting, setIngesting] = useState(false);
  const [batchIngesting, setBatchIngesting] = useState(false);
  const [batchPersonalizing, setBatchPersonalizing] = useState(false);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [statsRes, careersRes, mentorsRes, flagsRes] = await Promise.all([
        getAdminStats(),
        getAdminPendingCareers(),
        getAdminMentors(),
        getAdminFlaggedContent(),
      ]);
      setStats(statsRes.stats || null);
      setPendingCareers(careersRes.pending_careers || []);
      setMentors(mentorsRes.mentors || []);
      setFlaggedItems(flagsRes.flagged_items || []);
    } catch (err) {
      console.error('Failed to load admin data:', err);
      setToastMessage('Failed to load system metrics.');
    } finally {
      setLoading(false);
    }
  };

  const loadIngestionData = async () => {
    setLoadingIngestion(true);
    try {
      const results = await Promise.allSettled([
        getAdminIngestionOverview(),
        getAdminIngestionLessons(250),
        getAdminIngestionPriorities(),
        getAdminIngestionBatches(),
      ]);

      const [overviewRes, lessonsRes, prioritiesRes, batchesRes] = results;

      if (overviewRes.status === 'fulfilled') {
        setIngestionOverview(overviewRes.value);
      } else {
        console.warn('Overview fetch error:', overviewRes.reason);
      }

      if (lessonsRes.status === 'fulfilled') {
        setReservoirLessons(lessonsRes.value?.lessons || []);
      } else {
        console.warn('Lessons fetch error:', lessonsRes.reason);
      }

      if (prioritiesRes.status === 'fulfilled') {
        setSkillPriorities(prioritiesRes.value?.priorities || []);
      } else {
        console.warn('Priorities fetch error:', prioritiesRes.reason);
      }

      if (batchesRes.status === 'fulfilled') {
        setIngestionBatches(batchesRes.value?.batches || []);
      } else {
        console.warn('Batches fetch error:', batchesRes.reason);
      }
    } catch (err) {
      console.error('Failed to load ingestion data:', err);
    } finally {
      setLoadingIngestion(false);
    }
  };

  const handleBatchStatusChange = async (batchId, newStatus) => {
    try {
      const res = await updateAdminBatchStatus(batchId, newStatus);
      setToastMessage(res.message || `Commit status updated to ${newStatus}.`);
      await loadIngestionData();
    } catch (err) {
      setToastMessage(`Failed to update batch: ${err.message}`);
    }
  };

  const handleOpenEditLesson = (lesson) => {
    setEditingLesson(lesson);
    setEditForm({
      title: lesson.title || '',
      summary: lesson.summary || '',
      concept_overview: lesson.concept_overview || '',
      practice_scenario: lesson.practice_scenario || '',
      difficulty_level: lesson.difficulty_level || 2,
      quizzes: lesson.quizzes || [],
    });
  };

  const handleSaveEditLesson = async () => {
    if (!editingLesson) return;
    setSavingLesson(true);
    try {
      await editAdminIngestionLesson(editingLesson.id, editForm);
      setToastMessage(`Lesson '${editForm.title}' successfully updated.`);
      setEditingLesson(null);
      await loadIngestionData();
    } catch (err) {
      setToastMessage(`Failed to save lesson: ${err.message}`);
    } finally {
      setSavingLesson(false);
    }
  };

  const handleRunSingleIngestion = async (careerOverride = null, skillOverride = null) => {
    const targetCareer = typeof careerOverride === 'string' ? careerOverride : selectedCareer;
    const targetSkill = typeof skillOverride === 'string' ? skillOverride : selectedSkill;
    if (!targetCareer || !targetSkill) return;
    setIngesting(true);
    setIngestionLogs([`[${new Date().toLocaleTimeString()}] Triggering Live Ingestion for '${targetSkill}' (${targetCareer})...`]);
    try {
      const res = await triggerAdminIngestion(targetCareer, targetSkill);
      if (res.logs) setIngestionLogs(res.logs);
      if (res.lesson) {
        setReservoirLessons((prev) => [res.lesson, ...prev.filter((l) => l.id !== res.lesson.id)]);
        setToastMessage(`Seeded lesson '${res.lesson.title}' into Supabase reservoir.`);
      }
      await loadIngestionData();
    } catch (err) {
      const msg = err.message || 'Ingestion failed.';
      setIngestionLogs((prev) => [...prev, `[ERROR] ${msg}`]);
      setToastMessage(msg);
    } finally {
      setIngesting(false);
    }
  };

  const handleRunNightlyBatch = async () => {
    setBatchIngesting(true);
    setIngestionLogs([`[${new Date().toLocaleTimeString()}] Launching Nightly Autonomous Ingestion Worker sweep across deficit skills...`]);
    try {
      const res = await runAdminNightlyBatch(5, 3, false);
      if (res.logs) setIngestionLogs(res.logs);
      setToastMessage(`Nightly Ingestion sweep completed. Committed ${res.seeded_count || 0} lessons (${res.rejected_count || 0} rejected by quality gates).`);
      await loadIngestionData();
    } catch (err) {
      const msg = err.message || 'Nightly batch ingestion failed.';
      setIngestionLogs((prev) => [...prev, `[ERROR] ${msg}`]);
      setToastMessage(msg);
    } finally {
      setBatchIngesting(false);
    }
  };

  const handleRunDailyDropBatch = async () => {
    setBatchPersonalizing(true);
    setIngestionLogs([`[${new Date().toLocaleTimeString()}] Launching Daily Drop Personalization Worker for all registered learners...`]);
    try {
      const res = await runAdminDailyDropBatch();
      if (res.logs) setIngestionLogs(res.logs);
      setToastMessage(`Daily Drop Personalization completed for ${res.curated_count || 0} learners.`);
    } catch (err) {
      const msg = err.message || 'Daily Drop batch failed.';
      setIngestionLogs((prev) => [...prev, `[ERROR] ${msg}`]);
      setToastMessage(msg);
    } finally {
      setBatchPersonalizing(false);
    }
  };

  useEffect(() => {
    loadAdminData();
    loadIngestionData();
  }, []);

  const handleApproveCareer = async (careerId, title) => {
    setActionInProgress(true);
    try {
      await reviewAdminCareer(careerId, 'approve');
      setToastMessage(`Career "${title}" approved and verified.`);
      setPendingCareers((prev) => prev.filter((c) => c.id !== careerId));
      if (stats) setStats({ ...stats, unreviewed_careers: Math.max(0, stats.unreviewed_careers - 1) });
    } catch (err) {
      setToastMessage(err.message || 'Failed to approve career.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRejectCareer = async (careerId, title) => {
    setActionInProgress(true);
    try {
      await reviewAdminCareer(careerId, 'reject');
      setToastMessage(`Career "${title}" rejected and archived.`);
      setPendingCareers((prev) => prev.filter((c) => c.id !== careerId));
    } catch (err) {
      setToastMessage(err.message || 'Failed to reject career.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleToggleMentorVerify = async (mentorId, currentStatus) => {
    setActionInProgress(true);
    try {
      const nextStatus = !currentStatus;
      await verifyAdminMentor(mentorId, nextStatus);
      setMentors((prev) =>
        prev.map((m) => (m.mentor_id === mentorId ? { ...m, is_verified: nextStatus } : m))
      );
      setToastMessage(nextStatus ? 'Verified badge granted.' : 'Verified badge revoked.');
    } catch (err) {
      setToastMessage(err.message || 'Failed to update verification.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleModerationAction = async (itemId, action, itemType) => {
    setActionInProgress(true);
    try {
      const res = await takeAdminModerationAction(action, itemId, itemType);
      setFlaggedItems((prev) => prev.filter((f) => f.id !== itemId));
      if (action === 'delete' && itemType === 'recommendation') {
        loadIngestionData();
      }
      setToastMessage(res?.message || (action === 'dismiss' ? 'Flag dismissed.' : 'Content removed & moderation record updated.'));
    } catch (err) {
      setToastMessage(err.message || 'Failed to perform moderation action.');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    if (onSignOut) onSignOut();
  };

  return (
    <div className="app-shell" style={{ display: 'flex', minHeight: '100vh', background: 'var(--background)' }}>
      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="app-sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Admin Sidebar */}
      <aside className={`app-sidebar ${mobileMenuOpen ? 'app-sidebar--mobile-open' : ''}`} style={{ width: '260px' }}>
        <div className="app-sidebar__header">
          <div className="logo-mark">
            <div className="logo-mark__icon" style={{ background: 'var(--accent)' }}>
              <ShieldCheck size={18} style={{ color: '#fff' }} />
            </div>
            <span style={{ fontWeight: 700 }}>Admin Console</span>
          </div>

          <button
            type="button"
            className="btn btn--ghost btn--sm mobile-menu-btn"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
            style={{ padding: '4px' }}
          >
            <X size={16} />
          </button>
        </div>

        <nav className="app-sidebar__nav" aria-label="Admin Navigation">
          <div className="app-sidebar__section-label">Operations</div>
          <button
            type="button"
            className={`nav-item ${activeTab === 'overview' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('overview');
              setMobileMenuOpen(false);
            }}
          >
            <LayoutDashboard size={17} className="nav-item__icon" />
            <span>Overview &amp; Metrics</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'taxonomy' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('taxonomy');
              setMobileMenuOpen(false);
            }}
          >
            <Layers size={17} className="nav-item__icon" />
            <span style={{ flex: 1 }}>Taxonomy Review</span>
            {pendingCareers.length > 0 && (
              <span className="nav-item__badge">
                {pendingCareers.length}
              </span>
            )}
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'mentors' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('mentors');
              setMobileMenuOpen(false);
            }}
          >
            <Users size={17} className="nav-item__icon" />
            <span>Mentor Verification</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'moderation' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('moderation');
              setMobileMenuOpen(false);
            }}
          >
            <AlertTriangle size={17} className="nav-item__icon" />
            <span style={{ flex: 1 }}>Safety &amp; Moderation</span>
            {flaggedItems.length > 0 && (
              <span className="nav-item__badge">
                {flaggedItems.length}
              </span>
            )}
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'ingestion' ? 'nav-item--active' : ''}`}
            onClick={() => {
              setActiveTab('ingestion');
              setMobileMenuOpen(false);
              loadIngestionData();
            }}
          >
            <RefreshCw size={17} className="nav-item__icon" />
            <span style={{ flex: 1 }}>Content Ingestion</span>
            {ingestionOverview?.total_lessons !== undefined && (
              <span className="nav-item__badge">
                {ingestionOverview.total_lessons}
              </span>
            )}
          </button>
        </nav>

        <div className="app-sidebar__footer">
          <div style={{ padding: '6px 8px', marginBottom: '4px' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Administrator
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {user?.email || 'admin@careerbeacon.internal'}
            </div>
          </div>

          <button
            type="button"
            className="nav-item"
            onClick={() => setShowLogoutToast(true)}
            style={{ color: 'var(--text-secondary)' }}
          >
            <LogOut size={16} className="nav-item__icon" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main Administrative Workspace */}
      <div className="app-main" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header className="app-topbar" style={{ flexWrap: 'wrap', gap: '8px', height: 'auto', minHeight: '58px', paddingTop: '8px', paddingBottom: '8px' }}>
          <div className="app-topbar__left" style={{ minWidth: 0, flexWrap: 'wrap', gap: '6px' }}>
            <button
              type="button"
              className="topbar-sidebar-toggle"
              onClick={() => setMobileMenuOpen((o) => !o)}
              aria-label="Toggle navigation drawer"
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <span style={{ fontSize: '0.98rem', fontWeight: 700, fontFamily: 'var(--font-display)', lineHeight: 1.25 }}>
              Career Beacon System Governance
            </span>
            <span className="desktop-collapse-btn" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              · Live Admin Command Center
            </span>
          </div>

          <div className="app-topbar__right" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={loadAdminData}
              disabled={loading}
              title="Refresh Metrics"
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
            <ThemeSelector />
          </div>
        </header>

        <main className="app-content" style={{ flex: 1, minWidth: 0 }}>
          {/* TAB 1: OVERVIEW & SYSTEM HEALTH */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>System Health &amp; Activity Overview</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Platform telemetry across learner onboarding, mentor ecosystem engagement, and taxonomy induction.
                </p>
              </div>

              {/* KPI Metric Cards */}
              {loading && !stats ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '14px' }} aria-busy="true" aria-label="Loading system metrics">
                    {Array.from({ length: 4 }).map((_, idx) => (
                      <div key={idx} className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <Skeleton width="55%" height="13px" />
                        <Skeleton width="35%" height="28px" />
                        <Skeleton width="70%" height="12px" />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '16px' }}>
                    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <Skeleton width="45%" height="18px" />
                      <Skeleton width="100%" height="22px" />
                      <Skeleton width="100%" height="22px" />
                      <Skeleton width="100%" height="22px" />
                      <Skeleton width="100%" height="22px" />
                    </div>
                    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <Skeleton width="55%" height="18px" />
                      <Skeleton width="100%" height="72px" />
                      <Skeleton width="180px" height="32px" radius="var(--r-sm)" />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '14px' }}>
                    <div className="card" style={{ padding: '18px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Registered Learners</div>
                      <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--text-primary)' }}>
                        {stats?.learner_count ?? 0}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Active vocational profiles</div>
                    </div>

                    <div className="card" style={{ padding: '18px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Registered Mentors</div>
                      <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--accent)' }}>
                        {stats?.mentor_count ?? 0}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Industry advisors &amp; experts</div>
                    </div>

                    <div className="card" style={{ padding: '18px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>1-on-1 Sessions</div>
                      <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--status-success)' }}>
                        {stats?.total_sessions ?? 0}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {stats?.completed_sessions ?? 0} completed &amp; reviewed
                      </div>
                    </div>

                    <div className="card" style={{ padding: '18px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Taxonomy Knowledge Base</div>
                      <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--text-primary)' }}>
                        {stats?.total_careers ?? 0}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: stats?.unreviewed_careers ? 'var(--status-warning)' : 'var(--text-muted)', marginTop: '4px', fontWeight: 600 }}>
                        {stats?.unreviewed_careers ?? 0} pending review
                      </div>
                    </div>
                  </div>

                  {/* Secondary Stats */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '16px' }}>
                    <div className="card">
                      <h3 style={{ fontSize: '1.02rem', marginBottom: '12px' }}>Mentorship Activity</h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.86rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Accepted Mentee Connections</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{stats?.active_connections ?? 0}</strong>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.86rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Q&amp;A Hub Inquiries</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{stats?.total_questions ?? 0}</strong>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '0.86rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Verified Mentor Answers</span>
                          <strong style={{ color: 'var(--status-success)' }}>{stats?.answered_questions ?? 0}</strong>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: '0.86rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Mentor Pulse Feed Posts</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{stats?.total_pulse_posts ?? 0}</strong>
                        </div>
                      </div>
                    </div>

                    <div className="card">
                      <h3 style={{ fontSize: '1.02rem', marginBottom: '12px' }}>Academic Governance Summary</h3>
                      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                        The Career Beacon AI Engine operates on an <strong>Adaptive Occupational Induction Architecture</strong> with <strong>Human-by-Exception Governance</strong>. New career trajectories proposed or searched by users are provisionally induced with 8&ndash;10 testable vocational competencies, logged with provenance metadata (<code>source_origin: &apos;llm&apos;</code>), and queued for administrator verification.
                      </p>
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        style={{ marginTop: '12px' }}
                        onClick={() => setActiveTab('taxonomy')}
                      >
                        Open Taxonomy Review Desk ({pendingCareers.length})
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* TAB 2: TAXONOMY GOVERNANCE DESK */}
          {activeTab === 'taxonomy' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Career Taxonomy Governance</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Review, approve, or archive organically induced occupations and verify their 8&ndash;10 atomic vocational competencies.
                </p>
              </div>

              {pendingCareers.length === 0 ? (
                <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
                  <CheckCircle2 size={32} style={{ color: 'var(--status-success)', margin: '0 auto 10px' }} />
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '4px' }}>All Career Trajectories Verified</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    There are no unreviewed or pending career taxonomies awaiting approval.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {pendingCareers.map((c) => (
                    <div key={c.id} className="card" style={{ padding: '18px 22px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '12px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <h3 style={{ fontSize: '1.12rem', margin: 0 }}>{c.title}</h3>
                            <span className="badge badge--warning">Unreviewed Induction</span>
                          </div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            Origin: {c.source_origin} · Induced on {new Date(c.created_at).toLocaleDateString()}
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            style={{ color: 'var(--status-danger)' }}
                            onClick={() => handleRejectCareer(c.id, c.title)}
                            disabled={actionInProgress}
                          >
                            <X size={14} />
                            <span>Reject &amp; Archive</span>
                          </button>
                          <button
                            type="button"
                            className="btn btn--primary btn--sm"
                            onClick={() => handleApproveCareer(c.id, c.title)}
                            disabled={actionInProgress}
                          >
                            <Check size={14} />
                            <span>Approve &amp; Verify</span>
                          </button>
                        </div>
                      </div>

                      {c.description && (
                        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                          {c.description}
                        </p>
                      )}

                      <div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
                          Attached Vocational Competencies ({c.skills?.length || 0}):
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {(c.skills || []).map((s) => (
                            <span
                              key={s.id || s.name}
                              className="badge badge--neutral"
                              style={{ fontSize: '0.74rem', padding: '3px 8px' }}
                            >
                              {s.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: MENTOR CREDENTIAL VERIFICATION */}
          {activeTab === 'mentors' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Mentor Credential Verification</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Audit advisor profiles, inspect professional background credentials, and toggle the Gold Verified Mentor badge.
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {mentors.map((m) => (
                  <div key={m.mentor_id} className="card" style={{ padding: '18px 22px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div
                          style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'var(--accent-soft)',
                            color: 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.1rem',
                            fontWeight: 700,
                          }}
                        >
                          {m.full_name?.charAt(0) || 'M'}
                        </div>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h3 style={{ fontSize: '1.05rem', margin: 0 }}>{m.full_name}</h3>
                            {m.is_verified ? (
                              <span className="badge badge--success" style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                                <Award size={12} /> Verified Mentor
                              </span>
                            ) : (
                              <span className="badge badge--neutral">Standard Advisor</span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {m.headline || 'Industry Specialist'} · {m.primary_domain}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        className={`btn btn--sm ${m.is_verified ? 'btn--secondary' : 'btn--primary'}`}
                        onClick={() => handleToggleMentorVerify(m.mentor_id, m.is_verified)}
                        disabled={actionInProgress}
                      >
                        {m.is_verified ? 'Revoke Verified Badge' : 'Grant Verified Mentor Badge'}
                      </button>
                    </div>

                    {m.bio && (
                      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '0 0 10px', lineHeight: 1.45 }}>
                        {m.bio}
                      </p>
                    )}

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {(m.expertise_skills || []).map((sk) => (
                        <span key={sk} className="badge badge--neutral" style={{ fontSize: '0.72rem' }}>
                          {sk}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: SAFETY & CONTENT MODERATION */}
          {activeTab === 'moderation' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1100px' }}>
              <div>
                <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Safety &amp; Content Moderation</h1>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                  Audit reported chat messages, spam links, and community pulse posts flagged by users.
                </p>
              </div>

              {flaggedItems.length === 0 ? (
                <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
                  <CheckCircle2 size={32} style={{ color: 'var(--status-success)', margin: '0 auto 10px' }} />
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '4px' }}>All Clear &ndash; No Flagged Content</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    There are no reported messages or suspicious content items pending administrator action.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {flaggedItems.map((item) => (
                    <div key={item.id} className="card" style={{ padding: '18px 22px', borderLeft: '4px solid var(--status-danger)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="badge badge--danger" style={{ textTransform: 'uppercase' }}>
                              {item.item_type} Report
                            </span>
                            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                              Context: {item.target_context}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                            Flagged for: {item.reason} · Reported {new Date(item.created_at).toLocaleString()}
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => handleModerationAction(item.id, 'dismiss', item.item_type)}
                            disabled={actionInProgress}
                          >
                            Dismiss Report
                          </button>
                          <button
                            type="button"
                            className="btn btn--danger btn--sm"
                            onClick={() => handleModerationAction(item.id, 'delete', item.item_type)}
                            disabled={actionInProgress}
                          >
                            <Trash2 size={13} />
                            <span>Remove Content &amp; Warn</span>
                          </button>
                        </div>
                      </div>

                      <div
                        style={{
                          padding: '10px 14px',
                          background: 'var(--surface-subtle)',
                          borderRadius: 'var(--r-sm)',
                          fontSize: '0.84rem',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--status-danger)',
                        }}
                      >
                        &ldquo;{item.content_snippet}&rdquo;
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: CONTENT INGESTION & RESERVOIR */}
          {activeTab === 'ingestion' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', maxWidth: '1200px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h1 style={{ fontSize: '1.45rem', marginBottom: '4px' }}>Content Ingestion &amp; Curriculum Reservoir</h1>
                  <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                    Autonomous Offline Ingestion Plane: multi-source academic polling, pedagogical vector gates, and Supabase reservoir seeding.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={loadIngestionData}
                  disabled={ingesting || batchIngesting || batchPersonalizing}
                >
                  <RefreshCw size={13} />
                  <span>Refresh Reservoir</span>
                </button>
              </div>

              {/* Reservoir Summary Cards */}
              {loadingIngestion && !ingestionOverview ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '14px' }} aria-busy="true" aria-label="Loading curriculum reservoir stats">
                  {Array.from({ length: 4 }).map((_, idx) => (
                    <div key={idx} className="card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <Skeleton width="60%" height="13px" />
                      <Skeleton width="35%" height="28px" />
                      <Skeleton width="75%" height="12px" />
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: '14px' }}>
                  <div className="card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Total Reservoir Lessons</div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--text-primary)' }}>
                      {ingestionOverview?.total_lessons ?? 0}
                    </div>
                    <div style={{ fontSize: '0.73rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Verified in Supabase micro_content</div>
                  </div>

                  <div className="card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Unique Enrolled Skills Stocked</div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--accent)' }}>
                      {ingestionOverview?.unique_skills_seeded ?? 0}
                    </div>
                    <div style={{ fontSize: '0.73rem', color: 'var(--text-secondary)', marginTop: '4px' }}>With active learner demand</div>
                  </div>

                  <div className="card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Skills Needing Ingestion</div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 750, color: skillPriorities.filter((s) => s.needs_ingestion).length > 0 ? 'var(--status-warning)' : 'var(--status-success)' }}>
                      {skillPriorities.filter((s) => s.needs_ingestion).length}
                    </div>
                    <div style={{ fontSize: '0.73rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Fewer than 4 lessons in reservoir</div>
                  </div>

                  <div className="card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Active Source Adapters</div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 750, color: 'var(--text-primary)' }}>
                      {Object.keys(ingestionOverview?.adapter_breakdown || {}).length}
                    </div>
                    <div style={{ fontSize: '0.73rem', color: 'var(--text-secondary)', marginTop: '4px' }}>NCBI, MDN, YouTube, ArXiv, etc.</div>
                  </div>
                </div>
              )}

              {/* Switchable Content Ingestion Sub-Tabs */}
              <div className="segmented-tabs" role="tablist" aria-label="Content ingestion views" style={{ alignSelf: 'flex-start', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  role="tab"
                  aria-selected={ingestionSubTab === 'workers'}
                  className={`segmented-tab ${ingestionSubTab === 'workers' ? 'segmented-tab--active' : ''}`}
                  onClick={() => setIngestionSubTab('workers')}
                >
                  <span>Workers &amp; Telemetry</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={ingestionSubTab === 'batches'}
                  className={`segmented-tab ${ingestionSubTab === 'batches' ? 'segmented-tab--active' : ''}`}
                  onClick={() => setIngestionSubTab('batches')}
                >
                  <span>Commit Batches</span>
                  <span className="segmented-tab__count">{ingestionBatches.length}</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={ingestionSubTab === 'skills'}
                  className={`segmented-tab ${ingestionSubTab === 'skills' ? 'segmented-tab--active' : ''}`}
                  onClick={() => setIngestionSubTab('skills')}
                >
                  <span>Enrolled Skills</span>
                  <span className="segmented-tab__count">{skillPriorities.length}</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={ingestionSubTab === 'lessons'}
                  className={`segmented-tab ${ingestionSubTab === 'lessons' ? 'segmented-tab--active' : ''}`}
                  onClick={() => setIngestionSubTab('lessons')}
                >
                  <span>Seeded Lessons</span>
                  <span className="segmented-tab__count">{reservoirLessons.length}</span>
                </button>
              </div>

              {ingestionSubTab === 'workers' && (
                <>
                  {/* Action Controls: Nightly Ingestion Worker vs Daily Drop Worker */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: '16px' }}>
                    {/* Panel 1: Nightly Autonomous Ingestion Worker */}
                    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div>
                        <span className="badge badge--primary" style={{ marginBottom: '6px', display: 'inline-block' }}>Autonomous Ingestion Plane</span>
                        <h3 style={{ fontSize: '1rem', fontWeight: 650, margin: '2px 0 6px 0' }}>Nightly Multi-Skill Ingestion Worker</h3>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                          Iterates over enrolled skills with low lesson counts (&lt;4). Polls domain adapters, runs vector quality checks, and seeds Supabase without blocking learners.
                        </p>
                      </div>
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        onClick={handleRunNightlyBatch}
                        disabled={batchIngesting || ingesting}
                        style={{ alignSelf: 'flex-start' }}
                      >
                        <RefreshCw size={13} className={batchIngesting ? 'spin' : ''} />
                        <span>{batchIngesting ? 'Running Multi-Skill Ingestion Sweep...' : 'Run Nightly Ingestion Worker'}</span>
                      </button>
                    </div>

                    {/* Panel 2: Daily Drop Personalization Worker */}
                    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div>
                        <span className="badge badge--secondary" style={{ marginBottom: '6px', display: 'inline-block' }}>Online Personalization Plane</span>
                        <h3 style={{ fontSize: '1rem', fontWeight: 650, margin: '2px 0 6px 0' }}>Daily Drop Personalization Worker</h3>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                          Assembles personalized 5-primary + 5-reserve drops for all active learners from the pre-seeded reservoir, applying RRF ranking and impression cooldown.
                        </p>
                      </div>
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={handleRunDailyDropBatch}
                        disabled={batchPersonalizing || ingesting}
                        style={{ alignSelf: 'flex-start' }}
                      >
                        <RefreshCw size={13} className={batchPersonalizing ? 'spin' : ''} />
                        <span>{batchPersonalizing ? 'Curating All Learner Drops...' : 'Run Daily Drop Personalization Worker'}</span>
                      </button>
                    </div>

                    {/* Panel 3: Live Ingestion Probe (Supervisor Demo) */}
                    <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div>
                        <span className="badge badge--warning" style={{ marginBottom: '6px', display: 'inline-block' }}>Supervisor Live Demo</span>
                        <h3 style={{ fontSize: '1rem', fontWeight: 650, margin: '2px 0 6px 0' }}>Single-Skill Ingestion Probe</h3>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                          Test the full live pipeline on any custom career and skill on demand instead of running the full nightly queue.
                        </p>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '8px' }}>
                        <div>
                          <label htmlFor="demo-career-input" style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                            Target Career
                          </label>
                          <input
                            id="demo-career-input"
                            type="text"
                            className="input input--sm"
                            value={selectedCareer}
                            onChange={(e) => setSelectedCareer(e.target.value)}
                            placeholder="e.g. Backend Software Engineer"
                            disabled={ingesting}
                          />
                        </div>
                        <div>
                          <label htmlFor="demo-skill-input" style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                            Target Skill
                          </label>
                          <input
                            id="demo-skill-input"
                            type="text"
                            className="input input--sm"
                            value={selectedSkill}
                            onChange={(e) => setSelectedSkill(e.target.value)}
                            placeholder="e.g. RESTful API Design"
                            disabled={ingesting}
                          />
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={handleRunSingleIngestion}
                        disabled={ingesting || !selectedCareer || !selectedSkill}
                        style={{ alignSelf: 'flex-start' }}
                      >
                        <RefreshCw size={13} className={ingesting ? 'spin' : ''} />
                        <span>{ingesting ? 'Executing Live Ingestion...' : 'Execute Live Ingestion Probe'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Live Execution Telemetry Stream */}
                  <div className="card" style={{ padding: '18px 20px', background: 'var(--surface-subtle)', border: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-primary)' }}>
                          Ingestion Telemetry Stream &amp; Quality Audit
                        </span>
                        {(ingesting || batchIngesting || batchPersonalizing) && (
                          <span className="badge badge--primary" style={{ fontSize: '0.68rem', animation: 'pulse 1.5s infinite' }}>
                            ACTIVE STREAM
                          </span>
                        )}
                      </div>
                      {ingestionLogs.length > 0 && (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          style={{ fontSize: '0.72rem', padding: '2px 8px' }}
                          onClick={() => setIngestionLogs([])}
                        >
                          Clear Logs
                        </button>
                      )}
                    </div>
                    <div
                      style={{
                        minHeight: '120px',
                        maxHeight: '260px',
                        overflowY: 'auto',
                        fontFamily: 'var(--font-mono, monospace)',
                        fontSize: '0.76rem',
                        lineHeight: '1.55',
                        background: '#0d1117',
                        color: '#c9d1d9',
                        padding: '12px 14px',
                        borderRadius: 'var(--r-sm)',
                        border: '1px solid #30363d',
                      }}
                    >
                      {ingestionLogs.length === 0 ? (
                        <div style={{ color: '#8b949e', fontStyle: 'italic' }}>
                          Telemetry idle. Click &quot;Run Nightly Ingestion Worker&quot; or &quot;Execute Live Ingestion Probe&quot; to inspect real-time source retrieval, vector quality checks, and quiz grounding logs.
                        </div>
                      ) : (
                        ingestionLogs.map((log, idx) => {
                          const isErr = log.includes('FAILED') || log.includes('ERROR') || log.includes('REJECTED');
                          const isSuccess = log.includes('SUCCESS') || log.includes('Committed');
                          const color = isErr ? '#ff7b72' : isSuccess ? '#7ee787' : '#c9d1d9';
                          return (
                            <div key={idx} style={{ color, whiteSpace: 'pre-wrap' }}>
                              {log}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </>
              )}

              {ingestionSubTab === 'batches' && (
                /* Git-Commit Style Ingestion Ledger & Inline Batch Inspector */
                <div className="card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 650, marginBottom: '4px' }}>Ingestion Commit Ledger &amp; Batch Inspector</h3>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        Click any commit row to inspect batch stats, view the exact lessons seeded, audit retrieved sources, or approve/disapprove the batch.
                      </p>
                    </div>
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                      {ingestionBatches.length} Commits
                    </span>
                  </div>

                  {ingestionBatches.length === 0 ? (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                      No ingestion commits recorded yet.
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                            <th style={{ padding: '8px 12px' }}>Commit</th>
                            <th style={{ padding: '8px 12px' }}>Description / Message</th>
                            <th style={{ padding: '8px 12px' }}>Target Domain</th>
                            <th style={{ padding: '8px 12px' }}>Batch Scope</th>
                            <th style={{ padding: '8px 12px' }}>Status</th>
                            <th style={{ padding: '8px 12px', textAlign: 'right' }}>Governance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ingestionBatches.map((b) => {
                            const isApproved = b.status === 'approved';
                            const isRejected = b.status === 'rejected';
                            const isSelected = selectedBatch?.id === b.id;

                            const ids = Array.isArray(b.lesson_ids) ? b.lesson_ids : [];
                            const targetSkillLower = (b.skill_name || '').trim().toLowerCase();
                            const idMatchedLessons = ids.length > 0
                              ? reservoirLessons.filter((l) => ids.includes(l.id))
                              : [];
                            const matchedBySkill = idMatchedLessons.length === 0
                              ? reservoirLessons.filter(
                                  (l) =>
                                    (b.skill_id && l.associated_skill_id === b.skill_id) ||
                                    (targetSkillLower && (l.skill_name || '').trim().toLowerCase() === targetSkillLower)
                                )
                              : [];
                            const seededLessonsForBatch = idMatchedLessons.length > 0 ? idMatchedLessons : matchedBySkill;
                            const isSkillFallbackMatch = idMatchedLessons.length === 0 && matchedBySkill.length > 0;
                            const sources = b.sources || [];
                            const avgTrust = sources.length > 0
                              ? Math.round((sources.reduce((acc, s) => acc + (s.trust_score ?? 0.95), 0) / sources.length) * 100)
                              : 95;
                            const batchLessonTotal = b.lesson_count ?? seededLessonsForBatch.length;
                            const batchQuizTotal = b.quiz_count ?? (batchLessonTotal * 5);

                            return (
                              <Fragment key={b.id || b.commit_hash}>
                                <tr
                                  onClick={() => setSelectedBatch(isSelected ? null : b)}
                                  style={{
                                    borderBottom: isSelected ? 'none' : '1px solid var(--border)',
                                    background: isSelected ? 'var(--accent-soft)' : 'transparent',
                                    cursor: 'pointer',
                                  }}
                                >
                                  <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 650, color: 'var(--accent)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                                      <GitCommit size={14} />
                                      <span>{b.commit_hash}</span>
                                    </div>
                                  </td>
                                  <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)', maxWidth: '300px' }}>
                                    <div>{b.message}</div>
                                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                      {b.author || 'Admin / Ingestion Worker'} · {b.created_at ? new Date(b.created_at).toLocaleString() : 'Recent'}
                                    </div>
                                  </td>
                                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                                    <div style={{ fontWeight: 550 }}>{b.career_title}</div>
                                    <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>{b.skill_name}</div>
                                  </td>
                                  <td style={{ padding: '10px 12px' }}>
                                    <span className="btn btn--secondary btn--sm" style={{ fontSize: '0.72rem', padding: '3px 8px', pointerEvents: 'none' }}>
                                      {isSelected ? 'Hide Details' : `${sources.length} Sources · ${batchLessonTotal} Lessons`}
                                    </span>
                                  </td>
                                  <td style={{ padding: '10px 12px' }}>
                                    {isApproved && <span className="badge badge--success" style={{ fontSize: '0.7rem' }}>Approved</span>}
                                    {isRejected && <span className="badge badge--danger" style={{ fontSize: '0.7rem' }}>Disapproved</span>}
                                    {!isApproved && !isRejected && <span className="badge badge--warning" style={{ fontSize: '0.7rem' }}>Pending</span>}
                                  </td>
                                  <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                                      {isApproved ? (
                                        <button
                                          type="button"
                                          className="btn btn--secondary btn--sm"
                                          style={{ fontSize: '0.72rem', padding: '3px 8px', color: 'var(--status-danger)' }}
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleBatchStatusChange(b.id, 'rejected');
                                          }}
                                        >
                                          Disapprove
                                        </button>
                                      ) : (
                                        <button
                                          type="button"
                                          className="btn btn--primary btn--sm"
                                          style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleBatchStatusChange(b.id, 'approved');
                                          }}
                                        >
                                          Approve
                                        </button>
                                      )}
                                    </div>
                                  </td>
                                </tr>

                                {isSelected && (
                                  <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface-subtle)' }}>
                                    <td colSpan={6} style={{ padding: '16px 18px' }}>
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                        {/* Batch Stats Row */}
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                                          <div>
                                            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                                              Commit Audit #{b.commit_hash}
                                            </div>
                                            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                              {b.summary || 'Authoritative source audit and seeded curriculum output for this ingestion run.'}
                                            </div>
                                          </div>
                                          <button
                                            type="button"
                                            className="btn btn--ghost btn--sm"
                                            onClick={() => setSelectedBatch(null)}
                                          >
                                            Close Details
                                          </button>
                                        </div>

                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
                                          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '10px 12px' }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Lessons Seeded</div>
                                            <div style={{ fontSize: '1.25rem', fontWeight: 750, color: 'var(--text-primary)' }}>{batchLessonTotal}</div>
                                          </div>
                                          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '10px 12px' }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Quiz Checkpoints</div>
                                            <div style={{ fontSize: '1.25rem', fontWeight: 750, color: 'var(--accent)' }}>{batchQuizTotal}</div>
                                          </div>
                                          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '10px 12px' }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Audited Sources</div>
                                            <div style={{ fontSize: '1.25rem', fontWeight: 750, color: 'var(--text-primary)' }}>{sources.length}</div>
                                          </div>
                                          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '10px 12px' }}>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Avg Source Trust</div>
                                            <div style={{ fontSize: '1.25rem', fontWeight: 750, color: 'var(--status-success)' }}>{avgTrust}%</div>
                                          </div>
                                        </div>

                                        {/* What Was Seeded */}
                                        <div>
                                          <h4 style={{ fontSize: '0.84rem', fontWeight: 650, marginBottom: '8px', color: 'var(--text-primary)' }}>
                                            Seeded Lessons ({seededLessonsForBatch.length})
                                            {isSkillFallbackMatch && (
                                              <span style={{ fontWeight: 400, fontSize: '0.74rem', color: 'var(--text-muted)', marginLeft: '8px' }}>
                                                (Matched by target skill in Supabase reservoir)
                                              </span>
                                            )}
                                          </h4>
                                          {seededLessonsForBatch.length === 0 ? (
                                            <div style={{ padding: '12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                              No matching lesson rows found in the loaded reservoir snapshot for this commit ({b.skill_name}).
                                            </div>
                                          ) : (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                              {seededLessonsForBatch.map((l) => (
                                                <div
                                                  key={l.id}
                                                  style={{
                                                    display: 'flex',
                                                    justifyContent: 'space-between',
                                                    alignItems: 'center',
                                                    gap: '12px',
                                                    flexWrap: 'wrap',
                                                    background: 'var(--surface)',
                                                    border: '1px solid var(--border)',
                                                    borderRadius: 'var(--r-sm)',
                                                    padding: '10px 12px',
                                                  }}
                                                >
                                                  <div style={{ minWidth: 0, flex: 1 }}>
                                                    <div style={{ fontWeight: 650, fontSize: '0.83rem', color: 'var(--text-primary)' }}>
                                                      {l.title}
                                                    </div>
                                                    <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)', marginTop: '2px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                                                      <span className="badge badge--secondary" style={{ textTransform: 'uppercase', fontSize: '0.65rem' }}>
                                                        {l.source_adapter || 'web'}
                                                      </span>
                                                      <span>{l.skill_name || b.skill_name}</span>
                                                      <span>· Level {l.difficulty_level || 2}</span>
                                                      <span>· {l.quizzes?.length || 5} MCQs</span>
                                                    </div>
                                                  </div>
                                                  <button
                                                    type="button"
                                                    className="btn btn--secondary btn--sm"
                                                    style={{ fontSize: '0.72rem', padding: '4px 10px' }}
                                                    onClick={() => handleOpenEditLesson(l)}
                                                  >
                                                    <Edit3 size={11} />
                                                    <span>Inspect / Edit</span>
                                                  </button>
                                                </div>
                                              ))}
                                            </div>
                                          )}
                                        </div>

                                        {/* Audited Sources */}
                                        <div>
                                          <h4 style={{ fontSize: '0.84rem', fontWeight: 650, marginBottom: '8px', color: 'var(--text-primary)' }}>
                                            Audited Knowledge Sources ({sources.length})
                                          </h4>
                                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: '10px' }}>
                                            {sources.map((s, sIdx) => (
                                              <div
                                                key={sIdx}
                                                style={{
                                                  background: 'var(--surface)',
                                                  border: '1px solid var(--border)',
                                                  borderRadius: 'var(--r-sm)',
                                                  padding: '10px 12px',
                                                }}
                                              >
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', gap: '8px' }}>
                                                  <span style={{ fontWeight: 650, fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                                                    {s.name}
                                                  </span>
                                                  <span className="badge badge--secondary" style={{ fontSize: '0.64rem', textTransform: 'uppercase' }}>
                                                    {s.adapter}
                                                  </span>
                                                </div>
                                                {s.url && (
                                                  <a
                                                    href={s.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{
                                                      fontSize: '0.73rem',
                                                      color: 'var(--accent)',
                                                      display: 'inline-flex',
                                                      alignItems: 'center',
                                                      gap: '4px',
                                                      marginBottom: '4px',
                                                      wordBreak: 'break-all',
                                                    }}
                                                  >
                                                    <span>Inspect Source URL</span>
                                                    <ExternalLink size={12} />
                                                  </a>
                                                )}
                                                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                                  Calibrated Base Trust: <strong>{((s.trust_score || 0.95) * 100).toFixed(0)}%</strong>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      </div>
                                    </td>
                                  </tr>
                                )}
                              </Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {ingestionSubTab === 'skills' && (
                /* Enrolled Skills Prioritization Table */
                <div className="card" style={{ padding: '20px' }}>
                  <div style={{ marginBottom: '14px' }}>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 650, marginBottom: '4px' }}>Enrolled Skills Reservoir Status</h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      Ranked by learner deficit demand and current lesson coverage in Supabase. Low-coverage skills are automatically targeted by the nightly ingestion worker.
                    </p>
                  </div>

                  {skillPriorities.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                      No enrolled skill demand recorded yet. Register learners or run onboarding to track skills.
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                            <th style={{ padding: '8px 12px' }}>Skill Competency</th>
                            <th style={{ padding: '8px 12px' }}>Career Discipline</th>
                            <th style={{ padding: '8px 12px' }}>Enrolled</th>
                            <th style={{ padding: '8px 12px' }}>Deficits (&le;50%)</th>
                            <th style={{ padding: '8px 12px' }}>Reservoir Lessons</th>
                            <th style={{ padding: '8px 12px' }}>Status</th>
                            <th style={{ padding: '8px 12px', textAlign: 'right' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {skillPriorities.map((item) => (
                            <tr key={item.skill_id} style={{ borderBottom: '1px solid var(--border)' }}>
                              <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                                {item.skill_name}
                              </td>
                              <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                                {item.career_title}
                              </td>
                              <td style={{ padding: '10px 12px' }}>{item.enrolled_count}</td>
                              <td style={{ padding: '10px 12px', color: item.deficit_count > 0 ? 'var(--status-warning)' : 'var(--text-secondary)' }}>
                                {item.deficit_count}
                              </td>
                              <td style={{ padding: '10px 12px', fontWeight: 600 }}>
                                {item.current_lesson_count} / 4
                              </td>
                              <td style={{ padding: '10px 12px' }}>
                                {item.needs_ingestion ? (
                                  <span className="badge badge--warning" style={{ fontSize: '0.7rem' }}>Needs Ingestion</span>
                                ) : (
                                  <span className="badge badge--success" style={{ fontSize: '0.7rem' }}>Well Stocked</span>
                                )}
                              </td>
                              <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                                <button
                                  type="button"
                                  className="btn btn--secondary btn--sm"
                                  style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                                  onClick={() => {
                                    setSelectedCareer(item.career_title);
                                    setSelectedSkill(item.skill_name);
                                    setIngestionSubTab('workers');
                                    handleRunSingleIngestion(item.career_title, item.skill_name);
                                  }}
                                  disabled={ingesting}
                                >
                                  Seed Lesson
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {ingestionSubTab === 'lessons' && (
                /* Seeded Curriculum Reservoir Lessons Table */
                <div className="card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 650, marginBottom: '4px' }}>Seeded Curriculum Reservoir Lessons</h3>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        Lessons stored in Supabase micro_content available for instant Daily Drop curation.
                      </p>
                    </div>
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                      Showing {Math.min(reservoirLessons.length, 50)} of {reservoirLessons.length} lessons
                    </span>
                  </div>

                  {reservoirLessons.length === 0 ? (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                      Reservoir is currently empty. Run the Nightly Ingestion Worker to seed lessons into Supabase.
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                            <th style={{ padding: '8px 12px' }}>Lesson Title</th>
                            <th style={{ padding: '8px 12px' }}>Skill Competency</th>
                            <th style={{ padding: '8px 12px' }}>Adapter / Source</th>
                            <th style={{ padding: '8px 12px' }}>Difficulty</th>
                            <th style={{ padding: '8px 12px' }}>Checkpoints</th>
                            <th style={{ padding: '8px 12px' }}>Ingested</th>
                            <th style={{ padding: '8px 12px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reservoirLessons.slice(0, 50).map((l) => (
                            <tr key={l.id} style={{ borderBottom: '1px solid var(--border)', opacity: l.review_status === 'rejected' ? 0.6 : 1 }}>
                              <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)', maxWidth: '300px' }}>
                                <div>{l.title}</div>
                                {l.review_status === 'rejected' && (
                                  <span className="badge badge--danger" style={{ fontSize: '0.65rem', marginTop: '4px', display: 'inline-block' }}>
                                    Rejected / Hidden
                                  </span>
                                )}
                              </td>
                              <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                                {l.skill_name || 'Core Skill'}
                              </td>
                              <td style={{ padding: '10px 12px' }}>
                                <span className="badge badge--secondary" style={{ textTransform: 'uppercase', fontSize: '0.68rem' }}>
                                  {l.source_adapter || 'web'}
                                </span>
                              </td>
                              <td style={{ padding: '10px 12px' }}>
                                Level {l.difficulty_level || 2}
                              </td>
                              <td style={{ padding: '10px 12px', color: 'var(--status-success)' }}>
                                {l.quizzes?.length || 5} Qs
                              </td>
                              <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.74rem' }}>
                                {l.created_at ? new Date(l.created_at).toLocaleDateString() : 'Active'}
                              </td>
                              <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                                <button
                                  type="button"
                                  className="btn btn--secondary btn--sm"
                                  style={{ fontSize: '0.72rem', padding: '3px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                  onClick={() => handleOpenEditLesson(l)}
                                >
                                  <Edit3 size={11} />
                                  <span>Edit</span>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Lesson Edit Modal */}
      {editingLesson && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !savingLesson) setEditingLesson(null);
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: '720px',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              border: '1px solid var(--border)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '4px' }}>
                  Edit Ingested Lesson &amp; Checkpoint
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Refine lesson prose, practical scenario, difficulty, or multiple-choice questions.
                </p>
              </div>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setEditingLesson(null)}
                disabled={savingLesson}
              >
                Cancel
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 650, display: 'block', marginBottom: '4px' }}>
                  Lesson Title
                </label>
                <input
                  type="text"
                  className="input input--sm"
                  style={{ width: '100%' }}
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 650, display: 'block', marginBottom: '4px' }}>
                    Associated Skill Competency
                  </label>
                  <input
                    type="text"
                    className="input input--sm"
                    style={{ width: '100%' }}
                    value={editingLesson.skill_name || 'Core Skill'}
                    disabled
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 650, display: 'block', marginBottom: '4px' }}>
                    Difficulty Level (1-5)
                  </label>
                  <select
                    className="input input--sm"
                    style={{ width: '100%' }}
                    value={editForm.difficulty_level}
                    onChange={(e) => setEditForm({ ...editForm, difficulty_level: parseInt(e.target.value) || 2 })}
                  >
                    <option value={1}>Level 1 - Introductory</option>
                    <option value={2}>Level 2 - Foundational</option>
                    <option value={3}>Level 3 - Intermediate / Professional</option>
                    <option value={4}>Level 4 - Advanced Specialist</option>
                    <option value={5}>Level 5 - Expert / Mastery</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 650, display: 'block', marginBottom: '4px' }}>
                  Executive Summary / High-Yield Takeaway
                </label>
                <textarea
                  className="input input--sm"
                  rows={3}
                  style={{ width: '100%', resize: 'vertical' }}
                  value={editForm.summary}
                  onChange={(e) => setEditForm({ ...editForm, summary: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 650, display: 'block', marginBottom: '4px' }}>
                  Concept Overview (Mini-Lesson Text)
                </label>
                <textarea
                  className="input input--sm"
                  rows={4}
                  style={{ width: '100%', resize: 'vertical' }}
                  value={editForm.concept_overview}
                  onChange={(e) => setEditForm({ ...editForm, concept_overview: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 650, display: 'block', marginBottom: '4px' }}>
                  Applied Workplace Practice Scenario
                </label>
                <textarea
                  className="input input--sm"
                  rows={3}
                  style={{ width: '100%', resize: 'vertical' }}
                  value={editForm.practice_scenario}
                  onChange={(e) => setEditForm({ ...editForm, practice_scenario: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setEditingLesson(null)}
                disabled={savingLesson}
              >
                Discard
              </button>
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={handleSaveEditLesson}
                disabled={savingLesson || !editForm.title.trim()}
              >
                <span>{savingLesson ? 'Saving Updates...' : 'Save Lesson & Update Reservoir'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {toastMessage && (
        <Toast
          message={toastMessage}
          onClose={() => setToastMessage(null)}
        />
      )}

      {showLogoutToast && (
        <Toast
          message="Are you sure you want to sign out of the Admin Console?"
          confirmLabel="Sign out"
          onConfirm={handleSignOut}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </div>
  );
}

